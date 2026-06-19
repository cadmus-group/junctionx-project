from __future__ import annotations

from datetime import UTC, datetime

import pytest
from geoalchemy2.shape import from_shape
from gridtrace_api.db.models import (
    AssetEnergyReading,
    Customer,
    GridAsset,
    MeterReading,
    Operator,
    TechnicalLossEstimate,
)
from gridtrace_api.modules.assets.service import get_reconciliation
from gridtrace_api.modules.gis.service import anomalies_geojson
from shapely.geometry import Point

pytestmark = pytest.mark.asyncio


async def _seed(session):
    op = Operator(name="Test", country_code="NLD", timezone="Europe/Amsterdam")
    session.add(op)
    await session.flush()

    transformer = GridAsset(
        operator_id=op.id,
        asset_type="transformer",
        external_id="TX-1",
        name="TX-1",
        geometry=from_shape(Point(4.9, 52.37), srid=4326),
    )
    session.add(transformer)
    await session.flush()

    ts = datetime(2026, 1, 1, tzinfo=UTC)
    session.add(
        AssetEnergyReading(
            asset_id=transformer.id, timestamp=ts, energy_input_kwh=12400.0
        )
    )
    session.add(
        TechnicalLossEstimate(
            asset_id=transformer.id, timestamp=ts, estimated_technical_loss_kwh=620.0
        )
    )
    customer = Customer(
        operator_id=op.id,
        external_ref="C-1",
        transformer_id=transformer.id,
        customer_type="residential",
        geometry=from_shape(Point(4.9001, 52.3701), srid=4326),
    )
    session.add(customer)
    await session.flush()
    session.add(
        MeterReading(meter_id=customer.id, timestamp=ts, consumption_kwh=10550.0)
    )
    await session.commit()
    return transformer.id


async def test_reconciliation_matches_showcase(session):
    tx_id = await _seed(session)
    rec = await get_reconciliation(session, tx_id)
    assert rec.energy_input_kwh == pytest.approx(12400.0)
    assert rec.metered_output_kwh == pytest.approx(10550.0)
    assert rec.estimated_technical_loss_kwh == pytest.approx(620.0)
    assert rec.unexplained_loss_kwh == pytest.approx(1230.0)
    assert rec.unexplained_loss_ratio == pytest.approx(0.0992, abs=1e-3)


async def test_anomalies_geojson_is_valid_feature_collection(session):
    await _seed(session)
    fc = await anomalies_geojson(session, bbox=None, min_risk=0.0)
    assert fc["type"] == "FeatureCollection"
    assert isinstance(fc["features"], list)
