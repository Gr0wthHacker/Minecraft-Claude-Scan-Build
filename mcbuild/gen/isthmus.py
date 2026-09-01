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
platform out past the rim at the middle.

**DO NOT WRITE A NEW SCULPTURE. SITE AN OLD ONE.** This repo has eight failed mammal builds and
three that read instantly behind it, and the line between them is not species, it is
PLANAR/COLUMNAR against VOLUMETRIC - a spread wing, a neck, a splayed limb, a pattern on one
convex dome all read; four legs standing on the ground never do, at any scale (see CLAUDE.md's
ANIMALS section). `heron.py`, `dragonfly.py` and `ladybug.py` are three of the shapes that
passed, and none of them need a world capture to stand up - they take a world coordinate
directly - so sitting one on a plinth here is a siting job, exactly as asked, not a modelling one.
`turtle.py` and `frog.py` were left out on the same grounds this file already follows for every
other choice: both hard-code a ground-probing range that assumes the lowland's own Y band, and
patching a tested generator's internals to reuse it somewhere else is a bigger, riskier change
than choosing a different one of the seven that already stands on its own.

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
# `dragonfly.py` was tried and dropped: its two wing pairs are `birch_trapdoor`s placed with a
# deliberate gap from the body and from each other ("closed birch trapdoors... need no
# support" - its own docstring), which is a real design choice for a piece meant to be looked
# at, not placed, and it makes the model FIVE separate components by construction, at any
# scale. `heron.py` has the opposite problem in the other direction: it is tuned for its own
# full size and comes apart into a dozen fragments below about scale 0.85 - "wants to be built
# big rather than survive being small" is not a metaphor. Measured with a flood fill rather
# than assumed, `variant=heron` and `variant=flamingo` are both ONE piece at scale 0.9 and
# `ladybug.py` is one piece from 0.7 up - those are the numbers used below, and
# `_site_creature`'s own largest-component filter is the second line of defence against the
# odd stray cell (flamingo sheds a lone 2-cell fragment at its own full scale 1.0).
GAPS = [
    {"z_lo": 80450, "z_hi": 80550, "land_a": "frontier", "land_b": "midway",
     "title": "THE FRONTIER REACH",
     "creatures": [
         {"kind": "heron", "variant": "heron", "t": 0.14, "side": 1, "scale": 0.9,
          "title": "GREY HERON", "lines": ["wades the shallows", "of the frontier", "marsh"]},
         {"kind": "ladybug", "t": 0.86, "side": -1, "scale": 0.7,
          "title": "LADYBIRD", "lines": ["seven spots", "on a leaf", "by the road"]},
     ]},
    {"z_lo": 80650, "z_hi": 80750, "land_a": "midway", "land_b": "hollow",
     "title": "THE HOLLOW REACH",
     "creatures": [
         {"kind": "heron", "variant": "flamingo", "t": 0.14, "side": 1, "scale": 0.9,
          "title": "FLAMINGO", "lines": ["a flare of pink", "against the", "hollow dark"]},
         {"kind": "ladybug", "t": 0.86, "side": -1, "scale": 1.0,
          "title": "LADYBIRD", "lines": ["seven spots", "on a leaf", "in the gloom"]},
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


def _paste(w: World, canvas: Canvas, origin=None, keep_largest=False) -> int:
    """Copy an already-built `Canvas`'s cells into `w` at a world position.

    This is how a sited creature reaches the causeway: `heron.py` and `ladybug.py` are both
    tested, finished generators in their own right, and pasting their output is a siting job,
    never a re-modelling one. `origin` overrides the canvas's own `world_origin`, for callers
    that place it by hand rather than through a generator's own `feet`/`root` parameter.
    `keep_largest` runs `_largest_component` first - see its own docstring for why a sited
    creature needs it even at a scale that is otherwise safe.
    """
    ox, oy, oz = origin if origin is not None else getattr(canvas, "world_origin", (0, 0, 0))
    cells = _canvas_cells(canvas)
    if keep_largest:
        cells = _largest_component(cells)
    for (x, y, z), (name, props) in cells.items():
        w.put(x + ox, y + oy, z + oz, name, **props)
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


# --- sited creatures: two tested, non-mammal generators, neither of which needs a world capture

def _site_heron(w, plinth_top, cx, cz, spec):
    """A heron (or a flamingo, via `variant`) planted foot-first on the plinth.

    ONLY THE FEET NEED TO STAND ON SOMETHING - the neck, the wings and the tail coverts are
    already one connected piece with the legs inside `heron.py`'s own geometry (verified at
    this scale by flood fill, not assumed), so they are free to reach out over open air past
    the plinth's own edge exactly as a real heron's silhouette does. What the plinth has to get
    right is the two leg columns, not the whole bird's footprint.
    """
    from . import heron as heron_mod
    scale = float(spec.get("scale", 0.9))
    variant = spec.get("variant", "heron")
    c = heron_mod.build_heron({"variant": variant, "scale": scale,
                               "seed": spec.get("seed", 0),
                               "feet": [cx, plinth_top + 1, cz]})
    return _paste(w, c, keep_largest=True)


def _site_ladybug(w, plinth_top, cx, cz, spec):
    """A ladybird - which brings its own leaf and its own rock clod, so the plinth underneath
    is a flat place for THAT to stand on rather than the beetle itself."""
    from . import ladybug as ladybug_mod
    scale = float(spec.get("scale", 0.75))
    c = ladybug_mod.build_ladybug({"scale": scale, "seed": spec.get("seed", 0),
                                   "root": [cx, plinth_top + 1, cz]})
    return _paste(w, c, keep_largest=True)


_SITERS = {"heron": _site_heron, "ladybug": _site_ladybug}

# The plinth only has to be wide enough for a creature's own feet or clod, not its wingspan or
# its leaf - see `_site_heron`'s own note. The bulge asks for a little more than that so the
# plinth reads as a made platform rather than a pedestal cut flush with its own footing.
_PLINTH_HALF = {"heron": 5, "ladybug": 6}
_CREATURE_ROOM = {"heron": 13, "ladybug": 15}


# ------------------------------------------------------------------------------------ one gap

def _build_gap(w: World, p: dict, gap: dict, meta: dict) -> None:
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
        ccz = z_lo + int(round(float(spec["t"]) * span))
        ccx = xs + int(spec.get("side", 1)) * coff
        stops.append((ccx, ccz, room + 4, cextra, "creature", spec))
        creature_stops.append((ccx, ccz, int(_PLINTH_HALF[kind]), spec))

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
            half = next(h for (ccx, ccz, h, s) in creature_stops if s is spec)
            _flatten(cols, cx, cz, half + 3)          # the plinth PLUS a flat forecourt round it

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

    # ------------------------------------------------------------ pass 4: drifts on the shoulder,
    # excluding every stop's own footprint - a stop plants ITS OWN ground, deliberately, rather
    # than competing with a chance-picked ambient drift for the same cells.
    exclude = set()
    for (cx, cz, _zspan, _ehalf, kind, spec) in stops:
        r = (int(p["pool_radius"]) + 2 if kind == "pool" else
             int(p["garden_radius"]) + 2 if kind == "garden" else
             next(h for (ccx, ccz, h, s) in creature_stops if s is spec) + 3)
        for dx in range(-r, r + 1):
            for dz in range(-r, r + 1):
                if dx * dx + dz * dz <= r * r:
                    exclude.add((cx + dx, cz + dz))

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
        placed = _SITERS[spec["kind"]](w, top, ccx, ccz, spec)
        plaqued = _plaque(w, ccx, ccz, top, pal_c, "north",
                          spec.get("title") or spec["kind"].upper(), spec.get("lines") or [])
        creatures_built.append({"kind": spec["kind"], "at": [ccx, top, ccz],
                                "cells": placed, "named": plaqued})

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
                    if not z_lo <= z <= z_hi or (x, z) in placed_at or (x, z) in exclude:
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


def _delight(w: World, rounds=3) -> int:
    """Patch every spawnable cell still dark, by turning its own supporting block into a flush
    light - `frog.py`'s own rule ("in the skin, not on it") generalised to whatever this design
    actually built rather than guessed at in advance.

    A SITED CREATURE ARRIVES WITH A SURFACE THIS DESIGN DID NOT MEASURE IN ADVANCE. Every other
    light in this file is placed by a rule written for the SHAPE it is lighting - the flush
    grid for the terrain, one lamp in a pool's own bed, a lamp on each rim rail of the overlook
    - and a heron's back or a ladybird's shell is neither of those; it is whatever `heron.py`
    or `ladybug.py` happened to build. `Island Night` and `Lowland Glow` both solved their own
    islands the same way: place, measure again, repeat, because lighting one cell can only ever
    help its neighbours, never re-darken them, so a small fixed number of rounds converges.
    """
    from .. import nightlight
    fixed = 0
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
            break
        for (wx, wy, wz) in dark:
            w.put(wx, wy, wz, LAMP)
            fixed += 1
    return fixed


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
    meta["delight"] = _delight(w)
    _check(w, p)
    meta["kind"] = "reach"
    meta["contract"] = ("a walkable causeway across one void gap: a paved spine at the avenue's "
                        "own width joining flush to both plots and widened to the gateways' own "
                        "nine columns where it meets them, moss shoulders that flare to meet the "
                        "plots and narrow between, a fenced rim wherever the ground actually "
                        "ends, and five stops along the way - two sited creatures, a bedded "
                        "still pool, a planted garden and a lit overlook past the rim")
    return meta


def _isthmus(w: World, p: dict, ctx) -> dict:
    """Both gaps, shipped as one design - `transit._line`'s own reasoning: split in two they
    would only ever be generated and looked at together, and nothing here contests a shared
    cell between them, so there is no `defer_to` question to create by splitting."""
    gaps = p.get("gaps") or GAPS
    meta = {}
    for gap in gaps:
        _build_gap(w, p, gap, meta)
    meta["delight"] = _delight(w)
    _check(w, p)
    meta["kind"] = "isthmus"
    meta["contract"] = ("the void between every pair of theme-park islands, walkable end to "
                        "end and never empty: a paved spine continuing each zone's own avenue "
                        "and widened to meet its gateways square, moss shoulders that narrow to "
                        "a neck at the midpoint and flare to meet each plot, a fenced rim "
                        "wherever the ground gives way to the two-hundred-block drop, and five "
                        "stops on every span - two sited creatures on their own plinths, a "
                        "bedded still pool, a planted garden roundel and a lit overlook past "
                        "the rim - so the walk between the islands is a section of the park in "
                        "its own right rather than a gap between the real ones")
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
