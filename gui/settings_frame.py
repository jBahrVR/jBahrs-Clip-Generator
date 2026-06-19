import customtkinter as ctk # type: ignore
import webbrowser

class SettingsFrame(ctk.CTkScrollableFrame):
    def __init__(self, master: ctk.CTk, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.grid_columnconfigure(0, weight=1)
        
        config = getattr(master, "config", {})

        self.settings_title = ctk.CTkLabel(self, text="Configuration", font=ctk.CTkFont(size=28, weight="bold"))
        self.settings_title.grid(row=0, column=0, padx=30, pady=(20, 10), sticky="w")

        # --- Card 1: APIs & Models ---
        self.api_card = ctk.CTkFrame(self, corner_radius=15)
        self.api_card.grid(row=1, column=0, padx=30, pady=(5, 10), sticky="ew")
        self.api_card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self.api_card, text="Authentication & AI Models", font=ctk.CTkFont(weight="bold", size=16), text_color="#a0a0a0").grid(row=0, column=0, columnspan=3, padx=20, pady=(15, 10), sticky="w")

        ctk.CTkLabel(self.api_card, text="YouTube Channel ID:", font=ctk.CTkFont(weight="bold")).grid(row=1, column=0, padx=20, pady=5, sticky="e")
        self.yt_id_entry = ctk.CTkEntry(self.api_card, height=35, placeholder_text="e.g. UC_x5XG1OV2P6uZZ5FSM9Ttw")
        self.yt_id_entry.grid(row=1, column=1, columnspan=2, padx=(0, 20), pady=5, sticky="ew")
        self.yt_id_entry.insert(0, config.get('youtube', {}).get('channel_id', ''))

        ctk.CTkLabel(self.api_card, text="Twitch Username:", font=ctk.CTkFont(weight="bold")).grid(row=2, column=0, padx=20, pady=5, sticky="e")
        self.twitch_entry = ctk.CTkEntry(self.api_card, height=35, placeholder_text="e.g. ninja")
        self.twitch_entry.grid(row=2, column=1, columnspan=2, padx=(0, 20), pady=5, sticky="ew")
        self.twitch_entry.insert(0, config.get('twitch', {}).get('username', ''))

        self.api_link_label = ctk.CTkLabel(self.api_card, text="OpenAI API Key (Get Here):", font=ctk.CTkFont(weight="bold", underline=True), text_color="#3a7ebf", cursor="hand2")
        self.api_link_label.grid(row=3, column=0, padx=20, pady=5, sticky="e")
        self.api_link_label.bind("<Button-1>", lambda e: webbrowser.open("https://platform.openai.com/api-keys"))
        self.openai_entry = ctk.CTkEntry(self.api_card, show="•", height=35, placeholder_text="sk-proj-...")
        self.openai_entry.grid(row=3, column=1, padx=(0, 10), pady=5, sticky="ew")
        self.openai_entry.insert(0, config.get('openai', {}).get('api_key', ''))
        self.test_openai_btn = ctk.CTkButton(self.api_card, text="Test Key", width=80, command=master.test_openai_key) # type: ignore
        self.test_openai_btn.grid(row=3, column=2, padx=(0, 20), pady=5, sticky="e")

        ctk.CTkLabel(self.api_card, text="Custom Base URL (DeepSeek/OpenRouter):", font=ctk.CTkFont(weight="bold")).grid(row=4, column=0, padx=20, pady=5, sticky="e")
        self.base_url_entry = ctk.CTkEntry(self.api_card, height=35, placeholder_text="Leave blank for OpenAI")
        self.base_url_entry.grid(row=4, column=1, columnspan=2, padx=(0, 20), pady=5, sticky="ew")
        self.base_url_entry.insert(0, config.get('openai', {}).get('base_url', ''))

        self.anthropic_link_label = ctk.CTkLabel(self.api_card, text="Anthropic API Key (Get Here):", font=ctk.CTkFont(weight="bold", underline=True), text_color="#3a7ebf", cursor="hand2")
        self.anthropic_link_label.grid(row=5, column=0, padx=20, pady=5, sticky="e")
        self.anthropic_link_label.bind("<Button-1>", lambda e: webbrowser.open("https://console.anthropic.com/settings/keys"))
        self.anthropic_entry = ctk.CTkEntry(self.api_card, show="•", height=35, placeholder_text="sk-ant-...")
        self.anthropic_entry.grid(row=5, column=1, padx=(0, 10), pady=5, sticky="ew")
        self.anthropic_entry.insert(0, config.get('anthropic', {}).get('api_key', ''))
        self.test_anthropic_btn = ctk.CTkButton(self.api_card, text="Test Key", width=80, command=master.test_anthropic_key) # type: ignore
        self.test_anthropic_btn.grid(row=5, column=2, padx=(0, 20), pady=5, sticky="e")

        self.grok_link_label = ctk.CTkLabel(self.api_card, text="Grok/xAI API Key (Get Here):", font=ctk.CTkFont(weight="bold", underline=True), text_color="#3a7ebf", cursor="hand2")
        self.grok_link_label.grid(row=6, column=0, padx=20, pady=5, sticky="e")
        self.grok_link_label.bind("<Button-1>", lambda e: webbrowser.open("https://console.x.ai/"))
        self.grok_entry = ctk.CTkEntry(self.api_card, show="•", height=35, placeholder_text="xai-...")
        self.grok_entry.grid(row=6, column=1, padx=(0, 10), pady=5, sticky="ew")
        self.grok_entry.insert(0, config.get('xai', {}).get('api_key', ''))
        self.test_grok_btn = ctk.CTkButton(self.api_card, text="Test Key", width=80, command=master.test_grok_key) # type: ignore
        self.test_grok_btn.grid(row=6, column=2, padx=(0, 20), pady=5, sticky="e")

        self.google_link_label = ctk.CTkLabel(self.api_card, text="Google API Key (Get Free):", font=ctk.CTkFont(weight="bold", underline=True), text_color="#3a7ebf", cursor="hand2")
        self.google_link_label.grid(row=7, column=0, padx=20, pady=5, sticky="e")
        self.google_link_label.bind("<Button-1>", lambda e: webbrowser.open("https://aistudio.google.com/app/apikey"))
        self.google_entry = ctk.CTkEntry(self.api_card, show="•", height=35, placeholder_text="AIzaSy...")
        self.google_entry.grid(row=7, column=1, padx=(0, 10), pady=5, sticky="ew")
        self.google_entry.insert(0, config.get('google', {}).get('api_key', ''))
        self.test_google_btn = ctk.CTkButton(self.api_card, text="Test Key", width=80, command=master.test_google_key) # type: ignore
        self.test_google_btn.grid(row=7, column=2, padx=(0, 20), pady=5, sticky="e")

        ctk.CTkLabel(self.api_card, text="Discord Webhook URL (Optional):", font=ctk.CTkFont(weight="bold")).grid(row=8, column=0, padx=20, pady=5, sticky="e")
        self.discord_entry = ctk.CTkEntry(self.api_card, height=35, placeholder_text="https://discord.com/api/webhooks/...")
        self.discord_entry.grid(row=8, column=1, padx=(0, 10), pady=5, sticky="ew")
        self.discord_entry.insert(0, config.get('integrations', {}).get('discord_webhook', ''))
        self.test_discord_btn = ctk.CTkButton(self.api_card, text="Test Alert", width=80, command=master.test_discord_webhook) # type: ignore
        self.test_discord_btn.grid(row=8, column=2, padx=(0, 20), pady=5, sticky="e")

        ctk.CTkLabel(self.api_card, text="AI Chat Model:", font=ctk.CTkFont(weight="bold")).grid(row=9, column=0, padx=20, pady=5, sticky="e")
        self.model_menu = ctk.CTkComboBox(self.api_card, values=[
            "gemini-3.5-flash", "gemini-3.5-pro",
            "gemini-3-flash-preview", "gemini-3-pro-preview",
            "gpt-4o", "gpt-4o-mini", 
            "claude-sonnet-4-6", "claude-haiku-4-5-20251001",
            "grok-2-latest", "grok-2-mini",
            "deepseek-chat", "deepseek-reasoner",
            "openrouter/google/gemini-3.5-pro", "openrouter/meta-llama/llama-3.1-70b-instruct",
            "gemini-2.5-flash (Deprecated)", "gemini-2.5-pro (Deprecated)"
        ], height=35)
        self.model_menu.grid(row=9, column=1, columnspan=2, padx=(0, 20), pady=5, sticky="ew")
        self.model_menu.set(config.get('openai', {}).get('chat_model', 'gpt-4o'))

        ctk.CTkLabel(self.api_card, text="Whisper Transcribe Model:", font=ctk.CTkFont(weight="bold")).grid(row=10, column=0, padx=20, pady=5, sticky="e")
        self.whisper_menu = ctk.CTkOptionMenu(self.api_card, values=["tiny", "base", "small", "medium", "large"], height=35)
        self.whisper_menu.grid(row=10, column=1, columnspan=2, padx=(0, 20), pady=5, sticky="ew")
        self.whisper_menu.set(config.get('openai', {}).get('whisper_model', 'base'))

        ctk.CTkLabel(self.api_card, text="VOD Language:", font=ctk.CTkFont(weight="bold")).grid(row=11, column=0, padx=20, pady=(5, 15), sticky="e")
        self.language_menu = ctk.CTkComboBox(self.api_card, values=["Auto-Detect", "English", "Spanish", "French", "German", "Italian", "Portuguese", "Russian", "Japanese", "Korean", "Chinese"], height=35)
        self.language_menu.grid(row=11, column=1, columnspan=2, padx=(0, 20), pady=(5, 15), sticky="ew")
        self.language_menu.set(config.get('openai', {}).get('whisper_language', 'English'))

        # --- Card 2: Paths & Downloads ---
        self.paths_card = ctk.CTkFrame(self, corner_radius=15)
        self.paths_card.grid(row=2, column=0, padx=30, pady=(5, 10), sticky="ew")
        self.paths_card.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(self.paths_card, text="Paths & Downloads", font=ctk.CTkFont(weight="bold", size=16), text_color="#a0a0a0").grid(row=0, column=0, columnspan=3, padx=20, pady=(15, 10), sticky="w")

        ctk.CTkLabel(self.paths_card, text="VOD Download Size:", font=ctk.CTkFont(weight="bold")).grid(row=1, column=0, padx=20, pady=5, sticky="e")
        self.quality_menu = ctk.CTkOptionMenu(self.paths_card, values=["Best", "1080p", "720p"], height=35)
        self.quality_menu.grid(row=1, column=1, columnspan=2, padx=(0, 20), pady=5, sticky="w")
        self.quality_menu.set(config.get('settings', {}).get('download_quality', 'Best'))

        ctk.CTkLabel(self.paths_card, text="Raw VODs Folder:", font=ctk.CTkFont(weight="bold")).grid(row=2, column=0, padx=20, pady=5, sticky="e")
        self.vod_dir_entry = ctk.CTkEntry(self.paths_card, height=35, placeholder_text="C:\\Videos\\Raw")
        self.vod_dir_entry.grid(row=2, column=1, padx=(0, 10), pady=5, sticky="ew")
        self.vod_dir_entry.insert(0, config.get('settings', {}).get('download_dir', ''))
        self.vod_browse_btn = ctk.CTkButton(self.paths_card, text="Browse...", width=80, command=lambda: master.browse_folder(self.vod_dir_entry)) # type: ignore
        self.vod_browse_btn.grid(row=2, column=2, padx=(0, 20), pady=5, sticky="e")

        ctk.CTkLabel(self.paths_card, text="Generated Clips Folder:", font=ctk.CTkFont(weight="bold")).grid(row=3, column=0, padx=20, pady=5, sticky="e")
        self.clip_dir_entry = ctk.CTkEntry(self.paths_card, height=35, placeholder_text="C:\\Videos\\Clips")
        self.clip_dir_entry.grid(row=3, column=1, padx=(0, 10), pady=5, sticky="ew")
        self.clip_dir_entry.insert(0, config.get('settings', {}).get('clips_dir', ''))
        self.clip_browse_btn = ctk.CTkButton(self.paths_card, text="Browse...", width=80, command=lambda: master.browse_folder(self.clip_dir_entry)) # type: ignore
        self.clip_browse_btn.grid(row=3, column=2, padx=(0, 20), pady=5, sticky="e")

        ctk.CTkLabel(self.paths_card, text="Auth Browser (Cookies):", font=ctk.CTkFont(weight="bold")).grid(row=4, column=0, padx=20, pady=5, sticky="e")
        self.browser_menu = ctk.CTkOptionMenu(self.paths_card, values=["None", "chrome", "edge", "firefox", "opera", "brave", "vivaldi"], height=35)
        self.browser_menu.grid(row=4, column=1, columnspan=2, padx=(0, 20), pady=5, sticky="w")
        self.browser_menu.set(config.get('settings', {}).get('auth_browser', 'None'))

        ctk.CTkLabel(self.paths_card, text="Dependencies:", font=ctk.CTkFont(weight="bold")).grid(row=5, column=0, padx=20, pady=(5, 15), sticky="e")
        self.update_ytdlp_btn = ctk.CTkButton(self.paths_card, text="Update yt-dlp", width=120, command=master.update_ytdlp) # type: ignore
        self.update_ytdlp_btn.grid(row=5, column=1, columnspan=2, padx=(0, 20), pady=(5, 15), sticky="w")

        # --- Card 3: Video Processing Rules ---
        self.proc_card = ctk.CTkFrame(self, corner_radius=15)
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
        settings_cfg = config.get('settings', {})
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

        self.help_card = ctk.CTkFrame(self, corner_radius=15, fg_color="#1a1a1a")
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

        self.save_btn = ctk.CTkButton(self, text="Save Settings", height=45, font=ctk.CTkFont(weight="bold"), command=master.save_settings) # type: ignore
        self.save_btn.grid(row=5, column=0, padx=30, pady=20, sticky="e")
