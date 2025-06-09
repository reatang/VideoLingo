"""
# ----------------------------------------------------------------------------
# TTS引擎抽象基类和数据模型
# 
# 定义了统一的TTS接口规范，所有具体的引擎适配器都需要实现这些接口
# 使用数据类定义结构化的返回结果，确保类型安全和一致性
# 支持初始化期、配置期、运行期的完整生命周期管理
# ----------------------------------------------------------------------------
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union, Any
from pathlib import Path
import time


@dataclass
class AudioSegment:
    """音频段落信息"""
    text: str                          # 原始文本
    audio_path: str                   # 生成的音频文件路径
    duration: Optional[float] = None  # 音频时长（秒）
    voice: Optional[str] = None       # 使用的声音
    language: Optional[str] = None    # 语言
    start_time: Optional[float] = None  # 在合成任务中的开始时间
    end_time: Optional[float] = None    # 在合成任务中的结束时间
    metadata: Dict[str, Any] = field(default_factory=dict)  # 其他元数据


@dataclass
class TTSResult:
    """TTS合成结果的标准化数据结构"""
    segments: List[AudioSegment] = field(default_factory=list)
    total_duration: Optional[float] = None
    output_path: Optional[str] = None    # 最终合并的音频文件路径
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def audio_path(self) -> Optional[str]:
        """获取音频文件路径（兼容性属性）"""
        if self.output_path:
            return self.output_path
        elif len(self.segments) == 1:
            return self.segments[0].audio_path
        return None
    
    @property
    def success(self) -> bool:
        """检查合成是否成功"""
        return len(self.segments) > 0 and all(
            seg.audio_path and Path(seg.audio_path).exists() 
            for seg in self.segments
        )
    
    def to_dict(self) -> Dict:
        """转换为字典格式，保持与原有代码的兼容性"""
        return {
            'segments': [
                {
                    'text': seg.text,
                    'audio_path': seg.audio_path,
                    'duration': seg.duration,
                    'voice': seg.voice,
                    'language': seg.language,
                    'start_time': seg.start_time,
                    'end_time': seg.end_time,
                    'metadata': seg.metadata
                } for seg in self.segments
            ],
            'total_duration': self.total_duration,
            'output_path': self.output_path,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'TTSResult':
        """从字典创建TTSResult实例"""
        segments = []
        for seg_data in data.get('segments', []):
            segments.append(AudioSegment(
                text=seg_data.get('text', ''),
                audio_path=seg_data.get('audio_path', ''),
                duration=seg_data.get('duration'),
                voice=seg_data.get('voice'),
                language=seg_data.get('language'),
                start_time=seg_data.get('start_time'),
                end_time=seg_data.get('end_time'),
                metadata=seg_data.get('metadata', {})
            ))
        
        return cls(
            segments=segments,
            total_duration=data.get('total_duration'),
            output_path=data.get('output_path'),
            metadata=data.get('metadata', {})
        )


class TTSEngineBase(ABC):
    """TTS引擎抽象基类 - 定义统一的文本转语音接口"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化TTS引擎 - 初始化期
        
        Args:
            config: 引擎配置参数
        """
        self.config = config or {}
        self._is_initialized = False
        self._is_configured = False
        self.engine_name = self.__class__.__name__.replace('Adapter', '').replace('TTS', '')
    
    @abstractmethod
    def initialize(self) -> None:
        """
        初始化引擎资源 - 初始化期
        加载模型、建立API连接等一次性设置
        """
        pass
    
    @abstractmethod
    def configure(self, config: Dict[str, Any]) -> None:
        """
        配置引擎参数 - 配置期
        设置声音、语言、输出格式等可变参数
        
        Args:
            config: 配置参数字典
        """
        pass
    
    @abstractmethod
    def synthesize(self, text: str, 
                  output_path: Optional[str] = None,
                  **kwargs) -> TTSResult:
        """
        合成单个文本片段 - 运行期
        
        Args:
            text: 要合成的文本
            output_path: 输出音频文件路径（可选）
            **kwargs: 其他参数
            
        Returns:
            TTSResult: 标准化的合成结果
        """
        pass
    
    @abstractmethod
    def synthesize_batch(self, 
                        texts: List[str],
                        output_dir: Optional[str] = None,
                        **kwargs) -> TTSResult:
        """
        批量合成多个文本片段 - 运行期
        
        Args:
            texts: 要合成的文本列表
            output_dir: 输出目录（可选）
            **kwargs: 其他参数
            
        Returns:
            TTSResult: 包含多个片段的合成结果
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
        except Exception as e:
            print(f"⚠️  {self.engine_name}引擎不可用: {e}")
            return False
    
    def get_supported_voices(self) -> List[str]:
        """获取支持的声音列表"""
        return []
    
    def get_supported_languages(self) -> List[str]:
        """获取支持的语言列表"""
        return []
    
    def estimate_duration(self, text: str) -> float:
        """
        估算文本的合成时长
        
        Args:
            text: 文本内容
            
        Returns:
            估算的音频时长（秒）
        """
        # 简单估算：中文约2字符/秒，英文约4字符/秒
        char_count = len(text)
        if any(ord(char) > 127 for char in text):  # 包含中文
            return char_count / 2.0
        else:  # 纯英文
            return char_count / 4.0
    
    def validate_text(self, text: str) -> bool:
        """验证文本是否符合TTS要求"""
        if not text or not text.strip():
            return False
        
        # 检查文本长度（大多数TTS服务有长度限制）
        max_length = self.config.get('max_text_length', 5000)
        if len(text) > max_length:
            print(f"⚠️  文本长度({len(text)})超过限制({max_length})")
            return False
        
        return True
    
    def get_engine_info(self) -> Dict[str, Any]:
        """获取引擎信息"""
        return {
            'name': self.engine_name,
            'class_name': self.__class__.__name__,
            'version': getattr(self, 'version', 'unknown'),
            'supported_voices': self.get_supported_voices(),
            'supported_languages': self.get_supported_languages(),
            'is_available': self.is_available(),
            'config': self.config
        }


