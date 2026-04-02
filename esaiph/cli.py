"""eSaiph CLI — Command-line interface for software testing and monitoring."""

from __future__ import annotations

import csv
import json
import os
import signal
import sys
import time
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text

from .core.analyzer import analyze_session, format_summary_text
from .core.collector import (
    AccessDeniedError,
    ProcessNotFoundError,
    find_process_by_name,
    get_process_info,
)
from .core.logger_config import setup_logging
from .core.recorder import (
    DEFAULT_SESSIONS_DIR,
    RecordingSession,
    delete_session,
    list_sessions,
    load_session_snapshots,
)

# Force Rich to use UTF-8 on Windows to avoid cp1252 encoding errors
import io, sys
if sys.platform == "win32" and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

console = Console(highlight=False)


@click.group()
@click.version_option(version="0.1.0", prog_name="eSaiph")
def cli():
    """eSaiph — Software Testing & Monitoring Tool.

    Record detailed process metrics for later analysis. Provides far more detail
    than Task Manager, including CPU, memory, disk I/O, network, threads,
    open files, handles, and child process tracking.
    """
    setup_logging()


# ── Record Command ──

@cli.command()
@click.option("--pid", type=int, default=None, help="Process ID to monitor.")
@click.option("--name", type=str, default=None, help="Process name to monitor (partial match).")
@click.option("--duration", "-d", type=float, default=None, help="Auto-stop after N seconds.")
@click.option("--interval", "-i", type=float, default=1.0, help="Sampling interval in seconds.")
@click.option("--quiet", "-q", is_flag=True, help="Suppress live output.")
def record(pid: Optional[int], name: Optional[str], duration: Optional[float], interval: float, quiet: bool):
    """Start recording a process's resource usage.

    You must specify either --pid or --name. When using --name, if multiple
    processes match, you'll be prompted to select one.

    Press Ctrl+C to stop recording.
    """
    if pid is None and name is None:
        console.print("[red]Error:[/red] You must specify either --pid or --name.")
        raise SystemExit(1)

    # Resolve process
    if name and pid is None:
        pid = _resolve_process_by_name(name)
        if pid is None:
            raise SystemExit(1)

    # Show process info
    info = get_process_info(pid)
    if "error" in info:
        console.print(f"[red]Error:[/red] {info['error']}")
        raise SystemExit(1)

    console.print()
    console.print(Panel(
        f"[bold cyan]Process:[/bold cyan]  {info['name']}  (PID {info['pid']})\n"
        f"[bold cyan]Command:[/bold cyan]  {info.get('cmdline', 'N/A')}\n"
        f"[bold cyan]Status:[/bold cyan]   {info.get('status', 'N/A')}\n"
        f"[bold cyan]User:[/bold cyan]     {info.get('username', 'N/A')}",
        title="[bold]Target Process[/bold]",
        border_style="cyan",
    ))

    # Start recording
    try:
        session_record = RecordingSession(
            pid=pid,
            interval=interval,
            duration=duration,
        )
        session_info = session_record.start()
    except (ProcessNotFoundError, AccessDeniedError) as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)

    console.print(f"\n[green]● Recording started[/green] — Session [bold]{session_info.session_id}[/bold]")
    if duration:
        console.print(f"  Auto-stop in {duration:.0f}s. Press Ctrl+C to stop early.\n")
    else:
        console.print("  Press Ctrl+C to stop.\n")

    # Live display
    if not quiet:
        _live_monitor(session_record, duration)
    else:
        # Quiet mode — just wait
        try:
            while session_record.is_running:
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass

    # Stop recording
    if session_record.is_running:
        final = session_record.stop("manual_stop")
    else:
        final = session_record.get_session_info()

    console.print(f"\n[yellow]■ Recording stopped[/yellow] — {final.total_samples} samples in {final.duration_seconds:.1f}s")
    console.print(f"  Session: [bold]{final.session_id}[/bold]")
    console.print(f"  Log:     {final.log_file}")
    console.print(f"\n  View with: [bold cyan]esaiph logs show {final.session_id}[/bold cyan]\n")


def _resolve_process_by_name(name: str) -> Optional[int]:
    """Find a process by name, prompting if multiple matches."""
    matches = find_process_by_name(name)
    if not matches:
        console.print(f"[red]Error:[/red] No process found matching '{name}'.")
        return None

    if len(matches) == 1:
        return matches[0].pid

    # Multiple matches — show table and ask
    table = Table(title="Multiple Processes Found")
    table.add_column("#", style="bold")
    table.add_column("PID", style="cyan")
    table.add_column("Name")
    table.add_column("Status")

    for i, proc in enumerate(matches, 1):
        try:
            table.add_row(str(i), str(proc.pid), proc.name(), proc.status())
        except Exception:
            continue

    console.print(table)
    choice = click.prompt("Select process number", type=int)
    if 1 <= choice <= len(matches):
        return matches[choice - 1].pid
    else:
        console.print("[red]Invalid selection.[/red]")
        return None


