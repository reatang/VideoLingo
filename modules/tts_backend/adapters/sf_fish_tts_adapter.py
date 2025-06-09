"""
# ----------------------------------------------------------------------------
# SiliconFlow Fish TTS适配器
# 
# 实现SiliconFlow平台的Fish TTS服务适配器
# 支持预设声音、自定义声音和动态参考音频三种模式
# ----------------------------------------------------------------------------
"""

import os
import time
import json
import base64
import requests
from typing import Dict, List, Optional, Any
from pathlib import Path

from ..base import TTSEngineAdapter, TTSResult, AudioSegment
from ..utils import validate_audio_output, generate_unique_filename


class SFishTTSAdapter(TTSEngineAdapter):
    """SiliconFlow Fish TTS适配器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化SiliconFlow Fish TTS适配器"""
        super().__init__(config)
        self.version = "1.0.0"
        
        # SiliconFlow Fish TTS特定配置
        self.api_key = self.config.get('api_key', '')
        self.voice = self.config.get('voice', 'fishaudio/fish-speech-1.4:alex')
        self.mode = self.config.get('mode', 'preset')  # preset, custom, dynamic
        
        # API配置
        self.base_url = "https://api.siliconflow.cn/v1/audio/speech"
        self.voice_upload_url = "https://api.siliconflow.cn/v1/uploads/audio/voice"
        self.model_name = "fishaudio/fish-speech-1.4"
        
        # 动态模式配置
        self.ref_audio = self.config.get('ref_audio', None)
        self.ref_text = self.config.get('ref_text', None)
        self.voice_id = self.config.get('voice_id', None)
    
    def initialize(self) -> None:
        """初始化SiliconFlow Fish TTS引擎"""
        if not self.api_key:
            raise RuntimeError("❌ SiliconFlow Fish TTS需要API密钥")
        
        self._is_initialized = True
        print(f"✅ SiliconFlow Fish TTS引擎初始化成功")
    
    def configure(self, config: Dict[str, Any]) -> None:
        """配置SiliconFlow Fish TTS参数"""
        self.api_key = config.get('api_key', self.api_key)
        self.voice = config.get('voice', self.voice)
        self.mode = config.get('mode', self.mode)
        self.ref_audio = config.get('ref_audio', self.ref_audio)
        self.ref_text = config.get('ref_text', self.ref_text)
        self.voice_id = config.get('voice_id', self.voice_id)
        
        # 验证配置
        if self.mode not in ['preset', 'custom', 'dynamic']:
            print(f"⚠️  不支持的模式: {self.mode}，使用默认模式 preset")
            self.mode = 'preset'
        
        if self.mode == 'custom' and not self.voice_id:
            print("⚠️  自定义模式需要voice_id")
        
        if self.mode == 'dynamic' and (not self.ref_audio or not self.ref_text):
            print("⚠️  动态模式需要ref_audio和ref_text")
        
        self._is_configured = True
        print(f"🔧 SiliconFlow Fish TTS配置完成: mode={self.mode}, voice={self.voice}")
    
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
            output_path = generate_unique_filename(text, "sf_fish_tts", ".wav")
        
        self._log_synthesis_start(text)
        start_time = time.time()
        
        try:
            # 调用SiliconFlow Fish TTS API
            audio_path = self._call_siliconflow_api(text, output_path)
            
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
                    'engine': 'sf_fish_tts',
                    'voice': self.voice,
                    'mode': self.mode,
                    'model': self.model_name
                }
            )
            
            result = TTSResult(
                segments=[segment],
                total_duration=duration,
                output_path=audio_path,
                metadata={'engine': 'sf_fish_tts', 'voice': self.voice, 'mode': self.mode}
            )
            
            elapsed_time = time.time() - start_time
            self._log_synthesis_complete(elapsed_time, audio_path)
            
            return result
            
        except Exception as e:
            print(f"❌ SiliconFlow Fish TTS合成失败: {e}")
            raise
    
    def _call_siliconflow_api(self, text: str, output_path: str) -> str:
        """调用SiliconFlow Fish TTS API"""
        headers = {
            "Authorization": f'Bearer {self.api_key}',
            "Content-Type": "application/json"
        }
        
        # 根据模式构建不同的payload
        payload = {
            "model": self.model_name,
            "response_format": "wav",
            "stream": False,
            "input": text
        }
        
        if self.mode == "preset":
            payload["voice"] = f"fishaudio/fish-speech-1.4:{self.voice}"
        elif self.mode == "custom":
            if not self.voice_id:
                raise ValueError("自定义模式需要voice_id")
            payload["voice"] = self.voice_id
        elif self.mode == "dynamic":
            if not self.ref_audio or not self.ref_text:
                raise ValueError("动态模式需要ref_audio和ref_text")
            
            # 读取参考音频并转换为base64
            with open(self.ref_audio, 'rb') as f:
                audio_base64 = base64.b64encode(f.read()).decode('utf-8')
            
            payload["voice"] = None
            payload["references"] = [{
                "audio": f"data:audio/wav;base64,{audio_base64}",
                "text": self.ref_text
            }]
        
        # 确保输出目录存在
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        # 发送请求（带重试机制）
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    self.base_url,
                    json=payload,
                    headers=headers,
                    timeout=60  # Fish TTS可能需要更长时间
                )
                
                if response.status_code == 200:
                    # 保存音频文件
                    with open(output_path, 'wb') as f:
                        f.write(response.content)
                    
                    print(f"✅ SiliconFlow Fish TTS音频已保存: {output_path}")
                    return output_path
                else:
                    error_msg = f"HTTP {response.status_code}: {response.text}"
                    if attempt < max_retries - 1:
                        print(f"⚠️  SiliconFlow Fish TTS请求失败 (重试 {attempt + 1}/{max_retries}): {error_msg}")
                        time.sleep(2)
                        continue
                    else:
                        raise RuntimeError(f"❌ SiliconFlow Fish TTS请求失败: {error_msg}")
                        
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    print(f"⚠️  SiliconFlow Fish TTS网络错误 (重试 {attempt + 1}/{max_retries}): {e}")
                    time.sleep(2)
                    continue
                else:
                    raise RuntimeError(f"❌ SiliconFlow Fish TTS网络错误: {e}")
        
        raise RuntimeError("❌ SiliconFlow Fish TTS请求失败，已达到最大重试次数")
    
    def create_custom_voice(self, audio_path: str, text: str, custom_name: str = None) -> str:
        """创建自定义声音"""
        if not Path(audio_path).exists():
            raise FileNotFoundError(f"音频文件不存在: {audio_path}")
        
        # 读取音频文件并转换为base64
        with open(audio_path, 'rb') as f:
            audio_base64 = base64.b64encode(f.read()).decode('utf-8')
        
        payload = {
            "audio": f"data:audio/wav;base64,{audio_base64}",
            "model": self.model_name,
            "customName": custom_name or f"custom_{int(time.time())}",
            "text": text
        }
        
        headers = {
            "Authorization": f'Bearer {self.api_key}',
            "Content-Type": "application/json"
        }
        
        print(f"🎙️  正在创建自定义声音...")
        response = requests.post(
            self.voice_upload_url,
            json=payload,
            headers=headers,
            timeout=60
        )
        
        if response.status_code == 200:
            response_json = response.json()
            voice_id = response_json.get('uri')
            print(f"✅ 自定义声音创建成功: {voice_id}")
            return voice_id
        else:
            error_msg = f"HTTP {response.status_code}: {response.text}"
            raise RuntimeError(f"❌ 自定义声音创建失败: {error_msg}")
    
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
        
        print(f"🎵 开始SiliconFlow Fish TTS批量合成: {len(texts)}个文本片段")
        
        for i, text in enumerate(texts):
            try:
                # 生成输出路径
                output_path = os.path.join(output_dir, f"sf_fish_tts_batch_{i+1:03d}.wav")
                
                # 合成单个片段
                result = self.synthesize(text, output_path)
                
                if result.segments:
                    segment = result.segments[0]
                    segment.start_time = total_duration
                    segment.end_time = total_duration + (segment.duration or 0)
                    segments.append(segment)
                    total_duration += (segment.duration or 0)
                
                print(f"✅ 批量合成进度: {i+1}/{len(texts)}")
                
                # 添加延迟避免API限制
                time.sleep(0.5)
                
            except Exception as e:
                print(f"❌ 批量合成失败 ({i+1}/{len(texts)}): {e}")
                continue
        
        # 合并音频文件（可选）
        if len(segments) > 1:
            merged_path = os.path.join(output_dir, "sf_fish_tts_merged.wav")
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
            metadata={'engine': 'sf_fish_tts', 'batch_size': len(texts)}
        )
        
        print(f"✅ SiliconFlow Fish TTS批量合成完成: {len(segments)}/{len(texts)} 成功")
        return result
    
    def get_supported_voices(self) -> List[str]:
        """获取支持的预设声音列表"""
        return [
            'alex', 'bella', 'daniel', 'fred', 'mei', 'anya',
            'karina', 'elena', 'david', 'mike', 'sarah'
        ]
    
    def get_supported_languages(self) -> List[str]:
        """获取支持的语言列表"""
        return ['zh-CN', 'en-US', 'ja-JP', 'ko-KR']
    
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
        print(f"🧹 SiliconFlow Fish TTS适配器已清理")


# 便捷函数，保持与原有代码的兼容性
def siliconflow_fish_tts(text: str, 
                        save_path: str,
                        mode: str = "preset",
                        voice_id: str = None,
                        ref_audio: str = None,
                        ref_text: str = None,
                        api_key: str = None) -> bool:
    """
    SiliconFlow Fish TTS便捷函数（兼容原有接口）
    
    Args:
        text: 要合成的文本
        save_path: 保存路径
        mode: 模式 (preset/custom/dynamic)
        voice_id: 自定义声音ID
        ref_audio: 参考音频路径
        ref_text: 参考文本
        api_key: API密钥
    
    Returns:
        bool: 是否成功
    """
    try:
        config = {
            'mode': mode,
            'voice_id': voice_id,
            'ref_audio': ref_audio,
            'ref_text': ref_text,
            'api_key': api_key or ''
        }
        adapter = SFishTTSAdapter(config)
        adapter.initialize()
        adapter.configure(config)
        
        result = adapter.synthesize(text, save_path)
        adapter.cleanup()
        
        return result.success
        
    except Exception as e:
        print(f"❌ SiliconFlow Fish TTS合成失败: {e}")
        return False 