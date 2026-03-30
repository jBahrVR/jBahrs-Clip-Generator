import os
import json
import subprocess
import torch # type: ignore
import whisper # type: ignore
import config_manager # type: ignore
from openai import OpenAI # type: ignore
import numpy as np # type: ignore
import io
import contextlib

class WhisperProgressStream(io.StringIO):
    def __init__(self, logger):
        super().__init__()
        self.logger = logger
        self.counter = 0

    def write(self, s):
        raw_msg = s.strip()
        if raw_msg and "-->" in raw_msg:
            # Throttle to log only every 10th segment to prevent UI span lag
            if self.counter % 10 == 0:
                if "]" in raw_msg:
                    t_part, _, clean_msg = raw_msg.partition("]")
                    clean_msg = clean_msg.strip()
                    timestamp = t_part.replace("[", "").partition("-->")[0].strip()
                else:
                    clean_msg = raw_msg
                    timestamp = raw_msg.partition("-->")[0].strip()
                if self.logger:
                    self.logger(f"⏳ Processed up to {timestamp}: {clean_msg[:40]}...")
            self.counter += 1
        return super().write(s)

try:
    import google.generativeai as genai # type: ignore
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False

try:
    import anthropic # type: ignore
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

def analyze_audio_peaks(audio_array, segments, sample_rate=16000, peak_detection=True, combat_detection=True):
    """Calculates RMS loudness and detects combat transients for each Whisper segment."""
    enhanced_segments = []
    
    # Heuristic for Combat: Look for rapid spikes (transients)
    # Gunshots are typically sharp spikes that rise > 4x above the local RMS within 10ms.
    
    for seg in segments:
        start_idx = int(seg['start'] * sample_rate)
        end_idx = int(seg['end'] * sample_rate)
        
        # Ensure indices stay within array bounds
        start_idx = max(0, min(start_idx, len(audio_array) - 1))
        end_idx = max(start_idx + 1, min(end_idx, len(audio_array)))
        
        chunk = audio_array[start_idx:end_idx]
        if len(chunk) == 0:
            enhanced_segments.append(seg)
            continue

        prefix_tags = []

        # Calculate global RMS once to use as base if needed
        rms = 0.0
        if peak_detection or combat_detection:
            # Using np.linalg.norm is much faster than np.sqrt(np.mean(chunk**2))
            rms = float(np.linalg.norm(chunk) / np.sqrt(len(chunk)))

        # 1. Loudness Analysis
        loudness = 0
        if peak_detection:
            loudness = min(100, int((rms / 0.1) * 100))
            prefix_tags.append(f"[LOUDNESS: {loudness}%]")

        # 2. Combat Analysis (Transient Detection)
        if combat_detection and len(chunk) > 160: # At least 10ms
            # Divide chunk into 10ms windows
            window_size = 160 # 10ms @ 16khz
            num_windows = len(chunk) // window_size
            
            if num_windows > 0:
                transient_count = 0
                # Calculate global RMS for this segment to use as base
                seg_rms = rms + 0.001
                
                # Reshape into windows and find peak per window
                windows = chunk[:num_windows*window_size].reshape(-1, window_size)
                peaks = np.max(np.abs(windows), axis=1)
                
                # A "transient" is a peak that is significantly higher than the segment average
                # and exceeds a minimum absolute threshold (to avoid noise)
                transients = (peaks > (seg_rms * 4.5)) & (peaks > 0.15)
                transient_count = np.sum(transients)
                
                # If we see > 1.5 transients per second, it's likely combat/gunfire
                duration = seg['end'] - seg['start']
                if duration > 0 and (transient_count / duration) >= 1.5:
                    prefix_tags.append("[ACTION: COMBAT]")

        tag_str = " ".join(prefix_tags)
        enhanced_text = f"{tag_str} {seg['text'].strip()}" if tag_str else seg['text'].strip()
        
        new_seg = seg.copy()
        new_seg['text'] = enhanced_text
        enhanced_segments.append(new_seg)
        
    return enhanced_segments

