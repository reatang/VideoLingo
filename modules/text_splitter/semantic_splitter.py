"""
# ----------------------------------------------------------------------------
# 语义文本分割器
# 
# 基于GPT的智能语义分割：
# 1. 分析句子结构和复杂度
# 2. 生成多种分割方案并比较
# 3. 选择最佳分割点
# 4. 同步处理确保稳定性
# ----------------------------------------------------------------------------
"""

import math
from pathlib import Path
from typing import List, Optional
from difflib import SequenceMatcher

from modules.gpt import ask_gpt
from modules.config import get_config_manager
from modules.common_utils import paths


class SemanticSplitter:
    """基于语义的文本分割器"""
    
    def __init__(self, 
                 output_dir: str = "output",
                 max_split_length: int = 20,
                 retry_attempts: int = 3):
        """
        初始化语义分割器
        
        Args:
            output_dir: 输出目录
            max_split_length: 最大分割长度
            retry_attempts: 重试次数
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        self.max_split_length = max_split_length
        self.retry_attempts = retry_attempts
        
        # 获取配置管理器
        try:
            self.config = get_config_manager()
            self.language = self._get_language()
            self.joiner = self._get_joiner()
        except Exception as e:
            print(f"⚠️  配置管理器初始化失败: {e}")
            self.language = "auto"
            self.joiner = " "
    
    def _get_language(self) -> str:
        """获取检测到的语言"""
        try:
            whisper_language = self.config.load_key("whisper.language", "auto")
            if whisper_language == 'auto':
                return self.config.load_key("whisper.detected_language", "English")
            return whisper_language
        except:
            return "English"
    
    def _get_joiner(self) -> str:
        """获取语言对应的连接符"""
        try:
            # 无空格语言列表
            no_space_langs = self.config.load_key("language_split_without_space", [])
            if any(lang.lower() in self.language.lower() for lang in no_space_langs):
                return ""
            return " "
        except:
            return " "
    
    def _get_split_prompt(self, sentence: str, num_parts: int = 2, word_limit: int = 20) -> str:
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
                print(f"⚠️  低相似度分割点: {max_similarity}")
            
            if best_split is not None:
                split_positions.append(best_split)
                start = best_split
            else:
                print(f"⚠️  无法找到第{i+1}部分的合适分割点")
        
        return split_positions
    
    def _split_sentence(self, sentence: str, num_parts: int, 
                       word_limit: int = 20, index: int = -1) -> str:
        """使用GPT分割单个句子"""
        
        def valid_split(response_data):
            choice = response_data.get("choice", "1")
            split_key = f'split{choice}'
            if split_key not in response_data:
                return {"status": "error", "message": "Missing required key: `split`"}
            if "[br]" not in response_data[split_key]:
                return {"status": "error", "message": "Split failed, no [br] found"}
            return {"status": "success", "message": "Split completed"}
        
        # 多次重试
        for retry_attempt in range(self.retry_attempts):
            try:
                split_prompt = self._get_split_prompt(sentence, num_parts, word_limit)
                
                # 添加重试的随机性
                prompt_with_retry = split_prompt + " " * retry_attempt
                
                response_data = ask_gpt(
                    prompt_with_retry, 
                    resp_type='json', 
                    valid_def=valid_split, 
                    log_title='semantic_split',
                    cache_dir=self.output_dir / "gpt_log"
                )
                
                choice = response_data.get("choice", "1")
                best_split = response_data[f"split{choice}"]
                
                # 找到分割位置
                split_points = self._find_split_positions(sentence, best_split)
                
                # 根据分割点分割句子
                result = sentence
                for i, split_point in enumerate(split_points):
                    if i == 0:
                        result = sentence[:split_point] + '\n' + sentence[split_point:]
                    else:
                        parts = result.split('\n')
                        last_part = parts[-1]
                        split_in_last = split_point - split_points[i-1]
                        parts[-1] = last_part[:split_in_last] + '\n' + last_part[split_in_last:]
                        result = '\n'.join(parts)
                
                if index != -1:
                    print(f"✅ 句子 {index} 成功分割")
                    print(f"   原句: {sentence[:50]}{'...' if len(sentence) > 50 else ''}")
                    print(f"   分割: {result.replace(chr(10), ' ||')}")
                
                return result
                
            except Exception as e:
                print(f"⚠️  句子分割失败 (index={index}, 重试{retry_attempt+1}/{self.retry_attempts}): {str(e)}")
                if retry_attempt == self.retry_attempts - 1:
                    # 最后一次重试失败，返回原句
                    print(f"❌ 句子 {index} 分割最终失败，使用原句")
                    return sentence
        
        return sentence
    
    def _tokenize_sentence(self, sentence: str) -> List[str]:
        """简单的分词函数"""
        # 对于无空格语言，按字符分割；有空格语言按单词分割
        if not self.joiner:  # 无空格语言
            return list(sentence.strip())
        else:  # 有空格语言
            return sentence.strip().split()
    
    def _process_sentences_sync(self, sentences: List[str]) -> List[str]:
        """同步分割句子"""
        new_sentences = []
        
        for index, sentence in enumerate(sentences):
            tokens = self._tokenize_sentence(sentence)
            
            # 检查是否需要分割
            if len(tokens) > self.max_split_length:
                num_parts = math.ceil(len(tokens) / self.max_split_length)
                print(f"🔄 处理句子 {index}: {len(tokens)} 个词 -> 分割为 {num_parts} 部分")
                
                split_result = self._split_sentence(
                    sentence, 
                    num_parts, 
                    self.max_split_length, 
                    index
                )
                
                if split_result and '\n' in split_result:
                    split_lines = split_result.strip().split('\n')
                    for line in split_lines:
                        if line.strip():
                            new_sentences.append(line.strip())
                else:
                    new_sentences.append(sentence)
            else:
                new_sentences.append(sentence)
        
        return new_sentences
    
    def split_sentences(self, sentences: List[str]) -> List[str]:
        """分割句子列表"""
        print(f"🤖 开始语义分割 {len(sentences)} 个句子")
        print(f"   最大分割长度: {self.max_split_length}")
        print(f"   语言: {self.language}")
        print(f"   处理模式: 同步处理")
        
        # 同步处理所有句子
        result_sentences = self._process_sentences_sync(sentences)
        
        print(f"✅ 语义分割完成: {len(sentences)} -> {len(result_sentences)}")
        return result_sentences
    
    def cleanup(self):
        """清理资源"""
        try:
            # 清理GPT全局客户端
            from modules.gpt import cleanup_global_client
            cleanup_global_client()
        except Exception as e:
            print(f"⚠️  清理GPT客户端时出错: {e}")
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口，确保资源清理"""
        self.cleanup()
        return False
    
    def split_file(self, input_file: str, output_file: str = None) -> str:
        """分割文件中的句子"""
        print("🤖 开始语义文本分割...")
        
        # 确保输入文件路径正确
        input_file = paths.get_filepath_by_default(input_file, self.output_dir)
        
        # 读取输入文件
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                sentences = [line.strip() for line in f.readlines() if line.strip()]
        except Exception as e:
            raise FileNotFoundError(f"❌ 无法读取输入文件 {input_file}: {str(e)}")
        
        # 执行分割
        split_sentences = self.split_sentences(sentences)
        
        # 保存结果
        if not output_file:
            output_file = paths.get_filepath_by_default("split_by_meaning.txt", self.output_dir)
        else:
            output_file = paths.get_filepath_by_default(output_file, output_base_dir=self.output_dir)
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                for sentence in split_sentences:
                    f.write(sentence + '\n')
        except Exception as e:
            raise RuntimeError(f"❌ 无法保存结果文件 {output_file}: {str(e)}")
        
        print("✅ 语义分割完成！")
        print(f"📁 输出文件: {output_file}")
        print(f"📊 分割统计: {len(sentences)} -> {len(split_sentences)} 个句子")
        
        return str(output_file)


# ----------------------------------------------------------------------------
# 独立运行测试
# ----------------------------------------------------------------------------
if __name__ == '__main__':
    import sys
    
    # 测试语义分割器
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        input_file = "output/split_by_nlp.txt"
    
    try:
        splitter = SemanticSplitter()
        result_file = splitter.split_file(input_file)
        print(f"✅ 测试完成！结果文件: {result_file}")
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc() 