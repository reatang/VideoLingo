"""
# ----------------------------------------------------------------------------
# 文本分割模块演示程序
# 
# 演示重构后的文本分割模块的使用方法：
# 1. NLP分割 - 基于spaCy的语法分割
# 2. 语义分割 - 基于GPT的智能分割
# 3. 混合分割 - 完整的二阶段分割流程
# 4. 一键接口 - 最简单的使用方式
# ----------------------------------------------------------------------------
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

base_dir = os.path.join("my_scripts", "output")

def demo_nlp_splitter():
    """演示NLP分割器"""
    print("=" * 60)
    print("📍 演示1：NLP分割器 (基于spaCy)")
    print("=" * 60)
    
    try:
        from modules.text_splitter import NLPSplitter
        
        # 初始化NLP分割器
        splitter = NLPSplitter(output_dir=base_dir)
        
        # 处理文件
        input_file = paths.get_filepath_by_default("cleaned_chunks.xlsx", base_dir)
        result_file = splitter.split_file(input_file)
        
        print(f"✅ NLP分割演示完成！")
        print(f"📁 结果文件: {result_file}")
        
        return result_file
        
    except Exception as e:
        print(f"❌ NLP分割演示失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def demo_semantic_splitter(input_file: str = None):
    """演示语义分割器"""
    print("\n" + "=" * 60)
    print("📍 演示2：语义分割器 (基于GPT)")
    print("=" * 60)
    
    try:
        from modules.text_splitter import SemanticSplitter
        
        # 使用NLP分割的结果或默认文件
        if not input_file:
            input_file = paths.get_filepath_by_default("nlp_split_result.txt", base_dir)
        
        if not os.path.exists(input_file):
            print(f"⚠️  输入文件不存在: {input_file}")
            print("⚠️  跳过语义分割演示")
            return None
        
        # 使用上下文管理器确保资源清理
        with SemanticSplitter(
            output_dir="my_scripts/output",
            max_split_length=20
        ) as splitter:
            # 处理文件
            result_file = splitter.split_file(input_file)
        
        print(f"✅ 语义分割演示完成！")
        print(f"📁 结果文件: {result_file}")
        
        return result_file
        
    except Exception as e:
        print(f"❌ 语义分割演示失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def demo_hybrid_splitter():
    """演示混合分割器"""
    print("\n" + "=" * 60)
    print("📍 演示3：混合分割器 (NLP + GPT)")
    print("=" * 60)
    
    try:
        from modules.text_splitter import HybridSplitter
        
        # 使用上下文管理器确保资源清理
        with HybridSplitter(
            output_dir=base_dir,
            max_split_length=20,
            keep_intermediate_files=True  # 演示时保留中间文件
        ) as splitter:
            # 处理文件
            input_file = paths.get_filepath_by_default("cleaned_chunks.xlsx", base_dir)
            result_file = splitter.split_file(input_file)
        
        print(f"✅ 混合分割演示完成！")
        print(f"📁 结果文件: {result_file}")
        
        return result_file
        
    except Exception as e:
        print(f"❌ 混合分割演示失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def demo_one_line_api():
    """演示一键API"""
    print("\n" + "=" * 60)
    print("📍 演示4：一键分割API (最简单)")
    print("=" * 60)
    
    try:
        from modules.text_splitter import split_text_complete
        
        # 一键完成所有分割
        result_file = split_text_complete(
            input_file="cleaned_chunks.xlsx",
            output_dir=base_dir,
            use_semantic_split=True,
            max_split_length=20
        )
        
        print(f"✅ 一键分割演示完成！")
        print(f"📁 结果文件: {result_file}")
        
        return result_file
        
    except Exception as e:
        print(f"❌ 一键分割演示失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def demo_sentence_splitting():
    """演示句子列表分割"""
    print("\n" + "=" * 60)
    print("📍 演示5：句子列表分割")
    print("=" * 60)
    
    try:
        from modules.text_splitter import HybridSplitter
        
        # 测试句子列表
        test_sentences = [
            "This is a very long sentence that needs to be split into smaller parts for better readability.",
            "这是一个很长的中文句子，需要被分割成更小的部分以便更好的阅读体验。",
            "Another example of a sentence that is too long and should be divided appropriately.",
        ]
        
        print("🔍 原始句子:")
        for i, sentence in enumerate(test_sentences):
            print(f"   {i+1}. {sentence}")
        
        # 使用上下文管理器确保资源清理
        with HybridSplitter(
            output_dir=base_dir,
            max_split_length=15
        ) as splitter:
            # 分割句子
            split_sentences = splitter.split_sentences(test_sentences)
        
        print("\n📝 分割结果:")
        for i, sentence in enumerate(split_sentences):
            print(f"   {i+1}. {sentence}")
        
        print(f"\n✅ 句子分割演示完成: {len(test_sentences)} -> {len(split_sentences)}")
        
    except Exception as e:
        print(f"❌ 句子分割演示失败: {str(e)}")
        import traceback
        traceback.print_exc()

from modules.common_utils import paths
from modules.config import get_config_manager

def main():
    """主演示函数"""
    print("🎬 文本分割模块完整演示")
    print("重构后的模块支持多种分割策略和灵活的API接口")

    # 检查输入文件
    input_file = paths.get_filepath_by_default("cleaned_chunks.xlsx", output_base_dir=base_dir)
    if not os.path.exists(input_file):
        print(f"❌ 输入文件不存在: {input_file}")
        print("请先运行 AudioTranscriber 生成 cleaned_chunks.xlsx 文件")
        return
    
    # 创建输出目录
    os.makedirs(base_dir, exist_ok=True)

    # 启动配置
    config = get_config_manager()
    
    try:
        # 选择演示模式
        if len(sys.argv) > 1:
            mode = sys.argv[1].lower()
        else:
            mode = "all"
        
        if mode in ["all", "nlp"]:
            nlp_result = demo_nlp_splitter()
        else:
            nlp_result = None
        
        if mode in ["all", "semantic"]:
            demo_semantic_splitter(nlp_result)
        
        if mode in ["all", "hybrid"]:
            demo_hybrid_splitter()
        
        if mode in ["all", "api"]:
            demo_one_line_api()
        
        if mode in ["all", "sentence"]:
            demo_sentence_splitting()
        
        print("\n🎉 所有演示完成！")
        print("\n📚 使用说明:")
        print("   python my_scripts/4_TextSplitter_demo.py [mode]")
        print("   mode: all(默认) | nlp | semantic | hybrid | api | sentence")
        
    except KeyboardInterrupt:
        print("\n👋 用户中断演示")
    except Exception as e:
        print(f"\n💥 演示过程中发生错误: {str(e)}")


if __name__ == "__main__":
    main() 