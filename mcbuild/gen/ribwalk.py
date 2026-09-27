"""THE RIB WALK - a colossal skeleton the causeway walks THROUGH.

**IT IS NOT AN OBJECT ON A PLINTH, AND THAT IS THE WHOLE POINT.** Four subjects were block-out and
rejected for this stop - an ammonite, a pterosaur skull, a hatching egg, a dragonfly, a claw, a
tree fern - and the fault they shared was the REGISTER rather than the shape: every one was a
thousand-to-ten-thousand block object standing beside the walk, matched to the balloon and the
wyrm. Nothing on this island that inspires awe is that. The Abyss Squid hangs in the void under
the park, the Wyrm Gate straddles a live railway, the Mine Ridge has a coaster cut through it.
**What they have in common is that they USE THEIR SITE**, and the causeway's own unused resource
is that it is a walkway over nothing at all.

So the sculpture is the corridor. The spine arches overhead, the ribs come down either side of the
deck, and - the move only this bridge can offer - **THEY CARRY ON PAST IT INTO THE VOID**, so a
guest at the rail looks down and the cage continues under their feet with nothing below it.

**AND A SKELETON IS THE ONE SHAPE THIS MEDIUM CANNOT GET WRONG.** CLAUDE.md, on the Lost Plateau's
bone bed: *"a spine is a line, a rib is a curve one block thick, a skull is a small box with holes
in it. The plan is the money view, which voxels give away free."* There is no barrel, no haunch, no
compound muscle and above all NO LIMBS - so the failure that retired eight mammals, then the
stegosaur after four rounds of polish, then the ankylosaur after six, is structurally impossible
here. That is not a hope about execution, it is a property of the subject.

    mass      the spine, arched along the walk, swelling to the middle
    ribs      one cell thick, splayed, with real sky between them, carried below the deck
    skull     a gate at the far end: cranium over the walk, jaws either side of it, two orbits
    weather   a scatter of a second tone, because 4,000 identical bone cells is a plastic toy
"""
from __future__ import annotations

import math

import json

from mcbuild import nbt, schem
from mcbuild.gen import loft
from mcbuild.gen.canvas import Canvas, hash01

RIBWALK = {
    "kind": "ribwalk",
    "length": 75,              # NOSE TO LAST RIB, along the walk
    "facing": "north",
    "at": None,
    "deck": 7,                  # the walking course, in canvas coordinates
    "seed": 0,
    # **THE SKULL IS OFF BY DEFAULT, and that is a decision rather than an omission.** Built, it
    # came out a filled oval plate with a slot in it - consecutive rings overlap and fill - and a
    # skull is a box with HOLES in it or it is nothing. More to the point this park already has a
    # walk-through skull at the Wyrm Gate, and repeating it here is the reason the gecko and the
    # bat were removed from the hollow reach. The cage alone is the stronger object.
    "skull": False,
    "refuse": [],               # litematics whose cells this may never take
    "title": "THE RIB WALK",
    "lines": ["walk the length", "of it, and look", "over the rail"],
}

#: `bone_block` is a `rotated_pillar`, so `shell.slab_for` will never offer it a partial - which is
#: why there is no surfacing pass here and none is wanted. A skeleton is drawn in lines.
HIDE = {
    "bone": "bone_block",          # L225
    # **A SECOND TONE, OR IT IS A PLASTIC TOY.** Four thousand identical cells of the palest block
    # in the palette read as moulded plastic at any scale; a scatter of a duller, cooler stone is
    # what makes it read as something dug up. `smooth_stone` is 66 of luminance under bone, which
    # is a real step by this file's own measure and nowhere near a second colour.
    "weathered": "smooth_stone",   # L159
    "dark": "deepslate_bricks",    # L71 - the orbits' shadow, and the vertebral gaps
}


