"""
# ----------------------------------------------------------------------------
# 自定义TTS适配器
# 
# 实现自定义TTS服务的适配器，支持用户自定义的TTS接口
# 提供灵活的配置选项，适应不同的TTS服务
# ----------------------------------------------------------------------------
"""

import os
import time
import requests
import subprocess
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path

from ..base import TTSEngineAdapter, TTSResult, AudioSegment
from ..utils import validate_audio_output, generate_unique_filename


class CustomTTSAdapter(TTSEngineAdapter):
    """自定义TTS适配器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化自定义TTS适配器"""
        super().__init__(config)
        self.version = "1.0.0"
        
        # 自定义TTS配置
        self.api_url = self.config.get('api_url', '')
        self.api_key = self.config.get('api_key', '')
        self.voice = self.config.get('voice', 'default')
        self.model = self.config.get('model', 'default')
        
        # 请求配置
        self.headers = self.config.get('headers', {})
        self.params = self.config.get('params', {})
        self.request_method = self.config.get('request_method', 'POST')
        self.timeout = self.config.get('timeout', 30)
        
        # 响应处理配置
        self.response_format = self.config.get('response_format', 'audio')  # audio, json, custom
        self.audio_field = self.config.get('audio_field', None)  # JSON响应中音频数据的字段
        self.url_field = self.config.get('url_field', None)  # JSON响应中音频URL的字段
        
        # 命令行模式配置
        self.command_template = self.config.get('command_template', None)
        self.working_dir = self.config.get('working_dir', None)
        
        # 自定义处理函数
        self.custom_processor = self.config.get('custom_processor', None)
        
        # 模式选择
        self.mode = self.config.get('mode', 'api')  # api, command, custom
    
    def initialize(self) -> None:
        """初始化自定义TTS引擎"""
        if self.mode == 'api' and not self.api_url:
            raise RuntimeError("❌ API模式需要指定api_url")
        
        if self.mode == 'command' and not self.command_template:
            raise RuntimeError("❌ 命令行模式需要指定command_template")
        
        if self.mode == 'custom' and not self.custom_processor:
            raise RuntimeError("❌ 自定义模式需要指定custom_processor函数")
        
        self._is_initialized = True
        print(f"✅ 自定义TTS引擎初始化成功 (模式: {self.mode})")
    
    def configure(self, config: Dict[str, Any]) -> None:
        """配置自定义TTS参数"""
        self.api_url = config.get('api_url', self.api_url)
        self.api_key = config.get('api_key', self.api_key)
        self.voice = config.get('voice', self.voice)
        self.model = config.get('model', self.model)
        self.headers = config.get('headers', self.headers)
        self.params = config.get('params', self.params)
        self.request_method = config.get('request_method', self.request_method)
        self.timeout = config.get('timeout', self.timeout)
        self.response_format = config.get('response_format', self.response_format)
        self.command_template = config.get('command_template', self.command_template)
        self.working_dir = config.get('working_dir', self.working_dir)
        self.custom_processor = config.get('custom_processor', self.custom_processor)
        self.mode = config.get('mode', self.mode)
        
        self._is_configured = True
        print(f"🔧 自定义TTS配置完成: mode={self.mode}")
    
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
            output_path = generate_unique_filename(text, "custom_tts", ".wav")
        
        self._log_synthesis_start(text)
        start_time = time.time()
        
        try:
            # 根据模式调用不同的合成方法
            if self.mode == 'api':
                audio_path = self._call_api(text, output_path, **kwargs)
            elif self.mode == 'command':
                audio_path = self._call_command(text, output_path, **kwargs)
            elif self.mode == 'custom':
                audio_path = self._call_custom(text, output_path, **kwargs)
            else:
                raise ValueError(f"不支持的模式: {self.mode}")
            
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
                    'engine': 'custom_tts',
                    'voice': self.voice,
                    'model': self.model,
                    'mode': self.mode
                }
            )
            
            result = TTSResult(
                segments=[segment],
                total_duration=duration,
                output_path=audio_path,
                metadata={'engine': 'custom_tts', 'mode': self.mode}
            )
            
            elapsed_time = time.time() - start_time
            self._log_synthesis_complete(elapsed_time, audio_path)
            
            return result
            
        except Exception as e:
            print(f"❌ 自定义TTS合成失败: {e}")
            raise
    
    def _call_api(self, text: str, output_path: str, **kwargs) -> str:
        """通过API调用TTS服务"""
        # 构建请求数据
        data = {
            'text': text,
            'voice': self.voice,
            'model': self.model,
            **self.params,
            **kwargs
        }
        
        # 构建headers
        headers = self.headers.copy()
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
        
        # 确保输出目录存在
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # 发送请求
            if self.request_method.upper() == 'POST':
                response = requests.post(
                    self.api_url,
                    json=data,
                    headers=headers,
                    timeout=self.timeout
                )
            elif self.request_method.upper() == 'GET':
                response = requests.get(
                    self.api_url,
                    params=data,
                    headers=headers,
                    timeout=self.timeout
                )
            else:
                raise ValueError(f"不支持的请求方法: {self.request_method}")
            
            response.raise_for_status()
            
            # 处理响应
            return self._process_response(response, output_path)
            
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"❌ 自定义TTS API请求失败: {e}")
    
    def _process_response(self, response: requests.Response, output_path: str) -> str:
        """处理API响应"""
        if self.response_format == 'audio':
            # 直接是音频数据
            with open(output_path, 'wb') as f:
                f.write(response.content)
            return output_path
            
        elif self.response_format == 'json':
            # JSON响应
            data = response.json()
            
            if self.audio_field:
                # 音频数据在JSON中的某个字段
                import base64
                audio_data = data.get(self.audio_field)
                if isinstance(audio_data, str):
                    # 可能是base64编码
                    try:
                        audio_bytes = base64.b64decode(audio_data)
                        with open(output_path, 'wb') as f:
                            f.write(audio_bytes)
                        return output_path
                    except Exception:
                        raise RuntimeError("❌ 无法解码音频数据")
                        
            elif self.url_field:
                # 音频URL在JSON中的某个字段
                audio_url = data.get(self.url_field)
                if audio_url:
                    # 下载音频文件
                    audio_response = requests.get(audio_url, timeout=self.timeout)
                    audio_response.raise_for_status()
                    with open(output_path, 'wb') as f:
                        f.write(audio_response.content)
                    return output_path
                else:
                    raise RuntimeError("❌ 响应中没有找到音频URL")
            else:
                raise RuntimeError("❌ JSON响应格式配置错误")
        
        else:
            raise ValueError(f"不支持的响应格式: {self.response_format}")
    
    def _call_command(self, text: str, output_path: str, **kwargs) -> str:
        """通过命令行调用TTS"""
        # 替换命令模板中的变量
        cmd = self.command_template.format(
            text=text,
            output=output_path,
            voice=self.voice,
            model=self.model,
            **kwargs
        )
        
        # 确保输出目录存在
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # 切换工作目录（如果指定）
            original_dir = None
            if self.working_dir:
                original_dir = os.getcwd()
                os.chdir(self.working_dir)
            
            # 执行命令
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            
            # 恢复工作目录
            if original_dir:
                os.chdir(original_dir)
            
            if result.returncode == 0:
                print(f"✅ 自定义TTS命令执行成功: {output_path}")
                return output_path
            else:
                raise RuntimeError(f"❌ 命令执行失败: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            if original_dir:
                os.chdir(original_dir)
            raise RuntimeError("❌ 命令执行超时")
        except Exception as e:
            if original_dir:
                os.chdir(original_dir)
            raise RuntimeError(f"❌ 命令执行错误: {e}")
    
    def _call_custom(self, text: str, output_path: str, **kwargs) -> str:
        """使用自定义处理函数"""
        if not callable(self.custom_processor):
            raise RuntimeError("❌ custom_processor必须是可调用的函数")
        
        try:
            # 调用自定义处理函数
            result = self.custom_processor(
                text=text,
                output_path=output_path,
                voice=self.voice,
                model=self.model,
                config=self.config,
                **kwargs
            )
            
            if isinstance(result, str):
                return result
            else:
                return output_path
                
        except Exception as e:
            raise RuntimeError(f"❌ 自定义处理函数执行失败: {e}")
    
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
        
        print(f"🎵 开始自定义TTS批量合成: {len(texts)}个文本片段")
        
        for i, text in enumerate(texts):
            try:
                # 生成输出路径
                output_path = os.path.join(output_dir, f"custom_tts_batch_{i+1:03d}.wav")
                
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
                time.sleep(0.5)
                
            except Exception as e:
                print(f"❌ 批量合成失败 ({i+1}/{len(texts)}): {e}")
                continue
        
        # 合并音频文件（可选）
        if len(segments) > 1:
            merged_path = os.path.join(output_dir, "custom_tts_merged.wav")
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
            metadata={'engine': 'custom_tts', 'batch_size': len(texts)}
        )
        
        print(f"✅ 自定义TTS批量合成完成: {len(segments)}/{len(texts)} 成功")
        return result
    
    def get_supported_languages(self) -> List[str]:
        """获取支持的语言列表"""
        # 自定义TTS的语言支持由用户配置决定
        return self.config.get('supported_languages', ['zh-CN', 'en-US'])
    
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
            file_size = os.path.getsize(audio_path)
            estimated_duration = file_size / (44100 * 2 * 2)  # 44.1kHz, 16bit, stereo
            return max(estimated_duration, 0.5)
    
    def cleanup(self) -> None:
        """清理资源"""
        super().cleanup()
        print(f"🧹 自定义TTS适配器已清理")


