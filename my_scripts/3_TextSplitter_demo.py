"""
# ----------------------------------------------------------------------------
# 文本分割器演示程序
# 
# 演示如何使用重构后的TextSplitter模块进行完整的文本分割流程：
# 1. 基础配置和初始化
# 2. 标点符号分割
# 3. 智能逗号分割
# 4. 语义GPT分割
# 5. 结果统计和导出
# 6. 批量处理功能
# ----------------------------------------------------------------------------
"""

import sys
import os
from pathlib import Path

from modules.text_splitter import split_text_complete


# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def demonstrate_basic_splitting():
    """演示基础分割功能"""
    print("\n📝 演示基础文本分割功能")
    print("=" * 50)

    try:
        
        s1 = split_text_complete(
            input_file="log/cleaned_chunks.xlsx",
            output_dir="my_scripts/output",
            output_file="log/split_by_nlp.txt",
            use_semantic_split=False,
            keep_intermediate_files=True
        )
        
        return True
        
    except Exception as e:
        import traceback
        traceback.print_exc()

        print(f"❌ 基础分割演示失败: {str(e)}")
        return False

def demonstrate_semantic_splitting():
    """演示语义分割功能"""
    print("\n📝 演示语义文本分割功能")
    print("=" * 50)

    try:
        
        s1 = split_text_complete(
            input_file="log/cleaned_chunks.xlsx",
            output_dir="my_scripts/output",
            output_file="log/split_by_meaning.txt",
            use_semantic_split=True,
            keep_intermediate_files=True
        )
        
        return True
        
    except Exception as e:
        import traceback
        traceback.print_exc()

        print(f"❌ 语义分割演示失败: {str(e)}")
        return False

def main():
    """主函数"""
    print("🎬 TextSplitter完整演示程序")
    print("=" * 60)
    
    # 创建输出目录
    output_dir = Path("my_scripts/output")
    output_dir.mkdir(parents=True, exist_ok=True)

    # demonstrate_basic_splitting()
    demonstrate_semantic_splitting()
    
    print("\n🎉 TextSplitter演示程序结束！")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 用户中断，演示结束")
    except Exception as e:
        print(f"\n💥 演示程序发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
