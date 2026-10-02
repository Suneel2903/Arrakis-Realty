# Build context: repository root (pnpm workspace). docker build -f apps/web/Dockerfile .
FROM node:22-alpine AS base
ENV PNPM_HOME=/pnpm PATH=/pnpm:$PATH NEXT_TELEMETRY_DISABLED=1
RUN corepack enable
WORKDIR /repo

FROM base AS build
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json apps/web/
RUN pnpm install --frozen-lockfile --filter @arrakis/web...
COPY apps/web apps/web
RUN pnpm --filter @arrakis/web build

FROM node:22-alpine AS run
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PORT=8080 HOSTNAME=0.0.0.0
RUN adduser -D -u 10001 web
COPY --from=build --chown=web /repo/apps/web/.next/standalone ./
COPY --from=build --chown=web /repo/apps/web/.next/static ./apps/web/.next/static
COPY --from=build --chown=web /repo/apps/web/public ./apps/web/public
USER web
EXPOSE 8080
CMD ["node", "apps/web/server.js"]
