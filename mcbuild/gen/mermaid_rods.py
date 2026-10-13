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
    "height": 120,                # crown to the fluke's lowest point, in blocks
    "at": None,                   # world cell of canvas corner (0,0,0)
    "root": None,                 # ...or the world cell of the fluke's lowest rod
    "ring_every": 6,              # a contour ring this often up the body
    "ribs": 8,                    # longitudinal lines round the torso/tail
    "hair": 28,                    # flowing strands
    "sway": 0.16,                 # sideways S-curve of the tail, as a fraction of height
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


def _components(cells):
    seen, comps = set(), []
    for c0 in cells:
        if c0 in seen:
            continue
        comp, stack = [], [c0]
        seen.add(c0)
        while stack:
            x, y, z = stack.pop()
            comp.append((x, y, z))
            for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
                q = (x + d[0], y + d[1], z + d[2])
                if q in cells and q not in seen:
                    seen.add(q)
                    stack.append(q)
        comps.append(comp)
    return comps


def _join(cells):
    """Bridge every stray piece to the biggest by the shortest 6-connected line. Surface detail
    (an eye, a scale row) sits a cell or two off the cage and would otherwise be its own piece."""
    for _ in range(200):
        comps = _components(cells)
        if len(comps) <= 1:
            return
        comps.sort(key=len, reverse=True)
        main = np.array(comps[0])
        comp = np.array(comps[1])
        d = ((comp[:, None, :] - main[None, :, :]) ** 2).sum(-1)
        i, j = np.unravel_index(int(d.argmin()), d.shape)
        for q in _line6(tuple(comp[i]), tuple(main[j])):
            cells.add(tuple(int(v) for v in q))


