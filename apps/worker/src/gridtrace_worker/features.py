"""Pure, deterministic feature functions (no database, no I/O).

These operate on plain numpy arrays of hourly consumption so they can be unit
tested directly and reused by ``apps/ml-lab``. The DB-facing job in
``jobs/build_features.py`` loads readings and delegates here.

Leakage rule: callers pass ``as_of_idx`` and the functions only ever read indices
``<= as_of_idx``. The recent window is the last ``RECENT_HOURS`` up to ``as_of``;
the baseline is everything before that. No future data is consulted.
"""

from __future__ import annotations

import numpy as np

FEATURE_VERSION = "features-v1"

RECENT_HOURS = 14 * 24
BASELINE_HOURS = 21 * 24  # earliest clean reference window (pre-incident)
NIGHT_HOURS = set(range(0, 6))
_EPS = 1e-9


def _safe_div(a: float, b: float) -> float:
    return float(a) / (float(b) if abs(b) > _EPS else _EPS)


def window_slices(as_of_idx: int) -> tuple[slice, slice]:
    """Return (baseline_slice, recent_slice) honoring the no-leakage rule.

    Baseline is the EARLIEST ``BASELINE_HOURS`` (a clean historical reference) and
    recent is the last ``RECENT_HOURS`` up to ``as_of``. Both windows only read
    indices ``<= as_of_idx``; the gap between them is intentionally ignored so the
    baseline is not contaminated by the onset of an incident.
    """
    end = as_of_idx + 1
    baseline_end = min(BASELINE_HOURS, max(0, end - RECENT_HOURS))
    recent_start = max(baseline_end, end - RECENT_HOURS)
    return slice(0, baseline_end), slice(recent_start, end)


def _daily_means(series: np.ndarray) -> np.ndarray:
    """Mean per calendar day for a contiguous hourly series (drops a trailing partial day)."""
    full_days = series.size // 24
    if full_days == 0:
        return np.array([float(series.mean())]) if series.size else np.array([0.0])
    trimmed = series[: full_days * 24].reshape(full_days, 24)
    return trimmed.mean(axis=1)


