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
from modules.common_utils import paths


class AudioTranscriber:
    """音频转录器类 - 封装音频转录的所有功能"""
    
    def __init__(self,
                 output_dir: str = 'output',
                 target_segment_length: float = 30*60,
                 silence_window: float = 60,
                 target_db: float = -20.0):
        """
        初始化音频转录器
        
        Args:
            output_dir: 输出目录
            target_segment_length: 目标分段长度（秒）
            silence_window: 静默检测窗口（秒）
            target_db: 目标音量标准化dB值
        """
        self.output_dir = Path(output_dir)
        self.audio_dir = self.output_dir / "audio"
        self.target_segment_length = target_segment_length
        self.silence_window = silence_window
        
        # 创建必要的目录
        self.output_dir.mkdir(exist_ok=True)
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / 'log').mkdir(exist_ok=True)
        
        # 初始化音频处理器 
        self.target_db = target_db
        self.safe_margin = 0.5
        
        # 文件路径配置
        self.raw_audio_file = self.audio_dir / 'raw.mp3'
        self.vocal_audio_file = self.audio_dir / 'vocal.mp3'
    
    def _convert_video_to_audio(self, video_file: str) -> str:
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
        return AudioProcessor.convert_video_to_audio(
            video_file,
            str(self.raw_audio_file),
            audio_format="mp3",
            sample_rate=16000,
            channels=1,
            bitrate="32k"
        )
    
    def _merge_transcription_results(self, results: List[ASRResult]) -> pd.DataFrame:
        """
        合并多个转录结果
        
        Args:
            results: ASR转录结果列表
            
        Returns:
            合并后的DataFrame
        """
        print("🔗 正在合并多个转录结果...")
        
        all_dfs = []
        for i, result in enumerate(results):
            print(f"📝 处理第{i+1}/{len(results)}个转录结果...")
            df = AudioProcessor.process_transcription_result(result)
            all_dfs.append(df)
        
        # 合并所有DataFrame
        if all_dfs:
            combined_df = pd.concat(all_dfs, ignore_index=True)
            print(f"✅ 转录结果合并完成，共{len(combined_df)}个词汇")
            return combined_df
        else:
            raise ValueError("❌ 没有有效的转录结果可合并")
    
    def _save_transcription_results(self, df: pd.DataFrame, output_xlsx_file: str) -> str:
        """
        保存转录结果到Excel文件
        
        Args:
            df: 转录结果DataFrame
            
        Returns:
            保存的文件路径
        """
        print("💾 正在保存转录结果...")
        
        # 定义输出文件路径
        output_file = output_xlsx_file
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # 为文本添加引号（Excel格式要求）
        df_copy = df.copy()
        df_copy['text'] = df_copy['text'].apply(lambda x: f'"{x}"')
        
        # 保存到Excel
        try:
            df_copy.to_excel(output_file, index=False)
            print(f"✅ 转录结果已保存: {output_file}")
            print(f"📈 最终数据统计: {len(df_copy)}行记录")
            
            return output_file
            
        except Exception as e:
            print(f"❌ 保存转录结果失败: {str(e)}")
            raise
    
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
                                output_xlsx_file: Optional[str] = None,
                                use_vocal_separation: bool = False,
                                engine_type: str = "local",
                                config: Optional[Dict] = None) -> str:
        """
        完整的视频转录流程
        
        Args:
            video_file: 视频文件路径
            output_xlsx_file: 输出Excel文件名
            use_vocal_separation: 是否使用人声分离
            engine_type: ASR引擎类型
            config: 引擎配置
            
        Returns:
            保存的转录结果文件路径
        """
        print("🚀 开始完整视频转录流程...")

        if output_xlsx_file is None:
            output_xlsx_file = paths.get_filepath_by_log_dir('cleaned_chunks.xlsx', output_base_dir=self.output_dir)
        else:
            output_xlsx_file = paths.get_filepath_by_default(output_xlsx_file, output_base_dir=self.output_dir)
        
        try:
            # 1. 视频转音频
            audio_file = self._convert_video_to_audio(video_file)
            
            # 2. 人声分离（可选）
            if use_vocal_separation:
                print("🎵 正在进行人声分离...")
                vocal_audio = str(self.vocal_audio_file)
                # 这里需要外部提供人声分离函数，分离后进行音量标准化
                # 假设人声分离已完成，对分离后的音频进行标准化
                AudioProcessor.normalize_audio_volume(audio_file, vocal_audio, target_db=self.target_db, format="mp3")
            else:
                vocal_audio = audio_file
            
            # 3. 音频分段
            segments = AudioProcessor.split_audio_by_silence(
                audio_file,
                target_length=self.target_segment_length,
                silence_window=self.silence_window
            )
            
            # 4. 分段转录
            all_results = []
            for i, (start, end) in enumerate(segments):
                print(f"🎤 转录第{i+1}/{len(segments)}个片段...")
                result = self.transcribe_audio_segment(
                    audio_file, vocal_audio, start, end, engine_type, config
                )
                all_results.append(result)
            
            # 5. 合并结果
            combined_df = self._merge_transcription_results(all_results)

            # 6. 保存结果
            output_file = self._save_transcription_results(combined_df, output_xlsx_file)
            
            print("🎉 视频转录流程完成！")
            return output_file
            
        except Exception as e:
            print(f"💥 转录流程失败: {str(e)}")
            raise
        finally:
            # 确保清理所有引擎资源
            cleanup_all_engines()


def transcribe_video_complete(video_file: str,
                              output_dir: str = "output",
                             output_xlsx_file: Optional[str] = None,
                             use_vocal_separation: bool = False,
                             engine_type: str = "local",
                             config: Optional[Dict] = None) -> str:
    """
    一键完成视频转录的便捷接口
    """
    transcriber = AudioTranscriber(output_dir=output_dir)
    return transcriber.transcribe_video_complete(video_file, output_xlsx_file, use_vocal_separation, engine_type, config)

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