"""RecordView — The main recording dashboard with live metrics."""

from __future__ import annotations

import threading
from typing import Optional

import customtkinter as ctk
import psutil

from ..components.gauge_widget import GaugeWidget
from ..components.metric_card import MetricCard
from ..components.status_badge import StatusBadge
from ...core.collector import (
    AccessDeniedError,
    ProcessNotFoundError,
    find_process_by_name,
    get_process_info,
)
from ...core.models import ProcessSnapshot
from ...core.recorder import RecordingSession


class RecordView(ctk.CTkFrame):
    """Recording dashboard: process selection, start/stop, live metrics display."""

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        self._session: Optional[RecordingSession] = None
        self._update_job = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._build_controls()
        self._build_status_bar()
        self._build_dashboard()

    def _build_controls(self):
        """Build the top control bar with process input and buttons."""
        controls = ctk.CTkFrame(self, fg_color=("#f0f0f0", "#1a1a2e"), corner_radius=12)
        controls.grid(row=0, column=0, padx=16, pady=(16, 8), sticky="ew")
        controls.grid_columnconfigure(1, weight=1)

        # PID / Name input
        ctk.CTkLabel(
            controls,
            text="Process:",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=0, column=0, padx=(16, 8), pady=12)

        self._pid_entry = ctk.CTkEntry(
            controls,
            placeholder_text="Enter PID or process name...",
            height=36,
            font=ctk.CTkFont(size=13),
            corner_radius=8,
        )
        self._pid_entry.grid(row=0, column=1, padx=4, pady=12, sticky="ew")
        self._pid_entry.bind("<Return>", lambda e: self._start_recording())

        # Interval
        ctk.CTkLabel(
            controls,
            text="Interval:",
            font=ctk.CTkFont(size=12),
        ).grid(row=0, column=2, padx=(12, 4), pady=12)

        self._interval_var = ctk.StringVar(value="1.0")
        self._interval_entry = ctk.CTkEntry(
            controls,
            textvariable=self._interval_var,
            width=60,
            height=36,
            font=ctk.CTkFont(size=13),
            corner_radius=8,
        )
        self._interval_entry.grid(row=0, column=3, padx=4, pady=12)

        ctk.CTkLabel(controls, text="s", font=ctk.CTkFont(size=12)).grid(
            row=0, column=4, padx=(0, 8), pady=12
        )

        # Start button
        self._start_btn = ctk.CTkButton(
            controls,
            text="▶ Record",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#00d4aa",
            hover_color="#00b894",
            text_color="#000000",
            height=36,
            corner_radius=8,
            width=110,
            command=self._start_recording,
        )
        self._start_btn.grid(row=0, column=5, padx=4, pady=12)

        # Stop button
        self._stop_btn = ctk.CTkButton(
            controls,
            text="■ Stop",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#ff4757",
            hover_color="#ff3344",
            text_color="#ffffff",
            height=36,
            corner_radius=8,
            width=90,
            command=self._stop_recording,
            state="disabled",
        )
        self._stop_btn.grid(row=0, column=6, padx=(4, 16), pady=12)

    def _build_status_bar(self):
        """Build the status bar showing recording state."""
        status_frame = ctk.CTkFrame(self, fg_color="transparent")
        status_frame.grid(row=1, column=0, padx=16, pady=(0, 4), sticky="ew")
        status_frame.grid_columnconfigure(1, weight=1)

        self._status_badge = StatusBadge(status_frame, state="idle")
        self._status_badge.grid(row=0, column=0, sticky="w")

        self._info_label = ctk.CTkLabel(
            status_frame,
            text="Ready to record. Enter a PID or process name above.",
            font=ctk.CTkFont(size=12),
            text_color=("#888888", "#888888"),
            anchor="e",
        )
        self._info_label.grid(row=0, column=1, padx=(12, 0), sticky="e")

    def _build_dashboard(self):
        """Build the live metrics dashboard area."""
        dashboard = ctk.CTkFrame(self, fg_color="transparent")
        dashboard.grid(row=2, column=0, padx=16, pady=(8, 16), sticky="nsew")
        dashboard.grid_columnconfigure((0, 1, 2, 3), weight=1)
        dashboard.grid_rowconfigure((0, 1, 2), weight=1)

        self._dashboard = dashboard

        # Row 0: Gauges
        self._cpu_gauge = GaugeWidget(dashboard, size=150, label="CPU")
        self._cpu_gauge.grid(row=0, column=0, padx=8, pady=8, sticky="n")

        self._mem_gauge = GaugeWidget(dashboard, size=150, label="Memory")
        self._mem_gauge.grid(row=0, column=1, padx=8, pady=8, sticky="n")

        # Row 0, right side: key metrics
        metrics_right = ctk.CTkFrame(dashboard, fg_color="transparent")
        metrics_right.grid(row=0, column=2, columnspan=2, padx=8, pady=8, sticky="nsew")
        metrics_right.grid_columnconfigure((0, 1), weight=1)
        metrics_right.grid_rowconfigure((0, 1), weight=1)

        self._mem_card = MetricCard(metrics_right, label="Memory", value="0.0", unit="MB", show_bar=True, color="#6c5ce7")
        self._mem_card.grid(row=0, column=0, padx=4, pady=4, sticky="nsew")

        self._threads_card = MetricCard(metrics_right, label="Threads", value="0", color="#fd79a8")
        self._threads_card.grid(row=0, column=1, padx=4, pady=4, sticky="nsew")

        self._handles_card = MetricCard(metrics_right, label="Handles", value="0", color="#fdcb6e")
        self._handles_card.grid(row=1, column=0, padx=4, pady=4, sticky="nsew")

        self._files_card = MetricCard(metrics_right, label="Open Files", value="0", color="#74b9ff")
        self._files_card.grid(row=1, column=1, padx=4, pady=4, sticky="nsew")

        # Row 1: I/O & Network
        io_frame = ctk.CTkFrame(dashboard, fg_color="transparent")
        io_frame.grid(row=1, column=0, columnspan=4, padx=8, pady=4, sticky="ew")
        io_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self._disk_read_card = MetricCard(io_frame, label="Disk Read", value="0.0", unit="MB", color="#00cec9")
        self._disk_read_card.grid(row=0, column=0, padx=4, pady=4, sticky="ew")

        self._disk_write_card = MetricCard(io_frame, label="Disk Write", value="0.0", unit="MB", color="#e17055")
        self._disk_write_card.grid(row=0, column=1, padx=4, pady=4, sticky="ew")

        self._net_sent_card = MetricCard(io_frame, label="Net Sent", value="0.0", unit="MB", color="#a29bfe")
        self._net_sent_card.grid(row=0, column=2, padx=4, pady=4, sticky="ew")

        self._net_recv_card = MetricCard(io_frame, label="Net Recv", value="0.0", unit="MB", color="#55efc4")
        self._net_recv_card.grid(row=0, column=3, padx=4, pady=4, sticky="ew")

        # Row 2: Children and status
        bottom_frame = ctk.CTkFrame(dashboard, fg_color="transparent")
        bottom_frame.grid(row=2, column=0, columnspan=4, padx=8, pady=4, sticky="ew")
        bottom_frame.grid_columnconfigure((0, 1), weight=1)

        self._children_card = MetricCard(bottom_frame, label="Child Processes", value="0", color="#dfe6e9")
        self._children_card.grid(row=0, column=0, padx=4, pady=4, sticky="ew")

        self._status_card = MetricCard(bottom_frame, label="Process Status", value="—", color="#00d4aa")
        self._status_card.grid(row=0, column=1, padx=4, pady=4, sticky="ew")

    def _start_recording(self):
        """Start a recording session."""
        input_text = self._pid_entry.get().strip()
        if not input_text:
            self._info_label.configure(text="⚠ Please enter a PID or process name.", text_color="#ff4757")
            return

        # Try to parse as PID first
        pid = None
        try:
            pid = int(input_text)
        except ValueError:
            # Search by name
            matches = find_process_by_name(input_text)
            if not matches:
                self._info_label.configure(text=f"⚠ No process found matching '{input_text}'.", text_color="#ff4757")
                return
            if len(matches) > 1:
                self._info_label.configure(
                    text=f"⚠ {len(matches)} processes match '{input_text}'. Please use a PID.",
                    text_color="#ffa502",
                )
                return
            pid = matches[0].pid

        # Get interval
        try:
            interval = float(self._interval_var.get())
        except ValueError:
            interval = 1.0

        # Verify process
        info = get_process_info(pid)
        if "error" in info:
            self._info_label.configure(text=f"⚠ {info['error']}", text_color="#ff4757")
            return

        # Start recording
        try:
            self._session = RecordingSession(
                pid=pid,
                interval=interval,
                on_stopped=self._on_session_stopped,
            )
            self._session.start()
        except (ProcessNotFoundError, AccessDeniedError) as e:
            self._info_label.configure(text=f"⚠ {e}", text_color="#ff4757")
            return

        # Update UI
        self._status_badge.set_state("recording")
        self._info_label.configure(
            text=f"Recording {info['name']} (PID {pid}) — Session {self._session.session_id}",
            text_color="#00d4aa",
        )
        self._start_btn.configure(state="disabled")
        self._stop_btn.configure(state="normal")
        self._pid_entry.configure(state="disabled")

        # Start UI updates
        self._schedule_update()

    def _stop_recording(self):
        """Stop the current recording."""
        if self._session and self._session.is_running:
            self._session.stop("manual_stop")

        self._on_recording_ended()

    def _on_session_stopped(self, session_info):
        """Callback when the session stops (e.g. process exited)."""
        # Schedule UI update on main thread
        self.after(0, self._on_recording_ended)

    def _on_recording_ended(self):
        """Update UI after recording ends."""
        if self._update_job:
            self.after_cancel(self._update_job)
            self._update_job = None

        self._status_badge.set_state("stopped")
        self._start_btn.configure(state="normal")
        self._stop_btn.configure(state="disabled")
        self._pid_entry.configure(state="normal")

        if self._session:
            info = self._session.get_session_info()
            self._info_label.configure(
                text=f"Stopped — {info.total_samples} samples in {info.duration_seconds:.1f}s. "
                     f"Session: {info.session_id}",
                text_color="#ffa502",
            )

    def _schedule_update(self):
        """Schedule periodic UI updates for live metrics."""
        if self._session and self._session.is_running:
            self._update_dashboard()
            self._update_job = self.after(500, self._schedule_update)

    def _update_dashboard(self):
        """Update all dashboard widgets with latest snapshot data."""
        snap = self._session.latest_snapshot if self._session else None
        if not snap:
            return

        # CPU gauge
        self._cpu_gauge.set_value(snap.cpu.percent)

        # Memory gauge
        self._mem_gauge.set_value(snap.memory.percent)

        # Memory card
        mem_mb = snap.memory.rss / (1024 * 1024)
        self._mem_card.update_value(f"{mem_mb:.1f}", snap.memory.percent)

        # Threads
        self._threads_card.update_value(str(snap.num_threads))

        # Handles
        self._handles_card.update_value(str(snap.num_handles))

        # Open files
        self._files_card.update_value(str(len(snap.open_files)))

        # Disk I/O
        if snap.io:
            self._disk_read_card.update_value(f"{snap.io.read_bytes / (1024*1024):.1f}")
            self._disk_write_card.update_value(f"{snap.io.write_bytes / (1024*1024):.1f}")

        # Network
        if snap.network:
            self._net_sent_card.update_value(f"{snap.network.bytes_sent / (1024*1024):.1f}")
            self._net_recv_card.update_value(f"{snap.network.bytes_recv / (1024*1024):.1f}")

        # Children
        self._children_card.update_value(str(len(snap.children_pids)))

        # Status
        self._status_card.update_value(snap.status)

    def destroy(self):
        """Clean up on destroy."""
        if self._update_job:
            self.after_cancel(self._update_job)
        if self._session and self._session.is_running:
            self._session.stop("gui_closed")
        super().destroy()
