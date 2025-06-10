"""
# ----------------------------------------------------------------------------
# Download Backend 工具函数
# 
# 提供下载相关的实用工具函数
# 包括URL解析、平台检测、文件处理等功能
# ----------------------------------------------------------------------------
"""

import re
import os
import sys
import glob
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse
from pathlib import Path

from ..commons.logger import setup_logger
from .exceptions import UnsupportedPlatformError, DownloadError

logger = setup_logger(__name__)

# 平台域名映射
PLATFORM_DOMAINS = {
    'youtube': [
        'youtube.com', 'youtu.be', 'www.youtube.com', 
        'm.youtube.com', 'music.youtube.com'
    ],
    'bilibili': [
        'bilibili.com', 'www.bilibili.com', 'b23.tv',
        'm.bilibili.com', 'space.bilibili.com'
    ],
    'tiktok': [
        'tiktok.com', 'www.tiktok.com', 'vm.tiktok.com',
        'm.tiktok.com'
    ],
    'twitter': [
        'twitter.com', 'www.twitter.com', 'x.com', 'www.x.com',
        'mobile.twitter.com', 't.co'
    ],
    'instagram': [
        'instagram.com', 'www.instagram.com', 'instagr.am'
    ],
    'vimeo': [
        'vimeo.com', 'www.vimeo.com', 'player.vimeo.com'
    ],
    'dailymotion': [
        'dailymotion.com', 'www.dailymotion.com', 'dai.ly'
    ],
    'facebook': [
        'facebook.com', 'www.facebook.com', 'fb.watch',
        'm.facebook.com'
    ],
    'weibo': [
        'weibo.com', 'www.weibo.com', 'm.weibo.com',
        'weibo.cn'
    ]
}

# URL模式匹配
URL_PATTERNS = {
    'youtube': [
        r'(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:www\.)?youtube\.com/playlist\?list=([a-zA-Z0-9_-]+)',
        r'(?:https?://)?(?:www\.)?youtube\.com/c/([a-zA-Z0-9_-]+)',
        r'(?:https?://)?(?:www\.)?youtube\.com/@([a-zA-Z0-9_-]+)'
    ],
    'bilibili': [
        r'(?:https?://)?(?:www\.)?bilibili\.com/video/([a-zA-Z0-9]+)',
        r'(?:https?://)?b23\.tv/([a-zA-Z0-9]+)',
        r'(?:https?://)?(?:www\.)?bilibili\.com/bangumi/play/([a-zA-Z0-9]+)'
    ],
    'tiktok': [
        r'(?:https?://)?(?:www\.)?tiktok\.com/@[^/]+/video/(\d+)',
        r'(?:https?://)?vm\.tiktok\.com/([a-zA-Z0-9]+)'
    ]
}


def detect_platform(url: str) -> str:
    """
    自动检测视频URL的平台
    
    Args:
        url: 视频URL
        
    Returns:
        str: 平台名称
        
    Raises:
        UnsupportedPlatformError: 不支持的平台
    """
    if not url:
        raise UnsupportedPlatformError("URL不能为空")
    
    # 标准化URL
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        # 移除www前缀进行匹配
        domain_clean = domain.replace('www.', '')
        
        # 按域名匹配
        for platform, domains in PLATFORM_DOMAINS.items():
            if any(d in domain for d in domains):
                logger.info(f"基于域名检测到平台: {platform} (域名: {domain})")
                return platform
        
        # 按URL模式匹配
        for platform, patterns in URL_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, url, re.IGNORECASE):
                    logger.info(f"基于URL模式检测到平台: {platform}")
                    return platform
        
        # 默认使用通用下载器
        logger.warning(f"未识别的域名 {domain}，使用通用下载器")
        return 'generic'
        
    except Exception as e:
        logger.error(f"URL解析失败: {str(e)}")
        raise UnsupportedPlatformError(f"无法解析URL: {url}") from e


def sanitize_filename(filename: str) -> str:
    """
    清理文件名，移除非法字符
    
    Args:
        filename: 原始文件名
        
    Returns:
        str: 清理后的文件名
    """
    if not filename:
        return 'video'
    
    # 移除或替换非法字符
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    
    # 移除控制字符
    filename = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', filename)
    
    # 确保文件名不以点或空格开始/结束
    filename = filename.strip('. ')
    
    # 限制长度
    if len(filename) > 200:
        filename = filename[:200]
    
    # 如果文件名为空，使用默认名称
    return filename if filename else 'video'


