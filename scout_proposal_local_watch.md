# 🔭 Scout Idea: Local Watch Folder Integration

## Problem statement
Currently, jBahr's Clip Generator is an incredibly powerful tool for analyzing massive English-language VODs from YouTube and Twitch. However, a significant portion of the user base relies on local OBS recordings rather than streaming to external platforms. The "Auto-Scheduler" feature exclusively monitors YouTube and Twitch for new VODs, forcing users who record locally to manually process each video via the "Manual Clipper" tab. This creates friction for creators who want an automated, hands-off pipeline for their local recordings.

## Proposed Solution
Introduce a "Local Watch Folder" option to the "Auto-Scheduler" platform dropdown. This feature would allow users to specify a local directory (e.g., their OBS output folder) for the app to monitor. When enabled, the auto-scheduler loop would periodically check this folder for new `.mp4` files that haven't been processed yet and automatically queue them for transcription and clipping. This completes the "set it and forget it" workflow for users who prefer local, high-quality recordings over streamed VODs.

## Technical Feasibility
**High Feasibility / Moderate Effort.**
This feature extends the existing auto-scheduler logic without requiring new core dependencies or altering the AI editing process.

1. **UI Update (`app.py`):**
   - Add "Local Folder" to the `platform_menu` options in `_setup_auto_frame`.
   - Conditionally display a "Select Watch Folder" button (using `browse_folder`) when "Local Folder" is selected, saving the path to `settings.json`.
2. **Watcher Update (`watcher.py`):**
   - Modify the `main(logger_callback)` function loop to handle the "Local Folder" platform.
   - Instead of using `yt-dlp` to fetch a remote playlist, it would use `os.listdir()` on the configured watch folder.
   - Implement a simple tracking mechanism (e.g., maintaining a list of processed filenames in `settings.json` or a hidden `.processed` file in the folder) to ensure it only queues *new* files.
3. **Engine Pipeline (`app.py` / `editor.py`):**
   - When a new local file is detected, bypass the download step in `watcher.py` and directly pass the absolute file path to the existing `start_manual_process()` logic or a dedicated background queue, seamlessly integrating with the established Whisper and FFmpeg pipelines.