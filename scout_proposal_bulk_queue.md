# 🔭 Scout Idea: Dedicated Bulk Queue Manager UI

## Problem statement
Currently, jBahr's Clip Generator allows users to process multiple videos at once by separating URLs or local file paths with a semicolon (`;`) in the "Manual Clipper" tab. However, this feature is essentially a hidden power-user trick. It is clunky, prone to formatting errors (like missing semicolons), and lacks visibility. Once a user clicks "Process Queue", there is no way to see which item is currently being processed, how many items are left, or to pause, reorder, or remove items from the active queue.

## Proposed Solution
Introduce a dedicated "Queue Manager" UI element (either a new tab or an expansion of the "Manual Clipper" frame). This feature would provide a visual list of all queued videos. Users could drag and drop multiple local `.mp4` files or paste a list of URLs to add them to the queue.

The visual queue would display each item as a row with its current status (e.g., "Pending", "Downloading", "Transcribing", "Clipping", "Complete", or "Failed"). Users would have controls to reorder pending items, remove items before they start processing, and track the overall batch progress clearly.

## Technical Feasibility
**High Feasibility / Moderate Effort.**
This feature builds entirely upon the existing sequential batch logic in `app.py` but exposes it through a proper graphical interface.

1. **UI Update (`app.py`):**
   - Replace or augment the single `url_input` entry in the `manual_frame` with a `CTkScrollableFrame` that displays the current list of queued items.
   - Add "Add URL" and "Add Local Files" buttons that append new items to an underlying `self.processing_queue` list.
   - Each row in the scrollable frame would have a label for the file/URL, a dynamic status label, and an "X" button to remove it from the queue.
2. **Logic Update (`app.py`):**
   - Refactor `_process_video_thread` to pop items from `self.processing_queue` one by one.
   - Introduce status callback updates (e.g., passing a specific queue item ID) to the `logger_callback` or a new `status_callback` so the UI can update the label of the currently active item.
   - This approach safely manages the background thread while giving the user full visibility into the application's state.