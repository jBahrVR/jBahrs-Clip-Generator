# 🔭 Scout Idea: Chat Replay Density Mapping (Audience Reaction Integration)

## Problem Statement
Currently, jBahr's Clip Generator relies heavily on local Audio Peak Detection (RMS) and Combat Detection (transients) to guide the LLM toward high-intensity moments. While incredibly effective for jump scares or loud banter, this approach misses "silent but deadly" viral moments—such as visual gags, streamer mistakes, or epic gameplay moments where the streamer remains quiet and focused. Since the LLM cannot physically *see* the video, these visually spectacular moments are completely lost unless the streamer audibly reacts.

## Proposed Solution
Introduce **Chat Replay Density Mapping** to capture audience reactions and feed them to the AI.
When downloading a VOD from Twitch or YouTube, the app can simultaneously download the associated chat replay log. By analyzing message velocity (e.g., detecting sudden spikes in messages per second or identifying clusters of emotes like "LUL", "KEKW", or "Pog"), the app can identify exact timestamps where the audience lost their minds.
These chat spikes would be injected directly into the Whisper transcript as tags (e.g., `[CHAT_SPIKE: EXTREME]`) alongside the existing loudness tags. The LLM can then "read the room," finding viral highlights based purely on audience reaction, even if the streamer was dead silent.

## Technical Feasibility
**High Feasibility / Moderate Effort.**
This aligns perfectly with Scout's Journal directive to "Focus on areas the LLM cannot see or hear." It uses existing workflows without heavy new dependencies.

1. **Downloader Update (`watcher.py`):**
   - Add the `--write-subs` (and `--sub-langs live_chat` for YT) flag to the existing `yt-dlp` command to download the live chat JSON alongside the `.mp4`.
2. **Analysis Module (`editor.py` / new utility):**
   - Create a lightweight parsing function that reads the downloaded chat JSON.
   - Calculate message frequency per 10-30 second rolling window. Identify windows that exceed the standard deviation (the "spikes").
3. **Transcript Injection (`editor.py`):**
   - In the `_transcribe_audio_to_segments` logic, interleave the detected chat spikes with the generated Whisper text blocks based on the timestamps, similar to how `[LOUDNESS: 100%]` tags are currently injected.
4. **UI Settings (`app.py`):**
   - Add a simple toggle in the Settings tab: "Enable Chat Reaction Mapping (requires remote VOD download)".