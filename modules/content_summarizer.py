"""
# ----------------------------------------------------------------------------
# 内容总结器模块 - 整个翻译流程的核心桥梁
# 
# 核心功能：
# 1. 视频内容主题总结和理解
# 2. 专业术语智能识别和提取
# 3. 翻译上下文信息构建
# 4. 术语一致性管理系统
# 5. 自定义术语库集成管理
# 
# 输入：分割后的文本文件，自定义术语表
# 输出：主题总结JSON，术语字典JSON，翻译上下文信息
# 
# 设计原则：
# - 确保翻译质量的一致性和准确性
# - 支持多语言和领域自适应
# - 提供丰富的上下文信息支撑后续翻译
# - 智能术语管理和冲突解决
# ----------------------------------------------------------------------------
"""

import os
import json
import hashlib
from typing import List, Dict, Optional, Callable, Set, Tuple
from pathlib import Path
import concurrent.futures
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter
import re


@dataclass
class Term:
    """术语数据类"""
    src: str                 # 源语言术语
    tgt: str                 # 目标语言翻译
    note: str                # 术语说明
    confidence: float = 1.0  # 置信度
    category: str = ""       # 术语类别
    frequency: int = 1       # 出现频率
    context: List[str] = None # 上下文示例
    
    def __post_init__(self):
        if self.context is None:
            self.context = []


@dataclass  
class ContentSummary:
    """内容总结数据类"""
    theme: str                    # 主题总结
    domain: str = ""             # 领域分类
    style: str = ""              # 内容风格
    target_audience: str = ""    # 目标受众
    key_concepts: List[str] = None # 关键概念
    complexity_level: str = ""   # 内容复杂度
    
    def __post_init__(self):
        if self.key_concepts is None:
            self.key_concepts = []


