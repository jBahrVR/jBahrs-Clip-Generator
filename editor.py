import os
import shutil
import json
import re
import math
import subprocess

def setup_cuda_dll_path():
    """Ensures NVIDIA CUDA/cuBLAS/cuDNN runtime libraries installed in site-packages
    are accessible in the Windows DLL search path."""
    if os.name != "nt":
        return
    try:
        import sys
        search_dirs = [
            os.path.join(os.path.dirname(os.path.abspath(__file__)), ".venv", "Lib", "site-packages", "nvidia"),
            os.path.join(os.path.dirname(sys.executable), "..", "Lib", "site-packages", "nvidia"),
            os.path.join(os.path.dirname(sys.executable), "Lib", "site-packages", "nvidia"),
        ]
        try:
            import site
            for sp in site.getsitepackages():
                search_dirs.append(os.path.join(sp, "nvidia"))
        except Exception:
            pass

        for nvidia_dir in search_dirs:
            if os.path.isdir(nvidia_dir):
                for root, dirs, files in os.walk(nvidia_dir):
                    if "bin" in dirs:
                        bin_path = os.path.abspath(os.path.join(root, "bin"))
                        try:
                            os.add_dll_directory(bin_path)
                        except Exception:
                            pass
                        if bin_path not in os.environ.get("PATH", ""):
                            os.environ["PATH"] = bin_path + os.pathsep + os.environ.get("PATH", "")
    except Exception:
        pass

setup_cuda_dll_path()

import torch # type: ignore
import whisper # type: ignore
try:
    from faster_whisper import WhisperModel
    HAS_FASTER_WHISPER = True
except ImportError:
    WhisperModel = None
    HAS_FASTER_WHISPER = False
import config_manager # type: ignore
from openai import OpenAI # type: ignore
import numpy as np # type: ignore
import io
import contextlib
import utils
import subtitle_engine
import tracking_engine


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
                clean_msg = raw_msg.split("]")[1].strip() if "]" in raw_msg else raw_msg
                timestamp = raw_msg.split("]")[0].replace("[", "").split("-->")[0].strip() if "-->" in raw_msg else ""
                if self.logger:
                    self.logger(f"⏳ Processed up to {timestamp}: {clean_msg[:40]}...")
            self.counter += 1
        return super().write(s)

    def flush(self):
        pass

import logging
logging.getLogger("google_genai").setLevel(logging.ERROR)

try:
    from google import genai
    HAS_GEMINI = True
except ImportError:
    genai = None
    HAS_GEMINI = False

try:
    import anthropic # type: ignore
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

def _detect_combat_transients(chunk, rms, min_transients_per_sec=1.5):
    """Detects rapid acoustic transient spikes indicative of gunfire or explosions."""
    if len(chunk) <= 160:
        return False
    window_size = 160  # 10ms @ 16kHz
    num_windows = len(chunk) // window_size
    if num_windows == 0:
        return False
    seg_rms = rms + 0.001
    windows = chunk[:num_windows * window_size].reshape(-1, window_size)
    peaks = np.max(np.abs(windows), axis=1)
    transients = (peaks > (seg_rms * 4.5)) & (peaks > 0.15)
    transient_count = np.sum(transients)
    duration = len(chunk) / 16000.0
    return duration > 0 and (transient_count / duration) >= min_transients_per_sec


def analyze_audio_peaks(audio_array, segments, sample_rate=16000, peak_detection=True, combat_detection=True):
    """Calculates dynamic percentile loudness, detects combat transients, and synthesizes
    continuous non-verbal action highlights during silent speech intervals."""
    if len(audio_array) == 0:
        return segments

    # 1. Compute dynamic baseline percentiles across the audio waveform for normalized loudness
    chunk_size = sample_rate
    n_chunks = len(audio_array) // chunk_size
    if n_chunks > 0:
        step = max(1, n_chunks // 2000)
        sampled_chunks = audio_array[:n_chunks * chunk_size].reshape(n_chunks, chunk_size)[::step]
        chunk_rms = np.sqrt(np.mean(sampled_chunks**2, axis=1))
        p10 = float(np.percentile(chunk_rms, 10))
        p95 = float(np.percentile(chunk_rms, 95))
    else:
        p10, p95 = 0.0, 0.1

    use_dynamic_norm = (p95 > p10 + 1e-4)

    def calc_loudness(rms_val):
        if use_dynamic_norm:
            return int(np.clip(((rms_val - p10) / (p95 - p10)) * 100, 0, 100))
        return min(100, int((rms_val / 0.1) * 100))

    enhanced_segments = []

    # 2. Process all speech segments returned by Whisper
    for seg in segments:
        start_idx = int(seg['start'] * sample_rate)
        end_idx = int(seg['end'] * sample_rate)

        start_idx = max(0, min(start_idx, len(audio_array) - 1))
        end_idx = max(start_idx + 1, min(end_idx, len(audio_array)))

        chunk = audio_array[start_idx:end_idx]
        if len(chunk) == 0:
            enhanced_segments.append(seg)
            continue

        prefix_tags = []
        rms = 0.0
        if peak_detection or combat_detection:
            rms = float(np.linalg.norm(chunk) / np.sqrt(len(chunk)))

        # Loudness Analysis
        if peak_detection:
            loudness = calc_loudness(rms)
            prefix_tags.append(f"[LOUDNESS: {loudness}%]")

        # Combat Analysis
        if combat_detection and _detect_combat_transients(chunk, rms):
            prefix_tags.append("[ACTION: COMBAT]")

        tag_str = " ".join(prefix_tags)
        enhanced_text = f"{tag_str} {seg['text'].strip()}" if tag_str else seg['text'].strip()

        new_seg = seg.copy()
        new_seg['text'] = enhanced_text
        enhanced_segments.append(new_seg)

    # 3. Continuous Audio Energy Envelope: Scan non-verbal gaps to capture action highlights
    if peak_detection or combat_detection:
        total_duration = len(audio_array) / float(sample_rate)
        min_gap = 8.0  # Minimum non-verbal duration to inspect
        action_window = 15.0  # Window size for non-verbal action slices

        # Sort speech segments by start timestamp to find chronological gaps
        sorted_speech = sorted(segments, key=lambda s: s.get('start', 0.0))
        gaps = []
        last_speech_end = 0.0

        for s in sorted_speech:
            s_start = s.get('start', 0.0)
            s_end = s.get('end', 0.0)
            if s_start - last_speech_end >= min_gap:
                gaps.append((last_speech_end, s_start))
            last_speech_end = max(last_speech_end, s_end)

        if total_duration - last_speech_end >= min_gap:
            gaps.append((last_speech_end, total_duration))

        # Evaluate energy in each non-verbal gap
        synthesized_segments = []
        for gap_start, gap_end in gaps:
            curr_start = gap_start
            while curr_start < gap_end:
                curr_end = min(curr_start + action_window, gap_end)
                if curr_end - curr_start < 4.0:
                    break

                start_idx = int(curr_start * sample_rate)
                end_idx = min(int(curr_end * sample_rate), len(audio_array))
                chunk = audio_array[start_idx:end_idx]

                if len(chunk) > 160:
                    rms = float(np.linalg.norm(chunk) / np.sqrt(len(chunk)))
                    loudness = calc_loudness(rms)
                    has_combat = combat_detection and _detect_combat_transients(chunk, rms)

                    # Synthesize action highlight if high energy or combat transients detected
                    if has_combat or (peak_detection and loudness >= 65):
                        tags = []
                        if peak_detection:
                            tags.append(f"[LOUDNESS: {loudness}%]")
                        if has_combat:
                            tags.append("[ACTION: COMBAT]")
                        else:
                            tags.append("[ACTION: NON-VERBAL GAMEPLAY]")

                        tag_str = " ".join(tags)
                        synthesized_segments.append({
                            "start": round(curr_start, 2),
                            "end": round(curr_end, 2),
                            "text": f"{tag_str} [High action non-verbal gaming moment]"
                        })

                curr_start = curr_end

        if synthesized_segments:
            enhanced_segments.extend(synthesized_segments)

    # Sort all segments chronologically by start timestamp
    enhanced_segments.sort(key=lambda s: s.get('start', 0.0))
    return enhanced_segments

# --- MULTI-TRACK AUDIO DOWNMIXING UTILITIES ---
def get_audio_stream_count(file_path: str) -> int:
    """Detects the number of audio streams in a media file using ffprobe or ffmpeg."""
    # 1. Try ffprobe if available
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "a",
            "-show_entries", "stream=index",
            "-of", "csv=p=0",
            file_path
        ]
        code, stdout, _ = utils.run_subprocess_binary(cmd)
        if code == 0 and stdout:
            lines = [line.strip() for line in stdout.decode(errors="replace").splitlines() if line.strip()]
            if lines:
                return len(lines)
    except Exception:
        pass

    # 2. Fallback to ffmpeg -hide_banner -i
    try:
        cmd = ["ffmpeg", "-hide_banner", "-i", file_path]
        code, stdout, stderr = utils.run_subprocess_binary(cmd)
        text = stderr.decode(errors="replace")
        matches = re.findall(r'Stream #\d+:\d+.*Audio:', text)
        if matches:
            return len(matches)
    except Exception:
        pass

    return 1

