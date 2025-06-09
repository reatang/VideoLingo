"""
# ----------------------------------------------------------------------------
# SiliconFlow CosyVoice2适配器
# 
# 实现SiliconFlow平台的CosyVoice2服务适配器
# 支持多语言语音合成和角色声音定制
# ----------------------------------------------------------------------------
"""

import os
import time
import json
import requests
from typing import Dict, List, Optional, Any
from pathlib import Path

from ..base import TTSEngineAdapter, TTSResult, AudioSegment
from ..utils import validate_audio_output, generate_unique_filename


class SFCosyVoice2Adapter(TTSEngineAdapter):
    """SiliconFlow CosyVoice2适配器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化SiliconFlow CosyVoice2适配器"""
        super().__init__(config)
        self.version = "1.0.0"
        
        # SiliconFlow CosyVoice2特定配置
        self.api_key = self.config.get('api_key', '')
        self.voice = self.config.get('voice', 'zh-CN-xiaoxiao')
        self.speed = self.config.get('speed', 1.0)
        self.volume = self.config.get('volume', 1.0)
        
        # API配置
        self.base_url = "https://api.siliconflow.cn/v1/audio/speech"
        self.model_name = "FunAudioLLM/CosyVoice2-0.5B"
        
        # 支持的声音列表
        self.supported_voices = [
            'zh-CN-xiaoxiao', 'zh-CN-xiaoyan', 'zh-CN-xiaoyu',
            'en-US-emma', 'en-US-alex', 'ja-JP-yuki', 'ko-KR-minho'
        ]
    
    def initialize(self) -> None:
        """初始化SiliconFlow CosyVoice2引擎"""
        if not self.api_key:
            raise RuntimeError("❌ SiliconFlow CosyVoice2需要API密钥")
        
        self._is_initialized = True
        print(f"✅ SiliconFlow CosyVoice2引擎初始化成功")
    
    def configure(self, config: Dict[str, Any]) -> None:
        """配置SiliconFlow CosyVoice2参数"""
        self.api_key = config.get('api_key', self.api_key)
        self.voice = config.get('voice', self.voice)
        self.speed = config.get('speed', self.speed)
        self.volume = config.get('volume', self.volume)
        
        # 验证配置
        if self.voice not in self.supported_voices:
            print(f"⚠️  不支持的声音: {self.voice}，使用默认声音")
            self.voice = 'zh-CN-xiaoxiao'
        
        if not (0.5 <= self.speed <= 2.0):
            print(f"⚠️  速度超出范围: {self.speed}，调整为1.0")
            self.speed = 1.0
        
        if not (0.1 <= self.volume <= 2.0):
            print(f"⚠️  音量超出范围: {self.volume}，调整为1.0")
            self.volume = 1.0
        
        self._is_configured = True
        print(f"🔧 SiliconFlow CosyVoice2配置完成: voice={self.voice}")
    
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
            output_path = generate_unique_filename(text, "sf_cosyvoice2", ".wav")
        
        self._log_synthesis_start(text)
        start_time = time.time()
        
        try:
            # 调用SiliconFlow CosyVoice2 API
            audio_path = self._call_cosyvoice2_api(text, output_path)
            
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
                    'engine': 'sf_cosyvoice2',
                    'voice': self.voice,
                    'speed': self.speed,
                    'volume': self.volume,
                    'model': self.model_name
                }
            )
            
            result = TTSResult(
                segments=[segment],
                total_duration=duration,
                output_path=audio_path,
                metadata={'engine': 'sf_cosyvoice2', 'voice': self.voice}
            )
            
            elapsed_time = time.time() - start_time
            self._log_synthesis_complete(elapsed_time, audio_path)
            
            return result
            
        except Exception as e:
            print(f"❌ SiliconFlow CosyVoice2合成失败: {e}")
            raise
    
    def _call_cosyvoice2_api(self, text: str, output_path: str) -> str:
        """调用SiliconFlow CosyVoice2 API"""
        payload = {
            "model": self.model_name,
            "input": text,
            "voice": self.voice,
            "response_format": "wav",
            "speed": self.speed
        }
        
        headers = {
            "Authorization": f'Bearer {self.api_key}',
            "Content-Type": "application/json"
        }
        
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
                    timeout=60
                )
                
                if response.status_code == 200:
                    # 保存音频文件
                    with open(output_path, 'wb') as f:
                        f.write(response.content)
                    
                    print(f"✅ SiliconFlow CosyVoice2音频已保存: {output_path}")
                    return output_path
                else:
                    error_msg = f"HTTP {response.status_code}: {response.text}"
                    if attempt < max_retries - 1:
                        print(f"⚠️  SiliconFlow CosyVoice2请求失败 (重试 {attempt + 1}/{max_retries}): {error_msg}")
                        time.sleep(2)
                        continue
                    else:
                        raise RuntimeError(f"❌ SiliconFlow CosyVoice2请求失败: {error_msg}")
                        
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    print(f"⚠️  SiliconFlow CosyVoice2网络错误 (重试 {attempt + 1}/{max_retries}): {e}")
                    time.sleep(2)
                    continue
                else:
                    raise RuntimeError(f"❌ SiliconFlow CosyVoice2网络错误: {e}")
        
        raise RuntimeError("❌ SiliconFlow CosyVoice2请求失败，已达到最大重试次数")
    
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
        
        print(f"🎵 开始SiliconFlow CosyVoice2批量合成: {len(texts)}个文本片段")
        
        for i, text in enumerate(texts):
            try:
                # 生成输出路径
                output_path = os.path.join(output_dir, f"sf_cosyvoice2_batch_{i+1:03d}.wav")
                
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
            merged_path = os.path.join(output_dir, "sf_cosyvoice2_merged.wav")
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
            metadata={'engine': 'sf_cosyvoice2', 'batch_size': len(texts)}
        )
        
        print(f"✅ SiliconFlow CosyVoice2批量合成完成: {len(segments)}/{len(texts)} 成功")
        return result
    
    def get_supported_voices(self) -> List[str]:
        """获取支持的声音列表"""
        return self.supported_voices.copy()
    
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
        print(f"🧹 SiliconFlow CosyVoice2适配器已清理")


# 便捷函数，保持与原有代码的兼容性
def sf_cosyvoice2_tts(text: str, 
                     save_path: str,
                     voice: str = "zh-CN-xiaoxiao",
                     api_key: str = None) -> bool:
    """
    SiliconFlow CosyVoice2便捷函数
    
    Args:
        text: 要合成的文本
        save_path: 保存路径
        voice: 声音类型
        api_key: API密钥
    
    Returns:
        bool: 是否成功
    """
    try:
        config = {
            'voice': voice,
            'api_key': api_key or ''
        }
        adapter = SFCosyVoice2Adapter(config)
        adapter.initialize()
        adapter.configure(config)
        
        result = adapter.synthesize(text, save_path)
        adapter.cleanup()
        
        return result.success
        
    except Exception as e:
        print(f"❌ SiliconFlow CosyVoice2合成失败: {e}")
        return False 