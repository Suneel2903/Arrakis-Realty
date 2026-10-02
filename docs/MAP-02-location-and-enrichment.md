# MAP-02: Locating every project and filling gaps

## Problem
1. Older RERA projects (2017–2021) have no coordinates. Example: **SBR Horizon**, PRM/KA/RERA/1251/446/PR/171123/000625, registered 2017, address "Sy.No.24_5, Seegehalli Village, Bidarahalli Hobli", no lat/long on the portal.
2. Pre-RERA complexes are not in RERA at all. Example: **AWHO Sandeep Vihar**, Kannamangala, Whitefield–Hoskote Road. Buyers still expect to see them as context.
3. RERA lacks floors, prices, photos and sometimes units.

## Location cascade (stop at the first method that passes validation)
| # | Method | Confidence | Notes |
|---|---|---|---|
| 1 | Portal lat/long | high | Validate inside Bengaluru bbox and within 3 km of the PIN centroid |
| 2 | Portal boundary points → centroid + polygon | high | Reject degenerate polygons (all points equal, area < 200 sq m) |
| 3 | Name match to OpenStreetMap features (`landuse=residential`, `building=apartments`, `place=neighbourhood` with matching `name`), within the village/PIN area | medium-high | Overpass API extract of Bengaluru, refreshed monthly. ODbL: credit OSM |
| 4 | Web lookup: search API query `"<project name>" "<promoter>" Bangalore`; fetch top results that are developer sites or public listings; LLM extracts address, landmark, towers, floors, units, possession; geocode the extracted address | medium | Store every source URL. Use a search API (e.g. Brave Search API or SerpAPI). Do not scrape Google result pages. Do not bulk-crawl property portals; read only the specific pages a search returns |
| 5 | Geocode RERA address: village + hobli + taluk + PIN via LocationIQ or OpenCage (OSM-based, storage allowed) | low-medium | Survey numbers rarely geocode; village centroid is the usual result |
| 6 | PIN centroid | low | Shown as an approximate pin only |

Every method writes `project_location(project_id, lat, lng, polygon, method, confidence, source_url, checked_by, checked_at)`.

**Rules**
- Never use Google Geocoding or Places results as stored map coordinates (terms restrict storage and non-Google-map display). They may be used by a human in QA to sanity-check.
- Confidence low or medium: the project appears in the admin **Location QA queue**. A data operator confirms or drags the pin; that sets `method=manual`, `confidence=verified`.
- The UI shows approximate pins with a dashed outline and the note "Approximate location".

## Non-RERA existing complexes
- Source: OSM named residential polygons and apartment buildings, plus Overture Maps places/buildings.
- Stored in `existing_complex` with `source=osm|overture`, never mixed with RERA rows.
- Shown on the map as a separate grey layer "Existing communities (not RERA-registered)". No RERA claims are made about them.
- Example fixture: AWHO Sandeep Vihar must appear in this layer near Kannamangala, Whitefield–Hoskote Road.

## Enrichment of missing facts
Fields: floors per tower, total units (if missing), possession date (actual), configurations (BHK mix), size range.
- Sources in priority: RERA documents (sanctioned plan / form PDFs, extracted by LLM) > developer website > public listing page returned by search.
- Each value is a `project_fact(project_id, field, value, source, source_url, extracted_at, confidence, note)`.
- Conflicting values: keep all; the UI shows the highest-priority source and flags "sources differ" in admin.
- The UI labels enriched values "From developer/listing; not RERA-verified".
- Fixture: SBR Horizon. Public listings report 5 towers, 9 floors, 180 units, about 2 acres, possession June 2019. These must load as facts with source URLs and a note, not as RERA data.

## Budget guard
Search API calls capped per run (config, default 500). Enrichment only for projects visible in target micro-markets first, then city-wide.