def build(cfg: dict, donors=None) -> Canvas:
    p = {**MERMAID, **(cfg or {})}
    H = float(p["height"])
    k = H / 44.0                                   # every block-sized number below is in 44-high units
    ring_every = max(3, int(p["ring_every"]))
    nrib = max(4, int(p["ribs"]))
    seed = int(p["seed"])
    sway = float(p["sway"]) * H

    pad = 3
    half = int(math.ceil(H * 0.30)) + pad
    XC = ZC = half
    SX = SZ = 2 * half + 1
    SY = int(H * 1.32) + 2 * pad
    base = pad
    c = Canvas(SX, SY, SZ, donors)

    def Y(f):
        return base + f * H

    def spine(f):
        t = 1.0 - f
        low = max(0.0, (0.66 - f) / 0.66)
        x = sway * math.sin(low * math.pi * 1.25) * low ** 0.5
        z = -0.06 * H * low ** 1.6 + 0.012 * H * math.sin(t * 6)
        return x, z

    # stations BELOW the head: height fraction, half-width x, half-depth z (44-high units)
    ST = [
        (0.845, 1.15, 1.1), (0.83, 3.2, 1.9), (0.79, 3.0, 2.3), (0.745, 2.4, 1.8), (0.70, 2.0, 1.6),
        (0.655, 2.7, 2.1), (0.58, 2.5, 1.9), (0.46, 2.0, 1.5), (0.34, 1.5, 1.15), (0.23, 1.0, 0.8),
        (0.15, 0.6, 0.5),
    ]
    ST = [(f, a * k, b * k) for f, a, b in ST]
    HC, HR = 0.920, 0.066                           # the head: an egg, centre and half-height (big: a face needs ~16 blocks)
    HS, SF = 1.40, 1.55                              # head width scale; face vertical stretch

    def hf(v):                                       # a face height written for the old small head -> this one
        return HC + (v - 0.934) * SF

    def station(f):
        if f >= HC - HR * 0.92:                              # HEAD, so the face is drawn on the SAME surface
            t = (f - HC) / HR
            e = math.sqrt(max(0.0, 1 - min(1.0, t * t)))
            tp = 1 - 0.20 * max(0.0, -t)
            return max(0.35 * k, 2.25 * HS * k * e * tp), max(0.35 * k, 2.45 * HS * k * e * tp)
        for i in range(len(ST) - 1):
            f0, a0, b0 = ST[i]
            f1, a1, b1 = ST[i + 1]
            if f1 <= f <= f0:
                u = (f0 - f) / (f0 - f1)
                u = u * u * (3 - 2 * u)
                return a0 + (a1 - a0) * u, b0 + (b1 - b0) * u
        return ST[-1][1], ST[-1][2]

    def surf(f, phi, out=0.0):
        a, b = station(f)
        sx, sz = spine(f)
        return (XC + sx + (a + out) * math.cos(phi), Y(f), ZC + sz + (b + out) * math.sin(phi))

    cells: set = set()
    counts = {"cage": 0, "face": 0, "scales": 0, "hair": 0, "arms": 0, "fins": 0, "trident": 0, "shell": 0}

    def add(seq, tag=None):
        n0 = len(cells)
        for q in seq:
            cells.add(tuple(int(v) for v in q))
        if tag:
            counts[tag] += len(cells) - n0

    def hcurve(pf):                                 # same, with heights written for the old head
        return _poly([surf(hf(f), ph, o) for ph, f, o in pf])

    def curve(pf):                                  # polyline through (phi, f, out) surface samples
        return _poly([surf(f, ph, o) for ph, f, o in pf])

    FRONT = math.pi / 2
    deg = math.radians
    f_tail_top, f_tail_end = 0.64, 0.15
    ybot, ytop = int(Y(f_tail_end)), int(Y(0.985))

    def face_zone(phi, f):
        d = abs(((phi - FRONT + math.pi) % (2 * math.pi)) - math.pi)
        return f > HC - HR * 0.9 and d < deg(58)

    # ---- CAGE. Ribs (not through the face) and rings; scalloped rings on the tail = scales.
    angles = [2 * math.pi * i / nrib + math.pi / nrib for i in range(nrib)]
    for ang in angles:
        pts, run = [], []
        for y in range(ybot, ytop + 1):
            f = (y - base) / H
            if face_zone(ang, f) or (f > HC - HR * 0.92 and abs(math.sin(ang)) > 0.55):
                if len(run) > 1:
                    add(_poly(run), "cage")
                run = []
                continue
            run.append(surf(f, ang))
        if len(run) > 1:
            add(_poly(run), "cage")

    def ring(y0, phase=0.0, scallop=0, depth=0.0, tag="cage"):
        f0 = (y0 - base) / H
        a, b = station(f0)
        if a < 0.8 or b < 0.8:
            return
        n = max(16, int(2 * math.pi * max(a, b) * 3))
        run = []
        for i in range(n + 1):
            ph = 2 * math.pi * i / n
            yy = y0 - (depth * abs(math.sin(scallop * ph / 2 + phase)) if scallop else 0)
            f = (yy - base) / H
            dfront = abs(((ph - FRONT + math.pi) % (2 * math.pi)) - math.pi)
            if face_zone(ph, f) or (f > HC - HR * 0.92 and dfront < deg(120)):
                if len(run) > 1:
                    add(_poly(run), tag)
                run = []
                continue
            run.append(surf(f, ph)[:1] + (yy,) + surf(f, ph)[2:])
        if len(run) > 1:
            add(_poly(run), tag)

    row = 0
    y = ybot
    while y <= ytop:
        f = (y - base) / H
        if f_tail_end + 0.01 < f < f_tail_top:       # THE TAIL: scale rows, alternating phase
            a, b = station(f)
            ns = max(6, int(round(2 * math.pi * (a + b) / 2 / (2.4 * k ** 0.5 * 1.3))))
            ring(y + 2, phase=(math.pi / 2 if row % 2 else 0.0), scallop=ns, depth=2.0 * (k / 2.7) ** 0.5 + 0.6,
                 tag="scales")
            row += 1
            y += max(3, int(round(0.036 * H)))
        else:
            ring(y)
            y += ring_every

    # ---- THE FACE, drawn on the head's own surface (phi, f, out). Everything symmetric about FRONT.
    for sd in (-1, 1):
        cx = FRONT + sd * deg(25)
        # eye: almond outline, lid line above, brow arc over that
        eye = [(cx + sd * deg(a_ * 1.5), fz, 0.5) for a_, fz in
               ((-8, 0.9475), (-4, 0.9525), (1, 0.9535), (5, 0.9515), (8, 0.9465), (4, 0.9435), (-1, 0.9435), (-5, 0.9445), (-8, 0.9475))]
        add(hcurve(eye), "face")
        add(hcurve([(cx + sd * deg(a_ * 1.5), fz, 0.5) for a_, fz in ((-9, 0.9575), (-3, 0.9625), (4, 0.9625), (10, 0.9570))]), "face")
        add(hcurve([(cx + sd * deg(a_ * 1.5), fz, 0.5) for a_, fz in ((-10, 0.9665), (0, 0.9715), (11, 0.9680), (17, 0.9610))]), "face")
        # iris: a short vertical stroke so the eye is not blank
        add(hcurve([(cx + sd * deg(0), 0.9535, 0.8), (cx + sd * deg(0), 0.9440, 0.8)]), "face")
        # ear
        add(hcurve([(sd * deg(90) + FRONT - sd * deg(90) * 0 + (0 if sd > 0 else 0) + sd * deg(0), 0, 0)][:0]) if False else [], "face")
    # nose: bridge, tip, nostrils
    add(hcurve([(FRONT, 0.9535, 0.4), (FRONT, 0.9400, 0.9), (FRONT, 0.9300, 1.3)]), "face")
    add(hcurve([(FRONT - deg(7), 0.9285, 0.9), (FRONT - deg(3), 0.9255, 1.0), (FRONT + deg(3), 0.9255, 1.0), (FRONT + deg(7), 0.9285, 0.9)]), "face")
    # lips: upper with a cupid's bow, lower fuller, and the mouth line between
    add(hcurve([(FRONT + deg(a_ * 1.35), fz, 0.6) for a_, fz in
               ((-13, 0.9090), (-7, 0.9120), (-3, 0.9145), (0, 0.9120), (3, 0.9145), (7, 0.9120), (13, 0.9090))]), "face")
    add(hcurve([(FRONT + deg(a_ * 1.35), fz, 0.6) for a_, fz in
               ((-13, 0.9090), (-7, 0.9070), (0, 0.9065), (7, 0.9070), (13, 0.9090))]), "face")
    add(hcurve([(FRONT + deg(a_ * 1.35), fz, 0.6) for a_, fz in
               ((-11, 0.9060), (-5, 0.8995), (0, 0.8980), (5, 0.8995), (11, 0.9060))]), "face")
    # cheek and jaw contours
    for sd in (-1, 1):
        add(hcurve([(FRONT + sd * deg(a_ * 1.5), fz, 0.2) for a_, fz in ((38, 0.9300), (44, 0.9120), (38, 0.8950), (22, 0.8850))]), "face")

    # ---- TIARA: a band round the brow and five points, with a pearl-star at the centre.
    band = [(FRONT + deg(a_ * 1.35), 0.9705 + 0.002 * math.sin(a_ / 6.0), 0.9) for a_ in range(-112, 113, 4)]
    add(hcurve(band), "face")
    for a_ in (-60, -30, 0, 30, 60):
        h = 2.6 if a_ == 0 else 1.7
        x0, y0, z0 = surf(0.9705, FRONT + deg(a_ * 1.35), 0.9)
        add(_line6((x0, y0, z0), (x0, y0 + h * k * 0.9, z0 + 0.2 * k)), "face")
    # ---- NECKLACE collar + pendant down into the bust
    for a_ in range(0, 360, 6):
        pass
    add(_poly([surf(0.848, deg(a_), 0.5) for a_ in range(0, 361, 8)]), "face")
    add(curve([(FRONT - deg(70), 0.848, 0.5), (FRONT - deg(30), 0.826, 0.6), (FRONT, 0.806, 0.7),
               (FRONT + deg(30), 0.826, 0.6), (FRONT + deg(70), 0.848, 0.5)]), "face")

    # ---- SHELL TOP: two scallop shells - radiating ribs, a scalloped rim, a fan in a flat plane.
    for sd in (-1, 1):
        cxs, cys, czs = surf(0.790, FRONT + sd * deg(24), 0.7)
        R = 2.5 * k
        rim = []
        for i in range(0, 41):
            t = deg(15 + 150 * i / 40)
            rr = R * (1 + 0.10 * abs(math.sin(7 * t / 2)))
            rim.append((cxs + rr * math.cos(t), cys + 0.2 * k + rr * math.sin(t) * 0.9, czs))
        add(_poly(rim), "shell")
        for t_ in (25, 45, 65, 90, 115, 135, 155):
            tt = deg(t_)
            add(_line6((cxs, cys - 0.6 * k, czs), (cxs + R * math.cos(tt), cys + 0.2 * k + R * 0.95 * math.sin(tt), czs)), "shell")
        add(_poly([(cxs - R * 0.9, cys - 0.2 * k, czs), (cxs, cys - 0.8 * k, czs), (cxs + R * 0.9, cys - 0.2 * k, czs)]), "shell")
    # navel
    add(_poly([surf(0.69, FRONT + deg(a_), 0.4) for a_ in (-6, -2, 2, 6)]), "face")

    # ---- DORSAL FIN: a serrated crest down the back, hips to the tail.
    fd = 0.63
    while fd > 0.22:
        x0, y0, z0 = surf(fd, 3 * math.pi / 2)
        sp = (1.8 + 4.0 * (fd - 0.2)) * k * 0.7
        add(_poly([(x0, y0, z0), (x0, y0 - 0.5 * k, z0 - sp * 0.6), (x0, y0 - 2.4 * k, z0 - sp)]), "fins")
        fd -= 0.035
    add(curve([(3 * math.pi / 2, f_, 0.3) for f_ in (0.63, 0.56, 0.48, 0.40, 0.32, 0.24)]), "fins")
    # ---- HIP FINS: a flowing fan at each side of the hips
    for sd in (-1, 1):
        x0, y0, z0 = surf(0.625, 0 if sd > 0 else math.pi)
        edge = [(x0, y0, z0), (x0 + sd * 3.0 * k, y0 - 1.0 * k, z0 - 0.5 * k),
                (x0 + sd * 5.5 * k, y0 - 4.5 * k, z0 - 1.5 * k), (x0 + sd * 6.2 * k, y0 - 8.5 * k, z0 - 2.4 * k),
                (x0 + sd * 4.4 * k, y0 - 11 * k, z0 - 2.6 * k), (x0 + sd * 1.8 * k, y0 - 9.0 * k, z0 - 1.5 * k)]
        sm = _smooth(edge, 6)
        add(_poly(sm), "fins")
        for q in sm[8::5]:
            add(_line6((x0, y0 - 0.5 * k, z0), q), "fins")

    # ---- THE FLUKE: a big forked fin - two outlines, scalloped trailing edge, nine veins.
    fx, fz = spine(f_tail_end)
    fx, fz = XC + fx, ZC + fz
    y_tip = Y(f_tail_end)
    span = H * 0.20

    def fluke(sc):
        pts = [(0, 0.15), (0.30, 0.115), (0.62, 0.075), (0.86, 0.035), (1.0, 0.0), (0.84, 0.020), (0.66, 0.026),
               (0.46, 0.036), (0.22, 0.050), (0.0, 0.062)]
        right = [(fx + sc * span * u, Y(f_ + (1 - sc) * 0.05), fz) for u, f_ in pts]
        left = [(fx - sc * span * u, Y(f_ + (1 - sc) * 0.05), fz) for u, f_ in reversed(pts)]
        return right + left[1:] + [right[0]]

    add(_poly(_smooth(fluke(1.0), 5)), "fins")
    add(_poly(_smooth(fluke(0.74), 5)), "fins")
    for u in (-0.9, -0.7, -0.5, -0.3, -0.1, 0.1, 0.3, 0.5, 0.7, 0.9):
        tx = fx + u * span
        ty = Y(0.012 + 0.04 * (1 - abs(u)) ** 0.6)
        add(_line6((fx, y_tip, fz), (tx, ty, fz)), "fins")
    add(_line6((fx, y_tip, fz), (fx, Y(0.062), fz)), "fins")

    # ---- ARMS, as little cages (4 ribs + rings), a bracelet at the wrist and five fingers.
    def limb(ctrl, r0, r1, tag):
        sm = _smooth(ctrl, 6)
        n = len(sm)
        ribs = [[], [], [], []]
        for i, (px, py, pz) in enumerate(sm):
            r = r0 + (r1 - r0) * i / (n - 1)
            for j, (ox, oz) in enumerate(((1, 0), (0, 1), (-1, 0), (0, -1))):
                ribs[j].append((px + ox * r, py, pz + oz * r))
            if i % 4 == 0 and i > 0:
                add(_poly([(px + r * math.cos(t_), py, pz + r * math.sin(t_)) for t_ in
                           [2 * math.pi * q / 12 for q in range(13)]]), tag)
        for rb in ribs:
            add(_poly(rb), tag)
        return sm

    sh = 0.83
    a, b = station(sh)
    sx, sz = spine(sh)
    sy = Y(sh) - 0.5 * k
    arm_r = [(XC + sx + a, sy, ZC + sz), (XC + sx + a + 3.5 * k, sy - 4 * k, ZC + sz + 1.5 * k),
             (XC + sx + a + 6.0 * k, sy + 1 * k, ZC + sz + 3.0 * k), (XC + sx + a + 6.5 * k, sy + 4.5 * k, ZC + sz + 3.0 * k)]
    arm_l = [(XC + sx - a, sy, ZC + sz), (XC + sx - a - 2.0 * k, sy - 5 * k, ZC + sz + 1.5 * k),
             (XC + sx - a - 1.5 * k, sy - 10 * k, ZC + sz + 3.5 * k), (XC + sx - a - 0.5 * k, sy - 13 * k, ZC + sz + 5.0 * k)]
    hands = []
    for arm in (arm_r, arm_l):
        sm = limb(arm, 0.95 * k, 0.55 * k, "arms")
        hx, hy, hz = sm[-1]
        hands.append((hx, hy, hz, arm is arm_r))
        add(_poly([(hx + 0.9 * k * math.cos(2 * math.pi * q / 12), hy + 0.8 * k, hz + 0.9 * k * math.sin(2 * math.pi * q / 12))
                   for q in range(13)]), "arms")                     # bracelet
    for hx, hy, hz, raised in hands:
        sgn = 1 if raised else -1
        up = 1 if raised else -1
        add(_poly([(hx + 0.8 * k * math.cos(2 * math.pi * q / 10), hy + up * 0.9 * k, hz + 0.8 * k * math.sin(2 * math.pi * q / 10))
                   for q in range(11)]), "arms")                     # palm ring
        for fi, (dx, ln) in enumerate(((-0.8, 1.7), (-0.4, 2.3), (0.0, 2.5), (0.4, 2.2), (0.8, 1.6))):
            tipx = hx + dx * k * 0.9
            add(_line6((hx + dx * 0.6 * k, hy + up * 0.9 * k, hz), (tipx, hy + up * (0.9 + ln) * k, hz + (0.15 * k if not raised else 0))), "arms")
    # ---- THE TRIDENT, gripped in the raised hand.
    hx, hy, hz = hands[0][:3]
    ts, te = hy - 0.11 * H, hy + 0.20 * H
    add(_line6((hx, ts, hz), (hx, te, hz)), "trident")
    add(_poly([(hx + 0.7 * k * math.cos(2 * math.pi * q / 8), te - 1.0 * k, hz + 0.7 * k * math.sin(2 * math.pi * q / 8))
               for q in range(9)]), "trident")
    w = 0.036 * H
    prong = lambda x0, h0, h1: _line6((x0, te, hz), (x0, te + h0, hz)) + _line6((x0, te + h0, hz), (x0, te + h1, hz))
    add(_poly(_smooth([(hx, te, hz), (hx - w * 0.9, te + 0.2 * w, hz), (hx - w, te + 1.2 * w, hz)], 5)), "trident")
    add(_poly(_smooth([(hx, te, hz), (hx + w * 0.9, te + 0.2 * w, hz), (hx + w, te + 1.2 * w, hz)], 5)), "trident")
    add(_line6((hx - w, te + 1.2 * w, hz), (hx - w, te + 3.2 * w, hz)), "trident")
    add(_line6((hx + w, te + 1.2 * w, hz), (hx + w, te + 3.2 * w, hz)), "trident")
    add(_line6((hx, te, hz), (hx, te + 3.9 * w, hz)), "trident")
    for xx, yy0 in ((hx - w, te + 3.2 * w), (hx + w, te + 3.2 * w), (hx, te + 3.9 * w)):      # arrow barbs
        add(_poly([(xx - 0.55 * w, yy0 - 0.9 * w, hz), (xx, yy0, hz), (xx + 0.55 * w, yy0 - 0.9 * w, hz)]), "trident")

    # ---- HAIR: many long strands - behind the head and shoulders, with two front locks.
    nh = int(p["hair"])
    for i in range(nh):
        t = (i + 0.5) / nh
        cls = i % 5                                               # two curtains at the sides, a few at the back:
        if cls in (0, 1):                                         # nothing hangs behind the face, so it stays legible
            ang = FRONT + deg(72 + 62 * hash01(seed, i, 6))
        elif cls in (2, 3):
            ang = FRONT - deg(72 + 62 * hash01(seed, i, 6))
        else:
            ang = 3 * math.pi / 2 + deg(-28 + 56 * hash01(seed, i, 6))
        fstart = HC + HR * (0.30 + 0.62 * hash01(seed, i, 5))
        start = surf(fstart, ang, -0.4)
        length = H * (0.30 + 0.20 * hash01(seed, i, 1))
        ph = hash01(seed, i, 2) * 6.28
        amp = (1.2 + 1.4 * hash01(seed, i, 3)) * k
        ctrl = [start]
        for j in range(1, 10):
            f_ = j / 9
            side = math.cos(ang) if abs(math.cos(ang)) > 0.35 else (1 if i % 2 else -1) * 0.8
        ctrl.append((start[0] + side * (1.2 + 7.0 * f_ ** 0.8) * k + math.sin(f_ * 6 + ph) * amp * f_,
                         start[1] - length * f_,
                         start[2] - (1.2 + 5.2 * f_) * k + math.sin(ang) * 0.9 * k + math.cos(f_ * 5 + ph) * amp * 0.4 * f_))
        add(_poly(_smooth(ctrl, 4)), "hair")
    for sd in (-1, 1):
        st = surf(HC + 0.01, FRONT + sd * deg(78), 0.5)
        ctrl = [st]
        for j in range(1, 7):
            f_ = j / 6
            ctrl.append((st[0] + sd * (0.6 + 1.6 * math.sin(f_ * 3)) * k * 0.8, st[1] - 0.20 * H * f_,
                         st[2] + 1.0 * k + 1.8 * k * f_ + 0.6 * k * math.sin(f_ * 7)))
        add(_poly(_smooth(ctrl, 4)), "hair")

    _join(cells)

    # ---- write the rods, each faced along the axis it has the most neighbours on.
    n = 0
    for (x, y, z) in cells:
        if not c.inb(x, y, z):
            continue
        votes = {"x": 0, "y": 0, "z": 0}
        for ax, (_, d) in _AXES.items():
            for s_ in (1, -1):
                if (x + s_ * d[0], y + s_ * d[1], z + s_ * d[2]) in cells:
                    votes[ax] += 1
        ax = max(votes, key=lambda a_: (votes[a_], a_ == "y"))
        c.ids[y, z, x] = c.state(p["rod"], facing=_AXES[ax][0])
        n += 1
    counts["rods"] = n

    if p.get("at"):
        c.world_origin = tuple(int(v) for v in p["at"])
    elif p.get("root"):
        wx, wy, wz = (int(v) for v in p["root"])
        c.world_origin = (wx - int(round(fx)), wy - int(round(Y(0.0))), wz - int(round(fz)))
    c.meta = {"kind": "mermaid", "height": H, "facing": [0, 1], "features_built": counts}
    return c
