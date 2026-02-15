"""任务管理服务 - 持久化导入任务状态"""
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class TaskService:
    """任务管理服务 - 保存和恢复任务状态"""
    
    _instance = None
    _tasks_dir = None
    _active_tasks: Dict[str, dict] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._tasks_dir is None:
            self._tasks_dir = os.path.join(settings.data_dir, "tasks")
            os.makedirs(self._tasks_dir, exist_ok=True)
    
    def _get_task_file(self, task_id: str) -> str:
        """获取任务文件路径"""
        return os.path.join(self._tasks_dir, f"{task_id}.json")
    
    def create_task(self, task_id: str, task_type: str, total: int, files: List[str]) -> dict:
        """创建新任务"""
        task = {
            "task_id": task_id,
            "type": task_type,  # 'stream' 或 'upload'
            "status": "pending",
            "total": total,
            "processed": 0,
            "failed": 0,
            "files": files,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "completed_at": None,
            "events": [],  # 存储事件历史
            "current_file": None,
            "error": None
        }
        
        # 保存到内存和文件
        self._active_tasks[task_id] = task
        self._save_task(task)
        
        logger.info(f"Created task {task_id} with {total} files")
        return task
    
    def _save_task(self, task: dict):
        """保存任务到文件"""
        try:
            task_file = self._get_task_file(task["task_id"])
            with open(task_file, "w", encoding="utf-8") as f:
                json.dump(task, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save task: {e}")
    
    def get_task(self, task_id: str) -> Optional[dict]:
        """获取任务状态"""
        # 先从内存获取
        if task_id in self._active_tasks:
            return self._active_tasks[task_id]
        
        # 从文件加载
        try:
            task_file = self._get_task_file(task_id)
            if os.path.exists(task_file):
                with open(task_file, "r", encoding="utf-8") as f:
                    task = json.load(f)
                    self._active_tasks[task_id] = task
                    return task
        except Exception as e:
            logger.error(f"Failed to load task {task_id}: {e}")
        
        return None
    
    def update_task(self, task_id: str, updates: dict, add_event: dict = None):
        """更新任务状态"""
        task = self.get_task(task_id)
        if not task:
            logger.warning(f"Task {task_id} not found")
            return
        
        # 更新字段
        task.update(updates)
        task["updated_at"] = datetime.now().isoformat()
        
        # 添加事件
        if add_event:
            event_with_time = {
                **add_event,
                "timestamp": datetime.now().isoformat()
            }
            task["events"].append(event_with_time)
            # 只保留最近 100 个事件
            if len(task["events"]) > 100:
                task["events"] = task["events"][-100:]
        
        # 保存
        self._save_task(task)
    
    def complete_task(self, task_id: str, success: bool = True, error: str = None):
        """完成任务"""
        updates = {
            "status": "completed" if success else "failed",
            "completed_at": datetime.now().isoformat()
        }
        if error:
            updates["error"] = error
        
        self.update_task(task_id, updates)
        
        # 从活跃任务中移除（但文件保留）
        if task_id in self._active_tasks:
            del self._active_tasks[task_id]
        
        logger.info(f"Task {task_id} completed with status: {updates['status']}")
    
    def list_tasks(self, limit: int = 20) -> List[dict]:
        """列出最近的任务"""
        tasks = []
        
        try:
            # 获取所有任务文件
            task_files = []
            for filename in os.listdir(self._tasks_dir):
                if filename.endswith(".json"):
                    filepath = os.path.join(self._tasks_dir, filename)
                    task_files.append((filepath, os.path.getmtime(filepath)))
            
            # 按修改时间排序
            task_files.sort(key=lambda x: x[1], reverse=True)
            
            # 加载最近的任务
            for filepath, _ in task_files[:limit]:
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        task = json.load(f)
                        # 简化返回，不包含完整事件列表
                        tasks.append({
                            "task_id": task["task_id"],
                            "type": task["type"],
                            "status": task["status"],
                            "total": task["total"],
                            "processed": task["processed"],
                            "failed": task["failed"],
                            "created_at": task["created_at"],
                            "completed_at": task.get("completed_at"),
                            "current_file": task.get("current_file"),
                            "error": task.get("error")
                        })
                except Exception as e:
                    logger.error(f"Failed to load task file {filepath}: {e}")
        
        except Exception as e:
            logger.error(f"Failed to list tasks: {e}")
        
        return tasks
    
    def get_active_task_ids(self) -> List[str]:
        """获取活跃的任务ID列表"""
        return list(self._active_tasks.keys())
    
    def get_task_events(self, task_id: str, after_index: int = 0) -> List[dict]:
        """获取任务事件（支持断点续传）"""
        task = self.get_task(task_id)
        if not task:
            return []
        
        events = task.get("events", [])
        return events[after_index:]
    
    def cleanup_old_tasks(self, days: int = 7):
        """清理旧任务文件"""
        try:
            cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)
            
            for filename in os.listdir(self._tasks_dir):
                if filename.endswith(".json"):
                    filepath = os.path.join(self._tasks_dir, filename)
                    if os.path.getmtime(filepath) < cutoff:
                        os.remove(filepath)
                        logger.info(f"Cleaned up old task file: {filename}")
        
        except Exception as e:
            logger.error(f"Failed to cleanup old tasks: {e}")


# 全局实例
task_service = TaskService()
