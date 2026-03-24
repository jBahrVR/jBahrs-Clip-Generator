# 🔭 Scout Idea: Local Whisper Multi-Language Support

## 💡 The Problem
Currently, jBahr's Clip Generator is an incredibly powerful tool for analyzing massive English-language VODs. However, the core Whisper model implementation in `editor.py` implicitly relies on the default English transcription logic. For streamers who speak Spanish, French, German, or other supported languages, the local GPU transcription may struggle or attempt to hallucinate English translations. This artificially limits the application's user base strictly to English creators, despite the fact that modern LLMs (Gemini, Claude, GPT-4o) are exceptionally good at multi-lingual reasoning and could easily find highlights in a Spanish transcript.

## 🎯 Proposed Solution
Add a simple "VOD Language" dropdown to the Configuration tab (next to the Whisper Model Size selector). This dropdown would allow users to specify the primary spoken language of their VODs (e.g., "English", "Spanish", "French", "Auto-Detect").

When processing the video in `editor.py`, the `model.transcribe()` function call would be updated to pass the `language` argument (e.g., `language="es"` or `language=None` for auto-detect).

The output transcript would be accurately generated in the native language, and the large context LLM would read the native transcript to find the funniest/loudest moments based on the existing Omni-Genre prompt (which can also be easily customized by international users).

## 🛠️ Technical Feasibility
**High Feasibility / Low Effort.**
This feature does not require any new library dependencies or complex external logic. It simply utilizes an existing parameter built directly into OpenAI's `whisper` library.

1. **UI Update (`app.py`):** Add a `CTkComboBox` to the "Authentication & AI Models" or "Video Processing Rules" card in the Settings frame with a list of major Whisper-supported languages (and an "Auto-Detect" option).
2. **Config Update (`config_manager.py`):** Save the user's selected language code in `settings.json`.
3. **Engine Update (`editor.py`):** In `_transcribe_audio_to_segments`, retrieve the language code from the config. If a specific language is selected, pass `language="[code]"` into `model.transcribe()`. If "Auto-Detect" is selected, omit the language parameter and allow Whisper's built-in 30-second language detection to handle it.

## 📸 Expected Benefit
* **Global Reach:** Instantly opens the app up to the massive international gaming community.
* **Accuracy:** Forces Whisper to stop attempting to English-translate foreign speech, improving the timestamp accuracy of the transcript passed to the AI editor.
* **No Bloat:** Does not add extra heavy dependencies or deviate from the app's core automated workflow.
