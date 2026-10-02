# Acceptance tests

## MAP-01 pipeline
- [ ] Full run lists at least 3,400 Bengaluru residential/mixed projects (Sep 2026 baseline 3,498).
- [ ] Re-run with no portal changes produces zero row changes (idempotent).
- [ ] A truncated or "Invalid Request" detail page is retried and, if still bad, logged as failed without crashing the run.
- [ ] Listing count drop above 5% blocks tile publish and alerts admin.
- [ ] Every `project` row links to a raw HTML file in Cloud Storage.

## MAP-02 location and enrichment
- [ ] **SBR Horizon** (PRM/KA/RERA/1251/446/PR/171123/000625) has a location with method other than portal_latlng, a source URL, and lands in Seegehalli / Kannamangala area (east of Whitefield, near Whitefield–Hoskote Road).
- [ ] SBR Horizon has facts towers=5, floors_per_tower=9, total_units=180, each with source URL and note "from public listing".
- [ ] **AWHO Sandeep Vihar** appears in `existing_complex` near Kannamangala, Whitefield–Hoskote Road, and is NOT in `project`.
- [ ] At least 90% of Bengaluru residential projects have a location; the rest are in the QA queue with a reason.
- [ ] No stored coordinate has source Google Geocoding/Places.
- [ ] Low/medium confidence locations show as approximate in the UI.

## MAP-03 map
- [ ] Streets, metro lines, lakes and area names visible at every level.
- [ ] City → area in one tap; area → project in one tap; breadcrumb returns to each level.
- [ ] Searching "SBR Horizon", "Sandeep Vihar", a promoter name, or a RERA number finds the right item.
- [ ] Status colours distinguishable in greyscale screenshot.
- [ ] Mid-range Android: first map paint under 3s on 4G; Area level pans smoothly.
- [ ] Attribution for OSM, Overture and Karnataka RERA visible.
- [ ] "Show as list" gives the same results as the map for the current view.
