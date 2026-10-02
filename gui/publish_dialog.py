import os
import threading
import customtkinter as ctk # type: ignore
from typing import Optional, Callable, Dict, Any
from social_publisher import SocialPlatform, PublishPrivacy, PublishPayload, get_social_publish_manager

class PublishDialog(ctk.CTkToplevel):
    """
    Direct Social Media Publishing Modal.
    Allows creators to select target format, platform (YouTube Shorts, TikTok, Instagram Reels),
    customize title/caption, set privacy, and publish directly from the Clip Gallery.
    """

    def __init__(
        self,
        master: ctk.CTk,
        clip_info: Dict[str, Any],
        config: Dict[str, Any],
        on_publish_complete: Optional[Callable[[str, str], None]] = None,
        **kwargs
    ) -> None:
        super().__init__(master, **kwargs)
        self.title("🚀 Publish Clip to Social Media")
        self.geometry("560x660")
        self.resizable(False, False)
        
        self.clip_info = clip_info
        self.config = config
        self.on_publish_complete = on_publish_complete
        self.publish_manager = get_social_publish_manager()

        # Lift window
        self.lift()
        self.attributes("-topmost", True)

        self.grid_columnconfigure(0, weight=1)

        # Header
        self.header_label = ctk.CTkLabel(
            self,
            text="🚀 Publish to Social Media",
            font=ctk.CTkFont(size=22, weight="bold")
        )
        self.header_label.pack(pady=(20, 5), padx=25, anchor="w")

        self.sub_label = ctk.CTkLabel(
            self,
            text="Export directly to YouTube Shorts, TikTok, or Instagram Reels.",
            font=ctk.CTkFont(size=12),
            text_color="#a0a0a0"
        )
        self.sub_label.pack(pady=(0, 15), padx=25, anchor="w")

        # Container Card
        self.form_card = ctk.CTkFrame(self, corner_radius=12)
        self.form_card.pack(fill="both", expand=True, padx=25, pady=(0, 15))
        self.form_card.grid_columnconfigure(1, weight=1)

        # Row 0: Target Video File
        ctk.CTkLabel(self.form_card, text="Video Source:", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, padx=15, pady=10, sticky="e"
        )
        self._init_video_source_options()

        # Row 1: Target Social Platform
        ctk.CTkLabel(self.form_card, text="Platform:", font=ctk.CTkFont(weight="bold")).grid(
            row=1, column=0, padx=15, pady=10, sticky="e"
        )
        self.platform_menu = ctk.CTkSegmentedButton(
            self.form_card,
            values=[SocialPlatform.YOUTUBE_SHORTS.value, SocialPlatform.TIKTOK.value, SocialPlatform.INSTAGRAM_REELS.value],
            command=self._on_platform_changed
        )
        self.platform_menu.set(SocialPlatform.YOUTUBE_SHORTS.value)
        self.platform_menu.grid(row=1, column=1, padx=(0, 15), pady=10, sticky="ew")

        # Row 2: Title
        ctk.CTkLabel(self.form_card, text="Title / Hook:", font=ctk.CTkFont(weight="bold")).grid(
            row=2, column=0, padx=15, pady=10, sticky="e"
        )
        self.title_entry = ctk.CTkEntry(self.form_card, height=36)
        self.title_entry.grid(row=2, column=1, padx=(0, 15), pady=10, sticky="ew")

        # Pre-fill title
        raw_name = clip_info.get("filename", "")
        clean_title = raw_name.replace(".mp4", "").replace("_vertical", "").replace("_", " ").strip()
        self.title_entry.insert(0, f"{clean_title[:80]} #Shorts")

        # Row 3: Caption / Description
        ctk.CTkLabel(self.form_card, text="Caption / Tags:", font=ctk.CTkFont(weight="bold")).grid(
            row=3, column=0, padx=15, pady=10, sticky="ne"
        )
        self.desc_box = ctk.CTkTextbox(self.form_card, height=110, wrap="word", font=ctk.CTkFont(size=12))
        self.desc_box.grid(row=3, column=1, padx=(0, 15), pady=10, sticky="ew")
        
        # Pre-fill reasoning + tags
        reasoning = clip_info.get("reasoning", "")
        default_caption = f"{reasoning}\n\n#Shorts #Gaming #Highlights #Viral" if reasoning else "#Shorts #Gaming #Highlights"
        self.desc_box.insert("1.0", default_caption)

        # Row 4: Privacy
        ctk.CTkLabel(self.form_card, text="Privacy:", font=ctk.CTkFont(weight="bold")).grid(
            row=4, column=0, padx=15, pady=10, sticky="e"
        )
        self.privacy_menu = ctk.CTkOptionMenu(
            self.form_card,
            values=[PublishPrivacy.PUBLIC.value, PublishPrivacy.UNLISTED.value, PublishPrivacy.PRIVATE.value],
            height=32,
            width=140
        )
        self.privacy_menu.set(PublishPrivacy.PUBLIC.value)
        self.privacy_menu.grid(row=4, column=1, padx=(0, 15), pady=10, sticky="w")

        # Status & Progress Area
        self.status_label = ctk.CTkLabel(
            self.form_card,
            text="Ready to publish.",
            font=ctk.CTkFont(size=12),
            text_color="#a0a0a0"
        )
        self.status_label.grid(row=5, column=0, columnspan=2, padx=15, pady=(15, 4), sticky="w")

        self.progress_bar = ctk.CTkProgressBar(self.form_card, height=8)
        self.progress_bar.grid(row=6, column=0, columnspan=2, padx=15, pady=(0, 15), sticky="ew")
        self.progress_bar.set(0)

        # Action Buttons
        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.pack(fill="x", padx=25, pady=(0, 20))
        self.btn_frame.grid_columnconfigure((0, 1), weight=1)

        self.cancel_btn = ctk.CTkButton(
            self.btn_frame,
            text="Close",
            height=40,
            fg_color="#34495e",
            hover_color="#2c3e50",
            command=self.destroy
        )
        self.cancel_btn.grid(row=0, column=0, padx=(0, 8), sticky="ew")

        self.publish_btn = ctk.CTkButton(
            self.btn_frame,
            text="🚀 Publish Now",
            height=40,
            font=ctk.CTkFont(weight="bold"),
            fg_color="#e67e22",
            hover_color="#d35400",
            command=self._start_publish_thread
        )
        self.publish_btn.grid(row=0, column=1, padx=(8, 0), sticky="ew")

    def _init_video_source_options(self) -> None:
        """Determines best cut (vertical vs horizontal) and creates source dropdown."""
        main_path = self.clip_info.get("video_path", "")
        companion_path = self.clip_info.get("companion_path")

        options = []
        path_map = {}

        if main_path and os.path.exists(main_path):
            if "_vertical.mp4" in main_path:
                label = "📱 9:16 Vertical Cut (Shorts / Reels / TikTok)"
                options.append(label)
                path_map[label] = main_path
            else:
                label = "🖥️ 16:9 Horizontal Cut"
                options.append(label)
                path_map[label] = main_path

        if companion_path and os.path.exists(companion_path):
            if "_vertical.mp4" in companion_path:
                label = "📱 9:16 Vertical Cut (Shorts / Reels / TikTok)"
                options.insert(0, label)  # Prefer vertical
                path_map[label] = companion_path
            else:
                label = "🖥️ 16:9 Horizontal Cut"
                options.append(label)
                path_map[label] = companion_path

        if not options:
            options = ["No video selected"]
            path_map["No video selected"] = main_path

        self.path_map = path_map
        self.source_menu = ctk.CTkOptionMenu(self.form_card, values=options, height=32)
        self.source_menu.grid(row=0, column=1, padx=(0, 15), pady=10, sticky="ew")
        self.source_menu.set(options[0])

    def _on_platform_changed(self, platform_name: str) -> None:
        """Updates placeholder tips or tags based on platform selection."""
        current_title = self.title_entry.get()
        if platform_name == SocialPlatform.YOUTUBE_SHORTS.value:
            if "#shorts" not in current_title.lower():
                self.title_entry.delete(0, "end")
                self.title_entry.insert(0, f"{current_title.strip()} #Shorts")
        elif platform_name in (SocialPlatform.TIKTOK.value, SocialPlatform.INSTAGRAM_REELS.value):
            # TikTok/IG allow clean titles
            pass

    def _start_publish_thread(self) -> None:
        selected_label = self.source_menu.get()
        file_path = self.path_map.get(selected_label, "")

        if not file_path or not os.path.exists(file_path):
            self.status_label.configure(text="❌ Error: Selected video file not found on disk.", text_color="#e74c3c")
            return

        platform = self.platform_menu.get()
        title = self.title_entry.get().strip()
        description = self.desc_box.get("1.0", "end").strip()
        privacy = self.privacy_menu.get().strip()

        payload = PublishPayload(
            file_path=file_path,
            title=title,
            description=description,
            privacy=privacy,
            tags=["#Shorts", "#Gaming"] if "#Shorts" not in description else []
        )

        self.publish_btn.configure(state="disabled", text="Publishing...")
        self.status_label.configure(text=f"Connecting to {platform}...", text_color="#3498db")
        self.progress_bar.set(0.1)

        def worker():
            try:
                def progress_cb(fraction):
                    self.after(0, lambda: self.progress_bar.set(fraction))
                    self.after(0, lambda: self.status_label.configure(
                        text=f"Uploading to {platform}: {int(fraction * 100)}%",
                        text_color="#3498db"
                    ))

                result_url = self.publish_manager.publish_clip(
                    platform=platform,
                    payload=payload,
                    config=self.config,
                    progress_callback=progress_cb
                )

                def on_success():
                    self.progress_bar.set(1.0)
                    self.status_label.configure(text=f"✅ Published: {result_url}", text_color="#2ecc71")
                    self.publish_btn.configure(text="✅ Published!", state="disabled")
                    if self.on_publish_complete:
                        self.on_publish_complete(platform, result_url)

                self.after(0, on_success)

            except Exception as exc:
                def on_error():
                    self.status_label.configure(text=f"❌ Error: {str(exc)[:90]}", text_color="#e74c3c")
                    self.publish_btn.configure(text="Retry", state="normal")
                    self.progress_bar.set(0)

                self.after(0, on_error)

        threading.Thread(target=worker, daemon=True).start()
