import customtkinter as ctk # type: ignore
import webbrowser
from typing import Optional, Callable

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
        super().__init__(master, width=220, corner_radius=0, fg_color="#1e1e1e", **kwargs)
        self.on_navigate = on_navigate
        self.on_quick_action = on_quick_action
        self.grid_rowconfigure(12, weight=1)

        self.logo_label = ctk.CTkLabel(self, text="jBahr's Clip\nGenerator", font=ctk.CTkFont(size=24, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(30, 20))

        self.nav_manual_btn = ctk.CTkButton(
            self, text="🎬 Manual Clipper", fg_color="transparent", border_width=1,
            command=lambda: self._trigger_navigate("manual")
        )
        self.nav_manual_btn.grid(row=1, column=0, padx=20, pady=10, sticky="ew")

        self.nav_auto_btn = ctk.CTkButton(
            self, text="⏳ Auto Scheduler", fg_color="transparent", border_width=1,
            command=lambda: self._trigger_navigate("auto")
        )
        self.nav_auto_btn.grid(row=2, column=0, padx=20, pady=10, sticky="ew")

        self.nav_prompt_btn = ctk.CTkButton(
            self, text="📝 Prompt Manager", fg_color="transparent", border_width=1,
            command=lambda: self._trigger_navigate("prompt")
        )
        self.nav_prompt_btn.grid(row=3, column=0, padx=20, pady=10, sticky="ew")

        self.nav_settings_btn = ctk.CTkButton(
            self, text="⚙️ Settings", fg_color="transparent", border_width=1,
            command=lambda: self._trigger_navigate("settings")
        )
        self.nav_settings_btn.grid(row=4, column=0, padx=20, pady=10, sticky="ew")

        self.nav_gallery_btn = ctk.CTkButton(
            self, text="🖼️ Clip Gallery", fg_color="transparent", border_width=1,
            command=lambda: self._trigger_navigate("gallery")
        )
        self.nav_gallery_btn.grid(row=5, column=0, padx=20, pady=10, sticky="ew")

        self.github_btn = ctk.CTkButton(
            self, text="🌐 GitHub Repo", fg_color="#24292e", hover_color="#2f363d",
            command=lambda: webbrowser.open("https://github.com/jBahrVR/jBahrs-Clip-Generator")
        )
        self.github_btn.grid(row=6, column=0, padx=20, pady=(10, 0), sticky="ew")

        self.quick_access_label = ctk.CTkLabel(self, text="Quick Access", font=ctk.CTkFont(size=12, weight="bold"), text_color="gray")
        self.quick_access_label.grid(row=7, column=0, padx=20, pady=(20, 0), sticky="w")

        self.open_vods_btn = ctk.CTkButton(
            self, text="📁 Raw VODs", fg_color="#2b2b2b", hover_color="#3b3b3b",
            command=lambda: self._trigger_quick_action("download_dir")
        )
        self.open_vods_btn.grid(row=8, column=0, padx=20, pady=(5, 5), sticky="ew")

        self.open_clips_btn = ctk.CTkButton(
            self, text="✂️ Generated Clips", fg_color="#2b2b2b", hover_color="#3b3b3b",
            command=lambda: self._trigger_quick_action("clips_dir")
        )
        self.open_clips_btn.grid(row=9, column=0, padx=20, pady=(5, 5), sticky="ew")

        self.open_logs_btn = ctk.CTkButton(
            self, text="📝 View Crash Logs", fg_color="#2b2b2b", hover_color="#3b3b3b",
            command=lambda: self._trigger_quick_action("logs")
        )
        self.open_logs_btn.grid(row=10, column=0, padx=20, pady=(5, 5), sticky="ew")

        self.open_readme_btn = ctk.CTkButton(
            self, text="📖 View Readme", fg_color="#2b2b2b", hover_color="#3b3b3b",
            command=lambda: self._trigger_quick_action("readme")
        )
        self.open_readme_btn.grid(row=11, column=0, padx=20, pady=(5, 20), sticky="ew")

        self.discord_btn = ctk.CTkButton(
            self, text="💬 Join Discord", fg_color="#5865F2", hover_color="#4752C4",
            command=lambda: webbrowser.open("https://discord.gg/uUF8J9Zqwz")
        )
        self.discord_btn.grid(row=12, column=0, padx=20, pady=(5, 5), sticky="ew")

        self.version_label = ctk.CTkLabel(self, text="v1.2.1 Creator Edition", font=ctk.CTkFont(size=10), text_color="gray")
        self.version_label.grid(row=13, column=0, padx=20, pady=10, sticky="s")

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
