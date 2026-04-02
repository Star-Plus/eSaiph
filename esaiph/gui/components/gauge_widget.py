"""GaugeWidget — A circular gauge for displaying percentage values like CPU usage."""

from __future__ import annotations

import math

import customtkinter as ctk


class GaugeWidget(ctk.CTkCanvas):
    """Circular gauge that displays a percentage value with an animated arc.

    Features:
    - Smooth arc with gradient-like coloring (green → yellow → red)
    - Large centered value text
    - Label below the gauge
    """

    def __init__(
        self,
        master,
        size: int = 160,
        label: str = "CPU",
        value: float = 0.0,
        thickness: int = 12,
        **kwargs,
    ):
        # Filter out bg_color to avoid Canvas conflict
        kwargs.pop("bg_color", None)
        super().__init__(
            master,
            width=size,
            height=size + 30,
            highlightthickness=0,
            **kwargs,
        )

        self._size = size
        self._label = label
        self._value = value
        self._thickness = thickness
        self._center = size // 2
        self._radius = (size - thickness * 2) // 2

        # Try to match parent background
        self.configure(bg="#1a1a2e")
        self.bind("<Configure>", lambda e: self._draw())

        self._draw()

    def _draw(self):
        """Redraw the gauge."""
        self.delete("all")

        cx = self._center
        cy = self._center
        r = self._radius
        t = self._thickness

        # Background arc (full circle track)
        self.create_arc(
            cx - r, cy - r, cx + r, cy + r,
            start=225, extent=-270,
            style="arc", width=t,
            outline="#2a2a3e",
        )

        # Value arc
        extent = -(self._value / 100.0) * 270
        color = self._get_color(self._value)
        if self._value > 0:
            self.create_arc(
                cx - r, cy - r, cx + r, cy + r,
                start=225, extent=extent,
                style="arc", width=t,
                outline=color,
            )

        # Center value text
        self.create_text(
            cx, cy - 5,
            text=f"{self._value:.0f}%",
            fill=color,
            font=("Segoe UI", 22, "bold"),
        )

        # Label below
        self.create_text(
            cx, self._size + 10,
            text=self._label.upper(),
            fill="#888888",
            font=("Segoe UI", 10, "bold"),
        )

    def set_value(self, value: float):
        """Update the gauge value (0-100)."""
        self._value = max(0.0, min(100.0, value))
        self._draw()

    def _get_color(self, value: float) -> str:
        """Get color based on value — green → yellow → red."""
        if value <= 30:
            return "#00d4aa"  # Teal/green
        elif value <= 60:
            return "#ffd93d"  # Yellow
        elif value <= 80:
            return "#ff9f43"  # Orange
        else:
            return "#ff4757"  # Red
