"""Step 2: Nominatim, then Photon, search by name. Both are OpenStreetMap-based."""

import json

from .common import Candidate, Http, Match, Project, choose, confidence
from .geo import BLR_BBOX, in_bbox
from .names import MATCH_THRESHOLD, promoter_overlap, query_name, score

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
PHOTON_URL = "https://photon.komoot.io/api/"
OSM_TYPES = {"N": "node", "W": "way", "R": "relation"}


def queries(p: Project) -> list[str]:
    """'<name>, <locality>, Bengaluru', falling back to '<name>, Bengaluru'."""
    n = query_name(p.name)
    qs = [f"{n}, {p.area}, Bengaluru"] if p.area else []
    qs.append(f"{n}, Bengaluru")
    return qs


def _osm_ref(osm_type: str, osm_id) -> tuple[str, str]:
    t = OSM_TYPES.get(str(osm_type)[:1].upper(), str(osm_type))
    return f"osm {t}/{osm_id}", f"https://www.openstreetmap.org/{t}/{osm_id}"


def nominatim_candidates(body: str) -> list[Candidate]:
    out = []
    for r in json.loads(body):
        name = r.get("name") or (r.get("display_name") or "").split(",")[0]
        ref, url = _osm_ref(r.get("osm_type", ""), r.get("osm_id", ""))
        site = None
        gj = r.get("geojson") or {}
        if gj.get("type") == "Polygon" and gj.get("coordinates"):
            site = [tuple(pt) for pt in gj["coordinates"][0]]
        nd = r.get("namedetails") or {}
        out.append(
            Candidate(
                name=name,
                lat=float(r["lat"]),
                lng=float(r["lon"]),
                ref=ref,
                source_url=url,
                tags_text=" ".join([name, *nd.values()]),
                site=site,
                kind=f"{r.get('category', r.get('class', ''))}={r.get('type', '')}",
            )
        )
    return out


def photon_candidates(body: str) -> list[Candidate]:
    out = []
    for f in json.loads(body).get("features", []):
        pr = f.get("properties") or {}
        if not pr.get("name"):
            continue
        lng, lat = f["geometry"]["coordinates"][:2]
        ref, url = _osm_ref(pr.get("osm_type", ""), pr.get("osm_id", ""))
        out.append(
            Candidate(
                name=pr["name"],
                lat=float(lat),
                lng=float(lng),
                ref=ref,
                source_url=url,
                tags_text=pr["name"],
                kind=f"{pr.get('osm_key', '')}={pr.get('osm_value', '')}",
            )
        )
    return out


def _search(step: str, p: Project, log, fetch) -> Match | None:
    for q in queries(p):
        body, cached = fetch(q)
        cands = [c for c in fetch.parse(body) if in_bbox(c.lat, c.lng)]
        scored = []
        for c in cands:
            s = score(p.name, c.name, p.promoter)
            if s >= MATCH_THRESHOLD:
                scored.append((c, s, promoter_overlap(p.promoter, c.tags_text)))
        c, s, d, reason = choose(p, scored)
        if c is not None:
            log.write(
                step,
                p,
                q,
                "accepted",
                cached=int(cached),
                result_name=c.name,
                result_ref=c.ref,
                lat=c.lat,
                lng=c.lng,
                dist_km=d,
                score=s,
            )
            return Match(step, c, s, d, confidence(p, s), f"{step} '{c.name}'", extra={"query": q})
        best = max((score(p.name, c.name, p.promoter) for c in cands), default=None)
        status = reason if scored else ("name_mismatch" if cands else "no_result")
        top = cands[0] if cands else None
        log.write(
            step,
            p,
            q,
            status,
            cached=int(cached),
            result_name=top.name if top else "",
            result_ref=top.ref if top else "",
            lat=top.lat if top else None,
            lng=top.lng if top else None,
            dist_km=p.dist_km(top.lat, top.lng) if top else None,
            score=best,
        )
        if cands:  # results came back but none fit: a shorter query will not do better
            break
    return None


class _Fetch:
    def __init__(self, http: Http, url: str, params, parse):
        self.http, self.url, self.params, self.parse = http, url, params, parse

    def __call__(self, q: str):
        return self.http.get(self.url, self.params(q))


def nominatim(p: Project, http: Http, log) -> Match | None:
    s, w, n, e = BLR_BBOX
    params = lambda q: {  # noqa: E731
        "q": q,
        "format": "jsonv2",
        "limit": 5,
        "countrycodes": "in",
        "viewbox": f"{w},{n},{e},{s}",
        "bounded": 1,
        "namedetails": 1,
        "polygon_geojson": 1,
    }
    return _search("nominatim", p, log, _Fetch(http, NOMINATIM_URL, params, nominatim_candidates))


def photon(p: Project, http: Http, log) -> Match | None:
    s, w, n, e = BLR_BBOX
    params = lambda q: {"q": q, "limit": 5, "bbox": f"{w},{s},{e},{n}"}  # noqa: E731
    return _search("photon", p, log, _Fetch(http, PHOTON_URL, params, photon_candidates))
