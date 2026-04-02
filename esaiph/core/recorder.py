"""Session recorder — manages recording lifecycle and snapshot persistence."""

from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

import psutil

from .collector import (
    AccessDeniedError,
    ProcessNotFoundError,
    collect_snapshot,
    get_process,
    get_process_info,
)
from .logger_config import get_logger
from .models import ProcessSnapshot, SessionInfo

logger = get_logger("recorder")

# Default sessions directory
DEFAULT_SESSIONS_DIR = Path(os.path.expanduser("~")) / ".esaiph" / "sessions"


class RecordingSession:
    """Manages a single recording session for a process.

    Usage:
        session = RecordingSession(pid=1234, interval=1.0)
        session.start()
        # ... later ...
        session.stop()
        info = session.get_session_info()
    """

    def __init__(
        self,
        pid: int,
        interval: float = 1.0,
        duration: Optional[float] = None,
        sessions_dir: Optional[Path] = None,
        on_snapshot: Optional[Callable[[ProcessSnapshot], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
        on_stopped: Optional[Callable[[SessionInfo], None]] = None,
    ):
        """Initialize a recording session.

        Args:
            pid: Process ID to monitor.
            interval: Sampling interval in seconds.
            duration: Auto-stop after this many seconds (None = indefinite).
            sessions_dir: Where to store session log files.
            on_snapshot: Callback invoked after each snapshot is collected.
            on_error: Callback invoked on collection errors.
            on_stopped: Callback invoked when recording stops.
        """
        self.pid = pid
        self.interval = interval
        self.duration = duration
        self.sessions_dir = sessions_dir or DEFAULT_SESSIONS_DIR
        self.on_snapshot = on_snapshot
        self.on_error = on_error
        self.on_stopped = on_stopped

        # Session state
        self._session_info = SessionInfo(sample_interval=interval)
        self._process: Optional[psutil.Process] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._is_running = False
        self._log_file: Optional[Path] = None
        self._log_handle = None
        self._sample_count = 0
        self._latest_snapshot: Optional[ProcessSnapshot] = None

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def session_id(self) -> str:
        return self._session_info.session_id

    @property
    def latest_snapshot(self) -> Optional[ProcessSnapshot]:
        return self._latest_snapshot

    def start(self) -> SessionInfo:
        """Start recording in a background thread.

        Returns:
            SessionInfo with the session ID and metadata.

        Raises:
            ProcessNotFoundError: If the PID doesn't exist.
            AccessDeniedError: If access is denied.
            RuntimeError: If already recording.
        """
        if self._is_running:
            raise RuntimeError("Recording is already in progress.")

        # Validate the process exists
        self._process = get_process(self.pid)
        proc_info = get_process_info(self.pid)

        # Prepare session metadata
        self._session_info.pid = self.pid
        self._session_info.process_name = proc_info.get("name", "unknown")
        self._session_info.command_line = proc_info.get("cmdline", "")
        self._session_info.start_time = datetime.now(timezone.utc).isoformat()

        # Prepare log file
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self._log_file = self.sessions_dir / f"{self._session_info.session_id}.jsonl"
        self._session_info.log_file = str(self._log_file)

        # Write session header
        meta_file = self.sessions_dir / f"{self._session_info.session_id}.meta.json"
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(self._session_info.to_dict(), f, indent=2)

        # Prime the CPU percent measurement
        try:
            self._process.cpu_percent(interval=None)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

        # Open log file for streaming writes
        self._log_handle = open(self._log_file, "w", encoding="utf-8")

        # Start collection thread
        self._stop_event.clear()
        self._is_running = True
        self._thread = threading.Thread(target=self._collection_loop, daemon=True)
        self._thread.start()

        logger.info(
            "Recording started — session=%s pid=%d name=%s interval=%.1fs",
            self._session_info.session_id,
            self.pid,
            self._session_info.process_name,
            self.interval,
        )

        return self._session_info

    def stop(self, reason: str = "manual_stop") -> SessionInfo:
        """Stop the recording and finalize the session.

        Args:
            reason: Why the recording stopped.

        Returns:
            Finalized SessionInfo.
        """
        if not self._is_running:
            logger.warning("Stop called but recording is not running.")
            return self._session_info

        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=self.interval + 2)

        self._finalize_session(reason)
        return self._session_info

    def _collection_loop(self):
        """Background thread: collect snapshots at the configured interval."""
        start_time = time.monotonic()

        while not self._stop_event.is_set():
            # Check duration limit
            if self.duration and (time.monotonic() - start_time) >= self.duration:
                logger.info("Duration limit reached (%.1fs).", self.duration)
                self._stop_event.set()
                self._finalize_session("duration_reached")
                return

            # Collect snapshot
            try:
                snapshot = collect_snapshot(self._process)
                self._latest_snapshot = snapshot
                self._sample_count += 1

                # Write to log file
                if self._log_handle and not self._log_handle.closed:
                    line = json.dumps(snapshot.to_dict())
                    self._log_handle.write(line + "\n")
                    self._log_handle.flush()

                # Invoke callback
                if self.on_snapshot:
                    try:
                        self.on_snapshot(snapshot)
                    except Exception as e:
                        logger.warning("Snapshot callback error: %s", e)

            except ProcessNotFoundError:
                logger.warning("Process %d terminated.", self.pid)
                # Try to get exit code
                exit_code = self._get_exit_code()
                self._session_info.exit_code = exit_code
                self._stop_event.set()
                self._finalize_session("process_exited")
                return

            except AccessDeniedError as e:
                err_msg = f"Access denied during collection: {e}"
                logger.error(err_msg)
                if self.on_error:
                    self.on_error(err_msg)
                self._stop_event.set()
                self._finalize_session("access_denied")
                return

            except Exception as e:
                err_msg = f"Unexpected error during collection: {e}"
                logger.error(err_msg)
                if self.on_error:
                    self.on_error(err_msg)

            # Wait for next interval
            self._stop_event.wait(self.interval)

    def _finalize_session(self, reason: str):
        """Close files, update metadata, invoke callbacks."""
        self._is_running = False

        # Close log file
        if self._log_handle and not self._log_handle.closed:
            self._log_handle.close()

        # Update session info
        self._session_info.end_time = datetime.now(timezone.utc).isoformat()
        self._session_info.total_samples = self._sample_count
        self._session_info.exit_reason = reason

        # Calculate duration
        try:
            start = datetime.fromisoformat(self._session_info.start_time)
            end = datetime.fromisoformat(self._session_info.end_time)
            self._session_info.duration_seconds = (end - start).total_seconds()
        except (ValueError, TypeError):
            self._session_info.duration_seconds = 0

        # Update meta file
        meta_file = self.sessions_dir / f"{self._session_info.session_id}.meta.json"
        try:
            with open(meta_file, "w", encoding="utf-8") as f:
                json.dump(self._session_info.to_dict(), f, indent=2)
        except Exception as e:
            logger.error("Failed to write session metadata: %s", e)

        logger.info(
            "Recording stopped — session=%s reason=%s samples=%d duration=%.1fs",
            self._session_info.session_id,
            reason,
            self._sample_count,
            self._session_info.duration_seconds,
        )

        if self.on_stopped:
            try:
                self.on_stopped(self._session_info)
            except Exception as e:
                logger.warning("Stop callback error: %s", e)

    def _get_exit_code(self) -> Optional[int]:
        """Try to retrieve the exit code of a terminated process."""
        try:
            proc = psutil.Process(self.pid)
            return proc.wait(timeout=0)
        except Exception:
            return None

    def get_session_info(self) -> SessionInfo:
        return self._session_info


def list_sessions(sessions_dir: Optional[Path] = None) -> list[SessionInfo]:
    """List all recorded sessions by reading .meta.json files.

    Args:
        sessions_dir: Directory to scan. Defaults to ~/.esaiph/sessions/

    Returns:
        List of SessionInfo objects, sorted by start_time descending.
    """
    sessions_dir = sessions_dir or DEFAULT_SESSIONS_DIR
    sessions: list[SessionInfo] = []

    if not sessions_dir.exists():
        return sessions

    for meta_file in sessions_dir.glob("*.meta.json"):
        try:
            with open(meta_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            sessions.append(SessionInfo.from_dict(data))
        except Exception as e:
            logger.warning("Failed to read session metadata %s: %s", meta_file, e)

    # Sort newest first
    sessions.sort(key=lambda s: s.start_time, reverse=True)
    return sessions


def load_session_snapshots(
    session_id: str,
    sessions_dir: Optional[Path] = None,
) -> list[ProcessSnapshot]:
    """Load all snapshots for a session from its .jsonl log file.

    Args:
        session_id: The session ID to load.
        sessions_dir: Directory containing session files.

    Returns:
        List of ProcessSnapshot objects in chronological order.
    """
    sessions_dir = sessions_dir or DEFAULT_SESSIONS_DIR
    log_file = sessions_dir / f"{session_id}.jsonl"

    if not log_file.exists():
        raise FileNotFoundError(f"Session log not found: {log_file}")

    snapshots: list[ProcessSnapshot] = []
    with open(log_file, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                snapshots.append(ProcessSnapshot.from_dict(data))
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning("Malformed snapshot at line %d: %s", line_num, e)

    return snapshots


def delete_session(
    session_id: str,
    sessions_dir: Optional[Path] = None,
) -> bool:
    """Delete a session's log and metadata files.

    Returns:
        True if files were deleted, False if not found.
    """
    sessions_dir = sessions_dir or DEFAULT_SESSIONS_DIR
    deleted = False

    for suffix in (".jsonl", ".meta.json"):
        path = sessions_dir / f"{session_id}{suffix}"
        if path.exists():
            path.unlink()
            deleted = True

    return deleted
