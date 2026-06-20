"""Deterministic synthetic dataset generator for the GridTrace demo.

The generator is split into a PURE in-memory builder (``build_demo_dataset``) and a
persistence step (``persist_dataset``). The pure builder is fully deterministic
given a seed and is unit-tested without a database; the persistence step writes the
shared ORM tables from ``gridtrace_api.db.models``.

Physical model (so the energy balance reconciles exactly through the domain
formula ``unexplained_loss = input - metered - technical``):

    delivered[h]  = sum of customers' TRUE hourly consumption on the transformer
    input[h]      = delivered[h] / (1 - tech_factor) * (1 + extra_ntl)
    technical[h]  = tech_factor * input[h]
    metered[h]    = delivered[h] - stolen[h]      (under-reporting reduces the meter)
    unexplained   = input - metered - technical  = stolen + delivered * extra_ntl

So a customer that under-reports steals exactly (true - meter); the transformer
energy-balance picks it up as unexplained loss. ``extra_ntl`` adds a small, realistic
baseline non-technical loss on clean transformers.

Showcase calibration (documented, deterministic): the showcase transformer's
coordinated-cluster under-report fraction is solved at generation time so the
transformer's 60-day unexplained-loss ratio lands on ~0.0992, then all of that
transformer's energy is uniformly scaled so the 60-day energy input lands near the
illustrative 12,400 kWh target. Uniform scaling preserves both the ratio and the
exact energy-balance reconciliation.
"""

from __future__ import annotations

import random
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import numpy as np
from geoalchemy2.shape import from_shape
from gridtrace_api.db.models import (
    AssetEnergyReading,
    Customer,
    GridAsset,
    MeterReading,
    Operator,
    Region,
    TechnicalLossEstimate,
    User,
)
from gridtrace_api.modules.auth.constants import (
    DEMO_OPERATOR_ID,
    DEMO_OPERATOR_NAME,
    DEMO_OPERATOR_PASSWORD_HASH,
    DEMO_OPERATOR_ROLE,
    DEMO_OPERATOR_USERNAME,
)
from shapely.geometry import Point
from sqlalchemy import insert
from sqlalchemy.orm import Session

from gridtrace_worker.connectors.amsterdam_context import AmsterdamContextConnector
from gridtrace_worker.log import get_logger, log_event

logger = get_logger("generate_synthetic")

# ---------------------------------------------------------------------------
# Tunable, documented constants for the seeded demo.
# ---------------------------------------------------------------------------
NUM_DAYS = 60
HOURS_PER_DAY = 24
NUM_TIMESTAMPS = NUM_DAYS * HOURS_PER_DAY
SERIES_END = datetime(2026, 6, 1, 0, 0, 0, tzinfo=UTC)
INCIDENT_ONSET_DAYS_BEFORE_END = 30  # incidents start in the last 30 days

NUM_FEEDERS = 4
NUM_TRANSFORMERS = 10
NUM_CUSTOMERS = 1000
NUM_NEIGHBORHOODS = 5

TECH_LOSS_FACTOR = 0.05  # ~5% technical loss of transformer input
CLEAN_EXTRA_NTL = 0.013  # small realistic baseline NTL on clean transformers

SHOWCASE_TRANSFORMER_INDEX = 0
METER_FAULT_TRANSFORMER_INDEX = 1
SHOWCASE_CUSTOMER_COUNT = 60
CLUSTER_SIZE = 16  # coordinated under-reporting customers on the showcase transformer
PARTIAL_BYPASS_DROP = 0.64  # showcase customer under-reports 64%

SHOWCASE_RATIO_TARGET = 0.0992
SHOWCASE_INPUT_KWH_TARGET = 12400.0

AMS_LAT = 52.37
AMS_LON = 4.90

