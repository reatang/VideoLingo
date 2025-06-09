"""
# ----------------------------------------------------------------------------
# TTS工具函数
# 
# 提供TTS相关的工具函数，包括：
# - 音频处理和验证
# - 文本预处理和清理
# - 音频文件合并和转换
# - 时长估算和速度调整
# ----------------------------------------------------------------------------
"""

import os
import re
import time
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from .base import TTSResult, AudioSegment


class TTSProcessor:
    """TTS处理器 - 提供音频和文本处理功能"""
    
    def __init__(self):
        """初始化TTS处理器"""
        self.temp_files: List[str] = []
    
    def preprocess_text(self, text: str, language: str = "zh-CN") -> str:
        """
        预处理文本，优化TTS合成效果
        
        Args:
            text: 原始文本
            language: 语言代码
            
        Returns:
            处理后的文本
        """
        if not text:
            return ""
        
        # 移除多余空白符
        text = re.sub(r'\s+', ' ', text.strip())
        
        # 处理特殊字符
        text = self._handle_special_characters(text, language)
        
        # 处理数字和符号
        text = self._handle_numbers_and_symbols(text, language)
        
        # 处理标点符号
        text = self._normalize_punctuation(text, language)
        
        return text
    
    def _handle_special_characters(self, text: str, language: str) -> str:
        """处理特殊字符"""
        # 移除或替换不适合TTS的字符
        text = text.replace('…', '...')
        text = text.replace('—', '-')
        text = text.replace('–', '-')
        text = text.replace('"', '"')
        text = text.replace('"', '"')
        text = text.replace(''', "'")
        text = text.replace(''', "'")
        
        # 移除HTML标签
        text = re.sub(r'<[^>]+>', '', text)
        
        # 移除特殊符号（保留基本标点）
        if language.startswith('zh'):
            # 中文保留中文标点
            text = re.sub(r'[^\u4e00-\u9fff\w\s，。！？；：、""''（）【】〔〕『』「」.,!?;:()\[\]{}\'"-]', '', text)
        else:
            # 英文保留英文标点
            text = re.sub(r'[^\w\s.,!?;:()\[\]{}\'"-]', '', text)
        
        return text
    
    def _handle_numbers_and_symbols(self, text: str, language: str) -> str:
        """处理数字和符号"""
        # 处理百分号
        text = re.sub(r'(\d+)%', r'\1 percent', text)
        
        # 处理货币符号
        text = re.sub(r'\$(\d+)', r'\1 dollars', text)
        text = re.sub(r'¥(\d+)', r'\1 yuan', text)
        
        # 处理URL和邮箱（简单移除）
        text = re.sub(r'http[s]?://\S+', '', text)
        text = re.sub(r'\S+@\S+\.\S+', '', text)
        
        return text
    
    def _normalize_punctuation(self, text: str, language: str) -> str:
        """标准化标点符号"""
        # 处理连续标点
        text = re.sub(r'[.]{3,}', '...', text)
        text = re.sub(r'[!]{2,}', '!', text)
        text = re.sub(r'[?]{2,}', '?', text)
        
        # 确保句子结尾有标点
        if text and not text[-1] in '.!?。！？':
            if language.startswith('zh'):
                text += '。'
            else:
                text += '.'
        
        return text
    
    def split_text_by_length(self, text: str, max_length: int = 100) -> List[str]:
        """
        按长度分割文本
        
        Args:
            text: 原始文本
            max_length: 最大长度
            
        Returns:
            分割后的文本列表
        """
        if len(text) <= max_length:
            return [text]
        
        chunks = []
        # 按句子分割
        sentences = re.split(r'[.!?。！？]', text)
        current_chunk = ""
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # 如果加上这个句子超过长度限制
            if len(current_chunk) + len(sentence) > max_length:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = sentence
                else:
                    # 单个句子太长，强制分割
                    chunks.extend(self._force_split_text(sentence, max_length))
            else:
                current_chunk += sentence + "。"
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _force_split_text(self, text: str, max_length: int) -> List[str]:
        """强制按长度分割文本"""
        chunks = []
        for i in range(0, len(text), max_length):
            chunks.append(text[i:i + max_length])
        return chunks
    
    def merge_audio_files(self, audio_paths: List[str], 
                         output_path: str,
                         crossfade_duration: float = 0.1) -> str:
        """
        合并多个音频文件
        
        Args:
            audio_paths: 音频文件路径列表
            output_path: 输出文件路径
            crossfade_duration: 交叉淡化时长（秒）
            
        Returns:
            合并后的音频文件路径
        """
        try:
            from pydub import AudioSegment
            
            if not audio_paths:
                raise ValueError("❌ 没有音频文件需要合并")
            
            # 加载第一个音频文件
            merged_audio = AudioSegment.from_file(audio_paths[0])
            
            # 依次合并其他音频文件
            for audio_path in audio_paths[1:]:
                if not os.path.exists(audio_path):
                    print(f"⚠️  音频文件不存在，跳过: {audio_path}")
                    continue
                
                next_audio = AudioSegment.from_file(audio_path)
                
                # 添加交叉淡化效果
                if crossfade_duration > 0:
                    crossfade_ms = int(crossfade_duration * 1000)
                    merged_audio = merged_audio.append(next_audio, crossfade=crossfade_ms)
                else:
                    merged_audio = merged_audio + next_audio
            
            # 导出合并后的音频
            merged_audio.export(output_path, format="wav")
            
            print(f"✅ 音频合并完成: {output_path}")
            return output_path
            
        except ImportError:
            print("❌ 缺少pydub库，无法合并音频")
            raise
        except Exception as e:
            print(f"❌ 音频合并失败: {e}")
            raise
    
    def adjust_audio_speed(self, audio_path: str, 
                          speed_factor: float,
                          output_path: Optional[str] = None) -> str:
        """
        调整音频播放速度
        
        Args:
            audio_path: 输入音频文件路径
            speed_factor: 速度倍数（1.0=原速，>1.0=加速，<1.0=减速）
            output_path: 输出文件路径（可选）
            
        Returns:
            调整后的音频文件路径
        """
        try:
            from pydub import AudioSegment
            
            if not os.path.exists(audio_path):
                raise FileNotFoundError(f"❌ 音频文件不存在: {audio_path}")
            
            if output_path is None:
                name, ext = os.path.splitext(audio_path)
                output_path = f"{name}_speed_{speed_factor:.1f}{ext}"
            
            # 加载音频
            audio = AudioSegment.from_file(audio_path)
            
            # 调整速度（通过改变帧率实现）
            # 注意：这会同时改变音调
            new_sample_rate = int(audio.frame_rate * speed_factor)
            adjusted_audio = audio._spawn(audio.raw_data, overrides={"frame_rate": new_sample_rate})
            adjusted_audio = adjusted_audio.set_frame_rate(audio.frame_rate)
            
            # 导出调整后的音频
            adjusted_audio.export(output_path, format="wav")
            
            print(f"✅ 音频速度调整完成: {output_path} (倍速: {speed_factor:.1f})")
            return output_path
            
        except ImportError:
            print("❌ 缺少pydub库，无法调整音频速度")
            raise
        except Exception as e:
            print(f"❌ 音频速度调整失败: {e}")
            raise
    
    def get_audio_duration(self, audio_path: str) -> float:
        """
        获取音频文件时长
        
        Args:
            audio_path: 音频文件路径
            
        Returns:
            音频时长（秒）
        """
        try:
            from pydub import AudioSegment
            
            if not os.path.exists(audio_path):
                raise FileNotFoundError(f"❌ 音频文件不存在: {audio_path}")
            
            audio = AudioSegment.from_file(audio_path)
            duration = len(audio) / 1000.0  # 转换为秒
            
            return duration
            
        except ImportError:
            print("❌ 缺少pydub库，无法获取音频时长")
            return 0.0
        except Exception as e:
            print(f"❌ 获取音频时长失败: {e}")
            return 0.0
    
    def normalize_audio_volume(self, audio_path: str, 
                             target_db: float = -20.0,
                             output_path: Optional[str] = None) -> str:
        """
        标准化音频音量
        
        Args:
            audio_path: 输入音频文件路径
            target_db: 目标音量（dBFS）
            output_path: 输出文件路径（可选）
            
        Returns:
            标准化后的音频文件路径
        """
        try:
            from pydub import AudioSegment
            
            if not os.path.exists(audio_path):
                raise FileNotFoundError(f"❌ 音频文件不存在: {audio_path}")
            
            if output_path is None:
                name, ext = os.path.splitext(audio_path)
                output_path = f"{name}_normalized{ext}"
            
            # 加载音频
            audio = AudioSegment.from_file(audio_path)
            
            # 计算当前音量
            current_db = audio.dBFS
            
            # 计算需要调整的音量
            db_change = target_db - current_db
            
            # 调整音量
            normalized_audio = audio + db_change
            
            # 导出标准化后的音频
            normalized_audio.export(output_path, format="wav")
            
            print(f"✅ 音频音量标准化完成: {output_path} ({current_db:.1f}dB -> {target_db:.1f}dB)")
            return output_path
            
        except ImportError:
            print("❌ 缺少pydub库，无法标准化音频音量")
            raise
        except Exception as e:
            print(f"❌ 音频音量标准化失败: {e}")
            raise
    
    def cleanup_temp_files(self) -> None:
        """清理临时文件"""
        for filepath in self.temp_files:
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
                    print(f"🗑️  已清理临时文件: {filepath}")
            except Exception as e:
                print(f"⚠️  清理临时文件失败: {filepath} - {e}")
        
        self.temp_files.clear()


