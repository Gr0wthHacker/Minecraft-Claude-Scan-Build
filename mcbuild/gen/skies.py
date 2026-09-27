"""THE SKY OVER THE LOST PLATEAU: floating isles, and the expedition's aircraft banking over them.

Jack, having walked the land: *"add more sky elements that are disconnected e.g. maybe a high up
plane or something interesting."*

**THE LAND'S SKY WAS EMPTY AND IT IS THE ONLY LAND IN THE PARK THAT IS.** Measured over the park
as placed, cells standing above Y250:

    Lost Plateau   1,260   ...and 538 of those are the ridge's own canopy and vines, 691 the
                           pterosaur on its crag. ONE designed sky object, and it is perched
    Midway         5,218   Wyrm Gate 4,488, Sky Lift 730
    Prismworks     6,025   Prism Well 3,318, Wyrm Gate 2,142, Prism Rig, Crown Descent

The land's whole mass sits in a thirty-course band - 87% of it below Y230 - and every render of it
from every bearing is the same picture: a dense green strip across the bottom third and two thirds
of empty blue above. The tallest thing in 34,000 columns is Y279 and the build limit is Y320.

**WHY THESE TWO THINGS AND NOT A BIGGER MOUNTAIN.** The ground is full - 27 free pads of 8x8 in
the whole 600x200 - and the land already has the park's two largest terrain designs in it. What it
has none of is anything a guest looks UP at. So the sky gets mass (the isles) and a figure against
that mass (the aircraft), which is the composition a skyline needs and neither piece is on its own.

    THE ISLES      one convex mass each, a lens with a keel, jungle on top and vines off the rim.
                   The ladybird's category - a dome, which is a voxel primitive - and the money
                   view is the UNDERSIDE, which is the one view a guest on the ground always has
    THE AIRCRAFT   wings are flat SHEETS, the fuselage a TAPER, struts and undercarriage COLUMNS,
                   the propeller a disc. Every part on the good side of CLAUDE.md's own measured
                   line, and there is no joint anywhere that has to describe compound muscle -
                   which is what retired eight mammals and then a stegosaur after four rounds

**AND A BIPLANE IS THE LOST WORLD'S OWN VEHICLE.** The land is a palaeontology expedition camp on
a plateau; the thing that got the expedition there is an aeroplane, and a 1920s survey biplane is
both the right period for the fiction and the right shape for the medium.

**THE BANK IS THE WHOLE DIFFERENCE BETWEEN FLYING AND MOUNTED.** Level, an aircraft is a cross -
which is exactly how the pterosaur reads at land scale, a small dark crucifix on a crag. Rolled
into a turn the silhouette breaks: one wing up, one down, the fuselage at an angle, and the
underside presented to whoever is looking up at it. It costs one thing and the cost is stated
below: a banked sheet is a STAIRCASE, and a staircase one cell thick is not 6-connected.
"""
from __future__ import annotations

import math

import numpy as np

from . import pterosaur
from .canvas import Canvas, hash01
from .loft import Frame, ball, sweep, thread, r as _r
from ..nbt import state_name, state_props

#: **THE LADDER IS MEASURED ACROSS FAMILIES, WHICH IS THE ONLY PLACE THIS ECONOMY HAS ONE.** Five
#: separate notes in CLAUDE.md concluded it had none, and every one of them searched inside a
#: single material family, where a ladder cannot exist by construction. Luminance, side face:
#:
#:     polished_blackstone_bricks 45 . red_wool 65 . spruce_planks 89 . bone_block 225
#:
#: Steps of 20, 24 and 136 - and that last one is the point. An aircraft seen from below against a
#: bright sky is read by the contrast WITHIN it: pale doped wings against a dark body is what says
#: aeroplane at a distance where no detail survives. Every block cheap, every block 1.19.
PLANE = {
    "wing": "bone_block",             # doped linen - and the land's own fossil material
    "rib": "smooth_stone",            # the wing's leading edge, a shade down so the edge reads
    "body": "spruce_planks",          # the land's timber: the expedition built it out of what it had
    "keel": "stripped_spruce_log",
    "cowl": "polished_blackstone_bricks",
    "mark": "red_wool",               # roundel, fin flash, wingtip
    "strut": "spruce_fence",          # a fence IS an interplane strut
    "prop": "stripped_spruce_log",
    "glass": "black_wool",            # the cockpit opening, read as a hole rather than glazed
}

