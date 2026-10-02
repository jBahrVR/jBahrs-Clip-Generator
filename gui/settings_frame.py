import customtkinter as ctk # type: ignore
import webbrowser
from typing import Optional, Callable, Dict, Any, List
import model_fetcher

class DummyWidget:
    def __init__(self, val=""):
        self.val = val
    def get(self):
        return self.val
    def set(self, val):
        self.val = val
    def select(self):
        self.val = 1
    def deselect(self):
        self.val = 0
    def insert(self, idx, text):
        self.val = text

class SettingsFrame(ctk.CTkScrollableFrame):
    """
    Configuration and settings view.
    Encapsulates credentials, AI model choices, directory paths, and rendering switches.
    """

    def __init__(
        self,
        master: ctk.CTk,
        on_save: Optional[Callable] = None,
        on_test_key: Optional[Callable[[str], None]] = None,
        on_browse_folder: Optional[Callable[[str], None]] = None,
        on_update_ytdlp: Optional[Callable] = None,
        on_verify_social: Optional[Callable[[str], None]] = None,
        on_refresh_models: Optional[Callable[[], None]] = None,
        **kwargs
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.on_save = on_save
        self.on_test_key = on_test_key
        self.on_browse_folder = on_browse_folder
        self.on_update_ytdlp = on_update_ytdlp
        self.on_verify_social = on_verify_social
        self.on_refresh_models = on_refresh_models

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
        self.test_openai_btn = ctk.CTkButton(self.api_card, text="Test Key", width=80, command=lambda: self._trigger_test_key("openai"))
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
        self.test_anthropic_btn = ctk.CTkButton(self.api_card, text="Test Key", width=80, command=lambda: self._trigger_test_key("anthropic"))
        self.test_anthropic_btn.grid(row=5, column=2, padx=(0, 20), pady=5, sticky="e")

        self.grok_link_label = ctk.CTkLabel(self.api_card, text="Grok/xAI API Key (Get Here):", font=ctk.CTkFont(weight="bold", underline=True), text_color="#3a7ebf", cursor="hand2")
        self.grok_link_label.grid(row=6, column=0, padx=20, pady=5, sticky="e")
        self.grok_link_label.bind("<Button-1>", lambda e: webbrowser.open("https://console.x.ai/"))
        self.grok_entry = ctk.CTkEntry(self.api_card, show="•", height=35, placeholder_text="xai-...")
        self.grok_entry.grid(row=6, column=1, padx=(0, 10), pady=5, sticky="ew")
        self.grok_entry.insert(0, config.get('xai', {}).get('api_key', ''))
        self.test_grok_btn = ctk.CTkButton(self.api_card, text="Test Key", width=80, command=lambda: self._trigger_test_key("grok"))
        self.test_grok_btn.grid(row=6, column=2, padx=(0, 20), pady=5, sticky="e")

        self.google_link_label = ctk.CTkLabel(self.api_card, text="Google API Key (Get Free):", font=ctk.CTkFont(weight="bold", underline=True), text_color="#3a7ebf", cursor="hand2")
        self.google_link_label.grid(row=7, column=0, padx=20, pady=5, sticky="e")
        self.google_link_label.bind("<Button-1>", lambda e: webbrowser.open("https://aistudio.google.com/app/apikey"))
        self.google_entry = ctk.CTkEntry(self.api_card, show="•", height=35, placeholder_text="AIzaSy...")
        self.google_entry.grid(row=7, column=1, padx=(0, 10), pady=5, sticky="ew")
        self.google_entry.insert(0, config.get('google', {}).get('api_key', ''))
        self.test_google_btn = ctk.CTkButton(self.api_card, text="Test Key", width=80, command=lambda: self._trigger_test_key("google"))
        self.test_google_btn.grid(row=7, column=2, padx=(0, 20), pady=5, sticky="e")

        ctk.CTkLabel(self.api_card, text="Discord Webhook URL (Optional):", font=ctk.CTkFont(weight="bold")).grid(row=8, column=0, padx=20, pady=5, sticky="e")
        self.discord_entry = ctk.CTkEntry(self.api_card, show="•", height=35, placeholder_text="https://discord.com/api/webhooks/...")
        self.discord_entry.grid(row=8, column=1, padx=(0, 10), pady=5, sticky="ew")
        self.discord_entry.insert(0, config.get('integrations', {}).get('discord_webhook', ''))
        self.test_discord_btn = ctk.CTkButton(self.api_card, text="Test Alert", width=80, command=lambda: self._trigger_test_key("discord"))
        self.test_discord_btn.grid(row=8, column=2, padx=(0, 20), pady=5, sticky="e")

        ctk.CTkLabel(self.api_card, text="AI Chat Model:", font=ctk.CTkFont(weight="bold")).grid(row=9, column=0, padx=20, pady=5, sticky="e")
        initial_models = model_fetcher.load_cached_models() or model_fetcher.BASELINE_MODELS
        self.model_menu = ctk.CTkComboBox(self.api_card, values=initial_models, height=35)
        self.model_menu.grid(row=9, column=1, padx=(0, 10), pady=5, sticky="ew")
        self.model_menu.set(config.get('openai', {}).get('chat_model', 'gemini-3.6-flash'))
        self.refresh_models_btn = ctk.CTkButton(self.api_card, text="🔄 Refresh", width=80, command=self._trigger_refresh_models)
        self.refresh_models_btn.grid(row=9, column=2, padx=(0, 20), pady=5, sticky="e")

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
        self.vod_browse_btn = ctk.CTkButton(self.paths_card, text="Browse...", width=80, command=lambda: self._trigger_browse_folder("download_dir"))
        self.vod_browse_btn.grid(row=2, column=2, padx=(0, 20), pady=5, sticky="e")

        ctk.CTkLabel(self.paths_card, text="Generated Clips Folder:", font=ctk.CTkFont(weight="bold")).grid(row=3, column=0, padx=20, pady=5, sticky="e")
        self.clip_dir_entry = ctk.CTkEntry(self.paths_card, height=35, placeholder_text="C:\\Videos\\Clips")
        self.clip_dir_entry.grid(row=3, column=1, padx=(0, 10), pady=5, sticky="ew")
        self.clip_dir_entry.insert(0, config.get('settings', {}).get('clips_dir', ''))
        self.clip_browse_btn = ctk.CTkButton(self.paths_card, text="Browse...", width=80, command=lambda: self._trigger_browse_folder("clips_dir"))
        self.clip_browse_btn.grid(row=3, column=2, padx=(0, 20), pady=5, sticky="e")

        ctk.CTkLabel(self.paths_card, text="Auth Browser (Cookies):", font=ctk.CTkFont(weight="bold")).grid(row=4, column=0, padx=20, pady=5, sticky="e")
        self.browser_menu = ctk.CTkOptionMenu(self.paths_card, values=["None", "chrome", "edge", "firefox", "opera", "brave", "vivaldi"], height=35)
        self.browser_menu.grid(row=4, column=1, columnspan=2, padx=(0, 20), pady=5, sticky="w")
        self.browser_menu.set(config.get('settings', {}).get('auth_browser', 'None'))

        ctk.CTkLabel(self.paths_card, text="Dependencies:", font=ctk.CTkFont(weight="bold")).grid(row=5, column=0, padx=20, pady=(5, 15), sticky="e")
        self.update_ytdlp_btn = ctk.CTkButton(self.paths_card, text="Update yt-dlp", width=120, command=self._trigger_update_ytdlp)
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

        self.aspect_card = ctk.CTkFrame(self.proc_card, fg_color="#181818", corner_radius=8)
        self.aspect_card.grid(row=6, column=0, columnspan=3, padx=20, pady=(15, 10), sticky="ew")
        
        ctk.CTkLabel(
            self.aspect_card,
            text="📐 Aspect Ratio: Auto-Detect (Preserves Native Full Quality)",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#2ecc71"
        ).pack(anchor="w", padx=15, pady=(10, 2))
        
        ctk.CTkLabel(
            self.aspect_card,
            text="Videos are automatically analyzed to detect native dimensions & aspect ratio. Content is exported as-is in full quality without crop distortion.",
            font=ctk.CTkFont(size=11),
            text_color="#aaaaaa"
        ).pack(anchor="w", padx=15, pady=(0, 10))

        # Backward-compatibility dummy handles (no UI clutter)
        self.vertical_switch = DummyWidget(0)
        self.vertical_mode_menu = DummyWidget("Standard Center Crop")
        self.crop_x_entry = DummyWidget("0")
        self.crop_y_entry = DummyWidget("0")
        self.crop_w_entry = DummyWidget("400")
        self.crop_h_entry = DummyWidget("225")

        self.burn_subtitles_switch = ctk.CTkSwitch(self.proc_card, text="Burn Subtitles (TikTok/Shorts)", font=ctk.CTkFont(weight="bold"))
        self.burn_subtitles_switch.grid(row=8, column=0, padx=20, pady=(15, 5), sticky="w")

        self.subtitle_style_menu = ctk.CTkOptionMenu(
            self.proc_card,
            values=["Viral Yellow Highlight", "Neon Green Highlight", "Clean White Bold", "Classic Box"],
            height=35
        )
        self.subtitle_style_menu.grid(row=8, column=1, columnspan=2, padx=(0, 20), pady=(15, 5), sticky="w")

        self.sub_opt_frame = ctk.CTkFrame(self.proc_card, fg_color="transparent")
        self.sub_opt_frame.grid(row=9, column=1, columnspan=2, padx=(0, 20), pady=(5, 15), sticky="w")

        ctk.CTkLabel(self.sub_opt_frame, text="Pos:").pack(side="left", padx=(0, 5))
        self.subtitle_pos_menu = ctk.CTkOptionMenu(
            self.sub_opt_frame,
            values=["Bottom Third", "Center", "Top Third"],
            height=28, width=120
        )
        self.subtitle_pos_menu.pack(side="left", padx=(0, 10))

        ctk.CTkLabel(self.sub_opt_frame, text="Size:").pack(side="left", padx=(0, 5))
        self.subtitle_size_menu = ctk.CTkOptionMenu(
            self.sub_opt_frame,
            values=["36", "42", "48", "54"],
            height=28, width=70
        )
        self.subtitle_size_menu.pack(side="left", padx=(0, 0))

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

        if settings_cfg.get('burn_subtitles', False): self.burn_subtitles_switch.select()
        else: self.burn_subtitles_switch.deselect()

        self.vertical_mode_menu.set(settings_cfg.get('vertical_mode', 'Standard Center Crop'))
        self.subtitle_style_menu.set(settings_cfg.get('subtitle_style', 'Viral Yellow Highlight'))
        self.subtitle_pos_menu.set(settings_cfg.get('subtitle_position', 'Bottom Third'))
        self.subtitle_size_menu.set(str(settings_cfg.get('subtitle_font_size', 48)))
        self.crop_x_entry.insert(0, settings_cfg.get('crop_x', '0'))
        self.crop_y_entry.insert(0, settings_cfg.get('crop_y', '0'))
        self.crop_w_entry.insert(0, settings_cfg.get('crop_w', '400'))
        self.crop_h_entry.insert(0, settings_cfg.get('crop_h', '225'))

        # --- Card 4: Social Media Publishing ---
        self.social_card = ctk.CTkFrame(self, corner_radius=15)
        self.social_card.grid(row=4, column=0, padx=30, pady=(5, 10), sticky="ew")
        self.social_card.grid_columnconfigure(1, weight=1)

        social_cfg = config.get('social', {})
        yt_social = social_cfg.get('youtube', {})
        tk_social = social_cfg.get('tiktok', {})
        ig_social = social_cfg.get('instagram', {})

        ctk.CTkLabel(
            self.social_card,
            text="🚀 Direct Social Media Publishing APIs",
            font=ctk.CTkFont(weight="bold", size=16),
            text_color="#a0a0a0"
        ).grid(row=0, column=0, columnspan=3, padx=20, pady=(15, 5), sticky="w")

        ctk.CTkLabel(
            self.social_card,
            text="Publish rendered clips directly to YouTube Shorts, TikTok, and Instagram Reels from the Gallery.",
            font=ctk.CTkFont(size=12),
            text_color="#888888"
        ).grid(row=1, column=0, columnspan=3, padx=20, pady=(0, 10), sticky="w")

        # YouTube Shorts Section
        ctk.CTkLabel(self.social_card, text="YouTube Shorts (OAuth2)", font=ctk.CTkFont(weight="bold", size=13), text_color="#3498db").grid(row=2, column=0, columnspan=3, padx=20, pady=(5, 5), sticky="w")

        ctk.CTkLabel(self.social_card, text="Client ID:", font=ctk.CTkFont(weight="bold")).grid(row=3, column=0, padx=20, pady=4, sticky="e")
        self.yt_client_id_entry = ctk.CTkEntry(self.social_card, height=32, placeholder_text="apps.googleusercontent.com")
        self.yt_client_id_entry.grid(row=3, column=1, columnspan=2, padx=(0, 20), pady=4, sticky="ew")
        self.yt_client_id_entry.insert(0, yt_social.get('client_id', ''))

        ctk.CTkLabel(self.social_card, text="Client Secret:", font=ctk.CTkFont(weight="bold")).grid(row=4, column=0, padx=20, pady=4, sticky="e")
        self.yt_client_secret_entry = ctk.CTkEntry(self.social_card, show="•", height=32, placeholder_text="GOCSPX-...")
        self.yt_client_secret_entry.grid(row=4, column=1, columnspan=2, padx=(0, 20), pady=4, sticky="ew")
        self.yt_client_secret_entry.insert(0, yt_social.get('client_secret', ''))

        ctk.CTkLabel(self.social_card, text="Refresh Token:", font=ctk.CTkFont(weight="bold")).grid(row=5, column=0, padx=20, pady=4, sticky="e")
        self.yt_refresh_token_entry = ctk.CTkEntry(self.social_card, show="•", height=32, placeholder_text="1//0...")
        self.yt_refresh_token_entry.grid(row=5, column=1, padx=(0, 10), pady=4, sticky="ew")
        self.yt_refresh_token_entry.insert(0, yt_social.get('refresh_token', ''))

        self.verify_yt_btn = ctk.CTkButton(self.social_card, text="Verify", width=80, command=lambda: self._trigger_verify_social("YouTube Shorts"))
        self.verify_yt_btn.grid(row=5, column=2, padx=(0, 20), pady=4, sticky="e")

        # TikTok Section
        ctk.CTkLabel(self.social_card, text="TikTok Content Posting API", font=ctk.CTkFont(weight="bold", size=13), text_color="#2ecc71").grid(row=6, column=0, columnspan=3, padx=20, pady=(12, 5), sticky="w")

        ctk.CTkLabel(self.social_card, text="Access Token:", font=ctk.CTkFont(weight="bold")).grid(row=7, column=0, padx=20, pady=4, sticky="e")
        self.tiktok_token_entry = ctk.CTkEntry(self.social_card, show="•", height=32, placeholder_text="act.example_access_token...")
        self.tiktok_token_entry.grid(row=7, column=1, padx=(0, 10), pady=4, sticky="ew")
        self.tiktok_token_entry.insert(0, tk_social.get('access_token', ''))

        self.verify_tiktok_btn = ctk.CTkButton(self.social_card, text="Verify", width=80, command=lambda: self._trigger_verify_social("TikTok"))
        self.verify_tiktok_btn.grid(row=7, column=2, padx=(0, 20), pady=4, sticky="e")

        # Instagram Reels Section
        ctk.CTkLabel(self.social_card, text="Instagram Reels (Meta Graph API)", font=ctk.CTkFont(weight="bold", size=13), text_color="#e74c3c").grid(row=8, column=0, columnspan=3, padx=20, pady=(12, 5), sticky="w")

        ctk.CTkLabel(self.social_card, text="IG User / Page ID:", font=ctk.CTkFont(weight="bold")).grid(row=9, column=0, padx=20, pady=4, sticky="e")
        self.ig_user_id_entry = ctk.CTkEntry(self.social_card, height=32, placeholder_text="e.g. 17841400000000000")
        self.ig_user_id_entry.grid(row=9, column=1, columnspan=2, padx=(0, 20), pady=4, sticky="ew")
        self.ig_user_id_entry.insert(0, ig_social.get('user_id', ''))

        ctk.CTkLabel(self.social_card, text="Graph Access Token:", font=ctk.CTkFont(weight="bold")).grid(row=10, column=0, padx=20, pady=(4, 15), sticky="e")
        self.ig_token_entry = ctk.CTkEntry(self.social_card, show="•", height=32, placeholder_text="EAA...")
        self.ig_token_entry.grid(row=10, column=1, padx=(0, 10), pady=(4, 15), sticky="ew")
        self.ig_token_entry.insert(0, ig_social.get('access_token', ''))

        self.verify_ig_btn = ctk.CTkButton(self.social_card, text="Verify", width=80, command=lambda: self._trigger_verify_social("Instagram Reels"))
        self.verify_ig_btn.grid(row=10, column=2, padx=(0, 20), pady=(4, 15), sticky="e")

        self.help_card = ctk.CTkFrame(self, corner_radius=15, fg_color="#1a1a1a")
        self.help_card.grid(row=5, column=0, padx=30, pady=(20, 0), sticky="ew")
        
        help_text = (
            "🚀 Quick Start Guide:\n\n"
            "1. AI Engines: Gemini 2.5 Flash is highly recommended for streams over 1 hour.\n"
            "2. Hardware: NVIDIA GPUs (CUDA) process audio infinitely faster than CPU-only systems.\n"
            "3. Vertical Generation: Custom Coordinates are based on a 1080p source video size.\n\n"
            "⚠️ IMPORTANT: Make sure to click 'Save Settings' after making any changes above!"
        )
        self.help_label = ctk.CTkLabel(self.help_card, text=help_text, justify="left", font=ctk.CTkFont(size=12), padx=20, pady=20)
        self.help_label.pack(anchor="w")

        self.save_btn = ctk.CTkButton(self, text="Save Settings", height=45, font=ctk.CTkFont(weight="bold"), command=self._trigger_save)
        self.save_btn.grid(row=6, column=0, padx=30, pady=20, sticky="e")

    def _trigger_save(self) -> None:
        if self.on_save:
            self.on_save()
        else:
            fn = getattr(self.master, "save_settings", None)
            if callable(fn):
                fn()

    def _trigger_test_key(self, provider: str) -> None:
        if self.on_test_key:
            self.on_test_key(provider)
        else:
            fn = getattr(self.master, f"test_{provider}_key" if provider != "discord" else "test_discord_webhook", None)
            if callable(fn):
                fn()

    def _trigger_verify_social(self, platform: str) -> None:
        if self.on_verify_social:
            self.on_verify_social(platform)
        else:
            fn = getattr(self.master, "verify_social_credentials", None)
            if callable(fn):
                fn(platform)

    def _trigger_browse_folder(self, field_name: str) -> None:
        entry = self.vod_dir_entry if field_name == "download_dir" else self.clip_dir_entry
        if self.on_browse_folder:
            self.on_browse_folder(field_name)
        else:
            fn = getattr(self.master, "browse_folder", None)
            if callable(fn):
                fn(entry)

    def _trigger_update_ytdlp(self) -> None:
        if self.on_update_ytdlp:
            self.on_update_ytdlp()
        else:
            fn = getattr(self.master, "update_ytdlp", None)
            if callable(fn):
                fn()

    def _trigger_refresh_models(self) -> None:
        if self.on_refresh_models:
            self.on_refresh_models()
        else:
            fn = getattr(self.master, "refresh_available_models", None)
            if callable(fn):
                fn(manual=True)

    def set_refreshing_models_state(self, is_refreshing: bool, message: str = "") -> None:
        """Visual feedback on the refresh models button."""
        if not hasattr(self, 'refresh_models_btn'):
            return
        if is_refreshing:
            self.refresh_models_btn.configure(text="Fetching...", state="disabled")
        else:
            self.refresh_models_btn.configure(text=message or "🔄 Refresh", state="normal")
            if message and message != "🔄 Refresh":
                self.after(2500, lambda: self.refresh_models_btn.configure(text="🔄 Refresh"))

    # --- Public Encapsulated API ---

    def get_settings(self) -> Dict[str, Any]:
        """Extracts all form entries and toggle switches into a structured settings dictionary."""
        return {
            'youtube': {
                'channel_id': self.yt_id_entry.get().strip()
            },
            'twitch': {
                'username': self.twitch_entry.get().strip()
            },
            'openai': {
                'api_key': self.openai_entry.get().strip(),
                'base_url': self.base_url_entry.get().strip(),
                'chat_model': self.model_menu.get(),
                'whisper_model': self.whisper_menu.get(),
                'whisper_language': self.language_menu.get()
            },
            'anthropic': {
                'api_key': self.anthropic_entry.get().strip()
            },
            'xai': {
                'api_key': self.grok_entry.get().strip()
            },
            'google': {
                'api_key': self.google_entry.get().strip()
            },
            'integrations': {
                'discord_webhook': self.discord_entry.get().strip()
            },
            'settings': {
                'download_quality': self.quality_menu.get(),
                'download_dir': self.vod_dir_entry.get().strip(),
                'clips_dir': self.clip_dir_entry.get().strip(),
                'auth_browser': self.browser_menu.get(),
                'vr_stabilization': self.stabilize_switch.get() == 1,
                'hardware_encoding': self.hardware_switch.get() == 1,
                'audio_downmix': self.downmix_switch.get() == 1,
                'audio_peak_detection': self.audio_peak_switch.get() == 1,
                'combat_detection': self.combat_switch.get() == 1,
                'vertical_export': self.vertical_switch.get() == 1,
                'vertical_mode': self.vertical_mode_menu.get(),
                'crop_x': self.crop_x_entry.get().strip(),
                'crop_y': self.crop_y_entry.get().strip(),
                'crop_w': self.crop_w_entry.get().strip(),
                'burn_subtitles': (self.burn_subtitles_switch.get() == 1) if hasattr(self, 'burn_subtitles_switch') else False,
                'subtitle_style': self.subtitle_style_menu.get() if hasattr(self, 'subtitle_style_menu') else "Viral Yellow Highlight",
                'subtitle_position': self.subtitle_pos_menu.get() if hasattr(self, 'subtitle_pos_menu') else "Bottom Third",
                'subtitle_font_size': int(self.subtitle_size_menu.get()) if (hasattr(self, 'subtitle_size_menu') and str(self.subtitle_size_menu.get()).isdigit()) else 48
            }
        }
        if hasattr(self, 'yt_client_id_entry'):
            settings_dict['social'] = {
                'youtube': {
                    'enabled': bool(self.yt_client_id_entry.get().strip()),
                    'client_id': self.yt_client_id_entry.get().strip(),
                    'client_secret': self.yt_client_secret_entry.get().strip(),
                    'refresh_token': self.yt_refresh_token_entry.get().strip()
                },
                'tiktok': {
                    'enabled': bool(self.tiktok_token_entry.get().strip()),
                    'client_key': '',
                    'client_secret': '',
                    'access_token': self.tiktok_token_entry.get().strip()
                },
                'instagram': {
                    'enabled': bool(self.ig_user_id_entry.get().strip()),
                    'user_id': self.ig_user_id_entry.get().strip(),
                    'access_token': self.ig_token_entry.get().strip()
                }
            }
        return settings_dict

    def set_available_models(self, models: List[str]) -> None:
        """Dynamically populates the chat model combo box with fetched models."""
        if models:
            self.model_menu.configure(values=models)

    def show_saved_feedback(self) -> None:
        """Provides visual confirmation on the Save button."""
        original_color = self.save_btn.cget("fg_color")
        self.save_btn.configure(text="✅ Saved!", fg_color="#2ecc71")
        self.after(2000, lambda: self.save_btn.configure(text="Save Settings", fg_color=original_color))
