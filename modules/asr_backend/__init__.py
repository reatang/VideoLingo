"""
# ----------------------------------------------------------------------------
# ASR Backend Module - 基于适配器模式的音频转录后端
# 
# 模块结构：
# - base.py: 抽象基类和接口定义
# - adapters/: 各种ASR引擎的适配器实现
# - factory.py: 工厂模式创建适配器实例
# - utils.py: 通用工具函数
# 
# 设计特点：
# 1. 统一的ASR接口，支持多种引擎
# 2. 适配器模式实现引擎解耦
# 3. 工厂模式简化实例创建
# 4. 保持与原有代码的兼容性
# ----------------------------------------------------------------------------
"""
from typing import Optional, Dict, Any
from .base import ASREngineBase, ASRResult, AudioSegment
from .factory import (
    ASREngineFactory, 
    create_asr_engine,
    get_available_engines,
    auto_select_engine,
    cleanup_all_engines,
    register_custom_engine
)
from .utils import AudioProcessor
from .audio_separator import AudioSeparator, separate_audio_file, demucs_audio


# ----------------------------------------------------------------------------
# 兼容性函数 - 保持与原有代码的兼容性
# ----------------------------------------------------------------------------

def transcribe_audio_factory(engine_type: str, 
                           raw_audio: str, 
                           vocal_audio: str, 
                           start: float, 
                           end: float,
                           config: Optional[Dict[str, Any]] = None) -> ASRResult:
    """
    兼容性函数 - 使用工厂模式进行转录
    
    Args:
        engine_type: 引擎类型
        raw_audio: 原始音频路径
        vocal_audio: 人声音频路径
        start: 开始时间
        end: 结束时间
        config: 引擎配置
        
    Returns:
        转录结果字典（兼容原格式）
    """
    try:
        # 创建引擎实例
        engine = create_asr_engine(engine_type, config)
        
        # 执行转录
        return engine.transcribe(raw_audio, vocal_audio, start, end)
    except Exception as e:
        print(f"❌ 工厂转录失败: {str(e)}")
        raise


__all__ = [
    'ASREngineBase',
    'ASRResult', 
    'AudioSegment',
    'ASREngineFactory',
    'create_asr_engine',
    'get_available_engines',
    'auto_select_engine', 
    'cleanup_all_engines',
    'register_custom_engine',
    'AudioProcessor',
    'AudioSeparator',

    'separate_audio_file',
    # alias for separate_audio_file
    'demucs_audio'
]

__version__ = '1.0.0' 