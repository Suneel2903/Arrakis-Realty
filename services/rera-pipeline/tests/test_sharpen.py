"""End-to-end run against fake Overpass / Nominatim / Photon responses."""

import csv
import json
import urllib.parse
from pathlib import Path

from rera_pipeline.locate.common import GeoLog, Http
from rera_pipeline.locate.gmaps import coords_from_url, done_regs, is_blocked
from rera_pipeline.locate.gmaps import query as gquery
from rera_pipeline.locate.mapbuild import build
from rera_pipeline.locate.osm import parse
from rera_pipeline.locate.sharpen import run, to_project

REPO = Path(__file__).resolve().parents[3]
TEMPLATE = REPO / "reference" / "bengaluru-rera-map.html"

SEED_FIELDS = (
    "reg_number,project,promoter,status,lat,lng,location_method,confidence,location_note,"
    "area,pin,towers,homes,land_sqm,far,est_floors,completion,registered_year"
).split(",")

# Real reg numbers from the seed so the map builder finds them in the template.
SEED = [
    # exact from RERA: never touched
    [
        "PRM/KA/RERA/1251/308/PR/040926/008911",
        "Signature Regal",
        "Signature Dwellings",
        "new",
        "12.766577",
        "77.735305",
        "portal_latlng",
        "high",
        "",
        "Madivala",
        "562106",
    ],
    # approximate; OSM has it 1.2 km away with an outline
    [
        "PRM/KA/RERA/1251/446/PR/171123/000625",
        "Sbr Horizon",
        "Sbr Group",
        "ongoing",
        "13.038376",
        "77.77353",
        "village_centroid",
        "medium",
        "Village Seegehalli",
        "Seegehalli",
        "nan",
    ],
    # approximate; OSM namesake is 20 km away -> rejected; Nominatim finds it nearby
    [
        "PRM/KA/RERA/1251/446/PR/211005/004337",
        "Sterling Villa Grande Phase Ii",
        "Sterling Urban Developments",
        "ongoing",
        "13.038376",
        "77.77353",
        "village_centroid",
        "medium",
        "",
        "Seegehalli",
        "",
    ],
    # unplaced; only Photon knows it
    [
        "PRM/KA/RERA/1251/308/PR/220218/004714",
        "S R Suvarana Residency",
        "",
        "",
        "",
        "",
        "unplaced",
        "",
        "needs web lookup or manual pin: SURVERY NO 9/1, RAYANSANDRA ANEKAL",
        "",
        "",
    ],
    # generic name: skipped, never queried
    [
        "PRM/KA/RERA/1251/309/PR/210813/000001",
        "Sai Residency",
        "Sai Builders",
        "new",
        "12.9",
        "77.6",
        "locality_name",
        "low",
        "",
        "Hebbal",
        "",
    ],
]

RING = [
    [77.7810, 13.0300],
    [77.7830, 13.0300],
    [77.7830, 13.0315],
    [77.7810, 13.0315],
    [77.7810, 13.0300],
]
OVERPASS = {
    "elements": [
        {
            "type": "way",
            "id": 101,
            "tags": {"landuse": "residential", "name": "SBR Horizon"},
            "geometry": [{"lat": y, "lon": x} for x, y in RING],
        },
        {
            "type": "node",
            "id": 202,
            "lat": 12.85,
            "lon": 77.60,
            "tags": {"place": "neighbourhood", "name": "Sterling Villa Grande"},
        },
        {
            "type": "relation",
            "id": 303,
            "tags": {"landuse": "residential", "name": "Far Away"},
            "members": [
                {
                    "type": "way",
                    "role": "outer",
                    "geometry": [{"lat": y, "lon": x} for x, y in RING],
                }
            ],
        },
    ]
}
NOMINATIM = {
    "Sterling Villa Grande, Seegehalli, Bengaluru": [
        {
            "lat": "13.0410",
            "lon": "77.7690",
            "name": "Sterling Villa Grande",
            "osm_type": "way",
            "osm_id": 555,
            "category": "landuse",
            "type": "residential",
        }
    ],
}
PHOTON = {
    "S R Suvarana Residency, Bengaluru": {
        "features": [
            {
                "geometry": {"coordinates": [77.70, 12.80]},
                "properties": {
                    "name": "SR Suvarana Residency",
                    "osm_type": "W",
                    "osm_id": 777,
                    "osm_key": "building",
                    "osm_value": "apartments",
                },
            }
        ]
    },
}


class FakeNet:
    def __init__(self):
        self.calls: list[str] = []

    def __call__(self, req, timeout):
        u = urllib.parse.urlsplit(req.full_url)
        self.calls.append(u.netloc)
        q = urllib.parse.parse_qs(u.query).get("q", [""])[0]
        if "overpass" in u.netloc:
            return json.dumps(OVERPASS).encode()
        if "nominatim" in u.netloc:
            return json.dumps(NOMINATIM.get(q, [])).encode()
        if "photon" in u.netloc:
            return json.dumps(PHOTON.get(q, {"features": []})).encode()
        raise AssertionError(u.netloc)


def write_seed(path: Path) -> None:
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(SEED_FIELDS)
        for r in SEED:
            w.writerow(r + [""] * (len(SEED_FIELDS) - len(r)))


def make_http(tmp: Path, net: FakeNet, sleeps: list) -> Http:
    t = [0.0]
    return Http(
        tmp / "cache" / "http.jsonl",
        "test (+ops@example.com)",
        opener=net,
        sleep=lambda s: (sleeps.append(s), t.__setitem__(0, t[0] + s)),
        clock=lambda: t[0],
    )