# --- NEW: STEALTH AUDIO EXTRACTOR ---
def extract_audio_hidden(file_path, sr=16000):
    """Bypasses Whisper's internal ffmpeg call to prevent the cmd window pop-up on Windows."""
    cmd = [
        "ffmpeg", "-nostdin", "-threads", "0", "-i", file_path,
        "-f", "s16le", "-ac", "1", "-acodec", "pcm_s16le", "-ar", str(sr), "-"
    ]
    
    startupinfo = _get_startupinfo()

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo=startupinfo)
    stdout, stderr = process.communicate()
    if process.returncode != 0:
        raise RuntimeError(f"FFmpeg audio extraction failed: {stderr.decode()}") # type: ignore
        
    # ⚡ Bolt: Prevent massive intermediate array allocations by dropping redundant .flatten()
    # (since frombuffer is already 1D) and using in-place division. Reduces peak memory by 50%.
    audio_array = np.frombuffer(stdout, np.int16).astype(np.float32)
    audio_array /= 32768.0
    return audio_array

def _get_startupinfo():
    """Returns the startupinfo configuration to hide the FFmpeg command window on Windows."""
    startupinfo = None
    if os.name == 'nt' and hasattr(subprocess, 'STARTUPINFO'):
        startupinfo = subprocess.STARTUPINFO() # type: ignore
        if hasattr(subprocess, 'STARTF_USESHOWWINDOW'):
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW # type: ignore
        if hasattr(subprocess, 'SW_HIDE'):
            startupinfo.wShowWindow = subprocess.SW_HIDE # type: ignore
    return startupinfo

def _get_gpu_codec(logger=None):
    """Detects the optimal GPU architecture for hardware encoding."""
    gpu_codec = "h264_nvenc"
    try:
        if torch.cuda.is_available():
            device_name = torch.cuda.get_device_name(0).lower()
            if "amd" in device_name or "radeon" in device_name:
                gpu_codec = "h264_amf"
    except Exception as e:
        if logger: logger(f"⚠️ Failed to detect GPU for hardware encoding: {e}")
    return gpu_codec

def _generate_horizontal_clip(file_path, output_file, start_time, end_time, video_codec, audio_codec_flags, hardware_encoding, vr_stabilization, startupinfo, logger):
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start_time),
        "-to", str(end_time),
        "-i", file_path,
        "-c:v", video_codec,
        "-preset", "fast" if not hardware_encoding else "p4"
    ]

    if not hardware_encoding:
        cmd.extend(["-crf", "23"])
    else:
        cmd.extend(["-cq", "25", "-rc", "vbr"])

    if vr_stabilization:
        if logger: logger("🎞️ Applying VR Anti-Shake filter...")
        cmd.extend(["-vf", "deshake=rx=64:ry=64:edge=mirror"])

    cmd.extend(audio_codec_flags)
    cmd.append(output_file)

    if logger:
        logger(f"✂️ Cutting horizontal clip ({start_time}s - {end_time}s)...")
        
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, startupinfo=startupinfo, check=True)

def _generate_vertical_clip(file_path, vert_output, start_time, end_time, video_codec, audio_codec_flags, hardware_encoding, vertical_mode, config, startupinfo, logger):
    if logger: logger(f"📱 Generating Vertical Shorts format ({vertical_mode})...")

    if vertical_mode == "Standard Center Crop":
        vf_command = "crop=ih*9/16:ih,scale=1080:1920"
        vert_cmd = [
            "ffmpeg", "-y",
            "-ss", str(start_time),
            "-to", str(end_time),
            "-i", file_path,
            "-vf", vf_command,
            "-c:v", video_codec, "-preset", "fast" if not hardware_encoding else "p4",
        ]
        if not hardware_encoding: vert_cmd.extend(["-crf", "23"])
        else: vert_cmd.extend(["-cq", "25", "-rc", "vbr"])

        vert_cmd.extend(audio_codec_flags)
        vert_cmd.append(vert_output)

    else:
        x, y, w, h = 0, 0, 400, 225

        if vertical_mode == "Facecam Top-Left": x, y = 0, 0
        elif vertical_mode == "Facecam Top-Right": x, y = 1520, 0
        elif vertical_mode == "Facecam Bottom-Left": x, y = 0, 855
        elif vertical_mode == "Facecam Bottom-Right": x, y = 1520, 855
        elif vertical_mode == "Custom Coordinates":
            # 🛡️ Sentinel: Validate crop inputs to prevent FFmpeg filter injection
            try:
                x = int(config.get("settings", {}).get("crop_x", "0"))
                y = int(config.get("settings", {}).get("crop_y", "0"))
                w = int(config.get("settings", {}).get("crop_w", "400"))
                h = int(config.get("settings", {}).get("crop_h", "225"))
            except ValueError:
                x, y, w, h = 0, 0, 400, 225
                if logger: logger("⚠️ Invalid crop coordinates, falling back to safe defaults.")

        filter_complex = f"[0:v]crop={w}:{h}:{x}:{y},scale=1080:840[cam];[0:v]crop=1080:1080:420:0[game];[cam][game]vstack=inputs=2[out]"
        
        vert_cmd = [
            "ffmpeg", "-y", 
            "-ss", str(start_time), 
            "-to", str(end_time), 
            "-i", file_path, 
            "-filter_complex", filter_complex,
            "-map", "[out]", "-map", "0:a",
            "-c:v", video_codec, "-preset", "fast" if not hardware_encoding else "p4",
        ]
        if not hardware_encoding: vert_cmd.extend(["-crf", "23"])
        else: vert_cmd.extend(["-cq", "25", "-rc", "vbr"])
        
        vert_cmd.extend(audio_codec_flags)
        vert_cmd.append(vert_output)

    subprocess.run(vert_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, startupinfo=startupinfo, check=True)