#: The isles are the ridge's own rock, so they read as pieces OF the plateau rather than as
#: scenery hung over it - and dark underneath, because the underside is what a guest sees.
ISLE = {
    "keel": "cobbled_deepslate",
    "deep": "smooth_basalt",
    "rock": "stone",
    "warm": "dripstone_block",
    "soil": "moss_block",
    "leaf": "jungle_leaves",
    "bush": "azalea_leaves",
    "trunk": "jungle_log",
    "vine": "vine",
    "lamp": "ochre_froglight",
}

SKY = {
    "anchor": None,                   # [x, y, z] world origin of the lot
    "lot": None,                      # [dv, du]
    "at": [0, 0],
    "sy": 120,
    #: A SKY COMPOSITION IS DECLARED, NOT DERIVED, and that is not the same fault as a hard-coded
    #: waypoint. A canopy walk's route is a fact about rock that keeps arriving, so it is measured
    #: on every build; where a thing hangs in empty air is a decision about the SKYLINE, and there
    #: is nothing under it to derive it from. What must be derived is that it collides with
    #: nothing, and that is `verify_against` plus the test.
    "isles": (),                      # [{at: [v, u], y: , r: , tall: , trees: , lamp: }, ...]
    "birds": (),                      # [{at: [v, u], y: , span: , facing: , spread: }, ...]
    "plane": None,                    # {at: [v, u], y: , facing: , span: , bank: }
    "seed": 41,
}


# --------------------------------------------------------------------------- isles

