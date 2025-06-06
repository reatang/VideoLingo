"""
# ----------------------------------------------------------------------------
# 配置工具函数
# 
# 提供配置相关的实用工具函数，包括语言验证、默认配置生成等
# 基于项目实际的配置需求设计
# ----------------------------------------------------------------------------
"""

from typing import Dict, List, Any, Optional
from pathlib import Path


def get_joiner(language: str, config_manager=None) -> str:
    """
    根据语言获取分词连接符
    
    Args:
        language: 语言代码
        config_manager: 配置管理器实例，如果为None则使用全局实例
        
    Returns:
        连接符（空格或空字符串）
    """
    if config_manager is None:
        from . import get_global_config
        config_manager = get_global_config()
    
    # 获取语言分隔配置
    with_space = config_manager.load_key('language_split_with_space', [])
    without_space = config_manager.load_key('language_split_without_space', [])
    
    if language in with_space:
        return " "
    elif language in without_space:
        return ""
    else:
        # 默认使用空格，并给出警告
        print(f"⚠️  未知语言代码: {language}, 使用默认空格分隔")
        return " "


def validate_language_code(language: str, config_manager=None) -> bool:
    """
    验证语言代码是否受支持
    
    Args:
        language: 语言代码
        config_manager: 配置管理器实例
        
    Returns:
        是否支持该语言
    """
    if config_manager is None:
        from . import get_global_config
        config_manager = get_global_config()
    
    supported_languages = config_manager.get_supported_languages()
    all_languages = supported_languages['with_space'] + supported_languages['without_space']
    
    return language in all_languages


def get_whisper_model_path(model_name: str, config_manager=None) -> Path:
    """
    获取Whisper模型的完整路径
    
    Args:
        model_name: 模型名称
        config_manager: 配置管理器实例
        
    Returns:
        模型文件路径
    """
    if config_manager is None:
        from . import get_global_config
        config_manager = get_global_config()
    
    model_dir = config_manager.get_model_dir()
    return model_dir / model_name


def validate_file_format(file_path: str, format_type: str, config_manager=None) -> bool:
    """
    验证文件格式是否受支持
    
    Args:
        file_path: 文件路径
        format_type: 格式类型 ('video' 或 'audio')
        config_manager: 配置管理器实例
        
    Returns:
        是否支持该格式
    """
    if config_manager is None:
        from . import get_global_config
        config_manager = get_global_config()
    
    file_ext = Path(file_path).suffix.lower().lstrip('.')
    allowed_formats = config_manager.get_allowed_formats()
    
    if format_type == 'video':
        return file_ext in allowed_formats['video']
    elif format_type == 'audio':
        return file_ext in allowed_formats['audio']
    else:
        return False


def get_api_config_for_service(service: str, config_manager=None) -> Dict[str, Any]:
    """
    获取特定服务的API配置
    
    Args:
        service: 服务名称 ('whisper', 'tts', 'llm')
        config_manager: 配置管理器实例
        
    Returns:
        API配置字典
    """
    if config_manager is None:
        from . import get_global_config
        config_manager = get_global_config()
    
    if service == 'whisper':
        whisper_config = config_manager.get_whisper_config()
        runtime = whisper_config.get('runtime', 'local')
        
        if runtime == 'cloud':
            return {
                'api_key': whisper_config.get('whisperX_302_api_key'),
                'service': '302.ai'
            }
        elif runtime == 'elevenlabs':
            return {
                'api_key': whisper_config.get('elevenlabs_api_key'),
                'service': 'ElevenLabs'
            }
        else:
            return {'service': 'local'}
    
    elif service == 'tts':
        tts_method = config_manager.load_key('tts_method', 'edge_tts')
        tts_config = config_manager.get_tts_config(tts_method)
        return tts_config
    
    elif service == 'llm':
        return config_manager.get_api_config()
    
    else:
        return {}


