# 🎬 jBahr's Clip Generator

An automated, AI-powered highlight extraction tool built specifically for high-immersion VR and gaming content creators.

Tired of scrubbing through 4-hour VODs looking for a 20-second highlight? **jBahr's Clip Generator** automatically downloads your streams (or processes your local OBS recordings), transcribes the audio locally using your GPU, and uses advanced modern LLMs (Anthropic, DeepSeek, OpenAI, Google Gemini, xAI) to mathematically hunt down the funniest banter, the loudest jump scares, and the craziest clutches.

**DISCLAIMER!**

I am not a developer, I have entirely "Vibe Coded" this app as I was not finding any ideal solutions for auto clipping my VR content that didnt involve high costs and messy results. I am just sharing what I have made in the hopes that it helps other content creators out there generate solid content from their livestream vods or local recordings.

---

## ⚡ Quick Start Guide (Manual Processing)

Get up and running in 4 easy steps!

1. **Install the Application:** Run the `setup.exe` file to install the Clip Generator to your system.
2. **Install Prerequisites:** Ensure `ffmpeg.exe`, `ffprobe.exe`, `yt-dlp.exe`, and `deno.exe` are in the exact same folder as the app executable.
3. **Add an API Key:** Go to the **Settings** tab and paste in a valid API Key (see "API Limits & Recommendations" below). Make sure to choose the API Chat Model in the dropdown and click **Save Settings**.
4. **Queue a Video:** Go to the **Manual Clipper** tab, paste a VOD link (or select a local `.mp4`), and click **Process Queue**. Let it run and see if it finds some clips!

---

## ✨ Key Features (v1.2.0)

* **Combat & High-Intensity Detection (New!):** Analyzes local audio arrays for percussive transients (gunshots, explosions) and tags `[ACTION: COMBAT]` in the transcript so the AI knows exactly where the heat is—even if you're playing silently.
* **Audio Peak Detection (RMS Loudness Mapping):** Calculates RMS loudness for every segment, mapping chaotic peaks (`[LOUDNESS: 100%]`) so the AI can physically "hear" jump scares and screaming. (Built for VR/Horror!).
* **Huge Context AI Analysis (No Chunking!):** Supports modern LLMs with massive context windows (up to 2 Million tokens!). The AI analyzes your *entire* 4+ hour VOD in a single prompt for maximum coherence.
* **Agnostic AI Engine:** Choose your brain! Natively connects to:
  * **Anthropic** (`claude-3-5-sonnet`)
  * **xAI** (`grok-2-latest`)
  * **Google Gemini** (Optimized for `gemini-1.5-pro` & `gemini-1.5-flash`)
  * **OpenAI** (`gpt-4o`)
  * **DeepSeek & Llama** (via Custom Base URLs / OpenRouter!)
* **Advanced Clip Gallery:** Review your generated clips directly inside the app! Includes:
  * **Dynamic Sorting:** Sort your collection by **Created Date** or **AI Virality Score** to find your best content instantly.
  * **AI Reasoning & Metadata:** View virality scores and written justifications from the AI detailing exactly why each moment was extracted.
  * **Thumbnail Generation:** Automatically generates `.jpg` thumbnails for every clip.
* **Vertical Auto-Cropper & VR Stabilization:** Converts horizontal gameplay into perfect 9:16 Shorts/TikToks. Toggle on the post-processing VR filter to automatically smooth out jarring head movements.
* **Discord Webhook Alerts:** Automatically pings your private Discord server with a native alert when a batch of clips is successfully extracted.
* **Multi-Track Audio Downmixing:** Automatically downmixes multi-track OBS setups (e.g., Game on Track 1, Mic on Track 2) into a single unified stereo track for Whisper transcription.
* **GPU Hardware Encoding (NVENC/AMF):** Leverages your Nvidia or Radeon GPU to execute FFmpeg clipping filters, decimating render times.
* **100% Free Local Transcription:** Uses OpenAI's open-source `Whisper` model running local on your GPU to transcribe massive files in minutes without API fees.
* **The Auto-Scheduler:** Set it and forget it! The app silently runs in your system tray, checking YouTube or Twitch for new uploads and cutting clips while you sleep.

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

1. **FFmpeg & FFprobe:** The engines that physically cut and restack the `.mp4` files.
2. **yt-dlp:** The engine that downloads the VODs from YouTube and Twitch.
3. **Deno:** Required to execute the app's background logic.

---

## 🚀 How to Use

### 1. Configuration

1. Open the app and navigate to the **Settings** tab.
2. Enter your **YouTube Channel ID** and/or **Twitch Username**.
3. Paste an API key into the Auth card and click **"Test Key"** to verify it.
4. Set your **Raw VODs** and **Generated Clips** folders.
5. (Optional) Paste in a **Discord Webhook URL** to receive push notifications!
6. Click **Save Settings**.

### 2. Customizing AI Prompts

The app provides an optimized "Omni-Genre" profile that supports loudness mapping and combat detection. We have fine-tuned our default prompts to remove extraction biases, ensuring as many viral moments are captured as possible. You can create your own custom prompt profiles in the **Prompts** tab.

### 3. Reviewing & Sorting Clips

1. Navigate to the **🖼️ Clip Gallery** tab.
2. Use the **"Sort by"** dropdown to organize your clips by Date or Virality Score.
3. Select any clip to view its AI Reasoning and Score.
4. Click **▶️ Play Clip** to review your highlights.
5. Use the checkboxes and **Delete Marked Clips** for easy cleanup.

### 4. The Auto-Scheduler

1. Go to the **Auto Scheduler** tab.
2. Select your platform, lookback rules, and checking interval.
3. Toggle the **Enable Watcher** switch.
4. You can safely hit the "X" on the window. The app will minimize to your Windows System Tray and monitor your channel in the background!

---

## 💬 Community

Want to talk VR content creation or share feature requests?
**[Join the jBahrVR Discord Server](https://discord.gg/uUF8J9Zqwz)**

---

## 🐛 Troubleshooting & Logs

* **View Logs:** Navigate to `%APPDATA%\jBahrsClipGenerator\logs` to find your process logs, or click the **"View Crash Logs"** button in the app sidebar.
* **Twitch Fails:** If the log shows a Twitch `403 Forbidden` error, ensure your selected Auth Browser is completely closed while the Auto-Scheduler is running.

---

### Contributing

Pull requests are welcome!