def extract_video_id(url: str, platform: str) -> Optional[str]:
    """
    从URL中提取视频ID
    
    Args:
        url: 视频URL
        platform: 平台名称
        
    Returns:
        Optional[str]: 视频ID
    """
    if platform not in URL_PATTERNS:
        return None
    
    for pattern in URL_PATTERNS[platform]:
        match = re.search(pattern, url, re.IGNORECASE)
        if match:
            return match.group(1)
    
    return None


def get_available_formats() -> List[str]:
    """获取支持的视频格式列表"""
    try:
        from ..configs import load_key
        return load_key("allowed_video_formats")
    except:
        return ['mp4', 'mov', 'avi', 'mkv', 'webm', 'flv']


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
    if not os.path.exists(save_path):
        raise ValueError(f"路径不存在: {save_path}")
    
    # 获取允许的视频格式
    allowed_formats = get_available_formats()
    
    # 搜索视频文件
    video_files = []
    for ext in allowed_formats:
        pattern = os.path.join(save_path, f"*.{ext}")
        video_files.extend(glob.glob(pattern))
    
    # Windows路径处理
    if sys.platform.startswith('win'):
        video_files = [file.replace("\\", "/") for file in video_files]
    
    # 过滤掉重复下载的文件
    video_files = [file for file in video_files if not file.startswith("output/output")]
    
    if len(video_files) == 0:
        raise ValueError(f"在 {save_path} 中未找到视频文件")
    elif len(video_files) > 1:
        logger.warning(f"找到多个视频文件: {video_files}")
        # 返回最新的文件
        return max(video_files, key=os.path.getmtime)
    
    return video_files[0]


def validate_url(url: str) -> bool:
    """
    验证URL格式
    
    Args:
        url: 待验证的URL
        
    Returns:
        bool: 是否有效
    """
    try:
        # 标准化URL
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        parsed = urlparse(url)
        return bool(parsed.netloc and parsed.scheme in ('http', 'https'))
    except:
        return False


def get_file_size(file_path: str) -> int:
    """
    获取文件大小
    
    Args:
        file_path: 文件路径
        
    Returns:
        int: 文件大小(字节)
    """
    try:
        return os.path.getsize(file_path)
    except OSError:
        return 0


def format_file_size(size_bytes: int) -> str:
    """
    格式化文件大小显示
    
    Args:
        size_bytes: 文件大小(字节)
        
    Returns:
        str: 格式化的大小字符串
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    size_index = 0
    size = float(size_bytes)
    
    while size >= 1024.0 and size_index < len(size_names) - 1:
        size /= 1024.0
        size_index += 1
    
    return f"{size:.1f} {size_names[size_index]}"


def create_safe_path(base_path: str, filename: str) -> str:
    """
    创建安全的文件路径
    
    Args:
        base_path: 基础路径
        filename: 文件名
        
    Returns:
        str: 安全的完整路径
    """
    # 清理文件名
    safe_filename = sanitize_filename(filename)
    
    # 确保基础路径存在
    os.makedirs(base_path, exist_ok=True)
    
    # 生成完整路径
    full_path = os.path.join(base_path, safe_filename)
    
    # 处理重名文件
    counter = 1
    original_path = full_path
    name, ext = os.path.splitext(safe_filename)
    
    while os.path.exists(full_path):
        new_filename = f"{name}_{counter}{ext}"
        full_path = os.path.join(base_path, new_filename)
        counter += 1
    
    return full_path


def get_platform_info(platform: str) -> Dict[str, any]:
    """
    获取平台信息
    
    Args:
        platform: 平台名称
        
    Returns:
        Dict: 平台信息
    """
    platform_info = {
        'youtube': {
            'name': 'YouTube',
            'description': 'Google旗下的视频分享平台',
            'supports_playlists': True,
            'supports_live': True,
            'max_quality': '8K',
            'requires_cookies': False
        },
        'bilibili': {
            'name': 'Bilibili',
            'description': '中国领先的弹幕视频分享平台',
            'supports_playlists': True,
            'supports_live': True,
            'max_quality': '4K',
            'requires_cookies': True
        },
        'tiktok': {
            'name': 'TikTok',
            'description': '短视频社交平台',
            'supports_playlists': False,
            'supports_live': False,
            'max_quality': '1080p',
            'requires_cookies': False
        },
        'generic': {
            'name': 'Generic',
            'description': '通用下载器，支持大部分视频网站',
            'supports_playlists': False,
            'supports_live': False,
            'max_quality': 'Variable',
            'requires_cookies': False
        }
    }
    
    return platform_info.get(platform, platform_info['generic']) 