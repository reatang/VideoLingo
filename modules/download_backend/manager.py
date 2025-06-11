# ----------------------------------------------------------------------------
# 下载管理器 - 提供高级下载管理和查询功能
# ----------------------------------------------------------------------------

import json
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable
from datetime import datetime, timedelta
import logging

from .models import (
    DownloadConfig, VideoInfo, DownloadResult, DownloadHistory, 
    DownloadStatus, ResolutionType
)
from .downloader import VideoDownloader
from .exceptions import DownloadError

logger = logging.getLogger(__name__)

class DownloadManager:
    """下载管理器 - 统一管理所有下载操作和历史记录"""
    
    def __init__(self, 
                 config: DownloadConfig,
                 history_file: Optional[Path] = None):
        """
        Initialize download manager
        
        Args:
            config: Download configuration
            history_file: JSON file path for storing download history
        """
        self.config = config
        self.downloader = VideoDownloader(config)
        self.history_file = history_file or (config.save_path / "download_history.json")
        self.history = DownloadHistory()
        
        self._load_history()
    
    def _load_history(self) -> None:
        """Load download history from JSON file"""
        if not self.history_file.exists():
            return
            
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            for item in data:
                result = self._dict_to_download_result(item)
                self.history.add_result(result)
                
        except Exception as e:
            logger.error(f"Failed to load download history: {e}")
    
    def _dict_to_download_result(self, data: Dict[str, Any]) -> DownloadResult:
        """Convert dictionary to DownloadResult"""
        return DownloadResult(
            video_info=VideoInfo(
                url=data.get('url', ''),
                title=data.get('title', ''),
                duration=data.get('duration', 0),
                uploader=data.get('uploader', ''),
                view_count=data.get('view_count', 0),
                description=data.get('description', ''),
                thumbnail_url=data.get('thumbnail_url', ''),
                upload_date=data.get('upload_date'),
                format_available=data.get('format_available', [])
            ),
            status=DownloadStatus(data.get('status', 'completed')),
            file_path=Path(data['file_path']) if data.get('file_path') else None,
            thumbnail_path=Path(data['thumbnail_path']) if data.get('thumbnail_path') else None,
            file_size=data.get('file_size', 0),
            download_time=data.get('download_time', 0.0),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else datetime.now(),
            error_message=data.get('error_message', '')
        )
    
    def _save_history(self) -> None:
        """Save download history to JSON file"""
        try:
            # Ensure directory exists
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert results to dictionaries
            data = []
            for result in self.history.results:
                data.append({
                    'url': result.video_info.url,
                    'title': result.video_info.title,
                    'duration': result.video_info.duration,
                    'uploader': result.video_info.uploader,
                    'view_count': result.video_info.view_count,
                    'description': result.video_info.description,
                    'thumbnail_url': result.video_info.thumbnail_url,
                    'upload_date': result.video_info.upload_date,
                    'format_available': result.video_info.format_available,
                    'file_path': str(result.file_path) if result.file_path else None,
                    'thumbnail_path': str(result.thumbnail_path) if result.thumbnail_path else None,
                    'file_size': result.file_size,
                    'status': result.status.value,
                    'download_time': result.download_time,
                    'created_at': result.created_at.isoformat(),
                    'error_message': result.error_message
                })
            
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save download history: {e}")
    
    def download_video(self, 
                      url: str,
                      resolution: Optional[str] = None,
                      progress_callback: Optional[Callable[[float], None]] = None) -> DownloadResult:
        """
        Download video and save to history
        
        Args:
            url: Video URL
            resolution: Optional resolution override ('360', '480', '720', '1080', 'best')
            progress_callback: Optional progress callback
            
        Returns:
            Download result
        """
        logger.info(f"Starting download: {url}")
        
        # Check if already downloaded
        existing = self.find_downloaded_video_by_url(url)
        if existing and existing.status == DownloadStatus.COMPLETED:
            if existing.file_path and existing.file_path.exists():
                logger.info(f"Video already downloaded: {existing.file_path}")
                return existing
        
        # Download video
        result = self.downloader.download_video(url, resolution, progress_callback)
        
        # Save to history and JSON file
        self.history.add_result(result)
        self._save_history()
        
        return result
    
    def get_video_info(self, url: str) -> VideoInfo:
        """
        Get video information
        
        Args:
            url: Video URL
            
        Returns:
            Video information
        """
        return self.downloader.get_video_info(url)
    
    def find_downloaded_videos(self, 
                             title_filter: Optional[str] = None,
                             uploader_filter: Optional[str] = None,
                             status_filter: Optional[DownloadStatus] = None,
                             days_ago: Optional[int] = None,
                             limit: Optional[int] = None) -> List[DownloadResult]:
        """
        查询已下载的视频
        
        Args:
            title_filter: 按标题过滤（模糊匹配）
            uploader_filter: 按上传者过滤（模糊匹配）
            status_filter: 按状态过滤
            days_ago: 查询最近N天的下载
            limit: 限制返回数量
            
        Returns:
            符合条件的下载结果列表
        """
        try:
            results = list(self.history.results)
            
            # Apply filters
            if title_filter:
                results = [r for r in results 
                          if title_filter.lower() in r.video_info.title.lower()]
            
            if uploader_filter:
                results = [r for r in results 
                          if uploader_filter.lower() in r.video_info.uploader.lower()]
            
            if status_filter:
                results = [r for r in results if r.status == status_filter]
            
            if days_ago:
                cutoff_date = datetime.now() - timedelta(days=days_ago)
                results = [r for r in results if r.created_at >= cutoff_date]
            
            # Sort by created_at descending
            results.sort(key=lambda x: x.created_at, reverse=True)
            
            # Apply limit
            if limit:
                results = results[:limit]
                
            return results
            
        except Exception as e:
            logger.error(f"Failed to query downloaded videos: {e}")
            return []
    
    def find_downloaded_video_by_url(self, url: str) -> Optional[DownloadResult]:
        """
        根据URL查找已下载的视频
        
        Args:
            url: 视频URL
            
        Returns:
            下载结果，如果未找到则返回None
        """
        for result in self.history.results:
            if result.video_info.url == url:
                return result
        return None
    
    def get_download_statistics(self) -> Dict[str, Any]:
        """
        获取下载统计信息
        
        Returns:
            统计信息字典
        """
        try:
            results = self.history.results
            if not results:
                return {}
            
            # Basic stats
            total_downloads = len(results)
            successful_downloads = len([r for r in results if r.status == DownloadStatus.COMPLETED])
            failed_downloads = len([r for r in results if r.status == DownloadStatus.FAILED])
            total_size = sum(r.file_size for r in results if r.status == DownloadStatus.COMPLETED)
            
            # Recent downloads (last 7 days)
            seven_days_ago = datetime.now() - timedelta(days=7)
            recent_downloads = len([r for r in results 
                                  if r.created_at >= seven_days_ago and r.status == DownloadStatus.COMPLETED])
            
            # Top uploaders
            uploader_counts = {}
            for result in results:
                if result.status == DownloadStatus.COMPLETED and result.video_info.uploader:
                    uploader = result.video_info.uploader
                    uploader_counts[uploader] = uploader_counts.get(uploader, 0) + 1
            
            top_uploaders = [{"uploader": uploader, "count": count} 
                           for uploader, count in sorted(uploader_counts.items(), 
                                                       key=lambda x: x[1], reverse=True)[:5]]
            
            return {
                "total_downloads": total_downloads,
                "successful_downloads": successful_downloads,
                "failed_downloads": failed_downloads,
                "total_size_bytes": total_size,
                "success_rate": successful_downloads / total_downloads if total_downloads > 0 else 0,
                "recent_downloads_7days": recent_downloads,
                "top_uploaders": top_uploaders
            }
                
        except Exception as e:
            logger.error(f"Failed to get download statistics: {e}")
            return {}
    
    def cleanup_failed_downloads(self) -> int:
        """
        清理失败的下载记录
        
        Returns:
            清理的记录数量
        """
        try:
            original_count = len(self.history.results)
            
            # Filter out failed downloads
            self.history.results = [r for r in self.history.results if r.status != DownloadStatus.FAILED]
            
            # Update counters
            deleted_count = original_count - len(self.history.results)
            self.history.total_downloads = len(self.history.results)
            self.history.successful_downloads = len([r for r in self.history.results if r.status == DownloadStatus.COMPLETED])
            self.history.failed_downloads = 0  # Should be 0 after cleanup
            
            # Save updated history
            self._save_history()
            
            logger.info(f"Cleaned up {deleted_count} failed download records")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup failed downloads: {e}")
            return 0
    
    def export_download_history(self, file_path: Path) -> bool:
        """
        导出下载历史到JSON文件
        
        Args:
            file_path: 导出文件路径
            
        Returns:
            是否导出成功
        """
        try:
            export_data = []
            for result in self.history.results:
                export_data.append({
                    "url": result.video_info.url,
                    "title": result.video_info.title,
                    "duration": result.video_info.duration,
                    "uploader": result.video_info.uploader,
                    "view_count": result.video_info.view_count,
                    "description": result.video_info.description,
                    "thumbnail_url": result.video_info.thumbnail_url,
                    "upload_date": result.video_info.upload_date,
                    "format_available": result.video_info.format_available,
                    "file_path": str(result.file_path) if result.file_path else None,
                    "thumbnail_path": str(result.thumbnail_path) if result.thumbnail_path else None,
                    "file_size": result.file_size,
                    "status": result.status.value,
                    "download_time": result.download_time,
                    "created_at": result.created_at.isoformat(),
                    "error_message": result.error_message
                })
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Download history exported to: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export download history: {e}")
            return False
    
    def get_storage_usage(self) -> Dict[str, Any]:
        """
        获取存储使用情况
        
        Returns:
            存储使用情况信息
        """
        try:
            total_size = 0
            file_count = 0
            
            if self.config.save_path.exists():
                for file_path in self.config.save_path.rglob("*"):
                    if file_path.is_file():
                        file_count += 1
                        total_size += file_path.stat().st_size
            
            # Format size
            def format_size(size_bytes):
                if size_bytes == 0:
                    return "0 B"
                units = ["B", "KB", "MB", "GB", "TB"]
                size = float(size_bytes)
                unit_index = 0
                while size >= 1024 and unit_index < len(units) - 1:
                    size /= 1024
                    unit_index += 1
                return f"{size:.2f} {units[unit_index]}"
            
            return {
                "total_files": file_count,
                "total_size_bytes": total_size,
                "total_size_formatted": format_size(total_size),
                "save_path": str(self.config.save_path)
            }
            
        except Exception as e:
            logger.error(f"Failed to get storage usage: {e}")
            return {} 