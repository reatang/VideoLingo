"""
# ----------------------------------------------------------------------------
# 音频分离器模块 - 负责将混合音频分离为人声和背景音乐
# 
# 核心功能：
# 1. 使用Demucs模型进行音频源分离
# 2. 提取人声轨道和背景音乐轨道
# 3. 内存管理和资源清理
# 4. 支持多种音频格式输出
# 
# 输入：混合音频文件
# 输出：分离后的人声和背景音乐文件
# ----------------------------------------------------------------------------
"""

import os
import gc
import torch
from typing import Optional, Tuple
from pathlib import Path
from rich.console import Console
from rich import print as rprint
from ..commons.paths import get_filepath_by_audio_dir

try:
    from demucs.pretrained import get_model
    from demucs.audio import save_audio
    from demucs.api import Separator
    from demucs.apply import BagOfModels
    from torch.cuda import is_available as is_cuda_available
    DEMUCS_AVAILABLE = True
except ImportError:
    DEMUCS_AVAILABLE = False
    print("⚠️ Demucs not available, vocal separation will be disabled")
    # 创建占位符类
    class Separator:
        pass
    class BagOfModels:
        pass


class PreloadedSeparator(Separator):
    """预加载的音频分离器 - 优化的Demucs分离器"""
    
    def __init__(self, model: BagOfModels, shifts: int = 1, overlap: float = 0.25,
                 split: bool = True, segment: Optional[int] = None, jobs: int = 0):
        self._model = model
        self._audio_channels = model.audio_channels
        self._samplerate = model.samplerate
        
        # 自动选择最优设备
        if is_cuda_available():
            device = "cuda"
        elif torch.backends.mps.is_available():
            device = "mps"
        else:
            device = "cpu"
        
        self.update_parameter(
            device=device, 
            shifts=shifts, 
            overlap=overlap, 
            split=split,
            segment=segment, 
            jobs=jobs, 
            progress=True, 
            callback=None, 
            callback_arg=None
        )


class AudioSeparator:
    """音频分离器类 - 封装音频分离的所有功能"""

    def __init__(self, output_dir: str, model_name: str = 'htdemucs'):
        """
        初始化音频分离器
        
        Args:
            model_name: Demucs模型名称
        """
        if not DEMUCS_AVAILABLE:
            raise ImportError("❌ Demucs not available. Please install demucs package")
        
        self.model_name = model_name
        self._output_dir = output_dir

        self.console = Console()
        self._model = None
        self._separator = None
    
    def _load_model(self):
        """加载Demucs模型"""
        if self._model is None:
            self.console.print(f"🤖 正在加载 <{self.model_name}> 模型...")
            self._model = get_model(self.model_name)
            self._separator = PreloadedSeparator(
                model=self._model, 
                shifts=1, 
                overlap=0.25
            )
            self.console.print("✅ 模型加载完成")
    
    def separate_audio(self, 
                      input_audio_path: str,
                      sample_rate: Optional[int] = None,
                      bitrate: int = 128,
                      bits_per_sample: int = 16) -> Tuple[str, Optional[str]]:
        """
        分离音频文件
        
        Args:
            input_audio_path: 输入音频文件路径
            sample_rate: 采样率
            bitrate: 比特率
            bits_per_sample: 位深度
            
        Returns:
            (人声文件路径, 背景音乐文件路径)
        """
        if not os.path.exists(input_audio_path):
            raise FileNotFoundError(f"❌ 输入音频文件不存在: {input_audio_path}")
        
        # 确保输出目录存在
        os.makedirs(self._output_dir, exist_ok=True)

        vocal_output_path = str(get_filepath_by_audio_dir('vocal.mp3', output_base_dir=self._output_dir))
        background_output_path = str(get_filepath_by_audio_dir('background.mp3', output_base_dir=self._output_dir))
        
        try:
            # 加载模型
            self._load_model()
            
            # 执行分离
            self.console.print("🎵 正在分离音频...")
            _, outputs = self._separator.separate_audio_file(input_audio_path)
            
            # 设置输出参数
            if sample_rate is None:
                sample_rate = self._model.samplerate
            
            kwargs = {
                "samplerate": sample_rate, 
                "bitrate": bitrate, 
                "preset": 2,
                "clip": "rescale", 
                "as_float": False, 
                "bits_per_sample": bits_per_sample
            }
            
            # 保存人声轨道
            self.console.print("🎤 正在保存人声轨道...")
            save_audio(outputs['vocals'].cpu(), vocal_output_path, **kwargs)
            
            # 保存背景音乐轨道（可选）
            background_path = None
            if background_output_path:
                self.console.print("🎹 正在保存背景音乐...")
                background = sum(audio for source, audio in outputs.items() if source != 'vocals')
                save_audio(background.cpu(), background_output_path, **kwargs)
                background_path = background_output_path
            
            # 清理内存
            del outputs
            if background_path:
                del background
            gc.collect()
            
            self.console.print("[green]✨ 音频分离完成！[/green]")
            return vocal_output_path, background_path
            
        except Exception as e:
            self.console.print(f"[red]❌ 音频分离失败: {str(e)}[/red]")
            raise
    
    def cleanup(self):
        """清理模型资源"""
        if self._model is not None:
            del self._model
            self._model = None
        
        if self._separator is not None:
            del self._separator
            self._separator = None
        
        gc.collect()
        
        # 清理CUDA缓存
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


def separate_audio_file(input_audio_path: str,
                       output_dir: str = 'output',
                       model_name: str = 'htdemucs') -> Tuple[str, Optional[str]]:
    """
    分离音频文件的便捷接口
    
    Args:
        input_audio_path: 输入音频文件路径
        vocal_output_path: 人声输出文件路径
        background_output_path: 背景音乐输出文件路径（可选）
        model_name: Demucs模型名称
        
    Returns:
        (人声文件路径, 背景音乐文件路径)
    """
    separator = AudioSeparator(output_dir, model_name)
    try:
        return separator.separate_audio(input_audio_path)
    finally:
        separator.cleanup()


# ----------------------------------------------------------------------------
# 兼容性函数 - 保持与原有代码的兼容性
# ----------------------------------------------------------------------------
def demucs_audio(raw_audio_file: str,
                output_dir: str = 'output',
                model_name: str = 'htdemucs') -> None:
    """
    兼容性函数 - 保持与原有代码的兼容性
    """
    separate_audio_file(raw_audio_file, output_dir, model_name)


# ----------------------------------------------------------------------------
# 独立运行测试
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("用法: python audio_separator.py <输入音频文件> <人声输出文件> [背景音乐输出文件]")
        sys.exit(1)
    
    input_file = sys.argv[1]

    try:
        separate_audio_file(input_file)
        print(f"✅ 分离完成！")
            
    except Exception as e:
        print(f"💥 分离失败: {str(e)}")
        sys.exit(1) 