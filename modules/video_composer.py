"""
# ----------------------------------------------------------------------------
# 视频合成器模块 - 最终视频合成和输出
# 
# 核心功能：
# 1. 视频字幕嵌入和样式配置
# 2. 音频配音合成和背景音乐混合
# 3. 多平台兼容的字体和编码处理
# 4. GPU加速支持和性能优化
# 5. 多种输出格式和质量配置
# 6. 完整的视频后处理流程
# 
# 输入：原始视频，字幕文件，配音音频
# 输出：最终合成的配音视频
# 
# 设计原则：
# - 支持多种视频格式和分辨率
# - 智能字体配置和跨平台兼容
# - 高质量音频处理和标准化
# - 灵活的配置选项和样式控制
# ----------------------------------------------------------------------------
"""

import os
import re
import time
import shutil
import subprocess
import platform
from typing import List, Dict, Optional, Tuple, Any, Union
from pathlib import Path
import concurrent.futures
from dataclasses import dataclass, asdict
from collections import defaultdict
import warnings

warnings.filterwarnings("ignore", category=FutureWarning)


@dataclass
class SubtitleStyle:
    """字幕样式配置数据类"""
    font_size: int = 17               # 字体大小
    font_name: str = "Arial"          # 字体名称
    font_color: str = "&H00FFFF"      # 字体颜色
    outline_color: str = "&H000000"   # 描边颜色
    outline_width: int = 1            # 描边宽度
    back_color: str = "&H33000000"    # 背景颜色
    alignment: int = 2                # 对齐方式
    margin_v: int = 27               # 垂直边距
    border_style: int = 4            # 边框样式


@dataclass
class VideoConfig:
    """视频配置数据类"""
    target_width: int = 1920          # 目标宽度
    target_height: int = 1080         # 目标高度
    video_codec: str = ""             # 视频编解码器
    audio_codec: str = "aac"          # 音频编解码器
    audio_bitrate: str = "96k"        # 音频比特率
    use_gpu: bool = False            # 是否使用GPU加速
    burn_subtitles: bool = True      # 是否烧录字幕


@dataclass
class CompositionResult:
    """合成结果数据类"""
    output_video: str                 # 输出视频路径
    processing_time: float            # 处理时间
    video_resolution: str             # 视频分辨率
    file_size: int                    # 文件大小（字节）
    subtitle_files_used: List[str]    # 使用的字幕文件
    audio_files_used: List[str]       # 使用的音频文件
    success: bool = True              # 是否成功
    error_message: str = ""           # 错误信息
    
    def __post_init__(self):
        if not self.subtitle_files_used:
            self.subtitle_files_used = []
        if not self.audio_files_used:
            self.audio_files_used = []


