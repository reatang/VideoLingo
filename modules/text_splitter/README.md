# 文本分割模块 (Text Splitter Module)

## 🎯 模块概述

本模块对原有的 `_3_1_split_nlp.py` 和 `_3_2_split_meaning.py` 进行了全面重构，采用现代化的面向对象设计模式，提供了三种不同层次的文本分割解决方案。

## 🏗️ 架构设计

### 核心组件

```
modules/text_splitter/
├── __init__.py              # 主要API入口
├── nlp_splitter.py          # NLP分割器 (基于spaCy)
├── semantic_splitter.py     # 语义分割器 (基于GPT)
├── hybrid_splitter.py       # 混合分割器 (NLP+GPT)
├── split_spacy/            # 重构后的spaCy分割器
│   ├── core/               # 核心功能
│   └── strategies/         # 分割策略
└── README.md               # 本文档
```

### 设计原则

1. **单一职责** - 每个分割器专注于特定的分割策略
2. **依赖注入** - 通过配置管理器获取配置，支持灵活配置
3. **可组合性** - 可以单独使用任一分割器，或组合使用
4. **错误处理** - 完善的异常处理和错误恢复机制
5. **性能优化** - 并发处理、缓存机制、资源管理

## 📚 核心API

### 1. 一键分割API (推荐)

```python
from modules.text_splitter import split_text_complete

# 最简单的使用方式
result_file = split_text_complete(
    input_file="log/cleaned_chunks.xlsx",
    output_dir="output",
    use_semantic_split=True,  # 是否使用语义分割
    max_split_length=20,      # 最大分割长度
    max_workers=4             # 并发数
)
```

### 2. NLP分割器

基于spaCy的多层语法分割策略：

```python
from modules.text_splitter import NLPSplitter

splitter = NLPSplitter(
    output_dir="output",
    enable_all_strategies=True,    # 启用所有策略
    max_sentence_length=60,        # 最大句子长度
    min_sentence_length=3          # 最小句子长度
)

# 处理文件
result_file = splitter.split_file("log/cleaned_chunks.xlsx")

# 处理句子列表
sentences = ["Long sentence 1...", "Long sentence 2..."]
split_sentences = splitter.split_sentences(sentences)
```

**NLP分割策略：**
1. 标点符号分割 (句号、问号、感叹号等)
2. 逗号分割 (语法分析确保有效分割)
3. 连接词分割 (and, but, because等)
4. 长句根分割 (基于依赖关系的智能分割)

### 3. 语义分割器

基于GPT的智能语义理解分割：

```python
from modules.text_splitter import SemanticSplitter

# 推荐：使用上下文管理器确保资源清理
with SemanticSplitter(
    output_dir="output",
    max_split_length=20,    # 最大分割长度
    max_workers=4,          # 并发数
    retry_attempts=3        # 重试次数
) as splitter:
    # 处理文件
    result_file = splitter.split_file("input.txt")
    
    # 处理句子列表
    split_sentences = splitter.split_sentences(sentences)

# 或者传统方式（不推荐，可能有资源清理问题）
splitter = SemanticSplitter(max_split_length=20)
result_file = splitter.split_file("input.txt")
splitter.cleanup()  # 手动清理
```

**语义分割特点：**
- 理解句子结构和语义
- 生成多种分割方案并比较
- 选择最佳分割点
- 支持多语言处理
- 并发处理提高效率

### 4. 混合分割器

结合NLP和语义分割的完整流程：

```python
from modules.text_splitter import HybridSplitter

# 推荐：使用上下文管理器确保资源清理
with HybridSplitter(
    output_dir="output",
    max_split_length=20,           # 语义分割最大长度
    max_workers=4,                 # 语义分割并发数
    keep_intermediate_files=False  # 是否保留中间文件
) as splitter:
    # 完整的两阶段分割
    result_file = splitter.split_file("log/cleaned_chunks.xlsx")
```

**混合分割流程：**
1. **第一阶段：NLP分割** - 基于语法规则的快速分割
2. **第二阶段：语义分割** - 基于语义理解的精确分割
3. **结果整合** - 统一输出格式和统计信息

## 🔧 配置集成

模块完全集成了重构后的配置系统：

```python
from modules.config import get_config_manager

config = get_config_manager()

# 自动获取语言配置
language = config.load_key("whisper.detected_language", "English")
max_split_length = config.load_key("max_split_length", 20)
max_workers = config.load_key("max_workers", 4)
```

