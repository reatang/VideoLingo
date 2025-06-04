# 6. 关键算法和数据结构

*   **项目中使用的主要算法分析：**
    *   **ASR：** Whisper Transformer 模型, VAD（语音活动检测）, 词级对齐 (基于 wav2vec)。Demucs 用于声源分离。
    *   **NLP：** 句子边界检测 (Spacy), 基于LLM的语义切分, 基于LLM的摘要生成。
    *   **翻译：** 神经机器翻译 (通过 LLM), “翻译-反思-调整”提示工程。
    *   **TTS：** 多种神经TTS算法 (例如 Tacotron, FastSpeech, 用于声音克隆的VITS) 取决于后端。
    *   **时间戳对齐：** 将翻译文本映射到原始时间戳的算法。
*   **关键数据结构及其设计原理：**
    *   **文本：** 字符串, 字符串列表, JSON (用于ASR输出, LLM交互, 术语表)。
    *   **表格数据：** Pandas DataFrames 广泛用于管理字幕片段、时间戳和翻译。
    *   **配置：** 字典 (来自 `config.yaml`)。
    *   **音频数据：** Pydub `AudioSegment` 对象, NumPy 数组。
*   **性能关键点分析：** ASR推理, Demucs处理, LLM API调用, TTS生成, 视频/音频编码。