class VideoComposer:
    """视频合成器类 - 最终视频合成和输出"""
    
    def __init__(self,
                 input_video: str = '',
                 subtitle_dir: str = 'output',
                 audio_dir: str = 'output',
                 output_dir: str = 'output',
                 temp_dir: str = 'output/temp',
                 video_config: Optional[VideoConfig] = None,
                 src_subtitle_style: Optional[SubtitleStyle] = None,
                 trans_subtitle_style: Optional[SubtitleStyle] = None):
        """
        初始化视频合成器
        
        Args:
            input_video: 输入视频文件路径
            subtitle_dir: 字幕文件目录
            audio_dir: 音频文件目录
            output_dir: 输出目录
            temp_dir: 临时文件目录
            video_config: 视频配置
            src_subtitle_style: 源语言字幕样式
            trans_subtitle_style: 翻译字幕样式
        """
        self.input_video = Path(input_video) if input_video else None
        self.subtitle_dir = Path(subtitle_dir)
        self.audio_dir = Path(audio_dir)
        self.output_dir = Path(output_dir)
        self.temp_dir = Path(temp_dir)
        
        # 创建目录
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # 配置设置
        self.video_config = video_config or VideoConfig()
        self.src_subtitle_style = src_subtitle_style or self._get_default_src_style()
        self.trans_subtitle_style = trans_subtitle_style or self._get_default_trans_style()
        
        # 自动检测平台和字体
        self._detect_platform_fonts()
        
        # 懒加载依赖
        self._cv2 = None
        self._numpy = None
        
        # 内部状态
        self._detected_resolution = None
        
    def _get_opencv(self):
        """懒加载OpenCV"""
        if self._cv2 is None:
            try:
                import cv2
                self._cv2 = cv2
            except ImportError:
                raise ImportError("❌ 未找到OpenCV库, 请安装: pip install opencv-python")
        return self._cv2
    
    def _get_numpy(self):
        """懒加载NumPy"""
        if self._numpy is None:
            try:
                import numpy as np
                self._numpy = np
            except ImportError:
                raise ImportError("❌ 未找到NumPy库, 请安装: pip install numpy")
        return self._numpy
    
    def _detect_platform_fonts(self):
        """检测平台并设置合适的字体"""
        system = platform.system()
        
        if system == 'Linux':
            # Linux系统使用Noto字体
            self.src_subtitle_style.font_name = 'NotoSansCJK-Regular'
            self.trans_subtitle_style.font_name = 'NotoSansCJK-Regular'
        elif system == 'Darwin':
            # macOS系统使用Unicode字体
            self.src_subtitle_style.font_name = 'Arial Unicode MS'
            self.trans_subtitle_style.font_name = 'Arial Unicode MS'
        else:
            # Windows和其他系统使用Arial
            self.src_subtitle_style.font_name = 'Arial'
            self.trans_subtitle_style.font_name = 'Arial'
        
        print(f"📝 检测到{system}系统，设置字体: {self.src_subtitle_style.font_name}")
    
    def _get_default_src_style(self) -> SubtitleStyle:
        """获取默认源语言字幕样式"""
        return SubtitleStyle(
            font_size=15,
            font_name="Arial",
            font_color="&HFFFFFF",
            outline_color="&H000000",
            outline_width=1,
            back_color="&H80000000",
            alignment=1,
            margin_v=50,
            border_style=1
        )
    
    def _get_default_trans_style(self) -> SubtitleStyle:
        """获取默认翻译字幕样式"""
        return SubtitleStyle(
            font_size=17,
            font_name="Arial",
            font_color="&H00FFFF",
            outline_color="&H000000",
            outline_width=1,
            back_color="&H33000000",
            alignment=2,
            margin_v=27,
            border_style=4
        )
    
    def find_video_file(self, video_dir: Optional[str] = None) -> str:
        """
        查找视频文件
        
        Args:
            video_dir: 视频文件目录
            
        Returns:
            视频文件路径
        """
        if self.input_video and self.input_video.exists():
            return str(self.input_video)
        
        search_dir = Path(video_dir) if video_dir else self.output_dir.parent
        
        # 支持的视频格式
        video_extensions = ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm']
        
        # 查找视频文件
        for ext in video_extensions:
            video_files = list(search_dir.glob(f"*{ext}"))
            if video_files:
                video_file = str(video_files[0])
                print(f"📹 找到视频文件: {video_file}")
                return video_file
        
        raise FileNotFoundError("❌ 未找到视频文件")
    
    def detect_video_resolution(self, video_file: str) -> Tuple[int, int]:
        """
        检测视频分辨率
        
        Args:
            video_file: 视频文件路径
            
        Returns:
            (宽度, 高度)
        """
        try:
            cv2 = self._get_opencv()
            video = cv2.VideoCapture(video_file)
            
            width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            video.release()
            
            print(f"📐 检测到视频分辨率: {width}x{height}")
            self._detected_resolution = (width, height)
            
            return width, height
            
        except Exception as e:
            print(f"❌ 检测视频分辨率失败: {str(e)}")
            return self.video_config.target_width, self.video_config.target_height
    
    def check_gpu_support(self) -> bool:
        """
        检查GPU加速支持
        
        Returns:
            是否支持GPU加速
        """
        try:
            result = subprocess.run(
                ['ffmpeg', '-encoders'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            gpu_support = 'h264_nvenc' in result.stdout
            
            if gpu_support:
                print("🚀 检测到GPU加速支持")
            else:
                print("⚠️  未检测到GPU加速支持，将使用CPU")
            
            return gpu_support
            
        except Exception as e:
            print(f"❌ 检查GPU支持失败: {str(e)}")
            return False
    
    def create_placeholder_video(self, output_path: str) -> bool:
        """
        创建占位符视频（黑色视频）
        
        Args:
            output_path: 输出路径
            
        Returns:
            是否成功
        """
        try:
            cv2 = self._get_opencv()
            np = self._get_numpy()
            
            print("🖤 创建占位符视频...")
            
            # 创建黑色帧
            frame = np.zeros((self.video_config.target_height, self.video_config.target_width, 3), dtype=np.uint8)
            
            # 设置视频编写器
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(
                output_path,
                fourcc,
                1,
                (self.video_config.target_width, self.video_config.target_height)
            )
            
            # 写入一帧
            out.write(frame)
            out.release()
            
            print(f"✅ 占位符视频创建完成: {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ 创建占位符视频失败: {str(e)}")
            return False
    
    def normalize_audio(self, input_audio: str, output_audio: str) -> bool:
        """
        标准化音频音量
        
        Args:
            input_audio: 输入音频文件
            output_audio: 输出音频文件
            
        Returns:
            是否成功
        """
        try:
            print(f"🔊 正在标准化音频: {input_audio}")
            
            cmd = [
                'ffmpeg', '-y', '-i', input_audio,
                '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11',
                '-ar', '44100', '-ac', '2',
                output_audio
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print(f"✅ 音频标准化完成: {output_audio}")
                return True
            else:
                print(f"❌ 音频标准化失败: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ 音频标准化错误: {str(e)}")
            return False
    
    def build_subtitle_filter(self, subtitle_files: List[str]) -> str:
        """
        构建字幕滤镜字符串
        
        Args:
            subtitle_files: 字幕文件列表
            
        Returns:
            FFmpeg字幕滤镜字符串
        """
        filters = []
        
        for i, subtitle_file in enumerate(subtitle_files):
            if not os.path.exists(subtitle_file):
                continue
            
            # 确定使用哪种样式
            if 'src' in os.path.basename(subtitle_file).lower():
                style = self.src_subtitle_style
            else:
                style = self.trans_subtitle_style
            
            # 构建样式字符串
            style_str = (
                f"FontSize={style.font_size},"
                f"FontName={style.font_name},"
                f"PrimaryColour={style.font_color},"
                f"OutlineColour={style.outline_color},"
                f"OutlineWidth={style.outline_width},"
                f"BackColour={style.back_color},"
                f"Alignment={style.alignment},"
                f"MarginV={style.margin_v},"
                f"BorderStyle={style.border_style}"
            )
            
            # 添加字幕滤镜
            filter_str = f"subtitles={subtitle_file}:force_style='{style_str}'"
            filters.append(filter_str)
        
        return ','.join(filters) if filters else ""
    
    def compose_video_with_subtitles(self, 
                                   video_file: str,
                                   subtitle_files: List[str],
                                   output_file: str) -> bool:
        """
        合成视频和字幕
        
        Args:
            video_file: 输入视频文件
            subtitle_files: 字幕文件列表
            output_file: 输出视频文件
            
        Returns:
            是否成功
        """
        try:
            print("🎬 开始合成视频和字幕...")
            
            # 检测视频分辨率
            width, height = self.detect_video_resolution(video_file)
            
            # 构建基础滤镜
            base_filter = (
                f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
                f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"
            )
            
            # 构建字幕滤镜
            subtitle_filter = self.build_subtitle_filter(subtitle_files)
            
            # 组合完整滤镜
            full_filter = f"{base_filter},{subtitle_filter}" if subtitle_filter else base_filter
            
            # 构建FFmpeg命令
            cmd = ['ffmpeg', '-y', '-i', video_file, '-vf', full_filter]
            
            # 检查GPU支持
            if self.video_config.use_gpu and self.check_gpu_support():
                cmd.extend(['-c:v', 'h264_nvenc'])
                print("🚀 使用GPU加速")
            
            cmd.append(output_file)
            
            print(f"🎥 执行FFmpeg命令...")
            start_time = time.time()
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                elapsed_time = time.time() - start_time
                print(f"✅ 视频字幕合成完成，耗时: {elapsed_time:.2f}秒")
                return True
            else:
                print(f"❌ 视频字幕合成失败: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ 视频字幕合成错误: {str(e)}")
            return False
    
    def compose_final_video(self,
                          video_file: str,
                          audio_files: List[str],
                          background_audio: Optional[str],
                          subtitle_file: Optional[str],
                          output_file: str) -> bool:
        """
        合成最终视频（包含配音、背景音乐和字幕）
        
        Args:
            video_file: 输入视频文件
            audio_files: 配音音频文件列表
            background_audio: 背景音乐文件
            subtitle_file: 字幕文件
            output_file: 输出视频文件
            
        Returns:
            是否成功
        """
        try:
            print("🎭 开始合成最终视频...")
            
            # 检测视频分辨率
            width, height = self.detect_video_resolution(video_file)
            
            # 准备输入文件
            inputs = ['-i', video_file]
            input_count = 1
            
            # 添加背景音乐
            if background_audio and os.path.exists(background_audio):
                inputs.extend(['-i', background_audio])
                input_count += 1
                print(f"🎵 添加背景音乐: {background_audio}")
            
            # 添加配音音频
            dub_audio = None
            for audio_file in audio_files:
                if os.path.exists(audio_file):
                    # 先标准化音频
                    normalized_audio = str(self.temp_dir / f"normalized_{os.path.basename(audio_file)}")
                    if self.normalize_audio(audio_file, normalized_audio):
                        inputs.extend(['-i', normalized_audio])
                        dub_audio = normalized_audio
                        input_count += 1
                        print(f"🗣️  添加配音音频: {audio_file}")
                        break
            
            # 构建视频滤镜
            video_filter = (
                f"[0:v]scale={width}:{height}:force_original_aspect_ratio=decrease,"
                f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"
            )
            
            # 添加字幕滤镜
            if subtitle_file and os.path.exists(subtitle_file):
                style = self.trans_subtitle_style
                subtitle_filter = (
                    f"subtitles={subtitle_file}:force_style='"
                    f"FontSize={style.font_size},"
                    f"FontName={style.font_name},"
                    f"PrimaryColour={style.font_color},"
                    f"OutlineColour={style.outline_color},"
                    f"OutlineWidth={style.outline_width},"
                    f"BackColour={style.back_color},"
                    f"Alignment={style.alignment},"
                    f"MarginV={style.margin_v},"
                    f"BorderStyle={style.border_style}'"
                )
                video_filter += f",{subtitle_filter}"
            
            video_filter += "[v]"
            
            # 构建音频滤镜
            audio_filter = ""
            if input_count > 1:
                if background_audio and dub_audio:
                    # 混合背景音乐和配音
                    audio_filter = "[1:a][2:a]amix=inputs=2:duration=first:dropout_transition=3[a]"
                elif dub_audio:
                    # 仅配音
                    audio_filter = "[1:a]anull[a]"
                elif background_audio:
                    # 仅背景音乐
                    audio_filter = "[1:a]anull[a]"
            
            # 构建完整的filter_complex
            if audio_filter:
                filter_complex = f"{video_filter};{audio_filter}"
            else:
                filter_complex = video_filter
            
            # 构建FFmpeg命令
            cmd = ['ffmpeg', '-y'] + inputs + ['-filter_complex', filter_complex]
            
            # 映射输出
            cmd.extend(['-map', '[v]'])
            if audio_filter:
                cmd.extend(['-map', '[a]'])
            
            # 设置编码参数
            if self.video_config.use_gpu and self.check_gpu_support():
                cmd.extend(['-c:v', 'h264_nvenc'])
                print("🚀 使用GPU加速")
            
            cmd.extend([
                '-c:a', self.video_config.audio_codec,
                '-b:a', self.video_config.audio_bitrate,
                output_file
            ])
            
            print("🎬 执行最终合成...")
            start_time = time.time()
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                elapsed_time = time.time() - start_time
                print(f"✅ 最终视频合成完成，耗时: {elapsed_time:.2f}秒")
                return True
            else:
                print(f"❌ 最终视频合成失败: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ 最终视频合成错误: {str(e)}")
            return False
    
    def get_file_size(self, file_path: str) -> int:
        """获取文件大小"""
        try:
            return os.path.getsize(file_path) if os.path.exists(file_path) else 0
        except:
            return 0
    
    def process_complete_composition(self,
                                   composition_type: str = "full") -> CompositionResult:
        """
        处理完整的视频合成流程
        
        Args:
            composition_type: 合成类型 ("subtitles_only", "dubbing_only", "full")
            
        Returns:
            合成结果
        """
        print("🚀 开始完整视频合成流程...")
        
        start_time = time.time()
        
        try:
            # 1. 查找输入视频
            if not self.input_video:
                video_file = self.find_video_file()
            else:
                video_file = str(self.input_video)
            
            if not os.path.exists(video_file):
                raise FileNotFoundError(f"❌ 视频文件不存在: {video_file}")
            
            # 2. 准备输出文件路径
            output_files = {
                "subtitles_only": self.output_dir / "output_sub.mp4",
                "dubbing_only": self.output_dir / "output_dub.mp4",
                "full": self.output_dir / "output_final.mp4"
            }
            
            output_file = str(output_files.get(composition_type, output_files["full"]))
            
            # 3. 检查是否烧录字幕
            if not self.video_config.burn_subtitles:
                print("⚠️  未启用字幕烧录，生成占位符视频")
                success = self.create_placeholder_video(output_file)
                
                return CompositionResult(
                    output_video=output_file,
                    processing_time=time.time() - start_time,
                    video_resolution="1920x1080",
                    file_size=self.get_file_size(output_file),
                    subtitle_files_used=[],
                    audio_files_used=[],
                    success=success,
                    error_message="" if success else "创建占位符视频失败"
                )
            
            # 4. 查找字幕文件
            subtitle_files = []
            for pattern in ['src.srt', 'trans.srt', 'dub.srt']:
                subtitle_file = self.subtitle_dir / pattern
                if subtitle_file.exists():
                    subtitle_files.append(str(subtitle_file))
            
            # 5. 查找音频文件
            audio_files = []
            background_audio = None
            
            for pattern in ['dub.mp3', 'dub.wav', 'output_audio.mp3']:
                audio_file = self.audio_dir / pattern
                if audio_file.exists():
                    audio_files.append(str(audio_file))
            
            # 查找背景音乐
            for pattern in ['background.mp3', 'background.wav', 'bg_music.mp3']:
                bg_file = self.audio_dir / pattern
                if bg_file.exists():
                    background_audio = str(bg_file)
                    break
            
            # 6. 执行合成
            success = False
            
            if composition_type == "subtitles_only":
                # 仅字幕合成
                success = self.compose_video_with_subtitles(video_file, subtitle_files, output_file)
                
            elif composition_type == "dubbing_only":
                # 仅配音合成（使用dub.srt字幕）
                dub_subtitle = str(self.subtitle_dir / "dub.srt") if (self.subtitle_dir / "dub.srt").exists() else None
                success = self.compose_final_video(video_file, audio_files, background_audio, dub_subtitle, output_file)
                
            else:
                # 完整合成
                if subtitle_files and audio_files:
                    # 使用最适合的字幕文件
                    best_subtitle = None
                    for srt_file in subtitle_files:
                        if 'dub.srt' in srt_file:
                            best_subtitle = srt_file
                            break
                        elif 'trans.srt' in srt_file:
                            best_subtitle = srt_file
                    
                    success = self.compose_final_video(video_file, audio_files, background_audio, best_subtitle, output_file)
                elif subtitle_files:
                    # 仅有字幕，进行字幕合成
                    success = self.compose_video_with_subtitles(video_file, subtitle_files, output_file)
                else:
                    # 无字幕和音频，复制原视频
                    shutil.copy2(video_file, output_file)
                    success = True
                    print("⚠️  未找到字幕和音频文件，复制原视频")
            
            processing_time = time.time() - start_time
            
            # 7. 检测输出分辨率
            if success and os.path.exists(output_file):
                try:
                    width, height = self.detect_video_resolution(output_file)
                    resolution_str = f"{width}x{height}"
                except:
                    resolution_str = f"{self.video_config.target_width}x{self.video_config.target_height}"
            else:
                resolution_str = "未知"
            
            result = CompositionResult(
                output_video=output_file,
                processing_time=processing_time,
                video_resolution=resolution_str,
                file_size=self.get_file_size(output_file),
                subtitle_files_used=subtitle_files,
                audio_files_used=audio_files,
                success=success,
                error_message="" if success else "视频合成失败"
            )
            
            if success:
                print("🎉 视频合成流程完成！")
                print(f"📊 合成统计:")
                print(f"  📁 输出文件: {result.output_video}")
                print(f"  📐 分辨率: {result.video_resolution}")
                print(f"  💾 文件大小: {result.file_size / (1024*1024):.1f} MB")
                print(f"  🕒 处理耗时: {result.processing_time:.2f}秒")
                print(f"  📄 字幕文件: {len(result.subtitle_files_used)}个")
                print(f"  🎵 音频文件: {len(result.audio_files_used)}个")
            else:
                print(f"💥 视频合成失败: {result.error_message}")
            
            return result
            
        except Exception as e:
            error_msg = f"视频合成流程异常: {str(e)}"
            print(f"💥 {error_msg}")
            
            return CompositionResult(
                output_video="",
                processing_time=time.time() - start_time,
                video_resolution="未知",
                file_size=0,
                subtitle_files_used=[],
                audio_files_used=[],
                success=False,
                error_message=error_msg
            )


# ----------------------------------------------------------------------------
# 独立运行测试
# ----------------------------------------------------------------------------
if __name__ == '__main__':
    import sys
    
    # 创建视频合成器实例
    composer = VideoComposer(
        video_config=VideoConfig(
            use_gpu=False,  # 测试时不使用GPU
            burn_subtitles=True
        )
    )
    
    # 测试参数
    composition_type = "full"
    if "--subtitles-only" in sys.argv:
        composition_type = "subtitles_only"
    elif "--dubbing-only" in sys.argv:
        composition_type = "dubbing_only"
    
    try:
        # 检查必要的工具
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
            print("✅ FFmpeg 可用")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("❌ FFmpeg 不可用，请安装FFmpeg")
            sys.exit(1)
        
        # 运行完整视频合成流程
        print(f"\n🧪 测试视频合成流程（类型: {composition_type}）...")
        
        result = composer.process_complete_composition(composition_type)
        
        if result.success:
            print(f"\n✅ 测试完成！")
            print(f"📁 输出文件: {result.output_video}")
            print(f"📐 视频分辨率: {result.video_resolution}")
            print(f"💾 文件大小: {result.file_size / (1024*1024):.1f} MB")
        else:
            print(f"\n❌ 测试失败: {result.error_message}")
            sys.exit(1)
        
    except Exception as e:
        print(f"\n💥 测试过程中发生错误: {str(e)}")
        sys.exit(1) 