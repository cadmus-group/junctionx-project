# Contributing to GridTrace

## Commit convention

Use [Conventional Commits](https://www.conventionalcommits.org/):
`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`, `ci:`.
Scope by area when useful, e.g. `feat(api): add reconciliation endpoint`.

## Pull requests

- Keep PRs focused and small.
- Add tests for any business rule (formulas, scoring, thresholds).
- **Regenerate contracts after API changes**: `pnpm generate:contracts` and commit
  the result. CI fails if generated contracts are stale.
- **Create an Alembic migration for any schema change** (`apps/api`). Keep seed data
  out of migrations.
- **Document architecture decisions** with an ADR under `docs/adr/`.

## Risk-formula changes (special care)

Risk weights and thresholds are domain-critical. Any change MUST update, together:

1. `packages/domain-py` (the formula + version bump)
2. `packages/config` / `packages/domain` (TS display mirrors)
3. tests in `packages/domain-py/tests` and `packages/domain`
4. docs in `docs/architecture/risk-formula.md`
5. demo fixtures / expected showcase values

Never change a weight silently.

## Quality gates (must pass)

No TypeScript errors · no Python lint errors · no failed tests · no stale contracts ·
no invalid migrations · no committed secrets.

```bash
pnpm lint && pnpm typecheck && pnpm test
source .venv/bin/activate
ruff check . && mypy packages/domain-py/src apps/api/src && pytest
```
