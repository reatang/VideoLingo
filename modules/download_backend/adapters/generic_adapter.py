"""
# ----------------------------------------------------------------------------
# 通用下载适配器
# 
# 使用yt-dlp作为后端，支持大部分视频网站的通用下载功能
# 作为其他专用适配器的回退选项
# ----------------------------------------------------------------------------
"""

import os
import sys
import time
import subprocess
from typing import Dict, List, Optional, Any
from pathlib import Path

from ..base import DownloadEngineAdapter, DownloadResult, VideoInfo
from ..utils import sanitize_filename, get_file_size, format_file_size
from ...commons.logger import setup_logger
from ..exceptions import DownloadError

logger = setup_logger(__name__)


class GenericAdapter(DownloadEngineAdapter):
    """通用下载适配器 - 支持大部分视频网站"""
    
    def __init__(self, platform: str = "generic"):
        super().__init__("GenericDownloader", platform)
        self.ydl_class = None
        
    def _setup_dependencies(self) -> None:
        """设置yt-dlp依赖"""
        try:
            # 尝试更新yt-dlp
            self._update_ytdlp()
            
            # 导入YoutubeDL类
            from yt_dlp import YoutubeDL
            self.ydl_class = YoutubeDL
            
            logger.info("通用下载器 yt-dlp 依赖设置成功")
            
        except ImportError as e:
            logger.error("yt-dlp 未安装或导入失败")
            raise DownloadError("需要安装 yt-dlp: pip install yt-dlp") from e
        except Exception as e:
            logger.warning(f"更新 yt-dlp 失败: {str(e)}")
            # 尝试直接导入
            try:
                from yt_dlp import YoutubeDL
                self.ydl_class = YoutubeDL
            except ImportError:
                raise DownloadError("yt-dlp 不可用") from e
    
    def _update_ytdlp(self) -> None:
        """更新yt-dlp到最新版本"""
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"
            ], capture_output=True, text=True)
            
            # 清除模块缓存以使用新版本
            if 'yt_dlp' in sys.modules:
                del sys.modules['yt_dlp']
                
            logger.info("yt-dlp 已更新到最新版本")
            
        except subprocess.CalledProcessError as e:
            logger.warning(f"更新yt-dlp失败: {e}")
        except Exception as e:
            logger.warning(f"更新过程中出现错误: {str(e)}")
    
    def _check_environment(self) -> None:
        """检查环境依赖"""
        if self.ydl_class is None:
            raise DownloadError("YoutubeDL类未正确初始化")
    
    def is_supported(self, url: str) -> bool:
        """通用适配器支持所有URL"""
        return True  # 通用适配器尝试支持所有URL
    
    def get_supported_domains(self) -> List[str]:
        """获取支持的域名列表"""
        return ["*"]  # 表示支持所有域名
    
    def get_video_info(self, url: str) -> VideoInfo:
        """获取视频信息"""
        self._ensure_initialized()
        
        try:
            # 配置yt-dlp选项 - 仅提取信息
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
            }
            
            with self.ydl_class(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if not info:
                    raise DownloadError(f"无法获取视频信息: {url}")
                
                # 转换为标准VideoInfo格式
                video_info = VideoInfo(
                    title=info.get('title', ''),
                    description=info.get('description', ''),
                    duration=info.get('duration', 0.0),
                    uploader=info.get('uploader', ''),
                    upload_date=info.get('upload_date', ''),
                    view_count=info.get('view_count', 0),
                    thumbnail_url=info.get('thumbnail', ''),
                    formats=info.get('formats', []),
                    tags=info.get('tags', []),
                    platform=self.platform,
                    video_id=info.get('id', ''),
                    url=url
                )
                
                logger.info(f"获取视频信息成功: {video_info.title}")
                return video_info
                
        except Exception as e:
            logger.error(f"获取视频信息失败: {str(e)}")
            raise DownloadError(f"获取视频信息失败: {str(e)}") from e
    
    def download(self, url: str) -> DownloadResult:
        """下载视频"""
        self._ensure_initialized()
        self._ensure_configured()
        
        start_time = time.time()
        
        try:
            # 构建下载选项
            ydl_opts = self._build_download_options(url)
            
            logger.info(f"开始通用下载: {url}")
            logger.debug(f"下载选项: {ydl_opts}")
            
            downloaded_files = []
            
            # 执行下载
            with self.ydl_class(ydl_opts) as ydl:
                # 钩子函数来跟踪下载的文件
                def download_hook(d):
                    if d['status'] == 'finished':
                        downloaded_files.append(d['filename'])
                        logger.info(f"文件下载完成: {d['filename']}")
                
                ydl.add_progress_hook(download_hook)
                ydl.download([url])
            
            # 查找下载的视频文件
            video_path = self._find_downloaded_video(downloaded_files)
            if not video_path:
                # 尝试在保存目录中查找
                if self.config and self.config.save_path:
                    try:
                        from ..utils import find_video_files
                        video_path = find_video_files(self.config.save_path)
                    except:
                        raise DownloadError("下载完成但无法找到视频文件")
                else:
                    raise DownloadError("下载完成但无法找到视频文件")
            
            # 清理文件名
            cleaned_path = self._clean_downloaded_filename(video_path)
            
            # 获取视频信息
            try:
                video_info = self.get_video_info(url)
            except Exception as e:
                logger.warning(f"获取视频信息失败: {str(e)}")
                video_info = None
            
            # 创建下载结果
            download_time = time.time() - start_time
            file_size = get_file_size(cleaned_path)
            
            result = DownloadResult(
                success=True,
                video_path=cleaned_path,
                thumbnail_path=self._find_thumbnail(cleaned_path),
                video_info=video_info,
                download_time=download_time,
                file_size=file_size,
                metadata={
                    'platform': self.platform,
                    'original_url': url,
                    'file_size_formatted': format_file_size(file_size),
                    'adapter': 'generic'
                }
            )
            
            logger.info(f"通用下载成功: {cleaned_path}")
            logger.info(f"下载耗时: {download_time:.2f}秒, 文件大小: {format_file_size(file_size)}")
            
            return result
            
        except Exception as e:
            download_time = time.time() - start_time
            logger.error(f"通用下载失败: {str(e)}")
            
            return DownloadResult(
                success=False,
                error_message=str(e),
                download_time=download_time,
                metadata={'platform': self.platform, 'original_url': url, 'adapter': 'generic'}
            )
    
    def _build_download_options(self, url: str) -> Dict[str, Any]:
        """构建通用下载选项"""
        # 使用基类方法获取基础选项
        options = super()._build_download_options(url)
        
        # 通用优化设置
        options.update({
            'ignoreerrors': True,  # 忽略错误继续下载
            'no_warnings': False,
            'extractaudio': False,  # 不单独提取音频
            'embed_subs': False,    # 不嵌入字幕
            'writesubtitles': False, # 不下载字幕文件
        })
        
        # 网络优化
        options.update({
            'socket_timeout': 30,
            'retries': 3,
        })
        
        # 如果配置了代理
        if self.config and self.config.proxy:
            options['proxy'] = self.config.proxy
        
        return options
    
    def _find_downloaded_video(self, downloaded_files: List[str]) -> Optional[str]:
        """从下载文件列表中找到视频文件"""
        video_extensions = ['.mp4', '.webm', '.mkv', '.avi', '.mov', '.flv', '.m4v']
        
        for file_path in downloaded_files:
            if any(file_path.lower().endswith(ext) for ext in video_extensions):
                if os.path.exists(file_path):
                    return file_path
        
        return None
    
    def _clean_downloaded_filename(self, file_path: str) -> str:
        """清理下载的文件名"""
        if not file_path or not os.path.exists(file_path):
            return file_path
        
        directory = os.path.dirname(file_path)
        filename = os.path.basename(file_path)
        name, ext = os.path.splitext(filename)
        
        # 清理文件名
        cleaned_name = sanitize_filename(name)
        
        if cleaned_name != name:
            new_path = os.path.join(directory, cleaned_name + ext)
            try:
                os.rename(file_path, new_path)
                logger.info(f"文件名已清理: {filename} -> {cleaned_name + ext}")
                return new_path
            except OSError as e:
                logger.warning(f"文件重命名失败: {str(e)}")
        
        return file_path
    
    def _find_thumbnail(self, video_path: str) -> str:
        """查找缩略图文件"""
        if not video_path:
            return ""
        
        video_dir = os.path.dirname(video_path)
        video_name = os.path.splitext(os.path.basename(video_path))[0]
        
        # 可能的缩略图文件扩展名
        thumbnail_extensions = ['.jpg', '.jpeg', '.png', '.webp']
        
        for ext in thumbnail_extensions:
            thumbnail_path = os.path.join(video_dir, video_name + ext)
            if os.path.exists(thumbnail_path):
                return thumbnail_path
        
        return ""
    
    def test_url_support(self, url: str) -> Dict[str, Any]:
        """测试URL支持情况"""
        self._ensure_initialized()
        
        try:
            # 尝试提取基本信息
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,  # 只提取基本信息
                'skip_download': True,
            }
            
            with self.ydl_class(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                return {
                    'supported': True,
                    'title': info.get('title', ''),
                    'extractor': info.get('extractor', ''),
                    'formats_count': len(info.get('formats', [])),
                    'duration': info.get('duration', 0)
                }
                
        except Exception as e:
            return {
                'supported': False,
                'error': str(e),
                'extractor': None
            } 