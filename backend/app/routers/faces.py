"""人脸识别 API 路由"""
import os
import uuid
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from app.services.vector_service import vector_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/faces", tags=["faces"])

# 检查人脸识别服务是否可用
try:
    from app.services.face_service import face_service, PersonManager
    FACE_RECOGNITION_AVAILABLE = face_service.is_available
    person_manager = PersonManager(vector_service) if FACE_RECOGNITION_AVAILABLE else None
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False
    person_manager = None
    logger.warning("Face recognition service not available")


class PersonCreate(BaseModel):
    """创建人物请求"""
    name: str
    photo_id: Optional[str] = None  # 关联的照片ID


class PersonResponse(BaseModel):
    """人物响应"""
    id: str
    name: str
    face_count: int = 1
    photo_ids: List[str] = []


@router.get("/status")
async def get_face_status():
    """获取人脸识别服务状态"""
    return {
        "available": FACE_RECOGNITION_AVAILABLE,
        "message": "Face recognition service is ready" if FACE_RECOGNITION_AVAILABLE else 
                   "Face recognition not installed. Install with: pip install face-recognition"
    }


@router.get("/persons", response_model=List[PersonResponse])
async def list_persons():
    """获取所有人物列表"""
    if not FACE_RECOGNITION_AVAILABLE:
        raise HTTPException(status_code=503, detail="人脸识别服务不可用")
    
    persons = person_manager.list_persons()
    return [
        PersonResponse(
            id=p.get("id", ""),
            name=p.get("name", "未知"),
            face_count=p.get("face_count", 1),
            photo_ids=p.get("photo_ids", [])
        )
        for p in persons
    ]


@router.post("/persons", response_model=PersonResponse)
async def create_person(request: PersonCreate):
    """创建新人物（从已有照片中选择人脸）"""
    if not FACE_RECOGNITION_AVAILABLE:
        raise HTTPException(status_code=503, detail="人脸识别服务不可用")
    
    if request.photo_id:
        # 从照片中提取人脸
        photo = vector_service.get_photo(request.photo_id)
        if not photo:
            raise HTTPException(status_code=404, detail="照片不存在")
        
        file_path = photo.get("file_path")
        if not file_path or not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="照片文件不存在")
        
        # 检测人脸
        faces = face_service.detect_faces(file_path)
        if not faces:
            raise HTTPException(status_code=400, detail="照片中未检测到人脸")
        
        # 使用第一张人脸创建人物
        person_id = f"person_{uuid.uuid4().hex[:12]}"
        face_encoding = faces[0]["encoding"]
        
        success = person_manager.add_person(person_id, request.name, face_encoding)
        if not success:
            raise HTTPException(status_code=500, detail="创建人物失败")
        
        return PersonResponse(
            id=person_id,
            name=request.name,
            face_count=1,
            photo_ids=[request.photo_id]
        )
    else:
        raise HTTPException(status_code=400, detail="需要提供照片ID")


@router.post("/persons/{person_id}/add-face")
async def add_face_to_person(person_id: str, photo_id: str):
    """将照片中的人脸添加到已有人物"""
    if not FACE_RECOGNITION_AVAILABLE:
        raise HTTPException(status_code=503, detail="人脸识别服务不可用")
    
    # 获取照片
    photo = vector_service.get_photo(photo_id)
    if not photo:
        raise HTTPException(status_code=404, detail="照片不存在")
    
    file_path = photo.get("file_path")
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="照片文件不存在")
    
    # 检测人脸
    faces = face_service.detect_faces(file_path)
    if not faces:
        raise HTTPException(status_code=400, detail="照片中未检测到人脸")
    
    # TODO: 更新人物的人脸数据
    return {"message": "人脸已添加", "face_count": len(faces)}


@router.post("/detect/{photo_id}")
async def detect_faces_in_photo(photo_id: str):
    """检测照片中的人脸"""
    if not FACE_RECOGNITION_AVAILABLE:
        raise HTTPException(status_code=503, detail="人脸识别服务不可用")
    
    photo = vector_service.get_photo(photo_id)
    if not photo:
        raise HTTPException(status_code=404, detail="照片不存在")
    
    file_path = photo.get("file_path")
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="照片文件不存在")
    
    # 检测人脸
    faces = face_service.detect_faces(file_path)
    
    # 尝试识别每个人脸
    recognized = []
    for face in faces:
        person = person_manager.recognize_person(face["encoding"])
        recognized.append({
            "location": face["location"],
            "person_id": person.get("id") if person else None,
            "person_name": person.get("name") if person else "未知人物"
        })
    
    return {
        "photo_id": photo_id,
        "face_count": len(faces),
        "faces": recognized
    }


@router.post("/scan-all")
async def scan_all_photos():
    """扫描所有照片，检测人脸并尝试识别"""
    if not FACE_RECOGNITION_AVAILABLE:
        raise HTTPException(status_code=503, detail="人脸识别服务不可用")
    
    photos = vector_service.list_photos(limit=10000)
    results = []
    
    for photo in photos:
        file_path = photo.get("file_path")
        if not file_path or not os.path.exists(file_path):
            continue
        
        try:
            faces = face_service.detect_faces(file_path)
            if faces:
                # 尝试识别每个人脸
                recognized_faces = []
                for face in faces:
                    person = person_manager.recognize_person(face["encoding"])
                    recognized_faces.append({
                        "person_id": person.get("id") if person else None,
                        "person_name": person.get("name") if person else "未知"
                    })
                
                results.append({
                    "photo_id": photo.get("id"),
                    "filename": photo.get("filename"),
                    "face_count": len(faces),
                    "faces": recognized_faces
                })
        except Exception as e:
            logger.error(f"Failed to scan {file_path}: {e}")
    
    return {
        "total_photos": len(photos),
        "photos_with_faces": len(results),
        "results": results
    }


@router.delete("/persons/{person_id}")
async def delete_person(person_id: str):
    """删除人物"""
    if not FACE_RECOGNITION_AVAILABLE:
        raise HTTPException(status_code=503, detail="人脸识别服务不可用")
    
    success = vector_service.delete_photo(person_id)  # 人物也存储在同一个collection
    if not success:
        raise HTTPException(status_code=500, detail="删除人物失败")
    
    return {"message": "人物已删除"}
