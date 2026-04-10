"""LogsView — Cosmic-styled session log browser."""

from __future__ import annotations

from typing import Optional

import customtkinter as ctk

from ..components.session_card import SessionCard
from ..theme import (
    BG_BASE, BG_CARD, BG_INPUT,
    BORDER, BORDER_LIGHT,
    TEXT_MAIN, TEXT_MUTED, TEXT_DIM,
    PINK, PINK_HOVER, PURPLE, SUCCESS, ERROR,
    FONT_BODY, FONT_HEADING,
    RADIUS_SM, RADIUS_LG,
)
from ...core.analyzer import analyze_session, format_summary_text
from ...core.recorder import list_sessions, load_session_snapshots, delete_session


class LogsView(ctk.CTkFrame):
    """Session log browser — list + detail split view."""

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=BG_BASE, corner_radius=0, **kwargs)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_content()
        self._refresh_sessions()

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, padx=28, pady=(24, 0), sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        title_row = ctk.CTkFrame(header, fg_color="transparent")
        title_row.grid(row=0, column=0, sticky="ew")
        title_row.grid_columnconfigure(0, weight=1)

        # Thin + bold title
        t_frame = ctk.CTkFrame(title_row, fg_color="transparent")
        t_frame.grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            t_frame, text="Session ",
            font=ctk.CTkFont(family=FONT_HEADING, size=24),
            text_color=TEXT_MAIN, anchor="w",
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            t_frame, text="Logs",
            font=ctk.CTkFont(family=FONT_HEADING, size=24, weight="bold"),
            text_color=TEXT_MAIN, anchor="w",
        ).grid(row=0, column=1, sticky="w")

        ctk.CTkButton(
            title_row, text="↻  Refresh",
            font=ctk.CTkFont(family=FONT_BODY, size=11, weight="bold"),
            fg_color=BG_CARD, hover_color=BG_INPUT,
            text_color=TEXT_MUTED,
            border_width=1, border_color=BORDER,
            height=30, corner_radius=RADIUS_SM, width=90,
            command=self._refresh_sessions,
        ).grid(row=0, column=1, sticky="e")

        ctk.CTkLabel(
            header,
            text="Browse and analyze recorded monitoring sessions.",
            font=ctk.CTkFont(family=FONT_BODY, size=12),
            text_color=TEXT_MUTED, anchor="w",
        ).grid(row=1, column=0, pady=(2, 0), sticky="w")

    def _build_content(self):
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.grid(row=1, column=0, padx=28, pady=(16, 20), sticky="nsew")
        content.grid_columnconfigure(0, weight=2)
        content.grid_columnconfigure(1, weight=3)
        content.grid_rowconfigure(0, weight=1)

        # Session list card
        list_card = ctk.CTkFrame(
            content, fg_color=BG_CARD,
            corner_radius=RADIUS_LG, border_width=1, border_color=BORDER,
        )
        list_card.grid(row=0, column=0, padx=(0, 6), sticky="nsew")
        list_card.grid_columnconfigure(0, weight=1)
        list_card.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            list_card, text="SESSIONS",
            font=ctk.CTkFont(family=FONT_BODY, size=9, weight="bold"),
            text_color=TEXT_DIM, anchor="w",
        ).grid(row=0, column=0, padx=18, pady=(14, 6), sticky="w")

        self._list_frame = ctk.CTkScrollableFrame(
            list_card, fg_color="transparent",
            scrollbar_button_color=BORDER,
            scrollbar_button_hover_color=BORDER_LIGHT,
        )
        self._list_frame.grid(row=1, column=0, padx=8, pady=(0, 8), sticky="nsew")
        self._list_frame.grid_columnconfigure(0, weight=1)

        # Detail card
        detail_card = ctk.CTkFrame(
            content, fg_color=BG_CARD,
            corner_radius=RADIUS_LG, border_width=1, border_color=BORDER,
        )
        detail_card.grid(row=0, column=1, padx=(6, 0), sticky="nsew")
        detail_card.grid_columnconfigure(0, weight=1)
        detail_card.grid_rowconfigure(1, weight=1)

        self._detail_header = ctk.CTkLabel(
            detail_card, text="Select a session",
            font=ctk.CTkFont(family=FONT_BODY, size=13, weight="bold"),
            text_color=TEXT_DIM, anchor="w",
        )
        self._detail_header.grid(row=0, column=0, padx=18, pady=(14, 6), sticky="ew")

        self._detail_text = ctk.CTkTextbox(
            detail_card,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color=BG_INPUT, text_color=TEXT_MUTED,
            corner_radius=RADIUS_SM,
            border_width=1, border_color=BORDER,
            wrap="none", activate_scrollbars=True,
            scrollbar_button_color=BORDER,
        )
        self._detail_text.grid(row=1, column=0, padx=10, pady=(0, 6), sticky="nsew")

        # Actions
        actions = ctk.CTkFrame(detail_card, fg_color="transparent")
        actions.grid(row=2, column=0, padx=10, pady=(0, 12), sticky="ew")
        actions.grid_columnconfigure(2, weight=1)

        self._export_json_btn = ctk.CTkButton(
            actions, text="Export JSON", height=28, width=100,
            corner_radius=RADIUS_SM,
            fg_color=PINK, hover_color=PINK_HOVER, text_color="#ffffff",
            font=ctk.CTkFont(family=FONT_BODY, size=10, weight="bold"),
            command=lambda: self._export_selected("json"), state="disabled",
        )
        self._export_json_btn.grid(row=0, column=0, padx=(0, 4))

        self._export_csv_btn = ctk.CTkButton(
            actions, text="Export CSV", height=28, width=100,
            corner_radius=RADIUS_SM,
            fg_color=BG_INPUT, hover_color=BG_BASE,
            text_color=TEXT_MUTED, border_width=1, border_color=BORDER,
            font=ctk.CTkFont(family=FONT_BODY, size=10, weight="bold"),
            command=lambda: self._export_selected("csv"), state="disabled",
        )
        self._export_csv_btn.grid(row=0, column=1, padx=4)

        self._delete_btn = ctk.CTkButton(
            actions, text="Delete", height=28, width=70,
            corner_radius=RADIUS_SM,
            fg_color=BG_INPUT, hover_color=("#fde8e8", "#2a1020"),
            text_color=ERROR, border_width=1, border_color=BORDER,
            font=ctk.CTkFont(family=FONT_BODY, size=10, weight="bold"),
            command=self._delete_selected, state="disabled",
        )
        self._delete_btn.grid(row=0, column=3, padx=(4, 0))

        self._selected_session_id: Optional[str] = None

    def _refresh_sessions(self):
        for w in self._list_frame.winfo_children():
            w.destroy()

        sessions = list_sessions()
        if not sessions:
            ctk.CTkLabel(
                self._list_frame,
                text="No sessions yet.\nRecord one first.",
                font=ctk.CTkFont(family=FONT_BODY, size=12),
                text_color=TEXT_DIM, justify="center",
            ).grid(row=0, column=0, pady=40)
            return

        for i, s in enumerate(sessions):
            SessionCard(
                self._list_frame,
                session_id=s.session_id,
                process_name=s.process_name,
                pid=s.pid,
                start_time=s.start_time,
                duration=s.duration_seconds,
                samples=s.total_samples,
                exit_reason=s.exit_reason,
                on_click=self._show_session_detail,
            ).grid(row=i, column=0, padx=4, pady=3, sticky="ew")

    def _show_session_detail(self, session_id: str):
        self._selected_session_id = session_id
        sessions = list_sessions()
        session = next((s for s in sessions if s.session_id == session_id), None)
        if not session:
            return

        self._detail_header.configure(
            text=f"{session.process_name} (PID {session.pid})  ·  {session.session_id}",
            text_color=TEXT_MAIN,
        )

        try:
            snapshots = load_session_snapshots(session_id)
            summary = analyze_session(session, snapshots)
            report = format_summary_text(summary)
        except FileNotFoundError:
            report = "Session log file not found."
        except Exception as e:
            report = f"Error: {e}"

        self._detail_text.configure(state="normal")
        self._detail_text.delete("1.0", "end")
        self._detail_text.insert("1.0", report)
        self._detail_text.configure(state="disabled")

        for btn in (self._export_json_btn, self._export_csv_btn, self._delete_btn):
            btn.configure(state="normal")

    def _export_selected(self, fmt: str):
        if not self._selected_session_id:
            return
        from tkinter import filedialog
        fp = filedialog.asksaveasfilename(
            defaultextension=f".{fmt}",
            filetypes=[(f"{fmt.upper()}", f"*.{fmt}")],
            initialfile=f"{self._selected_session_id}.{fmt}",
        )
        if not fp:
            return
        import subprocess, sys
        subprocess.Popen(
            [sys.executable, "-m", "esaiph.cli", "logs", "export",
             self._selected_session_id, "-f", fmt, "-o", fp],
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

    def _delete_selected(self):
        if not self._selected_session_id:
            return
        d = ctk.CTkInputDialog(
            text=f"Type 'delete' to confirm:", title="Confirm Delete",
        )
        if (d.get_input() or "").strip().lower() == "delete":
            delete_session(self._selected_session_id)
            self._selected_session_id = None
            self._detail_header.configure(text="Deleted.", text_color=ERROR)
            self._detail_text.configure(state="normal")
            self._detail_text.delete("1.0", "end")
            self._detail_text.configure(state="disabled")
            for btn in (self._export_json_btn, self._export_csv_btn, self._delete_btn):
                btn.configure(state="disabled")
            self._refresh_sessions()