# Residential diurnal shape (24 values), normalized to mean 1.0 below.
_RESIDENTIAL_SHAPE = np.array(
    [0.45, 0.40, 0.38, 0.37, 0.40, 0.55, 0.85, 1.20, 1.25, 1.05, 0.95, 0.95,
     1.00, 0.95, 0.90, 0.95, 1.10, 1.45, 1.70, 1.65, 1.45, 1.15, 0.80, 0.55],
    dtype=float,
)
_COMMERCIAL_SHAPE = np.array(
    [0.30, 0.28, 0.27, 0.27, 0.30, 0.45, 0.70, 1.05, 1.55, 1.75, 1.80, 1.80,
     1.75, 1.78, 1.75, 1.65, 1.45, 1.20, 0.85, 0.60, 0.50, 0.42, 0.38, 0.33],
    dtype=float,
)


def _normalized(shape: np.ndarray) -> np.ndarray:
    return shape / shape.mean()


_RES = _normalized(_RESIDENTIAL_SHAPE)
_COM = _normalized(_COMMERCIAL_SHAPE)


@dataclass
class CustomerSpec:
    external_ref: str
    customer_type: str
    transformer_idx: int
    feeder_idx: int
    neighborhood_idx: int
    lon: float
    lat: float
    incident: str | None = None  # "partial_bypass" | "coordinated_cluster" | "meter_fault"
    is_ntl: bool = False  # ground-truth label for evaluation (theft only, not meter fault)
    true_kwh: np.ndarray = field(default_factory=lambda: np.zeros(NUM_TIMESTAMPS))
    meter_kwh: np.ndarray = field(default_factory=lambda: np.zeros(NUM_TIMESTAMPS))


@dataclass
class TransformerSpec:
    external_id: str
    index: int
    feeder_idx: int
    neighborhood_idx: int
    lon: float
    lat: float
    capacity_kva: float
    voltage_level: str
    input_kwh: np.ndarray = field(default_factory=lambda: np.zeros(NUM_TIMESTAMPS))
    technical_kwh: np.ndarray = field(default_factory=lambda: np.zeros(NUM_TIMESTAMPS))


@dataclass
class DemoDataset:
    seed: int
    timestamps: list[datetime]
    operator: dict
    regions: list[dict]
    feeders: list[dict]
    transformers: list[TransformerSpec]
    customers: list[CustomerSpec]
    showcase: dict


def _timestamps() -> list[datetime]:
    start = SERIES_END - timedelta(hours=NUM_TIMESTAMPS)
    return [start + timedelta(hours=i) for i in range(NUM_TIMESTAMPS)]


def _weekday_factor(ts: datetime) -> float:
    # Slightly lower on weekends for residential demand.
    return 0.92 if ts.weekday() >= 5 else 1.0


def _true_profile(
    rng: np.random.Generator,
    base_daily_kwh: float,
    shape: np.ndarray,
    timestamps: list[datetime],
) -> np.ndarray:
    out = np.empty(NUM_TIMESTAMPS, dtype=float)
    noise = rng.normal(0.0, 0.11, size=NUM_TIMESTAMPS)
    per_hour_base = base_daily_kwh / HOURS_PER_DAY
    for i, ts in enumerate(timestamps):
        h = ts.hour
        val = per_hour_base * shape[h] * _weekday_factor(ts) * (1.0 + noise[i])
        out[i] = max(val, 0.0)
    return out


