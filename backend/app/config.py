"""配置管理"""
from pydantic_settings import BaseSettings
from typing import Optional
from pathlib import Path

# 手动加载 .env 文件（支持从多个位置查找）
from dotenv import load_dotenv

# 尝试从多个位置加载 .env
env_paths = [
    Path(".env"),  # 当前目录
    Path(__file__).parent.parent.parent / ".env",  # 项目根目录
    Path("/app/.env"),  # Docker 容器根目录
]

for env_path in env_paths:
    if env_path.exists():
        load_dotenv(env_path, override=True)
        break


class Settings(BaseSettings):
    """应用配置"""
    
    # 服务配置
    app_name: str = "PhotoMind"
    app_version: str = "1.0.0"
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True
    
    # 数据目录（支持本地开发和 Docker 环境）
    data_dir: str = "./data"
    photos_dir: str = "./data/photos"
    chroma_dir: str = "./data/chroma"
    
    # 智谱 AI 配置
    zhipu_api_key: str = ""  # 从环境变量 ZHIPU_API_KEY 读取，或 .env 文件配置
    zhipu_base_url: str = "https://open.bigmodel.cn/api/paas/v4"
    zhipu_vision_model: str = "glm-4v-flash"  # 图像识别模型，免费版
    
    # ASR 模型配置
    asr_model_dir: str = "/app/models/asr"  # Docker 容器中挂载的绝对路径
    asr_model_url: str = "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-streaming-zipformer-zh-14M-2023-02-23.tar.bz2"
    
    # 高德地图 API 配置（用于 GPS 逆地理编码）
    amap_api_key: str = ""  # 需要用户自行申请，https://lbs.amap.com/
    
    # 向量模型配置
    embedding_model: str = "all-MiniLM-L6-v2"  # ChromaDB 默认模型
    
    class Config:
        # 支持从多个位置加载 .env 文件
        env_file = ".env"
        env_file_encoding = "utf-8"


# 全局配置实例
settings = Settings()
