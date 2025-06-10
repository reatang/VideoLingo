"""
# ----------------------------------------------------------------------------
# Download Backend 适配器模块
# 
# 包含各种平台的下载适配器实现
# 每个适配器负责特定平台的视频下载逻辑
# ----------------------------------------------------------------------------
"""

from .youtube_adapter import YoutubeAdapter
from .generic_adapter import GenericAdapter
from .bilibili_adapter import BilibiliAdapter

__all__ = [
    'YoutubeAdapter',
    'GenericAdapter',
    'BilibiliAdapter'
] 