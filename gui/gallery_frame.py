import customtkinter as ctk # type: ignore

class GalleryFrame(ctk.CTkFrame):
    def __init__(self, master: ctk.CTk, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(3, weight=1)

        self.gallery_title = ctk.CTkLabel(self, text="Clip Gallery & Reasoning", font=ctk.CTkFont(size=28, weight="bold"))
        self.gallery_title.grid(row=0, column=0, columnspan=2, padx=30, pady=(30, 10), sticky="w")
        
        self.sort_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.sort_frame.grid(row=1, column=0, padx=(30, 10), pady=(0, 5), sticky="ew")
        
        self.sort_label = ctk.CTkLabel(self.sort_frame, text="Sort by:", font=ctk.CTkFont(size=12))
        self.sort_label.pack(side="left", padx=(0, 5))
        
        self.sort_menu = ctk.CTkOptionMenu(self.sort_frame, values=["Date (Newest)", "Date (Oldest)", "Virality (High)", "Virality (Low)"], 
                                           command=lambda _: master.populate_gallery()) # type: ignore
        self.sort_menu.pack(side="left", fill="x", expand=True)
        self.sort_menu.set("Date (Newest)")

        # --- Filters ---
        self.filter_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.filter_frame.grid(row=2, column=0, padx=(30, 10), pady=(0, 5), sticky="ew")
        
        ctk.CTkLabel(self.filter_frame, text="Type:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 5))
        self.type_filter_menu = ctk.CTkOptionMenu(self.filter_frame, values=["All", "Horizontal", "Vertical"], width=100, command=lambda _: master.populate_gallery()) # type: ignore
        self.type_filter_menu.pack(side="left", padx=(0, 10))
        self.type_filter_menu.set("All")
        
        ctk.CTkLabel(self.filter_frame, text="Min Score:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 5))
        self.score_filter_menu = ctk.CTkOptionMenu(self.filter_frame, values=["All", "3+", "5+", "7+", "8+", "9+"], width=80, command=lambda _: master.populate_gallery()) # type: ignore
        self.score_filter_menu.pack(side="left")
        self.score_filter_menu.set("All")

        self.clip_listbox = ctk.CTkScrollableFrame(self, width=300, corner_radius=15)
        self.clip_listbox.grid(row=3, column=0, padx=(30, 10), pady=10, sticky="nsew")

        self.gallery_actions_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.gallery_actions_frame.grid(row=4, column=0, padx=(30, 10), pady=(0, 10), sticky="ew")

        self.select_all_var = ctk.BooleanVar(value=False)
        self.select_all_checkbox = ctk.CTkCheckBox(self.gallery_actions_frame, text="Select All", variable=self.select_all_var, command=master.toggle_select_all) # type: ignore
        self.select_all_checkbox.pack(side="left", padx=(0, 10))

        self.refresh_gallery_btn = ctk.CTkButton(self.gallery_actions_frame, text="🔄 Refresh List", command=master.refresh_gallery_action) # type: ignore
        self.refresh_gallery_btn.pack(side="right", fill="x", expand=True)

        self.delete_marked_btn = ctk.CTkButton(self, text="🗑️ Delete Marked Clips", fg_color="#c0392b", hover_color="#922b21", command=master.confirm_delete_marked) # type: ignore
        self.delete_marked_btn.grid(row=5, column=0, padx=(30, 10), pady=(0, 20), sticky="ew")

        self.details_card = ctk.CTkFrame(self, corner_radius=15)
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
