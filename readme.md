# 🎬 jBahr's Clip Generator

An automated, AI-powered highlight extraction tool built specifically for high-immersion VR and gaming content creators. 

Tired of scrubbing through 4-hour VODs looking for a 20-second highlight? **jBahr's Clip Generator** automatically downloads your streams (or processes your local OBS recordings), transcribes the audio locally using your GPU, and uses advanced modern LLMs (Anthropic, DeepSeek, OpenAI, Google Gemini, xAI) to mathematically hunt down the funniest banter, the loudest jump scares, and the craziest clutches.

**DISCLAIMER!**

I am not a developer, I have entirely "Vibe Coded" this app as I was not finding any ideal solutions for auto clipping my VR content that didnt involve high costs and messy results. I am just sharing what I have made in the hopes that it helps other content creators out there generate solid content from their livestream vods or local recordings. 

---

## ⚡ Quick Start Guide (Manual Processing)

Get up and running in 4 easy steps!
1. **Install the Application:** Run the `setup.exe` file to install the Clip Generator to your system.
2.**Install Prerequisites:** Ensure `ffmpeg.exe`, `ffprobe.exe`, `yt-dlp.exe`, and `deno.exe` are in the exact same folder as the app executable.
3. **Add an API Key:** Go to the **Settings** tab and paste in a valid API Key (see "API Limits & Recommendations" below) and click **Save Settings**.
4. **Queue a Video:** Go to the **Manual Clipper** tab, paste a VOD link (or select a local `.mp4`), and click **Process Queue**. You're done!

---

## ✨ Key Features

* **Audio Peak Detection (RMS Loudness Mapping):** Intercepts raw audio arrays to calculate RMS loudness, mapping chaotic peaks (`[LOUDNESS: 100%]`) alongside transcriptions so the AI can physically "hear" jump scares and screaming. (Built for VR!).
* **Huge Context AI Analysis (No Chunking!):** Supports modern LLMs with massive context windows (up to 2 Million tokens!). The AI analyzes your *entire* 4+ hour VOD in a single prompt, meaning it understands running jokes from the beginning to the end of the stream without hallucinating.
* **Agnostic AI Engine:** Choose your brain! Natively connects to:
  * **Anthropic** (`claude-sonnet-4-6`, `claude-haiku`)
  * **xAI** (`grok-2-latest`)
  * **Google Gemini** (`gemini-2.5-pro`)
  * **OpenAI** (`gpt-4o`)
  * **DeepSeek & Llama** (via Custom Base URLs / OpenRouter!)
* **Clip Gallery, Thumbnails & AI Reasoning:** Review your generated clips directly inside the app! The gallery generates `.jpg` thumbnails and displays a Virality Score with a written explanation from the AI detailing exactly why it extracted that specific moment.
* **Vertical Auto-Cropper & VR Stabilization:** Converts horizontal gameplay into perfect 9:16 Shorts/TikToks. Toggle on the post-processing VR filter to automatically smooth out jarring head movements.
* **Discord Webhook Alerts:** The app can automatically ping your private Discord server with a native alert when a batch of clips is successfully extracted!
* **Multi-Track Audio Downmixing:** Automatically downmixes multi-track OBS setups (e.g., Game on Track 1, Mic on Track 2) into a single unified stereo track.
* **GPU Hardware Encoding (NVENC/AMF):** Leverages your Nvidia or Radeon GPU to execute FFmpeg clipping filters, decimating render times. 
* **100% Free Local Transcription:** Uses OpenAI's open-source `Whisper` model running entirely on your local Nvidia GPU (CUDA) to transcribe massive files in minutes without paying API fees, complete with a live UI progress tracker!
* **The Auto-Scheduler:** Set it and forget it! The app silently runs in your system tray, checking YouTube or Twitch for new uploads, bypassing subscriber-only gates using your local browser cookies, and cutting clips in the background while you sleep.

---

## 🔑 API Engine Limits & Recommendations

To power the "Editor" brain of the app, you will need an API key from at least one of these providers. **AI models process massive amounts of tokens for full VOD transcribing, so your account tier matters!**

