"""
# ----------------------------------------------------------------------------
# 混合文本分割器
# 
# 整合NLP和语义分割的完整流程：
# 1. 第一阶段：基于spaCy的NLP分割（标点、语法等）
# 2. 第二阶段：基于GPT的语义分割（智能理解、上下文）
# 3. 统一的结果管理和输出
# ----------------------------------------------------------------------------
"""

from pathlib import Path
from typing import Optional

from .nlp_splitter import NLPSplitter
from .semantic_splitter import SemanticSplitter
from modules.commons import paths


class HybridSplitter:
    """混合文本分割器 - 结合NLP和语义分割"""
    
    def __init__(self, 
                 output_dir: str = "output",
                 max_split_length: int = 20,
                 keep_intermediate_files: bool = False):
        """
        初始化混合分割器
        
        Args:
            output_dir: 输出目录
            max_split_length: 语义分割的最大长度
            keep_intermediate_files: 是否保留中间文件
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        self.max_split_length = max_split_length
        self.keep_intermediate_files = keep_intermediate_files
        
        # 初始化分割器
        self.nlp_splitter = NLPSplitter(
            output_dir=str(self.output_dir),
            enable_all_strategies=True
        )
        
        self.semantic_splitter = SemanticSplitter(
            output_dir=str(self.output_dir),
            max_split_length=max_split_length
        )
        
        print("✅ 混合分割器初始化完成")
        print(f"   输出目录: {self.output_dir}")
        print(f"   语义分割最大长度: {max_split_length}")
        print(f"   处理模式: 同步处理")
    
    def split_file(self, input_file: str, output_file: str = None) -> str:
        """
        完整的混合分割流程
        
        Args:
            input_file: 输入Excel文件路径 (cleaned_chunks.xlsx)
            output_file: 最终输出文件路径
            
        Returns:
            最终分割结果文件路径
        """
        print("🚀 开始混合文本分割流程...")
        print("=" * 60)
        
        try:
            # ================================================================
            # 第一阶段：NLP分割
            # ================================================================
            print("\n📍 第一阶段：NLP分割")
            print("-" * 30)

            input_file = paths.get_filepath_by_default(input_file, output_base_dir=self.output_dir)
            
            nlp_result_file = self.nlp_splitter.split_file(input_file)
            print(f"📁 NLP分割结果: {nlp_result_file}")
            
            # ================================================================
            # 第二阶段：语义分割
            # ================================================================
            print("\n📍 第二阶段：语义分割")
            print("-" * 30)
            
            # 设置最终输出文件名
            if not output_file:
                final_output = paths.get_filepath_by_default("split_by_meaning.txt", output_base_dir=self.output_dir)
            else:
                final_output = paths.get_filepath_by_default(output_file, output_base_dir=self.output_dir)
            
            semantic_result_file = self.semantic_splitter.split_file(
                nlp_result_file, 
                str(final_output)
            )
            
            # ================================================================
            # 清理中间文件
            # ================================================================
            if not self.keep_intermediate_files:
                try:
                    import os
                    os.remove(nlp_result_file)
                    print(f"🧹 已删除中间文件: {nlp_result_file}")
                except Exception as e:
                    print(f"⚠️  无法删除中间文件: {e}")
            
            # ================================================================
            # 完成总结
            # ================================================================
            print("\n🎉 混合分割流程完成！")
            print("=" * 60)
            print(f"📁 最终结果文件: {semantic_result_file}")
            
            # 统计信息
            self._print_final_summary(input_file, semantic_result_file)
            
            return semantic_result_file
            
        except Exception as e:
            print(f"\n💥 混合分割流程失败: {str(e)}")
            raise
    
    def split_sentences(self, sentences: list) -> list:
        """
        对句子列表进行混合分割
        
        Args:
            sentences: 输入句子列表
            
        Returns:
            分割后的句子列表
        """
        print("🚀 开始混合句子分割...")
        
        try:
            # 第一阶段：NLP分割
            print("📍 执行NLP分割...")
            nlp_sentences = self.nlp_splitter.split_sentences(sentences)
            
            # 第二阶段：语义分割
            print("📍 执行语义分割...")
            with self.semantic_splitter:
                final_sentences = self.semantic_splitter.split_sentences(nlp_sentences)
            
            print(f"🎉 混合句子分割完成: {len(sentences)} -> {len(final_sentences)}")
            return final_sentences
            
        except Exception as e:
            print(f"❌ 混合句子分割失败: {str(e)}")
            # 发生错误时返回原始句子
            return sentences
    
    def _print_final_summary(self, input_file: Path, output_file: Path):
        """打印最终统计摘要"""
        try:
            # 读取原始文件统计
            if input_file.suffix == '.xlsx':
                import pandas as pd
                df = pd.read_excel(input_file)
                original_count = len(df)
                original_type = "Excel行"
            else:
                with open(input_file, 'r', encoding='utf-8') as f:
                    original_count = sum(1 for line in f if line.strip())
                original_type = "文本行"
            
            # 读取最终结果统计
            with open(output_file, 'r', encoding='utf-8') as f:
                final_count = sum(1 for line in f if line.strip())
            
            print(f"📊 分割统计摘要:")
            print(f"   输入: {original_count} {original_type}")
            print(f"   输出: {final_count} 分割句子")
            print(f"   分割比例: {final_count/original_count:.2f}x")
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"⚠️  无法生成统计摘要: {e}")
    

# ----------------------------------------------------------------------------
# 独立运行测试
# ----------------------------------------------------------------------------
if __name__ == '__main__':
    import sys
    
    # 测试混合分割器
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        input_file = "log/cleaned_chunks.xlsx"
    
    # 解析额外参数
    max_split_length = 20
    
    if len(sys.argv) > 2:
        try:
            max_split_length = int(sys.argv[2])
        except ValueError:
            print("⚠️  无效的max_split_length参数，使用默认值20")
    
    try:
        splitter = HybridSplitter(
            max_split_length=max_split_length,
            keep_intermediate_files=True  # 测试时保留中间文件
        )
        
        result_file = splitter.split_file(input_file)
        print(f"\n✅ 测试完成！结果文件: {result_file}")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc() 