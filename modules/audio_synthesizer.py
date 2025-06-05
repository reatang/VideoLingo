"""
# ----------------------------------------------------------------------------
# 音频合成器模块 - 基于适配器模式的多TTS后端音频合成
# 
# 核心功能：
# 1. 统一的TTS后端适配器接口设计
# 2. 多种TTS引擎支持和动态切换
# 3. 智能音频速度调节和时长匹配
# 4. 并行音频生成和批处理优化
# 5. 音频质量检测和自动修复
# 6. 参考音频管理和语音克隆
# 
# 输入：字幕SRT文件，音频任务数据
# 输出：高质量音频配音文件
# 
# 设计原则：
# - 使用适配器模式统一不同TTS后端的接口
# - 支持语音克隆和参考音频功能
# - 智能错误处理和降级策略
# - 高效的并行处理和资源管理
# ----------------------------------------------------------------------------
"""

import os
import re
import json
import time
import shutil
import subprocess
from typing import List, Dict, Optional, Tuple, Any, Protocol, Union
from pathlib import Path
import concurrent.futures
from dataclasses import dataclass, asdict
from collections import defaultdict
from abc import ABC, abstractmethod
import warnings

warnings.filterwarnings("ignore", category=FutureWarning)


@dataclass
class AudioTask:
    """音频任务数据类"""
    number: int                    # 任务编号
    text: str                     # 文本内容
    start_time: str               # 开始时间
    end_time: str                 # 结束时间
    duration: float               # 目标时长
    tolerance: float = 0.0        # 容忍度
    reference_audio: str = ""     # 参考音频路径
    reference_text: str = ""      # 参考音频文本
    priority: int = 1             # 优先级


@dataclass
class AudioSegment:
    """音频片段数据类"""
    task_number: int              # 任务编号
    segment_index: int            # 片段索引
    text: str                     # 文本内容
    file_path: str                # 音频文件路径
    duration: float = 0.0         # 实际时长
    confidence: float = 1.0       # 质量置信度
    speed_factor: float = 1.0     # 速度因子


@dataclass
class SynthesisResult:
    """合成结果数据类"""
    total_tasks: int              # 总任务数
    successful_tasks: int         # 成功任务数
    failed_tasks: int             # 失败任务数
    total_duration: float         # 总时长
    processing_time: float        # 处理时间
    output_files: List[str]       # 输出文件列表
    segments: List[AudioSegment] = None  # 详细片段信息
    
    def __post_init__(self):
        if self.segments is None:
            self.segments = []


# ----------------------------------------------------------------------------
# TTS适配器接口和实现
# ----------------------------------------------------------------------------

class TTSAdapter(ABC):
    """TTS适配器抽象基类"""
    
    @abstractmethod
    def synthesize(self, text: str, output_path: str, **kwargs) -> bool:
        """
        合成语音
        
        Args:
            text: 要合成的文本
            output_path: 输出文件路径
            **kwargs: 其他参数
            
        Returns:
            是否成功
        """
        pass
    
    @abstractmethod
    def supports_voice_cloning(self) -> bool:
        """是否支持语音克隆"""
        pass
    
    @abstractmethod
    def get_adapter_name(self) -> str:
        """获取适配器名称"""
        pass
    
    def cleanup_text(self, text: str) -> str:
        """文本清理（通用方法）"""
        if not text:
            return ""
        
        # 移除有问题的字符
        problematic_chars = ['&', '®', '™', '©', '\x00', '\x08', '\x0b', '\x0c']
        for char in problematic_chars:
            text = text.replace(char, '')
        
        # 清理多余空格和换行
        text = re.sub(r'\s+', ' ', text)
        return text.strip()


