"""
SpaCy Text Splitting Module

提供基于 spaCy 的智能文本分割功能，支持多语言和多种分割策略。

主要API:
- SpacySplitter: 主要的分割器类
- SplitterConfig: 配置类
- SplitResult: 结果类
"""

from .core.splitter import SpacySplitter
from .core.config import SplitterConfig
from .core.result import SplitResult
from .exceptions import SpacySplitterError

__version__ = "1.0.0"
__all__ = [
    "SpacySplitter",
    "SplitterConfig", 
    "SplitResult",
    "SpacySplitterError"
]

# ------------
# Quick API for simple usage
# ------------

def split_text(input_file: str, output_file: str = None, language: str = "auto", **kwargs) -> SplitResult:
    """
    Quick API for text splitting
    
    Args:
        input_file: input excel file path (cleaned_chunks.xlsx)
        output_file: output file path (optional)
        language: target language for processing
        **kwargs: additional configuration options
    
    Returns:
        SplitResult: splitting results and statistics
    """
    config = SplitterConfig(language=language, **kwargs)
    splitter = SpacySplitter(config)
    
    try:
        return splitter.process_file(input_file, output_file)
    finally:
        splitter.cleanup() 