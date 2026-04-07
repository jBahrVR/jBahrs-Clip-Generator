# 🔭 Scout Idea: AI-Generated Titles and Hashtags

## Problem statement
Currently, jBahr's Clip Generator automatically finds and extracts highly engaging clips, and provides metadata on *why* it extracted the clip (`reasoning`) and how engaging it is (`virality_score`). However, once the content creator wants to upload these clips to platforms like YouTube Shorts or TikTok, they still have to manually think of a catchy title and research relevant hashtags for each individual clip. This creates friction at the very final step of the content pipeline.

## Proposed Solution
Enhance the AI's JSON output structure to automatically generate a catchy, platform-ready title and a set of relevant hashtags for each extracted clip, based on the transcript segment's context.

The AI prompt in `config_manager.py` would be updated to instruct the LLM to output two new fields for each clip:
1. `title`: A short, engaging title optimized for short-form video (e.g., "The ULTIMATE Jump Scare! 😱").
2. `hashtags`: An array of 3-5 relevant hashtags (e.g., `["#gaming", "#vr", "#horrorgame"]`).

These new fields would be saved in the clip's JSON metadata file alongside the `reasoning` and `virality_score`. The `Clip Gallery` UI would then be updated to display this generated title and hashtags when a clip is selected, allowing the user to simply copy-paste them when uploading their content.

## Technical Feasibility
**High Feasibility / Low Effort.**
This feature requires no new dependencies and simply extends the existing AI metadata pipeline.

1. **Prompt Update (`config_manager.py`):** Update the `Omni-Genre Broad Net` profile to instruct the LLM to include `title` and `hashtags` keys in its JSON output structure for each clip.
2. **Data Persistence (`editor.py`):** The `json.dump` call in `_process_single_clip` already saves the entire `clip` object returned by the AI. No changes are needed here, as the new keys will automatically be written to the metadata `.json` file.
3. **UI Update (`app.py`):**
   - Add new `CTkLabel` or `CTkTextbox` widgets to the `details_card` in the `_setup_gallery_frame` method to display the title and hashtags.
   - Update `load_clip_details` to read the `title` and `hashtags` fields from the JSON file and populate the new UI widgets, falling back to empty strings if the keys are missing (to ensure backward compatibility with older clips).
   - Optionally add a "Copy Metadata" button to easily copy the title and tags to the clipboard.