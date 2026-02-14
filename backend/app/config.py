"""配置管理"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """应用配置"""
    
    # 服务配置
    app_name: str = "PhotoMind"
    app_version: str = "1.0.0"
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True
    
    # 数据目录
    data_dir: str = "./data"
    photos_dir: str = "./data/photos"
    chroma_dir: str = "./data/chroma"
    
    # 智谱 AI 配置
    zhipu_api_key: str = "334a0d2da68f47bd93c43d0916508609.Lrk85xXB1i7Bb1W5"
    zhipu_base_url: str = "https://open.bigmodel.cn/api/paas/v4"
    zhipu_vision_model: str = "glm-4v-flash"  # 图像识别模型
    
    # ASR 模型配置
    asr_model_dir: str = "/home/wuying/.clawdbot/tools/sherpa-onnx-asr/model"
    
    # 向量模型配置
    embedding_model: str = "all-MiniLM-L6-v2"  # ChromaDB 默认模型
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# 全局配置实例
settings = Settings()
