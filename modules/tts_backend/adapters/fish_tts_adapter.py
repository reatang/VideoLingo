"""
# ----------------------------------------------------------------------------
# Fish TTS适配器
# 
# 实现Fish TTS服务的适配器，使用302.ai API
# 支持角色声音定制和高质量语音合成
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


class FishTTSAdapter(TTSEngineAdapter):
    """Fish TTS适配器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化Fish TTS适配器"""
        super().__init__(config)
        self.version = "1.0.0"
        
        # Fish TTS特定配置
        self.api_key = self.config.get('api_key', '')
        self.character = self.config.get('character', 'default')
        self.character_id_dict = self.config.get('character_id_dict', {})
        self.chunk_length = self.config.get('chunk_length', 200)
        self.normalize = self.config.get('normalize', True)
        self.format = self.config.get('format', 'wav')
        self.latency = self.config.get('latency', 'normal')
        
        # API配置
        self.base_url = "https://api.302.ai/fish-audio/v1/tts"
    
    def initialize(self) -> None:
        """初始化Fish TTS引擎"""
        if not self.api_key:
            raise RuntimeError("❌ Fish TTS需要API密钥")
        
        if not self.character_id_dict:
            print("⚠️  未提供角色ID字典，将使用默认配置")
        
        self._is_initialized = True
        print(f"✅ Fish TTS引擎初始化成功")
    
    def configure(self, config: Dict[str, Any]) -> None:
        """配置Fish TTS参数"""
        self.api_key = config.get('api_key', self.api_key)
        self.character = config.get('character', self.character)
        self.character_id_dict = config.get('character_id_dict', self.character_id_dict)
        self.chunk_length = config.get('chunk_length', self.chunk_length)
        self.normalize = config.get('normalize', self.normalize)
        self.format = config.get('format', self.format)
        self.latency = config.get('latency', self.latency)
        
        # 验证配置
        if self.character not in self.character_id_dict:
            available_chars = list(self.character_id_dict.keys())
            if available_chars:
                self.character = available_chars[0]
                print(f"⚠️  角色 '{config.get('character')}' 不存在，使用: {self.character}")
            else:
                print("⚠️  没有可用的角色配置")
        
        self._is_configured = True
        print(f"🔧 Fish TTS配置完成: character={self.character}")
    
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
            output_path = generate_unique_filename(text, "fish_tts", ".wav")
        
        self._log_synthesis_start(text)
        start_time = time.time()
        
        try:
            # 调用Fish TTS API
            audio_path = self._call_fish_api(text, output_path)
            
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
                voice=self.character,
                language=self._detect_language(text),
                metadata={
                    'engine': 'fish_tts',
                    'character': self.character,
                    'chunk_length': self.chunk_length,
                    'normalize': self.normalize,
                    'latency': self.latency
                }
            )
            
            result = TTSResult(
                segments=[segment],
                total_duration=duration,
                output_path=audio_path,
                metadata={'engine': 'fish_tts', 'character': self.character}
            )
            
            elapsed_time = time.time() - start_time
            self._log_synthesis_complete(elapsed_time, audio_path)
            
            return result
            
        except Exception as e:
            print(f"❌ Fish TTS合成失败: {e}")
            raise
    
    def _call_fish_api(self, text: str, output_path: str) -> str:
        """调用Fish TTS API"""
        # 获取角色ID
        refer_id = self.character_id_dict.get(self.character, 'default')
        
        payload = {
            "text": text,
            "reference_id": refer_id,
            "chunk_length": self.chunk_length,
            "normalize": self.normalize,
            "format": self.format,
            "latency": self.latency
        }
        
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        # 确保输出目录存在
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        # 发送请求（带重试机制）
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    self.base_url,
                    headers=headers,
                    data=json.dumps(payload),
                    timeout=30
                )
                response.raise_for_status()
                response_data = response.json()
                
                if "url" in response_data:
                    # 下载音频文件
                    audio_response = requests.get(response_data["url"], timeout=30)
                    audio_response.raise_for_status()
                    
                    # 保存音频文件
                    with open(output_path, "wb") as f:
                        f.write(audio_response.content)
                    
                    print(f"✅ Fish TTS音频已保存: {output_path}")
                    return output_path
                else:
                    error_msg = f"API响应中没有音频URL: {response_data}"
                    if attempt < max_retries - 1:
                        print(f"⚠️  Fish TTS请求失败 (重试 {attempt + 1}/{max_retries}): {error_msg}")
                        time.sleep(1)
                        continue
                    else:
                        raise RuntimeError(f"❌ Fish TTS请求失败: {error_msg}")
                        
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    print(f"⚠️  Fish TTS网络错误 (重试 {attempt + 1}/{max_retries}): {e}")
                    time.sleep(1)
                    continue
                else:
                    raise RuntimeError(f"❌ Fish TTS网络错误: {e}")
            except json.JSONDecodeError as e:
                if attempt < max_retries - 1:
                    print(f"⚠️  Fish TTS响应解析错误 (重试 {attempt + 1}/{max_retries}): {e}")
                    time.sleep(1)
                    continue
                else:
                    raise RuntimeError(f"❌ Fish TTS响应解析错误: {e}")
        
        raise RuntimeError("❌ Fish TTS请求失败，已达到最大重试次数")
    
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
        
        print(f"🎵 开始Fish TTS批量合成: {len(texts)}个文本片段")
        
        for i, text in enumerate(texts):
            try:
                # 生成输出路径
                output_path = os.path.join(output_dir, f"fish_tts_batch_{i+1:03d}.wav")
                
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
            merged_path = os.path.join(output_dir, "fish_tts_merged.wav")
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
            metadata={'engine': 'fish_tts', 'batch_size': len(texts)}
        )
        
        print(f"✅ Fish TTS批量合成完成: {len(segments)}/{len(texts)} 成功")
        return result
    
    def get_supported_characters(self) -> List[str]:
        """获取支持的角色列表"""
        return list(self.character_id_dict.keys()) if self.character_id_dict else []
    
    def get_supported_languages(self) -> List[str]:
        """获取支持的语言列表"""
        return ['zh-CN', 'en-US', 'ja-JP']
    
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
        print(f"🧹 Fish TTS适配器已清理")


# 便捷函数，保持与原有代码的兼容性
def fish_tts(text: str, 
             save_as: str,
             character: str = "default",
             api_key: str = None,
             character_id_dict: Dict[str, str] = None) -> bool:
    """
    Fish TTS便捷函数（兼容原有接口）
    
    Args:
        text: 要合成的文本
        save_as: 保存路径
        character: 角色名称
        api_key: API密钥
        character_id_dict: 角色ID字典
    
    Returns:
        bool: 是否成功
    """
    try:
        config = {
            'character': character,
            'api_key': api_key or '',
            'character_id_dict': character_id_dict or {}
        }
        adapter = FishTTSAdapter(config)
        adapter.initialize()
        adapter.configure(config)
        
        result = adapter.synthesize(text, save_as)
        adapter.cleanup()
        
        return result.success
        
    except Exception as e:
        print(f"❌ Fish TTS合成失败: {e}")
        return False 