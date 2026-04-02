"""Centralized logging configuration for eSaiph."""

import logging
import logging.handlers
import os
from pathlib import Path


def get_log_directory() -> Path:
    """Get the application log directory, creating it if needed."""
    log_dir = Path(os.path.expanduser("~")) / ".esaiph" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def setup_logging(
    level: int = logging.INFO,
    log_to_file: bool = True,
    log_dir: Path | None = None,
) -> logging.Logger:
    """Configure and return the application-level logger.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, etc.)
        log_to_file: Whether to also log to a rotating file.
        log_dir: Directory for log files. Defaults to ~/.esaiph/logs/

    Returns:
        Configured logger instance.
    """
    logger = logging.getLogger("esaiph")
    logger.setLevel(level)

    # Avoid duplicate handlers on repeated calls
    if logger.handlers:
        return logger

    # Console handler — concise format
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_fmt = logging.Formatter(
        "%(asctime)s │ %(levelname)-7s │ %(message)s",
        datefmt="%H:%M:%S",
    )
    console_handler.setFormatter(console_fmt)
    logger.addHandler(console_handler)

    # File handler — detailed format with rotation
    if log_to_file:
        if log_dir is None:
            log_dir = get_log_directory()
        log_file = log_dir / "esaiph.log"

        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=5 * 1024 * 1024,  # 5 MB
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_fmt = logging.Formatter(
            "%(asctime)s │ %(levelname)-7s │ %(name)s.%(funcName)s:%(lineno)d │ %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_fmt)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str = "esaiph") -> logging.Logger:
    """Get a child logger under the esaiph namespace."""
    return logging.getLogger(f"esaiph.{name}")
