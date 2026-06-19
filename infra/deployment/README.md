# Deployment

| Component | Target |
|-----------|--------|
| `apps/web` | Vercel (or any Next.js host) |
| `apps/api` | Container — `infra/docker/api.Dockerfile` |
| `apps/worker` | Separate process — `infra/docker/worker.Dockerfile` |
| Database | Managed PostgreSQL with PostGIS |

## Release steps

1. Build and push the API/worker images.
2. Run migrations as an explicit step: `pnpm db:migrate`.
3. Deploy API and worker.
4. Deploy web (Vercel) with `NEXT_PUBLIC_API_BASE_URL` pointed at the API.
5. For a showcase environment, run `pnpm demo:reset` with fixed `DEMO_SEED` and
   pinned model artifacts.

Provide environment variables per [`.env.example`](../../.env.example). Keep public
(`NEXT_PUBLIC_*`) values separate from secrets.
