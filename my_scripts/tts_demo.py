# 简单使用
from modules.tts_backend import TTSEngineFactory
from modules.tts_backend.adapters import EdgeTTSAdapter


factory = TTSEngineFactory()
factory.register_engine('edge_tts', EdgeTTSAdapter)

# 从工厂中获取引擎
engine :EdgeTTSAdapter = factory.create_engine('edge_tts')
result = engine.synthesize("Edge TTS引擎初始化成功", "my_scripts/output/test.wav")
engine.cleanup()


# 便捷函数（向后兼容）
from modules.tts_backend.adapters import edge_tts
success = edge_tts("Edge TTS引擎初始化成功222", "my_scripts/output/test2.wav", "zh-CN-XiaoxiaoNeural")