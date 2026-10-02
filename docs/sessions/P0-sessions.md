# Phase 0 sessions (run after S00; A–F can run in parallel)
Read: docs/PHASE-0-SCOPE.md and reference/prototype-arrakis-ui.html for flows, stage names and copy.

- **P0-A Auth + consent** (Opus): Firebase phone OTP, per-purpose consent ledger, 18+ confirmation, staff email + TOTP, session handling.
- **P0-B Payments** (Opus): Razorpay order + checkout + verified webhook, access grant, receipt, idempotency, test-mode e2e test.
- **P0-C Admin core** (Sonnet): users, roles (Super admin, Admin, Sales manager, Sales executive), permissions middleware, audit log, project/unit CRUD, Excel import with validation report, media upload to Cloud Storage.
- **P0-D Leads** (Sonnet): lead model, 10 stages, notes, owner, UTM/gclid/fbclid capture, Meta and Google lead-form webhooks, pre-sales view of assigned leads.
- **P0-E WhatsApp** (Sonnet): BSP client, templates (OTP, welcome, payment received, advisor connect), inbound webhook to lead timeline, opt-out.
- **P0-F Website** (Sonnet): home, how it works, project page, policy pages, SEO, GA4 + consent banner.
