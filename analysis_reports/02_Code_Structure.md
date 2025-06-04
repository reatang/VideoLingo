# 2. 代码结构分析

*   **主要目录结构及其用途：**
    *   `.streamlit/`：Streamlit 应用配置。
    *   `batch/`：用于批量处理的脚本。
    *   `core/`：应用核心；包含主要处理流程、ASR/TTS 后端、NLP 工具等。
        *   编号文件 (`_1_ytdlp.py`, `_2_asr.py` 等) 定义了顺序处理阶段。
        *   `asr_backend/`, `tts_backend/`：不同服务的模块化后端。
    *   `docs/`：项目文档网站 (基于 Next.js)。
    *   `translations/`：UI 语言文件和翻译版 README。
*   **关键源代码文件及其作用：**
    *   `st.py`：Streamlit 应用主入口点。
    *   `install.py`：依赖安装脚本。
    *   `config.yaml.example`：配置文件示例。
    *   `core/_1_...` 到 `core/_12_... .py`：视频处理流程的各个阶段。
    *   `core/asr_backend/*.py`, `core/tts_backend/*.py`：ASR/TTS 服务的实现。
    *   `core/utils/config_utils.py`：配置加载。
    *   `core/utils/ask_gpt.py`：集中的大语言模型交互。
*   **代码组织模式（设计模式、架构模式等）：**
    *   **流水线架构 (Pipeline Architecture)：** 由 `core/` 中的编号模块清晰定义。
    *   **模块化设计 (Modular Design)：** UI、核心逻辑、ASR/TTS 后端和工具类的分离。
    *   **策略模式 (Strategy Pattern) (概念上)：** 用于选择 ASR/TTS 后端。
    *   **配置驱动 (Configuration-Driven)：** 行为受 `config.yaml` 严重影响。
*   **模块化程度评估：** 高。良好关注点分离，有助于维护性和扩展性。
