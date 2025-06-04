# 7. 函数调用图 (概念性)

*   **主要函数/方法列表和调用流程：** `st.py` (UI) -> `process_text()` / `process_audio()` -> 对 `core/_*_*.py` 模块的顺序调用。
*   **关键的编排函数：**
    *   `st.py:process_text()`: 调用ASR、NLP切分、翻译、字幕生成、字幕嵌入等。
    *   `st.py:process_audio()`: 调用TTS任务生成、参考音频提取、TTS渲染、音频合并等。
    *   `core.utils.ask_gpt.ask_gpt()`: LLM调用的中心点。
    *   `core.tts_backend.tts_main.tts_main()`: 分派到特定的TTS引擎。

*   **函数调用关系可视化 (PlantUML 图表)：**

(用户需要使用 PlantUML 渲染工具来从下面的文本描述中可视化此图表)

```plantuml
@startuml
title VideoLingo 概念性函数调用图

package "Streamlit UI (st.py)" {
  object "main()" as st_main
  object "text_processing_section()" as st_txt_proc_sec
  object "audio_processing_section()" as st_aud_proc_sec
  object "process_text()" as st_proc_txt
  object "process_audio()" as st_proc_aud
}

package "核心流水线 - 文本" {
  object "core._2_asr.transcribe()" as asr
  object "core._3_1_split_nlp.split_by_spacy()" as split_nlp
  object "core._3_2_split_meaning.split_sentences_by_meaning()" as split_meaning
  object "core._4_1_summarize.get_summary()" as summarize
  object "core._4_2_translate.translate_all()" as translate
  object "core._5_split_sub.split_for_sub_main()" as split_sub
  object "core._6_gen_sub.align_timestamp_main()" as gen_sub
  object "core._7_sub_into_vid.merge_subtitles_to_video()" as burn_sub
}

package "核心流水线 - 音频" {
  object "core._8_1_audio_task.gen_audio_task_main()" as gen_task
  object "core._8_2_dub_chunks.gen_dub_chunks()" as gen_chunks
  object "core._9_refer_audio.extract_refer_audio_main()" as refer_audio
  object "core._10_gen_audio.gen_audio()" as gen_audio_tts
  object "core._11_merge_audio.merge_full_audio()" as merge_audio_full
  object "core._12_dub_to_vid.merge_video_audio()" as merge_vid_aud
}

package "后端与服务" {
  object "core/asr_backend/*" as asr_backends
  object "core.tts_backend.tts_main.tts_main()" as tts_backends_main
  object "core/tts_backend/* (特定TTS)" as tts_specific_backends
  object "core.utils.ask_gpt.ask_gpt()" as llm_ask_gpt
  object "Spacy NLP Lib" as spacy
}

package "工具与配置" {
  object "core.utils.config_utils.load_key()" as config_load
}

' UI 流程
st_main --> st_txt_proc_sec
st_main --> st_aud_proc_sec
st_txt_proc_sec --> st_proc_txt : onClick
st_aud_proc_sec --> st_proc_aud : onClick

' 文本处理流水线
st_proc_txt --> asr
asr --> split_nlp
split_nlp --> split_meaning
split_meaning --> summarize
summarize --> translate
translate --> split_sub
split_sub --> gen_sub
gen_sub --> burn_sub

' 音频处理流水线
st_proc_aud --> gen_task
gen_task --> gen_chunks
gen_chunks --> refer_audio
refer_audio --> gen_audio_tts
gen_audio_tts --> merge_audio_full
merge_audio_full --> merge_vid_aud

' 后端依赖
asr --> asr_backends
split_nlp --> spacy
split_meaning --> llm_ask_gpt
summarize --> llm_ask_gpt
translate --> llm_ask_gpt

gen_audio_tts --> tts_backends_main
tts_backends_main --> tts_specific_backends
tts_backends_main ..> llm_ask_gpt : "用于文本修正"

' 通用配置依赖 (示意)
asr --> config_load
translate --> config_load
gen_audio_tts --> config_load
llm_ask_gpt --> config_load

@enduml
```

*   **高频调用路径分析：** `load_key()`, `ask_gpt()`, `tts_main()`, 片段文件的I/O操作。
*   **递归和复杂调用链识别：** 深层调用栈是正常的。通过 `ThreadPoolExecutor` 实现的并发为LLM调用增加了可管理的复杂性。无明显有害递归。
