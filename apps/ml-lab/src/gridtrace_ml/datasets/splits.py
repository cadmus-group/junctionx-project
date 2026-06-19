"""Leakage-safe dataset splitting.

Two independent guards against leakage:

1. CUSTOMER split: train and test customer sets are DISJOINT (a customer never
   appears in both), so the model cannot memorize an individual meter.
2. TIME split: train features are computed at an EARLIER ``as_of`` than the test
   features. Because the worker feature functions only read data up to ``as_of``,
   the training rows never see the evaluation period.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

import pandas as pd
from gridtrace_worker.jobs.generate_synthetic import build_demo_dataset

from gridtrace_ml.features import build_feature_frame

# Train on data up to ~46 days; evaluate at the full 60-day horizon.
TRAIN_AS_OF_IDX = 46 * 24 - 1
TEST_AS_OF_IDX = 60 * 24 - 1


def load_dataset(seed: int):
    return build_demo_dataset(seed)


def _is_test_customer(external_ref: str, test_fraction: float) -> bool:
    digest = hashlib.sha256(external_ref.encode()).hexdigest()
    bucket = int(digest[:8], 16) / 0xFFFFFFFF
    return bucket < test_fraction


@dataclass
class SplitResult:
    train: pd.DataFrame
    test: pd.DataFrame
    train_as_of_idx: int
    test_as_of_idx: int

    @property
    def train_refs(self) -> set[str]:
        return set(self.train["external_ref"])

    @property
    def test_refs(self) -> set[str]:
        return set(self.test["external_ref"])

    def assert_no_overlap(self) -> None:
        overlap = self.train_refs & self.test_refs
        if overlap:
            raise AssertionError(f"train/test customer overlap: {len(overlap)} customers")

    def assert_no_temporal_leakage(self) -> None:
        if self.train_as_of_idx >= self.test_as_of_idx:
            raise AssertionError("train as_of must be strictly earlier than test as_of")


def customer_time_split(seed: int, test_fraction: float = 0.3) -> SplitResult:
    ds = load_dataset(seed)
    train_frame = build_feature_frame(ds, TRAIN_AS_OF_IDX)
    test_frame = build_feature_frame(ds, TEST_AS_OF_IDX)

    test_mask = test_frame["external_ref"].map(lambda r: _is_test_customer(r, test_fraction))
    train_refs = set(test_frame.loc[~test_mask, "external_ref"])
    test_refs = set(test_frame.loc[test_mask, "external_ref"])

    train = train_frame[train_frame["external_ref"].isin(train_refs)].reset_index(drop=True)
    test = test_frame[test_frame["external_ref"].isin(test_refs)].reset_index(drop=True)

    result = SplitResult(train, test, TRAIN_AS_OF_IDX, TEST_AS_OF_IDX)
    result.assert_no_overlap()
    result.assert_no_temporal_leakage()
    return result
