"""FastAPI 主入口"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.models import HealthResponse
from app.routers import search, photos, import_router, import_stream, faces
from app.services.photo_processor import photo_processor
from app.services.vector_service import vector_service
from app.services.asr_service import asr_service, auto_download_asr_models
from app.services.geocoding_service import geocoding_service
# face_recognition 是可选依赖
try:
    from app.services.face_service import face_service
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    face_service = None
    FACE_RECOGNITION_AVAILABLE = False
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
app.include_router(import_stream.router)
app.include_router(photos.router)
app.include_router(faces.router)


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
    
    services = {
        "chromadb": {
            "status": "healthy" if vector_service._client else "unhealthy",
            "photo_count": vector_service.count()
        },
        "asr": asr_health,
        "geocoding": geo_health,
    }
    
    # 可选的人脸识别服务
    if FACE_RECOGNITION_AVAILABLE and face_service:
        face_health = await face_service.health_check()
        services["face_recognition"] = face_health
    else:
        services["face_recognition"] = {"status": "disabled", "message": "face_recognition not installed"}
    
    return {
        "status": "healthy",
        "version": settings.app_version,
        "services": services
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
    
    # 可选的人脸识别服务
    if FACE_RECOGNITION_AVAILABLE and face_service:
        face_status = face_service.status
        if face_status['available']:
            logger.info("✅ Face recognition service is available")
        else:
            logger.warning(f"⚠️ Face recognition unavailable: {face_status['error']}")
    else:
        logger.info("ℹ️ Face recognition service disabled (optional)")
    
    # 自动下载 ASR 模型（在后台线程中）
    auto_download_asr_models()
    
    # 启动照片 AI 处理器
    await photo_processor.start()
    logger.info("✅ Photo processor started")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    logger.info("Shutting down...")
    await photo_processor.stop()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
