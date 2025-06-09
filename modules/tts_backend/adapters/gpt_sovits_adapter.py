"""
# ----------------------------------------------------------------------------
# GPT-SoVITS适配器
# 
# 实现本地GPT-SoVITS服务的适配器
# 支持中文和英文语音合成，需要本地服务器运行
# ----------------------------------------------------------------------------
"""

import os
import sys
import time
import socket
import subprocess
import requests
from typing import Dict, List, Optional, Any
from pathlib import Path

from ..base import TTSEngineAdapter, TTSResult, AudioSegment
from ..utils import validate_audio_output, generate_unique_filename


class GPTSoVITSAdapter(TTSEngineAdapter):
    """GPT-SoVITS适配器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化GPT-SoVITS适配器"""
        super().__init__(config)
        self.version = "1.0.0"
        
        # GPT-SoVITS特定配置
        self.character = self.config.get('character', 'default')
        self.refer_mode = self.config.get('refer_mode', 1)
        self.speed_factor = self.config.get('speed_factor', 1.0)
        
        # 服务器配置
        self.server_host = self.config.get('server_host', '127.0.0.1')
        self.server_port = self.config.get('server_port', 9880)
        self.base_url = f"http://{self.server_host}:{self.server_port}"
        
        # 语言配置
        self.text_lang = self.config.get('text_lang', 'zh')
        self.prompt_lang = self.config.get('prompt_lang', 'zh')
        
        # 服务器进程
        self.server_process = None
    
    def initialize(self) -> None:
        """初始化GPT-SoVITS引擎"""
        if not self.character:
            raise RuntimeError("❌ GPT-SoVITS需要指定角色配置")
        
        # 启动GPT-SoVITS服务器
        self._start_server()
        
        self._is_initialized = True
        print(f"✅ GPT-SoVITS引擎初始化成功")
    
    def configure(self, config: Dict[str, Any]) -> None:
        """配置GPT-SoVITS参数"""
        self.character = config.get('character', self.character)
        self.refer_mode = config.get('refer_mode', self.refer_mode)
        self.speed_factor = config.get('speed_factor', self.speed_factor)
        self.text_lang = config.get('text_lang', self.text_lang)
        self.prompt_lang = config.get('prompt_lang', self.prompt_lang)
        
        # 验证配置
        if self.refer_mode not in [1, 2, 3]:
            print(f"⚠️  不支持的参考模式: {self.refer_mode}，使用默认模式 1")
            self.refer_mode = 1
        
        if not (0.5 <= self.speed_factor <= 2.0):
            print(f"⚠️  速度超出范围: {self.speed_factor}，调整为1.0")
            self.speed_factor = 1.0
        
        self._is_configured = True
        print(f"🔧 GPT-SoVITS配置完成: character={self.character}, refer_mode={self.refer_mode}")
    
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
            output_path = generate_unique_filename(text, "gpt_sovits", ".wav")
        
        self._log_synthesis_start(text)
        start_time = time.time()
        
        try:
            # 准备参考音频和文本
            ref_audio_path, prompt_text = self._prepare_reference()
            
            # 调用GPT-SoVITS API
            audio_path = self._call_gpt_sovits_api(
                text, output_path, ref_audio_path, prompt_text
            )
            
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
                language=self.text_lang,
                metadata={
                    'engine': 'gpt_sovits',
                    'character': self.character,
                    'refer_mode': self.refer_mode,
                    'speed_factor': self.speed_factor,
                    'text_lang': self.text_lang,
                    'prompt_lang': self.prompt_lang
                }
            )
            
            result = TTSResult(
                segments=[segment],
                total_duration=duration,
                output_path=audio_path,
                metadata={'engine': 'gpt_sovits', 'character': self.character}
            )
            
            elapsed_time = time.time() - start_time
            self._log_synthesis_complete(elapsed_time, audio_path)
            
            return result
            
        except Exception as e:
            print(f"❌ GPT-SoVITS合成失败: {e}")
            raise
    
    def _start_server(self) -> None:
        """启动GPT-SoVITS服务器"""
        # 检查端口是否已被占用
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex((self.server_host, self.server_port))
        if result == 0:
            sock.close()
            print(f"✅ GPT-SoVITS服务器已在运行: {self.base_url}")
            return
        sock.close()
        
        print(f"🚀 正在启动GPT-SoVITS服务器...")
        print(f"🚀 请等待大约1分钟，服务器启动过程中可能出现404警告是正常的")
        
        try:
            # 查找GPT-SoVITS目录和配置文件
            gpt_sovits_dir, config_path = self._find_gpt_sovits_path()
            
            # 切换到GPT-SoVITS目录
            os.chdir(gpt_sovits_dir)
            
            # 启动服务器
            if sys.platform == "win32":
                cmd = [
                    "runtime\\python.exe",
                    "api_v2.py",
                    "-a", self.server_host,
                    "-p", str(self.server_port),
                    "-c", str(config_path)
                ]
                # 在Windows上打开新窗口
                self.server_process = subprocess.Popen(
                    cmd, 
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )
            elif sys.platform == "darwin":  # macOS
                print("请手动启动GPT-SoVITS服务器，参考api_v2.py")
                while True:
                    user_input = input("已启动服务器吗? (y/n): ").lower()
                    if user_input == 'y':
                        break
                    elif user_input == 'n':
                        raise Exception("请先启动服务器")
            else:
                raise OSError("不支持的操作系统，仅支持Windows和macOS")
            
            # 切换回原目录
            os.chdir(Path.cwd())
            
            # 等待服务器启动
            self._wait_for_server()
            
        except Exception as e:
            raise RuntimeError(f"❌ GPT-SoVITS服务器启动失败: {e}")
    
    def _wait_for_server(self) -> None:
        """等待服务器启动"""
        start_time = time.time()
        timeout = 60  # 60秒超时
        
        while time.time() - start_time < timeout:
            try:
                time.sleep(2)
                response = requests.get(f"{self.base_url}/ping", timeout=5)
                if response.status_code == 200:
                    print(f"✅ GPT-SoVITS服务器已就绪: {self.base_url}")
                    return
            except requests.exceptions.RequestException:
                pass
        
        raise RuntimeError(f"❌ GPT-SoVITS服务器启动超时 ({timeout}秒)")
    
    def _find_gpt_sovits_path(self) -> tuple:
        """查找GPT-SoVITS路径和配置文件"""
        current_dir = Path(__file__).resolve().parent.parent.parent.parent
        parent_dir = current_dir.parent
        
        # 查找GPT-SoVITS目录
        gpt_sovits_dir = None
        for d in parent_dir.iterdir():
            if d.is_dir() and d.name.startswith('GPT-SoVITS-v2'):
                gpt_sovits_dir = d
                break
        
        if gpt_sovits_dir is None:
            raise FileNotFoundError("未找到GPT-SoVITS-v2目录")
        
        # 查找配置文件
        config_path = gpt_sovits_dir / "GPT_SoVITS" / "configs" / f"{self.character}.yaml"
        if not config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")
        
        return gpt_sovits_dir, config_path
    
    def _prepare_reference(self) -> tuple:
        """准备参考音频和文本"""
        ref_audio_path = None
        prompt_text = ""
        
        if self.refer_mode == 1:
            # 使用默认参考音频
            _, config_path = self._find_gpt_sovits_path()
            config_dir = config_path.parent
            
            # 查找参考音频文件
            ref_audio_files = (
                list(config_dir.glob(f"{self.character}_*.wav")) +
                list(config_dir.glob(f"{self.character}_*.mp3"))
            )
            if not ref_audio_files:
                raise FileNotFoundError(f"未找到角色 {self.character} 的参考音频")
            
            ref_audio_path = ref_audio_files[0]
            
            # 从文件名提取内容
            content = ref_audio_path.stem.split('_', 1)[1]
            prompt_text = content
            
            # 检测语言
            self.prompt_lang = 'zh' if any('\u4e00' <= char <= '\u9fff' for char in content) else 'en'
            
        elif self.refer_mode == 2:
            # 使用第一段参考音频
            ref_audio_path = Path("output/audio/refers/1.wav")
            if not ref_audio_path.exists():
                self._extract_reference_audio()
            
        elif self.refer_mode == 3:
            # 使用对应段落的参考音频
            # 这里需要根据具体实现来获取段落号
            # 暂时使用第一段作为fallback
            ref_audio_path = Path("output/audio/refers/1.wav")
            if not ref_audio_path.exists():
                self._extract_reference_audio()
        
        return ref_audio_path, prompt_text
    
    def _extract_reference_audio(self) -> None:
        """提取参考音频"""
        try:
            # 这里应该调用参考音频提取模块
            # 由于依赖关系，暂时抛出异常提示
            raise RuntimeError("参考音频文件不存在，请先运行参考音频提取")
        except Exception as e:
            print(f"⚠️  参考音频提取失败: {e}")
            raise
    
    def _call_gpt_sovits_api(self, text: str, output_path: str, 
                            ref_audio_path: Path, prompt_text: str) -> str:
        """调用GPT-SoVITS API"""
        # 检查和规范化语言代码
        text_lang, prompt_lang = self._check_lang(self.text_lang, self.prompt_lang)
        
        payload = {
            'text': text,
            'text_lang': text_lang,
            'ref_audio_path': str(ref_audio_path),
            'prompt_lang': prompt_lang,
            'prompt_text': prompt_text,
            'speed_factor': self.speed_factor,
        }
        
        # 确保输出目录存在
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        try:
            response = requests.post(
                f"{self.base_url}/tts",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                # 保存音频文件
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                
                print(f"✅ GPT-SoVITS音频已保存: {output_path}")
                return output_path
            else:
                raise RuntimeError(f"❌ GPT-SoVITS请求失败: HTTP {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"❌ GPT-SoVITS网络错误: {e}")
    
    def _check_lang(self, text_lang: str, prompt_lang: str) -> tuple:
        """检查和规范化语言代码"""
        # 规范化文本语言
        if any(lang in text_lang.lower() for lang in ['zh', 'cn', '中文', 'chinese']):
            text_lang = 'zh'
        elif any(lang in text_lang.lower() for lang in ['英文', '英语', 'english']):
            text_lang = 'en'
        else:
            raise ValueError("不支持的文本语言，仅支持中文和英文")
        
        # 规范化提示语言
        if any(lang in prompt_lang.lower() for lang in ['en', 'english', '英文', '英语']):
            prompt_lang = 'en'
        elif any(lang in prompt_lang.lower() for lang in ['zh', 'cn', '中文', 'chinese']):
            prompt_lang = 'zh'
        else:
            raise ValueError("不支持的提示语言，仅支持中文和英文")
        
        return text_lang, prompt_lang
    
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
        
        print(f"🎵 开始GPT-SoVITS批量合成: {len(texts)}个文本片段")
        
        for i, text in enumerate(texts):
            try:
                # 生成输出路径
                output_path = os.path.join(output_dir, f"gpt_sovits_batch_{i+1:03d}.wav")
                
                # 合成单个片段
                result = self.synthesize(text, output_path)
                
                if result.segments:
                    segment = result.segments[0]
                    segment.start_time = total_duration
                    segment.end_time = total_duration + (segment.duration or 0)
                    segments.append(segment)
                    total_duration += (segment.duration or 0)
                
                print(f"✅ 批量合成进度: {i+1}/{len(texts)}")
                
                # 添加延迟避免服务器过载
                time.sleep(0.2)
                
            except Exception as e:
                print(f"❌ 批量合成失败 ({i+1}/{len(texts)}): {e}")
                continue
        
        # 合并音频文件（可选）
        if len(segments) > 1:
            merged_path = os.path.join(output_dir, "gpt_sovits_merged.wav")
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
            metadata={'engine': 'gpt_sovits', 'batch_size': len(texts)}
        )
        
        print(f"✅ GPT-SoVITS批量合成完成: {len(segments)}/{len(texts)} 成功")
        return result
    
    def get_supported_languages(self) -> List[str]:
        """获取支持的语言列表"""
        return ['zh', 'en']
    
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
        if self.server_process:
            try:
                self.server_process.terminate()
                self.server_process.wait(timeout=5)
                print(f"🧹 GPT-SoVITS服务器已停止")
            except subprocess.TimeoutExpired:
                self.server_process.kill()
                print(f"🧹 GPT-SoVITS服务器已强制停止")
            except Exception as e:
                print(f"⚠️  停止GPT-SoVITS服务器失败: {e}")
        
        super().cleanup()
        print(f"🧹 GPT-SoVITS适配器已清理")


# 便捷函数，保持与原有代码的兼容性
def gpt_sovits_tts(text: str,
                  text_lang: str,
                  save_path: str,
                  ref_audio_path: str,
                  prompt_lang: str,
                  prompt_text: str) -> bool:
    """
    GPT-SoVITS便捷函数（兼容原有接口）
    
    Args:
        text: 要合成的文本
        text_lang: 文本语言
        save_path: 保存路径
        ref_audio_path: 参考音频路径
        prompt_lang: 提示语言
        prompt_text: 提示文本
    
    Returns:
        bool: 是否成功
    """
    try:
        config = {
            'text_lang': text_lang,
            'prompt_lang': prompt_lang,
            'ref_audio': ref_audio_path,
            'ref_text': prompt_text
        }
        adapter = GPTSoVITSAdapter(config)
        adapter.initialize()
        adapter.configure(config)
        
        result = adapter.synthesize(text, save_path)
        adapter.cleanup()
        
        return result.success
        
    except Exception as e:
        print(f"❌ GPT-SoVITS合成失败: {e}")
        return False 