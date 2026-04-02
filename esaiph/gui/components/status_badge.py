"""StatusBadge — A small colored indicator with text for showing recording state."""

from __future__ import annotations

import customtkinter as ctk


class StatusBadge(ctk.CTkFrame):
    """A compact badge showing status with a colored dot indicator.

    States:
    - idle: Gray dot, "IDLE"
    - recording: Pulsing green dot, "RECORDING"
    - error: Red dot, "ERROR"
    - stopped: Yellow dot, "STOPPED"
    """

    STATES = {
        "idle": {"color": "#888888", "text": "IDLE"},
        "recording": {"color": "#00d4aa", "text": "● RECORDING"},
        "error": {"color": "#ff4757", "text": "ERROR"},
        "stopped": {"color": "#ffa502", "text": "STOPPED"},
    }

    def __init__(self, master, state: str = "idle", **kwargs):
        super().__init__(
            master,
            corner_radius=20,
            fg_color=("#e8e8e8", "#1a1a2e"),
            height=32,
            **kwargs,
        )

        self.grid_columnconfigure(0, weight=1)

        self._label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=12, weight="bold"),
            height=28,
        )
        self._label.grid(row=0, column=0, padx=16, pady=2)

        self._pulse_id = None
        self._pulse_on = True

        self.set_state(state)

    def set_state(self, state: str):
        """Change the badge state."""
        self._state = state
        config = self.STATES.get(state, self.STATES["idle"])

        self._label.configure(
            text=config["text"],
            text_color=config["color"],
        )

        # Cancel any existing pulse
        if self._pulse_id:
            self.after_cancel(self._pulse_id)
            self._pulse_id = None

        # Start pulsing for recording state
        if state == "recording":
            self._pulse()

    def _pulse(self):
        """Create a pulsing effect for the recording indicator."""
        if self._state != "recording":
            return

        self._pulse_on = not self._pulse_on
        if self._pulse_on:
            self._label.configure(text="● RECORDING", text_color="#00d4aa")
        else:
            self._label.configure(text="● RECORDING", text_color="#006655")

        self._pulse_id = self.after(600, self._pulse)

    def destroy(self):
        if self._pulse_id:
            self.after_cancel(self._pulse_id)
        super().destroy()
