"""MetricCard — Clean stat card matching the dashboard reference."""

from __future__ import annotations

import customtkinter as ctk

from ..theme import (
    BG_CARD, BG_ELEVATED, BORDER, BORDER_HOVER,
    TEXT_MAIN, TEXT_MUTED, TEXT_DIM,
    FONT_BODY, RADIUS_LG,
)


class MetricCard(ctk.CTkFrame):
    """Compact stat card: small label on top, large bold value below.

    Matches the dashboard reference's hero stat cards.
    """

    def __init__(
        self,
        master,
        label: str = "Metric",
        value: str = "—",
        unit: str = "",
        accent_color: str = "#e040fb",
        show_bar: bool = False,
        bar_value: float = 0.0,
        **kwargs,
    ):
        # Remove unsupported kwargs
        kwargs.pop("show_sparkline", None)
        kwargs.pop("accent_color", None)

        super().__init__(
            master,
            corner_radius=RADIUS_LG,
            fg_color=BG_CARD,
            border_width=1,
            border_color=BORDER,
            **kwargs,
        )

        self._unit = unit
        self._accent = accent_color
        self.grid_columnconfigure(0, weight=1)

        # Accent dot + label row
        label_row = ctk.CTkFrame(self, fg_color="transparent")
        label_row.grid(row=0, column=0, padx=18, pady=(14, 0), sticky="w")

        ctk.CTkFrame(
            label_row, width=6, height=6,
            corner_radius=3, fg_color=accent_color,
        ).pack(side="left", padx=(0, 6))

        ctk.CTkLabel(
            label_row,
            text=label.upper(),
            font=ctk.CTkFont(family=FONT_BODY, size=10, weight="bold"),
            text_color=TEXT_DIM,
        ).pack(side="left")

        # Value
        self._value_label = ctk.CTkLabel(
            self,
            text=self._format(value),
            font=ctk.CTkFont(family=FONT_BODY, size=26, weight="bold"),
            text_color=TEXT_MAIN,
            anchor="w",
        )
        self._value_label.grid(row=1, column=0, padx=18, pady=(2, 4), sticky="w")

        # Optional progress bar
        self._bar = None
        if show_bar:
            self._bar = ctk.CTkProgressBar(
                self, height=3, corner_radius=2,
                progress_color=accent_color, fg_color=BORDER,
            )
            self._bar.grid(row=2, column=0, padx=18, pady=(0, 14), sticky="ew")
            self._bar.set(bar_value / 100.0 if bar_value <= 100 else 1.0)
        else:
            self._value_label.grid_configure(pady=(2, 14))

        # Hover
        self.bind("<Enter>", lambda e: self.configure(fg_color=BG_ELEVATED, border_color=BORDER_HOVER))
        self.bind("<Leave>", lambda e: self.configure(fg_color=BG_CARD, border_color=BORDER))

    def _format(self, value: str) -> str:
        return f"{value} {self._unit}".strip() if self._unit else value

    def update_value(self, value: str, bar_value: float | None = None):
        self._value_label.configure(text=self._format(value))
        if self._bar is not None and bar_value is not None:
            self._bar.set(max(0.0, min(1.0, bar_value / 100.0)))
            if bar_value > 85:
                self._bar.configure(progress_color="#ff4060")
            elif bar_value > 60:
                self._bar.configure(progress_color="#ffb347")
            else:
                self._bar.configure(progress_color=self._accent)
