"""SessionCard — Cosmic-styled clickable session card."""

from __future__ import annotations

from typing import Callable, Optional
import customtkinter as ctk

from ..theme import (
    BG_CARD, BG_ELEVATED, BORDER, BORDER_HOVER,
    TEXT_MAIN, TEXT_MUTED, TEXT_DIM,
    PINK, PURPLE, FONT_BODY, RADIUS_LG,
)


class SessionCard(ctk.CTkFrame):
    """Session card with pink accent bar and hover glow."""

    def __init__(
        self,
        master,
        session_id: str,
        process_name: str = "—",
        pid: int = 0,
        start_time: str = "",
        duration: float = 0.0,
        samples: int = 0,
        exit_reason: str = "",
        on_click: Optional[Callable[[str], None]] = None,
        **kwargs,
    ):
        super().__init__(
            master,
            corner_radius=RADIUS_LG,
            fg_color=BG_CARD,
            border_width=1,
            border_color=BORDER,
            cursor="hand2",
            **kwargs,
        )

        self._session_id = session_id
        self._on_click = on_click
        self.grid_columnconfigure(1, weight=1)

        # Pink accent bar
        ctk.CTkFrame(
            self, width=3, corner_radius=2, fg_color=PINK,
        ).grid(row=0, column=0, rowspan=2, padx=(10, 0), pady=12, sticky="ns")

        # Top row
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=1, padx=14, pady=(12, 2), sticky="ew")
        top.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            top, text=process_name,
            font=ctk.CTkFont(family=FONT_BODY, size=14, weight="bold"),
            text_color=TEXT_MAIN, anchor="w",
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            top, text=f"PID {pid}",
            font=ctk.CTkFont(family=FONT_BODY, size=11),
            text_color=TEXT_DIM, anchor="e",
        ).grid(row=0, column=1, sticky="e")

        # Bottom row
        meta = ctk.CTkFrame(self, fg_color="transparent")
        meta.grid(row=1, column=1, padx=14, pady=(0, 12), sticky="ew")
        meta.grid_columnconfigure(0, weight=1)

        display_time = start_time[:19].replace("T", " ") if start_time else "—"
        dur_str = f"{duration:.1f}s" if duration else "—"
        info_parts = [display_time, dur_str, f"{samples} samples"]
        if exit_reason:
            info_parts.append(exit_reason)

        ctk.CTkLabel(
            meta, text="  ·  ".join(info_parts),
            font=ctk.CTkFont(family=FONT_BODY, size=11),
            text_color=TEXT_MUTED, anchor="w",
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            meta, text=session_id,
            font=ctk.CTkFont(family=FONT_BODY, size=9),
            text_color=TEXT_DIM, anchor="e",
        ).grid(row=0, column=1, sticky="e")

        self._bind_recursive(self)

    def _bind_recursive(self, widget):
        widget.bind("<Button-1>", self._handle_click)
        widget.bind("<Enter>", self._on_enter)
        widget.bind("<Leave>", self._on_leave)
        for child in widget.winfo_children():
            self._bind_recursive(child)

    def _handle_click(self, event):
        if self._on_click:
            self._on_click(self._session_id)

    def _on_enter(self, event):
        self.configure(fg_color=BG_ELEVATED, border_color=BORDER_HOVER)

    def _on_leave(self, event):
        self.configure(fg_color=BG_CARD, border_color=BORDER)
