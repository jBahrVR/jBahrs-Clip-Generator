# 🔭 Scout Idea: Whisper Initial Prompt (Game Jargon Dictionary)

## Problem statement
When using Whisper to transcribe gaming content, highly specific game jargon, character names, or streamer catchphrases (e.g., "Tarkov", "chug jug", "Kappachino", "Pochinki") are frequently misinterpreted or phonetically spelled incorrectly. This leads to inaccurate transcripts. Since the AI relies entirely on the transcript to find highlights, these transcription errors can cause the AI to miss important moments or misunderstand the context of a clip.

## Proposed Solution
Introduce a "Whisper Initial Prompt" (or "Game Jargon Dictionary") text area in the Settings tab. Users can input a comma-separated list of common jargon, game-specific terms, or names they frequently use in their streams. This text will be passed directly into Whisper's transcription engine, guiding the model on how to correctly spell these niche terms and significantly improving the accuracy of the final transcript.

## Technical Feasibility
**High Feasibility / Low Effort.**
This feature leverages a built-in parameter of the OpenAI Whisper library and requires minimal UI additions.

1. **UI Update (`app.py`):**
   - Add a `CTkEntry` or `CTkTextbox` in the Configuration tab (perhaps under the "Authentication & AI Models" or "Video Processing Rules" card) labeled "Whisper Jargon Dictionary (Optional)".
   - Allow users to enter terms like: `Tarkov, chug jug, Kappachino, jBahr`
2. **Config Update (`config_manager.py`):**
   - Save the user's string in `settings.json` under `openai.whisper_initial_prompt` or similar.
3. **Engine Update (`editor.py`):**
   - In `_transcribe_audio_to_segments`, retrieve the initial prompt string from the config.
   - If it exists, add it to the `transcribe_kwargs` dictionary (e.g., `transcribe_kwargs["initial_prompt"] = config.get("openai", {}).get("whisper_initial_prompt", "")`).
   - The `model.transcribe()` function natively supports this parameter and uses it to condition the context for the entire audio file.
