"""照片详情 API 路由"""
from typing import List
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from app.models import PhotoMetadata
from app.services.vector_service import vector_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/photo", tags=["photo"])


@router.get("/", response_model=List[PhotoMetadata])
async def list_photos(
    limit: int = Query(1000, ge=1, le=5000, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量")
):
    """
    获取照片列表
    
    Args:
        limit: 返回数量限制
        offset: 偏移量
        
    Returns:
        照片元数据列表
    """
    photos = vector_service.list_photos(limit=limit, offset=offset)
    
    # 转换为 PhotoMetadata 模型
    result = []
    for photo in photos:
        try:
            # 解析 scores
            scores = photo.get('scores')
            if isinstance(scores, str):
                import json
                try:
                    scores = json.loads(scores)
                except:
                    scores = None
            
            photo_data = PhotoMetadata(
                id=photo.get('id', ''),
                file_path=photo.get('file_path', ''),
                filename=photo.get('filename', ''),
                datetime=photo.get('datetime'),
                location=photo.get('location'),
                camera=photo.get('camera'),
                lens=photo.get('lens'),
                iso=int(photo.get('iso')) if photo.get('iso') else None,
                aperture=photo.get('aperture'),
                shutter=photo.get('shutter'),
                focal_length=photo.get('focal_length'),
                description=photo.get('description'),
                tags=photo.get('tags', []),
                scores=scores,
                file_size=int(photo.get('file_size')) if photo.get('file_size') else None,
                width=int(photo.get('width')) if photo.get('width') else None,
                height=int(photo.get('height')) if photo.get('height') else None,
            )
            result.append(photo_data)
        except Exception as e:
            logger.error(f"Failed to parse photo metadata: {e}")
            continue
    
    return result


@router.get("/{photo_id}", response_model=PhotoMetadata)
async def get_photo(photo_id: str):
    """
    获取照片详情
    
    Args:
        photo_id: 照片 ID
        
    Returns:
        照片完整元数据
    """
    photo = vector_service.get_photo(photo_id)
    
    if not photo:
        raise HTTPException(status_code=404, detail="照片不存在")
    
    # 解析 scores
    scores = photo.get('scores')
    if isinstance(scores, str):
        try:
            import json
            scores = json.loads(scores)
        except:
            scores = None
    
    return PhotoMetadata(
        id=photo.get('id', ''),
        file_path=photo.get('file_path', ''),
        filename=photo.get('filename', ''),
        datetime=photo.get('datetime'),
        location=photo.get('location'),
        camera=photo.get('camera'),
        lens=photo.get('lens'),
        iso=int(photo.get('iso')) if photo.get('iso') else None,
        aperture=photo.get('aperture'),
        shutter=photo.get('shutter'),
        focal_length=photo.get('focal_length'),
        description=photo.get('description'),
        tags=photo.get('tags', []),
        scores=scores,
        file_size=int(photo.get('file_size')) if photo.get('file_size') else None,
        width=int(photo.get('width')) if photo.get('width') else None,
        height=int(photo.get('height')) if photo.get('height') else None,
    )


@router.get("/{photo_id}/thumbnail")
async def get_thumbnail(photo_id: str, size: int = 300):
    """
    获取照片缩略图
    
    Args:
        photo_id: 照片 ID
        size: 缩略图大小
        
    Returns:
        图片文件
    """
    photo = vector_service.get_photo(photo_id)
    
    if not photo:
        raise HTTPException(status_code=404, detail="照片不存在")
    
    file_path = photo.get('file_path')
    if not file_path:
        raise HTTPException(status_code=400, detail="照片路径无效")
    
    # 直接返回原图（生产环境应该生成缩略图）
    return FileResponse(
        file_path,
        media_type="image/jpeg",
        filename=photo.get('filename', 'photo.jpg')
    )


@router.get("/{photo_id}/original")
async def get_original_photo(photo_id: str):
    """
    获取原始照片
    
    Args:
        photo_id: 照片 ID
        
    Returns:
        原始图片文件
    """
    photo = vector_service.get_photo(photo_id)
    
    if not photo:
        raise HTTPException(status_code=404, detail="照片不存在")
    
    file_path = photo.get('file_path')
    if not file_path:
        raise HTTPException(status_code=400, detail="照片路径无效")
    
    return FileResponse(
        file_path,
        media_type="image/jpeg",
        filename=photo.get('filename', 'photo.jpg')
    )


@router.delete("/{photo_id}")
async def delete_photo(photo_id: str):
    """
    删除照片（从数据库中删除，不删除原文件）
    
    Args:
        photo_id: 照片 ID
        
    Returns:
        删除结果
    """
    success = vector_service.delete_photo(photo_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="照片不存在或删除失败")
    
    return {"status": "deleted", "photo_id": photo_id}
