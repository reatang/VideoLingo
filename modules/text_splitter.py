"""
# ----------------------------------------------------------------------------
# 文本分割器模块 - 负责将转录文本进行智能分割优化
# 
# 核心功能：
# 1. NLP标点符号分割
# 2. 智能逗号分割 
# 3. 句子连接符分割
# 4. 基于语义的GPT智能分割
# 5. 长句根据语法结构分割
# 
# 输入：转录结果Excel文件
# 输出：多层级分割优化的文本文件
# ----------------------------------------------------------------------------
"""

import os
import re
import json
import math
import itertools
import warnings
from typing import List, Dict, Optional, Callable
from pathlib import Path
import concurrent.futures
from difflib import SequenceMatcher

warnings.filterwarnings("ignore", category=FutureWarning)


class TextSplitter:
    """文本分割器类 - 封装文本分割的所有功能"""
    
    def __init__(self,
                 input_file: str = 'output/log/2_cleaned_chunks.xlsx',
                 output_dir: str = 'output/log',
                 language: str = 'en',
                 max_split_length: int = 20,
                 max_workers: int = 4):
        """
        初始化文本分割器
        
        Args:
            input_file: 输入的转录结果文件
            output_dir: 输出目录
            language: 语言代码 (en, zh, fr等)
            max_split_length: 最大分割长度
            max_workers: 并行处理的最大线程数
        """
        self.input_file = Path(input_file)
        self.output_dir = Path(output_dir)
        self.language = language
        self.max_split_length = max_split_length
        self.max_workers = max_workers
        
        # 创建输出目录
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 文件路径配置
        self.mark_split_file = self.output_dir / '3_1_split_by_mark.txt'
        self.comma_split_file = self.output_dir / '3_1_split_by_comma.txt'
        self.connector_split_file = self.output_dir / '3_1_split_by_connector.txt'
        self.nlp_split_file = self.output_dir / '3_1_split_by_nlp.txt'
        self.meaning_split_file = self.output_dir / '3_2_split_by_meaning.txt'
        
        # 语言相关配置
        self.language_configs = {
            'en': {'joiner': ' ', 'spacy_model': 'en_core_web_md'},
            'zh': {'joiner': '', 'spacy_model': 'zh_core_web_sm'},
            'fr': {'joiner': ' ', 'spacy_model': 'fr_core_news_sm'},
            'de': {'joiner': ' ', 'spacy_model': 'de_core_news_sm'},
            'es': {'joiner': ' ', 'spacy_model': 'es_core_news_sm'},
            'ja': {'joiner': '', 'spacy_model': 'ja_core_news_sm'},
        }
        
        self.joiner = self.language_configs.get(language, {'joiner': ' '})['joiner']
        self.spacy_model = self.language_configs.get(language, {'spacy_model': 'en_core_web_md'})['spacy_model']
        
        # 懒加载spaCy和pandas
        self._nlp = None
        self._pd = None
        self._ask_gpt_func = None
    
    def _get_nlp(self):
        """懒加载spaCy模型"""
        if self._nlp is None:
            try:
                import spacy
                print(f"🔄 正在加载spaCy模型: {self.spacy_model}")
                try:
                    self._nlp = spacy.load(self.spacy_model)
                    print(f"✅ spaCy模型加载成功")
                except IOError:
                    print(f"⚠️  模型 {self.spacy_model} 未找到, 正在下载...")
                    spacy.cli.download(self.spacy_model)
                    self._nlp = spacy.load(self.spacy_model)
                    print(f"✅ spaCy模型下载并加载成功")
            except ImportError:
                raise ImportError("❌ 未找到spaCy库, 请安装: pip install spacy")
        return self._nlp
    
    def _get_pandas(self):
        """懒加载pandas"""
        if self._pd is None:
            try:
                import pandas as pd
                self._pd = pd
            except ImportError:
                raise ImportError("❌ 未找到pandas库, 请安装: pip install pandas")
        return self._pd
    
    def set_gpt_function(self, ask_gpt_func: Callable):
        """
        设置GPT调用函数
        
        Args:
            ask_gpt_func: GPT API调用函数
        """
        self._ask_gpt_func = ask_gpt_func
        print("✅ GPT函数已设置")
    
    def load_transcription_data(self) -> List[str]:
        """
        加载转录数据
        
        Returns:
            文本列表
        """
        print(f"📖 正在加载转录数据: {self.input_file}")
        
        if not self.input_file.exists():
            raise FileNotFoundError(f"❌ 转录文件不存在: {self.input_file}")
        
        try:
            pd = self._get_pandas()
            chunks = pd.read_excel(self.input_file)
            
            if 'text' not in chunks.columns:
                raise ValueError("❌ Excel文件缺少'text'列")
            
            # 清理文本数据
            chunks['text'] = chunks['text'].apply(lambda x: str(x).strip('"').strip())
            text_list = chunks['text'].tolist()
            
            # 过滤空文本
            text_list = [text for text in text_list if text.strip()]
            
            print(f"✅ 加载了{len(text_list)}条文本记录")
            return text_list
            
        except Exception as e:
            print(f"❌ 加载转录数据失败: {str(e)}")
            raise
    
    def split_by_punctuation_marks(self, text_list: List[str]) -> List[str]:
        """
        使用标点符号进行句子分割
        
        Args:
            text_list: 文本列表
            
        Returns:
            分割后的句子列表
        """
        print("🔍 开始标点符号分割...")
        
        try:
            nlp = self._get_nlp()
            
            # 合并所有文本
            combined_text = self.joiner.join(text_list)
            
            # 使用spaCy进行句子分割
            doc = nlp(combined_text)
            
            if not doc.has_annotation("SENT_START"):
                print("⚠️  spaCy模型不支持句子分割, 使用简单分割")
                return self._simple_sentence_split(combined_text)
            
            sentences_by_mark = []
            current_sentence = []
            
            # 处理句子分割, 特别处理破折号和省略号
            for sent in doc.sents:
                text = sent.text.strip()
                
                # 检查是否应该与前一句合并
                if current_sentence and (
                    text.startswith('-') or 
                    text.startswith('...') or
                    current_sentence[-1].endswith('-') or
                    current_sentence[-1].endswith('...')
                ):
                    current_sentence.append(text)
                else:
                    if current_sentence:
                        sentences_by_mark.append(' '.join(current_sentence))
                        current_sentence = []
                    current_sentence.append(text)
            
            # 添加最后一个句子
            if current_sentence:
                sentences_by_mark.append(' '.join(current_sentence))
            
            # 处理单独的标点符号行（中文、日文等）
            final_sentences = []
            for i, sentence in enumerate(sentences_by_mark):
                if i > 0 and sentence.strip() in [',', '.', '，', '。', '？', '！']:
                    # 与前一句合并
                    if final_sentences:
                        final_sentences[-1] += sentence
                else:
                    final_sentences.append(sentence)
            
            print(f"✅ 标点符号分割完成, 共{len(final_sentences)}个句子")
            return final_sentences
            
        except Exception as e:
            print(f"❌ 标点符号分割失败: {str(e)}")
            # 回退到简单分割
            return self._simple_sentence_split(self.joiner.join(text_list))
    
    def _simple_sentence_split(self, text: str) -> List[str]:
        """简单的句子分割备用方案"""
        print("📝 使用简单句子分割...")
        
        # 基于常见句子结束符分割
        sentence_enders = r'[.!?。！？]+\s+'
        sentences = re.split(sentence_enders, text)
        
        # 清理空句子
        sentences = [s.strip() for s in sentences if s.strip()]
        
        return sentences
    
    def _is_valid_phrase(self, phrase) -> bool:
        """
        检查短语是否有效（包含主语和谓语）
        
        Args:
            phrase: spaCy Doc对象
            
        Returns:
            是否为有效短语
        """
        has_subject = any(
            token.dep_ in ["nsubj", "nsubjpass"] or token.pos_ == "PRON" 
            for token in phrase
        )
        has_verb = any(
            token.pos_ in ["VERB", "AUX"] 
            for token in phrase
        )
        return has_subject and has_verb
    
    def _analyze_comma_split(self, start: int, doc, token) -> bool:
        """
        分析逗号位置是否适合分割
        
        Args:
            start: 起始位置
            doc: spaCy Doc对象
            token: 当前token
            
        Returns:
            是否适合分割
        """
        # 获取左右短语
        left_phrase = doc[max(start, token.i - 9):token.i]
        right_phrase = doc[token.i + 1:min(len(doc), token.i + 10)]
        
        # 检查右侧短语的有效性
        suitable_for_splitting = self._is_valid_phrase(right_phrase)
        
        # 移除标点符号并检查词数
        left_words = [t for t in left_phrase if not t.is_punct]
        right_words = list(itertools.takewhile(lambda t: not t.is_punct, right_phrase))
        
        # 确保左右两边都有足够的词
        if len(left_words) <= 3 or len(right_words) <= 3:
            suitable_for_splitting = False
        
        return suitable_for_splitting
    
    def split_by_commas(self, sentences: List[str]) -> List[str]:
        """
        智能逗号分割
        
        Args:
            sentences: 句子列表
            
        Returns:
            逗号分割后的句子列表
        """
        print("📍 开始智能逗号分割...")
        
        try:
            nlp = self._get_nlp()
            all_split_sentences = []
            
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                
                doc = nlp(sentence)
                split_sentences = []
                start = 0
                
                for i, token in enumerate(doc):
                    if token.text in [",", "，"]:
                        suitable_for_splitting = self._analyze_comma_split(start, doc, token)
                        
                        if suitable_for_splitting:
                            split_part = doc[start:token.i].text.strip()
                            split_sentences.append(split_part)
                            print(f"✂️  逗号分割: ...{doc[start:token.i][-20:]} | {doc[token.i + 1:][:20]}...")
                            start = token.i + 1
                
                # 添加最后一部分
                if start < len(doc):
                    split_sentences.append(doc[start:].text.strip())
                
                # 如果没有分割, 保留原句
                if not split_sentences:
                    split_sentences = [sentence]
                
                all_split_sentences.extend(split_sentences)
            
            print(f"✅ 逗号分割完成, 共{len(all_split_sentences)}个片段")
            return all_split_sentences
            
        except Exception as e:
            print(f"❌ 逗号分割失败: {str(e)}")
            return sentences
    
    def split_by_semantic_meaning(self, sentences: List[str]) -> List[str]:
        """
        基于语义的智能分割
        
        Args:
            sentences: 句子列表
            
        Returns:
            语义分割后的句子列表
        """
        print("🧠 开始语义智能分割...")
        
        if self._ask_gpt_func is None:
            print("⚠️  未设置GPT函数, 跳过语义分割")
            return sentences
        
        try:
            nlp = self._get_nlp()
            
            # 并行处理语义分割
            new_sentences = self._parallel_semantic_split(sentences, nlp)
            
            print(f"✅ 语义分割完成, 共{len(new_sentences)}个句子")
            return new_sentences
            
        except Exception as e:
            print(f"❌ 语义分割失败: {str(e)}")
            return sentences
    
    def _tokenize_sentence(self, sentence: str) -> List[str]:
        """
        对句子进行分词
        
        Args:
            sentence: 句子
            
        Returns:
            词汇列表
        """
        try:
            nlp = self._get_nlp()
            doc = nlp(sentence)
            return [token.text for token in doc]
        except:
            # 简单分词备用方案
            return sentence.split()
    
    def _split_single_sentence(self, sentence: str, num_parts: int = 2, index: int = -1) -> str:
        """
        使用GPT分割单个句子
        
        Args:
            sentence: 待分割的句子
            num_parts: 分割成的部分数
            index: 句子索引
            
        Returns:
            分割后的句子（用\\n分隔）
        """
        if self._ask_gpt_func is None:
            return sentence
        
        try:
            # 构建分割提示词
            split_prompt = self._get_split_prompt(sentence, num_parts, self.max_split_length)
            
            # 调用GPT进行分割
            response_data = self._ask_gpt_func(
                split_prompt,
                resp_type='json',
                log_title='semantic_split'
            )
            
            # 解析响应
            choice = response_data.get("choice", "1")
            best_split = response_data.get(f"split{choice}", sentence)
            
            # 查找分割点
            split_points = self._find_split_positions(sentence, best_split)
            
            # 应用分割点
            result = self._apply_split_points(sentence, split_points)
            
            if index >= 0:
                print(f"✅ 句子{index}语义分割完成")
            
            return result
            
        except Exception as e:
            print(f"⚠️  句子分割失败: {str(e)}")
            return sentence
    
    def _get_split_prompt(self, sentence: str, num_parts: int, word_limit: int) -> str:
        """生成分割提示词"""
        return f"""
## Role
You are a professional Netflix subtitle splitter in **{self.language}**.

## Task
Split the given subtitle text into **{num_parts}** parts, each less than **{word_limit}** words.

1. Maintain sentence meaning coherence according to Netflix subtitle standards
2. MOST IMPORTANT: Keep parts roughly equal in length (minimum 3 words each)
3. Split at natural points like punctuation marks or conjunctions
4. If provided text is repeated words, simply split at the middle of the repeated words.

## Steps
1. Analyze the sentence structure, complexity, and key splitting challenges
2. Generate two alternative splitting approaches with [br] tags at split positions
3. Compare both approaches highlighting their strengths and weaknesses
4. Choose the best splitting approach

## Given Text
<split_this_sentence>
{sentence}
</split_this_sentence>

## Output in only JSON format and no other text
```json
{{
    "analysis": "Brief description of sentence structure, complexity, and key splitting challenges",
    "split1": "First splitting approach with [br] tags at split positions",
    "split2": "Alternative splitting approach with [br] tags at split positions",
    "assess": "Comparison of both approaches highlighting their strengths and weaknesses",
    "choice": "1 or 2"
}}
```

Note: Start you answer with ```json and end with ```, do not add any other text.
""".strip()
    
    def _find_split_positions(self, original: str, modified: str) -> List[int]:
        """查找分割位置"""
        split_positions = []
        parts = modified.split('[br]')
        start = 0
        
        for i in range(len(parts) - 1):
            max_similarity = 0
            best_split = None
            
            for j in range(start, len(original)):
                original_left = original[start:j]
                modified_left = self.joiner.join(parts[i].split())
                
                left_similarity = SequenceMatcher(None, original_left, modified_left).ratio()
                
                if left_similarity > max_similarity:
                    max_similarity = left_similarity
                    best_split = j
            
            if max_similarity < 0.9:
                print(f"⚠️  分割点相似度较低: {max_similarity:.3f}")
            
            if best_split is not None:
                split_positions.append(best_split)
                start = best_split
        
        return split_positions
    
    def _apply_split_points(self, sentence: str, split_points: List[int]) -> str:
        """应用分割点"""
        if not split_points:
            return sentence
        
        result = sentence
        for i, split_point in enumerate(split_points):
            if i == 0:
                result = sentence[:split_point] + '\n' + sentence[split_point:]
            else:
                parts = result.split('\n')
                last_part = parts[-1]
                offset = split_point - split_points[i-1]
                parts[-1] = last_part[:offset] + '\n' + last_part[offset:]
                result = '\n'.join(parts)
        
        return result
    
    def _parallel_semantic_split(self, sentences: List[str], nlp) -> List[str]:
        """并行语义分割处理"""
        new_sentences = [None] * len(sentences)
        futures = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            for index, sentence in enumerate(sentences):
                tokens = self._tokenize_sentence(sentence)
                num_parts = math.ceil(len(tokens) / self.max_split_length)
                
                if len(tokens) > self.max_split_length:
                    future = executor.submit(
                        self._split_single_sentence, 
                        sentence, 
                        num_parts, 
                        index
                    )
                    futures.append((future, index))
                else:
                    new_sentences[index] = [sentence]
            
            # 收集结果
            for future, index in futures:
                try:
                    split_result = future.result()
                    if split_result and '\n' in split_result:
                        split_lines = split_result.strip().split('\n')
                        new_sentences[index] = [line.strip() for line in split_lines]
                    else:
                        new_sentences[index] = [sentences[index]]
                except Exception as e:
                    print(f"⚠️  句子{index}分割失败: {str(e)}")
                    new_sentences[index] = [sentences[index]]
        
        # 展平结果
        return [sentence for sublist in new_sentences for sentence in sublist if sentence]
    
    def save_split_results(self, sentences: List[str], stage: str) -> str:
        """
        保存分割结果
        
        Args:
            sentences: 句子列表
            stage: 阶段名称 ('mark', 'comma', 'connector', 'nlp', 'meaning')
            
        Returns:
            保存的文件路径
        """
        file_map = {
            'mark': self.mark_split_file,
            'comma': self.comma_split_file,
            'connector': self.connector_split_file,
            'nlp': self.nlp_split_file,
            'meaning': self.meaning_split_file
        }
        
        output_file = file_map.get(stage, self.output_dir / f'split_{stage}.txt')
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                for sentence in sentences:
                    if sentence.strip():
                        f.write(sentence.strip() + '\n')
            
            print(f"💾 {stage}分割结果已保存: {output_file}")
            return str(output_file)
            
        except Exception as e:
            print(f"❌ 保存{stage}分割结果失败: {str(e)}")
            raise
    
    def process_complete_split(self, 
                             enable_comma_split: bool = True,
                             enable_semantic_split: bool = True) -> str:
        """
        完整的文本分割处理流程
        
        Args:
            enable_comma_split: 是否启用逗号分割
            enable_semantic_split: 是否启用语义分割
            
        Returns:
            最终分割结果文件路径
        """
        print("🚀 开始完整文本分割流程...")
        
        try:
            # 1. 加载转录数据
            text_list = self.load_transcription_data()
            
            # 2. 标点符号分割
            sentences = self.split_by_punctuation_marks(text_list)
            self.save_split_results(sentences, 'mark')
            
            # 3. 逗号分割（可选）
            if enable_comma_split:
                sentences = self.split_by_commas(sentences)
                self.save_split_results(sentences, 'comma')
            
            # 合并为NLP分割结果
            self.save_split_results(sentences, 'nlp')
            
            # 4. 语义分割（可选）
            if enable_semantic_split:
                sentences = self.split_by_semantic_meaning(sentences)
                final_file = self.save_split_results(sentences, 'meaning')
            else:
                final_file = str(self.nlp_split_file)
            
            print("🎉 文本分割流程完成！")
            print(f"📊 最终结果: {len(sentences)}个分割片段")
            
            return final_file
            
        except Exception as e:
            print(f"💥 文本分割流程失败: {str(e)}")
            raise


