"""
# ----------------------------------------------------------------------------
# TTS Backend Package
# 
# 文本转语音后端包，支持多种TTS引擎适配器
# 使用适配器模式统一不同TTS服务的接口
# 支持配置管理、工厂模式和生命周期管理
# ----------------------------------------------------------------------------
"""

# 版本信息
__version__ = '1.0.0'

# 导入核心接口
try:
    from .base import TTSEngineBase, TTSResult, AudioSegment
    from .factory import TTSEngineFactory, create_tts_engine, get_available_engines
    from .factory import cleanup_all_engines, get_engine_status_report
    from .config import TTSConfig, get_tts_config_for_engine
    from .utils import TTSProcessor, validate_audio_output
    
    __all__ = [
        # 基础类和数据模型
        'TTSEngineBase',
        'TTSResult', 
        'AudioSegment',
        
        # 工厂和管理
        'TTSEngineFactory',
        'create_tts_engine',
        'get_available_engines',
        'cleanup_all_engines',
        'get_engine_status_report',
        
        # 配置管理
        'TTSConfig',
        'get_tts_config_for_engine',
        
        # 工具类
        'TTSProcessor',
        'validate_audio_output',
    ]
    
except ImportError as e:
    # 安装时可能缺少依赖，不影响包的导入
    __all__ = []
    print(f"⚠️  TTS后端包部分功能不可用: {e}")

# 便捷函数
def synthesize_text(text: str, 
                   engine_type: str = "edge_tts",
                   voice: str = None,
                   output_path: str = None) -> str:
    """
    便捷的文本转语音函数
    
    Args:
        text: 要转换的文本
        engine_type: TTS引擎类型
        voice: 声音类型（可选）
        output_path: 输出路径（可选）
    
    Returns:
        生成的音频文件路径
    """
    try:
        engine = create_tts_engine(engine_type)
        config = {"voice": voice} if voice else {}
        result = engine.synthesize(text, config)
        
        if output_path and result.audio_path:
            import shutil
            shutil.copy2(result.audio_path, output_path)
            return output_path
        
        return result.audio_path
        
    except Exception as e:
        print(f"❌ TTS合成失败: {e}")
        raise

def get_supported_voices(engine_type: str) -> list:
    """
    获取指定引擎支持的声音列表
    
    Args:
        engine_type: TTS引擎类型
        
    Returns:
        支持的声音列表
    """
    try:
        engine = create_tts_engine(engine_type)
        return engine.get_supported_voices()
    except Exception as e:
        print(f"❌ 获取声音列表失败: {e}")
        return [] 