支持的配置项：
- `whisper.detected_language` - 检测到的语言
- `max_split_length` - 最大分割长度
- `max_workers` - 最大并发数
- `language_split_with_space` - 有空格语言列表
- `language_split_without_space` - 无空格语言列表

## 🎯 使用场景

### 场景1：快速NLP分割
适用于对精度要求不高，但需要快速处理的场景：

```python
from modules.text_splitter import NLPSplitter

splitter = NLPSplitter()
result = splitter.split_file("input.xlsx")
```

### 场景2：高精度语义分割
适用于对分割质量要求很高的场景：

```python
from modules.text_splitter import SemanticSplitter

splitter = SemanticSplitter(max_split_length=15)
result = splitter.split_file("input.txt")
```

### 场景3：完整分割流程
适用于生产环境，需要最佳分割效果：

```python
from modules.text_splitter import split_text_complete

result = split_text_complete(
    input_file="log/cleaned_chunks.xlsx",
    use_semantic_split=True
)
```

### 场景4：句子列表处理
适用于已有句子列表的批处理：

```python
from modules.text_splitter import HybridSplitter

splitter = HybridSplitter()
split_sentences = splitter.split_sentences(sentence_list)
```

## 📊 性能特性

### 1. 并发处理
- 语义分割支持多线程并发
- 可配置并发数量
- 自动负载均衡
- **新增：完善的超时机制和资源回收**
- **新增：使用 `concurrent.futures.as_completed` 确保所有协程正确终止**

### 2. 缓存机制
- GPT调用结果自动缓存
- 避免重复API调用
- 支持缓存失效和重试

### 3. 错误处理
- 完善的异常捕获和处理
- 自动重试机制
- 优雅降级策略
- **新增：超时保护，防止程序无限等待**

### 4. 内存管理
- 流式处理大文件
- 及时释放资源
- 可配置批处理大小
- **新增：上下文管理器支持，确保资源正确释放**

### 5. 资源管理 (新增)
- 所有分割器支持上下文管理器（`with` 语句）
- 自动清理线程池和未完成的任务
- 防止程序无法正常终止的问题

## 🔗 与其他模块集成

### 与AudioTranscriber集成
```python
# 音频转录后直接分割
from modules.audio_transcriber import AudioTranscriber
from modules.text_splitter import split_text_complete

# 转录
transcriber = AudioTranscriber()
transcript_file = transcriber.transcribe_video_complete("video.mp4")

# 分割
split_file = split_text_complete(transcript_file)
```

### 与GPT模块集成
```python
# 使用重构后的GPT模块
from modules.gpt import ask_gpt

# 语义分割器会自动使用新的GPT接口
```

### 与配置模块集成
```python
# 自动读取配置
from modules.config import get_config_manager

config = get_config_manager()
# 分割器会自动使用配置中的参数
```

## 🧪 测试和调试

### 运行演示脚本
```bash
# 完整演示
python my_scripts/4_TextSplitter_demo.py

# 单独测试NLP分割
python my_scripts/4_TextSplitter_demo.py nlp

# 单独测试语义分割
python my_scripts/4_TextSplitter_demo.py semantic

# 测试混合分割
python my_scripts/4_TextSplitter_demo.py hybrid
```

### 单元测试
```python
# 直接运行模块测试
python -m modules.text_splitter.nlp_splitter
python -m modules.text_splitter.semantic_splitter
python -m modules.text_splitter.hybrid_splitter
```

## 🔄 迁移指南

### 从旧代码迁移

**旧代码：**
```python
# 老的使用方式
from core._3_1_split_nlp import split_by_spacy
from core._3_2_split_meaning import split_sentences_by_meaning

split_by_spacy()
split_sentences_by_meaning()
```

**新代码：**
```python
# 新的使用方式 - 一键搞定
from modules.text_splitter import split_text_complete

result = split_text_complete("log/cleaned_chunks.xlsx")
```

### 配置迁移
- 原有的 `load_key()` 调用会自动适配新的配置系统
- 新增配置项会有合理的默认值
- 向前兼容旧的配置格式

## 🎉 优势总结

1. **简化API** - 一行代码完成所有分割
2. **模块化设计** - 可以灵活组合不同分割器
3. **性能提升** - 并发处理、缓存优化
4. **错误恢复** - 完善的异常处理机制
5. **易于测试** - 独立的演示和测试脚本
6. **配置集成** - 完全集成重构后的配置系统
7. **向前兼容** - 保持与旧代码的兼容性

通过这种重构，原本分散的文本分割功能现在被整合成一个强大、易用、可扩展的模块化系统。 