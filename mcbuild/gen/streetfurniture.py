"""STREET FURNITURE: the small pieces that make a plaza inhabited rather than empty.

`gen/park.py` builds the attractions and `gen/civic.py` builds the entrance zone. Both of them
leave the ground BETWEEN buildings to `park._plaza` and `park._paths`, and paving on its own is a
floor, not a place. This is what stands on it: benches, planters, lampposts, topiary, flagpoles,
fingerposts and litter bins.

**EVERY KIND HERE IS SMALL AND WILL BE PLACED MANY TIMES, SO THE VARIATION IS THE WHOLE POINT.**
A bench is thirty blocks; a plaza wants a dozen of them, and twelve identical benches is not
furniture, it is a pattern. That is the same failure the entrance zone was rejected for -
*"single small structures... some infrastructure and some huts"* - and the answer `civic` found
is the answer here: every choice comes from a deterministic hash of a `seed`, and the properties
move INDEPENDENTLY, so two neighbours differ in shape as well as in colour.

    seed        given    the piece is a pure function of it - the same seed anywhere is the
                         same bench, which is what makes a plan reproducible
    seed        None     derived from the world position, so a caller that never thinks about
                         seeds still gets a different bench in every bay

Both halves matter. A seed that always mixed in the position could not be reproduced; a seed that
never did would make `seed: 0` a default that builds a row of clones - and a default that quietly
produces the failure the module exists to prevent is worse than no default at all.

NEVER `random`. `park.hash01` or an index hash, every time: a design regenerated tomorrow has to
be the design that was placed today, or every cell of it reads as a deviation.

GEOMETRY, `park`'s exactly, imported rather than restated - two modules each holding a copy of
"which way does a stair lean" is how one facing bug becomes two:

    at       the piece's FRONT-LEFT floor corner, in world coordinates
    facing   the direction the FRONT looks out - a visitor stands in the +facing direction
    i        runs along the frontage (the side axis)
    d        runs from the front INTO the piece; +d is `f.back`
    h        courses up from the floor, and h=-1 is the pad the piece stands on

**THE PLOT IS VOID, SO EVERY KIND CARRIES ITS OWN PAD.** There is no terrain on a skyblock plot;
the h=-1 pad is not decoration, it is the reason each piece is one connected component instead of
a shape floating over nothing. It is laid on the WORLD-ALIGNED checker `park._plaza` and
`civic` use, so a bench's own pad reads as part of the paving it stands on rather than as a
patch someone dropped on it.

MATERIALS. Everything structural comes from `park.LANDS[land]`. The extras were each checked
against `blocks.spendable`, `blocks.available` and `palette.tier` before being written down, and
every one is cheap:

    moss_block · moss_carpet · azalea · flowering_azalea · five leaf families · the land's own
    trapdoor · cauldron · composter · end_rod · six cheap wools per land for the flags

**NO DIRT AND NO GRASS BLOCK.** They are CURRENCY on this server - `blocks.spendable` is False
for every form of them - so a planted bed is planted in MOSS, which is what this island has always
planted with and what `audit.DIRT_LIKE` accepts under an azalea. No sand or gravel either: a
planter overhanging a pad edge would pour into the void. No quartz, concrete, terracotta, glass
block, sea lantern, glowstone, redstone lamp, hay or note block - all expensive here.

**A STAIR COURSE SHORTER THAN THREE CELLS IS CONFETTI**, which the deck soffit settled: it drew a
grid per cell and produced 215 runs of which 184 were one or two cells, in the loudest block
available. So a lamppost's base flare is a 3x3 plinth inside a 5x5 ring - four runs of three -
and never four single stairs pointing at a post.
"""
from __future__ import annotations

from .canvas import Canvas, hash01
from .vertical import Ctx, World
from .park import (
    LANDS, SIGN_WIDTH, _STEP, _BACK, _LEAN, _Frame,
    _sign, _hang_light,
)

# The direction NAME of a unit step in world coordinates. Everything angular goes through it, so
# "which way is +i" is answered in one place.
_NAME = {(0, -1): "north", (0, 1): "south", (1, 0): "east", (-1, 0): "west"}

MIN_RUN = 3             # a trim or stair course shorter than this is not drawn at all

# Leaf families per land, so a topiary in the Hollow is not a bright oak bush. All cheap, all
# spendable, all 1.19. Leaves are placed `persistent=true` - ours would not have decayed anyway,
# but the download corpus is unanimous on it and a decayed topiary is a hole in a plaza.
_LEAVES = {
    "midway": ["oak_leaves", "azalea_leaves", "flowering_azalea_leaves", "birch_leaves"],
    "frontier": ["spruce_leaves", "oak_leaves", "azalea_leaves"],
    "hollow": ["dark_oak_leaves", "spruce_leaves", "azalea_leaves"],
}

# Flag cloth. Two are drawn per flagpole and they are drawn to be DIFFERENT - a two-tone flag
# whose tones are the same colour is a plain rectangle, and a plain rectangle is a wall.
_CLOTH = {
    "midway": ["red_wool", "white_wool", "yellow_wool", "light_blue_wool", "lime_wool",
               "magenta_wool"],
    "frontier": ["orange_wool", "brown_wool", "white_wool", "red_wool", "yellow_wool",
                 "green_wool"],
    "hollow": ["purple_wool", "black_wool", "gray_wool", "white_wool", "magenta_wool",
               "blue_wool"],
}

