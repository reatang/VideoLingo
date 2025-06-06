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
    'AudioProcessor'
]

__version__ = '1.0.0' 