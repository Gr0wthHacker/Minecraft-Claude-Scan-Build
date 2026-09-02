"""The Isthmus: the land between the theme park's three islands.

THE THREE PLOTS WERE JOINED BY A BRIDGE AND NOTHING ELSE. `gen/transit.py` hangs a skyway four
courses over the street from one island to the next - a real fix for "you cannot get there" -
but it is a viaduct on piers, not ground, and Jack asked for the gap ITSELF to be built: "we need
to build all the land etc and fill in the areas between the islands outside of just the
connecting rails". A visitor who never once uses the railway should still be able to WALK across.

**AND IT SHOULD NOT BE AN EMPTY WALK.** Jack, on the first version: "the land between the
islands should have things along the way, sculptures, or other things to visit or do, we want
this to feel like 1 full big theme park with multiple sections." A bulge with two benches at the
midpoint is a passing place, not a section of a park. Each span now carries five stops spaced
along its length: two sited creatures, a still pool, a planted garden roundel, and an overlook
platform out past the rim at the middle - the overlook now carrying two REAL seats and the whole
span named at both of its own ends by a REAL threshold, not a pair of stair blocks and a lone sign.

**DO NOT WRITE NEW FURNITURE OR NEW SIGNAGE EITHER.** `gen/streetfurniture.py` (bench, planter,
lamppost, topiary, flagpole, signpost, bin) and `gen/wayfinding.py` (mapboard, fingerpost, marker,
archway, noticeboard) are both tested generators of their own, and pasting their output is the
same siting job a heron or a gecko already is here - `_site_bench` and `_site_archway` do it
exactly the way `_site_heron` does. Two things had to be added for it to work at all: `_paste` only
ever read block STATES (`_canvas_cells` walks `canvas.ids`/`canvas.palette`), so a pasted
`wayfinding.archway` shipped its own wall-sign block with nothing behind it - a sign is two things
in two halves of the file, and the TEXT half lives in `canvas.tiles`, JSON-encoded, keyed in the
sub-canvas's own LOCAL coordinates. `_paste` decodes it and re-records it in `w.signs` at the
PASTED position, same as any sign this file places directly. And `wayfinding.archway`'s own
`entering` is checked against `known_destinations()` - real module names, the three zone names,
and transit station titles - so only the zone names ("FRONTIER" / "MIDWAY" / "HOLLOW") are legal
things for an isthmus archway to say; a creature's own plaque is not a registered destination and
stays on the plain `_sign` this file already had, exactly as it did before.

**FOUR SCULPTURES, FOUR SHAPES, AND NOT ONE GENERATOR USED TWICE.** This repo has eight failed
mammal builds and three that read instantly behind it, and the line between them is not
species, it is PLANAR/COLUMNAR against VOLUMETRIC - a spread wing, a neck, a splayed limb, a
pattern on one convex mass all read; four legs standing on the ground never do, at any scale
(see CLAUDE.md's ANIMALS section). Everything on this causeway is chosen on that line.

Two of the four are SITED - `heron.py` and `sloth.py`, tested generators of their own, pasted
exactly the way `streetfurniture`'s bench and `wayfinding`'s archway are. Two are BESPOKE and
were written for these two stops: `balloon.py` and `wyrm.py`, which replaced a sited bat and a
sited gecko on Jack's own instruction - *"those are used assets, we want NEW things"*. See
`_SITERS` for what each of the four has to be given to stand up at all, and `GAPS` for why no
two may be the same generator.

**AND THE TWO NEW ONES CARRY THEIR OWN GROUND, WHICH IS THE POINT OF WRITING THEM.** A heron
wants a pedestal, a gecko a stele, a bat a gantry, a sloth a bough: every one of those is
masonry THIS file has to lay on terraced ground before the creature exists at all, and every
one of them is somewhere a pier can miss its footing - a gantry shipped with one leg and only a
render caught it. A balloon brings its own basket and a wyrm its own milestone, so `_site_standing`
is one paste and there is nothing left to get wrong.

`turtle.py`, `frog.py` and `axolotl.py` remain out on the standing grounds: all three take a
`Ctx` world capture and probe a ground band that assumes the lowland's own Y, and patching a
tested generator's internals to reuse it somewhere else is a bigger, riskier change than either
siting one that already stands on its own or writing one that does.

**AND A SCULPTURE IS NOT TERRAIN, WHICH IS THE OTHER HALF OF SITING ONE.** Every lighting rule
in this file is written for the SHAPE it lights, and the night sweep at the end had none - it
replaced the block under any dark cell with a froglight, which put **1,138 lamps inside the four
creatures' own coats** on the first shipped build and nowhere else at all. See `_delight`.

**THE TWO SPANS DIFFER BECAUSE THEY LEAD SOMEWHERE DIFFERENT.** The frontier reach runs bright
midway wool into weathered frontier spruce; the hollow reach runs midway into blackstone and
deepslate. `_land_at` dithers the SPINE'S material continuously across the whole walk - not a
hard swap at the midpoint but a probability that climbs from 0 to 1 with `t` itself, so the change
of land is felt underfoot the way the Lowland Stair's own gradient is (`spiral.bands`: a per-cell
hash dither, because a hard material boundary across a walkway reads as two builds stacked). The
two spans also carry different creatures and are never symmetric twins of each other.

**THE GAPS, MEASURED OFF THE THREE SHIPPED ZONES** (`out/Park_{Left,Centre,Right} Complete`):
every zone's own floor is flush at Y202, edge to edge, and the boundary Z row of each is paved
solid the whole way across - so there is no wall to break through, only void to cross.

    islandleft   Z 80351..80449   frontier
    newisle      Z 80551..80649   midway     (the entrance)
    islandright  Z 80751..80849   hollow

    gap A: Z 80450..80550   frontier <-> midway    101 columns of void
    gap B: Z 80650..80750   midway  <-> hollow      101 columns of void

**THE AVENUE IS ALREADY AIMED AT THE GAP, AND THAT DECIDED THE SITE.** Every zone's own
north-south avenue lands its kerb lamp posts at X 97592 and X 97598 on EVERY boundary row of
all three zones - the same two columns, on four different edges of three unrelated builds. That
can only mean one thing: the main avenue is centred on X 97595 and runs the zone's own full Z
span, edge to edge. So the isthmus's own spine is laid at that exact centre - not chosen to
match, INCAPABLE of not matching, because it is the same road continuing.

**AND THE GATEWAYS NEED IT WIDER THAN THE ORDINARY SPINE.** `midway`'s Frontier Arch and Hollow
Arch, the frontier's own Frontier Gate and the hollow's own Hollow Gate all stand square on
X 97591..97599 - nine columns, not the spine's ordinary seven. `_spine_half_at` widens the paved
spine to that same nine at the two flush ends and tapers back to the ordinary width within a few
rows, or the gateway would narrow into a track the moment it left the plot it belongs to.

**THE EAST STRIP IS THE RAILWAY'S, NOT OURS.** `transit.py` reserves X 97640..97649 for the
skyway's piers and arches (measured there as "not one cell at X >= 97643 in any zone"); this
design stops at X 97639 and never claims a column past it, so the skyway's piers pass overhead
in the open air this leaves them.

**A NARROWED CAUSEWAY WITH A SHELL, NOT A SOLID SLAB - the cost the brief itself calls out.** A
flat 99-wide plate at three courses deep across both gaps is 2*101*99*3 = 60,000 blocks, which
is more than the entire built park. Two things cut that by construction rather than by hollowing
it out afterward:

    NARROW    the outline flares to meet each plot and pinches to a neck at the void's own
              midpoint - "shoulder_max" wide at the ends, "shoulder_min" plus the spine at the
              waist - so most of a gap's width is never built at all. The five stops each open a
              local bulge in that outline, exactly the way the rest-stop bulge always did, so a
              pool or a plinth never has to steal room from the spine or the shoulder around it.
    SHELL     every column is capped and given exactly enough rock underneath to reach its
              LOWEST orthogonal neighbour (see `_seat`) plus one extra course at the true
              outline - never a fixed deep fill. The interior is two or three blocks thick; only
              the outline reads as a cliff.

**THE RIM IS DERIVED, NOT DRAWN.** A column is an edge - and gets the kerb, the fence and the
deeper shell - exactly where an orthogonal neighbour is MISSING from the shape, except at the
two ends where the missing neighbour is the island's own already-built ground. Drawing the rim
from a hand-picked outline shipped the void tower's own mistake in a new body once already in
this project (a punched doorway repaints cells that already exist); deriving it from the
footprint itself means an overlook bulge, a pool's own footprint or an edge-noise ripple all get
a rim for free, everywhere one is actually needed, and nowhere the shape flush-joins a plot.

**A STOP'S OWN FOOTPRINT IS FLATTENED BEFORE THE TERRACE IS EVEN CUT** (`_flatten`), so a pool's
bed, a garden's border and a plinth's own top are all level - built ground, not a shape that
happens to have the right average height. A still pool then follows `park._plaza_pool`'s own
proven rule: a solid bed under every water cell and a solid kerb on every open side, checked
again here with `mcbuild.fluids.unenclosed` because the frontier's own flume shipped ten
open-sided cells once already and it was a player who found it in a render, not a test.

**PLANT IN DRIFTS, ON MOSS, NEVER ON THE SPINE.** `gen/thicket.py`'s own rule, copied rather
than reinvented: the noise belongs on a drift's RADIUS, not on its interior, or the first result
is 191 blobs of which three quarters are one or two cells. Grass and dirt are CURRENCY on this
server (`blocks.spendable`) - the shoulders are `moss_block` with a `moss_carpet` fringe, exactly
`thicket`'s own soil, and the spine is never planted on at all.

**THE LIGHT IS THE SURFACE, NOT A FIXTURE ON IT** - `ochre_froglight` flush in the cap, this
island's own idiom since the lowland turf and the skyway's own deck. Verified to zero spawnable
cells by `nightlight`, the one source this repo has for what emits, what passes, and what a mob
can stand on. Every stop is EXCLUDED from the ambient lamp grid and given its own dedicated
light instead - a lamp buried inside a plinth two courses under a heron's feet lights nothing,
which is the same mistake `transit._lamps` was written to stop making.

GEOMETRY, stated once because getting it wrong is invisible in every render:

    t     0 at the gap's own first row (flush with the northern/western plot), 1 at its last
    x     world X; the spine is centred on X_SPINE and is unaffected by t
    dx    abs(x - X_SPINE); 0 on the spine's own centreline
"""
from __future__ import annotations

