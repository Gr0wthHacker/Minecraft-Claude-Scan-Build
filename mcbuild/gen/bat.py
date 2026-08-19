"""A bat hanging from the cave ceiling. Membrane wings on finger struts - all plane, no volume.

    bat: hangs head-down from a roof, wings half-furled, membrane stretched between splayed fingers.

Same argument as `heron.py`. What this medium renders perfectly is PLANAR form, and a bat's wing is
the purest plane in nature: a single membrane one block thick, stretched between four finger bones
that are themselves straight tapers. There is no muscle to describe anywhere - the body is a small
furred lump and everything else is strut and skin.

It also uses a surface nothing else on this island touches. The lowland is ROOFED - 4,193 of its
columns sit under the plate and 1,504 under the void isle, and only 154 are open to the sky - so
there is a ceiling overhead everywhere you stand and not one thing hanging from it. A bat is the
animal that belongs there, and hanging it inverted costs nothing: `y` counts DOWN from the roof.

The wing membrane is drawn as a filled polygon between the struts rather than as swept spheres,
because a sphere sweep gives a rope and a membrane is a sheet. That is the whole difference.
"""
from __future__ import annotations

import numpy as np

from .canvas import Canvas, hash01

BAT = {
    "size": [56, 40, 22],
    "seed": 0,
    "scale": 1.0,
    # world coordinate of the canvas corner. A bespoke generator has to state this
    # itself - `World.canvas()` does it for the parametric ones - or the pipeline
    # writes no sidecar, and without a sidecar there is no origin, no in-context
    # audit and no `/cscan place`. The gecko still has this gap.
    "at": None,
    # ...or give `hang`, the world block its claws grip. A bat is placed by the ceiling it
    # holds on to, not by the corner of its box.
    "hang": None,
    # A PERCH: its own small floating rock, so the bat does not need a ceiling to exist under. It
    # can then hang in open air anywhere - which is the only way to put one in the gap between two
    # island lobes, where there is nothing overhead to grip.
    "perch": False,
    "perch_h": 8,                # courses of rock above the claws
    "perch_r": 7.0,              # its radius, in the design's own units
    "rock": ["stone", "cobblestone", "deepslate", "mossy_cobblestone"],
    "moss": "moss_block",
    "vine": "vine",
    "spread": 0.75,              # 0 = furled tight, 1 = wings fully out
    # dark, and deliberately NOT made of the ceiling it hangs from: the lowland's roof is stone,
    # cobble, deepslate and moss, so a bat in those would vanish the way the elephant did.
    # ALL CHEAP TIER. The membrane was `brown_terracotta` and its edge `black_terracotta`, which is
    # 290 blocks of clay on a skyblock for a brown that `brown_wool` gives for a dye. A LIGHTER
    # membrane against dark fur is also what a bat actually looks like: the wing is thin skin and
    # the body is fur, and they should not be the same tone.
    "fur": "dark_oak_wood",
    "fur_dark": "black_wool",
    "skin": "brown_wool",        # the membrane
    "skin_edge": "black_wool",
    "strut": "dark_oak_planks",  # finger bones
    "eye": "orange_wool",
    "claw": "bone_block",
}


def _membrane(c: Canvas, a, b, d, blk, steps=44, sag=0.15):
    """Fill the sheet between two struts, with the trailing edge SCALLOPED rather than straight.

    A sweep of spheres would give a rope; a membrane is one block thick and flat, so it is drawn as
    a fan of thin lines from the wrist anchor out to each point along the trailing edge.

    `sag` bows that edge back toward the anchor between the two finger tips. Straight edges made the
    wing a rectangle with struts drawn on it - the scallop between the fingers is the single thing
    that says "bat" rather than "kite", and it costs one lerp.
    """
    a, b, d = (np.array(q, float) for q in (a, b, d))
    for i in range(steps):
        t = i / max(1, steps - 1)
        edge = a + (b - a) * t
        edge = edge + (d - edge) * (sag * 4.0 * t * (1.0 - t))     # 0 at each tip, most mid-span
        c.line(tuple(d), tuple(edge), 0.5, blk)


