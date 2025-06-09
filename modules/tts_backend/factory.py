"""
# ----------------------------------------------------------------------------
# TTS引擎工厂类
# 
# 使用工厂模式创建和管理不同的TTS引擎实例
# 支持引擎注册、自动发现、配置管理等功能
# 集成项目配置管理系统，支持引擎生命周期管理
# ----------------------------------------------------------------------------
"""

import time
from typing import Dict, List, Optional, Any, Type
from .base import TTSEngineBase, TTSResult
from .config import get_tts_config, TTSBaseConfig


class TTSEngineFactory:
    """TTS引擎工厂类 - 负责创建和管理TTS引擎实例"""
    
    def __init__(self, config_manager=None):
        """
        初始化工厂
        
        Args:
            config_manager: 配置管理器实例，如果为None则尝试导入全局配置
        """
        self._engines: Dict[str, Type[TTSEngineBase]] = {}
        self._instances: Dict[str, TTSEngineBase] = {}
        self._config_manager = config_manager
        
        # 注册默认引擎
        self._register_default_engines()
    
    def _register_default_engines(self) -> None:
        """注册默认的TTS引擎"""
        try:
            # 动态导入适配器
            from .adapters import (
                EdgeTTSAdapter, OpenAITTSAdapter, AzureTTSAdapter,
                FishTTSAdapter, SFFishTTSAdapter, GPTSoVITSAdapter,
                SFCosyVoice2Adapter, F5TTSAdapter, CustomTTSAdapter
            )
            
            # 注册所有引擎
            self.register_engine('edge_tts', EdgeTTSAdapter)
            self.register_engine('openai_tts', OpenAITTSAdapter)
            self.register_engine('azure_tts', AzureTTSAdapter)
            self.register_engine('fish_tts', FishTTSAdapter)
            self.register_engine('sf_fish_tts', SFFishTTSAdapter)
            self.register_engine('gpt_sovits', GPTSoVITSAdapter)
            self.register_engine('sf_cosyvoice2', SFCosyVoice2Adapter)
            self.register_engine('f5tts', F5TTSAdapter)
            self.register_engine('custom_tts', CustomTTSAdapter)
            
        except ImportError as e:
            print(f"⚠️  部分TTS引擎不可用: {e}")
    
    def register_engine(self, name: str, engine_class: Type[TTSEngineBase]) -> None:
        """
        注册TTS引擎
        
        Args:
            name: 引擎名称
            engine_class: 引擎类
        """
        if not issubclass(engine_class, TTSEngineBase):
            raise ValueError(f"❌ 引擎类必须继承自TTSEngineBase: {engine_class}")
        
        self._engines[name] = engine_class
        print(f"✅ 已注册TTS引擎: {name} -> {engine_class.__name__}")
    
    def create_engine(self, 
                     engine_type: str, 
                     config: Optional[Dict[str, Any]] = None,
                     singleton: bool = True) -> TTSEngineBase:
        """
        创建TTS引擎实例
        
        Args:
            engine_type: 引擎类型
            config: 引擎配置，如果为None则从配置管理器获取
            singleton: 是否使用单例模式
            
        Returns:
            TTS引擎实例
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
            
            # 执行三阶段初始化
            engine_instance.initialize()      # 初始化期
            engine_instance.configure(config) # 配置期
            # 运行期在调用synthesize时执行
            
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
            tts_config = get_tts_config()
            config_obj = tts_config.get_engine_config(engine_type)
            
            # 将配置对象转换为字典
            from dataclasses import asdict
            return asdict(config_obj)
            
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
                print(f"⚠️  清理{name}引擎失败: {e}")
        
        self._instances.clear()
    
    def get_registered_engines(self) -> Dict[str, str]:
        """获取已注册的引擎列表"""
        return {name: cls.__name__ for name, cls in self._engines.items()}
    
    def auto_select_engine(self, preferred_order: Optional[List[str]] = None) -> str:
        """
        自动选择可用的TTS引擎
        
        Args:
            preferred_order: 优先选择顺序
            
        Returns:
            选择的引擎名称
        """
        if preferred_order is None:
            # 默认优先顺序：免费 -> 收费 -> 本地
            preferred_order = [
                'edge_tts',          # 免费，可靠
                'azure_tts',         # Azure 服务
                'openai_tts',        # OpenAI 服务
                'sf_fish_tts',       # SiliconFlow服务
                'fish_tts',          # Fish TTS服务
                'gpt_sovits',        # 本地模型
                'sf_cosyvoice2',     # CosyVoice服务
                'f5tts',             # F5-TTS服务
                'custom_tts'         # 自定义
            ]
        
        available_engines = self.get_available_engines()
        
        # 按照优先顺序选择
        for engine in preferred_order:
            if engine in available_engines:
                print(f"🎯 自动选择TTS引擎: {engine}")
                return engine
        
        # 如果没有配置的引擎可用，返回第一个可用的
        if available_engines:
            selected = available_engines[0]
            print(f"🎯 选择第一个可用TTS引擎: {selected}")
            return selected
        
        raise RuntimeError("❌ 没有可用的TTS引擎")


# 全局工厂实例
_global_factory = None


def get_tts_factory() -> TTSEngineFactory:
    """获取全局TTS工厂实例"""
    global _global_factory
    if _global_factory is None:
        _global_factory = TTSEngineFactory()
    return _global_factory


def create_tts_engine(engine_type: str, 
                     config: Optional[Dict[str, Any]] = None,
                     singleton: bool = True) -> TTSEngineBase:
    """
    创建TTS引擎实例（便捷函数）
    
    Args:
        engine_type: 引擎类型
        config: 引擎配置
        singleton: 是否使用单例模式
        
    Returns:
        TTS引擎实例
    """
    factory = get_tts_factory()
    return factory.create_engine(engine_type, config, singleton)


def get_available_engines() -> List[str]:
    """获取可用的TTS引擎列表（便捷函数）"""
    factory = get_tts_factory()
    return factory.get_available_engines()


def auto_select_engine(preferred_order: Optional[List[str]] = None) -> str:
    """自动选择TTS引擎（便捷函数）"""
    factory = get_tts_factory()
    return factory.auto_select_engine(preferred_order)


def cleanup_all_engines() -> None:
    """清理所有TTS引擎实例（便捷函数）"""
    factory = get_tts_factory()
    factory.cleanup_all()


def register_custom_engine(name: str, engine_class: Type[TTSEngineBase]) -> None:
    """
    注册自定义TTS引擎（便捷函数）
    
    Args:
        name: 引擎名称
        engine_class: 引擎类
    """
    factory = get_tts_factory()
    factory.register_engine(name, engine_class)


def synthesize_text_factory(engine_type: str, 
                          text: str, 
                          output_path: Optional[str] = None,
                          config: Optional[Dict[str, Any]] = None,
                          **kwargs) -> TTSResult:
    """
    使用指定引擎合成文本（便捷函数）
    
    Args:
        engine_type: TTS引擎类型
        text: 要合成的文本
        output_path: 输出音频文件路径
        config: 引擎配置
        **kwargs: 其他参数
        
    Returns:
        TTS合成结果
    """
    try:
        engine = create_tts_engine(engine_type, config)
        start_time = time.time()
        
        result = engine.synthesize(text, output_path, **kwargs)
        
        elapsed_time = time.time() - start_time
        print(f"⏱️  TTS合成完成，耗时: {elapsed_time:.2f}秒")
        
        return result
        
    except Exception as e:
        print(f"❌ TTS合成失败: {str(e)}")
        raise


def synthesize_batch_factory(engine_type: str, 
                           texts: List[str],
                           output_dir: Optional[str] = None,
                           config: Optional[Dict[str, Any]] = None,
                           **kwargs) -> TTSResult:
    """
    使用指定引擎批量合成文本（便捷函数）
    
    Args:
        engine_type: TTS引擎类型
        texts: 要合成的文本列表
        output_dir: 输出目录
        config: 引擎配置
        **kwargs: 其他参数
        
    Returns:
        TTS批量合成结果
    """
    try:
        engine = create_tts_engine(engine_type, config)
        start_time = time.time()
        
        result = engine.synthesize_batch(texts, output_dir, **kwargs)
        
        elapsed_time = time.time() - start_time
        print(f"⏱️  TTS批量合成完成，耗时: {elapsed_time:.2f}秒")
        
        return result
        
    except Exception as e:
        print(f"❌ TTS批量合成失败: {str(e)}")
        raise


def get_engine_status_report() -> Dict[str, Any]:
    """
    获取所有TTS引擎的状态报告
    
    Returns:
        引擎状态报告
    """
    factory = get_tts_factory()
    available_engines = factory.get_available_engines()
    registered_engines = factory.get_registered_engines()
    
    report = {
        'timestamp': time.time(),
        'total_registered': len(registered_engines),
        'total_available': len(available_engines),
        'registered_engines': registered_engines,
        'available_engines': available_engines,
        'engine_details': {}
    }
    
    # 获取每个引擎的详细信息
    for engine_name in registered_engines:
        try:
            info = factory.get_engine_info(engine_name)
            report['engine_details'][engine_name] = info
        except Exception as e:
            report['engine_details'][engine_name] = {
                'error': str(e),
                'is_available': False
            }
    
    return report


def get_best_engine_for_language(language: str = "zh-CN") -> str:
    """
    根据语言获取最佳TTS引擎
    
    Args:
        language: 目标语言
        
    Returns:
        推荐的引擎名称
    """
    # 根据语言的最佳引擎推荐
    language_engine_map = {
        'zh-CN': ['edge_tts', 'azure_tts', 'sf_fish_tts'],
        'zh': ['edge_tts', 'azure_tts', 'sf_fish_tts'],
        'en-US': ['openai_tts', 'edge_tts', 'azure_tts'],
        'en': ['openai_tts', 'edge_tts', 'azure_tts'],
        'ja': ['edge_tts', 'azure_tts'],
        'ko': ['edge_tts', 'azure_tts'],
    }
    
    preferred_engines = language_engine_map.get(language, ['edge_tts'])
    
    try:
        return auto_select_engine(preferred_engines)
    except RuntimeError:
        # 如果没有可用引擎，返回edge_tts作为默认值
        return 'edge_tts' 