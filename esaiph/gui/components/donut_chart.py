"""DonutChart — Matplotlib-based donut/ring chart for resource distribution."""

from __future__ import annotations

import customtkinter as ctk
import matplotlib
matplotlib.use("Agg")

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from ..theme import (
    PINK, PURPLE, PURPLE_SOFT, ACCENT_CYAN, ACCENT_GREEN,
    resolve, BG_CARD, TEXT_MAIN, TEXT_DIM, BORDER,
    FONT_BODY,
)

DONUT_COLORS = [PINK, PURPLE, PURPLE_SOFT, ACCENT_CYAN, ACCENT_GREEN, "#f97316"]


class DonutChart(ctk.CTkFrame):
    """Ring chart showing resource distribution."""

    def __init__(
        self,
        master,
        title: str = "Resource Distribution",
        subtitle: str = "Current allocation",
        height_px: int = 280,
        **kwargs,
    ):
        kwargs.pop("fg_color", None)
        super().__init__(master, fg_color=BG_CARD, corner_radius=20,
                         border_width=1, border_color=BORDER, **kwargs)

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

        # Figure
        bg = resolve(BG_CARD)
        dpi = 100
        fig_h = height_px / dpi

        self._fig = Figure(figsize=(3.5, fig_h), dpi=dpi, facecolor=bg)
        self._ax = self._fig.add_subplot(111)
        self._ax.set_facecolor(bg)

        self._mpl_canvas = FigureCanvasTkAgg(self._fig, master=self)
        self._mpl_canvas.get_tk_widget().pack(fill="both", expand=True, padx=12, pady=(0, 12))

        # Legend frame
        self._legend_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._legend_frame.pack(fill="x", padx=20, pady=(0, 14))

        # Draw empty state
        self._draw_empty()

    def _draw_empty(self):
        ax = self._ax
        ax.clear()
        ax.set_facecolor(resolve(BG_CARD))
        ax.pie([1], colors=[resolve(BORDER)], startangle=90,
               wedgeprops=dict(width=0.35, edgecolor=resolve(BG_CARD)))
        ax.text(0, 0, "—", ha="center", va="center",
                fontsize=18, fontweight="bold", color=resolve(TEXT_DIM))
        self._fig.tight_layout(pad=0.5)
        self._mpl_canvas.draw_idle()

    def update_data(self, labels: list[str], values: list[float],
                    center_text: str = ""):
        """Update the donut chart with new data."""
        ax = self._ax
        bg = resolve(BG_CARD)
        ax.clear()
        ax.set_facecolor(bg)

        # Filter out zero values
        filtered = [(l, v) for l, v in zip(labels, values) if v > 0]
        if not filtered:
            self._draw_empty()
            return

        labels_f, values_f = zip(*filtered)
        colors = [DONUT_COLORS[i % len(DONUT_COLORS)] for i in range(len(values_f))]

        wedges, _ = ax.pie(
            values_f,
            colors=colors,
            startangle=90,
            wedgeprops=dict(width=0.35, edgecolor=bg, linewidth=2),
        )

        # Center text
        ax.text(0, 0, center_text,
                ha="center", va="center",
                fontsize=16, fontweight="bold",
                color=resolve(TEXT_MAIN))

        self._fig.tight_layout(pad=0.5)
        self._mpl_canvas.draw_idle()

        # Update legend
        for w in self._legend_frame.winfo_children():
            w.destroy()

        for i, (label, val) in enumerate(zip(labels_f, values_f)):
            color = DONUT_COLORS[i % len(DONUT_COLORS)]
            ctk.CTkLabel(
                self._legend_frame,
                text=f"● {label}: {val:.1f}",
                font=ctk.CTkFont(family=FONT_BODY, size=10),
                text_color=color,
            ).pack(side="left", padx=(0, 12))
