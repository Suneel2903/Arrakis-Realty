"""Refresh the stand-alone map (reference/bengaluru-rera-map.html) with sharpened locations.

- Projects matched on OpenStreetMap (osm_name, nominatim, photon) show as exact dots, with
  the OSM feature linked on their card and the site outline when OSM has one.
- Google Maps candidates show as a separate, toggleable "suggested" layer. They never
  move a project's pin.
- Embedded data is written as strict JSON (the template's `NaN` values broke JSON.parse).
"""

import csv
import json
import math
import re
from pathlib import Path

OSM_METHODS = ("osm_name", "nominatim", "photon")


def _blk(html: str, bid: str) -> re.Match:
    m = re.search(rf'(<script id="{bid}" type="application/json">)(.*?)(</script>)', html, re.S)
    if not m:
        raise ValueError(f"template has no <script id={bid}>")
    return m


def _strict(o):
    if isinstance(o, float) and (math.isnan(o) or math.isinf(o)):
        return None
    if isinstance(o, dict):
        return {k: _strict(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_strict(v) for v in o]
    return o


def _dump(o) -> str:
    s = json.dumps(_strict(o), ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    return s.replace("</", "<\\/")


def _num(v: str):
    try:
        return float(v) if v not in ("", None) else None
    except ValueError:
        return None


def _read_csv(path: Path) -> list[dict]:
    if not path or not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


# (anchor, replacement). Each anchor must appear exactly once in the template.
JS_PATCHES = [
    (
        "const U=JSON.parse(document.getElementById('du').textContent);",
        "const U=JSON.parse(document.getElementById('du').textContent);\n"
        "const G=JSON.parse(document.getElementById('dg').textContent);\n"
        "const SITES=JSON.parse(document.getElementById('ds').textContent);",
    ),
    (
        "done:['Completed','#6b7280']};",
        "done:['Completed','#6b7280'],unk:['Status not available','#6b7280']};\n"
        "P.forEach(p=>{if(!ST[p.s])p.s='unk';});",
    ),
    (
        "const EXACT=new Set(['portal_latlng','portal_boundary']);",
        "const EXACT=new Set(['portal_latlng','portal_boundary','osm_name','nominatim','photon']);",
    ),
    (
        "pin_centroid:'PIN code area'};",
        "pin_centroid:'PIN code area',osm_name:'OpenStreetMap name match',"
        "nominatim:'OpenStreetMap search (Nominatim)',photon:'OpenStreetMap search (Photon)'};",
    ),
    (
        "const TG=towers();",
        "const TG=towers();\n"
        "const GG={type:'FeatureCollection',features:G.map((g,i)=>({type:'Feature',"
        "properties:{i},geometry:{type:'Point',coordinates:[g.lo,g.la]}}))};\n"
        "const GBY={};G.forEach((g,i)=>{GBY[g.rg]=i;});",
    ),
    (
        "let metric='n',d3=true,exOnly=false,sel=null,area=null;",
        "let metric='n',d3=true,exOnly=false,sel=null,area=null,sugOn=true;",
    ),
    (
        "map.addSource('ex',{type:'geojson',data:EG});",
        "map.addSource('ex',{type:'geojson',data:EG});\n"
        " map.addSource('sug',{type:'geojson',data:GG});\n"
        " map.addSource('sites',{type:'geojson',data:SITES});",
    ),
    (
        " map.addLayer({id:'exist',type:'circle'",
        " map.addLayer({id:'sites',type:'line',source:'sites',minzoom:13,paint:{"
        "'line-color':'#0f766e','line-width':1.6,'line-dasharray':[2,1]}});\n"
        " map.addLayer({id:'sug',type:'circle',source:'sug',minzoom:10.3,paint:{"
        "'circle-radius':['interpolate',['linear'],['zoom'],10.3,2.5,13,5,16,8],"
        "'circle-color':'#ffffff','circle-stroke-color':'#7c3aed','circle-stroke-width':2,"
        "'circle-opacity':['interpolate',['linear'],['zoom'],10.3,0,10.8,1],"
        "'circle-stroke-opacity':['interpolate',['linear'],['zoom'],10.3,0,10.8,1]}});\n"
        " map.addLayer({id:'exist',type:'circle'",
    ),
    (
        "map.setLayoutProperty('area-3d','visibility',d3?'visible':'none');",
        "map.setLayoutProperty('area-3d','visibility',d3?'visible':'none');\n"
        " if(map.getLayer('sug'))map.setLayoutProperty('sug','visibility',sugOn?'visible':'none');",
    ),
    (
        "a.textContent=sel?sel.a:(area||'Area');",
        "a.textContent=(sel?sel.a:area)||'Area';",
    ),
    (
        "if(p.ex)h+=",
        'if(p.su)h+=`<div class="box info"><b>Located by name:</b> matched “${esc(p.mn)}” on '
        'OpenStreetMap. ${esc(p.nt||\'\')}. <a href="${esc(p.su)}" target="_blank" '
        'rel="noopener">OSM feature</a> · © OpenStreetMap contributors (ODbL)</div>`;\n'
        ' if(GBY[p.rg]!=null&&!p.ex_){const g=G[GBY[p.rg]];h+=`<div class="box info" '
        'style="background:#f5f0ff;border-color:#ddd0fb">A Google Maps suggestion '
        "(unconfirmed) is ${g.d==null?'available':g.d.toFixed(1)+' km from this pin'}: "
        '“${esc(g.gn)}”. <a href="#" id="gosug">Show it</a></div>`;}\n'
        " if(p.ex)h+=",
    ),
    (
        "openCard(h);",
        "openCard(h);{const a=document.getElementById('gosug');"
        "if(a)a.onclick=ev=>{ev.preventDefault();showSug(G[GBY[p.rg]]);};}",
    ),
    (
        "function showArea(f){",
        "function showSug(g){sel=null;const p=P.find(x=>x.rg===g.rg);\n"
        ' openCard(`<span class="tag" style="background:#f3e8ff;color:#5b21b6">Suggested, '
        'not confirmed</span><h3>${esc(g.n)}</h3><p class="by">${esc(g.rg)}</p><dl>'
        "<dt>Google Maps place</dt><dd>${esc(g.gn)}</dd><dt>Name match</dt>"
        "<dd>${g.sc==null?'—':Math.round(g.sc*100)+'%'}</dd><dt>From current pin</dt>"
        "<dd>${g.d==null?'Unplaced':g.d.toFixed(1)+' km'}</dd></dl><div class=\"box info\">"
        "Found by a Google Maps search (“${esc(g.q)}”). A data operator must confirm the site "
        "before it is used. This suggestion is not stored as the project's location.</div>"
        '${p?\'<p style="margin-top:10px"><button class="chip" id="gocur">Show current '
        "pin</button></p>':''}`);\n"
        " const b=document.getElementById('gocur');if(b)b.onclick=()=>showProject(p);\n"
        " fly({center:[g.lo,g.la],zoom:15.5,pitch:50});}\n"
        "function showArea(f){",
    ),
    (
        "{layers:['pts','tw','exist','area-fill']",
        "{layers:['pts','tw','sug','exist','area-fill']",
    ),
    (
        "if(h.layer.id==='pts'||h.layer.id==='tw')return showProject(P[h.properties.id]);",
        "if(h.layer.id==='pts'||h.layer.id==='tw')return showProject(P[h.properties.id]);\n"
        " if(h.layer.id==='sug')return showSug(G[h.properties.i]);",
    ),
    (
        "['pts','tw','exist','area-fill'].forEach(l=>{map.on('mouseenter'",
        "['pts','tw','sug','exist','area-fill'].forEach(l=>{map.on('mouseenter'",
    ),
    (
        "tog('tun',",
        "tog('tsg',v=>{sugOn=v;apply();});document.getElementById('nsg').textContent=G.length;\n"
        "if(!G.length)document.getElementById('tsg').style.display='none';\n"
        "tog('tun',",
    ),
]

HTML_PATCHES = [
    (
        '<button class="chip" id="tun" aria-pressed="false">Unplaced (<span id="nun"></span>)'
        "</button>",
        '<button class="chip" id="tun" aria-pressed="false">Unplaced (<span id="nun"></span>)'
        '</button>\n   <button class="chip" id="tsg" aria-pressed="true">Google suggestions '
        '(<span id="nsg"></span>)</button>',
    ),
    (
        '<span class="k"><i class="sw ring"></i>Approximate spot</span>',
        '<span class="k"><i class="sw ring"></i>Approximate spot</span>\n'
        '  <span class="k"><i class="sw" style="background:#fff;border:2px solid #7c3aed"></i>'
        "Google suggestion</span>\n"
        '  <span class="k"><i class="sw" style="border-radius:2px;border:2px dashed #0f766e">'
        "</i>Site outline (OSM)</span>",
    ),
    (
        "Basemap © OpenStreetMap contributors, OpenFreeMap.",
        "Basemap © OpenStreetMap contributors, OpenFreeMap. Name-matched locations and site "
        "outlines © OpenStreetMap contributors (ODbL).",
    ),
]


def _patch(html: str, patches) -> str:
    for anchor, repl in patches:
        n = html.count(anchor)
        if n != 1:
            raise ValueError(f"template anchor found {n} times: {anchor[:70]!r}")
        html = html.replace(anchor, repl)
    return html


def build(template: Path, located_csv: Path, gmaps_csv: Path | None, out: Path) -> dict:
    html = template.read_text(encoding="utf-8")
    P = json.loads(_blk(html, "dp").group(2))
    U = json.loads(_blk(html, "du").group(2))
    rows = {r["reg_number"]: r for r in _read_csv(located_csv)}

    sharpened = 0
    for p in P:
        r = rows.get(p["rg"])
        if r and r.get("location_method") in OSM_METHODS:
            p.update(
                la=float(r["lat"]),
                lo=float(r["lng"]),
                m=r["location_method"],
                cf=r["confidence"],
                nt=r["location_note"],
                su=r["source_url"],
                mn=r["match_name"],
            )
            sharpened += 1

    newly, still = [], []
    for u in U:
        r = rows.get(u["rg"])
        if r and r.get("location_method") in OSM_METHODS and r.get("lat"):
            newly.append(
                {
                    "n": u["n"],
                    "p": r.get("promoter") or "",
                    "rg": u["rg"],
                    "la": float(r["lat"]),
                    "lo": float(r["lng"]),
                    "s": r.get("status") or "unk",
                    "m": r["location_method"],
                    "cf": r["confidence"],
                    "nt": r["location_note"],
                    "t": None,
                    "u": None,
                    "ld": None,
                    "f": None,
                    "fl": None,
                    "c": None,
                    "y": None,
                    "a": r.get("area") or "",
                    "ad": u.get("addr", ""),
                    "pin": None,
                    "su": r["source_url"],
                    "mn": r["match_name"],
                }
            )
        else:
            still.append(u)
    P += newly

    placed_osm = {p["rg"] for p in P if p.get("m") in OSM_METHODS}
    G = []
    for g in _read_csv(gmaps_csv) if gmaps_csv else []:
        if g["reg_number"] in placed_osm or not g.get("lat"):
            continue
        G.append(
            {
                "rg": g["reg_number"],
                "n": g["project"],
                "q": g["query"],
                "gn": g["google_name"],
                "la": float(g["lat"]),
                "lo": float(g["lng"]),
                "d": _num(g.get("dist_km_from_current")),
                "sc": _num(g.get("name_score")),
            }
        )

    sites = {"type": "FeatureCollection", "features": []}
    for reg in placed_osm:
        r = rows.get(reg)
        if r and r.get("site_geojson"):
            sites["features"].append(
                {
                    "type": "Feature",
                    "properties": {"rg": reg},
                    "geometry": json.loads(r["site_geojson"]),
                }
            )

    def put(h: str, bid: str, obj) -> str:
        m = _blk(h, bid)
        return h[: m.start(2)] + _dump(obj) + h[m.end(2) :]

    html = put(html, "dp", P)
    html = put(html, "du", still)
    end = _blk(html, "du").end()
    html = (
        html[:end] + f'\n<script id="dg" type="application/json">{_dump(G)}</script>'
        f'\n<script id="ds" type="application/json">{_dump(sites)}</script>' + html[end:]
    )
    html = _patch(html, JS_PATCHES)
    html = _patch(html, HTML_PATCHES)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return {
        "sharpened": sharpened,
        "newly_placed": len(newly),
        "unplaced": len(still),
        "suggestions": len(G),
        "outlines": len(sites["features"]),
    }


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser(description="Refresh the stand-alone RERA map")
    ap.add_argument("--template", type=Path, required=True)
    ap.add_argument("--located", type=Path, required=True)
    ap.add_argument("--gmaps", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    print(json.dumps(build(a.template, a.located, a.gmaps, a.out)))


if __name__ == "__main__":
    main()
