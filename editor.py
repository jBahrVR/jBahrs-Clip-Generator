import os
import json
import subprocess
import torch # type: ignore
import whisper # type: ignore
import config_manager # type: ignore
from openai import OpenAI # type: ignore
import numpy as np # type: ignore

try:
    import google.generativeai as genai # type: ignore
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False

def analyze_audio_peaks(audio_array, segments, sample_rate=16000):
    """Calculates RMS loudness for each Whisper segment and appends it to the text."""
    enhanced_segments = []
    for seg in segments:
        start_idx = int(seg['start'] * sample_rate)
        end_idx = int(seg['end'] * sample_rate)
        
        # Ensure indices stay within array bounds
        start_idx = max(0, min(start_idx, len(audio_array) - 1))
        end_idx = max(start_idx + 1, min(end_idx, len(audio_array)))
        
        # Calculate RMS for this chunk
        chunk = audio_array[start_idx:end_idx]
        if len(chunk) > 0:
            rms = np.sqrt(np.mean(chunk**2))
            # Convert subtle RMS (0 to 1.0) into a more aggressive "0-100%" loudness score
            loudness = min(100, int((rms / 0.1) * 100))
        else:
            loudness = 0
            
        enhanced_text = f"[LOUDNESS: {loudness}%] {seg['text'].strip()}"
        
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
    
    startupinfo = None
    if os.name == 'nt' and hasattr(subprocess, 'STARTUPINFO'):
        startupinfo = subprocess.STARTUPINFO() # type: ignore
        if hasattr(subprocess, 'STARTF_USESHOWWINDOW'):
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW # type: ignore
        if hasattr(subprocess, 'SW_HIDE'):
            startupinfo.wShowWindow = subprocess.SW_HIDE # type: ignore

    out = subprocess.run(cmd, capture_output=True, startupinfo=startupinfo)
    if out.returncode != 0:
        raise RuntimeError(f"FFmpeg audio extraction failed: {out.stderr.decode()}")
        
    return np.frombuffer(out.stdout, np.int16).flatten().astype(np.float32) / 32768.0