# Where a fingerpost points. A post with two blank arms is a post; the destinations are the
# feature. Every line is inside SIGN_WIDTH, and that is asserted rather than hoped for.
_WAYS = [
    ("THE GATE", "this way"), ("MIDWAY", "300 paces"), ("FRONTIER", "400 paces"),
    ("HOLLOW", "mind the dark"), ("FOUNTAIN", "straight on"), ("BANDSTAND", "music at three"),
    ("MARKET ROW", "shops"), ("LOOKOUT", "climb it"), ("TICKETS", "back that way"),
    ("FIRST AID", "round the back"), ("THE LAKE", "past the trees"), ("CAROUSEL", "left here"),
]

FURNITURE = {
    "under": None,
    "at": None,                 # world (x, y, z): the FRONT-LEFT floor corner
    "kind": "bench",
    "facing": "east",
    "land": "midway",
    "seed": None,               # None -> derived from the world position; see the docstring
    "title": None,              # flagpole / signpost: what the plaque reads
    "shape": None,              # bench: straight | double | corner  (None picks by hash)
    "plan": None,               # planter: square | trough | stepped
    "crown": None,              # topiary: sphere | cone | tiered
    "style": None,              # bin: cauldron | composter | capped
    "arms": None,               # signpost / lamppost: how many; None picks by hash
    "sign": True,
}

DEFAULTS = FURNITURE            # the defaults dict, under the name a caller might look for


# ---------------------------------------------------------------------------- small helpers

def _seed_of(p, f):
    """The seed the whole piece is drawn from.

    An explicit seed is honoured ANYWHERE, so a plan can be reproduced; `None` falls back to the
    world position, so a caller who never thinks about seeds still gets a different piece in
    every bay rather than a row of clones.
    """
    s = p.get("seed")
    if s is not None:
        return int(s)
    return f.x * 1237 + f.z * 91 + f.y


def _pick(options, seed, salt):
    options = list(options)
    return options[int(hash01(seed, salt) * len(options)) % len(options)]


def _span(seed, salt, lo, hi):
    """An integer in [lo, hi]."""
    return lo + int(hash01(seed, salt) * (hi - lo + 1)) % (hi - lo + 1)


def _i_dir(f, s):
    """The world direction name of +i (s=1) or -i (s=-1)."""
    return _NAME[(f.sx * s, f.sz * s)]


def _d_dir(f, s):
    """+d runs INTO the piece, which is `f.back`; -d is `f.facing`."""
    return f.back if s > 0 else f.facing


def _off_dir(f, di, dd):
    """The world direction of a unit frame offset. `at` moves by (sx, sz) per +i and by
    (-dx, -dz) per +d, so this is the one place that arithmetic is written down."""
    return _NAME[(f.sx * di - f.dx * dd, f.sz * di - f.dz * dd)]


def _stair(w, f, i, d, h, block, facing, half="bottom"):
    """A stair whose TALL side faces `facing` - `civic._roof_hip`'s convention, stated the same
    way here. Our renderer draws both directions identically, which is exactly why this is one
    helper with one meaning rather than a judgement made at twenty call sites."""
    w.put(*f.at(i, d, h), block, facing=facing, half=half, shape="straight", waterlogged="false")


def _slab(w, f, i, d, h, block, typ="bottom"):
    w.put(*f.at(i, d, h), block, type=typ, waterlogged="false")


def _free(w, f, i, d, h):
    return not w.has(*f.at(i, d, h))


def _put_free(w, f, i, d, h, block, **props):
    """Place only into an empty cell, so a crown laid over a trunk does not eat the trunk."""
    if _free(w, f, i, d, h):
        w.put(*f.at(i, d, h), block, **props)
        return True
    return False


def _leaf(w, f, i, d, h, kind):
    w.put(*f.at(i, d, h), kind, persistent="true", waterlogged="false")


def _fence_props(f, cells, i, d):
    """A fence connects only toward NEIGHBOURS THAT EXIST.

    With every side false a fence renders as a lone post, which is right for a pole and wrong for
    a bench back; with every side true the run grows a nub off each end into open air. This is
    `civic._pane_props`' lesson, applied to the block whose connections actually vary along a run.
    """
    have = set(cells)
    pr = {"north": "false", "south": "false", "east": "false", "west": "false",
          "waterlogged": "false"}
    for (di, dd) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        if (i + di, d + dd) in have:
            pr[_off_dir(f, di, dd)] = "true"
    return pr


def _pad(w, f, pal, i0, i1, d0, d1):
    """The ground the piece stands on, on the WORLD-ALIGNED checker every other paved surface in
    the park uses - so a bench's pad reads as part of the paving rather than as a patch dropped
    on it - with the border in the land's trim so the piece has an edge.

    A skyblock plot is VOID. Without this the piece is a shape hanging over nothing.
    """
    n = 0
    for i in range(i0, i1 + 1):
        for d in range(d0, d1 + 1):
            x, y, z = f.at(i, d, -1)
            if i in (i0, i1) or d in (d0, d1):
                blk = pal["trim"]
            elif (x + z) % 2 == 0:
                blk = pal["ground"]
            else:
                blk = pal["path"]
            w.put(x, y, z, blk)
            n += 1
    return n


