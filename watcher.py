import os
import shutil
import subprocess
import config_manager # type: ignore
import editor # type: ignore
import utils

YTDLP_PATH = "yt-dlp.exe" if os.name == 'nt' else "yt-dlp"

def get_ytdlp_js_runtime_args() -> list:
    """Auto-detects available JavaScript runtimes on the system for YouTube challenge solving."""
    for runtime in ["node", "deno", "bun", "quickjs"]:
        if shutil.which(runtime):
            return ["--js-runtimes", runtime]
    for node_path in [r"C:\Program Files\nodejs\node.exe", r"C:\Program Files (x86)\nodejs\node.exe"]:
        if os.path.exists(node_path):
            return ["--js-runtimes", f"node:{node_path}"]
    return []

def download_with_subprocess(url, video_id, logger_callback=None, force_manual=False, is_cancelled=None):
    config = config_manager.load_config()
    download_dir = config.get("settings", {}).get("download_dir", "")
    
    if not download_dir:
        if logger_callback: 
            logger_callback("❌ Error: Download directory not set in Settings.")
        return None

    if not os.path.exists(download_dir):
        os.makedirs(download_dir)

    video_type = config.get("auto_scheduler", {}).get("video_type", "Livestreams Only")
    quality_pref = config.get("settings", {}).get("download_quality", "Best")

    format_string = "bestvideo+bestaudio/best"
    sort_args = []
    if quality_pref == "1080p":
        sort_args = ["-S", "res:1080"]
    elif quality_pref == "720p":
        sort_args = ["-S", "res:720"]

    output_template = os.path.join(download_dir, f"%(title)s_%(id)s.%(ext)s")

    # Grab the user's browser choice from the config
    auth_browser = config.get("settings", {}).get("auth_browser", "None")
    
    # Build the base command WITHOUT the URL
    cmd = [
        YTDLP_PATH,
        "-f", format_string,
        "--merge-output-format", "mp4",
        "-o", output_template,
        "--retries", "10",
        "--fragment-retries", "10",
        "--retry-sleep", "exp=1:20"
    ]
    if sort_args:
        cmd.extend(sort_args)

    # Dynamically inject available JavaScript runtimes to solve YouTube n-sig challenges
    js_args = get_ytdlp_js_runtime_args()
    if js_args:
        cmd.extend(js_args)

    # Dynamically inject the cookies flag ONLY if they selected a browser
    if auth_browser and auth_browser != "None":
        cmd.extend(["--cookies-from-browser", auth_browser])

    if not force_manual and video_type == "Livestreams Only":
        if logger_callback: 
            logger_callback("🔍 Applying 'Livestreams Only' filter...")
        cmd.extend(["--match-filter", "live_status=?was_live"])

    # Add the URL to the very end of the command
    cmd.append("--")
    cmd.append(url)

    if logger_callback: 
        logger_callback(f"⬇️ Starting download for {url}...")

    downloaded_file_path = None
    error_log = []

    def log_progress(line: str) -> None:
        nonlocal downloaded_file_path
        line = line.strip()
        if not line:
            return
        
        # Keep the last 10 lines of console output in memory
        error_log.append(line)
        if len(error_log) > 10:
            error_log.pop(0)
        
        if logger_callback: 
            # Print progress and catch any explicit ERROR strings
            if "[download]" in line or "[Merger]" in line or "ERROR:" in line:
                logger_callback(f"[yt-dlp]: {line}")
        
        if "Merging formats into" in line:
            parts = line.split('"')
            if len(parts) >= 3:
                downloaded_file_path = parts[1]
        elif "Destination:" in line:
            parts = line.split("Destination:", 1)
            if len(parts) >= 2:
                candidate = parts[1].strip()
                if candidate and not candidate.endswith(".part"):
                    downloaded_file_path = candidate

    try:
        returncode = utils.run_subprocess_command(
            cmd,
            logger_callback=log_progress,
            is_cancelled=is_cancelled
        )

        # Verify the console string actually points to a real file
        if downloaded_file_path and not os.path.exists(downloaded_file_path):
            downloaded_file_path = None

        # Fallback: Safely scan the folder for the video ID
        if not downloaded_file_path and os.path.exists(download_dir):
            try:
                for f in os.listdir(download_dir):
                    if video_id in f and f.endswith(".mp4") and not f.endswith(".part"):
                        cand = os.path.join(download_dir, f)
                        if os.path.exists(cand):
                            downloaded_file_path = cand
                            break
            except Exception:
                pass

        # A download is successful if returncode is 0 and we found a path, OR if the video file exists on disk
        if (returncode == 0 or downloaded_file_path) and downloaded_file_path and os.path.exists(downloaded_file_path):
            if logger_callback: 
                logger_callback("✅ Download completed successfully!")
            return downloaded_file_path
        else:
            # Print the actual error message
            if logger_callback:
                err_strings = [str(x) for x in error_log[-3:] if x is not None]
                last_errors = "\n".join(err_strings)
                logger_callback(f"❌ Download failed! yt-dlp says:\n{last_errors}")
                if "403" in last_errors or "Forbidden" in last_errors:
                    logger_callback("💡 Tip: YouTube is throttling anonymous video data. In Settings, select your browser under 'Auth Browser (Cookies)' (e.g. Chrome/Edge/Firefox) to bypass YouTube rate limits.")
            return None

    except Exception as e:
        if logger_callback: 
            logger_callback(f"❌ Exception during download: {str(e)}")
        return None

