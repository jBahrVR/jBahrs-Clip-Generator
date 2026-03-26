# 🔭 Scout Idea: Local Auto-Process Folder (OBS Watcher)

## 💡 The Problem
Currently, the **Auto Scheduler** only monitors remote platforms (YouTube/Twitch) for new VODs. However, many users record their streams or gameplay locally (e.g., via OBS) in high quality to avoid compression artifacts. For these users, there is no automated workflow; they must manually queue their large `.mp4` or `.mkv` files through the **Manual Clipper** tab. This creates friction for creators who want the same "set-and-forget" overnight processing experience that remote streamers enjoy.

## 🎯 Proposed Solution
Add a **"Local Folder Watcher"** mode to the existing Auto Scheduler.

Users could designate a "Local Raw VODs Folder" (like their default OBS output directory) in the Settings tab. The background watcher would periodically scan this directory for newly completed video files. When a new file is detected, it is automatically passed to the AI Editor for clipping, and optionally moved to an "Archived" folder to prevent reprocessing.

## 🛠️ Technical Feasibility
**High Feasibility / Low Effort.**
This feature perfectly reuses the existing `editor.process_video()` orchestration pipeline.

1. **UI Update (`app.py`):**
   - Add `"Local Folder"` to the `platform_menu` dropdown in the Auto Scheduler frame.
   - Reuse the existing "Raw VODs Folder" path from the Settings tab as the target directory to monitor.
2. **Logic Update (`watcher.py`):**
   - If the platform is "Local Folder", bypass the `yt-dlp` download logic entirely.
   - Use `os.listdir()` to scan the raw VODs directory for `.mp4` or `.mkv` files.
   - Implement a simple file-lock check (e.g., attempting to briefly open the file in `r+` mode) to ensure OBS has finished writing to the file before passing its path to `editor.process_video()`.
3. **State Management:** Keep a lightweight local registry (e.g., a `.json` file in AppData or just appending a suffix to processed files) so the watcher remembers which local files have already been clipped.

## 📸 Expected Benefit
* **True Set-and-Forget Automation:** Perfectly complements the remote Auto-Scheduler by bringing identical automated, overnight processing to offline/local content creators.
* **Higher Quality Outputs:** Encourages users to clip their pristine, uncompressed local recordings instead of highly compressed stream downloads.
* **Low Technical Debt:** Recycles 90% of the existing background loop and editor routing logic.
