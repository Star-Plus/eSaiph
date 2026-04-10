"""eSaiph Design System — Cosmic Dashboard Theme.

Inspired by Fintat-style dark dashboard with deep navy backgrounds,
pink/purple gradient accents, glassmorphic cards, and cosmic particle effects.

All color constants are (light, dark) tuples for dual-mode support.
For Canvas widgets, use resolve(color_tuple).
"""

from __future__ import annotations

import customtkinter as ctk


# ─────────────────────────────────────────────────────────────
#  Color Palette  — (light, dark)
# ─────────────────────────────────────────────────────────────

# Backgrounds — deep navy cosmic
BG_BASE     = ("#F0EEF6", "#0f0e17")     # Page background
BG_CARD     = ("#FFFFFF", "#1a1932")     # Glassmorphic card surface
BG_NAVBAR   = ("#E8E6F0", "#0a0a14")     # Sidebar
BG_ELEVATED = ("#EBE9F3", "#252347")     # Hover / elevated
BG_INPUT    = ("#F0EEF6", "#12111e")     # Input fields
BG_OVERLAY  = ("#FFFFFF", "#1e1d35")     # Modals

# Accents — pink / purple gradient palette
PINK        = "#e040fb"                   # Primary pink
PINK_HOVER  = "#ea68fc"                   # Pink hover
PURPLE      = "#7c4dff"                   # Deep purple
PURPLE_SOFT = "#a78bfa"                   # Soft lavender
MAGENTA     = "#ff4081"                   # Hot pink/magenta

# Gradient stops (for Canvas drawing)
GRAD_START  = "#e040fb"                   # Pink
GRAD_MID    = "#a855f7"                   # Mid purple
GRAD_END    = "#7c4dff"                   # Deep purple

# Keep legacy names for compatibility
PRIMARY       = PINK
PRIMARY_HOVER = PINK_HOVER

# Text
TEXT_MAIN  = ("#1a1a2e", "#ffffff")      # Primary text
TEXT_MUTED = ("#7a7a8e", "#8b8ba7")      # Secondary / muted
TEXT_DIM   = ("#a0a0b0", "#5a5a7a")      # Tertiary / very muted

# Borders — very subtle in dark, soft in light
BORDER       = ("#DDDBE5", "#1c1b30")    # Standard
BORDER_LIGHT = ("#D0CED8", "#2a2948")    # Slightly stronger
BORDER_HOVER = ("#C5C3CF", "#3a3860")    # Hover

# Status / Semantic
SUCCESS = "#0BD900"
ERROR   = "#ff4060"
WARNING = "#ffb347"

# Metric accent colors
ACCENT_CYAN   = "#22d3ee"
ACCENT_ORANGE = "#f97316"
ACCENT_GREEN  = "#34d399"

# Canvas-specific resolved colors
GAUGE_TRACK   = ("#DDDBE5", "#1c1b30")
GAUGE_BG      = ("#F0EEF6", "#0f0e17")


# ─────────────────────────────────────────────────────────────
#  Typography
# ─────────────────────────────────────────────────────────────
FONT_HEADING = "Segoe UI"
FONT_BODY    = "Segoe UI"


# ─────────────────────────────────────────────────────────────
#  Spacing
# ─────────────────────────────────────────────────────────────
RADIUS_SM = 8
RADIUS_MD = 14
RADIUS_LG = 20
RADIUS_XL = 24

PADDING_SM = 8
PADDING_MD = 16
PADDING_LG = 24
PADDING_XL = 32


# ─────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────

def resolve(color) -> str:
    """Resolve a (light, dark) tuple for the current appearance mode."""
    if isinstance(color, str):
        return color
    mode = ctk.get_appearance_mode()
    return color[0] if mode == "Light" else color[1]


def interpolate_color(c1: str, c2: str, t: float) -> str:
    """Linearly interpolate between two hex colors. t=0 → c1, t=1 → c2."""
    r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)
    r2, g2, b2 = int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16)
    r = int(r1 + (r2 - r1) * t)
    g = int(g1 + (g2 - g1) * t)
    b = int(b1 + (b2 - b1) * t)
    return f"#{r:02x}{g:02x}{b:02x}"
