"""语音识别服务（sherpa-onnx）"""
import wave
import tempfile
import base64
import logging
from typing import Optional
import numpy as np

logger = logging.getLogger(__name__)


class ASRService:
    """语音识别服务"""
    
    _instance = None
    _recognizer = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._recognizer is None:
            self._init_recognizer()
    
    def _init_recognizer(self):
        """初始化 sherpa-onnx 识别器"""
        try:
            import sherpa_onnx
            from app.config import settings
            
            model_dir = settings.asr_model_dir
            
            self._recognizer = sherpa_onnx.OnlineRecognizer.from_transducer(
                encoder=f"{model_dir}/encoder-epoch-99-avg-1.int8.onnx",
                decoder=f"{model_dir}/decoder-epoch-99-avg-1.int8.onnx",
                joiner=f"{model_dir}/joiner-epoch-99-avg-1.int8.onnx",
                tokens=f"{model_dir}/tokens.txt",
                num_threads=2,
                sample_rate=16000,
                feature_dim=80,
                decoding_method='greedy_search'
            )
            logger.info("ASR recognizer initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize ASR recognizer: {e}")
            self._recognizer = None
    
    def transcribe(self, audio_base64: str) -> str:
        """
        将 Base64 编码的音频转为文字
        
        Args:
            audio_base64: Base64 编码的音频数据
            
        Returns:
            识别出的文字
        """
        if self._recognizer is None:
            logger.error("ASR recognizer not initialized")
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
            subprocess.run([
                'ffmpeg', '-y', '-i', tmp_path,
                '-ar', '16000', '-ac', '1',
                converted_path
            ], capture_output=True, check=True)
            
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
        if self._recognizer is None:
            return ""
        
        try:
            # 转换为 16kHz WAV
            import subprocess
            import tempfile
            
            converted_path = tempfile.mktemp(suffix='.wav')
            subprocess.run([
                'ffmpeg', '-y', '-i', audio_path,
                '-ar', '16000', '-ac', '1',
                converted_path
            ], capture_output=True, check=True)
            
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
            import os
            os.unlink(converted_path)
            
            return text
            
        except Exception as e:
            logger.error(f"ASR file transcription failed: {e}")
            return ""


# 全局服务实例
asr_service = ASRService()
