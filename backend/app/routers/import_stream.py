"""实时导入流 API 路由 (SSE)"""
import os
import uuid
import asyncio
import json
from typing import Dict, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.responses import StreamingResponse
from app.models import ImportStatus, PhotoScores
from app.services.exif_service import EXIFService
from app.services.vision_service import vision_service
from app.services.vector_service import vector_service
from app.services.geocoding_service import geocoding_service
from app.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/import-stream", tags=["import-stream"])

# 存储活跃的任务连接
active_streams: Dict[str, asyncio.Queue] = {}


class ImportStreamManager:
    """导入流管理器"""
    
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.queue = asyncio.Queue()
        self.total = 0
        self.processed = 0
        self.failed = 0
        
    async def send_event(self, event_type: str, data: dict):
        """发送事件到队列"""
        event = {
            "type": event_type,
            "data": data
        }
        await self.queue.put(json.dumps(event, ensure_ascii=False))
        
    async def process_photo(self, filepath: str, photo_id: str):
        """处理单张照片并实时推送结果"""
        try:
            filename = os.path.basename(filepath)
            
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
                    "tags": metadata["tags"][:5],  # 只发送前5个标签
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
                "filename": filename,
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
        
        # 发送结束标记
        await self.queue.put(None)


async def event_stream(task_id: str):
    """生成 SSE 事件流"""
    queue = active_streams.get(task_id)
    if not queue:
        yield f"data: {json.dumps({'type': 'error', 'data': {'message': '任务不存在'}})}\n\n"
        return
    
    try:
        while True:
            # 等待数据，设置超时
            try:
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
        if task_id in active_streams:
            del active_streams[task_id]


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
    manager = ImportStreamManager(task_id)
    active_streams[task_id] = manager.queue
    
    # 保存上传的文件
    import tempfile
    import shutil
    
    temp_dir = tempfile.mkdtemp(prefix="photomind_stream_")
    saved_paths = []
    
    for file in image_files:
        file_path = os.path.join(temp_dir, file.filename)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        saved_paths.append(file_path)
    
    # 启动后台处理
    async def process():
        try:
            await manager.process_files(saved_paths)
        finally:
            # 清理临时文件
            try:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
            except:
                pass
    
    # 创建新任务运行处理
    asyncio.create_task(process())
    
    return {"task_id": task_id, "total": len(saved_paths)}


@router.get("/events/{task_id}")
async def stream_events(task_id: str):
    """
    SSE 事件流接口
    
    连接此接口接收实时导入进度
    """
    if task_id not in active_streams:
        raise HTTPException(status_code=404, detail="任务不存在或已结束")
    
    return StreamingResponse(
        event_stream(task_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 Nginx 缓冲
        }
    )


@router.get("/tasks/{task_id}/status")
async def get_stream_status(task_id: str):
    """获取任务状态"""
    if task_id not in active_streams:
        return {"status": "completed", "message": "任务已完成或不存在"}
    
    return {"status": "processing", "message": "任务进行中"}
