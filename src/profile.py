"""用户画像构建模块"""
import logging
import json
import pickle
import sqlite3
from pathlib import Path
from typing import List, Dict, Any
from collections import Counter
from pyzotero import zotero
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

logger = logging.getLogger("ZotWatcher.profile")


class ProfileBuilder:
    """用户画像构建器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.zotero_config = config.get("zotero", {})
        self.scoring_config = config.get("scoring", {})
        self.data_dir = Path("data")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化向量化模型
        model_name = self.scoring_config.get("semantic", {}).get("model_name", "sentence-transformers/all-MiniLM-L6-v2")
        logger.info(f"加载向量化模型: {model_name}")
        self.model = SentenceTransformer(model_name)
    
    def build_full_profile(self):
        """全量构建用户画像"""
        logger.info("开始全量构建用户画像")
        
        # 1. 从 Zotero 获取所有条目
        items = self._fetch_zotero_items()
        logger.info(f"从 Zotero 获取到 {len(items)} 个条目")
        
        # 2. 提取文本特征并向量化
        vectors = self._vectorize_items(items)
        logger.info(f"完成 {len(vectors)} 个条目的向量化")
        
        # 3. 构建 FAISS 索引
        self._build_faiss_index(vectors)
        logger.info("FAISS 索引构建完成")
        
        # 4. 统计高频作者、期刊
        profile_stats = self._extract_statistics(items)
        logger.info("画像统计信息提取完成")
        
        # 5. 保存画像
        self._save_profile(items, profile_stats)
        logger.info("用户画像保存完成")
    
    def update_profile(self):
        """增量更新用户画像"""
        logger.info("开始增量更新用户画像")
        
        # 获取上次更新时间
        last_modified = self._get_last_modified()
        
        # 获取增量条目
        new_items = self._fetch_zotero_items(since=last_modified)
        logger.info(f"获取到 {len(new_items)} 个新条目")
        
        if not new_items:
            logger.info("没有新条目，跳过更新")
            return
        
        # 更新向量和索引
        self._update_vectors_and_index(new_items)
        
        # 更新统计信息
        self._update_statistics(new_items)
        
        logger.info("增量更新完成")
    
    def _fetch_zotero_items(self, since=None) -> List[Dict[str, Any]]:
        """从 Zotero 获取条目"""
        try:
            # 获取配置
            api_config = self.zotero_config.get("api", {})
            api_key = api_config.get("api_key", "").strip() if api_config.get("api_key") else None
            user_id = api_config.get("user_id", "").strip() if api_config.get("user_id") else None
            library_type = self.zotero_config.get("library_type", "user")
            
            if not api_key or not user_id:
                logger.error("缺少 Zotero API 配置")
                return []
            
            # 创建 Zotero 客户端
            zot = zotero.Zotero(user_id, library_type, api_key)
            
            # 获取条目
            items = []
            limit = api_config.get("page_size", 100)
            max_items = self.zotero_config.get("max_items", 0)
            
            logger.info(f"开始从 Zotero 获取条目...")
            
            # 分页获取
            start = 0
            while True:
                batch = zot.items(limit=limit, start=start)
                if not batch:
                    break
                
                items.extend(batch)
                start += len(batch)
                logger.info(f"已获取 {len(items)} 个条目")
                
                # 检查是否达到最大数量
                if max_items > 0 and len(items) >= max_items:
                    items = items[:max_items]
                    break
                
                # 如果返回的数量小于 limit，说明已经是最后一页
                if len(batch) < limit:
                    break
            
            # 过滤和处理条目
            processed_items = []
            for item in items:
                # 只处理包含数据的条目
                if 'data' not in item:
                    continue
                
                data = item['data']
                item_type = data.get('itemType', '')
                
                # 过滤掉非文献类型
                if item_type in ['attachment', 'note']:
                    continue
                
                # 提取关键信息
                processed_item = {
                    'key': item.get('key'),
                    'version': item.get('version'),
                    'itemType': item_type,
                    'title': data.get('title', ''),
                    'abstractNote': data.get('abstractNote', ''),
                    'creators': data.get('creators', []),
                    'date': data.get('date', ''),
                    'publicationTitle': data.get('publicationTitle', ''),
                    'DOI': data.get('DOI', ''),
                    'url': data.get('url', ''),
                    'tags': [tag.get('tag', '') for tag in data.get('tags', [])],
                    'dateAdded': data.get('dateAdded', ''),
                    'dateModified': data.get('dateModified', '')
                }
                
                processed_items.append(processed_item)
            
            logger.info(f"成功处理 {len(processed_items)} 个有效条目")
            return processed_items
            
        except Exception as e:
            logger.error(f"从 Zotero 获取条目失败: {e}")
            return []
    
    def _vectorize_items(self, items: List[Dict[str, Any]]) -> np.ndarray:
        """向量化文章"""
        if not items:
            return np.array([])
        
        logger.info("开始向量化文章...")
        texts = []
        for item in items:
            # 组合标题、摘要和标签作为文本
            title = item.get('title', '')
            abstract = item.get('abstractNote', '')
            tags = ' '.join(item.get('tags', []))
            
            # 组合文本
            text = f"{title}. {abstract} {tags}".strip()
            texts.append(text)
        
        # 批量向量化
        logger.info(f"使用模型对 {len(texts)} 个条目进行向量化...")
        vectors = self.model.encode(texts, show_progress_bar=True, convert_to_numpy=True)
        
        logger.info(f"向量化完成，向量维度: {vectors.shape}")
        return vectors
    
    def _build_faiss_index(self, vectors: np.ndarray):
        """构建 FAISS 索引"""
        if len(vectors) == 0:
            logger.warning("没有向量数据，跳过 FAISS 索引构建")
            return
        
        logger.info("开始构建 FAISS 索引...")
        
        # 获取向量维度
        dimension = vectors.shape[1]
        
        # 创建 FAISS 索引（使用 L2 距离）
        index = faiss.IndexFlatL2(dimension)
        
        # 添加向量到索引
        index.add(vectors.astype('float32'))
        
        # 保存索引
        index_path = self.data_dir / "faiss.index"
        faiss.write_index(index, str(index_path))
        
        logger.info(f"FAISS 索引已保存: {index_path}，包含 {index.ntotal} 个向量")
    
    def _extract_statistics(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """提取统计信息"""
        logger.info("开始提取统计信息...")
        
        if not items:
            return {}
        
        # 统计作者
        all_authors = []
        for item in items:
            creators = item.get('creators', [])
            for creator in creators:
                if creator.get('creatorType') in ['author', 'editor']:
                    last_name = creator.get('lastName', '')
                    first_name = creator.get('firstName', '')
                    name = f"{first_name} {last_name}".strip()
                    if name:
                        all_authors.append(name)
        
        # 统计期刊
        all_journals = []
        for item in items:
            journal = item.get('publicationTitle', '')
            if journal:
                all_journals.append(journal)
        
        # 统计标签
        all_tags = []
        for item in items:
            tags = item.get('tags', [])
            all_tags.extend(tags)
        
        # 计算 Top 作者、期刊、标签
        top_authors = Counter(all_authors).most_common(50)
        top_journals = Counter(all_journals).most_common(50)
        top_tags = Counter(all_tags).most_common(50)
        
        stats = {
            'total_items': len(items),
            'top_authors': [{'name': name, 'count': count} for name, count in top_authors],
            'top_journals': [{'name': name, 'count': count} for name, count in top_journals],
            'top_tags': [{'name': name, 'count': count} for name, count in top_tags],
        }
        
        logger.info(f"统计完成: {stats['total_items']} 个条目")
        return stats
    
    def _save_profile(self, items: List[Dict[str, Any]], stats: Dict[str, Any]):
        """保存画像"""
        logger.info("开始保存画像...")
        
        # 保存统计信息到 JSON
        profile_json_path = self.data_dir / "profile.json"
        with open(profile_json_path, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        logger.info(f"画像统计信息已保存到: {profile_json_path}")
        
        # 保存条目到 SQLite
        db_path = self.data_dir / "profile.sqlite"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 创建表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS items (
                key TEXT PRIMARY KEY,
                title TEXT,
                abstract TEXT,
                creators TEXT,
                date TEXT,
                publication TEXT,
                doi TEXT,
                url TEXT,
                tags TEXT,
                item_type TEXT,
                date_added TEXT,
                date_modified TEXT
            )
        ''')
        
        # 插入数据
        for item in items:
            creators_str = json.dumps(item.get('creators', []))
            tags_str = json.dumps(item.get('tags', []))
            
            cursor.execute('''
                INSERT OR REPLACE INTO items VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                item.get('key'),
                item.get('title'),
                item.get('abstractNote'),
                creators_str,
                item.get('date'),
                item.get('publicationTitle'),
                item.get('DOI'),
                item.get('url'),
                tags_str,
                item.get('itemType'),
                item.get('dateAdded'),
                item.get('dateModified')
            ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"画像数据已保存到: {db_path}")
    
    def _get_last_modified(self):
        """获取上次更新时间"""
        # TODO: 从数据库读取
        return None
    
    def _update_vectors_and_index(self, new_items: List[Dict[str, Any]]):
        """更新向量和索引"""
        # TODO: 增量更新
        logger.warning("_update_vectors_and_index 尚未实现")
    
    def _update_statistics(self, new_items: List[Dict[str, Any]]):
        """更新统计信息"""
        # TODO: 增量更新统计
        logger.warning("_update_statistics 尚未实现")
