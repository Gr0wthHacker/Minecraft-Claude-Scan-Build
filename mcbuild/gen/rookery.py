"""THE RIM ROOKERY - the clifftop behind the railway, where the sauropod stands.

Jack: *"what about the area behind the railway where the dinosaur is, that whole area needs to be
refined, i like the eggs and the idea of other small things there."*

---------------------------------------------------------------------------------------------
THE MEASUREMENT, AND IT IS ONE NUMBER

The Frontier's rim is V187-199 by U0-172 - 2,249 columns, the only band in the land with real
room, the only one against the void, and the only one a guest reaches by TRAIN rather than on
foot. Measured over the shipped park, split at the sauropod:

    sauropod end U0-70    923 columns . 57% carry something . tallest 50 . 504 columns over 6
    colony end  U71-172  1,326 columns . 37% carry something . TALLEST 5 . ZERO over 6

**A HUNDRED AND TWO BLOCKS OF NESTING COLONY WITH NOTHING IN IT OVER THREE COURSES TALL**, at 0.6
blocks per column. That is not a shortage of ideas, it is a shortage of HEIGHT: this file's own
Frontier note says it outright - *"on this moss, under ten-tall trees, architecture below ~6
courses dissolves into ground noise"* - and the previous rim design was a 3-wide walk, four
scrapes and two snags, every one of them under it.

---------------------------------------------------------------------------------------------
WHAT A ROOKERY ACTUALLY HAS, AND WHY EACH PIECE EARNS ITS PLACE

    perch stacks   the SKYLINE, and the whole reason this exists. Sea stacks of the rim's own
                   rock, 8-14 courses, guano-capped - what an adult pterosaur roosts on, and
                   isolated COLUMNS, so they frame the void view the reserve protects rather
                   than walling it.
    nests          more of them, and in variety: full clutches, part-hatched, and empty scrapes
                   with the shell still in them. `pterosaur.nest` already builds one, for the
                   recorded reason - an egg is a DOME and the canonical view of a nest is the
                   PLAN, which are the two things this medium gives away free.
    hatchlings     juveniles on the ground beside a nest. A small folded animal is one convex
                   mass with a pattern on it - the ladybird's category, and the only kind of
                   creature this repo has ever built at five blocks and had read.
    the hide       a timber observation hide ON the walk, with a viewing slit facing the colony.
                   A route with somewhere to STAND on it is somewhere to be; the walk had no
                   destination and no reason to exist beyond the nests it passed.
    the bone find  a partial skeleton weathering out at the drop. A skeleton is pure planar,
                   which is the one animal shape this medium cannot get wrong.
    the cliff rail a fence along the drop, with gaps. You are on a clifftop over open void and
                   there was nothing to say so - it reads as a viewpoint, not as an edge case.
    the belly deck the payoff. The sauropod's GROUND footprint is four feet; U33-45 under its
                   barrel is thirteen blocks of completely open lawn, and standing there looking
                   up is the best moment on this strip. It was empty grass.

---------------------------------------------------------------------------------------------
THE WALK GOES UNDER THE ANIMAL, AND THE LEGS DECIDE HOW WIDE IT IS

Measured off `PF Sauropod`'s own artifact at the ground course, the animal occupies only
**U28-32 and U46-50** - two rows of feet - and inside each row the near leg is V188-192 and the
far one V194-198, so **V193 is clear straight through**. Everywhere else under the barrel is open.

So the walk is DECLARED five wide under the animal and the legs carve it down to one: `_walk`
places only where the world's own ground is lawn, so a three-row squeeze between two feet is what
the geometry gives rather than something anybody special-cased. Squeezing past a dinosaur's foot
on a boardwalk is the point of putting a walk there at all.

**NOTHING KEEPS OUT OF THE SAUROPOD BY BOX.** Its silhouette is 11 of the band's 13 courses, so a
keep-out box would forfeit 63 blocks of the strip - most of it open ground under a belly twenty
courses up. Every piece here asks `_Ground.free` per CELL as it rises, and a stack checks two
courses of clearance over its own crown, so the animal stops the tall things and lets the low ones
stand under it. That is the ground probe doing its job instead of a table guessing.
"""
from __future__ import annotations

from . import claimrow as cr
from . import pterosaur as pt
from .canvas import Canvas, hash01
from .frontier_builds import _Lot
from .frontier_scatter import _Ground, flora_for, shipped_cells
from .vertical import Ctx

