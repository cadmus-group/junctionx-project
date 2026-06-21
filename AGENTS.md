## Learned User Preferences

- User-facing product name is **Atlas** (not GridTrace); use `logo_icon.png` and `logo_full.svg` from `apps/web/public/` for branding
- Internal `@gridtrace/*` and `gridtrace_*` package names are intentional — do not rename unless explicitly requested
- Frontend shell is sharp monochrome (black/white/gray); reserve color for data meaning, risk states, maps, charts, and selection
- Do not re-add Model Analytics or Data Quality pages to the sidebar — those routes were removed
- Map defaults: risk heatmap layer on, hotspots layer off; prefer a zoomed-in initial view
- Use PDOK Locatieserver for geocoding during Stedin data ingest

## Learned Workspace Facts

- Turborepo monorepo: `apps/web` (Next.js :3000), `apps/api` (FastAPI :8003), `apps/worker`, `apps/ml-lab`; shared `ui`, `charts`, `maps`, `config` packages
- `pnpm dev` starts web + API only; Postgres via `docker compose up -d postgres`; run `pnpm db:migrate` and `pnpm db:seed` separately; worker via `python -m gridtrace_worker.main scheduler`
- Demo auth users: `operator`, `analyst`, `inspector`, `demo_operator` — password `SuperSecret123!`
- Stedin consumption CSVs live in `data/raw/Stedin/`; NED.nl API supplies national grid data as 10-minute kWh volumes (aggregate to hourly, not raw MW)
- Optional MOMENT ML scoring needs `./scripts/pip-install-ml.sh` and `MOMENT_ENABLED=true` in `.env`
- `NEXT_PUBLIC_DEMO_MODE=true` runs the UI offline with in-browser mocks
