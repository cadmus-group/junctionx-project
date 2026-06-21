from sqlalchemy import create_engine, text

e = create_engine("postgresql+psycopg://gridtrace:gridtrace@localhost:5432/gridtrace")
with e.connect() as c:
    print("=== Dashboard KPIs ===")
    row = c.execute(
        text(
            """
            SELECT
              (SELECT count(*) FROM customers) AS customers,
              (SELECT count(*) FROM grid_assets WHERE asset_type = 'transformer') AS transformers,
              (SELECT coalesce(sum(estimated_loss_kwh), 0) FROM risk_scores
                 WHERE is_current AND entity_type = 'customer') AS loss_kwh,
              (SELECT coalesce(sum(estimated_loss_value), 0) FROM risk_scores
                 WHERE is_current AND entity_type = 'customer') AS loss_eur,
              (SELECT count(*) FROM inspection_cases
                 WHERE status NOT IN ('resolved', 'dismissed')) AS open_inspections
            """
        )
    ).one()
    print(dict(row._mapping))

    print("\n=== Risk tiers ===")
    for tier, count in c.execute(
        text(
            """
            SELECT risk_tier, count(*)
            FROM risk_scores
            WHERE is_current AND entity_type = 'customer'
            GROUP BY 1 ORDER BY 2 DESC
            """
        )
    ):
        print(tier, count)

    print("\n=== Sample Stedin coords ===")
    for row in c.execute(
        text(
            """
            SELECT external_ref, zipcode,
                   ST_X(geometry::geometry) AS lon,
                   ST_Y(geometry::geometry) AS lat
            FROM customers
            WHERE external_ref LIKE 'STEDIN-%'
            LIMIT 8
            """
        )
    ):
        print(row)

    print("\n=== Postcode / coord stats ===")
    print(
        c.execute(
            text(
                """
                SELECT min(zipcode), max(zipcode), count(DISTINCT zipcode),
                       min(ST_X(geometry::geometry)), max(ST_X(geometry::geometry)),
                       min(ST_Y(geometry::geometry)), max(ST_Y(geometry::geometry))
                FROM customers WHERE zipcode IS NOT NULL
                """
            )
        ).one()
    )

    print("\n=== Timestamp ranges ===")
    print(
        c.execute(
            text(
                """
                SELECT
                  (SELECT min(timestamp) FROM meter_readings) AS mr_min,
                  (SELECT max(timestamp) FROM meter_readings) AS mr_max,
                  (SELECT min(timestamp) FROM asset_energy_readings) AS ae_min,
                  (SELECT max(timestamp) FROM asset_energy_readings) AS ae_max
                """
            )
        ).one()
    )

    print("\n=== Loss scores ===")
    print(
        c.execute(
            text(
                """
                SELECT
                  count(*) FILTER (WHERE coalesce(estimated_loss_kwh, 0) = 0) AS zero_loss,
                  count(*) AS total,
                  avg(risk_score) AS avg_score
                FROM risk_scores
                WHERE is_current AND entity_type = 'customer'
                """
            )
        ).one()
    )

    print("\n=== Loss trend sample (last 3 days) ===")
    for row in c.execute(
        text(
            """
            WITH days AS (
              SELECT date_trunc('day', timestamp) AS day,
                     sum(energy_input_kwh) AS energy_in
              FROM asset_energy_readings
              GROUP BY 1
            ),
            meter AS (
              SELECT date_trunc('day', timestamp) AS day,
                     sum(consumption_kwh) AS metered
              FROM meter_readings
              GROUP BY 1
            ),
            tech AS (
              SELECT date_trunc('day', timestamp) AS day,
                     sum(estimated_technical_loss_kwh) AS technical
              FROM technical_loss_estimates
              GROUP BY 1
            )
            SELECT d.day, d.energy_in,
                   coalesce(m.metered, 0) AS metered,
                   coalesce(t.technical, 0) AS technical,
                   d.energy_in - coalesce(m.metered, 0) - coalesce(t.technical, 0) AS unexplained
            FROM days d
            LEFT JOIN meter m USING (day)
            LEFT JOIN tech t USING (day)
            ORDER BY d.day DESC
            LIMIT 5
            """
        )
    ):
        print(row)
