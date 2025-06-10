"""
# ----------------------------------------------------------------------------
# Download Backend 工厂模块
# 
# 实现工厂模式来创建和管理下载引擎
# 根据平台自动选择合适的下载适配器
# ----------------------------------------------------------------------------
"""

import importlib
from typing import Dict, List, Optional, Type, Any
from threading import Lock

from .base import DownloadEngineBase, DownloadEngineAdapter
from .utils import detect_platform, get_platform_info
from ..commons.logger import setup_logger
from .exceptions import (
    UnsupportedPlatformError, 
    DownloadError,
    DependencyError
)

logger = setup_logger(__name__)


class DownloadEngineFactory:
    """下载引擎工厂类"""
    
    def __init__(self):
        self._engines: Dict[str, DownloadEngineBase] = {}
        self._engine_classes: Dict[str, Type[DownloadEngineBase]] = {}
        self._lock = Lock()
        self._auto_discovery = True
        
        # 注册内置适配器
        self._register_builtin_adapters()
    
    def _register_builtin_adapters(self) -> None:
        """注册内置适配器"""
        builtin_adapters = {
            'youtube': 'modules.download_backend.adapters.youtube_adapter',
            'bilibili': 'modules.download_backend.adapters.bilibili_adapter', 
            'tiktok': 'modules.download_backend.adapters.tiktok_adapter',
            'twitter': 'modules.download_backend.adapters.twitter_adapter',
            'instagram': 'modules.download_backend.adapters.instagram_adapter',
            'vimeo': 'modules.download_backend.adapters.vimeo_adapter',
            'generic': 'modules.download_backend.adapters.generic_adapter'
        }
        
        for platform, module_path in builtin_adapters.items():
            try:
                self._register_adapter_from_module(platform, module_path)
            except Exception as e:
                logger.debug(f"内置适配器 {platform} 注册失败: {str(e)}")
    
    def _register_adapter_from_module(self, platform: str, module_path: str) -> None:
        """从模块路径注册适配器"""
        try:
            module = importlib.import_module(module_path)
            
            # 查找适配器类 (通常以PlatformAdapter命名)
            adapter_class_name = f"{platform.title()}Adapter"
            if hasattr(module, adapter_class_name):
                adapter_class = getattr(module, adapter_class_name)
                self.register_engine(platform, adapter_class)
                logger.debug(f"成功注册适配器: {platform}")
            else:
                logger.warning(f"模块 {module_path} 中未找到 {adapter_class_name}")
                
        except ImportError as e:
            logger.debug(f"无法导入适配器模块 {module_path}: {str(e)}")
        except Exception as e:
            logger.error(f"注册适配器 {platform} 时出错: {str(e)}")
    
    def register_engine(self, platform: str, engine_class: Type[DownloadEngineBase]) -> None:
        """
        注册下载引擎类
        
        Args:
            platform: 平台名称
            engine_class: 引擎类
        """
        with self._lock:
            if not issubclass(engine_class, DownloadEngineBase):
                raise ValueError(f"引擎类必须继承自 DownloadEngineBase")
            
            self._engine_classes[platform] = engine_class
            logger.info(f"注册下载引擎: {platform} -> {engine_class.__name__}")
    
    def create_engine(self, platform: str) -> DownloadEngineBase:
        """
        创建下载引擎实例
        
        Args:
            platform: 平台名称
            
        Returns:
            DownloadEngineBase: 下载引擎实例
            
        Raises:
            UnsupportedPlatformError: 不支持的平台
        """
        with self._lock:
            # 检查是否有缓存的引擎实例
            if platform in self._engines:
                return self._engines[platform]
            
            # 检查是否有注册的引擎类
            if platform not in self._engine_classes:
                # 尝试自动发现和注册
                if self._auto_discovery:
                    self._try_auto_register(platform)
                
                # 如果还是没有，抛出异常
                if platform not in self._engine_classes:
                    available = list(self._engine_classes.keys())
                    raise UnsupportedPlatformError(
                        f"不支持的平台: {platform}。可用平台: {available}"
                    )
            
            # 创建引擎实例
            try:
                engine_class = self._engine_classes[platform]
                engine = engine_class(platform)
                
                # 缓存实例
                self._engines[platform] = engine
                
                logger.info(f"创建下载引擎: {platform}")
                return engine
                
            except Exception as e:
                logger.error(f"创建下载引擎失败 {platform}: {str(e)}")
                raise DownloadError(f"创建下载引擎失败: {str(e)}") from e
    
    def _try_auto_register(self, platform: str) -> None:
        """尝试自动注册平台适配器"""
        module_path = f"modules.download_backend.adapters.{platform}_adapter"
        try:
            self._register_adapter_from_module(platform, module_path)
        except Exception as e:
            logger.debug(f"自动注册 {platform} 适配器失败: {str(e)}")
    
    def get_engine(self, platform: str) -> Optional[DownloadEngineBase]:
        """
        获取已创建的引擎实例
        
        Args:
            platform: 平台名称
            
        Returns:
            Optional[DownloadEngineBase]: 引擎实例，如果不存在则返回None
        """
        return self._engines.get(platform)
    
    def is_platform_supported(self, platform: str) -> bool:
        """
        检查平台是否支持
        
        Args:
            platform: 平台名称
            
        Returns:
            bool: 是否支持
        """
        return platform in self._engine_classes
    
    def get_available_platforms(self) -> List[str]:
        """
        获取所有可用的平台列表
        
        Returns:
            List[str]: 平台名称列表
        """
        return list(self._engine_classes.keys())
    
    def get_engine_status(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有引擎的状态信息
        
        Returns:
            Dict: 引擎状态信息
        """
        status = {}
        
        for platform in self._engine_classes.keys():
            engine = self._engines.get(platform)
            platform_info = get_platform_info(platform)
            
            status[platform] = {
                'registered': True,
                'created': engine is not None,
                'initialized': engine.is_initialized if engine else False,
                'class_name': self._engine_classes[platform].__name__,
                'platform_info': platform_info
            }
        
        return status
    
    def auto_create_engine_for_url(self, url: str) -> DownloadEngineBase:
        """
        根据URL自动创建合适的下载引擎
        
        Args:
            url: 视频URL
            
        Returns:
            DownloadEngineBase: 下载引擎实例
            
        Raises:
            UnsupportedPlatformError: 不支持的平台
        """
        platform = detect_platform(url)
        return self.create_engine(platform)
    
    def clear_cache(self) -> None:
        """清除引擎实例缓存"""
        with self._lock:
            self._engines.clear()
            logger.info("清除引擎缓存")
    
    def shutdown(self) -> None:
        """关闭所有引擎"""
        with self._lock:
            for platform, engine in self._engines.items():
                try:
                    if hasattr(engine, 'shutdown'):
                        engine.shutdown()
                except Exception as e:
                    logger.warning(f"关闭引擎 {platform} 时出错: {str(e)}")
            
            self._engines.clear()
            logger.info("关闭所有下载引擎")
    
    def set_auto_discovery(self, enabled: bool) -> None:
        """设置是否启用自动发现"""
        self._auto_discovery = enabled
        logger.info(f"自动发现功能: {'启用' if enabled else '禁用'}")
    
    def __len__(self) -> int:
        """返回已注册的引擎数量"""
        return len(self._engine_classes)
    
    def __contains__(self, platform: str) -> bool:
        """检查平台是否已注册"""
        return platform in self._engine_classes
    
    def __str__(self) -> str:
        return f"DownloadEngineFactory(engines={len(self._engine_classes)})"
    
    def __repr__(self) -> str:
        platforms = list(self._engine_classes.keys())
        return f"DownloadEngineFactory(platforms={platforms})"


# 全局工厂实例
_global_factory = DownloadEngineFactory()

# 便捷函数
def create_download_engine(platform: str) -> DownloadEngineBase:
    """
    创建下载引擎的便捷函数
    
    Args:
        platform: 平台名称
        
    Returns:
        DownloadEngineBase: 下载引擎实例
    """
    return _global_factory.create_engine(platform)


def get_available_engines() -> List[str]:
    """
    获取可用引擎列表的便捷函数
    
    Returns:
        List[str]: 引擎名称列表
    """
    return _global_factory.get_available_platforms()


def auto_create_engine(url: str) -> DownloadEngineBase:
    """
    根据URL自动创建引擎的便捷函数
    
    Args:
        url: 视频URL
        
    Returns:
        DownloadEngineBase: 下载引擎实例
    """
    return _global_factory.auto_create_engine_for_url(url)


def register_custom_engine(platform: str, engine_class: Type[DownloadEngineBase]) -> None:
    """
    注册自定义引擎的便捷函数
    
    Args:
        platform: 平台名称
        engine_class: 引擎类
    """
    _global_factory.register_engine(platform, engine_class)


def get_engine_status() -> Dict[str, Dict[str, Any]]:
    """
    获取引擎状态的便捷函数
    
    Returns:
        Dict: 引擎状态信息
    """
    return _global_factory.get_engine_status()


def is_platform_supported(platform: str) -> bool:
    """
    检查平台支持的便捷函数
    
    Args:
        platform: 平台名称
        
    Returns:
        bool: 是否支持
    """
    return _global_factory.is_platform_supported(platform) 