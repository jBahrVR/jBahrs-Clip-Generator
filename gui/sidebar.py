import customtkinter as ctk # type: ignore
import webbrowser
from typing import Optional, Callable
from . import theme

class Sidebar(ctk.CTkFrame):
    """
    Application navigation sidebar view.
    Encapsulates tab switching and quick-access utility shortcuts.
    """

    def __init__(
        self,
        master: ctk.CTk,
        on_navigate: Optional[Callable[[str], None]] = None,
        on_quick_action: Optional[Callable[[str], None]] = None,
        **kwargs
    ) -> None:
        super().__init__(master, width=230, corner_radius=0, fg_color=theme.COLOR_SIDEBAR_BG, **kwargs)
        self.on_navigate = on_navigate
        self.on_quick_action = on_quick_action
        self.grid_rowconfigure(14, weight=1)

        # Brand / App Title
        self.brand_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.brand_frame.grid(row=0, column=0, padx=20, pady=(24, 16), sticky="w")
        
        self.logo_label = ctk.CTkLabel(
            self.brand_frame,
            text="ClipGen",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=theme.COLOR_TEXT_PRIMARY
        )
        self.logo_label.pack(anchor="w")

        self.tagline_label = ctk.CTkLabel(
            self.brand_frame,
            text="AI Stream Studio",
            font=ctk.CTkFont(size=11),
            text_color=theme.COLOR_TEXT_MUTED
        )
        self.tagline_label.pack(anchor="w")

        # Section: Studio Views
        self.views_header = ctk.CTkLabel(
            self,
            text="STUDIO",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=theme.COLOR_TEXT_DIM
        )
        self.views_header.grid(row=1, column=0, padx=24, pady=(10, 4), sticky="w")

        self.nav_manual_btn = ctk.CTkButton(
            self, text="Manual Clipper", anchor="w", height=36, corner_radius=theme.RADIUS_BUTTON,
            fg_color="transparent", hover_color=theme.COLOR_HOVER_MUTED, text_color=theme.COLOR_TEXT_PRIMARY,
            command=lambda: self._trigger_navigate("manual")
        )
        self.nav_manual_btn.grid(row=2, column=0, padx=16, pady=3, sticky="ew")

        self.nav_auto_btn = ctk.CTkButton(
            self, text="Auto Scheduler", anchor="w", height=36, corner_radius=theme.RADIUS_BUTTON,
            fg_color="transparent", hover_color=theme.COLOR_HOVER_MUTED, text_color=theme.COLOR_TEXT_PRIMARY,
            command=lambda: self._trigger_navigate("auto")
        )
        self.nav_auto_btn.grid(row=3, column=0, padx=16, pady=3, sticky="ew")

        self.nav_gallery_btn = ctk.CTkButton(
            self, text="Clip Gallery", anchor="w", height=36, corner_radius=theme.RADIUS_BUTTON,
            fg_color="transparent", hover_color=theme.COLOR_HOVER_MUTED, text_color=theme.COLOR_TEXT_PRIMARY,
            command=lambda: self._trigger_navigate("gallery")
        )
        self.nav_gallery_btn.grid(row=4, column=0, padx=16, pady=3, sticky="ew")

        self.nav_prompt_btn = ctk.CTkButton(
            self, text="Prompt Manager", anchor="w", height=36, corner_radius=theme.RADIUS_BUTTON,
            fg_color="transparent", hover_color=theme.COLOR_HOVER_MUTED, text_color=theme.COLOR_TEXT_PRIMARY,
            command=lambda: self._trigger_navigate("prompt")
        )
        self.nav_prompt_btn.grid(row=5, column=0, padx=16, pady=3, sticky="ew")

        self.nav_settings_btn = ctk.CTkButton(
            self, text="Settings", anchor="w", height=36, corner_radius=theme.RADIUS_BUTTON,
            fg_color="transparent", hover_color=theme.COLOR_HOVER_MUTED, text_color=theme.COLOR_TEXT_PRIMARY,
            command=lambda: self._trigger_navigate("settings")
        )
        self.nav_settings_btn.grid(row=6, column=0, padx=16, pady=3, sticky="ew")

        # Section: Storage / Quick Access
        self.quick_access_label = ctk.CTkLabel(
            self, text="DIRECTORIES", font=ctk.CTkFont(size=10, weight="bold"), text_color=theme.COLOR_TEXT_DIM
        )
        self.quick_access_label.grid(row=7, column=0, padx=24, pady=(16, 4), sticky="w")

        self.open_vods_btn = ctk.CTkButton(
            self, text="Raw VODs", anchor="w", height=32, corner_radius=theme.RADIUS_BUTTON,
            fg_color=theme.COLOR_CARD_BG, hover_color=theme.COLOR_HOVER_MUTED, text_color=theme.COLOR_TEXT_MUTED,
            command=lambda: self._trigger_quick_action("download_dir")
        )
        self.open_vods_btn.grid(row=8, column=0, padx=16, pady=2, sticky="ew")

        self.open_clips_btn = ctk.CTkButton(
            self, text="Generated Clips", anchor="w", height=32, corner_radius=theme.RADIUS_BUTTON,
            fg_color=theme.COLOR_CARD_BG, hover_color=theme.COLOR_HOVER_MUTED, text_color=theme.COLOR_TEXT_MUTED,
            command=lambda: self._trigger_quick_action("clips_dir")
        )
        self.open_clips_btn.grid(row=9, column=0, padx=16, pady=2, sticky="ew")

        self.open_logs_btn = ctk.CTkButton(
            self, text="Crash Logs", anchor="w", height=32, corner_radius=theme.RADIUS_BUTTON,
            fg_color=theme.COLOR_CARD_BG, hover_color=theme.COLOR_HOVER_MUTED, text_color=theme.COLOR_TEXT_MUTED,
            command=lambda: self._trigger_quick_action("logs")
        )
        self.open_logs_btn.grid(row=10, column=0, padx=16, pady=2, sticky="ew")

        # Section: Community & Docs
        self.comm_header = ctk.CTkLabel(
            self, text="COMMUNITY", font=ctk.CTkFont(size=10, weight="bold"), text_color=theme.COLOR_TEXT_DIM
        )
        self.comm_header.grid(row=11, column=0, padx=24, pady=(16, 4), sticky="w")

        self.discord_btn = ctk.CTkButton(
            self, text="Discord Community", anchor="w", height=32, corner_radius=theme.RADIUS_BUTTON,
            fg_color=theme.COLOR_CARD_BG, hover_color=theme.COLOR_HOVER_MUTED, text_color=theme.COLOR_TEXT_MUTED,
            command=lambda: webbrowser.open("https://discord.gg/uUF8J9Zqwz")
        )
        self.discord_btn.grid(row=12, column=0, padx=16, pady=2, sticky="ew")

        self.github_btn = ctk.CTkButton(
            self, text="GitHub Repository", anchor="w", height=32, corner_radius=theme.RADIUS_BUTTON,
            fg_color=theme.COLOR_CARD_BG, hover_color=theme.COLOR_HOVER_MUTED, text_color=theme.COLOR_TEXT_MUTED,
            command=lambda: webbrowser.open("https://github.com/jBahrVR/jBahrs-Clip-Generator")
        )
        self.github_btn.grid(row=13, column=0, padx=16, pady=2, sticky="ew")

        self.version_label = ctk.CTkLabel(self, text="v2.0 Creator Edition", font=ctk.CTkFont(size=10), text_color=theme.COLOR_TEXT_DIM)
        self.version_label.grid(row=15, column=0, padx=20, pady=(10, 16), sticky="s")

    def _trigger_navigate(self, tab: str) -> None:
        if self.on_navigate:
            self.on_navigate(tab)
        else:
            fn = getattr(self.master, f"show_{tab}_frame", None)
            if callable(fn):
                fn()

    def _trigger_quick_action(self, action: str) -> None:
        if self.on_quick_action:
            self.on_quick_action(action)
        else:
            if action in ("download_dir", "clips_dir"):
                fn = getattr(self.master, "open_local_folder", None)
                if callable(fn):
                    fn(action)
            elif action == "logs":
                fn = getattr(self.master, "open_logs", None)
                if callable(fn):
                    fn()
            elif action == "readme":
                fn = getattr(self.master, "open_readme", None)
                if callable(fn):
                    fn()

    def set_active_tab(self, tab: str) -> None:
        """Updates navigation button highlights for the selected tab."""
        nav_buttons = {
            "manual": self.nav_manual_btn,
            "auto": self.nav_auto_btn,
            "prompt": self.nav_prompt_btn,
            "settings": self.nav_settings_btn,
            "gallery": self.nav_gallery_btn,
        }
        for name, btn in nav_buttons.items():
            btn.configure(fg_color="#1f538d" if name == tab else "transparent")