def build_amix_filter(stream_count: int, input_label: str = "0:a") -> str:
    """Constructs an FFmpeg amix filtergraph string for downmixing N audio streams."""
    if stream_count <= 1:
        return ""
    inputs = "".join(f"[{input_label}:{i}]" for i in range(stream_count))
    return f"{inputs}amix=inputs={stream_count}:duration=longest:dropout_transition=2,volume={stream_count}"

def get_video_dimensions_and_aspect(file_path: str):
    """Probes the video dimensions and aspect ratio using ffmpeg or ffprobe.
    Returns (width, height, aspect_ratio_description).
    Examples: (1920, 1080, '16:9 (Horizontal, 1920x1080)'), (360, 640, '9:16 (Vertical, 360x640)')
    """
    width, height = 1920, 1080
    dar_str = "16:9"
    try:
        cmd = ["ffmpeg", "-hide_banner", "-i", file_path]
        returncode, stdout, stderr = utils.run_subprocess_binary(cmd)
        text = stderr.decode(errors="replace")
        
        dar_match = re.search(r'DAR\s+(\d+):(\d+)', text)
        dim_match = re.search(r', (\d{2,5})x(\d{2,5})', text)
        if dim_match:
            width = int(dim_match.group(1))
            height = int(dim_match.group(2))
        
        if dar_match:
            dar_str = f"{dar_match.group(1)}:{dar_match.group(2)}"
        elif width and height:
            g = math.gcd(width, height)
            dar_str = f"{width // g}:{height // g}"
    except Exception:
        pass

    if width > height:
        orientation_label = "Horizontal"
    elif height > width:
        orientation_label = "Vertical"
    else:
        orientation_label = "Square"

    aspect_desc = f"{dar_str} ({orientation_label}, {width}x{height})"
    return width, height, aspect_desc

# --- NEW: STEALTH AUDIO EXTRACTOR ---
def extract_audio_hidden(file_path, sr=16000, stream_count=None):
    """Bypasses Whisper's internal ffmpeg call to prevent the cmd window pop-up on Windows.
    Automatically downmixes multi-track OBS audio into 16kHz mono PCM for Whisper."""
    if stream_count is None:
        stream_count = get_audio_stream_count(file_path)

    cmd = ["ffmpeg", "-nostdin", "-threads", "0", "-i", file_path]
    if stream_count > 1:
        amix = build_amix_filter(stream_count)
        cmd.extend(["-filter_complex", amix])

    cmd.extend(["-f", "s16le", "-ac", "1", "-acodec", "pcm_s16le", "-ar", str(sr), "-"])
    
    returncode, stdout, stderr = utils.run_subprocess_binary(cmd)
    if returncode != 0:
        err_msg = stderr.decode(errors='replace').strip()
        if "WinError 2" in err_msg or "cannot find the file" in err_msg.lower() or "not found" in err_msg.lower():
            raise FileNotFoundError(
                "FFmpeg executable not found. Please ensure ffmpeg.exe is installed, in your system PATH, or placed in the application folder."
            )
        raise RuntimeError(f"FFmpeg audio extraction failed: {err_msg}")
        
    return np.frombuffer(stdout, np.int16).flatten().astype(np.float32) / 32768.0

