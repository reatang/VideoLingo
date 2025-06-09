"""
# ----------------------------------------------------------------------------
# Edge TTS适配器
# 
# 实现Microsoft Edge TTS服务的适配器
# 支持多种语言和声音，免费使用，是TTS服务的首选
# 使用edge-tts库进行实现
# ----------------------------------------------------------------------------
"""

import os
import sys
import time
import asyncio
import tempfile
import warnings
import concurrent.futures
import threading
from typing import Dict, List, Optional, Any
from pathlib import Path

from ..base import TTSEngineAdapter, TTSResult, AudioSegment
from ..utils import validate_audio_output, generate_unique_filename


def run_async_safely(coro):
    """
    # ----------------------------------------------------------------------------
    # 安全运行异步函数的辅助函数
    # 
    # 处理事件循环已存在的情况，避免"RuntimeError: This event loop is already running"
    # 特别优化Windows系统的ProactorEventLoop问题
    # ----------------------------------------------------------------------------
    """
    try:
        # 尝试获取当前运行的事件循环
        loop = asyncio.get_running_loop()
        # 如果已有循环运行，在新线程中创建新事件循环
        def run_in_thread():
            # 设置事件循环策略，避免Windows上的ProactorEventLoop问题
            if sys.platform == 'win32':
                # 在Windows上使用SelectorEventLoop而不是ProactorEventLoop
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                # 忽略警告，避免ProactorBasePipeTransport的del警告
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", ResourceWarning)
                    warnings.simplefilter("ignore", RuntimeWarning)
                    result = new_loop.run_until_complete(coro)
                return result
            finally:
                # 确保正确清理事件循环
                try:
                    # 等待所有任务完成
                    pending = asyncio.all_tasks(new_loop)
                    if pending:
                        new_loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                except Exception:
                    pass
                finally:
                    new_loop.close()
                    # 在Windows上重置事件循环
                    if sys.platform == 'win32':
                        asyncio.set_event_loop(None)
                
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_in_thread)
            return future.result()
            
    except RuntimeError:
        # 没有运行的事件循环，直接使用asyncio.run
        # 但在Windows上也需要特殊处理
        if sys.platform == 'win32':
            # 使用SelectorEventLoop
            old_policy = asyncio.get_event_loop_policy()
            try:
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", ResourceWarning)
                    warnings.simplefilter("ignore", RuntimeWarning)
                    return asyncio.run(coro)
            finally:
                asyncio.set_event_loop_policy(old_policy)
        else:
            return asyncio.run(coro)


