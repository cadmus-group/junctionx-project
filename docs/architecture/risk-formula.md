# Risk formula

All formulas are implemented once in `packages/domain-py`
(`gridtrace_domain.formulas`). Do not duplicate or change them silently — see the
risk-formula change process in [`CONTRIBUTING.md`](../../CONTRIBUTING.md).

## Unexplained energy loss

```
UnexplainedLoss(a,t) = EnergyIn(a,t) − Σ MeteredConsumption(c,t) − EstimatedTechnicalLoss(a,t)
```

The **signed residual is preserved** for diagnostics. Clamp only in presentation or
prioritization (e.g. negative residuals do not create negative loss exposure).

## Unexplained loss ratio

```
UnexplainedLossRatio(a,t) = UnexplainedLoss(a,t) / max(EnergyIn(a,t), ε)     ε = 1e-9
```

## Composite risk score

```
RiskScore = 100 × (0.40·P_supervised + 0.25·S_anomaly + 0.20·S_grid + 0.10·S_peer + 0.05·S_spatial)
```

Each component is in `[0,1]`; the output is in `[0,100]`. Weights are versioned
(`RISK_WEIGHTS_VERSION`) and exposed via backend metadata. **The frontend displays
component values but never recomputes the authoritative score.**

## Risk tiers

| Tier     | Range   |
|----------|---------|
| LOW      | 0–29    |
| WATCH    | 30–49   |
| MEDIUM   | 50–69   |
| HIGH     | 70–84   |
| CRITICAL | 85–100  |

## Customer loss attribution

```
Attribution(c,t) = SuspicionWeight(c,t) / Σ SuspicionWeight(j,t) × UnexplainedLoss(transformer,t)
```

Operational estimate only — **never** presented as legal proof.

## Estimated financial value

```
EstimatedLossValue(c) = EstimatedLossKWh(c) × ApplicableEnergyPrice
```

Always reported with currency, tariff assumption, and estimation period.

## Inspection priority

```
InspectionPriority(c) = P(NTL_c) × EstimatedRecoverableValue(c) × Confidence(c) − ExpectedInspectionCost(c)
```

Optional factors: travel time, cluster efficiency, asset criticality, case age.
The raw value is normalized to a 0–100 display score by the API.
