"""A secondary sperm-whale sculpture for the dark water behind the Abyss Squid."""
from __future__ import annotations

import math

import numpy as np

from .canvas import Canvas, hash01


WHALE = {
    # A 200-course leviathan set west of the overlook. Its head approaches the
    # squid while the tail recedes north into the lower void.
    "at": [97500, 95, 80255],
    "size": [115, 85, 215],
    "seed": 11,
    "greybox": False,
    "shell": 2,
    "deep": "gray_wool",
    "dorsal": "black_wool",
    "ventral": "light_gray_wool",
    "pale": "white_wool",
    "scar": "bone_block",
    "eye": "black_wool",
    "mouth_inner": "red_wool",
    "gum": "pink_wool",
}


def _centre(z: int) -> tuple[float, float]:
    """A long, slightly curving pursuit line offset west of the overlook."""
    return 53.0 + 0.025 * z, 40.0 + 0.012 * z


def _ellipsoid(solid, parts, cx, cy, cz, rx, ry, rz, part, exponent=2.0):
    x0, x1 = int(cx-rx-1), int(cx+rx+1)
    y0, y1 = int(cy-ry-1), int(cy+ry+1)
    z0, z1 = int(cz-rz-1), int(cz+rz+1)
    for z in range(z0, z1+1):
        for y in range(y0, y1+1):
            for x in range(x0, x1+1):
                q = (abs((x-cx)/max(rx, .1))**exponent +
                     abs((y-cy)/max(ry, .1))**exponent +
                     abs((z-cz)/max(rz, .1))**exponent)
                if q <= 1.0:
                    solid.add((x, y, z)); parts[(x, y, z)] = part


def _ball_chain(solid, parts, points, radii, part):
    for i, p in enumerate(points):
        r = radii[i]
        _ellipsoid(solid, parts, *p, r, max(1.6, r*.55), r, part)


def _body(solid, parts):
    # Peduncle and torso, sampled per Z so every course overlaps its neighbour.
    for z in range(34, 164):
        t = (z-34)/130
        if t < .18:
            rx = 7 + 12*(t/.18)
        elif t < .62:
            rx = 19 + 7*((t-.18)/.44)
        else:
            rx = 26 - 3*((t-.62)/.38)
        ry = rx * (.70 + .06*math.sin(t*math.pi))
        cx, cy = _centre(z)
        for x in range(int(cx-rx-1), int(cx+rx+2)):
            for y in range(int(cy-ry-1), int(cy+ry+2)):
                if (abs((x-cx)/rx)**2.2 + abs((y-cy)/ry)**2.2) <= 1:
                    solid.add((x, y, z)); parts[(x, y, z)] = "body"

    # The sperm whale's diagnostic spermaceti case: a rising crown, a deep front,
    # and a clean shoulder transition.  The earlier superellipse stayed the same
    # height for forty courses and read as a submarine hull in profile.
    for z in range(142, 208):
        t = (z-142)/65
        rx = 24.0 + 8.0*t
        ry = 18.0 + 7.0*t
        cx, cy = _centre(z)
        hy = cy + 1.0 + 2.0*t
        for x in range(int(cx-rx-1), int(cx+rx+2)):
            for y in range(int(cy-ry-1), int(cy+ry+3)):
                nx, ny = abs((x-cx)/rx), abs((y-hy)/ry)
                if nx**2.65 + ny**2.45 <= 1:
                    solid.add((x, y, z)); parts[(x, y, z)] = "head"

    # A hinged underslung jaw.  Its top falls away from the head toward the nose,
    # creating a real gape instead of a pale patch painted onto a closed solid.
    for z in range(146, 212):
        cx, cy = _centre(z)
        t = (z-146)/65
        rx = 9.0-2.0*t
        high=round(cy-(16+11*t)); low=high-6
        for x in range(round(cx-rx), round(cx+rx)+1):
            for y in range(low,high+1):
                solid.add((x, y, z)); parts[(x, y, z)] = "jaw"

    # Excavate the mouth after the head and jaw exist. Courses 104-109 remain as
    # the hinge, so the lower jaw is structurally part of the animal. At the nose
    # the gap is thirteen courses high and open from both profiles and the front.
    for x,y,z in list(solid):
        if not 154 <= z <= 211 or parts.get((x,y,z)) == "jaw": continue
        cx,cy=_centre(z); t=max(0.0,min(1.0,(z-146)/65))
        jaw_top=round(cy-(16+11*t)); roof=round(cy-7)
        if jaw_top < y <= roof and abs(x-cx) <= 14.0:
            solid.remove((x,y,z)); parts.pop((x,y,z),None)

    # Low dorsal hump and knuckles, rather than a fish-like dorsal fin.
    for z,rx,ry,rz in ((92,11.0,4.0,10.0),(73,7.0,3.0,6.0),(57,5.0,2.2,4.0)):
        cx,cy=_centre(z)
        _ellipsoid(solid,parts,cx,cy+16.5,z,rx,ry,rz,"body",exponent=2.2)


