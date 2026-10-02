import os
import subprocess
from typing import Optional
import customtkinter as ctk  # type: ignore
from PIL import Image
from video_player import DualVideoSyncController


class VideoPreviewWidget(ctk.CTkFrame):
    """
    In-app video preview player featuring synchronized side-by-side comparison
    (16:9 Horizontal vs. 9:16 Vertical), frame-accurate scrubbing, and playback controls.
    """

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        self.controller: Optional[DualVideoSyncController] = None
        self.primary_path: Optional[str] = None
        self.companion_path: Optional[str] = None
        self.view_mode: str = "side_by_side"  # "horizontal", "vertical", "side_by_side"
        self._is_scrubbing: bool = False
        self._render_pending: bool = False
        self._cached_primary_img: Optional[Image.Image] = None
        self._cached_companion_img: Optional[Image.Image] = None

        self.grid_columnconfigure(0, weight=1)

        # --- Viewport Container (Dark Cinema Surface) ---
        self.viewport_container = ctk.CTkFrame(self, fg_color="#121212", corner_radius=12)
        self.viewport_container.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="nsew")
        self.grid_rowconfigure(0, weight=1)
        self.viewport_container.grid_columnconfigure((0, 1), weight=1)
        self.viewport_container.grid_rowconfigure(1, weight=1)

        # Viewport Header Badges
        self.badge_left = ctk.CTkLabel(
            self.viewport_container, text="16:9 Horizontal Source",
            font=ctk.CTkFont(size=11, weight="bold"), text_color="#3a7ebf"
        )
        self.badge_left.grid(row=0, column=0, padx=10, pady=(8, 2), sticky="w")

        self.badge_right = ctk.CTkLabel(
            self.viewport_container, text="9:16 Vertical Cut",
            font=ctk.CTkFont(size=11, weight="bold"), text_color="#2ecc71"
        )
        self.badge_right.grid(row=0, column=1, padx=10, pady=(8, 2), sticky="w")

        # Viewport Canvas Labels
        self.display_left = ctk.CTkLabel(self.viewport_container, text="No video loaded", text_color="gray")
        self.display_left.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

        self.display_right = ctk.CTkLabel(self.viewport_container, text="No companion cut", text_color="gray")
        self.display_right.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")

        # --- Scrubber Timeline ---
        self.scrub_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.scrub_frame.grid(row=1, column=0, padx=10, pady=(5, 0), sticky="ew")
        self.scrub_frame.grid_columnconfigure(0, weight=1)

        self.timeline_slider = ctk.CTkSlider(
            self.scrub_frame, from_=0.0, to=100.0, height=18,
            command=self._on_slider_moved
        )
        self.timeline_slider.set(0.0)
        self.timeline_slider.grid(row=0, column=0, sticky="ew")
        self.timeline_slider.bind("<Button-1>", self._on_slider_press)
        self.timeline_slider.bind("<ButtonRelease-1>", self._on_slider_release)

        # --- Playback Toolbar Controls ---
        self.controls_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.controls_frame.grid(row=2, column=0, padx=10, pady=(5, 10), sticky="ew")
        self.controls_frame.grid_columnconfigure(3, weight=1)

        # Play / Pause button
        self.play_btn = ctk.CTkButton(
            self.controls_frame, text="▶ Play", width=75, height=32,
            font=ctk.CTkFont(weight="bold"), command=self.toggle_play
        )
        self.play_btn.grid(row=0, column=0, padx=(0, 6))

        # Step -1s button
        self.step_back_btn = ctk.CTkButton(
            self.controls_frame, text="◀ 1s", width=50, height=32,
            fg_color="#2b2b2b", hover_color="#3b3b3b", command=lambda: self.step(-1.0)
        )
        self.step_back_btn.grid(row=0, column=1, padx=(0, 6))

        # Step +1s button
        self.step_fwd_btn = ctk.CTkButton(
            self.controls_frame, text="1s ▶", width=50, height=32,
            fg_color="#2b2b2b", hover_color="#3b3b3b", command=lambda: self.step(1.0)
        )
        self.step_fwd_btn.grid(row=0, column=2, padx=(0, 10))

        # Timecode Label
        self.timecode_label = ctk.CTkLabel(
            self.controls_frame, text="00:00.0 / 00:00.0",
            font=ctk.CTkFont(family="Consolas", size=12)
        )
        self.timecode_label.grid(row=0, column=3, sticky="w")

        # View Mode Segmented Selector
        self.mode_selector = ctk.CTkSegmentedButton(
            self.controls_frame,
            values=["Side-by-Side", "16:9 Only", "9:16 Only"],
            command=self._on_mode_selected
        )
        self.mode_selector.set("Side-by-Side")
        self.mode_selector.grid(row=0, column=4, padx=(10, 8))

        # Loop Toggle Switch
        self.loop_var = ctk.BooleanVar(value=True)
        self.loop_switch = ctk.CTkSwitch(
            self.controls_frame, text="Loop", variable=self.loop_var,
            width=50, command=self._on_loop_toggle
        )
        self.loop_switch.grid(row=0, column=5, padx=(0, 6))

        # External Player Launch Button
        self.ext_player_btn = ctk.CTkButton(
            self.controls_frame, text="↗ External", width=85, height=32,
            fg_color="#24292e", hover_color="#2f363d", command=self._open_external_player
        )
        self.ext_player_btn.grid(row=0, column=6)

    def load_video(self, primary_path: str, companion_path: Optional[str] = None) -> bool:
        """
        Loads the primary video and optional companion video into the player.
        Initializes viewports, slider bounds, and displays initial frame at t=0.
        """
        self.close()

        if not os.path.exists(primary_path):
            self.display_left.configure(text="Video file not found", image=None)
            self.display_right.configure(text="", image=None)
            return False

        self.primary_path = primary_path
        self.companion_path = companion_path if (companion_path and os.path.exists(companion_path)) else None

        try:
            self.controller = DualVideoSyncController(
                primary_path=self.primary_path,
                companion_path=self.companion_path,
                on_frame=self._on_frame_decoded,
                on_state_change=self._on_playback_state_changed
            )
            self.controller.loop = self.loop_var.get()

            # Configure slider bounds
            duration = self.controller.duration
            self.timeline_slider.configure(from_=0.0, to=duration if duration > 0 else 1.0)
            self.timeline_slider.set(0.0)

            # Configure view mode selector based on companion availability
            if self.companion_path:
                self.mode_selector.configure(state="normal")
                self.mode_selector.set("Side-by-Side")
                self.view_mode = "side_by_side"
            else:
                self.mode_selector.configure(state="normal")
                # Detect whether primary is 16:9 or 9:16
                is_vertical = self.controller.primary_decoder and self.controller.primary_decoder.aspect_ratio < 1.0
                initial_mode = "9:16 Only" if is_vertical else "16:9 Only"
                self.mode_selector.set(initial_mode)
                self.view_mode = "vertical" if is_vertical else "horizontal"

            self._apply_view_layout()

            # Seek to first frame and render
            prim_img, comp_img = self.controller.seek(0.0)
            self._update_viewports(0.0, prim_img, comp_img)
            self.play_btn.configure(state="normal", text="▶ Play")
            return True

        except Exception as e:
            self.display_left.configure(text=f"Error loading preview: {e}", image=None)
            self.display_right.configure(text="", image=None)
            return False

    def toggle_play(self):
        """Toggles between play and pause states."""
        if not self.controller:
            return
        self.controller.toggle_play()

    def play(self):
        if self.controller:
            self.controller.play()

    def pause(self):
        if self.controller:
            self.controller.pause()

    def stop(self):
        if self.controller:
            self.controller.stop()

    def step(self, seconds: float):
        """Steps forward or backward by the specified duration."""
        if not self.controller:
            return
        self.controller.step(seconds)

    def _on_playback_state_changed(self, state: str):
        def update():
            if state == "playing":
                self.play_btn.configure(text="⏸ Pause", fg_color="#e67e22", hover_color="#d35400")
            else:
                self.play_btn.configure(text="▶ Play", fg_color=["#3a7ebf", "#1f538d"], hover_color=["#326da3", "#1a4675"])
        self.after(0, update)

    def _on_loop_toggle(self):
        if self.controller:
            self.controller.loop = self.loop_var.get()

    def _on_slider_press(self, event=None):
        self._is_scrubbing = True
        if self.controller and self.controller.is_playing:
            self.controller.pause()

    def _on_slider_release(self, event=None):
        self._is_scrubbing = False
        if self.controller:
            self.controller.seek(self.timeline_slider.get())

    def _on_slider_moved(self, value: float):
        if self._is_scrubbing and self.controller:
            self.controller.seek(value)

    def _on_mode_selected(self, mode: str):
        if mode == "Side-by-Side":
            self.view_mode = "side_by_side"
        elif mode == "16:9 Only":
            self.view_mode = "horizontal"
        elif mode == "9:16 Only":
            self.view_mode = "vertical"

        self._apply_view_layout()
        if self._cached_primary_img:
            self._render_viewports(self.controller.current_time if self.controller else 0.0)

    def _apply_view_layout(self):
        """Configures grid layout and badge visibility for the active view mode."""
        if self.view_mode == "side_by_side":
            self.viewport_container.grid_columnconfigure(0, weight=3)
            self.viewport_container.grid_columnconfigure(1, weight=2)
            self.badge_left.grid(row=0, column=0, padx=10, pady=(8, 2), sticky="w")
            self.badge_right.grid(row=0, column=1, padx=10, pady=(8, 2), sticky="w")
            self.display_left.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
            self.display_right.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")
        elif self.view_mode == "horizontal":
            self.viewport_container.grid_columnconfigure(0, weight=1)
            self.viewport_container.grid_columnconfigure(1, weight=0)
            self.badge_left.grid(row=0, column=0, padx=10, pady=(8, 2), sticky="w")
            self.badge_right.grid_forget()
            self.display_left.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")
            self.display_right.grid_forget()
        elif self.view_mode == "vertical":
            self.viewport_container.grid_columnconfigure(0, weight=1)
            self.viewport_container.grid_columnconfigure(1, weight=0)
            self.badge_left.grid_forget()
            self.badge_right.grid(row=0, column=0, padx=10, pady=(8, 2), sticky="w")
            self.display_left.grid_forget()
            self.display_right.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")

    def _on_frame_decoded(self, time_sec: float, primary_img: Image.Image, companion_img: Optional[Image.Image]):
        if self._render_pending:
            return  # Drop frame if UI render is still processing
        self._render_pending = True
        self.after(0, self._update_viewports, time_sec, primary_img, companion_img)

    def _update_viewports(self, time_sec: float, primary_img: Optional[Image.Image], companion_img: Optional[Image.Image]):
        try:
            self._cached_primary_img = primary_img
            self._cached_companion_img = companion_img
            self._render_viewports(time_sec)
        finally:
            self._render_pending = False

    def _render_viewports(self, time_sec: float):
        duration = self.controller.duration if self.controller else 0.0

        # Update Timecode readout
        cur_fmt = f"{int(time_sec // 60):02d}:{time_sec % 60:04.1f}"
        dur_fmt = f"{int(duration // 60):02d}:{duration % 60:04.1f}"
        self.timecode_label.configure(text=f"{cur_fmt} / {dur_fmt}")

        if not self._is_scrubbing:
            self.timeline_slider.set(time_sec)

        # Scale and render left viewport (16:9 Primary)
        if self._cached_primary_img and self.view_mode in ("side_by_side", "horizontal"):
            pw, ph = self._cached_primary_img.size
            if self.view_mode == "side_by_side":
                max_w, max_h = 360, 202
            else:
                max_w, max_h = 560, 315

            scale = min(max_w / pw, max_h / ph)
            nw, nh = max(1, int(pw * scale)), max(1, int(ph * scale))
            p_resized = self._cached_primary_img.resize((nw, nh), Image.Resampling.BILINEAR)
            ctk_p = ctk.CTkImage(light_image=p_resized, dark_image=p_resized, size=(nw, nh))
            self.display_left.configure(image=ctk_p, text="")

        # Scale and render right viewport (9:16 Companion)
        if self.view_mode in ("side_by_side", "vertical"):
            target_img = self._cached_companion_img or (self._cached_primary_img if self.view_mode == "vertical" else None)
            if target_img:
                cw, ch = target_img.size
                if self.view_mode == "side_by_side":
                    max_w, max_h = 135, 240
                else:
                    max_w, max_h = 225, 400

                scale = min(max_w / cw, max_h / ch)
                nw, nh = max(1, int(cw * scale)), max(1, int(ch * scale))
                c_resized = target_img.resize((nw, nh), Image.Resampling.BILINEAR)
                ctk_c = ctk.CTkImage(light_image=c_resized, dark_image=c_resized, size=(nw, nh))
                self.display_right.configure(image=ctk_c, text="")
            else:
                self.display_right.configure(image=None, text="No 9:16 companion cut found")

    def _open_external_player(self):
        """Launches the primary clip in the OS default video player."""
        target = self.primary_path
        if target and os.path.exists(target):
            if hasattr(os, 'startfile'):
                os.startfile(os.path.abspath(target))  # type: ignore
            else:
                subprocess.run(['xdg-open', os.path.abspath(target)])

    def close(self):
        """Releases the playback controller and clears active frame references."""
        if self.controller:
            self.controller.close()
            self.controller = None
        self._cached_primary_img = None
        self._cached_companion_img = None
        self.play_btn.configure(text="▶ Play", fg_color=["#3a7ebf", "#1f538d"])