def validate_audio_output(audio_path: str, min_size: int = 1024) -> bool:
    """
    验证音频输出文件
    
    Args:
        audio_path: 音频文件路径
        min_size: 最小文件大小（字节）
        
    Returns:
        文件是否有效
    """
    if not audio_path or not os.path.exists(audio_path):
        print(f"❌ 音频文件不存在: {audio_path}")
        return False
    
    # 检查文件大小
    file_size = os.path.getsize(audio_path)
    if file_size < min_size:
        print(f"❌ 音频文件过小: {audio_path} ({file_size} bytes)")
        return False
    
    # 检查文件格式（简单检查）
    valid_extensions = ['.wav', '.mp3', '.mp4', '.flac', '.aac', '.ogg']
    if not any(audio_path.lower().endswith(ext) for ext in valid_extensions):
        print(f"❌ 不支持的音频格式: {audio_path}")
        return False
    
    return True


def estimate_synthesis_duration(text: str, 
                              engine_type: str = "edge_tts",
                              language: str = "zh-CN") -> float:
    """
    估算TTS合成时长
    
    Args:
        text: 文本内容
        engine_type: TTS引擎类型
        language: 语言
        
    Returns:
        估算的合成时长（秒）
    """
    char_count = len(text)
    
    # 基于语言的基础估算
    if language.startswith('zh'):
        # 中文：约2字符/秒
        base_duration = char_count / 2.0
    else:
        # 英文：约4字符/秒
        base_duration = char_count / 4.0
    
    # 基于引擎类型的修正系数
    engine_factors = {
        'edge_tts': 1.0,      # 基准
        'azure_tts': 1.0,     # 类似Edge
        'openai_tts': 0.9,    # 稍快
        'sf_fish_tts': 1.1,   # 稍慢
        'fish_tts': 1.1,      # 稍慢
        'gpt_sovits': 1.2,    # 本地模型较慢
        'f5tts': 1.3,         # 较慢
        'custom_tts': 1.0     # 默认
    }
    
    factor = engine_factors.get(engine_type, 1.0)
    estimated_duration = base_duration * factor
    
    return max(estimated_duration, 0.5)  # 最少0.5秒


