"""搜索 API 路由"""
from fastapi import APIRouter, HTTPException
from app.models import SearchRequest, VoiceSearchRequest, SearchResult, PhotoMetadata
from app.services.asr_service import asr_service
from app.services.vector_service import vector_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("/health")
async def search_health():
    """搜索服务健康检查"""
    asr_status = await asr_service.health_check()
    return {
        "status": "healthy",
        "asr": asr_status
    }


@router.post("/text", response_model=SearchResult)
async def text_search(request: SearchRequest):
    """
    文字搜索照片
    
    Args:
        request: 包含查询文本的请求
        
    Returns:
        匹配的照片列表
    """
    try:
        photos = vector_service.search(request.query, n_results=20)
        
        # 转换为 PhotoMetadata 格式
        photo_list = []
        for p in photos:
            photo_list.append(PhotoMetadata(
                id=p.get('id', ''),
                file_path=p.get('file_path', ''),
                filename=p.get('filename', ''),
                datetime=p.get('datetime'),
                location=p.get('location'),
                camera=p.get('camera'),
                lens=p.get('lens'),
                iso=int(p.get('iso')) if p.get('iso') else None,
                aperture=p.get('aperture'),
                shutter=p.get('shutter'),
                focal_length=p.get('focal_length'),
                description=p.get('description'),
                tags=p.get('tags', []),
                file_size=int(p.get('file_size')) if p.get('file_size') else None,
                width=int(p.get('width')) if p.get('width') else None,
                height=int(p.get('height')) if p.get('height') else None,
            ))
        
        return SearchResult(text=request.query, photos=photo_list)
        
    except Exception as e:
        logger.error(f"Text search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/voice", response_model=SearchResult)
async def voice_search(request: VoiceSearchRequest):
    """
    语音搜索照片
    
    Args:
        request: 包含 Base64 编码音频的请求
        
    Returns:
        识别的文字和匹配的照片列表
    """
    # 检查 ASR 服务是否可用
    if not asr_service.is_available:
        logger.warning(f"Voice search requested but ASR not available: {asr_service.status}")
        raise HTTPException(
            status_code=503,
            detail=f"语音识别服务暂不可用。{asr_service.status.get('error', '请检查模型配置。')}"
        )
    
    try:
        # 语音转文字
        text = asr_service.transcribe(request.audio)
        
        if not text:
            return SearchResult(text="", photos=[], message="未能识别语音，请重试")
        
        logger.info(f"Voice recognized: {text}")
        
        # 搜索照片
        photos = vector_service.search(text, n_results=20)
        
        # 转换为 PhotoMetadata 格式
        photo_list = []
        for p in photos:
            photo_list.append(PhotoMetadata(
                id=p.get('id', ''),
                file_path=p.get('file_path', ''),
                filename=p.get('filename', ''),
                datetime=p.get('datetime'),
                location=p.get('location'),
                camera=p.get('camera'),
                lens=p.get('lens'),
                iso=int(p.get('iso')) if p.get('iso') else None,
                aperture=p.get('aperture'),
                shutter=p.get('shutter'),
                focal_length=p.get('focal_length'),
                description=p.get('description'),
                tags=p.get('tags', []),
                file_size=int(p.get('file_size')) if p.get('file_size') else None,
                width=int(p.get('width')) if p.get('width') else None,
                height=int(p.get('height')) if p.get('height') else None,
            ))
        
        return SearchResult(text=text, photos=photo_list)
        
    except Exception as e:
        logger.error(f"Voice search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