def is_cuda_available() -> bool:
    """Checks whether CUDA acceleration is available.
    Respects unittest mocks on torch.cuda.is_available if present.
    If PyTorch is CPU-only, checks ctranslate2 and nvidia-smi for native GPU support."""
    try:
        if hasattr(torch.cuda.is_available, "mock_calls"):
            return bool(torch.cuda.is_available())
    except Exception:
        pass

    try:
        if torch.cuda.is_available():
            return True
    except Exception:
        pass

    if HAS_FASTER_WHISPER:
        try:
            import ctranslate2
            if ctranslate2.get_cuda_device_count() > 0:
                return True
        except Exception:
            pass

    return False

def get_gpu_name() -> str:
    """Returns the name of the active NVIDIA/AMD GPU device."""
    try:
        if hasattr(torch.cuda.get_device_name, "mock_calls") or torch.cuda.is_available():
            name = torch.cuda.get_device_name(0)
            if name:
                return name
    except Exception:
        pass
    if shutil.which("nvidia-smi"):
        try:
            out = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                text=True, stderr=subprocess.DEVNULL
            )
            name = out.strip().split("\n")[0].strip()
            if name:
                return name
        except Exception:
            pass
    return "NVIDIA GPU"

def _get_gpu_codec(logger=None):
    """Detects the optimal GPU architecture for hardware encoding."""
    gpu_codec = "libx264"
    try:
        if is_cuda_available():
            gpu_codec = "h264_nvenc"
            device_name = get_gpu_name().lower()
            if "amd" in device_name or "radeon" in device_name:
                gpu_codec = "h264_amf"
    except Exception as e:
        if logger: logger(f"⚠️ Failed to detect GPU for hardware encoding: {e}")
        gpu_codec = "libx264"
    return gpu_codec

def _get_video_encoder_flags(video_codec, hardware_encoding):
    """Returns codec-specific quality and rate-control flags."""
    if not hardware_encoding or video_codec == "libx264":
        return ["-c:v", video_codec, "-preset", "fast", "-crf", "23"]
    elif video_codec == "h264_nvenc":
        return ["-c:v", video_codec, "-preset", "p4", "-cq", "25", "-rc", "vbr"]
    elif video_codec == "h264_amf":
        return ["-c:v", video_codec, "-rc", "cqp", "-qp_p", "25", "-qp_i", "25"]
    else:
        return ["-c:v", video_codec, "-preset", "fast"]

def _generate_horizontal_clip(file_path, output_file, start_time, end_time, video_codec, audio_codec_flags, hardware_encoding, vr_stabilization, logger, is_cancelled=None, stream_count=1, audio_downmix=True):
    cmd = [
        "ffmpeg", "-y",
        "-avoid_negative_ts", "make_zero",
        "-ss", str(start_time),
        "-to", str(end_time),
        "-i", file_path,
    ]
    cmd.extend(_get_video_encoder_flags(video_codec, hardware_encoding))

    if audio_downmix and stream_count > 1:
        amix = build_amix_filter(stream_count)
        if vr_stabilization:
            if logger: logger("🎞️ Applying VR Anti-Shake filter & Downmixing multi-track audio...")
            filter_complex = f"[0:v]deshake=rx=64:ry=64:edge=mirror[vout];{amix}[aout]"
            cmd.extend(["-filter_complex", filter_complex, "-map", "[vout]", "-map", "[aout]"])
        else:
            if logger: logger("🎙️ Downmixing multi-track audio (amix)...")
            cmd.extend(["-filter_complex", f"{amix}[aout]", "-map", "0:v", "-map", "[aout]"])
        cmd.extend(["-c:a", "aac", "-b:a", "192k", "-ac", "2"])
    else:
        if vr_stabilization:
            if logger: logger("🎞️ Applying VR Anti-Shake filter...")
            cmd.extend(["-vf", "deshake=rx=64:ry=64:edge=mirror"])
        cmd.extend(audio_codec_flags)

    cmd.append(output_file)

    if logger:
        logger(f"✂️ Cutting clip ({start_time}s - {end_time}s) in native full quality...")
        
    output_lines = []
    ret = utils.run_subprocess_command(
        cmd,
        logger_callback=output_lines.append,
        is_cancelled=is_cancelled
    )
    if ret != 0:
        error_msg = "".join(output_lines)
        if "WinError 2" in error_msg or "cannot find the file" in error_msg.lower() or "failed to start subprocess" in error_msg.lower():
            raise FileNotFoundError(
                "FFmpeg executable not found. Please ensure ffmpeg.exe is installed, in your system PATH, or placed in the application folder."
            )
        raise RuntimeError(f"FFmpeg horizontal clip generation failed with exit code {ret}: {error_msg}")