def _generate_thumbnail(target_for_thumb, thumb_file, start_time, end_time, startupinfo, logger):
    if logger: logger("📸 Generating clip thumbnail...")
    mid_point = (end_time - start_time) / 2
    thumb_cmd = [
        "ffmpeg", "-y", "-ss", str(mid_point), "-i", target_for_thumb,
        "-vframes", "1", "-vf", "scale=-1:200", "-q:v", "5", thumb_file
    ]
    subprocess.run(thumb_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, startupinfo=startupinfo, check=True)


def _process_single_clip(i, clip, file_path, base_name, output_dir, video_codec, audio_codec_flags, hardware_encoding, vr_stabilization, vertical_export, vertical_mode, config, startupinfo, logger, is_cancelled):
    if is_cancelled and is_cancelled():
        if logger: logger("🛑 Clip extraction aborted by user.")
        return None
        
    start_time = clip.get("start_time")
    end_time = clip.get("end_time")

    # 🛡️ Sentinel: Sanitize AI output to prevent path traversal
    raw_score = str(clip.get("virality_score", "N/A"))
    score = "".join(c for c in raw_score if c.isalnum() or c in "._-")

    if start_time is None or end_time is None:
        return None

    output_file = os.path.join(output_dir, f"{base_name}_clip{i+1}_score{score}.mp4")
    json_meta_file = os.path.join(output_dir, f"{base_name}_clip{i+1}_score{score}.json")

    created_files_for_clip = []

    try:
        _generate_horizontal_clip(file_path, output_file, start_time, end_time, video_codec, audio_codec_flags, hardware_encoding, vr_stabilization, startupinfo, logger)
        created_files_for_clip.append(output_file)

        with open(json_meta_file, 'w', encoding='utf-8') as meta_f:
            json.dump(clip, meta_f, indent=4)
            
        # --- VERTICAL AUTO-CROPPER ---
        if vertical_export:
            vert_output = output_file.replace(".mp4", "_vertical.mp4")
            
            if is_cancelled and is_cancelled():
                if logger: logger("🛑 Clip extraction aborted by user.")
                return created_files_for_clip
                
            _generate_vertical_clip(file_path, vert_output, start_time, end_time, video_codec, audio_codec_flags, hardware_encoding, vertical_mode, config, startupinfo, logger)
            created_files_for_clip.append(vert_output)

        # --- THUMBNAIL GENERATOR ---
        target_for_thumb = vert_output if vertical_export else output_file
        thumb_file = output_file.replace(".mp4", ".jpg")

        if is_cancelled and is_cancelled():
            if logger: logger("🛑 Clip extraction aborted by user.")
            return created_files_for_clip

        _generate_thumbnail(target_for_thumb, thumb_file, start_time, end_time, startupinfo, logger)

    except Exception as e:
        if logger:
            logger(f"❌ FFmpeg error on clip {i+1}: {e}")

    return created_files_for_clip


