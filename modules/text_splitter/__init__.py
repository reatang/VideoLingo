"""
# ----------------------------------------------------------------------------
# 文本分割模块
# 
# 提供统一的文本分割接口，支持：
# 1. NLP分割 (基于spaCy的多层分割策略)
# 2. 语义分割 (基于GPT的智能语义分割)
# 3. 混合分割 (结合两种方法的完整分割流程)
# ----------------------------------------------------------------------------
"""

from .nlp_splitter import NLPSplitter
from .semantic_splitter import SemanticSplitter
from .hybrid_splitter import HybridSplitter
from .split_spacy import split_text as split_text_spacy
from modules.common_utils import paths
# 导出主要API
__all__ = [
    'NLPSplitter',
    'SemanticSplitter', 
    'HybridSplitter',
    'split_text_spacy',
    'split_text_complete'
]

def split_text_complete(input_file: str,
                        output_dir: str = "output", 
                        output_file: str = None,
                        use_semantic_split: bool = True,
                        max_split_length: int = 20,
                        keep_intermediate_files: bool = False) -> str:
    """
    一键完成文本分割的便捷接口
    
    Args:
        input_file: 输入Excel文件路径 (cleaned_chunks.xlsx)
        output_dir: 输出目录
        output_file: 输出文件名（可选）
        use_semantic_split: 是否使用语义分割（False则仅使用NLP分割）
        max_split_length: 语义分割的最大长度
        keep_intermediate_files: 是否保留中间文件
        
    Returns:
        最终分割结果文件路径
    """
    if use_semantic_split:
        # 使用混合分割（NLP + 语义）
        with HybridSplitter(
            output_dir=output_dir,
            max_split_length=max_split_length,
            keep_intermediate_files=keep_intermediate_files
        ) as splitter:
            return splitter.split_file(input_file, output_file)
    else:
        # 仅使用NLP分割
        with NLPSplitter(output_dir=output_dir) as splitter:
            return splitter.split_file(input_file) 