class EdgeTTSAdapter(TTSEngineAdapter):
    """Edge TTS适配器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化Edge TTS适配器"""
        super().__init__(config)
        self.version = "1.0.0"
        
        # Edge TTS特定配置
        self.voice = self.config.get('voice', 'zh-CN-XiaoxiaoNeural')
        self.rate = self.config.get('rate', '+0%')
        self.pitch = self.config.get('pitch', '+0Hz')
        self.volume = self.config.get('volume', '+0%')
        
        # 支持的声音列表
        self.supported_voices = [
            "zh-CN-XiaoxiaoNeural", "zh-CN-YunxiNeural", "zh-CN-YunjianNeural",
            "zh-CN-XiaoyiNeural", "zh-CN-YunyangNeural", "zh-CN-XiaochenNeural",
            "en-US-AriaNeural", "en-US-JennyNeural", "en-US-GuyNeural",
            "en-US-GuyNeural", "en-US-RyanMultilingualNeural"
        ]
    
    def initialize(self) -> None:
        """初始化Edge TTS引擎"""
        try:
            import edge_tts
            self.edge_tts = edge_tts
            self._is_initialized = True
            print(f"✅ Edge TTS引擎初始化成功")
        except ImportError:
            raise RuntimeError("❌ 缺少edge-tts库，请安装: pip install edge-tts")
    
    def configure(self, config: Dict[str, Any]) -> None:
        """配置Edge TTS参数"""
        self.voice = config.get('voice', self.voice)
        self.rate = config.get('rate', self.rate)
        self.pitch = config.get('pitch', self.pitch)
        self.volume = config.get('volume', self.volume)
        
        # 验证声音是否支持
        if self.voice not in self.supported_voices:
            print(f"⚠️  不支持的声音: {self.voice}，使用默认声音")
            self.voice = 'zh-CN-XiaoxiaoNeural'
        
        self._is_configured = True
        print(f"🔧 Edge TTS配置完成: voice={self.voice}")
    
    def synthesize(self, text: str, 
                  output_path: Optional[str] = None,
                  **kwargs) -> TTSResult:
        """合成单个文本片段"""
        if not self._is_initialized:
            self.initialize()
        
        if not self._is_configured:
            self.configure(self.config)
        
        # 验证文本
        if not self.validate_text(text):
            raise ValueError(f"❌ 无效文本: {text}")
        
        # 生成输出路径
        if output_path is None:
            output_path = generate_unique_filename(text, "edge_tts")
        
        self._log_synthesis_start(text)
        start_time = time.time()
        
        try:
            # 异步调用Edge TTS - 使用安全的异步运行函数
            audio_path = run_async_safely(self._synthesize_async(text, output_path))
            
            # 验证输出
            if not validate_audio_output(audio_path):
                raise RuntimeError(f"❌ 音频合成失败: {audio_path}")
            
            # 获取音频时长
            duration = self._get_audio_duration_simple(audio_path)
            
            # 创建结果
            segment = AudioSegment(
                text=text,
                audio_path=audio_path,
                duration=duration,
                voice=self.voice,
                language=self._detect_language(text),
                metadata={
                    'engine': 'edge_tts',
                    'voice': self.voice,
                    'rate': self.rate,
                    'pitch': self.pitch,
                    'volume': self.volume
                }
            )
            
            result = TTSResult(
                segments=[segment],
                total_duration=duration,
                output_path=audio_path,
                metadata={'engine': 'edge_tts', 'voice': self.voice}
            )
            
            elapsed_time = time.time() - start_time
            self._log_synthesis_complete(elapsed_time, audio_path)
            
            return result
            
        except Exception as e:
            print(f"❌ Edge TTS合成失败: {e}")
            raise
    
    async def _synthesize_async(self, text: str, output_path: str) -> str:
        """异步合成音频"""
        # 创建Edge TTS通信对象
        communicate = self.edge_tts.Communicate(text, self.voice)
        
        # 保存音频
        await communicate.save(output_path)
        
        return output_path

    def synthesize_batch(self, 
                        texts: List[str],
                        output_dir: Optional[str] = None,
                        **kwargs) -> TTSResult:
        """批量合成多个文本片段"""
        if output_dir is None:
            output_dir = "output/audio"
        
        os.makedirs(output_dir, exist_ok=True)
        
        segments = []
        total_duration = 0.0
        
        print(f"🎵 开始Edge TTS批量合成: {len(texts)}个文本片段")
        
        for i, text in enumerate(texts):
            try:
                # 生成输出路径
                output_path = os.path.join(output_dir, f"edge_tts_batch_{i+1:03d}.wav")
                
                # 合成单个片段
                result = self.synthesize(text, output_path)
                
                if result.segments:
                    segment = result.segments[0]
                    segment.start_time = total_duration
                    segment.end_time = total_duration + (segment.duration or 0)
                    segments.append(segment)
                    total_duration += (segment.duration or 0)
                
                print(f"✅ 批量合成进度: {i+1}/{len(texts)}")
                
            except Exception as e:
                print(f"❌ 批量合成失败 ({i+1}/{len(texts)}): {e}")
                continue
        
        # 合并音频文件（可选）
        if len(segments) > 1:
            merged_path = os.path.join(output_dir, "edge_tts_merged.wav")
            audio_paths = [seg.audio_path for seg in segments]
            try:
                from ..utils import TTSProcessor
                processor = TTSProcessor()
                merged_path = processor.merge_audio_files(audio_paths, merged_path)
                output_path = merged_path
            except Exception as e:
                print(f"⚠️  音频合并失败: {e}")
                output_path = None
        else:
            output_path = segments[0].audio_path if segments else None
        
        result = TTSResult(
            segments=segments,
            total_duration=total_duration,
            output_path=output_path,
            metadata={'engine': 'edge_tts', 'batch_size': len(texts)}
        )
        
        print(f"✅ Edge TTS批量合成完成: {len(segments)}/{len(texts)} 成功")
        return result
    
    def get_supported_voices(self) -> List[str]:
        """获取支持的声音列表"""
        return self.supported_voices.copy()
    
    def get_supported_languages(self) -> List[str]:
        """获取支持的语言列表"""
        return ['zh-CN', 'zh-TW', 'en-US', 'en-GB', 'ja-JP', 'ko-KR']
    
    def _detect_language(self, text: str) -> str:
        """检测文本语言"""
        # 简单的语言检测
        if any('\u4e00' <= char <= '\u9fff' for char in text):
            return 'zh-CN'
        elif any('\u3040' <= char <= '\u309f' or '\u30a0' <= char <= '\u30ff' for char in text):
            return 'ja-JP'
        elif any('\uac00' <= char <= '\ud7af' for char in text):
            return 'ko-KR'
        else:
            return 'en-US'
    
    def _get_audio_duration_simple(self, audio_path: str) -> float:
        """简单获取音频时长"""
        try:
            from ..utils import TTSProcessor
            processor = TTSProcessor()
            return processor.get_audio_duration(audio_path)
        except Exception:
            # 如果无法获取精确时长，使用估算
            with open(audio_path, 'rb') as f:
                # 粗略估算：WAV文件大小除以平均比特率
                file_size = len(f.read())
                estimated_duration = file_size / (44100 * 2 * 2)  # 44.1kHz, 16bit, stereo
                return max(estimated_duration, 0.5)
    
    def cleanup(self) -> None:
        """清理资源"""
        super().cleanup()
        print(f"🧹 Edge TTS适配器已清理")


# 便捷函数，保持与原有代码的兼容性
def edge_tts(text: str, 
            output_path: Optional[str] = None,
            voice: str = "zh-CN-XiaoxiaoNeural") -> str:
    """
    Edge TTS便捷函数（兼容原有接口）
    
    Args:
        text: 要合成的文本
        voice: 声音类型
        output_path: 输出路径
        
    Returns:
        生成的音频文件路径
    """
    try:
        config = {'voice': voice}
        adapter = EdgeTTSAdapter(config)
        adapter.initialize()
        adapter.configure(config)
        
        result = adapter.synthesize(text, output_path)
        adapter.cleanup()
        
        return result.audio_path or ""
        
    except Exception as e:
        print(f"❌ Edge TTS合成失败: {e}")
        raise 