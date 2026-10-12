import customtkinter as ctk

# Fix CustomTkinter issue where label.configure(image=None) fails to clear
# the underlying tkinter.Label image attribute, resulting in
# "_tkinter.TclError: image 'pyimageXXX' doesn't exist" after garbage collection.
_orig_ctk_label_configure = ctk.CTkLabel.configure

def _safe_ctk_label_configure(self, require_redraw=False, **kwargs):
    if "image" in kwargs and kwargs["image"] is None:
        if hasattr(self, "_label") and self._label:
            try:
                self._label.configure(image="")
            except Exception:
                pass
    return _orig_ctk_label_configure(self, require_redraw=require_redraw, **kwargs)

ctk.CTkLabel.configure = _safe_ctk_label_configure

from .sidebar import Sidebar
from .manual_frame import ManualFrame
from .auto_frame import AutoFrame
from .prompt_frame import PromptFrame
from .settings_frame import SettingsFrame
from .gallery_frame import GalleryFrame
from .video_preview import VideoPreviewWidget
from .publish_dialog import PublishDialog
from . import theme

__all__ = [
    "Sidebar",
    "ManualFrame",
    "AutoFrame",
    "PromptFrame",
    "SettingsFrame",
    "GalleryFrame",
    "VideoPreviewWidget",
    "PublishDialog",
    "theme",
]