def test_end_to_end(tmp_path):
    seed, out = tmp_path / "seed.csv", tmp_path / "exports"
    write_seed(seed)
    net, sleeps = FakeNet(), []
    s = run(seed, out, ["osm", "nominatim", "photon"], http=make_http(tmp_path, net, sleeps))

    assert s["targets"] == 4 and s["skipped_generic_name"] == 1
    assert s["matched_this_run"] == {"osm_name": 1, "nominatim": 1, "photon": 1}
    assert s["still_unplaced"] == 0

    rows = {r["reg_number"]: r for r in csv.DictReader(open(out / "blr_rera_projects_located.csv"))}
    sbr = rows["PRM/KA/RERA/1251/446/PR/171123/000625"]
    assert sbr["location_method"] == "osm_name" and sbr["confidence"] == "high"
    assert sbr["source_url"] == "https://www.openstreetmap.org/way/101"
    assert sbr["prev_method"] == "village_centroid" and json.loads(sbr["site_geojson"])
    sterling = rows["PRM/KA/RERA/1251/446/PR/211005/004337"]
    assert sterling["location_method"] == "nominatim"
    sr = rows["PRM/KA/RERA/1251/308/PR/220218/004714"]
    assert sr["location_method"] == "photon" and sr["confidence"] == "medium"
    assert rows["PRM/KA/RERA/1251/308/PR/040926/008911"]["location_method"] == "portal_latlng"
    assert rows["PRM/KA/RERA/1251/309/PR/210813/000001"]["location_method"] == "locality_name"

    log = list(csv.DictReader(open(out / "geocode_log.csv")))
    steps = {(r["step"], r["status"]) for r in log}
    assert ("osm", "too_far") in steps and ("filter", "skipped") in steps
    assert ("nominatim", "accepted") in steps and ("photon", "accepted") in steps
    # requests to one host are at least 1 s apart
    assert all(x <= 1.0 for x in sleeps)

    # rerun is served from cache: no new network calls
    before = len(net.calls)
    run(seed, out, ["osm", "nominatim", "photon"], http=make_http(tmp_path, net, []))
    assert len(net.calls) == before


def test_map_build_marks_osm_exact_and_adds_suggestions(tmp_path):
    seed, out = tmp_path / "seed.csv", tmp_path / "exports"
    write_seed(seed)
    run(seed, out, ["osm", "nominatim", "photon"], http=make_http(tmp_path, FakeNet(), []))
    gm = out / "gmaps_candidates.csv"
    gm.write_text(
        "searched_at,reg_number,project,query,status,google_name,lat,lng,"
        "dist_km_from_current,name_score,maps_url\n"
        "x,PRM/KA/RERA/1251/309/PR/210813/000001,Sai Residency,q,place,Sai Residency,"
        "12.91,77.61,1.5,1.0,u\n"
        # already placed via OSM: dropped from the suggestion layer
        "x,PRM/KA/RERA/1251/446/PR/171123/000625,Sbr Horizon,q,place,SBR,13.0,77.7,1,1,u\n"
    )
    html_out = out / "map.html"
    s = build(TEMPLATE, out / "blr_rera_projects_located.csv", gm, html_out)
    assert s == {
        "sharpened": 2,
        "newly_placed": 1,
        "unplaced": 188,
        "suggestions": 1,
        "outlines": 1,
    }
    html = html_out.read_text()
    assert "NaN" not in html.split("<script>")[0]  # data blocks are strict JSON
    assert "'osm_name','nominatim','photon'" in html and 'id="tsg"' in html


def test_osm_parse_handles_nodes_ways_relations():
    cands = parse(OVERPASS["elements"] + [{"type": "way", "id": 9, "tags": {}, "geometry": []}])
    assert [c.ref for c in cands] == ["osm way/101", "osm node/202", "osm relation/303"]
    assert cands[0].site and cands[2].site and cands[1].site is None


def test_gmaps_helpers(tmp_path):
    u = (
        "https://www.google.com/maps/place/SBR+Horizon/@13.03,77.77,17z/data=!3m1!4b1"
        "!4m6!3m5!1s0x0:0x0!8m2!3d13.0312!4d77.7821"
    )
    assert coords_from_url(u) == (13.0312, 77.7821, True)
    assert coords_from_url("https://www.google.com/maps/search/x/@13.1,77.6,14z") == (
        13.1,
        77.6,
        False,
    )
    assert coords_from_url("https://www.google.com/maps") is None
    assert is_blocked("https://www.google.com/sorry/index?continue=x", "")
    assert is_blocked("https://www.google.com/maps", "Our systems have detected unusual traffic")
    assert not is_blocked("https://www.google.com/maps/place/x", "<h1>SBR Horizon</h1>")

    p = to_project(
        {
            "reg_number": "R",
            "project": "Sbr Horizon Phase 2",
            "promoter": "Sbr Group",
            "area": "Seegehalli",
            "lat": "",
            "lng": "",
            "location_method": "unplaced",
            "location_note": "",
        }
    )
    assert gquery(p) == "Sbr Horizon Sbr Group Seegehalli Bengaluru"

    f = tmp_path / "g.csv"
    f.write_text("searched_at,reg_number,project,query,status\nx,A,a,q,place\nx,B,b,q,blocked\n")
    assert done_regs(f) == {"A"}  # a blocked search is retried on resume


def test_log_rounds_numbers(tmp_path):
    log = GeoLog(tmp_path / "l.csv")
    log.write("osm", None, "q", "ok", lat=12.123456789, dist_km=1.23456)
    log.close()
    r = next(csv.DictReader(open(tmp_path / "l.csv")))
    assert r["lat"] == "12.123457" and r["dist_km"] == "1.235"