def customer_feature_vector(
    meter_kwh: np.ndarray,
    hours: np.ndarray,
    as_of_idx: int,
) -> dict:
    """Base per-customer statistics from a single meter series."""
    baseline_sl, recent_sl = window_slices(as_of_idx)
    full = meter_kwh[: as_of_idx + 1]
    baseline = meter_kwh[baseline_sl]
    recent = meter_kwh[recent_sl]
    recent_hours = hours[recent_sl]

    baseline_mean = float(np.mean(baseline)) if baseline.size else float(np.mean(full))
    baseline_std = float(np.std(baseline)) if baseline.size else float(np.std(full))
    recent_mean = float(np.mean(recent)) if recent.size else 0.0
    recent_std = float(np.std(recent)) if recent.size else 0.0

    night_mask = np.isin(recent_hours, list(NIGHT_HOURS))
    night_mean = float(np.mean(recent[night_mask])) if night_mask.any() else 0.0
    day_mean = float(np.mean(recent[~night_mask])) if (~night_mask).any() else 0.0

    drop_ratio = _safe_div(recent_mean, baseline_mean)
    trend = _safe_div(recent_mean - baseline_mean, baseline_mean)
    zero_thresh = max(0.05 * baseline_mean, 0.05)
    zero_fraction = float(np.mean(recent < zero_thresh)) if recent.size else 0.0
    cv_recent = _safe_div(recent_std, recent_mean)
    flatline = 1.0 if (cv_recent < 0.05 and zero_fraction > 0.8) else 0.0

    # Anomaly z-score on DAILY aggregates so the diurnal swing does not mask a
    # sustained drop. Compared against the clean baseline window's daily variation.
    daily = _daily_means(full)
    base_days = max(1, BASELINE_HOURS // 24)
    recent_days = max(1, RECENT_HOURS // 24)
    base_daily = daily[:base_days]
    recent_daily = daily[-recent_days:]
    base_daily_mean = float(base_daily.mean())
    base_daily_std = float(base_daily.std())
    std_floor = max(base_daily_std, 0.03 * base_daily_mean, _EPS)
    anomaly_z = (base_daily_mean - float(recent_daily.mean())) / std_floor

    return {
        "mean_kwh": round(float(np.mean(full)), 6),
        "std_kwh": round(float(np.std(full)), 6),
        "baseline_mean_kwh": round(baseline_mean, 6),
        "baseline_std_kwh": round(baseline_std, 6),
        "recent_mean_kwh": round(recent_mean, 6),
        "recent_std_kwh": round(recent_std, 6),
        "drop_ratio": round(drop_ratio, 6),
        "trend": round(trend, 6),
        "night_day_ratio": round(_safe_div(night_mean, day_mean), 6),
        "zero_fraction": round(zero_fraction, 6),
        "flatline": flatline,
        "anomaly_z": round(anomaly_z, 6),
    }


def attach_peer_and_spatial(
    customer_features: dict[str, dict],
    customer_neighborhood: dict[str, str],
    transformer_ratio: float,
) -> dict[str, dict]:
    """Add peer deviation, grid imbalance, and spatial neighborhood-risk features.

    ``customer_features`` maps customer ref -> base feature dict for a SINGLE
    transformer's members. Peer median is computed across those members.
    """
    refs = list(customer_features)
    recent_means = np.array([customer_features[r]["recent_mean_kwh"] for r in refs])
    peer_median = float(np.median(recent_means)) if recent_means.size else 0.0

    for r in refs:
        f = customer_features[r]
        peer_dev = _safe_div(peer_median - f["recent_mean_kwh"], peer_median)
        f["peer_median_recent_kwh"] = round(peer_median, 6)
        f["peer_deviation"] = round(peer_dev, 6)
        f["grid_unexplained_ratio"] = round(float(transformer_ratio), 6)

    # Neighborhood spatial risk = mean positive peer deviation among neighbors.
    by_nb: dict[str, list[float]] = {}
    for r in refs:
        nb = customer_neighborhood.get(r, "")
        by_nb.setdefault(nb, []).append(max(0.0, customer_features[r]["peer_deviation"]))
    nb_risk = {nb: (sum(v) / len(v) if v else 0.0) for nb, v in by_nb.items()}
    for r in refs:
        nb = customer_neighborhood.get(r, "")
        customer_features[r]["spatial_neighborhood_risk"] = round(nb_risk.get(nb, 0.0), 6)
    return customer_features


def transformer_feature_vector(
    member_features: dict[str, dict],
    unexplained_ratio: float,
    input_total: float,
    metered_total: float,
    technical_total: float,
    unexplained_total: float,
) -> dict:
    """Aggregate per-transformer features from its members."""
    refs = list(member_features)
    drops = [member_features[r]["drop_ratio"] for r in refs]
    peer_devs = [max(0.0, member_features[r]["peer_deviation"]) for r in refs]
    anomalies = [member_features[r]["anomaly_z"] for r in refs]
    frac_dropping = float(np.mean([1.0 if d < 0.7 else 0.0 for d in drops])) if refs else 0.0
    return {
        "member_count": len(refs),
        "unexplained_ratio": round(float(unexplained_ratio), 6),
        "input_total_kwh": round(float(input_total), 4),
        "metered_total_kwh": round(float(metered_total), 4),
        "technical_total_kwh": round(float(technical_total), 4),
        "unexplained_total_kwh": round(float(unexplained_total), 4),
        "frac_members_dropping": round(frac_dropping, 6),
        "mean_peer_deviation": round(float(np.mean(peer_devs)) if refs else 0.0, 6),
        "max_member_anomaly_z": round(float(np.max(anomalies)) if refs else 0.0, 6),
    }