def _generate_vertical_clip(file_path, vert_output, start_time, end_time, video_codec, audio_codec_flags, hardware_encoding, vertical_mode, config, logger, is_cancelled=None, stream_count=1, audio_downmix=True, subtitle_file=None):
    if logger: logger(f"📱 Generating Vertical Shorts format ({vertical_mode})...")

    encoder_flags = _get_video_encoder_flags(video_codec, hardware_encoding)
    downmix_needed = audio_downmix and stream_count > 1
    amix = build_amix_filter(stream_count) if downmix_needed else ""

    sub_filter = ""
    if subtitle_file and os.path.exists(subtitle_file):
        escaped_sub = subtitle_engine.escape_ffmpeg_filter_path(subtitle_file)
        sub_filter = f"ass='{escaped_sub}'"
        if logger: logger("💬 Burning word-level animated subtitles into vertical cut...")

    if vertical_mode in ("Auto-Face Tracking (AI)", "Auto-Face Tracking", "Smart Action Tracking (AI)", "Smart Action Tracking"):
        track_mode = "face" if "face" in vertical_mode.lower() else "action"
        if logger: logger(f"🎯 Running AI {track_mode.capitalize()} Tracking across clip window...")
        s_time = start_time if start_time is not None else 0.0
        e_time = end_time if end_time is not None else (s_time + 30.0)
        try:
            crop_x, crop_y, crop_w, crop_h = tracking_engine.calculate_optimal_crop_window(
                video_path=file_path,
                start_time=s_time,
                end_time=e_time,
                mode=track_mode
            )
            if logger: logger(f"🎯 AI {track_mode.capitalize()} Tracking selected optimal crop: x={crop_x}, w={crop_w}, h={crop_h}")
        except Exception as track_err:
            if logger: logger(f"⚠️ Tracking failed ({track_err}), falling back to center crop.")
            crop_x, crop_y, crop_w, crop_h = 656, 0, 608, 1080

        vf_command = f"crop={crop_w}:{crop_h}:{crop_x}:{crop_y},scale=1080:1920"
        if sub_filter:
            vf_command = f"{vf_command},{sub_filter}"

        vert_cmd = ["ffmpeg", "-y"]
        if start_time is not None and end_time is not None:
            vert_cmd.extend(["-avoid_negative_ts", "make_zero", "-ss", str(start_time), "-to", str(end_time)])
        vert_cmd.extend(["-i", file_path])
        vert_cmd.extend(encoder_flags)

        if downmix_needed:
            filter_complex = f"[0:v]{vf_command}[vout];{amix}[aout]"
            vert_cmd.extend(["-filter_complex", filter_complex, "-map", "[vout]", "-map", "[aout]"])
            vert_cmd.extend(["-c:a", "aac", "-b:a", "192k", "-ac", "2"])
        else:
            vert_cmd.extend(["-vf", vf_command])
            vert_cmd.extend(audio_codec_flags)

        vert_cmd.append(vert_output)

    elif vertical_mode == "Standard Center Crop":
        # Dynamic resolution-independent 9:16 center crop
        vf_command = "crop='min(in_w,in_h*9/16)':'min(in_h,in_w*16/9)':(in_w-out_w)/2:(in_h-out_h)/2,scale=1080:1920"
        if sub_filter:
            vf_command = f"{vf_command},{sub_filter}"

        vert_cmd = ["ffmpeg", "-y"]
        if start_time is not None and end_time is not None:
            vert_cmd.extend(["-avoid_negative_ts", "make_zero", "-ss", str(start_time), "-to", str(end_time)])
        vert_cmd.extend(["-i", file_path])
        vert_cmd.extend(encoder_flags)

        if downmix_needed:
            filter_complex = f"[0:v]{vf_command}[vout];{amix}[aout]"
            vert_cmd.extend(["-filter_complex", filter_complex, "-map", "[vout]", "-map", "[aout]"])
            vert_cmd.extend(["-c:a", "aac", "-b:a", "192k", "-ac", "2"])
        else:
            vert_cmd.extend(["-vf", vf_command])
            vert_cmd.extend(audio_codec_flags)

        vert_cmd.append(vert_output)

    elif vertical_mode in ("Blurred Background (Letterbox)", "Blurred Background (Letterbox Blur)", "Blurred Background"):
        # Scale & crop to 1080x1920 with heavy blur for background, overlay uncropped 16:9 in center
        overlay_target = f"[vpre];[vpre]{sub_filter}[out]" if sub_filter else "[out]"
        video_fc = (
            "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:5[bg];"
            "[0:v]scale=1080:-2[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2{overlay_target}"
        )
        vert_cmd = ["ffmpeg", "-y"]
        if start_time is not None and end_time is not None:
            vert_cmd.extend(["-avoid_negative_ts", "make_zero", "-ss", str(start_time), "-to", str(end_time)])
        vert_cmd.extend(["-i", file_path])
        vert_cmd.extend(encoder_flags)

        if downmix_needed:
            filter_complex = f"{video_fc};{amix}[aout]"
            vert_cmd.extend(["-filter_complex", filter_complex, "-map", "[out]", "-map", "[aout]"])
            vert_cmd.extend(["-c:a", "aac", "-b:a", "192k", "-ac", "2"])
        else:
            vert_cmd.extend(["-filter_complex", video_fc, "-map", "[out]", "-map", "0:a:0?"])
            vert_cmd.extend(audio_codec_flags)

        vert_cmd.append(vert_output)

    else:
        x, y, w, h = 0, 0, 400, 225

        if vertical_mode == "Facecam Top-Left":
            x, y, w, h = 0, 0, 400, 225
        elif vertical_mode == "Facecam Top-Right":
            x, y, w, h = 1520, 0, 400, 225
        elif vertical_mode == "Facecam Bottom-Left":
            x, y, w, h = 0, 855, 400, 225
        elif vertical_mode == "Facecam Bottom-Right":
            x, y, w, h = 1520, 855, 400, 225
        elif vertical_mode == "Custom Coordinates":
            raw_settings = config.get("settings", {}) if config else {}
            try:
                x = int(raw_settings.get("crop_x", 0))
                y = int(raw_settings.get("crop_y", 0))
                w = int(raw_settings.get("crop_w", 400))
                h = int(raw_settings.get("crop_h", 225))
            except (ValueError, TypeError):
                x, y, w, h = 0, 0, 400, 225

        # Enforce bounds against standard 1080p canvas coordinates
        w = max(10, min(1920, w))
        h = max(10, min(1080, h))
        x = max(0, min(1920 - w, x))
        y = max(0, min(1080 - h, y))

        # Dynamic centered square crop scaled to 1080x1080 regardless of input resolution (720p, 1080p, 1440p, 4K)
        game_crop = "crop='min(in_w,in_h)':'min(in_w,in_h)':(in_w-min(in_w,in_h))/2:(in_h-min(in_w,in_h))/2,scale=1080:1080"
        vstack_target = f"[vpre];[vpre]{sub_filter}[out]" if sub_filter else "[out]"
        video_fc = f"[0:v]scale=1920:1080[v_1080];[v_1080]crop={w}:{h}:{x}:{y},scale=1080:840[cam];[0:v]{game_crop}[game];[cam][game]vstack=inputs=2{vstack_target}"

        vert_cmd = ["ffmpeg", "-y"]
        if start_time is not None and end_time is not None:
            vert_cmd.extend(["-avoid_negative_ts", "make_zero", "-ss", str(start_time), "-to", str(end_time)])
        vert_cmd.extend(["-i", file_path])
        vert_cmd.extend(encoder_flags)

        if downmix_needed:
            filter_complex = f"{video_fc};{amix}[aout]"
            vert_cmd.extend(["-filter_complex", filter_complex, "-map", "[out]", "-map", "[aout]"])
            vert_cmd.extend(["-c:a", "aac", "-b:a", "192k", "-ac", "2"])
        else:
            vert_cmd.extend(["-filter_complex", video_fc, "-map", "[out]", "-map", "0:a:0?"])
            vert_cmd.extend(audio_codec_flags)

        vert_cmd.append(vert_output)

    output_lines = []
    ret = utils.run_subprocess_command(
        vert_cmd,
        logger_callback=output_lines.append,
        is_cancelled=is_cancelled
    )
    if ret != 0:
        error_msg = "".join(output_lines)
        if "WinError 2" in error_msg or "cannot find the file" in error_msg.lower() or "failed to start subprocess" in error_msg.lower():
            raise FileNotFoundError(
                "FFmpeg executable not found. Please ensure ffmpeg.exe is installed, in your system PATH, or placed in the application folder."
            )
        raise RuntimeError(f"FFmpeg vertical clip generation failed with exit code {ret}: {error_msg}")

