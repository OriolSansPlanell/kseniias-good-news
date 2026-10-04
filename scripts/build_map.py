#!/usr/bin/env python3
"""Rebuild world.json (simplified continent outlines for the map).

Needs ne_110m_admin_0_countries.geojson from Natural Earth (public domain):
  git clone --depth 1 --filter=blob:none --sparse https://github.com/nvkelso/natural-earth-vector ne
  (cd ne && git sparse-checkout set --no-cone /geojson/ne_110m_admin_0_countries.geojson)
Then run from the folder holding ne/: python3 build_map.py
"""
import json, math
src = json.load(open("ne/geojson/ne_110m_admin_0_countries.geojson"))
W = 1000.0
# Equal Earth projection
A1,A2,A3,A4 = 1.340264,-0.081106,0.000893,0.003796
M = math.sqrt(3)/2
def ee(lon, lat):
    l = math.radians(lon); p = math.radians(lat)
    th = math.asin(M*math.sin(p)); t2=th*th; t6=t2*t2*t2
    x = 2*math.sqrt(3)*l*math.cos(th) / (3*(9*A4*t6*t2 + 7*A3*t6 + 3*A2*t2 + A1))
    y = th*(A4*t6*t2*th*0 + A1 + A2*t2 + t6*(A3 + A4*t2))
    return x, y
xmax,_ = ee(180,0)
_, ytop = ee(0,84); _, ybot = ee(0,-56)
S = W/(2*xmax)
H = (ytop-ybot)*S
def proj(lon,lat):
    lat = max(min(lat,84),-56)
    x,y = ee(lon,lat)
    return ((x+xmax)*S, (ytop-y)*S)
def dp(pts, tol):
    if len(pts) < 3: return pts
    a, b = pts[0], pts[-1]
    dmax, idx = 0, 0
    ax, ay = a; bx, by = b
    L = math.hypot(bx-ax, by-ay) or 1e-9
    for i in range(1, len(pts)-1):
        px, py = pts[i]
        d = abs((by-ay)*px - (bx-ax)*py + bx*ay - by*ax)/L
        if d > dmax: dmax, idx = d, i
    if dmax > tol:
        return dp(pts[:idx+1], tol)[:-1] + dp(pts[idx:], tol)
    return [a, b]
def area(pts):
    return abs(sum(pts[i][0]*pts[i-1][1]-pts[i-1][0]*pts[i][1] for i in range(len(pts))))/2
paths = {}
for f in src["features"]:
    c = f["properties"]["CONTINENT"]
    if c in ("Antarctica", "Seven seas (open ocean)"): continue
    g = f["geometry"]
    polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
    for poly in polys:
        for ri, ring in enumerate(poly):
            pts = [proj(lon, lat) for lon, lat in ring]
            if area(pts) < 6: continue
            k = max(range(len(pts)), key=lambda i: (pts[i][0]-pts[0][0])**2 + (pts[i][1]-pts[0][1])**2)
            pts = dp(pts[:k+1], 0.9)[:-1] + dp(pts[k:], 0.9)
            if len(pts) < 4: continue
            cx = sum(p[0] for p in pts)/len(pts)
            cc = "South America" if (c == "Europe" and cx < 400) else c
            d = "M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in pts[:-1]) + "Z"
            paths.setdefault(cc, []).append(d)
out = {"w": W, "h": round(H,1), "paths": {k: "".join(v) for k, v in paths.items()}}
json.dump(out, open("world.json","w"), separators=(",",":"))
print({k: len(v) for k,v in out["paths"].items()}, "H", out["h"], "bytes", len(json.dumps(out)))
