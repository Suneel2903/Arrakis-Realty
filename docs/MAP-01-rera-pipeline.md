# MAP-01: K-RERA data pipeline

## Goal
A weekly, auditable copy of every Karnataka RERA project relevant to Bengaluru, loaded into Postgres with provenance, so the map and admin always show current registry data.

## Why our own pipeline
An open dataset (github.com/Vonter/karnataka-rera-projects, by Vivek Matthew, ODbL) proved the portal can be read with plain HTTP and was used for the demo. We write **our own implementation** against the official portal so that:
- our enriched database is not bound by ODbL share-alike,
- we control refresh timing and fields,
- the only source credited is Karnataka RERA.
Do not copy code from that repo. It may be used to cross-check counts.

## Portal behaviour (observed Oct 2026; verify before building)
| Step | Request | Returns |
|---|---|---|
| Session | GET https://rera.karnataka.gov.in/projectViewDetails | session cookie |
| Districts | GET /viewAllProjects | HTML with `<select id="projectDist" name="district">` |
| Project list per district | POST /projectViewDetails, form: `project=&firm=&appNo=&regNo=&district=<name>&subdistrict=0&btn1=Search` | HTML table; project ids in anchors with `onclick` containing `showFileApplicationPreview`, id attribute numeric |
| Project detail | POST /projectDetails, form: `action=<project_id>`, headers `X-Requested-With: XMLHttpRequest`, `Referer: /projectViewDetails` | Multi-tab HTML: promoter, land, approvals, development details, costs, quarterly updates, documents |

Known failure bodies with HTTP 200: an "Invalid Request" stub and pages truncated before `</html>`. Treat both as failures and retry.

## Scope
Districts: Bengaluru Urban, Bengaluru Rural, Ramanagara (now Bengaluru South district; check portal naming), plus any district whose projects fall inside the Bengaluru metro bounding box after geocoding.

## Stages (each idempotent, each writes to its own table)
1. **fetch**: raw HTML stored gzipped in Cloud Storage `raw/rera/<yyyy-mm-dd>/<project_id>.html.gz`. Listings re-fetched every run; detail pages re-fetched if older than 30 days or status not Completed.
2. **parse**: HTML → `rera_project_raw` (one row per project, all scalar fields, JSON for tables). Parser versioned; store `parser_version`.
3. **normalise**: types, units (sq m), dates, status mapping, promoter name cleanup → `project`.
4. **locate**: see MAP-02. Writes `project_location` with method and confidence.
5. **enrich**: see MAP-02. Writes `project_fact` rows with source and confidence.
6. **export**: GeoJSON → PMTiles (`tippecanoe`) for projects and density cells; upload to Cloud Storage; bump `tiles_version`.

## Politeness and reliability
- 1 request/second max, 3 retries with exponential backoff, run Sunday 01:00–05:00 IST.
- User-Agent identifies Arrakis Realty with a contact email.
- A run that fetches less than 95% of last run's listing count fails loudly (Sentry + WhatsApp alert to admin) and does not publish tiles.

## Fields we need (minimum)
reg_number, project_id, project_name, promoter_name, status, project_status, project_type, district, taluk, address, pin, latitude, longitude, boundary points (N/E/S/W), registration_date, proposed_completion_date, extensions, land_area_sqm, number_of_towers, total_units, development_details (inventory table), FAR, approving_authority, approved_plan_number, quarterly progress, complaint count (if listed).

## Observed coverage (from the open dataset, Sep 2026)
- 3,498 Bengaluru residential/mixed projects; 1,359 have portal coordinates (registrations from about 2022); 2,139 do not.
- About 144 have usable site-boundary points.
- No floors-per-tower field. Floors must come from documents or enrichment.

## Acceptance
See ACCEPTANCE-TESTS.md, section MAP-01.
