# ----------------------------------------------------------------------------
# 视频下载器 - 核心下载功能实现
# ----------------------------------------------------------------------------

import os
import sys
import re
import subprocess
import time
from pathlib import Path
from typing import Optional, Callable, Any
import logging

from .models import DownloadConfig, VideoInfo, DownloadResult, DownloadStatus, ResolutionType
from .exceptions import DownloadError, VideoNotFoundError, NetworkError, AuthenticationError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VideoDownloader:
    """现代化的视频下载器"""
    
    def __init__(self, config: DownloadConfig):
        """
        Initialize video downloader
        
        Args:
            config: Download configuration
        """
        self.config = config
        self._ensure_save_directory()
        self._yt_dlp_class = None
        
    def _ensure_save_directory(self) -> None:
        """Ensure save directory exists"""
        self.config.save_path.mkdir(parents=True, exist_ok=True)
        
    def _sanitize_filename(self, filename: str) -> str:
        """
        Clean filename from illegal characters
        
        Args:
            filename: Original filename
            
        Returns:
            Cleaned filename
        """
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        filename = filename.strip('. ')
        return filename if filename else 'video'
        
    def _update_ytdlp(self) -> Any:
        """
        Update yt-dlp to latest version and return YoutubeDL class
        
        Returns:
            YoutubeDL class
            
        Raises:
            DownloadError: If yt-dlp cannot be imported
        """
        if self._yt_dlp_class is not None:
            return self._yt_dlp_class
            
        try:
            logger.info("Updating yt-dlp...")
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Clear loaded modules
            if 'yt_dlp' in sys.modules:
                del sys.modules['yt_dlp']
                
            logger.info("yt-dlp updated successfully")
            
        except subprocess.CalledProcessError as e:
            logger.warning(f"Failed to update yt-dlp: {e}")
            logger.warning("Continuing with current version")
            
        try:
            from yt_dlp import YoutubeDL
            self._yt_dlp_class = YoutubeDL
            return YoutubeDL
        except ImportError:
            raise DownloadError("Cannot import yt-dlp. Please install: pip install yt-dlp")
    
    def get_video_info(self, url: str) -> VideoInfo:
        """
        Get video information without downloading
        
        Args:
            url: Video URL
            
        Returns:
            Video information
            
        Raises:
            VideoNotFoundError: If video is not found
            NetworkError: If network error occurs
        """
        try:
            YoutubeDL = self._update_ytdlp()
            
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
            }
            
            if self.config.cookies_path and self.config.cookies_path.exists():
                ydl_opts["cookiefile"] = str(self.config.cookies_path)
            
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
            # Extract available formats
            formats = []
            if 'formats' in info:
                for fmt in info['formats']:
                    if fmt.get('height'):
                        formats.append(f"{fmt['height']}p")
                formats = list(set(formats))  # Remove duplicates
                
            return VideoInfo(
                url=url,
                title=info.get('title', 'Unknown Title'),
                duration=info.get('duration', 0) or 0,
                uploader=info.get('uploader', 'Unknown Uploader'),
                view_count=info.get('view_count', 0) or 0,
                description=info.get('description', ''),
                thumbnail_url=info.get('thumbnail', ''),
                upload_date=info.get('upload_date', ''),
                format_available=formats
            )
            
        except Exception as e:
            error_msg = str(e).lower()
            if 'private' in error_msg or 'unavailable' in error_msg:
                raise VideoNotFoundError(f"Video not found or unavailable: {e}")
            elif 'network' in error_msg or 'timeout' in error_msg:
                raise NetworkError(f"Network error: {e}")
            else:
                raise DownloadError(f"Failed to get video info: {e}")
    
    def download_video(self, 
                      url: str, 
                      resolution: Optional[str] = None,
                      progress_callback: Optional[Callable[[float], None]] = None) -> DownloadResult:
        """
        Download video
        
        Args:
            url: Video URL
            resolution: Optional resolution override ('360', '480', '720', '1080', 'best')
            progress_callback: Optional progress callback function
            
        Returns:
            Download result
        """
        start_time = time.time()
        
        try:
            # Get video info first
            logger.info(f"Getting video info for: {url}")
            video_info = self.get_video_info(url)
            logger.info(f"Video title: {video_info.title}")
            
            # Configure download options
            ydl_opts = self._build_download_options(resolution, progress_callback)
            
            # Add cookies if available
            if self.config.cookies_path and self.config.cookies_path.exists():
                ydl_opts["cookiefile"] = str(self.config.cookies_path)
                logger.info("Using cookies file for authentication")
            
            # Execute download
            YoutubeDL = self._update_ytdlp()
            
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                
            # Find downloaded files
            file_path = self._find_downloaded_video()
            thumbnail_path = self._find_thumbnail(file_path)
            
            # Get file size
            file_size = file_path.stat().st_size if file_path.exists() else 0
            download_time = time.time() - start_time
            
            logger.info(f"Download completed: {file_path}")
            
            return DownloadResult(
                video_info=video_info,
                status=DownloadStatus.COMPLETED,
                file_path=file_path,
                thumbnail_path=thumbnail_path,
                file_size=file_size,
                download_time=download_time
            )
            
        except Exception as e:
            download_time = time.time() - start_time
            logger.error(f"Download failed: {e}")
            
            return DownloadResult(
                video_info=VideoInfo(url=url),
                status=DownloadStatus.FAILED,
                download_time=download_time,
                error_message=str(e)
            )
    
    def _build_download_options(self, 
                                  resolution: Optional[str],
                                  progress_callback: Optional[Callable[[float], None]]) -> dict:
        """
        Build yt-dlp download options
        
        Args:
            resolution: Optional resolution override
            progress_callback: Progress callback function
            
        Returns:
            Download options dict
        """
        format_selector = self._get_format_selector(resolution)
        
        ydl_opts = {
            'format': format_selector,
            'outtmpl': str(self.config.save_path / '%(title)s.%(ext)s'),
            'noplaylist': True,
            'writethumbnail': self.config.enable_thumbnail,
        }
        
        # Add thumbnail processor
        if self.config.enable_thumbnail:
            ydl_opts['postprocessors'] = [
                {'key': 'FFmpegThumbnailsConvertor', 'format': 'jpg'}
            ]
        
        # Add subtitle options
        if self.config.enable_subtitle:
            ydl_opts.update({
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': ['en', 'zh', 'zh-CN'],
            })
        
        # Add progress hook
        if progress_callback:
            ydl_opts['progress_hooks'] = [self._create_progress_hook(progress_callback)]
            
        return ydl_opts
    
    def _get_format_selector(self, resolution_override: Optional[str] = None) -> str:
        """
        Get format selector based on resolution
        
        Args:
            resolution_override: Optional resolution override
            
        Returns:
            Format selector string
        """
        # Use override resolution if provided, otherwise use config
        if resolution_override:
            if resolution_override == 'best':
                return 'bestvideo+bestaudio/best'
            else:
                return f'bestvideo[height<={resolution_override}]+bestaudio/best[height<={resolution_override}]'
        else:
            if self.config.resolution == ResolutionType.BEST:
                return 'bestvideo+bestaudio/best'
            else:
                resolution = self.config.resolution.value
                return f'bestvideo[height<={resolution}]+bestaudio/best[height<={resolution}]'
    
    def _create_progress_hook(self, callback: Callable[[float], None]) -> Callable:
        """
        Create progress hook for yt-dlp
        
        Args:
            callback: Progress callback function
            
        Returns:
            Progress hook function
        """
        def hook(d):
            if d['status'] == 'downloading':
                if 'total_bytes' in d and d['total_bytes']:
                    progress = d['downloaded_bytes'] / d['total_bytes']
                    callback(progress)
                elif 'total_bytes_estimate' in d and d['total_bytes_estimate']:
                    progress = d['downloaded_bytes'] / d['total_bytes_estimate']
                    callback(progress)
        
        return hook
    
    def _find_downloaded_video(self) -> Optional[Path]:
        """
        Find downloaded video file
        
        Returns:
            Path to video file
            
        Raises:
            DownloadError: If no video file found
        """
        video_files = []
        
        for file_path in self.config.save_path.iterdir():
            if file_path.is_file():
                ext = file_path.suffix[1:].lower()
                if ext in self.config.allowed_formats:
                    # Exclude duplicate output files
                    if not str(file_path).startswith(str(self.config.save_path / "output")):
                        video_files.append(file_path)
        
        if not video_files:
            raise DownloadError("No video files found after download")
        elif len(video_files) > 1:
            logger.warning(f"Multiple video files found: {video_files}")
            logger.warning(f"Using first file: {video_files[0]}")
            
        return video_files[0]
    
    def _find_thumbnail(self, video_path: Path) -> Optional[Path]:
        """
        Find thumbnail file for video
        
        Args:
            video_path: Path to video file
            
        Returns:
            Path to thumbnail file if found
        """
        if not self.config.enable_thumbnail:
            return None
            
        # Common thumbnail extensions
        thumbnail_exts = ['.jpg', '.jpeg', '.png', '.webp']
        base_name = video_path.stem
        
        for ext in thumbnail_exts:
            thumbnail_path = video_path.parent / f"{base_name}{ext}"
            if thumbnail_path.exists():
                return thumbnail_path
                
        return None 