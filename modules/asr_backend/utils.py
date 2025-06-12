"""
# ----------------------------------------------------------------------------
# 音频处理工具类
# 
# 提供音频相关的通用功能：
# 1. 音频格式转换和处理
# 2. 音量标准化
# 3. 音频时长获取
# 4. 音频分段处理
# 5. 转录结果处理
# ----------------------------------------------------------------------------
"""

import os
import subprocess
import pandas as pd
from typing import Dict, List, Tuple, Optional
from pydub import AudioSegment
from pydub.silence import detect_silence
from pydub.utils import mediainfo
from pathlib import Path
from .base import ASRResult


class AudioProcessor:
    """音频处理器类 - 封装音频相关的通用操作"""

    @staticmethod
    def normalize_audio_volume(audio_path: str, 
                             output_path: str, 
                             target_db: Optional[float] = -20.0,
                             format: str = "wav") -> str:
        """
        标准化音频音量
        
        Args:
            audio_path: 输入音频文件路径
            output_path: 输出音频文件路径
            target_db: 目标dB值，None则使用默认值
            format: 输出格式
            
        Returns:
            标准化后的音频文件路径
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"❌ 音频文件不存在: {audio_path}")
        
        try:
            audio = AudioSegment.from_file(audio_path)
            original_db = audio.dBFS
            
            # 计算需要调整的分贝数
            change_in_dBFS = target_db - original_db
            normalized_audio = audio.apply_gain(change_in_dBFS)
            
            # 导出标准化后的音频
            normalized_audio.export(output_path, format=format)
            
            print(f"✅ 音频音量标准化完成: {original_db:.1f}dB -> {target_db:.1f}dB")
            return output_path
            
        except Exception as e:
            print(f"❌ 音频标准化失败: {str(e)}")
            raise
    
    @staticmethod
    def convert_video_to_audio(video_file: str, 
                             output_path: str,
                             audio_format: str = "mp3",
                             sample_rate: int = 16000,
                             channels: int = 1,
                             bitrate: str = "32k") -> str:
        """
        将视频文件转换为音频文件
        
        Args:
            video_file: 视频文件路径
            output_path: 输出音频文件路径
            audio_format: 音频格式
            sample_rate: 采样率
            channels: 声道数
            bitrate: 比特率
            
        Returns:
            音频文件路径
        """
        if not os.path.exists(video_file):
            raise FileNotFoundError(f"❌ 视频文件不存在: {video_file}")
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        if os.path.exists(output_path):
            print(f"✅ 音频文件已存在: {output_path}")
            return output_path
        
        print(f"🎬➡️🎵 正在使用FFmpeg转换为高质量音频...")
        
        try:
            cmd = [
                'ffmpeg', '-y', '-i', video_file, '-vn',
                '-c:a', 'libmp3lame' if audio_format == 'mp3' else 'pcm_s16le',
                '-b:a', bitrate,
                '-ar', str(sample_rate),
                '-ac', str(channels),
                '-metadata', 'encoding=UTF-8', 
                output_path
            ]
            
            # 修复Windows编码问题：使用bytes模式并手动处理编码
            result = subprocess.run(
                cmd, 
                check=True, 
                capture_output=True, 
                text=False  # 使用bytes模式避免编码问题
            )
            
            # 手动解码输出，使用错误处理策略
            try:
                stdout_text = result.stdout.decode('utf-8', errors='ignore')
                stderr_text = result.stderr.decode('utf-8', errors='ignore')
            except:
                # 如果UTF-8失败，尝试系统默认编码
                import locale
                try:
                    encoding = locale.getpreferredencoding()
                    stdout_text = result.stdout.decode(encoding, errors='ignore')
                    stderr_text = result.stderr.decode(encoding, errors='ignore')
                except:
                    stdout_text = str(result.stdout)
                    stderr_text = str(result.stderr)
            
            print(f"✅ 视频转音频完成: {video_file} -> {output_path}")
            return output_path
            
        except subprocess.CalledProcessError as e:
            # 处理错误信息的编码问题
            try:
                if hasattr(e, 'stderr') and e.stderr:
                    if isinstance(e.stderr, bytes):
                        error_msg = e.stderr.decode('utf-8', errors='ignore')
                    else:
                        error_msg = str(e.stderr)
                else:
                    error_msg = "FFmpeg执行失败"
            except:
                error_msg = "FFmpeg执行失败（无法解析错误信息）"
            
            print(f"❌ 视频转音频失败: {error_msg}")
            raise RuntimeError(f"FFmpeg转换失败: {error_msg}")
        except FileNotFoundError:
            raise RuntimeError("❌ 未找到FFmpeg, 请确保已安装并添加到PATH环境变量")
        except Exception as e:
            print(f"❌ 视频转音频发生未知错误: {str(e)}")
            raise
    
    @staticmethod
    def get_audio_duration(audio_file: str) -> float:
        """
        获取音频文件时长
        
        Args:
            audio_file: 音频文件路径
            
        Returns:
            音频时长（秒）
        """
        if not os.path.exists(audio_file):
            raise FileNotFoundError(f"❌ 音频文件不存在: {audio_file}")
        
        try:
            cmd = ['ffmpeg', '-i', audio_file]
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE
            )
            stdout_bytes, stderr_bytes = process.communicate()
            
            # 修复Windows编码问题：手动解码输出
            try:
                output = stderr_bytes.decode('utf-8', errors='ignore')
            except:
                # 如果UTF-8失败，尝试系统默认编码
                import locale
                try:
                    encoding = locale.getpreferredencoding()
                    output = stderr_bytes.decode(encoding, errors='ignore')
                except:
                    output = str(stderr_bytes)
            
            # 解析时长信息
            duration_lines = [line for line in output.split('\n') if 'Duration' in line]
            if not duration_lines:
                # 备用方法：使用pydub
                audio = AudioSegment.from_file(audio_file)
                return len(audio) / 1000.0
            
            duration_str = duration_lines[0].split('Duration: ')[1].split(',')[0]
            duration_parts = duration_str.split(':')
            
            duration = (
                float(duration_parts[0]) * 3600 + 
                float(duration_parts[1]) * 60 + 
                float(duration_parts[2])
            )
            
            return duration
            
        except Exception as e:
            print(f"⚠️  获取音频时长失败: {str(e)}")
            return 0.0
    
    @staticmethod
    def split_audio_by_silence(audio_file: str,
                             target_length: float = 30*60,
                             silence_window: float = 60,
                             safe_margin: float = 0.5) -> List[Tuple[float, float]]:
        """
        基于静默检测智能分割音频
        
        Args:
            audio_file: 音频文件路径
            target_length: 目标分段长度（秒）
            silence_window: 静默检测窗口（秒）
            
        Returns:
            分段列表, 每个元素为(开始时间, 结束时间)的元组
        """
        print(f"🎙️ 开始音频智能分段: {audio_file}")
        
        if not os.path.exists(audio_file):
            raise FileNotFoundError(f"❌ 音频文件不存在: {audio_file}")
        
        try:
            audio = AudioSegment.from_file(audio_file)
            duration = float(mediainfo(audio_file)["duration"])
            
            print(f"📏 音频总时长: {duration:.1f}秒")
            
            # 如果音频长度在允许范围内，不需要分割
            if duration <= target_length + silence_window:
                print("📝 音频长度适中，无需分割")
                return [(0, duration)]
            
            segments = []
            pos = 0.0
            
            while pos < duration:
                # 如果剩余时长不超过目标长度，直接作为最后一段
                if duration - pos <= target_length:
                    segments.append((pos, duration))
                    break
                
                # 计算分割点搜索区间
                threshold = pos + target_length
                window_start = int((threshold - silence_window) * 1000)
                window_end = int((threshold + silence_window) * 1000)
                
                # 确保窗口不超出音频范围
                window_end = min(window_end, len(audio))
                
                if window_start >= window_end:
                    # 窗口无效，使用阈值点分割
                    segments.append((pos, threshold))
                    pos = threshold
                    continue
                
                # 在窗口内检测静默区域
                silence_regions = detect_silence(
                    audio[window_start:window_end],
                    min_silence_len=int(safe_margin * 1000),
                    silence_thresh=-30
                )
                
                # 将静默区域时间转换为绝对时间
                silence_regions = [
                    (s/1000 + (threshold - silence_window), 
                     e/1000 + (threshold - silence_window))
                    for s, e in silence_regions
                ]
                
                # 筛选有效的静默区域
                valid_regions = [
                    (start, end) for start, end in silence_regions 
                    if (end - start) >= (safe_margin * 2) and 
                       threshold <= start + safe_margin <= threshold + silence_window
                ]
                
                if valid_regions:
                    # 使用第一个有效静默区域
                    start, end = valid_regions[0]
                    split_at = start + safe_margin
                    print(f"🎯 在静默区域分割: {split_at:.1f}秒")
                else:
                    # 没有找到合适的静默区域，使用阈值点
                    split_at = threshold
                    print(f"⚠️  未找到静默区域，在阈值点分割: {split_at:.1f}秒")
                
                segments.append((pos, split_at))
                pos = split_at
            
            print(f"✅ 音频分割完成，共{len(segments)}个片段")
            
            # 打印分段信息
            for i, (start, end) in enumerate(segments):
                print(f"  📎 片段{i+1}: {start:.1f}s - {end:.1f}s ({end-start:.1f}s)")
            
            return segments
            
        except Exception as e:
            print(f"❌ 音频分割失败: {str(e)}")
            raise

    @staticmethod
    def process_transcription_result(result: ASRResult) -> pd.DataFrame:
        """
        处理转录结果, 转换为标准DataFrame格式
        
        Args:
            result: ASR引擎返回的转录结果
            
        Returns:
            处理后的DataFrame
        """
        print("📊 正在处理转录结果...")
        
        # 使用ASRResult内置的转换方法
        df = result.to_dataframe()
        
        if df.empty:
            raise ValueError("❌ 未能提取到有效的转录结果")
        
        # 基本数据清理
        initial_rows = len(df)
        
        # 移除空文本行
        df = df[df['text'].str.len() > 0]
        removed_empty = initial_rows - len(df)
        if removed_empty > 0:
            print(f"🧹 移除了{removed_empty}行空文本")
        
        # 检查并移除过长词汇
        long_words = df[df['text'].str.len() > 30]
        if not long_words.empty:
            print(f"⚠️  检测到{len(long_words)}个过长词汇，已移除")
            df = df[df['text'].str.len() <= 30]
        
        # 清理特殊字符
        df['text'] = df['text'].replace({'»': '', '«': ''}, regex=True)
        
        print(f"✅ 转录结果处理完成，共{len(df)}个词汇")
        
        return df
    

# ----------------------------------------------------------------------------
# 配置读取工具
# ----------------------------------------------------------------------------
from ..configs import ConfigManager, get_global_config
from .base import ASRConfig

def get_asr_config(config: Optional[ConfigManager] = None) -> ASRConfig:
    """获取ASR配置"""

    if config is None:
        config = get_global_config()

    return ASRConfig(
        language=config.load_key('whisper.language', 'auto'),
        model=config.load_key('whisper.model', 'large-v3'),
        detected_language=config.load_key('whisper.detected_language', 'auto'),
        runtime=config.load_key('whisper.runtime', 'local'),
        whisperX_302_api_key=config.load_key('whisper.whisperX_302_api_key', ''),
        elevenlabs_api_key=config.load_key('whisper.elevenlabs_api_key', ''),
        model_dir=config.load_key('model_dir', '_model_cache_'),
        demucs=config.load_key('demucs', True)
    )

# ----------------------------------------------------------------------------
# 兼容性函数 - 保持与原有代码的兼容性
# ----------------------------------------------------------------------------

def normalize_audio_volume(audio_path: str, 
                         output_path: str, 
                         target_db: float = -20.0, 
                         format: str = "wav") -> str:
    """兼容性函数 - 音频音量标准化"""
    return AudioProcessor.normalize_audio_volume(audio_path, output_path, target_db, format)


def convert_video_to_audio(video_file: str, output_path: str) -> str:
    """兼容性函数 - 视频转音频"""
    return AudioProcessor.convert_video_to_audio(video_file, output_path)


def get_audio_duration(audio_file: str) -> float:
    """兼容性函数 - 获取音频时长"""
    return AudioProcessor.get_audio_duration(audio_file)


def split_audio(audio_file: str, 
               target_len: float = 30*60, 
               win: float = 60) -> List[Tuple[float, float]]:
    """兼容性函数 - 音频分段"""
    return AudioProcessor.split_audio_by_silence(audio_file, target_len, win)


def process_transcription(result: Dict) -> pd.DataFrame:
    """兼容性函数 - 处理转录结果"""
    return AudioProcessor.process_transcription_result(result)