## 2024-05-24 - Transient visual feedback for actions with hidden contextual logs
**Learning:** For global actions (like saving settings) where contextual logs or confirmation messages are hidden or redirected, a lack of visual feedback on the interactive component can make the app feel unresponsive.
**Action:** Implement transient UI feedback (e.g., momentarily updating button text and color to a success state before reverting) to reassure users without cluttering the UI with persistent notifications.

## 2024-05-27 - Empty States for Scrollable Frames
**Learning:** In desktop UI applications like CustomTkinter, users often encounter empty scrollable lists (e.g., when filtering clips or when a directory is not configured). If there's no visual feedback, the user might assume the app is loading, broken, or unresponsive.
**Action:** When a loop building UI elements in a scrollable frame results in zero visible items, dynamically append a generic empty-state label (`ctk.CTkLabel`) with italicized text to provide immediate, helpful guidance indicating that no items matched the criteria.
