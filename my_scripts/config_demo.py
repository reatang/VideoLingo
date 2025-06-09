#!/usr/bin/env python3
"""
# ----------------------------------------------------------------------------
# 配置管理系统演示程序
# 
# 演示如何使用新开发的配置管理模块：
# 1. 基础配置读取和更新
# 2. 专用配置获取器
# 3. 配置验证和工具函数
# 4. 配置数据模型使用
# 5. ASR适配器配置集成
# ----------------------------------------------------------------------------
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def demo_basic_config_access():
    """演示基础配置读取功能"""
    print("🔧 演示基础配置读取功能")
    print("-" * 50)
    
    try:
        from modules.configs import load_key, update_key, ConfigManager
        
        # 1. 使用便捷函数读取配置
        print("1. 使用便捷函数读取配置...")
        display_lang = load_key('display_language', 'zh-CN')
        target_lang = load_key('target_language', '英文')
        demucs_enabled = load_key('demucs', True)
        
        print(f"   显示语言: {display_lang}")
        print(f"   目标语言: {target_lang}")
        print(f"   人声分离: {'启用' if demucs_enabled else '禁用'}")
        
        # 2. 读取嵌套配置
        print("\n2. 读取嵌套配置...")
        whisper_model = load_key('whisper.model', 'large-v3')
        whisper_language = load_key('whisper.language', 'zh')
        whisper_runtime = load_key('whisper.runtime', 'local')
        api_model = load_key('api.model', 'deepseek-ai/DeepSeek-V3')
        
        print(f"   Whisper模型: {whisper_model}")
        print(f"   Whisper语言: {whisper_language}")
        print(f"   Whisper运行时: {whisper_runtime}")
        print(f"   API模型: {api_model}")
        
        # 3. 使用ConfigManager实例
        print("\n3. 使用ConfigManager实例...")
        config_manager = ConfigManager()
        
        # 获取配置摘要
        summary = config_manager.get_config_summary()
        print("   配置摘要:")
        for key, value in summary.items():
            print(f"     {key}: {value}")
        
        print("\n✅ 基础配置读取演示完成")
        return True
        
    except Exception as e:
        print(f"❌ 基础配置读取演示失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def demo_specialized_config_getters():
    """演示专用配置获取器"""
    print("\n🎯 演示专用配置获取器")
    print("-" * 50)
    
    try:
        from modules.configs import ConfigManager
        
        config_manager = ConfigManager()
        
        # 1. Whisper配置
        print("1. Whisper配置...")
        whisper_config = config_manager.get_whisper_config()
        print(f"   Whisper配置: {whisper_config}")
        
        # 2. API配置
        print("\n2. API配置...")
        api_config = config_manager.get_api_config()
        print(f"   API配置: {api_config}")
        
        # 3. TTS配置
        print("\n3. TTS配置...")
        tts_config = config_manager.get_tts_config()
        print(f"   当前TTS配置: {tts_config}")
        
        # 尝试获取特定TTS配置
        edge_tts_config = config_manager.get_tts_config('edge_tts')
        print(f"   Edge TTS配置: {edge_tts_config}")
        
        # 4. 支持的语言
        print("\n4. 支持的语言...")
        languages = config_manager.get_supported_languages()
        print(f"   使用空格分隔的语言: {languages['with_space']}")
        print(f"   不使用空格的语言: {languages['without_space']}")
        
        # 5. 支持的文件格式
        print("\n5. 支持的文件格式...")
        formats = config_manager.get_allowed_formats()
        print(f"   视频格式: {formats['video']}")
        print(f"   音频格式: {formats['audio']}")
        
        # 6. 模型目录
        print("\n6. 模型目录...")
        model_dir = config_manager.get_model_dir()
        print(f"   模型目录: {model_dir}")
        
        print("\n✅ 专用配置获取器演示完成")
        return True
        
    except Exception as e:
        print(f"❌ 专用配置获取器演示失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def demo_config_utils():
    """演示配置工具函数"""
    print("\n🛠️  演示配置工具函数")
    print("-" * 50)
    
    try:
        from modules.configs.utils import (
            get_joiner, 
            validate_language_code,
            validate_file_format,
            get_api_config_for_service,
            validate_api_keys,
            get_optimal_whisper_settings
        )
        
        # 1. 语言连接符
        print("1. 语言连接符测试...")
        test_languages = ['zh', 'en', 'ja', 'fr', 'xx']
        for lang in test_languages:
            joiner = get_joiner(lang)
            print(f"   {lang}: '{joiner}' ({'空' if joiner == '' else '空格' if joiner == ' ' else '其他'})")
        
        # 2. 语言验证
        print("\n2. 语言代码验证...")
        for lang in test_languages:
            is_valid = validate_language_code(lang)
            print(f"   {lang}: {'✅ 支持' if is_valid else '❌ 不支持'}")
        
        # 3. 文件格式验证
        print("\n3. 文件格式验证...")
        test_files = [
            ('test.mp4', 'video'),
            ('test.wav', 'audio'),
            ('test.txt', 'video'),
            ('test.pdf', 'audio')
        ]
        for file_path, format_type in test_files:
            is_valid = validate_file_format(file_path, format_type)
            print(f"   {file_path} ({format_type}): {'✅ 支持' if is_valid else '❌ 不支持'}")
        
        # 4. 服务配置获取
        print("\n4. 服务配置获取...")
        services = ['whisper', 'tts', 'llm']
        for service in services:
            try:
                service_config = get_api_config_for_service(service)
                print(f"   {service}服务配置: {service_config}")
            except Exception as e:
                print(f"   {service}服务配置获取失败: {str(e)}")
        
        # 5. API密钥验证
        print("\n5. API密钥配置状态...")
        try:
            api_status = validate_api_keys()
            for service, is_configured in api_status.items():
                status = "✅ 已配置" if is_configured else "❌ 未配置"
                print(f"   {service}: {status}")
        except Exception as e:
            print(f"   API密钥验证失败: {str(e)}")
        
        # 6. 最佳Whisper设置
        print("\n6. 最佳Whisper设置推荐...")
        test_langs = ['zh', 'en', 'fr']
        for lang in test_langs:
            settings = get_optimal_whisper_settings(lang)
            print(f"   {lang}: {settings}")
        
        print("\n✅ 配置工具函数演示完成")
        return True
        
    except Exception as e:
        print(f"❌ 配置工具函数演示失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def demo_config_models():
    """演示配置数据模型"""
    print("\n📊 演示配置数据模型")
    print("-" * 50)
    
    try:
        from modules.configs.models import (
            WhisperConfig,
            APIConfig,
            ASRConfig,
            VideoLingoConfig
        )
        
        # 1. WhisperConfig
        print("1. WhisperConfig模型...")
        whisper_config = WhisperConfig(
            model="large-v3",
            language="zh",
            runtime="local"
        )
        print(f"   Whisper配置: {whisper_config}")
        print(f"   API密钥: {whisper_config.get_api_key()}")
        
        # 2. APIConfig
        print("\n2. APIConfig模型...")
        api_config = APIConfig(
            key="test-key",
            model="deepseek-ai/DeepSeek-V3",
            max_workers=4
        )
        print(f"   API配置: {api_config}")
        
        # 3. ASRConfig
        print("\n3. ASRConfig组合模型...")
        asr_config = ASRConfig(
            whisper=whisper_config,
            demucs=True
        )
        print(f"   ASR配置: {asr_config}")
        
        # 4. 从字典创建配置
        print("\n4. 从字典创建配置...")
        config_dict = {
            'whisper': {
                'model': 'large-v3-turbo',
                'language': 'en',
                'runtime': 'cloud'
            },
            'demucs': False
        }
        asr_from_dict = ASRConfig.from_dict(config_dict)
        print(f"   从字典创建的ASR配置: {asr_from_dict}")
        
        # 5. VideoLingoConfig完整配置
        print("\n5. VideoLingoConfig完整配置模型...")
        full_config = VideoLingoConfig()
        print(f"   默认配置摘要:")
        print(f"     显示语言: {full_config.display_language}")
        print(f"     目标语言: {full_config.target_language}")
        print(f"     TTS方法: {full_config.tts_method}")
        print(f"     模型目录: {full_config.get_model_dir()}")
        
        # API密钥验证状态
        api_status = full_config.validate_api_keys()
        print(f"     API密钥状态: {api_status}")
        
        print("\n✅ 配置数据模型演示完成")
        return True
        
    except Exception as e:
        print(f"❌ 配置数据模型演示失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def demo_asr_integration():
    """演示ASR适配器配置集成"""
    print("\n🎤 演示ASR适配器配置集成")
    print("-" * 50)
    
    try:
        from modules.asr_backend import (
            get_available_engines,
            auto_select_engine,
            create_asr_engine
        )
        from modules.asr_backend.factory import get_engine_status_report, get_asr_factory
        
        # 1. 检查工厂配置集成
        print("1. ASR工厂配置集成检查...")
        factory = get_asr_factory()
        print(f"   工厂实例: {factory}")
        
        # 2. 引擎状态报告
        print("\n2. 引擎状态报告...")
        report = get_engine_status_report()
        
        print("   引擎详细状态:")
        for engine_name, details in report['engine_details'].items():
            is_available = details.get('is_available', False)
            status_icon = "✅" if is_available else "❌"
            error = details.get('error', '')
            print(f"     {status_icon} {engine_name}: {details.get('name', 'Unknown')}")
            if error:
                print(f"        错误: {error}")
        
        # 3. 本地模型检测测试
        print("\n3. 本地模型检测测试...")
        try:
            from modules.asr_backend.adapters.whisperx_local_adapter import WhisperXLocalAdapter
            
            # 测试不同语言的本地模型检测
            test_configs = [
                {'language': 'zh', 'model_name': 'large-v3'},
                {'language': 'en', 'model_name': 'large-v3'},
                {'language': 'auto', 'model_name': 'large-v2'}
            ]
            
            for config in test_configs:
                adapter = WhisperXLocalAdapter(config)
                has_local = adapter._check_local_model_exists()
                lang = config['language']
                print(f"   语言{lang}模型缓存状态: {'✅ 存在' if has_local else '❌ 不存在'}")
                if has_local:
                    print(f"     → 将跳过HuggingFace镜像检测，加快启动速度")
                else:
                    print(f"     → 首次使用时会从HuggingFace下载模型")
                
        except Exception as e:
            print(f"   本地模型检测测试失败: {str(e)}")
        
        # 4. 可用引擎列表
        print("\n4. 可用引擎列表...")
        available = get_available_engines()
        print(f"   可用引擎: {available}")
        
        # 5. 自动引擎选择
        if available:
            print("\n5. 自动引擎选择...")
            try:
                selected = auto_select_engine()
                print(f"   自动选择的引擎: {selected}")
                
                # 6. 创建引擎实例演示（使用配置文件参数）
                print("\n6. 创建引擎实例（使用配置文件参数）...")
                engine = create_asr_engine(selected)
                print(f"   创建的引擎实例: {engine}")
                
                # 获取引擎信息
                engine_info = engine.get_engine_info()
                print(f"   引擎信息: {engine_info}")
                
                # 清理引擎
                engine.cleanup()
                print("   引擎已清理")
                
            except Exception as e:
                print(f"   引擎操作失败: {str(e)}")
        else:
            print("\n⚠️  没有可用的ASR引擎")
        
        print("\n✅ ASR适配器配置集成演示完成")
        return True
        
    except Exception as e:
        print(f"❌ ASR适配器配置集成演示失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def demo_config_management():
    """演示配置管理操作"""
    print("\n⚙️  演示配置管理操作")
    print("-" * 50)
    
    try:
        from modules.configs import ConfigManager
        from modules.configs.utils import create_config_backup
        
        config_manager = ConfigManager()
        
        # 1. 配置验证
        print("1. 配置验证...")
        
        # 验证Whisper运行时
        runtime_tests = ['local', 'cloud', 'elevenlabs', 'invalid']
        for runtime in runtime_tests:
            is_valid = config_manager.validate_whisper_runtime(runtime)
            print(f"   Whisper运行时 '{runtime}': {'✅ 有效' if is_valid else '❌ 无效'}")
        
        # 验证TTS方法
        tts_tests = ['edge_tts', 'openai_tts', 'invalid_tts']
        for tts in tts_tests:
            is_valid = config_manager.validate_tts_method(tts)
            print(f"   TTS方法 '{tts}': {'✅ 有效' if is_valid else '❌ 无效'}")
        
        # 2. 配置热重载
        print("\n2. 配置热重载...")
        config_manager.reload_config()
        
        # 3. 创建配置备份
        print("\n3. 创建配置备份...")
        try:
            backup_path = create_config_backup()
            print(f"   备份文件: {backup_path}")
            
            # 检查备份文件是否存在
            if backup_path.exists():
                print("   ✅ 备份文件创建成功")
                # 可以选择删除测试备份
                backup_path.unlink()
                print("   🗑️  测试备份已删除")
            else:
                print("   ❌ 备份文件未找到")
                
        except Exception as e:
            print(f"   备份创建失败: {str(e)}")
        
        print("\n✅ 配置管理操作演示完成")
        return True
        
    except Exception as e:
        print(f"❌ 配置管理操作演示失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主演示函数"""
    print("🎬 配置管理系统完整演示")
    print("=" * 60)
    
    # 演示项目列表
    demos = [
        ("基础配置读取", demo_basic_config_access),
        ("专用配置获取器", demo_specialized_config_getters),
        ("配置工具函数", demo_config_utils),
        ("配置数据模型", demo_config_models),
        ("ASR适配器集成", demo_asr_integration),
        ("配置管理操作", demo_config_management)
    ]
    
    passed = 0
    total = len(demos)
    
    for demo_name, demo_func in demos:
        try:
            print(f"\n{'='*20} {demo_name} {'='*20}")
            if demo_func():
                passed += 1
                print(f"✅ {demo_name} 演示成功")
            else:
                print(f"❌ {demo_name} 演示失败")
        except Exception as e:
            print(f"💥 {demo_name} 演示异常: {str(e)}")
    
    print("\n" + "=" * 60)
    print(f"📊 演示结果: {passed}/{total} 成功")
    
    if passed == total:
        print("🎉 所有演示成功！配置管理系统工作正常")
        print("\n💡 您现在可以:")
        print("   - 使用 modules.config 模块进行配置管理")
        print("   - 通过 load_key/update_key 读写配置")
        print("   - 使用专用配置获取器获取特定配置")
        print("   - 利用配置工具函数进行验证和处理")
        print("   - 使用数据模型实现类型安全的配置访问")
        print("   - ASR适配器自动从配置文件获取参数")
        
        return True
    else:
        print("⚠️  部分演示失败，请检查相关配置和依赖")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 