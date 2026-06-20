"""MOMENT-1-large zero-shot reconstruction pipeline for customer anomaly scoring.

Extracts trailing hourly consumption sequences from PostgreSQL via DuckDB,
runs MOMENT reconstruction inference, and maps per-customer MSE into [0, 1]
anomaly scores for hybrid integration with the heuristic scorer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from urllib.parse import unquote, urlparse

import numpy as np
import polars as pl

from gridtrace_worker.log import get_logger, log_event

if TYPE_CHECKING:
    from gridtrace_worker.config import WorkerConfig

logger = get_logger("moment_pipeline")

_EPS = 1e-8
_ANOMALY_DECAY_K = 2.0
_PEAK_TOP_K = 3

_MODEL_CACHE: dict[str, Any] = {}


@dataclass(frozen=True)
class MomentAnomalyResult:
    customer_id: str
    anomaly_score: float
    reconstruction_mse: float
    peak_timestamps: list[str]
    peak_errors: list[float]


def _parse_database_url_for_duckdb(url: str) -> str:
    """Convert a SQLAlchemy/psycopg URL into DuckDB postgres ATTACH options."""
    parsed = urlparse(url)
    parts: list[str] = []
    dbname = parsed.path.lstrip("/")
    if dbname:
        parts.append(f"dbname={dbname}")
    if parsed.username:
        parts.append(f"user={unquote(parsed.username)}")
    if parsed.password:
        parts.append(f"password={unquote(parsed.password)}")
    if parsed.hostname:
        parts.append(f"host={parsed.hostname}")
    if parsed.port:
        parts.append(f"port={parsed.port}")
    return " ".join(parts)


def _sequence_extraction_sql(context_length: int) -> str:
    return f"""
WITH ranked AS (
  SELECT
    mr.meter_id AS customer_id,
    mr.timestamp,
    mr.consumption_kwh,
    ROW_NUMBER() OVER (PARTITION BY mr.meter_id ORDER BY mr.timestamp ASC) AS rn_asc,
    COUNT(*) OVER (PARTITION BY mr.meter_id) AS n
  FROM pg.meter_readings AS mr
  INNER JOIN pg.customers AS c ON c.id = mr.meter_id
),
last_window AS (
  SELECT *
  FROM ranked
  WHERE rn_asc > GREATEST(n - {context_length}, 0)
)
SELECT
  customer_id,
  LIST(consumption_kwh ORDER BY timestamp) AS values,
  LIST(CAST(timestamp AS VARCHAR) ORDER BY timestamp) AS timestamps,
  COUNT(*)::INTEGER AS actual_len
FROM last_window
GROUP BY customer_id
"""


def pad_sequence(
    values: list[float],
    timestamps: list[str],
    context_length: int,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Pad trailing values to ``context_length`` with zeros and build a mask."""
    arr = np.asarray(values, dtype=np.float64)
    actual_len = int(arr.size)
    if actual_len > context_length:
        arr = arr[-context_length:]
        ts = timestamps[-context_length:]
        actual_len = context_length
    else:
        ts = list(timestamps)

    padded = np.zeros(context_length, dtype=np.float64)
    mask = np.zeros(context_length, dtype=np.float64)
    if actual_len > 0:
        padded[:actual_len] = arr
        mask[:actual_len] = 1.0
    return padded, mask, ts


def instance_normalize(values: np.ndarray, mask: np.ndarray, eps: float = _EPS) -> np.ndarray:
    """Z-score each sequence using only masked (real) positions."""
    masked_sum = float(mask.sum())
    if masked_sum < 1.0:
        return values.copy()
    mean = float((values * mask).sum() / masked_sum)
    var = float(((values - mean) ** 2 * mask).sum() / masked_sum)
    std = float(np.sqrt(var) + eps)
    return (values - mean) / std


def mse_to_anomaly_scores(mse: np.ndarray, eps: float = _EPS) -> np.ndarray:
    """Map reconstruction MSE to [0, 1] via population z-score and decay."""
    if mse.size == 0:
        return mse
    mean_mse = float(mse.mean())
    std_mse = float(mse.std())
    z = (mse - mean_mse) / (std_mse + eps)
    return np.clip(1.0 - np.exp(-z / _ANOMALY_DECAY_K), 0.0, 1.0)


