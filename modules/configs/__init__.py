"""
# ----------------------------------------------------------------------------
# 配置管理模块
# 
# 提供线程安全的配置文件管理功能：
# 1. YAML配置文件的读取和写入
# 2. 键值对的安全访问和更新
# 3. 配置验证和类型转换
# 4. 多环境配置支持
# 5. 配置热重载功能
# ----------------------------------------------------------------------------
"""

from .manager import ConfigManager, get_config_manager
from .utils import get_joiner, validate_language_code, get_default_config
from .models import ASRConfig, AudioConfig, TranslationConfig

# 导出主要API
__all__ = [
    'ConfigManager',
    'get_config_manager',
    'load_key',
    'update_key', 
    'get_joiner',
    'validate_language_code',
    'get_default_config',
    'ASRConfig',
    'AudioConfig', 
    'TranslationConfig'
]

# 全局配置管理器实例
_global_config = None

def get_global_config() -> ConfigManager:
    """获取全局配置管理器实例"""
    global _global_config
    if _global_config is None:
        _global_config = ConfigManager()
    return _global_config

# 便捷函数 - 保持与原有代码的兼容性
def load_key(key: str):
    """加载配置键值"""
    return get_global_config().load_key(key)

def update_key(key: str, new_value):
    """更新配置键值"""
    return get_global_config().update_key(key, new_value)

__version__ = '1.0.0' 