NORTH, SOUTH, EAST, WEST = "north", "south", "east", "west"
_FACE_STEP = {NORTH: (0, -1), SOUTH: (0, 1), EAST: (1, 0), WEST: (-1, 0)}

#: **A MEASURED VALUE LADDER ACROSS FAMILIES, and this repo has now got it wrong in five separate
#: places by searching WITHIN one.** `blocks.color(name, "side")`, cheap-or-ok and on the 1.19
#: server: cobbled_deepslate 77 . dripstone_block 112 . cobblestone 127 . diorite 188 .
#: bone_block 225 . white_wool 236. Smallest adjacent step 15, biggest 61, against the ~15 below
#: which a tone stops being a tone. `tests/test_rookery.py` re-derives it rather than trusting
#: this comment.
KIT = {
    "dark": "cobbled_deepslate",       # L77  - the stack's own body, and the nest rim
    "warm": "dripstone_block",         # L112 - the one warm tone, so five greys are not five greys
    "wash": "cobblestone",             # L127
    "pale": "diorite",                 # L188 - the weathered upper stack
    "guano": "white_wool",             # L236 - the cap and the streaks. A rookery is WHITE on top
    "bone": "bone_block",              # L225 - eggs, and the skeleton
    "crust": "gravel",                 # RULE 13: top course only, always over solid ground
    "moss": "moss_block",
    "turf": "moss_carpet",
    # timber - the hide, the boardwalk and the rail, in the land's own spruce
    "post": "spruce_log",
    "beam": "stripped_spruce_log",
    "plank": "spruce_planks",
    "slab": "spruce_slab",
    "stair": "spruce_stairs",
    "fence": "spruce_fence",
    "gate": "spruce_fence_gate",
    "shutter": "spruce_trapdoor",
    "sign": "spruce_wall_sign",
    "pane": "glass_pane",
    # the animals
    "hide_dark": "gray_wool",          # a folded wing, read against sky
    "hide_body": "brown_wool",
    "hide_pale": "light_gray_wool",
    "crest": "red_wool",               # the land's own show tone, and the pterosaur's identity
    "eye": "black_wool",
    # fittings
    "glow": "ochre_froglight",         # flush: it IS the floor, and nobody knocks it off a walk
    "lamp": "lantern",
    "barrel": "barrel",
}

#: Rule 15, answered by `shipped_cells` off this design's own artifact. What stays here is the one
#: thing that is genuinely ground cover rather than anybody's build.
OWN = frozenset({"moss_carpet"})

ROOKERY = {
    "kind": "rookery",
    "lot": None,                 # [dv, du]
    "at": None,                  # [V, U]
    "anchor": [97500, 203, 80300],
    "under": None,               # the world it is verified against - ASK THE SAME ONE
    "previous": None,            # this design's own artifact, for rule 15
    "keep_out": [],
    #: [{v, w, u0, u1}] - the walk, in segments along U. DECLARED width; the world carves it.
    "walks": [],
    #: [[v, u, h]] - perch stacks. `h` is the crown height in courses.
    "stacks": [],
    #: [[v, u, eggs]] - a scrape. NEGATIVE eggs means HATCHED: the shell, and no whole egg.
    "nests": [],
    #: [[v, u, facing]] - a juvenile on the ground.
    "hatchlings": [],
    #: [[v, u]] - a partial skeleton weathering out of the rim.
    "bones": [],
    #: [[v, u]] - crates and a specimen table.
    "kit": [],
    "hide": None,                # {v, u, facing, title}
    "deck": None,                # {v, u, dv, du, title}
    "rail": None,                # {v, every}  - the fence along the drop, with gaps
    "plaques": [],               # [{v, u, facing, lines}]
    "plant": None,               # {step, density, kinds} - claimrow's own sweep
    "flora": "jungle",
    "clear": 1,
    "seed": 0,
    "title": "THE ROOKERY",
}


# --------------------------------------------------------------------------- the walk


#: What a walk needs under it and over it. `_Ground.lawn` demands NINE clear courses, which is
#: right for a tree and wrong for a path.
_HEADROOM = 3


