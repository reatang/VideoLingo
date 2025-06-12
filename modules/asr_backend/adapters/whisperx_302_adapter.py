"""
# ----------------------------------------------------------------------------
# WhisperX 302 API引擎适配器
# 
# 将302 API引擎适配到统一的ASR接口
# 支持API调用、结果缓存、时间戳调整等功能
# ----------------------------------------------------------------------------
"""

import os
import io
import json
import time
from typing import Dict, List, Optional, Any, TypedDict

try:
    import requests
    import librosa
    import soundfile as sf
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

from ..base import ASREngineAdapter, ASRResult

class _CloudConfig(TypedDict):
    api_key: str
    language: str
    cache_dir: str

class WhisperX302Adapter(ASREngineAdapter):
    """WhisperX 302 API引擎适配器"""
    
    def __init__(self, config: _CloudConfig):
        super().__init__(config)
        self.version = "1.0.0"
        
        # 配置参数
        self.api_key = config.get('api_key', None)
        self.language = config.get('language', 'auto')
        self.cache_dir = config.get('cache_dir', 'output/log') if config else 'output/log'
        
        # API配置
        self.api_url = "https://api.302.ai/302/whisperx"
        self.timeout = 300  # 5分钟超时
    
    def initialize(self) -> None:
        """初始化302 API引擎"""
        if not REQUESTS_AVAILABLE:
            raise RuntimeError("❌ requests库未安装，请运行: pip install requests librosa soundfile")
        
        if not self.api_key:
            raise ValueError("❌ 未配置302 API密钥，请设置api_key参数")
        
        if self._is_initialized:
            return
        
        print("🚀 正在初始化WhisperX 302 API引擎...")
        
        # 创建缓存目录
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # 测试API连接
        self._test_api_connection()
        
        self._is_initialized = True
        print("✅ WhisperX 302 API引擎初始化完成")
    
    def transcribe(self, 
                  raw_audio_path: str,
                  vocal_audio_path: str,
                  start_time: float = 0.0,
                  end_time: Optional[float] = None) -> ASRResult:
        """转录音频片段"""
        if not self._is_initialized:
            self.initialize()
        
        self._validate_audio_path(vocal_audio_path)
        
        self._log_transcription_start(start_time, end_time)
        start_timer = time.time()
        
        try:
            # 检查缓存
            cache_key = self._get_cache_key(vocal_audio_path, start_time, end_time)
            cache_file = os.path.join(self.cache_dir, f"whisperx302_{cache_key}.json")
            
            if os.path.exists(cache_file):
                print("📋 使用缓存结果...")
                with open(cache_file, "r", encoding="utf-8") as f:
                    result_dict = json.load(f)
                return ASRResult.from_dict(result_dict)
            
            # 加载和处理音频
            audio_data, duration = self._load_and_process_audio(
                vocal_audio_path, start_time, end_time
            )
            
            # 调用API
            result_dict = self._call_api(audio_data, start_time)
            
            # 保存缓存
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(result_dict, f, indent=4, ensure_ascii=False)
            
            # 转换为标准格式
            asr_result = ASRResult.from_dict(result_dict)
            
            elapsed_time = time.time() - start_timer
            self._log_transcription_complete(elapsed_time)
            
            return asr_result
            
        except Exception as e:
            print(f"❌ 302 API转录失败: {str(e)}")
            raise
    
    def cleanup(self) -> None:
        """清理引擎资源"""
        self._is_initialized = False
        print("🧹 302 API引擎资源已清理")
    
    def get_supported_languages(self) -> List[str]:
        """获取支持的语言列表"""
        return [
            'en', 'zh', 'es', 'fr', 'de', 'it', 'ja', 'ko', 'ru',
            'pt', 'ar', 'hi', 'th', 'vi', 'nl', 'sv', 'da', 'no'
        ]
    
    def is_available(self) -> bool:
        """检查引擎是否可用"""
        if not REQUESTS_AVAILABLE:
            return False
        if not self.api_key:
            return False
        try:
            self.initialize()
            return True
        except Exception:
            return False
    
    def _test_api_connection(self) -> None:
        """测试API连接"""
        try:
            # 创建一个短的测试音频
            test_audio = self._create_test_audio()
            
            headers = {'Authorization': f'Bearer {self.api_key}'}
            files = [('audio_input', ('test.wav', test_audio, 'application/octet-stream'))]
            payload = {
                "processing_type": "align", 
                "language": "en", 
                "output": "raw"
            }
            
            response = requests.post(
                self.api_url, 
                headers=headers, 
                data=payload, 
                files=files,
                timeout=30
            )
            
            if response.status_code == 200:
                print("✅ API连接测试成功")
            else:
                raise RuntimeError(f"API连接测试失败: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"❌ API连接测试失败: {str(e)}")
            raise
    
    def _create_test_audio(self) -> io.BytesIO:
        """创建测试音频"""
        import numpy as np
        
        # 创建1秒的静音音频
        sr = 16000
        duration = 1.0
        samples = int(sr * duration)
        audio_data = np.zeros(samples, dtype=np.float32)
        
        audio_buffer = io.BytesIO()
        sf.write(audio_buffer, audio_data, sr, format='WAV', subtype='PCM_16')
        audio_buffer.seek(0)
        
        return audio_buffer
    
    def _get_cache_key(self, 
                      audio_path: str, 
                      start_time: float, 
                      end_time: Optional[float]) -> str:
        """生成缓存键"""
        import hashlib
        
        # 使用文件路径、时间戳和语言生成唯一键
        key_string = f"{audio_path}_{start_time}_{end_time}_{self.language}"
        return hashlib.md5(key_string.encode()).hexdigest()[:16]
    
    def _load_and_process_audio(self, 
                               audio_path: str, 
                               start_time: float, 
                               end_time: Optional[float]) -> tuple:
        """加载和处理音频"""
        try:
            # 加载音频
            y, sr = librosa.load(audio_path, sr=16000)
            audio_duration = len(y) / sr
            
            # 处理时间范围
            if start_time is None:
                start_time = 0
            if end_time is None:
                end_time = audio_duration
            
            # 提取音频片段
            start_sample = int(start_time * sr)
            end_sample = int(end_time * sr)
            y_slice = y[start_sample:end_sample]
            
            # 转换为WAV格式
            audio_buffer = io.BytesIO()
            sf.write(audio_buffer, y_slice, sr, format='WAV', subtype='PCM_16')
            audio_buffer.seek(0)
            
            return audio_buffer, end_time - start_time
            
        except Exception as e:
            print(f"❌ 音频加载失败: {str(e)}")
            raise
    
    def _call_api(self, audio_data: io.BytesIO, start_time: float) -> Dict:
        """调用API进行转录"""
        try:
            print(f"🌐 正在调用302 API转录 (语言: {self.language})...")
            
            headers = {'Authorization': f'Bearer {self.api_key}'}
            files = [('audio_input', ('audio_slice.wav', audio_data, 'application/octet-stream'))]
            payload = {
                "processing_type": "align", 
                "language": self.language, 
                "output": "raw"
            }
            
            start_call = time.time()
            response = requests.post(
                self.api_url, 
                headers=headers, 
                data=payload, 
                files=files,
                timeout=self.timeout
            )
            call_time = time.time() - start_call
            
            if response.status_code != 200:
                raise RuntimeError(f"API调用失败: HTTP {response.status_code}, {response.text}")
            
            result_dict = response.json()
            
            # 调整时间戳
            if start_time > 0:
                result_dict = self._adjust_timestamps(result_dict, start_time)
            
            print(f"✅ API调用成功，耗时: {call_time:.2f}秒")
            return result_dict
            
        except requests.Timeout:
            raise RuntimeError("❌ API调用超时，请检查网络连接")
        except requests.RequestException as e:
            raise RuntimeError(f"❌ API请求失败: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"❌ API调用异常: {str(e)}") 