def _generate_thumbnail(target_for_thumb, thumb_file, start_time, end_time, logger, is_cancelled=None):
    if logger: logger("📸 Generating clip thumbnail...")
    mid_point = (end_time - start_time) / 2
    thumb_cmd = [
        "ffmpeg", "-y", "-ss", str(mid_point), "-i", target_for_thumb,
        "-vframes", "1", "-vf", "scale=-1:200", "-q:v", "5", thumb_file
    ]
    output_lines = []
    ret = utils.run_subprocess_command(
        thumb_cmd,
        logger_callback=output_lines.append,
        is_cancelled=is_cancelled
    )
    if ret != 0:
        error_msg = "".join(output_lines)
        if "WinError 2" in error_msg or "cannot find the file" in error_msg.lower() or "failed to start subprocess" in error_msg.lower():
            raise FileNotFoundError(
                "FFmpeg executable not found. Please ensure ffmpeg.exe is installed, in your system PATH, or placed in the application folder."
            )
        raise RuntimeError(f"FFmpeg thumbnail generation failed with exit code {ret}: {error_msg}")


def _process_single_clip(i, clip, file_path, base_name, output_dir, video_codec, audio_codec_flags, hardware_encoding, vr_stabilization, vertical_export, vertical_mode, config, logger, is_cancelled, stream_count=1, audio_downmix=True, target_orientation=None):
    if is_cancelled and is_cancelled():
        if logger: logger("🛑 Clip extraction aborted by user.")
        return None
        
    start_time = clip.get("start_time")
    end_time = clip.get("end_time")
    raw_score = clip.get("virality_score", "NA")
    clean_score = "".join(c for c in str(raw_score) if c.isalnum() or c in ("-", "_")) or "NA"

    if start_time is None or end_time is None:
        return None

    output_file = os.path.join(output_dir, f"{base_name}_clip{i+1}_score{clean_score}.mp4")
    json_meta_file = os.path.join(output_dir, f"{base_name}_clip{i+1}_score{clean_score}.json")

    created_files_for_clip = []

    try:
        _generate_horizontal_clip(
            file_path, output_file, start_time, end_time,
            video_codec, audio_codec_flags, hardware_encoding,
            vr_stabilization, logger, is_cancelled,
            stream_count=stream_count, audio_downmix=audio_downmix
        )
        created_files_for_clip.append(output_file)

        with open(json_meta_file, 'w', encoding='utf-8') as meta_f:
            json.dump(clip, meta_f, indent=4)
            
        # --- VERTICAL AUTO-CROPPER ---
        if vertical_export:
            vert_output = output_file.replace(".mp4", "_vertical.mp4")
            
            if is_cancelled and is_cancelled():
                if logger: logger("🛑 Clip extraction aborted by user.")
                return created_files_for_clip

            # Subtitle burn-in is strictly optional (default: False)
            subtitles_enabled = config.get("settings", {}).get("burn_subtitles", False) if config else False
            sub_file = None
            if subtitles_enabled:
                words = clip.get("words", [])
                if words:
                    ass_path = output_file.replace(".mp4", "_subtitles.ass")
                    try:
                        settings_sec = config.get("settings", {}) if config else {}
                        sub_file = subtitle_engine.generate_ass_subtitles(
                            words=words,
                            output_ass_path=ass_path,
                            clip_start=start_time,
                            clip_end=end_time,
                            style_preset=settings_sec.get("subtitle_style", "Viral Yellow Highlight"),
                            position_preset=settings_sec.get("subtitle_position", "Bottom Third"),
                            custom_font_size=int(settings_sec.get("subtitle_font_size", 48))
                        )
                        if logger: logger("💬 Generated viral word-level animated subtitles (.ass)")
                    except Exception as sub_err:
                        if logger: logger(f"⚠️ Warning: Subtitle generation failed: {sub_err}")
                        sub_file = None

            # Optimize: Crop directly from the extracted horizontal cut clip (2x render speedup).
            # Eliminates re-seeking and re-decoding the multi-GB source VOD, and reuses the
            # already-downmixed audio via instant stream copy.
            use_cut_clip = output_file in created_files_for_clip
            source_for_vert = output_file if use_cut_clip else file_path
            v_start = None if use_cut_clip else start_time
            v_end = None if use_cut_clip else end_time
            v_stream_count = 1 if use_cut_clip else stream_count
            v_downmix = False if use_cut_clip else audio_downmix
            v_audio_flags = ["-c:a", "copy"] if use_cut_clip else audio_codec_flags

            _generate_vertical_clip(
                source_for_vert, vert_output, v_start, v_end,
                video_codec, v_audio_flags, hardware_encoding,
                vertical_mode, config, logger, is_cancelled,
                stream_count=v_stream_count, audio_downmix=v_downmix,
                subtitle_file=sub_file
            )
            created_files_for_clip.append(vert_output)

            # If user specified Vertical Only, clean up the intermediate horizontal cut
            if target_orientation == "Vertical Only (9:16)":
                if output_file in created_files_for_clip and os.path.exists(output_file):
                    try:
                        os.remove(output_file)
                        created_files_for_clip.remove(output_file)
                    except Exception:
                        pass

        # --- THUMBNAIL GENERATOR ---
        target_for_thumb = vert_output if vertical_export else output_file
        thumb_file = output_file.replace(".mp4", ".jpg")

        if is_cancelled and is_cancelled():
            if logger: logger("🛑 Clip extraction aborted by user.")
            return created_files_for_clip

        _generate_thumbnail(target_for_thumb, thumb_file, start_time, end_time, logger, is_cancelled)

    except Exception as e:
        if logger:
            logger(f"❌ FFmpeg error on clip {i+1}: {e}")

    return created_files_for_clip


