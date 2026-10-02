# S02a plan: sharpen approximate locations (OSM first, Google candidates for QA)

Asked for directly (no separate review round). Code: `services/rera-pipeline/src/rera_pipeline/locate/`, run guide in `services/rera-pipeline/README.md`.

- Targets: seed rows not on `portal_latlng`/`portal_boundary` (1,460 approximate + 189 unplaced = 1,649). 31 have names too generic to name-match ("Zest", "Sr Residency"); they skip the OSM steps but still go to the Google candidate step.
- Steps 1–3 (Overpass name match, Nominatim, Photon) write `osm_name` / `nominatim` / `photon` with the OSM URL as provenance. Google Maps (step 4, opt-in `--gmaps`) writes candidates only.
- Acceptance: name score ≥ 0.92 on normalised tokens; inside Bengaluru bbox; ≤ 5 km from the current pin (any distance for unplaced); two equally good matches > 300 m apart are rejected as ambiguous.
- Schema follow-up for S02: add `nominatim`, `photon` to the `project_location.method` CHECK.
- Not run yet: this session's network policy blocks the OSM hosts. Run it in a session that allows them (see README).