def build_demo_dataset(seed: int) -> DemoDataset:
    """Build the full in-memory demo dataset deterministically from ``seed``."""
    rng = np.random.default_rng(seed)
    py_rng = random.Random(seed)
    timestamps = _timestamps()
    onset_idx = NUM_TIMESTAMPS - INCIDENT_ONSET_DAYS_BEFORE_END * HOURS_PER_DAY
    window = slice(onset_idx, NUM_TIMESTAMPS)

    operator = {
        "name": "GridTrace Demo Distribution Operator",
        "country_code": "NLD",
        "timezone": "Europe/Amsterdam",
        "default_currency": "EUR",
    }

    municipality = {
        "code": "AMS",
        "name": "Amsterdam",
        "region_type": "municipality",
        "parent_code": None,
    }
    neighborhoods = [
        {
            "code": f"AMS-N{i+1}",
            "name": f"Amsterdam Neighborhood {i+1}",
            "region_type": "neighborhood",
            "parent_code": "AMS",
        }
        for i in range(NUM_NEIGHBORHOODS)
    ]
    regions = [municipality, *neighborhoods]

    feeders = []
    for f in range(NUM_FEEDERS):
        lon = AMS_LON + rng.normal(0, 0.02)
        lat = AMS_LAT + rng.normal(0, 0.02)
        feeders.append(
            {
                "external_id": f"FDR-{f+1:02d}",
                "name": f"Feeder {f+1}",
                "voltage_level": "MV",
                "lon": float(lon),
                "lat": float(lat),
                "neighborhood_idx": f % NUM_NEIGHBORHOODS,
            }
        )

    transformers: list[TransformerSpec] = []
    for t in range(NUM_TRANSFORMERS):
        nb = t % NUM_NEIGHBORHOODS
        feeder_idx = t % NUM_FEEDERS
        lon = AMS_LON + 0.01 * (nb - 2) + rng.normal(0, 0.004)
        lat = AMS_LAT + 0.008 * ((t % 3) - 1) + rng.normal(0, 0.004)
        transformers.append(
            TransformerSpec(
                external_id=f"TX-{t+1:03d}",
                index=t,
                feeder_idx=feeder_idx,
                neighborhood_idx=nb,
                lon=float(lon),
                lat=float(lat),
                capacity_kva=float(py_rng.choice([250, 400, 630, 1000])),
                voltage_level="LV",
            )
        )

    # Distribute customers across transformers. The showcase transformer gets a
    # fixed count so the cluster calibration is stable; the rest are spread evenly.
    counts = [0] * NUM_TRANSFORMERS
    counts[SHOWCASE_TRANSFORMER_INDEX] = SHOWCASE_CUSTOMER_COUNT
    remaining = NUM_CUSTOMERS - SHOWCASE_CUSTOMER_COUNT
    others = [i for i in range(NUM_TRANSFORMERS) if i != SHOWCASE_TRANSFORMER_INDEX]
    for j in range(remaining):
        counts[others[j % len(others)]] += 1

    customers: list[CustomerSpec] = []
    cust_n = 0
    for t_idx, tx in enumerate(transformers):
        for _ in range(counts[t_idx]):
            cust_n += 1
            # Keep the showcase transformer all-residential so its energy balance is
            # dominated by comparable loads (large commercial customers would dwarf
            # the under-reporting signal and flatten the unexplained-loss ratio).
            is_commercial = (t_idx != SHOWCASE_TRANSFORMER_INDEX) and (py_rng.random() < 0.12)
            ctype = "commercial" if is_commercial else "residential"
            if is_commercial:
                base_daily = float(rng.uniform(30, 55))
                shape = _COM
            else:
                base_daily = float(rng.uniform(7.0, 13.5))
                shape = _RES
            lon = tx.lon + rng.normal(0, 0.0016)
            lat = tx.lat + rng.normal(0, 0.0016)
            spec = CustomerSpec(
                external_ref=f"CUST-{cust_n:05d}",
                customer_type=ctype,
                transformer_idx=t_idx,
                feeder_idx=tx.feeder_idx,
                neighborhood_idx=tx.neighborhood_idx,
                lon=float(lon),
                lat=float(lat),
            )
            spec.true_kwh = _true_profile(rng, base_daily, shape, timestamps)
            spec.meter_kwh = spec.true_kwh.copy()
            customers.append(spec)

    by_transformer: dict[int, list[CustomerSpec]] = {i: [] for i in range(NUM_TRANSFORMERS)}
    for c in customers:
        by_transformer[c.transformer_idx].append(c)

    # ---- Incident 1: partial bypass (showcase CRITICAL customer) on T0 ----
    showcase_customer = by_transformer[SHOWCASE_TRANSFORMER_INDEX][0]
    # Give it a stable, slightly-elevated residential profile so the drop is stark.
    showcase_customer.customer_type = "residential"
    showcase_customer.true_kwh = _true_profile(rng, 12.0, _RES, timestamps)
    showcase_customer.meter_kwh = showcase_customer.true_kwh.copy()
    showcase_customer.meter_kwh[window] = showcase_customer.true_kwh[window] * (1.0 - PARTIAL_BYPASS_DROP)
    showcase_customer.incident = "partial_bypass"
    showcase_customer.is_ntl = True

    # ---- Incident 2: coordinated cluster on the same showcase transformer ----
    cluster = by_transformer[SHOWCASE_TRANSFORMER_INDEX][1 : 1 + CLUSTER_SIZE]
    for c in cluster:
        c.incident = "coordinated_cluster"
        c.is_ntl = True

    # Calibrate the cluster under-report fraction so the transformer's unexplained
    # ratio lands on SHOWCASE_RATIO_TARGET. (extra_ntl is 0 on the showcase tx.)
    t0_customers = by_transformer[SHOWCASE_TRANSFORMER_INDEX]
    delivered_total = float(sum(c.true_kwh.sum() for c in t0_customers))
    input_total = delivered_total / (1.0 - TECH_LOSS_FACTOR)
    stolen_target = SHOWCASE_RATIO_TARGET * input_total
    stolen_show = float(showcase_customer.true_kwh[window].sum() * PARTIAL_BYPASS_DROP)
    cluster_true_window = float(sum(c.true_kwh[window].sum() for c in cluster)) or 1.0
    cluster_fraction = (stolen_target - stolen_show) / cluster_true_window
    cluster_fraction = float(min(0.9, max(0.05, cluster_fraction)))
    for c in cluster:
        c.meter_kwh[window] = c.true_kwh[window] * (1.0 - cluster_fraction)

    # ---- Incident 3: meter fault (flatline) on T1 ----
    mf_customer = by_transformer[METER_FAULT_TRANSFORMER_INDEX][0]
    mf_customer.incident = "meter_fault"
    mf_customer.is_ntl = False  # technical fault, NOT theft
    mf_customer.meter_kwh = mf_customer.true_kwh.copy()
    mf_customer.meter_kwh[window] = 0.02  # near-zero flatline

    # ---- Transformer energy balance for every transformer ----
    showcase_input_natural = 0.0
    for tx in transformers:
        members = by_transformer[tx.index]
        delivered = np.sum([c.true_kwh for c in members], axis=0)
        if isinstance(delivered, float):  # no members (shouldn't happen)
            delivered = np.zeros(NUM_TIMESTAMPS)
        if tx.index == SHOWCASE_TRANSFORMER_INDEX:
            extra = np.zeros(NUM_TIMESTAMPS)
        else:
            extra = CLEAN_EXTRA_NTL + rng.normal(0, 0.002, size=NUM_TIMESTAMPS)
            extra = np.clip(extra, 0.0, None)
        input_base = delivered / (1.0 - TECH_LOSS_FACTOR)
        tx.input_kwh = input_base * (1.0 + extra)
        tx.technical_kwh = TECH_LOSS_FACTOR * tx.input_kwh
        if tx.index == SHOWCASE_TRANSFORMER_INDEX:
            showcase_input_natural = float(tx.input_kwh.sum())

    # ---- Scale the showcase transformer to the illustrative energy target ----
    scale_k = SHOWCASE_INPUT_KWH_TARGET / max(showcase_input_natural, 1e-9)
    tx0 = transformers[SHOWCASE_TRANSFORMER_INDEX]
    tx0.input_kwh *= scale_k
    tx0.technical_kwh *= scale_k
    for c in by_transformer[SHOWCASE_TRANSFORMER_INDEX]:
        c.true_kwh *= scale_k
        c.meter_kwh *= scale_k

    # Recompute showcase reconciliation snapshot for verification/reporting.
    metered_total = float(sum(c.meter_kwh.sum() for c in by_transformer[SHOWCASE_TRANSFORMER_INDEX]))
    in_total = float(tx0.input_kwh.sum())
    tech_total = float(tx0.technical_kwh.sum())
    unexplained_total = in_total - metered_total - tech_total
    showcase = {
        "transformer_external_id": tx0.external_id,
        "customer_external_ref": showcase_customer.external_ref,
        "cluster_fraction": cluster_fraction,
        "energy_input_kwh": round(in_total, 2),
        "metered_kwh": round(metered_total, 2),
        "technical_kwh": round(tech_total, 2),
        "unexplained_kwh": round(unexplained_total, 2),
        "unexplained_ratio": round(unexplained_total / max(in_total, 1e-9), 4),
        "meter_fault_customer_external_ref": mf_customer.external_ref,
        "meter_fault_transformer_external_id": transformers[METER_FAULT_TRANSFORMER_INDEX].external_id,
    }

    log_event(
        logger,
        "synthetic_dataset_built",
        seed=seed,
        customers=len(customers),
        transformers=len(transformers),
        timestamps=len(timestamps),
        showcase=showcase,
    )

    return DemoDataset(
        seed=seed,
        timestamps=timestamps,
        operator=operator,
        regions=regions,
        feeders=feeders,
        transformers=transformers,
        customers=customers,
        showcase=showcase,
    )


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------
def _point(lon: float, lat: float):
    return from_shape(Point(lon, lat), srid=4326)