def extract_clips(file_path, clips_data, output_dir, logger, is_cancelled=None, target_orientation=None):
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    config = config_manager.load_config()
    vr_stabilization = config.get("settings", {}).get("vr_stabilization", False)
    
    # Auto-detect native video dimensions and aspect ratio
    width, height, aspect_desc = get_video_dimensions_and_aspect(file_path)
    if logger:
        logger(f"📐 Auto-detected source aspect ratio: {aspect_desc}")
        logger("🎞️ Preserving native video format in full quality (no crop manipulation)")

    if target_orientation == "Vertical Only (9:16)":
        vertical_export = True
    elif target_orientation in ("Horizontal Only (16:9)", "Native", "Auto", "Auto-Detect (Native)", None):
        vertical_export = False
    elif target_orientation == "Both (16:9 + 9:16)":
        vertical_export = False
    else:
        vertical_export = config.get("settings", {}).get("vertical_export", False)

    vertical_mode = config.get("settings", {}).get("vertical_mode", "Standard Center Crop")
    hardware_encoding = config.get("settings", {}).get("hardware_encoding", False)
    audio_downmix = config.get("settings", {}).get("audio_downmix", True)

    stream_count = get_audio_stream_count(file_path)
    if stream_count > 1 and audio_downmix and logger:
        logger(f"🎧 Detected {stream_count} audio streams (OBS multi-track). Downmixing enabled.")

    gpu_codec = _get_gpu_codec(logger)

    video_codec = gpu_codec if hardware_encoding else "libx264"
    audio_codec_flags = ["-ac", "2", "-c:a", "aac", "-b:a", "192k"] if audio_downmix else ["-c:a", "copy"]

    created_files = []
    for i, clip in enumerate(clips_data.get("clips", [])):
        clip_files = _process_single_clip(
            i, clip, file_path, base_name, output_dir,
            video_codec, audio_codec_flags, hardware_encoding,
            vr_stabilization, vertical_export, vertical_mode,
            config, logger, is_cancelled,
            stream_count=stream_count, audio_downmix=audio_downmix,
            target_orientation=target_orientation
        )

        if clip_files is None:
            break

        created_files.extend(clip_files)
        
    return created_files


def _validate_api_keys(config, chat_model, logger):
    chat_model = chat_model.replace(" (Deprecated)", "").strip()
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

_WHISPER_CACHE = {"model": None, "model_type": None, "device": None, "backend": None}

def free_whisper_model():
    """Explicitly frees the cached Whisper model and releases GPU VRAM."""
    global _WHISPER_CACHE
    if _WHISPER_CACHE["model"] is not None:
        try:
            del _WHISPER_CACHE["model"]
        except Exception:
            pass
        _WHISPER_CACHE = {"model": None, "model_type": None, "device": None, "backend": None}
        import gc
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

def get_whisper_model(model_type, device, logger=None):
    """Retrieves cached Whisper/faster-whisper model or loads a new instance."""
    global _WHISPER_CACHE
    backend = "faster-whisper" if HAS_FASTER_WHISPER else "whisper"
    if (_WHISPER_CACHE["model"] is not None and 
        _WHISPER_CACHE["model_type"] == model_type and 
        _WHISPER_CACHE["device"] == device and 
        _WHISPER_CACHE["backend"] == backend):
        return _WHISPER_CACHE["model"]

    free_whisper_model()

    if logger:
        logger(f"⏳ Loading {backend} '{model_type}' model into memory ({device})...")

    if HAS_FASTER_WHISPER and WhisperModel is not None:
        if device == "cuda":
            try:
                model = WhisperModel(model_type, device=device, compute_type="float16")
            except Exception:
                try:
                    model = WhisperModel(model_type, device=device, compute_type="int8_float16")
                except Exception:
                    model = WhisperModel(model_type, device=device, compute_type="default")
        else:
            model = WhisperModel(model_type, device=device, compute_type="int8")
    else:
        model = whisper.load_model(model_type, device=device)

    _WHISPER_CACHE = {
        "model": model,
        "model_type": model_type,
        "device": device,
        "backend": backend
    }
    return model

