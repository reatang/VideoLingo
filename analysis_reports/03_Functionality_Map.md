# 3. 功能地图

*   **核心功能列表及描述：** 视频获取 (下载/上传)、音频提取、人声分离 (Demucs)、ASR (WhisperX)、字幕切分 (NLP 和 LLM)、术语管理、翻译 (LLM, 包含翻译-反思-调整流程)、字幕生成 (单行, Netflix标准)、可选的字幕嵌入、配音 (多种TTS引擎, 包括声音克隆)、音频合并、最终视频生成、批量处理。

*   **功能之间的关系和交互方式 (PlantUML 图表)：**

(用户需要使用 PlantUML 渲染工具来从下面的文本描述中可视化此图表)

```plantuml
@startuml
title VideoLingo 功能工作流程

skinparam activity {
  BackgroundColor LightBlue
  BorderColor Blue
  FontName SansSerif
}
skinparam diamond {
  BackgroundColor LightYellow
  BorderColor Orange
  FontName SansSerif
}
skinparam arrow {
  Color Blue
}
skinparam note {
  BackgroundColor LightGray
  BorderColor Gray
}

(*) --> "视频输入：URL/上传" as VideoInput
VideoInput --> "1. 视频下载/加载" as DownloadLoad
DownloadLoad --> "2. 音频提取" as AudioExtraction
AudioExtraction --> if "Demucs 人声分离?" then
  --> [是] "人声分离" as VocalSep
  VocalSep --> "ASR 音频" as ASRAudio
else
  --> [否] ASRAudio
endif
ASRAudio --> "3. ASR - WhisperX" as ASRWhisperX
ASRWhisperX --> note: 原始文本
ASRWhisperX --> "4. 字幕切分" as SubSegmentation
SubSegmentation --> note: 切分后字幕
SubSegmentation --> if "术语 (自定义/AI)" as Terminology then
  --> [应用术语] "5. 翻译 - LLM" as TranslationLLM
else
  --> TranslationLLM
endif
TranslationLLM --> note: 翻译后文本
TranslationLLM --> "6. 字幕生成" as SubGeneration
SubGeneration --> if "嵌入字幕?" then
  --> [是] "7. 嵌入字幕到视频" as BurnSubs
  BurnSubs --> "带嵌入字幕的视频" as VideoWithSubs
  VideoWithSubs --> "合并音频和视频" as CombineAV_Subs
else
  --> [否] "用于配音的原始视频" as OriginalVideo
  OriginalVideo --> "合并音频和视频" as CombineAV_Orig
endif
TranslationLLM --> "8. TTS - 配音" as TTSDubbing
TTSDubbing --> note: 配音音频块
TTSDubbing --> "9. 合并配音音频" as MergeDubbedAudio
MergeDubbedAudio --> note:最终配音音轨
MergeDubbedAudio --> CombineAV_Subs
MergeDubbedAudio --> CombineAV_Orig
CombineAV_Subs --> "10. 最终输出视频" as FinalOutput
CombineAV_Orig --> FinalOutput
FinalOutput --> (*)

note "用户设置 / config.yaml" as UserSettings
UserSettings ..> DownloadLoad
UserSettings ..> ASRWhisperX
UserSettings ..> TranslationLLM
UserSettings ..> TTSDubbing
note "影响多个步骤" as SettingsNote
UserSettings .. SettingsNote

@enduml
```

*   **用户流程图 (Streamlit):** 配置设置 -> 输入视频 -> 开始处理 (字幕，然后是配音) -> 查看/下载输出。
*   **API接口分析：**
    *   **消费的API：** OpenAI, Azure, 302.ai, ElevenLabs, SiliconFlow 等，用于 LLM、ASR、TTS。
    *   **提供的API (可能)：** README 中提到 “类OpenAI API格式”，根据目前证据，这可能指的是内部Python API或其与LLM的交互方式，而非VideoLingo本身托管的公共API。