def _chunked(rows: list[dict], size: int = 5000):
    for i in range(0, len(rows), size):
        yield rows[i : i + size]


def persist_dataset(session: Session, dataset: DemoDataset) -> dict:
    """Write the in-memory dataset into the shared ORM tables.

    Returns a small summary dict used by the verification step.
    """
    operator = Operator(id=str(uuid.uuid4()), **dataset.operator)
    session.add(operator)
    session.flush()

    session.merge(
        User(
            id=DEMO_OPERATOR_ID,
            username=DEMO_OPERATOR_USERNAME,
            name=DEMO_OPERATOR_NAME,
            role=DEMO_OPERATOR_ROLE,
            password_hash=DEMO_OPERATOR_PASSWORD_HASH,
            operator_id=operator.id,
        )
    )
    session.flush()

    region_ids: dict[str, str] = {}
    # Insert municipality first so neighborhoods can reference it as parent.
    for r in dataset.regions:
        rid = str(uuid.uuid4())
        region_ids[r["code"]] = rid
    for r in dataset.regions:
        session.add(
            Region(
                id=region_ids[r["code"]],
                operator_id=operator.id,
                parent_region_id=region_ids.get(r["parent_code"]) if r["parent_code"] else None,
                region_type=r["region_type"],
                code=r["code"],
                name=r["name"],
                geometry=None,
                properties_json={},
            )
        )
    session.flush()

    neighborhood_codes = [r["code"] for r in dataset.regions if r["region_type"] == "neighborhood"]

    feeder_ids: dict[int, str] = {}
    for idx, f in enumerate(dataset.feeders):
        fid = str(uuid.uuid4())
        feeder_ids[idx] = fid
        session.add(
            GridAsset(
                id=fid,
                operator_id=operator.id,
                parent_asset_id=None,
                asset_type="feeder",
                external_id=f["external_id"],
                name=f["name"],
                voltage_level=f["voltage_level"],
                capacity_kva=None,
                region_id=region_ids[neighborhood_codes[f["neighborhood_idx"]]],
                geometry=_point(f["lon"], f["lat"]),
                properties_json={},
            )
        )
    session.flush()

    transformer_ids: dict[int, str] = {}
    for tx in dataset.transformers:
        txid = str(uuid.uuid4())
        transformer_ids[tx.index] = txid
        session.add(
            GridAsset(
                id=txid,
                operator_id=operator.id,
                parent_asset_id=feeder_ids[tx.feeder_idx],
                asset_type="transformer",
                external_id=tx.external_id,
                name=f"Transformer {tx.external_id}",
                voltage_level=tx.voltage_level,
                capacity_kva=tx.capacity_kva,
                region_id=region_ids[neighborhood_codes[tx.neighborhood_idx]],
                geometry=_point(tx.lon, tx.lat),
                properties_json={},
            )
        )
    session.flush()

    customer_ids: dict[str, str] = {}
    amsterdam_ctx = AmsterdamContextConnector()
    for c in dataset.customers:
        cid = str(uuid.uuid4())
        customer_ids[c.external_ref] = cid
        ctx = amsterdam_ctx.classify_customer(c.lon, c.lat)
        session.add(
            Customer(
                id=cid,
                operator_id=operator.id,
                external_ref=c.external_ref,
                meter_asset_id=None,
                transformer_id=transformer_ids[c.transformer_idx],
                feeder_id=feeder_ids[c.feeder_idx],
                region_id=region_ids[neighborhood_codes[c.neighborhood_idx]],
                customer_type=c.customer_type,
                tariff_type="single",
                building_type="apartment" if c.customer_type == "residential" else "office",
                woningwaarde_category=ctx.get("woningwaarde_category"),
                solar_potential_flag=bool(ctx.get("solar_potential_flag")),
                geometry=_point(c.lon, c.lat),
                metadata_json={
                    "incident": c.incident,
                    "is_ntl": bool(c.is_ntl),
                    "seed_label": True,
                    "zonatlas_label": ctx.get("zonatlas_label"),
                },
            )
        )
    session.flush()

    # Bulk-insert readings via Core for throughput.
    meter_rows: list[dict] = []
    for c in dataset.customers:
        cid = customer_ids[c.external_ref]
        for i, ts in enumerate(dataset.timestamps):
            meter_rows.append(
                {
                    "id": str(uuid.uuid4()),
                    "meter_id": cid,
                    "timestamp": ts,
                    "consumption_kwh": round(float(c.meter_kwh[i]), 6),
                    "voltage": 230.0,
                    "current": None,
                    "power_factor": 0.95,
                    "reading_quality": "good",
                    "source": "ami",
                }
            )
    for chunk in _chunked(meter_rows):
        session.execute(insert(MeterReading), chunk)

    asset_rows: list[dict] = []
    tech_rows: list[dict] = []
    for tx in dataset.transformers:
        txid = transformer_ids[tx.index]
        for i, ts in enumerate(dataset.timestamps):
            asset_rows.append(
                {
                    "id": str(uuid.uuid4()),
                    "asset_id": txid,
                    "timestamp": ts,
                    "energy_input_kwh": round(float(tx.input_kwh[i]), 6),
                    "energy_output_kwh": None,
                    "reading_quality": "good",
                    "source": "scada",
                }
            )
            tech_rows.append(
                {
                    "id": str(uuid.uuid4()),
                    "asset_id": txid,
                    "timestamp": ts,
                    "estimated_technical_loss_kwh": round(float(tx.technical_kwh[i]), 6),
                    "method": "loss_factor",
                    "confidence": 0.8,
                    "model_version": "tech-loss-v1",
                }
            )
    for chunk in _chunked(asset_rows):
        session.execute(insert(AssetEnergyReading), chunk)
    for chunk in _chunked(tech_rows):
        session.execute(insert(TechnicalLossEstimate), chunk)

    log_event(
        logger,
        "synthetic_dataset_persisted",
        meter_readings=len(meter_rows),
        asset_readings=len(asset_rows),
        technical_estimates=len(tech_rows),
    )

    return {
        "operator_id": operator.id,
        "transformer_ids": transformer_ids,
        "customer_ids": customer_ids,
        "showcase": dataset.showcase,
        "as_of": dataset.timestamps[-1],
    }


def run(session: Session, seed: int) -> dict:
    """Generate and persist the deterministic demo dataset (idempotent per fresh DB)."""
    dataset = build_demo_dataset(seed)
    return persist_dataset(session, dataset)
