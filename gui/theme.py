"""
Design tokens and theme definitions for Clip Generator following TASTE principles.
Defines cohesive surface colors, typography scales, single-accent color rules,
and unified corner radius standards across all views.
"""

# --- Theme Colors (Single Accent + Dark Studio Surface) ---
# Primary brand accent: Electric Studio Cyan
COLOR_ACCENT = "#00b4d8"
COLOR_ACCENT_HOVER = "#0096c7"
COLOR_ACCENT_MUTED = "#0077b6"
COLOR_ACCENT_TEXT = "#001824"

# Neutral Surfaces
COLOR_BG_BASE = "#121316"         # Deep obsidian window background
COLOR_SIDEBAR_BG = "#16171b"      # Sidebar container
COLOR_CARD_BG = "#1c1e23"         # Elevated card / panel background
COLOR_CARD_BORDER = "#282a32"     # Subtle card border
COLOR_INPUT_BG = "#131417"        # Form entry and console field background
COLOR_HOVER_MUTED = "#2c2e36"     # Ghost button and subtle hover fill

# Functional State Colors
COLOR_SUCCESS = "#2ecc71"         # Completed / Active / Valid indicator
COLOR_DANGER = "#e63946"          # Cancel / Delete / Error (Restrained Crimson)
COLOR_DANGER_HOVER = "#d62828"
COLOR_WARNING = "#f39c12"         # Alerts / FFmpeg logs
COLOR_TEXT_PRIMARY = "#f0f2f5"    # Crisp heading and body text
COLOR_TEXT_MUTED = "#8b909a"      # Secondary labels and captions
COLOR_TEXT_DIM = "#565a64"        # Placeholder / timestamp dim

# --- Geometry & Radius Locks ---
RADIUS_CARD = 10
RADIUS_BUTTON = 6
RADIUS_INPUT = 6

# --- Typography Font Specs ---
FONT_FAMILY_UI = "Segoe UI"
FONT_FAMILY_MONO = "Consolas"
