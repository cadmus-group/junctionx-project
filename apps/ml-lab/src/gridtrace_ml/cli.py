"""Command-line interface for the GridTrace ML lab.

    python -m gridtrace_ml <command> [options]
    gridtrace-ml <command> [options]      (console script)

Commands: generate-synthetic, build-features, train, evaluate, explain,
publish-artifact, score-demo.
"""

from __future__ import annotations

import json

import click

from gridtrace_ml import MODEL_VERSION
from gridtrace_ml.datasets import customer_time_split
from gridtrace_ml.datasets.splits import TEST_AS_OF_IDX, load_dataset
from gridtrace_ml.evaluation import evaluate
from gridtrace_ml.explainability import explain_customer, global_importances
from gridtrace_ml.features import build_feature_frame
from gridtrace_ml.inference import predict_frame
from gridtrace_ml.registry import save_artifact
from gridtrace_ml.training import train_models


def _echo(obj) -> None:
    click.echo(json.dumps(obj, indent=2, default=str))


def _full_frame(seed: int):
    ds = load_dataset(seed)
    return ds, build_feature_frame(ds, TEST_AS_OF_IDX)


@click.group()
def cli() -> None:
    """GridTrace ML lab CLI."""


@cli.command("generate-synthetic")
@click.option("--seed", default=42, type=int)
def generate_synthetic_cmd(seed: int) -> None:
    ds = load_dataset(seed)
    _echo(
        {
            "seed": seed,
            "customers": len(ds.customers),
            "transformers": len(ds.transformers),
            "timestamps": len(ds.timestamps),
            "showcase": ds.showcase,
        }
    )


@cli.command("build-features")
@click.option("--seed", default=42, type=int)
def build_features_cmd(seed: int) -> None:
    _, frame = _full_frame(seed)
    _echo(
        {
            "rows": int(len(frame)),
            "columns": list(frame.columns),
            "positives": int(frame["label_is_ntl"].sum()),
        }
    )


@cli.command("train")
@click.option("--seed", default=42, type=int)
def train_cmd(seed: int) -> None:
    split = customer_time_split(seed)
    bundle = train_models(split.train, seed)
    _echo(
        {
            "algorithm": bundle.algorithm,
            "feature_columns": bundle.feature_columns,
            "train_rows": int(len(split.train)),
            "test_rows": int(len(split.test)),
            "training_metadata": bundle.metadata,
        }
    )


@cli.command("evaluate")
@click.option("--seed", default=42, type=int)
@click.option("--k", default=20, type=int)
def evaluate_cmd(seed: int, k: int) -> None:
    split = customer_time_split(seed)
    bundle = train_models(split.train, seed)
    scored = predict_frame(bundle, split.test)
    report = evaluate(scored["label_is_ntl"].to_numpy(), scored["risk_score"].to_numpy(), k=k)
    _echo({"algorithm": bundle.algorithm, "report": report.to_dict()})


@cli.command("explain")
@click.option("--seed", default=42, type=int)
@click.option("--ref", default=None, help="Customer external_ref (defaults to showcase)")
def explain_cmd(seed: int, ref: str | None) -> None:
    ds, frame = _full_frame(seed)
    split = customer_time_split(seed)
    bundle = train_models(split.train, seed)
    target = ref or ds.showcase["customer_external_ref"]
    _echo(
        {
            "customer": target,
            "global_importances": global_importances(bundle, frame),
            "explanations": explain_customer(bundle, frame, target),
        }
    )


@cli.command("publish-artifact")
@click.option("--seed", default=42, type=int)
@click.option("--model-version", default=MODEL_VERSION)
@click.option("--artifacts-dir", default=None)
def publish_artifact_cmd(seed: int, model_version: str, artifacts_dir: str | None) -> None:
    split = customer_time_split(seed)
    bundle = train_models(split.train, seed)
    scored_test = predict_frame(bundle, split.test)
    report = evaluate(
        scored_test["label_is_ntl"].to_numpy(), scored_test["risk_score"].to_numpy()
    )

    _, full = _full_frame(seed)
    scored_full = predict_frame(bundle, full)
    manifest = save_artifact(
        bundle,
        report.to_dict(),
        scored_full,
        model_version=model_version,
        artifacts_dir=artifacts_dir,
        notes="ML-lab gradient-boosted NTL classifier + IsolationForest anomaly.",
    )
    _echo(manifest)


@cli.command("score-demo")
@click.option("--seed", default=42, type=int)
def score_demo_cmd(seed: int) -> None:
    ds, frame = _full_frame(seed)
    split = customer_time_split(seed)
    bundle = train_models(split.train, seed)
    scored = predict_frame(bundle, frame)
    showcase_ref = ds.showcase["customer_external_ref"]
    row = scored.loc[scored["external_ref"] == showcase_ref].iloc[0]
    report = evaluate(scored["label_is_ntl"].to_numpy(), scored["risk_score"].to_numpy())
    _echo(
        {
            "showcase_customer": showcase_ref,
            "risk_score": round(float(row["risk_score"]), 2),
            "risk_tier": row["risk_tier"],
            "supervised_probability": round(float(row["supervised_probability"]), 4),
            "anomaly_score": round(float(row["anomaly_score"]), 4),
            "explanations": explain_customer(bundle, frame, showcase_ref),
            "report": report.to_dict(),
        }
    )

if __name__ == "__main__":
    cli()
