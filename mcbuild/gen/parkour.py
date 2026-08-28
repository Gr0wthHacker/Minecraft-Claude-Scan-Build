"""The Island Run - a parkour descent that winds around the island, plate to lowland.

THE FIRST VERSION WAS A STAIRCASE AND JACK SAID SO. It hopped 3x3 landings four blocks apart
with a two-course drop every time: no failure mode, no variety, no jump pads, nothing to learn.
A ramp with gaps in it is not parkour. What makes a descent a course is what makes any of them
one - a VOCABULARY of moves, in a rhythm, getting harder as it goes.

  LEDGE   a 1x1 landing, 3 to 4.5 blocks out and level or nearly so. The sprint jump is the
          whole game, and a ONE-BLOCK target is what makes it a jump instead of a walk.
  PLUNGE  a real fall of 8 to 16 courses onto a SLIME pad, which bounces you and cancels the
          damage. This is the jump pad, and it is what buys the height.
  GATE    a wall on the landing, so the jump has to clear something as well as reach it.
  REST    a 3x3 lit platform - checkpoints, and the only place the run lets go of you.

WHY PLUNGES RATHER THAN MORE HOPS. Steering a fall buys ~2.0 blocks of horizontal reach for a
two-course drop and ~5.0 for a thirteen-course one, while one turn of this island is ~270
blocks of travel and there are ~150 courses to spend. Descending entirely by little drops
spends all the height on distance and leaves every jump trivial - which is exactly what the
first build did. Spend most of the height in a handful of plunges and the ledges stay nearly
level, so they have to be JUMPED.

THE PLOT IS A SQUARE, AND IT IS FOUND RATHER THAN TYPED. `mcbuild.plot` locates the island's
bedrock and measures 49 out from it on each axis. The first build guarded against the CAPTURE
box instead - 103x103, two blocks wider on every side - and shipped 120 cells off the edge.

Slime cancels all fall damage when you land on it without sneaking, so every plunge is safe by
construction and no move on the run costs health.
"""
from __future__ import annotations

import math

from . import protect
from ..plot import find as find_plot
from .canvas import Canvas, hash01
from .vertical import Ctx, World

PARKOUR = {
    "under": None,
    "y_top": 194,
    "y_bottom": 44,
    "radius": 43,                # base orbit; the search flexes and the PLOT clamps it
    "radius_flex": [0, 3, -3, 6, -6, 9, -9, 12, -12, 15, -15],
    "advance": [5.0, 6.5, 8.0, 4.0, 9.5, 11.0, 3.0],

    "ledge_gap": [4.2, 3.6, 3.0, 4.5],    # sprint-jump distances
    "ledge_drop": [0, 1, 2],              # nearly level: the jump does the work
    "plunge_drop": [12, 14, 10, 16, 8],   # onto slime
    "plunge_reach": 5.4,
    "rhythm": ["ledge", "ledge", "ledge", "gate", "ledge", "plunge",
               "ledge", "ledge", "gate", "ledge", "ledge", "plunge", "rest"],
    "hardening": 0.35,

    "slime": "slime_block",
    "gate_block": "stone_brick_wall",
    "light": "ochre_froglight",
    "rest_half": 1,
    "headroom": 3,
    # THE LEDGE IS ITS OWN LAMP. A 1x1 landing hanging in the void is a walkable surface, so
    # unlit it is 60-odd new places for a mob to stand - and when the night pass solved that,
    # it put 14 lanterns IN the cells you have to land on and broke fourteen jumps. Neither
    # design could see the other. Making the landing the light removes the conflict, needs no
    # extra fixture, and is what lets you see the next jump in the dark, which a parkour
    # course wants anyway. The froglight colour carries the descent's gradient instead of the
    # stone: warm at the top, green through the twilight, pale at the bottom.
    "ledge_light": [[150, "ochre_froglight"], [95, "verdant_froglight"],
                    [0, "pearlescent_froglight"]],
    "bands": [[150, "stone_bricks", "mossy_stone_bricks"],
              [95, "deepslate_bricks", "cobbled_deepslate"],
              [0, "polished_blackstone_bricks", "blackstone"]],
    "weather": 0.28,
    "seed": 3,
}

AIRY = ("air", "cave_air", "void_air")
_PASSABLE = set(AIRY) | {"vine", "short_grass", "tall_grass", "fern", "large_fern",
                         "moss_carpet", "azalea", "flowering_azalea", "glow_lichen",
                         "hanging_roots", "dead_bush", "snow", "tripwire"}


def _band(p, y):
    for lo, main, alt in p["bands"]:
        if y >= lo:
            return main, alt
    return p["bands"][-1][1], p["bands"][-1][2]


