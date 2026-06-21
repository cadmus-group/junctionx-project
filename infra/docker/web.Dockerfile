# GridTrace web image (Next.js standalone)
FROM node:22-slim AS base
ENV PNPM_HOME=/pnpm
ENV PATH="$PNPM_HOME:$PATH"
RUN corepack enable && corepack prepare pnpm@10.15.1 --activate
WORKDIR /app

FROM base AS deps
# Copy workspace manifests first for better layer caching.
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json apps/web/
COPY packages/api-client/package.json packages/api-client/
COPY packages/charts/package.json packages/charts/
COPY packages/config/package.json packages/config/
COPY packages/contracts/package.json packages/contracts/
COPY packages/domain/package.json packages/domain/
COPY packages/eslint-config/package.json packages/eslint-config/
COPY packages/maps/package.json packages/maps/
COPY packages/testing/package.json packages/testing/
COPY packages/typescript-config/package.json packages/typescript-config/
COPY packages/ui/package.json packages/ui/
ENV CI=true
RUN pnpm install --frozen-lockfile --ignore-scripts --filter @gridtrace/web...

FROM base AS build
COPY --from=deps /app/ ./
COPY apps/web apps/web
COPY packages packages
# Public env vars must be present at build time for Next.js.
ARG NEXT_PUBLIC_API_BASE_URL
ARG NEXT_PUBLIC_MAP_STYLE_URL
ARG NEXT_PUBLIC_DEMO_MODE
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL \
    NEXT_PUBLIC_MAP_STYLE_URL=$NEXT_PUBLIC_MAP_STYLE_URL \
    NEXT_PUBLIC_DEMO_MODE=$NEXT_PUBLIC_DEMO_MODE \
    CI=true
RUN pnpm --filter @gridtrace/web build

FROM base AS run
ENV NODE_ENV=production
ENV PORT=3000
# Next.js standalone binds to localhost unless HOSTNAME is set (required in containers).
ENV HOSTNAME=0.0.0.0
COPY --from=build /app/apps/web/.next/standalone ./
COPY --from=build /app/apps/web/.next/static ./apps/web/.next/static
COPY --from=build /app/apps/web/public ./apps/web/public
COPY apps/web/scripts/railway-start.sh ./railway-start.sh
RUN chmod +x ./railway-start.sh
EXPOSE 3000
CMD ["./railway-start.sh"]
