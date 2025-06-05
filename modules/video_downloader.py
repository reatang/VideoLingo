"""
# ----------------------------------------------------------------------------
# 视频下载器模块 - 负责从YouTube等平台下载视频
# 
# 核心功能：
# 1. 下载指定URL的视频文件
# 2. 自动处理文件名清理和重命名
# 3. 支持多种分辨率选择
# 4. 支持Cookie认证
# 
# 输入：视频URL、保存路径、分辨率要求
# 输出：下载完成的视频文件路径
# ----------------------------------------------------------------------------
"""

import os
import sys
import glob
import re
import subprocess
from typing import Optional, List
from pathlib import Path


class VideoDownloader:
    """视频下载器类 - 封装视频下载的所有功能"""
    
    def __init__(self, 
                 save_path: str = 'output',
                 allowed_formats: Optional[List[str]] = None,
                 cookies_path: Optional[str] = None):
        """
        初始化视频下载器
        
        Args:
            save_path: 保存路径, 默认为 'output'
            allowed_formats: 允许的视频格式列表
            cookies_path: Cookie文件路径, 用于需要认证的视频
        """
        self.save_path = save_path
        self.allowed_formats = allowed_formats or ['mp4', 'avi', 'mkv', 'mov', 'flv', 'webm']
        self.cookies_path = cookies_path
        
        # 创建保存目录
        os.makedirs(save_path, exist_ok=True)
        
    def _sanitize_filename(self, filename: str) -> str:
        """
        清理文件名中的非法字符
        
        Args:
            filename: 原始文件名
            
        Returns:
            清理后的文件名
            
        Note: 修复原代码缺陷 - 增加了对空文件名的处理
        """
        # 移除或替换非法字符
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        # 确保文件名不以点或空格开始/结束
        filename = filename.strip('. ')
        # 如果文件名为空则使用默认名称
        return filename if filename else 'video'
    
    def _update_ytdlp(self):
        """
        更新yt-dlp到最新版本
        
        Returns:
            YoutubeDL类
            
        Note: 修复原代码缺陷 - 增加了更详细的错误处理
        """
        try:
            print("🔄 正在更新yt-dlp...")
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # 清理已加载的模块
            if 'yt_dlp' in sys.modules:
                del sys.modules['yt_dlp']
                
            print("✅ yt-dlp更新成功")
            
        except subprocess.CalledProcessError as e:
            print(f"⚠️  警告: yt-dlp更新失败: {e}")
            print("⚠️  将使用当前版本继续")
            
        try:
            from yt_dlp import YoutubeDL
            return YoutubeDL
        except ImportError:
            raise ImportError("❌ 无法导入yt-dlp, 请先安装: pip install yt-dlp")
    
    def download_video(self, 
                      url: str, 
                      resolution: str = '1080') -> str:
        """
        下载视频的主要方法
        
        Args:
            url: 视频URL
            resolution: 目标分辨率 ('360', '480', '720', '1080', 'best')
            
        Returns:
            下载完成的视频文件路径
            
        Raises:
            Exception: 下载失败时抛出异常
        """
        print(f"🎬 开始下载视频: {url}")
        print(f"📊 目标分辨率: {resolution}")
        
        # 配置下载选项
        ydl_opts = {
            'format': self._get_format_selector(resolution),
            'outtmpl': f'{self.save_path}/%(title)s.%(ext)s',
            'noplaylist': True,
            'writethumbnail': True,
            'postprocessors': [{'key': 'FFmpegThumbnailsConvertor', 'format': 'jpg'}],
        }
        
        # 添加Cookie文件（如果存在）
        if self.cookies_path and os.path.exists(self.cookies_path):
            ydl_opts["cookiefile"] = str(self.cookies_path)
            print("🍪 已加载Cookie文件")
        
        try:
            # 获取更新后的YoutubeDL类
            YoutubeDL = self._update_ytdlp()
            
            # 执行下载
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                
            # 清理和重命名文件
            self._cleanup_downloaded_files()
            
            # 查找并返回下载的视频文件
            video_file = self.find_video_file()
            print(f"✅ 视频下载完成: {video_file}")
            
            return video_file
            
        except Exception as e:
            print(f"❌ 视频下载失败: {str(e)}")
            raise
    
    def _get_format_selector(self, resolution: str) -> str:
        """
        根据分辨率要求生成格式选择器
        
        Args:
            resolution: 目标分辨率
            
        Returns:
            yt-dlp格式选择器字符串
        """
        if resolution == 'best':
            return 'bestvideo+bestaudio/best'
        else:
            return f'bestvideo[height<={resolution}]+bestaudio/best[height<={resolution}]'
    
    def _cleanup_downloaded_files(self) -> None:
        """
        清理下载后的文件名
        
        Note: 修复原代码缺陷 - 增加了异常处理
        """
        try:
            for file in os.listdir(self.save_path):
                file_path = os.path.join(self.save_path, file)
                if os.path.isfile(file_path):
                    filename, ext = os.path.splitext(file)
                    new_filename = self._sanitize_filename(filename)
                    if new_filename != filename:
                        new_path = os.path.join(self.save_path, new_filename + ext)
                        os.rename(file_path, new_path)
                        print(f"🔄 文件重命名: {file} -> {new_filename + ext}")
        except Exception as e:
            print(f"⚠️  文件清理时出现警告: {str(e)}")
    
    def find_video_file(self) -> str:
        """
        查找下载的视频文件
        
        Returns:
            视频文件路径
            
        Raises:
            ValueError: 当找不到唯一视频文件时
            
        Note: 修复原代码缺陷 - 改进了文件查找逻辑
        """
        video_files = []
        
        for file in glob.glob(f"{self.save_path}/*"):
            if os.path.isfile(file):
                ext = os.path.splitext(file)[1][1:].lower()
                if ext in self.allowed_formats:
                    # 排除重复输出的文件
                    if not file.startswith(f"{self.save_path}/output"):
                        video_files.append(file)
        
        # Windows路径修正
        if sys.platform.startswith('win'):
            video_files = [file.replace("\\", "/") for file in video_files]
        
        if len(video_files) == 0:
            raise ValueError("❌ 没有找到下载的视频文件")
        elif len(video_files) > 1:
            print(f"⚠️  找到多个视频文件: {video_files}")
            print(f"📍 使用第一个文件: {video_files[0]}")
            
        return video_files[0]
    
    def get_video_info(self, url: str) -> dict:
        """
        获取视频信息（不下载）
        
        Args:
            url: 视频URL
            
        Returns:
            视频信息字典
        """
        try:
            YoutubeDL = self._update_ytdlp()
            
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
            }
            
            if self.cookies_path and os.path.exists(self.cookies_path):
                ydl_opts["cookiefile"] = str(self.cookies_path)
            
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
            return {
                'title': info.get('title', '未知标题'),
                'duration': info.get('duration', 0),
                'uploader': info.get('uploader', '未知上传者'),
                'view_count': info.get('view_count', 0),
                'description': info.get('description', ''),
            }
            
        except Exception as e:
            print(f"❌ 获取视频信息失败: {str(e)}")
            return {}


