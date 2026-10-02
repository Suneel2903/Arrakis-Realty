# Cloud session briefs

Run each brief as one Claude Code cloud session. Start in plan mode, save the plan to `docs/plans/<id>.md`, review, then execute. One PR per session.

| Order | Brief | Depends on | Model |
|---|---|---|---|
| 1 | S00-scaffold.md | none | Opus |
| 2 | P0-sessions.md (A–F, can run in parallel after S00) | S00 | Sonnet; Opus for auth/payments |
| 3 | S01-rera-fetch-parse.md | S00 | Opus |
| 4 | S02-locate.md | S01 | Opus |
| 5 | S03-enrich.md | S02 | Sonnet |
| 6 | S04-tiles-and-map.md | S02 (S03 optional) | Opus |
| 7 | S05-location-qa-admin.md | S02, P0-C | Sonnet |

Cloud sessions: network access must allow rera.karnataka.gov.in, registry.npmjs.org, pypi.org, overpass-api.de, the search API host and the geocoder host. Long full-city runs go to the GCP Cloud Run Job, not the session VM.
