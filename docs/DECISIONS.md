# Decisions

| Date | Decision | Reason |
|---|---|---|
| 2026-10-02 | GCP asia-south1 + Google Workspace | Client choice |
| 2026-10-02 | Own K-RERA scraper, not the ODbL dataset | Avoid share-alike on enriched DB; credit RERA only |
| 2026-10-02 | Light real-map basemap (MapLibre + Protomaps + Overture) | Demo without basemap was confusing |
| 2026-10-02 | Sharpen approximate pins with OSM name matches (Overpass), then Nominatim and Photon name search | Free, no keys, ODbL lets us store the coordinates with OSM credit |
| 2026-10-02 | Google Maps used only as a slow candidate finder for operator review, never stored (CLAUDE.md rule 5). **Pending client sign-off:** Google's terms forbid automated use and reuse of Maps coordinates; the client carries that risk and must agree in writing before `--gmaps` runs | Places projects OSM cannot, with a human confirming each pin |