def build_parkour(cfg: dict, donors=None) -> Canvas:
    p = {**PARKOUR, **cfg}
    if not p.get("under"):
        raise ValueError("parkour needs params.under")
    ctx = Ctx(p["under"])
    plot = find_plot(p["under"])
    w = World()
    cx, cz = plot.cx, plot.cz

    reserved = set()
    for path in (p.get("reserve") or []):
        import json
        import os
        if os.path.exists(path):
            for c in json.load(open(path, encoding="utf-8"))["cells"]:
                reserved.add((c[0], c[1], c[2]))

    def clear(x, y, z, half, head):
        """Room for the landing and for a body over it, touching nothing, ON THE PLOT.

        PASSABLE IS NOT EMPTY, and this design made that mistake for the second time in one
        session. The headroom question is "can a body stand here", which vine and grass answer
        yes to; the LANDING question is "may I build here", which they do not - two pads
        shipped on top of Jack's vines. So the landing course is tested for AIR and the
        courses above it for passability."""
        for dx in range(-half, half + 1):
            for dz in range(-half, half + 1):
                if not plot.contains(x + dx, z + dz):
                    return False
                for dy in range(0, head + 1):
                    q = (x + dx, y + dy, z + dz)
                    if q in reserved:
                        return False
                    n = ctx.name_at(*q)
                    allowed = AIRY if dy == 0 else _PASSABLE
                    if n not in allowed or protect.is_protected(n):
                        return False
        return True

    def site(ang, y, prev, half, gaps, drops, reach, head):
        for dr in p["radius_flex"]:
            for dd in drops:
                for gap in gaps:
                    for da in p["advance"]:
                        r = p["radius"] + dr
                        a = math.radians(ang + da)
                        x = int(round(cx + r * math.cos(a)))
                        z = int(round(cz + r * math.sin(a)))
                        ny = int(round(y - dd))
                        if ny < p["y_bottom"]:
                            continue
                        if prev is not None:
                            d = math.dist((x, z), (prev[0], prev[2]))
                            if d > min(gap, reach) + 0.35 or d < 2.0:
                                continue
                        if not clear(x, ny, z, half, head):
                            continue
                        return (x, ny, z, ang + da)
        return None

    moves, ang, y, prev, i = [], 0.0, float(p["y_top"]), None, 0
    while y > p["y_bottom"] + 4 and len(moves) < 260:
        kind = p["rhythm"][i % len(p["rhythm"])]
        i += 1
        progress = (p["y_top"] - y) / max(p["y_top"] - p["y_bottom"], 1)
        if kind == "plunge":
            # vary the fall: a course whose every plunge is the same twelve courses teaches
            # you the timing once and then repeats it
            order = list(p["plunge_drop"])
            k = int(hash01(int(y), i, p["seed"], 9) * len(order))
            order = order[k:] + order[:k]
            hop = site(ang, y, prev, 0, [p["plunge_reach"]], order,
                       p["plunge_reach"], p["headroom"])
        elif kind == "rest":
            hop = site(ang, y, prev, p["rest_half"], p["ledge_gap"], p["ledge_drop"],
                       4.5, p["headroom"])
        else:
            # HARDER AS IT GOES: further down, the long gap gets tried first more often
            gaps = list(p["ledge_gap"])
            if hash01(int(y), i, p["seed"]) > p["hardening"] * (1 - progress) + 0.25:
                gaps = sorted(gaps, reverse=True)
            hop = site(ang, y, prev, 0, gaps, p["ledge_drop"], 4.5,
                       p["headroom"] + (1 if kind == "gate" else 0))
        if hop is None:
            # fall back to the easiest move rather than inventing an impossible one
            hop = site(ang, y, prev, 0, [3.0, 3.6, 4.2, 4.5], [0, 1, 2, 3], 4.5, p["headroom"])
            kind = "ledge"
        if hop is None:
            break
        x, ny, z, ang = hop
        moves.append((x, ny, z, kind))
        prev = (x, ny, z)
        y = ny

    if len(moves) < 20:
        raise ValueError(f"the run found only {len(moves)} moves - check the radius and plot")

    feats = {k: 0 for k in ("ledge", "plunge", "gate", "rest", "slime", "lights", "gates")}
    for (x, y, z, kind) in moves:
        main, alt = _band(p, y)
        feats[kind] += 1
        if kind == "plunge":
            w.put(x, y, z, p["slime"])       # the jump pad: bounces, and cancels the fall
            feats["slime"] += 1
            continue
        if kind == "rest":
            h = p["rest_half"]
            for dx in range(-h, h + 1):
                for dz in range(-h, h + 1):
                    mat = alt if hash01(x + dx, y, z + dz, p["seed"]) < p["weather"] else main
                    w.put(x + dx, y, z + dz, mat)
            w.put(x, y, z, p["light"])
            feats["lights"] += 1
            continue
        lamp = next(b for lo, b in p["ledge_light"] if y >= lo)
        w.put(x, y, z, lamp)
        feats["lights"] += 1
        if kind == "gate" and ctx.name_at(x, y + 1, z) in AIRY:
            w.put(x, y + 1, z, p["gate_block"])   # clear it as well as reach it
            feats["gates"] += 1

    return w.canvas({"kind": "parkour", "profile_view": "top", "facing": [0, 1],
                     "features_built": feats,
                     "route": [[int(a), int(b), int(c), k] for a, b, c, k in moves]})