class OpenAITTSAdapter(TTSAdapter):
    """OpenAI TTS适配器"""
    
    def __init__(self, api_key: str, voice: str = "alloy", base_url: str = "https://api.302.ai/v1/audio/speech"):
        self.api_key = api_key
        self.voice = voice
        self.base_url = base_url
        self.voice_list = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
    
    def synthesize(self, text: str, output_path: str, **kwargs) -> bool:
        """OpenAI TTS合成"""
        try:
            import requests
            
            text = self.cleanup_text(text)
            if not text:
                return False
            
            if self.voice not in self.voice_list:
                raise ValueError(f"Invalid voice: {self.voice}. Choose from {self.voice_list}")
            
            payload = {
                "model": "tts-1",
                "input": text,
                "voice": self.voice,
                "response_format": "wav"
            }
            
            headers = {
                'Authorization': f"Bearer {self.api_key}",
                'Content-Type': 'application/json'
            }
            
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            response = requests.post(self.base_url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                with open(output_file, 'wb') as f:
                    f.write(response.content)
                return True
            else:
                print(f"❌ OpenAI TTS failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ OpenAI TTS error: {str(e)}")
            return False
    
    def supports_voice_cloning(self) -> bool:
        return False
    
    def get_adapter_name(self) -> str:
        return "OpenAI TTS"


class AzureTTSAdapter(TTSAdapter):
    """Azure TTS适配器"""
    
    def __init__(self, api_key: str, voice: str = "zh-CN-YunfengNeural", url: str = "https://api.302.ai/cognitiveservices/v1"):
        self.api_key = api_key
        self.voice = voice
        self.url = url
    
    def synthesize(self, text: str, output_path: str, **kwargs) -> bool:
        """Azure TTS合成"""
        try:
            import requests
            
            text = self.cleanup_text(text)
            if not text:
                return False
            
            payload = f"""<speak version='1.0' xml:lang='zh-CN'><voice name='{self.voice}'>{text}</voice></speak>"""
            
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'X-Microsoft-OutputFormat': 'riff-16khz-16bit-mono-pcm',
                'Content-Type': 'application/ssml+xml'
            }
            
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            response = requests.post(self.url, headers=headers, data=payload, timeout=30)
            
            if response.status_code == 200:
                with open(output_file, 'wb') as f:
                    f.write(response.content)
                return True
            else:
                print(f"❌ Azure TTS failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Azure TTS error: {str(e)}")
            return False
    
    def supports_voice_cloning(self) -> bool:
        return False
    
    def get_adapter_name(self) -> str:
        return "Azure TTS"


class EdgeTTSAdapter(TTSAdapter):
    """Edge TTS适配器"""
    
    def __init__(self, voice: str = "zh-CN-XiaoxiaoNeural"):
        self.voice = voice
    
    def synthesize(self, text: str, output_path: str, **kwargs) -> bool:
        """Edge TTS合成"""
        try:
            import subprocess
            
            text = self.cleanup_text(text)
            if not text:
                return False
            
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            cmd = ["edge-tts", "--voice", self.voice, "--text", text, "--write-media", str(output_file)]
            
            result = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=30)
            
            return output_file.exists() and output_file.stat().st_size > 0
                
        except Exception as e:
            print(f"❌ Edge TTS error: {str(e)}")
            return False
    
    def supports_voice_cloning(self) -> bool:
        return False
    
    def get_adapter_name(self) -> str:
        return "Edge TTS"


class FishTTSAdapter(TTSAdapter):
    """Fish TTS适配器 (支持语音克隆)"""
    
    def __init__(self, api_key: str, character: str = "AD学姐", character_id: str = ""):
        self.api_key = api_key
        self.character = character
        self.character_id = character_id
        self.base_url = "https://api.siliconflow.cn/v1/audio/speech"
    
    def synthesize(self, text: str, output_path: str, **kwargs) -> bool:
        """Fish TTS合成"""
        try:
            import requests
            import base64
            
            text = self.cleanup_text(text)
            if not text:
                return False
            
            mode = kwargs.get('mode', 'preset')
            reference_audio = kwargs.get('reference_audio')
            reference_text = kwargs.get('reference_text')
            
            headers = {
                "Authorization": f'Bearer {self.api_key}',
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "fishaudio/fish-speech-1.4",
                "response_format": "wav",
                "stream": False,
                "input": text
            }
            
            if mode == "preset":
                payload["voice"] = f"fishaudio/fish-speech-1.4:{self.character}"
            elif mode == "custom" and self.character_id:
                payload["voice"] = self.character_id
            elif mode == "dynamic" and reference_audio and reference_text:
                with open(reference_audio, 'rb') as f:
                    audio_base64 = base64.b64encode(f.read()).decode('utf-8')
                payload.update({
                    "voice": None,
                    "references": [{"audio": f"data:audio/wav;base64,{audio_base64}", "text": reference_text}]
                })
            
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            response = requests.post(self.base_url, json=payload, headers=headers, timeout=60)
            
            if response.status_code == 200:
                with open(output_file, 'wb') as f:
                    f.write(response.content)
                return True
            else:
                print(f"❌ Fish TTS failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Fish TTS error: {str(e)}")
            return False
    
    def supports_voice_cloning(self) -> bool:
        return True
    
    def get_adapter_name(self) -> str:
        return "Fish TTS"


