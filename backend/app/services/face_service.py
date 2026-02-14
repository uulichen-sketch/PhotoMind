"""人脸识别服务（可选功能）

需要安装：pip install face-recognition

注意：
- 首次运行会自动下载 dlib 模型（约 100MB）
- 人脸识别计算量较大，建议异步处理
- 人脸数据存储在 ChromaDB 中，与照片元数据关联
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import numpy as np

logger = logging.getLogger(__name__)


class FaceService:
    """人脸识别服务"""
    
    _instance = None
    _face_recognition = None
    _initialized = False
    _error_message = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._init_service()
            self._initialized = True
    
    def _init_service(self):
        """初始化人脸识别服务"""
        try:
            import face_recognition
            self._face_recognition = face_recognition
            logger.info("Face recognition service initialized successfully")
            self._error_message = None
        except ImportError:
            self._error_message = (
                "face_recognition not installed. "
                "Install with: pip install face-recognition"
            )
            logger.warning(self._error_message)
            self._face_recognition = None
        except Exception as e:
            self._error_message = f"Failed to initialize face recognition: {e}"
            logger.error(self._error_message)
            self._face_recognition = None
    
    @property
    def is_available(self) -> bool:
        """检查人脸识别服务是否可用"""
        return self._face_recognition is not None
    
    @property
    def status(self) -> Dict[str, Any]:
        """获取服务状态"""
        return {
            "available": self.is_available,
            "error": self._error_message
        }
    
    def detect_faces(self, image_path: str) -> List[Dict[str, Any]]:
        """
        检测照片中的人脸
        
        Args:
            image_path: 照片路径
            
        Returns:
            人脸列表，每个元素包含：
            - encoding: 人脸特征向量
            - location: 人脸位置 (top, right, bottom, left)
        """
        if not self.is_available:
            logger.warning("Face recognition not available")
            return []
        
        try:
            # 加载图片
            image = self._face_recognition.load_image_file(image_path)
            
            # 检测人脸位置
            face_locations = self._face_recognition.face_locations(image)
            
            # 提取人脸特征
            face_encodings = self._face_recognition.face_encodings(image, face_locations)
            
            faces = []
            for i, (location, encoding) in enumerate(zip(face_locations, face_encodings)):
                faces.append({
                    "id": f"face_{i}",
                    "encoding": encoding.tolist(),  # numpy array 转为 list
                    "location": {
                        "top": location[0],
                        "right": location[1],
                        "bottom": location[2],
                        "left": location[3]
                    }
                })
            
            logger.info(f"Detected {len(faces)} faces in {image_path}")
            return faces
            
        except Exception as e:
            logger.error(f"Face detection failed for {image_path}: {e}")
            return []
    
    def compare_faces(
        self, 
        known_encoding: List[float], 
        unknown_encoding: List[float],
        tolerance: float = 0.6
    ) -> bool:
        """
        比较两个人脸是否匹配
        
        Args:
            known_encoding: 已知人脸特征
            unknown_encoding: 待识别人脸特征
            tolerance: 容差，越小越严格（默认 0.6）
            
        Returns:
            是否匹配
        """
        if not self.is_available:
            return False
        
        try:
            known = np.array(known_encoding)
            unknown = np.array(unknown_encoding)
            
            result = self._face_recognition.compare_faces(
                [known], unknown, tolerance=tolerance
            )
            return result[0]
            
        except Exception as e:
            logger.error(f"Face comparison failed: {e}")
            return False
    
    def face_distance(
        self, 
        known_encoding: List[float], 
        unknown_encoding: List[float]
    ) -> float:
        """
        计算两个人脸的相似度距离
        
        Args:
            known_encoding: 已知人脸特征
            unknown_encoding: 待识别人脸特征
            
        Returns:
            欧氏距离，越小越相似
        """
        if not self.is_available:
            return float('inf')
        
        try:
            known = np.array(known_encoding)
            unknown = np.array(unknown_encoding)
            
            distance = self._face_recognition.face_distance([known], unknown)
            return float(distance[0])
            
        except Exception as e:
            logger.error(f"Face distance calculation failed: {e}")
            return float('inf')
    
    def find_matching_person(
        self, 
        face_encoding: List[float], 
        known_faces: List[Dict[str, Any]],
        tolerance: float = 0.6
    ) -> Optional[str]:
        """
        在已知人脸库中查找匹配的人物
        
        Args:
            face_encoding: 待识别人脸特征
            known_faces: 已知人脸列表，每项包含 person_id 和 encoding
            tolerance: 匹配容差
            
        Returns:
            匹配的人物 ID，未找到返回 None
        """
        if not self.is_available or not known_faces:
            return None
        
        best_match = None
        best_distance = float('inf')
        
        for known in known_faces:
            distance = self.face_distance(known["encoding"], face_encoding)
            if distance < tolerance and distance < best_distance:
                best_distance = distance
                best_match = known.get("person_id")
        
        return best_match
    
    async def health_check(self) -> Dict[str, Any]:
        """服务健康检查"""
        if not self.is_available:
            return {
                "status": "unhealthy",
                "message": self._error_message or "Face recognition not initialized",
                "available": False
            }
        
        return {
            "status": "healthy",
            "message": "Face recognition service is ready",
            "available": True
        }


class PersonManager:
    """人物管理器 - 管理已识别的人物"""
    
    def __init__(self, vector_service):
        """
        Args:
            vector_service: 向量数据库服务实例
        """
        self.vector_service = vector_service
        self.face_service = FaceService()
    
    def add_person(self, person_id: str, name: str, face_encoding: List[float]) -> bool:
        """
        添加/更新人物
        
        Args:
            person_id: 人物唯一 ID
            name: 人物名称（如 "爸爸"、"小明"）
            face_encoding: 人脸特征向量
            
        Returns:
            是否成功
        """
        try:
            # 存储到向量库
            metadata = {
                "type": "person",
                "person_id": person_id,
                "name": name,
                "face_count": 1
            }
            
            # 使用人脸特征向量作为文档（方便向量检索）
            document = f"人物 {name}"
            
            self.vector_service.add_person(person_id, metadata, document, face_encoding)
            logger.info(f"Added person: {name} ({person_id})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add person: {e}")
            return False
    
    def get_person(self, person_id: str) -> Optional[Dict[str, Any]]:
        """获取人物信息"""
        return self.vector_service.get_person(person_id)
    
    def list_persons(self) -> List[Dict[str, Any]]:
        """列出所有人物"""
        return self.vector_service.list_persons()
    
    def recognize_person(self, face_encoding: List[float]) -> Optional[Dict[str, Any]]:
        """
        识别照片中的人物
        
        Args:
            face_encoding: 人脸特征向量
            
        Returns:
            匹配的人物信息，未找到返回 None
        """
        if not self.face_service.is_available:
            return None
        
        # 获取所有人脸特征
        known_faces = self.vector_service.get_all_face_encodings()
        
        # 查找匹配
        person_id = self.face_service.find_matching_person(face_encoding, known_faces)
        
        if person_id:
            return self.get_person(person_id)
        
        return None


# 全局服务实例
face_service = FaceService()


async def check_face_health() -> Dict[str, Any]:
    """检查人脸识别服务健康状态"""
    return await face_service.health_check()
