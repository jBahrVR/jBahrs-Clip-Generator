import customtkinter as ctk # type: ignore
from typing import Optional, Callable, List
from . import theme

class PromptFrame(ctk.CTkFrame):
    """
    AI Prompt Manager view.
    Encapsulates profile selection, prompt editing, and profile persistence controls.
    """

    def __init__(
        self,
        master: ctk.CTk,
        on_profile_change: Optional[Callable[[str], None]] = None,
        on_new_profile: Optional[Callable[[], None]] = None,
        on_save_prompt: Optional[Callable[[], None]] = None,
        on_delete_profile: Optional[Callable[[], None]] = None,
        **kwargs
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.on_profile_change = on_profile_change
        self.on_new_profile = on_new_profile
        self.on_save_prompt = on_save_prompt
        self.on_delete_profile = on_delete_profile

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        
        self.prompt_title = ctk.CTkLabel(
            self,
            text="Prompt Profiles & System Directives",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=theme.COLOR_TEXT_PRIMARY
        )
        self.prompt_title.grid(row=0, column=0, padx=30, pady=(20, 6), sticky="w")

        self.prompt_select_card = ctk.CTkFrame(
            self,
            corner_radius=theme.RADIUS_CARD,
            fg_color=theme.COLOR_CARD_BG,
            border_width=1,
            border_color=theme.COLOR_CARD_BORDER
        )
        self.prompt_select_card.grid(row=1, column=0, padx=30, pady=8, sticky="ew")
        
        ctk.CTkLabel(
            self.prompt_select_card,
            text="Active Profile:",
            font=ctk.CTkFont(weight="bold"),
            text_color=theme.COLOR_TEXT_MUTED
        ).pack(side="left", padx=(18, 10), pady=14)
        
        self.profile_dropdown = ctk.CTkOptionMenu(
            self.prompt_select_card,
            height=32,
            corner_radius=theme.RADIUS_BUTTON,
            fg_color=theme.COLOR_HOVER_MUTED,
            button_color=theme.COLOR_HOVER_MUTED,
            command=self._trigger_profile_change
        )
        self.profile_dropdown.pack(side="left", padx=6)

        self.new_profile_btn = ctk.CTkButton(
            self.prompt_select_card,
            text="New Profile",
            width=90,
            height=32,
            corner_radius=theme.RADIUS_BUTTON,
            fg_color=theme.COLOR_HOVER_MUTED,
            hover_color="#363a44",
            text_color=theme.COLOR_TEXT_PRIMARY,
            command=self._trigger_new_profile
        )
        self.new_profile_btn.pack(side="left", padx=6)

        self.delete_profile_btn = ctk.CTkButton(
            self.prompt_select_card,
            text="Delete Profile",
            height=32,
            corner_radius=theme.RADIUS_BUTTON,
            fg_color=theme.COLOR_DANGER,
            hover_color=theme.COLOR_DANGER_HOVER,
            text_color="#FFFFFF",
            font=ctk.CTkFont(weight="bold"),
            command=self._trigger_delete_profile
        )
        self.delete_profile_btn.pack(side="right", padx=18)

        self.prompt_editor_card = ctk.CTkFrame(
            self,
            corner_radius=theme.RADIUS_CARD,
            fg_color=theme.COLOR_CARD_BG,
            border_width=1,
            border_color=theme.COLOR_CARD_BORDER
        )
        self.prompt_editor_card.grid(row=2, column=0, padx=30, pady=(4, 15), sticky="nsew")
        self.prompt_editor_card.grid_columnconfigure(0, weight=1)
        self.prompt_editor_card.grid_rowconfigure(0, weight=1)

        self.prompt_textbox = ctk.CTkTextbox(
            self.prompt_editor_card,
            font=ctk.CTkFont(size=13),
            wrap="word",
            fg_color=theme.COLOR_INPUT_BG,
            corner_radius=theme.RADIUS_INPUT
        )
        self.prompt_textbox.grid(row=0, column=0, padx=16, pady=16, sticky="nsew")

        self.save_prompt_btn = ctk.CTkButton(
            self.prompt_editor_card,
            text="Save Current Prompt",
            height=36,
            corner_radius=theme.RADIUS_BUTTON,
            text_color=theme.COLOR_ACCENT_TEXT,
            fg_color=theme.COLOR_ACCENT,
            hover_color=theme.COLOR_ACCENT_HOVER,
            font=ctk.CTkFont(weight="bold"),
            command=self._trigger_save_prompt
        )
        self.save_prompt_btn.grid(row=1, column=0, padx=16, pady=(0, 16), sticky="e")

    def _trigger_profile_change(self, choice: str) -> None:
        if self.on_profile_change:
            self.on_profile_change(choice)
        else:
            fn = getattr(self.master, "on_profile_change", None)
            if callable(fn):
                fn(choice)

    def _trigger_new_profile(self) -> None:
        if self.on_new_profile:
            self.on_new_profile()
        else:
            fn = getattr(self.master, "create_new_profile", None)
            if callable(fn):
                fn()

    def _trigger_save_prompt(self) -> None:
        if self.on_save_prompt:
            self.on_save_prompt()
        else:
            fn = getattr(self.master, "save_current_prompt", None)
            if callable(fn):
                fn()

    def _trigger_delete_profile(self) -> None:
        if self.on_delete_profile:
            self.on_delete_profile()
        else:
            fn = getattr(self.master, "delete_profile", None)
            if callable(fn):
                fn()

    # --- Public Encapsulated API ---

    def set_profiles(self, profiles: List[str], active: Optional[str] = None) -> None:
        """Populates the profile dropdown with available profile names."""
        if profiles:
            self.profile_dropdown.configure(values=profiles)
            if active and active in profiles:
                self.profile_dropdown.set(active)
            else:
                self.profile_dropdown.set(profiles[0])

    def get_active_profile(self) -> str:
        """Returns the currently selected profile name."""
        return self.profile_dropdown.get()

    def set_active_profile(self, profile_name: str) -> None:
        """Sets the selected profile name in the dropdown."""
        self.profile_dropdown.set(profile_name)

    def get_prompt_text(self) -> str:
        """Returns the text currently in the prompt editor."""
        return self.prompt_textbox.get("1.0", "end-1c")

    def set_prompt_text(self, text: str) -> None:
        """Replaces the prompt editor content."""
        self.prompt_textbox.delete("1.0", "end")
        self.prompt_textbox.insert("1.0", text)

    def show_save_feedback(self) -> None:
        """Briefly changes the save button to green feedback."""
        original_text = "Save Current Prompt"
        self.save_prompt_btn.configure(text="✅ Saved!", fg_color="#2ecc71")
        self.after(2000, lambda: self.save_prompt_btn.configure(text=original_text, fg_color=["#3a7ebf", "#1f538d"]))