class CustomTTSAdapter(TTSAdapter):
    """自定义TTS适配器"""
    
    def __init__(self, custom_function: Optional[callable] = None):
        self.custom_function = custom_function
    
    def synthesize(self, text: str, output_path: str, **kwargs) -> bool:
        """自定义TTS合成"""
        try:
            text = self.cleanup_text(text)
            if not text:
                return False
            
            if self.custom_function:
                return self.custom_function(text, output_path, **kwargs)
            else:
                # 默认实现：创建静默音频
                print(f"⚠️  使用默认静默音频: {output_path}")
                output_file = Path(output_path)
                output_file.parent.mkdir(parents=True, exist_ok=True)
                
                # 创建100ms的静默音频
                try:
                    from pydub import AudioSegment
                    silence = AudioSegment.silent(duration=100)
                    silence.export(output_file, format="wav")
                    return True
                except ImportError:
                    # 如果没有pydub，创建空文件
                    output_file.touch()
                    return True
                
        except Exception as e:
            print(f"❌ Custom TTS error: {str(e)}")
            return False
    
    def supports_voice_cloning(self) -> bool:
        return False
    
    def get_adapter_name(self) -> str:
        return "Custom TTS"


# ----------------------------------------------------------------------------
# TTS适配器工厂
# ----------------------------------------------------------------------------

class TTSAdapterFactory:
    """TTS适配器工厂类"""
    
    @staticmethod
    def create_adapter(tts_type: str, config: Dict[str, Any]) -> TTSAdapter:
        """
        创建TTS适配器
        
        Args:
            tts_type: TTS类型
            config: 配置参数
            
        Returns:
            TTS适配器实例
        """
        if tts_type == "openai_tts":
            return OpenAITTSAdapter(
                api_key=config.get("api_key", ""),
                voice=config.get("voice", "alloy")
            )
        elif tts_type == "azure_tts":
            return AzureTTSAdapter(
                api_key=config.get("api_key", ""),
                voice=config.get("voice", "zh-CN-YunfengNeural")
            )
        elif tts_type == "edge_tts":
            return EdgeTTSAdapter(
                voice=config.get("voice", "zh-CN-XiaoxiaoNeural")
            )
        elif tts_type == "fish_tts" or tts_type == "sf_fish_tts":
            return FishTTSAdapter(
                api_key=config.get("api_key", ""),
                character=config.get("character", "AD学姐"),
                character_id=config.get("character_id", "")
            )
        elif tts_type == "custom_tts":
            return CustomTTSAdapter(
                custom_function=config.get("custom_function")
            )
        else:
            raise ValueError(f"❌ 不支持的TTS类型: {tts_type}")


# ----------------------------------------------------------------------------
# 音频合成器主类
# ----------------------------------------------------------------------------