def _live_monitor(session: RecordingSession, duration: Optional[float]):
    """Display a live-updating dashboard while recording."""
    start_time = time.monotonic()

    try:
        with Live(console=console, refresh_per_second=2) as live:
            while session.is_running:
                snap = session.latest_snapshot
                elapsed = time.monotonic() - start_time

                if snap:
                    table = Table(show_header=False, box=None, padding=(0, 2))
                    table.add_column("Metric", style="bold cyan", width=16)
                    table.add_column("Value", width=50)

                    # CPU with bar
                    cpu_bar = _make_bar(snap.cpu.percent, 100)
                    table.add_row("CPU", f"{cpu_bar} {snap.cpu.percent:.1f}%")

                    # Memory
                    mem_mb = snap.memory.rss / (1024 * 1024)
                    mem_bar = _make_bar(snap.memory.percent, 100)
                    table.add_row("Memory", f"{mem_bar} {mem_mb:.1f} MB ({snap.memory.percent:.1f}%)")

                    # I/O
                    if snap.io:
                        table.add_row("Disk Read", f"{snap.io.read_bytes / (1024*1024):.1f} MB total")
                        table.add_row("Disk Write", f"{snap.io.write_bytes / (1024*1024):.1f} MB total")

                    # Network
                    if snap.network:
                        table.add_row("Net Sent", f"{snap.network.bytes_sent / (1024*1024):.1f} MB")
                        table.add_row("Net Recv", f"{snap.network.bytes_recv / (1024*1024):.1f} MB")

                    table.add_row("Threads", str(snap.num_threads))
                    table.add_row("Handles", str(snap.num_handles))
                    table.add_row("Open Files", str(len(snap.open_files)))
                    table.add_row("Children", str(len(snap.children_pids)))
                    table.add_row("Status", snap.status)

                    elapsed_str = f"{elapsed:.0f}s"
                    if duration:
                        remaining = max(0, duration - elapsed)
                        elapsed_str = f"{elapsed:.0f}s / {duration:.0f}s (remaining: {remaining:.0f}s)"

                    panel = Panel(
                        table,
                        title=f"[bold green]● RECORDING[/bold green] — {snap.name} (PID {snap.pid})",
                        subtitle=f"Elapsed: {elapsed_str} │ Samples: {session._sample_count}",
                        border_style="green",
                    )
                    live.update(panel)
                else:
                    live.update(Panel("[dim]Waiting for first sample...[/dim]", border_style="yellow"))

                time.sleep(0.5)

    except KeyboardInterrupt:
        pass  # Will be caught by the caller


def _make_bar(value: float, max_val: float, width: int = 20) -> str:
    """Create a simple text-based progress bar."""
    filled = int((value / max_val) * width) if max_val > 0 else 0
    filled = min(filled, width)
    empty = width - filled

    if value > 80:
        color = "red"
    elif value > 50:
        color = "yellow"
    else:
        color = "green"

    return f"[{color}]{'█' * filled}{'░' * empty}[/{color}]"


# ── Logs Command Group ──

@cli.group()
def logs():
    """View, export, and manage recorded session logs."""
    pass


@logs.command("list")
@click.option("--limit", "-n", type=int, default=20, help="Number of sessions to show.")
def logs_list(limit: int):
    """List all recorded sessions."""
    sessions = list_sessions()

    if not sessions:
        console.print("[dim]No sessions found. Start one with:[/dim] [bold]esaiph record --pid <PID>[/bold]")
        return

    table = Table(title="Recording Sessions", show_lines=True)
    table.add_column("Session ID", style="bold cyan")
    table.add_column("Process")
    table.add_column("PID", justify="right")
    table.add_column("Started")
    table.add_column("Duration", justify="right")
    table.add_column("Samples", justify="right")
    table.add_column("Exit Reason")

    for s in sessions[:limit]:
        # Format start time
        start = s.start_time[:19].replace("T", " ") if s.start_time else "—"
        dur = f"{s.duration_seconds:.1f}s" if s.duration_seconds else "—"

        table.add_row(
            s.session_id,
            s.process_name or "—",
            str(s.pid),
            start,
            dur,
            str(s.total_samples),
            s.exit_reason or "—",
        )

    console.print(table)
    console.print(f"\n[dim]Showing {min(limit, len(sessions))} of {len(sessions)} sessions.[/dim]\n")


