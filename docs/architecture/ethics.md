# Security & ethics

GridTrace is a **decision-support** tool, not an enforcement system.

## Non-negotiable principles

- **No automatic accusation or enforcement.** Outputs are prioritization signals.
- **Human inspection required** before any conclusion or action.
- **Non-accusatory language** everywhere in the UI and API ("probable", "suspicious",
  "prioritize inspection" — never "thief"/"fraudster").
- **Visible confidence and alternatives.** High-risk cases surface alternative
  explanations (meter fault, vacancy, tariff change) to rule out first.
- **Synthetic data only.** No real personally identifiable customer data is used.
- **Authoritative scoring stays on the backend.** The browser never computes the score.

## Security

- Public browser config (`NEXT_PUBLIC_*`) is separated from secrets.
- Local environment files are never committed; CI scans for committed secrets.
- PostGIS `pgcrypto` is available for at-rest hashing where needed.
- JWT-based auth; demo mode resolves a demo operator for frictionless showcasing.

## Limitations

- Synthetic data approximates but does not reproduce real grid behavior.
- The supervised component is calibrated on seeded incidents, not field-verified labels.
- Technical loss is an estimate, not a measurement.
