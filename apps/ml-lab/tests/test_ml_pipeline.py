"""ML lab pipeline tests (deterministic; sklearn fallback is sufficient)."""

from __future__ import annotations

import numpy as np
from gridtrace_ml import FEATURE_VERSION
from gridtrace_ml.datasets import customer_time_split
from gridtrace_ml.datasets.splits import load_dataset
from gridtrace_ml.evaluation import evaluate
from gridtrace_ml.explainability import explain_customer
from gridtrace_ml.features import FEATURE_COLUMNS, build_feature_frame
from gridtrace_ml.inference import predict_frame
from gridtrace_ml.registry import save_artifact
from gridtrace_ml.training import train_models

SEED = 42


def test_dataset_is_deterministic():
    a = load_dataset(SEED)
    b = load_dataset(SEED)
    assert a.showcase == b.showcase
    assert len(a.customers) == len(b.customers)


def test_no_train_test_customer_overlap():
    split = customer_time_split(SEED)
    split.assert_no_overlap()
    assert split.train_refs and split.test_refs
    assert split.train_refs.isdisjoint(split.test_refs)


def test_no_temporal_leakage():
    split = customer_time_split(SEED)
    split.assert_no_temporal_leakage()
    assert split.train_as_of_idx < split.test_as_of_idx


def test_feature_frame_columns_and_labels():
    ds = load_dataset(SEED)
    frame = build_feature_frame(ds)
    for col in FEATURE_COLUMNS:
        assert col in frame.columns
    assert frame["label_is_ntl"].sum() > 0


def test_component_and_risk_score_ranges():
    split = customer_time_split(SEED)
    bundle = train_models(split.train, SEED)
    scored = predict_frame(bundle, split.test)
    for col in (
        "supervised_probability",
        "anomaly_score",
        "grid_imbalance_score",
        "peer_score",
        "spatial_score",
    ):
        assert scored[col].between(0.0, 1.0).all()
    assert scored["risk_score"].between(0.0, 100.0).all()


def test_evaluation_reports_pr_auc_and_precision_at_k():
    split = customer_time_split(SEED)
    bundle = train_models(split.train, SEED)
    scored = predict_frame(bundle, split.test)
    report = evaluate(
        scored["label_is_ntl"].to_numpy(), scored["risk_score"].to_numpy(), k=20
    ).to_dict()
    assert report["primary_metric"] == "pr_auc"
    assert 0.0 <= report["pr_auc"] <= 1.0
    assert 0.0 <= report["precision_at_k"] <= 1.0


def test_explanations_generated():
    ds = load_dataset(SEED)
    frame = build_feature_frame(ds)
    split = customer_time_split(SEED)
    bundle = train_models(split.train, SEED)
    exps = explain_customer(bundle, frame, ds.showcase["customer_external_ref"])
    assert exps and all({"feature", "label", "contribution", "direction"} <= set(e) for e in exps)


def test_artifact_metadata_persisted(tmp_path):
    split = customer_time_split(SEED)
    bundle = train_models(split.train, SEED)
    scored = predict_frame(bundle, split.test)
    report = evaluate(scored["label_is_ntl"].to_numpy(), scored["risk_score"].to_numpy())
    manifest = save_artifact(
        bundle,
        report.to_dict(),
        scored,
        model_version="test-model-v1",
        artifacts_dir=tmp_path,
    )
    assert manifest["feature_version"] == FEATURE_VERSION
    assert manifest["metrics"]["primary_metric"] == "pr_auc"
    assert (tmp_path / "test-model-v1" / "model.joblib").exists()
    assert (tmp_path / "test-model-v1" / "metadata.json").exists()
    assert (tmp_path / "test-model-v1" / "predictions.parquet").exists()


def test_showcase_customer_high_risk():
    ds = load_dataset(SEED)
    frame = build_feature_frame(ds)
    split = customer_time_split(SEED)
    bundle = train_models(split.train, SEED)
    scored = predict_frame(bundle, frame)
    row = scored.loc[scored["external_ref"] == ds.showcase["customer_external_ref"]].iloc[0]
    assert float(row["risk_score"]) >= 70.0
    assert int(np.isfinite(row["risk_score"])) == 1
