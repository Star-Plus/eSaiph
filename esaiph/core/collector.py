"""Process data collector — wraps psutil into structured snapshots."""

from __future__ import annotations

import socket
from datetime import datetime, timezone
from typing import Optional

import psutil

from .logger_config import get_logger
from .models import (
    ConnectionInfo,
    CPUDetail,
    IOCounters,
    MemoryDetail,
    NetworkIOSnapshot,
    ProcessSnapshot,
    ThreadInfo,
)

logger = get_logger("collector")


class ProcessNotFoundError(Exception):
    """Raised when the target process no longer exists."""
    pass


class AccessDeniedError(Exception):
    """Raised when access to the target process is denied."""
    pass


def find_process_by_name(name: str) -> list[psutil.Process]:
    """Find all processes matching a name (case-insensitive).

    Returns:
        List of matching psutil.Process objects.
    """
    matches = []
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            if proc.info["name"] and name.lower() in proc.info["name"].lower():
                matches.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return matches


def get_process(pid: int) -> psutil.Process:
    """Get a psutil.Process object, raising clean errors if inaccessible.

    Args:
        pid: Process ID to look up.

    Returns:
        psutil.Process instance.

    Raises:
        ProcessNotFoundError: If the process doesn't exist.
        AccessDeniedError: If access is denied.
    """
    try:
        proc = psutil.Process(pid)
        proc.name()  # Trigger access check
        return proc
    except psutil.NoSuchProcess:
        raise ProcessNotFoundError(f"Process with PID {pid} not found.")
    except psutil.AccessDenied:
        raise AccessDeniedError(f"Access denied to process with PID {pid}.")


