"""THE CLAIM ROW AND THE MUSTER YARD - the ground the modules never built.

Jack, looking down Frontier column A: *"basically everything on this row from the orange flag to
the tower is useless/waste of usage of space."*

**MEASURED, AND THE CAUSE IS TWO CORRECT RULES MEETING.** Over the shipped park, the row from the
Prospecting Porch's pennant to the Vantage Lookout - V24-146 x U0-39, 5,840 columns - is **54% bare
moss**, and it carries one thing a guest can operate. The two biggest holes are not between the
modules, they are INSIDE them:

    Trailhead Gate      V24-68    1,800 cols   3.4 b/col   63% bare   a walled court, empty middle
    Prospecting Porch   V69-118   2,000 cols   3.1 b/col   54% bare   built as a strip on one flank
    the gap             V119-129    440 cols   1.1 b/col   52% bare
    Vantage Lookout     V130-146    680 cols   7.9 b/col   34% bare

* `frontier_builds._trailhead` builds a portal, two towers, an office, a porch, a stockade, a
  water tower and a store - and leaves its own ~24 x 31 court as untouched lawn. That is the shape
  Jack retired the Arrival Court for: *"a large rectangular building with an open center."* An open
  threshold is right; nine hundred columns of nothing in it is not, and **there is no paved route
  through the gate at all** - you come through a monumental portal onto a lawn.
* `frontier_builds._porch_lot`'s own docstring says why it does not fill its lot: its declared west
  door *"opens into the BACK OF TRAILHEAD GATE"*, so it is a strip on the avenue flank and U0-18 is
  its unbuilt back - pressed against the gate's unbuilt back. **Two buildings' backsides facing
  each other across twenty columns of lawn.**
* And `frontier_scatter` cannot reach either, correctly: it KEEPS OUT of every module's lot, because
  a material test cannot tell its own pine from the Diggings'. So the ground that is inside a lot
  and outside a building belongs to nobody, and that is exactly where the 3,153 columns are.

**THIS DESIGN OWNS THAT GROUND.** Two kinds, because the two dead zones are different places:

    claims   a worked-out placer flat - the porch's back and the gap up to the lookout
    yard     the muster yard inside the Trailhead Gate's own walled court

**NO WATER ANYWHERE IN IT.** Jack, on the Frontier: *"we dont need more water, we can do a
landscape or something with 1 or 2 small shops integrated."* A played-out placer claim is dry by
definition - the wash is worked out and the creek has moved - so the constraint and the subject
agree, and there is no creek, no pool and no trough here.

**AND NOT ONE BUILDING.** *"i dont want a bunch of buildings to go into, this is just a village
then."* Everything here is ground, a fence, a prop or a machine's collar. The tallest thing is a
windlass.

**IT CHANGES THE SURFACE, WHICH IS WHAT THE COMPLAINT IS ABOUT.** Scattering props over moss leaves
a green carpet with things standing on it - Jack's words about this land twice. The worked ground is
the design: a measured value ladder laid at the plane, reaching out from the way and the claims and
fading raggedly into untouched moss, so the flat reads as ground somebody turned over. **And the
mix is a function of how worked each cell is**, off the same score that decides how far the working
reaches - so the tone gradient and the outline are one thing and cannot drift apart. See `KIT`.

Rules this runs under, each of which has already cost this repo a rebuild:

* **PASSABLE IS NOT EMPTY.** A vine or a carpet answers "yes" to *can light pass* and "no" to *may
  I build here*. Every candidate goes through `_Ground`, which asks the WORLD it is verified
  against - the shop islet's own lesson, one design, two worlds, two answers.
* **RULE 15: a cell this design itself placed is built progress** - answered by `previous:`, which
  reads this design's own shipped litematic, and NOT by a material list. Every module in this land
  is stone brick, blackstone and spruce, so a material test cannot tell a neighbour's plinth from
  this design's own: it put a board post through the Prospecting Porch's marquee and grew 39 cells
  of canopy into the Trailhead Gate before `shipped_cells` replaced it.
* **GRAVEL FALLS (rule 13).** It is only ever the top course of a column that is solid to the
  ground, so nothing here can pour into the void.
* **A COLUMN TEST IS NOT A CELL TEST.** `lawn` decides where a post may stand; `free` decides where
  a canopy or a beam may go.
* **A SIGN'S SUPPORT IS CHECKED, NEVER HOPED FOR** - `_Lot.sign` refuses, and a refused sign is
  counted, because four of the park's building kinds once shipped a nameplate hung on air.
"""
from __future__ import annotations

from .canvas import Canvas, hash01
from .frontier_builds import EAST, SOUTH, _Lot
from .frontier_scatter import _Ground, _boulder, _pine, _snag, shipped_cells
from .vertical import Ctx

