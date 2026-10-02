import os
import customtkinter as ctk # type: ignore
from typing import Optional, Callable, List, Dict, Any

try:
    import windnd # type: ignore
    HAS_WINDND = True
except Exception:
    HAS_WINDND = False


class ManualFrame(ctk.CTkFrame):
    """
    Manual clipper view with integrated Multi-Video Queue Manager.
    Encapsulates input URL/files, interactive visual queue table, per-clip prompt profile
    assignment, orientation selection, processing controls, status indicators, and console logging.
    """

    def __init__(
        self,
        master: ctk.CTk,
        on_start_process: Optional[Callable] = None,
        on_cancel_process: Optional[Callable] = None,
        on_browse_files: Optional[Callable] = None,
        on_add_to_queue: Optional[Callable[[str], None]] = None,
        on_remove_queue_item: Optional[Callable[[str], None]] = None,
        on_clear_completed: Optional[Callable[[], None]] = None,
        on_clear_all: Optional[Callable[[], None]] = None,
        on_item_profile_changed: Optional[Callable[[str, str], None]] = None,
        on_item_orientation_changed: Optional[Callable[[str, str], None]] = None,
        on_files_dropped: Optional[Callable[[List[str]], None]] = None,
        **kwargs
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.on_start_process = on_start_process
        self.on_cancel_process = on_cancel_process
        self.on_browse_files = on_browse_files
        self.on_add_to_queue = on_add_to_queue
        self.on_remove_queue_item = on_remove_queue_item
        self.on_clear_completed = on_clear_completed
        self.on_clear_all = on_clear_all
        self.on_item_profile_changed = on_item_profile_changed
        self.on_item_orientation_changed = on_item_orientation_changed
        self.on_files_dropped = on_files_dropped

        self.available_profiles: List[str] = ["Omni-Genre Broad Net"]
        self.queue_items_cache: List[Any] = []

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(5, weight=1)
        
        # --- Top Title ---
        self.manual_title = ctk.CTkLabel(
            self,
            text="Manual Video Processor & Queue",
            font=ctk.CTkFont(size=26, weight="bold")
        )
        self.manual_title.grid(row=0, column=0, padx=30, pady=(20, 5), sticky="w")
        
        # --- Input Card ---
        self.input_card = ctk.CTkFrame(self, corner_radius=15)
        self.input_card.grid(row=1, column=0, padx=30, pady=8, sticky="ew")
        self.input_card.grid_columnconfigure(0, weight=1)

        self.url_input = ctk.CTkEntry(
            self.input_card,
            placeholder_text="Paste YouTube / Twitch URL or Drop Local Video File(s)...",
            height=42,
            border_width=0
        )
        self.url_input.grid(row=0, column=0, padx=(15, 8), pady=12, sticky="ew")
        self.url_input.bind("<Return>", lambda e: self._trigger_add_to_queue())

        self.add_queue_btn = ctk.CTkButton(
            self.input_card,
            text="➕ Add to Queue",
            height=42,
            width=120,
            text_color="#FFFFFF",
            fg_color="#2980b9",
            hover_color="#1f618d",
            font=ctk.CTkFont(weight="bold"),
            command=self._trigger_add_to_queue
        )
        self.add_queue_btn.grid(row=0, column=1, padx=(0, 6), pady=12)

        self.local_file_btn = ctk.CTkButton(
            self.input_card,
            text="📂 Browse Files",
            height=42,
            width=115,
            text_color="#FFFFFF",
            fg_color="#27ae60",
            hover_color="#1e8449",
            font=ctk.CTkFont(weight="bold"),
            command=self._trigger_browse_files
        )
        self.local_file_btn.grid(row=0, column=2, padx=(0, 6), pady=12)

        self.process_btn = ctk.CTkButton(
            self.input_card,
            text="▶ Process Queue",
            height=42,
            width=125,
            text_color="#FFFFFF",
            fg_color="#3a7ebf",
            hover_color="#1f538d",
            font=ctk.CTkFont(weight="bold"),
            command=self._trigger_start_process
        )
        self.process_btn.grid(row=0, column=3, padx=(0, 6), pady=12)

        self.cancel_btn = ctk.CTkButton(
            self.input_card,
            text="Cancel",
            height=42,
            width=85,
            text_color="#FFFFFF",
            fg_color="#c0392b",
            hover_color="#922b21",
            font=ctk.CTkFont(weight="bold"),
            state="disabled",
            command=self._trigger_cancel_process
        )
        self.cancel_btn.grid(row=0, column=4, padx=(0, 15), pady=12)

        # --- Interactive Queue Card ---
        self.queue_card = ctk.CTkFrame(self, corner_radius=15)
        self.queue_card.grid(row=2, column=0, padx=30, pady=6, sticky="ew")
        self.queue_card.grid_columnconfigure(1, weight=1)

        # Queue Header
        self.queue_header_label = ctk.CTkLabel(
            self.queue_card,
            text="📋 Video Queue",
            font=ctk.CTkFont(size=15, weight="bold")
        )
        self.queue_header_label.grid(row=0, column=0, padx=(18, 10), pady=(12, 6), sticky="w")

        self.queue_summary_label = ctk.CTkLabel(
            self.queue_card,
            text="0 queued • 0 processing • 0 done",
            font=ctk.CTkFont(size=12),
            text_color="#a0a0a0"
        )
        self.queue_summary_label.grid(row=0, column=1, padx=5, pady=(12, 6), sticky="w")

        self.clear_completed_btn = ctk.CTkButton(
            self.queue_card,
            text="🗑️ Clear Completed",
            height=28,
            width=120,
            font=ctk.CTkFont(size=11),
            fg_color="#34495e",
            hover_color="#2c3e50",
            command=self._trigger_clear_completed
        )
        self.clear_completed_btn.grid(row=0, column=2, padx=(0, 8), pady=(12, 6), sticky="e")

        self.clear_all_btn = ctk.CTkButton(
            self.queue_card,
            text="Clear All",
            height=28,
            width=80,
            font=ctk.CTkFont(size=11),
            fg_color="#7f8c8d",
            hover_color="#636e72",
            command=self._trigger_clear_all
        )
        self.clear_all_btn.grid(row=0, column=3, padx=(0, 18), pady=(12, 6), sticky="e")

        # Scrollable Queue List
        self.queue_scroll = ctk.CTkScrollableFrame(
            self.queue_card,
            height=165,
            corner_radius=8,
            fg_color="#181818"
        )
        self.queue_scroll.grid(row=1, column=0, columnspan=4, padx=15, pady=(0, 12), sticky="ew")
        self.queue_scroll.grid_columnconfigure(0, weight=1)

        self._render_empty_queue_placeholder()

        # --- Status & Progress Bar ---
        self.manual_status_label = ctk.CTkLabel(
            self,
            text="Status: Ready",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#a0a0a0"
        )
        self.manual_status_label.grid(row=3, column=0, padx=30, pady=(6, 0), sticky="w")
        
        self.manual_progress = ctk.CTkProgressBar(self, mode="indeterminate", height=8)
        self.manual_progress.grid(row=4, column=0, padx=30, pady=(3, 4), sticky="ew")
        self.manual_progress.set(0)

        # --- Console Output Card ---
        self.console_card = ctk.CTkFrame(self, corner_radius=15)
        self.console_card.grid(row=5, column=0, padx=30, pady=(4, 15), sticky="nsew")
        self.console_card.grid_columnconfigure(0, weight=1)
        self.console_card.grid_rowconfigure(0, weight=1)

        self.console_box = ctk.CTkTextbox(
            self.console_card,
            state="disabled",
            fg_color="#121212",
            font=ctk.CTkFont(family="Consolas", size=12)
        )
        self.console_box.grid(row=0, column=0, padx=15, pady=12, sticky="nsew")
        
        self.console_box.tag_config("error", foreground="#ff4d4d")
        self.console_box.tag_config("success", foreground="#2ecc71")
        self.console_box.tag_config("ai", foreground="#00d2ff")
        self.console_box.tag_config("ffmpeg", foreground="#f39c12")

        # Setup Drag and Drop if windnd is supported
        if HAS_WINDND:
            try:
                windnd.hook_dropfiles(self, func=self._on_drop_files)
            except Exception:
                pass

    # --- Drag & Drop Handler ---

    def _on_drop_files(self, files: List[Any]) -> None:
        """Handles Windows Explorer drag-and-drop file imports."""
        clean_paths: List[str] = []
        for f in files:
            if isinstance(f, bytes):
                try:
                    clean_paths.append(f.decode("utf-8"))
                except Exception:
                    try:
                        clean_paths.append(f.decode("mbcs"))
                    except Exception:
                        clean_paths.append(str(f))
            else:
                clean_paths.append(str(f))

        video_extensions = (".mp4", ".mkv", ".avi", ".mov", ".flv", ".webm", ".ts", ".m4v")
        valid_videos = [p for p in clean_paths if p.lower().endswith(video_extensions) and os.path.exists(p)]

        if valid_videos:
            self._trigger_files_dropped(valid_videos)

    # --- Trigger Callbacks ---

    def _trigger_start_process(self) -> None:
        if self.on_start_process:
            self.on_start_process()
        else:
            fn = getattr(self.master, "start_manual_process", None)
            if callable(fn):
                fn()

    def _trigger_cancel_process(self) -> None:
        if self.on_cancel_process:
            self.on_cancel_process()
        else:
            fn = getattr(self.master, "cancel_manual_process", None)
            if callable(fn):
                fn()

    def _trigger_browse_files(self) -> None:
        if self.on_browse_files:
            self.on_browse_files()
        else:
            fn = getattr(self.master, "browse_local_file", None)
            if callable(fn):
                fn()

    def _trigger_add_to_queue(self) -> None:
        url_text = self.get_url()
        if not url_text:
            return
        if self.on_add_to_queue:
            self.on_add_to_queue(url_text)
        else:
            fn = getattr(self.master, "add_manual_input_to_queue", None)
            if callable(fn):
                fn(url_text)
        self.set_url("")

    def _trigger_remove_item(self, item_id: str) -> None:
        if self.on_remove_queue_item:
            self.on_remove_queue_item(item_id)
        else:
            fn = getattr(self.master, "remove_queue_item", None)
            if callable(fn):
                fn(item_id)

    def _trigger_clear_completed(self) -> None:
        if self.on_clear_completed:
            self.on_clear_completed()
        else:
            fn = getattr(self.master, "clear_completed_queue", None)
            if callable(fn):
                fn()

    def _trigger_clear_all(self) -> None:
        if self.on_clear_all:
            self.on_clear_all()
        else:
            fn = getattr(self.master, "clear_all_queue", None)
            if callable(fn):
                fn()

    def _trigger_profile_changed(self, item_id: str, new_profile: str) -> None:
        if self.on_item_profile_changed:
            self.on_item_profile_changed(item_id, new_profile)
        else:
            fn = getattr(self.master, "on_queue_item_profile_changed", None)
            if callable(fn):
                fn(item_id, new_profile)

    def _trigger_orientation_changed(self, item_id: str, new_orientation: str) -> None:
        if self.on_item_orientation_changed:
            self.on_item_orientation_changed(item_id, new_orientation)
        else:
            fn = getattr(self.master, "on_queue_item_orientation_changed", None)
            if callable(fn):
                fn(item_id, new_orientation)

    def _trigger_files_dropped(self, files: List[str]) -> None:
        if self.on_files_dropped:
            self.on_files_dropped(files)
        else:
            fn = getattr(self.master, "on_files_dropped", None)
            if callable(fn):
                fn(files)
            else:
                for f in files:
                    if self.on_add_to_queue:
                        self.on_add_to_queue(f)

    # --- Queue Rendering ---

    def _render_empty_queue_placeholder(self) -> None:
        for widget in self.queue_scroll.winfo_children():
            widget.destroy()

        empty_label = ctk.CTkLabel(
            self.queue_scroll,
            text="Queue is empty. Drop video files here or paste URLs above to add them to the queue.",
            font=ctk.CTkFont(size=12, slant="italic"),
            text_color="#666666"
        )
        empty_label.pack(pady=45)

    def set_available_profiles(self, profiles: List[str]) -> None:
        """Updates available prompt profiles for queued item selectors."""
        if profiles:
            self.available_profiles = list(profiles)

    def render_queue(self, items: List[Any], summary: Optional[Dict[str, int]] = None) -> None:
        """
        Renders the entire queue list with per-clip prompt profile and orientation options.
        """
        self.queue_items_cache = list(items)

        # Update summary label
        if summary:
            queued = summary.get("queued", 0)
            processing = summary.get("processing", 0)
            done = summary.get("done", 0)
            failed = summary.get("failed", 0)
            self.queue_summary_label.configure(
                text=f"{queued} queued • {processing} active • {done} done" + (f" • {failed} failed" if failed else "")
            )

        if not items:
            self._render_empty_queue_placeholder()
            return

        for widget in self.queue_scroll.winfo_children():
            widget.destroy()

        orientation_options = [
            "Both (16:9 + 9:16)",
            "Horizontal Only (16:9)",
            "Vertical Only (9:16)"
        ]

        for idx, item in enumerate(items):
            item_id = getattr(item, "id", f"item_{idx}")
            display_name = getattr(item, "display_name", getattr(item, "source", "Video"))
            status = getattr(item, "status", "Queued")
            active_profile = getattr(item, "prompt_profile", self.available_profiles[0] if self.available_profiles else "Default")
            active_orientation = getattr(item, "target_orientation", "Both (16:9 + 9:16)")

            row_frame = ctk.CTkFrame(self.queue_scroll, fg_color="#222222", corner_radius=6, height=38)
            row_frame.pack(fill="x", pady=2, padx=2)
            row_frame.grid_columnconfigure(0, weight=1)

            # Left: Icon & Source Title
            icon = "🎬" if not display_name.startswith("http") else "🌐"
            title_text = f"{icon} {display_name}"
            if len(title_text) > 36:
                title_text = title_text[:33] + "..."

            title_lbl = ctk.CTkLabel(
                row_frame,
                text=title_text,
                font=ctk.CTkFont(size=12, weight="bold"),
                anchor="w",
                width=200
            )
            title_lbl.grid(row=0, column=0, padx=(10, 5), pady=4, sticky="w")

            # Per-Clip Prompt Profile Dropdown
            profile_menu = ctk.CTkOptionMenu(
                row_frame,
                values=self.available_profiles if self.available_profiles else [active_profile],
                width=160,
                height=26,
                font=ctk.CTkFont(size=11),
                command=lambda choice, i_id=item_id: self._trigger_profile_changed(i_id, choice)
            )
            profile_menu.set(active_profile if active_profile in self.available_profiles else (self.available_profiles[0] if self.available_profiles else active_profile))
            profile_menu.grid(row=0, column=1, padx=4, pady=4)

            # Native Aspect Ratio Indicator (Auto-Detected)
            aspect_badge = ctk.CTkLabel(
                row_frame,
                text="✨ Auto Aspect (Native)",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color="#2ecc71",
                fg_color="#14261a",
                corner_radius=5,
                width=150,
                height=26
            )
            aspect_badge.grid(row=0, column=2, padx=4, pady=4)

            # Status Badge Pill
            status_colors = {
                "Queued": ("#f39c12", "#332a00"),
                "Downloading": ("#3498db", "#0e2a47"),
                "Transcribing": ("#9b59b6", "#2b1138"),
                "Analyzing AI": ("#00d2ff", "#072b38"),
                "Cutting Clips": ("#e67e22", "#382207"),
                "Done": ("#2ecc71", "#0a2b16"),
                "Failed": ("#e74c3c", "#381010"),
                "Cancelled": ("#95a5a6", "#262626")
            }
            fg_text, bg_pill = status_colors.get(status, ("#a0a0a0", "#262626"))

            status_lbl = ctk.CTkLabel(
                row_frame,
                text=status,
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=fg_text,
                fg_color=bg_pill,
                corner_radius=5,
                width=85,
                height=24
            )
            status_lbl.grid(row=0, column=3, padx=6, pady=4)

            # Remove Item Button
            del_btn = ctk.CTkButton(
                row_frame,
                text="✕",
                width=24,
                height=24,
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color="#c0392b",
                hover_color="#922b21",
                command=lambda i_id=item_id: self._trigger_remove_item(i_id)
            )
            del_btn.grid(row=0, column=4, padx=(2, 8), pady=4)

    # --- Public Encapsulated API ---

    def get_url(self) -> str:
        """Returns the current input string."""
        return self.url_input.get().strip()

    def set_url(self, text: str) -> None:
        """Sets the input text field."""
        self.url_input.delete(0, "end")
        self.url_input.insert(0, text)

    def set_status(self, text: str, color: str = "#a0a0a0") -> None:
        """Updates the status indicator label."""
        self.manual_status_label.configure(text=text, text_color=color)

    def set_processing_state(self, is_processing: bool, status_text: Optional[str] = None) -> None:
        """Updates UI state to active processing or idle ready."""
        if is_processing:
            if hasattr(self, 'process_btn'):
                self.process_btn.configure(state="disabled")
            if hasattr(self, 'local_file_btn'):
                self.local_file_btn.configure(state="disabled")
            if hasattr(self, 'add_queue_btn'):
                self.add_queue_btn.configure(state="disabled")
            if hasattr(self, 'cancel_btn'):
                self.cancel_btn.configure(state="normal", text="Cancel")
            if hasattr(self, 'manual_progress'):
                self.manual_progress.start()
            if status_text:
                self.set_status(status_text, "#3a7ebf")
        else:
            if hasattr(self, 'process_btn'):
                self.process_btn.configure(state="normal")
            if hasattr(self, 'local_file_btn'):
                self.local_file_btn.configure(state="normal")
            if hasattr(self, 'add_queue_btn'):
                self.add_queue_btn.configure(state="normal")
            if hasattr(self, 'cancel_btn'):
                self.cancel_btn.configure(state="disabled", text="Cancel")
            if hasattr(self, 'manual_progress'):
                self.manual_progress.stop()
                self.manual_progress.set(0)
            if status_text:
                self.set_status(status_text, "#2ecc71")
            else:
                self.set_status("Status: Ready", "#a0a0a0")

    def append_log(self, text: str, tag: Optional[str] = None) -> None:
        """Appends a line of text to the console box."""
        self.console_box.configure(state="normal")
        if tag:
            self.console_box.insert("end", text + "\n", tag)
        else:
            self.console_box.insert("end", text + "\n")
        self.console_box.see("end")
        self.console_box.configure(state="disabled")

    def clear_log(self) -> None:
        """Clears console output."""
        self.console_box.configure(state="normal")
        self.console_box.delete("1.0", "end")
        self.console_box.configure(state="disabled")
