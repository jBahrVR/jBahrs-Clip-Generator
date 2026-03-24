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

        self._setup_sidebar()
        self._setup_manual_frame()
        self._setup_auto_frame()
        self._setup_prompt_frame()
        self._setup_settings_frame()
        self._setup_gallery_frame()

        self.load_prompt_data()
        self.show_manual_frame()

    def _setup_sidebar(self):
        # ==================== SIDEBAR ====================
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color="#1e1e1e")
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(12, weight=1) 

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="jBahr's Clip\nGenerator", font=ctk.CTkFont(size=24, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(30, 20))

        self.nav_manual_btn = ctk.CTkButton(self.sidebar_frame, text="🎬 Manual Clipper", fg_color="transparent", border_width=1, command=self.show_manual_frame)
        self.nav_manual_btn.grid(row=1, column=0, padx=20, pady=10, sticky="ew")

        self.nav_auto_btn = ctk.CTkButton(self.sidebar_frame, text="⏳ Auto Scheduler", fg_color="transparent", border_width=1, command=self.show_auto_frame)
        self.nav_auto_btn.grid(row=2, column=0, padx=20, pady=10, sticky="ew")

        self.nav_prompt_btn = ctk.CTkButton(self.sidebar_frame, text="📝 Prompt Manager", fg_color="transparent", border_width=1, command=self.show_prompt_frame)
        self.nav_prompt_btn.grid(row=3, column=0, padx=20, pady=10, sticky="ew")

        self.nav_settings_btn = ctk.CTkButton(self.sidebar_frame, text="⚙️ Settings", fg_color="transparent", border_width=1, command=self.show_settings_frame)
        self.nav_settings_btn.grid(row=4, column=0, padx=20, pady=10, sticky="ew")

        self.nav_gallery_btn = ctk.CTkButton(self.sidebar_frame, text="🖼️ Clip Gallery", fg_color="transparent", border_width=1, command=self.show_gallery_frame)
        self.nav_gallery_btn.grid(row=5, column=0, padx=20, pady=10, sticky="ew")

        self.github_btn = ctk.CTkButton(self.sidebar_frame, text="🌐 GitHub Repo", fg_color="#24292e", hover_color="#2f363d", command=lambda: webbrowser.open("https://github.com/jBahrVR/jBahrs-Clip-Generator"))
        self.github_btn.grid(row=6, column=0, padx=20, pady=(10, 0), sticky="ew")

        self.quick_access_label = ctk.CTkLabel(self.sidebar_frame, text="Quick Access", font=ctk.CTkFont(size=12, weight="bold"), text_color="gray")
        self.quick_access_label.grid(row=7, column=0, padx=20, pady=(20, 0), sticky="w")

        self.open_vods_btn = ctk.CTkButton(self.sidebar_frame, text="📁 Raw VODs", fg_color="#2b2b2b", hover_color="#3b3b3b", command=lambda: self.open_local_folder("download_dir"))
        self.open_vods_btn.grid(row=8, column=0, padx=20, pady=(5, 5), sticky="ew")

        self.open_clips_btn = ctk.CTkButton(self.sidebar_frame, text="✂️ Generated Clips", fg_color="#2b2b2b", hover_color="#3b3b3b", command=lambda: self.open_local_folder("clips_dir"))
        self.open_clips_btn.grid(row=9, column=0, padx=20, pady=(5, 5), sticky="ew")

        self.open_logs_btn = ctk.CTkButton(self.sidebar_frame, text="📝 View Crash Logs", fg_color="#2b2b2b", hover_color="#3b3b3b", command=self.open_logs)
        self.open_logs_btn.grid(row=10, column=0, padx=20, pady=(5, 5), sticky="ew")

        self.open_readme_btn = ctk.CTkButton(self.sidebar_frame, text="📖 View Readme", fg_color="#2b2b2b", hover_color="#3b3b3b", command=self.open_readme)
        self.open_readme_btn.grid(row=11, column=0, padx=20, pady=(5, 20), sticky="ew")

        self.discord_btn = ctk.CTkButton(self.sidebar_frame, text="💬 Join Discord", fg_color="#5865F2", hover_color="#4752C4", command=lambda: webbrowser.open("https://discord.gg/uUF8J9Zqwz"))
        self.discord_btn.grid(row=12, column=0, padx=20, pady=(5, 5), sticky="ew")

        self.version_label = ctk.CTkLabel(self.sidebar_frame, text="v1.2.1 Creator Edition", font=ctk.CTkFont(size=10), text_color="gray")
        self.version_label.grid(row=13, column=0, padx=20, pady=10, sticky="s")

    def _setup_manual_frame(self):
        # ==================== MANUAL FRAME ====================
        self.manual_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.manual_frame.grid_columnconfigure(0, weight=1)
        self.manual_frame.grid_rowconfigure(4, weight=1)
        
        self.manual_title = ctk.CTkLabel(self.manual_frame, text="Manual Video Processor", font=ctk.CTkFont(size=28, weight="bold"))
        self.manual_title.grid(row=0, column=0, padx=30, pady=(30, 10), sticky="w")
        
        self.input_card = ctk.CTkFrame(self.manual_frame, corner_radius=15)
        self.input_card.grid(row=1, column=0, padx=30, pady=10, sticky="ew")
        self.input_card.grid_columnconfigure(0, weight=1)

        self.url_input = ctk.CTkEntry(self.input_card, placeholder_text="Paste URL or Select Local File(s)...", height=45, border_width=0)
        self.url_input.grid(row=0, column=0, padx=20, pady=20, sticky="ew")
        self.url_input.bind("<Return>", self.start_manual_process)
        
        self.process_btn = ctk.CTkButton(self.input_card, text="Process Queue", height=45, text_color="#FFFFFF", font=ctk.CTkFont(weight="bold"), command=self.start_manual_process)
        self.process_btn.grid(row=0, column=1, padx=(0, 10), pady=20)

        self.cancel_btn = ctk.CTkButton(self.input_card, text="Cancel", height=45, text_color="#FFFFFF", fg_color="#c0392b", hover_color="#922b21", font=ctk.CTkFont(weight="bold"), state="disabled", command=self.cancel_manual_process)
        self.cancel_btn.grid(row=0, column=2, padx=(0, 10), pady=20)

        self.local_file_btn = ctk.CTkButton(self.input_card, text="📂 Browse Files", height=45, text_color="#FFFFFF", fg_color="#27ae60", hover_color="#1e8449", font=ctk.CTkFont(weight="bold"), command=self.browse_local_file)
        self.local_file_btn.grid(row=0, column=3, padx=(0, 20), pady=20)
        
        self.manual_status_label = ctk.CTkLabel(self.manual_frame, text="Status: Ready", font=ctk.CTkFont(size=14, weight="bold"), text_color="#a0a0a0")
        self.manual_status_label.grid(row=2, column=0, padx=30, pady=(10, 0), sticky="w")
        
        self.manual_progress = ctk.CTkProgressBar(self.manual_frame, mode="indeterminate", height=10)
        self.manual_progress.grid(row=3, column=0, padx=30, pady=(5, 5), sticky="ew")
        self.manual_progress.set(0)

        self.cancel_requested = False

        self.console_card = ctk.CTkFrame(self.manual_frame, corner_radius=15)
        self.console_card.grid(row=4, column=0, padx=30, pady=(5, 10), sticky="nsew")
        self.console_card.grid_columnconfigure(0, weight=1)
        self.console_card.grid_rowconfigure(0, weight=1)

        self.console_box = ctk.CTkTextbox(self.console_card, state="disabled", fg_color="#121212", font=ctk.CTkFont(family="Consolas", size=13))
        self.console_box.grid(row=0, column=0, padx=15, pady=15, sticky="nsew")
        
        self.console_box.tag_config("error", foreground="#ff4d4d")
        self.console_box.tag_config("success", foreground="#2ecc71")
        self.console_box.tag_config("ai", foreground="#00d2ff")
        self.console_box.tag_config("ffmpeg", foreground="#f39c12")

    def _setup_auto_frame(self):
        # ==================== AUTO FRAME ====================
        self.auto_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.auto_frame.grid_columnconfigure(0, weight=1)
        self.auto_frame.grid_rowconfigure(3, weight=1)

        self.auto_title = ctk.CTkLabel(self.auto_frame, text="Automated Background Watcher", font=ctk.CTkFont(size=28, weight="bold"))
        self.auto_title.grid(row=0, column=0, padx=30, pady=(30, 10), sticky="w")

        self.auto_controls_card = ctk.CTkFrame(self.auto_frame, corner_radius=15)
        self.auto_controls_card.grid(row=1, column=0, padx=30, pady=10, sticky="ew")
        
        ctk.CTkLabel(self.auto_controls_card, text="Platform:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=10, pady=(20,10))
        self.platform_menu = ctk.CTkOptionMenu(self.auto_controls_card, values=["YouTube", "Twitch"], width=110)
        self.platform_menu.grid(row=0, column=1, padx=5, pady=(20,10))
        self.platform_menu.set(self.config.get("auto_scheduler", {}).get("platform", "YouTube"))

        ctk.CTkLabel(self.auto_controls_card, text="Type:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=2, padx=10, pady=(20,10))
        self.type_menu = ctk.CTkOptionMenu(self.auto_controls_card, values=["Livestreams Only", "Any Upload"], width=130)
        self.type_menu.grid(row=0, column=3, padx=5, pady=(20,10))
        self.type_menu.set(self.config.get("auto_scheduler", {}).get("video_type", "Livestreams Only"))

        ctk.CTkLabel(self.auto_controls_card, text="Orientation:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=4, padx=10, pady=(20,10))
        self.target_menu = ctk.CTkOptionMenu(self.auto_controls_card, values=["Vertical Only", "Horizontal Only", "Any"], width=130)
        self.target_menu.grid(row=0, column=5, padx=5, pady=(20,10))
        self.target_menu.set(self.config.get("auto_scheduler", {}).get("target_orientation", "Horizontal Only"))

        ctk.CTkLabel(self.auto_controls_card, text="Max Age:", font=ctk.CTkFont(weight="bold")).grid(row=1, column=0, padx=10, pady=(10,10))
        self.lookback_menu = ctk.CTkOptionMenu(self.auto_controls_card, values=["1 Day", "3 Days", "7 Days", "14 Days", "30 Days", "All Time"], width=110)
        self.lookback_menu.grid(row=1, column=1, padx=5, pady=(10,10))
        self.lookback_menu.set(self.config.get("auto_scheduler", {}).get("lookback_days", "7 Days"))

        ctk.CTkLabel(self.auto_controls_card, text="Interval:", font=ctk.CTkFont(weight="bold")).grid(row=1, column=2, padx=10, pady=(10,10))
        self.interval_menu = ctk.CTkOptionMenu(self.auto_controls_card, values=["Every 1 Hour", "Every 4 Hours", "Every 12 Hours", "Every 24 Hours"], width=130)
        self.interval_menu.grid(row=1, column=3, padx=5, pady=(10,10))
        self.interval_menu.set(self.config.get("auto_scheduler", {}).get("check_interval", "Every 4 Hours"))

        ctk.CTkLabel(self.auto_controls_card, text="Auto-Prompt:", font=ctk.CTkFont(weight="bold")).grid(row=1, column=4, padx=10, pady=(10,10))
        self.auto_prompt_menu = ctk.CTkOptionMenu(self.auto_controls_card, width=130)
        self.auto_prompt_menu.grid(row=1, column=5, padx=5, pady=(10,10))

        self.auto_switch = ctk.CTkSwitch(self.auto_controls_card, text="Enable Watcher", font=ctk.CTkFont(weight="bold"), command=self.toggle_auto)
        self.auto_switch.grid(row=2, column=4, columnspan=2, padx=20, pady=(10,20), sticky="e")

        self.auto_progress = ctk.CTkProgressBar(self.auto_frame, mode="indeterminate", height=10)
        self.auto_progress.grid(row=2, column=0, padx=30, pady=(5, 5), sticky="ew")
        self.auto_progress.set(0)

        self.auto_console_card = ctk.CTkFrame(self.auto_frame, corner_radius=15)
        self.auto_console_card.grid(row=3, column=0, padx=30, pady=(5, 10), sticky="nsew")
        self.auto_console_card.grid_columnconfigure(0, weight=1)
        self.auto_console_card.grid_rowconfigure(1, weight=1)

        self.auto_status = ctk.CTkLabel(self.auto_console_card, text="● Status: OFF", text_color="gray", font=ctk.CTkFont(weight="bold"))
        self.auto_status.grid(row=0, column=0, padx=20, pady=(15, 0), sticky="w")

        self.auto_console = ctk.CTkTextbox(self.auto_console_card, state="disabled", fg_color="#121212", font=ctk.CTkFont(family="Consolas", size=13))
        self.auto_console.grid(row=1, column=0, padx=15, pady=15, sticky="nsew")
        
        self.auto_console.tag_config("error", foreground="#ff4d4d")
        self.auto_console.tag_config("success", foreground="#2ecc71")
        self.auto_console.tag_config("ai", foreground="#00d2ff")
        self.auto_console.tag_config("ffmpeg", foreground="#f39c12")

    def _setup_prompt_frame(self):
        # ==================== PROMPT MANAGER FRAME ====================
        self.prompt_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.prompt_frame.grid_columnconfigure(0, weight=1)
        self.prompt_frame.grid_rowconfigure(2, weight=1)
        
        self.prompt_title = ctk.CTkLabel(self.prompt_frame, text="AI Prompt Editor", font=ctk.CTkFont(size=28, weight="bold"))
        self.prompt_title.grid(row=0, column=0, padx=30, pady=(30, 10), sticky="w")

        self.prompt_select_card = ctk.CTkFrame(self.prompt_frame, corner_radius=15)
        self.prompt_select_card.grid(row=1, column=0, padx=30, pady=10, sticky="ew")
        
        ctk.CTkLabel(self.prompt_select_card, text="Active Manual Profile:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=20, pady=20)
        self.profile_dropdown = ctk.CTkOptionMenu(self.prompt_select_card, command=self.on_profile_change)
        self.profile_dropdown.pack(side="left", padx=10)

        self.new_profile_btn = ctk.CTkButton(self.prompt_select_card, text="➕ New", width=60, fg_color="#27ae60", hover_color="#1e8449", command=self.create_new_profile)
        self.new_profile_btn.pack(side="left", padx=5)

        self.delete_profile_btn = ctk.CTkButton(self.prompt_select_card, text="Delete Profile", fg_color="#c0392b", hover_color="#922b21", command=self.delete_profile)
        self.delete_profile_btn.pack(side="right", padx=20)

        self.prompt_editor_card = ctk.CTkFrame(self.prompt_frame, corner_radius=15)
        self.prompt_editor_card.grid(row=2, column=0, padx=30, pady=10, sticky="nsew")
        self.prompt_editor_card.grid_columnconfigure(0, weight=1)
        self.prompt_editor_card.grid_rowconfigure(0, weight=1)

        self.prompt_textbox = ctk.CTkTextbox(self.prompt_editor_card, font=ctk.CTkFont(size=14), wrap="word")
        self.prompt_textbox.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")

        self.save_prompt_btn = ctk.CTkButton(self.prompt_editor_card, text="Save Current Prompt", height=40, font=ctk.CTkFont(weight="bold"), command=self.save_current_prompt)
        self.save_prompt_btn.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="e")

    def _setup_settings_frame(self):
        # ==================== SETTINGS FRAME ====================
        self.settings_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.settings_frame.grid_columnconfigure(0, weight=1)
        
        self.settings_title = ctk.CTkLabel(self.settings_frame, text="Configuration", font=ctk.CTkFont(size=28, weight="bold"))
        self.settings_title.grid(row=0, column=0, padx=30, pady=(20, 10), sticky="w")

        # --- Card 1: APIs & Models ---
        self.api_card = ctk.CTkFrame(self.settings_frame, corner_radius=15)
        self.api_card.grid(row=1, column=0, padx=30, pady=(5, 10), sticky="ew")
        self.api_card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self.api_card, text="Authentication & AI Models", font=ctk.CTkFont(weight="bold", size=16), text_color="#a0a0a0").grid(row=0, column=0, columnspan=3, padx=20, pady=(15, 10), sticky="w")

        ctk.CTkLabel(self.api_card, text="YouTube Channel ID:", font=ctk.CTkFont(weight="bold")).grid(row=1, column=0, padx=20, pady=5, sticky="e")
        self.yt_id_entry = ctk.CTkEntry(self.api_card, height=35, placeholder_text="e.g. UC_x5XG1OV2P6uZZ5FSM9Ttw")
        self.yt_id_entry.grid(row=1, column=1, columnspan=2, padx=(0, 20), pady=5, sticky="ew")
        self.yt_id_entry.insert(0, self.config.get('youtube', {}).get('channel_id', ''))

        ctk.CTkLabel(self.api_card, text="Twitch Username:", font=ctk.CTkFont(weight="bold")).grid(row=2, column=0, padx=20, pady=5, sticky="e")
        self.twitch_entry = ctk.CTkEntry(self.api_card, height=35, placeholder_text="e.g. ninja")
        self.twitch_entry.grid(row=2, column=1, columnspan=2, padx=(0, 20), pady=5, sticky="ew")
        self.twitch_entry.insert(0, self.config.get('twitch', {}).get('username', ''))

        self.api_link_label = ctk.CTkLabel(self.api_card, text="OpenAI API Key (Get Here):", font=ctk.CTkFont(weight="bold", underline=True), text_color="#3a7ebf", cursor="hand2")
        self.api_link_label.grid(row=3, column=0, padx=20, pady=5, sticky="e")
        self.api_link_label.bind("<Button-1>", lambda e: webbrowser.open("https://platform.openai.com/api-keys"))
        self.openai_entry = ctk.CTkEntry(self.api_card, show="•", height=35, placeholder_text="sk-proj-...")
        self.openai_entry.grid(row=3, column=1, padx=(0, 10), pady=5, sticky="ew")
        self.openai_entry.insert(0, self.config.get('openai', {}).get('api_key', ''))
        self.test_openai_btn = ctk.CTkButton(self.api_card, text="Test Key", width=80, command=self.test_openai_key)
        self.test_openai_btn.grid(row=3, column=2, padx=(0, 20), pady=5, sticky="e")

        ctk.CTkLabel(self.api_card, text="Custom Base URL (DeepSeek/OpenRouter):", font=ctk.CTkFont(weight="bold")).grid(row=4, column=0, padx=20, pady=5, sticky="e")
        self.base_url_entry = ctk.CTkEntry(self.api_card, height=35, placeholder_text="Leave blank for OpenAI")
        self.base_url_entry.grid(row=4, column=1, columnspan=2, padx=(0, 20), pady=5, sticky="ew")
        self.base_url_entry.insert(0, self.config.get('openai', {}).get('base_url', ''))

        self.anthropic_link_label = ctk.CTkLabel(self.api_card, text="Anthropic API Key (Get Here):", font=ctk.CTkFont(weight="bold", underline=True), text_color="#3a7ebf", cursor="hand2")
        self.anthropic_link_label.grid(row=5, column=0, padx=20, pady=5, sticky="e")
        self.anthropic_link_label.bind("<Button-1>", lambda e: webbrowser.open("https://console.anthropic.com/settings/keys"))
        self.anthropic_entry = ctk.CTkEntry(self.api_card, show="•", height=35, placeholder_text="sk-ant-...")
        self.anthropic_entry.grid(row=5, column=1, padx=(0, 10), pady=5, sticky="ew")
        self.anthropic_entry.insert(0, self.config.get('anthropic', {}).get('api_key', ''))
        self.test_anthropic_btn = ctk.CTkButton(self.api_card, text="Test Key", width=80, command=self.test_anthropic_key)
        self.test_anthropic_btn.grid(row=5, column=2, padx=(0, 20), pady=5, sticky="e")

        self.grok_link_label = ctk.CTkLabel(self.api_card, text="Grok/xAI API Key (Get Here):", font=ctk.CTkFont(weight="bold", underline=True), text_color="#3a7ebf", cursor="hand2")
        self.grok_link_label.grid(row=6, column=0, padx=20, pady=5, sticky="e")
        self.grok_link_label.bind("<Button-1>", lambda e: webbrowser.open("https://console.x.ai/"))
        self.grok_entry = ctk.CTkEntry(self.api_card, show="•", height=35, placeholder_text="xai-...")
        self.grok_entry.grid(row=6, column=1, padx=(0, 10), pady=5, sticky="ew")
        self.grok_entry.insert(0, self.config.get('xai', {}).get('api_key', ''))
        self.test_grok_btn = ctk.CTkButton(self.api_card, text="Test Key", width=80, command=self.test_grok_key)
        self.test_grok_btn.grid(row=6, column=2, padx=(0, 20), pady=5, sticky="e")

        self.google_link_label = ctk.CTkLabel(self.api_card, text="Google API Key (Get Free):", font=ctk.CTkFont(weight="bold", underline=True), text_color="#3a7ebf", cursor="hand2")
        self.google_link_label.grid(row=7, column=0, padx=20, pady=5, sticky="e")
        self.google_link_label.bind("<Button-1>", lambda e: webbrowser.open("https://aistudio.google.com/app/apikey"))
        self.google_entry = ctk.CTkEntry(self.api_card, show="•", height=35, placeholder_text="AIzaSy...")
        self.google_entry.grid(row=7, column=1, padx=(0, 10), pady=5, sticky="ew")
        self.google_entry.insert(0, self.config.get('google', {}).get('api_key', ''))
        self.test_google_btn = ctk.CTkButton(self.api_card, text="Test Key", width=80, command=self.test_google_key)
        self.test_google_btn.grid(row=7, column=2, padx=(0, 20), pady=5, sticky="e")

        ctk.CTkLabel(self.api_card, text="Discord Webhook URL (Optional):", font=ctk.CTkFont(weight="bold")).grid(row=8, column=0, padx=20, pady=5, sticky="e")
        self.discord_entry = ctk.CTkEntry(self.api_card, height=35, placeholder_text="https://discord.com/api/webhooks/...")
        self.discord_entry.grid(row=8, column=1, padx=(0, 10), pady=5, sticky="ew")
        self.discord_entry.insert(0, self.config.get('integrations', {}).get('discord_webhook', ''))
        self.test_discord_btn = ctk.CTkButton(self.api_card, text="Test Alert", width=80, command=self.test_discord_webhook)
        self.test_discord_btn.grid(row=8, column=2, padx=(0, 20), pady=5, sticky="e")

        ctk.CTkLabel(self.api_card, text="AI Chat Model:", font=ctk.CTkFont(weight="bold")).grid(row=9, column=0, padx=20, pady=5, sticky="e")
        self.model_menu = ctk.CTkComboBox(self.api_card, values=[
            "gpt-4o", "gpt-4o-mini", 
            "gemini-2.5-flash", "gemini-2.5-pro",
            "claude-sonnet-4-6", "claude-haiku-4-5-20251001",
            "grok-2-latest", "grok-2-mini",
            "deepseek-chat", "deepseek-reasoner",
            "openrouter/google/gemini-2.5-pro", "openrouter/meta-llama/llama-3.1-70b-instruct"
        ], height=35)
        self.model_menu.grid(row=9, column=1, columnspan=2, padx=(0, 20), pady=5, sticky="ew")
        self.model_menu.set(self.config.get('openai', {}).get('chat_model', 'gpt-4o'))

        ctk.CTkLabel(self.api_card, text="Whisper Transcribe Model:", font=ctk.CTkFont(weight="bold")).grid(row=10, column=0, padx=20, pady=5, sticky="e")
        self.whisper_menu = ctk.CTkOptionMenu(self.api_card, values=["tiny", "base", "small", "medium", "large"], height=35)
        self.whisper_menu.grid(row=10, column=1, columnspan=2, padx=(0, 20), pady=5, sticky="ew")
        self.whisper_menu.set(self.config.get('openai', {}).get('whisper_model', 'base'))

        ctk.CTkLabel(self.api_card, text="VOD Language:", font=ctk.CTkFont(weight="bold")).grid(row=11, column=0, padx=20, pady=(5, 15), sticky="e")
        self.language_menu = ctk.CTkComboBox(self.api_card, values=["Auto-Detect", "English", "Spanish", "French", "German", "Italian", "Portuguese", "Russian", "Japanese", "Korean", "Chinese"], height=35)
        self.language_menu.grid(row=11, column=1, columnspan=2, padx=(0, 20), pady=(5, 15), sticky="ew")
        self.language_menu.set(self.config.get('openai', {}).get('whisper_language', 'English'))

        # --- Card 2: Paths & Downloads ---
        self.paths_card = ctk.CTkFrame(self.settings_frame, corner_radius=15)
        self.paths_card.grid(row=2, column=0, padx=30, pady=(5, 10), sticky="ew")
        self.paths_card.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(self.paths_card, text="Paths & Downloads", font=ctk.CTkFont(weight="bold", size=16), text_color="#a0a0a0").grid(row=0, column=0, columnspan=3, padx=20, pady=(15, 10), sticky="w")

        ctk.CTkLabel(self.paths_card, text="VOD Download Size:", font=ctk.CTkFont(weight="bold")).grid(row=1, column=0, padx=20, pady=5, sticky="e")
        self.quality_menu = ctk.CTkOptionMenu(self.paths_card, values=["Best", "1080p", "720p"], height=35)
        self.quality_menu.grid(row=1, column=1, columnspan=2, padx=(0, 20), pady=5, sticky="w")
        self.quality_menu.set(self.config.get('settings', {}).get('download_quality', 'Best'))

        ctk.CTkLabel(self.paths_card, text="Raw VODs Folder:", font=ctk.CTkFont(weight="bold")).grid(row=2, column=0, padx=20, pady=5, sticky="e")
        self.vod_dir_entry = ctk.CTkEntry(self.paths_card, height=35, placeholder_text="C:\\Videos\\Raw")
        self.vod_dir_entry.grid(row=2, column=1, padx=(0, 10), pady=5, sticky="ew")
        self.vod_dir_entry.insert(0, self.config.get('settings', {}).get('download_dir', ''))
        self.vod_browse_btn = ctk.CTkButton(self.paths_card, text="Browse...", width=80, command=lambda: self.browse_folder(self.vod_dir_entry))
        self.vod_browse_btn.grid(row=2, column=2, padx=(0, 20), pady=5, sticky="e")

        ctk.CTkLabel(self.paths_card, text="Generated Clips Folder:", font=ctk.CTkFont(weight="bold")).grid(row=3, column=0, padx=20, pady=5, sticky="e")
        self.clip_dir_entry = ctk.CTkEntry(self.paths_card, height=35, placeholder_text="C:\\Videos\\Clips")
        self.clip_dir_entry.grid(row=3, column=1, padx=(0, 10), pady=5, sticky="ew")
        self.clip_dir_entry.insert(0, self.config.get('settings', {}).get('clips_dir', ''))
        self.clip_browse_btn = ctk.CTkButton(self.paths_card, text="Browse...", width=80, command=lambda: self.browse_folder(self.clip_dir_entry))
        self.clip_browse_btn.grid(row=3, column=2, padx=(0, 20), pady=5, sticky="e")

        ctk.CTkLabel(self.paths_card, text="Auth Browser (Cookies):", font=ctk.CTkFont(weight="bold")).grid(row=4, column=0, padx=20, pady=(5, 15), sticky="e")
        self.browser_menu = ctk.CTkOptionMenu(self.paths_card, values=["None", "chrome", "edge", "firefox", "opera", "brave", "vivaldi"], height=35)
        self.browser_menu.grid(row=4, column=1, columnspan=2, padx=(0, 20), pady=(5, 15), sticky="w")
        self.browser_menu.set(self.config.get('settings', {}).get('auth_browser', 'None'))

        # --- Card 3: Video Processing Rules ---
        self.proc_card = ctk.CTkFrame(self.settings_frame, corner_radius=15)
        self.proc_card.grid(row=3, column=0, padx=30, pady=(5, 10), sticky="ew")
        self.proc_card.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(self.proc_card, text="Video Processing Rules", font=ctk.CTkFont(weight="bold", size=16), text_color="#a0a0a0").grid(row=0, column=0, columnspan=3, padx=20, pady=(15, 10), sticky="w")

        self.hardware_switch = ctk.CTkSwitch(self.proc_card, text="GPU Hardware Encoding (NVENC/AMF)", font=ctk.CTkFont(weight="bold"))
        self.hardware_switch.grid(row=1, column=0, columnspan=2, padx=20, pady=(5, 5), sticky="w")

        self.downmix_switch = ctk.CTkSwitch(self.proc_card, text="Downmix Multi-Track Audio (OBS)", font=ctk.CTkFont(weight="bold"))
        self.downmix_switch.grid(row=2, column=0, columnspan=2, padx=20, pady=(5, 5), sticky="w")

        self.audio_peak_switch = ctk.CTkSwitch(self.proc_card, text="Measure Audio Peak Levels", font=ctk.CTkFont(weight="bold"))
        self.audio_peak_switch.grid(row=3, column=0, columnspan=2, padx=20, pady=(5, 5), sticky="w")

        self.combat_switch = ctk.CTkSwitch(self.proc_card, text="AI Combat Detection (Gunfights/Action)", font=ctk.CTkFont(weight="bold"))
        self.combat_switch.grid(row=4, column=0, columnspan=2, padx=20, pady=(5, 5), sticky="w")

        self.stabilize_switch = ctk.CTkSwitch(self.proc_card, text="Apply VR Anti-Shake Filter (Experimental/Slow)", font=ctk.CTkFont(weight="bold"))
        self.stabilize_switch.grid(row=5, column=0, columnspan=2, padx=20, pady=(5, 5), sticky="w")

        self.vertical_switch = ctk.CTkSwitch(self.proc_card, text="Generate Vertical Shorts (9:16)", font=ctk.CTkFont(weight="bold"))
        self.vertical_switch.grid(row=6, column=0, padx=20, pady=(15, 5), sticky="w")
        
        self.vertical_mode_menu = ctk.CTkOptionMenu(
            self.proc_card, 
            values=["Standard Center Crop", "Facecam Top-Left", "Facecam Top-Right", "Facecam Bottom-Left", "Facecam Bottom-Right", "Custom Coordinates"],
            height=35
        )
        self.vertical_mode_menu.grid(row=6, column=1, columnspan=2, padx=(0, 20), pady=(15, 5), sticky="w")

        self.coord_frame = ctk.CTkFrame(self.proc_card, fg_color="transparent")
        self.coord_frame.grid(row=7, column=1, columnspan=2, padx=(0, 20), pady=(5, 15), sticky="w")
        
        ctk.CTkLabel(self.coord_frame, text="X:").pack(side="left", padx=(0, 5))
        self.crop_x_entry = ctk.CTkEntry(self.coord_frame, width=50)
        self.crop_x_entry.pack(side="left", padx=(0, 10))
        
        ctk.CTkLabel(self.coord_frame, text="Y:").pack(side="left", padx=(0, 5))
        self.crop_y_entry = ctk.CTkEntry(self.coord_frame, width=50)
        self.crop_y_entry.pack(side="left", padx=(0, 10))
        
        ctk.CTkLabel(self.coord_frame, text="W:").pack(side="left", padx=(0, 5))
        self.crop_w_entry = ctk.CTkEntry(self.coord_frame, width=50)
        self.crop_w_entry.pack(side="left", padx=(0, 10))
        
        ctk.CTkLabel(self.coord_frame, text="H:").pack(side="left", padx=(0, 5))
        self.crop_h_entry = ctk.CTkEntry(self.coord_frame, width=50)
        self.crop_h_entry.pack(side="left", padx=(0, 0))

        # LOAD SAVED STATES
        settings_cfg = self.config.get('settings', {})
        if settings_cfg.get('vr_stabilization', False): self.stabilize_switch.select()
        else: self.stabilize_switch.deselect()

        if settings_cfg.get('hardware_encoding', False): self.hardware_switch.select()
        else: self.hardware_switch.deselect()

        if settings_cfg.get('audio_downmix', True): self.downmix_switch.select()
        else: self.downmix_switch.deselect()

        if settings_cfg.get('audio_peak_detection', True): self.audio_peak_switch.select()
        else: self.audio_peak_switch.deselect()

        if settings_cfg.get('combat_detection', True): self.combat_switch.select()
        else: self.combat_switch.deselect()

        if settings_cfg.get('vertical_export', False): self.vertical_switch.select()
        else: self.vertical_switch.deselect()
        
        self.vertical_mode_menu.set(settings_cfg.get('vertical_mode', 'Standard Center Crop'))
        self.crop_x_entry.insert(0, settings_cfg.get('crop_x', '0'))
        self.crop_y_entry.insert(0, settings_cfg.get('crop_y', '0'))
        self.crop_w_entry.insert(0, settings_cfg.get('crop_w', '400'))
        self.crop_h_entry.insert(0, settings_cfg.get('crop_h', '225'))

        self.help_card = ctk.CTkFrame(self.settings_frame, corner_radius=15, fg_color="#1a1a1a")
        self.help_card.grid(row=4, column=0, padx=30, pady=(20, 0), sticky="ew")
        
        help_text = (
            "🚀 Quick Start Guide:\n\n"
            "1. AI Engines: Gemini 2.5 Flash is highly recommended for streams over 1 hour.\n"
            "2. Hardware: NVIDIA GPUs (CUDA) process audio infinitely faster than CPU-only systems.\n"
            "3. Vertical Generation: Custom Coordinates are based on a 1080p source video size.\n\n"
            "⚠️ IMPORTANT: Make sure to click 'Save Settings' after making any changes above!"
        )
        self.help_label = ctk.CTkLabel(self.help_card, text=help_text, justify="left", font=ctk.CTkFont(size=12), padx=20, pady=20)
        self.help_label.pack(anchor="w")

        self.save_btn = ctk.CTkButton(self.settings_frame, text="Save Settings", height=45, font=ctk.CTkFont(weight="bold"), command=self.save_settings)
        self.save_btn.grid(row=5, column=0, padx=30, pady=20, sticky="e")

    def _setup_gallery_frame(self):
        # ==================== GALLERY FRAME ====================
        self.gallery_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.gallery_frame.grid_columnconfigure(1, weight=1)
        self.gallery_frame.grid_rowconfigure(3, weight=1)

        self.gallery_title = ctk.CTkLabel(self.gallery_frame, text="Clip Gallery & Reasoning", font=ctk.CTkFont(size=28, weight="bold"))
        self.gallery_title.grid(row=0, column=0, columnspan=2, padx=30, pady=(30, 10), sticky="w")
        
        self.sort_frame = ctk.CTkFrame(self.gallery_frame, fg_color="transparent")
        self.sort_frame.grid(row=1, column=0, padx=(30, 10), pady=(0, 5), sticky="ew")
        
        self.sort_label = ctk.CTkLabel(self.sort_frame, text="Sort by:", font=ctk.CTkFont(size=12))
        self.sort_label.pack(side="left", padx=(0, 5))
        
        self.sort_menu = ctk.CTkOptionMenu(self.sort_frame, values=["Date (Newest)", "Date (Oldest)", "Virality (High)", "Virality (Low)"], 
                                           command=lambda _: self.populate_gallery())
        self.sort_menu.pack(side="left", fill="x", expand=True)
        self.sort_menu.set("Date (Newest)")

        # --- Filters ---
        self.filter_frame = ctk.CTkFrame(self.gallery_frame, fg_color="transparent")
        self.filter_frame.grid(row=2, column=0, padx=(30, 10), pady=(0, 5), sticky="ew")
        
        ctk.CTkLabel(self.filter_frame, text="Type:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 5))
        self.type_filter_menu = ctk.CTkOptionMenu(self.filter_frame, values=["All", "Horizontal", "Vertical"], width=100, command=lambda _: self.populate_gallery())
        self.type_filter_menu.pack(side="left", padx=(0, 10))
        self.type_filter_menu.set("All")
        
        ctk.CTkLabel(self.filter_frame, text="Min Score:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 5))
        self.score_filter_menu = ctk.CTkOptionMenu(self.filter_frame, values=["All", "3+", "5+", "7+", "8+", "9+"], width=80, command=lambda _: self.populate_gallery())
        self.score_filter_menu.pack(side="left")
        self.score_filter_menu.set("All")

        self.clip_listbox = ctk.CTkScrollableFrame(self.gallery_frame, width=300, corner_radius=15)
        self.clip_listbox.grid(row=3, column=0, padx=(30, 10), pady=10, sticky="nsew")

        self.gallery_actions_frame = ctk.CTkFrame(self.gallery_frame, fg_color="transparent")
        self.gallery_actions_frame.grid(row=4, column=0, padx=(30, 10), pady=(0, 10), sticky="ew")

        self.select_all_var = ctk.BooleanVar(value=False)
        self.select_all_checkbox = ctk.CTkCheckBox(self.gallery_actions_frame, text="Select All", variable=self.select_all_var, command=self.toggle_select_all)
        self.select_all_checkbox.pack(side="left", padx=(0, 10))

        self.refresh_gallery_btn = ctk.CTkButton(self.gallery_actions_frame, text="🔄 Refresh List", command=self.refresh_gallery_action)
        self.refresh_gallery_btn.pack(side="right", fill="x", expand=True)

        self.delete_marked_btn = ctk.CTkButton(self.gallery_frame, text="🗑️ Delete Marked Clips", fg_color="#c0392b", hover_color="#922b21", command=self.confirm_delete_marked)
        self.delete_marked_btn.grid(row=5, column=0, padx=(30, 10), pady=(0, 20), sticky="ew")

        self.details_card = ctk.CTkFrame(self.gallery_frame, corner_radius=15)
        self.details_card.grid(row=1, column=1, rowspan=5, padx=(10, 30), pady=(10, 20), sticky="nsew")
        self.details_card.grid_columnconfigure(0, weight=1)

        self.detail_title = ctk.CTkLabel(self.details_card, text="Select a clip to view details", font=ctk.CTkFont(size=20, weight="bold"))
        self.detail_title.grid(row=0, column=0, padx=20, pady=20, sticky="w")

        self.detail_score = ctk.CTkLabel(self.details_card, text="Score: --/10", font=ctk.CTkFont(size=16), text_color="#2ecc71")
        self.detail_score.grid(row=1, column=0, padx=20, pady=5, sticky="w")

        self.detail_reasoning = ctk.CTkTextbox(self.details_card, font=ctk.CTkFont(size=14), wrap="word", fg_color="transparent")
        self.detail_reasoning.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        self.details_card.grid_rowconfigure(2, weight=1)

        self.detail_thumbnail = ctk.CTkLabel(self.details_card, text="")
        self.detail_thumbnail.grid(row=3, column=0, padx=20, pady=5)

        self.gallery_btns_frame = ctk.CTkFrame(self.details_card, fg_color="transparent")
        self.gallery_btns_frame.grid(row=4, column=0, padx=20, pady=20, sticky="ew")
        self.gallery_btns_frame.grid_columnconfigure((0, 1), weight=1)

        self.play_clip_btn = ctk.CTkButton(self.gallery_btns_frame, text="▶️ Play Clip", height=50, font=ctk.CTkFont(weight="bold"), state="disabled")
        self.play_clip_btn.grid(row=0, column=0, padx=(0, 5), sticky="ew")

        self.open_folder_btn = ctk.CTkButton(self.gallery_btns_frame, text="📁 Open Folder", height=50, font=ctk.CTkFont(weight="bold"), state="disabled", fg_color="#2b2b2b", hover_color="#3b3b3b")
        self.open_folder_btn.grid(row=0, column=1, padx=(5, 0), sticky="ew")

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
                import google.generativeai as genai # type: ignore
                genai.configure(api_key=key)
                list(genai.list_models()) 
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
            for _ in range(14400):
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