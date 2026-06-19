import customtkinter as ctk # type: ignore

class AutoFrame(ctk.CTkFrame):
    def __init__(self, master: ctk.CTk, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)
        
        # Access master config safely
        config = master.config if hasattr(master, "config") else {} # type: ignore

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

        ctk.CTkLabel(self.auto_controls_card, text="Orientation:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=4, padx=10, pady=(20,10))
        self.target_menu = ctk.CTkOptionMenu(self.auto_controls_card, values=["Vertical Only", "Horizontal Only", "Any"], width=130)
        self.target_menu.grid(row=0, column=5, padx=5, pady=(20,10))
        self.target_menu.set(config.get("auto_scheduler", {}).get("target_orientation", "Horizontal Only"))

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

        self.auto_switch = ctk.CTkSwitch(self.auto_controls_card, text="Enable Watcher", font=ctk.CTkFont(weight="bold"), command=master.toggle_auto) # type: ignore
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
