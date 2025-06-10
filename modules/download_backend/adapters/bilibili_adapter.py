"""
# ----------------------------------------------------------------------------
# Bilibili 下载适配器
# 
# 使用bilibili_api实现Bilibili视频下载功能
# 支持高质量视频下载和混流处理
# ----------------------------------------------------------------------------
"""

import os
import sys
import time
import asyncio
import subprocess
from typing import Dict, List, Optional, Any
from pathlib import Path

from ..base import DownloadEngineAdapter, DownloadResult, VideoInfo
from ..utils import sanitize_filename, get_file_size, format_file_size, extract_video_id
from ...commons.logger import setup_logger
from ..exceptions import DownloadError
from ...configs import load_key

logger = setup_logger(__name__)


class BilibiliAdapter(DownloadEngineAdapter):
    """Bilibili下载适配器"""
    
    def __init__(self, platform: str = "bilibili"):
        super().__init__("BilibiliDownloader", platform)
        self.video_module = None
        self.credential = None
        self.ffmpeg_path = "ffmpeg"
        
    def _setup_dependencies(self) -> None:
        """设置bilibili_api依赖"""
        try:
            # 导入bilibili_api模块
            from bilibili_api import video, Credential, HEADERS, get_client
            self.video_module = video
            self.Credential = Credential
            self.HEADERS = HEADERS
            self.get_client = get_client
            
            # 设置认证信息
            self._setup_credentials()
            
            logger.info("bilibili_api 依赖设置成功")
            
        except ImportError as e:
            logger.error("bilibili_api 未安装或导入失败")
            raise DownloadError("需要安装 bilibili_api: pip install bilibili_api") from e
        except Exception as e:
            logger.error(f"设置bilibili_api依赖失败: {str(e)}")
            raise DownloadError(f"bilibili_api 配置失败: {str(e)}") from e
    
    def _setup_credentials(self) -> None:
        """设置Bilibili认证信息"""
        try:
            # 从配置中获取认证信息
            sessdata = load_key("bilibili.sessdata", "")
            bili_jct = load_key("bilibili.bili_jct", "")
            buvid3 = load_key("bilibili.buvid3", "")
            
            if sessdata and bili_jct and buvid3:
                self.credential = self.Credential(
                    sessdata=sessdata,
                    bili_jct=bili_jct,
                    buvid3=buvid3
                )
                logger.info("Bilibili认证信息已配置")
            else:
                logger.warning("Bilibili认证信息未完整配置，可能影响下载质量")
                self.credential = None
                
        except Exception as e:
            logger.warning(f"设置Bilibili认证信息失败: {str(e)}")
            self.credential = None
    
    def _check_environment(self) -> None:
        """检查环境依赖"""
        if self.video_module is None:
            raise DownloadError("bilibili_api模块未正确初始化")
        
        # 检查FFmpeg
        try:
            subprocess.run([self.ffmpeg_path, "-version"], 
                         capture_output=True, check=True)
            logger.info("FFmpeg 可用")
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.warning("FFmpeg 未找到，将影响视频处理功能")
    
    def is_supported(self, url: str) -> bool:
        """检查URL是否被Bilibili适配器支持"""
        bilibili_domains = [
            'bilibili.com', 'www.bilibili.com', 'b23.tv',
            'm.bilibili.com', 'space.bilibili.com'
        ]
        
        return any(domain in url.lower() for domain in bilibili_domains)
    
    def get_supported_domains(self) -> List[str]:
        """获取支持的域名列表"""
        return [
            'bilibili.com', 'www.bilibili.com', 'b23.tv',
            'm.bilibili.com', 'space.bilibili.com'
        ]
    
    def get_video_info(self, url: str) -> VideoInfo:
        """获取Bilibili视频信息"""
        self._ensure_initialized()
        
        try:
            # 提取BV号
            bvid = self._extract_bvid(url)
            if not bvid:
                raise DownloadError(f"无法从URL提取BV号: {url}")
            
            # 创建Video实例
            v = self.video_module.Video(bvid=bvid, credential=self.credential)
            
            # 异步获取视频信息
            info = asyncio.run(self._get_video_info_async(v))
            
            # 转换为标准VideoInfo格式
            video_info = VideoInfo(
                title=info.get('title', ''),
                description=info.get('desc', ''),
                duration=info.get('duration', 0),
                uploader=info.get('owner', {}).get('name', ''),
                upload_date=str(info.get('pubdate', '')),
                view_count=info.get('stat', {}).get('view', 0),
                thumbnail_url=info.get('pic', ''),
                platform=self.platform,
                video_id=bvid,
                url=url,
                tags=info.get('tag', [])
            )
            
            logger.info(f"获取Bilibili视频信息成功: {video_info.title}")
            return video_info
            
        except Exception as e:
            logger.error(f"获取Bilibili视频信息失败: {str(e)}")
            raise DownloadError(f"获取视频信息失败: {str(e)}") from e
    
    async def _get_video_info_async(self, video_obj) -> Dict[str, Any]:
        """异步获取视频信息"""
        return await video_obj.get_info()
    
    def download(self, url: str) -> DownloadResult:
        """下载Bilibili视频"""
        self._ensure_initialized()
        self._ensure_configured()
        
        start_time = time.time()
        
        try:
            # 提取BV号
            bvid = self._extract_bvid(url)
            if not bvid:
                raise DownloadError(f"无法从URL提取BV号: {url}")
            
            logger.info(f"开始下载Bilibili视频: {bvid}")
            
            # 异步执行下载
            result = asyncio.run(self._download_async(bvid, url, start_time))
            
            return result
            
        except Exception as e:
            download_time = time.time() - start_time
            logger.error(f"Bilibili视频下载失败: {str(e)}")
            
            return DownloadResult(
                success=False,
                error_message=str(e),
                download_time=download_time,
                metadata={'platform': self.platform, 'original_url': url}
            )
    
    async def _download_async(self, bvid: str, url: str, start_time: float) -> DownloadResult:
        """异步下载处理"""
        try:
            # 创建Video实例
            v = self.video_module.Video(bvid=bvid, credential=self.credential)
            
            # 获取下载链接
            download_url_data = await v.get_download_url(0)
            
            # 解析下载信息
            detecter = self.video_module.VideoDownloadURLDataDetecter(data=download_url_data)
            streams = detecter.detect_best_streams()
            
            if not streams:
                raise DownloadError("未找到可用的视频流")
            
            # 准备文件路径
            video_info = await v.get_info()
            video_title = sanitize_filename(video_info.get('title', bvid))
            save_path = self.config.save_path if self.config else 'output'
            os.makedirs(save_path, exist_ok=True)
            
            final_video_path = os.path.join(save_path, f"{video_title}.mp4")
            
            # 检查流类型并下载
            if detecter.check_flv_mp4_stream():
                # FLV流下载
                logger.info("检测到FLV流，开始下载...")
                
                flv_temp_path = os.path.join(save_path, "flv_temp.flv")
                await self._download_stream(streams[0].url, flv_temp_path, "下载FLV音视频流")
                
                # 转换格式
                logger.info("转换FLV到MP4格式...")
                result = subprocess.run([
                    self.ffmpeg_path, "-i", flv_temp_path, "-c", "copy", final_video_path
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    # 删除临时文件
                    os.remove(flv_temp_path)
                    logger.info("FLV转换完成")
                else:
                    raise DownloadError(f"FFmpeg转换失败: {result.stderr}")
                    
            else:
                # MP4流下载（分离音视频）
                logger.info("检测到分离音视频流，开始下载...")
                
                video_temp_path = os.path.join(save_path, "video_temp.m4s")
                audio_temp_path = os.path.join(save_path, "audio_temp.m4s")
                
                # 下载视频和音频流
                await asyncio.gather(
                    self._download_stream(streams[0].url, video_temp_path, "下载视频流"),
                    self._download_stream(streams[1].url, audio_temp_path, "下载音频流")
                )
                
                # 混流
                logger.info("混合音视频流...")
                result = subprocess.run([
                    self.ffmpeg_path, "-i", video_temp_path, "-i", audio_temp_path,
                    "-vcodec", "copy", "-acodec", "copy", final_video_path
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    # 删除临时文件
                    os.remove(video_temp_path)
                    os.remove(audio_temp_path)
                    logger.info("音视频混流完成")
                else:
                    raise DownloadError(f"FFmpeg混流失败: {result.stderr}")
            
            # 创建下载结果
            download_time = time.time() - start_time
            file_size = get_file_size(final_video_path)
            
            # 获取完整视频信息
            try:
                video_info_obj = VideoInfo(
                    title=video_info.get('title', ''),
                    description=video_info.get('desc', ''),
                    duration=video_info.get('duration', 0),
                    uploader=video_info.get('owner', {}).get('name', ''),
                    upload_date=str(video_info.get('pubdate', '')),
                    view_count=video_info.get('stat', {}).get('view', 0),
                    thumbnail_url=video_info.get('pic', ''),
                    platform=self.platform,
                    video_id=bvid,
                    url=url
                )
            except:
                video_info_obj = None
            
            result = DownloadResult(
                success=True,
                video_path=final_video_path,
                video_info=video_info_obj,
                download_time=download_time,
                file_size=file_size,
                metadata={
                    'platform': self.platform,
                    'original_url': url,
                    'bvid': bvid,
                    'file_size_formatted': format_file_size(file_size),
                    'stream_type': 'flv' if detecter.check_flv_mp4_stream() else 'mp4'
                }
            )
            
            logger.info(f"Bilibili视频下载成功: {final_video_path}")
            logger.info(f"下载耗时: {download_time:.2f}秒, 文件大小: {format_file_size(file_size)}")
            
            return result
            
        except Exception as e:
            download_time = time.time() - start_time
            logger.error(f"异步下载失败: {str(e)}")
            raise DownloadError(f"下载失败: {str(e)}") from e
    
    async def _download_stream(self, url: str, output_path: str, description: str) -> None:
        """下载单个流"""
        try:
            client = self.get_client()
            dwn_id = await client.download_create(url, self.HEADERS)
            
            total_size = client.download_content_length(dwn_id)
            downloaded_size = 0
            
            logger.info(f"开始{description}: {output_path}")
            
            with open(output_path, "wb") as file:
                while True:
                    chunk = await client.download_chunk(dwn_id)
                    if not chunk:
                        break
                        
                    downloaded_size += file.write(chunk)
                    
                    # 显示进度
                    if total_size > 0:
                        progress = (downloaded_size / total_size) * 100
                        logger.debug(f"{description} - 进度: {progress:.1f}% ({downloaded_size}/{total_size})")
                    
                    if downloaded_size >= total_size:
                        break
            
            logger.info(f"{description} 完成: {output_path}")
            
        except Exception as e:
            logger.error(f"{description} 失败: {str(e)}")
            raise DownloadError(f"{description} 失败: {str(e)}") from e
    
    def _extract_bvid(self, url: str) -> Optional[str]:
        """从URL中提取BV号"""
        import re
        
        # 直接BV号
        bv_match = re.search(r'BV[a-zA-Z0-9]+', url)
        if bv_match:
            return bv_match.group()
        
        # 从bilibili.com/video/格式提取
        video_match = re.search(r'/video/([a-zA-Z0-9]+)', url)
        if video_match:
            return video_match.group(1)
        
        # 从b23.tv短链接提取（需要解析重定向）
        if 'b23.tv' in url:
            try:
                import requests
                response = requests.head(url, allow_redirects=True, timeout=10)
                return self._extract_bvid(response.url)
            except:
                pass
        
        return None
    
    def batch_download(self, urls: List[str]) -> List[DownloadResult]:
        """批量下载Bilibili视频"""
        self._ensure_initialized()
        self._ensure_configured()
        
        results = []
        total = len(urls)
        
        logger.info(f"开始批量下载 {total} 个Bilibili视频")
        
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