"""
# ----------------------------------------------------------------------------
# 提示词管理模块
# 
# 集中管理各个业务模块使用的提示词模板：
# 1. 文本分割提示词
# 2. 翻译提示词  
# 3. 总结提示词
# 4. 字幕对齐提示词
# 5. 音频任务提示词
# ----------------------------------------------------------------------------
"""

from .base import PromptTemplate, PromptManager
from .text_split import TextSplitPromptGenerator
from .translation import TranslationPromptGenerator
from .summary import SummaryPromptGenerator
from .subtitle_align import SubtitleAlignPromptGenerator

# 导出主要API
__all__ = [
    'PromptTemplate',
    'PromptManager', 
    'TextSplitPromptGenerator',
    'TranslationPromptGenerator',
    'SummaryPromptGenerator',
    'SubtitleAlignPromptGenerator',
    'get_prompt_manager'
]

# 全局提示词管理器
_global_prompt_manager = None

def get_prompt_manager() -> PromptManager:
    """获取全局提示词管理器实例"""
    global _global_prompt_manager
    if _global_prompt_manager is None:
        _global_prompt_manager = PromptManager()
        
        # 注册默认提示词生成器
        _global_prompt_manager.register('text_split', TextSplitPromptGenerator())
        _global_prompt_manager.register('translation', TranslationPromptGenerator()) 
        _global_prompt_manager.register('summary', SummaryPromptGenerator())
        _global_prompt_manager.register('subtitle_align', SubtitleAlignPromptGenerator())
    
    return _global_prompt_manager 