def underfoot(g: _Ground, v: int, u: int, head: int = _HEADROOM) -> bool:
    """Ground you can lay a path on: lawn under it, and `head` courses of headroom over it.

    **A WALK NEEDS HEADROOM, NOT SKY**, and using `lawn()` for both is what put a one-cell hole in
    this walk at U48. The sauropod's legs merge into its barrel as they rise, so V193 - the gap the
    boardwalk threads between its feet - is open at the ground and closed nine courses up. `lawn()`
    saw that as an occupied column and refused the cell, which is exactly the right answer for a
    tree and exactly the wrong one for the path this design exists to run under the animal.
    """
    if g.owned(v, u) or not (0 <= v < g.dv and 0 <= u < g.du):
        return False
    x, z = g.world(v, u)
    if g.ctx.name_at(x, g.ay - 1, z).split(":")[-1] not in ("moss_block", "moss_carpet"):
        return False
    return all(g.free(v, u, y) for y in range(head))


def _walk(lot: _Lot, g: _Ground, spec: dict, seed: int) -> dict:
    """One segment of the cliff walk, along U at a declared V.

    **THE WIDTH IS DECLARED AND THE WORLD CARVES IT.** Under the sauropod the walk asks for five
    and the two rows of feet leave it one, which is exactly the squeeze a boardwalk past a
    dinosaur's leg should be - and it falls out of `g.lawn` refusing the leg cells rather than out
    of anybody special-casing two ranges of U.
    """
    v0, w = int(spec["v"]), int(spec.get("w", 3))
    u0, u1 = int(spec["u0"]), int(spec["u1"])
    every = max(4, int(spec.get("glow_every", 13)))
    cells = kerb = glow = 0
    laid = 0
    for u in range(u0, u1 + 1):
        row = 0
        for k in range(w):
            v = v0 + k
            if not underfoot(g, v, u) or lot.has(v, 0, u):
                continue
            row += 1
            if k == w // 2 and u % every == every // 2:
                glow += 1 if lot.put(v, 0, u, KIT["glow"]) else 0
                continue
            r = hash01(v * 3 + 2, u * 7 + 5, seed + 5)
            key = "wash" if r < 0.40 else ("dark" if r < 0.68 else
                                           "crust" if r < 0.88 else "warm")
            cells += 1 if lot.put(v, 0, u, KIT[key]) else 0
        laid += 1 if row else 0
        for k in (-1, w):
            v = v0 + k
            if underfoot(g, v, u) and not lot.has(v, 0, u) and hash01(v, u, seed + 6) < 0.70:
                kerb += 1 if lot.slab(v, 0, u, KIT["dark"] + "_slab", "bottom") else 0
    return {"v": [v0, v0 + w - 1], "u": [u0, u1], "rows": laid,
            "cells": cells, "kerb": kerb, "glow": glow}


# --------------------------------------------------------------------------- the skyline


