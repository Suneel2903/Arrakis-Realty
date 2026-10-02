from rera_pipeline.locate.common import Candidate, Project, choose
from rera_pipeline.locate.geo import haversine_km, ring_area_sqm, ring_centroid, stitch
from rera_pipeline.locate.names import is_distinctive, key, query_name, score, tokens


def proj(name="Sai Lakeview", promoter="Sai Builders", area="Varthur", lat=12.94, lng=77.75):
    return Project("REG1", name, promoter, area, "", lat, lng, "village_centroid")


def cand(name, lat=12.94, lng=77.75, ref="osm way/1", site=None):
    return Candidate(name, lat, lng, ref, "https://www.openstreetmap.org/way/1", name, site)


def test_tokens_drop_generic_words_and_numbering():
    assert key("Prestige Lakeside Habitat Phase II") == "prestige lakeside habitat"
    assert key("Sai Residency Apartments - Tower 3") == "sai"
    assert key("S R Suvarana Residency") == "sr suvarana"
    assert key("T.S.R'S Sai Arcade") == "tsr sai arcade"


def test_query_name_keeps_words_osm_uses():
    assert query_name("Prestige Lakeside Habitat Phase II") == "Prestige Lakeside Habitat"
    assert query_name("Sobha Dream Acres - Wing 12") == "Sobha Dream Acres"
    assert query_name("Sai Residency") == "Sai Residency"


def test_score_exact_brandless_and_different():
    assert score("Prestige Lakeside Habitat Phase 2", "Prestige Lakeside Habitat") == 1.0
    assert score("Prestige Lakeside Habitat", "Lakeside Habitat", "Prestige Estates") == 0.95
    assert score("Brigade Cornerstone Utopia", "Brigade Utopia") < 0.92
    assert score("Green Park", "Green Meadows") < 0.92


def test_generic_names_are_not_searched():
    assert not is_distinctive(tokens("Prestige Apartments"), {"prestige", "estates"})
    assert not is_distinctive(tokens("Green"), set())
    assert is_distinctive(tokens("Lakeside Habitat"), set())
    assert not proj(name="Varthur Residency", area="Varthur").name_ok
    assert proj(name="Sai Lakeview").name_ok


def test_choose_rejects_far_and_ambiguous_and_merges_outline():
    p = proj()
    far = cand("Sai Lakeview", lat=13.10)  # ~18 km north
    c, _, _, why = choose(p, [(far, 1.0, False)])
    assert c is None and why == "too_far"

    a, b = cand("Sai Lakeview", lng=77.74), cand("Sai Lakeview", lng=77.77, ref="osm way/2")
    c, _, _, why = choose(p, [(a, 1.0, False), (b, 1.0, False)])
    assert c is None and why.startswith("ambiguous")

    # promoter hit breaks the tie
    c, *_ = choose(p, [(a, 1.0, False), (b, 1.0, True)])
    assert c is b

    ring = [(77.75, 12.94), (77.751, 12.94), (77.751, 12.941), (77.75, 12.94)]
    node, area = cand("Sai Lakeview"), cand("Sai Lakeview", lat=12.9405, site=ring)
    c, *_ = choose(p, [(node, 1.0, False), (area, 1.0, False)])
    assert c.site == ring


def test_unplaced_project_accepts_any_distance_but_needs_unique_place():
    p = proj(lat=None, lng=None)
    c, _, d, _ = choose(p, [(cand("Sai Lakeview", lat=13.2), 1.0, False)])
    assert c is not None and d is None


def test_geo_helpers():
    assert abs(haversine_km(12.97, 77.59, 12.97, 77.6) - 1.085) < 0.01
    sq = [(0.0, 0.0), (0.001, 0.0), (0.001, 0.001), (0.0, 0.001), (0.0, 0.0)]
    lat, lng = ring_centroid(sq)
    assert abs(lat - 0.0005) < 1e-9 and abs(lng - 0.0005) < 1e-9
    assert 12000 < ring_area_sqm(sq) < 12500
    rings = stitch([[(0, 0), (1, 0), (1, 1)], [(0, 0), (0, 1), (1, 1)]])
    assert len(rings) == 1 and rings[0][0] == rings[0][-1] and len(rings[0]) == 5
