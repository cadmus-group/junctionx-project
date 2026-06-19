## Summary

<!-- What and why. Link issues. -->

## Scope

<!-- Areas touched: frontend / backend / ml / gis / data / infra / docs -->

## Screenshots or API examples

<!-- UI screenshots, or request/response examples for API changes -->

## Testing performed

<!-- Commands run and results -->

## Migration impact

- [ ] No schema change
- [ ] Alembic migration added (reversible where practical)

## Contract-generation impact

- [ ] No API change
- [ ] Ran `pnpm generate:contracts` and committed the result

## Risk-formula impact

- [ ] No change to formulas/weights/thresholds
- [ ] Updated formula + version + tests + docs + fixtures together

## Checklist

- [ ] `pnpm lint && pnpm typecheck && pnpm test` pass
- [ ] `uv run ruff check . && uv run mypy ... && uv run pytest` pass
- [ ] No secrets committed
- [ ] ADR added for architecture changes
