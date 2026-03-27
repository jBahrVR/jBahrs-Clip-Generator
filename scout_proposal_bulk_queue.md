# 🔭 Scout Idea: Bulk Processing Pipeline & Playlist Support

## 💡 The Problem
Currently, the **Manual Clipper** tab only accepts a single VOD URL or a single local `.mp4` file for processing. There is no mechanism to queue up multiple files or a batch of URLs. Because VOD transcription and processing can take a significant amount of time (often an hour or more for large VODs), users are forced to "babysit" the application—waiting for one long process to finish before they can manually input the next file. This creates unnecessary friction for creators trying to process a backlog of local recordings or a series of stream VODs.

## 🎯 Proposed Solution
Introduce a **Bulk Processing Queue** and **Playlist Support** to the Manual Clipper.

Instead of immediately starting a job when a URL or file is selected, users can click an **"Add to Queue"** button to build a list of tasks. When they click **"Process Queue"**, the app will iteratively process every item in the list sequentially. Furthermore, if a YouTube or Twitch playlist URL is submitted, the app will automatically parse the playlist and add all constituent VODs to the queue.

## 🛠️ Technical Feasibility
**High Feasibility / Moderate Effort.**
This feature builds directly upon the existing manual processing thread logic without requiring changes to the core AI processing engine.

1. **UI Update (`app.py`):**
   - In the `_setup_manual_frame`, add a scrollable list (e.g., `CTkScrollableFrame` or `Listbox`) to display queued items.
   - Change the "Select Local File" functionality to allow multi-file selection (e.g., `filedialog.askopenfilenames` instead of `askopenfilename`).
   - Add "Add to Queue" and "Process Queue" buttons.
2. **Logic Update (`app.py`):**
   - Modify the `start_manual_process()` method to loop through the populated queue. As each file finishes processing (calling `process_video()`), it is removed from the list, and the loop advances to the next item.
   - Update the `cancel_manual_process()` method to provide options to cancel the *current job* or abort the *entire queue*.
3. **Playlist Integration (`watcher.py`):**
   - Leverage `yt-dlp`'s native ability to extract playlist entries. If a user inputs a URL containing `list=`, use `yt-dlp` to fetch the URLs of all videos within that playlist and append them directly to the UI's processing queue.

## 📸 Expected Benefit
* **Eliminates Babysitting:** Creators can load up a weekend's worth of VODs, hit process, and walk away or sleep, greatly improving the user experience for backlog processing.
* **Maximized Hardware Utilization:** GPUs can be kept busy continuously processing multiple files back-to-back without idle downtime between manual user inputs.