# ----------------------------------------------------------------------------
# 独立运行测试
# ----------------------------------------------------------------------------
if __name__ == '__main__':
    # 创建下载器实例
    downloader = VideoDownloader(
        save_path='output',
        allowed_formats=['mp4', 'avi', 'mkv', 'mov', 'flv', 'webm']
    )
    
    # 测试URL输入
    test_url = input('请输入要下载的视频URL: ')
    if not test_url.strip():
        print("❌ URL不能为空")
        sys.exit(1)
    
    # 分辨率选择
    resolution = input('请输入期望的分辨率 (360/480/720/1080/best, 默认1080): ')
    resolution = resolution.strip() if resolution.strip() else '1080'
    
    try:
        # 先获取视频信息
        print("\n📋 正在获取视频信息...")
        info = downloader.get_video_info(test_url)
        if info:
            print(f"📺 标题: {info['title']}")
            print(f"⏱️  时长: {info['duration']}秒")
            print(f"👤 上传者: {info['uploader']}")
        
        # 开始下载
        print("\n🚀 开始下载...")
        video_path = downloader.download_video(test_url, resolution)
        print(f"\n🎉 下载完成！文件位置: {video_path}")
        
    except Exception as e:
        print(f"\n💥 下载过程中发生错误: {str(e)}")
        sys.exit(1) 