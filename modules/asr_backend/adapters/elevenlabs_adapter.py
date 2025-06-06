"""
# ----------------------------------------------------------------------------
# ElevenLabs API引擎适配器
# 
# 将ElevenLabs API引擎适配到统一的ASR接口
# 支持API调用、格式转换、说话人分离等功能
# ----------------------------------------------------------------------------
"""

import os
import json
import time
import tempfile
from typing import Dict, List, Optional, Any

try:
    import requests
    import librosa
    import soundfile as sf
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

from ..base import ASREngineAdapter, ASRResult


class ElevenLabsAdapter(ASREngineAdapter):
    """ElevenLabs API引擎适配器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.version = "1.0.0"
        
        # 配置参数
        self.api_key = config.get('api_key') if config else None
        self.language = config.get('language', 'auto') if config else 'auto'
        self.cache_dir = config.get('cache_dir', 'output/log') if config else 'output/log'
        
        # API配置
        self.api_url = "https://api.elevenlabs.io/v1/speech-to-text"
        self.timeout = 300  # 5分钟超时
        
        # 语言代码映射
        self.iso_639_2_to_1 = {
            "eng": "en", "fra": "fr", "deu": "de", "ita": "it",
            "spa": "es", "rus": "ru", "kor": "ko", "jpn": "ja",
            "zho": "zh", "yue": "zh"
        }
    
    def initialize(self) -> None:
        """初始化ElevenLabs API引擎"""
        if not REQUESTS_AVAILABLE:
            raise RuntimeError("❌ requests库未安装，请运行: pip install requests librosa soundfile")
        
        if not self.api_key:
            raise ValueError("❌ 未配置ElevenLabs API密钥，请设置api_key参数")
        
        if self._is_initialized:
            return
        
        print("🚀 正在初始化ElevenLabs API引擎...")
        
        # 创建缓存目录
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # 测试API连接
        self._test_api_connection()
        
        self._is_initialized = True
        print("✅ ElevenLabs API引擎初始化完成")
    
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
            cache_file = os.path.join(self.cache_dir, f"elevenlabs_{cache_key}.json")
            
            if os.path.exists(cache_file):
                print("📋 使用缓存结果...")
                with open(cache_file, "r", encoding="utf-8") as f:
                    result_dict = json.load(f)
                return ASRResult.from_dict(result_dict)
            
            # 创建临时音频文件
            temp_file = self._create_temp_audio_file(vocal_audio_path, start_time, end_time)
            
            try:
                # 调用API
                raw_result = self._call_api(temp_file)
                
                # 转换格式
                result_dict = self._convert_elevenlabs_format(raw_result, start_time)
                
                # 保存缓存
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump(result_dict, f, indent=4, ensure_ascii=False)
                
                # 转换为标准格式
                asr_result = ASRResult.from_dict(result_dict)
                
                elapsed_time = time.time() - start_timer
                self._log_transcription_complete(elapsed_time)
                
                return asr_result
                
            finally:
                # 清理临时文件
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            
        except Exception as e:
            print(f"❌ ElevenLabs转录失败: {str(e)}")
            raise
    
    def cleanup(self) -> None:
        """清理引擎资源"""
        self._is_initialized = False
        print("🧹 ElevenLabs引擎资源已清理")
    
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
            headers = {"xi-api-key": self.api_key}
            
            # 测试简单的API调用（不发送音频）
            response = requests.get(
                "https://api.elevenlabs.io/v1/user",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                print("✅ API连接测试成功")
            else:
                raise RuntimeError(f"API连接测试失败: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"❌ API连接测试失败: {str(e)}")
            raise
    
    def _get_cache_key(self, 
                      audio_path: str, 
                      start_time: float, 
                      end_time: Optional[float]) -> str:
        """生成缓存键"""
        import hashlib
        
        # 使用文件路径、时间戳和语言生成唯一键
        key_string = f"{audio_path}_{start_time}_{end_time}_{self.language}"
        return hashlib.md5(key_string.encode()).hexdigest()[:16]
    
    def _create_temp_audio_file(self, 
                               audio_path: str, 
                               start_time: float, 
                               end_time: Optional[float]) -> str:
        """创建临时音频文件"""
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
            
            # 创建临时文件
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
                temp_filepath = temp_file.name
                sf.write(temp_filepath, y_slice, sr, format='MP3')
            
            return temp_filepath
            
        except Exception as e:
            print(f"❌ 创建临时音频文件失败: {str(e)}")
            raise
    
    def _call_api(self, audio_file_path: str) -> Dict:
        """调用ElevenLabs API进行转录"""
        try:
            print(f"🎙️ 正在调用ElevenLabs API转录 (语言: {self.language})...")
            
            headers = {"xi-api-key": self.api_key}
            
            data = {
                "model_id": "scribe_v1",
                "timestamps_granularity": "word",
                "language_code": self.language,
                "diarize": True,
                "num_speakers": None,
                "tag_audio_events": False
            }
            
            with open(audio_file_path, 'rb') as audio_file:
                files = {"file": (os.path.basename(audio_file_path), audio_file, 'audio/mpeg')}
                
                start_call = time.time()
                response = requests.post(
                    self.api_url, 
                    headers=headers, 
                    data=data, 
                    files=files,
                    timeout=self.timeout
                )
                call_time = time.time() - start_call
            
            if response.status_code != 200:
                raise RuntimeError(f"API调用失败: HTTP {response.status_code}, {response.text}")
            
            result = response.json()
            
            # 保存检测到的语言
            detected_language = self.iso_639_2_to_1.get(
                result.get("language_code", ""), 
                result.get("language_code", "unknown")
            )
            result['detected_language'] = detected_language
            
            print(f"✅ API调用成功，耗时: {call_time:.2f}秒")
            return result
            
        except requests.Timeout:
            raise RuntimeError("❌ API调用超时，请检查网络连接")
        except requests.RequestException as e:
            raise RuntimeError(f"❌ API请求失败: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"❌ API调用异常: {str(e)}")
    
    def _convert_elevenlabs_format(self, 
                                 elev_result: Dict, 
                                 start_time: float,
                                 word_level_timestamp: bool = True) -> Dict:
        """将ElevenLabs格式转换为Whisper兼容格式"""
        try:
            words = elev_result.get("words", [])
            if not words:
                return {"segments": [], "language": elev_result.get('detected_language', 'unknown')}
            
            segments = []
            current_segment = {
                "text": "",
                "start": words[0]["start"] + start_time,
                "end": words[0]["end"] + start_time,
                "speaker_id": words[0].get("speaker_id", "speaker_1"),
                "words": []
            }
            
            split_gap = 1.0  # 1秒间隔分割段落
            
            for i, word in enumerate(words):
                # 调整时间戳
                word_start = word["start"] + start_time
                word_end = word["end"] + start_time
                word_text = word.get("text", "")
                word_speaker = word.get("speaker_id", "speaker_1")
                
                # 添加词汇到当前段落
                current_segment["text"] += word_text
                current_segment["end"] = word_end
                
                if word_level_timestamp:
                    current_segment["words"].append({
                        "word": word_text,
                        "start": word_start,
                        "end": word_end
                    })
                
                # 检查是否需要分割段落
                next_word = words[i + 1] if i + 1 < len(words) else None
                
                should_split = (
                    next_word is None or  # 最后一个词
                    (next_word["start"] - word["end"] > split_gap) or  # 间隔过长
                    (next_word.get("speaker_id", "speaker_1") != word_speaker)  # 说话人变化
                )
                
                if should_split:
                    current_segment["text"] = current_segment["text"].strip()
                    
                    if not word_level_timestamp:
                        current_segment.pop("words", None)
                    
                    segments.append(current_segment)
                    
                    # 准备下一个段落
                    if next_word is not None:
                        current_segment = {
                            "text": "",
                            "start": next_word["start"] + start_time,
                            "end": next_word["end"] + start_time,
                            "speaker_id": next_word.get("speaker_id", "speaker_1"),
                            "words": []
                        }
            
            return {
                "segments": segments,
                "language": elev_result.get('detected_language', 'unknown')
            }
            
        except Exception as e:
            print(f"❌ 格式转换失败: {str(e)}")
            raise 