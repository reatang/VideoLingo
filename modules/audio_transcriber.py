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
import pandas as pd
from typing import Dict, List, Tuple, Optional, Callable
from pathlib import Path

from modules.asr_backend.base import ASRResult
from modules.asr_backend.utils import AudioProcessor
from modules.asr_backend.factory import create_asr_engine, cleanup_all_engines


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
        
        # 创建必要的目录
        self.output_dir.mkdir(exist_ok=True)
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / 'log').mkdir(exist_ok=True)
        
        # 初始化音频处理器 - 使用已有的AudioProcessor类
        self.audio_processor = AudioProcessor(
            target_db=target_db,
            safe_margin=0.5
        )
        
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
        """
        if not os.path.exists(video_file):
            raise FileNotFoundError(f"❌ 视频文件不存在: {video_file}")
        
        if self.raw_audio_file.exists():
            print(f"✅ 音频文件已存在: {self.raw_audio_file}")
            return str(self.raw_audio_file)
        
        # 使用AudioProcessor进行转换
        return self.audio_processor.convert_video_to_audio(
            video_file,
            str(self.raw_audio_file),
            audio_format="mp3",
            sample_rate=16000,
            channels=1,
            bitrate="32k"
        )
    
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
        # 使用AudioProcessor的标准化功能
        return self.audio_processor.normalize_audio_volume(
            audio_path, output_path or audio_path, format=format
        )
    
    def get_audio_duration(self, audio_file: str) -> float:
        """
        获取音频文件时长
        
        Args:
            audio_file: 音频文件路径
            
        Returns:
            音频时长（秒）
        """
        # 使用AudioProcessor获取时长
        return self.audio_processor.get_audio_duration(audio_file)
    
    def split_audio_by_silence(self, audio_file: str) -> List[Tuple[float, float]]:
        """
        基于静默检测智能分割音频
        
        Args:
            audio_file: 音频文件路径
            
        Returns:
            分段列表, 每个元素为(开始时间, 结束时间)的元组
        """
        # 使用AudioProcessor进行分段
        return self.audio_processor.split_audio_by_silence(
            audio_file,
            target_length=self.target_segment_length,
            silence_window=self.silence_window
        )
    
    def process_transcription_result(self, result: ASRResult) -> pd.DataFrame:
        """
        处理转录结果, 转换为标准DataFrame格式
        
        Args:
            result: ASR引擎返回的转录结果
            
        Returns:
            处理后的DataFrame
        """
        # 使用AudioProcessor处理转录结果
        return self.audio_processor.process_transcription_result(result.to_dict())
    
    def save_transcription_results(self, df: pd.DataFrame) -> str:
        """
        保存转录结果到Excel文件
        
        Args:
            df: 转录结果DataFrame
            
        Returns:
            保存的文件路径
        """
        # 使用AudioProcessor保存结果
        return self.audio_processor.save_transcription_results(
            df, str(self.cleaned_chunks_file)
        )
    
    def transcribe_audio_segment(self, 
                               audio_file: str,
                               vocal_audio_file: Optional[str] = None,
                               start_time: float = 0,
                               end_time: Optional[float] = None,
                               engine_type: str = "local",
                               config: Optional[Dict] = None) -> ASRResult:
        """
        转录音频片段
        
        Args:
            audio_file: 原始音频文件路径
            vocal_audio_file: 人声分离后的音频文件路径（可选）
            start_time: 开始时间
            end_time: 结束时间
            engine_type: ASR引擎类型
            config: 引擎配置
            
        Returns:
            转录结果
        """
        print(f"🎤 转录音频片段: {start_time:.1f}s - {end_time or '结束'}s")
        
        # 创建ASR引擎
        asr_engine = create_asr_engine(engine_type, config)
        
        try:
            # 执行转录
            result = asr_engine.transcribe(
                raw_audio_path=audio_file,
                vocal_audio_path=vocal_audio_file or audio_file,
                start_time=start_time,
                end_time=end_time
            )
            
            return result
            
        finally:
            # 清理引擎资源
            asr_engine.cleanup()
    
    def transcribe_video_complete(self, 
                                video_file: str,
                                use_vocal_separation: bool = False,
                                engine_type: str = "local",
                                config: Optional[Dict] = None) -> str:
        """
        完整的视频转录流程
        
        Args:
            video_file: 视频文件路径
            use_vocal_separation: 是否使用人声分离
            engine_type: ASR引擎类型
            config: 引擎配置
            
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
                vocal_audio = str(self.vocal_audio_file)
                # 这里需要外部提供人声分离函数
                # vocal_separation_func(audio_file, vocal_audio)
            else:
                vocal_audio = audio_file
            
            # 3. 音频分段
            segments = self.split_audio_by_silence(audio_file)
            
            # 4. 分段转录
            all_results = []
            for i, (start, end) in enumerate(segments):
                print(f"🎤 转录第{i+1}/{len(segments)}个片段...")
                result = self.transcribe_audio_segment(
                    audio_file, vocal_audio, start, end, engine_type, config
                )
                all_results.append(result)
            
            # 5. 合并结果
            combined_words = []
            for result in all_results:
                result_df = result.to_dataframe()
                if not result_df.empty:
                    combined_words.append(result_df)
            
            if not combined_words:
                raise ValueError("❌ 未能获取到有效的转录结果")
            
            combined_df = pd.concat(combined_words, ignore_index=True)
            
            # 6. 保存结果
            output_file = self.save_transcription_results(combined_df)
            
            print("🎉 视频转录流程完成！")
            return output_file
            
        except Exception as e:
            print(f"💥 转录流程失败: {str(e)}")
            raise
        finally:
            # 确保清理所有引擎资源
            cleanup_all_engines()


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
        # 测试完整转录流程
        print("\n🧪 测试完整转录流程...")
        output_file = transcriber.transcribe_video_complete(
            video_file,
            engine_type="local"
        )
        
        print(f"\n✅ 测试完成！")
        print(f"📁 转录结果: {output_file}")
        
    except Exception as e:
        print(f"\n💥 测试过程中发生错误: {str(e)}")
        sys.exit(1) 