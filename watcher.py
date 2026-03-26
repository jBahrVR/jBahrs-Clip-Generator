import os
import subprocess
import config_manager # type: ignore
import editor # type: ignore

YTDLP_PATH = "yt-dlp.exe" if os.name == 'nt' else "yt-dlp"

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

    # Fixed variable name: changed from format_str to format_string
    if quality_pref == "1080p":
        format_string = "bestvideo[height<=1080]+bestaudio/best[height<=1080]"
    elif quality_pref == "720p":
        format_string = "bestvideo[height<=720]+bestaudio/best[height<=720]"
    else:
        format_string = "bestvideo+bestaudio/best"

    output_template = os.path.join(download_dir, f"%(title)s_%(id)s.%(ext)s")

    # Grab the user's browser choice from the config
    auth_browser = config.get("settings", {}).get("auth_browser", "None")
    
    # Build the base command WITHOUT the URL
    cmd = [
        YTDLP_PATH,
        "-f", format_string,
        "--merge-output-format", "mp4",
        "-o", output_template
    ]

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

    startupinfo = None
    if os.name == 'nt' and hasattr(subprocess, 'STARTUPINFO'):
        startupinfo = subprocess.STARTUPINFO() # type: ignore
        if hasattr(subprocess, 'STARTF_USESHOWWINDOW'):
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW # type: ignore
        if hasattr(subprocess, 'SW_HIDE'):
            startupinfo.wShowWindow = subprocess.SW_HIDE # type: ignore

    if logger_callback: 
        logger_callback(f"⬇️ Starting download for {url}...")

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Redirects errors into the stdout stream
            text=True,
            startupinfo=startupinfo,
            bufsize=1,
            universal_newlines=True,
            cwd=download_dir
        )

        downloaded_file_path = None
        error_log = []  # Keep a rolling log of the output to catch hidden errors

        if process.stdout:
            for line in process.stdout: # type: ignore
                line = line.strip()
                if not line:
                    continue
                
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

        process.wait()

        if process.returncode == 0:
            if logger_callback: 
                logger_callback("✅ Download completed successfully!")
            
            # Verify the console string actually points to a real file
            if downloaded_file_path and not os.path.exists(downloaded_file_path):
                downloaded_file_path = None
            
            # Fallback: Safely scan the folder for the video ID
            if not downloaded_file_path and os.path.exists(download_dir):
                for f in os.listdir(download_dir):
                    if video_id in f and f.endswith(".mp4"):
                        downloaded_file_path = os.path.join(download_dir, f)
                        break

            return downloaded_file_path
        else:
            # Report the specific yt-dlp error if found, otherwise fall back to the last few output lines
            if logger_callback:
                specific_errors = [str(line) for line in error_log if line is not None and "ERROR:" in str(line)]
                if specific_errors:
                    err_msg = "\n".join(specific_errors)
                else:
                    err_strings = [str(x) for x in error_log[-3:] if x is not None]
                    err_msg = "\n".join(err_strings)

                logger_callback(f"❌ Download failed! yt-dlp says:\n{err_msg}")
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
    target_url = f"https://www.youtube.com/channel/{yt_id}/streams" if platform == "YouTube" else f"https://www.twitch.tv/{twitch_user}/videos?filter=archives"

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
    
    startupinfo = None
    if os.name == 'nt' and hasattr(subprocess, 'STARTUPINFO'):
        startupinfo = subprocess.STARTUPINFO() # type: ignore
        if hasattr(subprocess, 'STARTF_USESHOWWINDOW'):
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW # type: ignore
        if hasattr(subprocess, 'SW_HIDE'):
            startupinfo.wShowWindow = subprocess.SW_HIDE # type: ignore

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, startupinfo=startupinfo)
        output_lines = result.stdout.strip().split('\n')
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