def _stack(lot: _Lot, g: _Ground, v0: int, u0: int, h: int, seed: int) -> dict:
    """A sea stack: a tapering pinnacle of the rim's own rock, guano-capped.

    **THIS IS THE ONE PIECE THE STRIP ACTUALLY NEEDED.** The colony measured ZERO columns over six
    courses in a hundred and two blocks; nothing else here is taller than a nest rim. A stack is a
    COLUMN and not a wall, so it gives the band a skyline without closing the outward sightline the
    rim reserve exists to protect - the same reason the void tower's merlons read from above and a
    solid parapet would not.

    It stops where the world stops it: two clear courses over the crown, so a stack under the
    sauropod's barrel comes out as a boulder rather than as a spike through the animal.
    """
    out = {"at": [v0, u0], "h": 0, "cells": 0, "clipped": False}
    n = 0
    top = 0
    for y in range(h):
        # **A SEA STACK IS A PILLAR WITH A HEAD, NOT A SPIKE.** Tapered smoothly to nothing the
        # first build came out as a chimney - a one-wide column of alternating tones with a white
        # cap on it, which reads as a smokestack or a totem and not as rock. What makes the shape
        # is a flared foot, a waisted shaft and a crown that OVERHANGS it.
        t = y / max(1, h - 1)
        if t < 0.22:
            r = 3.4 - 1.0 * (t / 0.22)            # the flared foot
        elif t < 0.70:
            r = 2.4 - 0.7 * ((t - 0.22) / 0.48)   # the waisted shaft
        else:
            r = 1.7 + 0.9 * ((t - 0.70) / 0.30)   # ...and the head
        # **THE CROWN IS CORBELLED, WHICH IS THE ONLY WAY A VOXEL OVERHANG GETS BUILT.** A strict
        # "something directly below" rule cannot widen a column at all, so the head never formed
        # and every stack came out as a spike whatever the profile said. Placing each course from
        # the CENTRE OUTWARD lets a cell lean on the one already laid beside it - one cell of
        # corbel per course, which is what the shape needs and no more.
        ring = sorted(((dv, du) for dv in range(-4, 5) for du in range(-4, 5)),
                      key=lambda c: c[0] * c[0] + c[1] * c[1])
        for dv, du in ring:
            d = (dv * dv + du * du) ** 0.5
            jit = (hash01(v0 + dv, u0 + du, y, seed + 81) - 0.5) * 0.9
            if d > r + jit:
                continue
            a, b = v0 + dv, u0 + du
            if not g.lawn(a, b):
                continue
            # TWO CLEAR COURSES OVER THE CROWN, or a stack grows into whatever is above it
            if not (g.free(a, b, y) and g.free(a, b, y + 1) and g.free(a, b, y + 2)):
                out["clipped"] = True
                continue
            if lot.has(a, y, b):
                # **A PIECE NEVER OVERWRITES A PIECE.** `Canvas.put` overwrites, so two footprints
                # that touch corrupt each other silently - a nest rim reappearing as the base
                # course of a stack, with nothing in the audit, the BOM or the component count to
                # say so. The colony is laid BEFORE the skyline and the skyline yields, because a
                # scrape with eggs in it is the thing Jack asked for.
                continue
            if y and not (lot.has(a, y - 1, b)
                          or lot.has(a - 1, y, b) or lot.has(a + 1, y, b)
                          or lot.has(a, y, b - 1) or lot.has(a, y, b + 1)):
                continue                           # nothing floats, and nothing corbels twice
            q = hash01(a, b, y, seed + 82)
            key = ("dark" if q < 0.34 else "warm" if q < 0.55 else
                   "wash" if q < 0.80 else "pale")
            if y >= h - 3 and q < 0.55:            # the weathered head, one rung up the ladder
                key = "pale"
            n += 1 if lot.put(a, y, b, KIT[key]) else 0
            top = max(top, y)
    # THE GUANO IS WHAT MAKES IT A ROOST RATHER THAN A ROCK, and it is 159 of luminance clear of
    # the stone under it. **THE CROWN, AND THE OUTER FACE OF THE HEAD - NEVER A STREAK DOWN THE
    # SHAFT.** Hashed course by course down the whole pillar it came out as bands, which on a
    # one-wide column is a barber pole; the same mistake the deck soffit made hashing on the
    # course instead of the cell, in a different direction.
    for dv in range(-4, 5):
        for du in range(-4, 5):
            a, b = v0 + dv, u0 + du
            if not lot.has(a, top, b):
                continue
            # **PATCHY, NOT A DISC.** Laid over the whole crown it is a flat white plate and the
            # stack reads as a mushroom - which is the same failure as a coat with no tonal
            # variation, at the one place on this design the eye goes first. The edge of the crown
            # always takes it, because that is the lip the birds sit on.
            edge = not (lot.has(a - 1, top, b) and lot.has(a + 1, top, b)
                        and lot.has(a, top, b - 1) and lot.has(a, top, b + 1))
            if edge or hash01(a, b, seed + 83) < 0.55:
                n += 1 if lot.put(a, top, b, KIT["guano"]) else 0
            # ...and one course down, but only where the head actually overhangs something
            if lot.has(a, top - 1, b) and not lot.has(a, top - 2, b):
                n += 1 if lot.put(a, top - 1, b, KIT["guano"]) else 0
    out["h"], out["cells"] = top + 1, n
    return out


# --------------------------------------------------------------------------- the colony


def _nest(lot: _Lot, g: _Ground, v0: int, u0: int, eggs: int, seed: int) -> dict:
    """A scrape. `eggs >= 0` is a clutch; NEGATIVE is a nest that has already HATCHED.

    A clutch is `pterosaur.nest` unchanged - an egg is a dome and a nest is read in plan, which is
    why it works at this size. What is new is the hatched one: the same scrape with broken shell in
    it instead of whole eggs, so a colony reads as a colony over a season rather than as one
    photograph repeated.
    """
    if eggs >= 0:
        out = pt.nest(lot, g, v0, u0, eggs, seed)
        out["hatched"] = False
        return out
    got = pt.nest(lot, g, v0, u0, 0, seed)
    n, shell = got["cells"], 0
    r = 3 + (-eggs) // 2
    for k in range(-eggs * 3):
        a = v0 + int((hash01(v0, u0, k, seed + 91) - 0.5) * 2 * (r - 1.5))
        b = u0 + int((hash01(v0, u0, k, seed + 92) - 0.5) * 2 * (r - 1.5))
        if not (g.lawn(a, b) and g.free(a, b, 1)) or not lot.has(a, 0, b):
            continue
        shell += 1 if lot.put(a, 1, b, KIT["bone"]) else 0
    got.update({"cells": n + shell, "hatched": True, "shell": shell, "eggs": 0})
    return got


