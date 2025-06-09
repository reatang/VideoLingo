"""
# ----------------------------------------------------------------------------
# TTS适配器模块
# 
# 导出所有TTS引擎适配器，提供统一的接口访问
# ----------------------------------------------------------------------------
"""

from .edge_tts_adapter import EdgeTTSAdapter
from .openai_tts_adapter import OpenAITTSAdapter
from .azure_tts_adapter import AzureTTSAdapter
from .fish_tts_adapter import FishTTSAdapter
from .sf_fish_tts_adapter import SFishTTSAdapter
from .gpt_sovits_adapter import GPTSoVITSAdapter
from .sf_cosyvoice2_adapter import SFCosyVoice2Adapter
from .f5tts_adapter import F5TTSAdapter
from .custom_tts_adapter import CustomTTSAdapter

# 便捷函数导出（保持向后兼容）
from .edge_tts_adapter import edge_tts
from .openai_tts_adapter import openai_tts
from .azure_tts_adapter import azure_tts
from .fish_tts_adapter import fish_tts
from .sf_fish_tts_adapter import siliconflow_fish_tts
from .gpt_sovits_adapter import gpt_sovits_tts
from .sf_cosyvoice2_adapter import sf_cosyvoice2_tts
from .f5tts_adapter import f5tts_synthesize
from .custom_tts_adapter import custom_tts_synthesize, example_custom_processor

__all__ = [
    # 适配器类
    'EdgeTTSAdapter',
    'OpenAITTSAdapter',
    'AzureTTSAdapter',
    'FishTTSAdapter',
    'SFishTTSAdapter',
    'GPTSoVITSAdapter',
    'SFCosyVoice2Adapter',
    'F5TTSAdapter',
    'CustomTTSAdapter',
    
    # 便捷函数
    'edge_tts_synthesize',
    'openai_tts',
    'azure_tts',
    'fish_tts',
    'siliconflow_fish_tts',
    'gpt_sovits_tts',
    'sf_cosyvoice2_tts',
    'f5tts_synthesize',
    'custom_tts_synthesize',
    'example_custom_processor',
]

# 适配器映射字典，便于工厂模式使用
ADAPTER_REGISTRY = {
    'edge_tts': EdgeTTSAdapter,
    'openai_tts': OpenAITTSAdapter,
    'azure_tts': AzureTTSAdapter,
    'fish_tts': FishTTSAdapter,
    'sf_fish_tts': SFishTTSAdapter,
    'gpt_sovits': GPTSoVITSAdapter,
    'sf_cosyvoice2': SFCosyVoice2Adapter,
    'f5tts': F5TTSAdapter,
    'custom_tts': CustomTTSAdapter,
}

# 便捷函数映射
CONVENIENCE_FUNCTIONS = {
    'edge_tts': edge_tts,
    'openai_tts': openai_tts,
    'azure_tts': azure_tts,
    'fish_tts': fish_tts,
    'sf_fish_tts': siliconflow_fish_tts,
    'gpt_sovits': gpt_sovits_tts,
    'sf_cosyvoice2': sf_cosyvoice2_tts,
    'f5tts': f5tts_synthesize,
    'custom_tts': custom_tts_synthesize,
}


def get_adapter_class(engine_name: str):
    """根据引擎名称获取适配器类"""
    return ADAPTER_REGISTRY.get(engine_name)


def get_convenience_function(engine_name: str):
    """根据引擎名称获取便捷函数"""
    return CONVENIENCE_FUNCTIONS.get(engine_name)


def list_available_engines():
    """列出所有可用的TTS引擎"""
    return list(ADAPTER_REGISTRY.keys())


def create_adapter(engine_name: str, config: dict = None):
    """创建TTS适配器实例"""
    adapter_class = get_adapter_class(engine_name)
    if adapter_class is None:
        raise ValueError(f"不支持的TTS引擎: {engine_name}")
    
    return adapter_class(config) 