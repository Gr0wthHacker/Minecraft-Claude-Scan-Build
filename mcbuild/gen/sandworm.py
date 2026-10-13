"""THE SANDWORM - something enormous breaking up through the paving of a round plaza.

**IT IS ONE CURVE, AND EVERYTHING ELSE IS READ OFF IT.** A worm is the one creature this medium
cannot get wrong for the reason the Rib Walk gives for a skeleton: no limbs, no haunch, no
compound muscle. It is a tube swept along a spine, a radius that changes with distance along that
spine, and a mouth. So the build is a single quartic Bezier through five control points, sampled
finely, and every cell of the animal is classified by its NEAREST SAMPLE: how far it is from the
spine, how far along the spine that sample is, and which way is "back". No part is placed at a
computed radius - the skin is wherever the classification says it is, and teeth, plates and fangs
are walked out from that same skin.

THE POSE IS A STRIKE, NOT A STAND. It comes up out of the ground, leans back into an S, and the
head hangs forward over the approach with the mouth opening toward whoever is walking in. Seen
from the arrival spine the open end is an ellipse with teeth round it and a red throat; seen from
the side it is the silhouette of something about to swallow the street.

    body     solid, segmented: a bulged ridge ring every `seg` blocks, two earth tones either side
    plates   a dorsal row of dark spines up the outside of the curve
    head     the tube swells and flares; the last metres are a HOLLOW shell with a lit throat
    teeth    inward rings (three, shrinking) and a few long fangs at the lip
    ground   rubble heaved up round the base, and cracks running out across the paving

THE BODY IS SOLID, THE HEAD IS NOT. A hollow body is a sealed dark room on a survival server, and
the audit counts it; the throat is open to the sky and lit by magma, so nothing spawns in it.

THE WALK STAYS A WALK. The plaza is 23 across and the worm's foot is 12, so a ring of paving
four wide is left round it, rubble is kept inside r8.7 and falls to nothing at the edge, and the
two roads that meet here come in on the ring. The head overhangs them thirty courses up.
"""
from __future__ import annotations

import math

import numpy as np

from mcbuild.gen import loft
from mcbuild.gen.canvas import Canvas, hash01

SANDWORM = {
    "kind": "sandworm",
    "centre": None,             # [world X, world Z] of the foot - required
    "plane_y": 202,             # the paving course
    "sink": 3,                  # courses of the foot carried BELOW the plane, so it is rooted
    "facing": "south",          # the way the head leans (toward whoever is arriving)
    "scale": 1.0,
    "seed": 0,
    # control points of the spine in (forward, up) from the foot, at scale 1. An S: straight up,
    # lean back, then over and out. The last segment sets the mouth's heading (forward and a
    # little UP, so the open end is visible from the ground and from the street).
    "spine": [[0, -4], [0, 20], [-13, 36], [7, 40], [24, 43]],
    # (t along the spine, radius) - the foot a little wide, a long even body, a thin neck, then
    # the head swelling and flaring to the lip.
    "radius": [[0.00, 6.6], [0.07, 6.0], [0.45, 5.7], [0.70, 5.2], [0.82, 6.6], [0.92, 8.8],
               [1.00, 10.4]],
    "seg": 4.6,                 # blocks of spine per body segment
    "ridge": 0.9,               # how far a ridge ring stands proud of the segment
    "throat_from": 0.80,        # t at which the body stops being solid and becomes a shell
    "shell": 2.6,               # skin thickness in the throat
    "plate_every": 3.4,
    "rubble": 8.7,              # outer radius of the heave, from the foot's axis
    "cracks": 9,
    "title": "SOMETHING BELOW",
}

HIDE = {
    "skin_a": "dripstone_block",
    "skin_b": "granite",
    "ridge": "smooth_basalt",
    "core": "cobblestone",
    "plate": "smooth_basalt",
    "lip": "smooth_basalt",
    "tooth": "bone_block",
    "gullet_a": "nether_wart_block",
    "gullet_b": "netherrack",
    "ember": "magma_block",
    "plug": "red_nether_bricks",
    "rub_a": "cracked_stone_bricks",
    "rub_b": "cobblestone",
    "rub_c": "stone_bricks",
    "rub_d": "mossy_stone_bricks",
    "crack": "tuff",
}


def _bezier(pts, n):
    """Points on a Bezier of any degree, by de Casteljau, as an (n+1, 2) array."""
    pts = np.asarray(pts, float)
    out = []
    for i in range(n + 1):
        t = i / n
        q = pts.copy()
        while len(q) > 1:
            q = q[:-1] * (1 - t) + q[1:] * t
        out.append(q[0])
    return np.array(out)


