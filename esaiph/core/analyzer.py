"""Session analyzer — post-processes recorded data into human-readable summaries."""

from __future__ import annotations

import math
from typing import Optional

from .logger_config import get_logger
from .models import ProcessSnapshot, SessionInfo, SessionSummary
from .recorder import load_session_snapshots

logger = get_logger("analyzer")


def analyze_session(
    session: SessionInfo,
    snapshots: Optional[list[ProcessSnapshot]] = None,
    cpu_spike_threshold: float = 80.0,
) -> SessionSummary:
    """Analyze a recorded session and produce a comprehensive summary.

    Args:
        session: SessionInfo metadata for the session.
        snapshots: Pre-loaded snapshots. If None, loads from disk.
        cpu_spike_threshold: CPU % above which a sample is flagged as a spike.

    Returns:
        SessionSummary with aggregated statistics, trends, and warnings.
    """
    if snapshots is None:
        snapshots = load_session_snapshots(session.session_id)

    if not snapshots:
        logger.warning("No snapshots found for session %s", session.session_id)
        return SessionSummary(session=session, warnings=["No data collected."])

    summary = SessionSummary(session=session)

    # ── CPU Analysis ──
    cpu_values = [s.cpu.percent for s in snapshots]
    summary.cpu_avg = _mean(cpu_values)
    summary.cpu_min = min(cpu_values)
    summary.cpu_max = max(cpu_values)
    summary.cpu_stddev = _stddev(cpu_values)

    for s in snapshots:
        if s.cpu.percent > cpu_spike_threshold:
            summary.cpu_spikes.append({
                "timestamp": s.timestamp,
                "cpu_percent": s.cpu.percent,
            })

    if summary.cpu_spikes:
        summary.warnings.append(
            f"CPU spiked above {cpu_spike_threshold}% in {len(summary.cpu_spikes)} samples "
            f"(peak: {summary.cpu_max:.1f}%)"
        )

    # ── Memory Analysis ──
    mem_mb_values = [s.memory.rss / (1024 * 1024) for s in snapshots]
    summary.memory_avg_mb = _mean(mem_mb_values)
    summary.memory_min_mb = min(mem_mb_values)
    summary.memory_max_mb = max(mem_mb_values)
    summary.memory_trend = _detect_trend(mem_mb_values)

    # Memory leak detection: check if memory grows monotonically over time
    if len(mem_mb_values) >= 10:
        # Compare first quarter average to last quarter average
        quarter = len(mem_mb_values) // 4
        first_avg = _mean(mem_mb_values[:quarter])
        last_avg = _mean(mem_mb_values[-quarter:])
        growth_pct = ((last_avg - first_avg) / first_avg * 100) if first_avg > 0 else 0

        if growth_pct > 20 and summary.memory_trend == "growing":
            summary.potential_memory_leak = True
            summary.warnings.append(
                f"Potential memory leak detected: memory grew {growth_pct:.1f}% "
                f"from {first_avg:.1f} MB to {last_avg:.1f} MB over the session."
            )

    # ── I/O Analysis ──
    io_snapshots = [s for s in snapshots if s.io is not None]
    if len(io_snapshots) >= 2:
        first_io = io_snapshots[0].io
        last_io = io_snapshots[-1].io
        summary.total_read_bytes = last_io.read_bytes - first_io.read_bytes
        summary.total_write_bytes = last_io.write_bytes - first_io.write_bytes
        summary.total_read_ops = last_io.read_count - first_io.read_count
        summary.total_write_ops = last_io.write_count - first_io.write_count

    # ── Network Analysis ──
    net_snapshots = [s for s in snapshots if s.network is not None]
    if len(net_snapshots) >= 2:
        first_net = net_snapshots[0].network
        last_net = net_snapshots[-1].network
        summary.total_net_sent = last_net.bytes_sent - first_net.bytes_sent
        summary.total_net_recv = last_net.bytes_recv - first_net.bytes_recv

    # ── Thread Analysis ──
    thread_counts = [s.num_threads for s in snapshots]
    summary.thread_count_avg = _mean(thread_counts)
    summary.thread_count_max = max(thread_counts)

    # ── Files & Handles ──
    summary.max_open_files = max(len(s.open_files) for s in snapshots)
    summary.max_handles = max(s.num_handles for s in snapshots)

    if summary.max_open_files > 100:
        summary.warnings.append(
            f"High number of open files detected (max: {summary.max_open_files})"
        )

    if summary.max_handles > 1000:
        summary.warnings.append(
            f"High handle count detected (max: {summary.max_handles})"
        )

    # ── Status Changes ──
    prev_status = None
    for s in snapshots:
        if s.status != prev_status and prev_status is not None:
            summary.status_changes.append({
                "timestamp": s.timestamp,
                "from": prev_status,
                "to": s.status,
            })
        prev_status = s.status

    # ── Child Process Events ──
    prev_children: set[int] = set()
    for s in snapshots:
        current_children = set(s.children_pids)
        spawned = current_children - prev_children
        terminated = prev_children - current_children
        for pid in spawned:
            summary.child_process_events.append({
                "timestamp": s.timestamp,
                "event": "spawned",
                "pid": pid,
            })
        for pid in terminated:
            summary.child_process_events.append({
                "timestamp": s.timestamp,
                "event": "terminated",
                "pid": pid,
            })
        prev_children = current_children

    return summary


