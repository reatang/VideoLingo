"""
# ----------------------------------------------------------------------------
# TTS Backend使用示例
# 
# 展示如何使用modules/tts_backend包进行语音合成
# 包含所有TTS引擎的配置和使用示例
# ----------------------------------------------------------------------------
"""

from modules.tts_backend import TTSFactory
from modules.tts_backend.adapters import *


def example_edge_tts():
    """Edge TTS使用示例"""
    print("=== Edge TTS示例 ===")
    
    config = {
        'voice': 'zh-CN-XiaoxiaoNeural',
        'rate': '+0%',
        'pitch': '+0Hz'
    }
    
    # 方法1：使用工厂模式
    factory = TTSFactory()
    factory.register_engine('edge_tts', config)
    
    result = factory.synthesize('edge_tts', "你好，欢迎使用VideoLingo！", "output/edge_tts_test.wav")
    print(f"合成结果: {result.success}")
    
    # 方法2：直接使用适配器
    adapter = EdgeTTSAdapter(config)
    adapter.initialize()
    adapter.configure(config)
    
    result = adapter.synthesize("这是Edge TTS的测试", "output/edge_tts_direct.wav")
    print(f"直接调用结果: {result.success}")
    
    adapter.cleanup()


def example_openai_tts():
    """OpenAI TTS使用示例"""
    print("=== OpenAI TTS示例 ===")
    
    config = {
        'api_key': 'your-api-key-here',
        'voice': 'alloy',
        'model': 'tts-1',
        'speed': 1.0
    }
    
    adapter = OpenAITTSAdapter(config)
    adapter.initialize()
    adapter.configure(config)
    
    result = adapter.synthesize("Hello, welcome to VideoLingo!", "output/openai_tts_test.wav")
    print(f"OpenAI TTS结果: {result.success}")
    
    adapter.cleanup()


def example_azure_tts():
    """Azure TTS使用示例"""
    print("=== Azure TTS示例 ===")
    
    config = {
        'api_key': 'your-api-key-here',
        'voice': 'zh-CN-XiaoxiaoNeural',
        'output_format': 'riff-16khz-16bit-mono-pcm'
    }
    
    adapter = AzureTTSAdapter(config)
    adapter.initialize()
    adapter.configure(config)
    
    result = adapter.synthesize("Azure TTS语音合成测试", "output/azure_tts_test.wav")
    print(f"Azure TTS结果: {result.success}")
    
    adapter.cleanup()


def example_fish_tts():
    """Fish TTS使用示例"""
    print("=== Fish TTS示例 ===")
    
    config = {
        'api_key': 'your-api-key-here',
        'character': 'bella',
        'character_id_dict': {
            'bella': 'character_id_here'
        }
    }
    
    adapter = FishTTSAdapter(config)
    adapter.initialize()
    adapter.configure(config)
    
    result = adapter.synthesize("Fish TTS语音合成测试", "output/fish_tts_test.wav")
    print(f"Fish TTS结果: {result.success}")
    
    adapter.cleanup()


def example_siliconflow_fish_tts():
    """SiliconFlow Fish TTS使用示例"""
    print("=== SiliconFlow Fish TTS示例 ===")
    
    # 预设模式
    config_preset = {
        'api_key': 'your-api-key-here',
        'voice': 'alex',
        'mode': 'preset'
    }
    
    adapter = SFishTTSAdapter(config_preset)
    adapter.initialize()
    adapter.configure(config_preset)
    
    result = adapter.synthesize("SiliconFlow Fish TTS预设模式测试", "output/sf_fish_preset.wav")
    print(f"SiliconFlow Fish TTS预设模式结果: {result.success}")
    
    # 动态模式
    config_dynamic = {
        'api_key': 'your-api-key-here',
        'mode': 'dynamic',
        'ref_audio': 'path/to/reference.wav',
        'ref_text': '参考音频的文本内容'
    }
    
    adapter.configure(config_dynamic)
    result = adapter.synthesize("动态模式语音克隆测试", "output/sf_fish_dynamic.wav")
    print(f"SiliconFlow Fish TTS动态模式结果: {result.success}")
    
    adapter.cleanup()


def example_gpt_sovits():
    """GPT-SoVITS使用示例"""
    print("=== GPT-SoVITS示例 ===")
    
    config = {
        'character': 'your_character_name',
        'refer_mode': 1,
        'text_lang': 'zh',
        'prompt_lang': 'zh'
    }
    
    adapter = GPTSoVITSAdapter(config)
    adapter.initialize()
    adapter.configure(config)
    
    result = adapter.synthesize("GPT-SoVITS本地语音合成测试", "output/gpt_sovits_test.wav")
    print(f"GPT-SoVITS结果: {result.success}")
    
    adapter.cleanup()