def _dims(L: float) -> dict:
    """Every number a FRACTION OF THE LENGTH, never a block count - this file's named trap."""
    return {
        "L": L,
        # the cage: how far over the deck the spine arches, how wide the ribs splay, and how far
        # they carry on BELOW it. The drop is what makes the void part of the sculpture.
        # **BIG ENOUGH THAT THE DECK IS INSIDE IT.** At 0.225 the cage was 34 across on an 89-wide
        # causeway and read as an ornament standing on the middle of a broad path rather than as
        # something the bridge goes through. The ribs have to come down OUTSIDE the walk and
        # outside the benches, so more of the deck is within the cage than beside it.
        "arch": 0.320 * L,
        "half": 0.300 * L,
        "drop": 0.220 * L,
        "ribs": 21,
        # **A RIB IS A LINE, NOT A SLAB.** At 0.021 of the length each rib is four to five cells
        # across and twenty of them read as a culvert with stripes; the whole reason a ribcage
        # works in this medium is that "a rib is a curve ONE BLOCK THICK" and the sky between them
        # is the feature. Same rule as the frog's hand and the ladybird's spot spacing.
        "rib_r0": 0.013 * L,       # at the spine
        "rib_r1": 0.006 * L,       # at the tip
        # the spine itself
        "vert_r": 0.026 * L,
        "vert_every": 3,           # a taller vertebra every N ribs
        "neural": 0.055 * L,       # the spines standing up off it
        # the skull, as a fraction of the whole
        "skull_len": 0.230 * L,
        "skull_half": 0.150 * L,
        "skull_high": 0.215 * L,
        "orbit_r": 0.050 * L,
        "jaw_drop": 0.085 * L,
    }


def _profile(d: dict, t: float) -> tuple:
    """(arch, half) at t along the cage - it swells to the middle and closes at both ends.

    **A CONSTANT SECTION IS A TUNNEL, NOT A RIBCAGE.** The first block-out ran every rib at one
    height and read as a culvert with stripes on it; what makes a cage read is that it has a widest
    point and closes toward the neck and the tail, which is also what a real one does.
    """
    s = math.sin(math.pi * min(1.0, max(0.0, t))) ** 0.42
    return d["arch"] * (0.34 + 0.66 * s), d["half"] * (0.42 + 0.58 * s)


def _rib(fr: loft.Frame, d: dict, f: float, sgn: int, arch: float, half: float, deck: float,
         seed: int) -> int:
    """One rib: a curve from the spine, out over the deck, and DOWN PAST IT into the void.

    **ONE CELL THICK ALONG THE WALK.** A rib swept as a tube is a hoop, and twenty hoops are a
    tunnel; what makes a ribcage is the SKY BETWEEN THE RIBS, which is the same rule as the frog's
    hand and the ladybird's spot spacing - the negative space is the feature.

    **AND A THIN CURVE HAS TO BE THREADED, NOT SWEPT.** Thinning the ribs from four cells to one
    took the model from seven pieces to THREE HUNDRED AND SIXTY: below about r=0.9 a ball is a
    single cell, and two consecutive cells whose centres moved on two axes at once are DIAGONAL
    neighbours, not connected. It cost the pterosaur three spans and the stegosaur its tail spikes
    before the rule was written down; `loft.thread` fills every corner ONE AXIS AT A TIME and is
    the only thing that makes a thin curve connected by construction rather than by luck.
    """
    n = 0
    lo = -d["drop"]
    amax = math.acos(max(-0.999, min(0.999, lo / max(1.0, arch))))
    steps = max(30, int(arch * 2.6))
    prev = None
    for i in range(steps + 1):
        t = i / float(steps)
        a = amax * t
        pt = (f, sgn * half * math.sin(a), deck + arch * math.cos(a))
        key = "weathered" if hash01(int(f), int(pt[2]), i, 13, seed) < 0.17 else "bone"
        if prev is not None:
            n += loft.thread(fr, prev, pt, key)
        prev = pt
        r = d["rib_r0"] + (d["rib_r1"] - d["rib_r0"]) * t
        if r > 0.85:
            # thin along the WALK (ra) and wider across the cage, so it reads as a rib rather
            # than as a rod: a rib is a flattened blade in life and has to be one here.
            n += loft.ball(fr, pt[0], pt[1], pt[2], 0.5, key, rs=r, ry=r)
    return n


