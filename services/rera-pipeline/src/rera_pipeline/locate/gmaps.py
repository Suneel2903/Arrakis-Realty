"""Step 3: Google Maps candidate finder for operator review.

Policy (CLAUDE.md rule 5, docs/MAP-02): one search at a time, 10-20 s apart, logged.
Results go only to exports/gmaps_candidates.csv as suggestions for a data operator.
They are never written as project coordinates. On a captcha or "unusual traffic" page
the run stops and saves progress; there is no captcha solving or proxy rotation.
"""

import csv
import random
import re
import time
import urllib.parse
from pathlib import Path

from .common import Project, now_iso
from .names import query_name, score

CAND_FIELDS = [
    "searched_at",
    "reg_number",
    "project",
    "query",
    "status",
    "google_name",
    "lat",
    "lng",
    "dist_km_from_current",
    "name_score",
    "maps_url",
]
_PLACE_DATA = re.compile(r"!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)")
_AT = re.compile(r"/@(-?\d+\.\d+),(-?\d+\.\d+)")
BLOCK_MARKERS = ("unusual traffic", "not a robot", "recaptcha", "/sorry/")


class Blocked(Exception):
    pass


def query(p: Project) -> str:
    parts = [query_name(p.name), p.promoter, p.area or _address_tail(p.address), "Bengaluru"]
    return " ".join(x for x in parts if x)


def _address_tail(addr: str) -> str:
    """Last two comma parts of a RERA address, which usually name the locality."""
    parts = [x.strip() for x in (addr or "").split(",") if x.strip()]
    return " ".join(parts[-2:])


def coords_from_url(url: str) -> tuple[float, float, bool] | None:
    """(lat, lng, is_place). Place pages carry the pin in `!3d..!4d..`; `@lat,lng` is the
    viewport centre, used only when the pin is absent."""
    u = urllib.parse.unquote(url or "")
    m = _PLACE_DATA.search(u)
    if m:
        return float(m.group(1)), float(m.group(2)), "/maps/place/" in u
    m = _AT.search(u)
    if m:
        return float(m.group(1)), float(m.group(2)), "/maps/place/" in u
    return None


def is_blocked(url: str, text: str) -> bool:
    hay = f"{url}\n{text[:20000]}".lower()
    return any(m in hay for m in BLOCK_MARKERS)


def done_regs(path: Path) -> set[str]:
    if not path.exists():
        return set()
    with path.open(newline="") as f:
        return {r["reg_number"] for r in csv.DictReader(f) if r["status"] != "blocked"}


def _writer(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists()
    f = path.open("a", newline="")
    w = csv.DictWriter(f, fieldnames=CAND_FIELDS)
    if new:
        w.writeheader()
    return f, w


def read_result(page, p: Project) -> dict:
    """Read the place (or the best of the result list) from the current Maps page."""
    url = page.url
    if "/maps/place/" in url:
        name = ""
        h1 = page.locator("h1").first
        if h1.count():
            name = h1.inner_text(timeout=3000).strip()
        c = coords_from_url(url)
        if c:
            return {
                "status": "place",
                "google_name": name,
                "lat": c[0],
                "lng": c[1],
                "maps_url": url,
            }
    # Result list: read names and pins from the result links, without clicking.
    best = None
    for a in page.locator('a[href*="/maps/place/"]').all()[:5]:
        href = a.get_attribute("href") or ""
        label = a.get_attribute("aria-label") or ""
        c = coords_from_url(href)
        if not c or not label:
            continue
        s = score(p.name, label, p.promoter)
        if best is None or s > best["s"]:
            best = {
                "s": s,
                "status": "list_best",
                "google_name": label,
                "lat": c[0],
                "lng": c[1],
                "maps_url": href,
            }
    if best:
        best.pop("s")
        return best
    return {"status": "no_result"}


def run(
    projects: list[Project],
    out: Path,
    log,
    headless: bool = False,
    profile: Path | None = None,
    delay=(10.0, 20.0),
    limit: int | None = None,
    sleep=time.sleep,
) -> dict:
    from playwright.sync_api import sync_playwright  # optional dependency

    path = out / "gmaps_candidates.csv"
    skip = done_regs(path)
    todo = [p for p in projects if p.reg not in skip][:limit]
    counts = {"searched": 0, "found": 0, "skipped_done": len(skip), "blocked": False}
    if not todo:
        return counts
    f, w = _writer(path)
    profile = profile or out / ".gmaps-profile"
    try:
        with sync_playwright() as pw:
            ctx = pw.chromium.launch_persistent_context(
                str(profile),
                headless=headless,
                locale="en-IN",
                viewport={"width": 1280, "height": 900},
            )
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            for i, p in enumerate(todo):
                if i:
                    sleep(random.uniform(*delay))
                q = query(p)
                url = "https://www.google.com/maps/search/" + urllib.parse.quote(q) + "?hl=en"
                page.goto(url, wait_until="domcontentloaded", timeout=45000)
                if "consent.google." in page.url:
                    raise Blocked(
                        "Google consent page: accept it once in the visible browser "
                        "profile, then rerun"
                    )
                try:
                    page.wait_for_url(re.compile(r"/maps/place/|/maps/search/.*@"), timeout=15000)
                    page.wait_for_timeout(2500)
                except Exception:
                    pass
                if is_blocked(page.url, page.content()):
                    log.write("gmaps", p, q, "blocked", note=page.url[:200])
                    w.writerow(
                        {
                            "searched_at": now_iso(),
                            "reg_number": p.reg,
                            "project": p.name,
                            "query": q,
                            "status": "blocked",
                        }
                    )
                    raise Blocked(f"Captcha / unusual-traffic page after {i} searches")
                r = read_result(page, p)
                counts["searched"] += 1
                row = {
                    "searched_at": now_iso(),
                    "reg_number": p.reg,
                    "project": p.name,
                    "query": q,
                    "status": r["status"],
                    "google_name": r.get("google_name", ""),
                }
                if "lat" in r:
                    counts["found"] += 1
                    d = p.dist_km(r["lat"], r["lng"])
                    s = score(p.name, r["google_name"], p.promoter)
                    row.update(
                        lat=round(r["lat"], 6),
                        lng=round(r["lng"], 6),
                        dist_km_from_current="" if d is None else round(d, 3),
                        name_score=round(s, 3),
                        maps_url=r["maps_url"],
                    )
                    log.write(
                        "gmaps",
                        p,
                        q,
                        r["status"],
                        result_name=r["google_name"],
                        lat=r["lat"],
                        lng=r["lng"],
                        dist_km=d,
                        score=s,
                        note="candidate only, not stored as a location",
                    )
                else:
                    log.write("gmaps", p, q, r["status"])
                w.writerow(row)
                f.flush()
            ctx.close()
    except Blocked as e:
        counts["blocked"] = str(e)
    finally:
        f.close()
    return counts
