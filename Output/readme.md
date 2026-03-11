# 🎬 jBahr's Clip Generator (v1.1.6 - Creator Edition)

An automated, AI-powered highlight extraction tool built specifically for high-immersion VR and gaming content creators. 

Tired of scrubbing through 4-hour VODs looking for a 20-second highlight? **jBahr's Clip Generator** automatically downloads your streams (or processes your local OBS recordings), transcribes the audio locally using your GPU, and uses advanced LLMs (OpenAI or Google Gemini) to mathematically hunt down the funniest banter, the loudest jump scares, and the craziest clutches.

## ✨ Key Features

* **Vertical Auto-Cropper (New in v1.1.6!):** Automatically converts horizontal esports gameplay into perfect 9:16 Shorts/TikToks. Use the Custom Coordinate engine to perfectly slice out your facecam and stack it directly over the gameplay.
* **VR Anti-Shake Stabilization (New in v1.1.6!):** Toggle on the post-processing VR filter to automatically smooth out jarring head movements and frantic gameplay using FFmpeg motion vector analysis.
* **Clip Gallery & AI Reasoning (New in v1.1.6!):** Review your generated clips directly inside the app, complete with a 1-10 Virality Score and a written explanation from the AI detailing exactly why it extracted that specific moment.
* **Batch Processing:** Select multiple local `.mp4` or `.mkv` OBS recordings at once and let the app crunch through the entire queue back-to-back.
* **Dual AI Engines:** Choose your brain. Use OpenAI (`gpt-4o`, `gpt-4o-mini`) or unlock massive context windows by feeding your entire unchunked VOD directly into Google Gemini (`gemini-2.5-flash`, `gemini-2.5-pro`).
* **100% Free Local Transcription:** Uses OpenAI's open-source `Whisper` model running entirely on your local Nvidia GPU (CUDA) to transcribe massive files in minutes without paying transcription API fees.
* **The Auto-Scheduler:** Set it and forget it. The app silently runs in your system tray, checking YouTube or Twitch for new uploads, bypassing subscriber-only gates using your local browser cookies, and cutting clips in the background while you sleep.

---

## 🛠️ Setup & Prerequisites

If you are running the compiled Windows executable, the core AI libraries are pre-packaged! However, the app relies on four external open-source tools to handle downloading, cutting, and backend routing.

**You MUST place the executable files for these tools in the same folder as your Clip Generator app:**
1.  **FFmpeg & FFprobe:** The engines that physically cut and restack the `.mp4` files. Visit the official [FFmpeg homepage](https://ffmpeg.org/) to find the latest Windows release.
2.  **yt-dlp:** The engine that downloads the VODs from YouTube and Twitch. Visit the [yt-dlp GitHub Repository](https://github.com/yt-dlp/yt-dlp) and navigate to their releases page.
3.  **Deno:** The secure JavaScript runtime required to execute the app's background logic. Visit the [Deno homepage](https://deno.com/) for installation instructions.

### API Keys
To power the "Editor" brain of the app, you will need an API key from at least one of these providers:
* **Google AI Studio (Recommended):** Get a Free Gemini API Key from the Google AI Studio dashboard. Highly recommended for streams over 1 hour due to its massive context window and cost-efficiency.
* **OpenAI:** Get an API Key from the OpenAI Developer Platform (Requires a loaded API balance).

---

## 🚀 How to Use

### 1. Configuration (The First Run)
1. Open the app and navigate to the **Settings** tab.
2. Enter your **YouTube Channel ID** and/or **Twitch Username**.
3. Paste your **Google** or **OpenAI** API key and click "Test Key" to verify it.
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
2. Select any newly generated clip to view its AI Virality Score and read the AI's reasoning for why the clip is engaging.
3. Click **▶️ Play Clip** to open the video in your native media player. 

### 4. The Auto-Scheduler
Want to wake up to fresh clips?
1. Go to the **Auto Scheduler** tab.
2. Select your platform, lookback rules, and checking interval (e.g., "Every 4 Hours").
3. Toggle the **Enable Watcher** switch.
4. You can safely hit the "X" on the window. The app will minimize to your Windows System Tray and quietly monitor your channel in the background!

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