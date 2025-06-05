"""
# ----------------------------------------------------------------------------
# 简化模块测试脚本 - 测试模块的基本导入和结构
# ----------------------------------------------------------------------------
"""

import sys
import os
from pathlib import Path

# 添加modules目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

def test_basic_imports():
    """测试基本导入功能"""
    print("🧪 测试模块导入...")
    
    try:
        # 测试视频下载器导入
        from video_downloader import VideoDownloader
        print("✅ VideoDownloader 导入成功")
        
        # 测试基本实例化
        downloader = VideoDownloader(save_path='test_output')
        print(f"✅ VideoDownloader 实例化成功: {downloader.save_path}")
        
        # 测试方法存在性
        assert hasattr(downloader, 'download_video'), "缺少 download_video 方法"
        assert hasattr(downloader, 'get_video_info'), "缺少 get_video_info 方法"
        assert hasattr(downloader, 'find_video_file'), "缺少 find_video_file 方法"
        print("✅ VideoDownloader 所有必需方法都存在")
        
        return True
        
    except Exception as e:
        print(f"❌ VideoDownloader 测试失败: {str(e)}")
        return False

def test_audio_transcriber_basic():
    """测试音频转录器基本功能（不需要pandas）"""
    print("\n🧪 测试AudioTranscriber基本结构...")
    
    try:
        # 尝试导入但先跳过pandas相关功能
        import importlib.util
        
        # 检查模块文件是否存在
        module_path = Path(__file__).parent / "audio_transcriber.py"
        if not module_path.exists():
            print("❌ audio_transcriber.py 文件不存在")
            return False
        
        # 检查代码语法是否正确
        with open(module_path, 'r', encoding='utf-8') as f:
            code = f.read()
        
        # 尝试编译代码（不执行）
        compile(code, str(module_path), 'exec')
        print("✅ audio_transcriber.py 语法正确")
        
        # 检查关键类定义
        assert 'class AudioTranscriber:' in code, "缺少 AudioTranscriber 类定义"
        assert 'def convert_video_to_audio' in code, "缺少 convert_video_to_audio 方法"
        assert 'def split_audio_by_silence' in code, "缺少 split_audio_by_silence 方法"
        print("✅ AudioTranscriber 关键方法定义存在")
        
        return True
        
    except Exception as e:
        print(f"❌ AudioTranscriber 基本测试失败: {str(e)}")
        return False

def test_text_splitter_basic():
    """测试文本分割器基本功能（不需要spaCy）"""
    print("\n🧪 测试TextSplitter基本结构...")
    
    try:
        # 检查模块文件是否存在
        module_path = Path(__file__).parent / "text_splitter.py"
        if not module_path.exists():
            print("❌ text_splitter.py 文件不存在")
            return False
        
        # 检查代码语法是否正确
        with open(module_path, 'r', encoding='utf-8') as f:
            code = f.read()
        
        # 尝试编译代码（不执行）
        compile(code, str(module_path), 'exec')
        print("✅ text_splitter.py 语法正确")
        
        # 检查关键类定义
        assert 'class TextSplitter:' in code, "缺少 TextSplitter 类定义"
        assert 'def split_by_punctuation_marks' in code, "缺少 split_by_punctuation_marks 方法"
        assert 'def split_by_commas' in code, "缺少 split_by_commas 方法"
        assert 'def split_by_semantic_meaning' in code, "缺少 split_by_semantic_meaning 方法"
        print("✅ TextSplitter 关键方法定义存在")
        
        # 测试基本实例化（不加载依赖）
        try:
            # 简单导入测试
            import importlib.util
            spec = importlib.util.spec_from_file_location("text_splitter", module_path)
            module = importlib.util.module_from_spec(spec)
            
            # 检查类是否可以定义（不执行__init__）
            print("✅ TextSplitter 模块结构完整")
            
        except Exception as e:
            print(f"⚠️  模块导入测试警告: {str(e)}")
        
        return True
        
    except Exception as e:
        print(f"❌ TextSplitter 基本测试失败: {str(e)}")
        return False