class TTSEngineAdapter(TTSEngineBase):
    """TTS引擎适配器基类 - 提供通用的适配器功能"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._temp_files: List[str] = []  # 临时文件列表，用于清理
    
    def _generate_output_path(self, text: str, 
                            output_dir: Optional[str] = None,
                            suffix: str = ".wav") -> str:
        """生成输出文件路径"""
        import hashlib
        import os
        
        if output_dir is None:
            output_dir = "output/audio"
        
        os.makedirs(output_dir, exist_ok=True)
        
        # 使用文本哈希生成文件名
        text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()[:8]
        timestamp = int(time.time() * 1000) % 10000
        filename = f"tts_{self.engine_name}_{text_hash}_{timestamp}{suffix}"
        
        return os.path.join(output_dir, filename)
    
    def _register_temp_file(self, filepath: str) -> None:
        """注册临时文件用于后续清理"""
        if filepath and filepath not in self._temp_files:
            self._temp_files.append(filepath)
    
    def _validate_output_audio(self, audio_path: str) -> bool:
        """验证输出音频文件"""
        if not audio_path or not Path(audio_path).exists():
            return False
        
        # 检查文件大小
        file_size = Path(audio_path).stat().st_size
        if file_size < 1024:  # 小于1KB的音频文件通常是无效的
            print(f"⚠️  音频文件过小: {audio_path} ({file_size} bytes)")
            return False
        
        return True
    
    def _log_synthesis_start(self, text: str) -> None:
        """记录合成开始日志"""
        text_preview = text[:50] + "..." if len(text) > 50 else text
        print(f"🎵 开始{self.engine_name}合成: {text_preview}")
    
    def _log_synthesis_complete(self, elapsed_time: float, output_path: str) -> None:
        """记录合成完成日志"""
        print(f"✅ {self.engine_name}合成完成 ({elapsed_time:.2f}s): {Path(output_path).name}")
    
    def cleanup(self) -> None:
        """清理临时文件和资源"""
        # 清理临时文件
        for filepath in self._temp_files:
            try:
                if Path(filepath).exists():
                    Path(filepath).unlink()
                    print(f"🗑️  已清理临时文件: {filepath}")
            except Exception as e:
                print(f"⚠️  清理临时文件失败: {filepath} - {e}")
        
        self._temp_files.clear()
        self._is_initialized = False
        self._is_configured = False


def create_legacy_result(audio_path: str, text: str = "", duration: float = None) -> str:
    """
    创建兼容原有代码的返回格式
    
    Args:
        audio_path: 音频文件路径
        text: 原始文本
        duration: 音频时长
        
    Returns:
        音频文件路径（保持与原有接口兼容）
    """
    return audio_path


def validate_tts_config(config: Dict[str, Any], required_keys: List[str]) -> bool:
    """
    验证TTS配置参数
    
    Args:
        config: 配置字典
        required_keys: 必需的配置键列表
        
    Returns:
        配置是否有效
    """
    for key in required_keys:
        if key not in config or not config[key]:
            print(f"❌ 缺少必需的配置项: {key}")
            return False
    return True 