def get_default_config() -> Dict[str, Any]:
    """
    获取默认配置模板
    
    Returns:
        默认配置字典
    """
    return {
        "display_language": "zh-CN",
        "target_language": "英文",
        "demucs": True,
        "whisper": {
            "model": "large-v3",
            "language": "zh", 
            "runtime": "local"
        },
        "burn_subtitles": True,
        "tts_method": "edge_tts",
        "edge_tts": {
            "voice": "zh-CN-XiaoxiaoNeural"
        },
        "api": {
            "model": "deepseek-ai/DeepSeek-V3",
            "max_workers": 4
        },
        "model_dir": "./_model_cache",
        "allowed_video_formats": ["mp4", "mov", "avi", "mkv"],
        "allowed_audio_formats": ["wav", "mp3", "flac", "m4a"],
        "language_split_with_space": ["en", "es", "fr", "de", "it", "ru"],
        "language_split_without_space": ["zh", "ja"]
    }


def get_optimal_whisper_settings(language: str = 'zh') -> Dict[str, Any]:
    """
    根据语言获取推荐的Whisper设置
    
    Args:
        language: 目标语言
        
    Returns:
        推荐的Whisper配置
    """
    if language == 'zh':
        return {
            "model": "large-v3",
            "language": "zh",
            "runtime": "local"
        }
    elif language == 'en':
        return {
            "model": "large-v3-turbo", 
            "language": "en",
            "runtime": "local"
        }
    else:
        return {
            "model": "large-v3",
            "language": "auto",
            "runtime": "local"
        }


def validate_api_keys(config_manager=None) -> Dict[str, bool]:
    """
    验证各种API密钥是否已配置
    
    Args:
        config_manager: 配置管理器实例
        
    Returns:
        各服务API密钥的配置状态
    """
    if config_manager is None:
        from . import get_global_config
        config_manager = get_global_config()
    
    status = {}
    
    # 检查LLM API密钥
    api_config = config_manager.get_api_config()
    status['llm_api'] = bool(api_config.get('key', '').strip())
    
    # 检查Whisper API密钥
    whisper_config = config_manager.get_whisper_config()
    runtime = whisper_config.get('runtime', 'local')
    
    if runtime == 'cloud':
        status['whisper_302'] = bool(whisper_config.get('whisperX_302_api_key', '').strip())
    elif runtime == 'elevenlabs':
        status['whisper_elevenlabs'] = bool(whisper_config.get('elevenlabs_api_key', '').strip())
    
    # 检查TTS API密钥
    tts_method = config_manager.load_key('tts_method', 'edge_tts')
    if 'api_key' in config_manager.get_tts_config(tts_method):
        tts_config = config_manager.get_tts_config(tts_method)
        status[f'tts_{tts_method}'] = bool(tts_config.get('api_key', '').strip())
    
    return status


def get_spacy_model(language: str, config_manager=None) -> Optional[str]:
    """
    获取指定语言的Spacy模型名称
    
    Args:
        language: 语言代码
        config_manager: 配置管理器实例
        
    Returns:
        Spacy模型名称，如果不支持则返回None
    """
    if config_manager is None:
        from . import get_global_config
        config_manager = get_global_config()
    
    spacy_map = config_manager.load_key('spacy_model_map', {})
    return spacy_map.get(language)


def create_config_backup(config_manager=None) -> Path:
    """
    创建配置文件备份
    
    Args:
        config_manager: 配置管理器实例
        
    Returns:
        备份文件路径
    """
    if config_manager is None:
        from . import get_global_config
        config_manager = get_global_config()
    
    import shutil
    from datetime import datetime
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = config_manager.config_path.with_name(f"config_backup_{timestamp}.yaml")
    
    shutil.copy2(config_manager.config_path, backup_path)
    print(f"✅ 配置备份已创建: {backup_path}")
    
    return backup_path


def restore_config_from_backup(backup_path: str, config_manager=None) -> bool:
    """
    从备份文件恢复配置
    
    Args:
        backup_path: 备份文件路径
        config_manager: 配置管理器实例
        
    Returns:
        是否恢复成功
    """
    if config_manager is None:
        from . import get_global_config
        config_manager = get_global_config()
    
    try:
        import shutil
        backup_file = Path(backup_path)
        
        if not backup_file.exists():
            print(f"❌ 备份文件不存在: {backup_path}")
            return False
        
        shutil.copy2(backup_file, config_manager.config_path)
        config_manager.reload_config()
        
        print(f"✅ 配置已从备份恢复: {backup_path}")
        return True
        
    except Exception as e:
        print(f"❌ 恢复配置失败: {str(e)}")
        return False 