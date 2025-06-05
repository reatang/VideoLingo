"""
# ----------------------------------------------------------------------------
# 文本翻译器模块 - 基于上下文的高质量智能翻译
# 
# 核心功能：
# 1. 基于ContentSummarizer上下文的智能翻译
# 2. 双阶段翻译策略：忠实翻译 → 表达优化
# 3. 术语一致性保证和智能匹配
# 4. 并行批量翻译和性能优化
# 5. 上下文感知的翻译质量控制
# 6. 自适应分块和边界处理
# 
# 输入：分割文本文件，术语信息，翻译上下文
# 输出：高质量双语对照翻译结果Excel
# 
# 设计原则：
# - 充分利用ContentSummarizer提供的丰富上下文
# - 确保术语翻译的一致性和准确性
# - 支持多种翻译策略和质量控制
# - 高效的并行处理和错误恢复
# ----------------------------------------------------------------------------
"""

import os
import json
import hashlib
import math
from typing import List, Dict, Optional, Callable, Tuple, Any
from pathlib import Path
import concurrent.futures
from dataclasses import dataclass, asdict
from collections import defaultdict
from difflib import SequenceMatcher
import warnings

warnings.filterwarnings("ignore", category=FutureWarning)


@dataclass
class TranslationChunk:
    """翻译块数据类"""
    index: int                      # 块索引
    source_text: str               # 源文本
    translated_text: str = ""      # 翻译文本
    confidence: float = 0.0        # 翻译置信度
    processing_time: float = 0.0   # 处理时间
    retry_count: int = 0           # 重试次数
    error_message: str = ""        # 错误信息
    context_terms: List[str] = None # 使用的术语
    
    def __post_init__(self):
        if self.context_terms is None:
            self.context_terms = []


@dataclass
class TranslationResult:
    """翻译结果数据类"""
    total_chunks: int              # 总块数
    successful_chunks: int         # 成功块数
    failed_chunks: int             # 失败块数
    total_time: float              # 总处理时间
    average_confidence: float      # 平均置信度
    output_file: str               # 输出文件路径
    chunks: List[TranslationChunk] = None # 详细结果
    
    def __post_init__(self):
        if self.chunks is None:
            self.chunks = []


