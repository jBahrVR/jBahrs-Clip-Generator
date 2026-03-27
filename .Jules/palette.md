## 2024-05-24 - Transient visual feedback for actions with hidden contextual logs
**Learning:** For global actions (like saving settings) where contextual logs or confirmation messages are hidden or redirected, a lack of visual feedback on the interactive component can make the app feel unresponsive.
**Action:** Implement transient UI feedback (e.g., momentarily updating button text and color to a success state before reverting) to reassure users without cluttering the UI with persistent notifications.

## 2024-05-27 - Empty States for Scrollable Frames
**Learning:** In desktop UI applications like CustomTkinter, users often encounter empty scrollable lists (e.g., when filtering clips or when a directory is not configured). If there's no visual feedback, the user might assume the app is loading, broken, or unresponsive.
**Action:** When a loop building UI elements in a scrollable frame results in zero visible items, dynamically append a generic empty-state label (`ctk.CTkLabel`) with italicized text to provide immediate, helpful guidance indicating that no items matched the criteria.
## 2024-05-28 - Dynamic text states can permanently truncate UI if not restored properly
**Learning:** When using transient UI feedback like temporarily changing button text to 'Saved!', hardcoding the restore text (e.g., reverting to 'Save Prompt') can inadvertently overwrite context-specific original text (e.g., 'Save Current Prompt'), confusing users and corrupting the UI.
**Action:** Always programmatically store the original state (`widget.cget('text')`) before modifying, and use that stored property to restore the UI.

## $(date +%Y-%m-%d) - Prevent silent failure on empty actions
**Learning:** Actions that depend on a selection (like deleting marked clips) that silently `return` when the selection is empty leave users confused, as they get no feedback indicating why their click had no effect.
**Action:** When a destructive or state-changing action is blocked by an empty selection state, temporarily update the trigger button with an error/warning state (e.g., "⚠️ No clips selected" and a distinct color like orange) before restoring its original state using `widget.cget()`.
