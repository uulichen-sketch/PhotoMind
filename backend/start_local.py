#!/usr/bin/env python3
"""
本地开发环境启动脚本
自动检查配置并启动后端服务
"""
import os
import sys
from pathlib import Path

# 设置项目根目录
ROOT_DIR = Path(__file__).parent
os.chdir(ROOT_DIR)

# 加载本地环境变量
from dotenv import load_dotenv

# 尝试加载 .env.local（本地配置优先）
env_local = ROOT_DIR / ".env.local"
env_root = ROOT_DIR.parent / ".env"

if env_local.exists():
    print(f"Loading local config: {env_local}")
    load_dotenv(env_local, override=True)

if env_root.exists():
    print(f"Loading root config: {env_root}")
    load_dotenv(env_root, override=True)

# 检查关键配置
from app.config import settings

print("\n" + "=" * 60)
print("PhotoMind Local Development Server")
print("=" * 60)

print(f"\nConfiguration:")
print(f"  Data Dir: {settings.data_dir}")
print(f"  Photos Dir: {settings.photos_dir}")
print(f"  Chroma Dir: {settings.chroma_dir}")
print(f"  API Key: {'Set' if settings.zhipu_api_key else 'Not Set'}")

# 创建必要目录
for dir_path in [settings.data_dir, settings.photos_dir, settings.chroma_dir]:
    Path(dir_path).mkdir(parents=True, exist_ok=True)
    print(f"  Created: {dir_path}")

print("\n" + "=" * 60)
print("Starting server at http://localhost:8000")
print("API Docs: http://localhost:8000/docs")
print("=" * 60)
print()

# 启动服务
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
