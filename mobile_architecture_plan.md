# Mobile Clip Generator - Architecture & Implementation Plan

## 1. Overview
The goal is to port the core "manual processor" functionality of the jBahr's Clip Generator desktop application into a mobile-first experience. Due to the heavy computational requirements of video processing (FFmpeg) and local AI transcription (Whisper), the mobile app will adopt a **Cloud-Offloading Architecture**.

The design aesthetic follows the **"Neon Protocol"**: a dark, high-contrast, cyberpunk/gaming theme characterized by sharp 0px corners, deep obsidian backgrounds (`#0e0e0f`), and neon cyan (`#8ff5ff`) / magenta (`#ff51fa`) accents.

---

## 2. Frontend (Mobile App)

### Technology Stack
*   **Framework:** React Native (with Expo) or Flutter. *Recommendation: React Native, given the likely existing knowledge base if a web dashboard exists, and excellent support for native video players.*
*   **State Management:** Zustand or Redux Toolkit.
*   **Styling:** Nativewind (Tailwind for React Native) to easily implement the "Neon Protocol" design tokens (0px borders, specific hex codes, glowing box-shadows).

### Core Responsibilities
1.  **Media Ingestion:** Handle VOD link pasting, local file selection (via `expo-image-picker` or `react-native-document-picker`), and Google Drive import integrations.
2.  **API Communication:** Send media/links, AI prompts, and model selections to the backend.
3.  **Real-time Status Updates:** Poll the backend (or use WebSockets/Server-Sent Events) to drive the "Neural Progress Bar" loading screen while processing occurs.
4.  **Playback & Export:** Render the final video using `expo-av` or `react-native-video`, and handle saving to the device's camera roll (`expo-media-library`) or triggering native share dialogs.

---

## 3. Backend (Cloud Infrastructure)

Since mobile devices cannot reliably run local Whisper models or execute heavy FFmpeg encoding without battery drain or OS-level background task termination, a robust backend is required.

### Technology Stack
*   **API Layer:** Node.js (Express/Fastify) or Python (FastAPI). *Recommendation: Python FastAPI, to reuse the existing Python logic, prompting, and RMS/Whisper integration from the desktop app.*
*   **Task Queue:** Celery with Redis (or AWS SQS) to handle asynchronous video processing tasks so the API doesn't time out.
*   **Storage:** AWS S3 or Google Cloud Storage for temporarily holding uploaded videos and storing the final generated clips.
*   **Compute:** Render Background Workers, AWS ECS, or a dedicated GPU VPS (e.g., RunPod, Lambda Labs) if utilizing open-source LLMs or local Whisper processing to keep costs down.

### Processing Pipeline
1.  **Upload/Ingest:** API receives the video file or VOD link. If a link, backend uses `yt-dlp` to download the media to temporary cloud storage.
2.  **Audio Extraction & Transcription:** Backend extracts audio via FFmpeg and runs it through Whisper (via API like OpenAI, or a self-hosted cloud GPU instance).
3.  **AI Analysis:** The transcript, combined with the user's prompt and selected model, is sent to the LLM (OpenAI/Anthropic/etc.) to identify highlight timestamps.
4.  **Video Clipping:** Backend uses FFmpeg to slice the video based on the LLM's timestamps.
5.  **Delivery:** The final clip is uploaded to S3, and a pre-signed download URL is returned to the mobile app.

---

## 4. API Communication Flow

1.  **POST `/api/v1/jobs`**
    *   *Payload:* Video file (multipart/form-data) OR VOD URL, `prompt`, `ai_model`.
    *   *Response:* Returns a `job_id`.
2.  **GET `/api/v1/jobs/{job_id}/status`**
    *   *Action:* Mobile app polls this endpoint every 3-5 seconds.
    *   *Response:* `{"status": "processing", "progress": 45, "message": "Extracting audio..."}`
3.  **Status Complete**
    *   *Response:* `{"status": "completed", "video_url": "https://s3.bucket.../clip.mp4", "title": "Quadra Kill @ Mid", "duration": 15}`
4.  **GET `/api/v1/clips`**
    *   *Action:* Populates the Home/Dashboard gallery with historical clips.

---

## 5. Next Steps for Implementation
1.  **Refine Designs:** Finalize the Stitch designs and export CSS/Tailwind tokens for the mobile framework.
2.  **Backend Proof of Concept (PoC):** Extract the core Python logic from the desktop app (`llm_manager.py`, `watcher.py`) into a basic FastAPI web server.
3.  **Queue Implementation:** Add Celery to the PoC to ensure video processing doesn't block incoming HTTP requests.
4.  **Mobile Scaffolding:** Initialize the Expo/Flutter project and build the static UI screens based on the designs.
5.  **Integration:** Connect the mobile app to the backend API.
