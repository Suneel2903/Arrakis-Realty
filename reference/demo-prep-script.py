import pandas as pd, json, math, os
from shapely.geometry import shape, Point, Polygon
d=pd.read_parquet('kr/data/rera-projects.parquet')
b=d[d.district.str.contains('Bengaluru',na=False)&d.status.eq('APPROVED')&d.project_type.str.contains('Residential|Mixed',na=False)]
for c in ['north_latitude','north_longitude','east_latitude','east_longitude','south_latitude','south_longitude','west_latitude','west_longitude']:
    b[c]=pd.to_numeric(b[c],errors='coerce')
mlat=b[['north_latitude','east_latitude','south_latitude','west_latitude']].mean(axis=1)
mlng=b[['north_longitude','east_longitude','south_longitude','west_longitude']].mean(axis=1)
b['latitude']=pd.to_numeric(b.latitude,errors='coerce').fillna(mlat)
b['longitude']=pd.to_numeric(b.longitude,errors='coerce').fillna(mlng)
b=b[b.latitude.between(12.7,13.3)&b.longitude.between(77.3,77.95)].copy()
W=json.load(open('w.json'))
wards=[]
for f in W['features']:
    g=shape(f['geometry']).buffer(0).simplify(0.0004,preserve_topology=True)
    wards.append((f['properties']['KGISWardName'],g))
def ward_of(lat,lng):
    p=Point(lng,lat)
    for n,g in wards:
        if g.contains(p): return n
    return None
rows=[]
for _,r in b.iterrows():
    towers=int(r.number_of_towers) if pd.notna(r.number_of_towers) and r.number_of_towers>0 else 1
    units=int(r.total_units_from_listing) if pd.notna(r.total_units_from_listing) and r.total_units_from_listing>0 else None
    land=float(r.land_area_sqm) if pd.notna(r.land_area_sqm) else None
    far=float(r.far_sanctioned) if pd.notna(r.far_sanctioned) else None
    if units: fl=math.ceil(units/towers/6)
    elif far: fl=round(far/0.35)
    else: fl=4
    fl=max(2,min(fl,45))
    poly=None
    try:
        pts=[(r.north_longitude,r.north_latitude),(r.east_longitude,r.east_latitude),(r.south_longitude,r.south_latitude),(r.west_longitude,r.west_latitude)]
        if all(pd.notna(x) for p in pts for x in p):
            P=Polygon(pts)
            if P.is_valid and P.area>2e-9 and P.centroid.distance(Point(r.longitude,r.latitude))<0.005 and P.area<4e-5:
                poly=[[round(x,6),round(y,6)] for x,y in P.exterior.coords]
    except Exception: pass
    st={'New Project Launch':'new','Ongoing':'ongoing','Completed':'done'}.get(r.project_status,'new')
    comp=pd.to_datetime(r.project_completion_date,errors='coerce')
    nm=r.project_name_full if isinstance(r.project_name_full,str) and r.project_name_full.strip() else r.project_name
    rows.append(dict(n=str(nm).strip().title(), p=str(r.promoter_name).strip().title(), rg=r.reg_number,
      la=round(r.latitude,6), lo=round(r.longitude,6), s=st, t=towers, u=units, ld=round(land) if land else None, f=far, fl=fl,
      c=comp.strftime('%b %Y') if pd.notna(comp) else None, w=ward_of(r.latitude,r.longitude), tk=r.project_taluk if isinstance(r.project_taluk,str) else None, pin=str(int(r.project_pin_code)) if pd.notna(r.project_pin_code) else None, pg=poly))
print(len(rows), 'ward',sum(1 for x in rows if x['w']), 'poly',sum(1 for x in rows if x['pg']), 'units',sum(1 for x in rows if x['u']))
R=1100; lat0=12.97; mx=111320*math.cos(math.radians(lat0)); my=110540
def tohex(lat,lng):
    x=(lng-77.5)*mx; y=(lat-lat0)*my
    q=(2/3*x)/R; rr=(-1/3*x+math.sqrt(3)/3*y)/R
    cx,cz=q,rr; cy=-cx-cz; rx,ry,rz=round(cx),round(cy),round(cz)
    dx,dy,dz=abs(rx-cx),abs(ry-cy),abs(rz-cz)
    if dx>dy and dx>dz: rx=-ry-rz
    elif dy>dz: ry=-rx-rz
    else: rz=-rx-ry
    return rx,rz
def center(q,r):
    x=R*1.5*q; y=R*math.sqrt(3)*(r+q/2)
    return lat0+y/my, 77.5+x/mx
bins={}
for x in rows:
    k=tohex(x['la'],x['lo']); bb=bins.setdefault(k,{'n':0,'u':0,'w':{}})
    bb['n']+=1; bb['u']+=x['u'] or 0
    a=x['w'] or x['tk']
    if a: bb['w'][a]=bb['w'].get(a,0)+1
H=[]
for (q,r),v in bins.items():
    la,lo=center(q,r)
    top=max(v['w'],key=v['w'].get) if v['w'] else None
    H.append(dict(la=round(la,5),lo=round(lo,5),n=v['n'],u=v['u'],w=top))
print('hexes',len(H),'max n',max(h['n'] for h in H),'max u',max(h['u'] for h in H))
def rnd(o):
    if isinstance(o,float): return round(o,5)
    if isinstance(o,(list,tuple)): return [rnd(x) for x in o]
    if isinstance(o,dict): return {k:rnd(v) for k,v in o.items()}
    return o
WG={'type':'FeatureCollection','features':[{'type':'Feature','properties':{'n':n},'geometry':rnd(g.__geo_interface__)} for n,g in wards]}
json.dump(rows,open('projects.json','w'),separators=(',',':'))
json.dump(H,open('hex.json','w'),separators=(',',':'))
json.dump(WG,open('wards.json','w'),separators=(',',':'))
for f in ['projects.json','hex.json','wards.json']: print(f, os.path.getsize(f)//1024,'KB')
print('outside wards share', round(sum(1 for x in rows if not x['w'])/len(rows),2))
