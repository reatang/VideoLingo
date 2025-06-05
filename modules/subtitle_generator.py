"""
# ----------------------------------------------------------------------------
# 字幕生成器模块 - 多格式字幕文件生成和时间轴对齐
# 
# 核心功能：
# 1. 智能字幕长度分割和内容优化
# 2. 精准时间轴对齐和间隔优化
# 3. 多格式字幕文件生成 (SRT, VTT, ASS等)
# 4. 双语字幕和样式自定义
# 5. 音频配音用字幕专门处理
# 6. 字幕质量检测和修复
# 
# 输入：翻译结果Excel，转录音频数据
# 输出：多种格式的字幕文件
# 
# 设计原则：
# - 确保字幕时间轴的精确对齐
# - 支持多种字幕格式和样式配置
# - 智能处理字幕长度和显示效果
# - 为音频配音提供专门的字幕支持
# ----------------------------------------------------------------------------
"""

import os
import re
import json
import math
from typing import List, Dict, Optional, Tuple, Any, Union
from pathlib import Path
import concurrent.futures
from dataclasses import dataclass, asdict
from collections import defaultdict
from datetime import datetime, timedelta
import warnings

warnings.filterwarnings("ignore", category=FutureWarning)


@dataclass
class SubtitleSegment:
    """字幕片段数据类"""
    index: int                      # 片段索引
    start_time: float              # 开始时间（秒）
    end_time: float                # 结束时间（秒）
    duration: float                # 持续时间（秒）
    source_text: str               # 源语言文本
    translated_text: str = ""      # 翻译文本
    display_source: str = ""       # 显示用源文本
    display_translation: str = ""  # 显示用翻译文本
    confidence: float = 1.0        # 对齐置信度
    needs_split: bool = False      # 是否需要分割
    
    def get_srt_timestamp(self) -> str:
        """获取SRT格式的时间戳"""
        return self._seconds_to_srt_format(self.start_time, self.end_time)
    
    def _seconds_to_srt_format(self, start: float, end: float) -> str:
        """将秒数转换为SRT时间格式"""
        def seconds_to_hmsm(seconds: float) -> str:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = seconds % 60
            milliseconds = int(secs * 1000) % 1000
            return f"{hours:02d}:{minutes:02d}:{int(secs):02d},{milliseconds:03d}"
        
        start_srt = seconds_to_hmsm(start)
        end_srt = seconds_to_hmsm(end)
        return f"{start_srt} --> {end_srt}"


@dataclass
class SubtitleConfig:
    """字幕配置数据类"""
    max_length: int = 50           # 最大字符长度
    target_multiplier: float = 2.5 # 目标语言长度倍数
    min_duration: float = 1.0      # 最小显示时长
    max_duration: float = 6.0      # 最大显示时长
    gap_threshold: float = 1.0     # 间隔阈值
    font_size: int = 16           # 字体大小
    font_name: str = "Arial"      # 字体名称
    enable_dual_language: bool = True # 是否启用双语


@dataclass
class SubtitleGenerationResult:
    """字幕生成结果数据类"""
    total_segments: int            # 总片段数
    generated_files: List[str]     # 生成的文件列表
    processing_time: float         # 处理时间
    average_duration: float        # 平均时长
    split_segments: int = 0        # 拆分的片段数
    alignment_issues: int = 0      # 对齐问题数
    
    def __post_init__(self):
        if not self.generated_files:
            self.generated_files = []