def _transcribe_audio_to_segments(file_path, config, logger, is_cancelled):
    global _WHISPER_CACHE
    whisper_model_type = config.get("openai", {}).get("whisper_model", "base")
    language_setting = config.get("openai", {}).get("whisper_language", "English")

    if language_setting == "Auto-Detect":
        target_language = None
    elif language_setting in LANGUAGE_MAP:
        target_language = LANGUAGE_MAP[language_setting]
    elif hasattr(whisper, "tokenizer") and hasattr(whisper.tokenizer, "TO_LANGUAGE_CODE") and language_setting.lower() in whisper.tokenizer.TO_LANGUAGE_CODE:
        target_language = whisper.tokenizer.TO_LANGUAGE_CODE[language_setting.lower()]
    else:
        # Fallback for custom inputs like "Dutch" -> "nl" if they enter the 2 letter code, else fallback to slicing
        target_language = language_setting.lower() if len(language_setting) == 2 else language_setting[:2].lower()

    device = "cuda" if is_cuda_available() else "cpu"
    
    if logger:
        if device == "cuda":
            gpu_name = get_gpu_name()
            logger(f"🧠 Hardware Check: NVIDIA GPU Detected ({gpu_name})")
            logger("🚀 Transcribing at maximum speed...")
        else:
            logger("🐌 Hardware Check: CPU Detected (CUDA not available)")
            logger("⚠️ Transcription will take significantly longer...")

    try:
        model = get_whisper_model(whisper_model_type, device, logger=logger)
    except Exception as e:
        if device == "cuda":
            if logger: logger(f"⚠️ CUDA transcription failed ({e}). Falling back to CPU...")
            device = "cpu"
            try:
                model = get_whisper_model(whisper_model_type, "cpu", logger=logger)
            except Exception as e_cpu:
                if logger: logger(f"❌ Failed to load Whisper on CPU: {e_cpu}")
                return None
        elif HAS_FASTER_WHISPER:
            if logger: logger(f"⚠️ faster-whisper failed to load ({e}). Falling back to standard Whisper...")
            try:
                free_whisper_model()
                model = whisper.load_model(whisper_model_type, device=device)
                _WHISPER_CACHE = {
                    "model": model,
                    "model_type": whisper_model_type,
                    "device": device,
                    "backend": "whisper"
                }
            except Exception as e2:
                if logger: logger(f"❌ Failed to load Whisper: {e2}")
                return None
        else:
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
        is_faster = HAS_FASTER_WHISPER and (_WHISPER_CACHE.get("backend") == "faster-whisper")
        if is_faster:
            transcribe_kwargs = {
                "vad_filter": True,
                "vad_parameters": dict(min_silence_duration_ms=500),
                "beam_size": 1,
                "condition_on_previous_text": False,
                "word_timestamps": True,
            }
            if target_language is not None:
                transcribe_kwargs["language"] = target_language

            transcribe_result = model.transcribe(audio_array, **transcribe_kwargs)
        else:
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

                transcribe_result = model.transcribe(audio_array, **transcribe_kwargs)
            
        if isinstance(transcribe_result, tuple):
            segments_generator, info = transcribe_result
            raw_segments = []
            for seg in segments_generator:
                if is_cancelled and is_cancelled():
                    if logger: logger("🛑 Transcription cancelled by user.")
                    return None
                start = seg["start"] if isinstance(seg, dict) else seg.start
                end = seg["end"] if isinstance(seg, dict) else seg.end
                text = seg["text"] if isinstance(seg, dict) else seg.text
                words = []
                if isinstance(seg, dict) and "words" in seg:
                    words = [{"word": str(w.get("word", "")), "start": float(w.get("start", 0)), "end": float(w.get("end", 0))} for w in seg["words"] if isinstance(w, dict)]
                elif hasattr(seg, "words") and seg.words:
                    words = [{"word": str(getattr(w, "word", "")), "start": float(getattr(w, "start", 0)), "end": float(getattr(w, "end", 0))} for w in seg.words]

                raw_segments.append({
                    "start": float(start),
                    "end": float(end),
                    "text": str(text),
                    "words": words
                })
                if logger and len(raw_segments) % 10 == 0:
                    logger(f"⏳ Processed up to {float(end):.1f}s: {str(text)[:40].strip()}...")
        elif isinstance(transcribe_result, dict):
            raw_segments = transcribe_result.get("segments", [])
        else:
            raw_segments = []
            for seg in transcribe_result:
                if is_cancelled and is_cancelled():
                    if logger: logger("🛑 Transcription cancelled by user.")
                    return None
                start = seg["start"] if isinstance(seg, dict) else seg.start
                end = seg["end"] if isinstance(seg, dict) else seg.end
                text = seg["text"] if isinstance(seg, dict) else seg.text
                words = []
                if isinstance(seg, dict) and "words" in seg:
                    words = [{"word": str(w.get("word", "")), "start": float(w.get("start", 0)), "end": float(w.get("end", 0))} for w in seg["words"] if isinstance(w, dict)]
                elif hasattr(seg, "words") and seg.words:
                    words = [{"word": str(getattr(w, "word", "")), "start": float(getattr(w, "start", 0)), "end": float(getattr(w, "end", 0))} for w in seg.words]

                raw_segments.append({
                    "start": float(start),
                    "end": float(end),
                    "text": str(text),
                    "words": words
                })
        
        if audio_peak_detection or combat_detection:
            segments = analyze_audio_peaks(audio_array, raw_segments, peak_detection=audio_peak_detection, combat_detection=combat_detection)
            if logger: logger("✅ Transcription complete! Audio patterns analyzed.")
        else:
            segments = raw_segments
            if logger: logger("✅ Transcription complete!")
            
    except Exception as e:
        if device == "cuda":
            if logger:
                logger(f"⚠️ CUDA transcription execution failed ({e}). Falling back to CPU transcription...")
            try:
                free_whisper_model()
                device = "cpu"
                model = get_whisper_model(whisper_model_type, "cpu", logger=logger)
                is_faster = HAS_FASTER_WHISPER and (_WHISPER_CACHE.get("backend") == "faster-whisper")
                if is_faster:
                    t_kwargs = {
                        "vad_filter": True,
                        "vad_parameters": dict(min_silence_duration_ms=500),
                        "beam_size": 1,
                        "condition_on_previous_text": False,
                        "word_timestamps": True,
                    }
                    if target_language is not None:
                        t_kwargs["language"] = target_language
                    t_result = model.transcribe(audio_array, **t_kwargs)
                else:
                    progress_stream = WhisperProgressStream(logger)
                    with contextlib.redirect_stdout(progress_stream):
                        t_kwargs = {
                            "condition_on_previous_text": False,
                            "beam_size": 1,
                            "fp16": False,
                            "verbose": True
                        }
                        if target_language is not None:
                            t_kwargs["language"] = target_language
                        t_result = model.transcribe(audio_array, **t_kwargs)
                
                if isinstance(t_result, tuple):
                    s_gen, _ = t_result
                    raw_segments = []
                    for seg in s_gen:
                        if is_cancelled and is_cancelled():
                            if logger: logger("🛑 Transcription cancelled by user.")
                            return None
                        s_start = seg["start"] if isinstance(seg, dict) else seg.start
                        s_end = seg["end"] if isinstance(seg, dict) else seg.end
                        s_text = seg["text"] if isinstance(seg, dict) else seg.text
                        words = []
                        if isinstance(seg, dict) and "words" in seg:
                            words = [{"word": str(w.get("word", "")), "start": float(w.get("start", 0)), "end": float(w.get("end", 0))} for w in seg["words"] if isinstance(w, dict)]
                        elif hasattr(seg, "words") and seg.words:
                            words = [{"word": str(getattr(w, "word", "")), "start": float(getattr(w, "start", 0)), "end": float(getattr(w, "end", 0))} for w in seg.words]
                        raw_segments.append({"start": float(s_start), "end": float(s_end), "text": str(s_text), "words": words})
                elif isinstance(t_result, dict):
                    raw_segments = t_result.get("segments", [])
                else:
                    raw_segments = []

                if audio_peak_detection or combat_detection:
                    segments = analyze_audio_peaks(audio_array, raw_segments, peak_detection=audio_peak_detection, combat_detection=combat_detection)
                else:
                    segments = raw_segments
                if logger: logger("✅ Transcription complete on CPU fallback!")
            except Exception as e_cpu:
                if logger: logger(f"❌ CPU fallback error: {e_cpu}")
                return None
        else:
            if logger: logger(f"❌ Transcription error: {e}")
            return None
    finally:
        if device == "cuda" and torch.cuda.is_available():
            torch.cuda.empty_cache()

    if not segments:
        if logger: logger("❌ No audio segments found in the transcription.")
        return None

    return segments

