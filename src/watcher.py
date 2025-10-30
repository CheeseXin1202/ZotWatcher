"""文献监测模块"""
import logging
import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime, timedelta
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
import arxiv
from crossref.restful import Works

logger = logging.getLogger("ZotWatcher.watcher")


class LiteratureWatcher:
    """文献监测器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.sources_config = config.get("sources", {})
        self.scoring_config = config.get("scoring", {})
        self.data_dir = Path("data")
        
        # 加载向量化模型
        model_name = self.scoring_config.get("semantic", {}).get("model_name", "sentence-transformers/all-MiniLM-L6-v2")
        logger.info(f"加载向量化模型: {model_name}")
        self.model = SentenceTransformer(model_name)
        
        # 加载 FAISS 索引和画像
        self._load_profile()
    
    def _load_profile(self):
        """加载用户画像"""
        try:
            # 加载 FAISS 索引
            index_path = self.data_dir / "faiss.index"
            if index_path.exists():
                self.index = faiss.read_index(str(index_path))
                logger.info(f"已加载 FAISS 索引，包含 {self.index.ntotal} 个向量")
            else:
                self.index = None
                logger.warning("FAISS 索引文件不存在")
            
            # 加载画像统计信息
            profile_json_path = self.data_dir / "profile.json"
            if profile_json_path.exists():
                with open(profile_json_path, 'r', encoding='utf-8') as f:
                    self.profile_stats = json.load(f)
                logger.info(f"已加载画像统计信息")
            else:
                self.profile_stats = {}
                logger.warning("画像统计文件不存在")
                
        except Exception as e:
            logger.error(f"加载画像失败: {e}")
            self.index = None
            self.profile_stats = {}
    
    
    def fetch_candidates(self) -> List[Dict[str, Any]]:
        """抓取候选文章"""
        logger.info("开始抓取候选文章")
        
        candidates = []
        
        # 1. Crossref
        if self.sources_config.get("sources", {}).get("crossref", {}).get("enabled"):
            crossref_articles = self._fetch_crossref()
            candidates.extend(crossref_articles)
            logger.info(f"Crossref: {len(crossref_articles)} 篇")
        
        # 2. arXiv
        if self.sources_config.get("sources", {}).get("arxiv", {}).get("enabled"):
            arxiv_articles = self._fetch_arxiv()
            candidates.extend(arxiv_articles)
            logger.info(f"arXiv: {len(arxiv_articles)} 篇")
        
        # 3. bioRxiv
        if self.sources_config.get("sources", {}).get("biorxiv", {}).get("enabled"):
            biorxiv_articles = self._fetch_biorxiv()
            candidates.extend(biorxiv_articles)
            logger.info(f"bioRxiv: {len(biorxiv_articles)} 篇")
        
        # 4. medRxiv
        if self.sources_config.get("sources", {}).get("medrxiv", {}).get("enabled"):
            medrxiv_articles = self._fetch_medrxiv()
            candidates.extend(medrxiv_articles)
            logger.info(f"medRxiv: {len(medrxiv_articles)} 篇")
        
        # 5. 热门期刊精准抓取
        if self.sources_config.get("top_journals", {}).get("enabled"):
            journal_articles = self._fetch_top_journals()
            candidates.extend(journal_articles)
            logger.info(f"热门期刊: {len(journal_articles)} 篇")
        
        # 去重
        candidates = self._deduplicate(candidates)
        logger.info(f"去重后: {len(candidates)} 篇")
        
        return candidates
    
    def score_and_rank(self, candidates: List[Dict[str, Any]], top_n: int = 100) -> List[Dict[str, Any]]:
        """评分并排序"""
        logger.info(f"开始评分，目标推荐 {top_n} 篇")
        
        if not candidates:
            logger.warning("没有候选文章")
            return []
        
        # 计算各项分数
        for article in candidates:
            scores = {}
            
            # 1. 语义相似度分数
            scores['semantic'] = self._calculate_semantic_similarity(article)
            
            # 2. 时间衰减分数
            scores['time'] = self._calculate_time_decay(article)
            
            # 3. 白名单加分
            scores['whitelist'] = self._calculate_whitelist_bonus(article)
            
            # 计算综合分数
            weights = self.scoring_config.get("weights", {})
            total_score = (
                scores['semantic'] * weights.get('semantic_similarity', 0.4) +
                scores['time'] * weights.get('time_decay', 0.15) +
                scores['whitelist'] * weights.get('whitelist_bonus', 0.05)
            )
            
            article['scores'] = scores
            article['total_score'] = total_score
        
        # 排序
        candidates.sort(key=lambda x: x.get('total_score', 0), reverse=True)
        
        # 返回 top_n
        top_articles = candidates[:top_n]
        logger.info(f"评分完成，返回前 {len(top_articles)} 篇文章")
        
        return top_articles
    
    def _calculate_semantic_similarity(self, article: Dict[str, Any]) -> float:
        """计算语义相似度"""
        try:
            if self.index is None or self.index.ntotal == 0:
                logger.warning("FAISS 索引为空，无法计算语义相似度")
                return 0.0
            
            # 构建文章文本
            title = article.get('title', '')
            abstract = article.get('abstract', '')
            text = f"{title}. {abstract}".strip()
            
            if not text:
                return 0.0
            
            # 向量化
            vector = self.model.encode([text], convert_to_numpy=True)
            
            # 在 FAISS 索引中搜索最相似的向量
            k = min(10, self.index.ntotal)  # 搜索前 10 个最相似的
            distances, indices = self.index.search(vector.astype('float32'), k)
            
            # 将距离转换为相似度（L2 距离越小越相似）
            # 使用负指数函数将距离转换为 [0, 1] 范围的相似度
            similarities = np.exp(-distances[0] / 10.0)
            avg_similarity = np.mean(similarities)
            
            return float(avg_similarity)
            
        except Exception as e:
            logger.error(f"计算语义相似度失败: {e}")
            return 0.0
    
    def _calculate_time_decay(self, article: Dict[str, Any]) -> float:
        """计算时间衰减分数"""
        try:
            # 获取文章日期
            date_str = article.get('date', '')
            if not date_str:
                return 0.5  # 默认中等分数
            
            # 解析日期
            if isinstance(date_str, list):
                date_str = '-'.join(str(x) for x in date_str if x)
            
            try:
                article_date = datetime.strptime(date_str, '%Y-%m-%d')
            except:
                try:
                    article_date = datetime.strptime(date_str[:10], '%Y-%m-%d')
                except:
                    return 0.5
            
            # 计算天数差
            days_ago = (datetime.now() - article_date).days
            
            # 获取配置
            time_config = self.scoring_config.get("time_decay", {})
            mode = time_config.get("mode", "exponential")
            half_life = time_config.get("half_life", 3.5)
            max_days = time_config.get("max_days", 14)
            
            # 超过最大天数，分数为 0
            if days_ago > max_days:
                return 0.0
            
            # 指数衰减
            if mode == "exponential":
                score = np.exp(-days_ago * np.log(2) / half_life)
            else:  # 线性衰减
                daily_decay = time_config.get("daily_decay_rate", 0.1)
                score = max(0, 1 - days_ago * daily_decay)
            
            return float(score)
            
        except Exception as e:
            logger.error(f"计算时间衰减失败: {e}")
            return 0.5
    
    def _calculate_whitelist_bonus(self, article: Dict[str, Any]) -> float:
        """计算白名单加分"""
        try:
            whitelist_config = self.scoring_config.get("whitelist", {})
            if not whitelist_config.get("enabled", False):
                return 0.0
            
            bonus_score = whitelist_config.get("bonus_score", 0.2)
            
            # 检查作者白名单
            whitelist_authors = [a.lower() for a in whitelist_config.get("authors", [])]
            article_authors = [a.lower() for a in article.get('authors', [])]
            
            for author in article_authors:
                if any(wa in author for wa in whitelist_authors):
                    return bonus_score
            
            # 检查期刊白名单
            whitelist_journals = [j.lower() for j in whitelist_config.get("journals", [])]
            article_journal = article.get('journal', '').lower()
            
            if any(wj in article_journal for wj in whitelist_journals):
                return bonus_score
            
            # 检查关键词白名单
            whitelist_keywords = [k.lower() for k in whitelist_config.get("keywords", [])]
            title = article.get('title', '').lower()
            abstract = article.get('abstract', '').lower()
            text = f"{title} {abstract}"
            
            if any(wk in text for wk in whitelist_keywords):
                return bonus_score
            
            return 0.0
            
        except Exception as e:
            logger.error(f"计算白名单加分失败: {e}")
            return 0.0
        return candidates[:top_n]
    
    def generate_rss(self, articles: List[Dict[str, Any]], output_path: Path):
        """生成 RSS feed"""
        logger.info(f"生成 RSS feed: {output_path}")
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 生成 RSS feed
        current_date = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000")
        
        rss_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>ZotWatcher Recommendations</title>
    <description>Personalized academic literature recommendations</description>
    <link>https://github.com/yourusername/ZotWatcher</link>
    <lastBuildDate>{current_date}</lastBuildDate>
  </channel>
</rss>"""
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(rss_content)
        
        logger.info("RSS feed 生成完成")
    
    def generate_html_report(self, articles: List[Dict[str, Any]], output_path: Path):
        """生成 HTML 报告"""
        logger.info(f"生成 HTML 报告: {output_path}")
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 生成 HTML 报告
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        article_count = len(articles)
        
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>ZotWatcher Recommendations</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #333; }}
        .article {{ margin-bottom: 20px; padding: 15px; border: 1px solid #ddd; }}
    </style>
</head>
<body>
    <h1>ZotWatcher 推荐文章</h1>
    <p>生成时间: {current_time}</p>
    <p>共 {article_count} 篇文章</p>
</body>
</html>"""
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        logger.info("HTML 报告生成完成")
    
    def push_to_zotero(self, articles: List[Dict[str, Any]]):
        """推送到 Zotero"""
        logger.info("推送文章到 Zotero")
        # TODO: 实现 Zotero API 推送
        logger.warning("push_to_zotero 尚未实现")
    
    def _fetch_crossref(self) -> List[Dict[str, Any]]:
        """抓取 Crossref"""
        try:
            crossref_config = self.sources_config.get("sources", {}).get("crossref", {})
            recent_days = self.sources_config.get("recent_days", 7)
            
            # 计算日期范围
            end_date = datetime.now()
            start_date = end_date - timedelta(days=recent_days)
            
            logger.info(f"从 Crossref 抓取 {start_date.date()} 到 {end_date.date()} 的文章")
            
            works = Works()
            articles = []
            
            # 查询最近的文章
            query = works.filter(
                from_pub_date=start_date.strftime('%Y-%m-%d'),
                until_pub_date=end_date.strftime('%Y-%m-%d'),
                type='journal-article'
            )
            
            # 获取指定数量的结果
            max_results = crossref_config.get('rows', 100) * crossref_config.get('max_pages', 5)
            count = 0
            
            for item in query:
                if count >= max_results:
                    break
                
                # 提取文章信息
                article = {
                    'title': item.get('title', [''])[0] if item.get('title') else '',
                    'abstract': item.get('abstract', ''),
                    'authors': [f"{a.get('given', '')} {a.get('family', '')}".strip() 
                               for a in item.get('author', [])],
                    'date': item.get('published-print', {}).get('date-parts', [['']])[0],
                    'journal': item.get('container-title', [''])[0] if item.get('container-title') else '',
                    'doi': item.get('DOI', ''),
                    'url': item.get('URL', ''),
                    'source': 'crossref',
                    'type': item.get('type', ''),
                }
                
                articles.append(article)
                count += 1
            
            logger.info(f"从 Crossref 获取到 {len(articles)} 篇文章")
            return articles
            
        except Exception as e:
            logger.error(f"Crossref 抓取失败: {e}")
            return []
    
    def _fetch_arxiv(self) -> List[Dict[str, Any]]:
        """抓取 arXiv"""
        try:
            arxiv_config = self.sources_config.get("sources", {}).get("arxiv", {})
            categories = arxiv_config.get('categories', [])
            max_results = arxiv_config.get('max_results', 200)
            recent_days = self.sources_config.get("recent_days", 7)
            
            logger.info(f"从 arXiv 抓取最近 {recent_days} 天的文章")
            
            articles = []
            
            # 如果没有指定分类，使用通用查询
            if not categories:
                categories = ['cs.AI', 'cs.CL', 'cs.CV', 'cs.LG']
            
            # 构建查询
            category_query = ' OR '.join([f'cat:{cat}' for cat in categories])
            
            # 计算日期范围
            start_date = datetime.now() - timedelta(days=recent_days)
            
            # 搜索 arXiv
            search = arxiv.Search(
                query=category_query,
                max_results=max_results,
                sort_by=arxiv.SortCriterion.SubmittedDate,
                sort_order=arxiv.SortOrder.Descending
            )
            
            for result in search.results():
                # 只获取最近的文章
                if result.published.replace(tzinfo=None) < start_date:
                    continue
                
                article = {
                    'title': result.title,
                    'abstract': result.summary,
                    'authors': [author.name for author in result.authors],
                    'date': result.published.strftime('%Y-%m-%d'),
                    'journal': 'arXiv',
                    'doi': result.doi if hasattr(result, 'doi') else '',
                    'url': result.entry_id,
                    'source': 'arxiv',
                    'type': 'preprint',
                    'arxiv_id': result.entry_id.split('/')[-1],
                    'categories': [cat for cat in result.categories],
                }
                
                articles.append(article)
            
            logger.info(f"从 arXiv 获取到 {len(articles)} 篇文章")
            return articles
            
        except Exception as e:
            logger.error(f"arXiv 抓取失败: {e}")
            return []
    
    def _fetch_biorxiv(self) -> List[Dict[str, Any]]:
        """抓取 bioRxiv"""
        # TODO: 实现 bioRxiv API 调用
        logger.warning("_fetch_biorxiv 尚未实现")
        return []
    
    def _fetch_medrxiv(self) -> List[Dict[str, Any]]:
        """抓取 medRxiv"""
        # TODO: 实现 medRxiv API 调用
        logger.warning("_fetch_medrxiv 尚未实现")
        return []
    
    def _fetch_top_journals(self) -> List[Dict[str, Any]]:
        """抓取热门期刊"""
        # TODO: 从画像读取热门期刊，精准抓取
        logger.warning("_fetch_top_journals 尚未实现")
        return []
    
    def _deduplicate(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """去重"""
        logger.info(f"开始去重，原始文章数: {len(articles)}")
        
        seen_dois = set()
        seen_titles = set()
        unique_articles = []
        
        for article in articles:
            doi = article.get('doi', '').strip().lower()
            title = article.get('title', '').strip().lower()
            
            # 优先使用 DOI 去重
            if doi and doi in seen_dois:
                continue
            
            # 如果没有 DOI，使用标题去重
            if not doi and title in seen_titles:
                continue
            
            # 记录并添加
            if doi:
                seen_dois.add(doi)
            if title:
                seen_titles.add(title)
            
            unique_articles.append(article)
        
        logger.info(f"去重完成，剩余文章数: {len(unique_articles)}")
        return unique_articles
