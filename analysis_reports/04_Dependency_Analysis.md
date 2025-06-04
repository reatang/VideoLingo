# 4. 依赖关系分析

*   **外部依赖库列表及用途：** 包含 `streamlit`, `whisperx`, `transformers`, `openai`, `spacy`, `moviepy`, `pydub`, `yt-dlp`, `demucs`, `edge-tts`, `pytorch-lightning`, `librosa`, `ctranslate2` 等大量库 (完整列表见 `requirements.txt`)。
*   **内部模块间依赖关系：** `st.py` 调度 `core/` 模块的调用。`core/` 中的流水线模块具有顺序依赖关系，并利用 `asr_backend/`、`tts_backend/`、`utils/`。
*   **依赖更新频率和维护状况：** 许多核心依赖库都在积极维护中。使用固定版本和git提交来确保稳定性。需要外部检查各个包的状态。
*   **潜在的依赖风险评估：** 活跃库的破坏性更新、git依赖的稳定性、对外部API可用性/更改的依赖、某些包（CUDA, FFmpeg）复杂的本地环境设置。
