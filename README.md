# Arrakis Realty Tech Systems

Monorepo for the Arrakis Realty platform: public website, mobile-browser customer app, admin/CRM, and the Bengaluru property map with its data pipeline.

## Layout

```
apps/web/                  Next.js app: public site, customer PWA, /admin
services/rera-pipeline/    Python: K-RERA fetch → parse → locate → enrich → export
packages/db/               SQL migrations (Postgres 16 + PostGIS), applied with dbmate
exports/                   Generated data and maps (located CSV, geocode log, refreshed map)
docs/                      Specs. Read docs/ARCHITECTURE.md first.
docs/sessions/             One brief per Claude Code cloud session
reference/                 Client inputs and earlier prototypes (read-only)
```

## Run it locally

Needs Node 22 + pnpm 10, Python 3.12 + uv, Docker.

```bash
docker compose up --build        # Postgres+PostGIS, migrations, web on http://localhost:3000
pnpm install && pnpm lint && pnpm typecheck && pnpm test
(cd services/rera-pipeline && uv sync && uv run ruff check . && uv run pytest)
pnpm db:new <name>               # new migration in packages/db/migrations
```

Deploying to staging: `docs/DEPLOY.md`.

## Where to start

1. `CLAUDE.md`: rules for every coding session
2. `docs/ARCHITECTURE.md`: stack, environments, phases
3. `docs/sessions/`: run sessions in the order given in `docs/sessions/README.md`

## Reference material (read-only, never edit)

| File | What it is |
|---|---|
| `reference/Arrakis_Realty_-_Scope_document.docx` | Client scope document (AI-drafted; our specs override it where they differ) |
| `reference/prototype-arrakis-ui.html` | Client's clickable prototype: UI flows, lead stages, triggers, roles |
| `reference/Arrakis_Realty_Tech_Systems_at_a_Glance.pptx` | Agreed phase plan |
| `reference/demo-3d-rera-density.html` | Throwaway 3D density demo on real K-RERA data (no basemap) |
| `reference/demo-prep-script.py` | Script that built the demo data; a starting point only |
| `reference/bengaluru-rera-map.html` | Real-map demo: OpenStreetMap basemap, 3D ward/village density, exact vs approximate pins (open in Chrome/Edge) |
| `reference/demo-3d-density-v1.html` | Earlier dark 3D density demo |
| `reference/blr_rera_projects_located.csv` | 3,459 K-RERA projects; 3,270 placed, with `location_method`, `confidence`, `location_note`. Seed for `project` / `project_location` |
