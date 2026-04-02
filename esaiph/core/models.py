"""Data models for eSaiph — structured representations of process metrics."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class ThreadInfo:
    """Information about a single thread within a process."""
    thread_id: int
    user_time: float
    system_time: float


@dataclass
class ConnectionInfo:
    """Information about a network connection."""
    fd: int
    family: str
    type: str
    local_address: str
    remote_address: str
    status: str


@dataclass
class IOCounters:
    """Disk I/O counters for a process."""
    read_count: int
    write_count: int
    read_bytes: int
    write_bytes: int


@dataclass
class MemoryDetail:
    """Detailed memory usage breakdown."""
    rss: int           # Resident Set Size (bytes)
    vms: int           # Virtual Memory Size (bytes)
    percent: float     # Percentage of total system memory
    # Windows-specific
    private: int = 0
    # Additional
    num_page_faults: int = 0


@dataclass
class CPUDetail:
    """Detailed CPU usage information."""
    percent: float           # Overall CPU percent
    user_time: float         # Time spent in user mode (seconds)
    system_time: float       # Time spent in kernel mode (seconds)
    num_ctx_switches_voluntary: int = 0
    num_ctx_switches_involuntary: int = 0


@dataclass
class NetworkIOSnapshot:
    """Network I/O counters — captured at system level or per-connection."""
    bytes_sent: int
    bytes_recv: int
    packets_sent: int
    packets_recv: int


@dataclass
class ProcessSnapshot:
    """A single point-in-time snapshot of a process's state.

    This is the fundamental unit of data that the collector produces
    and the recorder stores.
    """
    timestamp: str  # ISO 8601
    pid: int
    name: str
    status: str     # running, sleeping, stopped, zombie, etc.

    # Resource usage
    cpu: CPUDetail
    memory: MemoryDetail
    io: Optional[IOCounters]
    network: Optional[NetworkIOSnapshot]

    # Process internals
    num_threads: int
    threads: list[ThreadInfo] = field(default_factory=list)
    open_files: list[str] = field(default_factory=list)
    connections: list[ConnectionInfo] = field(default_factory=list)
    num_handles: int = 0

    # Child processes
    children_pids: list[int] = field(default_factory=list)

    # Errors encountered during collection
    collection_errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""
        return {
            "timestamp": self.timestamp,
            "pid": self.pid,
            "name": self.name,
            "status": self.status,
            "cpu": {
                "percent": self.cpu.percent,
                "user_time": self.cpu.user_time,
                "system_time": self.cpu.system_time,
                "ctx_switches_voluntary": self.cpu.num_ctx_switches_voluntary,
                "ctx_switches_involuntary": self.cpu.num_ctx_switches_involuntary,
            },
            "memory": {
                "rss_bytes": self.memory.rss,
                "vms_bytes": self.memory.vms,
                "percent": self.memory.percent,
                "private_bytes": self.memory.private,
                "page_faults": self.memory.num_page_faults,
            },
            "io": {
                "read_count": self.io.read_count,
                "write_count": self.io.write_count,
                "read_bytes": self.io.read_bytes,
                "write_bytes": self.io.write_bytes,
            } if self.io else None,
            "network": {
                "bytes_sent": self.network.bytes_sent,
                "bytes_recv": self.network.bytes_recv,
                "packets_sent": self.network.packets_sent,
                "packets_recv": self.network.packets_recv,
            } if self.network else None,
            "num_threads": self.num_threads,
            "threads": [
                {"id": t.thread_id, "user_time": t.user_time, "system_time": t.system_time}
                for t in self.threads
            ],
            "open_files": self.open_files,
            "connections": [
                {
                    "fd": c.fd,
                    "family": c.family,
                    "type": c.type,
                    "local": c.local_address,
                    "remote": c.remote_address,
                    "status": c.status,
                }
                for c in self.connections
            ],
            "num_handles": self.num_handles,
            "children_pids": self.children_pids,
            "collection_errors": self.collection_errors,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProcessSnapshot:
        """Deserialize from a dictionary."""
        cpu_data = data["cpu"]
        mem_data = data["memory"]
        io_data = data.get("io")
        net_data = data.get("network")

        return cls(
            timestamp=data["timestamp"],
            pid=data["pid"],
            name=data["name"],
            status=data["status"],
            cpu=CPUDetail(
                percent=cpu_data["percent"],
                user_time=cpu_data["user_time"],
                system_time=cpu_data["system_time"],
                num_ctx_switches_voluntary=cpu_data.get("ctx_switches_voluntary", 0),
                num_ctx_switches_involuntary=cpu_data.get("ctx_switches_involuntary", 0),
            ),
            memory=MemoryDetail(
                rss=mem_data["rss_bytes"],
                vms=mem_data["vms_bytes"],
                percent=mem_data["percent"],
                private=mem_data.get("private_bytes", 0),
                num_page_faults=mem_data.get("page_faults", 0),
            ),
            io=IOCounters(
                read_count=io_data["read_count"],
                write_count=io_data["write_count"],
                read_bytes=io_data["read_bytes"],
                write_bytes=io_data["write_bytes"],
            ) if io_data else None,
            network=NetworkIOSnapshot(
                bytes_sent=net_data["bytes_sent"],
                bytes_recv=net_data["bytes_recv"],
                packets_sent=net_data["packets_sent"],
                packets_recv=net_data["packets_recv"],
            ) if net_data else None,
            num_threads=data["num_threads"],
            threads=[
                ThreadInfo(thread_id=t["id"], user_time=t["user_time"], system_time=t["system_time"])
                for t in data.get("threads", [])
            ],
            open_files=data.get("open_files", []),
            connections=[
                ConnectionInfo(
                    fd=c["fd"], family=c["family"], type=c["type"],
                    local_address=c["local"], remote_address=c["remote"], status=c["status"],
                )
                for c in data.get("connections", [])
            ],
            num_handles=data.get("num_handles", 0),
            children_pids=data.get("children_pids", []),
            collection_errors=data.get("collection_errors", []),
        )


@dataclass
class SessionInfo:
    """Metadata about a recording session."""
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    pid: int = 0
    process_name: str = ""
    start_time: str = ""   # ISO 8601
    end_time: str = ""     # ISO 8601
    duration_seconds: float = 0.0
    sample_interval: float = 1.0
    total_samples: int = 0
    exit_code: Optional[int] = None
    exit_reason: str = ""  # "manual_stop", "duration_reached", "process_exited", "process_crashed"
    command_line: str = ""
    environment: dict[str, str] = field(default_factory=dict)
    log_file: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "pid": self.pid,
            "process_name": self.process_name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_seconds": self.duration_seconds,
            "sample_interval": self.sample_interval,
            "total_samples": self.total_samples,
            "exit_code": self.exit_code,
            "exit_reason": self.exit_reason,
            "command_line": self.command_line,
            "log_file": self.log_file,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SessionInfo:
        return cls(
            session_id=data["session_id"],
            pid=data["pid"],
            process_name=data["process_name"],
            start_time=data["start_time"],
            end_time=data["end_time"],
            duration_seconds=data["duration_seconds"],
            sample_interval=data["sample_interval"],
            total_samples=data["total_samples"],
            exit_code=data.get("exit_code"),
            exit_reason=data.get("exit_reason", ""),
            command_line=data.get("command_line", ""),
            log_file=data.get("log_file", ""),
        )


@dataclass
class SessionSummary:
    """Analyzed summary of a recording session — produced by the analyzer."""
    session: SessionInfo

    # CPU
    cpu_avg: float = 0.0
    cpu_min: float = 0.0
    cpu_max: float = 0.0
    cpu_stddev: float = 0.0
    cpu_spikes: list[dict[str, Any]] = field(default_factory=list)  # timestamps where CPU > threshold

    # Memory
    memory_avg_mb: float = 0.0
    memory_min_mb: float = 0.0
    memory_max_mb: float = 0.0
    memory_trend: str = ""  # "stable", "growing", "shrinking", "erratic"
    potential_memory_leak: bool = False

    # I/O
    total_read_bytes: int = 0
    total_write_bytes: int = 0
    total_read_ops: int = 0
    total_write_ops: int = 0

    # Network
    total_net_sent: int = 0
    total_net_recv: int = 0

    # Threads
    thread_count_avg: float = 0.0
    thread_count_max: int = 0

    # Files & Handles
    max_open_files: int = 0
    max_handles: int = 0

    # Events
    status_changes: list[dict[str, str]] = field(default_factory=list)
    child_process_events: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session": self.session.to_dict(),
            "cpu": {
                "avg": self.cpu_avg,
                "min": self.cpu_min,
                "max": self.cpu_max,
                "stddev": self.cpu_stddev,
                "spikes": self.cpu_spikes,
            },
            "memory": {
                "avg_mb": self.memory_avg_mb,
                "min_mb": self.memory_min_mb,
                "max_mb": self.memory_max_mb,
                "trend": self.memory_trend,
                "potential_leak": self.potential_memory_leak,
            },
            "io": {
                "total_read_bytes": self.total_read_bytes,
                "total_write_bytes": self.total_write_bytes,
                "total_read_ops": self.total_read_ops,
                "total_write_ops": self.total_write_ops,
            },
            "network": {
                "total_sent": self.total_net_sent,
                "total_recv": self.total_net_recv,
            },
            "threads": {
                "avg_count": self.thread_count_avg,
                "max_count": self.thread_count_max,
            },
            "files_handles": {
                "max_open_files": self.max_open_files,
                "max_handles": self.max_handles,
            },
            "events": {
                "status_changes": self.status_changes,
                "child_process_events": self.child_process_events,
            },
            "warnings": self.warnings,
        }
