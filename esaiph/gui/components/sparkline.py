"""SparklineWidget — Mini trend indicator for metric cards.

Uses a CTkProgressBar styled as a thin colored bar, avoiding
raw tk.Canvas inside CTkFrame which causes widget path issues.
For actual chart rendering, we use after_idle + bind to draw
on a Label's underlying tkinter canvas once it's fully mapped.
"""

from __future__ import annotations

import customtkinter as ctk

from ..theme import (
    PINK, PURPLE, BORDER,
    interpolate_color,
)


class SparklineWidget(ctk.CTkLabel):
    """Tiny trend indicator that shows the last few values as colored blocks.

    Uses CTkLabel with dynamic text to create a simple bar-chart
    representation without needing raw tk.Canvas.
    """

    def __init__(
        self,
        master,
        width: int = 80,
        height: int = 36,
        max_points: int = 20,
        accent: str = PINK,
        bg_color: str = "#1a1932",
        **kwargs,
    ):
        kwargs.pop("bg_color", None)
        kwargs.pop("fg_color", None)
        super().__init__(
            master,
            text="",
            width=width,
            height=height,
            fg_color="transparent",
            corner_radius=0,
            **kwargs,
        )

        self._max_points = max_points
        self._accent = accent
        self._bg = bg_color
        self._data: list[float] = []
        self._bar: ctk.CTkProgressBar | None = None

        # Create a thin progress bar as the trend indicator
        self._bar = ctk.CTkProgressBar(
            self,
            width=width,
            height=3,
            corner_radius=2,
            progress_color=accent,
            fg_color=BORDER,
        )
        self._bar.place(relx=0.5, rely=0.8, anchor="center")
        self._bar.set(0.0)

        # Trend arrow label
        self._trend = ctk.CTkLabel(
            self,
            text="—",
            font=ctk.CTkFont(size=14),
            text_color=accent,
            fg_color="transparent",
        )
        self._trend.place(relx=0.5, rely=0.35, anchor="center")

    def add_point(self, value: float):
        self._data.append(value)
        if len(self._data) > self._max_points:
            self._data = self._data[-self._max_points:]
        self._update_display()

    def set_data(self, data: list[float]):
        self._data = list(data[-self._max_points:])
        self._update_display()

    def _update_display(self):
        if not self._data:
            return

        # Normalize latest value to 0-1 for bar
        max_val = max(self._data) or 1
        latest = self._data[-1]
        normalized = max(0.0, min(1.0, latest / max_val))
        self._bar.set(normalized)

        # Trend arrow
        if len(self._data) >= 2:
            prev = self._data[-2]
            curr = self._data[-1]
            if curr > prev * 1.02:
                self._trend.configure(text="▲", text_color=self._accent)
            elif curr < prev * 0.98:
                self._trend.configure(text="▼", text_color=self._accent)
            else:
                self._trend.configure(text="—", text_color=self._accent)

    def update_bg(self, color: str):
        self._bg = color