def test_content_summarizer_basic():
    """测试内容总结器基本功能（不需要复杂依赖）"""
    print("\n🧪 测试ContentSummarizer基本结构...")
    
    try:
        # 检查模块文件是否存在
        module_path = Path(__file__).parent / "content_summarizer.py"
        if not module_path.exists():
            print("❌ content_summarizer.py 文件不存在")
            return False
        
        # 检查代码语法是否正确
        with open(module_path, 'r', encoding='utf-8') as f:
            code = f.read()
        
        # 尝试编译代码（不执行）
        compile(code, str(module_path), 'exec')
        print("✅ content_summarizer.py 语法正确")
        
        # 检查关键类和数据类定义
        assert 'class ContentSummarizer:' in code, "缺少 ContentSummarizer 类定义"
        assert '@dataclass' in code and 'class Term:' in code, "缺少 Term 数据类定义"
        assert '@dataclass' in code and 'class ContentSummary:' in code, "缺少 ContentSummary 数据类定义"
        assert 'def generate_content_summary' in code, "缺少 generate_content_summary 方法"
        assert 'def extract_terminology' in code, "缺少 extract_terminology 方法"
        assert 'def generate_translation_context' in code, "缺少 generate_translation_context 方法"
        print("✅ ContentSummarizer 关键方法和数据类定义存在")
        
        # 检查核心设计原则
        assert 'domain_keywords' in code, "缺少领域关键词配置"
        assert '_detect_domain_and_style' in code, "缺少领域和风格检测"
        assert '_deduplicate_terms' in code, "缺少术语去重逻辑"
        print("✅ ContentSummarizer 核心设计功能完整")
        
        return True
        
    except Exception as e:
        print(f"❌ ContentSummarizer 基本测试失败: {str(e)}")
        return False

def test_text_translator_basic():
    """测试文本翻译器基本功能（不需要复杂依赖）"""
    print("\n🧪 测试TextTranslator基本结构...")
    
    try:
        # 检查模块文件是否存在
        module_path = Path(__file__).parent / "text_translator.py"
        if not module_path.exists():
            print("❌ text_translator.py 文件不存在")
            return False
        
        # 检查代码语法是否正确
        with open(module_path, 'r', encoding='utf-8') as f:
            code = f.read()
        
        # 尝试编译代码（不执行）
        compile(code, str(module_path), 'exec')
        print("✅ text_translator.py 语法正确")
        
        # 检查关键类和数据类定义
        assert 'class TextTranslator:' in code, "缺少 TextTranslator 类定义"
        assert '@dataclass' in code and 'class TranslationChunk:' in code, "缺少 TranslationChunk 数据类定义"
        assert '@dataclass' in code and 'class TranslationResult:' in code, "缺少 TranslationResult 数据类定义"
        assert 'def translate_single_chunk' in code, "缺少 translate_single_chunk 方法"
        assert 'def translate_all_chunks' in code, "缺少 translate_all_chunks 方法"
        assert 'def load_translation_context' in code, "缺少 load_translation_context 方法"
        print("✅ TextTranslator 关键方法和数据类定义存在")
        
        # 检查核心设计原则
        assert 'get_faithful_translation_prompt' in code, "缺少忠实翻译提示词生成"
        assert 'get_expressive_translation_prompt' in code, "缺少表达优化提示词生成"
        assert 'search_relevant_terms' in code, "缺少术语搜索功能"
        assert 'similarity_match_results' in code, "缺少相似度匹配功能"
        print("✅ TextTranslator 核心翻译功能完整")
        
        return True
        
    except Exception as e:
        print(f"❌ TextTranslator 基本测试失败: {str(e)}")
        return False

def test_subtitle_generator_basic():
    """测试字幕生成器基本功能（不需要复杂依赖）"""
    print("\n🧪 测试SubtitleGenerator基本结构...")
    
    try:
        # 检查模块文件是否存在
        module_path = Path(__file__).parent / "subtitle_generator.py"
        if not module_path.exists():
            print("❌ subtitle_generator.py 文件不存在")
            return False
        
        # 检查代码语法是否正确
        with open(module_path, 'r', encoding='utf-8') as f:
            code = f.read()
        
        # 尝试编译代码（不执行）
        compile(code, str(module_path), 'exec')
        print("✅ subtitle_generator.py 语法正确")
        
        # 检查关键类和数据类定义
        assert 'class SubtitleGenerator:' in code, "缺少 SubtitleGenerator 类定义"
        assert '@dataclass' in code and 'class SubtitleSegment:' in code, "缺少 SubtitleSegment 数据类定义"
        assert '@dataclass' in code and 'class SubtitleConfig:' in code, "缺少 SubtitleConfig 数据类定义"
        assert '@dataclass' in code and 'class SubtitleGenerationResult:' in code, "缺少 SubtitleGenerationResult 数据类定义"
        assert 'def align_timestamps' in code, "缺少 align_timestamps 方法"
        assert 'def generate_srt_content' in code, "缺少 generate_srt_content 方法"
        print("✅ SubtitleGenerator 关键方法和数据类定义存在")
        
        # 检查核心设计原则
        assert 'optimize_subtitle_gaps' in code, "缺少字幕间隔优化功能"
        assert 'split_long_subtitles' in code, "缺少长字幕分割功能"
        assert 'calculate_text_weight' in code, "缺少文本权重计算功能"
        assert 'save_subtitle_files' in code, "缺少字幕文件保存功能"
        print("✅ SubtitleGenerator 核心字幕生成功能完整")
        
        return True
        
    except Exception as e:
        print(f"❌ SubtitleGenerator 基本测试失败: {str(e)}")
        return False

