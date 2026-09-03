"""SIGNAL ZERO - the bottom of the Prism Well: what catches you, and what you came down for.

TWO JOBS, AND THE FIRST IS NOT NEGOTIABLE. A hundred-course parkour course hanging in open void
over a floating park has, without this, exactly one failure mode: you miss a jump and fall out
of the world. Every other safety rule in the old Prismworks brief - checkpoints, catches, a
restart path - is downstream of there being a floor at all.

ONE CATCH, NOT THREE, and that is a design decision rather than a saving. The plan began with a
catch annulus under each act so that a miss cost one act rather than the run; measured, three
annuli covering a fall zone this wide came to seventeen thousand cells. The same promise is kept
by catching every fall in ONE pool and putting the checkpoints on the way back UP - the return
column stops at each act - so a miss still costs one act, and a long fall into a lit pool is
better drama than a net eight courses under your feet.

WATER, NOT SLIME. Both cancel a fall outright, and slime is cheap now (Jack, 2026-09-03,
correcting the invented tier table). But slime is one course where water needs a bed under it,
and the bed IS the chamber's floor, which the design needs anyway - so water's real marginal
cost is the source blocks. A pool also reads as somewhere you have arrived and a green rubber
disc does not, and you can walk in one-deep water, so nobody has to swim to the lift.

THE POOL IS SIZED FROM THE COURSE, NOT CHOSEN. The descent runs r30 to r14 with the search
flexing four either way, so a fall can begin anywhere in r10..r34 and lands near enough below
where it started. Thirty-four of water with a dry apron outside covers that - a third of what
the first geometry needed, and the Well's START PIER is what bought the difference.

AND THE BELL, WHICH IS THE WHOLE PAYOFF AND HAS NO REDSTONE IN IT. A descent with nothing at the
bottom is a chore. A bell is cheap, is in 1.19, needs no circuit, cannot desynchronise, cannot
be griefed into a broken state - and it is AUDIBLE FROM THE GALLERY, so ringing it tells
everyone watching that somebody just finished. The alternative considered was a signal running a
hundred courses up the shaft to light the rim's mast ring, and it is deliberately NOT built: a
vertical transmitter that tall is its own machine with its own contract, and this repo cut two
finished casino games rather than ship one it could not judge by simulation.
"""
from __future__ import annotations

import math

from .canvas import Canvas, hash01
from .vertical import World

FLOOR = {
    "under": None,
    "centre": [97590, 80815],
    "y_floor": 95,              # the water course; the bed is one under it
    "keep_clear": 6,            # the return column's own footprint, which the Well owns
    "pool_r": 34,               # the catch: it must cover everywhere the course can drop from
    "apron": 4,                 # dry ring outside the water, so you walk out rather than swim
    "wall": 2,
    "wall_h": 7,
    "bed": "deepslate_bricks",
    "pool_edge": "waxed_copper_block",
    "apron_pave": "smooth_stone",
    "apron_alt": "stone",
    "wall_lo": "polished_blackstone_bricks",
    "wall_hi": "cobbled_deepslate",
    "trim": "waxed_copper_block",
    "rail": "deepslate_brick_wall",
    "light": "pearlescent_froglight",   # the run cools as it falls: warm at the rim, pale here
    "bell_at": 180,             # the entry axis, so the plinth faces the way the course arrives
    "weather": 0.24,
    "seed": 23,
}


