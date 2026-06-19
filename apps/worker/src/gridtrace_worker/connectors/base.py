"""Connector base contract with source-freshness tracking."""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class SourceFreshness:
    source: str
    fetched_at: datetime
    record_count: int
    detail: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "fetched_at": self.fetched_at.isoformat(),
            "record_count": self.record_count,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class ConnectorResult:
    records: list[dict[str, Any]]
    freshness: SourceFreshness


class OfflineConnector(abc.ABC):
    """Base class for deterministic, offline context connectors."""

    name: str = "offline"

    @abc.abstractmethod
    def fetch(self) -> ConnectorResult:
        """Return records plus freshness metadata. Must be side-effect free."""

    def _freshness(self, records: list[dict[str, Any]], **detail: Any) -> SourceFreshness:
        return SourceFreshness(
            source=self.name,
            fetched_at=datetime.now(UTC),
            record_count=len(records),
            detail=detail,
        )
