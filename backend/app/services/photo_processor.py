"""照片处理器 - 异步 AI 分析和向量化"""
import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime
from app.services.exif_service import EXIFService
from app.services.vision_service import vision_service
from app.services.vector_service import vector_service
from app.services.geocoding_service import geocoding_service
import json

logger = logging.getLogger(__name__)


class PhotoProcessor:
    """异步照片处理器"""
    
    _instance = None
    _queue: asyncio.Queue = None
    _is_running = False
    _current_task = None
    _stats = {
        "pending": 0,
        "processing": 0,
        "completed": 0,
        "failed": 0,
        "current_photo": None
    }
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._queue = asyncio.Queue()
        return cls._instance
    
    async def start(self):
        """启动处理器"""
        if self._is_running:
            return
        
        self._is_running = True
        logger.info("PhotoProcessor started")
        
        # 启动后台处理循环
        asyncio.create_task(self._process_loop())
    
    async def stop(self):
        """停止处理器"""
        self._is_running = False
        if self._current_task:
            # 等待当前任务完成
            await self._current_task
        logger.info("PhotoProcessor stopped")
    
    async def add_photo(self, photo_id: str, file_path: str, metadata: dict):
        """添加照片到处理队列"""
        await self._queue.put({
            "photo_id": photo_id,
            "file_path": file_path,
            "metadata": metadata,
            "added_at": datetime.now().isoformat()
        })
        self._stats["pending"] += 1
        logger.info(f"Added photo {photo_id} to processing queue")
    
    async def _process_loop(self):
        """处理循环"""
        while self._is_running:
            try:
                # 获取队列中的照片
                task = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                
                self._stats["pending"] -= 1
                self._stats["processing"] = 1
                self._stats["current_photo"] = task["photo_id"]
                
                # 处理照片
                await self._process_photo(task)
                
                self._stats["processing"] = 0
                self._stats["current_photo"] = None
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Process loop error: {e}")
                self._stats["processing"] = 0
                self._stats["current_photo"] = None
    
    async def _process_photo(self, task: dict):
        """处理单张照片"""
        photo_id = task["photo_id"]
        file_path = task["file_path"]
        metadata = task["metadata"]
        
        try:
            logger.info(f"Processing photo {photo_id}: {metadata.get('filename')}")
            
            # 1. GPS 转地址（如果需要）
            if metadata.get("gps_latitude") and metadata.get("gps_longitude"):
                try:
                    address = await geocoding_service.reverse_geocode(
                        metadata["gps_latitude"],
                        metadata["gps_longitude"]
                    )
                    if address:
                        metadata["location"] = address
                except Exception as e:
                    logger.warning(f"Failed to get address for {photo_id}: {e}")
            
            # 2. AI 分析（最耗时）
            logger.info(f"AI analyzing {photo_id}...")
            vision_result = await vision_service.analyze_photo(file_path)
            
            # 解析评分
            scores_data = vision_result.get("scores", {})
            scores = {
                "composition": float(scores_data.get("composition", 0)),
                "color": float(scores_data.get("color", 0)),
                "lighting": float(scores_data.get("lighting", 0)),
                "sharpness": float(scores_data.get("sharpness", 0)),
                "overall": float(scores_data.get("overall", 0)),
                "reason": scores_data.get("reason", "")
            }
            
            # 更新元数据
            metadata.update({
                "description": vision_result.get("description", ""),
                "tags": vision_result.get("tags", []),
                "mood": vision_result.get("mood", ""),
                "subjects": vision_result.get("subjects", ""),
                "scores": scores,
                "ai_processed": True,
                "ai_processed_at": datetime.now().isoformat()
            })
            
            # 3. 构建文档文本用于向量化
            document = f"{metadata['description']} {' '.join(metadata['tags'])}"
            if metadata.get("location"):
                document += f" {metadata['location']}"
            
            # 4. 更新向量库（使用 upsert 更新已存在的记录）
            vector_service.update_photo(photo_id, metadata, document)
            
            self._stats["completed"] += 1
            logger.info(f"Photo {photo_id} processed successfully")
            
            # 稍微延迟，避免 API 限流
            await asyncio.sleep(0.5)
            
        except Exception as e:
            logger.error(f"Failed to process photo {photo_id}: {e}", exc_info=True)
            self._stats["failed"] += 1
            # 标记为失败，但保留照片
            metadata["ai_error"] = str(e)
            metadata["ai_processed"] = False
            
            # 将失败状态保存到向量库
            try:
                # 构建文档文本用于向量化
                document = f"{metadata.get('filename', '')} {metadata.get('datetime', '')}"
                if metadata.get("location"):
                    document += f" {metadata['location']}"
                
                vector_service.update_photo(photo_id, metadata, document)
                logger.info(f"Saved failed status for photo {photo_id}")
            except Exception as save_error:
                logger.error(f"Failed to save error status for {photo_id}: {save_error}")
    
    def get_stats(self) -> dict:
        """获取处理统计"""
        return {
            **self._stats,
            "queue_size": self._queue.qsize()
        }
    
    def get_queue_size(self) -> int:
        """获取队列大小"""
        return self._queue.qsize()


# 全局处理器实例
photo_processor = PhotoProcessor()
