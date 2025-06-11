# ----------------------------------------------------------------------------
# 视频下载后端模块
# 
# 现代化的视频下载系统，提供：
# 1. 类型安全的视频下载服务
# 2. 下载历史管理
# 3. 视频信息查询
# 4. 下载进度追踪
# 5. 多格式支持
# ----------------------------------------------------------------------------

from typing import Optional

from .downloader import VideoDownloader
from .manager import DownloadManager  
from .models import DownloadConfig, VideoInfo, DownloadResult
from .exceptions import DownloadError, VideoNotFoundError

OUTPUT_DIR = "output"

download_manager = DownloadManager(config=DownloadConfig(save_path=OUTPUT_DIR))

def download_video_ytdlp(url: str, resolution: Optional[str] = None) -> str:
    return download_manager.download_video(url, resolution=resolution)

def find_video_files() -> str:
    video_files = download_manager.find_downloaded_videos(limit=1)
    if len(video_files) == 0:
        return ""
    return str(video_files[0].file_path)

__all__ = [
    "VideoDownloader",
    "DownloadManager", 
    "DownloadConfig",
    "VideoInfo",
    "DownloadResult",
    "DownloadError",
    "VideoNotFoundError",
    "download_manager"
] 