"""A MERMAID built from blocks - a solid statue with a face, scaled tail, shell top, long hair and a
trident, standing on a pool of water.

The earlier end-rod version (`mermaid_rods.py`) was a wireframe and it failed for a structural reason:
a see-through cage shows its own back half through the front, so the face drowned in hair and ribs.
A solid statue has no back-through-front problem, so this one is a LOFT - the same idea (elliptical
stations swept along an S-curved spine) - but filled, and then PAINTED.

    body      head egg -> neck -> shoulders -> bust -> waist -> hips -> tail, one loft, one spine
    tail      3-tone fish SCALES: overlapping discs, rows offset by half, a colour ramp teal -> violet
    fluke     a thin two-lobed sheet swept back, veined; hip fins and a dorsal crest in glass
    arms      swept capsules; the raised one grips a trident (end-rod shaft, gold head)
    hair      a cap that leaves the face bare, thick locks down the back, two locks over the shoulders
    face      painted on the head's own front surface: eyes (white / iris / pupil / lash), brows, nose,
              lips, blush - found by probing the real skin, never a computed radius
    base      a pool the fluke tips stand on, so it is grounded

TRAPS (from this repo's own history):
  - Anything CLINGING is anchored by probing the built surface, never placed at a computed radius.
  - Integer centres; `round()` is banker's rounding.
  - Feature sizes are fractions of height, so `height` is the only knob.
  - Every part is written through `put`, and a part never replaces another part's block unless asked.
"""
from __future__ import annotations

import math

import numpy as np

from .canvas import Canvas, hash01