def _spine(fr: loft.Frame, d: dict, f0: float, f1: float, deck: float, seed: int) -> int:
    """The backbone along the crown, with a vertebra and a neural spine at each rib."""
    n = 0
    lo, hi = int(math.floor(min(f0, f1))), int(math.ceil(max(f0, f1)))
    every = max(1, int(round((hi - lo) / float(d["ribs"]))))
    # **THE CROWN LINE IS THREADED, because `sin(pi*t)**0.42` falls away VERTICALLY at both ends.**
    # Its derivative is unbounded as t approaches 0 or 1, so the last two spine stations differ by
    # more than a course, which makes them diagonal neighbours and not connected: the model shipped
    # with a 21-cell vertebra floating off the tail, one piece out of two, and it audits clean
    # because a detached vertebra is a legal block. A profile is a curve; a curve gets threaded.
    prev = None
    for f in range(lo, hi + 1):
        t0 = (f - lo) / float(max(1, hi - lo))
        a0, _h = _profile(d, t0)
        here = (float(f), 0.0, deck + a0)
        if prev is not None:
            n += loft.thread(fr, prev, here, "bone")
        prev = here
    for f in range(lo, hi + 1):
        t = (f - lo) / float(max(1, hi - lo))
        arch, _half = _profile(d, t)
        y = deck + arch
        big = (f - lo) % every == 0
        r = d["vert_r"] * (1.25 if big else 0.85)
        for du in range(-int(r) - 1, int(r) + 2):
            for dy in range(-int(r) - 1, int(r) + 2):
                if (du / max(0.5, r)) ** 2 + (dy / max(0.5, r)) ** 2 > 1.0:
                    continue
                key = "weathered" if hash01(f, int(y) + dy, du, 7, seed) < 0.14 else "bone"
                if fr.put(f, du, y + dy, key):
                    n += 1
        if big:
            for k in range(int(d["neural"])):
                w = 1 if k < d["neural"] * 0.55 else 0
                for du in range(-w, w + 1):
                    if fr.put(f, du, y + r + k, "bone"):
                        n += 1
    return n


def _skull(fr: loft.Frame, d: dict, f0: float, deck: float, seed: int) -> dict:
    """A gate at the head end: the cranium over the walk, the jaws either side, two orbits.

    **THE WALK GOES THROUGH IT**, which is the whole reason it is here rather than on a plinth -
    and it is the Wyrm Gate's own move, which this park has already proved reads.
    """
    n, orb = 0, 0
    L = d["skull_len"]
    for i in range(int(L)):
        t = i / max(1.0, L - 1.0)
        f = f0 + i
        # the cranium narrows and drops toward the snout
        hw = d["skull_half"] * (1.0 - 0.45 * t ** 1.3)
        ht = d["skull_high"] * (1.0 - 0.40 * t ** 1.5)
        for a in range(0, 360, 4):
            th = math.radians(a)
            # the lower half is the JAW, carried below the deck so the walk is clear
            x = hw * math.cos(th)
            y = deck + d["jaw_drop"] * 0.0 + ht * math.sin(th)
            if -0.35 < math.sin(th) < 0.35 and abs(x) < hw * 0.55:
                continue                      # the mouth: the opening you walk through
            for dr in range(2):
                X = x - dr * 0.7 * math.cos(th)
                Y = y - dr * 0.7 * math.sin(th)
                key = "weathered" if hash01(int(f), int(Y), a, 5, seed) < 0.16 else "bone"
                if fr.put(f, X, deck + Y - deck, key):
                    n += 1
    # the orbits, punched through both sides
    for sgn in (1, -1):
        cf = f0 + L * 0.34
        cy = deck + d["skull_high"] * 0.62
        cx = sgn * d["skull_half"] * 0.80
        r = d["orbit_r"]
        for df in range(-int(r) - 1, int(r) + 2):
            for dy in range(-int(r) - 1, int(r) + 2):
                if (df / r) ** 2 + (dy / r) ** 2 > 1.0:
                    continue
                for dx in range(-3, 4):
                    v, u = fr.at(loft.r(cf + df), loft.r(cx + dx))
                    y = loft.r(cy + dy)
                    if fr.c.inb(v, y, u) and fr.c.solid(v, y, u):
                        fr.c.put(v, y, u, 0)
                        orb += 1
    return {"skull": n, "orbit": orb}


