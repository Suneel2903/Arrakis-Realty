# CLAUDE.md: rules for every session

## Product in one line
A sales platform for Bengaluru homes: buyers explore a 3D map of the city, unlock verified project data, book visits and homes; staff run leads and inventory in /admin.

## Stack (do not change without a written decision in docs/DECISIONS.md)
- Web: Next.js (App Router, TypeScript strict), Tailwind, shadcn/ui. One app serves the public site, customer PWA and /admin.
- Map: MapLibre GL JS + deck.gl (MapboxOverlay) for 3D layers. Basemap and building tiles as PMTiles on Cloud Storage + Cloud CDN.
- DB: Postgres 16 + PostGIS on Cloud SQL. Migrations in packages/db as plain SQL.
- Jobs: Python 3.12 pipeline in services/rera-pipeline, run as Cloud Run Jobs on Cloud Scheduler.
- Hosting: GCP asia-south1 (Mumbai). Auth: Firebase phone OTP (customers), email + TOTP (staff).
- Messaging: WhatsApp via BSP. Payments: Razorpay.

## Hard rules
1. Never commit secrets. Use `.env` locally and Secret Manager in GCP. Cloud-session env vars hold test keys only.
2. Every data row that came from outside carries provenance: `source`, `source_url`, `fetched_at`, `confidence`. No silent facts.
3. Never invent data. If a field is unknown it stays NULL and the UI shows "Not available".
4. RERA data is shown as published, credited "Source: Karnataka RERA". Estimates are labelled "estimated" in the UI.
5. Do not scrape sites whose terms forbid it (property portals, Google Search result pages). Use official APIs or the sources listed in docs/MAP-02. OpenStreetMap services (Overpass, Nominatim, Photon) are allowed at their published rate limits. Google Maps lookups are allowed only as a slow, logged, one-at-a-time candidate finder for operator review; results are never stored as final coordinates. No captcha solving, no proxy rotation.
6. Be polite to rera.karnataka.gov.in: max 1 request/second, retries with backoff, identify with a contact User-Agent, run off-peak.
7. Money, consent, permissions and the 10% pre-agreement rule need tests before merge.
8. Small PRs: one session = one PR = one module. Update the relevant doc when behaviour changes.
9. Plan mode first for anything touching schema, auth, payments or the pipeline. Write the plan to docs/plans/<session>.md.

## Definition of done
- Lint, typecheck and tests pass in CI.
- Acceptance tests in docs/ACCEPTANCE-TESTS.md for this module pass.
- Doc updated. Screenshots (mobile + desktop) in the PR for any UI change.