# ----------------------------------------------------------------------------
# 独立运行测试
# ----------------------------------------------------------------------------
if __name__ == '__main__':
    import sys
    
    # 创建分割器实例
    splitter = TextSplitter(
        language='en',
        max_split_length=20,
        max_workers=2
    )
    
    # 测试参数
    test_with_gpt = '--gpt' in sys.argv
    
    if test_with_gpt:
        print("⚠️  注意: 需要提供GPT函数才能进行语义分割测试")
        # splitter.set_gpt_function(your_gpt_function)
    
    try:
        # 检查输入文件
        if not splitter.input_file.exists():
            print(f"❌ 输入文件不存在: {splitter.input_file}")
            print("💡 请先运行音频转录器生成转录文件")
            sys.exit(1)
        
        # 运行完整分割流程
        print("\n🧪 测试文本分割流程...")
        
        final_file = splitter.process_complete_split(
            enable_comma_split=True,
            enable_semantic_split=test_with_gpt
        )
        
        print(f"\n✅ 测试完成！")
        print(f"📁 最终文件: {final_file}")
        
        # 显示部分结果
        if Path(final_file).exists():
            with open(final_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()[:10]  # 显示前10行
            
            print(f"\n📋 结果预览 (前{len(lines)}行):")
            for i, line in enumerate(lines, 1):
                print(f"  {i:2d}. {line.strip()}")
            
            if len(lines) == 10:
                print("     ...")
        
    except Exception as e:
        print(f"\n💥 测试过程中发生错误: {str(e)}")
        sys.exit(1) 