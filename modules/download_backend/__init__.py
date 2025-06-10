"""
# ----------------------------------------------------------------------------
# Download Backend 模块
# 
# 提供多平台视频下载功能，支持YouTube、Bilibili等主流视频网站
# 使用适配器模式统一不同下载引擎的接口
# ----------------------------------------------------------------------------
"""

from typing import Optional, List, Dict, Any
from .factory import DownloadEngineFactory, get_available_engines
from .base import DownloadResult, VideoInfo
from .utils import detect_platform, sanitize_filename
from .exceptions import (
    DownloadBackendError,
    UnsupportedPlatformError,
    DownloadError
)
from ..commons.logger import setup_logger

logger = setup_logger(__name__)

# 模块级别的工厂实例
_factory = DownloadEngineFactory()

def download_video(
    url: str,
    save_path: str = 'output',
    resolution: str = '1080',
    platform: Optional[str] = None,
    **kwargs
) -> DownloadResult:
    """
    下载视频的便捷函数
    
    Args:
        url: 视频URL
        save_path: 保存路径
        resolution: 视频分辨率
        platform: 指定平台名称，如果不指定则自动检测
        **kwargs: 其他平台特定的参数
        
    Returns:
        DownloadResult: 下载结果信息
        
    Raises:
        UnsupportedPlatformError: 不支持的平台
        DownloadError: 下载失败
    """
    try:
        # 自动检测平台
        if platform is None:
            platform = detect_platform(url)
            
        logger.info(f"检测到平台: {platform}")
        logger.info(f"开始下载视频: {url}")
        
        # 创建下载引擎
        engine = _factory.create_engine(platform)
        
        # 配置下载参数
        config = {
            'save_path': save_path,
            'resolution': resolution,
            **kwargs
        }
        engine.configure(config)
        
        # 执行下载
        result = engine.download(url)
        
        logger.info(f"下载完成: {result.video_path}")
        return result
        
    except Exception as e:
        logger.error(f"下载失败: {str(e)}")
        raise DownloadError(f"下载视频失败: {str(e)}") from e

def get_video_info(url: str) -> VideoInfo:
    """
    获取视频信息
    
    Args:
        url: 视频URL
        
    Returns:
        VideoInfo: 视频信息
    """
    try:
        platform = detect_platform(url)
        engine = _factory.create_engine(platform)
        return engine.get_video_info(url)
    except Exception as e:
        logger.error(f"获取视频信息失败: {str(e)}")
        raise DownloadError(f"获取视频信息失败: {str(e)}") from e

def get_supported_platforms() -> List[str]:
    """获取支持的平台列表"""
    return get_available_engines()

def find_video_files(save_path: str = 'output') -> str:
    """
    查找下载的视频文件
    
    Args:
        save_path: 搜索路径
        
    Returns:
        str: 视频文件路径
        
    Raises:
        ValueError: 找不到唯一的视频文件
    """
    from ..utils import find_video_files as utils_find_video_files
    return utils_find_video_files(save_path)

# 向后兼容的函数
def download_video_ytdlp(url: str, save_path: str = 'output', resolution: str = '1080') -> None:
    """向后兼容的下载函数"""
    download_video(url, save_path, resolution)

__all__ = [
    'download_video',
    'get_video_info', 
    'get_supported_platforms',
    'find_video_files',
    'download_video_ytdlp',  # 向后兼容
    'DownloadResult',
    'VideoInfo',
    'DownloadEngineFactory'
] 