MERMAID = {
    "seed": 5,
    "height": 100,                # crown to the pool surface, in blocks
    "at": None,
    "root": None,                 # world cell of the pool's centre top
    "sway": 0.15,                 # side-to-side S of the tail, fraction of height

    # the palette is the repo's CHEAP tier: wool, bone block, blue ice. Concrete / terracotta / glass /
    # prismarine are all "expensive" on this skyblock and a figure this size would burn thousands.
    "skin": "white_wool",
    "skin_hi": "white_wool",
    "blush": "pink_wool",
    "lip_up": "red_wool",
    "lip_lo": "pink_wool",
    "eye_white": "white_wool",
    "iris": "light_blue_wool",
    "pupil": "black_wool",
    "lash": "black_wool",
    "hair": ["red_wool", "brown_wool", "orange_wool"],
    "gold": "yellow_wool",
    "gem": "ochre_froglight",
    "shell": ["pink_wool", "magenta_wool", "white_wool"],
    # tail ramp, top -> tip: (dark edge, main, light centre)
    "tail": [
        ("blue_wool", "cyan_wool", "light_blue_wool"),
        ("cyan_wool", "light_blue_wool", "light_blue_wool"),
        ("blue_wool", "purple_wool", "magenta_wool"),
    ],
    "fluke": ["magenta_wool", "purple_wool", "pink_wool"],
    "glass": "light_blue_wool",
    "rod": "end_rod",
    "pool": ["blue_ice", "light_blue_wool", "snow_block", "blue_wool"],
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


def build(cfg: dict, donors=None) -> Canvas:
    p = {**MERMAID, **(cfg or {})}
    H = float(p["height"])
    k = H / 44.0                                  # block-sized numbers below are in 44-high units
    seed = int(p["seed"])
    sway = float(p["sway"]) * H

    pad = 4
    base = pad + 3                                # y of the pool's surface; the pool is 3 thick below
    half = int(math.ceil(H * 0.36)) + pad
    XC = ZC = half
    SX = SZ = 2 * half + 1
    SY = int(H * 1.30) + base + pad
    c = Canvas(SX, SY, SZ, donors)
    S = c.state

    # cell centres of one horizontal layer, shape (SZ, SX): X varies along axis 1, Z along axis 0
    X, Z = np.meshgrid(np.arange(SX) + 0.5, np.arange(SZ) + 0.5, indexing="xy")

    def Y(f):
        return base + f * H

    def Fof(y):
        return (y + 0.5 - base) / H

    def spine(f):
        low = max(0.0, (0.66 - f) / 0.66)
        x = sway * math.sin(low * math.pi * 1.25) * low ** 0.5
        z = -0.06 * H * low ** 1.6 + 0.012 * H * math.sin((1 - f) * 6)
        return x, z

    # ---- stations: height fraction, half-width x, half-depth z (44-high units, scaled by k)
    ST = [
        (0.845, 1.15, 1.10), (0.83, 3.2, 1.9), (0.79, 3.0, 2.3), (0.745, 2.4, 1.8), (0.70, 1.95, 1.6),
        (0.655, 2.7, 2.1), (0.58, 2.5, 1.95), (0.46, 2.05, 1.6), (0.34, 1.55, 1.25), (0.23, 1.05, 0.9),
        (0.15, 0.75, 0.6), (0.10, 0.6, 0.5),
    ]
    ST = [(f, a * k, b * k) for f, a, b in ST]
    HC, HR, HS = 0.920, 0.066, 1.15               # head egg: centre, half-height, width scale
    f_hips, f_fluke = 0.655, 0.15

    def station(f):
        if f >= HC - HR * 0.92:
            t = (f - HC) / HR
            e = math.sqrt(max(0.0, 1 - min(1.0, t * t)))
            tp = 1 - 0.20 * max(0.0, -t)
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
        """Write block id blk at the True cells of mask (SZ,SX) in layer y."""
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
            rr = r * r - dy2
            m = ((X - cx) ** 2 + (Z - cz) ** 2) <= rr
            put(blk, y, m, replace)

    def sweep(pts, r0, r1, blk, replace=False, blkf=None):
        n = len(pts)
        for i, q in enumerate(pts):
            r = r0 + (r1 - r0) * i / max(1, n - 1)
            b = blkf(i, n) if blkf else blk
            ball(q[0], q[1], q[2], r, b, replace)

    skin = S(p["skin"])
    counts = {"body": 0, "scales": 0, "fluke": 0, "hair": 0, "face": 0, "shell": 0, "trident": 0}

    # ===== THE POOL the fluke stands on ======================================================
    fx0, fz0 = spine(0.0)
    FX, FZ = XC + fx0, ZC + fz0
    span = H * 0.20
    pool_c = (FX, FZ - 0.05 * H * 0.5)
    pool_r = span + 6
    pcols = [S(n) for n in p["pool"]]
    for yy in range(base - 3, base):
        rr0 = pool_r - (base - 1 - yy) * 0.8
        for z in range(SZ):
            for x in range(SX):
                dx, dz = x + 0.5 - pool_c[0], z + 0.5 - pool_c[1]
                d = math.hypot(dx, dz)
                th = math.atan2(dz, dx)
                lim = rr0 * (1 + 0.06 * math.sin(7 * th + 1.3))
                if d <= lim:
                    ring = d / lim
                    if yy == base - 1:
                        wave = 0.5 + 0.5 * math.sin(d * 1.1)
                        blk = pcols[2] if ring > 0.9 else (pcols[0] if wave > 0.55 else pcols[1])
                    else:
                        blk = pcols[3] if yy == base - 3 else pcols[0]
                    c.ids[yy, z, x] = blk

    # ===== THE BODY LOFT =====================================================================
    tops = [(S(a), S(b), S(cc)) for a, b, cc in p["tail"]]
    y_hi, y_lo = int(Y(0.99)), base
    gold = S(p["gold"])
    belt_y = int(Y(f_hips))
    for y in range(y_lo, y_hi + 1):
        f = Fof(y)
        a, b = station(f)
        sx, sz = spine(f)
        cx, cz = XC + sx, ZC + sz
        dx, dz = X - cx, Z - cz
        m = (dx / a) ** 2 + (dz / b) ** 2 <= 1.0
        if f > f_hips + 0.006:                              # above the hips: skin
            put(skin, y, m)
            counts["body"] += int(m.sum())
        else:                                                # TAIL: fish scales
            t = min(1.0, max(0.0, (f_hips - f) / (f_hips - 0.10)))
            seg = t * (len(tops) - 1)
            i0 = min(len(tops) - 2, int(seg))
            tt = seg - i0
            A = tops[i0] if tt < 0.5 else tops[i0 + 1]       # stepped ramp: dark, main, light
            rh = max(3.0, 0.042 * H)                         # scale row height
            row = math.floor((y - base) / rh)
            fr = (y - base) / rh - row
            ar, br = station(Fof(base + (row + 0.5) * rh))
            ns = max(5, int(round(2 * math.pi * (ar + br) / 2 / (0.075 * H))))
            th = np.arctan2(dz / max(b, 1e-6), dx / max(a, 1e-6))
            u = th / (2 * math.pi) * ns + (0.5 if row % 2 else 0.0)
            fu = u - np.floor(u) - 0.5
            fv = fr - 0.35
            dd = fu ** 2 * 1.6 + fv ** 2 * 1.9
            col = np.where(dd < 0.045, A[2], np.where(dd < 0.27, A[1], A[0]))
            layer = c.ids[y]
            sel = m & (layer == 0)
            layer[sel] = col[sel]
            counts["scales"] += int(m.sum())
        if y == belt_y:                                      # a gold belt on the hip line
            inner = (dx / (a - 1.0)) ** 2 + (dz / (b - 1.0)) ** 2 <= 1.0
            put(gold, y, m & ~inner, replace=True)
            put(gold, y + 1, m & ~inner, replace=True)

    # ===== THE FLUKE: a thin two-lobed sheet, swept back at the tips, veined =================
    lead = [(1.00, 0.0), (0.86, 0.035), (0.62, 0.075), (0.30, 0.115), (0.0, 0.15)]      # (u, f) upper edge
    trail = [(0.0, 0.062), (0.22, 0.050), (0.46, 0.036), (0.66, 0.026), (0.84, 0.020), (1.0, 0.0)]  # lower edge
    fl = [S(n) for n in p["fluke"]]
    zs_back = 0.05 * H

    def interp(pts, v, axis):
        # pts sorted by their [axis]; linear
        xs = [q[axis] for q in pts]
        ys = [q[1 - axis] for q in pts]
        order = np.argsort(xs)
        return float(np.interp(v, np.array(xs)[order], np.array(ys)[order]))

    for y in range(base, int(Y(0.17))):
        f = Fof(y)
        fxr, fzr = XC + spine(f)[0], ZC + spine(f)[1]          # the sheet rides the tail's own spine
        for x in range(SX):
            u = abs(x + 0.5 - fxr) / span
            if u > 1.0:
                continue
            fu_edge = interp(lead, f, 1) if f <= 0.15 else 0.0     # u max at this height
            if u > max(fu_edge, 0.10 if f > 0.1 else 0.0):
                continue
            if f < interp(trail, u, 0) - 0.002:
                continue
            zc = fzr - zs_back * u * u
            ang = math.atan2(f - 0.15, (x + 0.5 - fxr) / span * 0.35)
            vein = abs(math.sin(ang * 9.0)) < 0.28
            edge = (u > fu_edge - 0.05) or (f < interp(trail, u, 0) + 0.006)
            blk = fl[2] if edge else (fl[0] if vein else fl[1])
            for z in range(int(zc - 1.2), int(zc + 1.5)):
                if 0 <= z < SZ and c.ids[y, z, x] == 0:
                    c.ids[y, z, x] = blk
                    counts["fluke"] += 1
                    if y - base <= 3:                          # the lobe TIPS stand on the pool
                        for yy in range(y - 1, base - 1, -1):
                            if c.ids[yy, z, x] != 0:
                                break
                            c.ids[yy, z, x] = blk

    # ===== GLASS FINS: hip fins and a serrated dorsal crest =================================
    glass = S(p["glass"])
    for sd in (-1, 1):
        fy0 = f_hips - 0.02
        a, b = station(fy0)
        sx, sz = spine(fy0)
        x0 = XC + sx + sd * a * 0.9
        z0 = ZC + sz - b * 0.45
        hgt = 0.17 * H
        for yy in range(int(Y(fy0) - hgt), int(Y(fy0)) + 1):
            tt = (Y(fy0) - yy) / hgt
            wmax = 0.095 * H * math.sin(math.pi * min(1.0, tt * 0.95 + 0.04)) ** 0.8
            for xo in range(0, int(wmax) + 1):
                zc = z0 - 0.025 * H * (xo / max(1.0, wmax)) - tt * 0.03 * H
                x = int(x0 + sd * xo)
                z = int(round(zc))
                for zz in (z, z + 1):
                    if c.inb(x, yy, zz) and c.ids[yy, zz, x] == 0:
                        c.ids[yy, zz, x] = glass
    fd = f_hips - 0.02
    while fd > 0.20:
        a, b = station(fd)
        sx, sz = spine(fd)
        y0 = int(Y(fd))
        zb = int(ZC + sz - b)
        sp = int((1.4 + 3.4 * (fd - 0.18)) * k * 0.75)
        for j in range(sp + 1):
            for yy in (y0, y0 - (sp - j) // 2):
                x = int(XC + sx)
                z = zb - j
                if c.inb(x, yy, z) and c.ids[yy, z, x] == 0:
                    c.ids[yy, z, x] = glass
        fd -= 0.04

    # ===== ARMS ==============================================================================
    sh = 0.83
    a, b = station(sh)
    sx, sz = spine(sh)
    sy = Y(sh) - 0.9 * k
    arm_r = [(XC + sx + a * 0.6, sy, ZC + sz), (XC + sx + a + 2.6 * k, sy - 3.2 * k, ZC + sz + 1.2 * k),
             (XC + sx + a + 5.0 * k, sy + 1.2 * k, ZC + sz + 2.6 * k), (XC + sx + a + 5.4 * k, sy + 4.6 * k, ZC + sz + 2.8 * k)]
    arm_l = [(XC + sx - a * 0.6, sy, ZC + sz), (XC + sx - a - 1.8 * k, sy - 4.5 * k, ZC + sz + 1.2 * k),
             (XC + sx - a - 1.8 * k, sy - 9.5 * k, ZC + sz + 3.0 * k), (XC + sx - a - 1.0 * k, sy - 12.5 * k, ZC + sz + 4.2 * k)]
    hands = []
    for arm in (arm_r, arm_l):
        pts = _smooth(arm, 10)
        sweep(pts, 0.78 * k, 0.5 * k, skin)
        hands.append(pts[-1])
    hx, hy, hz = hands[0]
    ball(hx, hy + 0.5 * k, hz, 0.62 * k, skin)                                    # the gripping fist
    for fi, dxo in enumerate((-0.45, -0.15, 0.15, 0.45)):                         # knuckles wrap the shaft
        ball(hx + dxo * k, hy + 1.1 * k, hz + 0.45 * k, 0.28 * k, skin)
    lx, ly, lz = hands[1]
    ball(lx, ly - 0.4 * k, lz, 0.6 * k, skin)                                     # open hand
    for dxo, ln in ((-0.5, 1.2), (-0.17, 1.6), (0.17, 1.7), (0.5, 1.4)):
        sweep([(lx + dxo * k, ly - 0.9 * k - j * 0.3, lz + 0.3 * k) for j in range(int(ln * k))], 0.28 * k, 0.2 * k, skin)

    # ===== SHELL TOP =========================================================================
    scol = [S(n) for n in p["shell"]]
    fsh = 0.790
    a, b = station(fsh)
    sx, sz = spine(fsh)
    R = 1.55 * k
    for sd in (-1, 1):
        cxs = XC + sx + sd * a * 0.48
        cys = Y(fsh)
        czs = ZC + sz + b * (1 - 0.48 ** 2) ** 0.5 + 0.35 * R
        for y in range(int(cys - R - 1), int(cys + R + 2)):
            for z in range(int(czs - R), int(czs + R + 2)):
                for x in range(int(cxs - R - 1), int(cxs + R + 2)):
                    if not c.inb(x, y, z):
                        continue
                    dxs, dys, dzs = (x + 0.5 - cxs) / R, (y + 0.5 - cys) / (R * 0.92), (z + 0.5 - czs) / (R * 0.62)
                    if dxs * dxs + dys * dys + dzs * dzs <= 1.0 and dzs > -0.35:
                        th = math.atan2(dys, dxs)
                        rib = int(math.floor((th + math.pi) / (math.pi / 7)))
                        rr = math.hypot(dxs, dys)
                        blk = scol[2] if (rr > 0.86 or rib % 2 == 0 and rr < 0.18) else scol[rib % 2]
                        c.ids[y, z, x] = blk
                        counts["shell"] += 1

    # ===== HAIR ==============================================================================
    hcol = [S(n) for n in p["hair"]]
    ahead, bhead = station(HC)
    hcx, hcz = XC + spine(HC)[0], ZC + spine(HC)[1]
    hy_c = Y(HC)
    hr_y = HR * H
    for y in range(int(hy_c - hr_y * 0.35), int(hy_c + hr_y * 1.12) + 1):
        f = Fof(y)
        a, b = station(min(f, HC + HR * 0.999))
        sx, sz = spine(f)
        cx, cz = XC + sx, ZC + sz
        dx, dz = X - cx, Z - cz
        m = (dx / (a * 1.12 + 0.6)) ** 2 + (dz / (b * 1.10 + 0.6)) ** 2 <= 1.0
        back = dz < b * 0.10                                 # behind the ears; the face stays bare
        fringe = (y > hy_c + hr_y * 0.55)                     # a hairline: hair comes forward over the brow
        sel = m & (back | fringe)
        streak = ((np.floor((dx + dz * 0.5 + y * 0.35) / 2.0)).astype(int) % 3)
        col = np.choose(streak, [hcol[0], hcol[1], hcol[0]])
        layer = c.ids[y]
        s2 = sel & (layer == 0)
        layer[s2] = col[s2]
        counts["hair"] += int(s2.sum())
    nlock = 13
    for i in range(nlock):
        t0 = (i + 0.5) / nlock
        sd = -1 + 2 * t0
        h0 = hash01(seed, i, 1)
        f_top = HC - HR * 0.1
        L = H * (0.40 + 0.18 * h0)
        ph = hash01(seed, i, 2) * 6.28
        pts = []
        for j in range(0, 40):
            tt = j / 39
            f = f_top - (L / H) * tt
            a, b = station(max(f, 0.30))
            sx, sz = spine(max(f, 0.30))
            xlat = sd * (ahead * 0.92 * (1 + 0.55 * tt) + 1.3 * k * tt) + math.sin(tt * 6.0 + ph) * 1.4 * k * tt
            zb = ZC + sz - b - (1.6 + 2.0 * tt) * k * 0.7 - 0.6 * k * math.sin(tt * 5 + ph * 0.5) * tt
            pts.append((XC + sx + xlat, Y(f), zb))
        sweep(pts, 1.25 * k, 0.55 * k, None, blkf=lambda ii, nn, i=i: hcol[(i + (ii // 6)) % 3])
        counts["hair"] += 1
    for sd in (-1, 1):                                         # the two locks over the shoulders
        pts = []
        for j in range(0, 30):
            tt = j / 29
            f = HC - HR * 0.75 - tt * 0.27
            a, b = station(f)
            sx, sz = spine(f)
            pts.append((XC + sx + sd * (ahead * 0.96 + 0.3 * k * math.sin(tt * 3)), Y(f),
                        ZC + sz + b * (0.55 + 0.4 * (1 - tt)) + 0.6 * k + 0.4 * k * math.sin(tt * 6)))
        sweep(pts, 0.62 * k, 0.38 * k, None, blkf=lambda ii, nn: hcol[(ii // 5) % 3])

    # ===== A FLAT FACE PANEL: an ellipsoid's front is a stack of stair-steps, and features painted on it
    # smear. Fill/clip the front of the head to one plane so the face is a clean grid to paint on.
    pa, pb = station(HC)
    panel_hw = 0.74 * pa * 1.0
    for y in range(int(hy_c - hr_y * 0.80), int(hy_c + hr_y * 0.62) + 1):
        f = Fof(y)
        a, b = station(f)
        sx, sz = spine(f)
        cx, cz = XC + sx, ZC + sz
        zplane = cz + 0.86 * pb
        for x in range(SX):
            if abs(x + 0.5 - cx) > panel_hw:
                continue
            zt = int(zplane)                                   # first cell index behind the plane
            for z in range(SZ - 1, zt, -1):                    # clip anything proud of the plane
                if c.ids[y, z, x] == skin:
                    c.ids[y, z, x] = 0
            if c.ids[y, zt, x] == 0 and any(c.ids[y, z, x] == skin for z in range(max(0, zt - 4), zt)):
                c.ids[y, zt, x] = skin                          # fill the dip between ellipsoid and plane
                for z in range(zt - 1, max(0, zt - 6), -1):
                    if c.ids[y, z, x] == 0:
                        c.ids[y, z, x] = skin

    # ===== THE FACE ===========================================================================
    def front_z(x, y):
        """z of the front-most SKIN cell at (x, y), or None - the face is painted ON the skin."""
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

    hx0 = int(round(hcx))
    ey = int(hy_c + 0.20 * hr_y)                              # the eyes' middle row
    W_, IR, PU, LA = S(p["eye_white"]), S(p["iris"]), S(p["pupil"]), S(p["lash"])
    for sd in (-1, 1):
        # 3 wide x 3 tall, two columns clear of the centre line: white | iris | white, lash on top
        cols = [hx0 + 1 + i for i in range(3)] if sd > 0 else [hx0 - 2 - i for i in range(3)]
        cols_in_out = cols                                    # [inner .. outer]
        for xx in cols_in_out:
            paint(xx, ey + 1, LA)                              # lash line
            paint(xx, ey, W_)
            paint(xx, ey - 1, W_)
        paint(cols_in_out[1], ey, IR)
        paint(cols_in_out[1], ey - 1, PU)
        paint(cols_in_out[2] + sd, ey + 1, LA)                 # the flick at the outer corner
        for xx in cols_in_out:                                 # brow, arched toward the outside
            paint(xx, ey + 3 + (1 if xx == cols_in_out[2] else 0), hcol[1])
        paint(cols_in_out[2], ey - 3, S(p["blush"]))           # one blush cell under the outer eye
    # nose: two columns, standing 1 block proud, with a shaded tip
    for yy in (ey - 2, ey - 3):
        for xx in (hx0 - 1, hx0):
            z = front_z(xx, yy)
            if z is not None:
                c.ids[yy, z + 1, xx] = skin
                counts["face"] += 1
    for xx in (hx0 - 1, hx0):
        z = front_z(xx, ey - 3)
        if z is not None:
            c.ids[ey - 3, z, xx] = S(p["lip_lo"])             # the nose tip, a touch pink
    # mouth: a small closed smile - red line, fuller centre, corners lifted
    my = int(hy_c - 0.52 * hr_y)
    for xx in range(hx0 - 2, hx0 + 2):
        paint(xx, my, S(p["lip_up"]))
    for xx in (hx0 - 1, hx0):
        paint(xx, my - 1, S(p["lip_lo"]))
    paint(hx0 - 3, my + 1, S(p["lip_up"]))
    paint(hx0 + 2, my + 1, S(p["lip_up"]))

    # ===== ACCESSORIES: tiara, necklace, pendant, trident ====================================
    lantern = S(p["gem"])
    ty = int(hy_c + 0.55 * hr_y)
    f = Fof(ty)
    a, b = station(f)
    sx, sz = spine(f)
    dx, dz = X - (XC + sx), Z - (ZC + sz)
    ring = ((dx / (a * 1.13 + 0.8)) ** 2 + (dz / (b * 1.11 + 0.8)) ** 2 <= 1.0) & (
        (dx / (a * 1.13 - 0.2)) ** 2 + (dz / (b * 1.11 - 0.2)) ** 2 > 1.0) & (dz > -b * 0.2)
    put(gold, ty, ring, replace=True)
    for off in (-0.62, -0.31, 0.0, 0.31, 0.62):                # five points on the tiara
        xx = int(round(XC + sx + off * a * 1.1))
        zs_ = [z for z in range(SZ) if c.ids[ty, z, xx] == gold]      # anchor to the band itself
        if not zs_:
            continue
        zz = max(zs_)
        hgt = 3 if off == 0 else 2
        for j in range(1, hgt + 1):
            if c.inb(xx, ty + j, zz):
                c.ids[ty + j, zz, xx] = gold if j < hgt or off != 0 else lantern
    xx = int(round(XC + sx))
    zz = int(round(ZC + sz + (b * 1.11 + 0.8) - 0.2))
    if c.inb(xx, ty, zz):
        c.ids[ty, zz, xx] = lantern                            # the centre gem

    ny = int(Y(0.846))                                         # necklace
    f = Fof(ny)
    a, b = station(f)
    sx, sz = spine(f)
    dx, dz = X - (XC + sx), Z - (ZC + sz)
    ring = ((dx / (a + 0.9)) ** 2 + (dz / (b + 0.9)) ** 2 <= 1.0) & ((dx / (a - 0.2)) ** 2 + (dz / (b - 0.2)) ** 2 > 1.0)
    put(S("white_wool"), ny, ring, replace=True)
    for j in range(1, 4):                                      # pendant down the sternum
        f2 = Fof(ny - j)
        a2, b2 = station(f2)
        sx2, sz2 = spine(f2)
        zf = front_z(int(XC + sx2), ny - j)
        if zf is not None:
            c.ids[ny - j, zf + 1 if j == 3 else zf, int(XC + sx2)] = lantern if j == 3 else gold

    # TRIDENT: end-rod shaft through the raised fist, gold head with three prongs, lantern tips
    hx, hy, hz = hands[0]
    shaft_bot, shaft_top = int(hy - 0.12 * H), int(hy + 0.20 * H)
    sxh, szh = int(hx), int(hz)
    rod = S(p["rod"], facing="up")
    for yy in range(shaft_bot, shaft_top):
        if c.inb(sxh, yy, szh) and c.ids[yy, szh, sxh] == 0:
            c.ids[yy, szh, sxh] = rod
            counts["trident"] += 1
    wid = max(3, int(round(0.042 * H)))
    for yy in range(shaft_top - 1, shaft_top + 1):
        for xo in range(-wid, wid + 1):
            if c.inb(sxh + xo, yy, szh):
                c.ids[yy, szh, sxh + xo] = gold
                counts["trident"] += 1
    tall = int(0.075 * H)
    for xo, hgt in ((-wid, tall), (0, tall + max(2, int(0.025 * H))), (wid, tall)):
        for j in range(1, hgt + 1):
            if c.inb(sxh + xo, shaft_top + j, szh):
                c.ids[shaft_top + j, szh, sxh + xo] = gold if j < hgt else lantern
                counts["trident"] += 1

    # ----- sidecar -----
    if p.get("at"):
        c.world_origin = tuple(int(v) for v in p["at"])
    elif p.get("root"):
        wx, wy, wz = (int(v) for v in p["root"])
        c.world_origin = (wx - int(round(pool_c[0])), wy - base, wz - int(round(pool_c[1])))
    c.meta = {"kind": "mermaid", "height": H, "facing": [0, 1], "features_built": counts}
    return c
