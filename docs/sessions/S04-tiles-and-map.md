# S04: Tiles and map UI
Read: docs/MAP-03-map-experience.md.
Build:
- Tile build step: Protomaps Bengaluru basemap extract; Overture buildings for Bengaluru bbox; projects + existing complexes + micro-market density → PMTiles; upload; versioned URLs.
- apps/web route /explore: MapLibre + deck.gl overlay, three levels, breadcrumb, search, filters, bottom sheet, list view, attribution.
- API: GET /api/projects/:id (RERA fields + facts with sources + location method/confidence).
- Light theme tokens from MAP-03; dark follows system.
Done when: MAP-03 acceptance tests pass; screenshots at three levels on mobile and desktop in the PR.
