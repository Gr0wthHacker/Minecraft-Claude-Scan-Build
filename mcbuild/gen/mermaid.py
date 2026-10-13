"""A MERMAID drawn in light - an end-rod wireframe, a loft you can see through.

An end rod is a 2x2-pixel post, so it is a LINE and not a volume. That decides the whole design:
a mermaid cannot be a filled statue in this block, but a statue's wire cage - horizontal contour
rings stacked up a body, joined by longitudinal ribs - is exactly what a loft is, and it reads as a
glowing sculpture at night (an end rod is light level 14).

    head, neck, torso, hips, tail  - one lofted spine of elliptical stations; a ring every
                                     `ring_every` courses, `ribs` longitudinal lines between them
    fluke                          - an outline curve plus veins fanned from the tail tip (a flat
                                     sheet has no rings; extracting a "shell" from it would fill it)
    arms                           - one line each, shoulder -> elbow -> hand
    hair                           - long flowing lines off the crown, the cheapest, most
                                     recognisable thing a mermaid has

TRAPS (each from this repo's own history):
  - 6-CONNECTIVITY. Every curve is laid by `_line6`, one axis at a time, never as diagonal
    neighbours. The audit demands one connected piece.
  - ORIENTATION. An end rod only reads as a line if it points ALONG it; each cell is faced along the
    axis it has the most neighbours on. A rod whose neighbours are all above and below faces up.
  - INTEGER centres; offsets are added to them (round() is banker's rounding).
  - Everything is a fraction of the figure's own height so `height` is the only knob.
"""
from __future__ import annotations

import math

import numpy as np

from .canvas import Canvas, hash01

MERMAID = {
    "seed": 5,
    "height": 44,                 # crown to the fluke's lowest point, in blocks
    "at": None,                   # world cell of canvas corner (0,0,0)
    "root": None,                 # ...or the world cell of the fluke's lowest rod
    "ring_every": 3,              # a contour ring this often up the body
    "ribs": 8,                    # longitudinal lines round the torso/tail
    "hair": 7,                    # flowing strands
    "sway": 0.10,                 # sideways S-curve of the tail, as a fraction of height
    "rod": "end_rod",
}

_AXES = {"x": ("east", (1, 0, 0)), "y": ("up", (0, 1, 0)), "z": ("south", (0, 0, 1))}


def _line6(a, b):
    """Cells of a 6-connected line a -> b (inclusive): one axis step at a time, the axis whose
    remaining fraction is largest going first, so it stays close to the straight segment."""
    cur = [int(round(v)) for v in a]
    end = [int(round(v)) for v in b]
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


def _poly(pts):
    cells = []
    for i in range(len(pts) - 1):
        seg = _line6(pts[i], pts[i + 1])
        cells.extend(seg if not cells else seg[1:])
    return cells


def _smooth(ctrl, n):
    """Catmull-Rom through ctrl (3D), n samples per span. Soft curves from a few clear points."""
    P = [ctrl[0]] + list(ctrl) + [ctrl[-1]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = (np.array(P[j], float) for j in (i - 1, i, i + 1, i + 2))
        for k in range(n):
            t = k / n
            out.append(tuple(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                                     + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3)))
    out.append(tuple(P[-2]))
    return out


