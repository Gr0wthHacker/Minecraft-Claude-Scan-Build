"""THE SKY OVER THE MIDWAY: the fair's airship, and the display going off over the wheel.

Jack, having had the same look at the carnival: *"this applies to carnival area as well we can
have sky elements etc and more visual design etc."*

**THE MIDWAY'S SKY IS THE OPPOSITE PROBLEM TO THE LOST PLATEAU'S AND NEEDS A DIFFERENT ANSWER.**
Measured over the park as placed:

    Lost Plateau   0.88% of its mass above Y250   ONE object, and it is perched on a crag
    Midway         6.70%                          the Wyrm Gate 17,555 and the Sky Lift's tower
    Midway         165 cells above Y270           ...and nothing at all above Y280

So this land already has a MIDDLE sky - a skull you ride a train through, a wheel that tops out at
Y276 - and then fifty courses of nothing over it. What it is short of is not mass but ALTITUDE, and
a second floating mountain would only crowd the things that are already up there.

**A FAIRGROUND'S OWN SKY IS AN AIRSHIP AND A FIREWORK.** Both are new shapes for this repo and
both are on the good side of CLAUDE.md's measured line:

    THE AIRSHIP    one long convex hull - a voxel primitive - with planar fins, a box gondola and
                   a pattern painted on it. The ladybird's category at fifty-six blocks, and the
                   money view is the BROADSIDE, which is what a guest walking the entrance axis
                   gets for free
    THE BURSTS     radial spokes off a bright core. Pure columns, nothing volumetric anywhere, and
                   a firework is the one image a fairground sky is actually known by

**AND NEITHER IS A BALLOON, DELIBERATELY.** `gen/balloon.py` builds a verified one and it would be
the obvious thing to hang here - but Jack has already refused a reused asset once, on the causeway
(*"those are used assets, we want NEW things"*), and a show balloon over a fairground is the
causeway's own object in a second place rather than this land getting something of its own.
"""
from __future__ import annotations

import math

from .canvas import Canvas, hash01
from .loft import Frame, ball, sweep, thread, r as _r

#: The Midway's own palette - red, white and yellow - is what makes the airship read as the FAIR'S
#: airship rather than as a grey military one. Measured across families, luminance side face:
#: black_wool 21 . red_wool 65 . spruce_planks 89 . oak_planks 134 . yellow_wool 197 . white 236.
SHIP = {
    "hull": "white_wool",
    "band": "red_wool",               # the circumferential bands - the fairground's own colour
    "flash": "yellow_wool",           # the chevron down the flank
    "fin": "red_wool",
    "fin_edge": "white_wool",
    "car": "spruce_planks",           # the gondola: a timber box, like everything else here
    "trim": "oak_planks",
    "glass": "black_wool",            # the gondola's windows, read as openings
    "strut": "oak_fence",
    "pod": "gray_wool",               # engine nacelles
    "prop": "stripped_oak_log",
    "lamp": "ochre_froglight",
}

#: A burst is a CORE and SPOKES, and the spokes change colour along their length - which is what a
#: firework does and what stops a radial object reading as a sea urchin.
SPARK = {
    "core": "ochre_froglight",
    "red": ("red_wool", "orange_wool", "yellow_wool"),
    "gold": ("orange_wool", "yellow_wool", "white_wool"),
    "rose": ("purple_wool", "magenta_wool", "pink_wool"),
    "blue": ("cyan_wool", "light_blue_wool", "white_wool"),
    "lime": ("green_wool", "lime_wool", "yellow_wool"),
}

CARNIVAL = {
    "anchor": None,
    "lot": None,
    "at": [0, 0],
    "sy": 120,
    "ship": None,                     # {at: [v, u], y: , facing: , length: , beam: }
    "bursts": (),                     # [{at: [v, u], y: , r: , colour: , spokes: }, ...]
    "seed": 19,
}


# --------------------------------------------------------------------------- the airship

