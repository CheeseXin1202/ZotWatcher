"""用户画像构建模块"""
import logging
import json
from pathlib import Path
from typing import List, Dict, Any
from pyzotero import zotero

logger = logging.getLogger("ZotWatcher.profile")


class ProfileBuilder:
    """用户画像构建器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.zotero_config = config.get("zotero", {})
        self.data_dir = Path("data")
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
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
            api_key = self.zotero_config.get("api_key")
            user_id = self.zotero_config.get("user_id")
            library_type = self.zotero_config.get("library_type", "user")
            
            if not api_key or not user_id:
                logger.error("缺少 Zotero API 配置")
                return []
            
            # 创建 Zotero 客户端
            zot = zotero.Zotero(user_id, library_type, api_key)
            
            # 获取条目
            items = []
            limit = self.zotero_config.get("items_per_page", 100)
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
    
    def _vectorize_items(self, items: List[Dict[str, Any]]) -> List:
        """向量化文章"""
        # TODO: 使用 sentence-transformers 向量化
        logger.warning("_vectorize_items 尚未实现")
        return []
    
    def _build_faiss_index(self, vectors: List):
        """构建 FAISS 索引"""
        # TODO: 构建 FAISS 索引并保存
        logger.warning("_build_faiss_index 尚未实现")
    
    def _extract_statistics(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """提取统计信息"""
        # TODO: 统计高频作者、期刊等
        logger.warning("_extract_statistics 尚未实现")
        return {}
    
    def _save_profile(self, items: List[Dict[str, Any]], stats: Dict[str, Any]):
        """保存画像"""
        # TODO: 保存到 SQLite 和 JSON
        logger.warning("_save_profile 尚未实现")
    
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
