"""实时导入流 API 路由 (SSE)"""
import os
import uuid
import asyncio
import json
import shutil
from datetime import datetime
from typing import Dict, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.responses import StreamingResponse
from app.models import ImportStatus, PhotoScores
from app.services.exif_service import EXIFService
from app.services.vision_service import vision_service
from app.services.vector_service import vector_service
from app.services.geocoding_service import geocoding_service
from app.services.task_service import task_service
from app.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/import-stream", tags=["import-stream"])

# 存储活跃的任务连接
active_queues: Dict[str, asyncio.Queue] = {}


class ImportStreamManager:
    """导入流管理器"""
    
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.queue = asyncio.Queue()
        self.total = 0
        self.processed = 0
        self.failed = 0
        
    async def send_event(self, event_type: str, data: dict):
        """发送事件到队列并保存到任务"""
        event = {
            "type": event_type,
            "data": data
        }
        event_json = json.dumps(event, ensure_ascii=False)
        
        # 发送到队列（实时推送）
        await self.queue.put(event_json)
        
        # 保存到任务（持久化）
        task_service.update_task(
            self.task_id,
            {
                "processed": self.processed,
                "failed": self.failed,
                "current_file": data.get("filename")
            },
            add_event=event
        )
        
    async def process_photo(self, filepath: str, photo_id: str):
        """处理单张照片并实时推送结果"""
        try:
            filename = os.path.basename(filepath)
            
            # 更新任务状态
            task_service.update_task(
                self.task_id,
                {"status": "processing", "current_file": filename}
            )
            
            # 1. 开始处理 - 发送照片信息
            await self.send_event("photo_start", {
                "photo_id": photo_id,
                "filename": filename,
                "filepath": filepath,
                "progress": {
                    "current": self.processed + 1,
                    "total": self.total,
                    "percentage": round(((self.processed + 1) / self.total) * 100, 1)
                }
            })
            
            # 2. 提取 EXIF
            exif_data = EXIFService.extract(filepath)
            await self.send_event("exif_extracted", {
                "photo_id": photo_id,
                "filename": filename,
                "exif": {
                    "datetime": exif_data.get("datetime"),
                    "camera": exif_data.get("camera"),
                    "lens": exif_data.get("lens"),
                    "iso": exif_data.get("iso"),
                    "aperture": exif_data.get("aperture"),
                    "shutter": exif_data.get("shutter"),
                    "focal_length": exif_data.get("focal_length"),
                    "gps_latitude": exif_data.get("gps_latitude"),
                    "gps_longitude": exif_data.get("gps_longitude"),
                }
            })
            
            # 3. GPS 转地址
            location = None
            if exif_data.get("gps_latitude") and exif_data.get("gps_longitude"):
                address = await geocoding_service.reverse_geocode(
                    exif_data["gps_latitude"],
                    exif_data["gps_longitude"]
                )
                if address:
                    location = address
                    exif_data["location"] = address
                    await self.send_event("location_found", {
                        "photo_id": photo_id,
                        "filename": filename,
                        "location": location
                    })
            
            # 4. 调用 GLM-4V 识别
            await self.send_event("ai_analyzing", {
                "photo_id": photo_id,
                "filename": filename,
                "status": "正在分析照片内容..."
            })
            
            vision_result = await vision_service.analyze_photo(filepath)
            
            # 解析评分
            scores_data = vision_result.get("scores", {})
            scores = PhotoScores(
                composition=float(scores_data.get("composition", 0)),
                color=float(scores_data.get("color", 0)),
                lighting=float(scores_data.get("lighting", 0)),
                sharpness=float(scores_data.get("sharpness", 0)),
                overall=float(scores_data.get("overall", 0)),
                reason=scores_data.get("reason", "")
            )
            
            await self.send_event("ai_complete", {
                "photo_id": photo_id,
                "filename": filename,
                "description": vision_result.get("description", ""),
                "tags": vision_result.get("tags", []),
                "mood": vision_result.get("mood", ""),
                "subjects": vision_result.get("subjects", ""),
                "scores": scores.model_dump()
            })
            
            # 5. 组装元数据
            metadata = {
                "file_path": filepath,
                "filename": filename,
                **exif_data,
                "description": vision_result.get("description", ""),
                "tags": vision_result.get("tags", []),
                "scores": scores.model_dump()
            }
            
            # 6. 构建文档文本用于向量化
            document = f"{metadata['description']} {' '.join(metadata['tags'])}"
            if metadata.get("location"):
                document += f" {metadata['location']}"
            
            # 7. 存入向量库
            vector_service.add_photo(photo_id, metadata, document)
            
            await self.send_event("photo_complete", {
                "photo_id": photo_id,
                "filename": filename,
                "success": True,
                "metadata": {
                    "description": metadata["description"],
                    "tags": metadata["tags"][:5],
                    "location": metadata.get("location"),
                    "scores": scores.model_dump()
                }
            })
            
            self.processed += 1
            
            # 稍微延迟，让前端有时间展示
            await asyncio.sleep(0.5)
            
        except Exception as e:
            logger.error(f"Failed to process {filepath}: {e}")
            self.failed += 1
            await self.send_event("photo_error", {
                "photo_id": photo_id,
                "filename": os.path.basename(filepath),
                "error": str(e)
            })
    
    async def process_files(self, file_paths: list):
        """处理所有文件"""
        self.total = len(file_paths)
        
        await self.send_event("import_start", {
            "total": self.total,
            "message": f"开始导入 {self.total} 张照片"
        })
        
        for i, filepath in enumerate(file_paths):
            photo_id = f"photo_{uuid.uuid4().hex[:12]}"
            await self.process_photo(filepath, photo_id)
        
        await self.send_event("import_complete", {
            "total": self.total,
            "processed": self.processed,
            "failed": self.failed,
            "message": f"导入完成！成功 {self.processed} 张，失败 {self.failed} 张"
        })
        
        # 完成任务
        success = self.failed == 0
        task_service.complete_task(self.task_id, success=success)
        
        # 发送结束标记
        await self.queue.put(None)


