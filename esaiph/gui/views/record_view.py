"""RecordView — Polished dashboard with live charts.

Layout (matches reference dashboard):
┌──────────┬──────────┬──────────┬──────┬──────────┐
│  CPU %   │ Memory   │ Threads  │ Hdls │ Children │
├──────────┴──────────┴──────────┴──────┴──────────┤
│  Resource Timeline (line chart)  │  Distribution  │
│  CPU + Memory over time          │  (donut chart) │
├──────────┬──────────┬──────────┬─────────────────│
│ Disk Rd  │ Disk Wr  │ Net Sent │ Net Recv        │
└──────────┴──────────┴──────────┴─────────────────┘
"""

from __future__ import annotations

from typing import Optional

import customtkinter as ctk

from ..components.live_chart import LiveChart
from ..components.donut_chart import DonutChart
from ..components.metric_card import MetricCard
from ..components.status_badge import StatusBadge
from ..theme import (
    BG_BASE, BG_CARD, BG_INPUT,
    BORDER, BORDER_HOVER,
    TEXT_MAIN, TEXT_MUTED, TEXT_DIM,
    PINK, PINK_HOVER, PURPLE, PURPLE_SOFT, MAGENTA,
    ACCENT_CYAN, ACCENT_GREEN,
    SUCCESS, ERROR, WARNING,
    FONT_BODY, FONT_HEADING,
    RADIUS_SM, RADIUS_LG,
)
from ...core.collector import (
    AccessDeniedError,
    ProcessNotFoundError,
    find_process_by_name,
    get_process_info,
)
from ...core.recorder import RecordingSession


