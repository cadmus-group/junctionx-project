"""Filesystem connector: reads local context fixtures (JSON) from ``data/``.

This stands in for external context feeds (weather, holidays, tariff calendars)
without any network access. Missing files yield an empty, well-formed result so the
pipeline never fails on absent optional context.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from gridtrace_worker.connectors.base import ConnectorResult, OfflineConnector


class FilesystemConnector(OfflineConnector):
    name = "filesystem"

    def __init__(self, root: str | Path, glob: str = "*.json") -> None:
        self.root = Path(root)
        self.glob = glob

    def fetch(self) -> ConnectorResult:
        records: list[dict[str, Any]] = []
        files: list[str] = []
        if self.root.exists():
            for path in sorted(self.root.glob(self.glob)):
                if not path.is_file():
                    continue
                try:
                    payload = json.loads(path.read_text())
                except (json.JSONDecodeError, OSError):
                    continue
                items = payload if isinstance(payload, list) else [payload]
                for item in items:
                    if isinstance(item, dict):
                        item.setdefault("_source_file", path.name)
                        records.append(item)
                files.append(path.name)
        return ConnectorResult(
            records=records,
            freshness=self._freshness(records, root=str(self.root), files=files),
        )