def _hatchling(lot: _Lot, g: _Ground, v0: int, u0: int, facing: str, seed: int) -> dict:
    """A juvenile pteranodon on the ground: a folded body, a big head and a crest.

    **ONE CONVEX MASS WITH A PATTERN ON IT** - the ladybird's category, and the only shape this
    repo has ever built at five blocks and had a stranger name. The wings are FOLDED, because a
    spread wing at this size is two cells and reads as nothing; what carries it is the head, which
    on a juvenile pterosaur is nearly half the animal.
    """
    fv, fu = _FACE_STEP.get(facing, _FACE_STEP[SOUTH])
    sv, su = -fu, fv
    out = {"at": [v0, u0], "facing": facing, "cells": 0}
    n = 0

    def put(f, s, y, key):
        a, b = v0 + fv * f + sv * s, u0 + fu * f + su * s
        if not (g.lawn(a, b) and g.free(a, b, y)):
            return 0
        return 1 if lot.put(a, y, b, KIT[key]) else 0

    for f in range(-2, 1):                          # the body, tapering to the tail
        for s in (-1, 0, 1):
            if f == -2 and s:
                continue
            n += put(f, s, 0, "hide_body")
    for s in (-1, 1):                               # the folded wings, over the flanks
        n += put(-1, s, 1, "hide_dark")
        n += put(0, s, 1, "hide_dark")
    n += put(0, 0, 1, "hide_body")                  # the shoulders
    n += put(1, 0, 1, "hide_body")                  # the neck
    for s in (-1, 0, 1):                            # the head, and it is the big half
        n += put(2, s, 1, "hide_pale" if s else "hide_body")
    n += put(2, 0, 2, "crest")                      # the crest, straight up off the crown
    n += put(3, 0, 2, "crest")
    n += put(3, 0, 1, "bone")                       # the beak
    n += put(4, 0, 1, "bone")
    for s in (-1, 1):
        n += put(2, s, 2, "eye")
    out["cells"] = n
    return out


def _bones(lot: _Lot, g: _Ground, v0: int, u0: int, seed: int) -> dict:
    """A partial skeleton weathering out of the rim: a spine, some ribs and half a skull.

    A SKELETON IS PURE PLANAR, which is the one animal shape this medium cannot get wrong - sheets
    and tapers, and the plan is the money view. It is laid ALONG U so the walk reads it side-on.
    """
    out = {"at": [v0, u0], "cells": 0, "ribs": 0}
    n = 0

    def bed(a, b):
        """The matrix it is weathering OUT of. A skeleton laid flat on moss is a floor decal;
        what makes a bone bed read is that the bones stand PROUD of the rock around them."""
        if g.lawn(a, b) and g.free(a, b, 0) and not lot.has(a, 0, b):
            return 1 if lot.put(a, 0, b, KIT["dark"]) else 0
        return 0

    for k in range(-2, 10):
        for j in (-2, -1, 0, 1, 2):
            n += bed(v0 + j, u0 + k)
    for k in range(9):                              # the spine, one course PROUD of the bed
        b = u0 + k
        if g.free(v0, b, 1) and lot.has(v0, 0, b):
            n += 1 if lot.put(v0, 1, b, KIT["bone"]) else 0
    for k in (1, 3, 5, 7):                          # a RIBCAGE: up off the spine and down again
        for s in (-1, 1):
            a, b = v0 + s, u0 + k
            if g.free(a, b, 1) and lot.has(a, 0, b):
                n += 1 if lot.put(a, 1, b, KIT["bone"]) else 0
                out["ribs"] += 1
            a2 = v0 + 2 * s
            if g.free(a2, b, 0) and lot.has(a2, 0, b):
                n += 1 if lot.put(a2, 0, b, KIT["bone"]) else 0
                out["ribs"] += 1
    for dv, dy in ((0, 1), (-1, 1), (1, 1)):        # the skull, at the low end of the spine
        a = v0 + dv
        if g.free(a, u0 - 1, dy) and lot.has(a, 0, u0 - 1):
            n += 1 if lot.put(a, dy, u0 - 1, KIT["bone"]) else 0
    if g.free(v0, u0 - 2, 1) and lot.has(v0, 0, u0 - 2):
        n += 1 if lot.put(v0, 1, u0 - 2, KIT["bone"]) else 0   # the snout
    out["cells"] = n
    return out


