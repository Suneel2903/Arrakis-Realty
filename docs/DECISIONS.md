# Decisions

| Date | Decision | Reason |
|---|---|---|
| 2026-10-02 | GCP asia-south1 + Google Workspace | Client choice |
| 2026-10-02 | Own K-RERA scraper, not the ODbL dataset | Avoid share-alike on enriched DB; credit RERA only |
| 2026-10-02 | Light real-map basemap (MapLibre + Protomaps + Overture) | Demo without basemap was confusing |
| 2026-10-02 | Sharpen approximate pins with OSM name matches (Overpass), then Nominatim and Photon name search | Free, no keys, ODbL lets us store the coordinates with OSM credit |
| 2026-10-02 | Migrations with dbmate (plain SQL files, `-- migrate:up/down`), not a home-made runner | Mature, one static binary, works the same in compose, CI and a Cloud Run Job |
| 2026-10-02 | Next.js 16 (current release at scaffold time) | The stack says Next.js App Router; no reason to start on an older major |
| 2026-10-02 | `project_location.method` also allows `nominatim`, `photon`, `village_centroid`, `locality_name`, `ward_centroid` and `google_candidate` (low confidence only) | Match what the locate tooling and the seed CSV write; Google rows are QA candidates, the operator's confirmed pin is stored as `manual` |
| 2026-10-02 | Seed CSV comes from the open karnataka-rera-projects dataset (ODbL): fine for prototype/demo with credit; rebuild from our own S01 scraper before launch | Avoid ODbL share-alike on the production database |
| 2026-10-02 | Google Maps used only as a slow candidate finder for operator review, never stored (CLAUDE.md rule 5). **Pending client sign-off:** Google's terms forbid automated use and reuse of Maps coordinates; the client carries that risk and must agree in writing before `--gmaps` runs | Places projects OSM cannot, with a human confirming each pin |