def _isle(c: Canvas, p: dict, seed: int) -> dict:
    """One floating island: a lens of rock with a keel under it and a wood on top.

    **THE NOISE GOES ON THE RADIUS, NEVER ON THE INTERIOR.** Thresholded per cell a drift comes
    out as confetti - the deck soffit, the lowland thicket, the frog's blotches and the claim
    row's worked ground all shipped that once each. Wobbled at the boundary the mass fills solid
    and only the outline is ragged, which is what a torn-loose piece of rock looks like.
    """
    cv, cu = int(p["at"][0]), int(p["at"][1])
    y0 = int(p["y"])
    rad = float(p["r"])
    tall = int(p.get("tall", max(3, int(rad * 0.55))))
    keel = float(p.get("keel", rad * 1.35))
    n = {"rock": 0, "soil": 0, "wood": 0, "vine": 0, "lamp": 0}

    def wobble(dv, du, k):
        a = math.atan2(du, dv)
        return 1.0 + 0.16 * math.sin(a * 3 + seed) + 0.11 * math.sin(a * 5 - seed * 1.7) \
            + 0.07 * math.sin(a * 8 + k)

    # THE BODY: a lens. Widest one course under the top, so the rim OVERHANGS its own keel - the
    # single thing that separates a floating island from a cone standing on its point.
    lo = y0 - int(keel)
    for y in range(lo, y0 + 1):
        t = (y - lo) / max(1, (y0 - lo))          # 0 at the keel's tip, 1 at the deck
        prof = rad * (t ** 0.62)                  # fast near the tip, flattening at the top
        if y == y0:
            prof = rad * 0.94
        for dv in range(-int(rad) - 2, int(rad) + 3):
            for du in range(-int(rad) - 2, int(rad) + 3):
                d = math.hypot(dv, du)
                if d > prof * wobble(dv, du, y):
                    continue
                deep = (y0 - y) / max(1.0, keel)
                key = "keel" if deep > 0.72 else ("deep" if deep > 0.45 else
                                                 ("warm" if hash01(dv, du, y, seed) < 0.22 else "rock"))
                if c.put(cv + dv, y, cu + du, c.state(ISLE[key])):
                    n["rock"] += 1

    # THE SOIL AND THE WOOD on top, and the soil is what every plant roots in - rule 11, and the
    # lowland thicket returned 173 placement problems the one time it was ignored.
    top = []
    for dv in range(-int(rad) - 2, int(rad) + 3):
        for du in range(-int(rad) - 2, int(rad) + 3):
            if not c.solid(cv + dv, y0, cu + du):
                continue
            if c.put(cv + dv, y0 + 1, cu + du, c.state(ISLE["soil"])):
                n["soil"] += 1
                top.append((dv, du))
    for dv, du in top:
        if hash01(dv, du, seed, 7) < 0.30:
            if c.put(cv + dv, y0 + 2, cu + du, c.state("moss_carpet")):
                n["soil"] += 1

    for k in range(int(p.get("trees", 3))):
        if not top:
            break
        dv, du = top[int(hash01(k, seed, 11) * len(top)) % len(top)]
        if math.hypot(dv, du) > rad * 0.72:
            continue
        n["wood"] += _tree(c, cv + dv, y0 + 2, cu + du, 3 + int(hash01(k, seed, 3) * 3), seed + k)

    # THE VINES: off the RIM's underside, which is the one part of an isle a guest on the ground
    # can always see. Anything clinging is anchored to what is THERE - `Canvas.solid`, never a
    # computed radius, because this repo has had a mane, a pair of ossicones and a tail come away.
    for dv in range(-int(rad) - 2, int(rad) + 3):
        for du in range(-int(rad) - 2, int(rad) + 3):
            if not c.solid(cv + dv, y0, cu + du):
                continue
            if all(c.solid(cv + dv + a, y0, cu + du + b) for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                continue                            # interior: a vine hangs off the EDGE
            drop = 2 + int(hash01(dv, du, seed, 5) * 6)
            for k in range(1, drop + 1):
                y = y0 - k
                if c.solid(cv + dv, y, cu + du):
                    break
                if not c.put(cv + dv, y, cu + du, c.state(ISLE["vine"],
                                                          **_vine_faces(c, cv + dv, y, cu + du))):
                    break
                n["vine"] += 1

    # ONE LAMP IN THE SOIL, not on it. A fixture laid over a surface is the hole in a sculpture
    # `Island Night` forbids; a froglight IS the floor, and it is what makes an isle read at dusk.
    if p.get("lamp", True) and top:
        dv, du = top[len(top) // 2]
        if c.put(cv + dv, y0 + 1, cu + du, c.state(ISLE["lamp"])):
            n["lamp"] += 1
    return n


def _vine_faces(c: Canvas, x, y, z) -> dict:
    """**A VINE'S FLAGS NAME THE FACE IT CLINGS TO, NOT THE WAY IT FACES.**

    Written as the back of the side it grew from, 2,948 of the Overgrowth's 3,000 vines named a
    face with open air behind it - and a vine hanging in air renders identically to one on a wall
    in every sheet this repo has. It is the one block whose connection flags are a DECISION.
    """
    out = {}
    for face, (dx, dz) in (("north", (0, -1)), ("south", (0, 1)), ("east", (1, 0)), ("west", (-1, 0))):
        if c.solid(x + dx, y, z + dz):
            out[face] = "true"
    if not out:
        out["up"] = "true"
    return out


def _tree(c: Canvas, x, y0, z, h: int, seed: int) -> int:
    """A small jungle crown on a bare trunk - wide and flat, which is what says jungle."""
    n = 0
    for k in range(h):
        if c.put(x, y0 + k, z, c.state(ISLE["trunk"], axis="y")):
            n += 1
    # **THE CROWN MUST TOUCH ITS OWN TRUNK.** Skipping the centre cell at dy=0 - the obvious way
    # to keep the trunk visible - removes the crown's ONLY join to it, and seven crowns shipped as
    # 29-cell islands hanging beside their own trees. The ear-tip rule, in foliage.
    cy = y0 + h
    for dy in range(0, 2):
        rad = 2.4 - dy * 0.9
        for dv in range(-3, 4):
            for du in range(-3, 4):
                if math.hypot(dv, du) > rad:
                    continue
                key = "bush" if hash01(dv, du, dy, seed) < 0.18 else "leaf"
                if c.put(x + dv, cy + dy, z + du, c.state(ISLE[key], persistent="true")):
                    n += 1
    return n


# --------------------------------------------------------------------------- the flock


def _bird(c: Canvas, p: dict) -> dict:
    """A pterosaur SOARING, pasted from `gen/pterosaur.py` with its crag switched off.

    **THIS IS THE LAND'S OWN ANIMAL, WHICH IS NOT THE SAME AS A REUSED ASSET.** Jack refused two
    of those on the causeway - *"get rid of the gecko and bat - those are used assets, we want NEW
    things"* - and both were creatures lifted out of the lowland into a place that had no claim on
    them. The Lost Plateau already has a pteranodon roosting on its summit and a nesting colony on
    its rim; adults on the wing over the plateau is the same story finished, not a second copy of
    an object. What would be a repeat is the PERCHED animal again, and none of these has a crag.

    **SPREAD WIDER THAN THE ROOSTING ONE, DELIBERATELY.** That one is 0.72 and its own module
    records why - *"fully spread, a wing is one flat plate; half-furled it keeps a stepped
    outline"* - but a perched animal and a soaring one are meant to read as different things, and
    the difference IS the wing. These run 0.84-0.92: still short of a plate, and unmistakably not
    the same attitude as the bird on the rock.
    """
    span = float(p.get("span", 36))
    sub = pterosaur.build({
        "perch": False, "span": span, "spread": float(p.get("spread", 0.88)),
        "facing": p.get("facing", "west"), "seed": int(p.get("seed", 0)), "at": None,
    })
    ids = sub.ids
    ys, zs, xs = np.nonzero(ids != 0)
    if not len(xs):
        return {"cells": 0}
    # CENTRED ON ITS OWN CONTENT, never on its canvas. A pterosaur's canvas is sized to the
    # animal's own frame and the frame's origin is under the FEET, which on a flying one is
    # nowhere in particular - so a paste keyed to the canvas puts the animal wherever its
    # bounding box happened to fall, and moves it whenever the span changes.
    cx, cy, cz = (int(xs.min()) + int(xs.max())) // 2, int(ys.min()), (int(zs.min()) + int(zs.max())) // 2
    ov = int(p["at"][0]) - cx
    ou = int(p["at"][1]) - cz
    oy = int(p["y"]) - cy
    pal = sub.palette
    n = 0
    for y, z, x in zip(ys.tolist(), zs.tolist(), xs.tolist()):
        tag = pal[int(ids[y, z, x])]
        name = state_name(tag).split(":")[-1]
        if c.put(x + ov, y + oy, z + ou, c.state(name, **state_props(tag))):
            n += 1
    return {"cells": n, "span": int(span), "facing": p.get("facing", "west")}


# --------------------------------------------------------------------------- the aircraft

def _plane(c: Canvas, p: dict) -> dict:
    """A survey biplane, banked into a turn.

    Written in the aircraft's OWN axes - forward, side, up - through `loft.Frame`, so the bearing
    convention lives in one place. CLAUDE.md: *one frame, one bug*; the raycaster draws a facing
    and its opposite identically until `render3d.subdivide` expands a stair, and this project got
    the stair convention wrong twice in one session by hand.

    **A WING IS TWO COURSES AND THEY ARE DIFFERENT MATERIALS.** One course thick it came out as a
    row of separate plates - the bank's own steps, seen edge-on, with a cell of sky between each
    pair - which reads as a ladder rather than as a surface. Two courses merge the steps into a
    stepped SHEET, and making the lower course darker than the upper is what a wing looks like
    from any angle at all: lit on top, shaded underneath. From below - the view a guest eighty
    courses down always has - the dark course is the whole aircraft.
    """
    fr = Frame(c, int(p["at"][0]), int(p["at"][1]), p.get("facing", "north"), PLANE)
    y0 = int(p["y"])
    span = float(p.get("span", 46))
    bank = math.tan(math.radians(float(p.get("bank", 16))))
    half = span / 2.0
    L = float(p.get("length", span * 0.62))
    gap = int(p.get("gap", 5))                      # courses between the two wings
    n = {}

    def tally(key, fn):
        """**A PART COUNT IS UNIQUE CELLS, NOT `put` CALLS AND NOT `Frame.placed`.**

        The squid reported 251,264 arm blocks in a 116,000-cell animal, and the ankylosaur's horns
        reported 124 placements while gaining ZERO cells - they were entirely inside the skull, and
        no call count could ever have said so. `Frame.placed` counts WRITES, so two sweeps that
        overlap increment it twice: measured that way this aircraft's body and wings came to 5,437
        cells in a 2,124-cell aeroplane. The canvas is the only honest witness.
        """
        before = c.ids.copy()
        fn()
        #: CHANGED cells, not NEW ones. A roundel and a cockpit are PAINT - they recolour the wing
        #: and the fuselage they sit on - so counted as new cells both read 0, which is exactly
        #: indistinguishable from the part not having been placed at all. That ambiguity is the
        #: whole reason this count exists.
        n[key] = int((c.ids != before).sum())

    def lift(s):
        """**THE BANK, AND THE RISER THAT KEEPS IT CONNECTED.** A sheet that climbs a fraction of a
        course per cell of side is a STAIRCASE, and two cells that moved on two axes at once are
        DIAGONAL neighbours - the ear-tip rule, which has cost this repo a mane, two ossicones, a
        tail, three pterosaur spans and a bridge cable."""
        return y0 + s * bank

    def sheet(f0, f1, y_at, s_lo, s_hi, top="wing", under="rib", thick=2, edge=None):
        prev = None
        for i in range(int(s_lo), int(s_hi) + 1):
            y = _r(y_at(i))
            lo = y - (thick - 1)
            if prev is not None:
                for yy in range(min(y, prev), max(y, prev) + 1):   # the riser
                    for f in range(int(f0), int(f1) + 1):
                        fr.put(f, i, yy, top if yy == y else under)
            for k in range(thick):
                yy = lo + k
                key = top if k == thick - 1 else under
                for f in range(int(f0), int(f1) + 1):
                    fr.put(f, i, yy, edge if (edge and f == int(f1) and k == thick - 1) else key)
            prev = y

    chord = max(4, int(round(span * 0.15)))
    f_lo, f_hi = -chord // 2, chord - chord // 2 - 1
    #: **A STRUT HANGS OFF THE WING, WHICH MEANS INSIDE THE WING'S OWN CHORD.** Placed at
    #: f = L*0.16 the whole undercarriage is past the trailing edge and ships as a six-cell island
    #: in open air - which a render draws as a perfectly good undercarriage, because a strut
    #: hanging from nothing looks exactly like one hanging from something.
    leg_f = min(f_hi, max(f_lo, 1))
    body_y = lift(0) + gap * 0.45

    # THE TWO WINGS. The upper is longer and set a cell forward, which is what a real sesquiplane
    # does and what stops the pair reading as one thick slab from directly above.
    tally("wing", lambda: (sheet(f_lo, f_hi, lift, -half, half, edge="rib"),
                           sheet(f_lo + 1, f_hi + 1, lambda s: lift(s) + gap, -half - 2, half + 2,
                                 edge="rib")))

    # THE FUSELAGE: a taper, deepest at the cockpit and fining to the tail post.
    nose, tail = L * 0.52, -L * 0.48
    tally("body", lambda: (
        sweep(fr, (nose - 1.0, 0, body_y), (L * 0.12, 0, body_y), 2.0, 2.5, "body"),
        sweep(fr, (L * 0.12, 0, body_y), (tail + 1.5, 0, body_y + 0.6), 2.5, 1.0, "body"),
        thread(fr, (nose - 1.5, 0, body_y - 2), (tail + 1.5, 0, body_y - 0.5), "keel")))

    # THE COCKPIT: a hole in the top of the fuselage, two courses long, so it reads as an OPENING
    # rather than as a dark block - which is what puts a pilot in the thing.
    tally("cockpit", lambda: [fr.put(f, s, body_y + 2, "glass")
                              for f in range(int(L * 0.02), int(L * 0.20))
                              for s in (-1, 0, 1)])

    # THE ENGINE AND THE PROPELLER. A radial cowling is a disc - the one shape this medium gives
    # away free - and the prop is two long blades, THREADED, because a blade ends under one cell
    # and a swept taper that thin comes apart at some scales and not at the one you looked at.
    tally("cowl", lambda: ball(fr, nose - 0.8, 0, body_y, 2.7, "cowl", rs=2.7, ry=2.7))
    hub = (nose + 1.2, 0, body_y)
    #: **A PROPELLER IS ABOUT A FIFTH OF THE SPAN ACROSS, NOT HALF OF IT.** At 0.24 of the span
    #: each way the blades were a 22-course vertical bar off the nose - which reads as a mast, and
    #: in a render of a whole land as the tallest thing on the aircraft by a factor of three.
    blade = span * 0.10
    tally("prop", lambda: [
        (thread(fr, hub, (hub[0], hub[1] + sgn * 0.22 * blade, hub[2] + sgn * blade), "prop"),
         thread(fr, (hub[0] - 1, hub[1], hub[2]),
                (hub[0] - 1, hub[1] + sgn * 0.22 * blade, hub[2] + sgn * blade * 0.72), "prop"))
        for sgn in (-1, 1)])

    # THE TAIL. A stabiliser on the bank, and a FIN that is a swept triangle rather than a post -
    # a single column at the tail post reads as an aerial, and the fin is half of what tells a
    # stranger which end is the back.
    tspan = span * 0.32
    t0, t1 = int(tail) + 1, int(tail) + max(4, int(span * 0.11))
    tally("tail", lambda: sheet(t0, t1, lambda s: lift(s) + gap * 0.5, -tspan / 2, tspan / 2,
                                thick=1, edge="rib"))

    def fin():
        h = max(5, int(span * 0.15))
        for k in range(1, h + 1):
            back = int(round(k * 0.55))             # swept: the higher, the further aft
            for f in range(t0 + back, t1 + 1):
                fr.put(f, 0, lift(0) + gap * 0.5 + k, "mark" if k > h - 3 else "wing")
    tally("fin", fin)

    # THE INTERPLANE STRUTS. The courses of open air between the wings are the FEATURE - fill them
    # and the silhouette is a slab - and the struts are what say the gap is structural.
    def struts():
        for s in (-half * 0.34, -half * 0.66, half * 0.34, half * 0.66):
            for k in range(1, gap):
                fr.put(0, s, lift(s) + k, "strut")
        for s in (-1.5, 1.5):                       # cabane, cockpit to upper wing
            for k in range(1, gap):
                fr.put(leg_f, s, lift(s) + body_y - lift(0) + 2 + k, "strut")
    tally("strut", struts)

    # THE UNDERCARRIAGE, which is most of what makes an aeroplane read FROM BELOW.
    def gear():
        """**AND THE AXLE HAS TO REACH THE LEGS.** Run from int(-span*0.13) to int(span*0.13) it
        stops one cell short of legs placed at the unrounded value, and the whole undercarriage
        ships as two islands - which a render draws as a perfectly good undercarriage. It also
        rides the bank, so it needs the same riser every other sheet here needs."""
        gs = int(round(span * 0.13))
        for s in (-gs, gs):
            for k in range(1, 4):
                fr.put(leg_f, s, lift(s) - k, "strut")
            for f in range(leg_f - 1, leg_f + 2):
                fr.put(f, s, lift(s) - 4, "keel")
        prev = None
        for i in range(-gs, gs + 1):
            y = _r(lift(i) - 4)
            if prev is not None and y != prev:
                for yy in range(min(y, prev), max(y, prev) + 1):
                    fr.put(leg_f, i, yy, "keel")
            fr.put(leg_f, i, y, "keel")
            prev = y
    tally("gear", gear)

    # THE MARKINGS: a roundel on each upper wing and a flash down the fuselage - the one saturated
    # colour on the aircraft, and what tells a stranger it is a MACHINE rather than a bird.
    def marks():
        for s in (-half * 0.62, half * 0.62):
            for df in (0, 1):
                for ds in (-1, 0, 1):
                    fr.put(df + f_lo + 1, s + ds, lift(s + ds) + gap, "mark")
            fr.put(f_lo + 1, s, lift(s) + gap, "glass")
        for f in range(int(L * 0.24), int(L * 0.36)):
            for s in (-2, 2):
                fr.put(f, s, body_y, "mark")
    tally("mark", marks)

    n["refused"] = fr.refused
    n["clipped"] = fr.clipped
    n["declined"] = fr.declined
    return n


# --------------------------------------------------------------------------- build

def build(cfg: dict, donors=None) -> Canvas:
    p = {**SKY, **(cfg or {})}
    for k in ("anchor", "lot"):
        if not p.get(k):
            raise ValueError(f"the sky needs {k}")
    dv, du = int(p["lot"][0]), int(p["lot"][1])
    at = [int(x) for x in (p.get("at") or (0, 0))]
    anchor = [int(x) for x in p["anchor"]]
    ax, ay, az = anchor[0] + at[0], anchor[1], anchor[2] + at[1]
    c = Canvas(dv, int(p["sy"]), du, donors)
    seed = int(p["seed"])

    parts, isles = {}, []
    for i, spec in enumerate(p["isles"] or ()):
        q = dict(spec)
        q["y"] = int(q["y"]) - ay               # the config says WORLD Y; the canvas is lot-local
        got = _isle(c, q, seed + i * 13)
        isles.append(got)
        for k, v in got.items():
            parts["isle " + k] = parts.get("isle " + k, 0) + v
    parts["isles"] = len(isles)

    for i, spec in enumerate(p.get("birds") or ()):
        q = dict(spec)
        q["y"] = int(q["y"]) - ay
        q.setdefault("seed", seed + i * 7)
        for k, v in _bird(c, q).items():
            parts[f"bird{i + 1} {k}"] = v
    parts["birds"] = len(p.get("birds") or ())

    if p.get("plane"):
        q = dict(p["plane"])
        q["y"] = int(q["y"]) - ay
        for k, v in _plane(c, q).items():
            parts["plane " + k] = v

    c.world_origin = (ax, ay, az)
    c.meta = {
        "kind": "skies",
        "lot": [dv, du],
        "at": at,
        "land": "frontier",
        "facing": (p.get("plane") or {}).get("facing", "north"),
        "profile_axis": "v",
        "parts": parts,
        "note": ("Disconnected BY DESIGN: every isle and the aircraft is its own piece, hanging "
                 "in open air over the Lost Plateau. A component count of one would mean they "
                 "were touching, which is the one thing a sky composition must not do."),
    }
    return c
