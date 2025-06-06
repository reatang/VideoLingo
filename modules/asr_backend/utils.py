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
    
    def __init__(self, 
                 target_db: float = -20.0,
                 safe_margin: float = 0.5):
        """
        初始化音频处理器
        
        Args:
            target_db: 目标音量标准化dB值
            safe_margin: 静默检测安全边界（秒）
        """
        self.target_db = target_db
        self.safe_margin = safe_margin
    
    def normalize_audio_volume(self, 
                             audio_path: str, 
                             output_path: str, 
                             target_db: Optional[float] = None,
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
        
        target_db = target_db or self.target_db
        
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
    
    def convert_video_to_audio(self, 
                             video_file: str, 
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
    
    def get_audio_duration(self, audio_file: str) -> float:
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
    
    def split_audio_by_silence(self, 
                             audio_file: str,
                             target_length: float = 30*60,
                             silence_window: float = 60) -> List[Tuple[float, float]]:
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
                    min_silence_len=int(self.safe_margin * 1000),
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
                    if (end - start) >= (self.safe_margin * 2) and 
                       threshold <= start + self.safe_margin <= threshold + silence_window
                ]
                
                if valid_regions:
                    # 使用第一个有效静默区域
                    start, end = valid_regions[0]
                    split_at = start + self.safe_margin
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
    
    def process_transcription_result(self, result: ASRResult) -> pd.DataFrame:
        """
        处理转录结果, 转换为标准DataFrame格式
        
        Args:
            result: ASR引擎返回的转录结果
            
        Returns:
            处理后的DataFrame
        """
        print("📊 正在处理转录结果...")
        
        if 'segments' not in result:
            raise ValueError("❌ 转录结果格式错误：缺少segments字段")
        
        all_words = []
        
        for segment_idx, segment in enumerate(result['segments']):
            speaker_id = segment.get('speaker_id', None)
            
            if 'words' not in segment:
                print(f"⚠️  段落{segment_idx}缺少words字段，跳过")
                continue
            
            for word_idx, word in enumerate(segment['words']):
                try:
                    # 处理不同的word格式：字典或WordTimestamp对象
                    if hasattr(word, 'word'):
                        # WordTimestamp对象
                        word_text = word.word.strip() if word.word else ""
                        start_time = word.start
                        end_time = word.end
                    elif isinstance(word, dict):
                        # 字典格式
                        word_text = word.get("word", "").strip()
                        start_time = word.get('start', 0)
                        end_time = word.get('end', 0)
                    else:
                        print(f"⚠️  未知的word格式，跳过: {type(word)}")
                        continue
                    
                    # 检查词长度
                    if len(word_text) > 30:
                        print(f"⚠️  检测到过长词汇，跳过: {word_text[:30]}...")
                        continue
                    
                    if not word_text:
                        print(f"⚠️  检测到空词汇，跳过")
                        continue
                    
                    # 清理特殊字符（法语引号等）
                    word_text = word_text.replace('»', '').replace('«', '')
                    
                    # 处理时间戳异常情况
                    if start_time is None or end_time is None:
                        # 使用前一个词的结束时间或寻找下一个有时间戳的词
                        if all_words:
                            start_time = end_time = all_words[-1]['end']
                        else:
                            # 寻找下一个有时间戳的词
                            next_word = None
                            for next_w in segment['words'][word_idx+1:]:
                                if hasattr(next_w, 'start') and next_w.start is not None:
                                    next_word = next_w
                                    break
                                elif isinstance(next_w, dict) and 'start' in next_w:
                                    next_word = next_w
                                    break
                            
                            if next_word:
                                if hasattr(next_word, 'start'):
                                    start_time = end_time = next_word.start
                                else:
                                    start_time = end_time = next_word['start']
                            else:
                                print(f"⚠️  无法确定词汇时间戳: {word_text}")
                                continue
                    
                    word_dict = {
                        'text': word_text,
                        'start': start_time,
                        'end': end_time,
                        'speaker_id': speaker_id
                    }
                    
                    all_words.append(word_dict)
                    
                except Exception as e:
                    print(f"⚠️  处理词汇时出错: {str(e)}")
                    continue
        
        if not all_words:
            raise ValueError("❌ 未能提取到有效的转录结果")
        
        df = pd.DataFrame(all_words)
        print(f"✅ 转录结果处理完成，共{len(df)}个词汇")
        
        return df
    
    def save_transcription_results(self, df: pd.DataFrame, output_file: str) -> str:
        """
        保存转录结果到Excel文件
        
        Args:
            df: 转录结果DataFrame
            output_file: 输出文件路径
            
        Returns:
            保存的文件路径
        """
        print("💾 正在保存转录结果...")
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # 数据清理
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
        
        # 为文本添加引号（Excel格式要求）
        df['text'] = df['text'].apply(lambda x: f'"{x}"')
        
        # 保存到Excel
        try:
            df.to_excel(output_file, index=False)
            print(f"✅ 转录结果已保存: {output_file}")
            print(f"📈 最终数据统计: {len(df)}行记录")
            
            return output_file
            
        except Exception as e:
            print(f"❌ 保存转录结果失败: {str(e)}")
            raise


# ----------------------------------------------------------------------------
# 兼容性函数 - 保持与原有代码的兼容性
# ----------------------------------------------------------------------------

def normalize_audio_volume(audio_path: str, 
                         output_path: str, 
                         target_db: float = -20.0, 
                         format: str = "wav") -> str:
    """兼容性函数 - 音频音量标准化"""
    processor = AudioProcessor(target_db=target_db)
    return processor.normalize_audio_volume(audio_path, output_path, target_db, format)


def convert_video_to_audio(video_file: str, output_path: str) -> str:
    """兼容性函数 - 视频转音频"""
    processor = AudioProcessor()
    return processor.convert_video_to_audio(video_file, output_path)


def get_audio_duration(audio_file: str) -> float:
    """兼容性函数 - 获取音频时长"""
    processor = AudioProcessor()
    return processor.get_audio_duration(audio_file)


def split_audio(audio_file: str, 
               target_len: float = 30*60, 
               win: float = 60) -> List[Tuple[float, float]]:
    """兼容性函数 - 音频分段"""
    processor = AudioProcessor()
    return processor.split_audio_by_silence(audio_file, target_len, win)


def process_transcription(result: Dict) -> pd.DataFrame:
    """兼容性函数 - 处理转录结果"""
    processor = AudioProcessor()
    return processor.process_transcription_result(result)


def save_results(df: pd.DataFrame, output_file: str = "output/log/2_cleaned_chunks.xlsx") -> str:
    """兼容性函数 - 保存转录结果"""
    processor = AudioProcessor()
    return processor.save_transcription_results(df, output_file) 