import math

import numpy as np

from . import park
from .canvas import Canvas, hash01
from .vertical import World
from .. import nbt

# --------------------------------------------------------------------------------- the geometry

X_SPINE = 97595          # measured: every zone's own avenue is centred here - see module docstring
X_MIN = 97551             # measured: the plots' shared west edge (`transit.PLOT_RADIUS` band)
RESERVE_X = 97640         # measured: transit.py's own corridor starts here. Never build at >= this.

BASE_Y = 202               # the park's own floor course; flush ends must land exactly on it

# The two gaps, measured off the shipped zones - see the module docstring's table. Each carries
# its own pair of sited creatures, so the two spans are never twins of one another.
#
# FOUR SCULPTURES, FOUR SHAPES, AND NOT ONE GENERATOR USED TWICE. The first version shipped a
# heron and a flamingo - the same body plan off `heron.py`, differing only in colour and two
# curves, which its own docstring says outright - and a ladybird on both spans. Four pieces
# showing two shapes, and the verdict on seeing it was exactly that: "we dont need 2 standing
# birds", and the ladybird had to go for its own reasons (see `_delight`). What replaces them is
# chosen on CLAUDE.md's own measured line, PLANAR/COLUMNAR against VOLUMETRIC, not on taste:
#
#   heron   an upright column - stilt legs, an S-neck, a dagger bill, a layered planar wing
#   sloth   a body slung UNDER a line - four columnar limbs hooked over a branch
#   balloon ONE convex dome carrying a pattern, on a column of rigging over a box
#   wyrm    a free S-curve topped by a flared PLATE, off a coil at the ground
#
# THE BAT AND THE GECKO WERE REPLACED, and by two BESPOKE generators rather than by two more
# borrowed ones. Jack: "get rid of the gecko and bat - those are used assets, we want NEW
# things". Both replacements are written to the same measured line and neither is an animal
# this repo had a body plan for; the balloon is not an animal at all, which a theme park's
# landmarks are under no obligation to be and which nothing here had ever tried.
#
# Scales are MEASURED with a flood fill, never assumed, because every one of these generators
# has its own fragility. `heron.py` is tuned for its full size and comes apart into a dozen
# fragments below about scale 0.85 - "wants to be built big rather than survive being small" is
# not a metaphor - and is one piece at 0.9. `sloth.py` has no scale parameter at all: its
# geometry is written at one size and it is one piece there, and the same is true of the two
# bespoke pieces, which are written for exactly this siting and are asserted one-piece at BOTH
# orientations they can be built at (`tests/test_causeway_sculptures.py`). `_largest_component`
# is the second line of defence in every case, and any cell it drops is reported rather than
# silently discarded.
#
# `dragonfly.py` was tried and dropped again, for the reason already recorded: its two wing
# pairs are `birch_trapdoor`s placed with a deliberate gap from the body and from each other
# ("closed birch trapdoors... need no support" - its own docstring), which is a real design
# choice for a piece meant to be looked at rather than placed, and it makes the model FIVE
# separate components by construction, at any scale. Bridging that gap would be editing a
# tested generator's own silhouette to suit this file, which is not a trade worth making for
# a fifth shape. `turtle.py`, `frog.py` and `axolotl.py` are out on the standing grounds: all
# three take a world CAPTURE (`Ctx`) and probe a ground band that assumes the lowland's own Y.
GAPS = [
    {"z_lo": 80450, "z_hi": 80550, "land_a": "frontier", "land_b": "midway",
     "title": "THE FRONTIER REACH",
     "creatures": [
         {"kind": "heron", "variant": "heron", "t": 0.14, "side": 1, "scale": 0.9,
          "title": "GREY HERON", "lines": ["stands in the", "frontier marsh"]},
         # brown fur and moss against spruce and cobble, hung in the air so its own outline is
         # read against the sky rather than against the ground it never touches.
         {"kind": "sloth", "t": 0.82, "side": -1, "clear": 5,
          "title": "SLOTH", "lines": ["asleep on a", "bough over two", "hundred of void"]},
     ]},
    {"z_lo": 80650, "z_hi": 80750, "land_a": "midway", "land_b": "hollow",
     "title": "THE HOLLOW REACH",
     "creatures": [
         # THE FAIRGROUND END OF THE REACH GETS A FAIRGROUND OBJECT. A theme park's landmarks do
         # not have to be creatures and this repo had never once tried one - a balloon is the
         # ladybird's own winning category (one convex mass carrying a PATTERN) over a column of
         # rigging, and it is the brightest thing on either span.
         {"kind": "balloon", "t": 0.26, "side": 1,
          "title": "THE AERONAUT", "lines": ["moored over two", "hundred blocks", "of open void"]},
         # ...and the hollow end gets the dark one. Bone against blackstone is the biggest value
         # flip this land can offer - the turtle's own rule, measured: a creature the colour of
         # its ground is not a creature.
         {"kind": "wyrm", "t": 0.80, "side": -1,
          "title": "THE PALE WYRM", "lines": ["reared off a", "milestone at", "the hollow gate"]},
     ]},
]

ISTHMUS = {
    "under": None,
    "kind": "isthmus",          # "isthmus" (both gaps, shipped) or "reach" (one, for tuning/tests)
    "gaps": None,                # reach only: overrides GAPS[0] with an explicit single gap dict
    "avoid": None,                # design .litematic paths whose cells are already somebody's

    "x_spine": X_SPINE,
    "x_min": X_MIN,
    "reserve_x": RESERVE_X,       # None disables the check - never used for the shipped kind

    "spine_half": 3,              # HALF the avenue's own measured width - the two must match
    "spine_half_wide": 4,          # HALF the gateways' own measured width, at the two flush ends
    "spine_wide_ramp": 0.06,       # fraction of the span the widened spine tapers back over
    "shoulder_min": 4,            # half-width of moss beyond the spine at the narrowest waist
    "shoulder_max": 30,           # half-width of moss beyond the spine where it meets a plot
    "flare_power": 1.6,           # > 1 keeps the waist narrow for longer before it flares
    "edge_noise": 0.22,           # per-row ripple on the outline, so the coastline is not a curve
    "rise_max": 2,                 # courses the spine humps up at the gap's own midpoint
    "terrace_drop_max": 2,        # courses the shoulder steps down before it reaches the rim
    "overlook_half": 9,            # half-width of the overlook bulge at midspan
    "overlook_span": 6,            # +/- rows of the overlook bulge around midspan
    "pool_t": 0.30, "pool_side": -1, "pool_radius": 3,
    "garden_t": 0.70, "garden_side": 1, "garden_radius": 6,
    "rim_shell": 4,                # extra courses the true outline drops below its own neighbours
    "light_every": 9,
    "drifts_per_span": 9,          # drift centres per gap, scaled by length inside `_build_gap`
    "drift_min_gap": 7,
    "drift_radius": 3.2,
    "seed": 0,
}

LAMP = "ochre_froglight"


def _land_at(land_a, land_b, t, seed):
    """Which land's masonry the spine takes at fraction t.

    A GRADUAL TRANSITION THE WHOLE WALK, not a hard swap at the midpoint - `spiral.bands`'s own
    idiom (the Lowland Stair's per-cell hash dither), because a hard material boundary across a
    walkway reads as two different builds stacked rather than one road that changes underfoot.
    The probability of the far land climbs with `t` itself, so it is certain at t=0 (the near
    plot's own colour), certain at t=1 (the far plot's), and mixed everywhere between.
    """
    return land_b if hash01(int(round(t * 4000)), seed, 41) < t else land_a


def _spine_half_at(p, t):
    """The paved spine's own half-width at fraction t: WIDE at the two flush ends, to match the
    gateways' own measured nine columns, tapering to the ordinary width within a few rows."""
    base, wide = int(p["spine_half"]), int(p["spine_half_wide"])
    ramp = max(1e-6, float(p["spine_wide_ramp"]))
    near_end = min(t, 1.0 - t)
    if near_end >= ramp:
        return base
    frac = near_end / ramp
    return int(round(wide - (wide - base) * frac))


def _half_at(p, t, mid_bulge, extra=0.0):
    """The shape's own half-width beyond the centreline at fraction t, BEFORE per-row noise.
    `extra` is a plain additional half-width, used by the five stops to open room for
    themselves without touching the overlook's own flat-bulge mechanism."""
    flare = abs(2 * t - 1) ** p["flare_power"]
    half = p["shoulder_min"] + (p["shoulder_max"] - p["shoulder_min"]) * flare
    if mid_bulge:
        half = max(half, p["overlook_half"])
    return p["spine_half"] + max(half, extra)


def _edge_fade(t, e=0.14):
    """0 at the two flush ends, 1 through the middle - keeps a terrace from cutting into the
    exact row that has to match a plot's own flat floor."""
    return max(0.0, min(1.0, min(t, 1.0 - t) / e))


# --------------------------------------------------------------------------------- placing things

def _sign(w, x, y, z, facing, wood, front, back=()):
    """A wall sign in the cell IN FRONT of its wall, its text facing away from its support.
    `park._sign` / `transit._sign`'s own rule: the support is CHECKED, never assumed."""
    fdx, fdz = park._STEP[facing]
    if not w.has(x - fdx, y, z - fdz):
        return False
    lines = [str(t)[:park.SIGN_WIDTH] for t in list(front)[:4]]
    lines += [""] * (4 - len(lines))
    w.put(x, y, z, f"{wood}_wall_sign", facing=facing, waterlogged="false")
    w.sign(x, y, z, front=lines, back=[str(t)[:park.SIGN_WIDTH] for t in list(back)[:4]],
           colour="white", glowing=True)
    return True


