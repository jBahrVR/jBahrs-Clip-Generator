import customtkinter as ctk # type: ignore

class ManualFrame(ctk.CTkFrame):
    def __init__(self, master: ctk.CTk, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)
        
        self.manual_title = ctk.CTkLabel(self, text="Manual Video Processor", font=ctk.CTkFont(size=28, weight="bold"))
        self.manual_title.grid(row=0, column=0, padx=30, pady=(30, 10), sticky="w")
        
        self.input_card = ctk.CTkFrame(self, corner_radius=15)
        self.input_card.grid(row=1, column=0, padx=30, pady=10, sticky="ew")
        self.input_card.grid_columnconfigure(0, weight=1)

        self.url_input = ctk.CTkEntry(self.input_card, placeholder_text="Paste URL or Select Local File(s)...", height=45, border_width=0)
        self.url_input.grid(row=0, column=0, padx=20, pady=20, sticky="ew")
        self.url_input.bind("<Return>", master.start_manual_process) # type: ignore
        
        self.process_btn = ctk.CTkButton(self.input_card, text="Process Queue", height=45, text_color="#FFFFFF", font=ctk.CTkFont(weight="bold"), command=master.start_manual_process) # type: ignore
        self.process_btn.grid(row=0, column=1, padx=(0, 10), pady=20)

        self.cancel_btn = ctk.CTkButton(self.input_card, text="Cancel", height=45, text_color="#FFFFFF", fg_color="#c0392b", hover_color="#922b21", font=ctk.CTkFont(weight="bold"), state="disabled", command=master.cancel_manual_process) # type: ignore
        self.cancel_btn.grid(row=0, column=2, padx=(0, 10), pady=20)

        self.local_file_btn = ctk.CTkButton(self.input_card, text="📂 Browse Files", height=45, text_color="#FFFFFF", fg_color="#27ae60", hover_color="#1e8449", font=ctk.CTkFont(weight="bold"), command=master.browse_local_file) # type: ignore
        self.local_file_btn.grid(row=0, column=3, padx=(0, 20), pady=20)
        
        self.manual_status_label = ctk.CTkLabel(self, text="Status: Ready", font=ctk.CTkFont(size=14, weight="bold"), text_color="#a0a0a0")
        self.manual_status_label.grid(row=2, column=0, padx=30, pady=(10, 0), sticky="w")
        
        self.manual_progress = ctk.CTkProgressBar(self, mode="indeterminate", height=10)
        self.manual_progress.grid(row=3, column=0, padx=30, pady=(5, 5), sticky="ew")
        self.manual_progress.set(0)

        self.console_card = ctk.CTkFrame(self, corner_radius=15)
        self.console_card.grid(row=4, column=0, padx=30, pady=(5, 10), sticky="nsew")
        self.console_card.grid_columnconfigure(0, weight=1)
        self.console_card.grid_rowconfigure(0, weight=1)

        self.console_box = ctk.CTkTextbox(self.console_card, state="disabled", fg_color="#121212", font=ctk.CTkFont(family="Consolas", size=13))
        self.console_box.grid(row=0, column=0, padx=15, pady=15, sticky="nsew")
        
        self.console_box.tag_config("error", foreground="#ff4d4d")
        self.console_box.tag_config("success", foreground="#2ecc71")
        self.console_box.tag_config("ai", foreground="#00d2ff")
        self.console_box.tag_config("ffmpeg", foreground="#f39c12")
