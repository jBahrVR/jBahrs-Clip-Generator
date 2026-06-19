import sys
import os
from tkinter import messagebox

if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

import customtkinter as ctk # type: ignore
from customtkinter import filedialog # type: ignore
import config_manager # type: ignore
import gui
import threading
import subprocess
import time
import webbrowser
import watcher # type: ignore
import editor # type: ignore
import pystray # type: ignore
import json
import urllib.request
from PIL import Image # type: ignore
import logging
from logging.handlers import RotatingFileHandler
import datetime

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class ClipGenApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("jBahr's Clip Generator")
        self.geometry("1100x900") 
        
        self.protocol('WM_DELETE_WINDOW', self.minimize_to_tray)
        self.tray_icon = None
        
        self.config = config_manager.load_config()
        self.is_auto_running = False

        self._init_logging()

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # Instantiate views from gui package
        self.sidebar_frame = gui.Sidebar(self)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")

        self.manual_frame = gui.ManualFrame(self)
        # Aliasing for backwards compatibility
        self.url_input = self.manual_frame.url_input
        self.process_btn = self.manual_frame.process_btn
        self.cancel_btn = self.manual_frame.cancel_btn
        self.local_file_btn = self.manual_frame.local_file_btn
        self.manual_status_label = self.manual_frame.manual_status_label
        self.manual_progress = self.manual_frame.manual_progress
        self.console_box = self.manual_frame.console_box

        self.auto_frame = gui.AutoFrame(self)
        self.platform_menu = self.auto_frame.platform_menu
        self.type_menu = self.auto_frame.type_menu
        self.target_menu = self.auto_frame.target_menu
        self.lookback_menu = self.auto_frame.lookback_menu
        self.interval_menu = self.auto_frame.interval_menu
        self.auto_prompt_menu = self.auto_frame.auto_prompt_menu
        self.auto_switch = self.auto_frame.auto_switch
        self.auto_progress = self.auto_frame.auto_progress
        self.auto_status = self.auto_frame.auto_status
        self.auto_console = self.auto_frame.auto_console

        self.prompt_frame = gui.PromptFrame(self)
        self.profile_dropdown = self.prompt_frame.profile_dropdown
        self.new_profile_btn = self.prompt_frame.new_profile_btn
        self.delete_profile_btn = self.prompt_frame.delete_profile_btn
        self.prompt_textbox = self.prompt_frame.prompt_textbox
        self.save_prompt_btn = self.prompt_frame.save_prompt_btn

        self.settings_frame = gui.SettingsFrame(self)
        self.yt_id_entry = self.settings_frame.yt_id_entry
        self.twitch_entry = self.settings_frame.twitch_entry
        self.openai_entry = self.settings_frame.openai_entry
        self.base_url_entry = self.settings_frame.base_url_entry
        self.anthropic_entry = self.settings_frame.anthropic_entry
        self.grok_entry = self.settings_frame.grok_entry
        self.google_entry = self.settings_frame.google_entry
        self.discord_entry = self.settings_frame.discord_entry
        self.model_menu = self.settings_frame.model_menu
        self.whisper_menu = self.settings_frame.whisper_menu
        self.language_menu = self.settings_frame.language_menu
        self.quality_menu = self.settings_frame.quality_menu
        self.vod_dir_entry = self.settings_frame.vod_dir_entry
        self.clip_dir_entry = self.settings_frame.clip_dir_entry
        self.browser_menu = self.settings_frame.browser_menu
        self.hardware_switch = self.settings_frame.hardware_switch
        self.downmix_switch = self.settings_frame.downmix_switch
        self.audio_peak_switch = self.settings_frame.audio_peak_switch
        self.combat_switch = self.settings_frame.combat_switch
        self.stabilize_switch = self.settings_frame.stabilize_switch
        self.vertical_switch = self.settings_frame.vertical_switch
        self.vertical_mode_menu = self.settings_frame.vertical_mode_menu
        self.crop_x_entry = self.settings_frame.crop_x_entry
        self.crop_y_entry = self.settings_frame.crop_y_entry
        self.crop_w_entry = self.settings_frame.crop_w_entry
        self.crop_h_entry = self.settings_frame.crop_h_entry

        self.gallery_frame = gui.GalleryFrame(self)
        self.sort_menu = self.gallery_frame.sort_menu
        self.type_filter_menu = self.gallery_frame.type_filter_menu
        self.score_filter_menu = self.gallery_frame.score_filter_menu
        self.clip_listbox = self.gallery_frame.clip_listbox
        self.select_all_checkbox = self.gallery_frame.select_all_checkbox
        self.select_all_var = self.gallery_frame.select_all_var
        self.refresh_gallery_btn = self.gallery_frame.refresh_gallery_btn
        self.delete_marked_btn = self.gallery_frame.delete_marked_btn
        self.detail_title = self.gallery_frame.detail_title
        self.detail_score = self.gallery_frame.detail_score
        self.detail_reasoning = self.gallery_frame.detail_reasoning
        self.detail_thumbnail = self.gallery_frame.detail_thumbnail
        self.play_clip_btn = self.gallery_frame.play_clip_btn
        self.open_folder_btn = self.gallery_frame.open_folder_btn

        # Align sidebar buttons references for highlights
        self.nav_manual_btn = self.sidebar_frame.nav_manual_btn
        self.nav_auto_btn = self.sidebar_frame.nav_auto_btn
        self.nav_prompt_btn = self.sidebar_frame.nav_prompt_btn
        self.nav_settings_btn = self.sidebar_frame.nav_settings_btn
        self.nav_gallery_btn = self.sidebar_frame.nav_gallery_btn

        self.load_prompt_data()
        self.show_manual_frame()

        self.after(100, self.check_and_download_binaries)

    def check_and_download_binaries(self):
        if os.name != 'nt':
            return  # Auto-download only implemented for Windows environment

        app_dir = os.path.dirname(os.path.abspath(__file__))
        ffmpeg_path = os.path.join(app_dir, "ffmpeg.exe")
        ytdlp_path = os.path.join(app_dir, "yt-dlp.exe")

        missing = []
        if not os.path.exists(ffmpeg_path):
            missing.append("ffmpeg")
        if not os.path.exists(ytdlp_path):
            missing.append("yt-dlp")

        if not missing:
            return

        dialog = ctk.CTkToplevel(self)
        dialog.title("Downloading Prerequisites")
        dialog.geometry("450x200")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)

        label = ctk.CTkLabel(dialog, text="Downloading missing components...", font=ctk.CTkFont(size=14, weight="bold"))
        label.pack(pady=(20, 10))

        status_label = ctk.CTkLabel(dialog, text="Preparing download...", font=ctk.CTkFont(size=12))
        status_label.pack(pady=5)

        progress_bar = ctk.CTkProgressBar(dialog, width=350)
        progress_bar.pack(pady=10)
        progress_bar.set(0)

        def download_thread():
            try:
                import requests
                import zipfile
                import io
            except ImportError:
                self.log_to_console("❌ Error: Missing requests library. Run 'pip install -r requirements.txt'")
                status_label.configure(text="Error: Missing 'requests' module. Check logs.")
                dialog.update_idletasks()
                return

            try:
                # 1. Download yt-dlp.exe if missing
                if "yt-dlp" in missing:
                    self.log_to_console("📥 Downloading yt-dlp.exe...")
                    status_label.configure(text="Downloading yt-dlp.exe...")
                    url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
                    response = requests.get(url, stream=True)
                    response.raise_for_status()
                    
                    total_size = int(response.headers.get('content-length', 0))
                    downloaded = 0
                    
                    with open(ytdlp_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)
                                if total_size:
                                    percent = downloaded / total_size
                                    progress_bar.set(percent)
                                    status_label.configure(text=f"Downloading yt-dlp.exe ({int(percent * 100)}%)")
                                    dialog.update_idletasks()
                    self.log_to_console("✅ yt-dlp.exe downloaded successfully!")

                # 2. Download ffmpeg.exe if missing
                if "ffmpeg" in missing:
                    self.log_to_console("📥 Downloading FFmpeg zip...")
                    status_label.configure(text="Downloading FFmpeg builds (zip)...")
                    progress_bar.set(0)
                    dialog.update_idletasks()

                    url = "https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
                    response = requests.get(url, stream=True)
                    response.raise_for_status()

                    total_size = int(response.headers.get('content-length', 0))
                    downloaded = 0
                    zip_data = io.BytesIO()

                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            zip_data.write(chunk)
                            downloaded += len(chunk)
                            if total_size:
                                percent = downloaded / total_size
                                progress_bar.set(percent * 0.9)
                                status_label.configure(text=f"Downloading FFmpeg ({int(percent * 90)}%)")
                                dialog.update_idletasks()

                    status_label.configure(text="Extracting ffmpeg.exe...")
                    dialog.update_idletasks()

                    zip_data.seek(0)
                    with zipfile.ZipFile(zip_data) as z:
                        ffmpeg_member = None
                        for name in z.namelist():
                            if name.endswith("bin/ffmpeg.exe"):
                                ffmpeg_member = name
                                break
                        
                        if ffmpeg_member:
                            with z.open(ffmpeg_member) as source, open(ffmpeg_path, 'wb') as target:
                                target.write(source.read())
                            self.log_to_console("✅ ffmpeg.exe extracted successfully!")
                        else:
                            raise Exception("Could not find bin/ffmpeg.exe in the downloaded zip file.")

                    progress_bar.set(1.0)
                    status_label.configure(text="Finished downloading all components!")
                    dialog.update_idletasks()

                time.sleep(1)
                dialog.destroy()

            except Exception as e:
                self.log_to_console(f"❌ Error during binary download/extraction: {e}")
                status_label.configure(text=f"Error: {e}")
                messagebox.showerror("Error", f"Failed to download required binaries:\n{e}\n\nPlease install them manually.")
                dialog.destroy()

        import threading
        threading.Thread(target=download_thread, daemon=True).start()


    def update_ytdlp(self):
        self.log_to_console("🔄 Checking for yt-dlp updates...")
        self.settings_frame.update_ytdlp_btn.configure(text="Updating...", fg_color="#e67e22", state="disabled")
        
        def run_update():
            import utils
            try:
                app_dir = os.path.dirname(os.path.abspath(__file__))
                ytdlp_path = os.path.join(app_dir, "yt-dlp.exe")
                
                if not os.path.exists(ytdlp_path):
                    self.log_to_console("❌ Error: yt-dlp.exe is missing. Run setup or restart the app to download it.")
                    self.after(0, lambda: self.settings_frame.update_ytdlp_btn.configure(text="❌ Missing!", fg_color="#c0392b", state="normal"))
                    self.after(3000, lambda: self.settings_frame.update_ytdlp_btn.configure(text="Update yt-dlp", fg_color=["#3a7ebf", "#1f538d"]))
                    return
                
                cmd = [ytdlp_path, "--update"]
                
                ret = utils.run_subprocess_command(
                    cmd,
                    logger_callback=lambda line: self.log_to_console(f"[yt-dlp-update]: {line.strip()}"),
                    cwd=app_dir
                )
                if ret == 0:
                    self.log_to_console("✅ yt-dlp updated successfully!")
                    self.after(0, lambda: self.settings_frame.update_ytdlp_btn.configure(text="✅ Updated!", fg_color="#2ecc71", state="normal"))
                else:
                    self.log_to_console("❌ yt-dlp update failed or already up-to-date.")
                    self.after(0, lambda: self.settings_frame.update_ytdlp_btn.configure(text="❌ Failed/Up-to-date", fg_color="#c0392b", state="normal"))
            except Exception as e:
                self.log_to_console(f"❌ yt-dlp update error: {e}")
                self.after(0, lambda: self.settings_frame.update_ytdlp_btn.configure(text="❌ Error", fg_color="#c0392b", state="normal"))
            
            self.after(3000, lambda: self.settings_frame.update_ytdlp_btn.configure(text="Update yt-dlp", fg_color=["#3a7ebf", "#1f538d"]))
            
        import threading
        threading.Thread(target=run_update, daemon=True).start()


    def refresh_available_models(self):
        # Default fallback models
        models = [
            "gemini-3.5-flash", "gemini-3.5-pro",
            "gemini-3-flash-preview", "gemini-3-pro-preview",
            "gpt-4o", "gpt-4o-mini", 
            "claude-sonnet-4-6", "claude-haiku-4-5-20251001",
            "grok-2-latest", "grok-2-mini",
            "deepseek-chat", "deepseek-reasoner",
            "openrouter/google/gemini-3.5-pro", "openrouter/meta-llama/llama-3.1-70b-instruct",
            "gemini-2.5-flash (Deprecated)", "gemini-2.5-pro (Deprecated)"
        ]
        
        def fetch():
            fetched_models = set()
            
            # 1. Fetch from Google GenAI
            google_key = self.config.get("google", {}).get("api_key", "").strip()
            if google_key:
                try:
                    from google import genai
                    client = genai.Client(api_key=google_key)
                    for m in client.models.list():
                        name = m.name
                        if name.startswith("models/"):
                            name = name.split("/", 1)[1]
                        
                        methods = [method.lower() for method in getattr(m, 'supported_generation_methods', [])]
                        if "gemini" in name.lower() and "generatecontent" in methods:
                            fetched_models.add(name)
                except Exception as e:
                    print(f"Error fetching Google models: {e}")

            # 2. Fetch from OpenAI (or custom base url like deepseek / openrouter)
            openai_key = self.config.get("openai", {}).get("api_key", "").strip()
            base_url = self.config.get("openai", {}).get("base_url", "").strip()
            if openai_key:
                try:
                    from openai import OpenAI
                    client_args = {"api_key": openai_key}
                    if base_url:
                        client_args["base_url"] = base_url
                    client = OpenAI(**client_args)
                    for m in client.models.list():
                        name = m.id
                        if base_url:
                            fetched_models.add(name)
                        elif any(w in name.lower() for w in ["gpt-4", "gpt-3.5", "o1", "o3"]):
                            fetched_models.add(name)
                except Exception as e:
                    print(f"Error fetching OpenAI/Custom models: {e}")

            # 3. Fetch from Anthropic
            anthropic_key = self.config.get("anthropic", {}).get("api_key", "").strip()
            if anthropic_key:
                try:
                    import anthropic
                    client = anthropic.Anthropic(api_key=anthropic_key)
                    for m in client.models.list():
                        fetched_models.add(m.id)
                except Exception as e:
                    print(f"Error fetching Anthropic models: {e}")

            # 4. Fetch from Grok/xAI
            grok_key = self.config.get("xai", {}).get("api_key", "").strip()
            if grok_key:
                try:
                    from openai import OpenAI
                    client = OpenAI(api_key=grok_key, base_url="https://api.x.ai/v1")
                    for m in client.models.list():
                        fetched_models.add(m.id)
                except Exception as e:
                    print(f"Error fetching Grok models: {e}")

            if fetched_models:
                try:
                    current_selection = self.model_menu.get()
                except Exception:
                    current_selection = self.config.get("openai", {}).get("chat_model", "gpt-4o")
                
                dynamic_list = sorted(list(fetched_models))
                combined = []
                
                if current_selection and current_selection not in dynamic_list:
                    combined.append(current_selection)
                    
                combined.extend(dynamic_list)
                combined.extend([m for m in models if m not in dynamic_list and m != current_selection])
                
                self.after(0, lambda: [
                    self.model_menu.configure(values=combined),
                    self.model_menu.set(current_selection)
                ])
        
        import threading
        threading.Thread(target=fetch, daemon=True).start()


    def _init_logging(self):
        log_dir = os.path.join(config_manager.get_app_data_path(), "logs")
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        formatter = logging.Formatter('[%(asctime)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

        # Manual Logger
        manual_path = os.path.join(log_dir, "manual_processor.log")
        self.manual_logger = logging.getLogger("manual_logger")
        self.manual_logger.setLevel(logging.INFO)
        if not self.manual_logger.handlers:
            manual_handler = RotatingFileHandler(manual_path, maxBytes=1024*1024, backupCount=9, encoding='utf-8')
            manual_handler.setFormatter(formatter)
            self.manual_logger.addHandler(manual_handler)

        # Auto Logger
        auto_path = os.path.join(log_dir, "auto_scheduler.log")
        self.auto_logger = logging.getLogger("auto_logger")
        self.auto_logger.setLevel(logging.INFO)
        if not self.auto_logger.handlers:
            auto_handler = RotatingFileHandler(auto_path, maxBytes=1024*1024, backupCount=9, encoding='utf-8')
            auto_handler.setFormatter(formatter)
            self.auto_logger.addHandler(auto_handler)

    def test_openai_key(self):
        key = self.openai_entry.get().strip()
        base_url = self.base_url_entry.get().strip()
        self.test_openai_btn.configure(text="Testing...", fg_color="#e67e22")
        def run_test():
            try:
                from openai import OpenAI # type: ignore
                client_args = {"api_key": key if key else "blank_valid_key"}
                if base_url:
                    client_args["base_url"] = base_url
                client = OpenAI(**client_args)
                client.models.list() 
                self.after(0, lambda: self.test_openai_btn.configure(text="✅ Valid!", fg_color="#2ecc71"))
            except Exception as e:
                print(f"OpenAI Key Test Error: {e}")
                self.after(0, lambda: self.test_openai_btn.configure(text="❌ Invalid", fg_color="#c0392b"))
            self.after(3000, lambda: self.test_openai_btn.configure(text="Test Key", fg_color=["#3a7ebf", "#1f538d"]))
        threading.Thread(target=run_test, daemon=True).start()

    def test_anthropic_key(self):
        key = self.anthropic_entry.get().strip()
        self.test_anthropic_btn.configure(text="Testing...", fg_color="#e67e22")
        def run_test():
            try:
                import anthropic # type: ignore
                client = anthropic.Anthropic(api_key=key)
                client.models.list() 
                self.after(0, lambda: self.test_anthropic_btn.configure(text="✅ Valid!", fg_color="#2ecc71"))
            except Exception as e:
                print(f"Anthropic Key Test Error: {e}")
                self.after(0, lambda: self.test_anthropic_btn.configure(text="❌ Invalid", fg_color="#c0392b"))
            self.after(3000, lambda: self.test_anthropic_btn.configure(text="Test Key", fg_color=["#3a7ebf", "#1f538d"]))
        threading.Thread(target=run_test, daemon=True).start()

    def test_grok_key(self):
        key = self.grok_entry.get().strip()
        self.test_grok_btn.configure(text="Testing...", fg_color="#e67e22")
        def run_test():
            try:
                from openai import OpenAI # type: ignore
                client = OpenAI(api_key=key, base_url="https://api.x.ai/v1")
                client.models.list() 
                self.after(0, lambda: self.test_grok_btn.configure(text="✅ Valid!", fg_color="#2ecc71"))
            except Exception as e:
                print(f"Grok Key Test Error: {e}")
                self.after(0, lambda: self.test_grok_btn.configure(text="❌ Invalid", fg_color="#c0392b"))
            self.after(3000, lambda: self.test_grok_btn.configure(text="Test Key", fg_color=["#3a7ebf", "#1f538d"]))
        threading.Thread(target=run_test, daemon=True).start()

    def test_google_key(self):
        key = self.google_entry.get().strip()
        self.test_google_btn.configure(text="Testing...", fg_color="#e67e22")
        def run_test():
            try:
                from google import genai # type: ignore
                client = genai.Client(api_key=key)
                client.models.list() 
                self.after(0, lambda: self.test_google_btn.configure(text="✅ Valid!", fg_color="#2ecc71"))
            except Exception as e:
                print(f"Google Key Test Error: {e}")
                self.after(0, lambda: self.test_google_btn.configure(text="❌ Invalid", fg_color="#c0392b"))
            self.after(3000, lambda: self.test_google_btn.configure(text="Test Key", fg_color=["#3a7ebf", "#1f538d"]))
        threading.Thread(target=run_test, daemon=True).start()

    def test_discord_webhook(self):
        url = self.discord_entry.get().strip()
        if not url: return
        self.test_discord_btn.configure(text="Testing...", fg_color="#e67e22")
        def run_test():
            try:
                if not url.startswith("https://discord.com/"):
                    raise ValueError("Invalid Discord URL")
                headers = {
                    "Content-Type": "application/json",
                    "User-Agent": "jBahrsClipGen/1.2.1"
                }
                data = json.dumps({"content": "✅ **Test Alert from jBahr's Clip Generator!** The Webhook link is alive."}).encode('utf-8')
                req = urllib.request.Request(url, data=data, headers=headers, method="POST")
                
                with urllib.request.urlopen(req) as response:
                    if response.status in [200, 204]:
                        self.after(0, lambda: self.test_discord_btn.configure(text="✅ Valid!", fg_color="#2ecc71"))
                        self.after(3000, lambda: self.test_discord_btn.configure(text="Test Alert", fg_color=["#3a7ebf", "#1f538d"]))
                        return
                raise ValueError(f"Bad response: {response.status}")
            except Exception as e:
                self.log_to_console(f"❌ Discord Test Failed: {str(e)}")
                self.after(0, lambda: self.test_discord_btn.configure(text="❌ Invalid", fg_color="#c0392b"))
                self.after(3000, lambda: self.test_discord_btn.configure(text="Test Alert", fg_color=["#3a7ebf", "#1f538d"]))
        threading.Thread(target=run_test, daemon=True).start()

    def send_discord_alert(self, title):
        url = self.config.get("integrations", {}).get("discord_webhook", "").strip()
        if not url: return
        def run_alert():
            try:
                if not url.startswith("https://discord.com/"):
                    return
                payload = {
                    "content": None,
                    "embeds": [{
                        "title": "🎬 Generation Complete!",
                        "description": f"The App has finished processing your queue.\n**Event:** {title}",
                        "color": 3066993
                    }]
                }
                headers = {
                    "Content-Type": "application/json",
                    "User-Agent": "jBahrsClipGen/1.2.1"
                }
                data = json.dumps(payload).encode('utf-8')
                req = urllib.request.Request(url, data=data, headers=headers, method="POST")
                with urllib.request.urlopen(req) as _:
                    pass
            except Exception as e:
                self.log_to_console(f"❌ Discord Webhook Failed: {e}")
        threading.Thread(target=run_alert, daemon=True).start()

    def log_to_console(self, text, source="system"):
        tag = None
        if "❌" in text or "error" in text.lower(): tag = "error"
        elif "✅" in text or "✨" in text or "🏁" in text: tag = "success"
        elif "🧠" in text or "🌌" in text or "🤖" in text or "🎯" in text: tag = "ai"
        elif "✂️" in text or "🎞️" in text or "📸" in text or "📱" in text: tag = "ffmpeg"
        
        status_clean = text.split("]")[-1].strip() if "]" in text else text.strip()
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        display_text = f"[{timestamp}] {text}"

        def update_text():
            if source in ["manual", "system"]:
                if source == "manual": self.manual_status_label.configure(text=f"Status: {status_clean}")
                self.console_box.configure(state="normal")
                if tag:
                    self.console_box.insert("end", display_text + "\n", tag)
                else:
                    self.console_box.insert("end", display_text + "\n")
                self.console_box.configure(state="disabled")
                self.console_box.see("end")

            if source in ["auto", "system"]:
                self.auto_console.configure(state="normal")
                if tag:
                    self.auto_console.insert("end", display_text + "\n", tag)
                else:
                    self.auto_console.insert("end", display_text + "\n")
                self.auto_console.configure(state="disabled")
                self.auto_console.see("end")

        self.after(0, update_text)

        # Trigger Discord Webhook on Auto-Scheduler Completion
        if "🏁 Auto-Scheduler finished processing the new video!" in text:
            self.send_discord_alert("Auto-Scheduler Upload Complete")

        # Write to log files
        if source == "manual":
            self.manual_logger.info(text)
        elif source == "auto":
            self.auto_logger.info(text)
        else: # system messages go to both just in case
            self.manual_logger.info(text)
            self.auto_logger.info(text)

        # Legacy crash logger
        try:
            crash_log_path = os.path.join(config_manager.get_app_data_path(), "app_crash_log.txt")
            with open(crash_log_path, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] {text}\n")
        except Exception as e:
            pass

    def browse_folder(self, entry_widget):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            entry_widget.delete(0, "end")
            entry_widget.insert(0, folder_selected)

    def open_logs(self):
        log_path = os.path.join(config_manager.get_app_data_path(), "app_crash_log.txt")
        if os.path.exists(log_path):
            subprocess.run(['explorer', '/select,', log_path])
        else:
            app_data_path = config_manager.get_app_data_path()
            if hasattr(os, 'startfile'):
                os.startfile(os.path.abspath(app_data_path)) # type: ignore

    def open_local_folder(self, key):
        path = self.config.get('settings', {}).get(key, "")
        if path and hasattr(os, 'startfile'): 
            os.startfile(os.path.abspath(path)) # type: ignore

    def open_readme(self):
        if os.path.exists("README.md") and hasattr(os, 'startfile'): 
            os.startfile(os.path.abspath("README.md")) # type: ignore

    def get_video_id(self, url):
        try:
            startupinfo = None
            if os.name == 'nt' and hasattr(subprocess, 'STARTUPINFO'):
                startupinfo = subprocess.STARTUPINFO() # type: ignore
                if hasattr(subprocess, 'STARTF_USESHOWWINDOW'):
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW # type: ignore
                if hasattr(subprocess, 'SW_HIDE'):
                    startupinfo.wShowWindow = subprocess.SW_HIDE # type: ignore

            cmd = [watcher.YTDLP_PATH, "--get-id", "--", url]
            result = subprocess.run(cmd, capture_output=True, text=True, startupinfo=startupinfo)
            return result.stdout.strip()
        except Exception as e:
            self.log_to_console(f"❌ yt-dlp error: {e}") 
            return None

    def show_manual_frame(self):
        self._hide_all_frames()
        self.manual_frame.grid(row=0, column=1, sticky="nsew")
        self._highlight_button(self.nav_manual_btn)

    def show_auto_frame(self):
        self._hide_all_frames()
        self.auto_frame.grid(row=0, column=1, sticky="nsew")
        self._highlight_button(self.nav_auto_btn)

    def show_prompt_frame(self):
        self._hide_all_frames()
        self.prompt_frame.grid(row=0, column=1, sticky="nsew")
        self._highlight_button(self.nav_prompt_btn)

    def show_settings_frame(self):
        self._hide_all_frames()
        self.settings_frame.grid(row=0, column=1, sticky="nsew")
        self._highlight_button(self.nav_settings_btn)
        self.refresh_available_models()

    def show_gallery_frame(self):
        self._hide_all_frames()
        self.gallery_frame.grid(row=0, column=1, sticky="nsew")
        self._highlight_button(self.nav_gallery_btn)
        self.populate_gallery()

    def _hide_all_frames(self):
        for f in [self.manual_frame, self.auto_frame, self.prompt_frame, self.settings_frame, self.gallery_frame]: 
            f.grid_forget()

    def _highlight_button(self, active_button):
        for btn in [self.nav_manual_btn, self.nav_auto_btn, self.nav_prompt_btn, self.nav_settings_btn, self.nav_gallery_btn]: 
            btn.configure(fg_color="transparent")
        active_button.configure(fg_color="#1f538d")

    def load_prompt_data(self):
        profiles = self.config.get("prompts", {}).get("profiles", {})
        if not profiles: return
        p_names = list(profiles.keys())
        self.profile_dropdown.configure(values=p_names)
        active = self.config["prompts"].get("active_profile", p_names[0])
        self.profile_dropdown.set(active)
        self.on_profile_change(active)
        self.auto_prompt_menu.configure(values=p_names)
        auto_active = self.config.get("auto_scheduler", {}).get("auto_prompt_profile", p_names[0])
        self.auto_prompt_menu.set(auto_active if auto_active in p_names else p_names[0])

    def on_profile_change(self, choice):
        self.config["prompts"]["active_profile"] = choice
        p_text = self.config["prompts"]["profiles"].get(choice, "")
        self.prompt_textbox.delete("1.0", "end")
        self.prompt_textbox.insert("1.0", p_text)

    def create_new_profile(self):
        dialog = ctk.CTkInputDialog(text="Enter a name for your new prompt profile:", title="New Profile")
        new_name = dialog.get_input()
        
        if new_name:
            new_name = new_name.strip()
            if new_name and new_name not in self.config["prompts"]["profiles"]:
                self.config["prompts"]["profiles"][new_name] = "You are a specialized Gaming Editor. Your goal is to..."
                self.config["prompts"]["active_profile"] = new_name
                config_manager.save_config(self.config)
                self.load_prompt_data()
                self.log_to_console(f"📝 Created new prompt profile: '{new_name}'")

    def save_current_prompt(self):
        active = self.profile_dropdown.get()
        self.config["prompts"]["profiles"][active] = self.prompt_textbox.get("1.0", "end").strip()
        config_manager.save_config(self.config)
        self.save_prompt_btn.configure(text="✅ Saved!", fg_color="#2ecc71")
        self.after(2000, lambda: self.save_prompt_btn.configure(text="Save Prompt", fg_color=["#3a7ebf", "#1f538d"]))

    def delete_profile(self):
        active = self.profile_dropdown.get()
        if len(self.config["prompts"]["profiles"]) > 1:
            if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete the profile '{active}'?"):
                del self.config["prompts"]["profiles"][active]
                config_manager.save_config(self.config)
                self.load_prompt_data()
        else:
            messagebox.showwarning("Cannot Delete", "You must have at least one prompt profile.")

    def save_settings(self):
        self.config['youtube']['channel_id'] = self.yt_id_entry.get()
        self.config['twitch']['username'] = self.twitch_entry.get()
        self.config['openai']['api_key'] = self.openai_entry.get()
        self.config['openai']['base_url'] = self.base_url_entry.get()
        
        if 'anthropic' not in self.config:
            self.config['anthropic'] = {}
        self.config['anthropic']['api_key'] = self.anthropic_entry.get()
        
        if 'xai' not in self.config:
            self.config['xai'] = {}
        self.config['xai']['api_key'] = self.grok_entry.get()
        
        if 'google' not in self.config:
            self.config['google'] = {}
        self.config['google']['api_key'] = self.google_entry.get()
        
        self.config['openai']['chat_model'] = self.model_menu.get()
        self.config['openai']['whisper_model'] = self.whisper_menu.get()
        self.config['openai']['whisper_language'] = self.language_menu.get()
        self.config['settings']['download_quality'] = self.quality_menu.get()
        self.config['settings']['download_dir'] = self.vod_dir_entry.get()
        self.config['settings']['clips_dir'] = self.clip_dir_entry.get()
        self.config['settings']['auth_browser'] = self.browser_menu.get()
        
        self.config['settings']['vr_stabilization'] = self.stabilize_switch.get() == 1
        self.config['settings']['hardware_encoding'] = self.hardware_switch.get() == 1
        self.config['settings']['audio_downmix'] = self.downmix_switch.get() == 1
        self.config['settings']['audio_peak_detection'] = self.audio_peak_switch.get() == 1
        self.config['settings']['combat_detection'] = self.combat_switch.get() == 1
        self.config['settings']['vertical_export'] = self.vertical_switch.get() == 1
        self.config['settings']['vertical_mode'] = self.vertical_mode_menu.get()
        self.config['settings']['crop_x'] = self.crop_x_entry.get()
        self.config['settings']['crop_y'] = self.crop_y_entry.get()
        self.config['settings']['crop_w'] = self.crop_w_entry.get()
        self.config['settings']['crop_h'] = self.crop_h_entry.get()

        config_manager.save_config(self.config)
        self.log_to_console("✅ Settings saved!")
        self.refresh_available_models()

        # Provide immediate visual feedback on the button (prevent double-click bug)
        if self.save_btn.cget("text") != "✅ Saved!":
            self.original_btn_color = self.save_btn.cget("fg_color")

        self.save_btn.configure(text="✅ Saved!", fg_color="#2ecc71")
        self.after(2000, lambda: self.save_btn.configure(text="Save Settings", fg_color=getattr(self, 'original_btn_color', ["#3a7ebf", "#1f538d"])))

    # --- Gallery Logic ---
    def refresh_gallery_action(self):
        self.populate_gallery()

        if self.refresh_gallery_btn.cget("text") != "✅ Refreshed!":
            self.original_refresh_btn_color = self.refresh_gallery_btn.cget("fg_color")

        self.refresh_gallery_btn.configure(text="✅ Refreshed!", fg_color="#2ecc71")
        self.after(2000, lambda: self.refresh_gallery_btn.configure(text="🔄 Refresh List", fg_color=getattr(self, 'original_refresh_btn_color', ["#3a7ebf", "#1f538d"])))

    def toggle_select_all(self):
        select_state = self.select_all_var.get()
        if hasattr(self, 'marked_for_deletion'):
            for var in self.marked_for_deletion.values():
                var.set(select_state)

    def populate_gallery(self):
        for widget in self.clip_listbox.winfo_children():
            widget.destroy()

        # Reset select all checkbox
        if hasattr(self, 'select_all_var'):
            self.select_all_var.set(False)

        clips_dir = self.config.get('settings', {}).get('clips_dir', '')
        if not clips_dir or not os.path.exists(clips_dir):
            empty_label = ctk.CTkLabel(self.clip_listbox, text="Clip folder not set or does not exist.", font=ctk.CTkFont(slant="italic"), text_color="gray")
            empty_label.pack(pady=20)
            return

        sort_mode = self.sort_menu.get()
        self.marked_for_deletion = {}
        
        # Gather file data for sorting
        clip_data = []
        for f in os.listdir(clips_dir):
            if f.endswith(".mp4"):
                full_path = os.path.join(clips_dir, f)
                ctime = os.path.getctime(full_path)
                
                score = 0
                # Try to get virality score from JSON if sorting by it
                if "Virality" in sort_mode:
                    json_path = os.path.join(clips_dir, f.replace("_vertical.mp4", ".mp4").replace(".mp4", ".json"))
                    if os.path.exists(json_path):
                        try:
                            with open(json_path, 'r', encoding='utf-8') as jf:
                                jdata = json.load(jf)
                                score = float(jdata.get("virality_score", 0))
                        except Exception as e:
                            print(f"Error reading virality score from {json_path}: {e}")
                
                clip_data.append({
                    "filename": f,
                    "ctime": ctime,
                    "score": score
                })

        # Apply sorting
        if sort_mode == "Date (Newest)":
            clip_data.sort(key=lambda x: x["ctime"], reverse=True)
        elif sort_mode == "Date (Oldest)":
            clip_data.sort(key=lambda x: x["ctime"])
        elif sort_mode == "Virality (High)":
            clip_data.sort(key=lambda x: (x["score"], x["ctime"]), reverse=True)
        elif sort_mode == "Virality (Low)":
            clip_data.sort(key=lambda x: (x["score"], -x["ctime"]))

        # Apply Filters
        type_filter = self.type_filter_menu.get()
        score_filter = self.score_filter_menu.get()
        min_score = 0
        if score_filter != "All":
            min_score = int(score_filter.replace("+", ""))

        visible_count = 0
        for item in clip_data:
            file = item["filename"]
            
            # Filter by Orientation
            is_vertical = "_vertical" in str(file)
            if type_filter == "Horizontal" and is_vertical: continue
            if type_filter == "Vertical" and not is_vertical: continue

            # Filter by Score
            if float(item["score"]) < min_score: continue

            visible_count += 1
            row_frame = ctk.CTkFrame(self.clip_listbox, fg_color="transparent")
            row_frame.pack(fill="x", pady=2, padx=5)
            
            self.marked_for_deletion[file] = ctk.BooleanVar(value=False)
            checkbox = ctk.CTkCheckBox(row_frame, text="", variable=self.marked_for_deletion[file], width=20)
            checkbox.pack(side="left", padx=(0, 5))

            btn = ctk.CTkButton(row_frame, text=file, fg_color="#2b2b2b", hover_color="#3b3b3b", anchor="w", 
                                command=lambda f=file: self.load_clip_details(f, clips_dir))
            btn.pack(side="left", fill="x", expand=True)

        if visible_count == 0:
            empty_label = ctk.CTkLabel(self.clip_listbox, text="No clips found matching current filters.", font=ctk.CTkFont(slant="italic"), text_color="gray")
            empty_label.pack(pady=20)

    def confirm_delete_marked(self):
        files_to_delete = [f for f, var in getattr(self, 'marked_for_deletion', {}).items() if var.get()]
        if not files_to_delete:
            return
            
        from tkinter import messagebox
        confirm = messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete {len(files_to_delete)} marked clip(s)?\n\nThis will also delete the associated .jpg and .json metadata files.")
        if confirm:
            clips_dir = self.config.get('settings', {}).get('clips_dir', '')
            for f in files_to_delete:
                mp4_path = os.path.join(clips_dir, f)
                json_path = os.path.join(clips_dir, f.replace("_vertical.mp4", ".mp4").replace(".mp4", ".json"))
                jpg_path = os.path.join(clips_dir, f.replace("_vertical.mp4", ".mp4").replace(".mp4", ".jpg"))
                
                for p in [mp4_path, json_path, jpg_path]:
                    if os.path.exists(p):
                        try:
                            os.remove(p)
                        except Exception as e:
                            self.log_to_console(f"❌ Failed to delete {p}: {e}", source="system")
            
            self.populate_gallery()
            self.detail_title.configure(text="Select a clip to view details")
            self.detail_score.configure(text="Score: --/10")
            self.detail_reasoning.configure(state="normal")
            self.detail_reasoning.delete("1.0", "end")
            self.detail_reasoning.configure(state="disabled")
            self.detail_thumbnail.configure(image=None) # type: ignore
            self.play_clip_btn.configure(state="disabled")
            self.open_folder_btn.configure(state="disabled")

    def load_clip_details(self, filename, directory):
        self.detail_title.configure(text=filename)
        mp4_path = os.path.join(directory, filename)
        
        base_json_name = filename.replace("_vertical.mp4", ".mp4").replace(".mp4", ".json")
        json_path = os.path.join(directory, base_json_name)

        self.detail_reasoning.configure(state="normal")
        self.detail_reasoning.delete("1.0", "end")

        if os.path.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    score = data.get("virality_score", "N/A")
                    reasoning = data.get("reasoning", "No reasoning provided by AI.")
                    self.detail_score.configure(text=f"Virality Score: {score}/10")
                    self.detail_reasoning.insert("1.0", reasoning)
            except Exception as e:
                self.detail_score.configure(text="Score: N/A")
                self.detail_reasoning.insert("1.0", "Error reading metadata.")
        else:
            self.detail_score.configure(text="Score: N/A")
            self.detail_reasoning.insert("1.0", "No AI metadata found for this clip (might be an older generation).")

        self.detail_reasoning.configure(state="disabled")
        
        # Load large thumbnail
        thumb_name = filename.replace("_vertical.mp4", ".mp4").replace(".mp4", ".jpg")
        thumb_path = os.path.join(directory, thumb_name)
        if os.path.exists(thumb_path):
            try:
                pil_img = Image.open(thumb_path)
                # Calculate size to fit well (e.g. max width 600, or let CTkImage handle it)
                width, height = pil_img.size
                ratio = min(600 / width, 300 / height)
                new_w, new_h = int(width * ratio), int(height * ratio)
                large_clip_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(new_w, new_h))
                self.detail_thumbnail.configure(image=large_clip_img)
            except Exception as e:
                self.detail_thumbnail.configure(image=None) # type: ignore
        else:
            self.detail_thumbnail.configure(image=None) # type: ignore

        if hasattr(os, 'startfile'):
            self.play_clip_btn.configure(state="normal", command=lambda: os.startfile(mp4_path)) # type: ignore
            self.open_folder_btn.configure(state="normal", command=lambda: subprocess.run(['explorer', '/select,', os.path.abspath(mp4_path)]))

    # --- Processing Engine ---
    def browse_local_file(self):
        file_paths = filedialog.askopenfilenames(
            title="Select Local Video File(s)",
            filetypes=[("Video Files", "*.mp4 *.mkv *.avi *.mov *.flv")]
        )
        if file_paths:
            self.url_input.delete(0, "end")
            self.url_input.insert(0, ";".join(file_paths))

    def cancel_manual_process(self):
        self.cancel_requested = True
        self.cancel_btn.configure(state="disabled", text="Cancelling...")
        self.log_to_console("🛑 Cancellation requested. Aborting as soon as possible...", source="manual")

    def start_manual_process(self, event=None):
        input_val = self.url_input.get().strip()
        if input_val:
            self.cancel_requested = False
            self.process_btn.configure(state="disabled", text="Processing...")
            self.local_file_btn.configure(state="disabled")
            self.cancel_btn.configure(state="normal", text="Cancel")
            self.manual_progress.start()
            self.console_box.configure(state="normal")
            self.console_box.delete("1.0", "end")
            self.console_box.configure(state="disabled")
            
            threading.Thread(target=self._process_video_thread, args=(input_val,), daemon=True).start()

    def _process_video_thread(self, input_val):
        try:
            profile = self.profile_dropdown.get()
            queue = [item.strip() for item in input_val.split(";") if item.strip()]
            
            for index, item in enumerate(queue):
                if self.cancel_requested: break
                
                if len(queue) > 1:
                    self.log_to_console(f"\n📦 BATCH PROCESS: Starting item {index + 1} of {len(queue)}...", source="manual")

                if os.path.exists(item):
                    self.log_to_console(f"📁 Local file detected: {item}", source="manual")
                    editor.process_video(item, prompt_profile=profile, logger=lambda msg: self.log_to_console(msg, source="manual"), is_cancelled=lambda: self.cancel_requested)
                    
                elif item.startswith("http") or "twitch.tv" in item or "youtu" in item:
                    self.log_to_console(f"🌐 URL detected: {item}", source="manual")
                    v_id = self.get_video_id(item)
                    if not v_id:
                        self.log_to_console("❌ Video ID error. Skipping.", source="manual")
                        continue
                    f_path = watcher.download_with_subprocess(item, v_id, logger_callback=lambda msg: self.log_to_console(msg, source="manual"), force_manual=True, is_cancelled=lambda: self.cancel_requested)
                    if self.cancel_requested: break
                    if f_path:
                        editor.process_video(f_path, prompt_profile=profile, logger=lambda msg: self.log_to_console(msg, source="manual"), is_cancelled=lambda: self.cancel_requested)
                else:
                    self.log_to_console(f"❌ Invalid input: {item}", source="manual")

            if self.cancel_requested:
                self.log_to_console("🛑 Process aborted by user.", source="manual")
            else:
                self.log_to_console("🏁 ALL TASKS COMPLETE!", source="manual")
                self.send_discord_alert("Manual Queue Finished")
                self.after(0, lambda: self.process_btn.configure(text="✅ Complete!", fg_color="#27ae60"))
                self.after(3000, lambda: self.process_btn.configure(text="Process Queue", fg_color=["#3a7ebf", "#1f538d"]))
                
        except Exception as e:
            self.log_to_console(f"❌ Error: {e}", source="manual")
        finally:
            self.after(0, lambda: [
                self.process_btn.configure(state="normal"), 
                self.local_file_btn.configure(state="normal"),
                self.cancel_btn.configure(state="disabled", text="Cancel"),
                self.manual_progress.stop(),
                self.manual_status_label.configure(text="Status: Ready"),
                self.populate_gallery()
            ])

    def toggle_auto(self):
        if self.auto_switch.get() == 1:
            if "auto_scheduler" not in self.config:
                self.config["auto_scheduler"] = {}
            self.config["auto_scheduler"]["platform"] = self.platform_menu.get()
            self.config["auto_scheduler"]["video_type"] = self.type_menu.get()
            self.config["auto_scheduler"]["target_orientation"] = self.target_menu.get()
            self.config["auto_scheduler"]["lookback_days"] = self.lookback_menu.get()
            self.config["auto_scheduler"]["check_interval"] = self.interval_menu.get()
            self.config["auto_scheduler"]["auto_prompt_profile"] = self.auto_prompt_menu.get()
            config_manager.save_config(self.config)

            self.is_auto_running = True
            self.auto_status.configure(text="● Status: RUNNING", text_color="#2ecc71")
            self.auto_progress.start()
            self.log_to_console("📡 Auto-Scheduler enabled. Saving config and monitoring channels...", source="auto")
            threading.Thread(target=self._auto_run_loop, daemon=True).start()
        else:
            self.is_auto_running = False
            self.auto_status.configure(text="● Status: OFF", text_color="gray")
            self.auto_progress.stop()
            self.auto_progress.set(0)
            self.log_to_console("🛑 Auto-Scheduler disabled.", source="auto")

    def _auto_run_loop(self):
        while self.is_auto_running:
            watcher.main(logger_callback=lambda msg: self.log_to_console(msg, source="auto"))
            
            # Map check_interval from config to seconds
            interval_str = self.config.get("auto_scheduler", {}).get("check_interval", "Every 4 Hours")
            if interval_str == "Every 1 Hour":
                seconds = 3600
            elif interval_str == "Every 12 Hours":
                seconds = 43200
            elif interval_str == "Every 24 Hours":
                seconds = 86400
            else: # "Every 4 Hours"
                seconds = 14400
                
            for _ in range(seconds):
                if not self.is_auto_running: break
                time.sleep(1)

    def minimize_to_tray(self):
        self.withdraw() 
        try:
            image = Image.open("app_icon.ico")
        except Exception as e:
            print(f"Error loading tray icon: {e}")
            image = Image.new('RGB', (64, 64), color=(31, 83, 141))

        menu = pystray.Menu(
            pystray.MenuItem('Show Generator', self.show_window),
            pystray.MenuItem('Quit', self.quit_window)
        )
        
        self.tray_icon = pystray.Icon("jBahrsClipGen", image, "jBahr's Clip Generator", menu) # type: ignore
        self.tray_icon.run_detached() # type: ignore

    def show_window(self, icon, item):
        if self.tray_icon: 
            self.tray_icon.stop() # type: ignore
        self.after(0, self.deiconify) 

    def quit_window(self, icon, item):
        if self.tray_icon: 
            self.tray_icon.stop() # type: ignore
        self.is_auto_running = False  
        self.after(0, self.destroy)   

if __name__ == "__main__":
    app = ClipGenApp()
    app.mainloop()