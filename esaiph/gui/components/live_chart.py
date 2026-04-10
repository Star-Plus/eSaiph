"""LiveChart — Matplotlib-based real-time line chart for system resources."""

from __future__ import annotations

from collections import deque

import customtkinter as ctk
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend first

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from ..theme import (
    PINK, PURPLE, PURPLE_SOFT, ACCENT_CYAN, ACCENT_GREEN,
    resolve, BG_CARD, TEXT_MAIN, TEXT_DIM, BORDER,
    FONT_BODY,
)

# Chart color palette
CHART_COLORS = [PINK, PURPLE_SOFT, ACCENT_CYAN, ACCENT_GREEN, "#f97316"]


class LiveChart(ctk.CTkFrame):
    """Real-time multi-line chart with gradient fill.

    Uses matplotlib embedded via FigureCanvasTkAgg for proper
    chart rendering inside CustomTkinter frames.
    """

    def __init__(
        self,
        master,
        title: str = "Resource Timeline",
        subtitle: str = "Live CPU and memory usage",
        series_names: list[str] | None = None,
        max_points: int = 60,
        y_label: str = "%",
        y_max: float | None = 100.0,
        height_px: int = 280,
        **kwargs,
    ):
        kwargs.pop("fg_color", None)
        super().__init__(master, fg_color=BG_CARD, corner_radius=20,
                         border_width=1, border_color=BORDER, **kwargs)

        self._series_names = series_names or ["CPU", "Memory"]
        self._max_points = max_points
        self._y_label = y_label
        self._y_max = y_max

        # Data storage
        self._data: dict[str, deque] = {
            name: deque(maxlen=max_points) for name in self._series_names
        }

        # Header
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=20, pady=(16, 0))

        ctk.CTkLabel(
            hdr, text=title,
            font=ctk.CTkFont(family=FONT_BODY, size=15, weight="bold"),
            text_color=TEXT_MAIN,
        ).pack(side="left")

        ctk.CTkLabel(
            hdr, text=subtitle,
            font=ctk.CTkFont(family=FONT_BODY, size=10),
            text_color=TEXT_DIM,
        ).pack(side="left", padx=(10, 0))

        # Legend
        legend = ctk.CTkFrame(hdr, fg_color="transparent")
        legend.pack(side="right")
        for i, name in enumerate(self._series_names):
            color = CHART_COLORS[i % len(CHART_COLORS)]
            ctk.CTkLabel(
                legend, text=f"● {name}",
                font=ctk.CTkFont(family=FONT_BODY, size=10),
                text_color=color,
            ).pack(side="left", padx=(8, 0))

        # Matplotlib figure
        bg_color = resolve(BG_CARD)
        dpi = 100
        fig_w = 6.0
        fig_h = height_px / dpi

        self._fig = Figure(figsize=(fig_w, fig_h), dpi=dpi, facecolor=bg_color)
        self._ax = self._fig.add_subplot(111)

        self._mpl_canvas = FigureCanvasTkAgg(self._fig, master=self)
        self._mpl_canvas.get_tk_widget().pack(fill="both", expand=True, padx=12, pady=(4, 12))

        self._setup_axes(bg_color)
        self._fig.tight_layout(pad=1.5)
        self._mpl_canvas.draw_idle()

    def _setup_axes(self, bg_color: str):
        """Style the axes to match the dark dashboard."""
        ax = self._ax
        text_color = resolve(TEXT_MAIN)
        grid_color = resolve(BORDER)

        ax.set_facecolor(bg_color)
        ax.tick_params(colors=resolve(TEXT_DIM), labelsize=8)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["bottom"].set_color(grid_color)
        ax.spines["left"].set_color(grid_color)
        ax.grid(True, alpha=0.15, color=resolve(TEXT_DIM), linestyle="--", linewidth=0.5)

        if self._y_max is not None:
            ax.set_ylim(0, self._y_max)
        ax.set_xlim(0, self._max_points - 1)
        ax.set_ylabel(self._y_label, color=resolve(TEXT_DIM), fontsize=9)

    def add_values(self, **values):
        """Add one data point per series. e.g. add_values(CPU=25.3, Memory=40.1)"""
        for name, val in values.items():
            if name in self._data:
                self._data[name].append(val)

        self._redraw()

    def _redraw(self):
        """Redraw all series."""
        ax = self._ax
        bg_color = resolve(BG_CARD)

        ax.clear()
        self._setup_axes(bg_color)

        for i, (name, data) in enumerate(self._data.items()):
            if len(data) < 2:
                continue

            color = CHART_COLORS[i % len(CHART_COLORS)]
            x = list(range(len(data)))
            y = list(data)

            # Line
            ax.plot(x, y, color=color, linewidth=1.8, alpha=0.9)
            # Fill under
            ax.fill_between(x, y, alpha=0.08, color=color)

        self._fig.tight_layout(pad=1.5)
        self._mpl_canvas.draw_idle()