def extract_clips(file_path, clips_data, output_dir, logger, is_cancelled=None):
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    config = config_manager.load_config()
    vr_stabilization = config.get("settings", {}).get("vr_stabilization", False)
    vertical_export = config.get("settings", {}).get("vertical_export", False)
    vertical_mode = config.get("settings", {}).get("vertical_mode", "Standard Center Crop")
    hardware_encoding = config.get("settings", {}).get("hardware_encoding", False)
    audio_downmix = config.get("settings", {}).get("audio_downmix", True)

    gpu_codec = _get_gpu_codec(logger)

    video_codec = gpu_codec if hardware_encoding else "libx264"
    audio_codec_flags = ["-ac", "2", "-c:a", "aac", "-b:a", "192k"] if audio_downmix else ["-c:a", "copy"]

    startupinfo = _get_startupinfo()

    created_files = []
    for i, clip in enumerate(clips_data.get("clips", [])):
        clip_files = _process_single_clip(
            i, clip, file_path, base_name, output_dir,
            video_codec, audio_codec_flags, hardware_encoding,
            vr_stabilization, vertical_export, vertical_mode,
            config, startupinfo, logger, is_cancelled
        )

        if clip_files is None:
            break

        created_files.extend(clip_files)
        
    return created_files

def _validate_api_keys(config, chat_model, logger):
    openai_key = config.get("openai", {}).get("api_key", "")
    openai_base_url = config.get("openai", {}).get("base_url", "")
    google_key = config.get("google", {}).get("api_key", "")
    anthropic_key = config.get("anthropic", {}).get("api_key", "")
    xai_key = config.get("xai", {}).get("api_key", "")
    
    is_gemini_model = chat_model.startswith("gemini") or "gemini" in chat_model
    is_anthropic_model = chat_model.startswith("claude") and "openrouter" not in chat_model
    is_openrouter = "openrouter" in chat_model or openai_base_url != ""
    is_grok_model = chat_model.startswith("grok")
    
    if is_grok_model:
        openai_key = xai_key
        openai_base_url = "https://api.x.ai/v1"
    
    if is_gemini_model and not is_openrouter and not google_key:
        if logger: logger("❌ Error: Google API Key not set for Gemini model.")
        return False
    elif is_anthropic_model and not is_openrouter and not anthropic_key:
        if logger: logger("❌ Error: Anthropic API Key not set.")
        return False
    elif not is_gemini_model and not is_anthropic_model:
        if is_grok_model and not xai_key:
            if logger: logger("❌ Error: Grok/xAI API Key not set.")
            return False
        elif not is_grok_model and not openai_key:
            if logger: logger("❌ Error: OpenAI/Custom API Key not set.")
            return False
    return True

LANGUAGE_MAP = {
    "English": "en",
    "Spanish": "es",
    "French": "fr",
    "German": "de",
    "Italian": "it",
    "Portuguese": "pt",
    "Russian": "ru",
    "Japanese": "ja",
    "Korean": "ko",
    "Chinese": "zh",
    "Auto-Detect": None
}

