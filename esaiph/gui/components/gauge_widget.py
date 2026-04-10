"""GaugeWidget — Cosmic donut gauge using CTkLabel-based rendering.

Uses CTkLabel with large percentage text and a surrounding
CTkProgressBar ring instead of raw tk.Canvas to avoid
CustomTkinter widget path compatibility issues.
"""

from __future__ import annotations

import customtkinter as ctk

from ..theme import (
    GAUGE_BG, GAUGE_TRACK, BG_CARD, BORDER,
    TEXT_MAIN, TEXT_DIM,
    PINK, PURPLE, PURPLE_SOFT, MAGENTA,
    WARNING, ERROR,
    FONT_BODY,
    resolve,
)


class GaugeWidget(ctk.CTkFrame):
    """Circular-progress gauge using CTk widgets only."""

    def __init__(
        self,
        master,
        size: int = 160,
        label: str = "CPU",
        value: float = 0.0,
        thickness: int = 12,
        bg_override=None,
        **kwargs,
    ):
        kwargs.pop("bg_color", None)
        kwargs.pop("fg_color", None)

        bg = bg_override or BG_CARD

        super().__init__(
            master,
            fg_color=bg,
            width=size,
            height=size + 30,
            corner_radius=0,
            **kwargs,
        )
        self.grid_propagate(False)
        self.pack_propagate(False)

        self._size = size
        self._label = label
        self._value = value
        self._bg_source = bg

        # Outer ring (progress bar)
        self._ring = ctk.CTkProgressBar(
            self,
            width=size - 20,
            height=size - 20,
            corner_radius=(size - 20) // 2,
            progress_color=PURPLE,
            fg_color=BORDER,
            mode="determinate",
            border_width=0,
        )
        self._ring.place(relx=0.5, rely=0.42, anchor="center")
        self._ring.set(0.0)

        # Value label
        self._value_label = ctk.CTkLabel(
            self,
            text=f"{value:.1f}%",
            font=ctk.CTkFont(family=FONT_BODY, size=22, weight="bold"),
            text_color=TEXT_MAIN,
            fg_color="transparent",
        )
        self._value_label.place(relx=0.5, rely=0.36, anchor="center")

        # Sub-label (inside)
        self._sub_label = ctk.CTkLabel(
            self,
            text=label.upper(),
            font=ctk.CTkFont(family=FONT_BODY, size=9, weight="bold"),
            text_color=TEXT_DIM,
            fg_color="transparent",
        )
        self._sub_label.place(relx=0.5, rely=0.50, anchor="center")

        # Bottom label
        self._bottom_label = ctk.CTkLabel(
            self,
            text=label,
            font=ctk.CTkFont(family=FONT_BODY, size=10),
            text_color=TEXT_DIM,
            fg_color="transparent",
        )
        self._bottom_label.place(relx=0.5, rely=0.90, anchor="center")

    def set_value(self, value: float):
        self._value = max(0.0, min(100.0, value))
        normalized = self._value / 100.0
        self._ring.set(normalized)
        self._value_label.configure(text=f"{self._value:.1f}%")

        # Color based on value
        color = self._get_color(self._value)
        self._ring.configure(progress_color=color)

    def _get_color(self, value: float) -> str:
        if value <= 40:
            return PURPLE
        elif value <= 60:
            return PURPLE_SOFT
        elif value <= 75:
            return PINK
        elif value <= 85:
            return MAGENTA
        else:
            return ERROR

    def update_bg(self, color):
        self._bg_source = color

    def refresh_theme(self):
        pass  # CTk handles mode switching automatically