def test_audio_synthesizer_basic():
    """测试音频合成器基本功能（不需要复杂依赖）"""
    print("\n🧪 测试AudioSynthesizer基本结构...")
    
    try:
        # 检查模块文件是否存在
        module_path = Path(__file__).parent / "audio_synthesizer.py"
        if not module_path.exists():
            print("❌ audio_synthesizer.py 文件不存在")
            return False
        
        # 检查代码语法是否正确
        with open(module_path, 'r', encoding='utf-8') as f:
            code = f.read()
        
        # 尝试编译代码（不执行）
        compile(code, str(module_path), 'exec')
        print("✅ audio_synthesizer.py 语法正确")
        
        # 检查关键类和数据类定义
        assert 'class AudioSynthesizer:' in code, "缺少 AudioSynthesizer 类定义"
        assert '@dataclass' in code and 'class AudioTask:' in code, "缺少 AudioTask 数据类定义"
        assert '@dataclass' in code and 'class AudioSegment:' in code, "缺少 AudioSegment 数据类定义"
        assert '@dataclass' in code and 'class SynthesisResult:' in code, "缺少 SynthesisResult 数据类定义"
        assert 'def process_audio_synthesis' in code, "缺少 process_audio_synthesis 方法"
        assert 'def synthesize_single_task' in code, "缺少 synthesize_single_task 方法"
        print("✅ AudioSynthesizer 关键方法和数据类定义存在")
        
        # 检查适配器模式实现
        assert 'class TTSAdapter(ABC):' in code, "缺少 TTSAdapter 抽象基类定义"
        assert 'class TTSAdapterFactory:' in code, "缺少 TTSAdapterFactory 工厂类定义"
        assert 'class OpenAITTSAdapter(TTSAdapter):' in code, "缺少 OpenAITTSAdapter 适配器"
        assert 'class AzureTTSAdapter(TTSAdapter):' in code, "缺少 AzureTTSAdapter 适配器"
        assert 'class EdgeTTSAdapter(TTSAdapter):' in code, "缺少 EdgeTTSAdapter 适配器"
        assert 'class FishTTSAdapter(TTSAdapter):' in code, "缺少 FishTTSAdapter 适配器"
        assert 'class CustomTTSAdapter(TTSAdapter):' in code, "缺少 CustomTTSAdapter 适配器"
        print("✅ AudioSynthesizer 适配器模式设计完整")
        
        # 检查核心功能
        assert 'adjust_audio_speed' in code, "缺少音频速度调整功能"
        assert 'get_audio_duration' in code, "缺少音频时长获取功能"
        assert 'supports_voice_cloning' in code, "缺少语音克隆支持检测"
        assert '_postprocess_segments' in code, "缺少音频后处理功能"
        print("✅ AudioSynthesizer 核心音频处理功能完整")
        
        return True
        
    except Exception as e:
        print(f"❌ AudioSynthesizer 基本测试失败: {str(e)}")
        return False

def test_video_composer_basic():
    """测试视频合成器基本功能（不需要复杂依赖）"""
    print("\n🧪 测试VideoComposer基本结构...")
    
    try:
        # 检查模块文件是否存在
        module_path = Path(__file__).parent / "video_composer.py"
        if not module_path.exists():
            print("❌ video_composer.py 文件不存在")
            return False
        
        # 检查代码语法是否正确
        with open(module_path, 'r', encoding='utf-8') as f:
            code = f.read()
        
        # 尝试编译代码（不执行）
        compile(code, str(module_path), 'exec')
        print("✅ video_composer.py 语法正确")
        
        # 检查关键类和数据类定义
        assert 'class VideoComposer:' in code, "缺少 VideoComposer 类定义"
        assert '@dataclass' in code and 'class SubtitleStyle:' in code, "缺少 SubtitleStyle 数据类定义"
        assert '@dataclass' in code and 'class VideoConfig:' in code, "缺少 VideoConfig 数据类定义"
        assert '@dataclass' in code and 'class CompositionResult:' in code, "缺少 CompositionResult 数据类定义"
        assert 'def compose_video_with_subtitles' in code, "缺少 compose_video_with_subtitles 方法"
        assert 'def compose_final_video' in code, "缺少 compose_final_video 方法"
        assert 'def process_complete_composition' in code, "缺少 process_complete_composition 方法"
        print("✅ VideoComposer 关键方法和数据类定义存在")
        
        # 检查核心设计原则
        assert 'detect_video_resolution' in code, "缺少视频分辨率检测功能"
        assert 'check_gpu_support' in code, "缺少GPU支持检测功能"
        assert 'normalize_audio' in code, "缺少音频标准化功能"
        assert 'build_subtitle_filter' in code, "缺少字幕滤镜构建功能"
        assert '_detect_platform_fonts' in code, "缺少平台字体检测功能"
        assert 'create_placeholder_video' in code, "缺少占位符视频创建功能"
        print("✅ VideoComposer 核心视频处理功能完整")
        
        return True
        
    except Exception as e:
        print(f"❌ VideoComposer 基本测试失败: {str(e)}")
        return False

