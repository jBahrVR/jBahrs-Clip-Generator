# 🔭 Scout Idea: Automated Tagging & Smart Categorization for Clips

## 💡 The Problem
Currently, the application extracts high-value moments and dumps them into a single "Generated Clips" folder. Users can filter these by "Virality Score" or "Orientation" within the Clip Gallery, but this becomes incredibly messy for creators who stream variety content (e.g., jumping from a horror game to an FPS to Just Chatting). A user looking for their best "Funny Banter" moments or "Clutch Sniper Kills" has to manually watch every high-scoring clip. The LLM already identifies *why* a clip is good in its reasoning, but this metadata is trapped in a paragraph of text and isn't actionable for rapid sorting or exporting.

## 🎯 Proposed Solution
Introduce **"Smart Tagging & Categories"** to the AI extraction pipeline and Clip Gallery.

Update the AI prompt to enforce a new JSON field for each clip: `"category"`. The AI will select the most appropriate category from a predefined list (e.g., `Jump Scare`, `Clutch/Skill`, `Funny/Banter`, `Rage/Fail`, `Random Chaos`).

In the Clip Gallery UI, introduce a new "Category" dropdown filter alongside the existing Score/Type filters. Additionally, the app could append the category tag to the output filename (e.g., `MyStream_clip1_score9_[Funny].mp4`) or organize the output into automatically generated sub-folders (`/Clips/Jump Scares/`, `/Clips/Funny/`).

## 🛠️ Technical Feasibility
**High Feasibility / Low Effort.**
This leverages the existing LLM JSON output structure and CustomTkinter gallery without requiring any new heavy dependencies.

1. **Prompt Update (`config_manager.py` / `app.py`):**
   - Modify the default Omni-Genre prompt to require a `"category"` field in the JSON output array, providing a strict list of 5-6 allowed string values for the LLM to choose from.
2. **Gallery UI Update (`app.py`):**
   - Add a `CTkOptionMenu` for "Category" in the filter frame of the Gallery tab.
   - Update the `populate_gallery()` loop to read the `category` string from the associated `.json` metadata file (or filename) and filter the visible list accordingly.
3. **Metadata Storage (`editor.py`):**
   - Ensure the new `category` key is saved into the clip's `.json` metadata file alongside the `virality_score` and `reasoning`.

## 📸 Expected Benefit
* **Massive Workflow Speedup:** Creators can instantly isolate their "Funny" clips for a TikTok compilation, or their "Clutch" clips for a YouTube montage, without scrubbing through hundreds of mixed results.
* **Maximized AI Value:** We are already paying for/processing the LLM's deep contextual understanding of the scene; we should extract that understanding into actionable UI data points.
* **Better Organization:** Prevents the output folder from becoming an unmanageable dump of `clip_1.mp4`, `clip_2.mp4` files after weeks of auto-scheduler processing.