#: The worked flat's own kit. Every entry is checked against `blocks.available` (the 1.19 server),
#: `blocks.spendable` (dirt and grass are CURRENCY here) and `palette.tier` by
#: `tests/test_claimrow.py`, which asks the registry rather than trusting this comment.
KIT = {
    # ---------------------------------------------------------------------------------------
    # THE WORKED GROUND, AND IT IS A MEASURED VALUE LADDER ACROSS FAMILIES.
    #
    # The first build laid gravel 128, cobblestone 127, andesite 136, stone 126 and mossy
    # cobblestone 115 - **five materials inside twenty-one points of luminance**, which is one
    # grey however they are mixed, and the flat rendered as a pale slab. That is the identical
    # mistake `mineridge` records ("four materials inside ten points... a mass of those four is
    # one grey"), and the one CLAUDE.md has now made in four separate places, every time by
    # searching WITHIN a material family where a ladder cannot exist by construction.
    #
    # Measured with `blocks.color(name, "side")`, cheap-or-ok and on the 1.19 server:
    #
    #     cobbled_deepslate  77   the dark - spoil, and what a shaft throws up
    #     dripstone_block   112   turned earth, and WARM, so it is not a fifth grey
    #     cobblestone       127   the wash
    #     gravel            128   the crust - rule 13, top course only
    #     diorite           188   the pale washed bars
    #
    # Smallest adjacent step 15, biggest 60, against the ~15 below which a tone stops being a
    # tone at all. `tests/test_claimrow.py` re-derives it rather than trusting this comment.
    "spoil": "cobbled_deepslate",
    "earth": "dripstone_block",
    "wash": "cobblestone",
    "crust": "gravel",                  # RULE 13: top course only, always over solid ground
    "pale": "diorite",
    "wash_moss": "mossy_cobblestone",
    "ore": "coal_ore",
    #: **A BOUNDARY HAS TO BE A DIFFERENT VALUE FROM THE GROUND IT BOUNDS.** The first build kerbed
    #: every claim in `cobblestone_slab` - 127 against a working that runs 77-128, so a hundred and
    #: fifty slabs of it drew no line at all from the one view this reads from, which is the plan.
    #: 77 against a mid of ~120 is the same 50-point step `deepslate_bricks` gives the island's own
    #: masonry, and it is cheap.
    "kerb": "cobbled_deepslate_slab",
    # the way, and the yard's paving
    "pave": "smooth_stone",
    "pave_b": "stone_bricks",
    "pave_worn": "cracked_stone_bricks",
    "pave_moss": "mossy_stone_bricks",
    "plinth": "polished_blackstone_bricks",
    "pave_slab": "stone_brick_slab",
    "pave_stair": "stone_brick_stairs",
    # timber
    "post": "spruce_log",
    "beam": "stripped_spruce_log",
    "plank": "spruce_planks",
    "slab": "spruce_slab",
    "stair": "spruce_stairs",
    "fence": "spruce_fence",
    "gate": "spruce_fence_gate",
    "shutter": "spruce_trapdoor",
    "sign": "spruce_wall_sign",
    # fittings
    "glow": "ochre_froglight",          # flush: it IS the floor, and nobody can knock it off
    "lamp": "lantern",
    "chain": "iron_chain",
    "barrel": "barrel",
    "bell": "bell",
    "rail": "rail",
    "board": "white_wool",
    "paint": "red_wool",
}

#: **RULE 15 IS ANSWERED BY `shipped_cells`, NOT BY A MATERIAL LIST, AND THAT IS THE WHOLE POINT.**
#: A cell this design placed is built progress rather than an obstruction - but every module in
#: this land is stone brick, blackstone and spruce, so a material test cannot tell a neighbour's
#: plinth from this design's own. Measured on the first two builds: the claim row put a board post
#: and a pine straight through the Prospecting Porch's marquee (its plinth is
#: `polished_blackstone_bricks`, and so is this design's), and the muster yard grew **39 cells of
#: canopy into the Trailhead Gate**. Widening or narrowing a material set only trades one of those
#: failures for the other; the design's own previous cells are knowable EXACTLY, off its own
#: shipped litematic, so that is what `previous:` reads and what the ground probe trusts.
#:
#: What stays here is the one thing that is genuinely ground cover rather than anybody's build:
#: `moss_carpet`, which every design in this park declares replaceable.
OWN = frozenset({"moss_carpet"})

CLAIMROW = {
    "kind": "claims",              # claims | yard
    "lot": None,                   # [dv, du] - the ground this owns
    "at": None,                    # [V, U]
    "anchor": [97500, 203, 80300],
    "under": None,                 # the world this is verified against - ASK THE SAME ONE
    #: This design's OWN shipped artifact, if it has one. Rule 15 without a material heuristic:
    #: the cells named here are treated as this design's own and everything else in the world
    #: blocks, whatever it is made of. Absent is the correct answer for a first run.
    "previous": None,
    "sy": 16,
    #: LOCAL [[v0, v1, u0, u1], ...] - ground inside this lot that another design owns. `_Ground`
    #: already refuses a cell the world fills, so this is for ground that is EMPTY and still not
    #: ours: a neighbour's unbuilt remainder, or a walk the ground layer will pave later.
    "keep_out": [],
    "way": None,                   # claims: {"u": near edge, "w": width} - the packed way
    "legs": [],                    # yard: [[v0, v1, u0, u1], ...] - the paved way's straight runs
    "claims": [],                  # claims: [{v, u, dv, du, no, name}]
    "pits": [],                    # claims: [[v, u], ...] - a prospect pit and its windlass
    "props": [],                   # yard: [[v, u, kind], ...] - see `_PROPS`
    "worked": 7.0,                 # how far the worked ground reaches from the way and the claims
    "plant": None,                 # {"step": n, "density": f, "kinds": [...]}
    "clear": 1,                    # how far a planted trunk must be from anything built or paved
    "seed": 0,
    "title": "THE CLAIM ROW",
}


# --------------------------------------------------------------------------- the ground


