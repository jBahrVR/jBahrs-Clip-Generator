# 🔭 Scout Idea: Auto-Cleanup of Processed Raw VODs

## Problem statement
jBahr's Clip Generator extracts small, highly consumable clips from massive video files (VODs). These source VODs, especially raw 4+ hour recordings or high-quality streams, can easily consume tens of gigabytes of disk space per file. Currently, after processing, the original large VODs remain in the "Raw VODs" folder indefinitely until manually deleted. For users running the Auto-Scheduler overnight, this can lead to completely filling up their hard drives within days, halting further downloads and processing, and causing significant frustration.

## Proposed Solution
Introduce an optional "Auto-Delete Raw VOD After Processing" toggle in the Settings tab.

When enabled, the application will automatically delete the massive source `.mp4` or `.mkv` file from the `download_dir` folder *only* after it has successfully finished clipping and all final clips have been safely generated in the `clips_dir`. If an error occurs during processing (e.g., API failure, FFmpeg crash), the source file is kept so the user can retry.

This ensures users maintain a clean, storage-efficient environment without needing to constantly micromanage their file system.

## Technical Feasibility
**High Feasibility / Low Effort.**
This feature simply hooks into the end of the existing processing lifecycle.

1. **UI Update (`app.py`):** Add a simple `CTkSwitch` or checkbox in the "Settings" frame (e.g., under the File Paths card) for "Auto-Delete Processed VODs".
2. **Config Update (`config_manager.py`):** Store this boolean value (e.g., `delete_raw_vod`) in `settings.json`.
3. **Engine Pipeline (`editor.py` / `app.py`):**
   - In the `process_video` or the manual/auto processing loops, check this setting *after* `editor.process_video()` returns successfully (i.e., when `created_files` or similar success indicators are present).
   - If enabled and successful, use `os.remove(file_path)` to delete the original file.
   - Add a logger message (`"🗑️ Auto-deleted source VOD to save space."`) to provide transparency to the user.
