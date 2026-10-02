# MAP-03: The Bengaluru map experience

## What was wrong with the demo
No real streets or landmarks, a dark-and-gold palette that hid meaning, abstract hexagons, and missing older projects. The production map must read like a real map first and a data view second.

## Principles
1. **Real map first.** Roads, metro lines, lakes, landmarks and area names are always visible. Data sits on top of them.
2. **One question per zoom level.** City: "Where is activity?" Area: "Which projects are here?" Project: "What does it look like?"
3. **Honest data.** Approximate pins look approximate. Estimates say so. Non-RERA complexes are a separate grey layer.
4. **Light by default.** A clean day basemap. Satellite as an option. Dark mode follows the system setting.

## Stack
- MapLibre GL JS with a light vector basemap from Protomaps (OSM data) as PMTiles on Cloud Storage + CDN.
- 3D buildings: Overture Maps buildings with heights, converted to PMTiles; `fill-extrusion` layer in neutral grey.
- Data layers: deck.gl via `MapboxOverlay` (interleaved) for density and highlighted towers.
- Satellite option: licensed imagery provider (e.g. MapTiler Satellite or Esri World Imagery), cost per tile view. Decide after usage estimate.
- Photoreal option (later): Google Photorealistic 3D Tiles only if Bengaluru coverage is confirmed at test coordinates.
- Attribution always visible: © OpenStreetMap contributors, Overture Maps, Karnataka RERA.

## Levels
| Level | Zoom | Shows | Interaction |
|---|---|---|---|
| City | 9.5–12 | Basemap with labels; micro-market polygons shaded by number of active projects (or homes); optional "3D density" toggle extrudes them | Tap an area to fly in; legend explains the shading in words ("12–25 projects") |
| Area | 12–15 | Real 3D buildings in grey; RERA projects as pins, clustered below zoom 13.5, labelled above it; colour = status; grey outlines = existing non-RERA communities; Arrakis-listed projects get a distinct marker | Tap a pin to open the project; filters: status, possession year, BHK, budget (Arrakis inventory only) |
| Project | 15+ | Site outline; towers extruded (real footprint where an Overture/OSM building intersects the site, else schematic with "approximate" label); camera orbits | Bottom sheet / side card with RERA facts, enriched facts (labelled), media for Arrakis projects |

## Colours (light theme)
| Token | Hex | Use |
|---|---|---|
| land | #f4f5f7 | basemap land |
| water | #b7d4ea | lakes |
| building | #d6d9de | 3D context buildings |
| status-new | #2563eb | New launch |
| status-ongoing | #e8780f | Ongoing |
| status-done | #6b7280 | Completed |
| existing | #a3a8b0 outline | Non-RERA community |
| arrakis | #0f766e | Projects Arrakis sells |
| density ramp | #e8eefc → #93b4f5 → #2f5fd0 → #1b2f73 | Choropleth (single hue, light to dark) |
Status colours differ in lightness as well as hue.

## Mobile
Bottom sheet with three heights; "3D" toggle button; two-finger tilt; list view toggle ("Show as list") as an accessible alternative to the map.

## Search
Projects, developers, areas and RERA numbers in one box. Results show source and whether the location is exact or approximate.

## Performance
Map route lazy-loaded; city-level data under 1 MB; project detail fetched on tap from `/api/projects/:id`; 60 fps target on a mid-range Android at Area level.