def create_silence_audio(duration: float, output_path: str) -> str:
    """
    创建静音音频文件
    
    Args:
        duration: 静音时长（秒）
        output_path: 输出文件路径
        
    Returns:
        静音音频文件路径
    """
    try:
        from pydub import AudioSegment
        
        # 创建静音音频（44.1kHz采样率）
        silence = AudioSegment.silent(duration=int(duration * 1000))
        
        # 导出静音音频
        silence.export(output_path, format="wav")
        
        print(f"✅ 静音音频创建完成: {output_path} ({duration:.1f}s)")
        return output_path
        
    except ImportError:
        print("❌ 缺少pydub库，无法创建静音音频")
        raise
    except Exception as e:
        print(f"❌ 静音音频创建失败: {e}")
        raise


def generate_unique_filename(text: str, 
                           engine_type: str,
                           extension: str = ".wav",
                           output_dir: str = "output/audio") -> str:
    """
    生成唯一的文件名
    
    Args:
        text: 文本内容
        engine_type: TTS引擎类型
        extension: 文件扩展名
        output_dir: 输出目录
        
    Returns:
        唯一的文件路径
    """
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 使用文本哈希和时间戳生成唯一文件名
    text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()[:8]
    timestamp = int(time.time() * 1000) % 10000
    
    filename = f"tts_{engine_type}_{text_hash}_{timestamp}{extension}"
    return os.path.join(output_dir, filename)


def convert_audio_format(input_path: str, 
                        output_path: str,
                        output_format: str = "wav") -> str:
    """
    转换音频格式
    
    Args:
        input_path: 输入音频文件路径
        output_path: 输出音频文件路径
        output_format: 输出格式
        
    Returns:
        转换后的音频文件路径
    """
    try:
        from pydub import AudioSegment
        
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"❌ 输入音频文件不存在: {input_path}")
        
        # 加载音频
        audio = AudioSegment.from_file(input_path)
        
        # 转换格式
        audio.export(output_path, format=output_format)
        
        print(f"✅ 音频格式转换完成: {output_path}")
        return output_path
        
    except ImportError:
        print("❌ 缺少pydub库，无法转换音频格式")
        raise
    except Exception as e:
        print(f"❌ 音频格式转换失败: {e}")
        raise


def batch_process_audio_files(audio_paths: List[str],
                            processor_func,
                            output_dir: str,
                            **kwargs) -> List[str]:
    """
    批量处理音频文件
    
    Args:
        audio_paths: 音频文件路径列表
        processor_func: 处理函数
        output_dir: 输出目录
        **kwargs: 处理函数的额外参数
        
    Returns:
        处理后的音频文件路径列表
    """
    os.makedirs(output_dir, exist_ok=True)
    processed_paths = []
    
    for i, audio_path in enumerate(audio_paths):
        try:
            # 生成输出路径
            name = Path(audio_path).stem
            output_path = os.path.join(output_dir, f"{name}_processed.wav")
            
            # 调用处理函数
            result_path = processor_func(audio_path, output_path, **kwargs)
            processed_paths.append(result_path)
            
            print(f"✅ 处理完成 ({i+1}/{len(audio_paths)}): {result_path}")
            
        except Exception as e:
            print(f"❌ 处理失败 ({i+1}/{len(audio_paths)}): {audio_path} - {e}")
            continue
    
    return processed_paths 