def _airship(c: Canvas, p: dict) -> dict:
    """A fairground dirigible: hull, fins, gondola, two engine pods.

    **THE HULL IS ONE CONVEX MASS AND EVERYTHING ELSE HANGS OFF IT**, which is the whole reason an
    airship is buildable here where an aeroplane needed its wings kept level: there is no thin
    diagonal sheet anywhere in it, so nothing steps and nothing comes apart.
    """
    fr = Frame(c, int(p["at"][0]), int(p["at"][1]), p.get("facing", "north"), SHIP)
    y0 = int(p["y"])
    L = float(p.get("length", 56))
    beam = float(p.get("beam", 7.0))
    n = {}

    def tally(key, fn):
        before = c.ids.copy()
        fn()
        n[key] = int((c.ids != before).sum())

    nose, tail = L * 0.5, -L * 0.5

    def hull():
        # **A FINE STEP, BECAUSE A HULL IS A STACK OF ELLIPSES AND ONE GAP IS A HOLE IN A BALLOON.**
        steps = int(L * 3)
        for i in range(steps + 1):
            t = i / steps
            f = nose + (tail - nose) * t
            #: the classic airship section: blunt nose, maximum at a third, long fine tail
            rad = beam * max(0.0, (1 - ((t - 0.32) / 0.68) ** 2) if t > 0.32
                             else (1 - ((0.32 - t) / 0.36) ** 2)) ** 0.5
            if rad < 0.5:
                continue
            ball(fr, f, 0, y0, rad, "hull", rs=rad, ry=rad)
    tally("hull", hull)

    def paint():
        """THE LIVERY, and it is what makes this the FAIR'S airship rather than a white capsule.

        **A STRIPE ALONG THE LENGTH IS WHAT READS BROADSIDE, AND BROADSIDE IS THE VIEW.** Five
        one-cell rings round a fifty-six block hull came out at 78% white and read as unpainted -
        a band seen end-on is a band nobody sees. The identity of a convex mass is the PATTERN on
        it, which is the ladybird's own claim, and the pattern has to run the way the eye does.
        """
        lo, hi = _r(tail), _r(nose)
        rings = [_r(nose - L * v) for v in (0.20, 0.40, 0.60, 0.80)]
        for f in range(lo, hi + 1):
            for s in range(-int(beam) - 1, int(beam) + 2):
                for y in range(y0 - int(beam) - 1, y0 + int(beam) + 2):
                    if not fr.solid(f, s, y):
                        continue
                    if any(abs(f - rf) <= 1 for rf in rings):
                        fr.put(f, s, y, "band")           # four bands, three cells wide
                    elif abs(y - y0) <= 1:
                        fr.put(f, s, y, "band")           # the stripe, the whole length
                    elif y == y0 - 2 or y == y0 + 2:
                        fr.put(f, s, y, "flash")          # a yellow line either side of it
    tally("paint", paint)

    def fins():
        """Four planar fins at the tail - up, down and both flanks.

        **THE CHORD SHRINKS WITH THE REACH; THE REACH DOES NOT SHIFT WITH THE CHORD.** Built the
        other way round - each ring of the fin stepped forward as it went out - the four of them
        came out as a ragged red lump at the tail rather than as surfaces, because every cell was
        offset from its neighbour on two axes at once. Swept properly it is a clean trapezium: full
        chord at the tail post, tapering forward, longest at the back. A fin is a SHEET, which is
        the one thing this medium draws natively, and it is most of what says which end is the back.
        """
        h = beam * 1.45
        chord = L * 0.18
        f0 = tail + 1
        for dv, du in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            for f in range(_r(f0), _r(f0 + chord) + 1):
                t = (f - f0) / max(1.0, chord)          # 0 at the tail post, 1 forward
                reach = h * (1.0 - 0.6 * t)
                for k in range(1, _r(reach) + 1):
                    fr.put(f, du * k, y0 + dv * k, "fin_edge" if k >= _r(reach) else "fin")
    tally("fins", fins)

    def car():
        """THE GONDOLA, and it is what gives the thing SCALE. A hull alone could be any size; a
        car with windows in it says how big the hull is, which is the leaf under the ladybird."""
        cf0, cf1 = _r(nose - L * 0.30), _r(nose - L * 0.52)
        top = y0 - _r(beam) - 1
        for f in range(cf1, cf0 + 1):
            for s in (-2, -1, 0, 1, 2):
                fr.put(f, s, top - 1, "trim")                 # the roof, against the hull
                fr.put(f, s, top - 4, "car")                  # the floor
            for s in (-2, 2):
                for y in range(top - 3, top - 1):
                    fr.put(f, s, y, "glass" if (f + cf0) % 3 else "car")
        for f in (cf1, cf0):
            for s in (-2, -1, 0, 1, 2):
                for y in range(top - 3, top - 1):
                    fr.put(f, s, y, "car")
        # **A STRUT REACHES THE HULL, AND WHERE THE HULL IS IS FOUND RATHER THAN COMPUTED.** At
        # s = +-2 the hull's underside is a course higher than it is on the centreline - it is a
        # sphere - so a strut of a fixed height stops short and the whole gondola ships as a
        # 199-cell island under the airship. `loft.Frame.solid` is the only honest witness; this
        # repo has had a mane, a pair of ossicones and a tail come away from computed radii.
        for f in (cf1 + 1, cf0 - 1):
            for s in (-2, 2):
                for y in range(top, y0 + 1):
                    if fr.solid(f, s, y):
                        break
                    fr.put(f, s, y, "strut")
        fr.put(_r((cf0 + cf1) / 2), 0, top - 5, "lamp")       # a light under the car
    tally("car", car)

    def pods():
        """Engine nacelles on the flanks, each with a propeller - and a prop is THREADED, because
        a blade ends under one cell and a swept taper that thin comes apart at some scales and not
        at the one that was looked at."""
        pf = _r(nose - L * 0.46)
        for s in (-1, 1):
            sd = s * (_r(beam) - 1)
            sweep(fr, (pf + 2, sd, y0 - 2), (pf - 2, sd, y0 - 2), 1.6, 1.2, "pod")
            hub = (pf + 3, sd, y0 - 2)
            for sgn in (-1, 1):
                thread(fr, hub, (hub[0], sd, y0 - 2 + sgn * 3.2), "prop")
    tally("pods", pods)

    n["refused"] = fr.refused
    n["clipped"] = fr.clipped
    return n