def _largest_component(cells: dict) -> dict:
    """Keep only the largest 6-connected piece of a {(x,y,z): (name, props)} dict.

    `heron.py` is tuned for its own full size and comes apart into a dozen small fragments
    below about scale 0.85 - measured with a flood fill, never assumed - and its own docstring
    says outright that it "wants to be built big rather than survive being small". This is the
    second line of defence, after simply choosing a scale where the model holds together: even
    at a safe scale a stray one- or two-cell fragment (a toe tip, a wisp of primary) can still
    ship, and a sited creature has no business handing this design a floating cell it did not
    build. Any cell dropped here is reported by the caller rather than silently discarded.
    """
    from collections import deque
    if not cells:
        return cells
    seen, best = set(), []
    for start in cells:
        if start in seen:
            continue
        q, comp = deque([start]), []
        seen.add(start)
        while q:
            p = q.popleft()
            comp.append(p)
            x, y, z = p
            for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
                nb = (x + d[0], y + d[1], z + d[2])
                if nb in cells and nb not in seen:
                    seen.add(nb)
                    q.append(nb)
        if len(comp) > len(best):
            best = comp
    return {p: cells[p] for p in best}


def _canvas_cells(canvas: Canvas) -> dict:
    """A `Canvas`'s own solid cells, in ITS OWN local coordinates, as {(x,y,z): (name, props)}."""
    names = []
    for e in canvas.palette:
        name = nbt.state_name(e).split(":")[-1]
        props = nbt.state_props(e)
        names.append((name, props))
    ys, zs, xs = np.nonzero(canvas.ids > 0)
    return {(x, y, z): names[int(canvas.ids[y, z, x])]
            for y, z, x in zip(ys.tolist(), zs.tolist(), xs.tolist())}


def _put_cells(w: World, cells: dict, record=None) -> int:
    """Write a {(world x, y, z): (name, props)} mapping into `w`, optionally recording which
    cells it claimed. `record` is what tells `_delight` a cell belongs to a SCULPTURE'S COAT and
    is therefore not somewhere a lamp may go - see `_delight`'s own docstring."""
    for (x, y, z), (name, props) in cells.items():
        w.put(x, y, z, name, **props)
        if record is not None:
            record.add((x, y, z))
    return len(cells)


def _paste(w: World, canvas: Canvas, origin=None, keep_largest=False, record=None) -> int:
    """Copy an already-built `Canvas`'s cells into `w` at a world position.

    This is how a sited creature reaches the causeway: `heron.py`, `bat.py`, `sloth.py` and
    `gecko.py` are all tested, finished generators in their own right, and pasting their output
    is a siting job, never a re-modelling one. `origin` overrides the canvas's own
    `world_origin`, for callers that place it by hand rather than through a generator's own
    `feet`/`hang` parameter. `keep_largest` runs `_largest_component` first - see its own
    docstring for why a sited creature needs it even at a scale that is otherwise safe.
    """
    ox, oy, oz = origin if origin is not None else getattr(canvas, "world_origin", (0, 0, 0))
    cells = _canvas_cells(canvas)
    if keep_largest:
        cells = _largest_component(cells)
    _put_cells(w, {(x + ox, y + oy, z + oz): v for (x, y, z), v in cells.items()}, record)
    # A SIGN IS TWO THINGS IN TWO HALVES OF THE FILE - `_canvas_cells` only reads the BLOCK
    # states, so a pasted design carrying its own signage (`wayfinding`'s archway does) would
    # ship the wall-sign block with no text at all unless the tile entity comes across too.
    # `canvas.tiles` stores it already JSON-encoded (`Canvas.sign_text`'s own format); `World.sign`
    # wants plain lines, so it is decoded back rather than passed through raw.
    import json as _json
    for (x, y, z), t in getattr(canvas, "tiles", {}).items():
        if (x, y, z) not in cells:
            continue          # the block did not survive `keep_largest` - no floating text either
        def _plain(msgs):
            out = []
            for m in msgs:
                try:
                    out.append(_json.loads(m).get("text", ""))
                except (TypeError, ValueError):
                    out.append(str(m))
            return out
        w.sign(x + ox, y + oy, z + oz, front=_plain(t["front"]), back=_plain(t["back"]),
               colour=t.get("colour", "black"), glowing=bool(t.get("glowing")))
    return len(cells)


def _flatten(cols, cx, cz, radius):
    """Level a small footprint to its own centre's height, BEFORE `_seat` ever runs.

    A pool's bed, a garden's border and a plinth's own top all want to be flat - built ground,
    not a shape that happens to average out level. Doing this before `_seat` means the terrace
    boundary around the flattened patch is handled by the exact same mechanism that already
    bridges any other height change in this design, rather than a second one invented for it.
    """
    center = cols.get((cx, cz))
    if not center:
        return False
    y = center["y"]
    for dx in range(-radius, radius + 1):
        for dz in range(-radius, radius + 1):
            if dx * dx + dz * dz > radius * radius:
                continue
            info = cols.get((cx + dx, cz + dz))
            if info:
                info["y"] = y
    return True


def _room_for(spine_half, half, margin=3):
    """(offset from the spine's own edge to a feature's centre, half-width of shape needed)."""
    offset = spine_half + half + margin
    return offset, offset + half + 2


# --------------------------------------------------------------------------------- the five stops