def _generate_clips_with_llm(segments, config, chat_model, prompt_text, logger):
    chat_model = chat_model.replace(" (Deprecated)", "").strip()
    openai_key = config.get("openai", {}).get("api_key", "")
    openai_base_url = config.get("openai", {}).get("base_url", "")
    google_key = config.get("google", {}).get("api_key", "")
    anthropic_key = config.get("anthropic", {}).get("api_key", "")
    xai_key = config.get("xai", {}).get("api_key", "")

    is_gemini_model = (chat_model.startswith("gemini") or "gemini" in chat_model) and "openrouter" not in chat_model
    is_anthropic_model = chat_model.startswith("claude") and "openrouter" not in chat_model
    is_grok_model = chat_model.startswith("grok")
    is_deepseek_model = chat_model.startswith("deepseek")
    is_openrouter = "openrouter" in chat_model or (openai_base_url != "" and not is_grok_model and not is_deepseek_model)

    if is_grok_model:
        openai_key = xai_key
        openai_base_url = "https://api.x.ai/v1"
    elif is_deepseek_model and not openai_base_url:
        openai_base_url = "https://api.deepseek.com"

    all_clips = []
    
    full_transcript = "".join(
        f"[{seg['start']:.1f}s - {seg['end']:.1f}s] {seg['text'].strip()}\n"
        for seg in segments
    )

    # Estimate token count based on a common heuristic (1 token ~= 4 chars or ~0.75 words)
    # Using roughly 1.3 tokens per word as a general English baseline.
    word_count = len(full_transcript.split())
    estimated_tokens = int(word_count * 1.3)
    if logger:
        logger(f"📊 Extracted approx {estimated_tokens:,} tokens ({word_count:,} words) for the AI model's context window.")

    if is_gemini_model and not is_openrouter:
        if not HAS_GEMINI:
            if logger: logger("❌ Error: google-genai module missing. Run 'pip install -r requirements.txt'")
            return []
            
        if logger: logger(f"🌌 Routing to native Gemini Engine ({chat_model}) with {len(segments)} segments...")

        try:
            client = genai.Client(api_key=google_key)
            response = client.models.generate_content(
                model=chat_model,
                contents=f"Analyze this entire gaming transcript. The timestamps for each line are in brackets. Return strictly JSON.\n\n{full_transcript}",
                config={
                    "system_instruction": prompt_text,
                    "response_mime_type": "application/json"
                }
            )
            raw_text = response.text.strip()
            if "```json" in raw_text:
                raw_text = raw_text.split("```json")[-1].split("```")[0].strip()
            elif "```" in raw_text:
                raw_text = raw_text.split("```")[-1].split("```")[0].strip()

            chunk_data = json.loads(raw_text)
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
                raw_content = raw_content.split("```json")[-1].split("```")[0].strip()
            elif raw_content.startswith("```"):
                raw_content = raw_content.split("```")[-1].split("```")[0].strip()

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
            req_params = {
                "model": chat_model,
                "messages": [
                    {"role": "system", "content": prompt_text},
                    {"role": "user", "content": f"Analyze this entire gaming transcript. Return strictly JSON.\n\n{full_transcript}"}
                ]
            }
            # DeepSeek Reasoner and reasoning models reject response_format={"type": "json_object"} with HTTP 400
            is_reasoning_model = any(keyword in chat_model.lower() for keyword in ["reasoner", "r1", "o1"])
            if not is_reasoning_model:
                req_params["response_format"] = { "type": "json_object" }

            response = client.chat.completions.create(**req_params)
            raw_content = response.choices[0].message.content or ""

            # Strip markdown json code blocks if present
            if "```json" in raw_content:
                raw_content = raw_content.split("```json")[-1].split("```")[0].strip()
            elif "```" in raw_content:
                raw_content = raw_content.split("```")[-1].split("```")[0].strip()

            chunk_data = json.loads(raw_content)
            found_clips = chunk_data.get("clips", [])
            if found_clips:
                if logger: logger(f"🎯 Found {len(found_clips)} clip(s)!")
                all_clips.extend(found_clips)
            else:
                if logger: logger(f"🤷‍♂️ No clips found.")
        except Exception as e:
            if logger: logger(f"❌ OpenAI/Custom API Error: {e}")

    return all_clips

def process_video(file_path, prompt_profile="Omni-Genre Broad Net", logger=None, is_cancelled=None, target_orientation=None):
    """Main orchestration function for analyzing and cutting clips."""
    config = config_manager.load_config()
    chat_model = config.get("openai", {}).get("chat_model", "gpt-4o")
    chat_model = chat_model.replace(" (Deprecated)", "").strip()
    clips_dir = config.get("settings", {}).get("clips_dir", "")

    if not clips_dir:
        if logger: logger("❌ Error: Generated Clips folder not set in Settings.")
        return []

    if not _validate_api_keys(config, chat_model, logger):
        return []

    segments = _transcribe_audio_to_segments(file_path, config, logger, is_cancelled)
    if not segments:
        return []

    if is_cancelled and is_cancelled(): return []

    prompt_text = config.get("prompts", {}).get("profiles", {}).get(prompt_profile, "Find the best 15-90s moments. Output JSON.")

    all_clips = _generate_clips_with_llm(segments, config, chat_model, prompt_text, logger)

    if all_clips:
        # Attach word timestamps from transcription segments to extracted clips
        for clip in all_clips:
            c_start = float(clip.get("start_time", 0.0))
            c_end = float(clip.get("end_time", 0.0))
            clip_words = []
            for seg in segments:
                for w in seg.get("words", []):
                    w_s = float(w.get("start", 0.0))
                    w_e = float(w.get("end", 0.0))
                    if (c_start <= w_s <= c_end) or (c_start <= w_e <= c_end):
                        clip_words.append(w)
            clip["words"] = clip_words

        if logger: logger(f"🎬 Sending {len(all_clips)} total timestamp(s) to FFmpeg...")
        final_clips_data = {"clips": all_clips}
        created = extract_clips(file_path, final_clips_data, clips_dir, logger, is_cancelled, target_orientation=target_orientation)
        if logger: logger(f"✨ Successfully exported {len(created)} file(s) to your folder!")
        return created
    else:
        if logger: logger("🤷‍♂️ AI finished scanning the VOD but didn't extract any clips.")
        return []