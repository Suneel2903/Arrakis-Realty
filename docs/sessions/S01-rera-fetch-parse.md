# S01: K-RERA fetch, parse, normalise
Read: docs/MAP-01-rera-pipeline.md, CLAUDE.md rules 2, 5, 6.
Build in services/rera-pipeline:
- `fetch` with session handling, rate limit 1 req/s, retries, failure-body detection, raw gz storage (local dir or GCS by config).
- `parse` HTML → rera_project_raw.data (all tabs; inventory and documents as JSON). Fixture tests on 5 saved pages (new-format with lat/long, old-format 2017, plotted, mixed, withdrawn).
- `normalise` → project.
- CLI: `pipeline run --districts "Bengaluru Urban,Bengaluru Rural" --limit N`.
- Cloud Run Job definition + Cloud Scheduler (Sunday 01:00 IST).
Done when: MAP-01 acceptance tests pass on staging with a full Bengaluru run.