def example_custom_tts():
    """自定义TTS使用示例"""
    print("=== 自定义TTS示例 ===")
    
    # API模式示例
    config_api = {
        'mode': 'api',
        'api_url': 'https://your-custom-tts-api.com/synthesize',
        'api_key': 'your-api-key',
        'voice': 'custom_voice',
        'response_format': 'audio',
        'request_method': 'POST'
    }
    
    adapter = CustomTTSAdapter(config_api)
    adapter.initialize()
    adapter.configure(config_api)
    
    result = adapter.synthesize("自定义TTS API模式测试", "output/custom_api_test.wav")
    print(f"自定义TTS API模式结果: {result.success}")
    
    # 命令行模式示例
    config_command = {
        'mode': 'command',
        'command_template': 'python tts_script.py --text "{text}" --output "{output}" --voice "{voice}"',
        'working_dir': '/path/to/tts/directory'
    }
    
    adapter.configure(config_command)
    result = adapter.synthesize("命令行模式测试", "output/custom_command_test.wav")
    print(f"自定义TTS命令行模式结果: {result.success}")
    
    # 自定义处理函数模式
    config_custom = {
        'mode': 'custom',
        'custom_processor': example_custom_processor
    }
    
    adapter.configure(config_custom)
    result = adapter.synthesize("自定义处理函数测试", "output/custom_func_test.wav")
    print(f"自定义TTS函数模式结果: {result.success}")
    
    adapter.cleanup()


def example_batch_processing():
    """批量处理示例"""
    print("=== 批量处理示例 ===")
    
    texts = [
        "这是第一句话",
        "这是第二句话", 
        "这是第三句话"
    ]
    
    config = {
        'voice': 'zh-CN-XiaoxiaoNeural'
    }
    
    adapter = EdgeTTSAdapter(config)
    adapter.initialize()
    adapter.configure(config)
    
    result = adapter.synthesize_batch(texts, "output/batch_test")
    print(f"批量处理结果: {len(result.segments)}/{len(texts)} 成功")
    print(f"总时长: {result.total_duration:.2f}秒")
    
    adapter.cleanup()


def example_factory_usage():
    """工厂模式使用示例"""
    print("=== 工厂模式示例 ===")
    
    factory = TTSFactory()
    
    # 注册多个引擎
    factory.register_engine('edge_tts', {
        'voice': 'zh-CN-XiaoxiaoNeural'
    })
    
    factory.register_engine('openai_tts', {
        'api_key': 'your-openai-key',
        'voice': 'alloy'
    })
    
    # 设置默认引擎
    factory.set_default_engine('edge_tts')
    
    # 使用默认引擎
    result = factory.synthesize_default("使用默认引擎合成", "output/factory_default.wav")
    print(f"工厂默认引擎结果: {result.success}")
    
    # 使用指定引擎
    result = factory.synthesize('openai_tts', "Using specific engine", "output/factory_openai.wav")
    print(f"工厂指定引擎结果: {result.success}")
    
    # 自动选择引擎
    result = factory.auto_synthesize("自动选择最佳引擎", "output/factory_auto.wav")
    print(f"工厂自动选择结果: {result.success}")


def example_convenience_functions():
    """便捷函数使用示例"""
    print("=== 便捷函数示例 ===")
    
    # 使用便捷函数（向后兼容）
    success = edge_tts_synthesize(
        text="便捷函数测试",
        output_path="output/convenience_edge.wav",
        voice="zh-CN-XiaoxiaoNeural"
    )
    print(f"Edge TTS便捷函数结果: {success}")
    
    success = openai_tts(
        text="Convenience function test",
        save_path="output/convenience_openai.wav",
        voice="alloy",
        api_key="your-api-key"
    )
    print(f"OpenAI TTS便捷函数结果: {success is not None}")


if __name__ == "__main__":
    """运行所有示例"""
    import os
    
    # 创建输出目录
    os.makedirs("output", exist_ok=True)
    
    print("🎵 TTS Backend使用示例")
    print("=" * 50)
    
    # 运行示例（根据需要启用）
    example_edge_tts()
    # example_openai_tts()  # 需要API密钥
    # example_azure_tts()   # 需要API密钥
    # example_fish_tts()    # 需要API密钥
    # example_siliconflow_fish_tts()  # 需要API密钥
    # example_gpt_sovits()  # 需要本地服务
    example_custom_tts()
    example_batch_processing()
    example_factory_usage()
    example_convenience_functions()
    
    print("=" * 50)
    print("✅ 示例运行完成！") 