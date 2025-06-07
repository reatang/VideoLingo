"""
# ----------------------------------------------------------------------------
# 文本分割器模块
# 
# 负责将转录文本进行智能分割优化，分为两大步骤：
# 1. 基于 SpaCy 的规则分割（标点、语法等）
# 2. 基于大语言模型的语义分割
# ----------------------------------------------------------------------------
"""

from .split_spacy import (
    SpacySplitter,
    SplitterConfig,
    SplitResult
)

# 导出主要API
__all__ = [
    'TextSplitter',          # 主协调器
    'SpacySplitter',         # SpaCy 分割器 (可单独使用)
    'SplitterConfig',        # SpaCy 分割器配置
    'SplitResult',           # SpaCy 分割器结果
] 