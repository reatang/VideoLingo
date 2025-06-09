"""
# ----------------------------------------------------------------------------
# F5-TTS适配器
# 
# 实现F5-TTS语音合成适配器
# 支持零样本语音克隆和多语言语音合成
# ----------------------------------------------------------------------------
"""

import os
import time
import subprocess
import requests
from typing import Dict, List, Optional, Any
from pathlib import Path

from ..base import TTSEngineAdapter, TTSResult, AudioSegment
from ..utils import validate_audio_output, generate_unique_filename


class F5TTSAdapter(TTSEngineAdapter):
    """F5-TTS适配器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化F5-TTS适配器"""
        super().__init__(config)
        self.version = "1.0.0"
        
        # F5-TTS特定配置
        self.model_path = self.config.get('model_path', '')
        self.ref_audio = self.config.get('ref_audio', None)
        self.ref_text = self.config.get('ref_text', '')
        self.gen_text = self.config.get('gen_text', '')
        self.remove_silence = self.config.get('remove_silence', True)
        self.speed = self.config.get('speed', 1.0)
        
        # 工作目录
        self.working_dir = self.config.get('working_dir', 'F5-TTS')
        
        # 模式配置
        self.mode = self.config.get('mode', 'api')  # api 或 cli
        self.api_url = self.config.get('api_url', 'http://localhost:8000')
    
    def initialize(self) -> None:
        """初始化F5-TTS引擎"""
        if self.mode == 'cli' and not self.model_path:
            print("⚠️  CLI模式需要指定模型路径")
        
        if self.mode == 'api':
            # 检查API服务是否可用
            try:
                response = requests.get(f"{self.api_url}/health", timeout=5)
                if response.status_code != 200:
                    print("⚠️  F5-TTS API服务不可用，请启动服务")
            except requests.exceptions.RequestException:
                print("⚠️  F5-TTS API服务连接失败")
        
        self._is_initialized = True
        print(f"✅ F5-TTS引擎初始化成功 (模式: {self.mode})")
    
    def configure(self, config: Dict[str, Any]) -> None:
        """配置F5-TTS参数"""
        self.model_path = config.get('model_path', self.model_path)
        self.ref_audio = config.get('ref_audio', self.ref_audio)
        self.ref_text = config.get('ref_text', self.ref_text)
        self.gen_text = config.get('gen_text', self.gen_text)
        self.remove_silence = config.get('remove_silence', self.remove_silence)
        self.speed = config.get('speed', self.speed)
        self.mode = config.get('mode', self.mode)
        
        # 验证配置
        if not (0.5 <= self.speed <= 2.0):
            print(f"⚠️  速度超出范围: {self.speed}，调整为1.0")
            self.speed = 1.0
        
        self._is_configured = True
        print(f"🔧 F5-TTS配置完成: mode={self.mode}")
    
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
            output_path = generate_unique_filename(text, "f5tts", ".wav")
        
        self._log_synthesis_start(text)
        start_time = time.time()
        
        try:
            # 根据模式调用不同的合成方法
            if self.mode == 'api':
                audio_path = self._call_f5tts_api(text, output_path, **kwargs)
            else:
                audio_path = self._call_f5tts_cli(text, output_path, **kwargs)
            
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
                voice="f5tts_voice",
                language=self._detect_language(text),
                metadata={
                    'engine': 'f5tts',
                    'mode': self.mode,
                    'ref_audio': self.ref_audio,
                    'speed': self.speed,
                    'remove_silence': self.remove_silence
                }
            )
            
            result = TTSResult(
                segments=[segment],
                total_duration=duration,
                output_path=audio_path,
                metadata={'engine': 'f5tts', 'mode': self.mode}
            )
            
            elapsed_time = time.time() - start_time
            self._log_synthesis_complete(elapsed_time, audio_path)
            
            return result
            
        except Exception as e:
            print(f"❌ F5-TTS合成失败: {e}")
            raise
    
    def _call_f5tts_api(self, text: str, output_path: str, **kwargs) -> str:
        """通过API调用F5-TTS"""
        payload = {
            "text": text,
            "ref_audio": self.ref_audio,
            "ref_text": self.ref_text,
            "speed": self.speed,
            "remove_silence": self.remove_silence
        }
        
        # 确保输出目录存在
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        try:
            response = requests.post(
                f"{self.api_url}/synthesize",
                json=payload,
                timeout=120  # F5-TTS可能需要较长时间
            )
            
            if response.status_code == 200:
                # 保存音频文件
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                
                print(f"✅ F5-TTS音频已保存: {output_path}")
                return output_path
            else:
                raise RuntimeError(f"❌ F5-TTS API请求失败: HTTP {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"❌ F5-TTS API网络错误: {e}")
    
    def _call_f5tts_cli(self, text: str, output_path: str, **kwargs) -> str:
        """通过命令行调用F5-TTS"""
        if not Path(self.working_dir).exists():
            raise RuntimeError(f"❌ F5-TTS工作目录不存在: {self.working_dir}")
        
        # 构建命令
        cmd = [
            "python", "infer_cli.py",
            "--gen_text", text,
            "--output_path", output_path
        ]
        
        if self.ref_audio:
            cmd.extend(["--ref_audio", self.ref_audio])
        
        if self.ref_text:
            cmd.extend(["--ref_text", self.ref_text])
        
        if self.model_path:
            cmd.extend(["--model_path", self.model_path])
        
        cmd.extend([
            "--speed", str(self.speed),
            "--remove_silence", str(self.remove_silence).lower()
        ])
        
        # 确保输出目录存在
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # 切换到F5-TTS目录
            original_dir = os.getcwd()
            os.chdir(self.working_dir)
            
            # 执行命令
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )
            
            # 切换回原目录
            os.chdir(original_dir)
            
            if result.returncode == 0:
                print(f"✅ F5-TTS命令行合成成功: {output_path}")
                return output_path
            else:
                raise RuntimeError(f"❌ F5-TTS命令行执行失败: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            os.chdir(original_dir)
            raise RuntimeError("❌ F5-TTS命令行执行超时")
        except Exception as e:
            os.chdir(original_dir)
            raise RuntimeError(f"❌ F5-TTS命令行执行错误: {e}")
    
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
        
        print(f"🎵 开始F5-TTS批量合成: {len(texts)}个文本片段")
        
        for i, text in enumerate(texts):
            try:
                # 生成输出路径
                output_path = os.path.join(output_dir, f"f5tts_batch_{i+1:03d}.wav")
                
                # 合成单个片段
                result = self.synthesize(text, output_path)
                
                if result.segments:
                    segment = result.segments[0]
                    segment.start_time = total_duration
                    segment.end_time = total_duration + (segment.duration or 0)
                    segments.append(segment)
                    total_duration += (segment.duration or 0)
                
                print(f"✅ 批量合成进度: {i+1}/{len(texts)}")
                
                # 添加延迟避免过载
                time.sleep(1)
                
            except Exception as e:
                print(f"❌ 批量合成失败 ({i+1}/{len(texts)}): {e}")
                continue
        
        # 合并音频文件（可选）
        if len(segments) > 1:
            merged_path = os.path.join(output_dir, "f5tts_merged.wav")
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
            metadata={'engine': 'f5tts', 'batch_size': len(texts)}
        )
        
        print(f"✅ F5-TTS批量合成完成: {len(segments)}/{len(texts)} 成功")
        return result
    
    def get_supported_languages(self) -> List[str]:
        """获取支持的语言列表"""
        return ['zh-CN', 'en-US', 'ja-JP', 'multilingual']
    
    def _detect_language(self, text: str) -> str:
        """检测文本语言"""
        # 简单的语言检测
        if any('\u4e00' <= char <= '\u9fff' for char in text):
            return 'zh-CN'
        elif any('\u3040' <= char <= '\u309f' or '\u30a0' <= char <= '\u30ff' for char in text):
            return 'ja-JP'
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
            file_size = os.path.getsize(audio_path)
            estimated_duration = file_size / (44100 * 2 * 2)  # 44.1kHz, 16bit, stereo
            return max(estimated_duration, 0.5)
    
    def cleanup(self) -> None:
        """清理资源"""
        super().cleanup()
        print(f"🧹 F5-TTS适配器已清理")


# 便捷函数，保持与原有代码的兼容性
def f5tts_synthesize(text: str, 
                    save_path: str,
                    ref_audio: str = None,
                    ref_text: str = "",
                    mode: str = "api") -> bool:
    """
    F5-TTS便捷函数
    
    Args:
        text: 要合成的文本
        save_path: 保存路径
        ref_audio: 参考音频路径
        ref_text: 参考文本
        mode: 运行模式 (api/cli)
    
    Returns:
        bool: 是否成功
    """
    try:
        config = {
            'ref_audio': ref_audio,
            'ref_text': ref_text,
            'mode': mode
        }
        adapter = F5TTSAdapter(config)
        adapter.initialize()
        adapter.configure(config)
        
        result = adapter.synthesize(text, save_path)
        adapter.cleanup()
        
        return result.success
        
    except Exception as e:
        print(f"❌ F5-TTS合成失败: {e}")
        return False 