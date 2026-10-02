"""Sharpen approximate and missing project locations.

    uv run python -m rera_pipeline.locate.sharpen \\
        --seed ../../reference/blr_rera_projects_located.csv --out ../../exports [--gmaps]

Targets every seed project not placed from RERA coordinates/boundary, plus the unplaced.
Steps run in order and each only sees what the previous ones left:
  1. osm        Overpass named residential features, name match within 5 km
  2. nominatim  name search, 1 req/s
  3. photon     name search, 1 req/s
  4. gmaps      (opt-in) Google Maps candidates for operator review, never stored as locations
Rerunning is cheap: every HTTP response is cached under <out>/cache.
"""

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from . import geocoders, gmaps, osm
from .common import EXACT_METHODS, GeoLog, Http, Match, Project, now_iso, user_agent

ADDED_FIELDS = [
    "source",
    "source_url",
    "fetched_at",
    "match_name",
    "match_score",
    "osm_ref",
    "prev_lat",
    "prev_lng",
    "prev_method",
    "site_geojson",
]
UNPLACED_PREFIX = "needs web lookup or manual pin: "


def _clean(v: str) -> str:
    return "" if v is None or v.strip().lower() in ("nan", "none") else v.strip()


def load_seed(path: Path) -> tuple[list[dict], list[str]]:
    with path.open(newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        rows = [{k: _clean(v) for k, v in row.items()} for row in r]
        return rows, list(r.fieldnames or [])


def to_project(row: dict) -> Project:
    lat, lng = row.get("lat"), row.get("lng")
    note = row.get("location_note", "")
    return Project(
        reg=row["reg_number"],
        name=row["project"],
        promoter=row.get("promoter", ""),
        area=row.get("area", ""),
        address=note[len(UNPLACED_PREFIX) :] if note.startswith(UNPLACED_PREFIX) else "",
        lat=float(lat) if lat else None,
        lng=float(lng) if lng else None,
        method=row.get("location_method", ""),
    )


def is_target(row: dict) -> bool:
    return row.get("location_method") not in EXACT_METHODS


def apply(row: dict, m: Match) -> None:
    c = m.cand
    row.update(
        prev_lat=row.get("lat", ""),
        prev_lng=row.get("lng", ""),
        prev_method=row.get("location_method", ""),
        lat=f"{c.lat:.6f}",
        lng=f"{c.lng:.6f}",
        location_method=m.method,
        confidence=m.confidence,
        location_note=(
            f"{m.note}; {m.dist_km:.2f} km from previous pin"
            if m.dist_km is not None
            else f"{m.note}; previously unplaced"
        ),
        source="openstreetmap",
        source_url=c.source_url,
        fetched_at=now_iso(),
        match_name=c.name,
        match_score=f"{m.score:.3f}",
        osm_ref=c.ref,
        site_geojson=json.dumps({"type": "Polygon", "coordinates": [[list(p) for p in c.site]]})
        if c.site
        else "",
    )


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def run(
    seed: Path,
    out: Path,
    steps: list[str],
    http: Http | None = None,
    limit: int | None = None,
    gmaps_headless: bool = False,
    osm_index=None,
) -> dict:
    rows, fields = load_seed(seed)
    fields = fields + [f for f in ADDED_FIELDS if f not in fields]
    log = GeoLog(out / "geocode_log.csv")
    http = http or Http(out / "cache" / "http.jsonl", user_agent(), min_interval=1.0)

    targets = [r for r in rows if is_target(r)][:limit]
    pending = {r["reg_number"]: r for r in targets}
    # Too generic for an OSM name match; still searched on Google Maps, where the query adds
    # promoter and locality and an operator reviews the result.
    generic = set()
    for r in targets:
        if not to_project(r).name_ok:
            log.write(
                "filter",
                to_project(r),
                r["project"],
                "skipped",
                note="name too generic or same as its locality: no OSM name match",
            )
            generic.add(r["reg_number"])
    skipped = len(generic)
    by_step: Counter = Counter()

    def step(name: str, fn) -> None:
        for reg, r in list(pending.items()):
            if reg in generic:
                continue
            m = fn(to_project(r))
            if m:
                apply(r, m)
                by_step[name] += 1
                pending.pop(reg)

    if "osm" in steps:
        idx = osm_index or osm.load_index(http, log)
        step("osm_name", lambda p: osm.match(p, idx, log))
    if "nominatim" in steps:
        step("nominatim", lambda p: geocoders.nominatim(p, http, log))
    if "photon" in steps:
        step("photon", lambda p: geocoders.photon(p, http, log))

    write_csv(out / "blr_rera_projects_located.csv", rows, fields)

    gm = None
    if "gmaps" in steps:
        left = [to_project(r) for r in targets if r["reg_number"] in pending]
        gm = gmaps.run(left, out, log, headless=gmaps_headless)
    log.close()

    final = Counter(r["location_method"] or "unplaced" for r in rows)
    summary = {
        "at": now_iso(),
        "targets": len(targets),
        "skipped_generic_name": skipped,
        "matched_this_run": dict(by_step),
        "still_approximate": sum(1 for r in targets if r["reg_number"] in pending and r.get("lat")),
        "still_unplaced": sum(
            1 for r in targets if r["reg_number"] in pending and not r.get("lat")
        ),
        "final_methods": dict(final.most_common()),
        "gmaps": gm,
    }
    (out / "locate_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--seed", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--steps", default="osm,nominatim,photon")
    ap.add_argument("--gmaps", action="store_true", help="also run the Google Maps finder")
    ap.add_argument("--gmaps-headless", action="store_true")
    ap.add_argument("--limit", type=int, help="first N targets only (trial runs)")
    ap.add_argument(
        "--map-template",
        type=Path,
        help="reference map HTML to refresh into <out>/bengaluru-rera-map.html",
    )
    a = ap.parse_args()
    steps = a.steps.split(",") + (["gmaps"] if a.gmaps else [])
    s = run(a.seed, a.out, steps, limit=a.limit, gmaps_headless=a.gmaps_headless)
    if a.map_template:
        from .mapbuild import build

        build(
            a.map_template,
            a.out / "blr_rera_projects_located.csv",
            a.out / "gmaps_candidates.csv",
            a.out / "bengaluru-rera-map.html",
        )
    print(json.dumps(s, indent=2))


if __name__ == "__main__":
    main()
