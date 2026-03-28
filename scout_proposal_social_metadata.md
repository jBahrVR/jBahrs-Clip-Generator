# 🔭 Scout Idea: Automated Social Media Metadata Generation (Titles & Hashtags)

## 💡 The Problem
jBahr's Clip Generator excelle at finding and extracting the most engaging moments from long-form content. However, once the clips are generated, the creator still faces the manual and time-consuming task of writing catchy titles, descriptions, and hashtags for platforms like TikTok, YouTube Shorts, and Instagram Reels. The AI already analyzes the entire context of the clip to determine its virality score and reasoning, making it uniquely positioned to generate this metadata automatically, eliminating the final point of friction before publishing.

## 🎯 Proposed Solution
Enhance the AI's JSON output schema to include a `suggested_title` and `suggested_hashtags` field for each extracted clip. The app will save this metadata directly into the existing `.json` file generated alongside each `.mp4`.

Additionally, the **Clip Gallery** UI will be updated to display the suggested title and a "Copy to Clipboard" button next to the hashtags, allowing the creator to seamlessly paste the optimized metadata directly into their social media scheduling tool or publishing platform.

## 🛠️ Technical Feasibility
**High Feasibility / Low Effort.**
This feature leverages the existing LLM orchestration pipeline and requires no new backend dependencies.

1. **Prompt Update (`app.py` & `editor.py`):**
   - Update the base prompt instructions passed to the LLM to request two additional fields in the JSON response: `suggested_title` (a catchy 5-10 word title) and `suggested_hashtags` (an array of 3-5 relevant hashtags).
2. **Metadata Storage (`editor.py`):**
   - The existing `json.dump()` logic in `_process_single_clip` automatically saves the entire clip object to disk. No changes are required here as long as the LLM returns the new fields.
3. **UI Update (`app.py`):**
   - In `_setup_gallery_frame` and `load_clip_details`, update the `details_card` to display the `suggested_title` and `suggested_hashtags`.
   - Add a small `CTkButton` to copy the hashtags/title to the system clipboard using `self.clipboard_clear()` and `self.clipboard_append()`.

## 📸 Expected Benefit
* **Frictionless Publishing:** Creators can go straight from reviewing a clip to publishing it without having to manually brainstorm titles and tags.
* **Maximized Virality:** The AI, having analyzed the raw transcript, can generate highly relevant and engaging titles tailored to the specific context of the highlight.
* **Low Technical Debt:** Fully utilizes the existing LLM context window and JSON extraction pipeline without adding any new API calls or complex processing.