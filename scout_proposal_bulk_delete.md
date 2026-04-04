# 🔭 Scout Idea: Bulk Delete Options in Gallery

## Problem statement
The current Clip Gallery allows users to review their generated clips. However, deleting multiple clips requires clicking each individual checkbox and then clicking "Delete Marked Clips". For streamers who generate hundreds of clips per session, this becomes a tedious, repetitive workflow. There is no quick way to "Select All" or "Clear All" clips in the gallery.

## Proposed Solution
Add simple "Select All" and "Deselect All" workflow buttons to the Clip Gallery interface. This would allow users to quickly mark the entire visible list of clips for deletion, significantly streamlining the cleanup process after reviewing a large batch of highlights.

## Technical Feasibility
**High Feasibility / Low Effort.**
This feature does not require any backend engine changes and strictly enhances the existing CustomTkinter UI.

1. **UI Update (`app.py`):**
   - In the `_setup_gallery_frame` method, add a new horizontal frame (e.g., `selection_btns_frame`) above or below the `clip_listbox`.
   - Add two `CTkButton` widgets: "Select All" and "Deselect All".
2. **Logic Update (`app.py`):**
   - Create a `select_all_clips()` method that iterates through the `marked_for_deletion` dictionary and sets all BooleanVars to `True`.
   - Create a `deselect_all_clips()` method that iterates through the same dictionary and sets all BooleanVars to `False`.
