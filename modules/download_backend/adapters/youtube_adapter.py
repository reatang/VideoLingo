"""
# ----------------------------------------------------------------------------
# YouTube 下载适配器
# 
# 使用yt-dlp实现YouTube视频下载功能
# 支持单个视频、播放列表、频道等多种内容类型
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
from ...configs import load_key

logger = setup_logger(__name__)


class YoutubeAdapter(DownloadEngineAdapter):
    """YouTube下载适配器"""
    
    def __init__(self, platform: str = "youtube"):
        super().__init__("YouTubeDownloader", platform)
        self.ydl_class = None
        
    def _setup_dependencies(self) -> None:
        """设置yt-dlp依赖"""
        try:
            # 尝试更新yt-dlp
            self._update_ytdlp()
            
            # 导入YoutubeDL类
            from yt_dlp import YoutubeDL
            self.ydl_class = YoutubeDL
            
            logger.info("yt-dlp 依赖设置成功")
            
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
        """检查URL是否被YouTube适配器支持"""
        youtube_domains = [
            'youtube.com', 'youtu.be', 'www.youtube.com',
            'm.youtube.com', 'music.youtube.com'
        ]
        
        return any(domain in url.lower() for domain in youtube_domains)
    
    def get_supported_domains(self) -> List[str]:
        """获取支持的域名列表"""
        return [
            'youtube.com', 'youtu.be', 'www.youtube.com',
            'm.youtube.com', 'music.youtube.com'
        ]
    
    def get_video_info(self, url: str) -> VideoInfo:
        """获取YouTube视频信息"""
        self._ensure_initialized()
        
        try:
            # 配置yt-dlp选项 - 仅提取信息
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
            }
            
            # 添加cookies支持
            cookies_path = self._get_cookies_path()
            if cookies_path and os.path.exists(cookies_path):
                ydl_opts['cookiefile'] = cookies_path
            
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
            logger.error(f"获取YouTube视频信息失败: {str(e)}")
            raise DownloadError(f"获取视频信息失败: {str(e)}") from e
    
    def download(self, url: str) -> DownloadResult:
        """下载YouTube视频"""
        self._ensure_initialized()
        self._ensure_configured()
        
        start_time = time.time()
        
        try:
            # 构建下载选项
            ydl_opts = self._build_download_options(url)
            
            logger.info(f"开始下载YouTube视频: {url}")
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
                    'file_size_formatted': format_file_size(file_size)
                }
            )
            
            logger.info(f"YouTube视频下载成功: {cleaned_path}")
            logger.info(f"下载耗时: {download_time:.2f}秒, 文件大小: {format_file_size(file_size)}")
            
            return result
            
        except Exception as e:
            download_time = time.time() - start_time
            logger.error(f"YouTube视频下载失败: {str(e)}")
            
            return DownloadResult(
                success=False,
                error_message=str(e),
                download_time=download_time,
                metadata={'platform': self.platform, 'original_url': url}
            )
    
    def _build_download_options(self, url: str) -> Dict[str, Any]:
        """构建YouTube特定的下载选项"""
        # 使用基类方法获取基础选项
        options = super()._build_download_options(url)
        
        # YouTube特定优化
        options.update({
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': ['zh', 'zh-CN', 'en'],
            'ignoreerrors': True,
            'no_warnings': False,
        })
        
        # 添加cookies支持
        cookies_path = self._get_cookies_path()
        if cookies_path and os.path.exists(cookies_path):
            options['cookiefile'] = cookies_path
            logger.info(f"使用cookies文件: {cookies_path}")
        
        # 高质量下载配置
        if self.config and self.config.resolution:
            if self.config.resolution == 'best':
                options['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
            else:
                height = self.config.resolution.rstrip('p')
                options['format'] = f'bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/best[height<={height}][ext=mp4]/best'
        
        return options
    
    def _get_cookies_path(self) -> Optional[str]:
        """获取YouTube cookies文件路径"""
        try:
            return load_key("youtube.cookies_path")
        except:
            return None
    
    def _find_downloaded_video(self, downloaded_files: List[str]) -> Optional[str]:
        """从下载文件列表中找到视频文件"""
        video_extensions = ['.mp4', '.webm', '.mkv', '.avi', '.mov']
        
        for file_path in downloaded_files:
            if any(file_path.lower().endswith(ext) for ext in video_extensions):
                if os.path.exists(file_path):
                    return file_path
        
        # 如果没有找到，尝试在保存目录中搜索
        if self.config and self.config.save_path:
            try:
                from ..utils import find_video_files
                return find_video_files(self.config.save_path)
            except:
                pass
        
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
    
    def batch_download(self, urls: List[str]) -> List[DownloadResult]:
        """批量下载YouTube视频"""
        self._ensure_initialized()
        self._ensure_configured()
        
        results = []
        total = len(urls)
        
        logger.info(f"开始批量下载 {total} 个YouTube视频")
        
        for i, url in enumerate(urls, 1):
            logger.info(f"下载进度: {i}/{total}")
            
            try:
                result = self.download(url)
                results.append(result)
                
                if result.success:
                    logger.info(f"✓ [{i}/{total}] 下载成功: {result.get_video_filename()}")
                else:
                    logger.error(f"✗ [{i}/{total}] 下载失败: {result.error_message}")
                    
            except Exception as e:
                logger.error(f"✗ [{i}/{total}] 下载出错: {str(e)}")
                results.append(DownloadResult(
                    success=False,
                    error_message=str(e),
                    metadata={'platform': self.platform, 'original_url': url}
                ))
        
        successful = sum(1 for r in results if r.success)
        logger.info(f"批量下载完成: {successful}/{total} 成功")
        
        return results 