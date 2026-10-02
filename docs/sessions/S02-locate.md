# S02: Locate every project
Read: docs/MAP-02-location-and-enrichment.md.
Build:
- Cascade methods 1, 2, 3, 5, 6 (method 4 web lookup comes in S03 and slots in by config).
- OSM extract: Overpass query for Bengaluru bbox, named `landuse=residential`, `building=apartments|residential`, `place=neighbourhood`; store in a cache table; fuzzy name match (normalised tokens, promoter tokens as tie-breaker) within village/PIN area.
- Load existing_complex from the same OSM extract (+ Overture places if available).
- Validation: bbox, distance to PIN centroid, duplicate-pin detection.
- Report: counts per method/confidence; list of unresolved projects with reason.
Done when: SBR Horizon and AWHO Sandeep Vihar tests pass or are listed with a clear reason; at least 90% located.
