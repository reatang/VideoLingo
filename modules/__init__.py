"""
# ----------------------------------------------------------------------------
# VideoLingo Modules Package
# 
# 包含项目的核心模块：
# - config: 配置管理模块
# - asr_backend: ASR引擎适配器模块
# - 其他业务模块...
# ----------------------------------------------------------------------------
"""

# 版本信息
__version__ = '1.0.0'

# 可选的便捷导入
try:
    from .config import load_key, update_key, get_joiner
    from .asr_backend import create_asr_engine, get_available_engines
    __all__ = [
        'load_key', 
        'update_key', 
        'get_joiner',
        'create_asr_engine',
        'get_available_engines'
    ]
except ImportError:
    # 如果依赖不满足，不影响包的导入
    __all__ = []
