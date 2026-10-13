"""A MERMAID SPIRIT, swimming - lying on her side, gliding +x through the water, head turned to look at
whoever is standing at +z. More sea-spirit than woman: pale pearl skin that gives way to scales up her
flanks, a stylised glowing-eyed face, fin-ears, a coral crown that points the way she swims, hair and
long fin-veils streaming behind her, and a tail that undulates up and down through the water.

HOW IT IS BUILT. The loft/paint technique of the standing statue (`mermaid_standing.py`) is reused
unchanged - a filled S-spine loft, a fish-scale coat, a flat painted face panel, strands swept as
tapering ball-chains - but built UPRIGHT in a scratch frame and then ROTATED a quarter turn into the
swimming pose:

    scratch (+y up the body, x lateral, z facing)   ->   world (+x along the body, y lateral, z facing)

so "hair draping down her back" becomes "hair streaming behind her", and the tail's sideways S becomes a
vertical undulation, for free. End rods are placed in the scratch frame facing `up`/`east` and swapped
(up <-> east) by the rotation, so a rod always points along the line it belongs to.

WHAT GLOWS: the eyes, the brow gem, a dotted line down the belly and tail (froglights), hair wisps and
the long fluke filaments (end rods), the crown tips. Everything else is the repo's CHEAP tier - wool,
froglights, end rods.

TRAPS (from this repo's own history):
  - Anything CLINGING is anchored to the built surface by probing, never a computed radius.
  - A thread of rods is laid by `_line6` (one axis per step); diagonal neighbours are not connected.
  - Integer centres; `round()` is banker's rounding.
  - The rotation is a transpose, so cell states with a facing must be remapped (up <-> east).
"""
from __future__ import annotations

import math

import numpy as np

from .canvas import Canvas, hash01

MERMAID = {
    "seed": 11,
    "height": 110,                # body length along the swim axis, head crown to fluke bottom, blocks
    "at": None,
    "root": None,                 # world cell of the head's centre
    "sway": 0.20,                 # the S of the tail, fraction of length

    "skin": "white_wool",
    "mark": "light_blue_wool",    # flank scales, cheek lines, brow lines
    "mark_dk": "cyan_wool",
    "eye_glow": "verdant_froglight",
    "gem": "pearlescent_froglight",
    "dot": "verdant_froglight",
    "lash": "blue_wool",
    "mouth": "blue_wool",
    "crown": ["white_wool", "pink_wool", "magenta_wool"],
    "fin": ["cyan_wool", "light_blue_wool", "magenta_wool", "purple_wool"],   # base -> edge
    # hair: root -> tip
    "hair": ["light_blue_wool", "white_wool", "pink_wool", "magenta_wool"],
    # tail ramp, head end -> fluke: (dark edge, main, light centre)
    "tail": [
        ("blue_wool", "cyan_wool", "light_blue_wool"),
        ("blue_wool", "blue_wool", "cyan_wool"),
        ("blue_wool", "purple_wool", "magenta_wool"),
        ("purple_wool", "magenta_wool", "pink_wool"),
    ],
    "fluke": ["magenta_wool", "purple_wool", "pink_wool"],
    "rod": "end_rod",
}


