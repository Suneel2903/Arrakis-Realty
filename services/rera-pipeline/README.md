# rera-pipeline

Python 3.12, managed with [uv](https://docs.astral.sh/uv/). K-RERA fetch → parse → locate → enrich → export (docs/MAP-01, MAP-02). Only the **locate / sharpen** step exists so far. The rest arrives with S00/S01.

```bash
uv sync                      # install
uv run pytest                # tests (offline: all network calls are faked)
uv run ruff check . && uv run ruff format --check .
```

## Sharpen approximate locations

Re-places every seed project that is not on RERA coordinates/boundary (≈1,650), plus the unplaced ones. Steps run in order, and each step only works on what the earlier ones left:

| Step | What | Method written | Rate |
|---|---|---|---|
| osm | One Overpass download of named `landuse=residential`, `building=apartments\|residential`, `place=neighbourhood` in the Bengaluru bbox; normalised-name match within 5 km of the current pin (anywhere for unplaced) | `osm_name` (+ site outline) | 1 query |
| nominatim | `"<name>, <locality>, Bengaluru"`, then `"<name>, Bengaluru"` | `nominatim` | 1 req/s |
| photon | same queries | `photon` | 1 req/s |
| gmaps *(opt-in)* | Google Maps search in a visible browser, 10–20 s apart; **candidates only** → `exports/gmaps_candidates.csv` | never | 1 per 10–20 s |

Needs network access to `overpass-api.de`, `nominatim.openstreetmap.org`, `photon.komoot.io` (and `www.google.com` for `--gmaps`).

```bash
export GEOCODE_CONTACT_EMAIL=you@example.com          # goes in the User-Agent

# OSM steps (about 1 hour the first time, seconds on reruns thanks to the cache)
uv run python -m rera_pipeline.locate.sharpen \
  --seed ../../reference/blr_rera_projects_located.csv --out ../../exports \
  --map-template ../../reference/bengaluru-rera-map.html

# Google Maps candidates (only after the client has signed off, see docs/DECISIONS.md)
uv sync --extra gmaps
uv run python -m rera_pipeline.locate.sharpen \
  --seed ../../reference/blr_rera_projects_located.csv --out ../../exports \
  --steps osm,nominatim,photon --gmaps \
  --map-template ../../reference/bengaluru-rera-map.html
```

`--limit N` runs the first N targets only (trial run). `--gmaps` opens a visible Chromium with a persistent profile in `exports/.gmaps-profile`; on a machine without a display use `xvfb-run` or add `--gmaps-headless`. If Google shows a captcha or "unusual traffic" page, the run stops and records where it got to; rerun later and it continues with the projects not yet searched.

Outputs in `exports/`:

- `blr_rera_projects_located.csv`: the seed with sharpened rows. New columns: `source`, `source_url`, `fetched_at`, `match_name`, `match_score`, `osm_ref`, `prev_lat/lng/method`, `site_geojson`.
- `geocode_log.csv`: every query and decision (accepted, too_far, ambiguous, name_mismatch, no_result, skipped, blocked).
- `gmaps_candidates.csv`: Google suggestions for operator review.
- `locate_summary.json`: counts per method.
- `bengaluru-rera-map.html`: refreshed map. OSM/Nominatim/Photon matches show as exact dots with the OSM link and outline, and Google candidates show as a separate "Google suggestions" layer.

Rebuild just the map: `uv run python -m rera_pipeline.locate.mapbuild --template ../../reference/bengaluru-rera-map.html --located ../../exports/blr_rera_projects_located.csv --gmaps ../../exports/gmaps_candidates.csv --out ../../exports/bengaluru-rera-map.html`.