class RecordView(ctk.CTkFrame):
    """Full dashboard with live line chart and donut chart."""

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=BG_BASE, corner_radius=0, **kwargs)

        self._session: Optional[RecordingSession] = None
        self._update_job = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)  # charts row grows

        self._build_header()
        self._build_hero_row()
        self._build_charts_row()
        self._build_io_row()

    # ── HEADER + CONTROLS ──

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=RADIUS_LG,
                              border_width=1, border_color=BORDER)
        header.grid(row=0, column=0, padx=24, pady=(20, 0), sticky="ew")
        header.grid_columnconfigure(1, weight=1)

        # Left: title + subtitle
        left = ctk.CTkFrame(header, fg_color="transparent")
        left.grid(row=0, column=0, padx=18, pady=14, sticky="w")

        t = ctk.CTkFrame(left, fg_color="transparent")
        t.pack(anchor="w")
        ctk.CTkLabel(t, text="Dashboard",
                     font=ctk.CTkFont(family=FONT_HEADING, size=20, weight="bold"),
                     text_color=TEXT_MAIN).pack(side="left")
        self._status_badge = StatusBadge(t, state="idle")
        self._status_badge.pack(side="left", padx=(12, 0))

        self._info_label = ctk.CTkLabel(
            left, text="Enter a PID or process name to start recording.",
            font=ctk.CTkFont(family=FONT_BODY, size=11),
            text_color=TEXT_MUTED, anchor="w",
        )
        self._info_label.pack(anchor="w", pady=(2, 0))

        # Right: controls
        right = ctk.CTkFrame(header, fg_color="transparent")
        right.grid(row=0, column=1, padx=18, pady=14, sticky="e")

        self._pid_entry = ctk.CTkEntry(
            right, placeholder_text="PID or name...",
            width=180, height=34,
            font=ctk.CTkFont(family=FONT_BODY, size=12),
            corner_radius=RADIUS_SM,
            fg_color=BG_INPUT, border_width=1, border_color=BORDER,
            text_color=TEXT_MAIN, placeholder_text_color=TEXT_DIM,
        )
        self._pid_entry.pack(side="left", padx=(0, 6))
        self._pid_entry.bind("<Return>", lambda e: self._start_recording())

        self._interval_var = ctk.StringVar(value="1.0")
        ctk.CTkEntry(
            right, textvariable=self._interval_var,
            width=45, height=34,
            font=ctk.CTkFont(family=FONT_BODY, size=12),
            corner_radius=RADIUS_SM,
            fg_color=BG_INPUT, border_width=1, border_color=BORDER,
            text_color=TEXT_MAIN, justify="center",
        ).pack(side="left", padx=(0, 2))

        ctk.CTkLabel(right, text="s", font=ctk.CTkFont(size=11),
                     text_color=TEXT_DIM).pack(side="left", padx=(0, 8))

        self._start_btn = ctk.CTkButton(
            right, text="⦿ Record", width=100, height=34,
            font=ctk.CTkFont(family=FONT_BODY, size=12, weight="bold"),
            fg_color=PINK, hover_color=PINK_HOVER, text_color="#fff",
            corner_radius=RADIUS_SM, command=self._start_recording,
        )
        self._start_btn.pack(side="left", padx=(0, 4))

        self._stop_btn = ctk.CTkButton(
            right, text="■ Stop", width=80, height=34,
            font=ctk.CTkFont(family=FONT_BODY, size=12, weight="bold"),
            fg_color=BG_INPUT, hover_color=("#fde8e8", "#2a1020"),
            text_color=ERROR, border_width=1, border_color=BORDER,
            corner_radius=RADIUS_SM, command=self._stop_recording,
            state="disabled",
        )
        self._stop_btn.pack(side="left")

    # ── HERO STAT CARDS ──

    def _build_hero_row(self):
        hero = ctk.CTkFrame(self, fg_color="transparent")
        hero.grid(row=1, column=0, padx=24, pady=(12, 0), sticky="ew")
        hero.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

        self._cpu_card = MetricCard(hero, label="CPU", value="0.0", unit="%",
                                    accent_color=PINK, show_bar=True)
        self._cpu_card.grid(row=0, column=0, padx=(0, 4), sticky="ew")

        self._mem_card = MetricCard(hero, label="Memory", value="0.0", unit="MB",
                                    accent_color=PURPLE_SOFT, show_bar=True)
        self._mem_card.grid(row=0, column=1, padx=4, sticky="ew")

        self._threads_card = MetricCard(hero, label="Threads", value="0",
                                        accent_color=ACCENT_CYAN)
        self._threads_card.grid(row=0, column=2, padx=4, sticky="ew")

        self._handles_card = MetricCard(hero, label="Handles", value="0",
                                        accent_color=MAGENTA)
        self._handles_card.grid(row=0, column=3, padx=4, sticky="ew")

        self._files_card = MetricCard(hero, label="Open Files", value="0",
                                      accent_color=ACCENT_GREEN)
        self._files_card.grid(row=0, column=4, padx=(4, 0), sticky="ew")

    # ── CHARTS ROW ──

    def _build_charts_row(self):
        charts = ctk.CTkFrame(self, fg_color="transparent")
        charts.grid(row=2, column=0, padx=24, pady=(10, 0), sticky="nsew")
        charts.grid_columnconfigure(0, weight=3)
        charts.grid_columnconfigure(1, weight=2)
        charts.grid_rowconfigure(0, weight=1)

        # Line chart
        self._line_chart = LiveChart(
            charts,
            title="Resource Timeline",
            subtitle="Live system metrics",
            series_names=["CPU %", "Memory %"],
            max_points=60,
            y_label="%",
            y_max=100,
        )
        self._line_chart.grid(row=0, column=0, padx=(0, 5), sticky="nsew")

        # Donut chart
        self._donut = DonutChart(
            charts,
            title="Resource Split",
            subtitle="Current allocation",
        )
        self._donut.grid(row=0, column=1, padx=(5, 0), sticky="nsew")

    # ── BOTTOM I/O ROW ──

    def _build_io_row(self):
        io_row = ctk.CTkFrame(self, fg_color="transparent")
        io_row.grid(row=3, column=0, padx=24, pady=(10, 18), sticky="ew")
        io_row.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self._disk_read_card = MetricCard(io_row, label="Disk Read", value="0.0",
                                          unit="MB", accent_color=ACCENT_CYAN)
        self._disk_read_card.grid(row=0, column=0, padx=(0, 4), sticky="ew")

        self._disk_write_card = MetricCard(io_row, label="Disk Write", value="0.0",
                                           unit="MB", accent_color="#f97316")
        self._disk_write_card.grid(row=0, column=1, padx=4, sticky="ew")

        self._net_sent_card = MetricCard(io_row, label="Net Sent", value="0.0",
                                         unit="MB", accent_color=PURPLE_SOFT)
        self._net_sent_card.grid(row=0, column=2, padx=4, sticky="ew")

        self._net_recv_card = MetricCard(io_row, label="Net Recv", value="0.0",
                                         unit="MB", accent_color=ACCENT_GREEN)
        self._net_recv_card.grid(row=0, column=3, padx=(4, 0), sticky="ew")

    # ── RECORDING LOGIC ──

    def _start_recording(self):
        input_text = self._pid_entry.get().strip()
        if not input_text:
            self._info_label.configure(text="Please enter a PID or process name.", text_color=ERROR)
            return

        pid = None
        try:
            pid = int(input_text)
        except ValueError:
            matches = find_process_by_name(input_text)
            if not matches:
                self._info_label.configure(text=f"No process found matching '{input_text}'.", text_color=ERROR)
                return
            if len(matches) > 1:
                self._info_label.configure(text=f"{len(matches)} matches — use a PID.", text_color=WARNING)
                return
            pid = matches[0].pid

        try:
            interval = float(self._interval_var.get())
        except ValueError:
            interval = 1.0

        info = get_process_info(pid)
        if "error" in info:
            self._info_label.configure(text=str(info["error"]), text_color=ERROR)
            return

        try:
            self._session = RecordingSession(pid=pid, interval=interval,
                                             on_stopped=self._on_session_stopped)
            self._session.start()
        except (ProcessNotFoundError, AccessDeniedError) as e:
            self._info_label.configure(text=str(e), text_color=ERROR)
            return

        self._status_badge.set_state("recording")
        self._info_label.configure(
            text=f"Recording {info['name']} (PID {pid})  ·  {self._session.session_id}",
            text_color=SUCCESS,
        )
        self._start_btn.configure(state="disabled")
        self._stop_btn.configure(state="normal")
        self._pid_entry.configure(state="disabled")
        self._schedule_update()

    def _stop_recording(self):
        if self._session and self._session.is_running:
            self._session.stop("manual_stop")
        self._on_recording_ended()

    def _on_session_stopped(self, session_info):
        self.after(0, self._on_recording_ended)

    def _on_recording_ended(self):
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
                text=f"Stopped — {info.total_samples} samples in {info.duration_seconds:.1f}s  ·  {info.session_id}",
                text_color=WARNING,
            )

    def _schedule_update(self):
        if self._session and self._session.is_running:
            self._update_dashboard()
            self._update_job = self.after(800, self._schedule_update)

    def _update_dashboard(self):
        snap = self._session.latest_snapshot if self._session else None
        if not snap:
            return

        # Stat cards
        cpu = snap.cpu.percent
        mem_pct = snap.memory.percent
        mem_mb = snap.memory.rss / (1024 * 1024)

        self._cpu_card.update_value(f"{cpu:.1f}", cpu)
        self._mem_card.update_value(f"{mem_mb:.1f}", mem_pct)
        self._threads_card.update_value(str(snap.num_threads))
        self._handles_card.update_value(str(snap.num_handles))
        self._files_card.update_value(str(len(snap.open_files)))

        # Line chart
        self._line_chart.add_values(**{"CPU %": cpu, "Memory %": mem_pct})

        # Donut chart
        other = max(0, 100 - cpu - mem_pct)
        self._donut.update_data(
            labels=["CPU", "Memory", "Available"],
            values=[cpu, mem_pct, other],
            center_text=f"{cpu + mem_pct:.0f}%",
        )

        # I/O cards
        if snap.io:
            self._disk_read_card.update_value(f"{snap.io.read_bytes / (1024*1024):.1f}")
            self._disk_write_card.update_value(f"{snap.io.write_bytes / (1024*1024):.1f}")
        if snap.network:
            self._net_sent_card.update_value(f"{snap.network.bytes_sent / (1024*1024):.1f}")
            self._net_recv_card.update_value(f"{snap.network.bytes_recv / (1024*1024):.1f}")

    def refresh_theme(self):
        pass  # Charts auto-refresh on next data update

    def destroy(self):
        if self._update_job:
            self.after_cancel(self._update_job)
        if self._session and self._session.is_running:
            self._session.stop("gui_closed")
        super().destroy()