def build_ribwalk(cfg: dict, donors=None) -> Canvas:
    p = {**RIBWALK, **(cfg or {})}
    L = float(p.get("length") or 104) * float(p.get("scale") or 1.0)
    if L < 48:
        raise ValueError(
            "a rib walk under 48 blocks cannot be walked through: the arch has to clear a "
            "player's head over a deck that is already thirteen wide, and below that it is a "
            "hoop over a path rather than a cage you are inside")
    d = _dims(L)
    facing = str(p.get("facing", "north"))
    if facing not in loft.STEP:
        raise ValueError(f"a rib walk needs a real facing, not {facing!r}")
    seed = int(p.get("seed") or 0)

    # **THE DECK'S HEIGHT IS DERIVED FROM THE DROP, NOT PASSED IN.** The ribs and the jaws carry
    # BELOW the walk - that is the whole idea - so a deck at a fixed 7 puts nineteen blocks of
    # cage under the canvas floor: 25,565 cells clipped, a skull that placed NOTHING, and a render
    # that still showed a plausible ribcage. The sauropod's own recorded disaster, and the reason
    # `clipped` is counted apart from `refused`.
    deck = max(float(p.get("deck") or 0),
               math.ceil(max(d["drop"], d["skull_high"] * 0.55)) + 4)
    span_fore = int(math.ceil(L + d["skull_len"])) + 6
    span_back = 8
    width = int(math.ceil(d["half"] * 2)) + 10
    sy = int(math.ceil(deck + d["arch"] + d["neural"])) + 6
    width = max(width, int(math.ceil(d["skull_half"] * 2)) + 10)

    along_x = facing in ("east", "west")
    sx = (span_fore + span_back + 1) if along_x else width
    sz = width if along_x else (span_fore + span_back + 1)
    c = Canvas(sx, sy, sz, donors)
    # **THE ORIGIN GOES WHERE THE CONTENT IS NOT.** `Frame.at` maps forward as `cu + fz * f`, so
    # for a north-facing piece u DECREASES with f - and this design's content is entirely at
    # POSITIVE f, unlike an animal which straddles its own origin. Set to the back margin, every
    # cell of a 128-long cage mapped off the canvas: 25,565 clipped, a skull that placed NOTHING,
    # and a render that still showed a plausible ribcage because what survived was the near end.
    if along_x:
        cv = span_back if facing == "east" else span_fore
        cu = sz // 2
    else:
        cu = span_back if facing == "south" else span_fore
        cv = sx // 2
    fr = loft.Frame(c, cv, cu, facing, HIDE)

    # **THE CAUSEWAY IS REFUSED CELL BY CELL, so "the bridge was built THROUGH it" is a property of
    # the construction rather than a number to hope for.** The Wyrm Gate does the same thing to a
    # live railway. What it buys is the whole idea: a rib arrives at the deck, stops, and picks up
    # again underneath, so the walk reads as a cut through a fossil rather than a hoop over a path.
    keep = set()
    if p.get("refuse") and p.get("at"):
        ax, ay, az = (int(v) for v in p["at"])
        for path in p["refuse"]:
            om = schem.load(path)
            osc = json.load(open(str(path).rsplit(".", 1)[0] + ".scan.json"))
            bx, by, bz = osc["origin"]["x"], osc["origin"]["y"], osc["origin"]["z"]
            ys, zs, xs = (om.ids > 0).nonzero()
            for y, z, x in zip(ys.tolist(), zs.tolist(), xs.tolist()):
                keep.add((bx + x - ax, by + y - ay, bz + z - az))
    fr.taken = keep

    # **A PART'S COUNT IS UNIQUE CELLS, NEVER `put()` CALLS.** A thread and a sweep overlap by
    # construction, so the call count is an artefact of how a part is DRAWN: it read 20,258 ribs on
    # a 13,978-cell model. Counted by diffing the canvas the numbers partition the build, and on
    # the ankylosaur that is what exposed a pair of horns placing 124 blocks and gaining none.
    def _cells():
        return {(x, y, z) for y, z, x in zip(*(c.ids > 0).nonzero())}

    parts, seen = {}, set()

    def _step(fn):
        nonlocal seen
        fn()
        now = _cells()
        got = now - seen
        seen = now
        return len(got)

    parts["spine"] = _step(lambda: _spine(fr, d, 0, L, deck, seed))

    def _all_ribs():
        for k in range(d["ribs"]):
            t = (k + 0.5) / d["ribs"]
            arch, half = _profile(d, t)
            for sgn in (1, -1):
                _rib(fr, d, t * L, sgn, arch, half, deck, seed)

    parts["ribs"] = _step(_all_ribs)
    if p.get("skull"):
        parts["skull"] = _step(lambda: _skull(fr, d, L, deck, seed))

    if p.get("at"):
        c.world_origin = tuple(int(v) for v in p["at"])
    c.meta = {
        "kind": "ribwalk",
        "facing": facing,
        "length": round(L, 1),
        "profile_axis": "u" if along_x else "v",
        "refused": fr.refused,
        "clipped": fr.clipped,
        "declined": fr.declined,     # cells the causeway owns: the cut through the fossil
        "parts": parts,
        "contract": (
            "a colossal skeleton the causeway walks THROUGH: a spine arched over the deck, ribs "
            "one cell thick with real sky between them carried DOWN PAST the deck into the void, "
            "and a skull at the head end whose mouth is the gate. Not an object beside the walk."),
    }
    return c


build = build_ribwalk
DEFAULTS = RIBWALK
