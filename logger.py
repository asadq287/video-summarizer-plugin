"""Structured file logger for MCP server diagnostics.

MCP uses stdio for communication, so we CANNOT print to stdout/stderr.
All diagnostics go to a timestamped log file in ~/video-summarizer-logs/.

Usage:
    from logger import log

    log("download", "Starting download", url=url)
    log("download", "Complete", elapsed=1.8, size_mb=7.5)

Logs are at: ~/video-summarizer-logs/
"""

import os
import time
from pathlib import Path

LOG_DIR = Path(os.environ.get(
    "VIDEO_SUMMARIZER_LOG_DIR",
    str(Path.home() / ".cache" / "claude-plugins" / "video-summarizer" / "logs"),
))
LOG_DIR.mkdir(parents=True, exist_ok=True)

# One log file per server process
_process_start = time.strftime("%Y%m%d-%H%M%S")
_pid = os.getpid()
LOG_FILE = LOG_DIR / f"{_process_start}-{_pid}.log"

# Track timing
_timers: dict[str, float] = {}


def log(stage: str, message: str, **kv) -> None:
    """Append a structured log line to the log file.

    Args:
        stage: Pipeline stage (e.g., "server", "download", "transcribe").
        message: Human-readable description.
        **kv: Key-value pairs to include (e.g., elapsed=1.8, url="...").
    """
    ts = time.strftime("%H:%M:%S")
    ms = f"{time.time() % 1:.3f}"[1:]  # .123
    elapsed_total = f"{time.monotonic() - _boot:.1f}s" if _boot else ""

    parts = [f"[{ts}{ms}]", f"+{elapsed_total}" if elapsed_total else "", f"[{stage}]", message]
    if kv:
        detail = " ".join(f"{k}={v}" for k, v in kv.items())
        parts.append(f"| {detail}")

    line = " ".join(p for p in parts if p) + "\n"

    with open(LOG_FILE, "a") as f:
        f.write(line)


def timer_start(name: str) -> None:
    """Start a named timer."""
    _timers[name] = time.monotonic()


def timer_end(name: str) -> float:
    """End a named timer and return elapsed seconds."""
    start = _timers.pop(name, None)
    if start is None:
        return 0.0
    return time.monotonic() - start


# Record boot time
_boot = time.monotonic()
log("logger", "Logger initialized", log_file=str(LOG_FILE), pid=_pid)
