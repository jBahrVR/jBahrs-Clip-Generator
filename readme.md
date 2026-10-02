# 🎬 jBahr's Clip Generator

An automated, AI-powered highlight extraction and clipping suite built specifically for high-immersion VR and gaming content creators.

Tired of scrubbing through 4-hour VODs looking for a 20-second highlight? **jBahr's Clip Generator** automatically downloads your streams (or processes local OBS recordings), transcribes the audio locally using your GPU, and uses advanced modern LLMs (Anthropic Claude, DeepSeek, OpenAI, Google Gemini, xAI Grok) to mathematically hunt down the funniest banter, loudest jump scares, and craziest clutches.

> **DISCLAIMER!**
> 
> I am not a developer—I have entirely "Vibe Coded" this app as I was not finding any ideal solutions for auto-clipping my VR content that didn't involve high monthly costs and messy results. I am sharing what I have made in the hopes that it helps other creators out there generate solid content from their livestream VODs or local recordings.

---

## ⚡ Quick Start Guide

Get up and running in 4 easy steps:

1. **Clone or Download the Repository:**
   ```powershell
   git clone https://github.com/jBahrVR/jBahrs-Clip-Generator.git
   cd jBahrs-Clip-Generator
   ```
2. **Launch the Application:**
   - Double-click **`run.bat`** (or execute **`.\run.ps1`** in PowerShell).
   - Alternatively: `python app.py` (automatically detects and launches inside your project's `.venv` if available).
3. **Configure Settings:**
   - Navigate to the **⚙️ Settings** tab and enter your AI API key (Google Gemini is free and strongly recommended!).
   - Select your desired chat model from the dynamically updated model dropdown (click **🔄 Refresh Models** at any time to pull the latest models directly from the provider).
   - Verify your **Raw VODs** and **Generated Clips** folders and click **Save Settings**.
4. **Queue & Process a Video:**
   - Go to the **✂️ Manual Clipper** tab, paste a VOD link (or select a local `.mp4`), adjust your options, and click **Add to Queue** -> **Process Queue**!

---

## ✨ Key Features (v2.0)

### 🤖 Dynamic AI Brain & Curated Models
* **Dynamic Model Discovery:** Automatically queries provider APIs (Google GenAI, OpenAI, Anthropic, xAI, DeepSeek) to populate the dropdown with the latest available models—never get stuck with hardcoded, deprecated models.
* **Curated Top-Tier Recommendations:** Filters out hundreds of irrelevant audio/embedding/preview models, presenting an optimized list of top models best suited for large-context gaming transcripts.
* **Massive Context Window Support:** Analyzes entire 4+ hour VOD transcripts in a single prompt (up to 2M+ tokens with Gemini 2.5/2.0 Pro/Flash or Claude 3.7/3.5 Sonnet) with zero chunking artifacts.

### 🎙️ Local GPU Audio & High-Action Detection
* **RTX 50-Series & 40-Series GPU Acceleration:** Automated Windows NVIDIA CUDA runtime library detection (`setup_cuda_dll_path`) ensures modern GPUs (such as RTX 5070 Ti, RTX 40-series, and 30-series) execute Whisper locally on `cuda` without falling back to CPU.
* **Faster-Whisper Integration:** Transcribes hours of high-bitrate audio in minutes with FP16/INT8 precision and VAD silence filtering, falling back gracefully to standard Whisper or CPU if needed.
* **Multi-Language Transcription:** Transcribe speech in English, Spanish, French, German, Japanese, Korean, and dozens of other languages with automatic language detection.
* **Combat & Explosive Transient Detection:** Analyzes raw audio waveform arrays for percussive acoustic transients (gunshots, explosions) and injects `[ACTION: COMBAT]` tags so the AI flags high-intensity moments even during dead-silent gameplay.
* **RMS Loudness Peak Mapping:** Maps chaotic loudness spikes (`[LOUDNESS: 100%]`) across every timestamp so jump scares and screams are prioritized for horror and VR games.
* **Multi-Track Audio Downmixing:** Downmixes multi-track OBS recordings (e.g., Game Audio on Track 1, Microphone on Track 2) into clean stereo for Whisper transcription and video cuts.

### 🎥 Native Full HD Video & Intelligent Orientation
* **Full HD 1080p60 Download Quality:** Downloads full-resolution streams (`1080x1920 60fps` for portrait/vertical livestreams, and `1920x1080` for landscape) using smart resolution sorting (`-S res:1080`).
* **Aspect Ratio Auto-Detection:** Automatically detects whether incoming videos are 16:9 landscape or native 9:16 vertical, preserving original full video quality without forced or awkward cropping.
* **AI Smart Face & Action Tracking:** When vertical formatting is desired, runs automated face tracking or motion centroid tracking with Exponential Moving Average (EMA) trajectory smoothing to dynamically frame the subject in 9:16 vertical cuts.
* **Word-Level Animated Subtitles:** Burns dynamic, word-level `.ass` animated subtitles into vertical cuts.
* **VR Head-Motion Stabilization:** Optional deshake post-processing filter to smooth out jarring VR headset movements.

### 🖥️ Built-in Video Player & Clip Management
* **Integrated Dual-Stream Video Preview:** Review clips directly inside the app with a built-in synchronized video player. Compare horizontal and vertical cuts side-by-side or stacked, scrub along the timeline, step frame-by-frame, or launch in external players.
* **Batch Multi-Item Processing Queue:** Queue multiple local recordings or YouTube/Twitch URLs with individual settings, live progress tracking, and cancellation support.
* **Advanced Clip Gallery:** Filter and sort clips by creation date or AI Virality Score, inspect written AI reasoning justifications, review generated thumbnails, and batch delete unwanted files.
* **Social Publishing Suite:** Multi-platform sharing dialog for YouTube Shorts, TikTok, and Instagram Reels, plus automated Discord webhook notifications with virality rankings.
* **Background Auto-Scheduler:** Runs unobtrusively in your Windows System Tray, periodically checking YouTube or Twitch for new livestreams and cutting clips automatically.

---

## 🛠️ Prerequisites & Setup

### External Tools
The application relies on a few standard open-source command-line tools for media extraction and stream handling. Ensure the following are installed and added to your system `PATH` (or placed directly in the application folder):

1. **[FFmpeg & FFprobe](https://ffmpeg.org/download.html):** Required for media inspection, audio extraction, and clip rendering.
2. **[yt-dlp](https://github.com/yt-dlp/yt-dlp):** Handles downloading streams and VODs from YouTube and Twitch.
3. **[Node.js](https://nodejs.org/) or [Deno](https://deno.com/):** Required by `yt-dlp` to execute YouTube JavaScript challenge solving (`n-sig`) and prevent 403 Forbidden rate limiting.

### Python Environment
- Python 3.10 to 3.14 (64-bit recommended)
- Install project dependencies:
  ```powershell
  pip install -r requirements.txt
  ```

---

## 🔑 API Recommendations

To power the AI clipping analysis, you will need an API key from at least one provider:

* **Google AI Studio (Highly Recommended):** Free API keys available. Google Gemini (`gemini-2.5-flash`, `gemini-2.5-pro`) features a 2-Million token context window capable of ingesting entire 4+ hour VOD transcripts in a single request.
* **Anthropic:** Claude 3.7 Sonnet / Claude 3.5 Sonnet provide exceptional reasoning for nuanced comedic moments.
* **xAI Grok & DeepSeek:** High-performance, cost-effective options supported natively and via custom Base URLs / OpenRouter.
* **OpenAI:** GPT-4o / GPT-4.5. Note: OpenAI Tier 1 accounts have restrictive tokens-per-minute limits; Gemini or Anthropic are recommended for full VOD transcripts.

---

## 🧪 Automated Testing

The project includes a comprehensive automated test suite covering all critical workflows, security checks, and media pipelines.

To run the test suite:
```powershell
pytest
```
*Current test suite status: **238 passed** across 12 test modules.*

---

## 💬 Community & Feedback

Want to talk VR content creation, suggest features, or share feedback?
**[Join the jBahrVR Discord Server](https://discord.gg/uUF8J9Zqwz)**