def _skirt(w, f, pal, i0, i1, d0, d1, h=0):
    """A flared moulding round a plinth: one stair course on each of the four sides of the ring
    [i0..i1]x[d0..d1], leaning inward, WITH THE CORNERS LEFT OUT - a corner faces two ways and
    can face only one.

    Each side is a run of `i1-i0-1` or `d1-d0-1` cells and the caller is expected to keep that at
    or above `MIN_RUN`; the four singles a naive base flare produces are the confetti the deck
    soffit's run gate exists to stop.
    """
    laid = 0
    runs = ((range(i0 + 1, i1), (d0,), _d_dir(f, 1)),
            (range(i0 + 1, i1), (d1,), _d_dir(f, -1)),
            ((i0,), range(d0 + 1, d1), _i_dir(f, 1)),
            ((i1,), range(d0 + 1, d1), _i_dir(f, -1)))
    for iis, dds, inward in runs:
        cells = [(i, d) for i in iis for d in dds]
        if len(cells) < MIN_RUN:
            continue
        for (i, d) in cells:
            _stair(w, f, i, d, h, pal["stair"], inward)
            laid += 1
    return laid


class _Plaques:
    """Signs, counted, and never hung on a wall that is not there.

    `park._sign` returns False when the column behind the sign has an OPENING in it and places
    nothing - which is correct, and silent, and is how a kind ships with a nameplate that does not
    exist. Attempted and placed are both reported so the two can be compared, and the width is
    asserted rather than truncated in silence: a line over fifteen characters clips mid-word, and
    the only place that shows is a screenshot of the built piece.
    """

    def __init__(self, on=True):
        self.on = bool(on)
        self.want = 0
        self.got = 0

    def __call__(self, w, f, pal, i, d, h, facing, lines, back=()):
        for ln in lines:
            assert len(str(ln)) <= SIGN_WIDTH, f"sign line {ln!r} is over {SIGN_WIDTH} chars"
        if not self.on:
            return False
        self.want += 1
        if not _free(w, f, i, d, h):
            return False
        ok = _sign(w, f, pal, i, d, h, facing, lines, back)
        self.got += int(bool(ok))
        return ok


# ---------------------------------------------------------------------------- the bench

def _seat(w, f, pal, cells, facing):
    """A run of stair seats. The stair's TALL side is the BACK of the seat, so a sitter looks the
    other way - which is why `facing` is passed in rather than derived: a corner bench's two runs
    look out along different axes and a seat pointing into its own backrest is a step, not a seat.
    """
    for (i, d) in cells:
        _stair(w, f, i, d, 0, pal["stair"], facing)
    return len(cells)


def _bench(w: World, p: dict, ctx) -> dict:
    """A seat. Stair seats on a plinth, a back you can lean on, and an arm rest at each end.

    Three plans, and they are three different pieces of furniture rather than three lengths of
    one: a straight bench faces the path, a back-to-back double faces both ways down an avenue,
    and a corner bench wraps the inside of a turn. Length, back style and arm style move
    independently on top of that, so two benches on the same kerb are visibly not the same bench.
    """
    f = _Frame(p)
    pal = LANDS[p["land"]]
    seed = _seed_of(p, f)
    shape = p.get("shape") or _pick(("straight", "double", "corner"), seed, 1)
    if shape not in ("straight", "double", "corner"):
        raise ValueError(f"unknown bench shape {shape!r}; have ['corner', 'double', 'straight']")
    back_style = _pick(("fence", "slat", "solid"), seed, 2)
    arm_style = _pick(("fence", "slat", "post"), seed, 3)
    wood = pal["wood"]

    la = _span(seed, 4, 4, 7)
    lb = _span(seed, 5, 3, 5)
    fences: list[tuple[int, int, int]] = []          # placed last, so connections can be derived

    def back_run(cells, along_i):
        """Plinth at h=0, rail at h=1, and a coping on the solid version so the top is a line."""
        for (i, d) in cells:
            w.put(*f.at(i, d, 0), pal["trim"])
        if back_style == "solid":
            for (i, d) in cells:
                w.put(*f.at(i, d, 1), pal["wall"])
            if len(cells) >= MIN_RUN:
                for (i, d) in cells:
                    _slab(w, f, i, d, 2, pal["slab"], "bottom")
        elif back_style == "fence":
            for (i, d) in cells:
                fences.append((i, d, 1))
        else:                                        # slats: a trapdoor is the vertical slab
            face = _d_dir(f, -1) if along_i else _i_dir(f, 1)
            for (i, d) in cells:
                w.put(*f.at(i, d, 1), f"{wood}_trapdoor", facing=face, half="top",
                      open="true", powered="false", waterlogged="false")

    def arm(i, d, face):
        w.put(*f.at(i, d, 0), pal["trim"])
        if arm_style == "fence":
            fences.append((i, d, 1))
        elif arm_style == "slat":
            w.put(*f.at(i, d, 1), f"{wood}_trapdoor", facing=face, half="top",
                  open="true", powered="false", waterlogged="false")
        else:
            w.put(*f.at(i, d, 1), pal["post"])
            _slab(w, f, i, d, 2, pal["slab"], "bottom")

    seats = 0
    if shape == "straight":
        i0, i1, d0, d1 = 0, la + 1, 0, 3
        _pad(w, f, pal, i0 - 1, i1 + 1, d0, d1)
        back_run([(i, 2) for i in range(i0, i1 + 1)], along_i=True)
        seats += _seat(w, f, pal, [(i, 1) for i in range(1, la + 1)], f.back)
        arm(i0, 1, _i_dir(f, -1))
        arm(i1, 1, _i_dir(f, 1))
    elif shape == "double":
        i0, i1, d0, d1 = 0, la + 1, 0, 4
        _pad(w, f, pal, i0 - 1, i1 + 1, d0, d1)
        back_run([(i, 2) for i in range(i0, i1 + 1)], along_i=True)
        seats += _seat(w, f, pal, [(i, 1) for i in range(1, la + 1)], f.back)
        seats += _seat(w, f, pal, [(i, 3) for i in range(1, la + 1)], f.facing)
        for i, face in ((i0, _i_dir(f, -1)), (i1, _i_dir(f, 1))):
            arm(i, 1, face)
            arm(i, 3, face)
    else:                                            # corner: two runs meeting at one plinth
        i0, i1, d0, d1 = 0, la + 1, 0, lb + 3
        _pad(w, f, pal, i0 - 1, i1 + 1, d0, d1)
        back_run([(i, 2) for i in range(i0, i1 + 1)], along_i=True)
        back_run([(0, d) for d in range(3, lb + 3)], along_i=False)
        seats += _seat(w, f, pal, [(i, 1) for i in range(1, la + 1)], f.back)
        seats += _seat(w, f, pal, [(1, d) for d in range(3, lb + 3)], _i_dir(f, -1))
        arm(i1, 1, _i_dir(f, 1))
        arm(1, lb + 3, _d_dir(f, 1))

    have = {(i, d) for (i, d, _h) in fences}
    for (i, d, h) in fences:
        w.put(*f.at(i, d, h), pal["fence"], **_fence_props(f, have, i, d))

    return {"kind": "bench", "shape": shape, "seats": seats, "back": back_style,
            "arm": arm_style, "length": la, "seed": seed,
            "contract": "a seat you can sit on: stair seats at floor level with a back behind "
                        "them and an arm rest at each end, all of it standing on its own pad"}