def _spine(p):
    """(P, T, N, arc, t): sample points, unit tangents, in-plane BACK normals, arc length, t."""
    sc = float(p["scale"])
    ctrl = [[a * sc, b * sc] for a, b in p["spine"]]
    P = _bezier(ctrl, 600)
    seg = np.diff(P, axis=0)
    arc = np.concatenate([[0.0], np.cumsum(np.hypot(seg[:, 0], seg[:, 1]))])
    # resample at even arc length so the radius profile and the segments are even along it
    L = arc[-1]
    n = int(L * 2.0)
    s = np.linspace(0, L, n + 1)
    f = np.interp(s, arc, P[:, 0])
    y = np.interp(s, arc, P[:, 1])
    P = np.stack([f, y], axis=1)
    T = np.gradient(P, axis=0)
    T /= np.maximum(1e-9, np.hypot(T[:, 0], T[:, 1]))[:, None]
    N = np.stack([-T[:, 1], T[:, 0]], axis=1)       # up -> back, forward -> up
    return P, T, N, s, s / L


def _radius(p, t, arc):
    keys = [(a, b * float(p["scale"])) for a, b in p["radius"]]
    base = np.array([loft.lerp(keys, float(x))[0] for x in t])
    seg = float(p["seg"]) * float(p["scale"])
    k = np.floor(arc / seg)
    frac = arc / seg - k
    ridge = float(p["ridge"]) * float(p["scale"]) * (frac < 0.24)
    ridge *= (t < 0.90)                               # the lip is its own thing
    return base, ridge, k.astype(int)