# --------------------------------------------------------------------------- the bursts

def _burst(c: Canvas, p: dict, seed: int) -> dict:
    """A firework burst: a bright core with spokes radiating off it.

    **THE SPOKES ARE THREADED, NEVER SWEPT.** A spoke is one cell thick by definition - that is
    what makes it a spark rather than a sausage - and two single cells whose centres moved on two
    axes at once are DIAGONAL neighbours. It has cost this repo a mane, a pair of ossicones, a
    tail, three pterosaur spans, a bridge cable and seven tree crowns.

    **AND THE DIRECTIONS ARE EVEN, NOT RANDOM.** Hashed per spoke they clump, and a burst with a
    bald patch reads as a dead spider. A Fibonacci sphere spaces them by construction.
    """
    fr = Frame(c, int(p["at"][0]), int(p["at"][1]), "north", SPARK)
    y0 = int(p["y"])
    rad = float(p.get("r", 11))
    k = int(p.get("spokes", 16))
    inner, mid, outer = SPARK[p.get("colour", "gold")]
    n = {"core": 0, "spoke": 0, "tip": 0}

    before = c.ids.copy()
    ball(fr, 0, 0, y0, 2.0, "core")
    n["core"] = int((c.ids != before).sum())

    phi = math.pi * (3.0 - math.sqrt(5.0))
    for i in range(k):
        # an even spiral over the sphere - and the LOWER hemisphere is thinned, because a burst
        # falls: the sparks below have already started to drop and there are fewer of them
        cy = 1 - 2 * (i + 0.5) / k
        rr = math.sqrt(max(0.0, 1 - cy * cy))
        th = phi * i
        df, ds, dy = math.cos(th) * rr, math.sin(th) * rr, cy
        length = rad * (0.72 + 0.28 * hash01(i, seed, 3))
        if dy < -0.2:
            length *= 0.75
        before = c.ids.copy()
        thread(fr, (0, 0, y0), (df * length * 0.45, ds * length * 0.45, y0 + dy * length * 0.45),
               inner)
        thread(fr, (df * length * 0.40, ds * length * 0.40, y0 + dy * length * 0.40),
               (df * length * 0.80, ds * length * 0.80, y0 + dy * length * 0.80), mid)
        n["spoke"] += int((c.ids != before).sum())
        before = c.ids.copy()
        thread(fr, (df * length * 0.76, ds * length * 0.76, y0 + dy * length * 0.76),
               (df * length, ds * length, y0 + dy * length), outer)
        n["tip"] += int((c.ids != before).sum())
    n["refused"] = fr.refused
    n["clipped"] = fr.clipped
    return n


# --------------------------------------------------------------------------- build

def build(cfg: dict, donors=None) -> Canvas:
    p = {**CARNIVAL, **(cfg or {})}
    for kk in ("anchor", "lot"):
        if not p.get(kk):
            raise ValueError(f"the carnival sky needs {kk}")
    dv, du = int(p["lot"][0]), int(p["lot"][1])
    at = [int(x) for x in (p.get("at") or (0, 0))]
    anchor = [int(x) for x in p["anchor"]]
    ax, ay, az = anchor[0] + at[0], anchor[1], anchor[2] + at[1]
    c = Canvas(dv, int(p["sy"]), du, donors)
    parts = {}

    if p.get("ship"):
        q = dict(p["ship"])
        q["y"] = int(q["y"]) - ay
        for k, v in _airship(c, q).items():
            parts["ship " + k] = v

    for i, spec in enumerate(p.get("bursts") or ()):
        q = dict(spec)
        q["y"] = int(q["y"]) - ay
        got = _burst(c, q, int(p["seed"]) + i * 17)
        for k, v in got.items():
            parts[f"burst{i + 1} {k}"] = v
    parts["bursts"] = len(p.get("bursts") or ())

    c.world_origin = (ax, ay, az)
    c.meta = {
        "kind": "carnivalsky",
        "lot": [dv, du],
        "at": at,
        "land": "midway",
        "facing": (p.get("ship") or {}).get("facing", "north"),
        "profile_axis": "v",
        "parts": parts,
        "note": ("Disconnected BY DESIGN: the airship and every burst is its own piece in open "
                 "air. One component would mean two of them were touching."),
    }
    return c