def build(cfg: dict, donors=None) -> Canvas:
    p = {**MERMAID, **(cfg or {})}
    H = float(p["height"])
    ring_every = max(2, int(p["ring_every"]))
    nrib = max(4, int(p["ribs"]))
    seed = int(p["seed"])
    sway = float(p["sway"]) * H

    pad = 3
    half = int(math.ceil(H * 0.22)) + pad          # the fluke and hair set the width
    XC = ZC = half
    SX = SZ = 2 * half + 1
    SY = int(H) + 2 * pad
    base = pad                                      # y of the fluke's lowest rod
    c = Canvas(SX, SY, SZ, donors)

    def Y(f):                                       # fraction of height -> canvas y
        return base + f * H

    # ---- the spine of the body: (height fraction) -> (x offset, z offset). Facing +z, so the S is
    # in x (side to side) with a slight forward arch of the bust and a backward sweep of the tail.
    def spine(f):
        t = 1.0 - f                                  # 0 at crown, 1 at fluke
        low = max(0.0, (0.66 - f) / 0.66)            # 0 above the hips, 1 at the tail tip
        x = sway * math.sin(low * math.pi * 1.25) * low ** 0.5
        z = -0.06 * H * low ** 1.6 + 0.012 * H * math.sin(t * 6)
        return x, z

    # ---- the stations: height fraction, half-width (x), half-depth (z). Reads head-down.
    ST = [
        (0.985, 0.4, 0.4),      # crown
        (0.95, 2.1, 2.3),       # brow / skull
        (0.915, 2.2, 2.4),      # cheek
        (0.885, 1.9, 2.0),      # jaw
        (0.86, 0.95, 0.95),     # neck
        (0.83, 3.2, 1.9),       # shoulders
        (0.79, 3.0, 2.3),       # bust
        (0.745, 2.4, 1.8),      # ribcage
        (0.70, 2.0, 1.6),       # waist
        (0.655, 2.7, 2.1),      # hips
        (0.58, 2.5, 1.9),       # thigh-tail
        (0.46, 2.0, 1.5),
        (0.34, 1.5, 1.15),
        (0.23, 1.0, 0.8),
        (0.15, 0.6, 0.5),       # tail root of the fluke
    ]
    k = H / 44.0
    ST = [(f, a * k, b * k) for f, a, b in ST]

    def station(f):
        """Interpolated half-widths at height fraction f (stations run top -> bottom)."""
        for i in range(len(ST) - 1):
            f0, a0, b0 = ST[i]
            f1, a1, b1 = ST[i + 1]
            if f1 <= f <= f0:
                u = (f0 - f) / (f0 - f1)
                u = u * u * (3 - 2 * u)
                return a0 + (a1 - a0) * u, b0 + (b1 - b0) * u
        return ST[-1][1], ST[-1][2]

    cells: set = set()

    def add(seq):
        for q in seq:
            cells.add(q)

    ytop, ybot = int(Y(0.985)), int(Y(0.15))
    # ---- RIBS: nrib longitudinal lines, one point per course, bridged so they stay connected.
    angles = [2 * math.pi * i / nrib + math.pi / nrib for i in range(nrib)]
    for ang in angles:
        pts = []
        for y in range(ybot, ytop + 1):
            f = (y - base) / H
            a, b = station(f)
            sx, sz = spine(f)
            pts.append((XC + sx + a * math.cos(ang), y, ZC + sz + b * math.sin(ang)))
        add(_poly(pts))
    # ---- RINGS: a closed contour every ring_every courses, plus the extremes.
    ring_ys = list(range(ybot, ytop + 1, ring_every))
    for y in ring_ys + [ytop - 1]:
        f = (y - base) / H
        a, b = station(f)
        if a < 0.6 or b < 0.6:
            continue
        sx, sz = spine(f)
        n = max(12, int(2 * math.pi * max(a, b) * 2))
        pts = [(XC + sx + a * math.cos(2 * math.pi * i / n),
                y, ZC + sz + b * math.sin(2 * math.pi * i / n)) for i in range(n + 1)]
        add(_poly(pts))

    # ---- the BUST: two small rings on the front of the chest (the shell top, drawn in light).
    fb = 0.79
    a, b = station(fb)
    sx, sz = spine(fb)
    for side in (-1, 1):
        cx, cy, cz = XC + sx + side * a * 0.45, Y(fb), ZC + sz + b * 0.85
        n = 10
        add(_poly([(cx + 1.2 * k * math.cos(2 * math.pi * i / n), cy + 1.2 * k * math.sin(2 * math.pi * i / n), cz)
                   for i in range(n + 1)]))

    # ---- the FLUKE: outline + veins, in the x-y plane at the tail's own z.
    fx, fz = spine(0.15)
    fx, fz = XC + fx, ZC + fz
    y_tip = Y(0.15)
    span = H * 0.17
    out_pts = [
        (fx, y_tip, fz),
        (fx + span * 0.35, Y(0.10), fz),
        (fx + span * 0.80, Y(0.045), fz),
        (fx + span * 1.00, Y(0.0), fz),          # the lobe's tip
        (fx + span * 0.62, Y(0.025), fz),
        (fx + span * 0.22, Y(0.04), fz),         # the notch
        (fx, Y(0.05), fz),
        (fx - span * 0.22, Y(0.04), fz),
        (fx - span * 0.62, Y(0.025), fz),
        (fx - span * 1.00, Y(0.0), fz),
        (fx - span * 0.80, Y(0.045), fz),
        (fx - span * 0.35, Y(0.10), fz),
        (fx, y_tip, fz),
    ]
    add(_poly(_smooth(out_pts, 4)))
    for u in (-0.75, -0.4, 0.0, 0.4, 0.75):
        add(_line6((fx, y_tip, fz), (fx + u * span * 1.0, Y(0.02 + 0.02 * (1 - abs(u))), fz)))
    # the tail's own spine, continuous into the fluke
    add(_line6((fx, y_tip, fz), (fx, Y(0.05), fz)))

    # ---- ARMS: shoulder -> elbow -> hand. One waves, one rests.
    sh = 0.83
    a, b = station(sh)
    sx, sz = spine(sh)
    sy = Y(sh) - 0.5
    arm_r = [(XC + sx + a, sy, ZC + sz), (XC + sx + a + 3.5 * k, sy - 4 * k, ZC + sz + 1.5 * k),
             (XC + sx + a + 6.0 * k, sy + 1 * k, ZC + sz + 3.0 * k), (XC + sx + a + 6.5 * k, sy + 4.5 * k, ZC + sz + 3.0 * k)]
    arm_l = [(XC + sx - a, sy, ZC + sz), (XC + sx - a - 2.0 * k, sy - 5 * k, ZC + sz + 1.5 * k),
             (XC + sx - a - 1.5 * k, sy - 10 * k, ZC + sz + 3.5 * k), (XC + sx - a - 0.5 * k, sy - 13 * k, ZC + sz + 5.0 * k)]
    for arm in (arm_r, arm_l):
        add(_poly(_smooth(arm, 5)))
    # fingers of the raised hand: three short lines
    hx, hy, hz = arm_r[-1]
    for dx in (-1, 0, 1):
        add(_line6((hx, hy, hz), (hx + dx * 1.5 * k, hy + 2.5 * k, hz)))

    # ---- HAIR: long strands off the skull, down the back, waving out and in.
    crown = Y(0.975)
    for i in range(int(p["hair"])):
        t = (i + 0.5) / int(p["hair"])               # 0..1 across the head
        ang = math.pi * (0.15 + 0.7 * t)             # from the +x ear round the back to the -x ear
        ang = math.pi + (t - 0.5) * math.pi * 1.5    # centred on straight back (-z)
        r0 = 2.2 * k
        sx0, sz0 = spine(0.975)
        start = (XC + sx0 + 1.6 * k * math.cos(ang) * 0.8, crown - 0.5, ZC + sz0 + r0 * math.sin(ang) * 1.0)
        length = H * (0.36 + 0.14 * hash01(seed, i, 1))
        ph = hash01(seed, i, 2) * 6.28
        ctrl = [start]
        for j in range(1, 7):
            f = j / 6
            ctrl.append((start[0] + math.cos(ang) * (0.6 + 2.2 * f) * k + math.sin(f * 5 + ph) * 1.3 * k,
                         start[1] - length * f,
                         start[2] - (1.5 + 4.5 * f) * k + math.sin(ang) * 0.8 * k))
        add(_poly(_smooth(ctrl, 4)))

    # ---- write the rods. Orient each along the axis it has the most neighbours on.
    rod = c.state(p["rod"], facing="up")
    n = 0
    counts = {"rods": 0}
    for (x, y, z) in cells:
        if not c.inb(x, y, z):
            continue
        votes = {"x": 0, "y": 0, "z": 0}
        for ax, (_, d) in _AXES.items():
            for s in (1, -1):
                if (x + s * d[0], y + s * d[1], z + s * d[2]) in cells:
                    votes[ax] += 1
        ax = max(votes, key=lambda a_: (votes[a_], a_ == "y"))
        face = _AXES[ax][0]
        if face == "up" and False:
            pass
        c.ids[y, z, x] = c.state(p["rod"], facing=face)
        n += 1
    counts["rods"] = n

    if p.get("at"):
        c.world_origin = tuple(int(v) for v in p["at"])
    elif p.get("root"):
        wx, wy, wz = (int(v) for v in p["root"])
        c.world_origin = (wx - int(round(fx)), wy - int(round(Y(0.0))), wz - int(round(fz)))
    c.meta = {"kind": "mermaid", "height": H, "facing": [0, 1], "features_built": counts}
    return c
