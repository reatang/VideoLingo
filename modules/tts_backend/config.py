"""
# ----------------------------------------------------------------------------
# TTS配置管理
# 
# 为每个TTS引擎定义专门的配置类
# 支持从全局配置管理器获取配置，以及配置验证
# 基于config.yaml.example中的TTS配置结构设计
# ----------------------------------------------------------------------------
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from pathlib import Path


@dataclass
class TTSBaseConfig:
    """TTS基础配置类"""
    api_key: str = ""
    voice: str = ""
    language: str = "zh-CN"
    output_format: str = "wav"
    sample_rate: int = 24000
    max_text_length: int = 5000
    timeout: float = 30.0
    
    def validate(self) -> bool:
        """验证基础配置"""
        return True  # 基类默认通过验证


@dataclass
class EdgeTTSConfig(TTSBaseConfig):
    """Edge TTS配置"""
    voice: str = "zh-CN-XiaoxiaoNeural"
    rate: str = "+0%"
    pitch: str = "+0Hz"
    volume: str = "+0%"
    
    # Edge TTS支持的声音列表
    supported_voices: List[str] = field(default_factory=lambda: [
        "zh-CN-XiaoxiaoNeural", "zh-CN-YunxiNeural", "zh-CN-YunjianNeural",
        "zh-CN-XiaoyiNeural", "zh-CN-YunyangNeural", "zh-CN-XiaochenNeural",
        "en-US-AriaNeural", "en-US-JennyNeural", "en-US-GuyNeural"
    ])
    
    def validate(self) -> bool:
        """验证Edge TTS配置"""
        return self.voice in self.supported_voices


@dataclass
class OpenAITTSConfig(TTSBaseConfig):
    """OpenAI TTS配置"""
    api_key: str = ""
    voice: str = "alloy"
    model: str = "tts-1"
    speed: float = 1.0
    
    # OpenAI TTS支持的声音列表
    supported_voices: List[str] = field(default_factory=lambda: [
        "alloy", "echo", "fable", "onyx", "nova", "shimmer"
    ])
    
    supported_models: List[str] = field(default_factory=lambda: [
        "tts-1", "tts-1-hd"
    ])
    
    def validate(self) -> bool:
        """验证OpenAI TTS配置"""
        if not self.api_key:
            print("❌ OpenAI TTS缺少API密钥")
            return False
        return (self.voice in self.supported_voices and 
                self.model in self.supported_models and
                0.25 <= self.speed <= 4.0)


@dataclass
class AzureTTSConfig(TTSBaseConfig):
    """Azure TTS配置"""
    api_key: str = ""
    voice: str = "zh-CN-YunfengNeural"
    style: str = "general"
    rate: str = "medium"
    pitch: str = "medium"
    
    # Azure TTS支持的声音列表（部分）
    supported_voices: List[str] = field(default_factory=lambda: [
        "zh-CN-YunfengNeural", "zh-CN-XiaoxiaoNeural", "zh-CN-YunyangNeural",
        "zh-CN-XiaoyiNeural", "zh-CN-YunjianNeural", "zh-CN-XiaochenNeural"
    ])
    
    def validate(self) -> bool:
        """验证Azure TTS配置"""
        if not self.api_key:
            print("❌ Azure TTS缺少API密钥")
            return False
        return self.voice in self.supported_voices


@dataclass 
class FishTTSConfig(TTSBaseConfig):
    """Fish TTS配置"""
    api_key: str = ""
    character: str = "AD学姐"
    character_id_dict: Dict[str, str] = field(default_factory=lambda: {
        'AD学姐': '7f92f8afb8ec43bf81429cc1c9199cb1',
        '丁真': '54a5170264694bfc8e9ad98df7bd89c3'
    })
    
    def get_character_id(self) -> str:
        """获取角色ID"""
        return self.character_id_dict.get(self.character, "")
    
    def validate(self) -> bool:
        """验证Fish TTS配置"""
        if not self.api_key:
            print("❌ Fish TTS缺少API密钥")
            return False
        return self.character in self.character_id_dict


@dataclass
class SFFishTTSConfig(TTSBaseConfig):
    """SiliconFlow Fish TTS配置"""
    api_key: str = ""
    voice: str = "anna"
    custom_name: str = ""
    voice_id: str = ""
    mode: str = "preset"  # preset, custom, dynamic
    
    supported_preset_voices: List[str] = field(default_factory=lambda: [
        "anna", "bella", "charles", "david", "emma"
    ])
    
    def validate(self) -> bool:
        """验证SiliconFlow Fish TTS配置"""
        if not self.api_key:
            print("❌ SiliconFlow Fish TTS缺少API密钥")
            return False
        
        if self.mode == "preset":
            return self.voice in self.supported_preset_voices
        elif self.mode == "custom":
            return bool(self.custom_name and self.voice_id)
        
        return True


@dataclass
class GPTSoVITSConfig(TTSBaseConfig):
    """GPT-SoVITS配置"""
    character: str = "Huanyuv2"
    refer_mode: int = 3
    api_url: str = "http://127.0.0.1:9880"
    top_k: int = 15
    top_p: float = 1.0
    temperature: float = 1.0
    batch_size: int = 1
    speed_factor: float = 1.0
    seed: int = -1
    
    # 支持的角色列表（需要根据实际模型配置）
    supported_characters: List[str] = field(default_factory=lambda: [
        "Huanyuv2", "default"
    ])
    
    def validate(self) -> bool:
        """验证GPT-SoVITS配置"""
        return (self.character in self.supported_characters and
                1 <= self.refer_mode <= 4 and
                0.0 <= self.temperature <= 2.0 and
                0.0 <= self.top_p <= 1.0)


@dataclass
class SFCosyVoice2Config(TTSBaseConfig):
    """SiliconFlow CosyVoice2配置"""
    api_key: str = ""
    voice_id: str = ""
    instruct_text: str = ""
    
    def validate(self) -> bool:
        """验证CosyVoice2配置"""
        if not self.api_key:
            print("❌ CosyVoice2缺少API密钥")
            return False
        return bool(self.voice_id)


@dataclass
class F5TTSConfig(TTSBaseConfig):
    """F5-TTS配置"""
    api_key: str = ""
    model: str = "F5-TTS"
    ref_audio: str = ""
    ref_text: str = ""
    
    supported_models: List[str] = field(default_factory=lambda: [
        "F5-TTS", "E2-TTS"
    ])
    
    def validate(self) -> bool:
        """验证F5-TTS配置"""
        if not self.api_key:
            print("❌ F5-TTS缺少API密钥")
            return False
        return (self.model in self.supported_models and
                bool(self.ref_audio and self.ref_text))


@dataclass
class CustomTTSConfig(TTSBaseConfig):
    """自定义TTS配置"""
    api_url: str = ""
    headers: Dict[str, str] = field(default_factory=dict)
    request_format: str = "json"  # json, form
    response_format: str = "json"  # json, binary
    
    def validate(self) -> bool:
        """验证自定义TTS配置"""
        return bool(self.api_url)


class TTSConfig:
    """TTS配置管理器"""
    
    def __init__(self, config_manager=None):
        """初始化TTS配置管理器"""
        self._config_manager = config_manager
        self._configs_cache = {}
    
    def _get_config_manager(self):
        """获取全局配置管理器"""
        if self._config_manager is None:
            try:
                from ..configs import get_global_config
                self._config_manager = get_global_config()
            except ImportError:
                print("⚠️  配置管理器不可用，使用默认配置")
                return None
        return self._config_manager
    
    def get_tts_method(self) -> str:
        """获取当前选择的TTS方法"""
        config_manager = self._get_config_manager()
        if config_manager:
            return config_manager.get_config().get('tts_method', 'edge_tts')
        return 'edge_tts'
    
    def get_engine_config(self, engine_type: str) -> TTSBaseConfig:
        """
        获取指定引擎的配置
        
        Args:
            engine_type: TTS引擎类型
            
        Returns:
            对应的配置对象
        """
        if engine_type in self._configs_cache:
            return self._configs_cache[engine_type]
        
        config_manager = self._get_config_manager()
        if config_manager is None:
            return self._get_default_config(engine_type)
        
        try:
            global_config = config_manager.get_config()
            engine_config_data = global_config.get(engine_type, {})
            
            # 根据引擎类型创建对应配置对象
            config_obj = self._create_config_object(engine_type, engine_config_data)
            self._configs_cache[engine_type] = config_obj
            return config_obj
            
        except Exception as e:
            print(f"⚠️  获取{engine_type}配置失败: {e}")
            return self._get_default_config(engine_type)
    
    def _create_config_object(self, engine_type: str, config_data: Dict) -> TTSBaseConfig:
        """根据引擎类型创建配置对象"""
        config_classes = {
            'edge_tts': EdgeTTSConfig,
            'openai_tts': OpenAITTSConfig,
            'azure_tts': AzureTTSConfig,
            'fish_tts': FishTTSConfig,
            'sf_fish_tts': SFFishTTSConfig,
            'gpt_sovits': GPTSoVITSConfig,
            'sf_cosyvoice2': SFCosyVoice2Config,
            'f5tts': F5TTSConfig,
            'custom_tts': CustomTTSConfig,
        }
        
        config_class = config_classes.get(engine_type, TTSBaseConfig)
        
        try:
            return config_class(**config_data)
        except Exception as e:
            print(f"⚠️  创建{engine_type}配置对象失败: {e}")
            return config_class()
    
    def _get_default_config(self, engine_type: str) -> TTSBaseConfig:
        """获取默认配置"""
        defaults = {
            'edge_tts': EdgeTTSConfig(),
            'openai_tts': OpenAITTSConfig(),
            'azure_tts': AzureTTSConfig(),
            'fish_tts': FishTTSConfig(),
            'sf_fish_tts': SFFishTTSConfig(),
            'gpt_sovits': GPTSoVITSConfig(),
            'sf_cosyvoice2': SFCosyVoice2Config(),
            'f5tts': F5TTSConfig(),
            'custom_tts': CustomTTSConfig(),
        }
        
        return defaults.get(engine_type, TTSBaseConfig())
    
    def validate_engine_config(self, engine_type: str) -> bool:
        """验证指定引擎的配置"""
        config = self.get_engine_config(engine_type)
        return config.validate()
    
    def get_available_engines(self) -> List[str]:
        """获取配置完整的可用引擎列表"""
        engines = [
            'edge_tts', 'openai_tts', 'azure_tts', 'fish_tts',
            'sf_fish_tts', 'gpt_sovits', 'sf_cosyvoice2', 
            'f5tts', 'custom_tts'
        ]
        
        available = []
        for engine in engines:
            if self.validate_engine_config(engine):
                available.append(engine)
        
        return available
    
    def clear_cache(self) -> None:
        """清空配置缓存"""
        self._configs_cache.clear()


# 全局TTS配置管理器实例
_global_tts_config = None


def get_tts_config() -> TTSConfig:
    """获取全局TTS配置管理器"""
    global _global_tts_config
    if _global_tts_config is None:
        _global_tts_config = TTSConfig()
    return _global_tts_config


def get_tts_config_for_engine(engine_type: str) -> TTSBaseConfig:
    """
    获取指定引擎的配置（便捷函数）
    
    Args:
        engine_type: TTS引擎类型
        
    Returns:
        配置对象
    """
    return get_tts_config().get_engine_config(engine_type)


def validate_all_tts_configs() -> Dict[str, bool]:
    """验证所有TTS引擎配置"""
    tts_config = get_tts_config()
    engines = [
        'edge_tts', 'openai_tts', 'azure_tts', 'fish_tts',
        'sf_fish_tts', 'gpt_sovits', 'sf_cosyvoice2', 
        'f5tts', 'custom_tts'
    ]
    
    results = {}
    for engine in engines:
        try:
            results[engine] = tts_config.validate_engine_config(engine)
        except Exception as e:
            print(f"❌ 验证{engine}配置失败: {e}")
            results[engine] = False
    
    return results 