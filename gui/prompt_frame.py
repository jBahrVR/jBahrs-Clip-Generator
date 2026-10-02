import customtkinter as ctk # type: ignore
from typing import Optional, Callable, List

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
        
        self.prompt_title = ctk.CTkLabel(self, text="AI Prompt Editor", font=ctk.CTkFont(size=28, weight="bold"))
        self.prompt_title.grid(row=0, column=0, padx=30, pady=(30, 10), sticky="w")

        self.prompt_select_card = ctk.CTkFrame(self, corner_radius=15)
        self.prompt_select_card.grid(row=1, column=0, padx=30, pady=10, sticky="ew")
        
        ctk.CTkLabel(self.prompt_select_card, text="Active Manual Profile:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=20, pady=20)
        self.profile_dropdown = ctk.CTkOptionMenu(self.prompt_select_card, command=self._trigger_profile_change)
        self.profile_dropdown.pack(side="left", padx=10)

        self.new_profile_btn = ctk.CTkButton(
            self.prompt_select_card, text="➕ New", width=60, fg_color="#27ae60",
            hover_color="#1e8449", command=self._trigger_new_profile
        )
        self.new_profile_btn.pack(side="left", padx=5)

        self.delete_profile_btn = ctk.CTkButton(
            self.prompt_select_card, text="Delete Profile", fg_color="#c0392b",
            hover_color="#922b21", command=self._trigger_delete_profile
        )
        self.delete_profile_btn.pack(side="right", padx=20)

        self.prompt_editor_card = ctk.CTkFrame(self, corner_radius=15)
        self.prompt_editor_card.grid(row=2, column=0, padx=30, pady=10, sticky="nsew")
        self.prompt_editor_card.grid_columnconfigure(0, weight=1)
        self.prompt_editor_card.grid_rowconfigure(0, weight=1)

        self.prompt_textbox = ctk.CTkTextbox(self.prompt_editor_card, font=ctk.CTkFont(size=14), wrap="word")
        self.prompt_textbox.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")

        self.save_prompt_btn = ctk.CTkButton(
            self.prompt_editor_card, text="Save Current Prompt", height=40,
            font=ctk.CTkFont(weight="bold"), command=self._trigger_save_prompt
        )
        self.save_prompt_btn.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="e")

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