def _stick(c: Canvas, x, y, z, blk) -> bool:
    """Place a single cell ONLY where it has something to hold on to.

    Every detached-feature bug in this repo is the same mistake: a detail placed at a COMPUTED
    position rather than against the surface that was actually built. The eyes and claw tips here
    were floating one cell clear of a curved head, which put the design in four pieces and would
    have failed the `single_component` gate outright.
    """
    x, y, z = int(round(x)), int(round(y)), int(round(z))
    if c.get(x, y, z):
        c.put(x, y, z, blk)
        return True
    for dx, dy, dz in ((0, 1, 0), (0, -1, 0), (1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1)):
        if c.get(x + dx, y + dy, z + dz):
            c.put(x, y, z, blk)
            return True
    return False


def build_bat(cfg: dict, donors=None) -> Canvas:
    p = {**BAT, **cfg}
    sc = float(p.get("scale", 1.0))
    SX, SY, SZ = (max(8, int(round(v * sc))) for v in p["size"])
    seed, spread = int(p["seed"]), float(p["spread"])
    c = Canvas(SX, SY, SZ, donors)
    st = c.state
    S = {k: st(p[k]) for k in ("fur", "fur_dark", "skin", "skin_edge", "strut", "eye", "claw")}
    cx, cz = SX / 2.0, SZ / 2.0
    u = sc
    perch = bool(p.get("perch"))
    ph = int(round(float(p["perch_h"]) * sc)) if perch else 0
    roof = SY - 1 - ph                                # y counts DOWN from here: the bat hangs

    # ---- THE PERCH. A ragged lump of the island's own rock, wider than it is deep and thickest in
    # the middle, with moss on top and a couple of vines off the rim - so it reads as a piece that
    # broke off the plate rather than as a sphere someone parked there.
    if perch:
        h0 = lambda *a: hash01(*a, seed)
        rock = [st(b) for b in p["rock"]]
        moss, vine = st(p["moss"]), st(p["vine"])
        pr = float(p["perch_r"]) * sc
        for k in range(ph + 1):
            f_ = k / max(1, ph)                       # 0 at the bat's grip, 1 at the top
            r = pr * (0.45 + 0.75 * f_ - 0.35 * f_ * f_)
            for dx in range(-int(r) - 2, int(r) + 3):
                for dz in range(-int(r) - 2, int(r) + 3):
                    d = (dx * dx + dz * dz) ** 0.5
                    # ragged, but not SO ragged that the edge sheds islands - the noise is
                    # smoothed along k so a column cannot appear with nothing under it
                    if d > r * (0.86 + 0.18 * h0(dx, 0, dz, 5)):
                        continue
                    y = roof + k
                    blk = moss if k == ph else rock[int(h0(dx, k, dz, 9) * len(rock)) % len(rock)]
                    c.put(int(round(cx + dx)), int(y), int(round(cz + dz)), blk)
        # vines off the rim. A vine hangs from the block ABOVE it, so each strand starts only
        # where there is rock to hang from and stops the moment the run breaks - placed blind they
        # came away as nine separate floating threads.
        for j in range(max(3, int(round(6 * sc)))):
            a = h0(j, 1, 2, 13) * 6.283
            rx = int(round(cx + pr * 0.82 * np.cos(a)))
            rz = int(round(cz + pr * 0.82 * np.sin(a)))
            if not c.get(rx, roof, rz):
                continue                              # nothing to hang from here
            for k in range(1, 2 + int(6 * h0(j, 3, 4, 17))):
                if not c.get(rx, roof - k + 1, rz):
                    break
                c.put(rx, roof - k, rz, vine)

    # ---- FEET, gripping the roof. Two hooked claws, which is the detail that says "hanging"
    # rather than "falling" - without them the whole thing reads as a bat mid-air, upside down.
    for side in (-1, 1):
        fx = cx + side * 1.6 * u
        c.line((fx, roof, cz), (fx, roof - 3.0 * u, cz + 0.4 * u), 0.85 * u, S["fur_dark"])
        for k in (-1, 0, 1):
            c.line((fx, roof, cz + k * 0.9 * u),
                   (fx + side * 0.8 * u, roof - 1.4 * u, cz + k * 1.5 * u), 0.62 * u, S["claw"])

    # ---- BODY: a small lump, head DOWNWARD. Everything about a bat is wing; the body is the least
    # of it and must not be allowed to become a barrel.
    body_y = roof - 8.0 * u
    c.ellipsoid(cx, body_y, cz, 2.6 * u, 5.0 * u, 2.4 * u, S["fur"])
    head_y = body_y - 5.5 * u
    c.ellipsoid(cx, head_y, cz + 0.3 * u, 2.1 * u, 2.2 * u, 2.0 * u, S["fur"])
    for side in (-1, 1):                              # ears: upright planar fans, big, the way a
        ex = cx + side * 1.5 * u                      # bat's really are - and they point DOWN here
        c.line((ex, head_y + 0.5 * u, cz), (ex + side * 1.6 * u, head_y - 4.2 * u, cz - 0.4 * u),
               0.75 * u, S["fur"])
        c.line((ex + side * 0.3 * u, head_y - 0.4 * u, cz),
               (ex + side * 2.4 * u, head_y - 3.4 * u, cz - 0.3 * u), 0.5 * u, S["fur_dark"])
    for side in (-1, 1):
        _stick(c, cx + side * 1.2 * u, head_y - 1.4 * u, cz + 1.9 * u, S["eye"])

    # ---- WINGS. Arm out to the wrist, then four finger struts fanning back, with the membrane
    # filled between consecutive fingers. `spread` swings the whole fan outward.
    shoulder = (cx, body_y - 2.0 * u, cz - 0.2 * u)
    fingers = max(3, int(round(4 * sc)))
    for side in (-1, 1):
        out = (6.0 + 14.0 * spread) * u
        wrist = (cx + side * out, body_y - 5.0 * u, cz - 0.6 * u)
        c.line(shoulder, wrist, 1.15 * u, S["strut"])
        tips = []
        for i in range(fingers + 1):
            t = i / fingers
            # the fan: first finger forward and short, last one back along the body and long
            # SWEEP the fan hard: the first finger reaches far out and slightly up to make a real
            # WINGTIP, the last folds back in along the body. Fanning them all to a similar reach
            # gave a rectangle with struts drawn on it - square outer corners and no point.
            tip = (wrist[0] + side * (11.5 - 9.5 * t) * u * (0.45 + 0.75 * spread),
                   wrist[1] + (-1.0 + 13.5 * t) * u,
                   wrist[2] - (0.8 - 1.6 * t) * u)
            tips.append(tip)
            c.line(wrist, tip, (0.62 - 0.12 * t) * u, S["strut"])
        for i in range(len(tips) - 1):                # the sheet between each pair of fingers
            _membrane(c, tips[i], tips[i + 1], wrist, S["skin"])
        for i in range(len(tips) - 1):                # the trailing edge, following the same scallop
            a_, b_ = np.array(tips[i], float), np.array(tips[i + 1], float)
            w_ = np.array(wrist, float)
            prev = None
            for k in range(13):
                tt = k / 12.0
                e = a_ + (b_ - a_) * tt
                e = e + (w_ - e) * (0.15 * 4.0 * tt * (1.0 - tt))
                if prev is not None:
                    c.line(tuple(prev), tuple(e), 0.5 * u, S["skin_edge"])
                prev = e
        # and the sheet from the last finger back to the ankle, which is what makes it a BAT wing
        # rather than a bird's - the membrane runs all the way to the leg
        c.line(tips[-1], (cx + side * 1.6 * u, roof - 3.0 * u, cz + 0.4 * u), 0.5 * u, S["skin_edge"])
        _membrane(c, tips[-1], (cx + side * 1.6 * u, roof - 3.0 * u, cz + 0.4 * u), wrist, S["skin"])

    # ---- a little tone in the membrane so it is not one flat sheet of terracotta
    h = lambda *a: hash01(*a, seed)
    for y in range(SY):
        for z in range(SZ):
            for x in range(SX):
                if c.get(x, y, z) == S["skin"] and h(x, y, z, 11) < 0.14:
                    c.put(x, y, z, S["skin_edge"])
    if p.get("hang"):
        hx_, hy_, hz_ = (float(v) for v in p["hang"])
        c.world_origin = (int(round(hx_ - cx)), int(round(hy_ - roof)), int(round(hz_ - cz)))
    elif p.get("at"):
        c.world_origin = tuple(int(v) for v in p["at"])
    # its head points at the FLOOR, so "facing" says nothing useful; the view that
    # matters is the one looking along z, straight at the spread wings
    c.meta = {"kind": "bat", "scale": sc, "spread": spread, "profile_view": "face",
                     "features_built": {"wings": 2, "fingers": fingers * 2, "ears": 2,
                                        "claws": 6, "eyes": 2}}
    return c
