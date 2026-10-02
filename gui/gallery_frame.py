import os
import customtkinter as ctk # type: ignore
from typing import Optional, Callable, Dict, List, Any
from .video_preview import VideoPreviewWidget

class GalleryFrame(ctk.CTkFrame):
    """
    Clip Gallery view.
    Encapsulates clip list rendering, selection checkboxes, and detail inspection card.
    """

    def __init__(
        self,
        master: ctk.CTk,
        on_filter_changed: Optional[Callable] = None,
        on_refresh: Optional[Callable] = None,
        on_delete_marked: Optional[Callable] = None,
        on_publish_clip: Optional[Callable] = None,
        **kwargs
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.on_filter_changed = on_filter_changed
        self.on_refresh = on_refresh
        self.on_delete_marked = on_delete_marked
        self.on_publish_clip = on_publish_clip
        self.marked_for_deletion: Dict[str, ctk.BooleanVar] = {}
        self.current_filename: Optional[str] = None
        self.current_video_path: Optional[str] = None
        self.current_companion_path: Optional[str] = None
        self.current_reasoning: Optional[str] = None

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(3, weight=1)

        self.gallery_title = ctk.CTkLabel(self, text="Clip Gallery & Reasoning", font=ctk.CTkFont(size=28, weight="bold"))
        self.gallery_title.grid(row=0, column=0, columnspan=2, padx=30, pady=(30, 10), sticky="w")
        
        self.sort_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.sort_frame.grid(row=1, column=0, padx=(30, 10), pady=(0, 5), sticky="ew")
        
        self.sort_label = ctk.CTkLabel(self.sort_frame, text="Sort by:", font=ctk.CTkFont(size=12))
        self.sort_label.pack(side="left", padx=(0, 5))
        
        self.sort_menu = ctk.CTkOptionMenu(
            self.sort_frame, values=["Date (Newest)", "Date (Oldest)", "Virality (High)", "Virality (Low)"], 
            command=lambda _: self._trigger_filter_changed()
        )
        self.sort_menu.pack(side="left", fill="x", expand=True)
        self.sort_menu.set("Date (Newest)")

        # --- Filters ---
        self.filter_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.filter_frame.grid(row=2, column=0, padx=(30, 10), pady=(0, 5), sticky="ew")
        
        ctk.CTkLabel(self.filter_frame, text="Type:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 5))
        self.type_filter_menu = ctk.CTkOptionMenu(
            self.filter_frame, values=["All", "Horizontal", "Vertical"], width=100,
            command=lambda _: self._trigger_filter_changed()
        )
        self.type_filter_menu.pack(side="left", padx=(0, 10))
        self.type_filter_menu.set("All")
        
        ctk.CTkLabel(self.filter_frame, text="Min Score:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 5))
        self.score_filter_menu = ctk.CTkOptionMenu(
            self.filter_frame, values=["All", "3+", "5+", "7+", "8+", "9+"], width=80,
            command=lambda _: self._trigger_filter_changed()
        )
        self.score_filter_menu.pack(side="left")
        self.score_filter_menu.set("All")

        self.clip_listbox = ctk.CTkScrollableFrame(self, width=300, corner_radius=15)
        self.clip_listbox.grid(row=3, column=0, padx=(30, 10), pady=10, sticky="nsew")

        self.gallery_actions_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.gallery_actions_frame.grid(row=4, column=0, padx=(30, 10), pady=(0, 10), sticky="ew")

        self.select_all_var = ctk.BooleanVar(value=False)
        self.select_all_checkbox = ctk.CTkCheckBox(
            self.gallery_actions_frame, text="Select All", variable=self.select_all_var,
            command=self.toggle_select_all
        )
        self.select_all_checkbox.pack(side="left", padx=(0, 10))

        self.refresh_gallery_btn = ctk.CTkButton(
            self.gallery_actions_frame, text="🔄 Refresh List",
            command=self._trigger_refresh
        )
        self.refresh_gallery_btn.pack(side="right", fill="x", expand=True)

        self.delete_marked_btn = ctk.CTkButton(
            self, text="🗑️ Delete Marked Clips", fg_color="#c0392b", hover_color="#922b21",
            command=self._trigger_delete_marked
        )
        self.delete_marked_btn.grid(row=5, column=0, padx=(30, 10), pady=(0, 20), sticky="ew")

        self.details_card = ctk.CTkFrame(self, corner_radius=15)
        self.details_card.grid(row=1, column=1, rowspan=5, padx=(10, 30), pady=(10, 20), sticky="nsew")
        self.details_card.grid_columnconfigure(0, weight=1)

        self.detail_title = ctk.CTkLabel(self.details_card, text="Select a clip to view details", font=ctk.CTkFont(size=20, weight="bold"))
        self.detail_title.grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")

        self.detail_score = ctk.CTkLabel(self.details_card, text="Score: --/10", font=ctk.CTkFont(size=16), text_color="#2ecc71")
        self.detail_score.grid(row=1, column=0, padx=20, pady=(0, 5), sticky="w")

        # Integrated in-app Video Preview Player (Synchronized 16:9 vs 9:16)
        self.video_preview = VideoPreviewWidget(self.details_card)
        self.video_preview.grid(row=2, column=0, padx=15, pady=5, sticky="nsew")
        self.details_card.grid_rowconfigure(2, weight=3)

        self.detail_reasoning = ctk.CTkTextbox(self.details_card, font=ctk.CTkFont(size=13), height=85, wrap="word", fg_color="#181818")
        self.detail_reasoning.grid(row=3, column=0, padx=20, pady=(5, 10), sticky="nsew")
        self.details_card.grid_rowconfigure(3, weight=1)

        # Retain detail_thumbnail for test/fallback compatibility
        self.detail_thumbnail = ctk.CTkLabel(self.details_card, text="")

        self.gallery_btns_frame = ctk.CTkFrame(self.details_card, fg_color="transparent")
        self.gallery_btns_frame.grid(row=4, column=0, padx=20, pady=(5, 15), sticky="ew")
        self.gallery_btns_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.play_clip_btn = ctk.CTkButton(self.gallery_btns_frame, text="▶️ Play Clip", height=42, font=ctk.CTkFont(weight="bold"), state="disabled")
        self.play_clip_btn.grid(row=0, column=0, padx=(0, 4), sticky="ew")

        self.open_folder_btn = ctk.CTkButton(self.gallery_btns_frame, text="📁 Open Folder", height=42, font=ctk.CTkFont(weight="bold"), state="disabled", fg_color="#2b2b2b", hover_color="#3b3b3b")
        self.open_folder_btn.grid(row=0, column=1, padx=4, sticky="ew")

        self.publish_clip_btn = ctk.CTkButton(
            self.gallery_btns_frame, text="🚀 Publish to Social", height=42,
            font=ctk.CTkFont(weight="bold"), state="disabled",
            fg_color="#8e44ad", hover_color="#732d91",
            command=self._trigger_publish_clip
        )
        self.publish_clip_btn.grid(row=0, column=2, padx=(4, 0), sticky="ew")

    def _trigger_filter_changed(self, *args) -> None:
        if self.on_filter_changed:
            self.on_filter_changed()
        else:
            fn = getattr(self.master, "populate_gallery", None)
            if callable(fn):
                fn()

    def _trigger_refresh(self) -> None:
        if self.on_refresh:
            self.on_refresh()
        else:
            fn = getattr(self.master, "refresh_gallery_action", None)
            if callable(fn):
                fn()

    def _trigger_delete_marked(self) -> None:
        if self.on_delete_marked:
            self.on_delete_marked()
        else:
            fn = getattr(self.master, "confirm_delete_marked", None)
            if callable(fn):
                fn()

    # --- Public Encapsulated API ---

    def toggle_select_all(self) -> None:
        """Toggles all clip row checkboxes to match Select All state."""
        select_state = self.select_all_var.get()
        for var in self.marked_for_deletion.values():
            var.set(select_state)

    def get_filter_settings(self) -> Dict[str, str]:
        """Returns the current sort and filter options."""
        return {
            "sort_mode": self.sort_menu.get(),
            "type_filter": self.type_filter_menu.get(),
            "score_filter": self.score_filter_menu.get(),
        }

    def render_clips(self, clip_data: List[Dict[str, Any]], on_click_clip: Callable[[str], None]) -> None:
        """Renders clip rows with checkboxes and selection buttons."""
        for widget in self.clip_listbox.winfo_children():
            widget.destroy()

        self.marked_for_deletion.clear()
        self.select_all_var.set(False)

        if not clip_data:
            empty_label = ctk.CTkLabel(
                self.clip_listbox, text="No clips found matching current filters.",
                font=ctk.CTkFont(slant="italic"), text_color="gray"
            )
            empty_label.pack(pady=20)
            return

        for item in clip_data:
            file = item["filename"]
            row_frame = ctk.CTkFrame(self.clip_listbox, fg_color="transparent")
            row_frame.pack(fill="x", pady=2, padx=5)

            var = ctk.BooleanVar(value=False)
            self.marked_for_deletion[file] = var

            checkbox = ctk.CTkCheckBox(row_frame, text="", variable=var, width=20)
            checkbox.pack(side="left", padx=(0, 5))

            btn = ctk.CTkButton(
                row_frame,
                text=file,
                fg_color="#2b2b2b",
                hover_color="#3b3b3b",
                anchor="w",
                command=lambda f=file: on_click_clip(f)
            )
            btn.pack(side="left", fill="x", expand=True)

    def get_marked_files(self) -> List[str]:
        """Returns the list of filenames currently checked for deletion."""
        return [f for f, var in self.marked_for_deletion.items() if var.get()]

    def display_clip_details(
        self,
        filename: str,
        score_text: str,
        reasoning: str,
        thumbnail_img: Any = None,
        thumbnail_image: Any = None,
        play_command: Optional[Callable] = None,
        on_play: Optional[Callable] = None,
        open_folder_command: Optional[Callable] = None,
        on_open_folder: Optional[Callable] = None,
        video_path: Optional[str] = None,
        companion_path: Optional[str] = None,
        **kwargs
    ) -> None:
        """Populates the detail inspection card and loads the synchronized video preview."""
        self.detail_title.configure(text=filename)
        self.detail_score.configure(text=score_text)

        self.detail_reasoning.configure(state="normal")
        self.detail_reasoning.delete("1.0", "end")
        self.detail_reasoning.insert("1.0", reasoning)
        self.detail_reasoning.configure(state="disabled")

        thumb = thumbnail_image if thumbnail_image is not None else thumbnail_img
        if hasattr(self, 'detail_thumbnail'):
            try:
                self.detail_thumbnail.configure(image=thumb)
            except Exception:
                pass

        # Load video into preview player
        if video_path and os.path.exists(video_path):
            if hasattr(self, 'video_preview'):
                self.video_preview.load_video(video_path, companion_path)

        play_cmd = on_play or play_command
        if play_cmd:
            self.play_clip_btn.configure(state="normal", command=play_cmd)
        elif hasattr(self, 'video_preview') and self.video_preview.controller:
            self.play_clip_btn.configure(state="normal", command=self.video_preview.toggle_play)
        else:
            self.play_clip_btn.configure(state="disabled")

        self.current_filename = filename
        self.current_video_path = video_path
        self.current_companion_path = companion_path
        self.current_reasoning = reasoning

        open_cmd = on_open_folder or open_folder_command
        if open_cmd:
            self.open_folder_btn.configure(state="normal", command=open_cmd)
        else:
            self.open_folder_btn.configure(state="disabled")

        if hasattr(self, 'publish_clip_btn'):
            if video_path and os.path.exists(video_path):
                self.publish_clip_btn.configure(state="normal")
            else:
                self.publish_clip_btn.configure(state="disabled")

    def _trigger_publish_clip(self) -> None:
        callback = getattr(self, "on_publish_clip", None)
        if callable(callback):
            callback(
                getattr(self, "current_video_path", None),
                getattr(self, "current_companion_path", None),
                getattr(self, "current_filename", None),
                getattr(self, "current_reasoning", None)
            )
        else:
            from .publish_dialog import PublishDialog
            video_path = getattr(self, "current_video_path", None)
            if video_path:
                clip_info = {
                    "video_path": video_path,
                    "companion_path": getattr(self, "current_companion_path", None),
                    "filename": getattr(self, "current_filename", "Highlight Clip"),
                    "reasoning": getattr(self, "current_reasoning", "")
                }
                config = getattr(self.master, "config", {})
                PublishDialog(
                    master=self.winfo_toplevel(),
                    clip_info=clip_info,
                    config=config
                )

    def clear_clip_details(self) -> None:
        """Resets the detail inspection card to placeholder state."""
        self.current_filename = None
        self.current_video_path = None
        self.current_companion_path = None
        self.current_reasoning = None

        self.detail_title.configure(text="Select a clip to view details")
        self.detail_score.configure(text="Score: --/10")

        self.detail_reasoning.configure(state="normal")
        self.detail_reasoning.delete("1.0", "end")
        self.detail_reasoning.configure(state="disabled")

        if hasattr(self, 'video_preview'):
            self.video_preview.close()

        if hasattr(self, 'detail_thumbnail'):
            try:
                self.detail_thumbnail.configure(image=None)
            except Exception:
                pass

        self.play_clip_btn.configure(state="disabled")
        self.open_folder_btn.configure(state="disabled")
        if hasattr(self, 'publish_clip_btn'):
            self.publish_clip_btn.configure(state="disabled")

    def show_refreshed_feedback(self) -> None:
        """Provides brief visual feedback on the Refresh button."""
        original_color = self.refresh_gallery_btn.cget("fg_color")
        self.refresh_gallery_btn.configure(text="✅ Refreshed!", fg_color="#2ecc71")
        self.after(2000, lambda: self.refresh_gallery_btn.configure(text="🔄 Refresh List", fg_color=original_color))
