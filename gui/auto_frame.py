import customtkinter as ctk # type: ignore
from typing import Optional, Callable, Dict, List, Any

class AutoAspectLabel(ctk.CTkLabel):
    def get(self) -> str:
        return "Auto-Detect (Native)"
    def set(self, val: str) -> None:
        pass

class AutoFrame(ctk.CTkFrame):
    """
    Automated background watcher view.
    Encapsulates platform selection, scheduling parameters, watcher switch, and status logging.
    """

    def __init__(
        self,
        master: ctk.CTk,
        on_toggle_auto: Optional[Callable[[bool], None]] = None,
        **kwargs
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.on_toggle_auto = on_toggle_auto
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)
        
        config = getattr(master, "config", {})

        self.auto_title = ctk.CTkLabel(self, text="Automated Background Watcher", font=ctk.CTkFont(size=28, weight="bold"))
        self.auto_title.grid(row=0, column=0, padx=30, pady=(30, 10), sticky="w")

        self.auto_controls_card = ctk.CTkFrame(self, corner_radius=15)
        self.auto_controls_card.grid(row=1, column=0, padx=30, pady=10, sticky="ew")
        
        ctk.CTkLabel(self.auto_controls_card, text="Platform:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=10, pady=(20,10))
        self.platform_menu = ctk.CTkOptionMenu(self.auto_controls_card, values=["YouTube", "Twitch"], width=110)
        self.platform_menu.grid(row=0, column=1, padx=5, pady=(20,10))
        self.platform_menu.set(config.get("auto_scheduler", {}).get("platform", "YouTube"))

        ctk.CTkLabel(self.auto_controls_card, text="Type:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=2, padx=10, pady=(20,10))
        self.type_menu = ctk.CTkOptionMenu(self.auto_controls_card, values=["Livestreams Only", "Any Upload"], width=130)
        self.type_menu.grid(row=0, column=3, padx=5, pady=(20,10))
        self.type_menu.set(config.get("auto_scheduler", {}).get("video_type", "Livestreams Only"))

        ctk.CTkLabel(self.auto_controls_card, text="Aspect Ratio:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=4, padx=10, pady=(20,10))
        self.target_menu = AutoAspectLabel(
            self.auto_controls_card,
            text="✨ Auto-Detect (Native)",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#2ecc71"
        )
        self.target_menu.grid(row=0, column=5, padx=5, pady=(20,10))

        ctk.CTkLabel(self.auto_controls_card, text="Max Age:", font=ctk.CTkFont(weight="bold")).grid(row=1, column=0, padx=10, pady=(10,10))
        self.lookback_menu = ctk.CTkOptionMenu(self.auto_controls_card, values=["1 Day", "3 Days", "7 Days", "14 Days", "30 Days", "All Time"], width=110)
        self.lookback_menu.grid(row=1, column=1, padx=5, pady=(10,10))
        self.lookback_menu.set(config.get("auto_scheduler", {}).get("lookback_days", "7 Days"))

        ctk.CTkLabel(self.auto_controls_card, text="Interval:", font=ctk.CTkFont(weight="bold")).grid(row=1, column=2, padx=10, pady=(10,10))
        self.interval_menu = ctk.CTkOptionMenu(self.auto_controls_card, values=["Every 1 Hour", "Every 4 Hours", "Every 12 Hours", "Every 24 Hours"], width=130)
        self.interval_menu.grid(row=1, column=3, padx=5, pady=(10,10))
        self.interval_menu.set(config.get("auto_scheduler", {}).get("check_interval", "Every 4 Hours"))

        ctk.CTkLabel(self.auto_controls_card, text="Auto-Prompt:", font=ctk.CTkFont(weight="bold")).grid(row=1, column=4, padx=10, pady=(10,10))
        self.auto_prompt_menu = ctk.CTkOptionMenu(self.auto_controls_card, width=130)
        self.auto_prompt_menu.grid(row=1, column=5, padx=5, pady=(10,10))

        self.auto_switch = ctk.CTkSwitch(
            self.auto_controls_card, text="Enable Watcher", font=ctk.CTkFont(weight="bold"),
            command=self._trigger_toggle_auto
        )
        self.auto_switch.grid(row=2, column=4, columnspan=2, padx=20, pady=(10,20), sticky="e")

        self.auto_progress = ctk.CTkProgressBar(self, mode="indeterminate", height=10)
        self.auto_progress.grid(row=2, column=0, padx=30, pady=(5, 5), sticky="ew")
        self.auto_progress.set(0)

        self.auto_console_card = ctk.CTkFrame(self, corner_radius=15)
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

    def _trigger_toggle_auto(self) -> None:
        is_enabled = self.auto_switch.get() == 1
        if self.on_toggle_auto:
            self.on_toggle_auto(is_enabled)
        else:
            fn = getattr(self.master, "toggle_auto", None)
            if callable(fn):
                fn()

    # --- Public Encapsulated API ---

    def get_scheduler_settings(self) -> Dict[str, Any]:
        """Returns the dictionary of configured auto-scheduler options."""
        return {
            "platform": self.platform_menu.get(),
            "video_type": self.type_menu.get(),
            "target_orientation": self.target_menu.get(),
            "lookback_days": self.lookback_menu.get(),
            "check_interval": self.interval_menu.get(),
            "auto_prompt_profile": self.auto_prompt_menu.get(),
        }

    def set_scheduler_settings(self, settings: Dict[str, Any]) -> None:
        """Sets dropdown choices based on saved configuration."""
        if "platform" in settings:
            self.platform_menu.set(settings["platform"])
        if "video_type" in settings:
            self.type_menu.set(settings["video_type"])
        if "target_orientation" in settings:
            self.target_menu.set(settings["target_orientation"])
        if "lookback_days" in settings:
            self.lookback_menu.set(settings["lookback_days"])
        if "check_interval" in settings:
            self.interval_menu.set(settings["check_interval"])
        if "auto_prompt_profile" in settings:
            self.auto_prompt_menu.set(settings["auto_prompt_profile"])

    def is_auto_enabled(self) -> bool:
        """Returns True if the auto switch is toggled ON."""
        return self.auto_switch.get() == 1

    def set_auto_enabled(self, enabled: bool) -> None:
        """Toggles the auto-switch programmatically."""
        if enabled:
            self.auto_switch.select()
        else:
            self.auto_switch.deselect()

    def set_status(self, is_running: bool, status_text: Optional[str] = None) -> None:
        """Updates watcher indicator and progress bar."""
        if is_running:
            self.auto_progress.start()
            text = status_text or "● Status: RUNNING"
            self.auto_status.configure(text=text, text_color="#2ecc71")
        else:
            self.auto_progress.stop()
            self.auto_progress.set(0)
            text = status_text or "● Status: OFF"
            self.auto_status.configure(text=text, text_color="gray")

    def set_prompt_profiles(self, profiles: List[str], active: Optional[str] = None) -> None:
        """Updates the list of selectable auto-prompt profiles."""
        if profiles:
            self.auto_prompt_menu.configure(values=profiles)
            if active and active in profiles:
                self.auto_prompt_menu.set(active)
            elif profiles:
                self.auto_prompt_menu.set(profiles[0])

    def append_log(self, text: str, tag: Optional[str] = None) -> None:
        """Appends a line of text to the auto console."""
        self.auto_console.configure(state="normal")
        if tag:
            self.auto_console.insert("end", text + "\n", tag)
        else:
            self.auto_console.insert("end", text + "\n")
        self.auto_console.see("end")
        self.auto_console.configure(state="disabled")

    def clear_log(self) -> None:
        """Clears auto console output."""
        self.auto_console.configure(state="normal")
        self.auto_console.delete("1.0", "end")
        self.auto_console.configure(state="disabled")