def _flukes(solid, parts):
    cx, cy = _centre(35)
    # Two broad lobes with a real notch. The whole tail is banked: in the previous
    # version a horizontal fluke was seen edge-on in every important profile and
    # vanished, taking the strongest whale cue with it.
    for side in (-1, 1):
        for z in range(2, 44):
            t = (z-2)/41
            reach = 13 + 34*math.sin(math.pi*t)
            root = 3 + 6*t
            for a in np.arange(root, reach+0.1, .8):
                x = int(round(cx + side*a))
                y = int(round(cy + side*.18*a + 2.0*math.sin(t*math.pi)))
                for yy in range(y-3, y+4):
                    solid.add((x, yy, z)); parts[(x, yy, z)] = "fluke"
    for z in range(30, 48):
        for x in range(round(cx-7), round(cx+8)):
            for y in range(round(cy-5), round(cy+6)):
                solid.add((x, y, z)); parts[(x, y, z)] = "peduncle"


def _fins(solid, parts):
    # Short paddle-like pectorals, asymmetric in the bank so one reads in profile.
    for side in (-1, 1):
        pts, radii = [], []
        cx, cy = _centre(142)
        for i in range(16):
            t = i/15
            reach=20+(25 if side>0 else 20)*t
            drop=(22 if side>0 else 16)*t
            pts.append((cx + side*reach, cy-6-drop, 146-25*t))
            radii.append(6.0-3.8*t)
        _ball_chain(solid, parts, pts, radii, "fin")


def _shell(solid: set[tuple[int, int, int]], depth: int):
    if depth <= 0:
        return solid
    current = set(solid)
    inner = set(solid)
    for _ in range(depth):
        inner = {p for p in inner if all((p[0]+dx, p[1]+dy, p[2]+dz) in inner
                 for dx,dy,dz in ((1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)))}
    return current-inner


