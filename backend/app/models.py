"""数据模型"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class ImportStatus(str, Enum):
    """导入状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class PhotoMetadata(BaseModel):
    """照片元数据"""
    id: str = Field(..., description="照片唯一 ID")
    file_path: str = Field(..., description="文件路径")
    filename: str = Field(..., description="文件名")
    
    # EXIF 信息
    datetime: Optional[str] = Field(None, description="拍摄时间")
    location: Optional[str] = Field(None, description="拍摄地点")
    camera: Optional[str] = Field(None, description="相机型号")
    lens: Optional[str] = Field(None, description="镜头信息")
    iso: Optional[int] = Field(None, description="ISO")
    aperture: Optional[str] = Field(None, description="光圈")
    shutter: Optional[str] = Field(None, description="快门速度")
    focal_length: Optional[str] = Field(None, description="焦距")
    
    # AI 生成信息
    description: Optional[str] = Field(None, description="AI 生成的照片描述")
    tags: List[str] = Field(default_factory=list, description="分类标签")
    
    # 文件信息
    file_size: Optional[int] = Field(None, description="文件大小（字节）")
    width: Optional[int] = Field(None, description="图片宽度")
    height: Optional[int] = Field(None, description="图片高度")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "photo_001",
                "file_path": "/photos/2025/07/beach_001.jpg",
                "filename": "beach_001.jpg",
                "datetime": "2025-07-15T15:20:00",
                "location": "山东省青岛市金沙滩",
                "camera": "Canon EOS R5",
                "lens": "RF 24-70mm f/2.8L IS USM",
                "iso": 400,
                "aperture": "f/8",
                "shutter": "1/500s",
                "focal_length": "35mm",
                "description": "夕阳下的金沙滩，海浪轻柔地拍打着岸边",
                "tags": ["风景", "海边", "日落", "夏天"],
                "file_size": 5242880,
                "width": 8192,
                "height": 5464
            }
        }


class SearchRequest(BaseModel):
    """搜索请求"""
    query: str = Field(..., description="搜索关键词或语音转文字结果")


class VoiceSearchRequest(BaseModel):
    """语音搜索请求"""
    audio: str = Field(..., description="Base64 编码的音频数据")


class SearchResult(BaseModel):
    """搜索结果"""
    text: Optional[str] = Field(None, description="语音识别后的文字")
    photos: List[PhotoMetadata] = Field(default_factory=list, description="匹配的照片列表")
    message: Optional[str] = Field(None, description="额外消息或错误提示")


class ImportStartRequest(BaseModel):
    """开始导入请求"""
    folder_path: str = Field(..., description="要导入的文件夹路径")


class ImportStatusResponse(BaseModel):
    """导入状态响应"""
    task_id: str = Field(..., description="任务 ID")
    status: ImportStatus = Field(..., description="当前状态")
    total: int = Field(0, description="总照片数")
    processed: int = Field(0, description="已处理数")
    failed: int = Field(0, description="失败数")
    current_file: Optional[str] = Field(None, description="当前处理的文件")
    message: Optional[str] = Field(None, description="状态消息")


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str = "ok"
    version: str = "1.0.0"
    services: Dict[str, Any] = Field(default_factory=dict)
