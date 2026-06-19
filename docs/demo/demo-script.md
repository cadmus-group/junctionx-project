# Demo script

Run `pnpm demo:reset` first for a deterministic dataset.

1. **Command Center** (`/`) — review system KPIs: total unexplained loss, estimated
   value, high/critical counts, loss-trend chart, risk-tier breakdown. Note the
   visible model + feature versions.
2. **Risk Map** (`/map`) — identify a high-risk region via the hotspot heatmap. Adjust
   the risk threshold; the customer layer renders only when zoomed in.
3. **Transformer Digital Twin** (`/assets/transformers/[id]`) — open the critical
   transformer. Read the **energy reconciliation waterfall**: Energy In (12,400) →
   Metered (10,550) → Technical (620) → **Unexplained 1,230 kWh (ratio 0.0992)**.
4. **Suspicious customer** (`/customers/[id]`) — open the CRITICAL customer (score 87).
   Review component scores, **confidence**, SHAP-style explanations, peer comparison,
   loss estimate (kWh) and financial value (EUR). Note the non-accusatory language and
   alternative explanations.
5. **Add to inspection mission** — create or pick a mission and add the customer as a case.
6. **Record outcome** — submit a confirmed outcome; the case resolves and recovery
   estimates are stored.

Also demonstrate the **meter-fault** case: high anomaly but a recommendation to run
*meter diagnostics before fraud escalation* — showing the system avoids false accusation.
