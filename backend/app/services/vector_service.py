"""向量数据库服务（ChromaDB）"""
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional, Any
import logging
import json
from app.config import settings

logger = logging.getLogger(__name__)


class VectorService:
    """向量数据库服务"""
    
    _instance = None
    _client = None
    _collection = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._client is None:
            self._init_client()
    
    def _init_client(self):
        """初始化 ChromaDB 客户端"""
        try:
            self._client = chromadb.PersistentClient(
                path=settings.chroma_dir,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # 创建或获取 collection
            self._collection = self._client.get_or_create_collection(
                name="photos",
                metadata={"description": "Photo metadata collection"}
            )
            
            logger.info(f"ChromaDB initialized with {self._collection.count()} photos")
            
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            self._client = None
            self._collection = None
    
    def add_photo(self, photo_id: str, metadata: Dict[str, Any], document: str):
        """
        添加照片到向量库
        
        Args:
            photo_id: 照片唯一 ID
            metadata: 照片元数据
            document: 用于向量化的文档文本（描述 + 标签）
        """
        if self._collection is None:
            logger.error("Collection not initialized")
            return False
        
        try:
            # 将 metadata 转为可存储的格式
            metadata_stored = {}
            for key, value in metadata.items():
                if value is not None:
                    if isinstance(value, list):
                        metadata_stored[key] = json.dumps(value, ensure_ascii=False)
                    else:
                        metadata_stored[key] = str(value)
            
            self._collection.add(
                ids=[photo_id],
                documents=[document],
                metadatas=[metadata_stored]
            )
            
            logger.info(f"Added photo {photo_id} to collection")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add photo {photo_id}: {e}")
            return False
    
    def search(self, query: str, n_results: int = 20) -> List[Dict[str, Any]]:
        """
        语义搜索照片
        
        Args:
            query: 搜索查询
            n_results: 返回结果数量
            
        Returns:
            匹配的照片列表
        """
        if self._collection is None:
            logger.error("Collection not initialized")
            return []
        
        try:
            results = self._collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            # 解析结果
            photos = []
            if results and results.get('ids') and results['ids'][0]:
                for i, photo_id in enumerate(results['ids'][0]):
                    metadata = results['metadatas'][0][i] if results.get('metadatas') else {}
                    distance = results['distances'][0][i] if results.get('distances') else 0
                    
                    # 还原 metadata
                    parsed_metadata = {}
                    for key, value in metadata.items():
                        try:
                            # 尝试解析 JSON
                            if key == 'tags':
                                parsed_metadata[key] = json.loads(value)
                            else:
                                parsed_metadata[key] = value
                        except:
                            parsed_metadata[key] = value
                    
                    parsed_metadata['id'] = photo_id
                    parsed_metadata['_score'] = 1 - distance  # 转为相似度
                    photos.append(parsed_metadata)
            
            logger.info(f"Found {len(photos)} photos for query: {query}")
            return photos
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def get_photo(self, photo_id: str) -> Optional[Dict[str, Any]]:
        """
        获取单张照片信息
        
        Args:
            photo_id: 照片 ID
            
        Returns:
            照片元数据
        """
        if self._collection is None:
            return None
        
        try:
            results = self._collection.get(ids=[photo_id])
            
            if results and results.get('metadatas'):
                metadata = results['metadatas'][0]
                
                # 还原 metadata
                parsed_metadata = {}
                for key, value in metadata.items():
                    try:
                        if key == 'tags':
                            parsed_metadata[key] = json.loads(value)
                        else:
                            parsed_metadata[key] = value
                    except:
                        parsed_metadata[key] = value
                
                parsed_metadata['id'] = photo_id
                return parsed_metadata
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get photo {photo_id}: {e}")
            return None
    
    def delete_photo(self, photo_id: str) -> bool:
        """删除照片"""
        if self._collection is None:
            return False
        
        try:
            self._collection.delete(ids=[photo_id])
            logger.info(f"Deleted photo {photo_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete photo {photo_id}: {e}")
            return False
    
    def count(self) -> int:
        """获取照片总数"""
        if self._collection is None:
            return 0
        return self._collection.count()
    
    def clear_all(self):
        """清空所有照片"""
        if self._client is None:
            return
        
        try:
            self._client.delete_collection("photos")
            self._collection = self._client.create_collection(
                name="photos",
                metadata={"description": "Photo metadata collection"}
            )
            logger.info("Cleared all photos")
        except Exception as e:
            logger.error(f"Failed to clear collection: {e}")


# 全局服务实例
vector_service = VectorService()