def build_sandworm(cfg: dict, donors=None) -> Canvas:
    p = {**SANDWORM, **(cfg or {})}
    if not p.get("centre"):
        raise ValueError("a sandworm needs `centre: [world X, world Z]` - the foot of the thing")
    facing = str(p["facing"])
    if facing not in loft.STEP:
        raise ValueError(f"a sandworm needs a real facing, not {facing!r}")
    sc = float(p["scale"])
    seed = int(p["seed"])
    sink = int(p["sink"])

    P, T, N, arc, t = _spine(p)
    R, bulge, seg_k = _radius(p, t, arc)
    n_s = len(P)
    rmax = float((R + bulge).max())

    # ---------------------------------------------------------------- the canvas
    pad = 5
    half = int(math.ceil(max(rmax + 8, 16 * sc))) + pad
    f_lo = int(math.floor(min(P[:, 0].min() - rmax, -(p["rubble"] + 7)))) - pad
    f_hi = int(math.ceil(P[:, 0].max() + rmax + 10)) + pad
    y_hi = int(math.ceil(P[:, 1].max() + rmax + 6)) + pad
    sx, sz, sy = 2 * half + 1, f_hi - f_lo + 1, y_hi + sink + 1
    along_x = facing in ("east", "west")
    if along_x:
        raise ValueError("a sandworm is built facing north or south; turn it with `facing`")
    c = Canvas(sx, sy, sz, donors)
    cv = half
    cu = -f_lo if facing == "south" else f_hi
    fr = loft.Frame(c, cv, cu, facing, HIDE)

    def yy(y):                      # plane-relative course -> canvas course
        return y + sink

    # ---------------------------------------------------------------- classify every cell
    # nearest spine sample per cell, in the (f, s, up) frame; the spine lies in the s = 0 plane
    fg = np.arange(f_lo, f_hi + 1, dtype=float)
    sg = np.arange(-half, half + 1, dtype=float)
    ug = np.arange(-sink, y_hi + 1, dtype=float)
    S, F, Y = np.meshgrid(sg, fg, ug, indexing="ij")       # (s, f, up)
    best = np.full(S.shape, 1e18)
    idx = np.zeros(S.shape, dtype=int)
    for i in range(n_s):
        d2 = (F - P[i, 0]) ** 2 + (Y - P[i, 1]) ** 2 + S ** 2
        m = d2 < best
        best[m] = d2[m]
        idx[m] = i
    dist = np.sqrt(best)
    # signed distance along the axis at the nearest sample, so the two open ends are CUT FLAT
    a_along = ((F - P[idx, 0]) * T[idx, 0] + (Y - P[idx, 1]) * T[idx, 1])
    tt = t[idx]
    Rr = R[idx] + bulge[idx]
    in_tube = (dist <= Rr)
    in_tube &= ~((idx == n_s - 1) & (a_along > 0.4))
    in_tube &= ~((idx == 0) & (a_along < -0.4))
    # a cell on the near side of the foot is below the plane only as far as the sink
    th = float(p["shell"]) * sc
    throat = tt >= float(p["throat_from"])
    # the throat is a SHELL; the lip ring is thicker
    lip = tt >= 0.985
    th_here = np.where(lip, th + 1.4, th)
    hollow = throat & (dist < Rr - th_here)
    # the plug that closes the throat, a few courses thick, seated where the shell begins
    i_plug = int(float(p["throat_from"]) * (n_s - 1))
    plug = in_tube & (idx >= i_plug) & (idx < i_plug + 5) & (dist < Rr - th_here + 0.5)
    solid = in_tube & ~hollow

    parts: dict = {}
    seen = 0

    def _count(label):
        nonlocal seen
        now = int((np.asarray(c.ids) > 0).sum())
        parts[label] = now - seen
        seen = now

    # ---------------------------------------------------------------- the body
    ss, ff, uu = np.nonzero(solid)
    for a, b, d in zip(ss.tolist(), ff.tolist(), uu.tolist()):
        s_, f_, u_ = sg[a], fg[b], ug[d]
        i = int(idx[a, b, d])
        dd = float(dist[a, b, d])
        rr = float(Rr[a, b, d])
        key = None
        if plug[a, b, d]:
            key = "ember" if hash01(int(f_), int(u_), int(s_), 3, seed) < 0.20 else "plug"
        elif throat[a, b, d] and dd > rr - th_here[a, b, d] and dd < rr - th_here[a, b, d] + 1.15 \
                and not lip[a, b, d]:
            h = hash01(int(f_), int(u_), int(s_), 5, seed)
            key = "ember" if h < 0.07 else ("gullet_a" if h < 0.62 else "gullet_b")
        elif lip[a, b, d] and dist[a, b, d] > rr - th_here[a, b, d] + 1.15:
            key = "lip"
        elif dd >= rr - 1.45:                                 # the skin
            if bulge[i] > 0 and dd >= R[i] - 0.2:
                key = "ridge"
            else:
                odd = (seg_k[i] % 2) == 1
                key = "skin_a" if (odd != (hash01(int(f_), int(u_), int(s_), 9, seed) < 0.16)) \
                    else "skin_b"
        else:
            key = "core"
        fr.put(f_, s_, yy(u_), key)
    _count("body")

    # ---------------------------------------------------------------- the dorsal plates
    pe = float(p["plate_every"]) * sc
    k = 0
    for j in range(n_s):
        if not (0.10 <= t[j] <= 0.80):
            continue
        if int(arc[j] / pe) == k:
            continue
        k = int(arc[j] / pe)
        base = P[j] + N[j] * (R[j] + bulge[j] - 0.8)
        ln = (2.6 + 1.6 * math.sin(k * 0.9) ** 2) * sc
        tip = base + N[j] * ln - T[j] * 0.9 * sc
        for off in (-1, 0, 1):
            loft.sweep(fr, (base[0], off * 1.0, base[1]), (tip[0], off * 0.5, tip[1]),
                       1.0 if off == 0 else 0.6, 0.35, "plate")
    _count("plates")

    # ---------------------------------------------------------------- the teeth
    def _tooth(i, ang, rin, length, r0, r1, outward=0.0, key="tooth"):
        ca, sa = math.cos(ang), math.sin(ang)
        radial = np.array([N[i, 0] * ca, sa, N[i, 1] * ca])          # (f, s, up)
        axis = np.array([T[i, 0], 0.0, T[i, 1]])
        root = np.array([P[i, 0], 0.0, P[i, 1]]) + radial * rin
        d = -radial * (0.80 - outward) + axis * (0.62 + outward)
        d /= np.linalg.norm(d)
        tip = root + d * length
        loft.sweep(fr, tuple(root), tuple(tip), r0, r1, key)

    last = n_s - 1
    for ring, (back, n_t, ln, r0) in enumerate([(1, 16, 5.0, 1.0), (7, 11, 4.0, 0.9)]):
        i = last - int(back * 2 * sc)
        rin = float(R[i]) - float(p["shell"]) * sc + 0.4
        for q in range(n_t):
            ang = 2 * math.pi * (q + 0.5 * (ring % 2)) / n_t
            j = 0.78 + 0.44 * hash01(q, ring, 1, 2, seed)
            _tooth(i, ang, rin, ln * sc * j, r0 * sc, 0.35, key="tooth")
    # the fangs: long, at the lip, flared outward
    for q in range(6):
        ang = 2 * math.pi * (q + 0.5) / 6
        _tooth(last - 1, ang, float(R[last - 1]) - 1.0, 9.5 * sc, 1.6 * sc, 0.4, outward=0.34)
    _count("teeth")

    # ---------------------------------------------------------------- the ground
    # Everything here is at the plane or a few courses over it, round the foot's axis.
    rub = float(p["rubble"]) * sc
    foot_r = float(R[0])
    for f in range(int(-rub - 8), int(rub + 9)):
        for s in range(int(-rub - 8), int(rub + 9)):
            rho = math.hypot(f, s)
            if rho <= foot_r + 0.2 or rho > rub:
                continue
            h = hash01(f, s, 7, 11, seed)
            x = (rho - foot_r) / max(0.5, rub - foot_r)          # 0 at the skin, 1 at the edge
            hh = int(round(3.4 * (1.0 - x) ** 1.2 + (h - 0.5) * 1.6))
            hh = max(0, min(4, hh))
            key = ("rub_a", "rub_b", "rub_c", "rub_d")[int(hash01(f, s, 3, 5, seed) * 4) % 4]
            # the course AT the plane is always laid - it is what holds the heave to the foot
            fr.put(f, s, yy(0), key)
            for u in range(1, hh + 1):
                if u > 1 and hash01(f, s, u, 13, seed) < 0.30 * u / 4.0:
                    break                                       # ragged tops
                fr.put(f, s, yy(u), key)
    _count("rubble")

    # cracks: jagged 4-connected lines out from the heave across the paving
    nck = int(p["cracks"])
    for k in range(nck):
        ang = 2 * math.pi * (k + 0.5 * hash01(k, 1, 2, 3, seed)) / nck
        f, s = rub * math.cos(ang), rub * math.sin(ang)
        ln = 3 + int(5 * hash01(k, 4, 5, 6, seed))
        cf, cs = loft.r(f), loft.r(s)
        for step in range(ln):
            fr.put(cf, cs, yy(0), "crack")
            dx, dz = math.cos(ang), math.sin(ang)
            # one axis at a time, picking the axis the heading favours with a little noise
            w = abs(dx) / (abs(dx) + abs(dz) + 1e-9) + (hash01(k, step, 8, 9, seed) - 0.5) * 0.7
            if w > 0.5:
                cf += 1 if dx > 0 else -1
            else:
                cs += 1 if dz > 0 else -1
    _count("cracks")

    # ---------------------------------------------------------------- prune strays, seal pockets
    ids = np.asarray(c.ids)
    occ = ids > 0
    seen_c = np.zeros_like(occ)
    comps = []
    for start in zip(*np.nonzero(occ)):
        if seen_c[start]:
            continue
        stack, cells = [start], []
        seen_c[start] = True
        while stack:
            q = stack.pop()
            cells.append(q)
            for ax in range(3):
                for dlt in (-1, 1):
                    r_ = list(q)
                    r_[ax] += dlt
                    r_ = tuple(r_)
                    if 0 <= r_[0] < occ.shape[0] and 0 <= r_[1] < occ.shape[1] \
                            and 0 <= r_[2] < occ.shape[2] and occ[r_] and not seen_c[r_]:
                        seen_c[r_] = True
                        stack.append(r_)
        comps.append(cells)
    comps.sort(key=len, reverse=True)
    pruned = 0
    for cells in comps[1:]:
        for q in cells:
            c.ids[q] = 0
            pruned += 1
    parts["pruned"] = pruned

    # ---------------------------------------------------------------- the world
    cx, cz = (int(v) for v in p["centre"])
    # canvas (v, u) <-> world (x, z): v = cv - s, u = cu + f  =>  foot (f = s = 0) is (cv, cu)
    c.world_origin = (cx - cv, int(p["plane_y"]) - sink, cz - cu)
    c.meta = {
        "kind": "sandworm",
        "facing": facing,
        "foot": [cx, int(p["plane_y"]), cz],
        "height": round(float(P[:, 1].max() + R[int(np.argmax(P[:, 1]))]), 1),
        "length": round(float(arc[-1]), 1),
        "mouth_radius": round(float(R[-1]), 1),
        "refused": fr.refused,
        "clipped": fr.clipped,
        "parts": parts,
        "contract": (
            "a colossal worm rearing out of a round plaza: a solid segmented body on one curved "
            "spine, a hollow lit throat with three rings of teeth and six fangs, a dorsal row of "
            "plates, and the paving heaved and cracked round its foot. The walk round it stays."),
    }
    return c


build = build_sandworm
DEFAULTS = SANDWORM
