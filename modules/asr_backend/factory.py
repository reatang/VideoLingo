"""
# ----------------------------------------------------------------------------
# ASR引擎工厂类
# 
# 使用工厂模式创建和管理不同的ASR引擎实例
# 支持引擎注册、自动发现、配置管理等功能
# 集成项目配置管理系统
# ----------------------------------------------------------------------------
"""

import time
from typing import Dict, List, Optional, Any, Type

from .base import ASREngineBase, ASRConfig
from .adapters import WhisperXLocalAdapter, WhisperX302Adapter, ElevenLabsAdapter
from .utils import get_asr_config

class ASREngineFactory:
    """ASR引擎工厂类 - 负责创建和管理ASR引擎实例"""

    _config : Optional[ASRConfig]
    
    def __init__(self, output_dir: str, config=None):
        """
        初始化工厂
        
        Args:
            config_manager: 配置管理器实例，如果为None则尝试导入全局配置
        """
        self._engines: Dict[str, Type[ASREngineBase]] = {}
        self._instances: Dict[str, ASREngineBase] = {}
        self._output_dir = output_dir
        if config is None:
            self._config = get_asr_config()
        else:
            self._config = config
        
        # 注册默认引擎
        self._register_default_engines()
    
    def _register_default_engines(self) -> None:
        """注册默认的ASR引擎"""
        self.register_engine('local', WhisperXLocalAdapter)
        self.register_engine('whisperx_local', WhisperXLocalAdapter)
        self.register_engine('cloud', WhisperX302Adapter)
        self.register_engine('whisperx_302', WhisperX302Adapter)
        self.register_engine('elevenlabs', ElevenLabsAdapter)
    
    def register_engine(self, name: str, engine_class: Type[ASREngineBase]) -> None:
        """
        注册ASR引擎
        
        Args:
            name: 引擎名称
            engine_class: 引擎类
        """
        if not issubclass(engine_class, ASREngineBase):
            raise ValueError(f"❌ 引擎类必须继承自ASREngineBase: {engine_class}")
        
        self._engines[name] = engine_class
        print(f"✅ 已注册ASR引擎: {name} -> {engine_class.__name__}")
    
    def create_engine(self, 
                     engine_type: str, 
                     config: Optional[Dict[str, Any]] = None,
                     singleton: bool = True) -> ASREngineBase:
        """
        创建ASR引擎实例
        
        Args:
            engine_type: 引擎类型 ('local', 'cloud', 'elevenlabs')
            config: 引擎配置，如果为None则从配置管理器获取
            singleton: 是否使用单例模式
            
        Returns:
            ASR引擎实例
        """
        if engine_type not in self._engines:
            available_engines = list(self._engines.keys())
            raise ValueError(f"❌ 不支持的引擎类型: {engine_type}, 可用引擎: {available_engines}")
        
        # 单例模式检查
        if singleton and engine_type in self._instances:
            print(f"🔄 使用现有{engine_type}引擎实例")
            return self._instances[engine_type]
        
        # 获取配置
        if config is None:
            config = self._get_engine_config(engine_type)
        
        # 创建新实例
        engine_class = self._engines[engine_type]
        try:
            engine_instance = engine_class(config)
            
            if singleton:
                self._instances[engine_type] = engine_instance
            
            print(f"✨ 创建{engine_type}引擎实例: {engine_class.__name__}")
            return engine_instance
            
        except Exception as e:
            print(f"❌ 创建{engine_type}引擎失败: {str(e)}")
            raise
    
    def _get_engine_config(self, engine_type: str) -> Dict[str, Any]:
        """
        从配置管理器获取引擎配置
        
        Args:
            engine_type: 引擎类型
            
        Returns:
            引擎配置字典
        """
        
        try:
            # 根据引擎类型返回相应配置
            if engine_type in ['local', 'whisperx_local']:
                return {
                    'language': self._config.language,
                    'model_name': self._config.model,
                    'model_dir': self._config.model_dir,
                }
            
            elif engine_type in ['cloud', 'whisperx_302']:
                return {
                    'api_key': self._config.whisperX_302_api_key,
                    'language': self._config.language,
                    'cache_dir': self._output_dir
                }
            
            elif engine_type == 'elevenlabs':
                return {
                    'api_key': self._config.elevenlabs_api_key,
                    'language': self._config.language,
                    'cache_dir': self._output_dir
                }
            
            else:
                return {}
                
        except Exception as e:
            print(f"⚠️  获取{engine_type}引擎配置失败: {str(e)}")
            return {}
    
    def get_available_engines(self) -> List[str]:
        """获取可用的引擎列表"""
        available = []
        for name, engine_class in self._engines.items():
            try:
                # 获取引擎配置
                config = self._get_engine_config(name)
                
                # 创建临时实例测试可用性
                temp_instance = engine_class(config)
                if temp_instance.is_available():
                    available.append(name)
                temp_instance.cleanup()
            except Exception:
                continue
        return available
    
    def get_engine_info(self, engine_type: str) -> Dict[str, Any]:
        """获取引擎信息"""
        if engine_type not in self._engines:
            raise ValueError(f"❌ 不支持的引擎类型: {engine_type}")
        
        engine_class = self._engines[engine_type]
        
        try:
            config = self._get_engine_config(engine_type)
            temp_instance = engine_class(config)
            info = temp_instance.get_engine_info()
            temp_instance.cleanup()
            return info
        except Exception as e:
            return {
                'name': engine_class.__name__,
                'error': str(e),
                'is_available': False
            }
    
    def cleanup_all(self) -> None:
        """清理所有引擎实例"""
        for name, instance in self._instances.items():
            try:
                instance.cleanup()
                print(f"🧹 已清理{name}引擎实例")
            except Exception as e:
                print(f"⚠️  清理{name}引擎失败: {str(e)}")
        
        self._instances.clear()
        print("✅ 所有引擎实例已清理")
    
    def get_registered_engines(self) -> Dict[str, str]:
        """获取已注册的引擎列表"""
        return {name: cls.__name__ for name, cls in self._engines.items()}
    
    def auto_select_engine(self, preferred_order: Optional[List[str]] = None) -> str:
        """
        自动选择可用的引擎
        
        Args:
            preferred_order: 优先级顺序列表
            
        Returns:
            选择的引擎名称
        """
        if preferred_order is None:
            if self._config:
                try:
                    # 根据配置的运行时确定优先级
                    if self._config.runtime == 'local':
                        preferred_order = ['local', 'cloud', 'elevenlabs']
                    elif self._config.runtime == 'cloud':
                        preferred_order = ['cloud', 'local', 'elevenlabs']
                    elif self._config.runtime == 'elevenlabs':
                        preferred_order = ['elevenlabs', 'local', 'cloud']
                    else:
                        preferred_order = ['local', 'cloud', 'elevenlabs']
                except Exception:
                    preferred_order = ['local', 'cloud', 'elevenlabs']
            else:
                preferred_order = ['local', 'cloud', 'elevenlabs']
        
        available_engines = self.get_available_engines()
        
        # 按优先级选择
        for engine in preferred_order:
            if engine in available_engines:
                print(f"🎯 自动选择引擎: {engine}")
                return engine
        
        # 如果没有优先级匹配，选择第一个可用的
        if available_engines:
            selected = available_engines[0]
            print(f"🎲 选择第一个可用引擎: {selected}")
            return selected
        
        raise RuntimeError("❌ 没有可用的ASR引擎")