class ContentSummarizer:
    """内容总结器类 - 翻译流程的核心桥梁"""
    
    def __init__(self,
                 input_file: str = 'output/log/3_2_split_by_meaning.txt',
                 custom_terms_file: str = 'custom_terms.xlsx',
                 output_dir: str = 'output/log',
                 src_language: str = 'en',
                 tgt_language: str = 'zh',
                 summary_length: int = 5000,
                 max_terms: int = 30,
                 min_term_frequency: int = 2,
                 max_workers: int = 4):
        """
        初始化内容总结器
        
        Args:
            input_file: 输入的分割文本文件
            custom_terms_file: 自定义术语表文件
            output_dir: 输出目录
            src_language: 源语言代码
            tgt_language: 目标语言代码
            summary_length: 用于总结的文本长度限制
            max_terms: 最大术语提取数量
            min_term_frequency: 术语最小频率阈值
            max_workers: 并行处理的最大线程数
        """
        self.input_file = Path(input_file)
        self.custom_terms_file = Path(custom_terms_file)
        self.output_dir = Path(output_dir)
        self.src_language = src_language
        self.tgt_language = tgt_language
        self.summary_length = summary_length
        self.max_terms = max_terms
        self.min_term_frequency = min_term_frequency
        self.max_workers = max_workers
        
        # 创建输出目录
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 文件路径配置
        self.summary_file = self.output_dir / '4_1_content_summary.json'
        self.terminology_file = self.output_dir / '4_1_terminology.json'
        self.context_file = self.output_dir / '4_1_translation_context.json'
        self.cache_file = self.output_dir / '4_1_summary_cache.json'
        
        # 领域关键词配置（用于自动领域识别）
        self.domain_keywords = {
            'technology': ['technology', 'software', 'algorithm', 'AI', 'machine learning', 'data', 'programming', 'system', 'network'],
            'medicine': ['medical', 'health', 'disease', 'treatment', 'patient', 'diagnosis', 'medicine', 'therapy', 'clinical'],
            'business': ['business', 'market', 'financial', 'economy', 'investment', 'company', 'strategy', 'management', 'revenue'],
            'education': ['education', 'learning', 'student', 'teacher', 'school', 'university', 'course', 'academic', 'study'],
            'science': ['science', 'research', 'experiment', 'theory', 'analysis', 'study', 'data', 'method', 'result'],
            'entertainment': ['movie', 'music', 'game', 'entertainment', 'show', 'performance', 'art', 'culture', 'story']
        }
        
        # 懒加载依赖
        self._pd = None
        self._ask_gpt_func = None
        
        # 内部状态
        self._content_cache = {}
        self._custom_terms = []
        self._extracted_terms = []
        
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
    
    def _calculate_content_hash(self, content: str) -> str:
        """计算内容哈希，用于缓存"""
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def load_input_content(self) -> str:
        """
        加载并预处理输入内容
        
        Returns:
            处理后的文本内容
        """
        print(f"📖 正在加载分割文本: {self.input_file}")
        
        if not self.input_file.exists():
            raise FileNotFoundError(f"❌ 分割文本文件不存在: {self.input_file}")
        
        try:
            with open(self.input_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # 清理和合并文本
            cleaned_lines = [line.strip() for line in lines if line.strip()]
            combined_text = ' '.join(cleaned_lines)
            
            # 限制总结长度，避免超出GPT限制
            if len(combined_text) > self.summary_length:
                print(f"📏 文本长度超限，截取前{self.summary_length}个字符")
                combined_text = combined_text[:self.summary_length]
            
            print(f"✅ 加载了{len(cleaned_lines)}行文本，共{len(combined_text)}个字符")
            return combined_text
            
        except Exception as e:
            print(f"❌ 加载分割文本失败: {str(e)}")
            raise
    
    def load_custom_terms(self) -> List[Term]:
        """
        加载自定义术语表
        
        Returns:
            自定义术语列表
        """
        print(f"📚 正在加载自定义术语表...")
        
        custom_terms = []
        
        if not self.custom_terms_file.exists():
            print(f"⚠️  自定义术语表文件不存在: {self.custom_terms_file}")
            return custom_terms
        
        try:
            pd = self._get_pandas()
            df = pd.read_excel(self.custom_terms_file)
            
            # 假设Excel格式为: 源术语 | 目标翻译 | 说明
            for _, row in df.iterrows():
                if len(row) >= 3 and pd.notna(row.iloc[0]):
                    term = Term(
                        src=str(row.iloc[0]).strip(),
                        tgt=str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else "",
                        note=str(row.iloc[2]).strip() if pd.notna(row.iloc[2]) else "",
                        confidence=1.0,  # 自定义术语置信度最高
                        category="custom"
                    )
                    custom_terms.append(term)
            
            print(f"✅ 加载了{len(custom_terms)}个自定义术语")
            return custom_terms
            
        except Exception as e:
            print(f"❌ 加载自定义术语表失败: {str(e)}")
            return custom_terms
    
    def _detect_domain_and_style(self, content: str) -> Tuple[str, str, str]:
        """
        检测内容领域、风格和目标受众
        
        Args:
            content: 文本内容
            
        Returns:
            (领域, 风格, 目标受众)
        """
        content_lower = content.lower()
        
        # 领域检测
        domain_scores = {}
        for domain, keywords in self.domain_keywords.items():
            score = sum(content_lower.count(keyword) for keyword in keywords)
            domain_scores[domain] = score
        
        detected_domain = max(domain_scores, key=domain_scores.get) if max(domain_scores.values()) > 0 else "general"
        
        # 风格检测（基于简单启发式）
        if any(word in content_lower for word in ['tutorial', 'how to', 'step', 'guide']):
            style = "tutorial"
        elif any(word in content_lower for word in ['analysis', 'research', 'study', 'data']):
            style = "analytical"
        elif any(word in content_lower for word in ['news', 'report', 'today', 'recent']):
            style = "news"
        else:
            style = "general"
        
        # 目标受众检测
        if detected_domain in ['technology', 'science']:
            audience = "technical"
        elif detected_domain in ['education']:
            audience = "educational"
        elif detected_domain in ['business']:
            audience = "professional"
        else:
            audience = "general"
        
        return detected_domain, style, audience
    
    def generate_content_summary(self, content: str, custom_terms: List[Term]) -> ContentSummary:
        """
        生成内容总结
        
        Args:
            content: 文本内容
            custom_terms: 自定义术语列表
            
        Returns:
            内容总结对象
        """
        print("🧠 正在生成内容总结...")
        
        if self._ask_gpt_func is None:
            print("⚠️  未设置GPT函数，使用默认总结")
            domain, style, audience = self._detect_domain_and_style(content)
            return ContentSummary(
                theme=f"这是一个关于{domain}领域的{style}内容，主要面向{audience}受众。",
                domain=domain,
                style=style,
                target_audience=audience,
                key_concepts=[],
                complexity_level="medium"
            )
        
        try:
            # 构建总结提示词
            summary_prompt = self._get_summary_prompt(content, custom_terms)
            
            # 调用GPT生成总结
            response = self._ask_gpt_func(
                summary_prompt,
                resp_type='json',
                log_title='content_summary',
                valid_def=self._validate_summary_response
            )
            
            # 解析响应
            theme = response.get('theme', '')
            domain, style, audience = self._detect_domain_and_style(content)
            
            summary = ContentSummary(
                theme=theme,
                domain=response.get('domain', domain),
                style=response.get('style', style),
                target_audience=response.get('target_audience', audience),
                key_concepts=response.get('key_concepts', []),
                complexity_level=response.get('complexity_level', 'medium')
            )
            
            print(f"✅ 内容总结生成完成")
            return summary
            
        except Exception as e:
            print(f"❌ 内容总结生成失败: {str(e)}")
            # 回退到基础总结
            domain, style, audience = self._detect_domain_and_style(content)
            return ContentSummary(
                theme="视频内容总结生成失败，将使用基础分析结果。",
                domain=domain,
                style=style,
                target_audience=audience
            )
    
    def _get_summary_prompt(self, content: str, custom_terms: List[Term]) -> str:
        """生成总结提示词"""
        
        # 构建自定义术语提示
        terms_note = ""
        if custom_terms:
            terms_list = [f"- {term.src}: {term.tgt} ({term.note})" for term in custom_terms]
            terms_note = f"\n### Existing Terms\nPlease consider these existing terms:\n" + "\n".join(terms_list)
        
        return f"""
## Role
You are a professional video content analyst and translation consultant, specializing in {self.src_language} comprehension and {self.tgt_language} localization strategy.

## Task
Analyze the provided {self.src_language} video content and generate a comprehensive summary for translation optimization:

1. **Content Theme**: Write 2-3 sentences summarizing the main topic and key points
2. **Domain Classification**: Identify the content domain (technology/medicine/business/education/science/entertainment/general)
3. **Content Style**: Determine the presentation style (tutorial/analytical/news/documentary/entertainment/general)
4. **Target Audience**: Identify the intended audience (technical/educational/professional/general)
5. **Key Concepts**: Extract 5-8 most important concepts or themes
6. **Complexity Level**: Assess content complexity (beginner/intermediate/advanced)

{terms_note}

## Guidelines
- Focus on information that will help translators understand context and maintain consistency
- Consider cultural adaptation needs for {self.tgt_language} audience
- Identify any domain-specific language patterns or terminology requirements

## INPUT
<content>
{content}
</content>

## Output in only JSON format and no other text
```json
{{
    "theme": "2-3 sentence comprehensive summary of the video content",
    "domain": "technology|medicine|business|education|science|entertainment|general",
    "style": "tutorial|analytical|news|documentary|entertainment|general",
    "target_audience": "technical|educational|professional|general",
    "key_concepts": ["concept1", "concept2", "concept3"],
    "complexity_level": "beginner|intermediate|advanced"
}}
```

Note: Start your answer with ```json and end with ```, do not add any other text.
""".strip()
    
    def extract_terminology(self, content: str, custom_terms: List[Term]) -> List[Term]:
        """
        提取专业术语
        
        Args:
            content: 文本内容
            custom_terms: 自定义术语列表
            
        Returns:
            提取的术语列表
        """
        print("🔍 正在提取专业术语...")
        
        if self._ask_gpt_func is None:
            print("⚠️  未设置GPT函数，使用基础术语提取")
            return self._extract_terms_fallback(content, custom_terms)
        
        try:
            # 构建术语提取提示词
            terminology_prompt = self._get_terminology_prompt(content, custom_terms)
            
            # 调用GPT提取术语
            response = self._ask_gpt_func(
                terminology_prompt,
                resp_type='json',
                log_title='terminology_extraction',
                valid_def=self._validate_terminology_response
            )
            
            # 解析术语
            extracted_terms = []
            for term_data in response.get('terms', []):
                term = Term(
                    src=term_data.get('src', ''),
                    tgt=term_data.get('tgt', ''),
                    note=term_data.get('note', ''),
                    confidence=term_data.get('confidence', 0.8),
                    category=term_data.get('category', 'extracted'),
                    frequency=self._count_term_frequency(term_data.get('src', ''), content)
                )
                extracted_terms.append(term)
            
            # 合并自定义术语和提取术语
            all_terms = custom_terms + extracted_terms
            
            # 去重和优化
            unique_terms = self._deduplicate_terms(all_terms)
            
            print(f"✅ 术语提取完成，共{len(unique_terms)}个术语")
            return unique_terms
            
        except Exception as e:
            print(f"❌ 术语提取失败: {str(e)}")
            return self._extract_terms_fallback(content, custom_terms)
    
    def _get_terminology_prompt(self, content: str, custom_terms: List[Term]) -> str:
        """生成术语提取提示词"""
        
        # 构建排除术语列表
        exclude_terms = [term.src for term in custom_terms]
        exclude_note = ""
        if exclude_terms:
            exclude_note = f"\n### Exclude These Terms\nDo not extract these terms as they are already defined:\n{', '.join(exclude_terms)}"
        
        return f"""
## Role
You are a professional terminology expert specializing in {self.src_language} to {self.tgt_language} translation, with deep understanding of domain-specific terminology.

## Task
Extract and translate professional terms from the provided {self.src_language} content:

1. **Identify Terms**: Find technical terms, proper nouns, concepts, and domain-specific vocabulary
2. **Provide Translations**: Give accurate {self.tgt_language} translations or keep original if appropriate
3. **Add Explanations**: Brief explanations to help translators understand context and usage
4. **Categorize Terms**: Classify terms by type (technical/proper_noun/concept/acronym/general)
5. **Assess Confidence**: Rate translation confidence (0.6-1.0)

{exclude_note}

## Extraction Guidelines
- Focus on terms that appear multiple times or are central to understanding
- Include acronyms, technical jargon, and specialized vocabulary
- Prioritize terms that might be difficult for general translators
- Extract no more than {self.max_terms} terms
- Ensure translations are contextually appropriate

## INPUT
<content>
{content}
</content>

## Output in only JSON format and no other text
```json
{{
    "terms": [
        {{
            "src": "{self.src_language} term or phrase",
            "tgt": "{self.tgt_language} translation or original if appropriate",
            "note": "Brief explanation of meaning and usage context",
            "category": "technical|proper_noun|concept|acronym|general",
            "confidence": 0.8
        }}
    ]
}}
```

Note: Start your answer with ```json and end with ```, do not add any other text.
""".strip()
    
    def _extract_terms_fallback(self, content: str, custom_terms: List[Term]) -> List[Term]:
        """术语提取的备用方案"""
        print("📝 使用基础术语提取...")
        
        # 简单的启发式术语提取
        terms = custom_terms.copy()
        
        # 提取大写单词和缩写
        uppercase_pattern = r'\b[A-Z]{2,}\b'
        acronyms = re.findall(uppercase_pattern, content)
        
        # 提取常见术语模式
        term_patterns = [
            r'\b[A-Z][a-z]+ [A-Z][a-z]+\b',  # 专有名词
            r'\b\w+ing\b',                    # 技术动作
            r'\b\w+tion\b',                   # 概念名词
        ]
        
        all_candidates = set(acronyms)
        for pattern in term_patterns:
            candidates = re.findall(pattern, content)
            all_candidates.update(candidates)
        
        # 转换为Term对象
        for candidate in list(all_candidates)[:self.max_terms//2]:
            if len(candidate) > 2 and candidate.lower() not in [t.src.lower() for t in terms]:
                term = Term(
                    src=candidate,
                    tgt=candidate,  # 保持原文
                    note=f"Automatically extracted term",
                    confidence=0.6,
                    category="extracted",
                    frequency=content.lower().count(candidate.lower())
                )
                terms.append(term)
        
        return terms
    
    def _count_term_frequency(self, term: str, content: str) -> int:
        """计算术语在内容中的频率"""
        return content.lower().count(term.lower())
    
    def _deduplicate_terms(self, terms: List[Term]) -> List[Term]:
        """去重和优化术语列表"""
        # 按源术语去重，保留置信度最高的
        unique_terms = {}
        for term in terms:
            key = term.src.lower()
            if key not in unique_terms or term.confidence > unique_terms[key].confidence:
                unique_terms[key] = term
        
        # 排序：自定义术语优先，然后按频率和置信度
        sorted_terms = sorted(
            unique_terms.values(),
            key=lambda t: (t.category == "custom", t.frequency, t.confidence),
            reverse=True
        )
        
        return sorted_terms[:self.max_terms]
    
    def generate_translation_context(self, 
                                   summary: ContentSummary, 
                                   terms: List[Term]) -> Dict:
        """
        生成翻译上下文信息
        
        Args:
            summary: 内容总结
            terms: 术语列表
            
        Returns:
            翻译上下文字典
        """
        print("🔗 正在生成翻译上下文...")
        
        # 构建术语字典（用于快速查询）
        term_dict = {term.src.lower(): term for term in terms}
        
        # 按类别分组术语
        terms_by_category = defaultdict(list)
        for term in terms:
            terms_by_category[term.category].append(term)
        
        # 生成翻译指导
        translation_guidelines = self._generate_translation_guidelines(summary, terms)
        
        context = {
            "content_summary": asdict(summary),
            "terminology": {
                "total_terms": len(terms),
                "by_category": {cat: len(terms) for cat, terms in terms_by_category.items()},
                "high_priority": [asdict(t) for t in terms if t.confidence > 0.8 or t.category == "custom"],
                "all_terms": [asdict(t) for t in terms]
            },
            "translation_guidelines": translation_guidelines,
            "quick_reference": {
                term.src: {"tgt": term.tgt, "note": term.note} 
                for term in terms if term.confidence > 0.7
            },
            "metadata": {
                "src_language": self.src_language,
                "tgt_language": self.tgt_language,
                "generation_time": self._get_timestamp(),
                "content_hash": self._calculate_content_hash(str(summary) + str(terms))
            }
        }
        
        print(f"✅ 翻译上下文生成完成")
        return context
    
    def _generate_translation_guidelines(self, summary: ContentSummary, terms: List[Term]) -> Dict:
        """生成翻译指导原则"""
        guidelines = {
            "domain_specific": {
                "domain": summary.domain,
                "terminology_density": "high" if len(terms) > 20 else "medium" if len(terms) > 10 else "low",
                "technical_level": summary.complexity_level
            },
            "style_adaptation": {
                "source_style": summary.style,
                "target_audience": summary.target_audience,
                "formality_level": "formal" if summary.target_audience in ["technical", "professional"] else "casual"
            },
            "consistency_rules": {
                "maintain_terminology": [t.src for t in terms if t.category in ["custom", "technical"]],
                "cultural_adaptation": summary.domain in ["entertainment", "education"],
                "preserve_names": [t.src for t in terms if t.category == "proper_noun"]
            }
        }
        return guidelines
    
    def _get_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def save_results(self, 
                    summary: ContentSummary, 
                    terms: List[Term], 
                    context: Dict) -> Tuple[str, str, str]:
        """
        保存所有结果
        
        Args:
            summary: 内容总结
            terms: 术语列表
            context: 翻译上下文
            
        Returns:
            (总结文件路径, 术语文件路径, 上下文文件路径)
        """
        print("💾 正在保存结果...")
        
        try:
            # 保存内容总结
            with open(self.summary_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(summary), f, ensure_ascii=False, indent=2)
            
            # 保存术语信息（兼容原格式）
            terminology_data = {
                "theme": summary.theme,
                "terms": [asdict(term) for term in terms]
            }
            with open(self.terminology_file, 'w', encoding='utf-8') as f:
                json.dump(terminology_data, f, ensure_ascii=False, indent=2)
            
            # 保存翻译上下文
            with open(self.context_file, 'w', encoding='utf-8') as f:
                json.dump(context, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 结果保存完成")
            print(f"  📄 内容总结: {self.summary_file}")
            print(f"  📚 术语信息: {self.terminology_file}")
            print(f"  🔗 翻译上下文: {self.context_file}")
            
            return str(self.summary_file), str(self.terminology_file), str(self.context_file)
            
        except Exception as e:
            print(f"❌ 保存结果失败: {str(e)}")
            raise
    
    def _validate_summary_response(self, response_data: Dict) -> Dict:
        """验证总结响应格式"""
        if not isinstance(response_data, dict):
            return {"status": "error", "message": "Response must be a dictionary"}
        
        required_fields = ['theme']
        for field in required_fields:
            if field not in response_data:
                return {"status": "error", "message": f"Missing required field: {field}"}
        
        return {"status": "success", "message": "Summary validation passed"}
    
    def _validate_terminology_response(self, response_data: Dict) -> Dict:
        """验证术语响应格式"""
        if not isinstance(response_data, dict):
            return {"status": "error", "message": "Response must be a dictionary"}
        
        if 'terms' not in response_data:
            return {"status": "error", "message": "Missing 'terms' field"}
        
        required_term_keys = {'src', 'tgt', 'note'}
        for term in response_data['terms']:
            if not all(key in term for key in required_term_keys):
                return {"status": "error", "message": "Invalid term format"}
        
        return {"status": "success", "message": "Terminology validation passed"}
    
    def process_complete_summarization(self) -> Tuple[str, str, str]:
        """
        完整的内容总结处理流程
        
        Returns:
            (总结文件路径, 术语文件路径, 上下文文件路径)
        """
        print("🚀 开始完整内容总结流程...")
        
        try:
            # 1. 加载输入内容和自定义术语
            content = self.load_input_content()
            custom_terms = self.load_custom_terms()
            
            # 2. 生成内容总结
            summary = self.generate_content_summary(content, custom_terms)
            
            # 3. 提取术语
            terms = self.extract_terminology(content, custom_terms)
            
            # 4. 生成翻译上下文
            context = self.generate_translation_context(summary, terms)
            
            # 5. 保存结果
            file_paths = self.save_results(summary, terms, context)
            
            print("🎉 内容总结流程完成！")
            print(f"📊 总结统计:")
            print(f"  🎯 主题: {summary.theme[:100]}...")
            print(f"  🏷️  领域: {summary.domain}")
            print(f"  📝 风格: {summary.style}")
            print(f"  👥 受众: {summary.target_audience}")
            print(f"  📚 术语数量: {len(terms)}")
            print(f"  🔗 上下文信息: {len(context)} 项")
            
            return file_paths
            
        except Exception as e:
            print(f"💥 内容总结流程失败: {str(e)}")
            raise


# ----------------------------------------------------------------------------
# 独立运行测试
# ----------------------------------------------------------------------------
if __name__ == '__main__':
    import sys
    
    # 创建总结器实例
    summarizer = ContentSummarizer(
        src_language='en',
        tgt_language='zh',
        summary_length=5000,
        max_terms=25
    )
    
    # 测试参数
    test_with_gpt = '--gpt' in sys.argv
    
    if test_with_gpt:
        print("⚠️  注意: 需要提供GPT函数才能进行完整测试")
        # summarizer.set_gpt_function(your_gpt_function)
    
    try:
        # 检查输入文件
        if not summarizer.input_file.exists():
            print(f"❌ 输入文件不存在: {summarizer.input_file}")
            print("💡 请先运行文本分割器生成分割文件")
            sys.exit(1)
        
        # 运行完整总结流程
        print("\n🧪 测试内容总结流程...")
        
        file_paths = summarizer.process_complete_summarization()
        
        print(f"\n✅ 测试完成！")
        print(f"📁 生成文件:")
        for i, path in enumerate(file_paths, 1):
            print(f"  {i}. {path}")
        
        # 显示部分结果
        if Path(file_paths[1]).exists():  # 术语文件
            with open(file_paths[1], 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            print(f"\n📋 术语预览 (前5个):")
            for i, term in enumerate(data.get('terms', [])[:5], 1):
                print(f"  {i}. {term.get('src', '')} → {term.get('tgt', '')} ({term.get('note', '')})")
        
    except Exception as e:
        print(f"\n💥 测试过程中发生错误: {str(e)}")
        sys.exit(1) 