@logs.command("show")
@click.argument("session_id")
def logs_show(session_id: str):
    """Show a detailed report for a recorded session."""
    sessions = list_sessions()
    session = next((s for s in sessions if s.session_id == session_id), None)

    if not session:
        # Try partial match
        matches = [s for s in sessions if session_id in s.session_id]
        if len(matches) == 1:
            session = matches[0]
        elif len(matches) > 1:
            console.print(f"[yellow]Ambiguous session ID. Matches:[/yellow]")
            for m in matches:
                console.print(f"  {m.session_id} — {m.process_name}")
            return
        else:
            console.print(f"[red]Session not found:[/red] {session_id}")
            return

    try:
        snapshots = load_session_snapshots(session.session_id)
    except FileNotFoundError:
        console.print(f"[red]Session log file not found for {session.session_id}[/red]")
        return

    summary = analyze_session(session, snapshots)
    report = format_summary_text(summary)
    console.print(report)


@logs.command("export")
@click.argument("session_id")
@click.option("--format", "-f", "fmt", type=click.Choice(["json", "csv", "txt"]), default="json")
@click.option("--output", "-o", type=click.Path(), default=None, help="Output file path.")
def logs_export(session_id: str, fmt: str, output: Optional[str]):
    """Export session data in JSON, CSV, or TXT format."""
    sessions = list_sessions()
    session = next((s for s in sessions if s.session_id == session_id), None)
    if not session:
        matches = [s for s in sessions if session_id in s.session_id]
        if len(matches) == 1:
            session = matches[0]
        else:
            console.print(f"[red]Session not found:[/red] {session_id}")
            return

    try:
        snapshots = load_session_snapshots(session.session_id)
    except FileNotFoundError:
        console.print(f"[red]Session log file not found.[/red]")
        return

    if output is None:
        output = f"{session.session_id}.{fmt}"

    if fmt == "json":
        summary = analyze_session(session, snapshots)
        data = {
            "summary": summary.to_dict(),
            "snapshots": [s.to_dict() for s in snapshots],
        }
        with open(output, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    elif fmt == "csv":
        with open(output, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp", "cpu_percent", "memory_rss_mb", "memory_percent",
                "io_read_bytes", "io_write_bytes", "num_threads", "num_handles",
                "open_files", "status",
            ])
            for s in snapshots:
                writer.writerow([
                    s.timestamp,
                    f"{s.cpu.percent:.1f}",
                    f"{s.memory.rss / (1024*1024):.1f}",
                    f"{s.memory.percent:.1f}",
                    s.io.read_bytes if s.io else "",
                    s.io.write_bytes if s.io else "",
                    s.num_threads,
                    s.num_handles,
                    len(s.open_files),
                    s.status,
                ])

    elif fmt == "txt":
        summary = analyze_session(session, snapshots)
        report = format_summary_text(summary)
        with open(output, "w", encoding="utf-8") as f:
            f.write(report)

    console.print(f"[green]Exported to:[/green] {output}")


@logs.command("delete")
@click.argument("session_id")
@click.confirmation_option(prompt="Delete this session?")
def logs_delete(session_id: str):
    """Delete a recorded session."""
    if delete_session(session_id):
        console.print(f"[green]Deleted session:[/green] {session_id}")
    else:
        console.print(f"[red]Session not found:[/red] {session_id}")


# ── Status Command ──

@cli.command()
def status():
    """Show system overview and active processes."""
    import psutil

    # System overview
    cpu_percent = psutil.cpu_percent(interval=1)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    table = Table(title="System Overview", show_header=False)
    table.add_column("Metric", style="bold cyan", width=20)
    table.add_column("Value")

    table.add_row("CPU Usage", f"{cpu_percent:.1f}%")
    table.add_row("Memory", f"{mem.used / (1024**3):.1f} / {mem.total / (1024**3):.1f} GB ({mem.percent}%)")
    table.add_row("Disk", f"{disk.used / (1024**3):.1f} / {disk.total / (1024**3):.1f} GB ({disk.percent}%)")
    table.add_row("CPU Cores", f"{psutil.cpu_count(logical=False)} physical, {psutil.cpu_count()} logical")

    console.print(table)

    # Recent sessions
    sessions = list_sessions()
    if sessions:
        console.print(f"\n[dim]{len(sessions)} recorded sessions. Use[/dim] [bold]esaiph logs list[/bold] [dim]to view.[/dim]")


# ── GUI Launch Command ──

@cli.command()
def gui():
    """Launch the eSaiph graphical interface."""
    console.print("[cyan]Launching eSaiph GUI...[/cyan]")
    from .gui.app import launch_gui
    launch_gui()


def main():
    """Entry point for the esaiph command."""
    cli()


if __name__ == "__main__":
    main()
