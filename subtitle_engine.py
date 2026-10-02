import os
import re
from typing import List, Dict, Any, Optional


def format_ass_time(seconds: float) -> str:
    """Formats seconds as ASS timestamp format: H:MM:SS.cs"""
    seconds = max(0.0, seconds)
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centis = int(round((seconds % 1.0) * 100))
    if centis >= 100:
        secs += 1
        centis = 0
    return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"


def escape_ffmpeg_filter_path(filepath: str) -> str:
    """
    Safely escapes a file path for use within an FFmpeg filter argument (ass=...).
    Handles Windows drive letters, backslashes, colons, and single quotes.
    Example: C:\\path\\to\\sub.ass -> C\\\\:/path/to/sub.ass
    """
    # Normalize to forward slashes first
    clean_path = filepath.replace("\\", "/")
    # Escape colon (especially drive letter C:)
    clean_path = clean_path.replace(":", r"\:")
    # Escape single quotes and brackets
    clean_path = clean_path.replace("'", r"\'")
    clean_path = clean_path.replace("[", r"\[")
    clean_path = clean_path.replace("]", r"\]")
    return clean_path


# Style Presets for ASS vertical 1080x1920 video
STYLE_PRESETS = {
    "Viral Yellow Highlight": {
        "font_name": "Arial Black",
        "font_size": 48,
        "primary_color": "&H00FFFFFF&",    # Inactive words: White
        "highlight_color": "&H0000FFFF&",  # Active word: Vivid Yellow
        "outline_color": "&H00000000&",    # Black outline
        "back_color": "&H80000000&",       # Semi-transparent shadow
        "bold": 1,
        "outline": 4,
        "shadow": 3,
        "border_style": 1,
    },
    "Neon Green Highlight": {
        "font_name": "Arial Black",
        "font_size": 48,
        "primary_color": "&H00FFFFFF&",    # White
        "highlight_color": "&H0000FF00&",  # Neon Green
        "outline_color": "&H00000000&",
        "back_color": "&H80000000&",
        "bold": 1,
        "outline": 4,
        "shadow": 3,
        "border_style": 1,
    },
    "Clean White Bold": {
        "font_name": "Arial Black",
        "font_size": 46,
        "primary_color": "&H00FFFFFF&",
        "highlight_color": "&H00D0D0D0&",  # Light grey highlight
        "outline_color": "&H00000000&",
        "back_color": "&H80000000&",
        "bold": 1,
        "outline": 4,
        "shadow": 2,
        "border_style": 1,
    },
    "Classic Box": {
        "font_name": "Arial Black",
        "font_size": 44,
        "primary_color": "&H00FFFFFF&",
        "highlight_color": "&H0000FFFF&",
        "outline_color": "&H00000000&",
        "back_color": "&HAA000000&",       # Dark box background
        "bold": 1,
        "outline": 0,
        "shadow": 0,
        "border_style": 3,                 # Opaque bounding box
    },
}

POSITION_PRESETS = {
    "Bottom Third": {
        "alignment": 2,  # Bottom-Center
        "margin_v": 280, # Elevated above TikTok/Reels UI overlay
    },
    "Center": {
        "alignment": 5,  # Middle-Center
        "margin_v": 0,
    },
    "Top Third": {
        "alignment": 8,  # Top-Center
        "margin_v": 260,
    },
}


def group_words_into_phrases(
    words: List[Dict[str, Any]],
    max_words_per_line: int = 4,
    max_pause_sec: float = 0.5
) -> List[List[Dict[str, Any]]]:
    """
    Groups a stream of timestamped words into compact, readable phrases (3-4 words).
    Starts a new phrase if max_words_per_line is reached or a pause > max_pause_sec occurs.
    """
    phrases = []
    current_phrase = []

    for word_info in words:
        word_text = word_info.get("word", "").strip()
        if not word_text:
            continue

        if not current_phrase:
            current_phrase.append(word_info)
            continue

        prev_end = current_phrase[-1].get("end", 0.0)
        curr_start = word_info.get("start", prev_end)

        # Split on sentence-ending punctuation or pause or word limit
        pause = curr_start - prev_end
        prev_word = current_phrase[-1].get("word", "")
        ends_sentence = any(prev_word.endswith(p) for p in (".", "?", "!"))

        if len(current_phrase) >= max_words_per_line or pause > max_pause_sec or ends_sentence:
            phrases.append(current_phrase)
            current_phrase = [word_info]
        else:
            current_phrase.append(word_info)

    if current_phrase:
        phrases.append(current_phrase)

    return phrases


def generate_ass_subtitles(
    words: List[Dict[str, Any]],
    output_ass_path: str,
    clip_start: float = 0.0,
    clip_end: Optional[float] = None,
    style_preset: str = "Viral Yellow Highlight",
    position_preset: str = "Bottom Third",
    custom_font_size: Optional[int] = None,
    max_words_per_line: int = 4
) -> str:
    """
    Generates an Advanced SubStation Alpha (.ass) subtitle file with viral word-level
    karaoke highlighting and returns the generated filepath.
    """
    style = STYLE_PRESETS.get(style_preset, STYLE_PRESETS["Viral Yellow Highlight"])
    pos = POSITION_PRESETS.get(position_preset, POSITION_PRESETS["Bottom Third"])
    font_size = custom_font_size or style["font_size"]

    # Filter words within clip boundaries and adjust timestamps relative to clip start
    clip_words = []
    for w in words:
        w_start = float(w.get("start", 0.0))
        w_end = float(w.get("end", w_start + 0.3))

        # Check overlap with clip window
        if clip_end is not None and w_start >= clip_end:
            continue
        if w_end <= clip_start:
            continue

        # Adjust relative to clip start
        rel_start = max(0.0, w_start - clip_start)
        rel_end = max(rel_start + 0.05, (w_end - clip_start) if clip_end is None else min(clip_end - clip_start, w_end - clip_start))

        clip_words.append({
            "word": str(w.get("word", "")).strip(),
            "start": rel_start,
            "end": rel_end
        })

    phrases = group_words_into_phrases(clip_words, max_words_per_line=max_words_per_line)

    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1080",
        "PlayResY: 1920",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Default,{style['font_name']},{font_size},{style['primary_color']},{style['highlight_color']},"
        f"{style['outline_color']},{style['back_color']},{style['bold']},0,0,0,100,100,0,0,"
        f"{style['border_style']},{style['outline']},{style['shadow']},{pos['alignment']},40,40,{pos['margin_v']},1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
    ]

    primary_hex = style["primary_color"]
    highlight_hex = style["highlight_color"]

    for phrase in phrases:
        if not phrase:
            continue

        # Create sequential highlight dialogue lines for each word in phrase
        for i, target_word in enumerate(phrase):
            t_start = target_word["start"]
            t_end = target_word["end"]

            # Format words in phrase with target_word highlighted
            formatted_words = []
            for j, w in enumerate(phrase):
                w_clean = re.sub(r'[{}\\]', '', w["word"])
                if j == i:
                    formatted_words.append(f"{{\\c{highlight_hex}}}{w_clean}{{\\c{primary_hex}}}")
                else:
                    formatted_words.append(w_clean)

            dialogue_text = " ".join(formatted_words)
            start_str = format_ass_time(t_start)
            end_str = format_ass_time(t_end)

            lines.append(f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{dialogue_text}")

    os.makedirs(os.path.dirname(os.path.abspath(output_ass_path)), exist_ok=True)
    with open(output_ass_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    return output_ass_path