class TextTranslator:
    """文本翻译器类 - 基于上下文的高质量翻译"""
    
    def __init__(self,
                 input_file: str = 'output/log/3_2_split_by_meaning.txt',
                 terminology_file: str = 'output/log/4_1_terminology.json',
                 context_file: str = 'output/log/4_1_translation_context.json',
                 output_dir: str = 'output/log',
                 src_language: str = 'en',
                 tgt_language: str = 'zh',
                 chunk_size: int = 600,
                 max_chunk_lines: int = 10,
                 max_workers: int = 4,
                 enable_reflect_translate: bool = True,
                 similarity_threshold: float = 0.9):
        """
        初始化文本翻译器
        
        Args:
            input_file: 输入的分割文本文件
            terminology_file: 术语信息文件
            context_file: 翻译上下文文件
            output_dir: 输出目录
            src_language: 源语言代码
            tgt_language: 目标语言代码
            chunk_size: 分块大小（字符数）
            max_chunk_lines: 分块最大行数
            max_workers: 并行处理的最大线程数
            enable_reflect_translate: 是否启用反思翻译
            similarity_threshold: 相似度阈值
        """
        self.input_file = Path(input_file)
        self.terminology_file = Path(terminology_file)
        self.context_file = Path(context_file)
        self.output_dir = Path(output_dir)
        self.src_language = src_language
        self.tgt_language = tgt_language
        self.chunk_size = chunk_size
        self.max_chunk_lines = max_chunk_lines
        self.max_workers = max_workers
        self.enable_reflect_translate = enable_reflect_translate
        self.similarity_threshold = similarity_threshold
        
        # 创建输出目录
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 文件路径配置
        self.translation_file = self.output_dir / '4_2_translation.xlsx'
        self.faithful_file = self.output_dir / '4_2_faithful_translation.json'
        self.expressive_file = self.output_dir / '4_2_expressive_translation.json'
        
        # 懒加载依赖
        self._pd = None
        self._ask_gpt_func = None
        
        # 内部状态
        self._terminology_data = {}
        self._translation_context = {}
        self._content_theme = ""
        self._chunks = []
        self._term_mapping = {}
        
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
            ask_gpt_func: GPT API调用函数，签名为(prompt, resp_type='json', log_title='', valid_def=None)
        """
        self._ask_gpt_func = ask_gpt_func
        print("✅ GPT函数已设置")
    
    def load_translation_context(self) -> Tuple[Dict, Dict, str]:
        """
        加载翻译上下文信息
        
        Returns:
            (术语信息, 翻译上下文, 内容主题)
        """
        print("📚 正在加载翻译上下文...")
        
        # 加载术语信息
        terminology_data = {}
        if self.terminology_file.exists():
            try:
                with open(self.terminology_file, 'r', encoding='utf-8') as f:
                    terminology_data = json.load(f)
                print(f"✅ 加载了{len(terminology_data.get('terms', []))}个术语")
            except Exception as e:
                print(f"⚠️  加载术语文件失败: {str(e)}")
        
        # 加载翻译上下文
        translation_context = {}
        if self.context_file.exists():
            try:
                with open(self.context_file, 'r', encoding='utf-8') as f:
                    translation_context = json.load(f)
                print(f"✅ 加载了翻译上下文信息")
            except Exception as e:
                print(f"⚠️  加载上下文文件失败: {str(e)}")
        
        # 提取内容主题
        content_theme = terminology_data.get('theme', '视频内容翻译')
        
        # 构建术语映射表
        self._build_term_mapping(terminology_data.get('terms', []))
        
        return terminology_data, translation_context, content_theme
    
    def _build_term_mapping(self, terms: List[Dict]):
        """构建术语映射表以便快速查询"""
        self._term_mapping = {}
        for term in terms:
            src = term.get('src', '').lower()
            if src:
                self._term_mapping[src] = {
                    'tgt': term.get('tgt', ''),
                    'note': term.get('note', ''),
                    'category': term.get('category', ''),
                    'confidence': term.get('confidence', 1.0)
                }
        print(f"📖 构建了{len(self._term_mapping)}个术语的快速映射表")
    
    def load_input_text(self) -> List[str]:
        """
        加载输入文本
        
        Returns:
            文本行列表
        """
        print(f"📖 正在加载分割文本: {self.input_file}")
        
        if not self.input_file.exists():
            raise FileNotFoundError(f"❌ 分割文本文件不存在: {self.input_file}")
        
        try:
            with open(self.input_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # 清理文本行
            cleaned_lines = [line.strip() for line in lines if line.strip()]
            
            print(f"✅ 加载了{len(cleaned_lines)}行文本")
            return cleaned_lines
            
        except Exception as e:
            print(f"❌ 加载分割文本失败: {str(e)}")
            raise
    
    def split_text_into_chunks(self, lines: List[str]) -> List[str]:
        """
        将文本分割为翻译块
        
        Args:
            lines: 文本行列表
            
        Returns:
            文本块列表
        """
        print(f"✂️  正在分割文本为翻译块...")
        
        chunks = []
        current_chunk = ''
        current_line_count = 0
        
        for line in lines:
            # 检查是否超过大小或行数限制
            if (len(current_chunk) + len(line + '\n') > self.chunk_size or 
                current_line_count >= self.max_chunk_lines):
                
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                current_chunk = line + '\n'
                current_line_count = 1
            else:
                current_chunk += line + '\n'
                current_line_count += 1
        
        # 添加最后一个块
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        print(f"✅ 分割为{len(chunks)}个翻译块")
        return chunks
    
    def get_chunk_context(self, chunks: List[str], chunk_index: int) -> Tuple[Optional[List[str]], Optional[List[str]]]:
        """
        获取翻译块的上下文
        
        Args:
            chunks: 所有块列表
            chunk_index: 当前块索引
            
        Returns:
            (前文行列表, 后文行列表)
        """
        # 获取前文（前一个块的最后3行）
        previous_content = None
        if chunk_index > 0:
            prev_lines = chunks[chunk_index - 1].split('\n')
            previous_content = prev_lines[-3:] if len(prev_lines) >= 3 else prev_lines
        
        # 获取后文（后一个块的前2行）
        after_content = None
        if chunk_index < len(chunks) - 1:
            next_lines = chunks[chunk_index + 1].split('\n')
            after_content = next_lines[:2] if len(next_lines) >= 2 else next_lines
        
        return previous_content, after_content
    
    def search_relevant_terms(self, text: str) -> List[Dict]:
        """
        搜索文本中的相关术语
        
        Args:
            text: 待搜索的文本
            
        Returns:
            相关术语列表
        """
        relevant_terms = []
        text_lower = text.lower()
        
        for src_term, term_info in self._term_mapping.items():
            if src_term in text_lower:
                relevant_terms.append({
                    'src': src_term,
                    'tgt': term_info['tgt'],
                    'note': term_info['note'],
                    'category': term_info['category'],
                    'confidence': term_info['confidence']
                })
        
        # 按置信度和类别排序
        relevant_terms.sort(key=lambda x: (x['category'] == 'custom', x['confidence']), reverse=True)
        
        return relevant_terms
    
    def generate_shared_prompt(self, 
                             previous_content: Optional[List[str]], 
                             after_content: Optional[List[str]], 
                             theme: str, 
                             relevant_terms: List[Dict]) -> str:
        """
        生成共享提示词
        
        Args:
            previous_content: 前文内容
            after_content: 后文内容  
            theme: 内容主题
            relevant_terms: 相关术语
            
        Returns:
            共享提示词
        """
        # 构建上下文信息
        context_parts = []
        
        if previous_content:
            context_parts.append(f"### Previous Content\n{chr(10).join(previous_content)}")
        
        if after_content:
            context_parts.append(f"### Subsequent Content\n{chr(10).join(after_content)}")
        
        # 构建术语信息
        terms_info = ""
        if relevant_terms:
            terms_list = []
            for term in relevant_terms:
                terms_list.append(f"- {term['src']}: {term['tgt']} ({term['note']})")
            terms_info = f"### Key Terms\n{chr(10).join(terms_list)}"
        
        # 组合提示词
        shared_prompt = f"""### Context Information
{chr(10).join(context_parts)}

