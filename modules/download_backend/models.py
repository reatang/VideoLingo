# ----------------------------------------------------------------------------
# 数据模型定义
# ----------------------------------------------------------------------------

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from enum import Enum

class ResolutionType(Enum):
    """支持的分辨率类型"""
    BEST = "best"
    HIGH_1080P = "1080"
    HIGH_720P = "720"
    MEDIUM_480P = "480"
    LOW_360P = "360"

class DownloadStatus(Enum):
    """下载状态"""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class DownloadConfig:
    """下载配置"""
    resolution: ResolutionType = ResolutionType.HIGH_1080P
    save_path: Path = field(default_factory=lambda: Path("output"))
    allowed_formats: List[str] = field(default_factory=lambda: ["mp4", "avi", "mkv", "mov", "flv", "webm"])
    cookies_path: Optional[Path] = None
    enable_thumbnail: bool = True
    enable_subtitle: bool = False
    max_retries: int = 3
    timeout: int = 300  # seconds

    def __post_init__(self):
        if isinstance(self.save_path, str):
            self.save_path = Path(self.save_path)

@dataclass 
class VideoInfo:
    """视频信息"""
    url: str
    title: str = ""
    duration: int = 0  # seconds
    uploader: str = ""
    view_count: int = 0
    description: str = ""
    thumbnail_url: str = ""
    upload_date: Optional[str] = None
    format_available: List[str] = field(default_factory=list)
    
    @property
    def duration_formatted(self) -> str:
        """格式化的时长"""
        hours = self.duration // 3600
        minutes = (self.duration % 3600) // 60
        seconds = self.duration % 60
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"

@dataclass
class DownloadResult:
    """下载结果"""
    video_info: VideoInfo
    status: DownloadStatus
    file_path: Optional[Path] = None
    thumbnail_path: Optional[Path] = None
    file_size: int = 0  # bytes
    download_time: float = 0.0  # seconds
    error_message: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    
    @property
    def file_size_formatted(self) -> str:
        """格式化的文件大小"""
        if self.file_size == 0:
            return "0 B"
            
        units = ["B", "KB", "MB", "GB", "TB"]
        size = float(self.file_size)
        unit_index = 0
        
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
            
        return f"{size:.2f} {units[unit_index]}"

@dataclass
class DownloadHistory:
    """下载历史记录"""
    results: List[DownloadResult] = field(default_factory=list)
    total_downloads: int = 0
    successful_downloads: int = 0
    failed_downloads: int = 0
    total_size: int = 0  # bytes
    
    def add_result(self, result: DownloadResult) -> None:
        """添加下载结果"""
        self.results.append(result)
        self.total_downloads += 1
        
        if result.status == DownloadStatus.COMPLETED:
            self.successful_downloads += 1
            self.total_size += result.file_size
        elif result.status == DownloadStatus.FAILED:
            self.failed_downloads += 1
    
    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.total_downloads == 0:
            return 0.0
        return self.successful_downloads / self.total_downloads
    
    @property
    def total_size_formatted(self) -> str:
        """格式化的总大小"""
        if self.total_size == 0:
            return "0 B"
            
        units = ["B", "KB", "MB", "GB", "TB"]
        size = float(self.total_size)
        unit_index = 0
        
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
            
        return f"{size:.2f} {units[unit_index]}" 