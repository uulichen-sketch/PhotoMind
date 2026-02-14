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
    
    # ========== 人物管理方法 ==========
    
    def add_person(
        self, 
        person_id: str, 
        metadata: Dict[str, Any], 
        document: str,
        face_encoding: List[float]
    ):
        """
        添加人物到向量库
        
        Args:
            person_id: 人物唯一 ID
            metadata: 人物元数据
            document: 用于向量化的文档文本
            face_encoding: 人脸特征向量（128维）
        """
        if self._collection is None:
            logger.error("Collection not initialized")
            return False
        
        try:
            # 将 metadata 转为可存储的格式
            metadata_stored = {"type": "person"}  # 标记为人物类型
            for key, value in metadata.items():
                if value is not None:
                    if isinstance(value, list):
                        metadata_stored[key] = json.dumps(value, ensure_ascii=False)
                    else:
                        metadata_stored[key] = str(value)
            
            # 将人脸特征向量作为 embedding 直接存储
            self._collection.add(
                ids=[person_id],
                documents=[document],
                metadatas=[metadata_stored],
                embeddings=[face_encoding]  # 直接使用人脸特征向量
            )
            
            logger.info(f"Added person {person_id} to collection")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add person {person_id}: {e}")
            return False
    
    def get_person(self, person_id: str) -> Optional[Dict[str, Any]]:
        """获取人物信息"""
        return self.get_photo(person_id)  # 复用 get_photo 方法
    
    def list_persons(self) -> List[Dict[str, Any]]:
        """列出所有人物"""
        if self._collection is None:
            return []
        
        try:
            # 获取所有文档，然后过滤出人物
            results = self._collection.get()
            
            persons = []
            if results and results.get('ids'):
                for i, person_id in enumerate(results['ids']):
                    metadata = results['metadatas'][i] if results.get('metadatas') else {}
                    
                    # 只返回类型为 person 的
                    if metadata.get('type') == 'person':
                        # 还原 metadata
                        parsed_metadata = {}
                        for key, value in metadata.items():
                            try:
                                if key in ['tags', 'face_encoding']:
                                    parsed_metadata[key] = json.loads(value)
                                else:
                                    parsed_metadata[key] = value
                            except:
                                parsed_metadata[key] = value
                        
                        parsed_metadata['id'] = person_id
                        persons.append(parsed_metadata)
            
            return persons
            
        except Exception as e:
            logger.error(f"Failed to list persons: {e}")
            return []
    
    def get_all_face_encodings(self) -> List[Dict[str, Any]]:
        """
        获取所有人物的人脸特征向量
        
        Returns:
            人物列表，每项包含 person_id 和 encoding
        """
        if self._collection is None:
            return []
        
        try:
            # 获取所有包含 embeddings 的结果
            results = self._collection.get(include=["embeddings", "metadatas"])
            
            faces = []
            if results and results.get('ids'):
                for i, person_id in enumerate(results['ids']):
                    metadata = results['metadatas'][i] if results.get('metadatas') else {}
                    embedding = results['embeddings'][i] if results.get('embeddings') else None
                    
                    # 只返回类型为 person 且有 embedding 的
                    if metadata.get('type') == 'person' and embedding is not None:
                        faces.append({
                            "person_id": person_id,
                            "encoding": embedding,
                            "name": metadata.get('name', 'Unknown')
                        })
            
            return faces
            
        except Exception as e:
            logger.error(f"Failed to get face encodings: {e}")
            return []


# 全局服务实例
vector_service = VectorService()