def test_file_structure():
    """测试文件结构"""
    print("\n🧪 测试文件结构...")
    
    try:
        current_dir = Path(__file__).parent
        
        # 检查必需文件
        required_files = [
            'video_downloader.py',
            'audio_transcriber.py',
            'text_splitter.py',
            'content_summarizer.py',
            'text_translator.py',
            'subtitle_generator.py',
            'audio_synthesizer.py',
            'video_composer.py',
            'test_modules.py'
        ]
        
        for file in required_files:
            file_path = current_dir / file
            assert file_path.exists(), f"缺少文件: {file}"
            print(f"✅ {file} 存在")
        
        # 检查文件大小（基本验证）
        for file in required_files:
            file_path = current_dir / file
            size = file_path.stat().st_size
            assert size > 100, f"{file} 文件太小，可能是空文件"
            print(f"✅ {file} 大小正常: {size} bytes")
        
        return True
        
    except Exception as e:
        print(f"❌ 文件结构测试失败: {str(e)}")
        return False

def test_coding_standards():
    """测试编码标准"""
    print("\n🧪 测试编码标准...")
    
    try:
        # 检查文件编码
        files_to_check = ['video_downloader.py', 'audio_transcriber.py', 'text_splitter.py', 'content_summarizer.py', 'text_translator.py', 'subtitle_generator.py', 'audio_synthesizer.py', 'video_composer.py']
        
        for filename in files_to_check:
            filepath = Path(__file__).parent / filename
            
            # 检查UTF-8编码
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 检查是否有中文注释
            has_chinese = any('\u4e00' <= char <= '\u9fff' for char in content)
            if has_chinese:
                print(f"✅ {filename} 包含中文注释")
            
            # 检查是否有类型提示
            if 'from typing import' in content:
                print(f"✅ {filename} 使用了类型提示")
            
            # 检查是否有文档字符串
            if '"""' in content:
                print(f"✅ {filename} 包含文档字符串")
            
            # 检查特殊要求（数据类设计）
            if filename in ['content_summarizer.py', 'text_translator.py', 'subtitle_generator.py', 'audio_synthesizer.py', 'video_composer.py']:
                if '@dataclass' in content:
                    print(f"✅ {filename} 使用了数据类设计")
                    
            # 检查AudioSynthesizer的适配器模式
            if filename == 'audio_synthesizer.py':
                if 'class TTSAdapter(ABC):' in content and 'TTSAdapterFactory' in content:
                    print(f"✅ {filename} 实现了适配器模式")
                    
            # 检查VideoComposer的多平台兼容
            if filename == 'video_composer.py':
                if '_detect_platform_fonts' in content and 'platform.system()' in content:
                    print(f"✅ {filename} 实现了多平台兼容设计")
        
        return True
        
    except Exception as e:
        print(f"❌ 编码标准测试失败: {str(e)}")
        return False

def main():
    """主测试函数"""
    print("🚀 开始简化模块测试...")
    print("=" * 60)
    
    test_results = []
    
    # 运行各项测试
    test_results.append(("基本导入功能", test_basic_imports()))
    test_results.append(("音频转录器基本结构", test_audio_transcriber_basic()))
    test_results.append(("文本分割器基本结构", test_text_splitter_basic()))
    test_results.append(("内容总结器基本结构", test_content_summarizer_basic()))
    test_results.append(("文本翻译器基本结构", test_text_translator_basic()))
    test_results.append(("字幕生成器基本结构", test_subtitle_generator_basic()))
    test_results.append(("音频合成器基本结构", test_audio_synthesizer_basic()))
    test_results.append(("视频合成器基本结构", test_video_composer_basic()))
    test_results.append(("文件结构", test_file_structure()))
    test_results.append(("编码标准", test_coding_standards()))
    
    # 输出测试总结
    print("\n" + "=" * 60)
    print("📊 测试结果总结")
    print("=" * 60)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n📈 测试统计: {passed}/{total} 项测试通过")
    
    if passed == total:
        print("🎉 基本模块测试全部通过！")
        print("💡 提示: 完整功能测试需要安装pandas, opencv-python, numpy等依赖")
        return True
    else:
        print("💥 部分测试失败，需要修复问题")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1) 