def _pool(w, cols, cx, cz, pal, radius) -> tuple[int, list]:
    """A bedded, kerbed still pool - `park._plaza_pool`'s own rule, restated on a cap that is
    already flat (`_flatten` ran on this footprint in pass 1b): a solid bed under every water
    cell (the cap itself, untouched) and a solid kerb on every open side. `fluids.unenclosed`
    checks the result in the test suite, because a design that only LOOKS like still water is
    this project's cardinal sin - the frontier's own flume shipped ten open-sided cells once."""
    info0 = cols.get((cx, cz))
    if not info0:
        return 0, []
    y = info0["y"]
    n, water = 0, []
    for dx in range(-radius - 1, radius + 2):
        for dz in range(-radius - 1, radius + 2):
            x, z = cx + dx, cz + dz
            if (x, z) not in cols:
                continue
            d = (dx * dx + dz * dz) ** 0.5
            if d > radius + 1:
                continue
            if d > radius:
                w.put(x, y + 1, z, pal["trim"])                 # the kerb, one block above the bed
            else:
                w.put(x, y + 1, z, "water")
                water.append((x, y + 1, z))
                n += 1
    if water:
        cx2, cz2 = water[len(water) // 2][0], water[len(water) // 2][2]
        w.put(cx2, y, cz2, LAMP)                                 # one light, IN the bed itself
    return n, water


def _garden(w, cols, cx, cz, seed, radius) -> int:
    """A deliberate, ALWAYS-PRESENT planting roundel - denser than the ambient drifts and
    bordered, so it reads as a made garden rather than a patch of the same moss the shoulders
    already carry. Still noised on its own RADIUS rather than filled solid, or a perfect disc of
    flowers reads as a stamp; `thicket`'s own rule, at a higher density than the ambient pass."""
    n = 0
    for dx in range(-radius - 1, radius + 2):
        for dz in range(-radius - 1, radius + 2):
            x, z = cx + dx, cz + dz
            info = cols.get((x, z))
            if not info:
                continue
            d = (dx * dx + dz * dz) ** 0.5
            if d > radius + 1:
                continue
            y = info["y"]
            if d > radius:
                w.put(x, y, z, park.LANDS["midway"]["trim"] if (dx + dz) % 5 == 0
                      else "moss_block")
                if (dx + dz) % 7 == 0:
                    w.put(x, y + 1, z, LAMP)
                continue
            w.put(x, y, z, "moss_block")
            if d > radius * (0.55 + 0.35 * hash01(x, z, seed, 61)):
                w.put(x, y + 1, z, "moss_carpet")
            else:
                r = hash01(x, z, seed, 62)
                if r < 0.35:
                    w.put(x, y + 1, z, "flowering_azalea" if hash01(x, z, seed, 63) < 0.4
                          else "azalea")
                elif r < 0.75:
                    w.put(x, y + 1, z, "fern")
                else:
                    w.put(x, y + 1, z, "short_grass")
            n += 1
    return n


def _plinth(w, cols, cx, cz, pal, half, height=2):
    """A raised, flat pedestal - `_flatten` already ran on this footprint, so every column here
    shares one height and the pedestal reads as BUILT rather than as a lump in the terrain."""
    info = cols.get((cx, cz))
    if not info:
        return None
    base = info["y"]
    for dx in range(-half, half + 1):
        for dz in range(-half, half + 1):
            if dx * dx + dz * dz > half * half:
                continue
            x, z = cx + dx, cz + dz
            if (x, z) not in cols:
                continue
            for h in range(1, height + 1):
                w.put(x, base + h, z, pal["trim"] if h == height else pal["post"])
            w.put(x, base + height + 1, z, LAMP) if (dx == 0 and dz == -half) else None
    return base + height


def _plaque(w, cx, cz, plinth_top, pal, facing, title, lines):
    """The name plaque, on the plinth's own north face - a block this function did not have to
    place first, because the plinth's rim is already solid there."""
    return _sign(w, cx, plinth_top, cz - 1, facing, pal["wood"],
                 [str(title)[:park.SIGN_WIDTH]] + list(lines)[:3])


# --- sited creatures: four tested, non-mammal generators, none of which needs a world capture,
# and THE STRUCTURE EACH ONE NEEDS TO EXIST AT ALL.
#
# A CREATURE IS SITED WITH THE THING IT STANDS ON, HANGS FROM OR CLINGS TO, and that is the whole
# of the work here. `heron.py` wants a pedestal and nothing else. `bat.py` and `sloth.py` are
# HANGING animals - a bat's own docstring places it under a cave roof and a sloth's says to paste
# it "with the top layer touching the underside" - and a causeway has no ceiling anywhere, so each
# is given a beam of the land's own masonry to grip. `gecko.py` clings to a vertical face and its
# own docstring says to "paste with the z=0 face flush against the cliff", so it is given one.
# Every one of those is masonry this file already lays - the same siting job `_plinth` always was
# - and not one line of any creature generator is touched.
#
# NO TWO OF THE FOUR SHARE A SILHOUETTE, which is the point and was the complaint: an upright
# column (the heron), a body slung under a bough (the sloth), a dome on a column of rigging (the
# balloon) and a free S under a flared plate (the wyrm). Two standing birds off one generator,
# and two ladybirds off another, was four sculptures showing two shapes.
#
# `_site_bat` AND `_site_gecko` ARE KEPT AND ARE NO LONGER SITED. Jack retired both from this
# causeway as used assets, and the two bespoke pieces replaced them - but a gantry and a stele
# are general answers to "this creature hangs" and "this creature clings", they are covered by
# their own tests, and deleting them would narrow what this file can site rather than fixing
# anything. Adding either one back to `GAPS` is a decision about REUSING AN ASSET, not a
# maintenance job, and that decision is Jack's: it was made once already, the other way.

BAND = "deepslate_bricks"     # THE ONE CHEAP BLOCK THAT CAN DRAW A LINE ON ANY OF THE THREE
                              # LANDS' OWN MASONRY. Measured, because `pal["trim"]` cannot: on the
                              # frontier, cobblestone against stone_bricks is FIVE points of
                              # luminance and the band is invisible. deepslate_bricks is 56 off
                              # cobblestone, 51 off stone_bricks and 26 off polished blackstone -
                              # the same block, and the same reasoning, as the void tower's.


_AXIS_TURN = {"x": "z", "z": "x", "y": "y"}
_VERTICAL_PROPS = ("waterlogged", "up", "down", "half", "type", "open", "powered", "lit",
                   "snowy", "persistent", "distance", "berries", "thickness", "age")


def _turn(cells: dict) -> dict:
    """A quarter turn about Y of a canvas-local cell map: (x, y, z) -> (-z, y, x).

    EVERY SITED CREATURE ON THIS CAUSEWAY NEEDS ONE, AND THE FIRST BUILD OF TWO OF THEM DID NOT
    HAVE IT. `_paste` only offsets, so a pasted generator keeps its own long axis on world X -
    and a creature stop is itself offset along world X, which is the axis a walker on the spine
    looks straight down. So a 39-block wingspan and a 28-block bough both came out EDGE-ON from
    the only place anybody stands: a post and a lump. It is invisible in a plan view and obvious
    the moment `tools/look.py` is pointed at the bearing the walkway actually gives you. The
    gecko had already been turned by hand, for exactly this, and the rule was not generalised.

    A turn is only SAFE on a block whose state does not name a horizontal direction. `axis` is
    turned; a purely vertical property is carried through; anything else - a facing, a live wall
    or fence connection, a hinge, a stair's shape - is REFUSED, because re-deriving those is a
    rotation library and this is a siting helper. A fence with every connection false, which is
    what `sloth.py` hangs its claws from, has no direction to turn and passes.
    """
    out = {}
    for (x, y, z), (name, props) in cells.items():
        turned = {}
        for k, v in props.items():
            if k == "axis":
                turned[k] = _AXIS_TURN.get(v, v)
            elif k in _VERTICAL_PROPS or (k in ("north", "south", "east", "west") and v == "false"):
                turned[k] = v
            else:
                raise ValueError(f"{name} carries {k}={v!r}, which names a horizontal direction - "
                                 f"a quarter turn cannot re-aim it, so this siting is not safe")
        out[(-z, y, x)] = (name, turned)
    return out


def _y_props(name):
    """A log or a stripped wood laid as an upright post needs its own axis said out loud;
    everything else this file stands in a column is plain masonry."""
    return {"axis": "y"} if name.endswith(("_log", "_wood", "_stem", "_hyphae")) else {}


def _ground_pier(w, cols, x, z, y_top, name, band_every=0, y_from=None) -> int:
    """Fill one column from ITS OWN ground up to `y_top`.

    The causeway terraces, so a pier's foot cannot be assumed level with the plinth's - `cols`
    is asked for the real cap height exactly as `_seat` does. A column that starts from a
    guessed Y is the floating-structure bug this design already has a whole test for.
    """
    info = cols.get((x, z))
    if not info:
        return 0
    props, band = _y_props(name), _y_props(BAND)
    n = 0
    for y in range(info["y"] + 1 if y_from is None else y_from, y_top + 1):
        if w.has(x, y, z):
            continue
        if band_every and (y - info["y"]) % band_every == 0:
            w.put(x, y, z, BAND, **band)
        else:
            w.put(x, y, z, name, **props)
        n += 1
    return n


def creature_canvas(spec: dict, place=None) -> Canvas:
    """The creature's OWN canvas, at exactly the scale and seed this design sites it at.

    ONE ENTRY POINT, so the one-piece check in `tests/test_isthmus.py` and the siting here
    cannot drift apart about what is actually being pasted - the same rule `proportions.measure`
    and `rubric.score` already share, and the reason it matters is that every one of these
    generators is fragile at some scale and the fragile scale is not the same for any two of
    them. `place` is whatever that generator calls its own anchor: a heron's `feet`, a bat's
    `hang`; the gecko and the sloth have neither and are placed by this file instead.
    """
    kind, seed = spec["kind"], spec.get("seed", 0)
    if kind == "heron":
        from . import heron as m
        return m.build_heron({"variant": spec.get("variant", "heron"),
                              "scale": float(spec.get("scale", 0.9)), "seed": seed,
                              "feet": list(place or [0, 0, 0])})
    if kind == "bat":
        from . import bat as m
        return m.build_bat({"scale": float(spec.get("scale", 0.7)), "seed": seed,
                            "hang": list(place or [0, 0, 0])})
    if kind == "gecko":
        from . import gecko as m
        return m.build({"seed": seed})
    if kind == "sloth":
        from . import sloth as m
        return m.build({"seed": seed})
    if kind == "balloon":
        from . import balloon as m
        return m.build_balloon({"seed": seed, "stand": list(place or [0, 0, 0])})
    if kind == "wyrm":
        from . import wyrm as m
        # THE HEAD FACES THE WALKWAY, and that is a function of which side of the spine the stop
        # was put on, not a constant. `side` +1 puts the stop east of the spine, so the walk is
        # to its WEST and the head has to rear that way - the gecko's stele is turned by exactly
        # the same argument. Written the other way round the wyrm faces the void.
        #
        # `form: serpent` IS NOT A DEFAULT AND MUST NOT BECOME ONE. `wyrm.py` now builds the
        # locked W1 threshold - a 60x17 ribcage you walk through, rooted into a bridge rim -
        # and that is not a thing that can stand on a causeway plinth beside a walkway: pasted
        # here it runs straight off the span and into the park's own cells. The causeway keeps
        # the retired ornament until its stop is re-programmed, which is Jack's call.
        return m.build_wyrm({"seed": seed, "form": "serpent",
                             "face": -int(spec.get("side", 1)),
                             "stand": list(place or [0, 0, 0])})
    raise ValueError(f"unknown creature kind {kind!r}; have {sorted(_SITERS)}")


def _site_heron(w, cols, top, cx, cz, spec, pal, side, record):
    """A heron planted foot-first on the plinth.

    ONLY THE FEET NEED TO STAND ON SOMETHING - the neck, the wings and the tail coverts are
    already one connected piece with the legs inside `heron.py`'s own geometry (verified at
    this scale by flood fill, not assumed), so they are free to reach out over open air past
    the plinth's own edge exactly as a real heron's silhouette does. What the plinth has to get
    right is the two leg columns, not the whole bird's footprint.
    """
    return _paste(w, creature_canvas(spec, [cx, top + 1, cz]), keep_largest=True, record=record)


def _site_gecko(w, cols, top, cx, cz, spec, pal, side, record):
    """A gecko splayed on a STELE - a slab of the land's own masonry standing on the plinth,
    with the lizard on the face that looks back at the walkway.

    `gecko.py`'s canvas is x ALONG the wall, y up, z OUT from it, so the siting is one quarter
    turn: the lizard's length becomes the walk's own axis and its depth becomes the walk's
    width, which is what puts a 28-block animal on a causeway seven columns wide. The turn is
    written out here as three coordinate lines rather than run through `_paste`, because a
    general rotation would have to re-aim every `facing` and `axis` it met - and it is only
    SAFE at all because the gecko is six plain wools and a moss block with no directional
    property anywhere. That is checked, not remembered: the moment it stops being true this
    refuses to build rather than shipping a lizard facing into its own wall.

    THE STELE IS ALSO WHY THIS STOP HAS NO GLOW PROBLEM. A sculpture on a vertical face has
    almost no upward-facing surface for a mob to stand on, so there is next to nothing for the
    night pass to want to light - `_delight`'s own worst case, avoided by the geometry rather
    than argued with afterwards.
    """
    cells = _largest_component(_canvas_cells(creature_canvas(spec)))
    for name, props in cells.values():
        if props:
            raise ValueError(f"gecko.py now emits {name} with {sorted(props)} - a turned paste "
                             f"cannot re-aim that, so this siting is no longer safe")
    gx = [k[0] for k in cells]
    gy = [k[1] for k in cells]
    x0, x1, y0, y1 = min(gx), max(gx), min(gy), max(gy)
    hw = (x1 - x0) // 2 + 2                       # the stele's half-width, along the walk
    height = (y1 - y0) + 4                        # ...and its height above the plinth's own top
    n = 0
    crown = top + height
    for dz in range(-hw, hw + 1):
        for k in range(2):                        # two courses thick: a slab, not a wall
            n += _ground_pier(w, cols, cx + side * k, cz + dz, crown, pal["ground"], band_every=8)
    # THE CROWN IS A THIRTY-BLOCK FLAT ROOF AND IT LIGHTS ITSELF. Flush froglights in the top
    # course, this island's own idiom - a lamp standing ON a stele's cap is a lamp somebody
    # knocks off, and a cap left dark is the mob highway the whole night pass exists to stop.
    for dz in range(-hw, hw + 1, 4):
        w.put(cx, crown, cz + dz, LAMP)
    face = cx - side                              # the column the lizard's own z=0 lands in
    mid = (x0 + x1) // 2
    n += _put_cells(w, {(face - side * z, top + 2 + (y - y0), cz + (x - mid)): v
                        for (x, y, z), v in cells.items()}, record)
    return n


def _site_bat(w, cols, top, cx, cz, spec, pal, side, record):
    """A bat hanging under a GANTRY - two piers and a lintel, spanned wide enough that the
    membrane clears both posts.

    THE PIERS STAND OUTSIDE THE WINGSPAN, and that is measured off the bat itself rather than
    guessed: a pier inside the span would be overwritten cell for cell by the wing pasted over
    it and could be cut in half without anything noticing, because the design would still audit
    as one piece through the lintel. THE WHOLE GANTRY RUNS ALONG THE WALK, not across it - see
    `_turn`: a wingspan laid on world X points its own edge at everyone who ever looks at it.
    """
    c = creature_canvas(spec, [0, 0, 0])
    ox, oy, oz = c.world_origin
    rel = _turn({(x + ox, y + oy, z + oz): v
                 for (x, y, z), v in _largest_component(_canvas_cells(c)).items()})
    span = max(abs(k[2]) for k in rel)                       # half the wingspan, along the walk
    drop = -min(k[1] for k in rel)                           # how far it hangs below its grip
    beam = cols[(cx, cz)]["y"] + drop + int(spec.get("clear", 4))
    pz = span + 2
    n = 0
    for s in (-1, 1):
        for dx in (0, 1):
            n += _ground_pier(w, cols, cx + dx, cz + s * pz, beam, pal["post"], band_every=6)
    # THE LINTEL IS A FLAT ROOF THIRTY-SEVEN BLOCKS LONG AND IT HAS TO LIGHT ITSELF, so the
    # froglights ARE part of the beam's own far course rather than something laid on it after -
    # written the other way round the band went in first, `w.has` was then true at every one of
    # those cells and not a single lamp was placed, silently, leaving seventy dark spawnable
    # cells fifteen blocks over the walkway. `transit._lamps`'s own rule, in a new body.
    for z in range(cz - pz, cz + pz + 1):
        for dx in (0, 1):
            if w.has(cx + dx, beam, z):
                continue
            lit = dx == 1 and (z - cz) % 5 == 0
            w.put(cx + dx, beam, z, LAMP if lit else BAND, **({} if lit else _y_props(BAND)))
            n += 1
    return n + _put_cells(w, {(cx + kx, beam + ky, cz + kz): v
                              for (kx, ky, kz), v in rel.items()}, record)


def _site_sloth(w, cols, top, cx, cz, spec, pal, side, record):
    """A sloth slung under a BOUGH, on two posts.

    `sloth.py` brings its own branch - two courses of spruce log the whole length of the piece,
    with the animal's four limbs hooked over it - so all this has to add is something to hold
    that branch up at each end. The posts are found from the BRANCH'S OWN LOG CELLS rather than
    from the canvas's corner: the body, the head and the limbs all hang past the branch's ends
    in places, so a post placed off the bounding box would stand in the middle of the animal.
    Turned a quarter (`_turn`) so the bough runs ALONG the walk, which is the only bearing from
    which a hanging animal is anything but a lump - and which turns its own `spruce_log` axis
    with it, because a log laid the wrong way is a bough with its grain running across it.
    """
    cells = _turn(_largest_component(_canvas_cells(creature_canvas(spec))))
    ks = list(cells)
    x0, x1 = min(k[0] for k in ks), max(k[0] for k in ks)
    z0, z1 = min(k[2] for k in ks), max(k[2] for k in ks)
    logs = [k for k, (nm, _p) in cells.items() if nm.endswith("_log")]
    lz0, lz1 = min(k[2] for k in logs), max(k[2] for k in logs)
    lx = sorted({k[0] for k in logs})
    bough = min(k[1] for k in logs)                          # the branch's own lowest course
    ground = cols[(cx, cz)]["y"]
    ox = cx - (x0 + x1) // 2
    oz = cz - (z0 + z1) // 2
    oy = ground + int(spec.get("clear", 4)) - min(k[1] for k in ks)
    n = 0
    for z in (lz0, lz0 + 1, lz1 - 1, lz1):
        for x in lx:
            n += _ground_pier(w, cols, x + ox, z + oz, oy + bough - 1, pal["post"], band_every=6)
    return n + _put_cells(w, {(x + ox, y + oy, z + oz): v for (x, y, z), v in cells.items()},
                          record)


def _site_standing(w, cols, top, cx, cz, spec, pal, side, record):
    """A sculpture that CARRIES ITS OWN GROUND, planted on the plinth and nothing else.

    THE TWO NEW PIECES ON THIS CAUSEWAY NEED NO STRUCTURE FROM THIS FILE, and that is a
    deliberate difference from the four that came before it. A heron wants a pedestal, a gecko
    a stele, a bat a gantry and a sloth a bough - every one of those is masonry `isthmus` has
    to lay on terraced ground before the creature can exist at all, and every one of them is a
    place a pier can miss its footing (a gantry shipped with one leg, and only a render caught
    it). `balloon.py` brings its own basket and `wyrm.py` its own milestone, so the siting is
    one paste at the plinth's own top course and there is nothing left to get wrong.

    `keep_largest` stays on regardless. It is not expected to drop anything - both generators
    are asserted one-piece at their own default scale, which is the scale sited here - but a
    sited creature has no business handing this design a floating cell it did not build, and
    anything it does drop is reported by the caller rather than silently discarded.
    """
    return _paste(w, creature_canvas(spec, [cx, top + 1, cz]), keep_largest=True, record=record)


_SITERS = {"heron": _site_heron, "gecko": _site_gecko,
           "bat": _site_bat, "sloth": _site_sloth,
           "balloon": _site_standing, "wyrm": _site_standing}


# --- real furniture and real signage, sited rather than hand-rolled: `streetfurniture.py` and
# `wayfinding.py` are both tested generators of their own, and pasting their output is the same
# siting job as a heron or a gecko - not a licence to re-invent a bench or a nameplate here.

def _paste_bbox(canvas: Canvas, keep_largest=False):
    """The world-coordinate (x, z) footprint of a canvas about to be pasted, WITHOUT pasting it -
    the caller records this so a design like an archway lintel, which legitimately bridges open
    air between its two posts, can be told apart from an actual floating defect by anything
    checking column-by-column contiguity (see `test_nothing_floats_between_two_terraces`)."""
    cells = _canvas_cells(canvas)
    if keep_largest:
        cells = _largest_component(cells)
    if not cells:
        return None
    ox, _oy, oz = canvas.world_origin
    xs_ = [k[0] + ox for k in cells]
    zs_ = [k[2] + oz for k in cells]
    return [[min(xs_), min(zs_)], [max(xs_), max(zs_)]]


def _site_bench(w, cols, cx, cz, land, side):
    """A real seat - `streetfurniture.bench`'s own back, arm rests and pad - replacing what used
    to be two lone stair blocks at the overlook. `side` decides which way it opens: AWAY from
    the spine, so a sitter looks out over the drop rather than back at the walkway they just
    crossed. The offset from (cx, cz) to the piece's own front-left corner is fixed rather than
    measured from the randomised length `streetfurniture` picks internally - exact centring is
    not the point, staying inside the room this stop already reserved is.

    Returns (cells placed, world (x, z) bounding box) - the bbox is for bookkeeping only, so a
    test can exclude this stop's own footprint from a check written for plain terraced ground.
    """
    from . import streetfurniture as sf_mod
    info = cols.get((cx, cz))
    if not info:
        return 0, None
    y = info["y"]
    facing = "east" if side < 0 else "west"
    at = [cx - 2 * side, y + 1, cz - 4 * side]
    c = sf_mod.build({"kind": "bench", "at": at, "facing": facing, "land": land,
                      "shape": "straight",
                      "seed": (abs(int(cx)) * 7919 + abs(int(cz)) * 104729) % 1_000_003})
    bbox = _paste_bbox(c, keep_largest=True)
    return _paste(w, c, keep_largest=True), bbox


def _site_archway(w, at, facing, land, entering):
    """A real threshold - `wayfinding.archway`'s own job - naming the land you are about to walk
    into, at the exact spot the walk actually crosses into it. Its posts stand at the two edges
    of the widened gateway spine (`arch_width=9` matches `spine_half_wide`'s own measured nine
    columns) and every interior column is left open, so the arch marks the walkway without ever
    standing in it - which is exactly why its own lintel bridges open air over those columns; see
    `_paste_bbox`'s own docstring for why that footprint is recorded rather than only its count.
    """
    from . import wayfinding as wf_mod
    c = wf_mod.build({"kind": "archway", "at": list(at), "facing": facing, "land": land,
                      "arch_width": 9, "arch_height": 5, "entering": entering})
    bbox = _paste_bbox(c, keep_largest=True)
    return _paste(w, c, keep_largest=True), bbox

# The plinth only has to be wide enough for a creature's own feet, or for the foot of whatever
# it hangs from or clings to - see `_site_heron`'s own note. The bulge asks for a good deal more
# than that, because a gantry's piers and a stele's own footing stand well outside it and each
# one seats on its own real ground (`_ground_pier`), which only exists where the shape does.
#
#   _PLINTH_HALF     the pedestal, and the block the name plaque hangs on
#   _CREATURE_ROOM   half-width of shoulder the stop opens for itself, in BOTH axes
#   _FLATTEN         radius levelled before the terrace is cut, so a stele's or a gantry's feet
#                    all start from one course. The gecko's is the big one: its stele is 33
#                    blocks long ALONG the walk, so the level patch has to be too.
# A HANGING CREATURE WANTS A MARKER STONE, NOT A PEDESTAL. Given the heron's own
# five-block plinth the bat and the sloth each stood over a two-course disc of the
# land's own trim with nothing on it - an empty plinth reads as a statue somebody has
# taken away. Three is enough to carry the name plaque and no more.
_PLINTH_HALF = {"heron": 5, "gecko": 5, "bat": 3, "sloth": 3, "balloon": 4, "wyrm": 5}
_CREATURE_ROOM = {"heron": 13, "gecko": 15, "bat": 18, "sloth": 16,
                  "balloon": 11, "wyrm": 13}
_FLATTEN = {"heron": 8, "gecko": 18, "bat": 21, "sloth": 16, "balloon": 11, "wyrm": 11}
# HOW FAR A STOP'S OWN STRUCTURE REACHES ALONG THE WALK, either side of its own centre.
#
# THIS EXISTS BECAUSE A GANTRY SHIPPED WITH ONE LEG. A span is 101 rows and a stele is 33 of
# them; a creature sited at t=0.86 puts its far end two rows PAST the plot the causeway stops
# against, `cols` has no column out there at all, and `_ground_pier` therefore built exactly
# nothing - no error, no missing-cell report, and the design still audits as one piece because
# the lintel carries it. It was visible only in a render, from the one bearing the walkway
# gives you. The centre is CLAMPED into the span now and the clamp is recorded, so a gap too
# short for a stop still builds and says so rather than quietly losing half a structure.
#
# THE TWO SELF-CARRYING PIECES ARE THE SMALL NUMBERS HERE, and that is the point of them: a
# stop's reach is set by the STRUCTURE this file has to build for a creature, not by the
# creature. A stele is 33 rows of a 101-row span; a balloon's basket is five.
_CREATURE_ZHALF = {"heron": 7, "gecko": 18, "bat": 22, "sloth": 16, "balloon": 9, "wyrm": 7}


# ------------------------------------------------------------------------------------ one gap

def _build_gap(w: World, p: dict, gap: dict, meta: dict) -> None:
    protect = meta.setdefault("protect", set())     # every cell a sited creature's COAT owns
    z_lo, z_hi = int(gap["z_lo"]), int(gap["z_hi"])
    if z_hi - z_lo < 8:
        raise ValueError("a gap needs at least 8 rows - it is not worth a shape below that")
    land_a, land_b = gap["land_a"], gap["land_b"]
    for land in (land_a, land_b):
        if land not in park.LANDS:
            raise ValueError(f"unknown land {land!r}; have {sorted(park.LANDS)}")
    xs = int(p["x_spine"])
    # NEVER Python's own `hash()` on a string here - it is salted per PROCESS
    # (PYTHONHASHSEED), so two runs of the identical config would build two different shapes.
    # `sum(map(ord, ...))` is what the rest of this codebase uses for exactly this reason.
    seed = int(p["seed"]) + sum(map(ord, str(gap.get("title") or ""))) % 97
    span = z_hi - z_lo
    mid_z = z_lo + span // 2
    ov_span = max(1, int(p["overlook_span"]))
    spine_half = max(1, int(p["spine_half"]))

    # ---- the five stops, sited before the shape itself so pass 1 can open room for them.
    stops = []       # (cx, cz, z_span, extra_half, kind, spec)
    pool_cz = z_lo + int(round(float(p["pool_t"]) * span))
    poff, pextra = _room_for(spine_half, int(p["pool_radius"]) + 1)
    pool_cx = xs + int(p["pool_side"]) * poff
    stops.append((pool_cx, pool_cz, 8, pextra, "pool", None))

    garden_cz = z_lo + int(round(float(p["garden_t"]) * span))
    goff, gextra = _room_for(spine_half, int(p["garden_radius"]))
    garden_cx = xs + int(p["garden_side"]) * goff
    stops.append((garden_cx, garden_cz, 10, gextra, "garden", None))

    creature_stops = []          # (cx, cz, PLINTH half, spec) - see `_site_heron`'s own note:
                                  # the plinth only has to carry the feet or the clod, so this
                                  # is deliberately much smaller than the room the bulge opens.
    for spec in (gap.get("creatures") or []):
        kind = spec["kind"]
        room = int(_CREATURE_ROOM[kind])
        coff, cextra = _room_for(spine_half, room)
        want = z_lo + int(round(float(spec["t"]) * span))
        zh = min(int(_CREATURE_ZHALF[kind]), span // 2)
        ccz = max(z_lo + zh, min(z_hi - zh, want))
        if ccz != want:
            meta.setdefault("stops_clamped", []).append(
                {"kind": kind, "wanted_z": want, "at_z": ccz, "reach": zh})
        ccx = xs + int(spec.get("side", 1)) * coff
        stops.append((ccx, ccz, room + 4, cextra, "creature", spec))
        creature_stops.append((ccx, ccz, int(_PLINTH_HALF[kind]), spec))

    # a real streetfurniture bench either side of the overlook's own centre, at the void's own
    # midpoint rather than tuned to whatever `t` the pool/garden/creatures already occupy -
    # nothing else in this gap sits at t=0.5 on either side.
    bench_half = 8
    boff, bextra = _room_for(spine_half, bench_half)
    bench_stops = []             # (cx, cz, side)
    for side in (-1, 1):
        bcx = xs + side * boff
        stops.append((bcx, mid_z, 10, bextra, "bench", {"side": side}))
        bench_stops.append((bcx, mid_z, side))

    # ------------------------------------------------------------ pass 1: the footprint + height
    cols = {}
    row_half, row_spine_half = {}, {}
    for z in range(z_lo, z_hi + 1):
        t = (z - z_lo) / float(span)
        bulge = abs(z - mid_z) <= ov_span
        extra = 0.0
        for (_cx, cz, zspan, ehalf, _kind, _spec) in stops:
            if abs(z - cz) <= zspan:
                extra = max(extra, ehalf)
        half = _half_at(p, t, bulge, extra)
        noise_on = not (bulge or extra)
        noise = 1.0 + p["edge_noise"] * (hash01(z, seed, 7) - 0.5) * (2.0 if noise_on else 0.0)
        half = max(spine_half + 2, half * noise)
        half = min(half, xs - p["x_min"])
        if p.get("reserve_x") is not None:
            half = min(half, int(p["reserve_x"]) - 1 - xs)
        half = int(round(half))
        row_half[z] = half
        sph = min(half, _spine_half_at(p, t))
        row_spine_half[z] = sph
        rise = int(round(p["rise_max"] * math.sin(math.pi * t)))
        fade = _edge_fade(t)
        for x in range(xs - half, xs + half + 1):
            dx = abs(x - xs)
            if dx <= sph:
                y = BASE_Y + rise
                band = "spine"
            else:
                extent = max(1.0, half - spine_half)
                frac = min(1.0, (dx - spine_half) / extent)
                drop = int(round(frac * p["terrace_drop_max"] * fade))
                y = BASE_Y + rise - drop
                band = "spine" if bulge and dx <= p["overlook_half"] else "shoulder"
            cols[(x, z)] = {"y": y, "band": band, "t": t, "bulge": bulge}

    # ------------------------------------------------------------ pass 1b: flatten each stop's
    # own footprint - BEFORE seating, so the terrace bridges into it like anything else.
    for (cx, cz, _zspan, _ehalf, kind, spec) in stops:
        if kind == "pool":
            _flatten(cols, cx, cz, int(p["pool_radius"]) + 2)
        elif kind == "garden":
            _flatten(cols, cx, cz, int(p["garden_radius"]) + 1)
        elif kind == "creature":
            # THE WHOLE STOP, not just the plinth: a stele is 33 blocks long along the walk and
            # a gantry's piers stand well outside the wingspan, and each of those columns seats
            # on its own real ground. Level it all first or the structure carrying a sculpture
            # is the one thing on this causeway that steps.
            _flatten(cols, cx, cz, int(_FLATTEN[spec["kind"]]))
        elif kind == "bench":
            _flatten(cols, cx, cz, 8)          # a level pad for a real piece, not a tuned lump

    # ------------------------------------------------------------ pass 2: seat every column on
    # its lowest orthogonal neighbour, and mark the true outline (`_seat` is the fix for a
    # floating gap between two differently-terraced columns - see the module docstring).
    def _seat(x, z):
        info = cols[(x, z)]
        y = info["y"]
        floor = y
        is_rim = False
        for ddx, ddz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, nz = x + ddx, z + ddz
            if ddz and not (z_lo <= nz <= z_hi):
                continue          # the island-ward end: treated as already-built, never a rim
            nb = cols.get((nx, nz))
            if nb is None:
                is_rim = True
                continue
            floor = min(floor, nb["y"])
        info["fill_bottom"] = floor - 1 - (int(p["rim_shell"]) if is_rim else 0)
        info["rim"] = is_rim

    for (x, z) in cols:
        _seat(x, z)

    # ------------------------------------------------------------ pass 3: place the mass
    rim_n = spine_n = shoulder_n = 0
    for (x, z), info in cols.items():
        land = _land_at(land_a, land_b, info["t"], seed)
        pal = park.LANDS[land]
        y, bottom = info["y"], info["fill_bottom"]
        if info["band"] == "spine":
            spine_n += 1
            if info.get("bulge"):
                cap = pal["trim"] if (x + z) % 6 == 0 else (pal["ground"] if (x + z) % 2 == 0 else pal["path"])
            elif abs(x - xs) >= spine_half:
                cap = pal["trim"]                                    # the kerb line
            else:
                cap = pal["ground"] if (x + z) % 2 == 0 else pal["path"]
        else:
            shoulder_n += 1
            cap = "moss_block"
        w.put(x, y, z, cap)
        for yy in range(y - 1, bottom - 1, -1):
            core = "cobblestone" if hash01(x, yy, z, seed, 9) < 0.4 else "stone"
            w.put(x, yy, z, core)
        if info["rim"]:
            rim_n += 1
            w.put(x, y + 1, z, pal["fence"])

    # ------------------------------------------------------------ pass 3b: name the span at BOTH
    # ends - a real `wayfinding.archway` at each flush join, reused rather than another hand-
    # rolled sign. Only where the span is long enough that the two thresholds cannot reach into
    # each other (each needs a few rows clear of its own end); every shipped gap clears this by
    # a wide margin, and a gap too short for one is still a legal, if unmarked, causeway.
    archways_built = []
    if span >= 20:
        a_lo, bbox_lo = _site_archway(w, [xs + 4, BASE_Y + 1, z_lo + 2], "south", land_a, land_a)
        a_hi, bbox_hi = _site_archway(w, [xs - 4, BASE_Y + 1, z_hi - 2], "north", land_b, land_b)
        archways_built = [{"end": "z_lo", "entering": land_a, "cells": a_lo, "bbox": bbox_lo},
                          {"end": "z_hi", "entering": land_b, "cells": a_hi, "bbox": bbox_hi}]

    # ------------------------------------------------------------ pass 4: drifts on the shoulder,
    # excluding every stop's own footprint - a stop plants ITS OWN ground, deliberately, rather
    # than competing with a chance-picked ambient drift for the same cells.
    # TWO DIFFERENT RADII, BECAUSE THEY ANSWER TWO DIFFERENT QUESTIONS. A drift must keep out of
    # the whole levelled stop - ferns sprouting through a stele's footing is the ambient pass
    # competing with a made thing for its own ground. The LAMP grid must not, and using the one
    # radius for both was a real regression the moment a creature's stop grew from a nine-block
    # plinth to a twenty-block structure: 534 columns of moss went unlit at a stroke, because
    # "a stop lights itself" is only true of the stop's own FOOTPRINT, never of the twenty
    # blocks of open shoulder around it.
    exclude, light_exclude = set(), set()
    for (cx, cz, _zspan, _ehalf, kind, spec) in stops:
        if kind == "pool":
            r = lr = int(p["pool_radius"]) + 2
        elif kind == "garden":
            r = lr = int(p["garden_radius"]) + 2
        elif kind == "bench":
            r = lr = 9
        else:
            r = int(_FLATTEN[spec["kind"]]) + 2
            lr = int(_PLINTH_HALF[spec["kind"]]) + 3
        for dx in range(-r, r + 1):
            for dz in range(-r, r + 1):
                if dx * dx + dz * dz <= r * r:
                    exclude.add((cx + dx, cz + dz))
                    if dx * dx + dz * dz <= lr * lr:
                        light_exclude.add((cx + dx, cz + dz))

    shoulder_cells = [(x, z, info["y"]) for (x, z), info in cols.items()
                       if info["band"] != "spine" and not info["rim"] and (x, z) not in exclude]
    n_drifts = max(1, int(round(p["drifts_per_span"] * span / 100.0)))
    order = sorted(shoulder_cells, key=lambda c: hash01(c[0], c[1], seed, 51))
    picked, drifted = [], 0
    for (cx, cz, cy) in order:
        if any(abs(cx - a) < p["drift_min_gap"] and abs(cz - b) < p["drift_min_gap"]
               for a, b in picked):
            continue
        picked.append((cx, cz))
        if len(picked) >= n_drifts:
            break
    for (cx, cz) in picked:
        rad = p["drift_radius"] * (0.7 + 0.6 * hash01(cx, cz, seed, 12))
        for dxx in range(-4, 5):
            for dzz in range(-4, 5):
                x, z = cx + dxx, cz + dzz
                info = cols.get((x, z))
                if not info or info["band"] == "spine" or info["rim"] or (x, z) in exclude:
                    continue
                d = (dxx * dxx + dzz * dzz) ** 0.5
                if d > rad:
                    continue
                # THE NOISE IS ON THE RADIUS, NEVER THE INTERIOR - `thicket`'s own rule.
                if d > rad * (0.7 + 0.5 * hash01(x, z, seed, 13)):
                    w.put(x, info["y"] + 1, z, "moss_carpet")
                else:
                    r = hash01(x, z, seed, 14)
                    if r < 0.28:
                        w.put(x, info["y"] + 1, z,
                              "flowering_azalea" if hash01(x, z, seed, 15) < 0.25 else "azalea")
                    elif r < 0.6:
                        w.put(x, info["y"] + 1, z, "fern")
                    elif r < 0.85:
                        w.put(x, info["y"] + 1, z, "short_grass")
                drifted += 1

    # ------------------------------------------------------------ pass 5: the overlook - the
    # platform PAST THE RIM, at the void's own midpoint. "the drop is the view."
    land_mid = _land_at(land_a, land_b, 0.5, seed)
    pal_mid = park.LANDS[land_mid]
    bench_n = 0
    for side, bz in ((-1, mid_z - 3), (1, mid_z + 3), (-1, mid_z + 3), (1, mid_z - 3)):
        bx = xs - side * (spine_half + 2)
        info = cols.get((bx, bz))
        if not info or w.has(bx, info["y"] + 1, bz):
            continue
        w.put(bx, info["y"] + 1, bz, pal_mid["stair"], facing="east" if side < 0 else "west",
              half="bottom", shape="straight", waterlogged="false")
        bench_n += 1
    post_x, post_z = xs, mid_z
    info = cols.get((post_x, post_z))
    named = False
    if info:
        py = info["y"] + 1
        for h in range(2):
            w.put(post_x, py + h, post_z, pal_mid["post"])
        w.put(post_x, py + 2, post_z, LAMP)
        title = str(gap.get("title") or "THE REACH")
        named = _sign(w, post_x, py + 1, post_z - 1, "north", pal_mid["wood"],
                      [title[:park.SIGN_WIDTH], "", land_a.upper(), land_b.upper()])
    # a lamp on the rim rail itself, so the overlook's own guard is never the dark part of it
    for x in (xs - p["overlook_half"], xs + p["overlook_half"]):
        info = cols.get((x, mid_z))
        if info and info["rim"] and not w.has(x, info["y"] + 1, mid_z):
            w.put(x, info["y"] + 1, mid_z, LAMP)

    # ------------------------------------------------------------ pass 5b: the still pool
    pool_n, pool_water = _pool(w, cols, pool_cx, pool_cz, park.LANDS[land_mid],
                               int(p["pool_radius"]))

    # ------------------------------------------------------------ pass 5c: the garden roundel
    garden_n = _garden(w, cols, garden_cx, garden_cz, seed, int(p["garden_radius"]))

    # ------------------------------------------------------------ pass 5d: the sited creatures
    creatures_built = []
    for (ccx, ccz, half, spec) in creature_stops:
        land_c = _land_at(land_a, land_b, cols[(ccx, ccz)]["t"] if (ccx, ccz) in cols else 0.5,
                          seed)
        pal_c = park.LANDS[land_c]
        top = _plinth(w, cols, ccx, ccz, pal_c, half=half)
        if top is None:
            continue
        # THE COAT IS RECORDED CELL BY CELL, and that record is the whole glow fix: `_delight`
        # is told which cells belong to a sculpture so that it can light them from beside
        # rather than turn them into lamps. Only what the CREATURE generator placed goes in -
        # a stele's crown or a gantry's lintel is masonry this file laid and is a perfectly
        # good place for a flush froglight.
        coat = set()
        placed = _SITERS[spec["kind"]](w, cols, top, ccx, ccz, spec, pal_c,
                                       int(spec.get("side", 1)), coat)
        protect |= coat
        plaqued = _plaque(w, ccx, ccz, top, pal_c, "north",
                          spec.get("title") or spec["kind"].upper(), spec.get("lines") or [])
        creatures_built.append({"kind": spec["kind"], "at": [ccx, top, ccz],
                                "cells": placed, "coat": len(coat), "named": plaqued})

    # ------------------------------------------------------------ pass 5e: the overlook's own
    # benches - real `streetfurniture.bench`, one either side, reused rather than the two lone
    # stair blocks this used to be.
    benches_built = []
    for (bcx, bcz, side) in bench_stops:
        info = cols.get((bcx, bcz))
        if not info:
            continue
        land_here = _land_at(land_a, land_b, info["t"], seed)
        n, bbox = _site_bench(w, cols, bcx, bcz, land_here, side)
        if n:
            benches_built.append({"at": [bcx, info["y"], bcz], "side": side, "cells": n,
                                  "bbox": bbox})

    # ------------------------------------------------------------ pass 6: the light, last - a
    # brick grid over the WHOLE shape, not just the spine, offset row to row so no seam lines
    # up twice. Slides to the nearest column whose own cell above is clear - `transit._lamps`'s
    # own rule, because a lamp under a fence or a bench is not a lamp. RIM COLUMNS AND EVERY
    # STOP'S OWN FOOTPRINT ARE SKIPPED: a rim's fence already blocks the headroom
    # `nightlight.surface` needs before it calls a cell spawnable, and a stop lights itself.
    every = max(3, int(p["light_every"]))
    lamps, missed = [], 0
    placed_at = set()
    for row_i, z0 in enumerate(range(z_lo, z_hi + 1, every)):
        half = row_half.get(z0, spine_half)
        offset = (every // 2) if row_i % 2 else 0
        for dx in range(-half + offset, half + 1, every):
            tx = xs + dx
            found = False
            for r in range(0, every + 1):
                ring = [(0, 0)] if r == 0 else [(r, 0), (-r, 0), (0, r), (0, -r)]
                for (ddx, ddz) in ring:
                    x, z = tx + ddx, z0 + ddz
                    if not z_lo <= z <= z_hi or (x, z) in placed_at or (x, z) in light_exclude:
                        continue
                    info = cols.get((x, z))
                    if not info or info["rim"] or w.has(x, info["y"] + 1, z):
                        continue
                    w.put(x, info["y"], z, LAMP)
                    lamps.append([x, info["y"], z])
                    placed_at.add((x, z))
                    found = True
                    break
                if found:
                    break
            if not found:
                missed += 1

    meta.setdefault("gaps_built", []).append({
        "title": gap.get("title"), "z_lo": z_lo, "z_hi": z_hi,
        "land_a": land_a, "land_b": land_b,
        "spine": spine_n, "shoulder": shoulder_n, "rim": rim_n, "drifted": drifted,
        "bench": bench_n, "named": named, "lamps": lamps, "lamps_unplaceable": missed,
        "pool": pool_n, "pool_water": pool_water, "garden": garden_n,
        "creatures": creatures_built,
        "benches": benches_built, "archways": archways_built,
        "columns": list(cols.keys()),
    })


def _full_states(model):
    out = []
    for e in model.palette:
        name = nbt.state_name(e).split(":")[-1]
        props = nbt.state_props(e)
        tail = ",".join(f"{k}={v}" for k, v in sorted(props.items()))
        out.append(f"{name}[{tail}]" if props else name)
    return out


LICHEN = "glow_lichen"
LICHEN_SPACING = 5       # its light is 7, so one reaches six cells of air: this is well inside


def _delight(w: World, rounds=6, protect=frozenset()) -> dict:
    """Patch every spawnable cell still dark - and NEVER by turning a sculpture into a lamp.

    A SITED CREATURE ARRIVES WITH A SURFACE THIS DESIGN DID NOT MEASURE IN ADVANCE. Every other
    light in this file is placed by a rule written for the SHAPE it is lighting - the flush grid
    for the terrain, one lamp in a pool's own bed, a lamp on each rim rail of the overlook - and
    a bat's membrane or a gecko's back is neither of those; it is whatever the creature
    generator happened to build. So it has to be swept for afterwards, and that much was right.

    WHAT WAS WRONG IS WHERE THE LIGHT WENT. This pass used to replace the dark block itself with
    `ochre_froglight`, and on a design carrying four large sculptures it did that 1,138 times -
    every single one of them inside a creature's coat, 299 cells of black wool, 295 of red, 147
    of the ladybird's own leaf. Three per cent of the whole causeway was a lamp and the verdict
    was the obvious one: the sculptures were "all glowing". `frog.py`'s "in the skin, not on it"
    was cited for it, and that rule is about a HANDFUL of lamps a designer chose and placed; it
    is not a licence to perforate a coat wholesale. The rule that actually governs here is
    `Island Night`'s, and this file simply had no cost model to state it with:

        a fixture ON a sculpture damages it - ordinary ground is cheap, a coat is dear

    So a dark cell over ordinary ground still gets the flush froglight. A dark cell over a COAT
    gets `glow_lichen` in the AIR above it instead - `Lowland Glow`'s own answer, arrived at for
    exactly this and on exactly this kind of surface (it is what lit the axolotl's back). It
    emits 7, it is passable, it is cheap and 1.19, and above all it ADDS to the sculpture rather
    than eating it: not one cell of any creature is replaced. Because 7 carries six blocks
    through air, they are thinned to `LICHEN_SPACING` and the model is re-propagated - so a
    handful of them settles a whole flank, where a lamp per dark cell settled nothing but the
    count.

    Lighting a cell can only ever help its neighbours and never re-darken them, so the rounds
    converge; `Island Night` and `Lowland Glow` both solve their own islands this way.
    """
    from .. import nightlight
    faces = {"down": "true", "up": "false", "north": "false", "south": "false",
             "east": "false", "west": "false", "waterlogged": "false"}
    out = {"ground": 0, "lichen": 0, "in_coat": 0, "left_dark": 0}
    for _ in range(rounds):
        if not w.cells:
            break
        c = w.canvas()
        m = c.to_model()
        sts = _full_states(m)
        opaque, emit, passy, spawn, _water = nightlight.classify(sts)
        ids = m.ids
        light = nightlight.propagate(opaque[ids], emit[ids])
        clear = passy[ids] | (ids == 0)
        standable = spawn[ids]
        ny = ids.shape[0]
        ox, oy, oz = c.world_origin
        dark = []
        for y in range(ny - 1):
            zz, xx = np.nonzero(standable[y])
            for z, x in zip(zz.tolist(), xx.tolist()):
                head = clear[y + 2, z, x] if y + 2 < ny else True
                if clear[y + 1, z, x] and head and light[y + 1, z, x] < 1:
                    dark.append((x + ox, y + oy, z + oz))
        if not dark:
            out["left_dark"] = 0
            break
        out["left_dark"] = len(dark)
        laid = []
        for (wx, wy, wz) in dark:
            if (wx, wy, wz) not in protect:
                w.put(wx, wy, wz, LAMP)                  # ordinary ground: flush, as it always was
                out["ground"] += 1
                continue
            air = (wx, wy + 1, wz)
            if air in protect or w.has(*air):
                continue                     # a coat cell of its own overhead: the next round's
                                              # re-propagation reaches this from a neighbour
            if any(max(abs(air[0] - q[0]), abs(air[1] - q[1]), abs(air[2] - q[2]))
                   < LICHEN_SPACING for q in laid):
                continue
            w.put(*air, LICHEN, **faces)
            laid.append(air)
            out["lichen"] += 1
    out["total"] = out["ground"] + out["lichen"]
    return out


def _finish_light(w: World, meta: dict) -> None:
    """Run the night sweep over everything the design built, and record what it had to do.

    The COAT set is a build artifact, not a sidecar fact - it is thousands of coordinates and a
    reader wants the counts - so it is popped rather than shipped, and what survives is the one
    number this file now has to keep honest: how many lamps ended up inside a sculpture.
    """
    protect = meta.pop("protect", set())
    d = _delight(w, protect=protect)
    meta["delight"] = d["total"]
    meta["delight_ground"] = d["ground"]
    meta["delight_lichen"] = d["lichen"]
    meta["delight_in_coat"] = sum(1 for k, (nm, _p) in w.cells.items()
                                  if nm == LAMP and k in protect)
    meta["spawnable_dark"] = d["left_dark"]


# --------------------------------------------------------------------------------- the builders

def _check(w: World, p: dict) -> None:
    """Refuse a build that has actually crossed a line, BEFORE it ships. Both checks here are
    ones a per-cell audit cannot see: a cell claimed by another design, or one east of the
    railway's own corridor - `transit._check`'s own two failures, restated for a landform that
    has no track to make the first of them automatic."""
    avoid = set()
    for path in (p.get("avoid") or []):
        from .railspiral import _reserved as rs_reserved
        avoid |= rs_reserved([path])
    reserve_x = p.get("reserve_x")
    for (x, y, z) in w.cells:
        if (x, y, z) in avoid:
            raise ValueError(f"cell {(x, y, z)} is claimed by another design - move the isthmus")
        if reserve_x is not None and x >= int(reserve_x):
            raise ValueError(f"cell {(x, y, z)} is at x={x}, inside the railway's own corridor "
                             f"(>= {reserve_x}) - narrow the shape")


def _reach(w: World, p: dict, ctx) -> dict:
    """One gap alone - for tuning a single span and for fast tests."""
    gap = p.get("gaps") or GAPS[0]
    meta = {}
    _build_gap(w, p, gap, meta)
    _finish_light(w, meta)
    _check(w, p)
    meta["kind"] = "reach"
    meta["contract"] = ("a walkable causeway across one void gap: a paved spine at the avenue's "
                        "own width joining flush to both plots and widened to the gateways' own "
                        "nine columns where it meets them, moss shoulders that flare to meet the "
                        "plots and narrow between, a fenced rim wherever the ground actually "
                        "ends, and five stops along the way - two sited creatures, a bedded "
                        "still pool, a planted garden and a lit overlook past the rim, carrying "
                        "two real streetfurniture benches and named at both flush ends by a real "
                        "wayfinding archway")
    return meta


def _isthmus(w: World, p: dict, ctx) -> dict:
    """Both gaps, shipped as one design - `transit._line`'s own reasoning: split in two they
    would only ever be generated and looked at together, and nothing here contests a shared
    cell between them, so there is no `defer_to` question to create by splitting."""
    gaps = p.get("gaps") or GAPS
    meta = {}
    for gap in gaps:
        _build_gap(w, p, gap, meta)
    _finish_light(w, meta)
    _check(w, p)
    meta["kind"] = "isthmus"
    meta["contract"] = ("the void between every pair of theme-park islands, walkable end to "
                        "end and never empty: a paved spine continuing each zone's own avenue "
                        "and widened to meet its gateways square, moss shoulders that narrow to "
                        "a neck at the midpoint and flare to meet each plot, a fenced rim "
                        "wherever the ground gives way to the two-hundred-block drop, and five "
                        "stops on every span - two sited creatures on their own plinths, a "
                        "bedded still pool, a planted garden roundel and a lit overlook past "
                        "the rim carrying two real streetfurniture benches - every span named at "
                        "both its own flush ends by a real wayfinding archway, so the walk "
                        "between the islands is a section of the park in its own right rather "
                        "than a gap between the real ones")
    return meta


BUILDERS = {"isthmus": _isthmus, "reach": _reach}


def build(cfg: dict, donors=None) -> Canvas:
    p = {**ISTHMUS, **(cfg or {})}
    if p["kind"] not in BUILDERS:
        raise ValueError(f"unknown isthmus kind {p['kind']!r}; have {sorted(BUILDERS)}")
    w = World()
    meta = BUILDERS[p["kind"]](w, p, None)
    return w.canvas({
        "kind": f"isthmus/{p['kind']}",
        "facing": "south",
        "x_spine": int(p["x_spine"]),
        "contract": meta.get("contract", ""),
        **{k: v for k, v in meta.items() if k != "contract"},
    })