* **Google AI Studio (Highly Recommended):** Get a Free Gemini API Key. Google Gemini is exceptionally well-tested for this app. It boasts a huge 2 Million token context window, making it incredible for 4+ hour streams.
* **Anthropic / xAI / DeepSeek:** These are also fantastic contenders with great context windows. Highly recommended if you have funded API accounts.
* **⚠️ OpenAI (Caution!):** While GPT-4o works great, **if you only have a "Tier 1" OpenAI Developer Account, you will likely hit hard Rate Limits** instantly. OpenAI severely restricts the Tokens-Per-Minute limit for Tier 1 users, making it almost impossible to pass an entire VOD transcription block into GPT-4. Use Gemini instead if you do not have a higher-tier OpenAI account!

---

## 🛠️ Setup & Prerequisites

If you are running the compiled Windows executable, the core AI libraries are pre-packaged! However, the app relies on four external open-source tools to handle downloading, cutting, and backend routing.

**You MUST place the executable files for these tools in the same folder as your Clip Generator app:**
1.  **FFmpeg & FFprobe:** The engines that physically cut and restack the `.mp4` files. Visit the official FFmpeg homepage to track down the latest Windows build.
2.  **yt-dlp:** The engine that downloads the VODs from YouTube and Twitch. Locate the yt-dlp GitHub Repository and navigate to their releases page.
3.  **Deno:** The secure JavaScript runtime required to execute the app's background logic. Visit the Deno homepage for installation instructions.

---

## 🚀 How to Use

### 1. Configuration (The First Run)
1. Open the app and navigate to the **Settings** tab.
2. Enter your **YouTube Channel ID** and/or **Twitch Username**.
3. Paste an API key into the Auth card (Anthropic, Grok, Gemini, or OpenAI) and click **"Test Key"** to verify it.
4. If you have a private discord server, you can paste in a **Discord Webhook URL** to receive push notifications when VODs finish processing!
5. Set your **Raw VODs** and **Generated Clips** folders.
6. Configure your **Vertical Export Settings** to match your OBS layout.
7. Click **Save Settings**.

### 2. Customizing AI Prompts (Important!)
You can tell the AI exactly what kind of content to look for! The app provides a "Default VR" profile, but you can build your own parameters in the **Prompts** tab.

**How the Default Prompt Works:**
The default prompt instructs the AI to treat the provided transcript like a movie script. It looks for sudden volume spikes (using `[LOUDNESS: 95%]`), chaotic overlapping dialogue, or extended periods of silence followed by screaming. It specifically bypasses "mundane" dialogue to find natural viral archetypes (e.g. Rage, Jump Scares, Funny Banter).

**Tips for Creating Custom Prompts:**
If you create your own Prompt Profile, **you MUST ensure the AI formats its output as a raw JSON array**. The clipping system will break if the AI starts its response with "Here are your clips:" or formats it in markdown. 
* Always include a strict formatting rule in your prompt, such as: `You must return ONLY a raw JSON array of objects. Do not include markdown formatting or markdown code blocks (e.g. no triple backticks). Just the raw json text.`
* Ensure your prompt asks the AI to provide exact variable keys for `"start_time"` (in seconds), `"end_time"` (in seconds), `"description"`, `"title"`, and `"reasoning"`.

### 3. Reviewing Clips
1. Navigate to the **🖼️ Clip Gallery** tab.
2. View your newly generated clips alongside their visual thumbnails!
3. Select any clip to view its AI Virality Score and read the AI's reasoning for why the clip is engaging.
4. Click **▶️ Play Clip** to open the video in your native media player. 
5. Want to bulk delete? Check the clips you don't want and hit **Delete Marked Clips** at the bottom!

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

If a download fails or the AI hits a snag, the app features persistent output logs to help you track down the issue.
* **View Logs:** Navigate to the `logs/` folder inside your app directory to find `manual_processor.log` and `auto_scheduler.log`.
* **Missing Progress?:** Ensure `yt-dlp.exe`, `ffmpeg.exe`, `ffprobe.exe`, and `deno.exe` are all physically sitting in your root app folder.
* **Twitch Fails:** If the log shows a Twitch `403 Forbidden` error, ensure your selected Auth Browser is completely closed while the Auto-Scheduler is running so the app can successfully access your session cookies.
* **Missing Audio:** Ensure your downloaded VOD or local OBS file actually contains an active audio track on Track 1. Whisper will gracefully exit if it detects zero spoken words.

---

### Contributing
Pull requests are welcome! If you have a killer prompt profile for a specific gaming genre, feel free to submit it to the `config_manager.py` default list.
