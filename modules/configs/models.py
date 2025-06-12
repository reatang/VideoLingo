"""
# ----------------------------------------------------------------------------
# 配置数据模型
# 
# 提供类型安全的配置数据模型，对应config.yaml中的各个配置节
# 使用数据类实现结构化的配置访问
# ----------------------------------------------------------------------------
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path


@dataclass
class APIConfig:
    """API配置模型"""
    key: str = ""
    base_url: str = "https://api.siliconflow.cn"
    model: str = "deepseek-ai/DeepSeek-V3"
    llm_support_json: bool = False
    max_workers: int = 4


@dataclass 
class WhisperConfig:
    """Whisper配置模型"""
    model: str = "large-v3"
    language: str = "zh"
    detected_language: str = "en"
    runtime: str = "local"  # local, cloud, elevenlabs
    whisperX_302_api_key: str = ""
    elevenlabs_api_key: str = ""
    
    def get_api_key(self) -> Optional[str]:
        """根据运行时获取对应的API密钥"""
        if self.runtime == "cloud":
            return self.whisperX_302_api_key or None
        elif self.runtime == "elevenlabs":
            return self.elevenlabs_api_key or None
        else:
            return None


@dataclass
class SubtitleConfig:
    """字幕配置模型"""
    max_length: int = 75
    target_multiplier: float = 1.2
    burn_subtitles: bool = True


@dataclass
class TTSBaseConfig:
    """TTS基础配置"""
    api_key: str = ""


@dataclass
class EdgeTTSConfig(TTSBaseConfig):
    """Edge TTS配置"""
    voice: str = "zh-CN-XiaoxiaoNeural"


@dataclass
class OpenAITTSConfig(TTSBaseConfig):
    """OpenAI TTS配置"""
    voice: str = "alloy"


@dataclass
class AzureTTSConfig(TTSBaseConfig):
    """Azure TTS配置"""
    voice: str = "zh-CN-YunfengNeural"


@dataclass
class FishTTSConfig(TTSBaseConfig):
    """Fish TTS配置"""
    character: str = "AD学姐"
    character_id_dict: Dict[str, str] = field(default_factory=dict)


@dataclass
class SFFishTTSConfig(TTSBaseConfig):
    """SiliconFlow Fish TTS配置"""
    voice: str = "anna"
    custom_name: str = ""
    voice_id: str = ""
    mode: str = "preset"  # preset, custom, dynamic


@dataclass
class GPTSoVITSConfig:
    """GPT-SoVITS配置"""
    character: str = "Huanyuv2"
    refer_mode: int = 3


@dataclass
class SpeedFactorConfig:
    """音频速度配置"""
    min: float = 1.0
    accept: float = 1.2
    max: float = 1.4


@dataclass
class AudioConfig:
    """音频处理配置"""
    min_subtitle_duration: float = 2.5
    min_trim_duration: float = 3.5
    tolerance: float = 1.5
    speed_factor: SpeedFactorConfig = field(default_factory=SpeedFactorConfig)


@dataclass
class YoutubeConfig:
    """YouTube配置"""
    cookies_path: str = ""
    ytb_resolution: str = "1080"


@dataclass
class TranslationConfig:
    """翻译相关配置"""
    target_language: str = "英文"
    max_split_length: int = 20
    reflect_translate: bool = True
    pause_before_translate: bool = False
    summary_length: int = 8000


@dataclass
class SystemConfig:
    """系统配置"""
    display_language: str = "zh-CN"
    model_dir: str = "./_model_cache"
    ffmpeg_gpu: bool = False
    allowed_video_formats: List[str] = field(default_factory=lambda: ['mp4', 'mov', 'avi', 'mkv'])
    allowed_audio_formats: List[str] = field(default_factory=lambda: ['wav', 'mp3', 'flac', 'm4a'])


@dataclass
class LanguageConfig:
    """语言配置"""
    language_split_with_space: List[str] = field(default_factory=lambda: ['en', 'es', 'fr', 'de', 'it', 'ru'])
    language_split_without_space: List[str] = field(default_factory=lambda: ['zh', 'ja'])
    spacy_model_map: Dict[str, str] = field(default_factory=dict)
    
    def get_joiner(self, language: str) -> str:
        """获取语言的分词连接符"""
        if language in self.language_split_with_space:
            return " "
        elif language in self.language_split_without_space:
            return ""
        else:
            return " "  # 默认使用空格


@dataclass
class VideoLingoConfig:
    """VideoLingo完整配置模型"""
    display_language: str = "zh-CN"
    target_language: str = "英文"
    demucs: bool = True
    burn_subtitles: bool = True
    tts_method: str = "edge_tts"
    
    # 各个配置组件
    api: APIConfig = field(default_factory=APIConfig)
    whisper: WhisperConfig = field(default_factory=WhisperConfig)
    subtitle: SubtitleConfig = field(default_factory=SubtitleConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    translation: TranslationConfig = field(default_factory=TranslationConfig)
    system: SystemConfig = field(default_factory=SystemConfig)
    language: LanguageConfig = field(default_factory=LanguageConfig)
    youtube: YoutubeConfig = field(default_factory=YoutubeConfig)
    
    # TTS配置 (动态根据tts_method确定)
    edge_tts: EdgeTTSConfig = field(default_factory=EdgeTTSConfig)
    openai_tts: OpenAITTSConfig = field(default_factory=OpenAITTSConfig)
    azure_tts: AzureTTSConfig = field(default_factory=AzureTTSConfig)
    fish_tts: FishTTSConfig = field(default_factory=FishTTSConfig)
    sf_fish_tts: SFFishTTSConfig = field(default_factory=SFFishTTSConfig)
    gpt_sovits: GPTSoVITSConfig = field(default_factory=GPTSoVITSConfig)
    
    def get_current_tts_config(self) -> Any:
        """获取当前选择的TTS配置"""
        return getattr(self, self.tts_method, None)
    
    def get_model_dir(self) -> Path:
        """获取模型目录路径"""
        return Path(self.system.model_dir)
    
    def validate_api_keys(self) -> Dict[str, bool]:
        """验证API密钥配置状态"""
        status = {}
        
        # LLM API密钥
        status['llm'] = bool(self.api.key.strip())
        
        # Whisper API密钥
        if self.whisper.runtime == 'cloud':
            status['whisper_302'] = bool(self.whisper.whisperX_302_api_key.strip())
        elif self.whisper.runtime == 'elevenlabs':
            status['whisper_elevenlabs'] = bool(self.whisper.elevenlabs_api_key.strip())
        
        # TTS API密钥
        current_tts = self.get_current_tts_config()
        if current_tts and hasattr(current_tts, 'api_key'):
            status[f'tts_{self.tts_method}'] = bool(current_tts.api_key.strip())
        
        return status
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VideoLingoConfig':
        """从配置字典创建完整配置对象"""
        config = cls()
        
        # 基本配置
        config.display_language = data.get('display_language', config.display_language)
        config.target_language = data.get('target_language', config.target_language)
        config.demucs = data.get('demucs', config.demucs)
        config.burn_subtitles = data.get('burn_subtitles', config.burn_subtitles)
        config.tts_method = data.get('tts_method', config.tts_method)
        
        # 组件配置
        if 'api' in data:
            config.api = APIConfig(**data['api'])
        
        if 'whisper' in data:
            config.whisper = WhisperConfig(**data['whisper'])
        
        if 'subtitle' in data:
            config.subtitle = SubtitleConfig(**data['subtitle'])
        
        # TTS配置
        tts_configs = {
            'edge_tts': EdgeTTSConfig,
            'openai_tts': OpenAITTSConfig,
            'azure_tts': AzureTTSConfig,
            'fish_tts': FishTTSConfig,
            'sf_fish_tts': SFFishTTSConfig
        }
        
        for tts_name, tts_class in tts_configs.items():
            if tts_name in data:
                setattr(config, tts_name, tts_class(**data[tts_name]))
        
        if 'gpt_sovits' in data:
            config.gpt_sovits = GPTSoVITSConfig(**data['gpt_sovits'])
        
        return config
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {
            'display_language': self.display_language,
            'target_language': self.target_language,
            'demucs': self.demucs,
            'burn_subtitles': self.burn_subtitles,
            'tts_method': self.tts_method
        }
        
        # 添加各组件配置
        from dataclasses import asdict
        result['api'] = asdict(self.api)
        result['whisper'] = asdict(self.whisper)
        result['subtitle'] = asdict(self.subtitle)
        
        # 添加TTS配置
        result['edge_tts'] = asdict(self.edge_tts)
        result['openai_tts'] = asdict(self.openai_tts)
        result['azure_tts'] = asdict(self.azure_tts)
        result['fish_tts'] = asdict(self.fish_tts)
        result['sf_fish_tts'] = asdict(self.sf_fish_tts)
        result['gpt_sovits'] = asdict(self.gpt_sovits)
        
        return result 