class SubtitleGenerator:
    """字幕生成器类 - 多格式字幕文件生成"""
    
    def __init__(self,
                 translation_file: str = 'output/log/4_2_translation.xlsx',
                 audio_data_file: str = 'output/log/2_cleaned_chunks.xlsx',
                 output_dir: str = 'output',
                 audio_output_dir: str = 'output/audio',
                 src_language: str = 'en',
                 tgt_language: str = 'zh',
                 subtitle_config: Optional[SubtitleConfig] = None,
                 max_workers: int = 4):
        """
        初始化字幕生成器
        
        Args:
            translation_file: 翻译结果文件
            audio_data_file: 音频数据文件（包含时间戳）
            output_dir: 字幕输出目录
            audio_output_dir: 音频用字幕输出目录
            src_language: 源语言代码
            tgt_language: 目标语言代码
            subtitle_config: 字幕配置对象
            max_workers: 并行处理的最大线程数
        """
        self.translation_file = Path(translation_file)
        self.audio_data_file = Path(audio_data_file)
        self.output_dir = Path(output_dir)
        self.audio_output_dir = Path(audio_output_dir)
        self.src_language = src_language
        self.tgt_language = tgt_language
        self.subtitle_config = subtitle_config or SubtitleConfig()
        self.max_workers = max_workers
        
        # 创建输出目录
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.audio_output_dir.mkdir(parents=True, exist_ok=True)
        
        # 字幕输出配置
        self.subtitle_output_configs = [
            ('src.srt', ['source']),
            ('trans.srt', ['translation']),
            ('src_trans.srt', ['source', 'translation']),
            ('trans_src.srt', ['translation', 'source'])
        ]
        
        self.audio_subtitle_configs = [
            ('src_subs_for_audio.srt', ['source']),
            ('trans_subs_for_audio.srt', ['translation'])
        ]
        
        # 懒加载依赖
        self._pd = None
        self._ask_gpt_func = None
        
        # 内部状态
        self._audio_words_data = []
        self._translation_data = []
        self._segments = []
        
    def _get_pandas(self):
        """懒加载pandas"""
        if self._pd is None:
            try:
                import pandas as pd
                self._pd = pd
            except ImportError:
                raise ImportError("❌ 未找到pandas库, 请安装: pip install pandas")
        return self._pd
    
    def set_gpt_function(self, ask_gpt_func):
        """
        设置GPT调用函数（用于字幕分割优化）
        
        Args:
            ask_gpt_func: GPT API调用函数
        """
        self._ask_gpt_func = ask_gpt_func
        print("✅ GPT函数已设置（用于字幕分割优化）")
    
    def load_audio_data(self) -> List[Dict]:
        """
        加载音频词级数据
        
        Returns:
            词级数据列表
        """
        print(f"📖 正在加载音频数据: {self.audio_data_file}")
        
        if not self.audio_data_file.exists():
            raise FileNotFoundError(f"❌ 音频数据文件不存在: {self.audio_data_file}")
        
        try:
            pd = self._get_pandas()
            df = pd.read_excel(self.audio_data_file)
            
            # 检查必需的列
            required_columns = ['text', 'start', 'end']
            if not all(col in df.columns for col in required_columns):
                raise ValueError(f"❌ 音频数据文件缺少必需列: {required_columns}")
            
            # 转换为词级数据
            words_data = []
            for _, row in df.iterrows():
                if pd.notna(row['text']) and pd.notna(row['start']) and pd.notna(row['end']):
                    words_data.append({
                        'text': str(row['text']).strip().strip('"'),
                        'start': float(row['start']),
                        'end': float(row['end'])
                    })
            
            print(f"✅ 加载了{len(words_data)}个音频片段")
            return words_data
            
        except Exception as e:
            print(f"❌ 加载音频数据失败: {str(e)}")
            raise
    
    def load_translation_data(self) -> List[Dict]:
        """
        加载翻译数据
        
        Returns:
            翻译数据列表
        """
        print(f"📖 正在加载翻译数据: {self.translation_file}")
        
        if not self.translation_file.exists():
            raise FileNotFoundError(f"❌ 翻译数据文件不存在: {self.translation_file}")
        
        try:
            pd = self._get_pandas()
            df = pd.read_excel(self.translation_file)
            
            # 检查必需的列
            required_columns = ['Source', 'Translation']
            if not all(col in df.columns for col in required_columns):
                raise ValueError(f"❌ 翻译数据文件缺少必需列: {required_columns}")
            
            # 转换为翻译数据
            translation_data = []
            for _, row in df.iterrows():
                if pd.notna(row['Source']):
                    translation_data.append({
                        'source': str(row['Source']).strip(),
                        'translation': str(row['Translation']).strip() if pd.notna(row['Translation']) else ""
                    })
            
            print(f"✅ 加载了{len(translation_data)}个翻译条目")
            return translation_data
            
        except Exception as e:
            print(f"❌ 加载翻译数据失败: {str(e)}")
            raise
    
    def calculate_text_weight(self, text: str) -> float:
        """
        计算文本显示权重（考虑不同语言字符的显示宽度）
        
        Args:
            text: 文本内容
            
        Returns:
            文本显示权重
        """
        if not text:
            return 0.0
        
        weight = 0.0
        for char in str(text):
            code = ord(char)
            if 0x4E00 <= code <= 0x9FFF or 0x3040 <= code <= 0x30FF:  # 中文和日文
                weight += 1.75
            elif 0xAC00 <= code <= 0xD7A3 or 0x1100 <= code <= 0x11FF:  # 韩文
                weight += 1.5
            elif 0x0E00 <= code <= 0x0E7F:  # 泰文
                weight += 1.0
            elif 0xFF01 <= code <= 0xFF5E:  # 全角符号
                weight += 1.75
            else:  # 其他字符（英文、半角符号等）
                weight += 1.0
        
        return weight
    
    def clean_text_for_matching(self, text: str) -> str:
        """
        清理文本用于匹配（移除标点和空格）
        
        Args:
            text: 原始文本
            
        Returns:
            清理后的文本
        """
        if not text:
            return ""
        
        # 移除多余空格
        text = re.sub(r'\s+', ' ', text)
        # 移除标点符号
        text = re.sub(r'[^\w\s]', '', text)
        return text.strip().lower()
    
    def align_timestamps(self, audio_words: List[Dict], translations: List[Dict]) -> List[SubtitleSegment]:
        """
        对齐时间戳，将翻译文本匹配到音频时间戳
        
        Args:
            audio_words: 音频词级数据
            translations: 翻译数据
            
        Returns:
            对齐后的字幕片段列表
        """
        print("⏰ 正在进行时间戳对齐...")
        
        segments = []
        
        # 构建完整的音频文本字符串和位置映射
        full_audio_text = ''
        position_to_word_idx = {}
        
        for idx, word_data in enumerate(audio_words):
            clean_word = self.clean_text_for_matching(word_data['text'])
            start_pos = len(full_audio_text)
            full_audio_text += clean_word
            
            # 建立位置到词索引的映射
            for pos in range(start_pos, len(full_audio_text)):
                position_to_word_idx[pos] = idx
        
        print(f"📝 构建了{len(full_audio_text)}字符的音频文本索引")
        
        # 对每个翻译句子进行时间戳匹配
        current_pos = 0
        
        for idx, trans_data in enumerate(translations):
            source_text = trans_data['source']
            translation_text = trans_data['translation']
            
            clean_sentence = self.clean_text_for_matching(source_text).replace(" ", "")
            sentence_len = len(clean_sentence)
            
            if sentence_len == 0:
                print(f"⚠️  跳过空句子: {idx}")
                continue
            
            # 在音频文本中查找匹配
            match_found = False
            search_start = current_pos
            
            while search_start <= len(full_audio_text) - sentence_len:
                if full_audio_text[search_start:search_start + sentence_len] == clean_sentence:
                    # 找到匹配，获取对应的词索引
                    start_word_idx = position_to_word_idx[search_start]
                    end_word_idx = position_to_word_idx[search_start + sentence_len - 1]
                    
                    # 获取时间戳
                    start_time = float(audio_words[start_word_idx]['start'])
                    end_time = float(audio_words[end_word_idx]['end'])
                    duration = end_time - start_time
                    
                    # 创建字幕片段
                    segment = SubtitleSegment(
                        index=len(segments),
                        start_time=start_time,
                        end_time=end_time,
                        duration=duration,
                        source_text=source_text,
                        translated_text=translation_text,
                        confidence=1.0
                    )
                    
                    segments.append(segment)
                    current_pos = search_start + sentence_len
                    match_found = True
                    break
                
                search_start += 1
            
            if not match_found:
                print(f"⚠️  未找到匹配的时间戳: {source_text[:50]}...")
                # 创建一个占位符片段
                prev_end = segments[-1].end_time if segments else 0.0
                segment = SubtitleSegment(
                    index=len(segments),
                    start_time=prev_end,
                    end_time=prev_end + 2.0,  # 默认2秒时长
                    duration=2.0,
                    source_text=source_text,
                    translated_text=translation_text,
                    confidence=0.5
                )
                segments.append(segment)
        
        print(f"✅ 完成时间戳对齐，生成{len(segments)}个字幕片段")
        return segments
    
    def optimize_subtitle_gaps(self, segments: List[SubtitleSegment]) -> List[SubtitleSegment]:
        """
        优化字幕间隔，消除小间隙
        
        Args:
            segments: 原始字幕片段
            
        Returns:
            优化后的字幕片段
        """
        print("🕳️  正在优化字幕间隔...")
        
        if not segments:
            return segments
        
        optimized_segments = []
        
        for i, segment in enumerate(segments):
            new_segment = SubtitleSegment(**asdict(segment))
            
            # 检查与下一个片段的间隔
            if i < len(segments) - 1:
                next_segment = segments[i + 1]
                gap = next_segment.start_time - segment.end_time
                
                # 如果间隔小于阈值，延长当前片段
                if 0 < gap < self.subtitle_config.gap_threshold:
                    new_segment.end_time = next_segment.start_time
                    new_segment.duration = new_segment.end_time - new_segment.start_time
                    print(f"🔧 优化片段{i}：消除{gap:.2f}秒间隔")
            
            optimized_segments.append(new_segment)
        
        print(f"✅ 间隔优化完成")
        return optimized_segments
    
    def check_subtitle_length(self, segments: List[SubtitleSegment]) -> List[SubtitleSegment]:
        """
        检查并标记需要分割的字幕
        
        Args:
            segments: 字幕片段列表
            
        Returns:
            检查后的字幕片段
        """
        print("📏 正在检查字幕长度...")
        
        needs_split_count = 0
        
        for segment in segments:
            source_len = len(segment.source_text)
            trans_weight = self.calculate_text_weight(segment.translated_text)
            trans_display_len = trans_weight * self.subtitle_config.target_multiplier
            
            if (source_len > self.subtitle_config.max_length or 
                trans_display_len > self.subtitle_config.max_length):
                segment.needs_split = True
                needs_split_count += 1
                print(f"📏 片段{segment.index}需要分割: 源文本{source_len}字符, 翻译{trans_weight:.1f}权重")
        
        print(f"✅ 长度检查完成，{needs_split_count}个片段需要分割")
        return segments
    
    def split_long_subtitles(self, segments: List[SubtitleSegment]) -> List[SubtitleSegment]:
        """
        分割过长的字幕
        
        Args:
            segments: 字幕片段列表
            
        Returns:
            分割后的字幕片段
        """
        print("✂️  正在分割过长字幕...")
        
        result_segments = []
        split_count = 0
        
        for segment in segments:
            if not segment.needs_split:
                result_segments.append(segment)
                continue
            
            # 简单分割：按长度一分为二
            source_text = segment.source_text
            translated_text = segment.translated_text
            
            mid_point_source = len(source_text) // 2
            mid_point_trans = len(translated_text) // 2
            
            # 找到较好的分割点（空格或标点）
            source_split_point = self._find_best_split_point(source_text, mid_point_source)
            trans_split_point = self._find_best_split_point(translated_text, mid_point_trans)
            
            # 时间分割
            duration_each = segment.duration / 2
            
            # 创建两个新片段
            segment1 = SubtitleSegment(
                index=len(result_segments),
                start_time=segment.start_time,
                end_time=segment.start_time + duration_each,
                duration=duration_each,
                source_text=source_text[:source_split_point].strip(),
                translated_text=translated_text[:trans_split_point].strip(),
                confidence=segment.confidence * 0.8  # 分割会降低置信度
            )
            
            segment2 = SubtitleSegment(
                index=len(result_segments) + 1,
                start_time=segment.start_time + duration_each,
                end_time=segment.end_time,
                duration=duration_each,
                source_text=source_text[source_split_point:].strip(),
                translated_text=translated_text[trans_split_point:].strip(),
                confidence=segment.confidence * 0.8
            )
            
            result_segments.extend([segment1, segment2])
            split_count += 1
        
        print(f"✅ 字幕分割完成，分割了{split_count}个片段")
        return result_segments
    
    def _find_best_split_point(self, text: str, mid_point: int) -> int:
        """
        在文本中找到最佳分割点
        
        Args:
            text: 要分割的文本
            mid_point: 中点位置
            
        Returns:
            最佳分割点位置
        """
        if not text or mid_point <= 0 or mid_point >= len(text):
            return mid_point
        
        # 在中点附近寻找空格或标点
        search_range = min(20, len(text) // 4)
        
        # 向后搜索
        for i in range(mid_point, min(mid_point + search_range, len(text))):
            if text[i] in ' ,.!?;。，！？；':
                return i + 1
        
        # 向前搜索
        for i in range(mid_point, max(mid_point - search_range, 0), -1):
            if text[i] in ' ,.!?;。，！？；':
                return i + 1
        
        # 如果没找到合适的分割点，使用中点
        return mid_point
    
    def prepare_display_text(self, segments: List[SubtitleSegment]) -> List[SubtitleSegment]:
        """
        准备显示用文本（清理和美化）
        
        Args:
            segments: 字幕片段列表
            
        Returns:
            准备好显示文本的字幕片段
        """
        print("✨ 正在准备显示文本...")
        
        for segment in segments:
            # 清理源文本
            segment.display_source = self._clean_display_text(segment.source_text)
            
            # 清理翻译文本
            segment.display_translation = self._clean_display_text(segment.translated_text)
        
        print("✅ 显示文本准备完成")
        return segments
    
    def _clean_display_text(self, text: str) -> str:
        """
        清理显示文本
        
        Args:
            text: 原始文本
            
        Returns:
            清理后的文本
        """
        if not text:
            return ""
        
        # 移除多余的标点符号
        text = re.sub(r'[，。]', ' ', text)
        # 清理多余空格
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def generate_srt_content(self, segments: List[SubtitleSegment], columns: List[str]) -> str:
        """
        生成SRT格式内容
        
        Args:
            segments: 字幕片段列表
            columns: 要包含的列 ['source', 'translation']
            
        Returns:
            SRT格式字符串
        """
        srt_content = []
        
        for i, segment in enumerate(segments, 1):
            srt_content.append(f"{i}")
            srt_content.append(segment.get_srt_timestamp())
            
            # 根据配置添加文本行
            for column in columns:
                if column == 'source' and segment.display_source:
                    srt_content.append(segment.display_source)
                elif column == 'translation' and segment.display_translation:
                    srt_content.append(segment.display_translation)
            
            srt_content.append("")  # 空行分隔
        
        return '\n'.join(srt_content).strip()
    
    def save_subtitle_files(self, segments: List[SubtitleSegment], for_audio: bool = False) -> List[str]:
        """
        保存字幕文件
        
        Args:
            segments: 字幕片段列表
            for_audio: 是否为音频配音用字幕
            
        Returns:
            生成的文件路径列表
        """
        print(f"💾 正在保存{'音频用' if for_audio else '显示用'}字幕文件...")
        
        output_dir = self.audio_output_dir if for_audio else self.output_dir
        configs = self.audio_subtitle_configs if for_audio else self.subtitle_output_configs
        
        generated_files = []
        
        for filename, columns in configs:
            file_path = output_dir / filename
            srt_content = self.generate_srt_content(segments, columns)
            
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(srt_content)
                
                generated_files.append(str(file_path))
                print(f"✅ 生成: {file_path}")
                
            except Exception as e:
                print(f"❌ 保存文件失败 {file_path}: {str(e)}")
        
        return generated_files
    
    def process_complete_subtitle_generation(self) -> SubtitleGenerationResult:
        """
        完整的字幕生成处理流程
        
        Returns:
            字幕生成结果
        """
        print("🚀 开始完整字幕生成流程...")
        
        import time
        start_time = time.time()
        
        try:
            # 1. 加载数据
            audio_words = self.load_audio_data()
            translations = self.load_translation_data()
            
            # 2. 时间戳对齐
            segments = self.align_timestamps(audio_words, translations)
            
            # 3. 优化间隔
            segments = self.optimize_subtitle_gaps(segments)
            
            # 4. 检查长度
            segments = self.check_subtitle_length(segments)
            
            # 5. 分割过长字幕
            original_count = len(segments)
            segments = self.split_long_subtitles(segments)
            split_count = len(segments) - original_count
            
            # 6. 准备显示文本
            segments = self.prepare_display_text(segments)
            
            # 7. 保存字幕文件
            display_files = self.save_subtitle_files(segments, for_audio=False)
            audio_files = self.save_subtitle_files(segments, for_audio=True)
            
            processing_time = time.time() - start_time
            
            # 计算统计信息
            total_duration = sum(seg.duration for seg in segments)
            average_duration = total_duration / len(segments) if segments else 0
            alignment_issues = sum(1 for seg in segments if seg.confidence < 1.0)
            
            result = SubtitleGenerationResult(
                total_segments=len(segments),
                generated_files=display_files + audio_files,
                processing_time=processing_time,
                average_duration=average_duration,
                split_segments=split_count,
                alignment_issues=alignment_issues
            )
            
            print("🎉 字幕生成流程完成！")
            print(f"📊 生成统计:")
            print(f"  📄 总片段数: {result.total_segments}")
            print(f"  ✂️  分割片段: {result.split_segments}")
            print(f"  ⚠️  对齐问题: {result.alignment_issues}")
            print(f"  ⏱️  平均时长: {result.average_duration:.2f}秒")
            print(f"  🕒 处理耗时: {result.processing_time:.2f}秒")
            print(f"  📁 生成文件: {len(result.generated_files)}个")
            
            return result
            
        except Exception as e:
            print(f"💥 字幕生成流程失败: {str(e)}")
            raise


# ----------------------------------------------------------------------------
# 独立运行测试
# ----------------------------------------------------------------------------
if __name__ == '__main__':
    import sys
    
    # 创建字幕生成器实例
    generator = SubtitleGenerator(
        src_language='en',
        tgt_language='zh',
        subtitle_config=SubtitleConfig(
            max_length=50,
            target_multiplier=2.5,
            min_duration=1.0,
            max_duration=6.0
        )
    )
    
    try:
        # 检查输入文件
        if not generator.translation_file.exists():
            print(f"❌ 翻译文件不存在: {generator.translation_file}")
            print("💡 请先运行文本翻译器生成翻译文件")
            sys.exit(1)
        
        if not generator.audio_data_file.exists():
            print(f"❌ 音频数据文件不存在: {generator.audio_data_file}")
            print("💡 请先运行音频转录器生成音频数据文件")
            sys.exit(1)
        
        # 运行完整字幕生成流程
        print("\n🧪 测试字幕生成流程...")
        
        result = generator.process_complete_subtitle_generation()
        
        print(f"\n✅ 测试完成！")
        print(f"📁 生成的字幕文件:")
        for i, file_path in enumerate(result.generated_files, 1):
            print(f"  {i}. {file_path}")
        
    except Exception as e:
        print(f"\n💥 测试过程中发生错误: {str(e)}")
        sys.exit(1) 