# S00: Repo scaffold
Read: CLAUDE.md, docs/ARCHITECTURE.md.
Build:
- pnpm workspace; apps/web Next.js (TS strict, Tailwind, shadcn/ui); services/rera-pipeline Python 3.12 with uv, ruff, pytest; packages/db SQL migrations runner.
- docker-compose: postgis/postgis:16, app, pipeline.
- Apply docs/DATA-MODEL.sql as migration 0001.
- GitHub Actions: lint, typecheck, test for web and pipeline; build images; deploy to Cloud Run staging on main (workload identity federation, no JSON keys).
- .env.example with every variable named, no values.
Done when: `docker compose up` serves the web app and the DB has all tables; CI green.
