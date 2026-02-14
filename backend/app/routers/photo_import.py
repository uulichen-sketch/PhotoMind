"""照片导入 API 路由"""
import os
import uuid
import asyncio
from typing import Dict
from fastapi import APIRouter, HTTPException, BackgroundTasks
from app.models import ImportStartRequest, ImportStatusResponse, ImportStatus
from app.services.exif_service import EXIFService
from app.services.vision_service import vision_service
from app.services.vector_service import vector_service
from app.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/import", tags=["import"])

# 存储导入任务状态
import_tasks: Dict[str, dict] = {}


async def process_import(task_id: str, folder_path: str):
    """
    处理照片导入任务
    
    Args:
        task_id: 任务 ID
        folder_path: 文件夹路径
    """
    task = import_tasks[task_id]
    task["status"] = ImportStatus.PROCESSING
    
    try:
        # 扫描文件夹
        photo_files = []
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if EXIFService.is_supported(file):
                    photo_files.append(os.path.join(root, file))
        
        task["total"] = len(photo_files)
        logger.info(f"Found {len(photo_files)} photos to import")
        
        # 处理每张照片
        for i, filepath in enumerate(photo_files):
            task["current_file"] = os.path.basename(filepath)
            task["processed"] = i + 1
            
            try:
                # 1. 提取 EXIF
                exif_data = EXIFService.extract(filepath)
                
                # 2. 调用 GLM-4V 识别
                vision_result = await vision_service.analyze_photo(filepath)
                
                # 3. 组装元数据
                photo_id = f"photo_{uuid.uuid4().hex[:12]}"
                metadata = {
                    "file_path": filepath,
                    "filename": os.path.basename(filepath),
                    **exif_data,
                    "description": vision_result.get("description", ""),
                    "tags": vision_result.get("tags", [])
                }
                
                # 4. 构建文档文本用于向量化
                document = f"{metadata['description']} {' '.join(metadata['tags'])}"
                if metadata.get("location"):
                    document += f" {metadata['location']}"
                
                # 5. 存入向量库
                vector_service.add_photo(photo_id, metadata, document)
                
                logger.info(f"Imported {i+1}/{len(photo_files)}: {os.path.basename(filepath)}")
                
                # 稍微延迟，避免 API 限流
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Failed to import {filepath}: {e}")
                task["failed"] += 1
        
        task["status"] = ImportStatus.COMPLETED
        task["message"] = f"成功导入 {task['processed'] - task['failed']} 张照片"
        logger.info(f"Import task {task_id} completed")
        
    except Exception as e:
        logger.error(f"Import task {task_id} failed: {e}")
        task["status"] = ImportStatus.FAILED
        task["message"] = str(e)


@router.post("/start", response_model=ImportStatusResponse)
async def start_import(request: ImportStartRequest, background_tasks: BackgroundTasks):
    """
    开始导入照片
    
    Args:
        request: 包含文件夹路径的请求
        background_tasks: FastAPI 后台任务
        
    Returns:
        任务状态
    """
    # 检查文件夹是否存在
    if not os.path.isdir(request.folder_path):
        raise HTTPException(status_code=400, detail="文件夹不存在")
    
    # 创建任务
    task_id = f"import_{uuid.uuid4().hex[:8]}"
    import_tasks[task_id] = {
        "task_id": task_id,
        "status": ImportStatus.PENDING,
        "total": 0,
        "processed": 0,
        "failed": 0,
        "current_file": None,
        "message": "等待开始..."
    }
    
    # 启动后台任务
    background_tasks.add_task(process_import, task_id, request.folder_path)
    
    return ImportStatusResponse(**import_tasks[task_id])


@router.get("/status/{task_id}", response_model=ImportStatusResponse)
async def get_import_status(task_id: str):
    """
    获取导入任务状态
    
    Args:
        task_id: 任务 ID
        
    Returns:
        任务状态
    """
    if task_id not in import_tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    return ImportStatusResponse(**import_tasks[task_id])


@router.get("/tasks")
async def list_import_tasks():
    """列出所有导入任务"""
    return list(import_tasks.values())