def main(logger_callback=None):
    config = config_manager.load_config()
    platform = config.get("auto_scheduler", {}).get("platform", "YouTube")
    yt_id = config.get("youtube", {}).get("channel_id", "")
    twitch_user = config.get("twitch", {}).get("username", "")

    if platform == "YouTube" and not yt_id:
        if logger_callback: 
            logger_callback("⚠️ YouTube Channel ID not set. Skipping auto-check.")
        return
    if platform == "Twitch" and not twitch_user:
        if logger_callback: 
            logger_callback("⚠️ Twitch Username not set. Skipping auto-check.")
        return

    # Check the streams archive for YT, and the past broadcasts archive for Twitch
    if platform == "YouTube":
        if yt_id.startswith("@"):
            target_url = f"https://www.youtube.com/{yt_id}/streams"
        else:
            target_url = f"https://www.youtube.com/channel/{yt_id}/streams"
    else:
        target_url = f"https://www.twitch.tv/{twitch_user}/videos?filter=archives"

    if logger_callback: 
        logger_callback(f"📡 Checking {platform} for new content...")
    
    cmd = [
        YTDLP_PATH,
        "--flat-playlist",
        "--print", "id",
        "--max-downloads", "1", 
        "--",
        target_url
    ]
    
    try:
        output_lines = []
        code = utils.run_subprocess_command(cmd, logger_callback=lambda line: output_lines.append(line.strip()))
        latest_id = output_lines[0] if output_lines and output_lines[0] else None
        
        # 👈 THE FIX: Strip the stray 'v' from Twitch IDs so the URL doesn't 404
        if platform == "Twitch" and latest_id and isinstance(latest_id, str) and latest_id.startswith("v"):
            latest_id = str(latest_id)[1:] # type: ignore
        
        if latest_id:
            video_url = f"https://www.youtube.com/watch?v={latest_id}" if platform == "YouTube" else f"https://www.twitch.tv/videos/{latest_id}"
            
            download_dir = config.get("settings", {}).get("download_dir", "")
            already_downloaded = False
            
            if os.path.exists(download_dir):
                for f in os.listdir(download_dir):
                    if latest_id in f:
                        already_downloaded = True
                        break
            
            if not already_downloaded:
                if logger_callback: 
                    logger_callback(f"🎥 Found new video! Starting automated download...")
                
                # Capture the downloaded file path
                downloaded_path = download_with_subprocess(video_url, latest_id, logger_callback, force_manual=False)
                
                if downloaded_path:
                    prompt_profile = config.get("auto_scheduler", {}).get("auto_prompt_profile", "Default VR")
                    if logger_callback: 
                        logger_callback(f"🧠 Passing VOD to AI Editor using profile: [{prompt_profile}]")
                    # We are passing down a mock lambda just for completeness, as watcher doesn't have a UI cancel button yet
                    editor.process_video(downloaded_path, prompt_profile=prompt_profile, logger=logger_callback, is_cancelled=lambda: False)
                    
                    if logger_callback: 
                        logger_callback("🏁 Auto-Scheduler finished processing the new video!")
            else:
                if logger_callback: 
                    logger_callback("😴 No new videos found.")
                    
    except Exception as e:
         if logger_callback: 
             logger_callback(f"❌ Watcher error: {e}")