def build(cfg: dict, donors=None) -> Canvas:
    p = {**WHALE, **(cfg or {})}
    sx, sy, sz = (int(v) for v in p["size"])
    solid, parts = set(), {}
    _body(solid, parts); _flukes(solid, parts); _fins(solid, parts)
    solid = {q for q in solid if 0 <= q[0] < sx and 0 <= q[1] < sy and 0 <= q[2] < sz}
    shown = solid if p.get("greybox") else _shell(solid, int(p.get("shell", 2)))
    c = Canvas(sx, sy, sz, donors)
    states = {k: c.raw_state(v) for k,v in p.items() if k in
              ("deep","dorsal","ventral","pale","scar","eye","mouth_inner","gum")}
    grey = c.raw_state("light_gray_wool")
    counts = {k: 0 for k in ("body","head","jaw","fin","fluke","peduncle",
                              "eye","mouth","teeth","blowhole","scar")}

    for x,y,z in shown:
        part = parts.get((x,y,z), "body")
        counts[part] = counts.get(part, 0)+1
        if p.get("greybox"):
            c.put(x,y,z,grey); continue
        cx, cy = _centre(z)
        mat = states["deep"]
        if y >= cy+6: mat = states["dorsal"]
        elif y <= cy-7: mat = states["ventral"]
        if part == "jaw": mat = states["pale"]
        c.put(x,y,z,mat)

    if not p.get("greybox"):
        skin = shown
        # Colour only surfaces that face the actual cavity. The red palate and
        # pink jaw-top describe depth without painting the whale's exterior.
        for x,y,z in shown:
            if z < 154: continue
            part=parts.get((x,y,z))
            if part == "jaw" and (x,y+1,z) not in solid:
                c.put(x,y,z,states["gum"])
            elif part != "jaw" and (x,y-1,z) not in solid and y <= _centre(z)[1]-5:
                c.put(x,y,z,states["mouth_inner"])

        # Two restrained tooth rows hang from the palate. Each tooth begins on a
        # supported palate cell; alternating lengths keep the mouth animal rather
        # than turning it into a regular portcullis.
        for z in range(156,210,5):
            cx,cy=_centre(z)
            for side in (-1,1):
                x=round(cx+side*5)
                upper=sorted(y for xx,y,zz in solid if xx==x and zz==z and
                             parts.get((xx,y,zz)) != "jaw" and y>cy-5)
                if not upper: continue
                y0=upper[0]
                for dy in range(1,3 if (z//4)&1 else 4):
                    if (x,y0-dy,z) not in solid:
                        c.put(x,y0-dy,z,states["scar"]); counts["teeth"]+=1

        # Small eyes behind the mouth line. The old five-course white patch looked
        # like a ship's porthole and overwhelmed the animal's face.
        for side in (-1,1):
            for z in range(151,156):
                cx, cy = _centre(z); yy=round(cy+1)
                xs = [x for x,y,zz in skin if zz==z and abs(y-yy) <= 1]
                if not xs: continue
                x = min(xs) if side<0 else max(xs)
                for ey in (yy,yy+1):
                    if (x,ey,z) in skin: c.put(x,ey,z,states["pale"])
                if (x,yy,z) in skin:
                    if z in (107,108): c.put(x,yy,z,states["eye"])
                    counts["eye"] += 1

        # Mouth seam on both profiles.
        for side in (-1,1):
            for z in range(151,211):
                cx,cy=_centre(z); yy=round(cy-16+1.4*((z-151)/60))
                xs=[x for x,y,zz in skin if zz==z and y==yy]
                if xs:
                    x=min(xs) if side<0 else max(xs)
                    c.put(x,yy,z,states["eye"]); counts["mouth"] += 1

        # Offset blowhole on the crown.
        for z in range(193,199):
            cx,cy=_centre(z); x=round(cx-4)
            ys=[y for xx,y,zz in skin if zz==z and abs(xx-x)<=1]
            if ys:
                y=max(ys); c.put(x,y,z,states["eye"]); counts["blowhole"] += 1

        # Sucker scars: three restrained rings on the west face of head/shoulder.
        for cz,cy0,r in ((151,48,5),(168,53,4),(186,42,4)):
            for z in range(cz-r-1,cz+r+2):
                cx, _ = _centre(z)
                xs=[x for x,y,zz in skin if zz==z and abs(y-cy0)<=r+1]
                if not xs: continue
                x=min(xs)
                for y in range(cy0-r-1,cy0+r+2):
                    d=math.hypot(y-cy0,z-cz)
                    if r-.65 <= d <= r+.65 and (x,y,z) in skin and (y+z)&1:
                        c.put(x,y,z,states["scar"]); counts["scar"] += 1

        # A low-density value mottle, folded across the centre so it never dents one flank.
        for x,y,z in shown:
            cx,cy=_centre(z)
            if abs(y-cy)<6 and hash01(round(abs(x-cx)),y,z,int(p["seed"])) < .045:
                c.put(x,y,z,states["dorsal"])

    c.world_origin = tuple(int(v) for v in p["at"])
    c.meta = {
        "kind":"sperm_whale", "facing":[0,1], "profile_view":"side",
        "features_built":counts,
        "mouth_open":{"hinge_z":[146,153],"gape_z":[154,211],
                      "nose_gape_courses":19,"tooth_rows":2},
        "reservation":[97500,95,80255,97614,179,80469],
        "purpose":"Secondary abyss landmark revealed from the squid tail overlook",
        "public_access":False, "review_views":["head_on","profile","three_quarter",
        "tail_on","parkour_approach","squid_tail_overlook"],
    }
    return c


DEFAULTS = WHALE