def build_floor(cfg: dict, donors=None) -> Canvas:
    p = {**FLOOR, **cfg}
    w = World()
    cx, cz = int(p["centre"][0]), int(p["centre"][1])
    wy = int(p["y_floor"])
    keep = int(p["keep_clear"])
    pr, ap, wl = int(p["pool_r"]), int(p["apron"]), int(p["wall"])
    feats = {k: 0 for k in ("bed", "water", "apron", "wall", "light", "rail", "bell")}
    outer = pr + ap

    def r_of(x, z):
        return math.hypot(x - cx, z - cz)

    for x in range(cx - outer - wl - 1, cx + outer + wl + 2):
        for z in range(cz - outer - wl - 1, cz + outer + wl + 2):
            r = r_of(x, z)
            if r < keep - 0.5:
                continue                        # the Well owns the return column's footprint
            if r < outer + 0.5:
                # THE BED, which carries the whole floor: the pool and the apron both stand on it.
                w.put(x, wy - 1, z, p["bed"] if hash01(x, wy, z, p["seed"]) > p["weather"]
                      else p["wall_lo"])
                feats["bed"] += 1
                if r < pr - 0.5:
                    w.put(x, wy, z, "water")
                    feats["water"] += 1
                elif r < pr + 0.5:
                    w.put(x, wy, z, p["pool_edge"])      # the lip, so the pool has an edge
                    feats["apron"] += 1
                else:
                    mat = p["apron_pave"]
                    if hash01(x, wy, z, p["seed"], 5) < p["weather"]:
                        mat = p["apron_alt"]
                    w.put(x, wy, z, mat)
                    feats["apron"] += 1
            elif r < outer + wl + 0.5:
                # THE WALL is what makes this a room rather than a ledge: the floor hangs in open
                # void and its edge is a drop on every side, with nothing under it for 160 courses.
                for q in range(0, int(p["wall_h"])):
                    w.put(x, wy + q, z,
                          p["wall_hi"] if q >= int(p["wall_h"]) - 2 else p["wall_lo"])
                    feats["wall"] += 1
                w.put(x, wy - 1, z, p["wall_lo"])
                feats["wall"] += 1

    # the lamps, which are what make the pool read from a hundred courses up - the arrival has to
    # be visible from the gallery or nobody watching knows where a runner has got to
    n_lamp = max(12, int(2 * math.pi * (outer - 1) / 9))
    for i in range(n_lamp):
        a = math.radians(i * 360.0 / n_lamp)
        x = int(round(cx + (outer - 1) * math.cos(a)))
        z = int(round(cz + (outer - 1) * math.sin(a)))
        w.put(x, wy, z, p["light"])
        feats["light"] += 1
        # A CORNICE CAPS THE WALL, so it goes at the WALL's radius. Placed at the lamp ring's
        # own radius it sat one course above the APRON with nothing under it - twenty-five
        # floating cells, and the audit's component list only ever prints the largest six, so
        # it read as "5 strays" until they were counted by hand.
        wx = int(round(cx + (outer + wl - 1) * math.cos(a)))
        wz = int(round(cz + (outer + wl - 1) * math.sin(a)))
        w.put(wx, wy + int(p["wall_h"]), wz, p["trim"])
        feats["wall"] += 1

    # ---------------------------------------------------------------------- THE BELL
    a = math.radians(float(p["bell_at"]))
    ux, uz = math.cos(a), math.sin(a)
    tx, tz = -uz, ux
    bx = int(round(cx + (pr + 2) * ux))
    bz = int(round(cz + (pr + 2) * uz))
    for s in (-2, -1, 0, 1, 2):                             # the plinth: the bell stands on it
        for q in (0, 1):
            x = int(round(bx + tx * s - ux * q))
            z = int(round(bz + tz * s - uz * q))
            w.put(x, wy, z, p["trim"] if abs(s) == 2 else p["wall_hi"])
            feats["bell"] += 1
    for s in (-2, 2):                                       # two posts carrying a lintel
        for q in range(1, 4):
            w.put(int(round(bx + tx * s)), wy + q, int(round(bz + tz * s)), p["trim"])
            feats["bell"] += 1
    for s in (-2, -1, 0, 1, 2):
        w.put(int(round(bx + tx * s)), wy + 4, int(round(bz + tz * s)), p["trim"])
        feats["bell"] += 1
    # A BELL HANGS FROM THE BLOCK ABOVE IT, AND THAT BLOCK HAS TO BE REAL. The bat perch's vines
    # and the taproot entrance's lantern chains both shipped as loose links for want of a ceiling
    # to find; the lintel above is placed before this and is what it hangs on.
    w.put(bx, wy + 4, bz, p["trim"])
    w.put(bx, wy + 3, bz, "bell", facing="east", attachment="ceiling")
    w.put(bx, wy + 1, bz, p["light"])
    feats["bell"] += 2

    return w.canvas({"kind": "prismfloor", "profile_view": "top", "facing": [-1, 0],
                     "features_built": feats, "centre": [cx, cz], "y_floor": wy,
                     "pool_r": pr})
