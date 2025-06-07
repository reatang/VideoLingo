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

from modules.text_splitter import TextSplitter
from modules.config import get_config_manager


# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def demonstrate_basic_splitting():
    """演示基础分割功能"""
    print("\n📝 演示基础文本分割功能")
    print("=" * 50)

    # 获取配置管理器
    config = get_config_manager()
    
    try:
        
        # 1. 基础初始化
        print("1. 初始化TextSplitter...")
        splitter = TextSplitter(
            output_dir="my_scripts/output",
            max_split_length=15,
            max_workers=2
        )
        
        # 3. 运行完整分割流程（不使用语义分割）
        print("\n2. 执行基础分割流程（不含语义分割）...")
        final_file = splitter.process_complete_split(
            input_file="log/cleaned_chunks.xlsx",
            output_file="log/split_by_nlp.txt",
            enable_comma_split=True,
            enable_semantic_split=False,
            save_intermediate_files=True
        )
        
        print(f"✅ 基础分割完成！结果文件: {final_file}")
        
        # 4. 显示结果预览
        if Path(final_file).exists():
            with open(final_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()[:8]
            
            print(f"\n📋 结果预览 (前{len(lines)}行):")
            for i, line in enumerate(lines, 1):
                print(f"  {i:2d}. {line.strip()}")
        
        return True
        
    except Exception as e:
        print(f"❌ 基础分割演示失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("🎬 TextSplitter完整演示程序")
    print("=" * 60)
    
    # 创建输出目录
    output_dir = Path("my_scripts/output")
    output_dir.mkdir(parents=True, exist_ok=True)

    demonstrate_basic_splitting()
    
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