def _smooth(ctrl, n):
    """Catmull-Rom through 3D control points, n samples per span."""
    P = [ctrl[0]] + list(ctrl) + [ctrl[-1]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = (np.array(P[j], float) for j in (i - 1, i, i + 1, i + 2))
        for k in range(n):
            t = k / n
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(np.array(P[-2], float))
    return out


def _line6(a, b):
    """Cells of a 6-connected line a -> b: one axis step at a time."""
    cur = [int(round(float(v))) for v in a]
    end = [int(round(float(v))) for v in b]
    out = [tuple(cur)]
    total = [abs(end[i] - cur[i]) for i in range(3)]
    done = [0, 0, 0]
    while cur != end:
        best, bi = -1.0, None
        for i in range(3):
            if cur[i] != end[i]:
                rem = (total[i] - done[i]) / total[i]
                if rem > best:
                    best, bi = rem, i
        cur[bi] += 1 if end[bi] > cur[bi] else -1
        done[bi] += 1
        out.append(tuple(cur))
    return out


def _thread(pts):
    cells = []
    for i in range(len(pts) - 1):
        seg = _line6(pts[i], pts[i + 1])
        cells.extend(seg if not cells else seg[1:])
    return cells


def build(cfg: dict, donors=None) -> Canvas:
    p = {**MERMAID, **(cfg or {})}
    H = float(p["height"])
    k = H / 44.0
    seed = int(p["seed"])
    sway = float(p["sway"]) * H

    pad = 4
    base = pad
    half = int(math.ceil(H * 0.34)) + pad
    XC = ZC = half
    SX = SZ = 2 * half + 1
    SY = int(H * 1.24) + base + pad
    c = Canvas(SX, SY, SZ, donors)
    S = c.state
    X, Z = np.meshgrid(np.arange(SX) + 0.5, np.arange(SZ) + 0.5, indexing="xy")   # (SZ, SX) per layer

    def Y(f):
        return base + f * H

    def Fof(y):
        return (y + 0.5 - base) / H

    def spine(f):
        low = max(0.0, (0.66 - f) / 0.66)
        x = sway * math.sin(low * math.pi * 1.25) * low ** 0.5
        z = -0.04 * H * low ** 1.6 + 0.010 * H * math.sin((1 - f) * 6)
        return x, z

    # stations (height fraction, half-width x [lateral], half-depth z), 44-high units. Slim, sleek torso:
    # no bust, narrow shoulders, a long tail.
    ST = [
        (0.90, 1.25, 1.2), (0.845, 1.15, 1.1), (0.83, 2.7, 1.7), (0.79, 2.5, 1.85), (0.745, 2.1, 1.6), (0.70, 1.8, 1.5),
        (0.655, 2.3, 1.9), (0.58, 2.3, 1.85), (0.46, 1.95, 1.6), (0.34, 1.5, 1.25), (0.23, 1.05, 0.9),
        (0.15, 0.75, 0.6), (0.10, 0.6, 0.5),
    ]
    ST = [(f, a * k, b * k) for f, a, b in ST]
    HC, HR, HS = 0.920, 0.074, 1.38
    HEAD = [False]                                             # the head egg is only used in the head phase
    f_hips = 0.655

    def station(f):
        if f >= HC - HR * 0.92 and HEAD[0]:
            t = (f - HC) / HR
            e = math.sqrt(max(0.0, 1 - min(1.0, t * t)))
            tp = 1 - 0.26 * max(0.0, -t)                       # a pointed, elfin chin
            return max(0.4 * k, 2.25 * HS * k * e * tp), max(0.4 * k, 2.45 * HS * k * e * tp)
        for i in range(len(ST) - 1):
            f0, a0, b0 = ST[i]
            f1, a1, b1 = ST[i + 1]
            if f1 <= f <= f0:
                u = (f0 - f) / (f0 - f1)
                u = u * u * (3 - 2 * u)
                return a0 + (a1 - a0) * u, b0 + (b1 - b0) * u
        return ST[-1][1], ST[-1][2]

    def put(blk, y, mask, replace=False):
        if not (0 <= y < SY):
            return
        layer = c.ids[y]
        m = mask if replace else (mask & (layer == 0))
        layer[m] = blk

    def ball(cx, cy, cz, r, blk, replace=False):
        for y in range(max(0, int(cy - r - 1)), min(SY, int(cy + r + 2))):
            dy2 = (y + 0.5 - cy) ** 2
            if dy2 > r * r:
                continue
            m = ((X - cx) ** 2 + (Z - cz) ** 2) <= (r * r - dy2)
            put(blk, y, m, replace)

    def sweep(pts, r0, r1, blk, replace=False, blkf=None):
        n = len(pts)
        for i, q in enumerate(pts):
            r = r0 + (r1 - r0) * i / max(1, n - 1)
            ball(q[0], q[1], q[2], r, blkf(i, n) if blkf else blk, replace)

    def cell(x, y, z, blk, replace=False):
        x, y, z = int(round(x)), int(round(y)), int(round(z))
        if c.inb(x, y, z) and (replace or c.ids[y, z, x] == 0):
            c.ids[y, z, x] = blk
            return True
        return False

    ROD_UP = S(p["rod"], facing="up")          # scratch-frame: along the body  -> world east
    ROD_EAST = S(p["rod"], facing="east")      # scratch-frame: lateral         -> world up

    skin, mark, markdk = S(p["skin"]), S(p["mark"]), S(p["mark_dk"])
    counts = {"body": 0, "scales": 0, "fluke": 0, "hair": 0, "face": 0, "fins": 0, "crown": 0, "glow": 0}

    # ===== THE BODY LOFT: pearl skin, scales up the flanks, a fish-scale tail ================
    tops = [(S(a), S(b), S(cc)) for a, b, cc in p["tail"]]

    def scale_cols(y, a, b, dx, dz, stop, row_h):
        row = math.floor((y - base) / row_h)
        fr = (y - base) / row_h - row
        ar, br = station(Fof(base + (row + 0.5) * row_h))
        ns = max(5, int(round(2 * math.pi * (ar + br) / 2 / (0.075 * H))))
        th = np.arctan2(dz / max(b, 1e-6), dx / max(a, 1e-6))
        u = th / (2 * math.pi) * ns + (0.5 if row % 2 else 0.0)
        fu = u - np.floor(u) - 0.5
        dd = fu ** 2 * 1.6 + (fr - 0.35) ** 2 * 1.9
        A = tops[stop]
        return np.where(dd < 0.045, A[2], np.where(dd < 0.27, A[1], A[0]))

    y_hi, y_lo = int(Y(0.862)), base                         # the loft stops at the neck: the head is built later, upright
    row_h = max(3.0, 0.042 * H)
    for y in range(y_lo, y_hi + 1):
        f = Fof(y)
        a, b = station(f)
        sx, sz = spine(f)
        cx, cz = XC + sx, ZC + sz
        dx, dz = X - cx, Z - cz
        m = (dx / a) ** 2 + (dz / b) ** 2 <= 1.0
        layer = c.ids[y]
        sel = m & (layer == 0)
        if f > f_hips + 0.006:                                 # TORSO: skin, scales climbing the flanks
            layer[sel] = skin
            counts["body"] += int(m.sum())
            top = 0.80
            if f < top:
                thr = 0.50 + 0.50 * (f - f_hips) / (top - f_hips)
                flank = (np.abs(dx) / a > thr) & sel
                if flank.any():
                    cols = scale_cols(y, a, b, dx, dz, 0, row_h)
                    layer[flank] = cols[flank]
                    counts["scales"] += int(flank.sum())
        else:                                                  # TAIL: a four-stop ramp, head -> fluke
            t = min(0.999, max(0.0, (f_hips - f) / (f_hips - 0.04)))
            stop = int(t * len(tops))
            cols = scale_cols(y, a, b, dx, dz, stop, row_h)
            layer[sel] = cols[sel]
            counts["scales"] += int(m.sum())

    # belly line of light: a froglight dot every few scale rows down the front of the tail
    dot = S(p["dot"])
    n_dots = 0
    y = int(Y(f_hips)) - 2
    while y > base + 2:
        f = Fof(y)
        sx, sz = spine(f)
        x0 = int(round(XC + sx))
        zf = max([z for z in range(SZ) if c.ids[y, z, x0] != 0] or [-1])
        if zf >= 0 and f < f_hips - 0.01:
            c.ids[y, zf, x0] = dot
            n_dots += 1
        y -= int(round(row_h * 1.5))
    counts["glow"] += n_dots

    # ===== THE FLUKE: a big crescent sheet of veined colour, with filaments of light =========
    lead = [(1.00, 0.0), (0.88, 0.045), (0.66, 0.090), (0.34, 0.130), (0.0, 0.170)]       # (u, f) upper edge
    trail = [(0.0, 0.060), (0.22, 0.045), (0.46, 0.030), (0.66, 0.022), (0.84, 0.014), (1.0, 0.0)]
    fl = [S(n) for n in p["fluke"]]
    span = H * 0.26
    zs_back = 0.04 * H

    def interp(pts, v, axis):
        xs = np.array([q[axis] for q in pts])
        ys = np.array([q[1 - axis] for q in pts])
        o = np.argsort(xs)
        return float(np.interp(v, xs[o], ys[o]))

    for y in range(base, int(Y(0.19))):
        f = Fof(y)
        fxr, fzr = XC + spine(f)[0], ZC + spine(f)[1]
        for x in range(SX):
            u = abs(x + 0.5 - fxr) / span
            if u > 1.0:
                continue
            fu_edge = interp(lead, f, 1) if f <= 0.17 else 0.0
            if u > max(fu_edge, 0.10 if f > 0.12 else 0.0):
                continue
            tr = interp(trail, u, 0)
            if f < tr - 0.002:
                continue
            zc = fzr - zs_back * u * u
            ang = math.atan2(f - 0.17, (x + 0.5 - fxr) / span * 0.32)
            vein = abs(math.sin(ang * 10.0)) < 0.26
            edge = (u > fu_edge - 0.05) or (f < tr + 0.006)
            blk = fl[2] if edge else (fl[0] if vein else fl[1])
            for z in range(int(zc - 1.2), int(zc + 1.5)):
                if 0 <= z < SZ and c.ids[y, z, x] == 0:
                    c.ids[y, z, x] = blk
                    counts["fluke"] += 1
    # filaments: threads of end rods trailing from the trailing edge, all connected to the fluke
    for i, u in enumerate((-1.0, -0.82, -0.6, -0.36, -0.12, 0.12, 0.36, 0.6, 0.82, 1.0)):
        fxr = XC + spine(0.0)[0]
        fzr = ZC + spine(0.0)[1]
        f_s = interp(trail, abs(u), 0)
        x_s = fxr + u * span
        z_s = fzr - zs_back * u * u
        y_s = Y(f_s)
        if not c.inb(int(x_s), int(y_s), int(z_s)):
            continue
        ln = (0.10 + 0.07 * hash01(seed, i, 1)) * H
        ph = hash01(seed, i, 2) * 6.28
        pts = [(x_s, y_s, z_s)]
        for j in range(1, 8):
            tt = j / 7
            pts.append((x_s + u * 3.0 * k * tt + math.sin(tt * 5 + ph) * 1.8 * k * tt, y_s - ln * tt,
                        z_s - 0.4 * k * tt + math.sin(tt * 4 + ph) * 0.9 * k * tt))
        for (x, y, z) in _thread(_smooth(pts, 3)):
            if cell(x, y, z, ROD_UP):
                counts["glow"] += 1

    # ===== FIN VEILS: translucent-looking ribbons along both flanks of the tail ==============
    fin = [S(n) for n in p["fin"]]

    def veil(f0, f1, side, amp, phase):
        for y in range(int(Y(f1)), int(Y(f0)) + 1):
            f = Fof(y)
            a, b = station(f)
            sx, sz = spine(f)
            env = max(0.0, math.sin(math.pi * (f - f1) / (f0 - f1))) ** 0.85
            w = amp * H * env * (0.78 + 0.22 * math.sin(phase + f * 21))
            if w < 1.0:
                continue
            xb = XC + sx + side * (a * 0.93)
            for d in range(0, int(w) + 1):
                tt = d / w
                zc = ZC + sz - 0.012 * H * tt - 0.5 * b * tt * 0.3
                ray = ((y - base) * 0.9 + d * 1.4) % 6.5 < 1.0
                blk = fin[min(len(fin) - 1, int(tt * len(fin)))]
                if ray and d > 1:
                    blk = fin[min(len(fin) - 1, int(tt * len(fin)) + 1)]
                if tt > 0.86 and ((y + d) % 3 == 0):               # a scalloped, ragged edge
                    continue
                x = int(round(xb + side * d))
                for zz in (int(round(zc)), int(round(zc)) + 1):
                    if cell(x, y, zz, blk):
                        counts["fins"] += 1

    for sd in (-1, 1):
        veil(0.64, 0.17, sd, 0.085, 0.0 if sd > 0 else 2.1)
        veil(0.74, 0.58, sd, 0.045, 1.0 if sd > 0 else 3.0)        # a shorter hip frill above it

    # ===== ARMS: swept back along the body, with webbed fin-sleeves ==========================
    sh = 0.83
    a, b = station(sh)
    sx, sz = spine(sh)
    sy = Y(sh) - 0.8 * k
    hands = []
    for sd in (-1, 1):
        arm = [(XC + sx + sd * a * 0.65, sy, ZC + sz + 0.1 * b),
               (XC + sx + sd * (a + 1.4 * k), sy - 4.5 * k, ZC + sz + 0.6 * b),
               (XC + sx + sd * (a + 2.8 * k), sy - 9.5 * k, ZC + sz + 0.7 * b),
               (XC + sx + sd * (a + 3.6 * k), sy - 13.0 * k, ZC + sz + 0.6 * b)]
        pts = _smooth(arm, 10)
        sweep(pts, 0.70 * k, 0.42 * k, skin)
        hx, hy, hz = pts[-1]
        hands.append((hx, hy, hz, sd))
        # the fin-sleeve: a sheet on the outer side of the forearm, widest mid-forearm - one row per
        # integer course, so it is a membrane and not a comb
        n0 = len(pts) // 3
        rows = {}
        for i in range(n0, len(pts)):
            px, py, pz = pts[i]
            rows.setdefault(int(round(py)), []).append((i, px, pz))
        for yy, lst in rows.items():
            i, px, pz = lst[len(lst) // 2]
            tt = (i - n0) / max(1, len(pts) - 1 - n0)
            w = 3.6 * k * math.sin(math.pi * (0.1 + 0.9 * tt)) ** 0.8
            for d in range(1, int(w) + 1):
                blk = fin[min(len(fin) - 1, int(d / max(1.0, w) * len(fin)))]
                for zz in (int(round(pz)), int(round(pz)) + 1):
                    if cell(px + sd * (0.6 * k + d), yy, zz, blk):
                        counts["fins"] += 1
    for hx, hy, hz, sd in hands:                                 # long webbed fingers, fanned back
        ball(hx, hy, hz, 0.5 * k, skin)
        for fi, spread in enumerate((-0.55, -0.2, 0.15, 0.5)):
            ln = (1.8 + 0.5 * math.sin(fi * 1.7)) * k
            fpts = [(hx + sd * spread * k * (1 + j * 0.12), hy - j * 0.55, hz) for j in range(int(ln * 1.8))]
            sweep(fpts, 0.26 * k, 0.16 * k, skin)
            if fi < 3:                                           # web between fingers
                for j in range(int(ln * 1.1)):
                    cell(hx + sd * (spread + 0.18) * k * (1 + j * 0.12), hy - j * 0.55, hz, fin[1])

    # ===== ROTATE the body into the swimming pose; from here on we build in WORLD axes ==========
    ids = np.transpose(c.ids, (2, 1, 0)).copy()                 # (Yw, Zw, Xw) = (x_s, z_s, y_s)
    east_w, up_w = S(p["rod"], facing="east"), S(p["rod"], facing="up")
    was_up, was_east = ids == ROD_UP, ids == ROD_EAST
    ids[was_up] = east_w                                          # along the body -> along world x
    ids[was_east] = up_w                                          # lateral -> world y
    c.ids = ids
    SY, SZ, SX = ids.shape
    c.sy, c.sz, c.sx = SY, SZ, SX
    X, Z = np.meshgrid(np.arange(SX) + 0.5, np.arange(SZ) + 0.5, indexing="xy")

    # the HEAD is upright and turned to the viewer (neck bent), centred just ahead of the neck
    HEAD[0] = True
    hxw = int(round(Y(HC + 0.014)))                              # world x of the head centre
    hyw = int(round(XC + spine(0.86)[0]))                        # world y (the body's lateral centre)
    hzw = int(round(ZC + spine(0.86)[1]))
    hr_y = HR * H
    ahead, bhead = station(HC)
    ROD_E = east_w                                                # along x
    ROD_U = up_w

    def Yh(f):
        return hyw + (f - HC) * H

    def Fh(y):
        return HC + (y + 0.5 - hyw) / H

    # neck: a short tube from the body's neck end to the head's centre
    for xx in range(int(Y(0.84)), hxw):
        ball_x = xx + 0.5
        for y in range(hyw - 4, hyw + 5):
            for z in range(hzw - 4, hzw + 5):
                if ((y + 0.5 - hyw) / 1.35 / k * 1.0) ** 2 + ((z + 0.5 - hzw) / 1.3 / k) ** 2 <= 1.0:
                    if c.ids[y, z, xx] == 0:
                        c.ids[y, z, xx] = skin

    # ===== THE HEAD: the same egg as always, now looped over world y ===========================
    for y in range(int(hyw - hr_y - 1), int(hyw + hr_y + 2)):
        f = Fh(y)
        if f > HC + HR or f < HC - HR * 0.92:
            continue
        a, b = station(f)
        m = ((X - hxw) / a) ** 2 + ((Z - hzw) / b) ** 2 <= 1.0
        put(skin, y, m)
        counts["body"] += int(m.sum())

    # ===== HAIR CAP: leaves the face bare =====================================================
    hcol = [S(n) for n in p["hair"]]
    for y in range(int(hyw - hr_y * 0.35), int(hyw + hr_y * 1.10) + 1):
        f = Fh(y)
        a, b = station(min(f, HC + HR * 0.999))
        dx, dz = X - hxw, Z - hzw
        m = (dx / (a * 1.10 + 0.5)) ** 2 + (dz / (b * 1.08 + 0.5)) ** 2 <= 1.0
        back = dz < b * 0.10
        fringe = (y > hyw + hr_y * 0.60)
        sel = m & (back | fringe) & (c.ids[y] == 0)
        streak = ((np.floor((dx * 0.5 + dz + y * 0.35) / 2.0)).astype(int) % 2)
        col = np.where(streak == 0, hcol[0], hcol[1])
        c.ids[y][sel] = col[sel]
        counts["hair"] += int(sel.sum())

    # ===== HAIR: long locks that stream BEHIND her, along the body and past the tail =============
    def body_at(x):
        fb = min(0.86, max(0.2, Fof(x)))
        a, b = station(fb)
        sx, sz = spine(fb)
        return XC + sx, ZC + sz, a, b

    nlock = 26
    for i in range(nlock):
        cls = i % 4                                              # upper flank, lower flank, behind (x2)
        side = 1 if cls == 0 else (-1 if cls == 1 else 0)
        h0 = hash01(seed, i, 1)
        ph = hash01(seed, i, 2) * 6.28
        L = H * (0.50 + 0.30 * h0)
        amp = (1.5 + 2.0 * hash01(seed, i, 4)) * k
        zoff = (hash01(seed, i, 6) - 0.5) * 2.0
        y_root = hyw + (side if side else (hash01(seed, i, 5) - 0.5) * 1.6) * hr_y * (0.25 + 0.55 * hash01(seed, i, 3))
        pts = []
        N = 56
        for j in range(N):
            tt = j / (N - 1)
            x = hxw - ahead * 0.55 - L * tt
            cyb, czb, ab, bb = body_at(x)
            sm = min(1.0, tt * 5.0)                              # blend from the head to hugging the body
            r = (1.25 - 0.85 * tt) * k
            if side:
                y_t = cyb + side * (ab + r + 0.8 + (0.6 + 4.0 * tt ** 1.1) * k)
                z_t = czb + zoff * bb * 0.5
            else:
                y_t = cyb + math.sin(tt * 6 + ph) * amp * 0.7
                z_t = czb - bb - r - 0.8 - (0.4 + 3.0 * tt) * k
            y_t += math.sin(tt * 6 + ph) * amp * tt * (1 if side else 0.3)
            y = y_root * (1 - sm) + y_t * sm
            z = (hzw - 0.1 * bhead) * (1 - sm) + z_t * sm
            pts.append((x, y, z))
        sweep(pts, 1.25 * k, 0.40 * k, None,
              blkf=lambda ii, nn: hcol[min(len(hcol) - 1, int(ii / nn * len(hcol)))])
        counts["hair"] += 1
        tip = pts[-1]                                            # a wisp of light off the tip, still connected
        wisp = [tip] + [(tip[0] - j * 1.5 * k, tip[1] + (side or 1) * j * 0.35 * k + math.sin(j * 0.9 + ph) * 0.9 * k,
                         tip[2] - j * 0.15 * k) for j in range(1, 6)]
        for (x, y, z) in _thread(_smooth(wisp, 3)):
            if cell(x, y, z, ROD_E):
                counts["glow"] += 1

    # ===== A FLAT FACE PANEL, then the face ====================================================
    pa, pb = station(HC)
    panel_hw = 0.74 * pa
    for y in range(int(hyw - hr_y * 0.80), int(hyw + hr_y * 0.62) + 1):
        zt = int(hzw + 0.86 * pb)
        for x in range(SX):
            if abs(x + 0.5 - hxw) > panel_hw:
                continue
            for z in range(SZ - 1, zt, -1):
                if c.ids[y, z, x] == skin:
                    c.ids[y, z, x] = 0
            if c.ids[y, zt, x] == 0 and any(c.ids[y, z, x] == skin for z in range(max(0, zt - 4), zt)):
                c.ids[y, zt, x] = skin
                for z in range(zt - 1, max(0, zt - 6), -1):
                    if c.ids[y, z, x] == 0:
                        c.ids[y, z, x] = skin

    def front_z(x, y):
        for z in range(SZ - 1, -1, -1):
            if c.ids[y, z, x] == skin:
                return z
        return None

    def paint(x, y, blk):
        z = front_z(int(x), int(y))
        if z is None:
            return False
        c.ids[y, z, int(x)] = blk
        counts["face"] += 1
        return True

    hx0 = hxw
    ey = int(hyw + 0.18 * hr_y)
    GLOW, LASH, MOUTH = S(p["eye_glow"]), S(p["lash"]), S(p["mouth"])
    for sd in (-1, 1):
        cols = [hx0 + 1 + i for i in range(5)] if sd > 0 else [hx0 - 2 - i for i in range(5)]
        for i, xx in enumerate(cols):                            # a large almond eye of pure light
            paint(xx, ey, GLOW)
            if i < 4:
                paint(xx, ey - 1, GLOW)
            paint(xx, ey + 1, LASH)
        paint(cols[-1] + sd, ey + 1, LASH)
        paint(cols[-1] + 2 * sd, ey + 2, LASH)                   # the liner sweeps up toward the temple
        for r, (x0, ln) in enumerate(((1, 3), (2, 3), (3, 2))):  # cheek lines, angling down and out
            for j in range(ln):
                paint(cols[min(4, x0 + j)] + sd * (1 if j == ln - 1 else 0), ey - 3 - r, markdk)
        for i, xx in enumerate(cols):                            # brow: one arched stroke
            paint(xx, ey + 3 + (1 if i >= 2 else 0), mark)
    for xx in (hx0 - 1, hx0):                                    # nose: barely there
        paint(xx, ey - 2, mark)
    z = front_z(hx0, ey - 3)
    if z is not None:
        c.ids[ey - 3, z + 1, hx0] = mark
        c.ids[ey - 3, z + 1, hx0 - 1] = mark
    my = int(hyw - 0.54 * hr_y)
    for xx in range(hx0 - 2, hx0 + 2):                           # a thin closed mouth, no lips
        paint(xx, my, MOUTH)
    gem = S(p["gem"])
    gy = int(hyw + 0.62 * hr_y)
    for dx_, dy_ in ((-1, 0), (0, 0), (-1, 1), (0, 1)):
        paint(hx0 + dx_, gy + dy_, gem)
    for dx_, dy_ in ((-2, 0), (1, 0), (-2, 1), (1, 1), (-1, -1), (0, -1), (-1, 2), (0, 2)):
        paint(hx0 + dx_, gy + dy_, mark)
    counts["glow"] += 6

    # ===== FIN-EARS: swept leaves off the sides of the head, each rimmed with light ==============
    for sd in (-1, 1):
        base_pt = (hxw + sd * ahead * 0.92, hyw + 0.15 * hr_y, hzw + 0.1 * bhead)
        tip_pt = (hxw + sd * (ahead + 7.5 * k), hyw - 9.5 * k, hzw - 0.3 * bhead)
        mid_c = (hxw + sd * (ahead + 5.5 * k), hyw + 1.5 * k, hzw)
        spine_pts = _smooth([base_pt, mid_c, tip_pt], 20)
        n = len(spine_pts)
        for i, (px, py, pz) in enumerate(spine_pts):
            tt = i / (n - 1)
            w = 2.7 * k * math.sin(math.pi * (0.12 + 0.88 * tt)) ** 0.9
            tx, ty = ((spine_pts[i + 1][0] - px, spine_pts[i + 1][1] - py) if i < n - 1
                      else (px - spine_pts[i - 1][0], py - spine_pts[i - 1][1]))
            nl = math.hypot(tx, ty) or 1.0
            nx, ny = -ty / nl, tx / nl
            for d in np.linspace(-w, w, max(3, int(w * 3.0))):
                blk = fin[1] if abs(d) < w * 0.7 else fin[0]
                for zz in (pz, pz + 1):
                    if cell(px + nx * d, py + ny * d, zz, blk):
                        counts["fins"] += 1
        wisp = [tip_pt, (tip_pt[0] + sd * 1.2 * k, tip_pt[1] - 3.0 * k, tip_pt[2]),
                (tip_pt[0] + sd * 0.6 * k, tip_pt[1] - 6.5 * k, tip_pt[2])]
        for (x, y, z) in _thread(_smooth(wisp, 3)):
            if cell(x, y, z, ROD_U):
                counts["glow"] += 1

    # ===== CORAL CROWN: branching antlers rising from the brow ================================
    ccol = [S(n) for n in p["crown"]]
    crown_y = hyw + hr_y * 0.80
    for off, lean, ln in ((0.0, 0.0, 9.0), (-0.52, -0.55, 7.0), (0.52, 0.55, 7.0), (-0.95, -1.0, 4.5), (0.95, 1.0, 4.5)):
        x0 = hxw + off * ahead
        y0 = crown_y - (abs(off) * 0.9) * k
        z0 = hzw + 0.12 * bhead
        path = [(x0, y0, z0), (x0 + lean * 1.8 * k, y0 + ln * 0.45 * k, z0 + 0.2 * k),
                (x0 + lean * 4.2 * k, y0 + ln * 0.80 * k, z0 + 0.5 * k), (x0 + lean * 6.4 * k, y0 + ln * k, z0 + 0.4 * k)]
        pts = _smooth(path, 10)
        sweep(pts, 0.85 * k, 0.28 * k, None, blkf=lambda ii, nn: ccol[min(2, int(ii / nn * 3))])
        counts["crown"] += 1
        for tw, at in ((0.45, 1), (0.7, -1)):                   # twigs off the main branch
            q = pts[int(len(pts) * tw)]
            end = (q[0] + at * 2.6 * k + lean * 0.8 * k, q[1] + 3.6 * k, q[2])
            sweep(_smooth([q, ((q[0] + end[0]) / 2, (q[1] + end[1]) / 2, q[2]), end], 5), 0.45 * k, 0.2 * k, None,
                  blkf=lambda ii, nn: ccol[1 if ii < nn * 0.6 else 2])
            for (x, y, z) in _thread([end, (end[0] + at * 0.3 * k, end[1] + 2.2 * k, end[2])]):
                cell(x, y, z, ROD_U)
        tip = pts[-1]
        for (x, y, z) in _thread([tip, (tip[0] + lean * 0.5 * k, tip[1] + 2.8 * k, tip[2])]):
            if cell(x, y, z, ROD_U):
                counts["glow"] += 1

    # ===== PEARL COLLAR: a ring round the neck (a plane at one x) with a drop of light ===========
    xn = int(Y(0.852))
    ra, rb = 1.15 * k + 0.9, 1.1 * k + 0.9
    for y in range(hyw - 8, hyw + 9):
        for z in range(hzw - 8, hzw + 9):
            q = ((y + 0.5 - hyw) / ra) ** 2 + ((z + 0.5 - hzw) / rb) ** 2
            if 0.45 < q <= 1.0 and c.inb(xn, y, z):
                c.ids[y, z, xn] = S("white_wool")
    cell(xn, hyw, hzw + int(rb), gem, replace=True)

    # ===== JOIN any stray piece to the main body with a thread of end rod ======================
    def comps():
        nzs = set(zip(*[a_.tolist() for a_ in np.nonzero(c.ids)]))
        seen, out = set(), []
        for s0 in nzs:
            if s0 in seen:
                continue
            st, comp = [s0], []
            seen.add(s0)
            while st:
                y, z, x = st.pop()
                comp.append((y, z, x))
                for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
                    q = (y + d[0], z + d[1], x + d[2])
                    if q in nzs and q not in seen:
                        seen.add(q)
                        st.append(q)
            out.append(comp)
        return out

    for _ in range(60):
        cs = comps()
        if len(cs) <= 1:
            break
        cs.sort(key=len, reverse=True)
        main, other = np.array(cs[0]), np.array(cs[1])
        d2 = ((other[:, None, :] - main[None, :, :]) ** 2).sum(-1)
        i_, j_ = np.unravel_index(int(d2.argmin()), d2.shape)
        a_, b_ = tuple(other[i_]), tuple(main[j_])
        for (y, z, x) in _thread([a_, b_]):
            if c.ids[y, z, x] == 0:
                c.ids[y, z, x] = ROD_E
                counts["glow"] += 1

    # ===== crop to the model, and set the sidecar ===============================================
    nz = np.nonzero(c.ids)
    y0, y1 = max(0, int(nz[0].min()) - 2), int(nz[0].max()) + 3
    z0_, z1_ = max(0, int(nz[1].min()) - 2), int(nz[1].max()) + 3
    x0_, x1_ = max(0, int(nz[2].min()) - 2), int(nz[2].max()) + 3
    c.ids = c.ids[y0:y1, z0_:z1_, x0_:x1_].copy()
    c.sy, c.sz, c.sx = c.ids.shape
    head_w = (hxw - x0_, hyw - y0, hzw - z0_)                     # (x, y, z) of the head centre

    if p.get("at"):
        c.world_origin = tuple(int(v) for v in p["at"])
    elif p.get("root"):
        wx, wy, wz = (int(v) for v in p["root"])
        c.world_origin = (wx - head_w[0], wy - head_w[1], wz - head_w[2])
    c.meta = {"kind": "mermaid", "height": H, "facing": [1, 0], "pose": "swimming",
              "features_built": counts}
    return c