async def event_stream(task_id: str, last_event_index: int = 0):
    """生成 SSE 事件流 - 支持从历史位置恢复"""
    
    # 获取任务
    task = task_service.get_task(task_id)
    if not task:
        yield f"data: {json.dumps({'type': 'error', 'data': {'message': '任务不存在'}})}\n\n"
        return
    
    # 获取或创建队列
    queue = active_queues.get(task_id)
    if not queue:
        queue = asyncio.Queue()
        active_queues[task_id] = queue
    
    try:
        # 如果有历史事件，先发送
        if last_event_index > 0 and task.get("events"):
            events = task["events"][last_event_index:]
            for event in events:
                yield f"data: {json.dumps(event)}\n\n"
        
        # 如果任务已完成，直接发送完成事件
        if task.get("status") in ["completed", "failed"]:
            yield f"data: {json.dumps({'type': 'import_complete', 'data': {'total': task.get('total'), 'processed': task.get('processed'), 'failed': task.get('failed')}})}\n\n"
            yield f"data: {json.dumps({'type': 'complete', 'data': {}})}\n\n"
            return
        
        # 实时等待新事件
        while True:
            try:
                # 设置超时，避免无限等待
                data = await asyncio.wait_for(queue.get(), timeout=300.0)
            except asyncio.TimeoutError:
                yield f"data: {json.dumps({'type': 'error', 'data': {'message': '导入超时'}})}\n\n"
                break
            
            # None 表示结束
            if data is None:
                yield f"data: {json.dumps({'type': 'complete', 'data': {}})}\n\n"
                break
            
            yield f"data: {data}\n\n"
            
    finally:
        # 清理
        if task_id in active_queues:
            del active_queues[task_id]


@router.post("/upload")
async def start_stream_import(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...)
):
    """
    开始流式导入照片
    
    返回 task_id，用于连接 SSE 流
    """
    # 过滤图片文件
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff'}
    image_files = [f for f in files if os.path.splitext(f.filename.lower())[1] in image_extensions]
    
    if not image_files:
        raise HTTPException(status_code=400, detail="未找到图片文件")
    
    # 创建任务
    task_id = f"stream_{uuid.uuid4().hex[:8]}"
    
    # 记录文件列表
    file_list = [f.filename for f in image_files]
    task_service.create_task(task_id, "stream", len(image_files), file_list)
    
    # 确保照片存储目录存在
    photos_storage_dir = settings.photos_dir
    os.makedirs(photos_storage_dir, exist_ok=True)
    
    # 创建按日期的子目录
    today = datetime.now().strftime("%Y%m%d")
    storage_dir = os.path.join(photos_storage_dir, today)
    os.makedirs(storage_dir, exist_ok=True)
    
    saved_paths = []
    
    for file in image_files:
        # 生成唯一文件名，避免冲突
        ext = os.path.splitext(file.filename)[1].lower()
        unique_name = f"{uuid.uuid4().hex[:16]}{ext}"
        file_path = os.path.join(storage_dir, unique_name)
        
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        saved_paths.append(file_path)
        logger.info(f"Saved photo to {file_path}")
    
    # 创建管理器并启动处理
    manager = ImportStreamManager(task_id)
    active_queues[task_id] = manager.queue
    
    # 启动后台处理
    asyncio.create_task(manager.process_files(saved_paths))
    
    return {"task_id": task_id, "total": len(saved_paths)}


@router.get("/events/{task_id}")
async def stream_events(task_id: str, last_index: int = 0):
    """
    SSE 事件流接口 - 支持断点续传
    
    参数:
        last_index: 上次接收到的事件索引，用于恢复连接
        
    连接此接口接收实时导入进度
    """
    # 检查任务是否存在
    task = task_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    return StreamingResponse(
        event_stream(task_id, last_index),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.get("/tasks/{task_id}")
async def get_task(task_id: str):
    """获取任务详情"""
    task = task_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 简化返回
    return {
        "task_id": task["task_id"],
        "type": task["type"],
        "status": task["status"],
        "total": task["total"],
        "processed": task["processed"],
        "failed": task["failed"],
        "created_at": task["created_at"],
        "updated_at": task["updated_at"],
        "completed_at": task.get("completed_at"),
        "current_file": task.get("current_file"),
        "error": task.get("error"),
        "event_count": len(task.get("events", []))
    }


@router.get("/tasks")
async def list_tasks(limit: int = 20):
    """列出最近的导入任务"""
    return task_service.list_tasks(limit)