#: **THE MIX IS A FUNCTION OF HOW WORKED THE CELL IS, NOT ONE NOISE OVER THE WHOLE FLAT.** A
#: single mix laid everywhere is a texture, and a texture over a thousand columns is a slab with
#: speckles on it - which is what the first build rendered as. The middle of a working has been
#: turned over, so it is spoil and earth; the edge has been barely scratched, so it is gravel and
#: moss showing through. Reading the mix off the SAME score that decides where the ground reaches
#: means the tone gradient and the outline are one thing and cannot drift apart.
_MIX = (
    # (up to this worked-ness, ((key, share), ...))
    (0.45, (("crust", 0.30), ("wash", 0.22), ("wash_moss", 0.26), ("pale", 0.10),
            ("earth", 0.12))),
    (0.75, (("crust", 0.28), ("wash", 0.28), ("earth", 0.24), ("spoil", 0.10),
            ("pale", 0.10))),
    (1.01, (("earth", 0.30), ("spoil", 0.26), ("wash", 0.24), ("crust", 0.14),
            ("pale", 0.06))),
)


def _crust(lot: _Lot, g: _Ground, v: int, u: int, seed: int, ore=False, depth: float = 1.0) -> int:
    """One column of worked ground, at the plane.

    **GRAVEL IS A CRUST AND NOTHING ELSE (rule 13).** It goes at y0, whose support is the world's
    own lawn block one course down - so it can never be the thing with air under it. Everything
    else in the ladder is rock and does not fall, so a heap can be built out of it.
    """
    if not g.lawn(v, u) or lot.has(v, 0, u):
        return 0
    # **THE MATERIAL IS CHOSEN ON A COARSE LATTICE, NOT PER CELL.** Drawn per cell, five materials
    # over a thousand columns is static - a slab with speckles on it, which is the confetti failure
    # the deck soffit and the Lowland Thicket both shipped, in stone. Three quarters of the draw
    # comes from a 3x3 block of ground and a quarter from the cell, so the flat comes out as
    # PATCHES with ragged edges: a heap of spoil here, a gravel bar there, which is what ground
    # somebody has turned over actually looks like.
    r = 0.75 * hash01(v // 3, u // 3, seed + 3) + 0.25 * hash01(v * 5 + 1, u * 11 + 7, seed + 4)
    if ore and hash01(v, u, seed + 9) < 0.035:
        return 1 if lot.put(v, 0, u, KIT["ore"]) else 0
    table = next(t for lim, t in _MIX if depth < lim)
    acc = 0.0
    key = table[-1][0]
    for name, share in table:
        acc += share
        if r < acc:
            key = name
            break
    return 1 if lot.put(v, 0, u, KIT[key]) else 0


def _worked(lot: _Lot, g: _Ground, p: dict, seeds, seed: int) -> dict:
    """The worked flat itself - the single biggest thing this design does.

    **THE REACH IS NOISY, NOT THE CELL.** Thresholded per cell this is confetti, which is exactly
    what the Lowland Thicket shipped and had to rebuild, and what the deck soffit shipped one
    surface up. The noise goes on how far the working reaches from each seed, so the middle fills
    solid and only the boundary wobbles - which is what the edge of a worked-out wash looks like.

    **AND IT FADES OUT.** A rectangle of gravel is a car park in a different colour; what makes it
    read as ground somebody turned over is that it stops raggedly, with moss showing through.
    """
    reach = float(p.get("worked") or 0)
    if reach <= 0 or not seeds:
        return {"cells": 0, "reach": reach}
    n = 0
    for v in range(lot.dv):
        for u in range(lot.du):
            best = 0.0
            for sv, su in seeds:
                d = max(abs(v - sv), abs(u - su)) * 0.6 + (abs(v - sv) + abs(u - su)) * 0.2
                if d >= reach * 1.6:
                    continue
                # the noise is on the REACH, sampled coarsely so a boundary lobes rather than
                # speckling: one value per 3x3 of ground, not one per cell.
                wob = 0.55 + 0.9 * hash01(v // 3, u // 3, seed + 17)
                best = max(best, 1.0 - d / max(1.0, reach * wob))
            if best > 0.34:
                # the score is BOTH the outline and the tone - see `_MIX`
                n += _crust(lot, g, v, u, seed, ore=best > 0.8, depth=best)
    return {"cells": n, "reach": reach}


def _way(lot: _Lot, g: _Ground, p: dict, seed: int) -> dict:
    """The packed way down the flat, so the ground is WALKED and not merely looked at.

    One course proud of the moss, which is a free step in Minecraft and therefore needs no flight;
    the kerb slab outside it is the half-step that says where the way ends. Froglights are set
    FLUSH in it - the island's own idiom, an opaque emitter a course down, so its reach is 14 and
    not 15, and nothing on a walkway can be knocked off.
    """
    spec = p.get("way") or {}
    u0 = int(spec.get("u", 1))
    w = max(1, int(spec.get("w", 3)))
    every = max(4, int(spec.get("glow_every", 11)))
    cells = kerb = glow = 0
    for v in range(lot.dv):
        for k in range(w):
            u = u0 + k
            if not g.lawn(v, u) or lot.has(v, 0, u):
                continue
            mid = k == w // 2
            if mid and v % every == every // 2:
                glow += 1 if lot.put(v, 0, u, KIT["glow"]) else 0
                continue
            # THE WAY IS THE HARDEST-PACKED GROUND ON THE FLAT, so it reads darker than the
            # working either side of it. That contrast is the only thing that makes a way in
            # gravel legible as a way rather than as more gravel.
            r = hash01(v * 3 + 2, u * 7 + 5, seed + 5)
            key = "wash" if r < 0.38 else ("spoil" if r < 0.66 else
                                           "crust" if r < 0.88 else "earth")
            cells += 1 if lot.put(v, 0, u, KIT[key]) else 0
        for u in (u0 - 1, u0 + w):
            if g.lawn(v, u) and not lot.has(v, 0, u) and hash01(v, u, seed + 6) < 0.72:
                kerb += 1 if lot.slab(v, 0, u, KIT["kerb"], "bottom") else 0
    return {"u": [u0, u0 + w - 1], "cells": cells, "kerb": kerb, "glow": glow}


def _heap(lot: _Lot, g: _Ground, v0: int, u0: int, r: int, h: int, seed: int) -> int:
    """A tailings heap: built from the ground UP, so nothing in it is ever unsupported.

    Written the obvious way - each column straight to its own height - the top course of a wide
    heap lands on columns the courses below never reached. `mineridge` records the same trap and
    the frontier scatter's timber stack shipped it once as six free-floating clusters.
    """
    n = 0
    for dv in range(-r, r + 1):
        for du in range(-r, r + 1):
            v, u = v0 + dv, u0 + du
            if not g.lawn(v, u):
                continue
            d = (dv * dv + du * du) ** 0.5
            wob = 0.75 + 0.5 * hash01(v // 2, u // 2, seed + 23)
            top = int(round(h * max(0.0, 1.0 - d / max(0.9, r * wob))))
            for y in range(top):
                # **A HEAP HAS A SECTION.** Spoil at the bottom where the shaft's dark rock went
                # first, turned earth over it, and the CRUST only at the very top of the stack -
                # which is rule 13 and also what a tip actually looks like.
                if y == top - 1:
                    key = "crust"
                elif y == 0:
                    key = "spoil"
                else:
                    key = "earth" if (y + v + u) % 3 else "spoil"
                n += 1 if lot.put(v, y, u, KIT[key]) else 0
    return n


def _rocker(lot: _Lot, g: _Ground, v: int, u: int, seed: int) -> int:
    """A gold rocker - a cradle box on two log rockers, with its handle.

    A PROP WITH A JOB, never a heap of vague blocks: the void tower had that rejected on sight, and
    the rule it produced is that regularity is what makes voxels read as a made thing.
    """
    n = 0
    for du in range(3):                                   # the two rockers it sits on
        for v2 in (v, v + 2):
            if g.lawn(v2, u + du):
                n += 1 if lot.log(v2, 0, u + du, KIT["beam"], axis="z") else 0
    for dv in range(3):                                   # the box
        for du in range(3):
            if not g.lawn(v + dv, u + du):
                continue
            edge = dv in (0, 2) or du in (0, 2)
            if edge:
                n += 1 if lot.put(v + dv, 1, u + du, KIT["plank"]) else 0
            else:
                n += 1 if lot.slab(v + dv, 1, u + du, KIT["slab"], "bottom") else 0
    if g.lawn(v + 1, u + 3):                              # the handle, off the back
        n += 1 if lot.fence(v + 1, 1, u + 3, "u", KIT["fence"]) else 0
        n += 1 if lot.fence(v + 1, 2, u + 3, "u", KIT["fence"]) else 0
    return n


def _barrow(lot: _Lot, g: _Ground, v: int, u: int, seed: int) -> int:
    """A barrow, tipped: a plank tray, a rail axle and a fence handle. Five cells."""
    n = 0
    if g.lawn(v, u):
        n += 1 if lot.put(v, 0, u, KIT["rail"], shape="north_south", waterlogged="false") else 0
    for dv in (0, 1):
        if g.lawn(v + dv, u + 1):
            n += 1 if lot.slab(v + dv, 0, u + 1, KIT["slab"], "bottom") else 0
    if g.lawn(v, u + 2):
        n += 1 if lot.fence(v, 0, u + 2, "v", KIT["fence"]) else 0
    if g.lawn(v + 1, u + 1) and hash01(v, u, seed + 41) < 0.5:
        n += 1 if lot.put(v + 1, 1, u + 1, KIT["barrel"], facing="up", open="false") else 0
    return n


def _claim(lot: _Lot, g: _Ground, spec: dict, seed: int) -> dict:
    """One staked claim: a kerbed working, four stakes, a numbered board, tailings and a rocker.

    **THE STAKES ARE WHAT MAKE IT A CLAIM AND NOT A PATCH OF GRAVEL.** A worked flat with no
    boundary in it is texture; a boundary with a number on it is somebody's ground, which is the
    whole story of a gold rush. The board is REFUSED rather than hoped for if its post did not
    stand, and the refusal is counted.
    """
    v0, u0 = int(spec["v"]), int(spec["u"])
    dv, du = int(spec.get("dv", 9)), int(spec.get("du", 7))
    v1, u1 = v0 + dv - 1, u0 + du - 1
    #: **NOT `no`.** YAML 1.1 parses `no:` as the BOOLEAN False, so a claim written `no: 1` comes
    #: out keyed `False` - which does not raise, silently loses the number, and then breaks the
    #: design fingerprint's `sort_keys` on a dict holding both a bool and a string. The Lowland
    #: Glow shipped the same trap with a key called `on`.
    out = {"v": [v0, v1], "u": [u0, u1], "number": spec.get("number"), "signed": False}
    n = 0
    for v in range(v0, v1 + 1):                           # the working itself, fully turned over
        for u in range(u0, u1 + 1):
            n += _crust(lot, g, v, u, seed, ore=True, depth=1.0)
    for v in range(v0, v1 + 1):                           # ...kerbed, a half course over it
        for u in (u0, u1):
            if lot.has(v, 0, u) and not lot.has(v, 1, u):
                n += 1 if lot.slab(v, 1, u, KIT["kerb"], "bottom") else 0
    for u in range(u0 + 1, u1):
        for v in (v0, v1):
            if lot.has(v, 0, u) and not lot.has(v, 1, u):
                n += 1 if lot.slab(v, 1, u, KIT["kerb"], "bottom") else 0
    for v, u in ((v0, u0), (v0, u1), (v1, u0), (v1, u1)):  # the four stakes
        if not lot.has(v, 1, u):
            continue
        n += 1 if lot.fence(v, 1, u, "v", KIT["fence"]) else 0
        n += 1 if lot.fence(v, 2, u, "v", KIT["fence"]) else 0
    # The numbered board, on its own post at one end of the claim's far edge, facing the way.
    #
    # **A SIGN GOES IN A CELL, AND `_Lot.sign` ONLY ASKS THE CANVAS.** It checks that the board has
    # something behind it and nothing in it - both true of a cell inside a NEIGHBOUR's keep-out
    # box, because the canvas is this design's own and knows nothing about the world. Measured:
    # claim 1's post stood legally at U13 and hung its sign at U14, one cell inside the Prospecting
    # Porch's marquee, and the sign refused SILENTLY.
    #
    # **SO IT TRIES BOTH ENDS.** A hand-tuned offset per claim is a number that goes stale the
    # first time a claim moves; asking for the near corner and falling back to the far one is the
    # same answer without anything to keep in sync, and `signed: false` still means neither worked.
    lines = [f"CLAIM No {spec.get('number', 1)}", str(spec.get("name", ""))[:15],
             str(spec.get("note", "worked out"))[:15]]
    for bv in (v0, v1):
        bu = u1 + 1
        if not (g.lawn(bv, bu) and g.free(bv, bu + 1, 2)):   # free(v, u, y) - NOT (v, y, u)
            continue
        for y in range(3):
            n += 1 if lot.log(bv, y, bu, KIT["post"], axis="y") else 0
        out["signed"] = lot.sign(bv, 2, bu + 1, SOUTH, [x for x in lines if x])
        out["board"] = [bv, bu]
        n += 1 if out["signed"] else 0
        break
    heap = spec.get("heap")
    if heap:
        n += _heap(lot, g, v0 + int(heap[0]), u0 + int(heap[1]), int(heap[2]), int(heap[3]), seed)
    if spec.get("rocker"):
        rv, ru = spec["rocker"]
        n += _rocker(lot, g, v0 + int(rv), u0 + int(ru), seed)
    if spec.get("barrow"):
        bv2, bu2 = spec["barrow"]
        n += _barrow(lot, g, v0 + int(bv2), u0 + int(bu2), seed)
    out["cells"] = n
    return out


def _pit(lot: _Lot, g: _Ground, v: int, u: int, seed: int) -> dict:
    """A prospect pit: a cribbed collar and a windlass over it.

    **A CHAIN HANGS FROM THE BLOCK ABOVE IT**, so the head beam goes in first and the chain is
    hung under it - placed blind, a string of links comes away as a loose fitting and the audit
    calls it out as a cluster with nothing to place against. The bat perch's vines and the stair
    head's chains both shipped that once.

    There is no hole. A litematic cannot express removal, so a shaft mouth here is a COLLAR - which
    is what `diggings._workings` does for the same reason, and what reads from above anyway.
    """
    out = {"at": [v, u], "windlass": False}
    n = 0
    for dv in range(-1, 2):                               # the cribbed collar, two courses
        for du in range(-1, 2):
            if abs(dv) + abs(du) == 0 or not g.lawn(v + dv, u + du):
                continue
            for y in (0, 1):
                n += 1 if lot.log(v + dv, y, u + du, KIT["post" if y else "beam"],
                                  axis="x" if dv else "z") else 0
    legs = [(v - 2, u), (v + 2, u)]
    ok = all(g.lawn(a, b) for a, b in legs)
    if ok:
        for a, b in legs:                                 # two legs, leaning in
            for y in range(4):
                n += 1 if lot.log(a, y, b, KIT["post"], axis="y") else 0
        for dv in range(-2, 3):                           # the head beam
            n += 1 if lot.log(v + dv, 4, u, KIT["beam"], axis="x") else 0
        for y in (2, 3):                                  # ...and the chain under it
            n += 1 if lot.put(v, y, u, KIT["chain"], axis="y", waterlogged="false") else 0
        if g.lawn(v, u):
            n += 1 if lot.put(v, 1, u, KIT["barrel"], facing="up", open="false") else 0
        n += 1 if lot.fence(v + 2, 4, u + 1, "u", KIT["fence"]) else 0   # the crank
        out["windlass"] = True
    out["cells"] = n
    return out


# --------------------------------------------------------------------------- the muster yard


def _leg(lot: _Lot, g: _Ground, box, seed: int, every: int = 9) -> dict:
    """One straight run of the yard's paving, kerbed, with a flush light down the middle.

    A guest comes through the Trailhead Gate's portal and, before this, walks on moss. **A
    THRESHOLD WITH NO PATH THROUGH IT IS A GATE ONTO A LAWN**, which is most of why the court read
    as unfinished whatever was standing round its edge.
    """
    v0, v1, u0, u1 = (int(x) for x in box)
    cells = glow = 0
    mv, mu = (v0 + v1) // 2, (u0 + u1) // 2
    run_v = (v1 - v0) >= (u1 - u0)
    for v in range(v0, v1 + 1):
        for u in range(u0, u1 + 1):
            if not g.lawn(v, u) or lot.has(v, 0, u):
                continue
            on_mid = (u == mu) if run_v else (v == mv)
            along = v if run_v else u
            if on_mid and along % every == every // 2:
                glow += 1 if lot.put(v, 0, u, KIT["glow"]) else 0
                continue
            r = hash01(v * 9 + 4, u * 5 + 3, seed + 7)
            key = ("pave" if r < 0.52 else "pave_b" if r < 0.78
                   else "pave_worn" if r < 0.9 else "pave_moss")
            cells += 1 if lot.put(v, 0, u, KIT[key]) else 0
    return {"box": [v0, v1, u0, u1], "cells": cells, "glow": glow}


def _hitch(lot: _Lot, g: _Ground, v: int, u: int, seed: int, n: int = 7) -> int:
    """A hitching rail: posts every third cell with a rail between them, along V."""
    out = 0
    for k in range(n):
        v2 = v + k
        if not g.lawn(v2, u):
            continue
        if k % 3 == 0:
            for y in (0, 1):
                out += 1 if lot.log(v2, y, u, KIT["post"], axis="y") else 0
        else:
            out += 1 if lot.fence(v2, 1, u, "v", KIT["fence"]) else 0
    return out


def _crates(lot: _Lot, g: _Ground, v: int, u: int, seed: int) -> int:
    """Freight, waiting: barrels and crated timber. The barrels are a verb - they open."""
    out = 0
    for dv in range(2):
        for du in range(2):
            if not g.lawn(v + dv, u + du):
                continue
            r = hash01(v + dv, u + du, seed + 51)
            if r < 0.45:
                out += 1 if lot.put(v + dv, 0, u + du, KIT["barrel"],
                                    facing="up", open="false") else 0
            else:
                out += 1 if lot.put(v + dv, 0, u + du, KIT["plank"]) else 0
                if r > 0.8:
                    out += 1 if lot.slab(v + dv, 1, u + du, KIT["slab"], "bottom") else 0
    return out


def _stack(lot: _Lot, g: _Ground, v: int, u: int, seed: int) -> int:
    """Cut timber, cross-piled. **EVERY COURSE SITS ON THE ONE UNDER IT** - written as rows at
    computed heights the top row lands on columns the bottom rows never touched, and the scatter
    shipped exactly that as six free-floating clusters."""
    out = 0
    for du in range(3):
        if g.lawn(v, u + du):
            out += 1 if lot.log(v, 0, u + du, KIT["beam"], axis="z") else 0
    for dv in range(-1, 2):
        if g.lawn(v + dv, u + 1) and lot.has(v, 0, u + 1):
            out += 1 if lot.log(v + dv, 1, u + 1, KIT["beam"], axis="x") else 0
    if lot.has(v, 1, u + 1):
        out += 1 if lot.log(v, 2, u + 1, KIT["beam"], axis="z") else 0
    return out


#: Which way a sign steps off the wall it hangs on, per facing. `_Lot.sign` checks the support at
#: `(v - dv, y, u - du)`, so the sign's own cell is the board's cell PLUS this step.
_FACE_STEP = {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0)}


def _notice(lot: _Lot, g: _Ground, v: int, u: int, seed: int, facing=SOUTH) -> dict:
    """The trail notice board: two posts, a plank field, and what a guest needs to know on it.

    **A GAME OR A GATE NOBODY CAN WORK OUT IS AN EMPTY STRUCTURE**, which is the complaint this
    whole pass answers. The board is the one thing in the court that tells you where the row goes.

    **THE SIGN'S CELL IS DERIVED FROM THE FACING, NOT HARD-CODED.** Written as `u + 1` the board
    can only ever be read from one side, so a board placed to be read from the WAY - which is the
    only reason to put one in a yard - hung its text on the far face and showed the walk its back.
    Our renderer draws a sign the same way round either way, so this is arithmetic, not a look.
    """
    out = {"at": [v, u], "facing": facing, "signed": 0}
    n = 0
    sv, su = _FACE_STEP[facing]
    for dv in (0, 3):
        for y in range(4):
            if g.lawn(v + dv, u):
                n += 1 if lot.log(v + dv, y, u, KIT["post"], axis="y") else 0
    for dv in range(1, 3):
        for y in (2, 3):
            n += 1 if lot.put(v + dv, y, u, KIT["board" if y == 3 else "plank"]) else 0
    for dv in range(1, 3):
        n += 1 if lot.slab(v + dv, 4, u, KIT["slab"], "bottom") else 0
    for dv, lines in ((1, ["THE CLAIM ROW", "stakes east", "keep to the way"]),
                      (2, ["THE LOOKOUT", "south, 60 out", "no ore past", "the stakes"])):
        if lot.sign(v + dv + sv, 3, u + su, facing, lines):
            out["signed"] += 1
            n += 1
    out["cells"] = n
    return out


def _bellpost(lot: _Lot, g: _Ground, v: int, u: int, seed: int, facing=SOUTH) -> dict:
    """The muster bell - the one thing in this design a guest OPERATES.

    A bell is a verb, it is cheap, it is on the 1.19 server, and it is what a trailhead actually
    has: the bell that calls a party away. **IT HANGS FROM A CEILING ATTACHMENT, SO THE BEAM GOES
    IN FIRST** - the same rule as a chain and a hanging lantern, and the reason `_Lot.hang` refuses
    a fitting with nothing over it.
    """
    out = {"at": [v, u], "bell": False}
    n = 0
    for dv in (0, 2):
        n += 1 if lot.put(v + dv, 0, u, KIT["plinth"]) else 0
        for y in range(1, 4):
            n += 1 if lot.log(v + dv, y, u, KIT["post"], axis="y") else 0
    for dv in range(3):
        n += 1 if lot.log(v + dv, 4, u, KIT["beam"], axis="x") else 0
    if lot.has(v + 1, 4, u):
        out["bell"] = lot.put(v + 1, 3, u, KIT["bell"], attachment="ceiling",
                              facing=facing, powered="false")
        n += 1 if out["bell"] else 0
    n += 1 if lot.slab(v + 1, 0, u, KIT["pave_slab"], "bottom") else 0
    out["cells"] = n
    return out


def _corral(lot: _Lot, g: _Ground, v0: int, u0: int, dv: int, du: int, seed: int) -> dict:
    """A pen: a fence ring with a real gate in it, and a rack of feed - no water anywhere.

    **THE GATE IS LEFT OUT BY THE RING, NEVER PUNCHED AFTERWARDS.** Building the ring and then
    replacing a cell repaints what already exists - the void tower's crenellations shipped as a
    plain drum for exactly this, and nothing about the code looked wrong.
    """
    v1, u1 = v0 + dv - 1, u0 + du - 1
    gate_v = (v0 + v1) // 2
    out = {"v": [v0, v1], "u": [u0, u1], "gate": False}
    n = 0
    for v in range(v0, v1 + 1):
        for u in (u0, u1):
            if not g.lawn(v, u):
                continue
            if u == u1 and v == gate_v:
                out["gate"] = lot.put(v, 0, u, KIT["gate"], facing=EAST, open="false",
                                      in_wall="false", powered="false")
                n += 1 if out["gate"] else 0
                continue
            n += 1 if lot.fence(v, 0, u, "v", KIT["fence"]) else 0
    for u in range(u0 + 1, u1):
        for v in (v0, v1):
            if g.lawn(v, u):
                n += 1 if lot.fence(v, 0, u, "u", KIT["fence"]) else 0
    for du2 in range(3):                                  # a feed rack along the back
        if g.lawn(v0 + 1, u0 + 1 + du2):
            n += 1 if lot.slab(v0 + 1, 0, u0 + 1 + du2, KIT["slab"], "bottom") else 0
    out["cells"] = n
    return out


def _wagon(lot: _Lot, g: _Ground, v: int, u: int, seed: int) -> int:
    """A flat wagon: two rail axles, a plank bed, boarded sides and a tongue."""
    n = 0
    for du in range(4):
        for v2 in (v, v + 3):
            if g.lawn(v2, u + du):
                n += 1 if lot.put(v2, 0, u + du, KIT["rail"], shape="north_south",
                                  waterlogged="false") else 0
    for dv in range(4):
        for du in range(4):
            if not g.lawn(v + dv, u + du) or (dv in (0, 3) and du in (0, 3)):
                continue
            if dv in (0, 3) or du in (0, 3):
                n += 1 if lot.put(v + dv, 1, u + du, KIT["plank"]) else 0
            else:
                n += 1 if lot.slab(v + dv, 1, u + du, KIT["slab"], "bottom") else 0
    for du in (4, 5):                                     # the tongue
        if g.lawn(v + 1, u + du) and lot.has(v + 1, 1, u + du - 1):
            n += 1 if lot.log(v + 1, 1, u + du, KIT["beam"], axis="z") else 0
    return n


_PROPS = {"hitch": _hitch, "crates": _crates, "stack": _stack, "wagon": _wagon,
          "barrow": _barrow, "rocker": _rocker}


# --------------------------------------------------------------------------- planting


def _plant(lot: _Lot, g: _Ground, p: dict, seed: int) -> dict:
    """Pines, snags and boulders on whatever ground the working left untouched.

    **IT SWEEPS RATHER THAN PLANTING A LIST OF STANDS**, for the reason the scatter measured: the
    open ground here is verges and gaps, and a hand-picked list of stand centres finds almost
    nothing. Anything the worked flat has already claimed is refused by `clearing`, so the trees
    land in the moss the working stopped at - which is where a tree would actually still be.
    """
    spec = p.get("plant") or {}
    if not spec:
        return {"trees": 0, "cells": 0}
    step = max(2, int(spec.get("step", 4)))
    dens = float(spec.get("density", 0.7))
    kinds = list(spec.get("kinds") or ("pine", "pine", "snag", "rock"))
    trees = cells = 0
    for v in range(1, lot.dv - 1, step):
        for u in range(1, lot.du - 1, step):
            jv = int(hash01(v, u, seed + 61) * step)
            ju = int(hash01(v, u, seed + 62) * step)
            a, b = v + jv, u + ju
            if hash01(a, b, seed + 63) > dens or not g.clearing(a, b):
                continue
            kind = kinds[int(hash01(a, b, seed + 64) * len(kinds)) % len(kinds)]
            if kind == "pine":
                got = _pine(lot, g, a, b, seed)
            elif kind == "snag":
                got = _snag(lot, g, a, b, seed)
            else:
                got = _boulder(lot, g, a, b, 1 + int(hash01(a, b, seed + 65) * 2), seed)
            if got:
                trees += 1
                cells += got
    return {"trees": trees, "cells": cells}


# --------------------------------------------------------------------------- entry point


def build(cfg: dict, donors=None) -> Canvas:
    p = {**CLAIMROW, **(cfg or {})}
    if not p.get("lot"):
        raise ValueError("the claim row needs its measured lot: lot: [dv, du]")
    if not p.get("under"):
        raise ValueError("the claim row reads the world it is verified against: under: <capture>")
    kind = str(p.get("kind"))
    if kind not in ("claims", "yard"):
        raise ValueError(f"unknown claim row kind {kind!r}; have claims | yard")
    dv, du = int(p["lot"][0]), int(p["lot"][1])
    seed = int(p.get("seed", 0))
    c = Canvas(dv, int(p.get("sy") or 16), du, donors)
    lot = _Lot(c, dv, du, seed=seed)
    anchor = [int(v) for v in p["anchor"]]
    at_v, at_u = (int(v) for v in (p.get("at") or (0, 0)))
    ctx = Ctx(p["under"])
    g = _Ground(ctx, anchor, dv, du, (at_v, at_u), int(p.get("clear", 1)),
                keep_out=p.get("keep_out") or (), own=OWN,
                mine=shipped_cells(p.get("previous")))

    parts: dict = {}
    if kind == "claims":
        # ORDER: the way, then the claims, then the flat that fades out from both of them, then
        # the pits, then the planting. The worked ground is laid AFTER the things it surrounds so
        # a crust cell can never take a cell a stake or a kerb wanted - and `_crust` refuses an
        # occupied cell, so this is a property of the order rather than of a check.
        parts["way"] = _way(lot, g, p, seed)
        parts["claims"] = [_claim(lot, g, spec, seed) for spec in (p.get("claims") or ())]
        seeds = []
        w = p.get("way") or {}
        wu = int(w.get("u", 1)) + max(1, int(w.get("w", 3))) // 2
        for v in range(0, dv, 3):
            seeds.append((v, wu))
        for spec in (p.get("claims") or ()):
            seeds.append((int(spec["v"]) + int(spec.get("dv", 9)) // 2,
                          int(spec["u"]) + int(spec.get("du", 7)) // 2))
        parts["worked"] = _worked(lot, g, p, seeds, seed)
        parts["pits"] = [_pit(lot, g, int(a), int(b), seed) for a, b in (p.get("pits") or ())]
    else:
        parts["legs"] = [_leg(lot, g, box, seed) for box in (p.get("legs") or ())]
        parts["props"] = []
        # **A YARD IS BEATEN GROUND WITH A ROUTE THROUGH IT, NOT A LAWN WITH A PATH ON IT.** The
        # first build paved the two legs and stopped: 116 cells of route in a nine-hundred-column
        # court, which leaves the court exactly as bare as the complaint found it. The apron is
        # the same mechanism the claim row's flat uses, seeded off the legs, so it fills the court
        # and fades out against the stockade instead of stopping at a drawn rectangle.
        seeds = []
        for box in (p.get("legs") or ()):
            v0, v1, u0, u1 = (int(x) for x in box)
            mv, mu = (v0 + v1) // 2, (u0 + u1) // 2
            if (v1 - v0) >= (u1 - u0):
                seeds += [(v, mu) for v in range(v0, v1 + 1, 3)]
            else:
                seeds += [(mv, u) for u in range(u0, u1 + 1, 3)]
        for entry in (p.get("props") or ()):
            v, u, what = int(entry[0]), int(entry[1]), str(entry[2])
            rest = entry[3:] if len(entry) > 3 else ()
            if what == "notice":
                # A BOARD IS PUT UP TO BE READ FROM A PARTICULAR SIDE, so the facing is the
                # caller's to state - it is which way the walk is, and only the config knows.
                face = str(rest[0]) if rest else SOUTH
                if face not in _FACE_STEP:
                    raise ValueError(f"a notice board needs a real facing, not {face!r}")
                parts["notice"] = _notice(lot, g, v, u, seed, facing=face)
            elif what == "bell":
                face = str(rest[0]) if rest else SOUTH
                parts["bell"] = _bellpost(lot, g, v, u, seed, facing=face)
            elif what == "corral":
                parts["corral"] = _corral(lot, g, v, u, int(rest[0]), int(rest[1]), seed)
            elif what in _PROPS:
                parts["props"].append({"at": [v, u], "kind": what,
                                       "cells": _PROPS[what](lot, g, v, u, seed)})
            else:
                raise ValueError(f"unknown yard prop {what!r}; have "
                                 f"{sorted(list(_PROPS) + ['notice', 'bell', 'corral'])}")
        # LAST, so the apron can never take a cell a prop or a leg wanted - `_crust` refuses an
        # occupied cell, which makes that a property of the order rather than of a check.
        parts["worked"] = _worked(lot, g, p, seeds, seed)
    parts["planting"] = _plant(lot, g, p, seed)

    c.world_origin = (anchor[0] + at_v, anchor[1], anchor[2] + at_u)
    c.meta = {
        "kind": f"frontier_{kind}",
        "lot": [dv, du],
        "at": [at_v, at_u],
        "land": "frontier",
        "facing": "west",
        "profile_axis": "u",
        "signs": lot.signs,
        "refused": lot.refused,
        "parts": parts,
        "contract": (
            "the ground inside Frontier column A's lots that no module ever built: worked placer "
            "ground laid at the plane and fading into untouched moss, a packed way that is walked "
            "rather than looked at, and staked, numbered claims with their tailings and rockers. "
            "No water, no building, and every candidate asked of the world this is verified "
            "against."
            if kind == "claims" else
            "the muster yard inside the Trailhead Gate's walled court: the paved route from the "
            "portal to the exit arch that the threshold never had, and the freight, pens and "
            "bell of a trail head. The bell is the verb."),
    }
    return c