# --------------------------------------------------------------------------- the built things


def _hide(lot: _Lot, g: _Ground, spec: dict, seed: int) -> dict:
    """A timber observation hide: four walls, a doorway on the walk, a viewing slit on the colony.

    **A ROUTE WITH SOMEWHERE TO STAND ON IT IS SOMEWHERE TO BE.** The walk had nests beside it and
    no destination, which is the same complaint this land has already answered twice. And what
    makes voxels read as architecture is REGULARITY AND OPENINGS: the doorway and the slit are left
    empty by the wall loop rather than punched afterwards, because building the ring first and
    cutting a hole repaints cells that already exist - the void tower shipped a plain drum that way
    and nothing about the code looked wrong.
    """
    v0, u0 = int(spec["v"]), int(spec["u"])
    dv, du = int(spec.get("dv", 5)), int(spec.get("du", 7))
    facing = str(spec.get("facing", EAST))          # the way the SLIT looks - out at the colony
    out = {"at": [v0, u0], "size": [dv, du], "facing": facing,
           "cells": 0, "door": 0, "slit": 0, "signed": False}
    n = 0
    # the sill: one course of plank, so the hut stands on a floor rather than on moss
    for a in range(v0, v0 + dv):
        for b in range(u0, u0 + du):
            if g.lawn(a, b) and g.free(a, b, 0):
                n += 1 if lot.put(a, 0, b, KIT["plank"]) else 0
    door_u = u0 + du // 2
    slit_v = v0 + dv - 1 if facing == EAST else v0
    walk_v = v0 if facing == EAST else v0 + dv - 1
    for y in range(1, 4):
        for a in range(v0, v0 + dv):
            for b in range(u0, u0 + du):
                edge = a in (v0, v0 + dv - 1) or b in (u0, u0 + du - 1)
                if not edge or not (g.lawn(a, b) and g.free(a, b, y)):
                    continue
                if a == walk_v and b in (door_u - 1, door_u, door_u + 1) and y < 3:
                    out["door"] += 1                # LEFT EMPTY BY THE LOOP - never punched after
                    continue
                if a == slit_v and y == 2 and u0 < b < u0 + du - 1:
                    n += 1 if lot.put(a, y, b, KIT["pane"], north="true", south="true",
                                      east="false", west="false", waterlogged="false") else 0
                    out["slit"] += 1
                    continue
                # A LOG TAKES AN AXIS AND A PLANK DOES NOT. Written through `lot.log` for both,
                # thirty-one wall cells shipped as `spruce_planks[axis=y]` - not a legal state, and
                # the audit is the only thing that can see it.
                corner = a in (v0, v0 + dv - 1) and b in (u0, u0 + du - 1)
                n += 1 if (lot.log(a, y, b, KIT["post"], axis="y") if corner
                           else lot.put(a, y, b, KIT["plank"])) else 0
    # a lean-to roof of stairs, falling away from the walk
    for a in range(v0, v0 + dv):
        for b in range(u0 - 1, u0 + du + 1):
            if not g.free(a, b, 4):
                continue
            n += 1 if lot.slab(a, 4, b, KIT["slab"], "bottom") else 0
    # THE SUPPORT IS CHECKED, not assumed - `hang` refuses a lantern with nothing over it,
    # which is the bat perch's own rule and the reason the stair head's chains stayed up.
    n += 1 if lot.hang(v0 + dv // 2, 3, u0 + du // 2) else 0
    # **THE BOARD HANGS BESIDE THE DOOR, NOT OVER IT.** Written at the doorway's own column the
    # support check failed every time and the sign was refused in SILENCE - the doorway is the one
    # column of that wall with nothing in it, which is precisely the failure four of this park's
    # seven building kinds shipped once. `signed` is reported either way.
    lines = list(spec.get("lines") or ("THE HIDE", "voices down", "they are", "nesting"))
    step = -1 if facing == EAST else 1
    for off in (2, -2, 3, -3):
        b = door_u + off
        if lot.has(walk_v, 2, b) and not lot.has(walk_v + step, 2, b):
            out["signed"] = lot.sign(walk_v + step, 2, b,
                                     WEST if facing == EAST else EAST, lines)
            if out["signed"]:
                break
    out["cells"] = n
    return out


def _deck(lot: _Lot, g: _Ground, spec: dict, seed: int) -> dict:
    """A plank viewing deck, railed, with a step up onto it.

    **THE SAUROPOD'S GROUND FOOTPRINT IS FOUR FEET.** U33-45 under its barrel is thirteen blocks of
    open lawn twenty courses below the animal, and standing there looking up is the best moment on
    this strip - it was bare grass with nothing leading to it.
    """
    v0, u0 = int(spec["v"]), int(spec["u"])
    dv, du = int(spec.get("dv", 5)), int(spec.get("du", 9))
    out = {"at": [v0, u0], "size": [dv, du], "cells": 0, "rail": 0, "signed": False}
    n = 0
    for a in range(v0, v0 + dv):
        for b in range(u0, u0 + du):
            if not (g.lawn(a, b) and g.free(a, b, 0)):
                continue
            r = hash01(a, b, seed + 41)
            n += 1 if lot.put(a, 0, b, KIT["plank"] if r < 0.8 else KIT["beam"]) else 0
    for a in range(v0 - 1, v0 + dv + 1):
        for b in range(u0 - 1, u0 + du + 1):
            edge = a in (v0 - 1, v0 + dv) or b in (u0 - 1, u0 + du)
            if not edge or not (g.lawn(a, b) and g.free(a, b, 0) and g.free(a, b, 1)):
                continue
            # **THE WAY ON AND OFF IS AT THE ENDS, ON THE WALK'S OWN LINE.** Left on the SIDES
            # the rail ran a complete fence across both ends of the deck - and the deck stands in
            # the middle of the walk's own lane under the animal, so it fenced the walk off
            # entirely. A gate in the wrong wall is a wall.
            if a == v0 + dv // 2 and b in (u0 - 1, u0 + du):
                continue
            n += 1 if lot.put(a, 0, b, KIT["plank"]) else 0
            out["rail"] += 1 if lot.fence(a, 1, b, "u", KIT["fence"]) else 0
    # THE BOARD HANGS OFF THE DECK'S OWN RAIL, facing in. A post planted on the deck for it landed
    # in the cell the sign then needed, so `lot.sign` refused it and said nothing.
    lines = list(spec.get("lines") or ("UNDER THE", "SAUROPOD", "look up - that", "is one animal"))
    for k in range(dv):
        a = v0 + k
        if lot.has(a, 1, u0 - 1) and not lot.has(a, 1, u0):
            out["signed"] = lot.sign(a, 1, u0, SOUTH, lines)
            if out["signed"]:
                break
    out["cells"] = n
    return out


def _rail(lot: _Lot, g: _Ground, spec: dict, seed: int) -> dict:
    """The fence along the drop, with gaps. You are on a clifftop over open void.

    **GAPS, BECAUSE A CONTINUOUS FENCE IS A WALL AND THE VIEW IS THE POINT.** It reads as a
    viewpoint rather than as an edge, and a rider on the railway sees a dotted line rather than a
    hem across the whole band.
    """
    v = int(spec["v"])
    every, run = max(4, int(spec.get("every", 11))), max(2, int(spec.get("run", 7)))
    n = posts = 0
    for u in range(lot.du):
        if u % every >= run:
            continue
        if not (g.lawn(v, u) and g.free(v, u, 0) and g.free(v, u, 1)):
            continue
        if lot.has(v, 0, u) or lot.has(v, 1, u):
            continue                               # a piece never overwrites a piece
        n += 1 if lot.put(v, 0, u, KIT["dark"]) else 0
        posts += 1 if lot.fence(v, 1, u, "u", KIT["fence"]) else 0
    return {"v": v, "cells": n + posts, "posts": posts}


def _kit(lot: _Lot, g: _Ground, v0: int, u0: int, seed: int) -> int:
    """A ranger's kit: crates, a specimen table and a lamp on a post. `claimrow`'s own props."""
    n = cr._crates(lot, g, v0, u0, seed)
    if g.lawn(v0 + 2, u0) and g.free(v0 + 2, u0, 0):
        n += 1 if lot.put(v0 + 2, 0, u0, KIT["post"], axis="y") else 0
        for du in (0, 1):
            if g.free(v0 + 2, u0 + du, 1):
                n += 1 if lot.slab(v0 + 2, 1, u0 + du, KIT["slab"], "top") else 0
    if g.lawn(v0 + 2, u0 + 3) and g.free(v0 + 2, u0 + 3, 0):
        n += 1 if lot.put(v0 + 2, 0, u0 + 3, KIT["post"], axis="y") else 0
        if g.free(v0 + 2, u0 + 3, 1):
            n += 1 if lot.put(v0 + 2, 1, u0 + 3, KIT["lamp"], hanging="false",
                              waterlogged="false") else 0
    return n


# --------------------------------------------------------------------------- entry point


def build(cfg: dict, donors=None) -> Canvas:
    p = {**ROOKERY, **(cfg or {})}
    if not p.get("lot"):
        raise ValueError("the rookery needs its lot: lot: [dv, du]")
    if not p.get("under"):
        raise ValueError("a rim design must ask the world it is verified against: under: <capture>")
    dv, du = int(p["lot"][0]), int(p["lot"][1])
    at = [int(x) for x in (p.get("at") or (0, 0))]
    anchor = [int(x) for x in p["anchor"]]
    seed = int(p.get("seed", 0))
    c = Canvas(dv, 24, du, donors)
    lot = _Lot(c, dv, du, seed=seed)
    g = _Ground(Ctx(p["under"]), anchor, dv, du, at, int(p.get("clear", 1)),
                p.get("keep_out") or (), own=OWN, mine=shipped_cells(p.get("previous")),
                flora=flora_for(p.get("flora")))

    # ORDER: the walk first, so nothing else can stand in it - a prop sited by hand near a way
    # will eventually be sited IN it, which is why the way refuses rather than the hand remembering.
    walks = [_walk(lot, g, s, seed) for s in (p.get("walks") or [])]
    hide = _hide(lot, g, p["hide"], seed) if p.get("hide") else None
    deck = _deck(lot, g, p["deck"], seed) if p.get("deck") else None
    # THE COLONY BEFORE THE SKYLINE: `Canvas.put` overwrites, so where two footprints touch the
    # order decides which one survives, and a scrape with eggs in it is the thing that was asked
    # for. The stacks and the rail yield; the nests and the juveniles do not.
    nests = [_nest(lot, g, int(n[0]), int(n[1]), int(n[2]), seed)
             for n in (p.get("nests") or [])]
    chicks = [_hatchling(lot, g, int(h[0]), int(h[1]), str(h[2]), seed)
              for h in (p.get("hatchlings") or [])]
    bones = [_bones(lot, g, int(b[0]), int(b[1]), seed) for b in (p.get("bones") or [])]
    stacks = [_stack(lot, g, int(s[0]), int(s[1]), int(s[2]), seed)
              for s in (p.get("stacks") or [])]
    rail = _rail(lot, g, p["rail"], seed) if p.get("rail") else None
    kit = sum(_kit(lot, g, int(k[0]), int(k[1]), seed) for k in (p.get("kit") or []))
    plaques = [cr._plaque(lot, g, s) for s in (p.get("plaques") or [])]
    plant = cr._plant(lot, g, p, seed) if p.get("plant") else {"trees": 0, "cells": 0}

    c.world_origin = (anchor[0] + at[0], anchor[1], anchor[2] + at[1])
    c.meta = {
        "kind": "rookery",
        "lot": [dv, du],
        "at": at,
        "land": "frontier",
        "facing": "west",
        "profile_axis": "u",
        "refused": lot.refused,
        "parts": {
            "walks": walks, "rail": rail, "hide": hide, "deck": deck,
            "stacks": stacks, "nests": nests, "hatchlings": chicks, "bones": bones,
            "kit": kit, "plaques": plaques, "plant": plant,
            "eggs": sum(n.get("eggs", 0) for n in nests),
            "skyline": max([s["h"] for s in stacks], default=0),
            "cells": (sum(w["cells"] + w["kerb"] + w["glow"] for w in walks)
                      + (rail["cells"] if rail else 0) + (hide["cells"] if hide else 0)
                      + (deck["cells"] if deck else 0)
                      + sum(s["cells"] for s in stacks) + sum(n["cells"] for n in nests)
                      + sum(h["cells"] for h in chicks) + sum(b["cells"] for b in bones)
                      + kit + plant["cells"]),
        },
        "contract": (
            "the Frontier's clifftop rookery, behind the railway: a walk that runs the whole band "
            "and passes UNDER the sauropod between its feet, perch stacks that give the strip a "
            "skyline it measured zero of, a nesting colony of full, hatching and hatched scrapes "
            "with juveniles beside them, an observation hide, a bone find and a railed drop. "
            "Nothing is placed on paving or on anything standing; every piece asks the world per "
            "CELL as it rises, so the sauropod stops the tall things and the low ones stand under "
            "it."),
    }
    return c
