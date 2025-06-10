"""
# ----------------------------------------------------------------------------
# Download Backend 基础模块
# 
# 定义下载引擎的抽象基类和相关数据结构
# 提供统一的下载接口规范
# ----------------------------------------------------------------------------
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path
import time

from ..commons.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class VideoInfo:
    """视频信息数据结构"""
    title: str
    description: str = ""
    duration: float = 0.0  # 视频时长(秒)
    uploader: str = ""
    upload_date: str = ""
    view_count: int = 0
    thumbnail_url: str = ""
    formats: List[Dict] = field(default_factory=list)  # 可用格式列表
    tags: List[str] = field(default_factory=list)
    
    # 平台特定信息
    platform: str = ""
    video_id: str = ""
    url: str = ""
    
    def get_best_format(self, max_height: int = 1080) -> Optional[Dict]:
        """获取最佳格式"""
        if not self.formats:
            return None
            
        # 过滤出符合要求的格式
        suitable_formats = [
            fmt for fmt in self.formats 
            if fmt.get('height', 0) <= max_height and fmt.get('vcodec') != 'none'
        ]
        
        if not suitable_formats:
            return self.formats[0] if self.formats else None
            
        # 按分辨率排序，选择最高的
        return max(suitable_formats, key=lambda x: x.get('height', 0))


@dataclass 
class DownloadResult:
    """下载结果数据结构"""
    success: bool
    video_path: str = ""
    thumbnail_path: str = ""
    video_info: Optional[VideoInfo] = None
    download_time: float = 0.0
    file_size: int = 0
    error_message: str = ""
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_success(self) -> bool:
        """是否下载成功"""
        return self.success and Path(self.video_path).exists()
    
    def get_video_filename(self) -> str:
        """获取视频文件名"""
        return Path(self.video_path).name if self.video_path else ""


@dataclass
class DownloadConfig:
    """下载配置"""
    save_path: str = "output"
    resolution: str = "1080"  # 最大分辨率
    format_preference: str = "mp4"  # 首选格式
    audio_quality: str = "best"
    download_thumbnail: bool = True
    cookies_path: str = ""
    proxy: str = ""
    
    # 高级选项
    extract_audio: bool = False
    audio_format: str = "mp3"
    subtitle_languages: List[str] = field(default_factory=list)
    write_description: bool = False
    write_info_json: bool = False
    
    # 网络配置
    retries: int = 3
    timeout: int = 60
    max_filesize: str = ""  # 例如: "100M", "1G"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        from dataclasses import asdict
        return asdict(self)


class DownloadEngineBase(ABC):
    """下载引擎抽象基类"""
    
    def __init__(self, name: str):
        self.name = name
        self.config: Optional[DownloadConfig] = None
        self.logger = setup_logger(f"{__name__}.{name}")
        self._initialized = False
        
    @property
    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized
    
    # ------------
    # 生命周期管理
    # ------------
    
    @abstractmethod
    def initialize(self) -> None:
        """
        初始化阶段 - 加载依赖、检查环境
        
        Raises:
            DownloadError: 初始化失败
        """
        pass
    
    def configure(self, config: Dict[str, Any]) -> None:
        """
        配置阶段 - 设置下载参数
        
        Args:
            config: 配置字典
        """
        self.config = DownloadConfig(**config)
        self.logger.info(f"配置下载引擎: {self.name}")
    
    @abstractmethod
    def download(self, url: str) -> DownloadResult:
        """
        运行阶段 - 执行下载
        
        Args:
            url: 视频URL
            
        Returns:
            DownloadResult: 下载结果
            
        Raises:
            DownloadError: 下载失败
        """
        pass
    
    # ------------
    # 核心功能接口  
    # ------------
    
    @abstractmethod
    def get_video_info(self, url: str) -> VideoInfo:
        """
        获取视频信息
        
        Args:
            url: 视频URL
            
        Returns:
            VideoInfo: 视频信息
            
        Raises:
            DownloadError: 获取信息失败
        """
        pass
    
    @abstractmethod
    def is_supported(self, url: str) -> bool:
        """
        检查URL是否被支持
        
        Args:
            url: 视频URL
            
        Returns:
            bool: 是否支持
        """
        pass
    
    @abstractmethod
    def get_supported_domains(self) -> List[str]:
        """
        获取支持的域名列表
        
        Returns:
            List[str]: 域名列表
        """
        pass
    
    # ------------
    # 辅助方法
    # ------------
    
    def _ensure_initialized(self) -> None:
        """确保引擎已初始化"""
        if not self.is_initialized:
            self.initialize()
    
    def _ensure_configured(self) -> None:
        """确保引擎已配置"""
        if self.config is None:
            self.configure({})  # 使用默认配置
    
    def _create_download_result(
        self, 
        success: bool = False,
        video_path: str = "",
        error_message: str = ""
    ) -> DownloadResult:
        """创建下载结果对象"""
        return DownloadResult(
            success=success,
            video_path=video_path,
            error_message=error_message,
            download_time=0.0
        )
    
    def __str__(self) -> str:
        return f"DownloadEngine({self.name})"
    
    def __repr__(self) -> str:
        return f"DownloadEngine(name='{self.name}', initialized={self.is_initialized})"


class DownloadEngineAdapter(DownloadEngineBase):
    """下载引擎适配器基类"""
    
    def __init__(self, name: str, platform: str):
        super().__init__(name)
        self.platform = platform
        
    def initialize(self) -> None:
        """默认初始化实现"""
        if self._initialized:
            return
            
        try:
            self._setup_dependencies()
            self._check_environment()
            self._initialized = True
            self.logger.info(f"下载引擎 {self.name} 初始化成功")
        except Exception as e:
            self.logger.error(f"下载引擎 {self.name} 初始化失败: {str(e)}")
            raise
    
    def _setup_dependencies(self) -> None:
        """设置依赖项 - 子类可重写"""
        pass
    
    def _check_environment(self) -> None:
        """检查环境 - 子类可重写"""
        pass
    
    def _build_download_options(self, url: str) -> Dict[str, Any]:
        """构建下载选项 - 子类可重写"""
        if not self.config:
            self.config = DownloadConfig()
            
        options = {
            'outtmpl': f'{self.config.save_path}/%(title)s.%(ext)s',
            'format': self._get_format_selector(),
            'noplaylist': True,
        }
        
        if self.config.download_thumbnail:
            options['writethumbnail'] = True
            options['postprocessors'] = [
                {'key': 'FFmpegThumbnailsConvertor', 'format': 'jpg'}
            ]
        
        if self.config.cookies_path:
            options['cookiefile'] = self.config.cookies_path
            
        if self.config.proxy:
            options['proxy'] = self.config.proxy
            
        return options
    
    def _get_format_selector(self) -> str:
        """获取格式选择器"""
        if not self.config:
            return 'best'
            
        if self.config.resolution == 'best':
            return 'bestvideo+bestaudio/best'
        else:
            height = self.config.resolution.rstrip('p')
            return f'bestvideo[height<={height}]+bestaudio/best[height<={height}]'
    
    def _sanitize_path(self, path: str) -> str:
        """清理文件路径"""
        from .utils import sanitize_filename
        return sanitize_filename(path) 