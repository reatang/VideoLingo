"""
# ----------------------------------------------------------------------------
# NLP文本分割器
# 
# 基于spaCy的多层NLP分割策略：
# 1. 标点符号分割
# 2. 逗号分割 
# 3. 连接词分割
# 4. 长句根据依赖关系分割
# ----------------------------------------------------------------------------
"""

import os
from pathlib import Path
from typing import Optional

from .split_spacy import SpacySplitter, SplitterConfig
from modules.common_utils import paths


class NLPSplitter:
    """基于NLP的文本分割器"""
    
    def __init__(self, 
                 output_dir: str = "output",
                 enable_all_strategies: bool = True,
                 max_sentence_length: int = 60,
                 min_sentence_length: int = 3):
        """
        初始化NLP分割器
        
        Args:
            output_dir: 输出目录
            enable_all_strategies: 是否启用所有分割策略
            max_sentence_length: 最大句子长度
            min_sentence_length: 最小句子长度
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # 配置spaCy分割器
        self.config = SplitterConfig(
            output_dir=str(self.output_dir),
            output_file="split_by_nlp.txt",
            enable_mark_split=enable_all_strategies,
            enable_comma_split=enable_all_strategies,
            enable_connector_split=enable_all_strategies,
            enable_root_split=enable_all_strategies,
            max_sentence_length=max_sentence_length,
            min_sentence_length=min_sentence_length
        )
        
        self.splitter = SpacySplitter(self.config)
    
    def split_file(self, input_file: str, output_file: Optional[str] = None) -> str:
        """
        对文件进行NLP分割
        
        Args:
            input_file: 输入Excel文件路径
            
        Returns:
            分割结果文件路径
        """
        print("🔧 开始NLP文本分割...")
        
        # 确保输入文件路径正确
        if not os.path.isabs(input_file):
            input_file = paths.get_filepath_by_default(input_file)
        
        if output_file is None:
            output_file = paths.get_filepath_by_default("split_by_nlp.txt", output_base_dir=self.output_dir)
        else:
            output_file = paths.get_filepath_by_default(output_file, output_base_dir=self.output_dir)
        
        # 启动分割器并处理
        with self.splitter:
            result = self.splitter.process_file(input_file, output_file)
        
        if result.success:
            print("✅ NLP分割完成！")
            print(f"📁 输出文件: {result.output_file}")
            print(f"📊 分割统计: {result.final_sentence_count}个句子")
            return str(result.output_file)
        else:
            raise RuntimeError(f"❌ NLP分割失败: {result.error}")
    
    def split_sentences(self, sentences: list) -> list:
        """
        直接对句子列表进行分割
        
        Args:
            sentences: 句子列表
            
        Returns:
            分割后的句子列表
        """
        print("🔧 开始NLP句子分割...")
        
        # 启动分割器
        with self.splitter:
            nlp = self.splitter.runtime.get_nlp()
            
            # 手动执行分割流程
            current_sentences = sentences
            
            # Step 1: Skip mark splitting for sentence list
            # Step 2: Comma splitting
            if self.config.enable_comma_split:
                from .split_spacy.strategies import CommaSplitter
                comma_splitter = CommaSplitter(self.config)
                current_sentences, _ = comma_splitter.process(current_sentences, nlp)
            
            # Step 3: Connector splitting
            if self.config.enable_connector_split:
                from .split_spacy.strategies import ConnectorSplitter
                connector_splitter = ConnectorSplitter(self.config)
                current_sentences, _ = connector_splitter.process(current_sentences, nlp)
            
            # Step 4: Root splitting
            if self.config.enable_root_split:
                from .split_spacy.strategies import RootSplitter
                root_splitter = RootSplitter(self.config)
                current_sentences, _ = root_splitter.process(current_sentences, nlp)
        
        print(f"✅ NLP句子分割完成: {len(sentences)} -> {len(current_sentences)}")
        return current_sentences


# ----------------------------------------------------------------------------
# 独立运行测试
# ----------------------------------------------------------------------------
if __name__ == '__main__':
    import sys
    
    # 测试NLP分割器
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        input_file = "log/cleaned_chunks.xlsx"
    
    try:
        splitter = NLPSplitter()
        result_file = splitter.split_file(input_file)
        print(f"✅ 测试完成！结果文件: {result_file}")
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc() 