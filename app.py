import sys
import os
import subprocess

# Auto-re-launch with project virtual environment if invoked with global/system Python
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)
venv_python = os.path.join(script_dir, ".venv", "Scripts", "python.exe")
if __name__ == "__main__" and os.path.exists(venv_python) and os.path.normcase(os.path.abspath(sys.executable)) != os.path.normcase(os.path.abspath(venv_python)):
    print(f"[ClipGen] Switching to virtual environment Python: {venv_python}")
    app_script = os.path.abspath(__file__)
    ret = subprocess.call([venv_python, app_script] + sys.argv[1:], cwd=script_dir)
    sys.exit(ret)

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
logging.getLogger("google_genai").setLevel(logging.ERROR)
from logging.handlers import RotatingFileHandler
import datetime
from gallery_manager import GalleryMetadataCache, ThumbnailCache, scan_and_filter_clips
from event_bus import EventBus, Event, get_event_bus
from queue_manager import QueueManager, QueueItem
import utils
utils.ensure_app_dir_in_path()

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

        # Initialize thread-safe application Event Bus
        self.event_bus = get_event_bus()

        # Initialize Multi-Video Queue Manager
        self.queue_manager = QueueManager(event_bus=self.event_bus)
        self.event_bus.subscribe(Event.QUEUE_UPDATED, self._on_queue_updated)
        self.event_bus.subscribe(Event.SOCIAL_PUBLISHED, self._on_social_published)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # Instantiate views from gui package with callbacks
        self.sidebar_frame = gui.Sidebar(
            self,
            on_navigate=self.navigate_tab,
            on_quick_action=self.handle_quick_action
        )
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")

        self.manual_frame = gui.ManualFrame(
            self,
            on_start_process=self.start_manual_process,
            on_cancel_process=self.cancel_manual_process,
            on_browse_files=self.browse_local_file,
            on_add_to_queue=self.add_manual_input_to_queue,
            on_remove_queue_item=self.remove_queue_item,
            on_clear_completed=self.clear_completed_queue,
            on_clear_all=self.clear_all_queue,
            on_item_profile_changed=self.on_queue_item_profile_changed,
            on_item_orientation_changed=self.on_queue_item_orientation_changed,
            on_files_dropped=self.on_files_dropped
        )
        # Aliasing for backwards compatibility
        self.url_input = self.manual_frame.url_input
        self.process_btn = self.manual_frame.process_btn
        self.cancel_btn = self.manual_frame.cancel_btn
        self.local_file_btn = self.manual_frame.local_file_btn
        self.manual_status_label = self.manual_frame.manual_status_label
        self.manual_progress = self.manual_frame.manual_progress
        self.console_box = self.manual_frame.console_box
        self.add_queue_btn = getattr(self.manual_frame, 'add_queue_btn', None)
        self.queue_card = getattr(self.manual_frame, 'queue_card', None)
        self.queue_scroll = getattr(self.manual_frame, 'queue_scroll', None)

        self.auto_frame = gui.AutoFrame(
            self,
            on_toggle_auto=lambda _: self.toggle_auto()
        )
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

        self.prompt_frame = gui.PromptFrame(
            self,
            on_profile_change=self.on_profile_change,
            on_new_profile=self.create_new_profile,
            on_save_prompt=self.save_current_prompt,
            on_delete_profile=self.delete_profile
        )
        self.profile_dropdown = self.prompt_frame.profile_dropdown
        self.new_profile_btn = self.prompt_frame.new_profile_btn
        self.delete_profile_btn = self.prompt_frame.delete_profile_btn
        self.prompt_textbox = self.prompt_frame.prompt_textbox
        self.save_prompt_btn = self.prompt_frame.save_prompt_btn

        self.settings_frame = gui.SettingsFrame(
            self,
            on_save=self.save_settings,
            on_test_key=self.test_api_key_dispatch,
            on_browse_folder=self.browse_folder_dispatch,
            on_update_ytdlp=self.update_ytdlp,
            on_verify_social=self.verify_social_credentials,
            on_refresh_models=lambda: self.refresh_available_models(manual=True)
        )
        self.yt_id_entry = self.settings_frame.yt_id_entry
        self.twitch_entry = self.settings_frame.twitch_entry
        self.openai_entry = self.settings_frame.openai_entry
        self.base_url_entry = self.settings_frame.base_url_entry
        self.test_openai_btn = self.settings_frame.test_openai_btn
        self.anthropic_entry = self.settings_frame.anthropic_entry
        self.test_anthropic_btn = self.settings_frame.test_anthropic_btn
        self.grok_entry = self.settings_frame.grok_entry
        self.test_grok_btn = self.settings_frame.test_grok_btn
        self.google_entry = self.settings_frame.google_entry
        self.test_google_btn = self.settings_frame.test_google_btn
        self.discord_entry = self.settings_frame.discord_entry
        self.test_discord_btn = self.settings_frame.test_discord_btn
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
        self.save_btn = self.settings_frame.save_btn
        self.update_ytdlp_btn = self.settings_frame.update_ytdlp_btn
        self.verify_yt_btn = getattr(self.settings_frame, 'verify_yt_btn', None)
        self.verify_tiktok_btn = getattr(self.settings_frame, 'verify_tiktok_btn', None)
        self.verify_ig_btn = getattr(self.settings_frame, 'verify_ig_btn', None)

        self.gallery_frame = gui.GalleryFrame(
            self,
            on_filter_changed=self.populate_gallery,
            on_refresh=self.refresh_gallery_action,
            on_delete_marked=self.confirm_delete_marked,
            on_publish_clip=self.open_publish_dialog
        )
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
        self.publish_clip_btn = getattr(self.gallery_frame, 'publish_clip_btn', None)

        self.gallery_meta_cache = GalleryMetadataCache()
        self.thumbnail_cache = ThumbnailCache(maxsize=64)
        self._gallery_scan_id = 0

        # Align sidebar buttons references for highlights
        self.nav_manual_btn = self.sidebar_frame.nav_manual_btn
        self.nav_auto_btn = self.sidebar_frame.nav_auto_btn
        self.nav_prompt_btn = self.sidebar_frame.nav_prompt_btn
        self.nav_settings_btn = self.sidebar_frame.nav_settings_btn
        self.nav_gallery_btn = self.sidebar_frame.nav_gallery_btn

        self.load_prompt_data()
        self.show_manual_frame()

        self.deiconify()
        self.lift()
        self.attributes('-topmost', True)
        self.after(500, lambda: self.attributes('-topmost', False))
        self.focus_force()

        self.after(100, self.check_and_download_binaries)
        self.after(300, lambda: self.refresh_available_models(manual=False))

    def check_and_download_binaries(self):
        if os.name != 'nt':
            return  # Auto-download only implemented for Windows environment

        app_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
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

        def set_status(text, progress=None):
            def update():
                try:
                    status_label.configure(text=text)
                    if progress is not None:
                        progress_bar.set(progress)
                except Exception:
                    pass
            self.after(0, update)

        def close_dialog():
            self.after(0, lambda: dialog.destroy())

        def show_error(msg):
            def on_err():
                try:
                    status_label.configure(text=f"Error: {msg}")
                    messagebox.showerror("Error", f"Failed to download required binaries:\n{msg}\n\nPlease install them manually.")
                    dialog.destroy()
                except Exception:
                    pass
            self.after(0, on_err)

        def download_thread():
            try:
                import requests
                import zipfile
                import io
            except ImportError:
                self.log_to_console("❌ Error: Missing requests library. Run 'pip install -r requirements.txt'")
                set_status("Error: Missing 'requests' module. Check logs.")
                return

            try:
                # 1. Download yt-dlp.exe if missing
                if "yt-dlp" in missing:
                    self.log_to_console("📥 Downloading yt-dlp.exe...")
                    set_status("Downloading yt-dlp.exe...")
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
                                    set_status(f"Downloading yt-dlp.exe ({int(percent * 100)}%)", percent)
                    self.log_to_console("✅ yt-dlp.exe downloaded successfully!")

                # 2. Download ffmpeg.exe if missing
                if "ffmpeg" in missing:
                    self.log_to_console("📥 Downloading FFmpeg zip...")
                    set_status("Downloading FFmpeg builds (zip)...", 0)

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
                                set_status(f"Downloading FFmpeg ({int(percent * 90)}%)", percent * 0.9)

                    set_status("Extracting ffmpeg.exe...")

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

                    set_status("Finished downloading all components!", 1.0)

                time.sleep(1)
                close_dialog()

            except Exception as e:
                self.log_to_console(f"❌ Error during binary download/extraction: {e}")
                show_error(str(e))

        import threading
        threading.Thread(target=download_thread, daemon=True).start()

    def navigate_tab(self, tab: str):
        if tab == "manual":
            self.show_manual_frame()
        elif tab == "auto":
            self.show_auto_frame()
        elif tab == "prompt":
            self.show_prompt_frame()
        elif tab == "settings":
            self.show_settings_frame()
        elif tab == "gallery":
            self.show_gallery_frame()
        if 'event_bus' in self.__dict__ and self.event_bus:
            self.event_bus.publish(Event.NAVIGATE, tab)

    def handle_quick_action(self, action: str):
        if action in ("download_dir", "clips_dir"):
            self.open_local_folder(action)
        elif action == "logs":
            self.open_logs()
        elif action == "readme":
            self.open_readme()

    def test_api_key_dispatch(self, provider: str):
        if provider == "openai":
            self.test_openai_key()
        elif provider == "anthropic":
            self.test_anthropic_key()
        elif provider == "grok":
            self.test_grok_key()
        elif provider == "google":
            self.test_google_key()
        elif provider == "discord":
            self.test_discord_webhook()

    def browse_folder_dispatch(self, field_name: str):
        entry = self.settings_frame.vod_dir_entry if field_name == "download_dir" else self.settings_frame.clip_dir_entry
        self.browse_folder(entry)


    def update_ytdlp(self):
        self.log_to_console("🔄 Checking for yt-dlp updates...")
        self.settings_frame.update_ytdlp_btn.configure(text="Updating...", fg_color="#e67e22", state="disabled")
        
        def run_update():
            import utils
            try:
                app_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
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


    def refresh_available_models(self, manual: bool = False):
        """
        Dynamically refreshes the list of available AI models across all configured providers
        and public catalogs, updating the UI dropdown.
        """
        if manual and hasattr(self, 'settings_frame') and hasattr(self.settings_frame, 'set_refreshing_models_state'):
            self.settings_frame.set_refreshing_models_state(True)

        active_keys = {}
        if hasattr(self, 'settings_frame'):
            if hasattr(self.settings_frame, 'google_entry'):
                active_keys["google"] = self.settings_frame.google_entry.get().strip()
            if hasattr(self.settings_frame, 'openai_entry'):
                active_keys["openai"] = self.settings_frame.openai_entry.get().strip()
            if hasattr(self.settings_frame, 'base_url_entry'):
                active_keys["base_url"] = self.settings_frame.base_url_entry.get().strip()
            if hasattr(self.settings_frame, 'anthropic_entry'):
                active_keys["anthropic"] = self.settings_frame.anthropic_entry.get().strip()
            if hasattr(self.settings_frame, 'grok_entry'):
                active_keys["xai"] = self.settings_frame.grok_entry.get().strip()

        try:
            current_selection = self.model_menu.get() if hasattr(self, 'model_menu') else ""
        except Exception:
            current_selection = ""
        if not current_selection:
            current_selection = self.config.get("openai", {}).get("chat_model", "gemini-3.6-flash")

        def fetch():
            import model_fetcher
            try:
                models = model_fetcher.fetch_all_dynamic_models(
                    config=self.config,
                    active_keys=active_keys,
                    current_selection=current_selection
                )
            except Exception as e:
                logging.getLogger("app").warning(f"Error fetching dynamic models: {e}")
                models = model_fetcher.load_cached_models() or model_fetcher.BASELINE_MODELS

            def apply_to_gui():
                if hasattr(self, 'settings_frame') and hasattr(self.settings_frame, 'set_available_models'):
                    self.settings_frame.set_available_models(models)
                    if hasattr(self.settings_frame, 'model_menu'):
                        self.settings_frame.model_menu.set(current_selection)
                elif hasattr(self, 'model_menu'):
                    self.model_menu.configure(values=models)
                    self.model_menu.set(current_selection)

                if manual and hasattr(self, 'settings_frame') and hasattr(self.settings_frame, 'set_refreshing_models_state'):
                    self.settings_frame.set_refreshing_models_state(False, "✅ Updated!")

            self.after(0, apply_to_gui)

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
                self.after(300, lambda: self.refresh_available_models(manual=False))
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
                self.after(300, lambda: self.refresh_available_models(manual=False))
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
                self.after(300, lambda: self.refresh_available_models(manual=False))
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
                self.after(300, lambda: self.refresh_available_models(manual=False))
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

    def verify_social_credentials(self, platform: str) -> None:
        """Verifies API credentials for YouTube Shorts, TikTok, or Instagram Reels."""
        from social_publisher import get_social_publish_manager, SocialPlatform

        btn_map = {
            SocialPlatform.YOUTUBE_SHORTS.value: getattr(self.settings_frame, 'verify_yt_btn', None),
            SocialPlatform.TIKTOK.value: getattr(self.settings_frame, 'verify_tiktok_btn', None),
            SocialPlatform.INSTAGRAM_REELS.value: getattr(self.settings_frame, 'verify_ig_btn', None)
        }
        btn = btn_map.get(platform)
        orig_text = btn.cget("text") if btn else "Verify"
        orig_color = btn.cget("fg_color") if btn else ["#3a7ebf", "#1f538d"]

        if btn:
            btn.configure(text="Verifying...", fg_color="#e67e22")

        def run_verify():
            try:
                curr_settings = self.settings_frame.get_settings()
                mgr = get_social_publish_manager()
                success, msg = mgr.verify_platform(platform, curr_settings)

                def update_ui():
                    if btn:
                        if success:
                            btn.configure(text="✅ Valid!", fg_color="#2ecc71")
                        else:
                            btn.configure(text="❌ Invalid", fg_color="#c0392b")
                        self.after(3000, lambda: btn.configure(text=orig_text, fg_color=orig_color))
                    self.log_to_console(f"[{platform}] {msg}")

                self.after(0, update_ui)
            except Exception as e:
                def update_err():
                    if btn:
                        btn.configure(text="❌ Error", fg_color="#c0392b")
                        self.after(3000, lambda: btn.configure(text=orig_text, fg_color=orig_color))
                    self.log_to_console(f"[{platform}] Verification failed: {e}")
                self.after(0, update_err)

        threading.Thread(target=run_verify, daemon=True).start()

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
        text = utils.redact_sensitive(str(text))
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
                if source == "manual":
                    if 'manual_frame' in self.__dict__ and hasattr(self.manual_frame, 'set_status'):
                        self.manual_frame.set_status(f"Status: {status_clean}")
                    elif 'manual_status_label' in self.__dict__:
                        self.manual_status_label.configure(text=f"Status: {status_clean}")

                if 'manual_frame' in self.__dict__ and hasattr(self.manual_frame, 'append_log'):
                    self.manual_frame.append_log(display_text, tag)
                elif 'console_box' in self.__dict__:
                    self.console_box.configure(state="normal")
                    if tag:
                        self.console_box.insert("end", display_text + "\n", tag)
                    else:
                        self.console_box.insert("end", display_text + "\n")
                    self.console_box.configure(state="disabled")
                    self.console_box.see("end")

            if source in ["auto", "system"]:
                if 'auto_frame' in self.__dict__ and hasattr(self.auto_frame, 'append_log'):
                    self.auto_frame.append_log(display_text, tag)
                elif 'auto_console' in self.__dict__:
                    self.auto_console.configure(state="normal")
                    if tag:
                        self.auto_console.insert("end", display_text + "\n", tag)
                    else:
                        self.auto_console.insert("end", display_text + "\n")
                    self.auto_console.configure(state="disabled")
                    self.auto_console.see("end")

        self.after(0, update_text)

        if 'event_bus' in self.__dict__ and self.event_bus:
            self.event_bus.publish(Event.LOG, text=text, source=source)

        # Trigger Discord Webhook on Auto-Scheduler Completion
        if "🏁 Auto-Scheduler finished processing the new video!" in text:
            self.send_discord_alert("Auto-Scheduler Upload Complete")

        # Write to log files
        if 'manual_logger' in self.__dict__ and 'auto_logger' in self.__dict__:
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
        if 'sidebar_frame' in self.__dict__ and hasattr(self.sidebar_frame, 'set_active_tab'):
            self.sidebar_frame.set_active_tab("manual")
        elif 'nav_manual_btn' in self.__dict__:
            self._highlight_button(self.nav_manual_btn)

    def show_auto_frame(self):
        self._hide_all_frames()
        self.auto_frame.grid(row=0, column=1, sticky="nsew")
        if 'sidebar_frame' in self.__dict__ and hasattr(self.sidebar_frame, 'set_active_tab'):
            self.sidebar_frame.set_active_tab("auto")
        elif 'nav_auto_btn' in self.__dict__:
            self._highlight_button(self.nav_auto_btn)

    def show_prompt_frame(self):
        self._hide_all_frames()
        self.prompt_frame.grid(row=0, column=1, sticky="nsew")
        if 'sidebar_frame' in self.__dict__ and hasattr(self.sidebar_frame, 'set_active_tab'):
            self.sidebar_frame.set_active_tab("prompt")
        elif 'nav_prompt_btn' in self.__dict__:
            self._highlight_button(self.nav_prompt_btn)

    def show_settings_frame(self):
        self._hide_all_frames()
        self.settings_frame.grid(row=0, column=1, sticky="nsew")
        if 'sidebar_frame' in self.__dict__ and hasattr(self.sidebar_frame, 'set_active_tab'):
            self.sidebar_frame.set_active_tab("settings")
        elif 'nav_settings_btn' in self.__dict__:
            self._highlight_button(self.nav_settings_btn)
        self.refresh_available_models()

    def show_gallery_frame(self):
        self._hide_all_frames()
        self.gallery_frame.grid(row=0, column=1, sticky="nsew")
        if 'sidebar_frame' in self.__dict__ and hasattr(self.sidebar_frame, 'set_active_tab'):
            self.sidebar_frame.set_active_tab("gallery")
        elif 'nav_gallery_btn' in self.__dict__:
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
        active = self.config.get("prompts", {}).get("active_profile", p_names[0])
        
        if 'prompt_frame' in self.__dict__ and hasattr(self.prompt_frame, 'set_profiles'):
            self.prompt_frame.set_profiles(p_names, active)
        elif 'profile_dropdown' in self.__dict__:
            self.profile_dropdown.configure(values=p_names)
            self.profile_dropdown.set(active)

        self.on_profile_change(active)

        if 'auto_frame' in self.__dict__ and hasattr(self.auto_frame, 'set_prompt_profiles'):
            auto_active = self.config.get("auto_scheduler", {}).get("auto_prompt_profile", p_names[0])
            self.auto_frame.set_prompt_profiles(p_names, auto_active if auto_active in p_names else p_names[0])
        elif 'auto_prompt_menu' in self.__dict__:
            self.auto_prompt_menu.configure(values=p_names)
            auto_active = self.config.get("auto_scheduler", {}).get("auto_prompt_profile", p_names[0])
            self.auto_prompt_menu.set(auto_active if auto_active in p_names else p_names[0])

        if 'manual_frame' in self.__dict__ and hasattr(self.manual_frame, 'set_available_profiles'):
            self.manual_frame.set_available_profiles(p_names)

    def on_profile_change(self, choice):
        self.config["prompts"]["active_profile"] = choice
        p_text = self.config["prompts"]["profiles"].get(choice, "")
        if 'prompt_frame' in self.__dict__ and hasattr(self.prompt_frame, 'set_prompt_text'):
            self.prompt_frame.set_prompt_text(p_text)
        elif 'prompt_textbox' in self.__dict__:
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
                if 'event_bus' in self.__dict__ and self.event_bus:
                    self.event_bus.publish(Event.PROMPT_UPDATED, new_name, self.config["prompts"]["profiles"][new_name])

    def save_current_prompt(self):
        if 'prompt_frame' in self.__dict__ and hasattr(self.prompt_frame, 'get_active_profile'):
            active = self.prompt_frame.get_active_profile()
            prompt_content = self.prompt_frame.get_prompt_text()
        else:
            active = self.profile_dropdown.get()
            prompt_content = self.prompt_textbox.get("1.0", "end").strip()

        self.config["prompts"]["profiles"][active] = prompt_content
        config_manager.save_config(self.config)

        if 'prompt_frame' in self.__dict__ and hasattr(self.prompt_frame, 'show_save_feedback'):
            self.prompt_frame.show_save_feedback()
        elif hasattr(self, 'save_prompt_btn'):
            self.save_prompt_btn.configure(text="✅ Saved!", fg_color="#2ecc71")
            self.after(2000, lambda: self.save_prompt_btn.configure(text="Save Prompt", fg_color=["#3a7ebf", "#1f538d"]))

        if 'event_bus' in self.__dict__ and self.event_bus:
            self.event_bus.publish(Event.PROMPT_UPDATED, active, prompt_content)

    def delete_profile(self):
        if 'prompt_frame' in self.__dict__ and hasattr(self.prompt_frame, 'get_active_profile'):
            active = self.prompt_frame.get_active_profile()
        else:
            active = self.profile_dropdown.get()

        if len(self.config["prompts"]["profiles"]) > 1:
            if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete the profile '{active}'?"):
                del self.config["prompts"]["profiles"][active]
                config_manager.save_config(self.config)
                self.load_prompt_data()
        else:
            messagebox.showwarning("Cannot Delete", "You must have at least one prompt profile.")

    def save_settings(self):
        if 'settings_frame' in self.__dict__ and hasattr(self.settings_frame, 'get_settings'):
            new_settings = self.settings_frame.get_settings()
            for section, kvs in new_settings.items():
                if section not in self.config:
                    self.config[section] = {}
                self.config[section].update(kvs)
        else:
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

        if 'event_bus' in self.__dict__ and self.event_bus:
            self.event_bus.publish(Event.CONFIG_SAVED, self.config)

        # Provide immediate visual feedback on the button (prevent double-click bug)
        if 'settings_frame' in self.__dict__ and hasattr(self.settings_frame, 'show_saved_feedback'):
            self.settings_frame.show_saved_feedback()
        elif hasattr(self, 'save_btn'):
            if self.save_btn.cget("text") != "✅ Saved!":
                self.original_btn_color = self.save_btn.cget("fg_color")
            self.save_btn.configure(text="✅ Saved!", fg_color="#2ecc71")
            self.after(2000, lambda: self.save_btn.configure(text="Save Settings", fg_color=getattr(self, 'original_btn_color', ["#3a7ebf", "#1f538d"])))

    # --- Gallery Logic ---
    def refresh_gallery_action(self):
        self.populate_gallery()
        if 'gallery_frame' in self.__dict__ and hasattr(self.gallery_frame, 'show_refreshed_feedback'):
            self.gallery_frame.show_refreshed_feedback()
        elif hasattr(self, 'refresh_gallery_btn'):
            if self.refresh_gallery_btn.cget("text") != "✅ Refreshed!":
                self.original_refresh_btn_color = self.refresh_gallery_btn.cget("fg_color")
            self.refresh_gallery_btn.configure(text="✅ Refreshed!", fg_color="#2ecc71")
            self.after(2000, lambda: self.refresh_gallery_btn.configure(text="🔄 Refresh List", fg_color=getattr(self, 'original_refresh_btn_color', ["#3a7ebf", "#1f538d"])))

    def toggle_select_all(self):
        if 'gallery_frame' in self.__dict__ and hasattr(self.gallery_frame, 'toggle_select_all'):
            self.gallery_frame.toggle_select_all()
        else:
            select_state = self.select_all_var.get()
            if hasattr(self, 'marked_for_deletion'):
                for var in self.marked_for_deletion.values():
                    var.set(select_state)

    def populate_gallery(self):
        # Reset select all checkbox
        if 'gallery_frame' in self.__dict__ and hasattr(self.gallery_frame, 'select_all_var'):
            self.gallery_frame.select_all_var.set(False)
        elif 'select_all_var' in self.__dict__ and self.select_all_var is not None:
            self.select_all_var.set(False)

        clips_dir = self.config.get('settings', {}).get('clips_dir', '')
        if not clips_dir or not os.path.exists(clips_dir):
            if 'gallery_frame' in self.__dict__ and hasattr(self.gallery_frame, 'render_clips'):
                self.gallery_frame.render_clips([], lambda f: None)
            elif hasattr(self, 'clip_listbox'):
                for widget in self.clip_listbox.winfo_children():
                    widget.destroy()
                empty_label = ctk.CTkLabel(self.clip_listbox, text="Clip folder not set or does not exist.", font=ctk.CTkFont(slant="italic"), text_color="gray")
                empty_label.pack(pady=20)
            return

        # Ensure caches and scan ID exist (even if __init__ was bypassed)
        if 'gallery_meta_cache' not in self.__dict__:
            self.gallery_meta_cache = GalleryMetadataCache()
        if 'thumbnail_cache' not in self.__dict__:
            self.thumbnail_cache = ThumbnailCache(maxsize=64)
        if '_gallery_scan_id' not in self.__dict__:
            self._gallery_scan_id = 0

        self._gallery_scan_id += 1
        scan_id = self._gallery_scan_id

        if 'gallery_frame' in self.__dict__ and hasattr(self.gallery_frame, 'get_filter_settings'):
            filters = self.gallery_frame.get_filter_settings()
            sort_mode = filters["sort_mode"]
            type_filter = filters["type_filter"]
            score_filter = filters["score_filter"]
        else:
            sort_mode = self.sort_menu.get() if 'sort_menu' in self.__dict__ else "Date (Newest)"
            type_filter = self.type_filter_menu.get() if 'type_filter_menu' in self.__dict__ else "All"
            score_filter = self.score_filter_menu.get() if 'score_filter_menu' in self.__dict__ else "All"

        if hasattr(self, 'clip_listbox') and not self.clip_listbox.winfo_children():
            loading_label = ctk.CTkLabel(self.clip_listbox, text="Loading clips...", font=ctk.CTkFont(slant="italic"), text_color="gray")
            loading_label.pack(pady=20)

        threading.Thread(
            target=self._scan_gallery_worker,
            args=(scan_id, clips_dir, sort_mode, type_filter, score_filter),
            daemon=True
        ).start()

    def _scan_gallery_worker(self, scan_id, clips_dir, sort_mode, type_filter, score_filter):
        clip_data = scan_and_filter_clips(
            clips_dir=clips_dir,
            sort_mode=sort_mode,
            type_filter=type_filter,
            score_filter=score_filter,
            meta_cache=self.gallery_meta_cache
        )

        if scan_id != getattr(self, '_gallery_scan_id', 0):
            return

        self.after(0, self._render_gallery_items, scan_id, clip_data, clips_dir)

    def _render_gallery_items(self, scan_id, clip_data, clips_dir):
        if scan_id != getattr(self, '_gallery_scan_id', 0):
            return

        if 'gallery_frame' in self.__dict__ and hasattr(self.gallery_frame, 'render_clips'):
            self.gallery_frame.render_clips(clip_data, lambda f: self.load_clip_details(f, clips_dir))
            self.marked_for_deletion = self.gallery_frame.marked_for_deletion
        else:
            for widget in self.clip_listbox.winfo_children():
                widget.destroy()

            self.marked_for_deletion = {}

            if not clip_data:
                empty_label = ctk.CTkLabel(self.clip_listbox, text="No clips found matching current filters.", font=ctk.CTkFont(slant="italic"), text_color="gray")
                empty_label.pack(pady=20)
                return

            for item in clip_data:
                file = item["filename"]
                row_frame = ctk.CTkFrame(self.clip_listbox, fg_color="transparent")
                row_frame.pack(fill="x", pady=2, padx=5)

                self.marked_for_deletion[file] = ctk.BooleanVar(value=False)
                checkbox = ctk.CTkCheckBox(row_frame, text="", variable=self.marked_for_deletion[file], width=20)
                checkbox.pack(side="left", padx=(0, 5))

                btn = ctk.CTkButton(
                    row_frame,
                    text=file,
                    fg_color="#2b2b2b",
                    hover_color="#3b3b3b",
                    anchor="w",
                    command=lambda f=file: self.load_clip_details(f, clips_dir)
                )
                btn.pack(side="left", fill="x", expand=True)

    def confirm_delete_marked(self):
        if 'gallery_frame' in self.__dict__ and hasattr(self.gallery_frame, 'get_marked_files'):
            files_to_delete = self.gallery_frame.get_marked_files()
        else:
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
                
                # Invalidate from caches
                if 'gallery_meta_cache' in self.__dict__:
                    self.gallery_meta_cache.invalidate(json_path)
                if 'thumbnail_cache' in self.__dict__:
                    self.thumbnail_cache.evict(jpg_path)

                for p in [mp4_path, json_path, jpg_path]:
                    if os.path.exists(p):
                        try:
                            os.remove(p)
                        except Exception as e:
                            self.log_to_console(f"❌ Failed to delete {p}: {e}", source="system")
            
            self.populate_gallery()
            if 'gallery_frame' in self.__dict__ and hasattr(self.gallery_frame, 'clear_clip_details'):
                self.gallery_frame.clear_clip_details()
            elif hasattr(self, 'detail_title'):
                self.detail_title.configure(text="Select a clip to view details")
                self.detail_score.configure(text="Score: --/10")
                self.detail_reasoning.configure(state="normal")
                self.detail_reasoning.delete("1.0", "end")
                self.detail_reasoning.configure(state="disabled")
                self.detail_thumbnail.configure(image=None) # type: ignore
                self.play_clip_btn.configure(state="disabled")
                self.open_folder_btn.configure(state="disabled")

            if 'event_bus' in self.__dict__ and self.event_bus:
                self.event_bus.publish(Event.CLIPS_UPDATED)

    def load_clip_details(self, filename, directory):
        mp4_path = os.path.join(directory, filename)
        base_json_name = filename.replace("_vertical.mp4", ".mp4").replace(".mp4", ".json")
        json_path = os.path.join(directory, base_json_name)

        if 'gallery_meta_cache' not in self.__dict__:
            self.gallery_meta_cache = GalleryMetadataCache()
        if 'thumbnail_cache' not in self.__dict__:
            self.thumbnail_cache = ThumbnailCache(maxsize=64)

        data = self.gallery_meta_cache.get_metadata(json_path)
        if data and isinstance(data, dict):
            score = data.get("virality_score", "N/A")
            reasoning = data.get("reasoning", "No reasoning provided by AI.")
            score_text = f"Virality Score: {score}/10"
        else:
            score_text = "Score: N/A"
            reasoning = "No AI metadata found for this clip (might be an older generation)."

        # Load large thumbnail using LRU cache
        thumb_name = filename.replace("_vertical.mp4", ".mp4").replace(".mp4", ".jpg")
        thumb_path = os.path.join(directory, thumb_name)

        def _load_image(path):
            try:
                pil_img = Image.open(path)
                width, height = pil_img.size
                ratio = min(600 / width, 300 / height)
                new_w, new_h = max(1, int(width * ratio)), max(1, int(height * ratio))
                return ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(new_w, new_h))
            except Exception:
                return None

        large_clip_img = self.thumbnail_cache.get_thumbnail(thumb_path, _load_image)

        play_cmd = (lambda: os.startfile(mp4_path)) if hasattr(os, 'startfile') else None
        open_cmd = (lambda: subprocess.run(['explorer', '/select,', os.path.abspath(mp4_path)])) if hasattr(os, 'startfile') else None

        # Resolve companion video (16:9 Landscape vs 9:16 Vertical)
        if "_vertical.mp4" in filename:
            companion_filename = filename.replace("_vertical.mp4", ".mp4")
        else:
            companion_filename = filename.replace(".mp4", "_vertical.mp4")
        companion_path = os.path.join(directory, companion_filename)
        if not os.path.exists(companion_path):
            companion_path = None

        if 'gallery_frame' in self.__dict__ and hasattr(self.gallery_frame, 'display_clip_details'):
            self.gallery_frame.display_clip_details(
                filename=filename,
                score_text=score_text,
                reasoning=reasoning,
                thumbnail_image=large_clip_img,
                on_play=play_cmd,
                on_open_folder=open_cmd,
                video_path=mp4_path,
                companion_path=companion_path
            )
        elif hasattr(self, 'detail_title'):
            self.detail_title.configure(text=filename)
            self.detail_reasoning.configure(state="normal")
            self.detail_reasoning.delete("1.0", "end")
            self.detail_score.configure(text=score_text)
            self.detail_reasoning.insert("1.0", reasoning)
            self.detail_reasoning.configure(state="disabled")
            self.detail_thumbnail.configure(image=large_clip_img)
            if play_cmd:
                self.play_clip_btn.configure(state="normal", command=play_cmd)
            if open_cmd:
                self.open_folder_btn.configure(state="normal", command=open_cmd)

    # --- Direct Social Media Publishing ---
    def open_publish_dialog(
        self,
        video_path: Optional[str] = None,
        companion_path: Optional[str] = None,
        filename: Optional[str] = None,
        reasoning: Optional[str] = None
    ) -> None:
        """Opens the Social Media Direct Publishing modal dialog."""
        from gui import PublishDialog
        if not video_path:
            messagebox.showinfo("Publish Clip", "Please select a clip from the gallery first.")
            return

        clip_info = {
            "video_path": video_path,
            "companion_path": companion_path,
            "filename": filename or os.path.basename(video_path),
            "reasoning": reasoning or ""
        }
        curr_cfg = self.config if hasattr(self, 'config') else {}
        PublishDialog(
            master=self,
            clip_info=clip_info,
            config=curr_cfg,
            on_publish_complete=self._on_social_publish_completed
        )

    def _on_social_publish_completed(self, platform: str, url: str) -> None:
        """Callback invoked when a clip is successfully published to social media."""
        self.log_to_console(f"🎉 Successfully published clip to {platform}!\n🔗 URL: {url}")

    def _on_social_published(self, **kwargs) -> None:
        """Event subscriber invoked whenever a social upload completes."""
        platform = kwargs.get("platform", "Social Media")
        url = kwargs.get("url", "")
        title = kwargs.get("title", "")
        self.log_to_console(f"🚀 Published to {platform}: {title} ({url})")
        self.send_discord_alert(f"Published to {platform}: {title}\n{url}")

    # --- Queue Manager Integration ---
    def _on_queue_updated(self, items, summary):
        if 'manual_frame' in self.__dict__ and hasattr(self.manual_frame, 'render_queue'):
            self.after(0, lambda: self.manual_frame.render_queue(items, summary))

    def add_manual_input_to_queue(self, input_val=None):
        if input_val is None:
            if 'manual_frame' in self.__dict__ and hasattr(self.manual_frame, 'get_url'):
                input_val = self.manual_frame.get_url()
            elif hasattr(self, 'url_input'):
                input_val = self.url_input.get().strip()
            else:
                input_val = ""

        input_val = (input_val or "").strip()
        if not input_val:
            return

        sources = [s.strip() for s in input_val.split(";") if s.strip()]
        if not sources:
            return

        active_profile = self.config.get("prompts", {}).get("active_profile", "Omni-Genre Broad Net")
        if hasattr(self, 'queue_manager'):
            added = self.queue_manager.add_items(sources, prompt_profile=active_profile)
            self.log_to_console(f"➕ Added {len(added)} item(s) to processing queue.", source="manual")
        
        if 'manual_frame' in self.__dict__ and hasattr(self.manual_frame, 'set_url'):
            self.manual_frame.set_url("")
        elif hasattr(self, 'url_input'):
            self.url_input.delete(0, "end")

    def remove_queue_item(self, item_id):
        if hasattr(self, 'queue_manager'):
            self.queue_manager.remove_item(item_id)

    def clear_completed_queue(self):
        if hasattr(self, 'queue_manager'):
            removed = self.queue_manager.clear_completed()
            if removed > 0:
                self.log_to_console(f"🧹 Cleared {removed} completed/cancelled item(s) from queue.", source="manual")

    def clear_all_queue(self):
        if hasattr(self, 'queue_manager'):
            self.queue_manager.clear_all()
            self.log_to_console("🧹 Cleared all queue items.", source="manual")

    def on_queue_item_profile_changed(self, item_id, new_profile):
        if hasattr(self, 'queue_manager'):
            self.queue_manager.update_item_profile(item_id, new_profile)

    def on_queue_item_orientation_changed(self, item_id, new_orientation):
        if hasattr(self, 'queue_manager'):
            self.queue_manager.update_item_orientation(item_id, new_orientation)

    def on_files_dropped(self, files):
        if not files:
            return
        active_profile = self.config.get("prompts", {}).get("active_profile", "Omni-Genre Broad Net")
        if hasattr(self, 'queue_manager'):
            added = self.queue_manager.add_items(files, prompt_profile=active_profile)
            self.log_to_console(f"📥 Dropped {len(added)} video file(s) into queue.", source="manual")

    # --- Processing Engine ---
    def browse_local_file(self):
        file_paths = filedialog.askopenfilenames(
            title="Select Local Video File(s)",
            filetypes=[("Video Files", "*.mp4 *.mkv *.avi *.mov *.flv")]
        )
        if file_paths:
            combined = ";".join(file_paths)
            if 'manual_frame' in self.__dict__ and hasattr(self.manual_frame, 'set_url'):
                self.manual_frame.set_url(combined)
            elif hasattr(self, 'url_input'):
                self.url_input.delete(0, "end")
                self.url_input.insert(0, combined)

            if hasattr(self, 'queue_manager'):
                active_profile = self.config.get("prompts", {}).get("active_profile", "Omni-Genre Broad Net")
                self.queue_manager.add_items(list(file_paths), prompt_profile=active_profile)

    def cancel_manual_process(self):
        self.cancel_requested = True
        if hasattr(self, 'queue_manager'):
            self.queue_manager.cancel()

        if 'manual_frame' in self.__dict__ and hasattr(self.manual_frame, 'cancel_btn'):
            self.manual_frame.cancel_btn.configure(state="disabled", text="Cancelling...")
        elif hasattr(self, 'cancel_btn'):
            self.cancel_btn.configure(state="disabled", text="Cancelling...")

        self.log_to_console("🛑 Cancellation requested. Aborting as soon as possible...", source="manual")
        utils.cleanup_all_processes()

    def start_manual_process(self, event=None):
        # If queue is empty, check if user pasted a URL directly in input
        if hasattr(self, 'queue_manager') and not self.queue_manager.get_pending_items():
            input_val = self.manual_frame.get_url() if ('manual_frame' in self.__dict__ and hasattr(self.manual_frame, 'get_url')) else (self.url_input.get().strip() if hasattr(self, 'url_input') else "")
            if input_val:
                self.add_manual_input_to_queue(input_val)

        has_pending = hasattr(self, 'queue_manager') and bool(self.queue_manager.get_pending_items())

        if not has_pending:
            self.log_to_console("⚠️ Queue is empty. Add a video URL or drop files to begin.", source="manual")
            return

        self.cancel_requested = False
        if hasattr(self, 'queue_manager'):
            self.queue_manager.reset_cancel()

        if 'manual_frame' in self.__dict__ and hasattr(self.manual_frame, 'set_processing_state'):
            self.manual_frame.set_processing_state(True, "Status: Processing Queue...")
            self.manual_frame.clear_log()
        else:
            if hasattr(self, 'process_btn'):
                self.process_btn.configure(state="disabled", text="Processing...")
            if hasattr(self, 'local_file_btn'):
                self.local_file_btn.configure(state="disabled")
            if hasattr(self, 'cancel_btn'):
                self.cancel_btn.configure(state="normal", text="Cancel")
            if hasattr(self, 'manual_progress'):
                self.manual_progress.start()
            if hasattr(self, 'console_box'):
                self.console_box.configure(state="normal")
                self.console_box.delete("1.0", "end")
                self.console_box.configure(state="disabled")

        threading.Thread(target=self._process_video_thread, daemon=True).start()

    def _process_video_thread(self, input_val=None):
        try:
            if input_val and hasattr(self, 'queue_manager') and not self.queue_manager.get_pending_items():
                self.add_manual_input_to_queue(input_val)

            if hasattr(self, 'queue_manager'):
                count = self.queue_manager.process_queue(
                    process_video_fn=lambda path, **kw: editor.process_video(path, **kw),
                    download_fn=lambda url, vid, **kw: watcher.download_with_subprocess(url, vid, **kw),
                    get_video_id_fn=self.get_video_id,
                    logger=lambda msg: self.log_to_console(msg, source="manual"),
                    on_item_complete=lambda it: self.after(0, self.populate_gallery)
                )

                if self.queue_manager.cancel_requested:
                    self.log_to_console("🛑 Process aborted by user.", source="manual")
                else:
                    self.log_to_console(f"🏁 ALL TASKS COMPLETE! ({count} video(s) processed)", source="manual")
                    self.send_discord_alert("Manual Queue Finished")
                    if hasattr(self, 'process_btn'):
                        self.after(0, lambda: self.process_btn.configure(text="✅ Complete!", fg_color="#27ae60"))
                        self.after(3000, lambda: self.process_btn.configure(text="▶ Process Queue", fg_color=["#3a7ebf", "#1f538d"]))
            else:
                self.log_to_console("❌ QueueManager not initialized.", source="manual")
        except Exception as e:
            self.log_to_console(f"❌ Error: {e}", source="manual")
        finally:
            def reset_ui():
                if 'manual_frame' in self.__dict__ and hasattr(self.manual_frame, 'set_processing_state'):
                    self.manual_frame.set_processing_state(False)
                else:
                    if hasattr(self, 'process_btn'):
                        self.process_btn.configure(state="normal")
                    if hasattr(self, 'local_file_btn'):
                        self.local_file_btn.configure(state="normal")
                    if hasattr(self, 'cancel_btn'):
                        self.cancel_btn.configure(state="disabled", text="Cancel")
                    if hasattr(self, 'manual_progress'):
                        self.manual_progress.stop()
                    if hasattr(self, 'manual_status_label'):
                        self.manual_status_label.configure(text="Status: Ready")
                self.populate_gallery()
            self.after(0, reset_ui)

    def toggle_auto(self):
        is_enabled = False
        if 'auto_frame' in self.__dict__ and hasattr(self.auto_frame, 'is_auto_enabled'):
            is_enabled = self.auto_frame.is_auto_enabled()
        elif hasattr(self, 'auto_switch'):
            is_enabled = self.auto_switch.get() == 1

        if is_enabled:
            if "auto_scheduler" not in self.config:
                self.config["auto_scheduler"] = {}

            if 'auto_frame' in self.__dict__ and hasattr(self.auto_frame, 'get_scheduler_settings'):
                sched = self.auto_frame.get_scheduler_settings()
                self.config["auto_scheduler"].update(sched)
            else:
                if hasattr(self, 'platform_menu'): self.config["auto_scheduler"]["platform"] = self.platform_menu.get()
                if hasattr(self, 'type_menu'): self.config["auto_scheduler"]["video_type"] = self.type_menu.get()
                if hasattr(self, 'target_menu'): self.config["auto_scheduler"]["target_orientation"] = self.target_menu.get()
                if hasattr(self, 'lookback_menu'): self.config["auto_scheduler"]["lookback_days"] = self.lookback_menu.get()
                if hasattr(self, 'interval_menu'): self.config["auto_scheduler"]["check_interval"] = self.interval_menu.get()
                if hasattr(self, 'auto_prompt_menu'): self.config["auto_scheduler"]["auto_prompt_profile"] = self.auto_prompt_menu.get()
            config_manager.save_config(self.config)

            self.is_auto_running = True
            if 'auto_frame' in self.__dict__ and hasattr(self.auto_frame, 'set_status'):
                self.auto_frame.set_status(True)
            elif hasattr(self, 'auto_status'):
                self.auto_status.configure(text="● Status: RUNNING", text_color="#2ecc71")
                self.auto_progress.start()
            self.log_to_console("📡 Auto-Scheduler enabled. Saving config and monitoring channels...", source="auto")
            threading.Thread(target=self._auto_run_loop, daemon=True).start()
        else:
            self.is_auto_running = False
            if 'auto_frame' in self.__dict__ and hasattr(self.auto_frame, 'set_status'):
                self.auto_frame.set_status(False)
            elif hasattr(self, 'auto_status'):
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

    def quit_window(self, icon=None, item=None):
        if self.tray_icon: 
            try:
                self.tray_icon.stop() # type: ignore
            except Exception:
                pass
        self.is_auto_running = False  
        self.cancel_requested = True
        utils.cleanup_all_processes()
        self.after(0, self.destroy)   

if __name__ == "__main__":
    print("==================================================")
    print("  Starting jBahr's Clip Generator...")
    print("  Loading GUI libraries & initializing window...")
    print("==================================================")
    try:
        app = ClipGenApp()
        app.deiconify()
        app.lift()
        app.attributes('-topmost', True)
        app.after(500, lambda: app.attributes('-topmost', False))
        app.focus_force()
        print("[ClipGen] Application window opened successfully.")
        print("[ClipGen] (Keep this console open or close the app window when done)")
        app.mainloop()
    except Exception as e:
        import traceback
        err_msg = traceback.format_exc()
        try:
            with open("startup_error.log", "w", encoding="utf-8") as f:
                f.write(err_msg)
        except Exception:
            pass
        print(f"FATAL STARTUP ERROR:\n{err_msg}", file=sys.stderr)
        try:
            from tkinter import messagebox
            messagebox.showerror("Clip Generator Startup Error", f"Fatal error starting application:\n\n{err_msg}")
        except Exception:
            pass