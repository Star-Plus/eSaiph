"""LogsView — Browse, inspect, and export recorded session logs."""

from __future__ import annotations

from typing import Optional

import customtkinter as ctk

from ..components.session_card import SessionCard
from ...core.analyzer import analyze_session, format_summary_text
from ...core.recorder import list_sessions, load_session_snapshots, delete_session


class LogsView(ctk.CTkFrame):
    """Session log browser with list of sessions and detail panel."""

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_toolbar()
        self._build_content()
        self._refresh_sessions()

    def _build_toolbar(self):
        """Build the top toolbar with refresh and export buttons."""
        toolbar = ctk.CTkFrame(self, fg_color=("#f0f0f0", "#1a1a2e"), corner_radius=12)
        toolbar.grid(row=0, column=0, padx=16, pady=(16, 8), sticky="ew")
        toolbar.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            toolbar,
            text="📋 Session Logs",
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, padx=16, pady=12, sticky="w")

        refresh_btn = ctk.CTkButton(
            toolbar,
            text="🔄 Refresh",
            font=ctk.CTkFont(size=12),
            fg_color=("#ddd", "#2a2a3e"),
            hover_color=("#ccc", "#3a3a4e"),
            text_color=("#333", "#e0e0e0"),
            height=32,
            corner_radius=8,
            width=90,
            command=self._refresh_sessions,
        )
        refresh_btn.grid(row=0, column=1, padx=(4, 16), pady=12)

    def _build_content(self):
        """Build the split content area: session list + detail panel."""
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.grid(row=1, column=0, padx=16, pady=(0, 16), sticky="nsew")
        content.grid_columnconfigure(0, weight=2)
        content.grid_columnconfigure(1, weight=3)
        content.grid_rowconfigure(0, weight=1)

        # Left: scrollable session list
        self._list_frame = ctk.CTkScrollableFrame(
            content,
            fg_color=("#f8f8f8", "#141425"),
            corner_radius=12,
            label_text="Sessions",
            label_font=ctk.CTkFont(size=12, weight="bold"),
        )
        self._list_frame.grid(row=0, column=0, padx=(0, 8), sticky="nsew")
        self._list_frame.grid_columnconfigure(0, weight=1)

        # Right: detail panel
        self._detail_frame = ctk.CTkFrame(
            content,
            fg_color=("#f8f8f8", "#141425"),
            corner_radius=12,
        )
        self._detail_frame.grid(row=0, column=1, padx=(8, 0), sticky="nsew")
        self._detail_frame.grid_columnconfigure(0, weight=1)
        self._detail_frame.grid_rowconfigure(1, weight=1)

        # Detail header
        self._detail_header = ctk.CTkLabel(
            self._detail_frame,
            text="Select a session to view details",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=("#888", "#888"),
            anchor="w",
        )
        self._detail_header.grid(row=0, column=0, padx=16, pady=(16, 8), sticky="ew")

        # Detail text
        self._detail_text = ctk.CTkTextbox(
            self._detail_frame,
            font=ctk.CTkFont(family="Consolas", size=12),
            fg_color=("#ffffff", "#0d0d1a"),
            text_color=("#333333", "#d0d0d0"),
            corner_radius=8,
            wrap="none",
        )
        self._detail_text.grid(row=1, column=0, padx=12, pady=(0, 8), sticky="nsew")

        # Detail actions
        actions = ctk.CTkFrame(self._detail_frame, fg_color="transparent")
        actions.grid(row=2, column=0, padx=12, pady=(0, 12), sticky="ew")
        actions.grid_columnconfigure(2, weight=1)

        self._export_json_btn = ctk.CTkButton(
            actions, text="Export JSON", height=30, width=100, corner_radius=6,
            fg_color="#6c5ce7", hover_color="#5a4bd1",
            font=ctk.CTkFont(size=11),
            command=lambda: self._export_selected("json"),
            state="disabled",
        )
        self._export_json_btn.grid(row=0, column=0, padx=(0, 4))

        self._export_csv_btn = ctk.CTkButton(
            actions, text="Export CSV", height=30, width=100, corner_radius=6,
            fg_color="#00b894", hover_color="#00a381",
            font=ctk.CTkFont(size=11),
            command=lambda: self._export_selected("csv"),
            state="disabled",
        )
        self._export_csv_btn.grid(row=0, column=1, padx=4)

        self._delete_btn = ctk.CTkButton(
            actions, text="🗑 Delete", height=30, width=90, corner_radius=6,
            fg_color="#ff4757", hover_color="#ff3344",
            font=ctk.CTkFont(size=11),
            command=self._delete_selected,
            state="disabled",
        )
        self._delete_btn.grid(row=0, column=3, padx=(4, 0))

        self._selected_session_id: Optional[str] = None

    def _refresh_sessions(self):
        """Reload and display all sessions."""
        # Clear existing cards
        for widget in self._list_frame.winfo_children():
            widget.destroy()

        sessions = list_sessions()

        if not sessions:
            ctk.CTkLabel(
                self._list_frame,
                text="No sessions yet.\nStart recording with the Record tab.",
                font=ctk.CTkFont(size=13),
                text_color=("#888", "#888"),
                justify="center",
            ).grid(row=0, column=0, pady=40)
            return

        for i, session in enumerate(sessions):
            card = SessionCard(
                self._list_frame,
                session_id=session.session_id,
                process_name=session.process_name,
                pid=session.pid,
                start_time=session.start_time,
                duration=session.duration_seconds,
                samples=session.total_samples,
                exit_reason=session.exit_reason,
                on_click=self._show_session_detail,
            )
            card.grid(row=i, column=0, padx=4, pady=4, sticky="ew")

    def _show_session_detail(self, session_id: str):
        """Load and display the detailed report for a session."""
        self._selected_session_id = session_id

        sessions = list_sessions()
        session = next((s for s in sessions if s.session_id == session_id), None)
        if not session:
            return

        self._detail_header.configure(
            text=f"{session.process_name} (PID {session.pid}) — {session.session_id}",
            text_color=("#222", "#e0e0e0"),
        )

        # Load and analyze
        try:
            snapshots = load_session_snapshots(session_id)
            summary = analyze_session(session, snapshots)
            report = format_summary_text(summary)
        except FileNotFoundError:
            report = "Session log file not found."
        except Exception as e:
            report = f"Error loading session: {e}"

        self._detail_text.configure(state="normal")
        self._detail_text.delete("1.0", "end")
        self._detail_text.insert("1.0", report)
        self._detail_text.configure(state="disabled")

        # Enable buttons
        self._export_json_btn.configure(state="normal")
        self._export_csv_btn.configure(state="normal")
        self._delete_btn.configure(state="normal")

    def _export_selected(self, fmt: str):
        """Export the selected session via file dialog."""
        if not self._selected_session_id:
            return

        from tkinter import filedialog
        ext = fmt
        filepath = filedialog.asksaveasfilename(
            defaultextension=f".{ext}",
            filetypes=[(f"{fmt.upper()} files", f"*.{ext}")],
            initialfile=f"{self._selected_session_id}.{ext}",
        )
        if not filepath:
            return

        import subprocess
        import sys
        subprocess.Popen(
            [sys.executable, "-m", "esaiph.cli", "logs", "export",
             self._selected_session_id, "-f", fmt, "-o", filepath],
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
        )

    def _delete_selected(self):
        """Delete the selected session."""
        if not self._selected_session_id:
            return

        # Confirm
        dialog = ctk.CTkInputDialog(
            text=f"Type 'delete' to confirm deletion of session {self._selected_session_id}:",
            title="Confirm Delete",
        )
        result = dialog.get_input()
        if result and result.strip().lower() == "delete":
            delete_session(self._selected_session_id)
            self._selected_session_id = None
            self._detail_header.configure(text="Session deleted.", text_color="#ff4757")
            self._detail_text.configure(state="normal")
            self._detail_text.delete("1.0", "end")
            self._detail_text.configure(state="disabled")
            self._export_json_btn.configure(state="disabled")
            self._export_csv_btn.configure(state="disabled")
            self._delete_btn.configure(state="disabled")
            self._refresh_sessions()
