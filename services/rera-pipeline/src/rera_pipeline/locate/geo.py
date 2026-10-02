"""Small geometry helpers. Planar maths is fine at city scale."""

import math

# south, west, north, east. Bengaluru metro and fringe (Hoskote, Anekal, Nelamangala,
# Bidadi), wide enough for every placed seed project bar a handful of outliers.
BLR_BBOX = (12.55, 77.15, 13.45, 77.95)

Ring = list[tuple[float, float]]  # [(lng, lat), ...] closed


def in_bbox(lat: float, lng: float, bbox: tuple[float, float, float, float] = BLR_BBOX) -> bool:
    s, w, n, e = bbox
    return s <= lat <= n and w <= lng <= e


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lng2 - lng1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def ring_area_sqm(ring: Ring) -> float:
    if len(ring) < 4:
        return 0.0
    lat0 = sum(p[1] for p in ring) / len(ring)
    kx, ky = 111320 * math.cos(math.radians(lat0)), 110540
    a = 0.0
    for (x1, y1), (x2, y2) in zip(ring, ring[1:], strict=False):
        a += (x1 * kx) * (y2 * ky) - (x2 * kx) * (y1 * ky)
    return abs(a) / 2


def ring_centroid(ring: Ring) -> tuple[float, float]:
    """(lat, lng) area centroid of a closed ring; vertex mean if degenerate."""
    a = cx = cy = 0.0
    for (x1, y1), (x2, y2) in zip(ring, ring[1:], strict=False):
        c = x1 * y2 - x2 * y1
        a += c
        cx += (x1 + x2) * c
        cy += (y1 + y2) * c
    if abs(a) < 1e-14:
        pts = ring[:-1] or ring
        return sum(p[1] for p in pts) / len(pts), sum(p[0] for p in pts) / len(pts)
    a *= 0.5
    return cy / (6 * a), cx / (6 * a)


def stitch(ways: list[Ring]) -> list[Ring]:
    """Join open way segments end to end into closed rings (multipolygon outers)."""
    segs = [list(w) for w in ways if len(w) >= 2]
    rings: list[Ring] = []
    while segs:
        cur = segs.pop(0)
        changed = True
        while cur[0] != cur[-1] and changed:
            changed = False
            for i, s in enumerate(segs):
                if s[0] == cur[-1]:
                    cur += s[1:]
                elif s[-1] == cur[-1]:
                    cur += s[-2::-1]
                elif s[-1] == cur[0]:
                    cur = s[:-1] + cur
                elif s[0] == cur[0]:
                    cur = s[:0:-1] + cur
                else:
                    continue
                segs.pop(i)
                changed = True
                break
        if cur[0] == cur[-1] and len(cur) >= 4:
            rings.append(cur)
    return rings
