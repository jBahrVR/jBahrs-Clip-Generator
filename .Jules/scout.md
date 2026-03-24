## 2024-05-24 - Auto-Captioning Feature Rejected
**Learning:** The product owner explicitly stated they do not want the app to act as a full video editor. The core vision of the app is strictly AI highlight extraction and formatting, not heavy post-processing or visual modifications like subtitle burn-in.
**Action:** Avoid proposing features that handle complex video editing tasks (transitions, effects, captions). Instead, focus on extraction accuracy, workflow integrations, metadata, or features that hand off seamlessly to dedicated professional tools.
## 2024-05-24 - Timeline Export Feature Rejected
**Learning:** The product owner feels that exporting timeline metadata (XML/EDL) to professional NLEs like Premiere/Resolve is unnecessary for this app's target audience.
**Action:** Avoid proposing workflow handoffs to external professional editing software. The app's value is in providing finished, ready-to-share clips directly to the user.
## 2024-05-24 - Twitch Chat Command Integration Rejected
**Learning:** The app's default prompt already instructs the LLM to listen for verbal "clip it" cues from the streamer. Adding a chat-based clip command integration is redundant to the existing audio-based extraction logic.
**Action:** Do not propose features that duplicate functionality already handled effectively by the AI prompt's audio analysis (e.g., verbal cues, streamer intent). Focus on areas the LLM *cannot* see or hear.
