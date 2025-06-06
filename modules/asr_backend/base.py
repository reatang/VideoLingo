"""
# ----------------------------------------------------------------------------
# ASR引擎抽象基类和数据模型
# 
# 定义了统一的ASR接口规范，所有具体的引擎适配器都需要实现这些接口
# 使用数据类定义结构化的返回结果，确保类型安全和一致性
# ----------------------------------------------------------------------------
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union, Any
import pandas as pd


@dataclass
class WordTimestamp:
    """词级别时间戳信息"""
    word: str
    start: float
    end: float
    confidence: Optional[float] = None


@dataclass
class AudioSegment:
    """音频段落信息"""
    text: str
    start: float
    end: float
    words: list[WordTimestamp] = field(default_factory=list)
    speaker_id: Optional[str] = None
    language: Optional[str] = None
    confidence: Optional[float] = None


@dataclass
class ASRResult:
    """ASR转录结果的标准化数据结构"""
    segments: list[AudioSegment] = field(default_factory=list)
    language: Optional[str] = None
    duration: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """转换为字典格式，保持与原有代码的兼容性"""
        return {
            'segments': [
                {
                    'start': seg.start,
                    'end': seg.end,
                    'text': seg.text,
                    'words': [
                        {
                            'word': word.word,
                            'start': word.start,
                            'end': word.end
                        } for word in seg.words
                    ],
                    'speaker_id': seg.speaker_id
                } for seg in self.segments
            ],
            'language': self.language,
            'duration': self.duration
        }
    
    def to_dataframe(self) -> pd.DataFrame:
        """转换为DataFrame格式，用于后续处理"""
        all_words = []
        for segment in self.segments:
            for word in segment.words:
                all_words.append({
                    'text': word.word,
                    'start': word.start,
                    'end': word.end,
                    'speaker_id': segment.speaker_id
                })
        return pd.DataFrame(all_words)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ASRResult':
        """从字典创建ASRResult实例"""
        segments = []
        for seg_data in data.get('segments', []):
            words = []
            for word_data in seg_data.get('words', []):
                words.append(WordTimestamp(
                    word=word_data.get('word', ''),
                    start=word_data.get('start', 0.0),
                    end=word_data.get('end', 0.0)
                ))
            
            segments.append(AudioSegment(
                text=seg_data.get('text', ''),
                start=seg_data.get('start', 0.0),
                end=seg_data.get('end', 0.0),
                words=words,
                speaker_id=seg_data.get('speaker_id')
            ))
        
        return cls(
            segments=segments,
            language=data.get('language'),
            duration=data.get('duration')
        )


class ASREngineBase(ABC):
    """ASR引擎抽象基类 - 定义统一的转录接口"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化ASR引擎
        
        Args:
            config: 引擎配置参数
        """
        self.config = config or {}
        self._is_initialized = False
    
    @abstractmethod
    def initialize(self) -> None:
        """初始化引擎资源（模型加载、API连接等）"""
        pass
    
    @abstractmethod
    def transcribe(self, 
                  raw_audio_path: str,
                  vocal_audio_path: str,
                  start_time: float = 0.0,
                  end_time: Optional[float] = None) -> ASRResult:
        """
        转录音频片段
        
        Args:
            raw_audio_path: 原始音频文件路径
            vocal_audio_path: 人声分离后的音频文件路径
            start_time: 开始时间（秒）
            end_time: 结束时间（秒），None表示到音频结尾
            
        Returns:
            ASRResult: 标准化的转录结果
        """
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """清理引擎资源"""
        pass
    
    def is_available(self) -> bool:
        """检查引擎是否可用"""
        try:
            self.initialize()
            return True
        except Exception:
            return False
    
    def get_supported_languages(self) -> List[str]:
        """获取支持的语言列表"""
        return []
    
    def get_engine_info(self) -> Dict[str, Any]:
        """获取引擎信息"""
        return {
            'name': self.__class__.__name__,
            'version': getattr(self, 'version', 'unknown'),
            'supported_languages': self.get_supported_languages(),
            'is_available': self.is_available()
        }


class ASREngineAdapter(ASREngineBase):
    """ASR引擎适配器基类 - 提供通用的适配器功能"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.engine_name = self.__class__.__name__.replace('Adapter', '')
    
    def _validate_audio_path(self, audio_path: str) -> None:
        """验证音频文件路径"""
        import os
        if not audio_path or not os.path.exists(audio_path):
            raise FileNotFoundError(f"❌ 音频文件不存在: {audio_path}")
    
    def _adjust_timestamps(self, result: Dict, start_time: float) -> Dict:
        """调整时间戳偏移"""
        if start_time > 0:
            for segment in result.get('segments', []):
                segment['start'] += start_time
                segment['end'] += start_time
                for word in segment.get('words', []):
                    if 'start' in word:
                        word['start'] += start_time
                    if 'end' in word:
                        word['end'] += start_time
        return result
    
    def _log_transcription_start(self, start_time: float, end_time: Optional[float]) -> None:
        """记录转录开始日志"""
        end_str = f"{end_time:.1f}s" if end_time else "结束"
        print(f"🎤 {self.engine_name}转录: {start_time:.1f}s - {end_str}")
    
    def _log_transcription_complete(self, elapsed_time: float) -> None:
        """记录转录完成日志"""
        print(f"✅ {self.engine_name}转录完成，耗时: {elapsed_time:.2f}秒")


# ----------------------------------------------------------------------------
# 兼容性接口 - 保持与原有代码的兼容性
# ----------------------------------------------------------------------------

def create_legacy_result(asr_result: ASRResult) -> Dict:
    """创建与原有代码兼容的结果格式"""
    return asr_result.to_dict()


def process_legacy_input(raw_audio: str, vocal_audio: str, start: float, end: float) -> Dict[str, Any]:
    """处理原有代码的输入参数格式"""
    return {
        'raw_audio_path': raw_audio,
        'vocal_audio_path': vocal_audio,
        'start_time': start,
        'end_time': end
    } 