def format_summary_text(summary: SessionSummary) -> str:
    """Format a SessionSummary into a human-readable text report."""
    s = summary.session
    lines: list[str] = []

    lines.append("=" * 70)
    lines.append(f"  eSaiph Session Report — {s.session_id}")
    lines.append("=" * 70)
    lines.append("")

    # Session info
    lines.append("┌─ Session Info ─────────────────────────────────────────────────┐")
    lines.append(f"│  Process:    {s.process_name} (PID {s.pid})")
    lines.append(f"│  Command:    {s.command_line or 'N/A'}")
    lines.append(f"│  Started:    {s.start_time}")
    lines.append(f"│  Ended:      {s.end_time}")
    lines.append(f"│  Duration:   {_format_duration(s.duration_seconds)}")
    lines.append(f"│  Samples:    {s.total_samples} (every {s.sample_interval:.1f}s)")
    lines.append(f"│  Exit:       {s.exit_reason} (code: {s.exit_code})")
    lines.append("└────────────────────────────────────────────────────────────────┘")
    lines.append("")

    # CPU
    lines.append("┌─ CPU Usage ─────────────────────────────────────────────────────┐")
    lines.append(f"│  Average:    {summary.cpu_avg:.1f}%")
    lines.append(f"│  Min:        {summary.cpu_min:.1f}%")
    lines.append(f"│  Max:        {summary.cpu_max:.1f}%")
    lines.append(f"│  Std Dev:    {summary.cpu_stddev:.1f}%")
    lines.append(f"│  Spikes:     {len(summary.cpu_spikes)} (>{80}%)")
    lines.append("└────────────────────────────────────────────────────────────────┘")
    lines.append("")

    # Memory
    leak_indicator = " ⚠ POSSIBLE LEAK" if summary.potential_memory_leak else ""
    lines.append("┌─ Memory Usage ──────────────────────────────────────────────────┐")
    lines.append(f"│  Average:    {summary.memory_avg_mb:.1f} MB")
    lines.append(f"│  Min:        {summary.memory_min_mb:.1f} MB")
    lines.append(f"│  Max:        {summary.memory_max_mb:.1f} MB")
    lines.append(f"│  Trend:      {summary.memory_trend}{leak_indicator}")
    lines.append("└────────────────────────────────────────────────────────────────┘")
    lines.append("")

    # I/O
    lines.append("┌─ Disk I/O ──────────────────────────────────────────────────────┐")
    lines.append(f"│  Read:       {_format_bytes(summary.total_read_bytes)} ({summary.total_read_ops} ops)")
    lines.append(f"│  Written:    {_format_bytes(summary.total_write_bytes)} ({summary.total_write_ops} ops)")
    lines.append("└────────────────────────────────────────────────────────────────┘")
    lines.append("")

    # Network
    lines.append("┌─ Network I/O ───────────────────────────────────────────────────┐")
    lines.append(f"│  Sent:       {_format_bytes(summary.total_net_sent)}")
    lines.append(f"│  Received:   {_format_bytes(summary.total_net_recv)}")
    lines.append("└────────────────────────────────────────────────────────────────┘")
    lines.append("")

    # Threads & Handles
    lines.append("┌─ Threads & Handles ─────────────────────────────────────────────┐")
    lines.append(f"│  Threads:    avg {summary.thread_count_avg:.1f}, max {summary.thread_count_max}")
    lines.append(f"│  Open Files: max {summary.max_open_files}")
    lines.append(f"│  Handles:    max {summary.max_handles}")
    lines.append("└────────────────────────────────────────────────────────────────┘")
    lines.append("")

    # Status changes
    if summary.status_changes:
        lines.append("┌─ Status Changes ───────────────────────────────────────────────┐")
        for change in summary.status_changes:
            lines.append(f"│  {change['timestamp']}: {change['from']} → {change['to']}")
        lines.append("└────────────────────────────────────────────────────────────────┘")
        lines.append("")

    # Child process events
    if summary.child_process_events:
        lines.append("┌─ Child Process Events ─────────────────────────────────────────┐")
        for event in summary.child_process_events:
            lines.append(f"│  {event['timestamp']}: PID {event['pid']} {event['event']}")
        lines.append("└────────────────────────────────────────────────────────────────┘")
        lines.append("")

    # Warnings
    if summary.warnings:
        lines.append("┌─ ⚠ Warnings ───────────────────────────────────────────────────┐")
        for warning in summary.warnings:
            lines.append(f"│  • {warning}")
        lines.append("└────────────────────────────────────────────────────────────────┘")
        lines.append("")

    return "\n".join(lines)


# ── Helper functions ──

def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _stddev(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    avg = _mean(values)
    variance = sum((v - avg) ** 2 for v in values) / (len(values) - 1)
    return math.sqrt(variance)


def _detect_trend(values: list[float]) -> str:
    """Detect whether a series is growing, shrinking, stable, or erratic."""
    if len(values) < 5:
        return "insufficient_data"

    # Simple linear regression slope
    n = len(values)
    x_mean = (n - 1) / 2
    y_mean = _mean(values)
    numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
    denominator = sum((i - x_mean) ** 2 for i in range(n))

    if denominator == 0:
        return "stable"

    slope = numerator / denominator
    relative_slope = slope / y_mean if y_mean != 0 else 0

    # Check variability
    cv = _stddev(values) / y_mean if y_mean != 0 else 0

    if cv > 0.3:
        return "erratic"
    elif relative_slope > 0.01:
        return "growing"
    elif relative_slope < -0.01:
        return "shrinking"
    else:
        return "stable"


def _format_bytes(num_bytes: int) -> str:
    """Format bytes into human-readable string."""
    if num_bytes == 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    value = float(num_bytes)
    while value >= 1024 and i < len(units) - 1:
        value /= 1024
        i += 1
    return f"{value:.1f} {units[i]}"


def _format_duration(seconds: float) -> str:
    """Format seconds into human-readable duration."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        m = int(seconds // 60)
        s = seconds % 60
        return f"{m}m {s:.0f}s"
    else:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        return f"{h}h {m}m"