class AudioSynthesizer:
    """音频合成器类 - 基于适配器模式的多TTS后端音频合成"""
    
    def __init__(self,
                 subtitle_file: str = 'output/trans_subs_for_audio.srt',
                 audio_task_file: str = 'output/log/8_1_audio_task.xlsx',
                 output_dir: str = 'output/audio_segments',
                 temp_dir: str = 'output/audio_temp',
                 tts_config: Optional[Dict] = None,
                 max_workers: int = 4,
                 max_retries: int = 3):
        """
        初始化音频合成器
        
        Args:
            subtitle_file: 字幕文件路径
            audio_task_file: 音频任务文件路径
            output_dir: 输出目录
            temp_dir: 临时文件目录
            tts_config: TTS配置
            max_workers: 最大并行数
            max_retries: 最大重试次数
        """
        self.subtitle_file = Path(subtitle_file)
        self.audio_task_file = Path(audio_task_file)
        self.output_dir = Path(output_dir)
        self.temp_dir = Path(temp_dir)
        self.tts_config = tts_config or {}
        self.max_workers = max_workers
        self.max_retries = max_retries
        
        # 创建目录
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # 懒加载依赖
        self._pd = None
        self._tts_adapter = None
        
        # 内部状态
        self._audio_tasks = []
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
    
    def set_tts_adapter(self, tts_type: str, config: Dict[str, Any]):
        """
        设置TTS适配器
        
        Args:
            tts_type: TTS类型
            config: 配置参数
        """
        self._tts_adapter = TTSAdapterFactory.create_adapter(tts_type, config)
        print(f"✅ 设置TTS适配器: {self._tts_adapter.get_adapter_name()}")
    
    def load_audio_tasks(self) -> List[AudioTask]:
        """
        加载音频任务
        
        Returns:
            音频任务列表
        """
        print(f"📖 正在加载音频任务: {self.audio_task_file}")
        
        if not self.audio_task_file.exists():
            raise FileNotFoundError(f"❌ 音频任务文件不存在: {self.audio_task_file}")
        
        try:
            pd = self._get_pandas()
            df = pd.read_excel(self.audio_task_file)
            
            # 检查必需的列
            required_columns = ['number', 'text', 'start_time', 'end_time', 'duration']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(f"❌ 音频任务文件缺少必需列: {missing_columns}")
            
            tasks = []
            for _, row in df.iterrows():
                if pd.notna(row['text']):
                    task = AudioTask(
                        number=int(row['number']),
                        text=str(row['text']).strip(),
                        start_time=str(row['start_time']),
                        end_time=str(row['end_time']),
                        duration=float(row['duration']),
                        tolerance=float(row.get('tolerance', 0.0)),
                        reference_audio=str(row.get('reference_audio', '')),
                        reference_text=str(row.get('reference_text', ''))
                    )
                    tasks.append(task)
            
            print(f"✅ 加载了{len(tasks)}个音频任务")
            return tasks
            
        except Exception as e:
            print(f"❌ 加载音频任务失败: {str(e)}")
            raise
    
    def get_audio_duration(self, file_path: str) -> float:
        """
        获取音频文件时长
        
        Args:
            file_path: 音频文件路径
            
        Returns:
            时长（秒）
        """
        try:
            if not os.path.exists(file_path):
                return 0.0
            
            # 尝试使用ffprobe
            cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', '-of', 'csv=p=0', file_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                return float(result.stdout.strip())
            
            # 备选方案：使用pydub
            try:
                from pydub import AudioSegment
                audio = AudioSegment.from_file(file_path)
                return len(audio) / 1000.0
            except ImportError:
                pass
            
            return 0.0
            
        except Exception:
            return 0.0
    
    def adjust_audio_speed(self, input_file: str, output_file: str, speed_factor: float) -> bool:
        """
        调整音频速度
        
        Args:
            input_file: 输入文件
            output_file: 输出文件
            speed_factor: 速度因子
            
        Returns:
            是否成功
        """
        try:
            # 如果速度因子接近1，直接复制文件
            if abs(speed_factor - 1.0) < 0.001:
                shutil.copy2(input_file, output_file)
                return True
            
            # 使用ffmpeg调整速度
            cmd = [
                'ffmpeg', '-i', input_file,
                '-filter:a', f'atempo={speed_factor}',
                '-y', output_file
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                return True
            else:
                print(f"❌ 速度调整失败: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ 速度调整错误: {str(e)}")
            return False
    
    def synthesize_single_task(self, task: AudioTask) -> List[AudioSegment]:
        """
        合成单个任务的音频
        
        Args:
            task: 音频任务
            
        Returns:
            音频片段列表
        """
        if not self._tts_adapter:
            raise ValueError("❌ 未设置TTS适配器")
        
        segments = []
        
        # 分割文本（如果需要）
        lines = self._split_task_text(task.text)
        
        for i, line in enumerate(lines):
            if not line.strip():
                continue
            
            # 生成临时文件路径
            temp_file = self.temp_dir / f"{task.number}_{i}_temp.wav"
            
            # 尝试合成音频
            success = False
            for attempt in range(self.max_retries):
                try:
                    kwargs = {}
                    
                    # 如果支持语音克隆，添加参考音频
                    if (self._tts_adapter.supports_voice_cloning() and 
                        task.reference_audio and 
                        Path(task.reference_audio).exists()):
                        kwargs.update({
                            'mode': 'dynamic',
                            'reference_audio': task.reference_audio,
                            'reference_text': task.reference_text
                        })
                    
                    success = self._tts_adapter.synthesize(line, str(temp_file), **kwargs)
                    
                    if success and self.get_audio_duration(str(temp_file)) > 0:
                        break
                    
                    if attempt < self.max_retries - 1:
                        print(f"⚠️  任务{task.number}片段{i}重试 {attempt + 1}/{self.max_retries}")
                        time.sleep(1)
                        
                except Exception as e:
                    print(f"❌ 任务{task.number}片段{i}合成失败: {str(e)}")
                    if attempt == self.max_retries - 1:
                        break
            
            # 创建音频片段
            segment = AudioSegment(
                task_number=task.number,
                segment_index=i,
                text=line,
                file_path=str(temp_file),
                duration=self.get_audio_duration(str(temp_file)) if success else 0.0,
                confidence=1.0 if success else 0.0
            )
            
            segments.append(segment)
        
        return segments
    
    def _split_task_text(self, text: str) -> List[str]:
        """
        分割任务文本（如果太长）
        
        Args:
            text: 原始文本
            
        Returns:
            分割后的文本列表
        """
        # 简单实现：如果文本超过100字符，按句号分割
        if len(text) <= 100:
            return [text]
        
        # 按句号分割
        sentences = re.split(r'[。！？.!?]', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        return sentences if sentences else [text]
    
    def process_audio_synthesis(self) -> SynthesisResult:
        """
        处理完整的音频合成流程
        
        Returns:
            合成结果
        """
        print("🚀 开始音频合成流程...")
        
        start_time = time.time()
        
        try:
            # 1. 加载音频任务
            tasks = self.load_audio_tasks()
            
            if not self._tts_adapter:
                raise ValueError("❌ 未设置TTS适配器")
            
            # 2. 并行处理任务
            all_segments = []
            successful_tasks = 0
            failed_tasks = 0
            
            print(f"🎯 使用{self._tts_adapter.get_adapter_name()}开始合成...")
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # 提交所有任务
                future_to_task = {
                    executor.submit(self.synthesize_single_task, task): task 
                    for task in tasks
                }
                
                # 收集结果
                for future in concurrent.futures.as_completed(future_to_task):
                    task = future_to_task[future]
                    try:
                        segments = future.result()
                        all_segments.extend(segments)
                        
                        # 检查任务是否成功
                        if any(seg.confidence > 0 for seg in segments):
                            successful_tasks += 1
                            print(f"✅ 任务{task.number}完成")
                        else:
                            failed_tasks += 1
                            print(f"❌ 任务{task.number}失败")
                            
                    except Exception as e:
                        failed_tasks += 1
                        print(f"💥 任务{task.number}异常: {str(e)}")
            
            # 3. 后处理：速度调整和文件整理
            output_files = self._postprocess_segments(all_segments, tasks)
            
            processing_time = time.time() - start_time
            
            # 计算总时长
            total_duration = sum(seg.duration for seg in all_segments)
            
            result = SynthesisResult(
                total_tasks=len(tasks),
                successful_tasks=successful_tasks,
                failed_tasks=failed_tasks,
                total_duration=total_duration,
                processing_time=processing_time,
                output_files=output_files,
                segments=all_segments
            )
            
            print("🎉 音频合成流程完成！")
            print(f"📊 合成统计:")
            print(f"  📄 总任务数: {result.total_tasks}")
            print(f"  ✅ 成功: {result.successful_tasks}")
            print(f"  ❌ 失败: {result.failed_tasks}")
            print(f"  ⏱️  总时长: {result.total_duration:.2f}秒")
            print(f"  🕒 处理耗时: {result.processing_time:.2f}秒")
            print(f"  📁 输出文件: {len(result.output_files)}个")
            
            return result
            
        except Exception as e:
            print(f"💥 音频合成流程失败: {str(e)}")
            raise
    
    def _postprocess_segments(self, segments: List[AudioSegment], tasks: List[AudioTask]) -> List[str]:
        """
        后处理音频片段：速度调整和文件整理
        
        Args:
            segments: 音频片段列表
            tasks: 原始任务列表
            
        Returns:
            输出文件列表
        """
        print("🔧 正在进行音频后处理...")
        
        output_files = []
        task_dict = {task.number: task for task in tasks}
        
        # 按任务号分组
        segments_by_task = defaultdict(list)
        for segment in segments:
            segments_by_task[segment.task_number].append(segment)
        
        for task_number, task_segments in segments_by_task.items():
            if task_number not in task_dict:
                continue
                
            task = task_dict[task_number]
            
            # 计算实际总时长
            actual_duration = sum(seg.duration for seg in task_segments if seg.confidence > 0)
            
            # 计算速度因子
            if actual_duration > 0 and task.duration > 0:
                speed_factor = actual_duration / task.duration
                # 限制速度因子范围
                speed_factor = max(0.5, min(2.0, speed_factor))
            else:
                speed_factor = 1.0
            
            # 处理每个片段
            for segment in task_segments:
                if segment.confidence == 0:
                    continue
                
                # 生成最终输出路径
                output_path = self.output_dir / f"{task_number}_{segment.segment_index}.wav"
                
                # 调整速度
                if abs(speed_factor - 1.0) > 0.05:  # 只有明显差异才调整
                    success = self.adjust_audio_speed(segment.file_path, str(output_path), speed_factor)
                    if success:
                        segment.speed_factor = speed_factor
                        print(f"🎵 任务{task_number}片段{segment.segment_index}速度调整: {speed_factor:.2f}x")
                    else:
                        # 调整失败，直接复制
                        shutil.copy2(segment.file_path, output_path)
                else:
                    # 不需要调整，直接复制
                    shutil.copy2(segment.file_path, output_path)
                
                output_files.append(str(output_path))
        
        # 清理临时文件
        try:
            for segment in segments:
                if Path(segment.file_path).exists():
                    os.remove(segment.file_path)
        except Exception as e:
            print(f"⚠️  清理临时文件失败: {str(e)}")
        
        return output_files


# ----------------------------------------------------------------------------
# 独立运行测试
# ----------------------------------------------------------------------------
if __name__ == '__main__':
    import sys
    
    # 创建音频合成器实例
    synthesizer = AudioSynthesizer(
        max_workers=2,
        max_retries=3
    )
    
    # 测试参数
    test_with_real_tts = '--real-tts' in sys.argv
    
    try:
        # 检查输入文件
        if not synthesizer.audio_task_file.exists():
            print(f"❌ 音频任务文件不存在: {synthesizer.audio_task_file}")
            print("💡 请先运行字幕生成器和音频任务生成器")
            sys.exit(1)
        
        # 设置TTS适配器
        if test_with_real_tts:
            print("⚠️  注意: 需要提供真实的TTS配置才能进行完整测试")
            # 使用Edge TTS作为示例（免费）
            synthesizer.set_tts_adapter("edge_tts", {"voice": "zh-CN-XiaoxiaoNeural"})
        else:
            # 使用自定义适配器进行测试
            synthesizer.set_tts_adapter("custom_tts", {})
        
        # 运行完整音频合成流程
        print("\n🧪 测试音频合成流程...")
        
        result = synthesizer.process_audio_synthesis()
        
        print(f"\n✅ 测试完成！")
        print(f"📁 生成的音频文件:")
        for i, file_path in enumerate(result.output_files[:10], 1):  # 只显示前10个
            print(f"  {i}. {file_path}")
        
        if len(result.output_files) > 10:
            print(f"  ... 还有{len(result.output_files) - 10}个文件")
        
    except Exception as e:
        print(f"\n💥 测试过程中发生错误: {str(e)}")
        sys.exit(1) 