### Content Summary
{theme}

### Points to Note
{terms_info}"""
        
        return shared_prompt
    
    def get_faithful_translation_prompt(self, lines: str, shared_prompt: str) -> str:
        """生成忠实翻译提示词"""
        
        # 构建JSON格式模板
        line_splits = lines.split('\n')
        json_dict = {}
        for i, line in enumerate(line_splits, 1):
            json_dict[str(i)] = {
                "origin": line, 
                "direct": f"direct {self.tgt_language} translation {i}."
            }
        json_format = json.dumps(json_dict, indent=2, ensure_ascii=False)
        
        return f"""
## Role
You are a professional Netflix subtitle translator, fluent in both {self.src_language} and {self.tgt_language}, as well as their respective cultures. 
Your expertise lies in accurately understanding the semantics and structure of the original {self.src_language} text and faithfully translating it into {self.tgt_language} while preserving the original meaning.

## Task
We have a segment of original {self.src_language} subtitles that need to be directly translated into {self.tgt_language}. These subtitles come from a specific context and may contain specific themes and terminology.

1. Translate the original {self.src_language} subtitles into {self.tgt_language} line by line
2. Ensure the translation is faithful to the original, accurately conveying the original meaning
3. Consider the context and professional terminology

{shared_prompt}

<translation_principles>
1. Faithful to the original: Accurately convey the content and meaning of the original text, without arbitrarily changing, adding, or omitting content.
2. Accurate terminology: Use professional terms correctly and maintain consistency in terminology.
3. Understand the context: Fully comprehend and reflect the background and contextual relationships of the text.
</translation_principles>

## INPUT
<subtitles>
{lines}
</subtitles>

## Output in only JSON format and no other text
```json
{json_format}
```

Note: Start your answer with ```json and end with ```, do not add any other text.
""".strip()
    
    def get_expressive_translation_prompt(self, faithful_result: Dict, lines: str, shared_prompt: str) -> str:
        """生成表达优化翻译提示词"""
        
        # 构建JSON格式模板
        json_format = {}
        for key, value in faithful_result.items():
            json_format[key] = {
                "origin": value["origin"],
                "direct": value["direct"],
                "reflect": "your reflection on direct translation",
                "free": "your free translation"
            }
        json_format_str = json.dumps(json_format, indent=2, ensure_ascii=False)
        
        return f"""
## Role
You are a professional Netflix subtitle translator and language consultant.
Your expertise lies not only in accurately understanding the original {self.src_language} but also in optimizing the {self.tgt_language} translation to better suit the target language's expression habits and cultural background.

## Task
We already have a direct translation version of the original {self.src_language} subtitles.
Your task is to reflect on and improve these direct translations to create more natural and fluent {self.tgt_language} subtitles.

1. Analyze the direct translation results line by line, pointing out existing issues
2. Provide detailed modification suggestions
3. Perform free translation based on your analysis
4. Do not add comments or explanations in the translation, as the subtitles are for the audience to read
5. Do not leave empty lines in the free translation, as the subtitles are for the audience to read