# 便捷函数，保持与原有代码的兼容性
def custom_tts_synthesize(text: str, 
                         save_path: str,
                         config: Dict[str, Any]) -> bool:
    """
    自定义TTS便捷函数
    
    Args:
        text: 要合成的文本
        save_path: 保存路径
        config: 自定义配置
    
    Returns:
        bool: 是否成功
    """
    try:
        adapter = CustomTTSAdapter(config)
        adapter.initialize()
        adapter.configure(config)
        
        result = adapter.synthesize(text, save_path)
        adapter.cleanup()
        
        return result.success
        
    except Exception as e:
        print(f"❌ 自定义TTS合成失败: {e}")
        return False


# 示例自定义处理函数
def example_custom_processor(text: str, 
                           output_path: str, 
                           voice: str = 'default',
                           model: str = 'default',
                           config: Dict[str, Any] = None,
                           **kwargs) -> str:
    """
    示例自定义处理函数
    
    用户可以根据此模板实现自己的TTS处理逻辑
    """
    print(f"🔧 自定义处理: {text} -> {output_path}")
    
    # 这里实现您的自定义TTS逻辑
    # 例如：调用第三方库、处理音频文件等
    
    # 确保输出目录存在
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    # 生成一个简单的静音文件作为示例（实际应替换为真正的TTS逻辑）
    import wave
    import numpy as np
    
    # 创建1秒的静音音频
    sample_rate = 44100
    duration = 1.0
    samples = int(sample_rate * duration)
    audio_data = np.zeros(samples, dtype=np.int16)
    
    with wave.open(output_path, 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_data.tobytes())
    
    return output_path 