def _peak_metadata(
    timestamps: list[str],
    point_errors: np.ndarray,
    mask: np.ndarray,
    top_k: int = _PEAK_TOP_K,
) -> tuple[list[str], list[float]]:
    """Return top-k peak timestamps and per-point squared errors."""
    valid_idx = np.where(mask > 0.5)[0]
    if valid_idx.size == 0:
        return [], []

    errors = point_errors[valid_idx]
    order = np.argsort(-errors, kind="stable")[:top_k]
    peak_ts: list[str] = []
    peak_errs: list[float] = []
    for rank in order:
        idx = int(valid_idx[rank])
        peak_ts.append(timestamps[idx] if idx < len(timestamps) else "unknown")
        peak_errs.append(float(point_errors[idx]))
    return peak_ts, peak_errs


def build_peak_explanation_entries(
    timestamps: list[str],
    point_errors: np.ndarray,
    mask: np.ndarray,
    top_k: int = _PEAK_TOP_K,
) -> list[dict[str, Any]]:
    """Build explanation dicts for the highest per-point reconstruction errors."""
    peak_ts, peak_errs = _peak_metadata(timestamps, point_errors, mask, top_k)
    if not peak_ts:
        return []

    max_err = max(peak_errs) if peak_errs else 1.0
    norm_denom = max_err if max_err > _EPS else 1.0
    entries: list[dict[str, Any]] = []
    for ts, point_mse in zip(peak_ts, peak_errs, strict=True):
        contribution = round(point_mse / norm_denom, 4)
        entries.append(
            {
                "feature": "moment_reconstruction_peak",
                "label": "Reconstruction anomaly peak",
                "contribution": contribution,
                "direction": "increases" if contribution >= 0.5 else "neutral",
                "detail": (
                    f"MOMENT reconstruction error peaked at {ts} "
                    f"(point MSE={point_mse:.4f})."
                ),
            }
        )
    return entries


def moment_peak_explanations(result: MomentAnomalyResult) -> list[dict[str, Any]]:
    """Convert stored peak metadata into API-compatible explanation entries."""
    if not result.peak_timestamps:
        return []
    max_err = max(result.peak_errors) if result.peak_errors else 1.0
    norm_denom = max_err if max_err > _EPS else 1.0
    entries: list[dict[str, Any]] = []
    for ts, err in zip(result.peak_timestamps, result.peak_errors, strict=False):
        contribution = round(float(err) / norm_denom, 4)
        entries.append(
            {
                "feature": "moment_reconstruction_peak",
                "label": "Reconstruction anomaly peak",
                "contribution": contribution,
                "direction": "increases" if contribution >= 0.5 else "neutral",
                "detail": (
                    f"MOMENT reconstruction error peaked at {ts} "
                    f"(point MSE={float(err):.4f})."
                ),
            }
        )
    return entries


