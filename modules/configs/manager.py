"""
# ----------------------------------------------------------------------------
# 配置管理器核心类
# 
# 基于项目实际的config.yaml文件结构设计的配置管理器
# 支持线程安全的配置读写、验证和类型转换
# ----------------------------------------------------------------------------
"""

import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from ruamel.yaml import YAML


class ConfigManager:
    """线程安全的配置管理器"""
    
    def __init__(self, config_path: str = 'config.yaml'):
        """
        初始化配置管理器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = Path(config_path)
        self._lock = threading.Lock()
        self._cache = {}
        self._cache_valid = False
        
        # 初始化YAML解析器
        self.yaml = YAML()
        self.yaml.preserve_quotes = True
        self.yaml.width = 4096  # 避免长行自动换行
        
        # 验证配置文件
        self._validate_config_file()
    
    def _validate_config_file(self) -> None:
        """验证配置文件是否存在和有效"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"❌ 配置文件不存在: {self.config_path}")
        
        try:
            # 尝试加载配置文件以验证YAML格式
            with open(self.config_path, 'r', encoding='utf-8') as file:
                data = self.yaml.load(file)
            if not isinstance(data, dict):
                raise ValueError("配置文件根节点必须是字典")
        except Exception as e:
            raise ValueError(f"❌ 配置文件格式错误: {str(e)}")
    
    def _load_config(self, force_reload: bool = False) -> Dict[str, Any]:
        """
        加载配置文件内容
        
        Args:
            force_reload: 是否强制重新加载
            
        Returns:
            配置字典
        """
        with self._lock:
            if force_reload or not self._cache_valid:
                try:
                    with open(self.config_path, 'r', encoding='utf-8') as file:
                        self._cache = self.yaml.load(file)
                    self._cache_valid = True
                except Exception as e:
                    raise RuntimeError(f"❌ 加载配置文件失败: {str(e)}")
            
            return self._cache.copy()
    
    def _save_config(self, data: Dict[str, Any]) -> None:
        """
        保存配置到文件
        
        Args:
            data: 要保存的配置数据
        """
        try:
            # 备份原文件
            backup_path = self.config_path.with_suffix('.yaml.backup')
            if self.config_path.exists():
                import shutil
                shutil.copy2(self.config_path, backup_path)
            
            # 保存新配置
            with open(self.config_path, 'w', encoding='utf-8') as file:
                self.yaml.dump(data, file)
            
            # 更新缓存
            self._cache = data.copy()
            self._cache_valid = True
            
        except Exception as e:
            # 如果保存失败，尝试恢复备份
            if backup_path.exists():
                import shutil
                shutil.copy2(backup_path, self.config_path)
            raise RuntimeError(f"❌ 保存配置文件失败: {str(e)}")
    
    def load_key(self, key: str, default: Any = None) -> Any:
        """
        加载指定键的值
        
        Args:
            key: 配置键，支持点分隔的嵌套键，如 'whisper.model'
            default: 默认值
            
        Returns:
            配置值
        """
        data = self._load_config()
        
        keys = key.split('.')
        value = data
        
        try:
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    if default is not None:
                        return default
                    raise KeyError(f"配置键 '{k}' 不存在于路径 '{key}' 中")
            return value
        except Exception as e:
            if default is not None:
                return default
            raise
    
    def update_key(self, key: str, new_value: Any) -> bool:
        """
        更新指定键的值
        
        Args:
            key: 配置键
            new_value: 新值
            
        Returns:
            是否更新成功
        """
        with self._lock:
            try:
                data = self._load_config()
                keys = key.split('.')
                
                # 导航到目标位置
                current = data
                for k in keys[:-1]:
                    if isinstance(current, dict) and k in current:
                        current = current[k]
                    else:
                        raise KeyError(f"配置路径 '{key}' 中的键 '{k}' 不存在")
                
                # 更新值
                if isinstance(current, dict) and keys[-1] in current:
                    old_value = current[keys[-1]]
                    current[keys[-1]] = new_value
                    
                    # 保存配置
                    self._save_config(data)
                    
                    print(f"✅ 配置更新成功: {key} = {old_value} -> {new_value}")
                    return True
                else:
                    raise KeyError(f"配置键 '{keys[-1]}' 不存在")
                    
            except Exception as e:
                print(f"❌ 更新配置失败: {str(e)}")
                return False
    
    def get_whisper_config(self) -> Dict[str, Any]:
        """获取Whisper相关配置"""
        return self.load_key('whisper', {})
    
    def get_api_config(self) -> Dict[str, Any]:
        """获取API相关配置"""
        return self.load_key('api', {})
    
    def get_tts_config(self, method: Optional[str] = None) -> Dict[str, Any]:
        """
        获取TTS相关配置
        
        Args:
            method: 指定TTS方法，如果为None则返回当前选择的方法配置
        """
        if method is None:
            method = self.load_key('tts_method', 'edge_tts')
        
        return self.load_key(method, {})
    
    def get_supported_languages(self) -> Dict[str, List[str]]:
        """获取支持的语言配置"""
        return {
            'with_space': self.load_key('language_split_with_space', []),
            'without_space': self.load_key('language_split_without_space', [])
        }
    
    def get_allowed_formats(self) -> Dict[str, List[str]]:
        """获取支持的文件格式"""
        return {
            'video': self.load_key('allowed_video_formats', []),
            'audio': self.load_key('allowed_audio_formats', [])
        }
    
    def validate_whisper_runtime(self, runtime: str) -> bool:
        """验证Whisper运行时设置是否有效"""
        valid_runtimes = ['local', 'cloud', 'elevenlabs']
        return runtime in valid_runtimes
    
    def validate_tts_method(self, method: str) -> bool:
        """验证TTS方法是否有效"""
        valid_methods = [
            'sf_fish_tts', 'openai_tts', 'gpt_sovits', 
            'azure_tts', 'fish_tts', 'edge_tts', 'custom_tts'
        ]
        return method in valid_methods
    
    def get_model_dir(self) -> Path:
        """获取模型目录路径"""
        model_dir = self.load_key('model_dir', './_model_cache')
        return Path(model_dir)
    
    def reload_config(self) -> None:
        """重新加载配置文件"""
        print("🔄 重新加载配置文件...")
        self._load_config(force_reload=True)
        print("✅ 配置文件重新加载完成")
    
    def get_config_summary(self) -> Dict[str, Any]:
        """获取配置摘要信息"""
        config = self._load_config()
        
        return {
            'display_language': config.get('display_language'),
            'target_language': config.get('target_language'),
            'whisper_runtime': config.get('whisper', {}).get('runtime'),
            'whisper_model': config.get('whisper', {}).get('model'),
            'tts_method': config.get('tts_method'),
            'demucs_enabled': config.get('demucs', False),
            'burn_subtitles': config.get('burn_subtitles', True),
            'api_model': config.get('api', {}).get('model'),
            'max_workers': config.get('max_workers', 4)
        }


# 全局配置管理器实例
_global_config_manager = None

def get_config_manager(config_path: str = 'config.yaml') -> ConfigManager:
    """
    获取配置管理器实例（单例模式）
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        配置管理器实例
    """
    global _global_config_manager
    if _global_config_manager is None:
        _global_config_manager = ConfigManager(config_path)
    return _global_config_manager 