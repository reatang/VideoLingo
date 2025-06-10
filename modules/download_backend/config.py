"""
# ----------------------------------------------------------------------------
# Download Backend 配置模型
# 
# 定义各种下载平台的配置数据结构
# 提供类型安全的配置访问和验证
# ----------------------------------------------------------------------------
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path


@dataclass
class BaseDownloadConfig:
    """下载配置基类"""
    save_path: str = "output"
    resolution: str = "1080"  # 最大分辨率
    format_preference: str = "mp4"  # 首选格式
    audio_quality: str = "best"
    download_thumbnail: bool = True
    proxy: str = ""
    
    # 网络配置
    retries: int = 3
    timeout: int = 60
    max_filesize: str = ""  # 例如: "100M", "1G"
    
    def validate(self) -> bool:
        """验证配置有效性"""
        return True


@dataclass
class YoutubeConfig(BaseDownloadConfig):
    """YouTube下载配置"""
    cookies_path: str = ""
    download_subtitles: bool = True
    subtitle_languages: List[str] = field(default_factory=lambda: ['zh', 'zh-CN', 'en'])
    write_description: bool = False
    write_info_json: bool = False
    extract_audio: bool = False
    audio_format: str = "mp3"
    
    def validate(self) -> bool:
        """验证YouTube配置"""
        if self.cookies_path and not Path(self.cookies_path).exists():
            return False
        return super().validate()


@dataclass
class BilibiliConfig(BaseDownloadConfig):
    """Bilibili下载配置"""
    sessdata: str = ""
    bili_jct: str = ""
    buvid3: str = ""
    ffmpeg_path: str = "ffmpeg"
    use_dash: bool = True  # 使用DASH流
    
    def validate(self) -> bool:
        """验证Bilibili配置"""
        # 检查认证信息
        if not (self.sessdata and self.bili_jct and self.buvid3):
            return False
        return super().validate()
    
    @property
    def has_credentials(self) -> bool:
        """是否有完整的认证信息"""
        return bool(self.sessdata and self.bili_jct and self.buvid3)


@dataclass
class TiktokConfig(BaseDownloadConfig):
    """TikTok下载配置"""
    watermark: bool = False  # 是否保留水印
    music_only: bool = False  # 仅下载音乐
    
    def validate(self) -> bool:
        return super().validate()


@dataclass
class TwitterConfig(BaseDownloadConfig):
    """Twitter下载配置"""
    bearer_token: str = ""
    include_replies: bool = False
    
    def validate(self) -> bool:
        return super().validate()


@dataclass
class InstagramConfig(BaseDownloadConfig):
    """Instagram下载配置"""
    username: str = ""
    password: str = ""
    session_file: str = ""
    
    def validate(self) -> bool:
        return super().validate()


@dataclass
class VimeoConfig(BaseDownloadConfig):
    """Vimeo下载配置"""
    access_token: str = ""
    
    def validate(self) -> bool:
        return super().validate()


@dataclass
class GenericConfig(BaseDownloadConfig):
    """通用下载配置"""
    extractor_args: Dict[str, Any] = field(default_factory=dict)
    custom_headers: Dict[str, str] = field(default_factory=dict)
    
    def validate(self) -> bool:
        return super().validate()


@dataclass
class DownloadBackendConfig:
    """下载后端整体配置"""
    default_platform: str = "youtube"
    auto_detect_platform: bool = True
    preferred_quality: str = "1080"
    output_directory: str = "output"
    
    # 平台特定配置
    youtube: YoutubeConfig = field(default_factory=YoutubeConfig)
    bilibili: BilibiliConfig = field(default_factory=BilibiliConfig)
    tiktok: TiktokConfig = field(default_factory=TiktokConfig)
    twitter: TwitterConfig = field(default_factory=TwitterConfig)
    instagram: InstagramConfig = field(default_factory=InstagramConfig)
    vimeo: VimeoConfig = field(default_factory=VimeoConfig)
    generic: GenericConfig = field(default_factory=GenericConfig)
    
    def get_platform_config(self, platform: str) -> BaseDownloadConfig:
        """获取指定平台的配置"""
        config_map = {
            'youtube': self.youtube,
            'bilibili': self.bilibili,
            'tiktok': self.tiktok,
            'twitter': self.twitter,
            'instagram': self.instagram,
            'vimeo': self.vimeo,
            'generic': self.generic
        }
        
        return config_map.get(platform, self.generic)
    
    def validate_platform_config(self, platform: str) -> bool:
        """验证平台配置"""
        config = self.get_platform_config(platform)
        return config.validate() if config else False
    
    def list_available_platforms(self) -> List[str]:
        """列出所有可用平台"""
        return ['youtube', 'bilibili', 'tiktok', 'twitter', 'instagram', 'vimeo', 'generic']
    
    def get_config_status(self) -> Dict[str, Dict[str, Any]]:
        """获取所有平台的配置状态"""
        status = {}
        
        for platform in self.list_available_platforms():
            config = self.get_platform_config(platform)
            status[platform] = {
                'configured': config is not None,
                'valid': config.validate() if config else False,
                'config_class': config.__class__.__name__ if config else None
            }
            
            # 添加平台特定的状态信息
            if platform == 'bilibili' and isinstance(config, BilibiliConfig):
                status[platform]['has_credentials'] = config.has_credentials
            elif platform == 'youtube' and isinstance(config, YoutubeConfig):
                status[platform]['has_cookies'] = bool(config.cookies_path)
        
        return status
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DownloadBackendConfig':
        """从字典创建配置对象"""
        config = cls()
        
        # 基本配置
        config.default_platform = data.get('default_platform', config.default_platform)
        config.auto_detect_platform = data.get('auto_detect_platform', config.auto_detect_platform)
        config.preferred_quality = data.get('preferred_quality', config.preferred_quality)
        config.output_directory = data.get('output_directory', config.output_directory)
        
        # 平台配置
        platform_configs = {
            'youtube': YoutubeConfig,
            'bilibili': BilibiliConfig,
            'tiktok': TiktokConfig,
            'twitter': TwitterConfig,
            'instagram': InstagramConfig,
            'vimeo': VimeoConfig,
            'generic': GenericConfig
        }
        
        for platform, config_class in platform_configs.items():
            if platform in data:
                setattr(config, platform, config_class(**data[platform]))
        
        return config
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        from dataclasses import asdict
        
        result = {
            'default_platform': self.default_platform,
            'auto_detect_platform': self.auto_detect_platform,
            'preferred_quality': self.preferred_quality,
            'output_directory': self.output_directory
        }
        
        # 添加平台配置
        platforms = ['youtube', 'bilibili', 'tiktok', 'twitter', 'instagram', 'vimeo', 'generic']
        for platform in platforms:
            config = getattr(self, platform)
            result[platform] = asdict(config)
        
        return result 