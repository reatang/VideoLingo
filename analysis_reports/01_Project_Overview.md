# 1. 项目概述

*   **主要功能和目的：** VideoLingo 是一款集视频翻译、本地化和配音功能于一体的综合工具。其主要目标是生成Netflix质量的字幕和高质量的配音，以便跨越语言障碍促进全球知识共享。它支持的功能包括：YouTube视频下载、WhisperX 词级字幕识别、NLP驱动的字幕切分、AI驱动的翻译、单行字幕生成以及使用多种TTS（文本转语音）技术的配音。
*   **编程语言和主要技术栈：**
    *   **编程语言：** Python (主要)
    *   **主要技术栈：** Streamlit (用户界面), WhisperX (自动语音识别), Spacy 和 大语言模型 (自然语言处理), 多种TTS后端 (例如 Azure, OpenAI, GPT-SoVITS), FFmpeg, MoviePy, Pydub (视频/音频处理), PyTorch, Transformers (机器学习)
*   **核心第三方包及其主要版本与介绍：**
    *   `streamlit==1.38.0`：用于构建Web应用程序界面。
    *   `whisperx @ git+https://github.com/m-bain/whisperx.git@...`：用于语音识别。
    *   `transformers==4.39.3`：核心机器学习模型。
    *   `openai==1.55.3`：OpenAI API客户端。
    *   `spacy==3.7.4`：自然语言处理任务。
    *   `moviepy==1.0.3`：视频编辑。
    *   `pydub==0.25.1`：音频处理。
    *   `yt-dlp`：YouTube视频下载。
    *   `demucs`：人声分离。
    *   `edge-tts` 等：用于特定的TTS服务。
*   **许可证类型：** Apache License 2.0
*   **项目活跃度评估：** 从README更新、Star历史记录和提供的联系方式来看，项目维护活跃。具体的贡献者数量和最近提交日期需要直接访问代码仓库。
