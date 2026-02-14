"""FastAPI 主入口"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.models import HealthResponse
from app.routers import search, photo, import_router
from app.services.vector_service import vector_service
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO if settings.debug else logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# 创建应用
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="智能照片管理系统 - 支持语音搜索和 AI 分类",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(search.router)
app.include_router(import_router)
app.include_router(photo.router)


@app.get("/", response_model=HealthResponse)
async def root():
    """健康检查"""
    return HealthResponse(
        status="ok",
        version=settings.app_version,
        services={
            "chromadb": vector_service._client is not None,
            "collection": vector_service._collection is not None,
            "photo_count": vector_service.count()
        }
    )


@app.get("/health", response_model=HealthResponse)
async def health():
    """健康检查端点"""
    return await root()


@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Photo count: {vector_service.count()}")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    logger.info("Shutting down...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
