"""
# ----------------------------------------------------------------------------
# WhisperX本地引擎适配器
# 
# 将本地WhisperX引擎适配到统一的ASR接口
# 支持GPU/CPU自适应，模型自动下载，时间戳对齐等功能
# ----------------------------------------------------------------------------
"""

import os
import time
import subprocess
import warnings
from typing import Dict, List, Optional, Any

try:
    import torch
    import whisperx
    import librosa
    WHISPERX_AVAILABLE = True
except ImportError:
    WHISPERX_AVAILABLE = False

from ..base import ASREngineAdapter, ASRResult
from ..utils import AudioProcessor

warnings.filterwarnings("ignore")


class WhisperXLocalAdapter(ASREngineAdapter):
    """WhisperX本地引擎适配器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.version = "1.0.0"
        
        # 配置参数
        self.model_dir = config.get('model_dir', '_model_cache_') if config else '_model_cache_'
        self.language = config.get('language', 'auto') if config else 'auto'
        self.model_name = config.get('model_name', 'large-v2') if config else 'large-v2'
        
        # 运行时变量
        self.device = None
        self.batch_size = None
        self.compute_type = None
        self.model = None
        self.align_model = None
        self.metadata = None
    
    def initialize(self) -> None:
        """初始化WhisperX引擎"""
        if not WHISPERX_AVAILABLE:
            raise RuntimeError("❌ WhisperX库未安装，请运行: pip install whisperx")
        
        if self._is_initialized:
            return
        
        print("🚀 正在初始化WhisperX本地引擎...")
        
        # 设置HuggingFace镜像
        self._setup_hf_mirror()
        
        # 检测设备配置
        self._setup_device_config()
        
        # 加载主模型
        self._load_main_model()
        
        self._is_initialized = True
        print("✅ WhisperX本地引擎初始化完成")
    
    def transcribe(self, 
                  raw_audio_path: str,
                  vocal_audio_path: str,
                  start_time: float = 0.0,
                  end_time: Optional[float] = None) -> ASRResult:
        """转录音频片段"""
        if not self._is_initialized:
            self.initialize()
        
        self._validate_audio_path(raw_audio_path)
        self._validate_audio_path(vocal_audio_path)
        
        self._log_transcription_start(start_time, end_time)
        start_timer = time.time()
        
        try:
            # 加载音频段
            raw_audio = self._load_audio_segment(raw_audio_path, start_time, end_time)
            vocal_audio = self._load_audio_segment(vocal_audio_path, start_time, end_time)
            
            # 1. 转录原始音频
            print("🎤 正在转录音频...")
            result = self.model.transcribe(
                raw_audio, 
                batch_size=self.batch_size, 
                print_progress=True
            )
            
            # 清理GPU内存
            if self.device == "cuda":
                del self.model
                torch.cuda.empty_cache()
            
            # 检查语言
            detected_language = result.get('language', 'unknown')
            if detected_language == 'zh' and self.language != 'zh':
                print("⚠️  检测到中文语音，建议设置language='zh'以获得更好效果")
            
            # 2. 时间戳对齐
            print("⏰ 正在进行时间戳对齐...")
            if not self.align_model:
                self._load_align_model(detected_language)
            
            result = whisperx.align(
                result["segments"], 
                self.align_model, 
                self.metadata, 
                vocal_audio, 
                self.device, 
                return_char_alignments=False
            )
            
            # 清理GPU内存
            if self.device == "cuda":
                torch.cuda.empty_cache()
            
            # 3. 调整时间戳
            result_dict = {'segments': result['segments'], 'language': detected_language}
            result_dict = self._adjust_timestamps(result_dict, start_time)
            
            # 4. 转换为标准格式
            asr_result = ASRResult.from_dict(result_dict)
            
            elapsed_time = time.time() - start_timer
            self._log_transcription_complete(elapsed_time)
            
            return asr_result
            
        except Exception as e:
            print(f"❌ WhisperX转录失败: {str(e)}")
            raise
    
    def cleanup(self) -> None:
        """清理引擎资源"""
        if hasattr(self, 'model') and self.model:
            del self.model
        if hasattr(self, 'align_model') and self.align_model:
            del self.align_model
        if hasattr(self, 'metadata') and self.metadata:
            del self.metadata
        
        if self.device == "cuda":
            torch.cuda.empty_cache()
        
        self._is_initialized = False
        print("🧹 WhisperX引擎资源已清理")
    
    def get_supported_languages(self) -> List[str]:
        """获取支持的语言列表"""
        return [
            'en', 'zh', 'es', 'fr', 'de', 'it', 'ja', 'ko', 'ru',
            'pt', 'ar', 'hi', 'th', 'vi', 'nl', 'sv', 'da', 'no'
        ]
    
    def is_available(self) -> bool:
        """检查引擎是否可用"""
        if not WHISPERX_AVAILABLE:
            return False
        try:
            self.initialize()
            return True
        except Exception:
            return False
    
    def _setup_hf_mirror(self) -> None:
        """设置HuggingFace镜像"""
        try:
            mirrors = {'Official': 'huggingface.co', 'Mirror': 'hf-mirror.com'}
            fastest_url = f"https://{mirrors['Official']}"
            best_time = float('inf')
            
            print("🔍 检测HuggingFace镜像...")
            for name, domain in mirrors.items():
                if os.name == 'nt':
                    cmd = ['ping', '-n', '1', '-w', '3000', domain]
                else:
                    cmd = ['ping', '-c', '1', '-W', '3', domain]
                
                start = time.time()
                result = subprocess.run(cmd, capture_output=True, text=True)
                response_time = time.time() - start
                
                if result.returncode == 0:
                    if response_time < best_time:
                        best_time = response_time
                        fastest_url = f"https://{domain}"
                    print(f"  ✓ {name}: {response_time:.2f}s")
            
            if best_time == float('inf'):
                print("⚠️  所有镜像都无法访问，使用默认设置")
            else:
                print(f"🚀 选择镜像: {fastest_url} ({best_time:.2f}s)")
            
            os.environ['HF_ENDPOINT'] = fastest_url
            
        except Exception as e:
            print(f"⚠️  镜像检测失败: {str(e)}")
    
    def _setup_device_config(self) -> None:
        """设置设备配置"""
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        if self.device == "cuda":
            gpu_mem = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            self.batch_size = 16 if gpu_mem > 8 else 2
            self.compute_type = "float16" if torch.cuda.is_bf16_supported() else "int8"
            print(f"🎮 GPU内存: {gpu_mem:.2f}GB, 批次大小: {self.batch_size}, 计算类型: {self.compute_type}")
        else:
            self.batch_size = 1
            self.compute_type = "int8"
            print(f"💻 使用CPU模式, 批次大小: {self.batch_size}, 计算类型: {self.compute_type}")
    
    def _load_main_model(self) -> None:
        """加载主模型"""
        try:
            # 确定模型名称和路径
            if self.language == 'zh':
                model_name = "Huan69/Belle-whisper-large-v3-zh-punct-fasterwhisper"
                local_model = os.path.join(self.model_dir, "Belle-whisper-large-v3-zh-punct-fasterwhisper")
            else:
                model_name = self.model_name
                local_model = os.path.join(self.model_dir, model_name)
            
            # 设置模型选项
            vad_options = {"vad_onset": 0.500, "vad_offset": 0.363}
            asr_options = {"temperatures": [0], "initial_prompt": ""}
            whisper_language = None if 'auto' in self.language else self.language
            
            print("⚠️  可忽略torch版本警告信息")
            
            # 加载模型
            self.model = whisperx.load_model(
                model_name, 
                self.device, 
                compute_type=self.compute_type, 
                language=whisper_language, 
                vad_options=vad_options, 
                asr_options=asr_options, 
                download_root=self.model_dir
            )
            
            print("✅ 主模型加载完成")
            
        except Exception as e:
            print(f"❌ 加载主模型失败: {str(e)}")
            raise
    
    def _load_align_model(self, language: str) -> None:
        """加载对齐模型"""
        try:
            print(f"📥 加载{language}语言对齐模型...")
            self.align_model, self.metadata = whisperx.load_align_model(
                language_code=language, 
                device=self.device
            )
            print("✅ 对齐模型加载完成")
            
        except Exception as e:
            print(f"❌ 加载对齐模型失败: {str(e)}")
            raise
    
    def _load_audio_segment(self, 
                          audio_file: str, 
                          start_time: float, 
                          end_time: Optional[float]) -> 'numpy.ndarray':
        """加载音频段"""
        try:
            duration = end_time - start_time if end_time else None
            audio, _ = librosa.load(
                audio_file, 
                sr=16000, 
                offset=start_time, 
                duration=duration, 
                mono=True
            )
            return audio
            
        except Exception as e:
            print(f"❌ 加载音频段失败: {str(e)}")
            raise 