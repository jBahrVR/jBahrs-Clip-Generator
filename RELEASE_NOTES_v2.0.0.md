# jBahr's Clip Generator v2.0.0 Release Notes

## 🚀 Highlights & New Features

### ⏱️ Temporal Window Chunking for Long Streams & VODs
- **Deep Attention & High Clip Density:** Automatically partitions multi-hour VODs (> 30 minutes) into 25-minute chronological analysis windows with 2-minute overlapping seams. Eliminates LLM attention saturation, context dilution, and "lost-in-the-middle" issues so the entire stream is thoroughly analyzed from minute 0 to the final second.
- **Boundary Deduplication:** Automatically calculates Intersection-over-Union (IoU) and timestamp proximity between adjacent windows, deduplicating boundary clips while preserving the higher-scoring clip.
- **Graceful Cancellation:** Supports responsive user cancellation between windows without burning unnecessary API credits.

### 🧠 2-Pass Adaptive AI Content Profiling
- **Acoustic & Transcript Analysis:** Pass 1 samples audio metrics (combat transients, loudness spikes, screams, silence) and transcript cues to identify the exact game, tone, and pacing.
- **Dynamic System Rubric:** Synthesizes a bespoke virality rubric and system prompt tailored to the detected content before extraction begins.

### 🎥 Native Vertical Source & Aspect Ratio Detection
- Automatically detects native 9:16 vertical video sources (`height > width`), preventing duplicate vertical cuts and preserving native quality.
- Displays dynamic badges (`16:9 Horizontal Source` vs. `9:16 Vertical Source`) in the Clip Gallery.

### 🎬 Built-in Video Player & Synchronized Clip Gallery
- Real-time video preview with synchronized 16:9 horizontal and 9:16 vertical playback.
- Dual layout modes (side-by-side and stacked), frame-accurate scrubbing, and external player launching.
- Clean deduplication in the gallery view.

### ⬇️ Enhanced Full HD Video Downloader
- Upgraded yt-dlp pipeline prioritizing 1080p60/best source resolution over lower-res chunks.
- Full browser cookie integration (`--cookies-from-browser`) for YouTube/Twitch authentication.

### 📦 Standalone Portable Packaging
- Packaged with PyInstaller, bundling companion binaries (`ffmpeg.exe`, `ffprobe.exe`, `yt-dlp.exe`, `deno.exe`) and faster-whisper Silero VAD models.
- Python 3.14+ runtime hardening with full test suite coverage (255 tests passing).

---

## 📥 Download Assets

| File | Description | Size |
|---|---|---|
| `jBahrs-Clip-Generator-v2.0.0-Windows.zip` | Complete portable standalone application (batteries-included, no Python or external tools required). | ~1.78 GB |
| `jBahrs-Clip-Generator-v2.0.0-Dependencies-Windows.zip` | Companion external binaries package (`ffmpeg.exe`, `ffprobe.exe`, `yt-dlp.exe`, `deno.exe`). | ~181.8 MB |

---

## 🛠️ Quick Start Instructions

1. Download and extract `jBahrs-Clip-Generator-v2.0.0-Windows.zip`.
2. Double-click `jBahrs-Clip-Generator.exe` to launch.
3. Open **Settings** to add your AI API key (Google Gemini, OpenAI, Claude, Grok, or DeepSeek) and set your output folder.
4. Paste a YouTube or Twitch URL (or drag & drop a local video file) and click **Process Video**!