# ---------------------------------------------------------------------------- the planter

def _planter(w: World, p: dict, ctx) -> dict:
    """A raised bed with a moulded rim, planted.

    **PLANTED IN MOSS, BECAUSE DIRT IS CURRENCY.** `blocks.spendable` is False for every form of
    dirt and for the grass block on this server, so a naturalistic bed of soil is not expensive,
    it is unbuildable - and moss is in `audit.DIRT_LIKE`, so an azalea rooted in it is a legal
    plant rather than a placement problem.

    Three plans, three rim mouldings and four plantings, all dealt independently: a square bed
    with a slab lip full of azalea and a stepped bed with a stone coping carrying a clipped shrub
    are not the same object twice.
    """
    f = _Frame(p)
    pal = LANDS[p["land"]]
    seed = _seed_of(p, f)
    plan = p.get("plan") or _pick(("square", "trough", "stepped"), seed, 1)
    if plan not in ("square", "trough", "stepped"):
        raise ValueError(f"unknown planter plan {plan!r}; have ['square', 'stepped', 'trough']")
    rim = _pick(("slab", "stair", "coping"), seed, 2)
    planting = _pick(("azalea", "mound", "shrub", "tuft"), seed, 3)
    leaf = _pick(_LEAVES[p["land"]], seed, 4)

    if plan == "square":
        width = depth = _span(seed, 5, 3, 5) | 1
    elif plan == "trough":
        width, depth = _span(seed, 5, 5, 9), 3
    else:
        width = depth = 5

    i0, i1, d0, d1 = 0, width - 1, 0, depth - 1
    _pad(w, f, pal, i0 - 1, i1 + 1, d0 - 1, d1 + 1)

    def ring(h, block, corner=None):
        for i in range(i0, i1 + 1):
            for d in range(d0, d1 + 1):
                if not (i in (i0, i1) or d in (d0, d1)):
                    continue
                is_corner = i in (i0, i1) and d in (d0, d1)
                w.put(*f.at(i, d, h), (corner or block) if is_corner else block)

    def fill(h, block, **props):
        for i in range(i0 + 1, i1):
            for d in range(d0 + 1, d1):
                w.put(*f.at(i, d, h), block, **props)

    # ---- the kerb course, and the soil inside it
    ring(0, pal["trim"])
    fill(0, "moss_block")
    soil = 0

    # ---- the moulding. `coping` raises the whole bed a course, which is a visibly taller piece
    # of furniture rather than a different-coloured lip on the same one.
    if rim == "coping":
        ring(1, pal["wall"], corner=pal["post"])
        fill(1, "moss_block")
        soil = 1
        for i in range(i0, i1 + 1):
            for d in range(d0, d1 + 1):
                if i in (i0, i1) or d in (d0, d1):
                    _slab(w, f, i, d, 2, pal["slab"], "bottom")
    elif rim == "slab":
        for i in range(i0, i1 + 1):
            for d in range(d0, d1 + 1):
                if i in (i0, i1) or d in (d0, d1):
                    _slab(w, f, i, d, 1, pal["slab"], "bottom")
    else:
        # A FLARED LIP, laid as four runs with the corners taken by a pier: a corner faces two
        # ways and can face only one, and a gap there reads as a chip out of the rim.
        #
        # **AND THE RUN GATE LEAVES HOLES IN A NARROW BED, SO THE REST OF THE RIM IS SLABBED.**
        # `_skirt`'s sides are `width - 2` and `depth - 2` cells, so a three-wide square bed has
        # one-cell sides and a trough has one-cell ENDS - every one of them under `MIN_RUN` and
        # correctly refused. Left there the bed ships with four corner piers and open gaps
        # between them, which is not a rim; every perimeter cell the flare did not take gets a
        # plain slab lip instead. A moulding that is flared along its long sides and plain across
        # its ends is masonry; a moulding with holes in it is damage.
        _skirt(w, f, pal, i0, i1, d0, d1, h=1)
        for (i, d) in ((i0, d0), (i0, d1), (i1, d0), (i1, d1)):
            _put_free(w, f, i, d, 1, pal["trim"])
        for i in range(i0, i1 + 1):
            for d in range(d0, d1 + 1):
                if i in (i0, i1) or d in (d0, d1):
                    if _free(w, f, i, d, 1):
                        _slab(w, f, i, d, 1, pal["slab"], "bottom")

    # ---- the planting, on top of whatever course the soil ended up at
    top = soil + 1
    inner = [(i, d) for i in range(i0 + 1, i1) for d in range(d0 + 1, d1)]
    ci, cd = (i0 + i1) // 2, (d0 + d1) // 2
    plants = 0
    if planting == "azalea":
        for (i, d) in inner:
            r = hash01(seed, 21, i * 31 + d)
            if r < 0.30:
                w.put(*f.at(i, d, top), "flowering_azalea")
            elif r < 0.72:
                w.put(*f.at(i, d, top), "azalea")
            else:
                w.put(*f.at(i, d, top), "moss_carpet")
            plants += 1
    elif planting == "tuft":
        for (i, d) in inner:
            if hash01(seed, 22, i * 31 + d) < 0.25:
                w.put(*f.at(i, d, top), "azalea")
            else:
                w.put(*f.at(i, d, top), "moss_carpet")
            plants += 1
    elif planting == "mound":
        # A clipped mound: moss over the whole bed, leaves standing proud of the middle of it.
        for (i, d) in inner:
            w.put(*f.at(i, d, top), "moss_block")
            plants += 1
        for (i, d) in inner:
            if abs(i - ci) + abs(d - cd) <= max(1, (min(width, depth) - 3) // 2):
                _leaf(w, f, i, d, top + 1, leaf)
    else:                                            # a small clipped shrub on a stem
        for (i, d) in inner:
            w.put(*f.at(i, d, top), "moss_carpet")
            plants += 1
        w.put(*f.at(ci, cd, top), pal["post"])
        w.put(*f.at(ci, cd, top + 1), pal["post"])
        for (i, d) in inner:
            if abs(i - ci) <= 1 and abs(d - cd) <= 1:
                _put_free(w, f, i, d, top + 2, leaf, persistent="true", waterlogged="false")
        _put_free(w, f, ci, cd, top + 3, leaf, persistent="true", waterlogged="false")

    return {"kind": "planter", "plan": plan, "rim": rim, "planting": planting, "leaf": leaf,
            "width": width, "depth": depth, "cells": plants, "seed": seed,
            "contract": "a raised bed whose rim is a real moulding and whose planting is rooted "
                        "in moss - never dirt or grass, which cannot be spent on this server"}


# ---------------------------------------------------------------------------- the lamppost

def _lamppost(w: World, p: dict, ctx) -> dict:
    """An ornamental post: a moulded base, a fluted shaft, bracket arms and lanterns.

    Taller and more worked than `park._plaza`'s plain three-block post, which is deliberate - a
    plaza wants both, and the difference between the ordinary one and the ornamental one is what
    makes an avenue read as an avenue.

    **A LANTERN ON A POST TOP STANDS, IT DOES NOT HANG.** Written `hanging=true` it is looking for
    a block ABOVE it, finds open sky, and is a lantern hanging from nothing - which the audit says
    in as many words. A lantern on a BRACKET hangs, because the bracket is a full block over it.
    """
    f = _Frame(p)
    pal = LANDS[p["land"]]
    seed = _seed_of(p, f)
    height = _span(seed, 1, 6, 9)
    shaft = _pick(("log", "fluted", "banded"), seed, 2)
    crown = _pick(("lantern", "urn", "rod"), seed, 3)
    arms = int(p["arms"]) if p.get("arms") is not None else _span(seed, 4, 0, 2)
    along_i = hash01(seed, 5) < 0.5

    # A POST THAT CARRIES NO LIGHT IS A POLE. `rod` is the one crown that ends in a finial rather
    # than in a lamp, so with no bracket to hang one from it is not an option at all.
    if arms == 0 and crown == "rod":
        crown = "lantern"

    ci = cd = 1
    _pad(w, f, pal, -2, 4, -2, 4)

    # ---- the base: a 3x3 plinth inside a 5x5 flare, so the moulding is four runs of three
    for i in range(0, 3):
        for d in range(0, 3):
            w.put(*f.at(i, d, 0), pal["trim"])
    _skirt(w, f, pal, -1, 3, -1, 3, h=0)

    # ---- a slab collar over the plinth, and the shaft rising out of it
    for i in range(0, 3):
        for d in range(0, 3):
            if (i, d) != (ci, cd):
                _slab(w, f, i, d, 1, pal["slab"], "bottom")
    w.put(*f.at(ci, cd, 1), pal["post"])
    for h in range(2, height):
        if h in (2, height - 1) or shaft == "log":
            blk = pal["post"]                        # solid where the arms and the collar meet
        elif shaft == "fluted":
            blk = pal["fence"]
        else:
            blk = pal["trim"] if (h % 2) else pal["post"]
        if blk == pal["fence"]:
            w.put(*f.at(ci, cd, h), blk, north="false", south="false", east="false",
                  west="false", waterlogged="false")
        else:
            w.put(*f.at(ci, cd, h), blk)
    w.put(*f.at(ci, cd, height), pal["trim"])        # the cap: a FULL block, so a crown can stand

    # ---- bracket arms. `_hang_light` fills the cell above the lantern with trim, which IS the
    # bracket - the arm and the thing it needs to hang from are one block, not two.
    offs = [(1, 0), (-1, 0)] if along_i else [(0, 1), (0, -1)]
    for k in range(arms):
        di, dd = offs[k]
        _hang_light(w, f, pal, ci + di, cd + dd, height - 2)

    if crown == "lantern":
        w.put(*f.at(ci, cd, height + 1), pal["light"], hanging="false", waterlogged="false")
        top = height + 1
    elif crown == "urn":
        w.put(*f.at(ci, cd, height + 1), pal["accent"])
        w.put(*f.at(ci, cd, height + 2), pal["light"], hanging="false", waterlogged="false")
        top = height + 2
    else:
        w.put(*f.at(ci, cd, height + 1), pal["accent"])
        w.put(*f.at(ci, cd, height + 2), "end_rod", facing="up")
        top = height + 2

    return {"kind": "lamppost", "height": top + 1, "shaft": shaft, "crown": crown,
            "arms": arms, "seed": seed,
            "contract": "a lit post between six and nine courses to its cap, with a moulded base "
                        "of four three-cell runs and every lantern either standing on a full "
                        "block or hanging under one"}


# ---------------------------------------------------------------------------- the topiary

def _topiary(w: World, p: dict, ctx) -> dict:
    """A clipped shrub in a tub: a stem and a tidy geometric crown.

    CLIPPED, not natural. A voxel tree built as a natural canopy is a green blob; a sphere, a cone
    and a three-tier standard are shapes this medium gives away free, and all three read instantly
    as something a gardener did on purpose - which is the whole difference between a park and a
    field.
    """
    f = _Frame(p)
    pal = LANDS[p["land"]]
    seed = _seed_of(p, f)
    crown = p.get("crown") or _pick(("sphere", "cone", "tiered"), seed, 1)
    if crown not in ("sphere", "cone", "tiered"):
        raise ValueError(f"unknown topiary crown {crown!r}; have ['cone', 'sphere', 'tiered']")
    tub = _pick(("ring", "pot"), seed, 2)
    leaf = _pick(_LEAVES[p["land"]], seed, 3)
    r = _span(seed, 4, 2, 3)
    stem = _span(seed, 5, 1, 3)

    ci = cd = 2
    _pad(w, f, pal, -1, 5, -1, 5)

    # ---- the tub. `ring` is a kerb with a slab lip; `pot` stands a second, brighter course on it,
    # so the two are a bed and a planter rather than one object in two colours.
    for i in range(0, 5):
        for d in range(0, 5):
            edge = i in (0, 4) or d in (0, 4)
            w.put(*f.at(i, d, 0), pal["trim"] if edge else "moss_block")
    soil = 0
    if tub == "ring":
        for i in range(0, 5):
            for d in range(0, 5):
                if i in (0, 4) or d in (0, 4):
                    _slab(w, f, i, d, 1, pal["slab"], "bottom")
    else:
        for i in range(1, 4):
            for d in range(1, 4):
                edge = i in (1, 3) or d in (1, 3)
                w.put(*f.at(i, d, 1), pal["accent"] if edge else "moss_block")
        soil = 1
        for i in range(0, 5):
            for d in range(0, 5):
                if i in (0, 4) or d in (0, 4):
                    _slab(w, f, i, d, 1, pal["slab"], "top")

    # ---- the stem. It runs the WHOLE way to the top of the crown on a tiered standard: the tiers
    # are separated by a clear course, and without a stem through them each tier is a floating
    # disc - six-connectivity does not see a diagonal, and nothing else ties them together.
    base = soil + 1
    reach = stem + (5 if crown == "tiered" else 0)
    for h in range(base, base + reach):
        w.put(*f.at(ci, cd, h), pal["post"])
    top = base + stem - 1                            # the last stem cell before the crown

    if crown == "sphere":
        c = top + r
        for di in range(-r, r + 1):
            for dd in range(-r, r + 1):
                for dh in range(-r, r + 1):
                    if di * di + dd * dd + dh * dh <= r * r:
                        _put_free(w, f, ci + di, cd + dd, c + dh, leaf,
                                  persistent="true", waterlogged="false")
        crest = c + r
    elif crown == "cone":
        crest = top
        for lv in range(r + 1):
            rr = r - lv
            for di in range(-rr, rr + 1):
                for dd in range(-rr, rr + 1):
                    if abs(di) + abs(dd) <= rr + (1 if rr > 1 else 0):
                        _put_free(w, f, ci + di, cd + dd, top + 1 + lv, leaf,
                                  persistent="true", waterlogged="false")
            crest = top + 1 + lv
    else:
        crest = top
        for k, rr in enumerate((r, max(1, r - 1), 1)):
            lv = top + 1 + k * 2
            for di in range(-rr, rr + 1):
                for dd in range(-rr, rr + 1):
                    if abs(di) + abs(dd) <= rr + (1 if rr > 1 else 0):
                        _put_free(w, f, ci + di, cd + dd, lv, leaf,
                                  persistent="true", waterlogged="false")
            crest = lv

    return {"kind": "topiary", "crown": crown, "tub": tub, "leaf": leaf, "radius": r,
            "stem": stem, "height": crest + 1, "seed": seed,
            "contract": "a clipped crown on a stem in a tub: the stem runs through every tier, "
                        "so the whole shrub is one piece rather than discs hanging over a pot"}


# ---------------------------------------------------------------------------- the flagpole

def _cloth(seed, land):
    """Two DIFFERENT cloths. Drawn independently they collide about one time in six, and a
    two-tone flag in one tone is a plain rectangle - which reads, at a distance, as a wall."""
    opts = _CLOTH[land]
    a = int(hash01(seed, 31) * len(opts)) % len(opts)
    b = (a + 1 + int(hash01(seed, 32) * (len(opts) - 1))) % len(opts)
    return opts[a], opts[b]


def _flagpole(w: World, p: dict, ctx) -> dict:
    """A tall pole on a stepped base, with a banner that reads in silhouette.

    THE FLAG IS THE FEATURE AND IT IS DRAWN AS A SILHOUETTE, so the pattern is bold - bands, a
    cross, a chevron, a half or a quarter - and never a texture. At six cells wide a detailed
    device is noise; two colours in a large shape is legible from the far side of a plaza, which
    is the only distance a flag is ever read at.
    """
    f = _Frame(p)
    pal = LANDS[p["land"]]
    say = _Plaques(p.get("sign", True))
    seed = _seed_of(p, f)
    height = _span(seed, 1, 12, 18)
    fw = _span(seed, 2, 4, 6)
    fh = _span(seed, 3, 4, 6)
    pattern = _pick(("bands", "cross", "chevron", "half", "quarters"), seed, 4)
    swallow = hash01(seed, 5) < 0.45
    a, b = _cloth(seed, p["land"])

    ci = cd = 3
    _pad(w, f, pal, -1, 7, -1, 7)

    # ---- a stepped base: 7x7, 5x5, 3x3, with a flared skirt round the widest course
    for i in range(0, 7):
        for d in range(0, 7):
            edge = i in (0, 6) or d in (0, 6)
            w.put(*f.at(i, d, 0), pal["trim"] if edge else pal["ground"])
    _skirt(w, f, pal, -1, 7, -1, 7, h=0)
    for i in range(1, 6):
        for d in range(1, 6):
            edge = i in (1, 5) or d in (1, 5)
            w.put(*f.at(i, d, 1), pal["trim"] if edge else pal["ground"])
    for i in range(2, 5):
        for d in range(2, 5):
            w.put(*f.at(i, d, 2), pal["trim"])

    # ---- the pole: a solid butt you can hang a plaque on, then a thin shaft
    for h in range(3, 6):
        w.put(*f.at(ci, cd, h), pal["post"])
    for h in range(6, height + 1):
        w.put(*f.at(ci, cd, h), pal["fence"], north="false", south="false",
              east="false", west="false", waterlogged="false")
    w.put(*f.at(ci, cd, height + 1), pal["accent"])
    w.put(*f.at(ci, cd, height + 2), "end_rod", facing="up")

    # ---- lanterns standing on the third step's corners, never on the pole
    for (i, d) in ((2, 2), (2, 4), (4, 2), (4, 4)):
        w.put(*f.at(i, d, 3), pal["light"], hanging="false", waterlogged="false")

    # ---- the flag: a rectangle in the (i, h) plane hard against the pole, so the column nearest
    # the mast touches it and the rest of the cloth touches that. One piece by construction.
    h0 = height - fh
    cells = 0
    for k in range(fw):
        for lv in range(fh):
            if swallow and k >= fw - 2 and abs(lv - (fh - 1) / 2) > (fw - 1 - k) + 0.5:
                continue                             # the swallow tail, notched out of the fly
            if pattern == "bands":
                blk = a if (lv * 2) // max(1, fh) == 0 else b
            elif pattern == "cross":
                blk = a if (k == fw // 2 or lv == fh // 2) else b
            elif pattern == "chevron":
                blk = a if k <= abs(lv - (fh - 1) // 2) else b
            elif pattern == "half":
                blk = a if k < fw // 2 else b
            else:
                blk = a if ((k < fw // 2) == (lv < fh // 2)) else b
            w.put(*f.at(ci + 1 + k, cd, h0 + lv), blk)
            cells += 1

    title = str(p.get("title") or "THE PARK").upper()
    # ON THE POLE'S OWN BUTT, which is `pal["post"]` and solid for three courses. `facing` is the
    # direction the TEXT looks, so the support `park._sign` checks is one cell behind it - which
    # is the butt, and is why the plaque is at d = cd - 1 rather than at the pole's own cell.
    say(w, f, pal, ci, cd - 1, 4, f.facing, [title[:SIGN_WIDTH], "", "flown daily", ""])

    return {"kind": "flagpole", "height": height + 3, "flag": (fw, fh), "pattern": pattern,
            "swallow": swallow, "cloth": [a, b], "cells": cells, "seed": seed,
            "signs": say.want, "signs_placed": say.got,
            "contract": "a pole twelve to eighteen courses on a three-step base, carrying a "
                        "two-colour banner whose pattern reads as a silhouette"}


# ---------------------------------------------------------------------------- the fingerpost

def _signpost(w: World, p: dict, ctx) -> dict:
    """A fingerpost: a post with two or three projecting arms, each carrying a sign.

    **EVERY ARM IS A FULL BLOCK AND EVERY SIGN HANGS ON IT.** A wall sign sits in the cell IN
    FRONT of its support and its `facing` is the direction the TEXT looks - so the arm goes one
    cell out from the post and the sign one cell beyond that, and `park._sign` checks the cell
    behind rather than trusting the arithmetic. Written the other way round the sign lands ON the
    arm, the cell is occupied, nothing is placed, and the fingerpost points nowhere in silence.
    """
    f = _Frame(p)
    pal = LANDS[p["land"]]
    say = _Plaques(p.get("sign", True))
    seed = _seed_of(p, f)
    n = int(p["arms"]) if p.get("arms") is not None else _span(seed, 1, 2, 3)
    n = max(2, min(4, n))
    cap = _pick(("lantern", "finial"), seed, 2)

    ci = cd = 1
    height = 3 + n
    _pad(w, f, pal, -1, 3, -1, 3)

    # ---- base and shaft, the lamppost's own moulding at the smaller size
    for i in range(0, 3):
        for d in range(0, 3):
            w.put(*f.at(i, d, 0), pal["trim"])
    _skirt(w, f, pal, -1, 3, -1, 3, h=0)
    for i in range(0, 3):
        for d in range(0, 3):
            if (i, d) != (ci, cd):
                _slab(w, f, i, d, 1, pal["slab"], "bottom")
    for h in range(1, height + 1):
        w.put(*f.at(ci, cd, h), pal["post"])

    # ---- the arms. Four cardinals, dealt so no two arms of one post point the same way, and at
    # descending heights so the post reads as a fingerpost rather than as a crossroads sign.
    dirs = [(1, 0), (0, -1), (-1, 0), (0, 1)]
    start = int(hash01(seed, 3) * 4) % 4
    ways = []
    for k in range(n):
        di, dd = dirs[(start + k) % 4]
        h = height - 1 - k
        w.put(*f.at(ci + di, cd + dd, h), pal["trim"])
        name, tag = _WAYS[int(hash01(seed, 4, k) * len(_WAYS)) % len(_WAYS)]
        placed = say(w, f, pal, ci + 2 * di, cd + 2 * dd, h, _off_dir(f, di, dd),
                     [name[:SIGN_WIDTH], tag[:SIGN_WIDTH]])
        ways.append({"dir": _off_dir(f, di, dd), "h": h, "to": name, "placed": bool(placed)})

    w.put(*f.at(ci, cd, height + 1), pal["trim"])
    if cap == "lantern":
        w.put(*f.at(ci, cd, height + 2), pal["light"], hanging="false", waterlogged="false")
    else:
        w.put(*f.at(ci, cd, height + 2), pal["accent"])
        w.put(*f.at(ci, cd, height + 3), "end_rod", facing="up")

    return {"kind": "signpost", "arms": n, "cap": cap, "ways": ways, "seed": seed,
            "signs": say.want, "signs_placed": say.got,
            "contract": "two to four arms pointing different ways, each a full block with its "
                        "sign in the cell beyond it, so every sign has something to hang on"}


# ---------------------------------------------------------------------------- the litter bin

def _bin(w: World, p: dict, ctx) -> dict:
    """A litter bin: two or three courses with a rim, which is all a bin is.

    THE RIM IS THE WHOLE PIECE. A two-block column of one material is a bollard; a cauldron, a
    composter or a slab lip on top of it is a bin, and the three read as three different bins on
    the same plaza rather than as one repeated.
    """
    f = _Frame(p)
    pal = LANDS[p["land"]]
    seed = _seed_of(p, f)
    style = p.get("style") or _pick(("cauldron", "composter", "capped"), seed, 1)
    if style not in ("cauldron", "composter", "capped"):
        raise ValueError(f"unknown bin style {style!r}; have ['capped', 'cauldron', 'composter']")
    tall = _span(seed, 2, 2, 3)
    banded = hash01(seed, 3) < 0.5

    ci = cd = 1
    _pad(w, f, pal, 0, 2, 0, 2)

    for h in range(tall):
        if h == 0:
            blk = pal["trim"]
        elif banded and h == 1:
            blk = pal["accent"]
        else:
            blk = pal["post"]
        w.put(*f.at(ci, cd, h), blk)

    if style == "cauldron":
        w.put(*f.at(ci, cd, tall), "cauldron")
    elif style == "composter":
        w.put(*f.at(ci, cd, tall), "composter", level="0")
    else:
        _slab(w, f, ci, cd, tall, pal["slab"], "bottom")

    return {"kind": "bin", "style": style, "height": tall + 1, "banded": banded, "seed": seed,
            "contract": "a bin between two and three courses tall with a rim on top of it, "
                        "standing on its own paved cell"}


BUILDERS = {
    "bench": _bench,
    "planter": _planter,
    "lamppost": _lamppost,
    "topiary": _topiary,
    "flagpole": _flagpole,
    "signpost": _signpost,
    "bin": _bin,
}


def build(cfg: dict, donors=None) -> Canvas:
    p = {**FURNITURE, **cfg}
    if not p.get("at"):
        raise ValueError("streetfurniture needs params.at = [x, y, z] of the front-left corner")
    if p["facing"] not in _STEP:
        raise ValueError(f"facing must be one of {sorted(_STEP)}")
    if p["kind"] not in BUILDERS:
        raise ValueError(f"unknown streetfurniture kind {p['kind']!r}; have {sorted(BUILDERS)}")
    if p["land"] not in LANDS:
        raise ValueError(f"unknown land {p['land']!r}; have {sorted(LANDS)}")

    w = World()
    ctx = Ctx(p["under"]) if p.get("under") else None
    meta = BUILDERS[p["kind"]](w, p, ctx)

    return w.canvas({
        # `kind` IS EXCLUDED FROM THE SPREAD, and that is not a style choice. Every builder
        # returns its own short `kind` in its meta, so spreading the meta over this dict
        # OVERWRITES the namespaced one and the sidecar ends up saying `bench` where the config
        # said `streetfurniture`. The piece keeps its own name under `piece`.
        "kind": f"streetfurniture/{p['kind']}",
        "piece": p["kind"],
        "land": p["land"],
        "facing": p["facing"],
        "contract": meta.get("contract", ""),
        "unverified": meta.get("unverified", []),
        **{k: v for k, v in meta.items() if k not in ("kind", "contract", "unverified")},
    })
