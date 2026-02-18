"""照片管理 API 路由 - 新版异步处理"""
import os
import uuid
import shutil
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import FileResponse
from app.models import PhotoMetadata, PhotoScores
from app.services.vector_service import vector_service
from app.services.exif_service import EXIFService
from app.services.photo_processor import photo_processor
from app.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/photos", tags=["photos"])


@router.get("/", response_model=List[PhotoMetadata])
async def list_photos(
    status: Optional[str] = None,  # pending, processing, completed, all
    limit: int = 1000,
    offset: int = 0
):
    """
    获取照片列表
    
    Args:
        status: 筛选状态 (pending=待处理, processing=处理中, completed=已完成, all=全部)
        limit: 返回数量限制
        offset: 偏移量
    """
    photos = vector_service.list_photos(limit=limit, offset=offset)
    
    result = []
    for photo in photos:
        try:
            # 解析 scores
            scores = photo.get('scores')
            if isinstance(scores, str):
                try:
                    import json
                    scores = json.loads(scores)
                except:
                    scores = None
            
            # 将 dict 转换为 PhotoScores 对象
            if isinstance(scores, dict):
                try:
                    scores = PhotoScores(**scores)
                except Exception as e:
                    logger.warning(f"Failed to parse scores for {photo.get('id')}: {e}")
                    scores = None
            
            # 确定状态
            ai_processed = photo.get('ai_processed', False)
            ai_error = photo.get('ai_error')
            
            if ai_error:
                photo_status = "failed"
            elif ai_processed:
                photo_status = "completed"
            elif photo.get('ai_processing'):
                photo_status = "processing"
            else:
                photo_status = "pending"
            
            # 如果需要筛选
            if status and status != "all" and photo_status != status:
                continue
            
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
            # 添加状态字段（不在模型中，但前端需要）
            result.append({
                **photo_data.model_dump(),
                "status": photo_status,
                "ai_processed": ai_processed,
                "ai_error": ai_error
            })
        except Exception as e:
            logger.error(f"Failed to parse photo metadata: {e}")
            continue
    
    return result


@router.post("/upload")
async def upload_photos(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...)
):
    """
    快速上传照片（仅保存文件和 EXIF，AI 分析后台异步处理）
    
    返回上传结果，包含已保存的照片列表
    """
    # 过滤图片文件
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff'}
    image_files = [f for f in files if os.path.splitext(f.filename.lower())[1] in image_extensions]
    
    if not image_files:
        raise HTTPException(status_code=400, detail="未找到图片文件")
    
    # 确保存储目录存在
    photos_storage_dir = settings.photos_dir
    os.makedirs(photos_storage_dir, exist_ok=True)
    
    # 创建按日期的子目录
    today = datetime.now().strftime("%Y%m%d")
    storage_dir = os.path.join(photos_storage_dir, today)
    os.makedirs(storage_dir, exist_ok=True)
    
    uploaded_photos = []
    
    for file in image_files:
        try:
            # 生成唯一文件名
            ext = os.path.splitext(file.filename)[1].lower()
            unique_name = f"{uuid.uuid4().hex[:16]}{ext}"
            file_path = os.path.join(storage_dir, unique_name)
            
            # 保存文件
            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)
            
            # 提取 EXIF（快速）
            exif_data = EXIFService.extract(file_path)
            
            # 生成照片 ID
            photo_id = f"photo_{uuid.uuid4().hex[:12]}"
            
            # 准备元数据
            metadata = {
                "file_path": file_path,
                "filename": file.filename,
                **exif_data,
                "uploaded_at": datetime.now().isoformat(),
                "ai_processed": False
            }
            
            # 先存入向量库（标记为待处理）
            # 创建简单文档用于基本搜索
            document = f"{metadata['filename']} {metadata.get('datetime', '')}"
            vector_service.add_photo(photo_id, metadata, document)
            
            # 添加到 AI 处理队列（确保处理器已启动）
            if not photo_processor._is_running:
                await photo_processor.start()
            await photo_processor.add_photo(photo_id, file_path, metadata)
            
            uploaded_photos.append({
                "photo_id": photo_id,
                "filename": file.filename,
                "status": "pending"
            })
            
            logger.info(f"Uploaded and queued: {file.filename}")
            
        except Exception as e:
            logger.error(f"Failed to upload {file.filename}: {e}")
            uploaded_photos.append({
                "filename": file.filename,
                "status": "error",
                "error": str(e)
            })
    
    return {
        "total": len(image_files),
        "uploaded": len([p for p in uploaded_photos if p.get("status") == "pending"]),
        "photos": uploaded_photos
    }


@router.get("/processing-stats")
async def get_processing_stats():
    """
    获取 AI 处理统计信息（用于首页进度条）
    """
    stats = photo_processor.get_stats()
    
    # 获取待处理总数
    all_photos = vector_service.list_photos(limit=10000)
    pending_count = sum(1 for p in all_photos if not p.get('ai_processed') and not p.get('ai_error'))
    completed_count = sum(1 for p in all_photos if p.get('ai_processed'))
    failed_count = sum(1 for p in all_photos if p.get('ai_error'))
    
    return {
        "queue_size": stats["queue_size"],
        "processing": stats["processing"],
        "current_photo": stats["current_photo"],
        "pending_total": pending_count,
        "completed_total": completed_count,
        "failed_total": failed_count,
        "total": pending_count + completed_count + failed_count
    }


@router.get("/{photo_id}")
async def get_photo(photo_id: str):
    """获取照片详情"""
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
    
    # 将 dict 转换为 PhotoScores 对象
    if isinstance(scores, dict):
        try:
            scores = PhotoScores(**scores)
        except Exception as e:
            logger.warning(f"Failed to parse scores for {photo_id}: {e}")
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
async def get_thumbnail(photo_id: str):
    """获取照片缩略图（返回原图）"""
    photo = vector_service.get_photo(photo_id)
    
    if not photo:
        raise HTTPException(status_code=404, detail="照片不存在")
    
    file_path = photo.get('file_path')
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="照片文件不存在")
    
    return FileResponse(
        file_path,
        media_type="image/jpeg",
        filename=photo.get('filename', 'photo.jpg')
    )


@router.get("/{photo_id}/file")
async def get_photo_file(photo_id: str):
    """获取原始照片文件"""
    photo = vector_service.get_photo(photo_id)
    
    if not photo:
        raise HTTPException(status_code=404, detail="照片不存在")
    
    file_path = photo.get('file_path')
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="照片文件不存在")
    
    return FileResponse(
        file_path,
        media_type="image/jpeg",
        filename=photo.get('filename', 'photo.jpg')
    )


@router.delete("/{photo_id}")
async def delete_photo(photo_id: str):
    """删除照片"""
    photo = vector_service.get_photo(photo_id)
    
    if not photo:
        raise HTTPException(status_code=404, detail="照片不存在")
    
    # 删除文件
    file_path = photo.get('file_path')
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception as e:
            logger.warning(f"Failed to delete file {file_path}: {e}")
    
    # 删除数据库记录
    success = vector_service.delete_photo(photo_id)
    
    if not success:
        raise HTTPException(status_code=500, detail="删除失败")
    
    return {"status": "deleted", "photo_id": photo_id}