def extract_clips(file_path, clips_data, output_dir, logger):
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    config = config_manager.load_config()
    vr_stabilization = config.get("settings", {}).get("vr_stabilization", False)
    vertical_export = config.get("settings", {}).get("vertical_export", False)
    vertical_mode = config.get("settings", {}).get("vertical_mode", "Standard Center Crop")
    hardware_encoding = config.get("settings", {}).get("hardware_encoding", False)
    audio_downmix = config.get("settings", {}).get("audio_downmix", True)

    # Detect optimal GPU architecture
    gpu_codec = "h264_nvenc"
    try:
        if torch.cuda.is_available():
            device_name = torch.cuda.get_device_name(0).lower()
            if "amd" in device_name or "radeon" in device_name:
                gpu_codec = "h264_amf"
    except Exception:
        pass

    video_codec = gpu_codec if hardware_encoding else "libx264"
    audio_codec_flags = ["-ac", "2", "-c:a", "aac", "-b:a", "192k"] if audio_downmix else ["-c:a", "copy"]

    created_files = []
    for i, clip in enumerate(clips_data.get("clips", [])):
        start_time = clip.get("start_time")
        end_time = clip.get("end_time")
        score = clip.get("virality_score", "N/A")
        
        if start_time is None or end_time is None:
            continue

        output_file = os.path.join(output_dir, f"{base_name}_clip{i+1}_score{score}.mp4")
        json_meta_file = os.path.join(output_dir, f"{base_name}_clip{i+1}_score{score}.json")
        
        cmd = [
            "ffmpeg", "-y", 
            "-i", file_path, 
            "-ss", str(start_time), 
            "-to", str(end_time), 
            "-c:v", video_codec,
            "-preset", "fast" if not hardware_encoding else "p4" # p4 is a safe default preset for nvenc
        ]
        
        if not hardware_encoding:
            cmd.extend(["-crf", "23"])
        else:
            cmd.extend(["-cq", "25", "-rc", "vbr"]) # Better sizing for hardware encode

        if vr_stabilization:
            if logger: logger("🎞️ Applying VR Anti-Shake filter...")
            cmd.extend(["-vf", "deshake=rx=64:ry=64:edge=mirror"])

        cmd.extend(audio_codec_flags)
        cmd.append(output_file)
        
        if logger: 
            logger(f"✂️ Cutting horizontal clip {i+1} ({start_time}s - {end_time}s)...")
            
        startupinfo = None
        if os.name == 'nt' and hasattr(subprocess, 'STARTUPINFO'):
            startupinfo = subprocess.STARTUPINFO() # type: ignore
            if hasattr(subprocess, 'STARTF_USESHOWWINDOW'):
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW # type: ignore
            if hasattr(subprocess, 'SW_HIDE'):
                startupinfo.wShowWindow = subprocess.SW_HIDE # type: ignore
            
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, startupinfo=startupinfo, check=True)
            created_files.append(output_file)
            
            with open(json_meta_file, 'w', encoding='utf-8') as meta_f:
                json.dump(clip, meta_f, indent=4)
                
            # --- VERTICAL AUTO-CROPPER ---
            if vertical_export:
                vert_output = output_file.replace(".mp4", "_vertical.mp4")
                if logger: logger(f"📱 Generating Vertical Shorts format ({vertical_mode})...")
                
                if vertical_mode == "Standard Center Crop":
                    vf_command = "crop=ih*9/16:ih,scale=1080:1920"
                    vert_cmd = [
                        "ffmpeg", "-y", "-i", output_file, 
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
                        x = config.get("settings", {}).get("crop_x", "0")
                        y = config.get("settings", {}).get("crop_y", "0")
                        w = config.get("settings", {}).get("crop_w", "400")
                        h = config.get("settings", {}).get("crop_h", "225")

                    filter_complex = f"[0:v]crop={w}:{h}:{x}:{y},scale=1080:840[cam];[0:v]crop=1080:1080:420:0[game];[cam][game]vstack=inputs=2[out]"
                    
                    vert_cmd = [
                        "ffmpeg", "-y", "-i", output_file, 
                        "-filter_complex", filter_complex, 
                        "-map", "[out]", "-map", "0:a", 
                        "-c:v", video_codec, "-preset", "fast" if not hardware_encoding else "p4", 
                    ]
                    if not hardware_encoding: vert_cmd.extend(["-crf", "23"])
                    else: vert_cmd.extend(["-cq", "25", "-rc", "vbr"])
                    
                    vert_cmd.extend(audio_codec_flags)
                    vert_cmd.append(vert_output)

                subprocess.run(vert_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, startupinfo=startupinfo, check=True)
                created_files.append(vert_output)

        except Exception as e:
            if logger: 
                logger(f"❌ FFmpeg error on clip {i+1}: {e}")
        
    return created_files

def process_video(file_path, prompt_profile="Omni-Genre Broad Net", logger=None):
    config = config_manager.load_config()
    chat_model = config.get("openai", {}).get("chat_model", "gpt-4o")
    openai_key = config.get("openai", {}).get("api_key", "")
    google_key = config.get("google", {}).get("api_key", "")
    whisper_model_type = config.get("openai", {}).get("whisper_model", "base")
    clips_dir = config.get("settings", {}).get("clips_dir", "")
    
    if not clips_dir:
        if logger: logger("❌ Error: Generated Clips folder not set in Settings.")
        return

    is_gemini_model = chat_model.startswith("gemini")
    
    if is_gemini_model and not google_key:
        if logger: logger("❌ Error: Google API Key not set for Gemini model.")
        return
    elif not is_gemini_model and not openai_key:
        if logger: logger("❌ Error: OpenAI API Key not set.")
        return

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
        return

    # --- THE FIX: We use our hidden interceptor to pull the audio first ---
    if logger: logger("🎙️ Extracting audio track silently...")
    try:
        audio_array = extract_audio_hidden(file_path)
    except Exception as e:
        if logger: logger(f"❌ Audio extraction error: {e}")
        return

    if logger: logger("🎙️ Transcribing audio and measuring peak levels (this may take a while)...")
    try:
        # We feed the raw audio_array directly to Whisper, completely bypassing its command window bug!
        result = model.transcribe(audio_array, condition_on_previous_text=False, beam_size=1)
        raw_segments = result.get("segments", [])
        
        # Inject Audio Peak Detection Logic
        segments = analyze_audio_peaks(audio_array, raw_segments)
        
        if logger: logger("✅ Transcription complete! Peak volumes measured.")
    except Exception as e:
        if logger: logger(f"❌ Transcription error: {e}")
        return

    if not segments:
        if logger: logger("❌ No audio segments found in the transcription.")
        return

    prompt_text = config.get("prompts", {}).get("profiles", {}).get(prompt_profile, "Find the best 15-90s moments. Output JSON.")
    all_clips = []

    if is_gemini_model:
        if not HAS_GEMINI:
            if logger: logger("❌ Error: google-generativeai module missing.")
            return
            
        if logger: logger(f"🌌 Routing to Gemini Engine ({chat_model})")
        
        full_transcript = ""
        for seg in segments:
            full_transcript += f"[{seg['start']:.1f}s - {seg['end']:.1f}s] {seg['text'].strip()}\n"

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

    else:
        if logger: logger(f"🤖 Routing to OpenAI Engine ({chat_model}) with 15-Minute Chunking...")
        chunks = []
        current_chunk = ""
        chunk_start_time = segments[0]['start']
        chunk_duration_limit = 900
        
        for seg in segments:
            start = seg['start']
            end = seg['end']
            text = seg['text'].strip()
            
            if start - chunk_start_time > chunk_duration_limit and current_chunk:
                chunks.append(current_chunk)
                current_chunk = ""
                chunk_start_time = start
                
            current_chunk += f"[{start:.1f}s - {end:.1f}s] {text}\n"
            
        if current_chunk:
            chunks.append(current_chunk)

        client = OpenAI(api_key=openai_key)

        for i, chunk_text in enumerate(chunks):
            if logger: logger(f"⏳ Processing chunk {i+1}/{len(chunks)}...")
            try:
                response = client.chat.completions.create(
                    model=chat_model,
                    response_format={ "type": "json_object" },
                    messages=[
                        {"role": "system", "content": prompt_text},
                        {"role": "user", "content": f"Analyze this 15-minute chunk. Return strictly JSON.\n\n{chunk_text}"}
                    ]
                )
                chunk_data = json.loads(response.choices[0].message.content)
                found_clips = chunk_data.get("clips", [])
                if found_clips:
                    if logger: logger(f"🎯 Found {len(found_clips)} clip(s) in chunk {i+1}!")
                    all_clips.extend(found_clips)
                else:
                    if logger: logger(f"🤷‍♂️ No clips found in chunk {i+1}.")
            except Exception as e:
                if logger: logger(f"❌ OpenAI API Error on chunk {i+1}: {e}")

    if all_clips:
        if logger: logger(f"🎬 Sending {len(all_clips)} total timestamp(s) to FFmpeg...")
        final_clips_data = {"clips": all_clips}
        created = extract_clips(file_path, final_clips_data, clips_dir, logger)
        if logger: logger(f"✨ Successfully exported {len(created)} file(s) to your folder!")
    else:
        if logger: logger("🤷‍♂️ AI finished scanning the VOD but didn't extract any clips.")