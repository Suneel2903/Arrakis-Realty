# Architecture

## Phases (agreed plan)
| Phase | Weeks | Scope |
|---|---|---|
| Pre-start | before Week 1 | Accounts, approvals, repo, GCP staging, feasibility tests |
| Phase 0 | 1–2 | Website, OTP login + paid access, WhatsApp OTP and alerts, admin (users, roles, Excel/media upload), leads + pre-sales view, ad lead capture |
| Phase 1 | 3–10 | Pipeline and SLAs, visits, holds, reports, refunds, GST, **3D city map**, media viewers, ads dashboard, bookings, fee ledger, privacy centre |
| Phase 2 | after 10 | Mobile apps, push, advisor app, AI assistant, Hindi/Kannada |

The map data pipeline (docs/MAP-01, MAP-02) starts in Phase 0 as a parallel track so data is ready when the map UI lands in Phase 1.

## Components
```
            ┌──────────── Cloud CDN ─────────────┐
 Browser ──►│ Next.js on Cloud Run (web + /admin)│──► Cloud SQL Postgres + PostGIS
            │ PMTiles: basemap, buildings,        │
            │ projects (Cloud Storage)            │
            └─────────────────────────────────────┘
 Cloud Scheduler ─► Cloud Run Job: rera-pipeline (weekly)
                      fetch → parse → locate → enrich → load DB → export tiles
 Integrations: Firebase Auth, Razorpay, WhatsApp BSP, Meta/Google lead forms, GA4, Sentry
```

## Environments
- `local`: docker compose (Postgres + PostGIS), seed data from reference/demo-prep-script.py output.
- `staging`: GCP project arrakis-staging, test keys only.
- `prod`: GCP project arrakis-prod, Secret Manager, daily backups, PITR on Cloud SQL.

## Budgets
- First screen under 2.5s on a mid-range Android over 4G.
- Map JS loaded lazily, only on map routes.
- City-level map data under 1 MB; project details fetched on demand.

## Decisions log
Record any deviation in docs/DECISIONS.md (date, decision, reason).
