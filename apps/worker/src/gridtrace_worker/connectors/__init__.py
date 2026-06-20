"""Offline/local context connectors.

No live third-party APIs are used. The base connector defines a minimal contract
and exposes source-freshness metadata; the filesystem connector reads context
fixtures from the local ``data/`` tree so the demo is fully reproducible offline.
"""

from gridtrace_worker.connectors.base import (
    ConnectorResult,
    OfflineConnector,
    SourceFreshness,
)
from gridtrace_worker.connectors.amsterdam_context import AmsterdamContextConnector
from gridtrace_worker.connectors.filesystem import FilesystemConnector
from gridtrace_worker.connectors.ned import NEDConnector

__all__ = [
    "AmsterdamContextConnector",
    "ConnectorResult",
    "FilesystemConnector",
    "NEDConnector",
    "OfflineConnector",
    "SourceFreshness",
]