# ----------------------------------------------------------------------------
# 全局工厂实例和便捷函数
# ----------------------------------------------------------------------------

# 全局工厂实例
_global_factory = None

def get_asr_factory() -> ASREngineFactory:
    """获取全局ASR工厂实例"""
    global _global_factory
    if _global_factory is None:
        _global_factory = ASREngineFactory(output_dir='output/log')
    return _global_factory


def create_asr_engine(engine_type: str, 
                     config: Optional[Dict[str, Any]] = None,
                     singleton: bool = True) -> ASREngineBase:
    """
    便捷函数 - 创建ASR引擎实例
    
    Args:
        engine_type: 引擎类型
        config: 引擎配置
        singleton: 是否使用单例模式
        
    Returns:
        ASR引擎实例
    """
    return get_asr_factory().create_engine(engine_type, config, singleton)


def get_available_engines() -> List[str]:
    """便捷函数 - 获取可用引擎列表"""
    return get_asr_factory().get_available_engines()


def auto_select_engine(preferred_order: Optional[List[str]] = None) -> str:
    """便捷函数 - 自动选择引擎"""
    return get_asr_factory().auto_select_engine(preferred_order)


def cleanup_all_engines() -> None:
    """便捷函数 - 清理所有引擎"""
    get_asr_factory().cleanup_all()


def register_custom_engine(name: str, engine_class: Type[ASREngineBase]) -> None:
    """便捷函数 - 注册自定义引擎"""
    get_asr_factory().register_engine(name, engine_class)



def get_engine_status_report() -> Dict[str, Any]:
    """获取引擎状态报告"""
    report = {
        'timestamp': time.time(),
        'registered_engines': get_asr_factory().get_registered_engines(),
        'available_engines': get_asr_factory().get_available_engines(),
        'engine_details': {}
    }
    
    for engine_name in report['registered_engines']:
        try:
            info = get_asr_factory().get_engine_info(engine_name)
            report['engine_details'][engine_name] = info
        except Exception as e:
            report['engine_details'][engine_name] = {'error': str(e)}
    
    return report


if __name__ == "__main__":
    # 测试工厂功能
    print("🧪 测试ASR引擎工厂...")
    
    # 获取状态报告
    report = get_engine_status_report()
    print("\n📊 引擎状态报告:")
    for engine, status in report['engine_details'].items():
        print(f"  {engine}: {'✅ 可用' if status.get('is_available', False) else '❌ 不可用'}")
    
    print("\n✅ 工厂测试完成") 