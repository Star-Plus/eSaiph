"""MetricCard — A styled card widget displaying a single metric with label, value, and optional bar."""

from __future__ import annotations

import customtkinter as ctk


class MetricCard(ctk.CTkFrame):
    """Displays a labeled metric with a value and optional progress bar.

    Used in the recording dashboard to show CPU, memory, I/O, etc.
    """

    def __init__(
        self,
        master,
        label: str = "Metric",
        value: str = "—",
        unit: str = "",
        show_bar: bool = False,
        bar_value: float = 0.0,
        color: str = "#00d4aa",
        **kwargs,
    ):
        super().__init__(
            master,
            corner_radius=12,
            fg_color=("#f0f0f0", "#1a1a2e"),
            border_width=1,
            border_color=("#e0e0e0", "#2a2a3e"),
            **kwargs,
        )

        self._color = color

        # Layout
        self.grid_columnconfigure(0, weight=1)

        # Label
        self._label = ctk.CTkLabel(
            self,
            text=label.upper(),
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("#888888", "#888888"),
            anchor="w",
        )
        self._label.grid(row=0, column=0, padx=16, pady=(12, 2), sticky="w")

        # Value
        self._value_label = ctk.CTkLabel(
            self,
            text=f"{value} {unit}".strip(),
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=color,
            anchor="w",
        )
        self._value_label.grid(row=1, column=0, padx=16, pady=(0, 4), sticky="w")

        # Optional progress bar
        self._bar = None
        if show_bar:
            self._bar = ctk.CTkProgressBar(
                self,
                height=6,
                corner_radius=3,
                progress_color=color,
                fg_color=("#e0e0e0", "#2a2a3e"),
            )
            self._bar.grid(row=2, column=0, padx=16, pady=(0, 12), sticky="ew")
            self._bar.set(bar_value / 100.0 if bar_value <= 100 else 1.0)
        else:
            self._value_label.grid_configure(pady=(0, 12))

        self._unit = unit

    def update_value(self, value: str, bar_value: float | None = None):
        """Update the displayed value and optionally the bar."""
        display = f"{value} {self._unit}".strip()
        self._value_label.configure(text=display)

        if self._bar is not None and bar_value is not None:
            normalized = max(0.0, min(1.0, bar_value / 100.0))
            self._bar.set(normalized)

            # Dynamic color based on value
            if bar_value > 80:
                self._bar.configure(progress_color="#ff4757")
            elif bar_value > 50:
                self._bar.configure(progress_color="#ffa502")
            else:
                self._bar.configure(progress_color=self._color)

    def update_color(self, color: str):
        """Change the accent color."""
        self._color = color
        self._value_label.configure(text_color=color)
        if self._bar:
            self._bar.configure(progress_color=color)
