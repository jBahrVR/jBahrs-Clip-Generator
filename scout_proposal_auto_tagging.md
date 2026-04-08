# 🔭 Scout Idea: Automated Title, Tagging, and Description Generation

## Problem statement
Currently, jBahr's Clip Generator is fantastic at automatically extracting viral moments from long VODs and generating vertical shorts. It even provides an AI virality score and reasoning for why the clip was selected. However, when the user is ready to share these clips on social media platforms (like YouTube Shorts, TikTok, or Instagram Reels), they are faced with the manual, repetitive task of inventing a catchy title, writing a description, and researching relevant hashtags for each individual clip. This interrupts the automated pipeline and adds friction to the content distribution process.

## Proposed Solution
Enhance the existing AI analysis phase to also generate platform-ready metadata for each extracted clip. When the LLM processes the transcript to find highlights, it should be instructed to simultaneously output a suggested Title, a short Description, and a list of relevant Hashtags based on the clip's specific context (e.g., #JumpScare, #Clutch, #FunnyMoments). This generated metadata would be saved directly into the existing `.json` file that accompanies each `.mp4` clip. The Clip Gallery UI could then be updated to display this metadata and provide a "Copy to Clipboard" button, making social media uploading completely frictionless.

## Technical Feasibility
**High Feasibility / Low Effort.**
This feature perfectly leverages the existing LLM orchestration pipeline and requires no new dependencies.

1. **Prompt Update (`config_manager.py` / `editor.py`):**
   - Update the default system prompt (and custom prompt profiles) to instruct the LLM to include `title`, `description`, and `hashtags` (as a list of strings) in the JSON output array alongside the existing `start_time`, `end_time`, `virality_score`, and `reasoning`.
2. **Metadata Saving (`editor.py`):**
   - The existing JSON saving logic in `_process_single_clip` automatically dumps the entire `clip` dictionary object. As long as the LLM returns the new keys, they will seamlessly be saved into the `.json` file alongside the `.mp4`.
3. **UI Enhancement (`app.py`):**
   - Update `_setup_gallery_frame` and `load_clip_details` to display the newly generated Title, Description, and Hashtags.
   - Add a simple "Copy Metadata" button to the details card that copies the formatted text to the user's system clipboard using `self.clipboard_clear()` and `self.clipboard_append()`.