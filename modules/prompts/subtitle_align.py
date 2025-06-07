"""
# ----------------------------------------------------------------------------
# 字幕对齐提示词生成器
# 
# 为字幕对齐模块提供专用的提示词模板和生成逻辑
# ----------------------------------------------------------------------------
"""

from typing import Dict
from .base import PromptGenerator, PromptTemplate


class SubtitleAlignPromptGenerator(PromptGenerator):
    """字幕对齐提示词生成器"""
    
    def __init__(self):
        self._templates = {}
    
    def get_templates(self) -> Dict[str, PromptTemplate]:
        return self._templates
    
    def generate(self, **kwargs) -> str:
        # 占位符实现
        return "Subtitle align prompt placeholder" 