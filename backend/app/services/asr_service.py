"""语音识别服务（sherpa-onnx）"""
import wave
import tempfile
import base64
import logging
from typing import Optional, Dict, Any
from pathlib import Path
import numpy as np
import os
import urllib.request
import tarfile
import threading

logger = logging.getLogger(__name__)


class ASRService:
    """语音识别服务"""
    
    _instance = None
    _recognizer = None
    _initialized = False
    _error_message = None
    _downloading = False
    _model_downloaded = False
    
    # 默认模型下载地址
    DEFAULT_MODEL_URL = "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-streaming-zipformer-zh-14M-2023-02-23.tar.bz2"
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._init_recognizer()
            self._initialized = True
    
    def _get_required_files(self):
        """获取必需的模型文件列表"""
        return [
            "encoder-epoch-99-avg-1.int8.onnx",
            "decoder-epoch-99-avg-1.int8.onnx",
            "joiner-epoch-99-avg-1.int8.onnx",
            "tokens.txt"
        ]
    
    def check_models_exist(self, model_dir: Path = None) -> bool:
        """
        检查模型文件是否存在
        
        Args:
            model_dir: 模型目录，默认使用配置中的路径
            
        Returns:
            是否所有必需文件都存在
        """
        if model_dir is None:
            from app.config import settings
            model_dir = Path(settings.asr_model_dir)
        
        required_files = self._get_required_files()
        return all((model_dir / f).exists() for f in required_files)
    
    def _init_recognizer(self):
        """初始化 sherpa-onnx 识别器"""
        try:
            import sherpa_onnx
            from app.config import settings
            
            model_dir = Path(settings.asr_model_dir)
            
            # 检查模型文件是否存在
            required_files = self._get_required_files()
            
            missing_files = []
            for f in required_files:
                if not (model_dir / f).exists():
                    missing_files.append(f)
            
            if missing_files:
                self._error_message = f"ASR model files not found: {missing_files}. Models will be auto-downloaded on startup."
                logger.warning(self._error_message)
                self._recognizer = None
                return
            
            self._recognizer = sherpa_onnx.OnlineRecognizer.from_transducer(
                encoder=str(model_dir / "encoder-epoch-99-avg-1.int8.onnx"),
                decoder=str(model_dir / "decoder-epoch-99-avg-1.int8.onnx"),
                joiner=str(model_dir / "joiner-epoch-99-avg-1.int8.onnx"),
                tokens=str(model_dir / "tokens.txt"),
                num_threads=2,
                sample_rate=16000,
                feature_dim=80,
                decoding_method='greedy_search'
            )
            logger.info("ASR recognizer initialized successfully")
            self._error_message = None
            
        except ImportError:
            self._error_message = "sherpa-onnx not installed. Install with: pip install sherpa-onnx"
            logger.warning(self._error_message)
            self._recognizer = None
        except Exception as e:
            self._error_message = f"Failed to initialize ASR recognizer: {e}"
            logger.error(self._error_message)
            self._recognizer = None
    
    @property
    def is_available(self) -> bool:
        """检查 ASR 服务是否可用"""
        return self._recognizer is not None
    
    @property
    def status(self) -> Dict[str, Any]:
        """获取服务状态"""
        return {
            "available": self.is_available,
            "error": self._error_message,
            "model_dir": self._get_model_dir(),
            "models_exist": self.check_models_exist(),
            "downloading": self._downloading,
            "model_downloaded": self._model_downloaded
        }
    
    def _get_model_dir(self) -> str:
        """获取模型目录路径"""
        from app.config import settings
        return settings.asr_model_dir
    
    def transcribe(self, audio_base64: str) -> str:
        """
        将 Base64 编码的音频转为文字
        
        Args:
            audio_base64: Base64 编码的音频数据
            
        Returns:
            识别出的文字，失败返回空字符串
        """
        if not self.is_available:
            logger.error(f"ASR not available: {self._error_message}")
            return ""
        
        try:
            # 解码音频
            audio_data = base64.b64decode(audio_base64)
            
            # 保存为临时文件并转换格式
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                tmp.write(audio_data)
                tmp_path = tmp.name
            
            # 使用 ffmpeg 转换为 16kHz 单声道 WAV
            import subprocess
            converted_path = tmp_path.replace('.wav', '_converted.wav')
            result = subprocess.run([
                'ffmpeg', '-y', '-i', tmp_path,
                '-ar', '16000', '-ac', '1',
                converted_path
            ], capture_output=True)
            
            if result.returncode != 0:
                logger.error(f"ffmpeg conversion failed: {result.stderr.decode()}")
                import os
                os.unlink(tmp_path)
                return ""
            
            # 读取 WAV 文件
            with wave.open(converted_path, 'rb') as wf:
                frames = wf.readframes(wf.getnframes())
                samples = np.frombuffer(frames, dtype=np.int16)
                samples = samples.astype(np.float32) / 32768.0
            
            # 识别
            stream = self._recognizer.create_stream()
            stream.accept_waveform(16000, samples)
            
            while self._recognizer.is_ready(stream):
                self._recognizer.decode_stream(stream)
            
            result = self._recognizer.get_result(stream)
            text = result if isinstance(result, str) else result.text
            
            # 清理临时文件
            import os
            os.unlink(tmp_path)
            os.unlink(converted_path)
            
            logger.info(f"ASR transcription: '{text}'")
            return text
            
        except Exception as e:
            logger.error(f"ASR transcription failed: {e}")
            return ""
    
    def transcribe_file(self, audio_path: str) -> str:
        """
        转录音频文件
        
        Args:
            audio_path: 音频文件路径
            
        Returns:
            识别出的文字
        """
        if not self.is_available:
            return ""
        
        try:
            # 转换为 16kHz WAV
            import subprocess
            import tempfile
            import os
            
            converted_path = tempfile.mktemp(suffix='.wav')
            result = subprocess.run([
                'ffmpeg', '-y', '-i', audio_path,
                '-ar', '16000', '-ac', '1',
                converted_path
            ], capture_output=True)
            
            if result.returncode != 0:
                logger.error(f"ffmpeg conversion failed: {result.stderr.decode()}")
                return ""
            
            # 读取并识别
            with wave.open(converted_path, 'rb') as wf:
                frames = wf.readframes(wf.getnframes())
                samples = np.frombuffer(frames, dtype=np.int16)
                samples = samples.astype(np.float32) / 32768.0
            
            stream = self._recognizer.create_stream()
            stream.accept_waveform(16000, samples)
            
            while self._recognizer.is_ready(stream):
                self._recognizer.decode_stream(stream)
            
            result = self._recognizer.get_result(stream)
            text = result if isinstance(result, str) else result.text
            
            # 清理
            os.unlink(converted_path)
            
            return text
            
        except Exception as e:
            logger.error(f"ASR file transcription failed: {e}")
            return ""
    
    async def health_check(self) -> Dict[str, Any]:
        """服务健康检查"""
        status = {
            "status": "unhealthy" if not self.is_available else "healthy",
            "available": self.is_available,
            "models_exist": self.check_models_exist(),
            "downloading": self._downloading,
            "model_dir": self._get_model_dir()
        }
        
        if not self.is_available:
            if self._downloading:
                status["message"] = "ASR models are being downloaded..."
            else:
                status["message"] = self._error_message or "ASR recognizer not initialized"
        else:
            status["message"] = "ASR service is ready"
        
        return status
    
    def download_models(
        self, 
        model_url: str = None, 
        model_dir: str = None,
        callback = None
    ) -> bool:
        """
        下载 ASR 模型文件（后台线程中运行）
        
        Args:
            model_url: 模型下载地址，默认使用 DEFAULT_MODEL_URL
            model_dir: 模型保存目录，默认使用配置中的路径
            callback: 下载完成后的回调函数，接收 (success: bool, message: str)
            
        Returns:
            是否开始下载（如果已经在下载中返回 False）
        """
        if self._downloading:
            logger.info("ASR models are already being downloaded")
            return False
        
        if self.check_models_exist():
            logger.info("ASR models already exist")
            self._model_downloaded = True
            if callback:
                callback(True, "Models already exist")
            return True
        
        # 在后台线程中下载，避免阻塞
        def _download():
            self._downloading = True
            try:
                from app.config import settings
                
                url = model_url or getattr(settings, 'asr_model_url', self.DEFAULT_MODEL_URL)
                save_dir = Path(model_dir) if model_dir else Path(settings.asr_model_dir)
                
                logger.info(f"Starting ASR model download from {url}")
                logger.info(f"Models will be saved to: {save_dir}")
                
                save_dir.mkdir(parents=True, exist_ok=True)
                
                # 下载压缩包
                tar_path = save_dir / "model.tar.bz2"
                
                # 使用 urllib 下载，带进度回调
                def _progress_hook(count, block_size, total_size):
                    percent = min(int(count * block_size * 100 / total_size), 100)
                    if percent % 10 == 0:  # 每 10% 记录一次
                        logger.info(f"Downloading ASR models: {percent}%")
                
                urllib.request.urlretrieve(url, tar_path, reporthook=_progress_hook)
                logger.info("Download completed, extracting...")
                
                # 解压
                with tarfile.open(tar_path, "r:bz2") as tar:
                    # 解压到临时目录，然后移动文件
                    temp_extract = save_dir / "temp_extract"
                    temp_extract.mkdir(exist_ok=True)
                    tar.extractall(temp_extract)
                    
                    # 查找解压后的模型文件
                    for root, dirs, files in os.walk(temp_extract):
                        for file in files:
                            if file in self._get_required_files():
                                src = Path(root) / file
                                dst = save_dir / file
                                import shutil
                                shutil.move(str(src), str(dst))
                                logger.info(f"Moved {file} to {save_dir}")
                    
                    # 清理临时目录
                    import shutil
                    shutil.rmtree(temp_extract)
                
                # 删除压缩包
                os.remove(tar_path)
                
                # 验证下载
                if self.check_models_exist(save_dir):
                    logger.info("ASR models downloaded and verified successfully!")
                    self._model_downloaded = True
                    self._error_message = None
                    
                    # 重新初始化识别器
                    self._init_recognizer()
                    
                    if callback:
                        callback(True, "Models downloaded successfully")
                    return True
                else:
                    error_msg = "Download completed but some files are missing"
                    logger.error(error_msg)
                    if callback:
                        callback(False, error_msg)
                    return False
                    
            except Exception as e:
                error_msg = f"Failed to download ASR models: {e}"
                logger.error(error_msg)
                if callback:
                    callback(False, error_msg)
                return False
            finally:
                self._downloading = False
        
        # 启动后台线程
        thread = threading.Thread(target=_download, daemon=True)
        thread.start()
        
        return True
    
    def reinit_after_download(self):
        """下载完成后重新初始化识别器"""
        if self.check_models_exist() and not self.is_available:
            logger.info("Reinitializing ASR recognizer after model download...")
            self._init_recognizer()


# 全局服务实例
asr_service = ASRService()


async def check_asr_health() -> Dict[str, Any]:
    """检查 ASR 服务健康状态"""
    return await asr_service.health_check()


def auto_download_asr_models():
    """
    自动下载 ASR 模型（在后台线程中）
    如果没有配置模型或模型不存在，会自动触发下载
    """
    from app.config import settings
    
    def on_download_complete(success: bool, message: str):
        if success:
            logger.info(f"ASR model download: {message}")
            # 下载完成后重新初始化
            asr_service.reinit_after_download()
        else:
            logger.error(f"ASR model download failed: {message}")
    
    # 检查是否需要下载
    if not asr_service.check_models_exist():
        logger.info("ASR models not found, starting auto-download...")
        asr_service.download_models(
            model_url=getattr(settings, 'asr_model_url', None),
            model_dir=settings.asr_model_dir,
            callback=on_download_complete
        )
    else:
        logger.info("ASR models already exist, skipping download")
