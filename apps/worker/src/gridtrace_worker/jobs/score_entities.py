"""Scoring job: feature_snapshots -> risk_scores (atomic publication).

Maps features to the five risk components (pure, deterministic), composes the
0-100 score and tier via ``gridtrace_domain``, attributes transformer unexplained
loss to customers, and publishes the new generation of scores atomically (old
``is_current`` flags cleared and new rows inserted in a single transaction).

A ``ModelRegistry`` row is written with PR-AUC and precision@K measured against the
known seeded incident labels.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import UTC, datetime

import numpy as np
from gridtrace_api.db.models import FeatureSnapshot, ModelRegistry, RiskScore
from gridtrace_domain import (
    RISK_WEIGHTS_VERSION,
    customer_loss_attribution,
    estimated_loss_value,
    inspection_priority,
)
from sqlalchemy import delete, insert, select, update
from sqlalchemy.orm import Session

from gridtrace_worker import MODEL_VERSION
from gridtrace_worker.config import get_worker_config
from gridtrace_worker.features import FEATURE_VERSION
from gridtrace_worker.log import get_logger, log_event
from gridtrace_worker.ml import ntl_scorer
from gridtrace_worker.scoring import (
    ScoredEntity,
    build_explanations,
    customer_components,
    customer_components_from_ml,
    replace_anomaly_component,
    transformer_components,
)

logger = get_logger("score_entities")

EXPECTED_INSPECTION_COST_EUR = 75.0
PRECISION_AT_K = 20
MOMENT_ALGORITHM = "moment-reconstruction-hybrid+domain-composite"
HEURISTIC_ALGORITHM = "deterministic-logistic-heuristic+zscore-anomaly"


def _load_moment_results(cfg) -> tuple[dict, str | None]:
    """Run MOMENT inference when enabled; return empty dict on failure.

    MOMENT uses torch in a child process so the main worker can run LightGBM/SHAP
    without the two runtimes interfering after inference.
    """
    if not cfg.moment_active:
        return {}, None
    try:
        import json
        import subprocess
        import sys
        import tempfile
        from pathlib import Path

        from gridtrace_worker.ml.moment_pipeline import moment_results_from_json

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            output_path = Path(tmp.name)

        try:
            proc = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "gridtrace_worker.main",
                    "score-moment",
                    "--output",
                    str(output_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            if proc.returncode != 0:
                raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "score-moment failed")

            payload = json.loads(output_path.read_text())
            results = moment_results_from_json(payload)
        finally:
            output_path.unlink(missing_ok=True)

        log_event(
            logger,
            "moment_scoring_applied",
            customers=len(results),
            model=cfg.moment_model_name,
        )
        return results, MOMENT_ALGORITHM
    except Exception as exc:  # noqa: BLE001 — fallback preserves demo reliability
        log_event(logger, "moment_scoring_failed", error=str(exc))
        return {}, None


def _average_precision(labels: np.ndarray, scores: np.ndarray) -> float:
    """Area under the precision-recall curve (average precision)."""
    if labels.sum() == 0:
        return 0.0
    order = np.argsort(-scores, kind="stable")
    y = labels[order]
    tp = np.cumsum(y)
    fp = np.cumsum(1 - y)
    precision = tp / np.maximum(tp + fp, 1)
    recall = tp / labels.sum()
    ap = 0.0
    prev_recall = 0.0
    for p, r in zip(precision, recall, strict=False):
        ap += p * (r - prev_recall)
        prev_recall = r
    return float(ap)


def _precision_at_k(labels: np.ndarray, scores: np.ndarray, k: int) -> float:
    if scores.size == 0:
        return 0.0
    k = min(k, scores.size)
    order = np.argsort(-scores, kind="stable")[:k]
    return float(labels[order].mean())


def run(session: Session, seed: int | None = None) -> dict:
    cfg = get_worker_config()
    price = cfg.energy_price_eur_per_kwh
    effective_seed = 42 if seed is None else seed
    now = datetime.now(UTC)
    moment_results, algorithm_override = _load_moment_results(cfg)

    snapshots = session.execute(
        select(FeatureSnapshot).where(FeatureSnapshot.feature_version == FEATURE_VERSION)
    ).scalars().all()
    if not snapshots:
        raise RuntimeError("No feature snapshots found; run build-features first.")

    customer_snaps = [s for s in snapshots if s.entity_type == "customer"]
    transformer_snaps = [s for s in snapshots if s.entity_type == "transformer"]

    # Train the live AI model (supervised theft classifier + IsolationForest) on the
    # current labelled population. Falls back to the deterministic heuristic when
    # scikit-learn is unavailable or the labels are too sparse to train.
    ml_scoring = ntl_scorer.score_customers(customer_snaps, seed=effective_seed)
    if ml_scoring is not None:
        algorithm = ml_scoring.algorithm
        if algorithm_override:
            algorithm = f"{ml_scoring.algorithm}+moment-anomaly"
        log_event(
            logger,
            "ml_scoring_trained",
            algorithm=ml_scoring.algorithm,
            **ml_scoring.metrics,
        )
    else:
        algorithm = algorithm_override or HEURISTIC_ALGORITHM
        log_event(logger, "ml_scoring_skipped", reason="unavailable_or_insufficient_labels")

    tx_unexplained: dict[str, float] = {}
    for s in transformer_snaps:
        tx_unexplained[s.entity_id] = float(s.features_json.get("unexplained_total_kwh", 0.0))

    # Pass 1: component scores + suspicion weights, grouped by parent transformer.
    cust_scored: dict[str, ScoredEntity] = {}
    by_tx_refs: dict[str, list[str]] = defaultdict(list)
    cust_features: dict[str, dict] = {}
    for s in customer_snaps:
        feats = s.features_json
        ml_res = ml_scoring.results.get(s.entity_id) if ml_scoring else None
        if ml_res is not None:
            scored = customer_components_from_ml(
                feats, ml_res.supervised_probability, ml_res.anomaly_score
            )
        else:
            scored = customer_components(feats)
        cust_scored[s.entity_id] = scored
        cust_features[s.entity_id] = feats
        by_tx_refs[feats.get("parent_transformer_entity_id", "")].append(s.entity_id)

    rows: list[dict] = []
    eval_labels: list[int] = []
    eval_scores: list[float] = []
    moment_applied = 0
    moment_peak_fn = None
    if moment_results:
        from gridtrace_worker.ml.moment_pipeline import moment_peak_explanations

        moment_peak_fn = moment_peak_explanations

    for s in customer_snaps:
        entity_id = s.entity_id
        feats = cust_features[entity_id]
        scored = cust_scored[entity_id]
        moment = moment_results.get(entity_id)
        if moment:
            scored = replace_anomaly_component(scored, moment.anomaly_score)
            moment_applied += 1
        tx_id = feats.get("parent_transformer_entity_id", "")
        member_ids = by_tx_refs.get(tx_id, [entity_id])
        weights = [cust_scored[m].suspicion_weight for m in member_ids]
        total_weight = float(sum(weights)) or 1e-9
        share = float(scored.suspicion_weight) / total_weight

        loss_kwh = customer_loss_attribution(
            scored.suspicion_weight, weights, tx_unexplained.get(tx_id, 0.0)
        )
        loss_kwh = max(0.0, loss_kwh)
        loss_value = estimated_loss_value(loss_kwh, price)
        priority = inspection_priority(
            p_ntl=scored.components.supervised_probability,
            estimated_recoverable_value=loss_value,
            confidence=scored.confidence,
            expected_inspection_cost=EXPECTED_INSPECTION_COST_EUR,
            optional_factor=1.0,
        )
        explanations = build_explanations(scored, feats, share)
        ml_res = ml_scoring.results.get(entity_id) if ml_scoring else None
        if ml_res is not None:
            explanations.extend(ml_res.explanations)
        if moment and moment_peak_fn:
            explanations.extend(moment_peak_fn(moment))

        rows.append(
            _risk_row(
                entity_type="customer",
                entity_id=entity_id,
                scored=scored,
                now=now,
                loss_kwh=loss_kwh,
                loss_value=loss_value,
                priority=priority,
                explanations=explanations,
                currency=cfg.default_currency,
            )
        )
        eval_labels.append(1 if feats.get("is_ntl") else 0)
        eval_scores.append(scored.score)

    for s in transformer_snaps:
        feats = s.features_json
        scored = transformer_components(feats)
        loss_kwh = max(0.0, tx_unexplained.get(s.entity_id, 0.0))
        loss_value = estimated_loss_value(loss_kwh, price)
        priority = inspection_priority(
            p_ntl=scored.components.supervised_probability,
            estimated_recoverable_value=loss_value,
            confidence=scored.confidence,
            expected_inspection_cost=EXPECTED_INSPECTION_COST_EUR,
            optional_factor=1.0,
        )
        explanations = build_explanations(scored, feats, 1.0)
        rows.append(
            _risk_row(
                entity_type="transformer",
                entity_id=s.entity_id,
                scored=scored,
                now=now,
                loss_kwh=loss_kwh,
                loss_value=loss_value,
                priority=priority,
                explanations=explanations,
                currency=cfg.default_currency,
            )
        )

    # ---- Atomic publication: clear old current flags, insert new rows. ----
    session.execute(
        update(RiskScore).where(RiskScore.is_current.is_(True)).values(is_current=False)
    )
    for i in range(0, len(rows), 2000):
        session.execute(insert(RiskScore), rows[i : i + 2000])

    # ---- Model registry with metrics vs. known incident labels. ----
    labels = np.array(eval_labels)
    scores = np.array(eval_scores)
    metrics = {
        "pr_auc": round(_average_precision(labels, scores), 4),
        "precision_at_k": round(_precision_at_k(labels, scores, PRECISION_AT_K), 4),
        "positives": int(labels.sum()),
        "scored_customers": int(labels.size),
        "moment_customers": moment_applied,
        "risk_weights_version": RISK_WEIGHTS_VERSION,
        "ml_enabled": ml_scoring is not None,
    }
    if ml_scoring is not None:
        metrics["ml"] = ml_scoring.metrics
        metrics["feature_importances"] = ml_scoring.feature_importances
    session.execute(delete(ModelRegistry).where(ModelRegistry.model_version == MODEL_VERSION))
    session.execute(update(ModelRegistry).values(is_active=False))
    session.add(
        ModelRegistry(
            id=str(uuid.uuid4()),
            model_version=MODEL_VERSION,
            feature_version=FEATURE_VERSION,
            algorithm=algorithm,
            trained_at=now,
            metrics_json=metrics,
            is_active=True,
            k=PRECISION_AT_K,
            notes=(
                "Supervised theft/no-theft classifier + IsolationForest anomaly "
                "(SHAP explanations when available) trained on the live population; "
                "MOMENT-1-large anomaly override when MOMENT_ENABLED=true; "
                "deterministic heuristic fallback when scikit-learn is unavailable."
            ),
        )
    )

    log_event(
        logger,
        "scores_published",
        model_version=MODEL_VERSION,
        feature_version=FEATURE_VERSION,
        rows=len(rows),
        metrics=metrics,
        moment_enabled=cfg.moment_active,
        moment_applied=moment_applied,
    )
    return {
        "rows": len(rows),
        "metrics": metrics,
        "model_version": MODEL_VERSION,
        "moment_applied": moment_applied,
    }


def _risk_row(
    *,
    entity_type: str,
    entity_id: str,
    scored,
    now: datetime,
    loss_kwh: float,
    loss_value: float,
    priority: float,
    explanations: list[dict],
    currency: str,
) -> dict:
    c = scored.components
    return {
        "id": str(uuid.uuid4()),
        "entity_type": entity_type,
        "entity_id": entity_id,
        "scored_at": now,
        "risk_score": scored.score,
        "risk_tier": scored.tier,
        "supervised_probability": c.supervised_probability,
        "anomaly_score": c.anomaly_score,
        "grid_imbalance_score": c.grid_imbalance_score,
        "peer_score": c.peer_score,
        "spatial_score": c.spatial_score,
        "confidence": scored.confidence,
        "estimated_loss_kwh": round(float(loss_kwh), 4),
        "estimated_loss_value": round(float(loss_value), 2),
        "currency": currency,
        "inspection_priority": round(float(priority), 4),
        "explanations_json": explanations,
        "model_version": MODEL_VERSION,
        "feature_version": FEATURE_VERSION,
        "is_current": True,
    }