def _transcribe_audio_to_segments(file_path, config, logger, is_cancelled):
    whisper_model_type = config.get("openai", {}).get("whisper_model", "base")
    language_setting = config.get("openai", {}).get("whisper_language", "English")

    if language_setting == "Auto-Detect":
        target_language = None
    elif language_setting in LANGUAGE_MAP:
        target_language = LANGUAGE_MAP[language_setting]
    else:
        # Fallback for custom inputs like "Dutch" -> "nl" if they enter the 2 letter code, else fallback to slicing
        target_language = language_setting.lower() if len(language_setting) == 2 else language_setting[:2].lower()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    if logger:
        if device == "cuda":
            gpu_name = torch.cuda.get_device_name(0)
            logger(f"🧠 Hardware Check: NVIDIA GPU Detected ({gpu_name})")
            logger("🚀 Transcribing at maximum speed...")
        else:
            logger("🐌 Hardware Check: CPU Detected (CUDA not available)")
            logger("⚠️ Transcription will take significantly longer...")

    if logger: logger(f"⏳ Loading Whisper '{whisper_model_type}' model into memory...")
    try:
        model = whisper.load_model(whisper_model_type, device=device)
    except Exception as e:
        if logger: logger(f"❌ Failed to load Whisper: {e}")
        return None

    if is_cancelled and is_cancelled(): return None
    
    if logger: logger("🎙️ Extracting audio track silently...")
    try:
        audio_array = extract_audio_hidden(file_path)
    except Exception as e:
        if logger: logger(f"❌ Audio extraction error: {e}")
        return None

    if is_cancelled and is_cancelled(): return None

    audio_peak_detection = config.get("settings", {}).get("audio_peak_detection", True)
    combat_detection = config.get("settings", {}).get("combat_detection", True)

    if logger:
        if audio_peak_detection or combat_detection:
            logger("🎙️ Transcribing audio and analyzing patterns (Loudness/Combat)...")
        else:
            logger("🎙️ Transcribing audio...")
            
    try:
        fp16_enabled = True if device == "cuda" else False
        progress_stream = WhisperProgressStream(logger)
        with contextlib.redirect_stdout(progress_stream):
            transcribe_kwargs = {
                "condition_on_previous_text": False,
                "beam_size": 1,
                "fp16": fp16_enabled,
                "verbose": True
            }
            if target_language is not None:
                transcribe_kwargs["language"] = target_language

            result = model.transcribe(audio_array, **transcribe_kwargs)
            
        raw_segments = result.get("segments", [])
        
        if audio_peak_detection or combat_detection:
            segments = analyze_audio_peaks(audio_array, raw_segments, peak_detection=audio_peak_detection, combat_detection=combat_detection)
            if logger: logger("✅ Transcription complete! Audio patterns analyzed.")
        else:
            segments = raw_segments
            if logger: logger("✅ Transcription complete!")
            
    except Exception as e:
        if logger: logger(f"❌ Transcription error: {e}")
        return None

    if not segments:
        if logger: logger("❌ No audio segments found in the transcription.")
        return None

    return segments

