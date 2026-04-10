"""StatusBadge — Cosmic-styled recording state indicator."""

from __future__ import annotations

import customtkinter as ctk

from ..theme import (
    BG_CARD, BORDER,
    TEXT_MAIN, TEXT_MUTED,
    SUCCESS, ERROR, WARNING, PINK,
    FONT_BODY, RADIUS_MD,
)


class StatusBadge(ctk.CTkFrame):
    """Compact glowing status pill."""

    STATES = {
        "idle":      {"color": TEXT_MUTED, "text": "IDLE",        "dot": "○"},
        "recording": {"color": SUCCESS,    "text": "RECORDING",   "dot": "●"},
        "error":     {"color": ERROR,      "text": "ERROR",       "dot": "●"},
        "stopped":   {"color": WARNING,    "text": "STOPPED",     "dot": "■"},
    }

    def __init__(self, master, state: str = "idle", **kwargs):
        super().__init__(
            master,
            corner_radius=RADIUS_MD,
            fg_color=BG_CARD,
            border_width=1,
            border_color=BORDER,
            height=30,
            **kwargs,
        )
        self.grid_columnconfigure(0, weight=1)

        self._label = ctk.CTkLabel(
            self, text="",
            font=ctk.CTkFont(family=FONT_BODY, size=11, weight="bold"),
            height=26,
        )
        self._label.grid(row=0, column=0, padx=14, pady=2)

        self._pulse_id = None
        self._pulse_on = True
        self.set_state(state)

    def set_state(self, state: str):
        self._state = state
        config = self.STATES.get(state, self.STATES["idle"])
        self._label.configure(
            text=f"{config['dot']}  {config['text']}",
            text_color=config["color"],
        )
        if self._pulse_id:
            self.after_cancel(self._pulse_id)
            self._pulse_id = None
        if state == "recording":
            self._pulse()

    def _pulse(self):
        if self._state != "recording":
            return
        self._pulse_on = not self._pulse_on
        color = SUCCESS if self._pulse_on else "#065f00"
        self._label.configure(text_color=color)
        self._pulse_id = self.after(500, self._pulse)

    def destroy(self):
        if self._pulse_id:
            self.after_cancel(self._pulse_id)
        super().destroy()