class MOMENTInferencePipeline:
    """DuckDB extraction → MOMENT reconstruction → per-customer anomaly scores."""

    def __init__(self, config: WorkerConfig | None = None) -> None:
        from gridtrace_worker.config import get_worker_config

        self.config = config or get_worker_config()
        self._device: Any = None

    @property
    def context_length(self) -> int:
        return self.config.moment_context_length

    @property
    def batch_size(self) -> int:
        return self.config.moment_batch_size

    def _resolve_device(self):
        import torch

        if self._device is not None:
            return self._device
        if self.config.moment_device:
            self._device = torch.device(self.config.moment_device)
        else:
            self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        return self._device

    @staticmethod
    def _load_model(model_name: str, device_str: str):
        import torch
        from momentfm import MOMENTPipeline

        if model_name in _MODEL_CACHE:
            return _MODEL_CACHE[model_name]

        model = MOMENTPipeline.from_pretrained(
            model_name,
            model_kwargs={"task_name": "reconstruction"},
        )
        model.init()
        device = torch.device(device_str)
        model.to(device)
        model.eval()
        _MODEL_CACHE[model_name] = model
        return model

    def extract_sequences(self, database_url: str) -> pl.DataFrame:
        """Vectorized DuckDB query: trailing hourly windows per active customer."""
        import duckdb

        attach_opts = _parse_database_url_for_duckdb(database_url)
        conn = duckdb.connect()
        try:
            conn.execute("INSTALL postgres; LOAD postgres;")
            conn.execute(
                f"ATTACH '{attach_opts}' AS pg (TYPE postgres, READ_ONLY);"
            )
            df = conn.execute(_sequence_extraction_sql(self.context_length)).pl()
        finally:
            conn.close()

        if df.is_empty():
            return df

        padded_values: list[list[float]] = []
        masks: list[list[float]] = []
        norm_timestamps: list[list[str]] = []
        for row in df.iter_rows(named=True):
            values, mask, ts = pad_sequence(
                list(row["values"]),
                list(row["timestamps"]),
                self.context_length,
            )
            padded_values.append(values.tolist())
            masks.append(mask.tolist())
            norm_timestamps.append(ts)

        return df.with_columns(
            pl.Series("values", padded_values),
            pl.Series("mask", masks),
            pl.Series("timestamps", norm_timestamps),
        )

    def prepare_tensors(
        self, df: pl.DataFrame
    ) -> tuple[Any, Any, list[str], list[list[str]], list[np.ndarray]]:
        """Normalize sequences and build [batch, 1, 512] tensors plus metadata."""
        import torch

        if df.is_empty():
            empty = torch.empty(0, 1, self.context_length)
            return empty, empty, [], [], []

        values_list = [np.asarray(v, dtype=np.float64) for v in df["values"].to_list()]
        mask_list = [np.asarray(m, dtype=np.float64) for m in df["mask"].to_list()]
        timestamps = df["timestamps"].to_list()
        customer_ids = df["customer_id"].to_list()

        normalized = [
            instance_normalize(v, m) for v, m in zip(values_list, mask_list, strict=True)
        ]
        x = torch.tensor(np.stack(normalized), dtype=torch.float32).unsqueeze(1)
        mask = torch.tensor(np.stack(mask_list), dtype=torch.float32)
        return x, mask, customer_ids, timestamps, mask_list

    def run_inference(
        self,
        x: Any,
        mask: Any,
        raw_masks: list[np.ndarray] | None = None,
        timestamps_batch: list[list[str]] | None = None,
    ) -> tuple[np.ndarray, list[list[dict[str, Any]]], list[tuple[list[str], list[float]]]]:
        """Run MOMENT reconstruction and return per-row MSE + peak metadata."""
        import torch

        if x.numel() == 0:
            return np.array([]), [], []

        device = self._resolve_device()
        model = self._load_model(self.config.moment_model_name, str(device))
        x = x.to(device)
        mask = mask.to(device)

        with torch.no_grad():
            out = model(x, input_mask=mask)
            recon = getattr(out, "reconstruction", None)
            if recon is None and isinstance(out, dict):
                recon = out.get("reconstruction")
            if recon is None:
                raise RuntimeError("MOMENT forward pass did not return reconstruction output")
            point_sq = (x - recon) ** 2
            if point_sq.dim() == 3 and point_sq.shape[1] == 1:
                point_sq = point_sq.squeeze(1)
            mask_denom = mask.sum(dim=-1).clamp(min=1.0)
            mse = (point_sq * mask).sum(dim=-1) / mask_denom

        mse_np = mse.detach().cpu().numpy()
        peak_entries: list[list[dict[str, Any]]] = []
        peak_meta: list[tuple[list[str], list[float]]] = []
        if raw_masks is not None and timestamps_batch is not None:
            point_sq_cpu = point_sq.detach().cpu().numpy()
            for i, (m, ts) in enumerate(zip(raw_masks, timestamps_batch, strict=True)):
                peak_ts, peak_errs = _peak_metadata(ts, point_sq_cpu[i], m)
                peak_meta.append((peak_ts, peak_errs))
                peak_entries.append(build_peak_explanation_entries(ts, point_sq_cpu[i], m))
        return mse_np, peak_entries, peak_meta

    def score_batch(self, mse: np.ndarray) -> np.ndarray:
        return mse_to_anomaly_scores(mse)

    def infer(self, database_url: str) -> dict[str, MomentAnomalyResult]:
        """Full pipeline: extract → infer in batches → return per-customer results."""
        df = self.extract_sequences(database_url)
        if df.is_empty():
            log_event(logger, "moment_infer_empty", reason="no_sequences")
            return {}

        results: dict[str, MomentAnomalyResult] = {}
        total = df.height
        log_event(
            logger,
            "moment_infer_start",
            customers=total,
            model=self.config.moment_model_name,
            context_length=self.context_length,
        )

        for start in range(0, total, self.batch_size):
            batch_df = df.slice(start, self.batch_size)
            x, mask, customer_ids, timestamps, raw_masks = self.prepare_tensors(batch_df)
            mse, peak_entries, peak_meta = self.run_inference(
                x, mask, raw_masks=raw_masks, timestamps_batch=timestamps
            )
            anomaly_scores = self.score_batch(mse)

            for i, cid in enumerate(customer_ids):
                peak_ts, peak_errs = peak_meta[i] if i < len(peak_meta) else ([], [])
                results[cid] = MomentAnomalyResult(
                    customer_id=cid,
                    anomaly_score=float(anomaly_scores[i]),
                    reconstruction_mse=float(mse[i]),
                    peak_timestamps=peak_ts,
                    peak_errors=peak_errs,
                )

        log_event(logger, "moment_infer_complete", scored=len(results))
        return results
