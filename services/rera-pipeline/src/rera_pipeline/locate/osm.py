"""Step 1: match project names to named OpenStreetMap residential features (Overpass)."""

import json
from collections import defaultdict

from .common import Candidate, Http, Match, Project, choose, confidence
from .geo import BLR_BBOX, ring_area_sqm, ring_centroid, stitch
from .names import MATCH_THRESHOLD, promoter_overlap, score, tokens

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
NAME_TAGS = ("name", "name:en", "alt_name", "old_name", "short_name", "official_name")
INFO_TAGS = ("operator", "brand", "developer", "builder", "owner")


def overpass_query(bbox: tuple[float, float, float, float] = BLR_BBOX) -> str:
    b = ",".join(str(x) for x in bbox)
    return f"""[out:json][timeout:600][maxsize:1073741824];
(
  nwr["landuse"="residential"]["name"]({b});
  nwr["building"~"^(apartments|residential)$"]["name"]({b});
  nwr["place"="neighbourhood"]["name"]({b});
);
out tags geom;"""


def _kind(tags: dict) -> str:
    for k in ("landuse", "building", "place"):
        if k in tags:
            return f"{k}={tags[k]}"
    return ""


def parse(elements: list[dict]) -> list[Candidate]:
    """Overpass `out tags geom` elements -> candidates with point and optional outline."""
    out = []
    for el in elements:
        tags = el.get("tags") or {}
        names = [tags[t] for t in NAME_TAGS if tags.get(t)]
        if not names:
            continue
        site = None
        if el["type"] == "node":
            lat, lng = el["lat"], el["lon"]
        elif el["type"] == "way":
            pts = [(g["lon"], g["lat"]) for g in el.get("geometry") or []]
            if not pts:
                continue
            if len(pts) >= 4 and pts[0] == pts[-1]:
                site = pts
                lat, lng = ring_centroid(pts)
            else:
                lat = sum(p[1] for p in pts) / len(pts)
                lng = sum(p[0] for p in pts) / len(pts)
        else:  # relation
            outers = [
                [(g["lon"], g["lat"]) for g in m.get("geometry") or []]
                for m in el.get("members") or []
                if m.get("type") == "way" and m.get("role") in ("outer", "")
            ]
            rings = stitch(outers)
            if rings:
                site = max(rings, key=ring_area_sqm)
                lat, lng = ring_centroid(site)
            elif el.get("bounds"):
                bd = el["bounds"]
                lat, lng = (bd["minlat"] + bd["maxlat"]) / 2, (bd["minlon"] + bd["maxlon"]) / 2
            else:
                continue
        info = " ".join(tags.get(t, "") for t in INFO_TAGS)
        ref = f"{el['type']}/{el['id']}"
        for nm in dict.fromkeys(names):
            out.append(
                Candidate(
                    name=nm,
                    lat=lat,
                    lng=lng,
                    ref=f"osm {ref}",
                    source_url=f"https://www.openstreetmap.org/{ref}",
                    tags_text=f"{nm} {info}",
                    site=site,
                    kind=_kind(tags),
                )
            )
    return out


class OsmIndex:
    def __init__(self, cands: list[Candidate]):
        self.cands = cands
        self._by_token: dict[str, list[int]] = defaultdict(list)
        for i, c in enumerate(cands):
            for t in set(tokens(c.name)):
                if len(t) >= 3:
                    self._by_token[t].append(i)

    def lookup(self, p: Project) -> list[tuple[Candidate, float, bool]]:
        seen: set[int] = set()
        for t in set(tokens(p.name)):
            seen.update(self._by_token.get(t, ()))
        out = []
        for i in seen:
            c = self.cands[i]
            s = score(p.name, c.name, p.promoter)
            if s >= MATCH_THRESHOLD:
                out.append((c, s, promoter_overlap(p.promoter, c.tags_text)))
        return out


def load_index(http: Http, log, bbox=BLR_BBOX) -> OsmIndex:
    q = overpass_query(bbox)
    body, cached = http.get(OVERPASS_URL, data="data=" + _urlenc(q), timeout=900)
    elements = json.loads(body).get("elements", [])
    cands = parse(elements)
    log.write(
        "overpass",
        None,
        "named residential/apartments/neighbourhood in Bengaluru bbox",
        "ok",
        cached=int(cached),
        note=f"{len(elements)} elements, {len(cands)} named entries",
    )
    return OsmIndex(cands)


def _urlenc(s: str) -> str:
    from urllib.parse import quote

    return quote(s, safe="")


def match(p: Project, idx: OsmIndex, log) -> Match | None:
    scored = idx.lookup(p)
    c, s, d, reason = choose(p, scored)
    if c is None:
        log.write(
            "osm",
            p,
            p.name,
            reason or "no_match",
            score=s or None,
            dist_km=d,
            note=f"{len(scored)} name hits",
        )
        return None
    note = f"OSM {c.kind} '{c.name}'"
    log.write(
        "osm",
        p,
        p.name,
        "accepted",
        result_name=c.name,
        result_ref=c.ref,
        lat=c.lat,
        lng=c.lng,
        dist_km=d,
        score=s,
        note=note,
    )
    return Match("osm_name", c, s, d, confidence(p, s), note)