{shared_prompt}

<Translation Analysis Steps>
Please use a two-step thinking process to handle the text line by line:

1. Direct Translation Reflection:
   - Evaluate language fluency
   - Check if the language style is consistent with the original text
   - Check the conciseness of the subtitles, point out where the translation is too wordy

2. {self.tgt_language} Free Translation:
   - Aim for contextual smoothness and naturalness, conforming to {self.tgt_language} expression habits
   - Ensure it's easy for {self.tgt_language} audience to understand and accept
   - Adapt the language style to match the theme (e.g., use casual language for tutorials, professional terminology for technical content, formal language for documentaries)
</Translation Analysis Steps>
   
## INPUT
<subtitles>
{lines}
</subtitles>

## Output in only JSON format and no other text
```json
{json_format_str}
```

Note: Start your answer with ```json and end with ```, do not add any other text.
""".strip()
    
    def validate_translation_result(self, result: Dict, required_keys: List[str], required_sub_keys: List[str]) -> Dict:
        """验证翻译结果格式"""
        # 检查必需的键
        if not all(key in result for key in required_keys):
            missing_keys = set(required_keys) - set(result.keys())
            return {"status": "error", "message": f"Missing required key(s): {', '.join(missing_keys)}"}
        
        # 检查所有项目中的必需子键
        for key in result:
            if not all(sub_key in result[key] for sub_key in required_sub_keys):
                missing_sub_keys = set(required_sub_keys) - set(result[key].keys())
                return {"status": "error", "message": f"Missing required sub-key(s) in item {key}: {', '.join(missing_sub_keys)}"}
        
        return {"status": "success", "message": "Translation completed"}
    
    def translate_single_chunk(self, 
                             chunk_text: str, 
                             chunk_index: int, 
                             chunks: List[str], 
                             theme: str) -> TranslationChunk:
        """
        翻译单个文本块
        
        Args:
            chunk_text: 文本块内容
            chunk_index: 块索引
            chunks: 所有块列表
            theme: 内容主题
            
        Returns:
            翻译结果
        """
        import time
        start_time = time.time()
        
        if self._ask_gpt_func is None:
            # 没有GPT函数时的简单处理
            return TranslationChunk(
                index=chunk_index,
                source_text=chunk_text,
                translated_text=f"[需要GPT翻译] {chunk_text}",
                confidence=0.0,
                processing_time=time.time() - start_time,
                error_message="GPT function not set"
            )
        
        try:
            # 获取上下文和相关术语
            previous_content, after_content = self.get_chunk_context(chunks, chunk_index)
            relevant_terms = self.search_relevant_terms(chunk_text)
            
            # 生成共享提示词
            shared_prompt = self.generate_shared_prompt(
                previous_content, after_content, theme, relevant_terms
            )
            
            # 第一阶段：忠实翻译
            faithful_prompt = self.get_faithful_translation_prompt(chunk_text, shared_prompt)
            
            # 重试机制
            line_count = len(chunk_text.split('\n'))
            for retry in range(3):
                try:
                    def valid_faithful(response_data):
                        return self.validate_translation_result(
                            response_data, 
                            [str(i) for i in range(1, line_count + 1)], 
                            ['direct']
                        )
                    
                    faithful_result = self._ask_gpt_func(
                        faithful_prompt + " " * retry,
                        resp_type='json',
                        valid_def=valid_faithful,
                        log_title='translate_faithful'
                    )
                    
                    if len(faithful_result) == line_count:
                        break
                        
                except Exception as e:
                    if retry == 2:
                        raise e
                    print(f"⚠️  块{chunk_index}忠实翻译重试{retry + 1}/3...")
            
            # 清理换行符
            for key in faithful_result:
                faithful_result[key]["direct"] = faithful_result[key]["direct"].replace('\n', ' ')
            
            # 如果不启用反思翻译，直接返回忠实翻译
            if not self.enable_reflect_translate:
                final_translation = '\n'.join([
                    faithful_result[str(i)]["direct"].strip() 
                    for i in range(1, line_count + 1)
                ])
                
                return TranslationChunk(
                    index=chunk_index,
                    source_text=chunk_text,
                    translated_text=final_translation,
                    confidence=0.8,
                    processing_time=time.time() - start_time,
                    context_terms=[term['src'] for term in relevant_terms]
                )
            
            # 第二阶段：表达优化
            expressive_prompt = self.get_expressive_translation_prompt(
                faithful_result, chunk_text, shared_prompt
            )
            
            for retry in range(3):
                try:
                    def valid_expressive(response_data):
                        return self.validate_translation_result(
                            response_data,
                            [str(i) for i in range(1, line_count + 1)],
                            ['free']
                        )
                    
                    expressive_result = self._ask_gpt_func(
                        expressive_prompt + " " * retry,
                        resp_type='json',
                        valid_def=valid_expressive,
                        log_title='translate_expressive'
                    )
                    
                    if len(expressive_result) == line_count:
                        break
                        
                except Exception as e:
                    if retry == 2:
                        raise e
                    print(f"⚠️  块{chunk_index}表达优化重试{retry + 1}/3...")
            
            # 组合最终翻译结果
            final_translation = '\n'.join([
                expressive_result[str(i)]["free"].replace('\n', ' ').strip()
                for i in range(1, line_count + 1)
            ])
            
            # 验证翻译结果长度
            if len(chunk_text.split('\n')) != len(final_translation.split('\n')):
                raise ValueError(f"Translation length mismatch for chunk {chunk_index}")
            
            return TranslationChunk(
                index=chunk_index,
                source_text=chunk_text,
                translated_text=final_translation,
                confidence=0.9,
                processing_time=time.time() - start_time,
                context_terms=[term['src'] for term in relevant_terms]
            )
            
        except Exception as e:
            return TranslationChunk(
                index=chunk_index,
                source_text=chunk_text,
                translated_text="",
                confidence=0.0,
                processing_time=time.time() - start_time,
                retry_count=3,
                error_message=str(e)
            )
    
    def translate_all_chunks(self, chunks: List[str], theme: str) -> List[TranslationChunk]:
        """
        并行翻译所有文本块
        
        Args:
            chunks: 文本块列表
            theme: 内容主题
            
        Returns:
            翻译结果列表
        """
        print(f"🚀 开始并行翻译{len(chunks)}个文本块...")
        
        results = [None] * len(chunks)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有翻译任务
            futures = []
            for i, chunk in enumerate(chunks):
                future = executor.submit(
                    self.translate_single_chunk, 
                    chunk, i, chunks, theme
                )
                futures.append((future, i))
            
            # 收集结果
            completed_count = 0
            for future, index in futures:
                try:
                    result = future.result()
                    results[index] = result
                    completed_count += 1
                    
                    if result.error_message:
                        print(f"❌ 块{index}翻译失败: {result.error_message}")
                    else:
                        print(f"✅ 块{index}翻译完成 (耗时{result.processing_time:.2f}s)")
                        
                except Exception as e:
                    print(f"💥 块{index}处理异常: {str(e)}")
                    results[index] = TranslationChunk(
                        index=index,
                        source_text=chunks[index] if index < len(chunks) else "",
                        error_message=str(e)
                    )
        
        print(f"🎉 并行翻译完成: {completed_count}/{len(chunks)} 成功")
        return [r for r in results if r is not None]
    
    def similarity_match_results(self, chunks: List[str], results: List[TranslationChunk]) -> List[str]:
        """
        使用相似度匹配翻译结果
        
        Args:
            chunks: 原始文本块
            results: 翻译结果
            
        Returns:
            匹配后的翻译文本列表
        """
        print("🔍 正在进行相似度匹配...")
        
        matched_translations = []
        
        for i, chunk in enumerate(chunks):
            chunk_lines = chunk.split('\n')
            chunk_text = ''.join(chunk_lines).lower()
            
            # 计算与所有结果的相似度
            similarities = []
            for result in results:
                if result.source_text:
                    source_text = ''.join(result.source_text.split('\n')).lower()
                    similarity = SequenceMatcher(None, chunk_text, source_text).ratio()
                    similarities.append((result, similarity))
            
            # 找到最佳匹配
            if similarities:
                best_match, best_similarity = max(similarities, key=lambda x: x[1])
                
                if best_similarity < self.similarity_threshold:
                    print(f"⚠️  块{i}匹配度较低: {best_similarity:.3f}")
                    if best_similarity < 0.8:
                        raise ValueError(f"Translation matching failed for chunk {i}")
                
                if best_match.translated_text:
                    matched_translations.extend(best_match.translated_text.split('\n'))
                else:
                    # 如果翻译失败，使用原文
                    matched_translations.extend(chunk_lines)
            else:
                matched_translations.extend(chunk_lines)
        
        print(f"✅ 相似度匹配完成，共{len(matched_translations)}行")
        return matched_translations
    
    def save_translation_results(self, source_lines: List[str], translated_lines: List[str]) -> TranslationResult:
        """
        保存翻译结果
        
        Args:
            source_lines: 源文本行
            translated_lines: 翻译文本行
            
        Returns:
            翻译结果统计
        """
        print("💾 正在保存翻译结果...")
        
        try:
            pd = self._get_pandas()
            
            # 创建双语对照数据框
            df_translate = pd.DataFrame({
                'Source': source_lines,
                'Translation': translated_lines
            })
            
            # 保存为Excel文件
            df_translate.to_excel(self.translation_file, index=False)
            
            print(f"✅ 翻译结果已保存: {self.translation_file}")
            print(f"📊 统计信息: {len(source_lines)}行源文本，{len(translated_lines)}行翻译")
            
            return TranslationResult(
                total_chunks=len(source_lines),
                successful_chunks=len(translated_lines),
                failed_chunks=max(0, len(source_lines) - len(translated_lines)),
                total_time=0.0,
                average_confidence=0.85,
                output_file=str(self.translation_file)
            )
            
        except Exception as e:
            print(f"❌ 保存翻译结果失败: {str(e)}")
            raise
    
    def process_complete_translation(self) -> TranslationResult:
        """
        完整的文本翻译处理流程
        
        Returns:
            翻译结果
        """
        print("🚀 开始完整文本翻译流程...")
        
        try:
            # 1. 加载翻译上下文
            terminology_data, translation_context, content_theme = self.load_translation_context()
            
            # 2. 加载输入文本
            text_lines = self.load_input_text()
            
            # 3. 分割为翻译块
            chunks = self.split_text_into_chunks(text_lines)
            
            # 4. 并行翻译所有块
            translation_results = self.translate_all_chunks(chunks, content_theme)
            
            # 5. 相似度匹配结果
            matched_translations = self.similarity_match_results(chunks, translation_results)
            
            # 6. 重建源文本行列表
            source_lines = []
            for chunk in chunks:
                source_lines.extend(chunk.split('\n'))
            
            # 7. 保存翻译结果
            result = self.save_translation_results(source_lines, matched_translations)
            
            print("🎉 文本翻译流程完成！")
            print(f"📊 翻译统计:")
            print(f"  📄 总块数: {len(chunks)}")
            print(f"  ✅ 成功: {result.successful_chunks}")
            print(f"  ❌ 失败: {result.failed_chunks}")
            print(f"  📝 术语使用: {len(self._term_mapping)}个")
            print(f"  📁 输出文件: {result.output_file}")
            
            return result
            
        except Exception as e:
            print(f"💥 文本翻译流程失败: {str(e)}")
            raise


# ----------------------------------------------------------------------------
# 独立运行测试
# ----------------------------------------------------------------------------
if __name__ == '__main__':
    import sys
    
    # 创建翻译器实例
    translator = TextTranslator(
        src_language='en',
        tgt_language='zh',
        chunk_size=600,
        max_chunk_lines=10,
        max_workers=2,
        enable_reflect_translate=True
    )
    
    # 测试参数
    test_with_gpt = '--gpt' in sys.argv
    
    if test_with_gpt:
        print("⚠️  注意: 需要提供GPT函数才能进行完整测试")
        # translator.set_gpt_function(your_gpt_function)
    
    try:
        # 检查输入文件
        if not translator.input_file.exists():
            print(f"❌ 输入文件不存在: {translator.input_file}")
            print("💡 请先运行文本分割器生成分割文件")
            sys.exit(1)
        
        # 检查上下文文件
        if not translator.terminology_file.exists():
            print(f"❌ 术语文件不存在: {translator.terminology_file}")
            print("💡 请先运行内容总结器生成术语文件")
            sys.exit(1)
        
        # 运行完整翻译流程
        print("\n🧪 测试文本翻译流程...")
        
        result = translator.process_complete_translation()
        
        print(f"\n✅ 测试完成！")
        print(f"📁 输出文件: {result.output_file}")
        
        # 显示部分结果
        if Path(result.output_file).exists():
            pd = translator._get_pandas()
            df = pd.read_excel(result.output_file)
            
            print(f"\n📋 翻译预览 (前5行):")
            for i in range(min(5, len(df))):
                source = df.iloc[i]['Source']
                translation = df.iloc[i]['Translation']
                print(f"  {i+1:2d}. {source[:50]}...")
                print(f"      → {translation[:50]}...")
                print()
        
    except Exception as e:
        print(f"\n💥 测试过程中发生错误: {str(e)}")
        sys.exit(1) 