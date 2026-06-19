"""Structured JSON logging for worker jobs."""

from __future__ import annotations

import json
import logging
import sys
import time
from typing import Any

_CONFIGURED = False


def _configure() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    root = logging.getLogger("gridtrace_worker")
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    root.propagate = False
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    _configure()
    return logging.getLogger(f"gridtrace_worker.{name}")


def log_event(logger: logging.Logger, event: str, **fields: Any) -> None:
    """Emit a single structured log line as JSON."""
    record = {"event": event, "ts": time.time(), **fields}
    logger.info(json.dumps(record, default=str, sort_keys=True))
