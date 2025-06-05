"""
# ----------------------------------------------------------------------------
# 音频转录器模块 - 负责将音频转录为文本
# 
# 核心功能：
# 1. 视频到音频的转换
# 2. 音频音量标准化
# 3. 音频智能分段
# 4. 多种ASR引擎支持 (WhisperX本地/云端, ElevenLabs)
# 5. 人声分离 (可选)
# 
# 输入：视频文件路径
# 输出：标准化的转录结果DataFrame和Excel文件
# ----------------------------------------------------------------------------
"""

import os
import subprocess
import pandas as pd
from typing import Dict, List, Tuple, Optional, Callable
from pydub import AudioSegment
from pydub.silence import detect_silence
from pydub.utils import mediainfo
from pathlib import Path


class AudioTranscriber:
    """音频转录器类 - 封装音频转录的所有功能"""
    
    def __init__(self,
                 output_dir: str = 'output',
                 audio_dir: str = 'output/audio',
                 target_segment_length: float = 30*60,
                 silence_window: float = 60,
                 target_db: float = -20.0):
        """
        初始化音频转录器
        
        Args:
            output_dir: 输出目录
            audio_dir: 音频文件目录
            target_segment_length: 目标分段长度（秒）
            silence_window: 静默检测窗口（秒）
            target_db: 目标音量标准化dB值
        """
        self.output_dir = Path(output_dir)
        self.audio_dir = Path(audio_dir)
        self.target_segment_length = target_segment_length
        self.silence_window = silence_window
        self.target_db = target_db
        
        # 创建必要的目录
        self.output_dir.mkdir(exist_ok=True)
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / 'log').mkdir(exist_ok=True)
        
        # 文件路径配置
        self.raw_audio_file = self.audio_dir / 'raw_audio.mp3'
        self.vocal_audio_file = self.audio_dir / 'vocal_audio.mp3'
        self.cleaned_chunks_file = self.output_dir / 'log' / '2_cleaned_chunks.xlsx'
    
    def convert_video_to_audio(self, video_file: str) -> str:
        """
        将视频文件转换为音频文件
        
        Args:
            video_file: 视频文件路径
            
        Returns:
            音频文件路径
            
        Note: 修复原代码缺陷 - 增加了文件存在检查和更好的错误处理
        """
        if not os.path.exists(video_file):
            raise FileNotFoundError(f"❌ 视频文件不存在: {video_file}")
        
        if self.raw_audio_file.exists():
            print(f"✅ 音频文件已存在: {self.raw_audio_file}")
            return str(self.raw_audio_file)
        
        print(f"🎬➡️🎵 正在使用FFmpeg转换为高质量音频...")
        
        try:
            # 使用FFmpeg转换视频为音频
            cmd = [
                'ffmpeg', '-y', '-i', video_file, '-vn',
                '-c:a', 'libmp3lame', '-b:a', '32k',
                '-ar', '16000', '-ac', '1', 
                '-metadata', 'encoding=UTF-8', 
                str(self.raw_audio_file)
            ]
            
            result = subprocess.run(
                cmd, 
                check=True, 
                capture_output=True, 
                text=True
            )
            
            print(f"✅ 视频转音频完成: {video_file} -> {self.raw_audio_file}")
            return str(self.raw_audio_file)
            
        except subprocess.CalledProcessError as e:
            print(f"❌ 视频转音频失败: {e.stderr}")
            raise RuntimeError(f"FFmpeg转换失败: {e.stderr}")
        except FileNotFoundError:
            raise RuntimeError("❌ 未找到FFmpeg, 请确保已安装并添加到PATH环境变量")
    
    def normalize_audio_volume(self, 
                             audio_path: str, 
                             output_path: Optional[str] = None,
                             format: str = "mp3") -> str:
        """
        标准化音频音量
        
        Args:
            audio_path: 输入音频文件路径
            output_path: 输出音频文件路径, 如果为None则覆盖原文件
            format: 输出格式
            
        Returns:
            标准化后的音频文件路径
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"❌ 音频文件不存在: {audio_path}")
        
        if output_path is None:
            output_path = audio_path
            
        try:
            audio = AudioSegment.from_file(audio_path)
            original_db = audio.dBFS
            
            # 计算需要调整的分贝数
            change_in_dBFS = self.target_db - original_db
            normalized_audio = audio.apply_gain(change_in_dBFS)
            
            # 导出标准化后的音频
            normalized_audio.export(output_path, format=format)
            
            print(f"✅ 音频音量标准化完成: {original_db:.1f}dB -> {self.target_db:.1f}dB")
            return output_path
            
        except Exception as e:
            print(f"❌ 音频标准化失败: {str(e)}")
            raise
    
    def get_audio_duration(self, audio_file: str) -> float:
        """
        获取音频文件时长
        
        Args:
            audio_file: 音频文件路径
            
        Returns:
            音频时长（秒）
        """
        try:
            cmd = ['ffmpeg', '-i', audio_file]
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE
            )
            _, stderr = process.communicate()
            output = stderr.decode('utf-8', errors='ignore')
            
            # 解析时长信息
            duration_lines = [line for line in output.split('\n') if 'Duration' in line]
            if not duration_lines:
                raise ValueError("无法从FFmpeg输出中找到时长信息")
            
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
    
    def split_audio_by_silence(self, audio_file: str) -> List[Tuple[float, float]]:
        """
        基于静默检测智能分割音频
        
        Args:
            audio_file: 音频文件路径
            
        Returns:
            分段列表, 每个元素为(开始时间, 结束时间)的元组
            
        Note: 修复原代码缺陷 - 改进了静默检测算法和边界处理
        """
        print(f"🎙️ 开始音频智能分段: {audio_file}")
        
        if not os.path.exists(audio_file):
            raise FileNotFoundError(f"❌ 音频文件不存在: {audio_file}")
        
        try:
            audio = AudioSegment.from_file(audio_file)
            duration = float(mediainfo(audio_file)["duration"])
            
            print(f"📏 音频总时长: {duration:.1f}秒")
            
            # 如果音频长度在允许范围内，不需要分割
            if duration <= self.target_segment_length + self.silence_window:
                print("📝 音频长度适中，无需分割")
                return [(0, duration)]
            
            segments = []
            pos = 0.0
            safe_margin = 0.5  # 静默点前后安全边界
            
            while pos < duration:
                # 如果剩余时长不超过目标长度，直接作为最后一段
                if duration - pos <= self.target_segment_length:
                    segments.append((pos, duration))
                    break
                
                # 计算分割点搜索区间
                threshold = pos + self.target_segment_length
                window_start = int((threshold - self.silence_window) * 1000)
                window_end = int((threshold + self.silence_window) * 1000)
                
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
                    (s/1000 + (threshold - self.silence_window), 
                     e/1000 + (threshold - self.silence_window))
                    for s, e in silence_regions
                ]
                
                # 筛选有效的静默区域
                valid_regions = [
                    (start, end) for start, end in silence_regions 
                    if (end - start) >= (safe_margin * 2) and 
                       threshold <= start + safe_margin <= threshold + self.silence_window
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
    
    def process_transcription_result(self, result: Dict) -> pd.DataFrame:
        """
        处理转录结果, 转换为标准DataFrame格式
        
        Args:
            result: ASR引擎返回的转录结果
            
        Returns:
            处理后的DataFrame
            
        Note: 修复原代码缺陷 - 增加了数据验证和异常处理
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
                    # 检查词长度
                    word_text = word.get("word", "").strip()
                    if len(word_text) > 30:
                        print(f"⚠️  检测到过长词汇，跳过: {word_text[:30]}...")
                        continue
                    
                    if not word_text:
                        print(f"⚠️  检测到空词汇，跳过")
                        continue
                    
                    # 清理特殊字符（法语引号等）
                    word_text = word_text.replace('»', '').replace('«', '')
                    
                    # 处理时间戳
                    if 'start' not in word or 'end' not in word:
                        # 使用前一个词的结束时间或寻找下一个有时间戳的词
                        if all_words:
                            start_time = end_time = all_words[-1]['end']
                        else:
                            # 寻找下一个有时间戳的词
                            next_word = next(
                                (w for w in segment['words'][word_idx+1:] 
                                 if 'start' in w and 'end' in w), 
                                None
                            )
                            if next_word:
                                start_time = end_time = next_word["start"]
                            else:
                                print(f"⚠️  无法确定词汇时间戳: {word_text}")
                                continue
                    else:
                        start_time = word.get('start', 0)
                        end_time = word['end']
                    
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
    
    def save_transcription_results(self, df: pd.DataFrame) -> str:
        """
        保存转录结果到Excel文件
        
        Args:
            df: 转录结果DataFrame
            
        Returns:
            保存的文件路径
            
        Note: 修复原代码缺陷 - 增加了数据清理和验证
        """
        print("💾 正在保存转录结果...")
        
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
            df.to_excel(self.cleaned_chunks_file, index=False)
            print(f"✅ 转录结果已保存: {self.cleaned_chunks_file}")
            print(f"📈 最终数据统计: {len(df)}行记录")
            
            return str(self.cleaned_chunks_file)
            
        except Exception as e:
            print(f"❌ 保存转录结果失败: {str(e)}")
            raise
    
    def transcribe_audio(self, 
                        audio_file: str,
                        vocal_audio_file: Optional[str] = None,
                        start_time: float = 0,
                        end_time: Optional[float] = None,
                        transcribe_func: Optional[Callable] = None) -> Dict:
        """
        转录音频片段
        
        Args:
            audio_file: 原始音频文件路径
            vocal_audio_file: 人声分离后的音频文件路径（可选）
            start_time: 开始时间
            end_time: 结束时间
            transcribe_func: 转录函数（由外部ASR引擎提供）
            
        Returns:
            转录结果字典
        """
        if transcribe_func is None:
            raise ValueError("❌ 未提供转录函数，请指定ASR引擎")
        
        print(f"🎤 转录音频片段: {start_time:.1f}s - {end_time or '结束'}s")
        
        try:
            result = transcribe_func(audio_file, vocal_audio_file, start_time, end_time)
            return result
        except Exception as e:
            print(f"❌ 音频转录失败: {str(e)}")
            raise
    
    def transcribe_video_complete(self, 
                                video_file: str,
                                use_vocal_separation: bool = False,
                                transcribe_func: Optional[Callable] = None) -> str:
        """
        完整的视频转录流程
        
        Args:
            video_file: 视频文件路径
            use_vocal_separation: 是否使用人声分离
            transcribe_func: 转录函数
            
        Returns:
            保存的转录结果文件路径
        """
        print("🚀 开始完整视频转录流程...")
        
        try:
            # 1. 视频转音频
            audio_file = self.convert_video_to_audio(video_file)
            
            # 2. 人声分离（可选）
            if use_vocal_separation:
                print("🎵 正在进行人声分离...")
                # 这里需要外部提供人声分离函数
                vocal_audio = str(self.vocal_audio_file)
                # vocal_separation_func(audio_file, vocal_audio)  # 需要外部实现
            else:
                vocal_audio = audio_file
            
            # 3. 音频分段
            segments = self.split_audio_by_silence(audio_file)
            
            # 4. 分段转录
            all_results = []
            for i, (start, end) in enumerate(segments):
                print(f"🎤 转录第{i+1}/{len(segments)}个片段...")
                result = self.transcribe_audio(
                    audio_file, vocal_audio, start, end, transcribe_func
                )
                all_results.append(result)
            
            # 5. 合并结果
            combined_result = {'segments': []}
            for result in all_results:
                if 'segments' in result:
                    combined_result['segments'].extend(result['segments'])
            
            # 6. 处理转录结果
            df = self.process_transcription_result(combined_result)
            
            # 7. 保存结果
            output_file = self.save_transcription_results(df)
            
            print("🎉 视频转录流程完成！")
            return output_file
            
        except Exception as e:
            print(f"💥 转录流程失败: {str(e)}")
            raise


# ----------------------------------------------------------------------------
# 独立运行测试
# ----------------------------------------------------------------------------
if __name__ == '__main__':
    import sys
    
    # 创建转录器实例
    transcriber = AudioTranscriber()
    
    # 测试视频文件输入
    if len(sys.argv) > 1:
        video_file = sys.argv[1]
    else:
        video_file = input('请输入视频文件路径: ')
    
    if not video_file.strip():
        print("❌ 视频文件路径不能为空")
        sys.exit(1)
    
    try:
        # 测试视频转音频
        print("\n🧪 测试视频转音频...")
        audio_file = transcriber.convert_video_to_audio(video_file)
        
        # 测试获取音频时长
        print("\n📏 测试获取音频时长...")
        duration = transcriber.get_audio_duration(audio_file)
        print(f"⏱️  音频时长: {duration:.1f}秒")
        
        # 测试音频分段
        print("\n✂️  测试音频分段...")
        segments = transcriber.split_audio_by_silence(audio_file)
        
        print(f"\n✅ 测试完成！")
        print(f"📁 音频文件: {audio_file}")
        print(f"📊 分段数量: {len(segments)}")
        
    except Exception as e:
        print(f"\n💥 测试过程中发生错误: {str(e)}")
        sys.exit(1) 