def _generate_clips_with_llm(segments, config, chat_model, prompt_text, logger):
    openai_key = config.get("openai", {}).get("api_key", "")
    openai_base_url = config.get("openai", {}).get("base_url", "")
    google_key = config.get("google", {}).get("api_key", "")
    anthropic_key = config.get("anthropic", {}).get("api_key", "")
    xai_key = config.get("xai", {}).get("api_key", "")

    is_gemini_model = chat_model.startswith("gemini") or "gemini" in chat_model
    is_anthropic_model = chat_model.startswith("claude") and "openrouter" not in chat_model
    is_openrouter = "openrouter" in chat_model or openai_base_url != ""
    is_grok_model = chat_model.startswith("grok")

    if is_grok_model:
        openai_key = xai_key
        openai_base_url = "https://api.x.ai/v1"

    all_clips = []
    
    full_transcript = "".join(
        f"[{seg['start']:.1f}s - {seg['end']:.1f}s] {seg['text'].strip()}\n"
        for seg in segments
    )

    # Estimate token count based on a common heuristic (1 token ~= 4 chars or ~0.75 words)
    # Using roughly 1.3 tokens per word as a general English baseline.
    word_count = full_transcript.count(' ') + 1 if full_transcript.strip() else 0
    estimated_tokens = int(word_count * 1.3)
    if logger:
        logger(f"📊 Extracted approx {estimated_tokens:,} tokens ({word_count:,} words) for the AI model's context window.")

    if is_gemini_model and not is_openrouter:
        if not HAS_GEMINI:
            if logger: logger("❌ Error: google-generativeai module missing.")
            return []
            
        if logger: logger(f"🌌 Routing to native Gemini Engine ({chat_model}) with {len(segments)} segments...")

        genai.configure(api_key=google_key)
        model = genai.GenerativeModel(
            model_name=chat_model,
            system_instruction=prompt_text
        )

        try:
            response = model.generate_content(
                f"Analyze this entire gaming transcript. The timestamps for each line are in brackets. Return strictly JSON.\n\n{full_transcript}",
                generation_config={"response_mime_type": "application/json"}
            )
            chunk_data = json.loads(response.text)
            found_clips = chunk_data.get("clips", [])
            if found_clips:
                if logger: logger(f"🎯 Gemini found {len(found_clips)} clip(s) in the VOD!")
                all_clips.extend(found_clips)
            else:
                if logger: logger(f"🤷‍♂️ Gemini finished but didn't find any clips.")
        except Exception as e:
            if logger: logger(f"❌ Gemini API Error: {e}")

    elif is_anthropic_model:
        if not HAS_ANTHROPIC:
            if logger: logger("❌ Error: anthropic python module missing.")
            return []
            
        if logger: logger(f"🌌 Routing to native Anthropic Engine ({chat_model}) with {len(segments)} segments...")

        client = anthropic.Anthropic(api_key=anthropic_key)
        
        try:
            response = client.messages.create(
                model=chat_model,
                max_tokens=4000,
                system=prompt_text,
                messages=[
                    {"role": "user", "content": f"Analyze this entire gaming transcript. Return strictly valid JSON containing a 'clips' array with 'start_time', 'end_time', 'virality_score', and 'reasoning'. Do not include markdown formatting.\n\n{full_transcript}"}
                ]
            )
            
            raw_content = response.content[0].text.strip()
            if raw_content.startswith("```json"):
                raw_content = raw_content.partition("```json")[2].partition("```")[0].strip()
            elif raw_content.startswith("```"):
                raw_content = raw_content.partition("```")[2].partition("```")[0].strip()

            chunk_data = json.loads(raw_content)
            found_clips = chunk_data.get("clips", [])
            if found_clips:
                if logger: logger(f"🎯 Claude found {len(found_clips)} clip(s) in the VOD!")
                all_clips.extend(found_clips)
            else:
                if logger: logger(f"🤷‍♂️ Claude finished but didn't find any clips.")
                
        except Exception as e:
            if logger: logger(f"❌ Anthropic API Error: {e}")

    else:
        if logger: 
            if is_openrouter: logger(f"🤖 Routing to via Custom Base URL ({chat_model}) with {len(segments)} segments...")
            else: logger(f"🤖 Routing to OpenAI Engine ({chat_model}) with {len(segments)} segments...")
            
        client_args = {"api_key": openai_key}
        if openai_base_url:
            client_args["base_url"] = openai_base_url
            
        client = OpenAI(**client_args)

        try:
            response = client.chat.completions.create(
                model=chat_model,
                response_format={ "type": "json_object" },
                messages=[
                    {"role": "system", "content": prompt_text},
                    {"role": "user", "content": f"Analyze this entire gaming transcript. Return strictly JSON.\n\n{full_transcript}"}
                ]
            )
            chunk_data = json.loads(response.choices[0].message.content)
            found_clips = chunk_data.get("clips", [])
            if found_clips:
                if logger: logger(f"🎯 Found {len(found_clips)} clip(s)!")
                all_clips.extend(found_clips)
            else:
                if logger: logger(f"🤷‍♂️ No clips found.")
        except Exception as e:
            if logger: logger(f"❌ OpenAI/Custom API Error: {e}")

    return all_clips

def process_video(file_path, prompt_profile="Omni-Genre Broad Net", logger=None, is_cancelled=None):
    """Main orchestration function for analyzing and cutting clips."""
    config = config_manager.load_config()
    chat_model = config.get("openai", {}).get("chat_model", "gpt-4o")
    clips_dir = config.get("settings", {}).get("clips_dir", "")

    if not clips_dir:
        if logger: logger("❌ Error: Generated Clips folder not set in Settings.")
        return

    if not _validate_api_keys(config, chat_model, logger):
        return

    segments = _transcribe_audio_to_segments(file_path, config, logger, is_cancelled)
    if not segments:
        return

    if is_cancelled and is_cancelled(): return

    prompt_text = config.get("prompts", {}).get("profiles", {}).get(prompt_profile, "Find the best 15-90s moments. Output JSON.")

    all_clips = _generate_clips_with_llm(segments, config, chat_model, prompt_text, logger)

    if all_clips:
        if logger: logger(f"🎬 Sending {len(all_clips)} total timestamp(s) to FFmpeg...")
        final_clips_data = {"clips": all_clips}
        created = extract_clips(file_path, final_clips_data, clips_dir, logger, is_cancelled)
        if logger: logger(f"✨ Successfully exported {len(created)} file(s) to your folder!")
    else:
        if logger: logger("🤷‍♂️ AI finished scanning the VOD but didn't extract any clips.")