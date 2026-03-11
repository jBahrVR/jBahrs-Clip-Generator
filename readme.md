# 🎬 jBahr's Clip Generator

An automated, AI-powered highlight extraction tool built specifically for high-immersion VR and gaming content creators. 

Tired of scrubbing through 4-hour VODs looking for a 20-second highlight? **jBahr's Clip Generator** automatically downloads your streams (or processes your local OBS recordings), transcribes the audio locally using your GPU, and uses advanced modern LLMs (Anthropic, DeepSeek, OpenAI, Google Gemini, xAI) to mathematically hunt down the funniest banter, the loudest jump scares, and the craziest clutches.

**DISCLAIMER!**

I am not a developer, I have entirely "Vibe Coded" this app as I was not finding any ideal solutions for auto clipping my VR content that didnt involve high costs and messy results. I am just sharing what I have made in the hopes that it helps other content creators out there generate solid content from their livestream vods or local recordings. 

## ✨ Key Features

* **Audio Peak Detection (RMS Loudness Mapping):** Intercepts raw audio arrays to calculate RMS loudness, mapping chaotic peaks (`[LOUDNESS: 100%]`) alongside transcriptions so the AI can physically "hear" jump scares and screaming. (Built for VR!).
* **Huge Context AI Analysis (No Chunking!):** Supports modern LLMs with massive context windows (up to 2 Million tokens!). The AI analyzes your *entire* 4+ hour VOD in a single prompt, meaning it understands running jokes from the beginning to the end of the stream without hallucinating.
* **Aggnostic AI Engine (New!):** Choose your brain! Natively connects to:
  * **Anthropic** (`claude-sonnet-4-6`, `claude-haiku`)
  * **xAI** (`grok-2-latest`)
  * **Google Gemini** (`gemini-2.5-pro`)
  * **OpenAI** (`gpt-4o`)
  * **DeepSeek & Llama** (via Custom Base URLs / OpenRouter!)
* **Clip Gallery, Thumbnails & AI Reasoning:** Review your generated clips directly inside the app! The gallery now automatically generates `.jpg` thumbnails and displays a 1-10 Virality Score with a written explanation from the AI detailing exactly why it extracted that specific moment.
* **Vertical Auto-Cropper & VR Stabilization:** Converts horizontal gameplay into perfect 9:16 Shorts/TikToks. Toggle on the post-processing VR filter to automatically smooth out jarring head movements.
* **Color-Coded Live Console & Cancel Operations:** Watch the AI's internal monologue and FFmpeg cut commands color-coded in real-time. Made a mistake? Seamlessly abort long-running transcriptions and generations with the new "Cancel" process control.
* **Multi-Track Audio Downmixing:** Automatically downmixes multi-track OBS setups (e.g., Game on Track 1, Mic on Track 2) into a single unified stereo track.
* **GPU Hardware Encoding (NVENC/AMF):** Leverages your Nvidia or Radeon GPU to execute FFmpeg clipping filters, decimating the time it takes to render your final files. 
* **100% Free Local Transcription:** Uses OpenAI's open-source `Whisper` model running entirely on your local Nvidia GPU (CUDA) to transcribe massive files in minutes without paying API fees.
* **The Auto-Scheduler:** Set it and forget it! The app silently runs in your system tray, checking YouTube or Twitch for new uploads, bypassing subscriber-only gates using your local browser cookies, and cutting clips in the background while you sleep.

---

## 🛠️ Setup & Prerequisites

If you are running the compiled Windows executable, the core AI libraries are pre-packaged! However, the app relies on four external open-source tools to handle downloading, cutting, and backend routing.

**You MUST place the executable files for these tools in the same folder as your Clip Generator app:**
1.  **FFmpeg & FFprobe:** The engines that physically cut and restack the `.mp4` files. Visit the official FFmpeg homepage to track down the latest Windows build.
2.  **yt-dlp:** The engine that downloads the VODs from YouTube and Twitch. Locate the yt-dlp GitHub Repository and navigate to their releases page.
3.  **Deno:** The secure JavaScript runtime required to execute the app's background logic. Visit the Deno homepage for installation instructions.

### API Keys
To power the "Editor" brain of the app, you will need an API key from at least one of these providers:
* **Anthropic:** The new Claude models are incredible at identifying viral context and humor.
* **Google AI Studio (Recommended for Cost):** Get a Free Gemini API Key. Incredible for huge 4 hour streams.
* **OpenRouter / OpenAI / xAI:** Natively drop your keys in the Settings tab to gain access to GPT-4o, Grok-2, DeepSeek, and Llama 3.1!

---

## 🚀 How to Use

### 1. Configuration (The First Run)
1. Open the app and navigate to the **Settings** tab.
2. Enter your **YouTube Channel ID** and/or **Twitch Username**.
3. Paste an API key into the Auth card (Anthropic, Grok, Gemini, or OpenAI) and click **"Test Key"** to verify it.
4. Set your **Raw VODs** and **Generated Clips** folders.
5. Configure your **Vertical Export Settings** to match your OBS layout.
6. Click **Save Settings**.

### 2. Manual & Batch Processing
Got a specific VOD or local recording you want to cut right now?
1. Go to the **Manual Clipper** tab.
2. Paste a direct URL to a YouTube/Twitch video, OR click **📂 Browse Files** to select one or more local video files.
3. Click **Process Queue**. The console will log the transcription, AI analysis, and FFmpeg filtergraphs in real-time.

### 3. Reviewing Clips
1. Navigate to the **🖼️ Clip Gallery** tab.
2. View your newly generated clips alongside their visual thumbnails!
3. Select any clip to view its AI Virality Score and read the AI's reasoning for why the clip is engaging.
4. Click **▶️ Play Clip** to open the video in your native media player. 

### 4. The Auto-Scheduler
Want to wake up to fresh clips?
1. Go to the **Auto Scheduler** tab.
2. Select your platform, lookback rules, and checking interval (e.g., "Every 4 Hours").
3. Toggle the **Enable Watcher** switch.
4. You can safely hit the "X" on the window. The app will minimize to your Windows System Tray and quietly monitor your channel in the background!

---

## 💬 Community

Want to talk VR content creation or share feature requests? 
**[Join the jBahrVR Discord Server](https://discord.gg/uUF8J9Zqwz)**

---

## 🐛 Troubleshooting & Logs

If a download fails or the AI hits a snag, the app features a persistent crash logger to help you track down the issue.
* **View Logs:** Click the **"📝 View Crash Logs"** button in the sidebar to instantly open `app_crash_log.txt`.
* **Missing Progress?:** Ensure `yt-dlp.exe`, `ffmpeg.exe`, `ffprobe.exe`, and `deno.exe` are all physically sitting in your root app folder.
* **Twitch Fails:** If the log shows a Twitch `403 Forbidden` error, ensure your selected Auth Browser is completely closed while the Auto-Scheduler is running so the app can successfully access your session cookies.
* **Missing Audio:** Ensure your downloaded VOD or local OBS file actually contains an active audio track on Track 1. Whisper will gracefully exit if it detects zero spoken words.

---

### Contributing
Pull requests are welcome! If you have a killer prompt profile for a specific gaming genre, feel free to submit it to the `config_manager.py` default list.
