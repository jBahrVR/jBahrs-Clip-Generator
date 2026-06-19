import customtkinter as ctk # type: ignore

class PromptFrame(ctk.CTkFrame):
    def __init__(self, master: ctk.CTk, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        
        self.prompt_title = ctk.CTkLabel(self, text="AI Prompt Editor", font=ctk.CTkFont(size=28, weight="bold"))
        self.prompt_title.grid(row=0, column=0, padx=30, pady=(30, 10), sticky="w")

        self.prompt_select_card = ctk.CTkFrame(self, corner_radius=15)
        self.prompt_select_card.grid(row=1, column=0, padx=30, pady=10, sticky="ew")
        
        ctk.CTkLabel(self.prompt_select_card, text="Active Manual Profile:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=20, pady=20)
        self.profile_dropdown = ctk.CTkOptionMenu(self.prompt_select_card, command=master.on_profile_change) # type: ignore
        self.profile_dropdown.pack(side="left", padx=10)

        self.new_profile_btn = ctk.CTkButton(self.prompt_select_card, text="➕ New", width=60, fg_color="#27ae60", hover_color="#1e8449", command=master.create_new_profile) # type: ignore
        self.new_profile_btn.pack(side="left", padx=5)

        self.delete_profile_btn = ctk.CTkButton(self.prompt_select_card, text="Delete Profile", fg_color="#c0392b", hover_color="#922b21", command=master.delete_profile) # type: ignore
        self.delete_profile_btn.pack(side="right", padx=20)

        self.prompt_editor_card = ctk.CTkFrame(self, corner_radius=15)
        self.prompt_editor_card.grid(row=2, column=0, padx=30, pady=10, sticky="nsew")
        self.prompt_editor_card.grid_columnconfigure(0, weight=1)
        self.prompt_editor_card.grid_rowconfigure(0, weight=1)

        self.prompt_textbox = ctk.CTkTextbox(self.prompt_editor_card, font=ctk.CTkFont(size=14), wrap="word")
        self.prompt_textbox.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")

        self.save_prompt_btn = ctk.CTkButton(self.prompt_editor_card, text="Save Current Prompt", height=40, font=ctk.CTkFont(weight="bold"), command=master.save_current_prompt) # type: ignore
        self.save_prompt_btn.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="e")
