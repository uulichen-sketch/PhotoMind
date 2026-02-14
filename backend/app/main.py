"""FastAPI 主入口"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.models import HealthResponse
from app.routers import search, photo, import_router
from app.services.vector_service import vector_service
from app.services.asr_service import asr_service, auto_download_asr_models
from app.services.geocoding_service import geocoding_service
from app.services.face_service import face_service
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


@app.get("/health/detailed")
async def health_detailed():
    """详细健康检查 - 包含所有服务状态"""
    asr_health = await asr_service.health_check()
    geo_health = await geocoding_service.health_check()
    face_health = await face_service.health_check()
    
    return {
        "status": "healthy",
        "version": settings.app_version,
        "services": {
            "chromadb": {
                "status": "healthy" if vector_service._client else "unhealthy",
                "photo_count": vector_service.count()
            },
            "asr": asr_health,
            "geocoding": geo_health,
            "face_recognition": face_health
        }
    }


@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Photo count: {vector_service.count()}")
    
    # 检查各服务状态
    asr_status = asr_service.status
    if asr_status['available']:
        logger.info("✅ ASR service is available")
    elif asr_status['downloading']:
        logger.info("⏳ ASR models are being downloaded...")
    else:
        logger.warning(f"⚠️ ASR service unavailable: {asr_status['error']}")
    
    if geocoding_service.is_enabled:
        logger.info("✅ Geocoding service is enabled")
    else:
        logger.warning("⚠️ Geocoding service disabled (no API key)")
    
    face_status = face_service.status
    if face_status['available']:
        logger.info("✅ Face recognition service is available")
    else:
        logger.warning(f"⚠️ Face recognition unavailable: {face_status['error']}")
    
    # 自动下载 ASR 模型（在后台线程中）
    auto_download_asr_models()


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
