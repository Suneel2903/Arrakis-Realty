"""Shared types, polite HTTP with caching, and the geocode log."""

import csv
import hashlib
import json
import os
import time
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from .geo import Ring, haversine_km
from .names import is_distinctive, key, tokens

EXACT_METHODS = {"portal_latlng", "portal_boundary"}
MAX_KM = 5.0
# Two accepted candidates further apart than this are different places, so the match is
# ambiguous. Closer ones are usually the same complex mapped twice (landuse + building).
SAME_PLACE_KM = 0.3


def now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class Project:
    reg: str
    name: str
    promoter: str
    area: str
    address: str
    lat: float | None
    lng: float | None
    method: str

    @property
    def placed(self) -> bool:
        return self.lat is not None and self.lng is not None

    @property
    def name_ok(self) -> bool:
        """Name is specific enough to search for and is not just its locality's name."""
        t = tokens(self.name)
        if not is_distinctive(t, set(tokens(self.promoter))):
            return False
        return not (self.area and key(self.area) == " ".join(t))

    def dist_km(self, lat: float, lng: float) -> float | None:
        return haversine_km(self.lat, self.lng, lat, lng) if self.placed else None


@dataclass
class Candidate:
    name: str
    lat: float
    lng: float
    ref: str  # "osm way/123"
    source_url: str
    tags_text: str = ""  # operator/brand/etc. for promoter tie-break
    site: Ring | None = None
    kind: str = ""  # landuse=residential, building=apartments, ...


@dataclass
class Match:
    method: str
    cand: Candidate
    score: float
    dist_km: float | None
    confidence: str
    note: str = ""
    extra: dict = field(default_factory=dict)


def choose(
    p: Project, scored: list[tuple[Candidate, float, bool]], max_km: float = MAX_KM
) -> tuple[Candidate | None, float, float | None, str]:
    """Pick one candidate from (cand, score, promoter_hit) already above threshold.

    Returns (cand, score, dist_km, reason). cand is None when nothing is acceptable;
    reason then says why (too_far, ambiguous).
    """
    ok = []
    for c, s, hit in scored:
        d = p.dist_km(c.lat, c.lng)
        if d is not None and d > max_km:
            continue
        ok.append((c, s, hit, d))
    if not ok:
        return None, 0.0, None, "too_far" if scored else "no_match"
    ok.sort(key=lambda x: (not x[2], -x[1], x[3] if x[3] is not None else 0.0))
    best = ok[0]
    rivals = [
        o
        for o in ok[1:]
        if o[2] == best[2]
        and o[1] == best[1]
        and haversine_km(o[0].lat, o[0].lng, best[0].lat, best[0].lng) > SAME_PLACE_KM
    ]
    if rivals:
        return None, best[1], best[3], f"ambiguous ({len(rivals) + 1} places)"
    # Same complex mapped as both a landuse area and a building: keep the outline.
    if best[0].site is None:
        for o in ok[1:]:
            near = haversine_km(o[0].lat, o[0].lng, best[0].lat, best[0].lng) <= SAME_PLACE_KM
            if o[0].site and near:
                best[0].site = o[0].site
                break
    return best[0], best[1], best[3], ""


def confidence(p: Project, s: float) -> str:
    return "high" if p.placed and s >= 0.999 else "medium"


class Http:
    """GET with a contact User-Agent, a minimum interval between requests, and a disk cache.

    The cache means a rerun never repeats a query (Nominatim's usage policy asks for this)
    and an interrupted run resumes where it stopped.
    """

    def __init__(
        self,
        cache_path: Path,
        user_agent: str,
        min_interval: float = 1.0,
        opener: Callable[[urllib.request.Request, float], bytes] | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.cache_path = cache_path
        self.user_agent = user_agent
        self.min_interval = min_interval
        self._opener = opener or (lambda req, t: urllib.request.urlopen(req, timeout=t).read())
        self._sleep, self._clock = sleep, clock
        self._last: dict[str, float] = {}
        self._cache: dict[str, str] = {}
        if cache_path.exists():
            for line in cache_path.read_text().splitlines():
                if line.strip():
                    rec = json.loads(line)
                    self._cache[rec["k"]] = rec["body"]
        cache_path.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def cache_key(url: str, data: str | None) -> str:
        return hashlib.sha256(f"{url}\n{data or ''}".encode()).hexdigest()

    def get(
        self, url: str, params: dict | None = None, data: str | None = None, timeout: float = 60
    ) -> tuple[str, bool]:
        """Returns (body, from_cache)."""
        if params:
            url = f"{url}?{urllib.parse.urlencode(params)}"
        k = self.cache_key(url, data)
        if k in self._cache:
            return self._cache[k], True
        host = urllib.parse.urlsplit(url).netloc
        wait = self._last.get(host, -1e9) + self.min_interval - self._clock()
        if wait > 0:
            self._sleep(wait)
        body = None
        req = urllib.request.Request(
            url,
            data=data.encode() if data is not None else None,
            headers={"User-Agent": self.user_agent, "Accept": "application/json"},
        )
        for attempt in range(4):
            try:
                body = self._opener(req, timeout).decode("utf-8")
                break
            except Exception:
                if attempt == 3:
                    raise
                self._sleep(2 ** (attempt + 1))
            finally:
                self._last[host] = self._clock()
        self._cache[k] = body
        with self.cache_path.open("a") as f:
            f.write(json.dumps({"k": k, "url": url, "at": now_iso(), "body": body}) + "\n")
        return body, False


def user_agent() -> str:
    email = os.environ.get("GEOCODE_CONTACT_EMAIL") or os.environ.get("RERA_CONTACT_EMAIL")
    if not email:
        raise SystemExit(
            "Set GEOCODE_CONTACT_EMAIL (or RERA_CONTACT_EMAIL): OSM services require a "
            "User-Agent that identifies a contact."
        )
    return f"ArrakisRealty-locate/0.1 (+{email})"


LOG_FIELDS = [
    "at",
    "step",
    "reg_number",
    "project",
    "query",
    "cached",
    "status",
    "result_name",
    "result_ref",
    "lat",
    "lng",
    "dist_km",
    "score",
    "note",
]


class GeoLog:
    """Append-only CSV of every query and decision (exports/geocode_log.csv)."""

    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        new = not path.exists()
        self._f = path.open("a", newline="")
        self._w = csv.DictWriter(self._f, fieldnames=LOG_FIELDS)
        if new:
            self._w.writeheader()

    def write(self, step: str, p: Project | None, query: str, status: str, **kw) -> None:
        row = {
            "at": now_iso(),
            "step": step,
            "reg_number": p.reg if p else "",
            "project": p.name if p else "",
            "query": query,
            "status": status,
        }
        for k, v in kw.items():
            if isinstance(v, float):
                v = round(v, 6 if k in ("lat", "lng") else 3)
            row[k] = "" if v is None else v
        self._w.writerow(row)
        self._f.flush()

    def close(self) -> None:
        self._f.close()
