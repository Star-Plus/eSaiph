"""SessionCard — A clickable card representing a recorded session in the logs view."""

from __future__ import annotations

from typing import Callable, Optional

import customtkinter as ctk


class SessionCard(ctk.CTkFrame):
    """Displays a summary of a recorded session as a clickable card.

    Shows: process name, PID, date, duration, sample count, and exit reason.
    Clicking the card triggers the on_click callback with the session_id.
    """

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
            corner_radius=10,
            fg_color=("#f5f5f5", "#1e1e30"),
            border_width=1,
            border_color=("#e0e0e0", "#2a2a3e"),
            cursor="hand2",
            **kwargs,
        )

        self._session_id = session_id
        self._on_click = on_click

        self.grid_columnconfigure(1, weight=1)

        # Left accent bar
        accent = ctk.CTkFrame(self, width=4, corner_radius=2, fg_color="#00d4aa")
        accent.grid(row=0, column=0, rowspan=2, padx=(8, 0), pady=8, sticky="ns")

        # Top row — process name + PID
        top_frame = ctk.CTkFrame(self, fg_color="transparent")
        top_frame.grid(row=0, column=1, padx=12, pady=(10, 2), sticky="ew")
        top_frame.grid_columnconfigure(0, weight=1)

        name_label = ctk.CTkLabel(
            top_frame,
            text=f"{process_name}",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=("#222222", "#e0e0e0"),
            anchor="w",
        )
        name_label.grid(row=0, column=0, sticky="w")

        pid_label = ctk.CTkLabel(
            top_frame,
            text=f"PID {pid}",
            font=ctk.CTkFont(size=11),
            text_color=("#888888", "#888888"),
            anchor="e",
        )
        pid_label.grid(row=0, column=1, sticky="e")

        # Bottom row — metadata
        meta_frame = ctk.CTkFrame(self, fg_color="transparent")
        meta_frame.grid(row=1, column=1, padx=12, pady=(0, 10), sticky="ew")

        # Format start time
        display_time = start_time[:19].replace("T", " ") if start_time else "—"
        dur_str = f"{duration:.1f}s" if duration else "—"

        meta_text = f"📅 {display_time}  ⏱ {dur_str}  📊 {samples} samples"
        if exit_reason:
            meta_text += f"  🏁 {exit_reason}"

        meta_label = ctk.CTkLabel(
            meta_frame,
            text=meta_text,
            font=ctk.CTkFont(size=11),
            text_color=("#666666", "#aaaaaa"),
            anchor="w",
        )
        meta_label.grid(row=0, column=0, sticky="w")

        # Session ID (small, dimmed)
        sid_label = ctk.CTkLabel(
            meta_frame,
            text=session_id,
            font=ctk.CTkFont(size=10),
            text_color=("#aaaaaa", "#555555"),
            anchor="e",
        )
        sid_label.grid(row=0, column=1, sticky="e")
        meta_frame.grid_columnconfigure(0, weight=1)

        # Bind click to all children
        self._bind_click_recursive(self)

    def _bind_click_recursive(self, widget):
        """Bind click event to widget and all its children."""
        widget.bind("<Button-1>", self._handle_click)
        # Hover effect
        widget.bind("<Enter>", self._on_enter)
        widget.bind("<Leave>", self._on_leave)
        for child in widget.winfo_children():
            self._bind_click_recursive(child)

    def _handle_click(self, event):
        if self._on_click:
            self._on_click(self._session_id)

    def _on_enter(self, event):
        self.configure(fg_color=("#e8e8f0", "#252540"))

    def _on_leave(self, event):
        self.configure(fg_color=("#f5f5f5", "#1e1e30"))