def collect_snapshot(proc: psutil.Process) -> ProcessSnapshot:
    """Collect a complete point-in-time snapshot of a process.

    Gathers CPU, memory, I/O, network, threads, open files, and connections.
    Handles partial failures gracefully — if a specific metric can't be collected,
    it's logged as a collection error but doesn't prevent the rest from being captured.

    Args:
        proc: A psutil.Process object to snapshot.

    Returns:
        A filled ProcessSnapshot dataclass.

    Raises:
        ProcessNotFoundError: If the process has terminated.
    """
    errors: list[str] = []
    timestamp = datetime.now(timezone.utc).isoformat()

    # Basic info
    try:
        pid = proc.pid
        name = proc.name()
        status = proc.status()
    except psutil.NoSuchProcess:
        raise ProcessNotFoundError(f"Process {proc.pid} terminated during collection.")
    except psutil.AccessDenied as e:
        raise AccessDeniedError(f"Access denied: {e}")

    # CPU
    try:
        cpu_times = proc.cpu_times()
        cpu_percent = proc.cpu_percent(interval=0)  # Non-blocking; requires prior call to prime
        try:
            ctx = proc.num_ctx_switches()
            ctx_vol = ctx.voluntary
            ctx_invol = ctx.involuntary
        except (AttributeError, psutil.AccessDenied):
            ctx_vol = 0
            ctx_invol = 0

        cpu = CPUDetail(
            percent=cpu_percent,
            user_time=cpu_times.user,
            system_time=cpu_times.system,
            num_ctx_switches_voluntary=ctx_vol,
            num_ctx_switches_involuntary=ctx_invol,
        )
    except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
        errors.append(f"CPU: {e}")
        cpu = CPUDetail(percent=0, user_time=0, system_time=0)

    # Memory
    try:
        mem = proc.memory_info()
        mem_percent = proc.memory_percent()
        memory = MemoryDetail(
            rss=mem.rss,
            vms=mem.vms,
            percent=mem_percent,
            private=getattr(mem, "private", 0),
            num_page_faults=getattr(mem, "num_page_faults", 0),
        )
    except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
        errors.append(f"Memory: {e}")
        memory = MemoryDetail(rss=0, vms=0, percent=0)

    # Disk I/O
    io: Optional[IOCounters] = None
    try:
        io_counters = proc.io_counters()
        io = IOCounters(
            read_count=io_counters.read_count,
            write_count=io_counters.write_count,
            read_bytes=io_counters.read_bytes,
            write_bytes=io_counters.write_bytes,
        )
    except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
        errors.append(f"I/O: {e}")
    except AttributeError:
        errors.append("I/O: Not supported on this platform.")

    # Network I/O (system-wide — per-process not always available)
    network: Optional[NetworkIOSnapshot] = None
    try:
        net = psutil.net_io_counters()
        network = NetworkIOSnapshot(
            bytes_sent=net.bytes_sent,
            bytes_recv=net.bytes_recv,
            packets_sent=net.packets_sent,
            packets_recv=net.packets_recv,
        )
    except Exception as e:
        errors.append(f"Network I/O: {e}")

    # Threads
    num_threads = 0
    threads: list[ThreadInfo] = []
    try:
        num_threads = proc.num_threads()
        for t in proc.threads():
            threads.append(ThreadInfo(
                thread_id=t.id,
                user_time=t.user_time,
                system_time=t.system_time,
            ))
    except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
        errors.append(f"Threads: {e}")

    # Open files
    open_files: list[str] = []
    try:
        for f in proc.open_files():
            open_files.append(f.path)
    except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
        errors.append(f"Open files: {e}")

    # Network connections
    connections: list[ConnectionInfo] = []
    try:
        for conn in proc.net_connections(kind="all"):
            local = f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else ""
            remote = f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else ""
            family_name = _socket_family_name(conn.family)
            type_name = _socket_type_name(conn.type)
            connections.append(ConnectionInfo(
                fd=conn.fd if conn.fd != -1 else 0,
                family=family_name,
                type=type_name,
                local_address=local,
                remote_address=remote,
                status=conn.status if conn.status else "NONE",
            ))
    except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
        errors.append(f"Connections: {e}")

    # Handles (Windows)
    num_handles = 0
    try:
        num_handles = proc.num_handles()
    except (psutil.NoSuchProcess, psutil.AccessDenied, AttributeError):
        pass  # Not available on all platforms

    # Children
    children_pids: list[int] = []
    try:
        children_pids = [c.pid for c in proc.children(recursive=True)]
    except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
        errors.append(f"Children: {e}")

    if errors:
        logger.debug("Collection warnings for PID %d: %s", pid, "; ".join(errors))

    return ProcessSnapshot(
        timestamp=timestamp,
        pid=pid,
        name=name,
        status=status,
        cpu=cpu,
        memory=memory,
        io=io,
        network=network,
        num_threads=num_threads,
        threads=threads,
        open_files=open_files,
        connections=connections,
        num_handles=num_handles,
        children_pids=children_pids,
        collection_errors=errors,
    )


def get_process_info(pid: int) -> dict:
    """Get basic info about a process (name, cmdline, create_time, etc.)."""
    try:
        proc = psutil.Process(pid)
        return {
            "pid": proc.pid,
            "name": proc.name(),
            "cmdline": " ".join(proc.cmdline()) if proc.cmdline() else "",
            "create_time": datetime.fromtimestamp(proc.create_time(), tz=timezone.utc).isoformat(),
            "status": proc.status(),
            "username": proc.username() if hasattr(proc, "username") else "",
            "cwd": proc.cwd() if hasattr(proc, "cwd") else "",
        }
    except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
        return {"error": str(e)}


def _socket_family_name(family: int) -> str:
    """Convert socket family constant to readable string."""
    mapping = {
        socket.AF_INET: "IPv4",
        socket.AF_INET6: "IPv6",
    }
    if hasattr(socket, "AF_UNIX"):
        mapping[socket.AF_UNIX] = "UNIX"
    return mapping.get(family, f"AF_{family}")


def _socket_type_name(sock_type: int) -> str:
    """Convert socket type constant to readable string."""
    mapping = {
        socket.SOCK_STREAM: "TCP",
        socket.SOCK_DGRAM: "UDP",
    }
    return mapping.get(sock_type, f"TYPE_{sock_type}")
