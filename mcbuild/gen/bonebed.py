"""THE BONE BED - the excavation the Lost Plateau is actually about.

Jack, on the re-themed land: *"its just buildings, the dig zone is crappy ... i really dont like
this splatter of buildings that dont look amazing and dont really do anything."*

Measured over the shipped park before this was written, the Frontier's west half - columns A and
B, U0-93, 11,310 columns, 40% of the land's ground - carried **six buildings, 17,857 blocks and
ONE interactive block between them**:

    Trailhead Gate 4,260 / 0 verbs   Prospecting Porch 3,499 / 0   Mining Square 2,469 / 0
    Assay & Prize  2,248 / 0         Works Yard        1,227 / 0   Vantage Lookout 4,154 / 1

...and its density was 4.3 and 3.1 blocks per column against column C's 10.8, which is the
mountain and the coaster. **The land's whole identity is in its east half and its west half was a
gold-rush mining camp that got re-SIGNED for the jungle and never re-BUILT.**

This replaces `PF Frontier Diggings` and `PF Mining Square` with ONE excavation across both their
lots - V24-122 x U47-92, 99 x 46 - and it is a single mass rather than a set of objects, which is
the only thing that has ever read in this park. CLAUDE.md records the rule three times over now:
*scattered objects on a flat plane are clutter whatever their shape; every part of this park that
reads is TERRAIN or a single mass.*

## The form

**A PIT IS A HOLE IN THE SPOIL, NOT A CUT.** A litematic cannot express removal, so an excavation
sunk below the plane would be a dig list a hundred columns wide. It does not need to be: the floor
stays at the park's own plane and the ground is RAISED around it, which is `fossils.reserve`'s own
trick at fifty times the size and `downs.py`'s "the shaft is a hole in a HILL". Relief from crest
to floor is twelve to fourteen courses and nothing has to be broken first.

**THE WALLS ARE BENCHED, WHICH IS WHAT MAKES IT AN EXCAVATION RATHER THAN A CRATER.** A quarry
face steps: a rise every couple of cells, so the wall reads as worked ground and a guest can see
how deep they are. `_field` steps it BY CONSTRUCTION rather than snapping a smooth field
afterwards - `mineridge._terrace` shipped a ziggurat the first time a snap was applied everywhere.

**THE STREET IS THE WAY IN.** `Park Ways` runs a three-wide cross walk at V77-79 from U41 to U97,
straight through this lot, and it must stay level - so it is not fought, it is USED: the walk
arrives at the pit's own floor course and becomes the causeway between the north bay (the
excavation) and the south bay (the working camp). You do not look at this dig over a fence; the
park's own path delivers you into the bottom of it.

**AND THE OVERLOOK IS ON THE AVENUE.** The bank on the lot's u=0 flank is the one a guest walks
past on the main avenue, so it is the low one and it carries a timber gallery: you step off the
street onto a deck eight courses up and the whole skeleton is laid out below you in PLAN, which is
the view voxels give away free and the reason a dig is the right subject for this medium at all.

## What is in it

    the north bay   the excavation: benched walls, a sauropod laid out on the floor, the bones
                    still half in the matrix, plaster jackets on the ones being lifted
    the causeway    the park's own walk, at the floor course, between the two
    the south bay   the working camp: a gantry and winch over a second trench, spoil heaps,
                    the field shelter, crates and stacked jackets
    the gallery     a timber deck on the avenue bank, railed, with steps up from the street

**NOT ONE BUILDING WITH A DOOR IN IT.** The shelter is an open canvas roof on posts, which is what
a field camp has; the rest is ground, timber and bone.

## The geology is the ridge's own

Imported from `gen/mineridge.py` rather than restated - same materials, same repeating strata,
same `_pick`. Two files each holding a copy of what rock looks like is how one mountain becomes
two different mountains in the same land, and this pit is cut into that mountain's own foot.

The turf and the planting are `gen/plateau.py`'s JUNGLE for the same reason: the ground above the
pit is the ground the plateau dresses, and a second green would read as a second land.
"""
from __future__ import annotations

import numpy as np

from .canvas import Canvas, hash01
from . import fossils
from .frontier_builds import _Lot
from .mineridge import ROCK, _BAND, _CRUST, _DARK, _MID, _STRATA, _noise, _pick
from .plateau import JUNGLE

#: The camp's own kit. Timber and canvas - a field camp is tents and scaffold, never masonry, and
#: the one thing this design must not do is put another building on this land.
#: Checked against `blocks.available` (1.19), `blocks.spendable` (dirt is CURRENCY here) and
#: `palette.tier` by `tests/test_bonebed.py`, which asks the registry rather than this comment.
CAMP = {
    "post": "jungle_log",
    "beam": "stripped_jungle_log",
    "plank": "jungle_planks",
    "slab": "jungle_slab",
    "stair": "jungle_stairs",
    "fence": "jungle_fence",
    "trap": "jungle_trapdoor",
    "sign": "jungle_wall_sign",
    "canvas_a": "white_wool",          # L236 - the tent fly, and the plaster jackets
    "canvas_b": "red_wool",            # L65  - 171 of luminance in one step
    "rope": "iron_chain",
    "crate": "barrel",
    "lamp": "lantern",
    "glow": "ochre_froglight",
    "walk": "cobblestone",             # the dig road
    "walk_b": "gravel",
    "kerb": "cobbled_deepslate_slab",  # L77 against the road's 127 - the line that reads
    "step": "cobblestone_stairs",
    "grille": "iron_bars",
}

#: THE FLOOR OF THE PIT, AND IT IS DARK ON PURPOSE. `bone_block` is 225 luminance; on
#: `cobbled_deepslate` (77) that is a 148-point step and the skeleton reads from the gallery eight
#: courses up. The exhibit IS the contrast, and this repo has laid four greys of one family on
#: each other four separate times before anybody measured across families.
_PIT_FLOOR = (("deep", 0.44), ("deep_b", 0.22), ("rock_c", 0.20), ("scree", 0.14))

BONEBED = {
    "kind": "bonebed",
    "lot": None,                  # [dv, du] - the measured lot, and the hard boundary
    "at": None,                   # [V, U] - the lot's near corner in park coordinates
    "anchor": [97500, 203, 80300],
    "sy": 30,

    #: **LOCAL v bands that must stay at the plane and passable.** The park's own cross walk runs
    #: V77-79 x U41-97 straight through this lot; it is a guest street and this design does not
    #: get to raise it. Everything else is shaped around it.
    "level_v": [],                # [[v0, v1], ...]
    "level_u": [],                # [[u0, u1], ...] - an avenue running ALONG v, same rule
    "margin": 2,                  # cells of dead-level apron at the lot's own edges

    #: THE PITS, in LOCAL cells: [v0, v1, u0, u1, depth]. `depth` is how far the ground around one
    #: stands above its floor, which is the only sense "depth" has when the floor is the plane and
    #: all the relief is spoil.
    "pits": [],
    #: HOW FAR THE PIT'S EDGE WANDERS OFF THE BOX IT DECLARES. amp 0 gives the literal
    #: rectangle, which reads in plan as a swimming pool - see `_pit_mask`.
    "wobble": {"amp": 2.6, "grain": 9},
    "bench_run": 2,               # cells of tread between benches on a pit wall
    "bench_rise": 3,              # ...and the riser
    #: THE SOFT LIMIT. Height is clamped to this many courses per cell of distance from anything
    #: that must stay level, so a bank never walls a street and every crest is reachable on foot.
    #: Under 1.0 by a margin, because rounding to whole courses adds back up to half of one.
    "slope": 0.62,
    "roll": {"grain": 17, "amp": 2.2},   # the bank is ground, not a berm: coarse roll over it
    "cap": 14,                    # the highest the spoil ever stands

    "ramps": [],                  # see `_ramp` - a cut through a bank down into a pit
    "gallery": None,              # see `_gallery` - the timber overlook on the avenue bank
    "skeletons": [],              # see `_skeletons`
    "skulls": [],                 # see `_skulls` - a find too big for a full animal
    "gantry": None,               # see `_gantry`
    "shelter": None,              # [v, u, w, d]
    "spoil": [],                  # [[v, u, r, h], ...] - tipped heaps on the flat
    "crates": [],                 # [[v, u], ...]
    "jackets": [],                # [[v, u], ...] - plaster-jacketed bones waiting to be lifted
    #: GROUND ANOTHER DESIGN STANDS ON: [[v0, v1, u0, u1], ...]. The mass and the floor still form
    #: under it - a game needs something to stand ON - but nothing this design DRESSES goes there,
    #: because a survey stake in the middle of somebody's console is a console that does not work.
    #: `test_bonebed.py` asserts the reserve is empty above the floor course.
    "reserve": [],
    "grid": {"step": 6},          # the survey stakes on the dig floor
    "walks": [],                  # [[v0, v1, u, wide], ...] - the plank walk on the floor
    "plant": {"tree": 0.010, "fern": 0.13, "vine": 0.22},
    "light": 11,                  # a flush froglight about every this many cells of dig floor
    #: THE LAND'S FRONT DOOR, AND IT IS ONE ARCH. Jack, choosing what replaces the Trailhead
    #: Gate's 45x39 of towers, court, stockade, office and store: "a single arch/portal, small -
    #: no court, no towers, no stockade. The land's identity comes from the terrain behind it."
    "arch": None,                 # see `_arch`
    "boards": [],                 # [{v, u, facing, lines}] - the interpretation signs
    "seed": 0,
    "title": "THE BONE BED",
}


# --------------------------------------------------------------------------- the ground


def _dist_out(mask: np.ndarray, cap: int) -> np.ndarray:
    """Cells of distance OUT of `mask`, capped - iterative dilation, numpy only (no scipy).

    `mineridge._away` answers the same question as a float already capped; this returns the
    INTEGER step count, because a benched wall is `ceil(d / run) * rise` and a float that has
    been clamped cannot be stepped without inheriting the clamp's own plateau.
    """
    d = np.full(mask.shape, cap, np.int32)
    if not mask.any():
        return d
    d[mask] = 0
    cur = mask.copy()
    for k in range(1, cap + 1):
        grown = cur.copy()
        grown[1:, :] |= cur[:-1, :]
        grown[:-1, :] |= cur[1:, :]
        grown[:, 1:] |= cur[:, :-1]
        grown[:, :-1] |= cur[:, 1:]
        ring = grown & ~cur
        d[ring] = k
        cur = grown
        if cur.all():
            break
    return d


def _reserved(p: dict, dv: int, du: int) -> np.ndarray:
    """Cells another design stands on - dressed by nobody, floored by this one."""
    m = np.zeros((dv, du), bool)
    for box in (p.get("reserve") or []):
        v0, v1, u0, u1 = (int(x) for x in box)
        m[max(0, v0):min(dv, v1 + 1), max(0, u0):min(du, u1 + 1)] = True
    return m


def _level_mask(p: dict, dv: int, du: int) -> np.ndarray:
    """Every cell this design may not raise: the streets through it and its own edges.

    **TWO KINDS OF BOUNDARY, AND CONFLATING THEM COSTS THE WHOLE IDEA** - which `downs.py` records
    from the other side. A STREET is met at grade over many cells, because that is what makes this
    a park; a PIT is met with a benched scarp, and that scarp is the excavation. So the streets go
    in here and the pits emphatically do not.
    """
    m = np.zeros((dv, du), bool)
    margin = max(0, int(p.get("margin", 2)))
    if margin:
        m[:margin, :] = True
        m[dv - margin:, :] = True
        m[:, :margin] = True
        m[:, du - margin:] = True
    for band in (p.get("level_v") or []):
        a, b = int(band[0]), int(band[1])
        m[max(0, a):min(dv, b + 1), :] = True
    for band in (p.get("level_u") or []):
        a, b = int(band[0]), int(band[1])
        m[:, max(0, a):min(du, b + 1)] = True
    #: **RESERVED GROUND IS LEVEL GROUND.** A box another design stands on is a box this one may
    #: not raise either - the ride inside this lot is 23 x 26 of track laid at the plane, and a
    #: bank rising under half of it is a ride buried in a hillside. It is the same rule as a
    #: street and it wants the same mask.
    m |= _reserved(p, dv, du)
    return m


def _pit_mask(p: dict, dv: int, du: int):
    """Every pit, as (mask, per-pit mask+depth) - and NOT ONE OF THEM IS A RECTANGLE.

    **THE RECTANGLE A PIT DECLARES IS THE TOP OF THE HOLE.** Written the other way round - the
    rectangle as the floor, benches stepping UP outside it - the wall came out as a ridge that
    crested midway across the bank and then fell back to three courses at the lip, which is the
    exact opposite of an open pit and shipped once. A pit's face is highest AT the edge and steps
    DOWN inward to the floor, so the benches live inside the declared box.

    **AND THE BOX IS ONLY THE BRIEF.** Built as its literal rectangle the north bay read in plan as
    a swimming pool: four straight benched edges and a green rectangular frame round them. An
    excavation is worked outward from where the bones are, so its edge wanders. The wobble is
    coarse noise on the SIGNED DISTANCE to the box - the boundary moves and the interior does not,
    which is the lowland thicket's own rule (`the noise belongs on the drift's RADIUS, never on its
    interior`) and the reason that pass went from 191 blobs of one or two cells to real drifts.
    """
    m = np.zeros((dv, du), bool)
    out = []
    cap = float(p.get("cap", 14))
    w = p.get("wobble") or {}
    amp = float(w.get("amp", 2.6))
    grain = int(w.get("grain", 9))
    seed = int(p.get("seed", 0))
    for k, spec in enumerate(p.get("pits") or []):
        v0, v1, u0, u1 = (int(x) for x in spec[:4])
        d = float(spec[4]) if len(spec) > 4 else cap
        box = np.zeros((dv, du), bool)
        box[max(0, v0):min(dv, v1 + 1), max(0, u0):min(du, u1 + 1)] = True
        if amp > 0:
            reach = int(amp) + 2
            signed = _dist_out(~box, reach).astype(float) - _dist_out(box, reach).astype(float)
            wob = (_noise(dv, du, seed + 91 + k * 13, grain) - 0.5) * 2.0 * amp
            box = signed > wob
        m |= box
        out.append((box, d))
    return m, out


def _field(p: dict, dv: int, du: int) -> np.ndarray:
    """The ground: spoil banks outside the pits, benched faces stepping down inside them.

    Three terms, and how they compose is the design:

    1. **the soft limit** - `slope` courses per cell of distance from any street. Nothing rises
       faster than a player climbs, so every crest is reachable and no bank walls a walk. It binds
       OUTSIDE a pit, where it is the bank's own height, and it binds INSIDE one too - which is
       what lets the causeway enter the excavation at grade instead of over a nine-course face.
    2. **the benched face** - inside a pit, `depth - ceil((d_in - 1) / run) * rise` where `d_in` is
       the distance INWARD from the rim. Highest at the lip, stepping down to a floor at zero.
       That is an open pit; stepped from the other side it is a ridge.
    3. **the roll** - coarse noise, on the BANKS ONLY. A bank at one height is a berm; a benched
       floor with noise on it is a mess.

    **AND A NESTED PIT TAKES THE LOWER OF THE TWO.** The south bay is a shallow working floor with
    a deeper trench inside it, which is two boxes over one cell, and the minimum is what makes the
    trench a trench rather than the working floor's own bench.
    """
    seed = int(p.get("seed", 0))
    cap = float(p.get("cap", 14))
    slope = float(p.get("slope", 0.62))
    run = max(1, int(p.get("bench_run", 2)))
    rise = max(1, int(p.get("bench_rise", 3)))

    level = _level_mask(p, dv, du)
    soft = _dist_out(level, int(cap / max(slope, 0.05)) + 2).astype(float) * slope

    pit, specs = _pit_mask(p, dv, du)
    inner = np.full((dv, du), cap, float)
    for box, depth in specs:
        d_in = _dist_out(~box, int(depth / rise) * run + run + 2)
        face = depth - np.ceil(np.maximum(0, d_in - 1) / run) * rise
        inner = np.where(box, np.minimum(inner, np.maximum(face, 0.0)), inner)

    r = p.get("roll") or {}
    roll = (_noise(dv, du, seed + 41, int(r.get("grain", 17))) - 0.5) * 2.0         * float(r.get("amp", 2.2))

    bank = np.minimum(soft, cap) + roll
    h = np.where(pit, np.minimum(inner, soft), bank)
    h = np.minimum(h, soft)                 # neither the roll nor a face may over-top a street
    h = np.maximum(h, 0.0)
    h[level] = 0.0
    return np.round(h).astype(int)


def _steep(h: np.ndarray, v: int, u: int) -> bool:
    """True where the ground falls two or more courses to a face neighbour - no soil holds there."""
    dv, du = h.shape
    a = int(h[v, u])
    for dvv, duu in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        b, c = v + dvv, u + duu
        if 0 <= b < dv and 0 <= c < du and a - int(h[b, c]) >= 2:
            return True
    return False


def _fill(lot: _Lot, h: np.ndarray, pit: np.ndarray, seed: int) -> dict:
    """The spoil itself: bedded rock to the crest, turf over it, scree only on a CRUST.

    Rule 13 - a gravity block may not stand over air - so gravel is only ever the top course of a
    column that is solid to the plane, which is what `_CRUST` is for and what the ridge learned.
    """
    dv, du = h.shape
    out = {"rock": 0, "turf": 0}
    for v in range(dv):
        for u in range(du):
            top = int(h[v, u])
            if top <= 0:
                continue
            for y in range(top + 1):
                if y == top:
                    #: TURF WHERE THE GROUND IS FLAT ENOUGH TO HOLD SOIL AND ROCK WHERE IT IS NOT.
                    #: That is what keeps a bank reading as a hillside with spoil showing through
                    #: rather than as a grey mound, and it is `downs.py`'s own rule.
                    #: **AND NOTHING INSIDE A PIT IS EVER TURF.** A bench is a worked face; grassed
                    #: over, the first build grew a line of trees down the middle of its own
                    #: excavation - which passes every check there is and makes no sense at all to
                    #: anybody standing in it.
                    if pit[v, u] or _steep(h, v, u):
                        out["rock"] += int(lot.put(v, y, u, ROCK[_pick(_CRUST, v, u, y, seed)]))
                    else:
                        out["turf"] += int(lot.put(v, y, u, JUNGLE["turf"]))
                else:
                    band = _STRATA[((top - y) // _BAND) % len(_STRATA)]
                    if top - y < 3:
                        band = _MID
                    if y < 2:
                        band = _DARK
                    out["rock"] += int(lot.put(v, y, u, ROCK[_pick(band, v, u, y, seed)]))
    return out


# --------------------------------------------------------------------------- the excavation


def _floor(lot: _Lot, p: dict, seed: int) -> dict:
    """The dig floor, and the causeway that crosses it.

    Everything at y=0 inside a pit or on a level band, so a guest coming off the park's own walk
    steps onto worked ground rather than onto lawn - the one thing that would say "this is a lawn
    with a hole beside it" instead of "this is the bottom of an excavation".
    """
    dv, du = lot.dv, lot.du
    pit, _ = _pit_mask(p, dv, du)
    #: RESERVED GROUND IS SOMEBODY ELSE'S FLOOR. The causeway's own kerb ran along the band's last
    #: row and six of its slabs landed inside a game's footprint - which the audit cannot see,
    #: because a slab beside a console is a legal slab.
    keep = _reserved(p, dv, du)
    out = {"floor": 0, "road": 0, "kerb": 0}
    for v in range(dv):
        for u in range(du):
            if not pit[v, u] or keep[v, u]:
                continue
            key = _pick(_PIT_FLOOR, v, u, 0, seed)
            out["floor"] += int(lot.put(v, 0, u, ROCK[key]))
    #: **THE CAUSEWAY IS NOT RESURFACED, AND IT USED TO BE.** `Park Ways` already paves V77-79 and
    #: it is a guest street; laying a dig road over it is two designs on one surface, which is what
    #: `finish.defer_to` and the casino's layer slice both exist to stop. Worse, the kerb that came
    #: with it ran along the band's own first and last rows - so a THREE-WIDE walk had two thirds of
    #: it kerbed and one cell left to walk on, which every audit passes because a bottom slab is a
    #: legal bottom slab. The street stays the street; the pit floor abuts it at the same course.
    return out


def _near_pit(pit: np.ndarray, v: int, u: int, r: int) -> bool:
    dv, du = pit.shape
    return bool(pit[max(0, v - r):min(dv, v + r + 1), max(0, u - r):min(du, u + r + 1)].any())


def _grid(lot: _Lot, h: np.ndarray, pit: np.ndarray, p: dict, seed: int) -> dict:
    """The survey grid: stakes on the dig floor at a lattice, and a plank walk between them.

    **THE STAKES ARE THE ONE THING EVERY PHOTOGRAPH OF A REAL EXCAVATION HAS IN IT** - the rule
    `fossils.furniture` states - but that one squares a RECTANGLE's lip, and this pit's edge
    wanders by construction. A lattice on the FLOOR reads better anyway: from the gallery it is a
    grid over the bones, which is the whole visual language of a dig.

    **AND THE WALK IS WHY A GUEST IS DOWN THERE.** A pit with a skeleton in it and nowhere to
    stand is a diorama; a plank walk from the causeway past the animal and out at the ramp is a
    route, and a route is somewhere to be. It is laid ONE CELL PROUD of nothing - flat on the
    floor - so it can never fence the bones off from the view.
    """
    dv, du = h.shape
    step = max(3, int((p.get("grid") or {}).get("step", 6)))
    #: **A STREET IS NOT DIG FLOOR, HOWEVER FLAT IT IS.** The pit's edge wanders by construction,
    #: so the wobbled mask reaches into the causeway band - and a survey stake standing in a guest
    #: walk is an obstruction that every audit passes, because a fence post is a legal fence post.
    keep = _reserved(p, dv, du) | _level_mask(p, dv, du)
    out = {"stake": 0, "walk": 0}
    for v in range(0, dv, step):
        for u in range(0, du, step):
            if keep[v, u] or not pit[v, u] or h[v, u] != 0:
                continue
            if lot.has(v, 1, u):
                continue                       # a bone, a crate or a jacket owns this cell
            for y in (1, 2):
                out["stake"] += int(lot.fence(v, y, u, "v", key=CAMP["fence"]))
    for run in (p.get("walks") or []):
        v0, v1, u = int(run[0]), int(run[1]), int(run[2])
        wide = int(run[3]) if len(run) > 3 else 1
        for v in range(v0, v1 + 1):
            for k in range(wide):
                uu = u + k
                if not lot.inside(v, uu) or h[v, uu] != 0 or keep[v, uu]:
                    continue
                if lot.has(v, 1, uu):
                    continue
                out["walk"] += int(lot.put(v, 0, uu, CAMP["plank"]))
    return out


def _ramp(lot: _Lot, h: np.ndarray, spec, p: dict, seed: int) -> dict:
    """A cut down a benched wall - the way a barrow gets to the floor, and the way a guest does.

    **A BENCHED WALL IS DELIBERATELY UNCLIMBABLE**, so a pit with no ramp is a pit a guest can
    only look at. The ramp is a designed slot: the height field is not consulted, it is
    OVERWRITTEN course by course down the slot, so the ramp cannot be a dent in whatever the wall
    happened to give at that column. That is the ridge's own tunnel lesson, twice recorded.
    """
    v, u, axis, length, width = spec["v"], spec["u"], spec.get("axis", "u"), \
        int(spec.get("length", 12)), int(spec.get("width", 3))
    step = int(spec.get("step", 1))
    sign = int(spec.get("sign", 1))
    out = {"tread": 0, "kerb": 0}
    for k in range(length):
        y = max(0, int(round((length - 1 - k) * step * 0.5)))
        for w in range(width):
            if axis == "u":
                vv, uu = v + w, u + sign * k
            else:
                vv, uu = v + sign * k, u + w
            # the slot itself, and everything under it filled so the ramp is ground rather than a
            # shelf with air below.
            for yy in range(0, y + 1):
                if yy == y:
                    r = hash01(vv * 3, uu * 5, yy, seed)
                    out["tread"] += int(lot.put(vv, yy, uu,
                                                CAMP["walk" if r < 0.6 else "walk_b"]))
                else:
                    lot.put(vv, yy, uu, ROCK[_pick(_MID, vv, uu, yy, seed)])
            # clear the bank above the slot, or the ramp is a tunnel through the spoil
            for yy in range(y + 1, int(h.max()) + 3):
                lot.put(vv, yy, uu, "air")
    return out


# --------------------------------------------------------------------------- the timber


def _gallery(lot: _Lot, h: np.ndarray, spec: dict, seed: int) -> dict:
    """The overlook: a LEVEL timber deck on the crest of the avenue bank, railed, with two flights.

    **THIS IS THE MONEY VIEW AND IT IS ON THE MAIN ROUTE.** A dig is read in PLAN - the one view
    voxels give away free, and the reason the ladybird and the turtle work - so the design's whole
    job is to put a guest above the floor and let them look down the length of the skeleton.

    **A DECK IS LEVEL AND THE GROUND UNDER IT IS NOT.** Seated per column on the height field it
    stepped four courses over its own length, which is a path up a hill rather than a platform;
    one course is taken for the whole run and the posts make up whatever each column is short.
    That is also the only way the rail reads as a rail rather than as a staircase of fences.
    """
    v0, v1 = int(spec["v0"]), int(spec["v1"])
    u = int(spec["u"])
    w = int(spec.get("w", 4))
    du = lot.du
    band = h[v0:v1 + 1, max(0, u):min(du, u + w)]
    y = int(np.median(band)) + 1 if band.size else 1
    out = {"deck": 0, "rail": 0, "post": 0, "step": 0, "lamp": 0, "y": y}
    for v in range(v0, v1 + 1):
        for k in range(w):
            uu = u + k
            #: everything between the deck and the ground it stands over is cleared, or a deck laid
            #: over a crest higher than itself is a plank buried in a bank.
            for yy in range(y, y + 3):
                lot.put(v, yy, uu, "air")
            out["deck"] += int(lot.put(v, y, uu, CAMP["plank"]))
        for k in (0, w - 1):
            uu = u + k
            ground = int(h[v, max(0, min(du - 1, uu))])
            if v % 4 == 0 and ground < y:
                for yy in range(ground, y):
                    out["post"] += int(lot.log(v, yy, uu, CAMP["post"], axis="y"))
        # THE RAIL IS ON THE PIT SIDE ONLY. A rail on the street side would fence the deck off the
        # avenue it is entered from, which is the one thing an overlook must not do.
        out["rail"] += int(lot.fence(v, y + 1, u + w - 1, "v", key=CAMP["fence"]))
        if v % 8 == 0:
            out["post"] += int(lot.log(v, y + 1, u + w - 1, CAMP["post"], axis="y"))
            out["lamp"] += int(lot.put(v, y + 2, u + w - 1, CAMP["lamp"], hanging="false",
                                       waterlogged="false"))
    for fv in (spec.get("steps") or []):
        out["step"] += _steps(lot, h, int(fv), u, y, seed)
    return out


def _steps(lot: _Lot, h: np.ndarray, v: int, u: int, top: int, seed: int) -> int:
    """A flight from the street course up onto the deck, TWO WIDE, ascending toward the deck.

    A FLIGHT THAT ASCENDS TOWARD D HAS EVERY TREAD `facing=D, half=bottom` - the convention this
    repo settled off Jack's own flight and pinned in `tests/test_stairhead.py`, because our
    renderer draws both directions identically and a backwards flight cannot be walked up. The
    deck is at rising u from the street, so the flight ascends SOUTH.
    """
    n = 0
    du = lot.du
    for k in range(top + 1):
        uu = u - (top - k)
        if uu < 0:
            continue
        for dvv in range(2):
            for yy in range(0, k):
                lot.put(v + dvv, yy, uu, ROCK[_pick(_MID, v, uu, yy, seed)])
            for yy in range(k + 1, k + 4):
                lot.put(v + dvv, yy, uu, "air")
            if k == top:
                n += int(lot.put(v + dvv, k, uu, CAMP["plank"]))
            else:
                n += int(lot.stair(v + dvv, k, uu, CAMP["stair"], facing="south"))
    return n


def _gantry(lot: _Lot, h: np.ndarray, spec: dict, seed: int) -> dict:
    """A lifting frame over the working trench: four legs, two head beams, a winch and a jacket.

    A gantry is the one piece of kit that says a dig is WORKING rather than finished, and it is
    also the only tall thing in the south bay - which is what stops the working end reading as a
    yard with props on it.
    """
    v, u = int(spec["v"]), int(spec["u"])
    w, d = int(spec.get("w", 7)), int(spec.get("d", 9))
    hgt = int(spec.get("h", 8))
    out = {"leg": 0, "beam": 0, "rope": 0, "load": 0, "brace": 0}
    corners = ((v, u), (v + w - 1, u), (v, u + d - 1), (v + w - 1, u + d - 1))
    for cv, cu in corners:
        base = int(h[max(0, min(lot.dv - 1, cv)), max(0, min(lot.du - 1, cu))])
        for y in range(base, base + hgt):
            out["leg"] += int(lot.log(cv, y, cu, CAMP["post"], axis="y"))
        # a knee brace at the head, or the frame reads as four sticks and a plank
        out["brace"] += int(lot.stair(cv, base + hgt - 1, cu + (1 if cu == u else -1),
                                      CAMP["stair"],
                                      facing="south" if cu == u else "north", half="top"))
    top = int(h[max(0, min(lot.dv - 1, v)), max(0, min(lot.du - 1, u))]) + hgt
    for cu in (u, u + d - 1):
        for k in range(w):
            out["beam"] += int(lot.log(v + k, top, cu, CAMP["beam"], axis="x"))
    for k in range(d):
        out["beam"] += int(lot.log(v + w // 2, top + 1, u + k, CAMP["beam"], axis="z"))
    # the winch: a chain off the head beam with a jacketed block on the end, hanging clear
    hv, hu = v + w // 2, u + d // 2
    for y in range(top, top - int(spec.get("drop", 4)), -1):
        out["rope"] += int(lot.put(hv, y, hu, CAMP["rope"], axis="y", waterlogged="false"))
    ly = top - int(spec.get("drop", 4))
    for dvv in range(-1, 1):
        for duu in range(-1, 1):
            out["load"] += int(lot.put(hv + dvv, ly, hu + duu, CAMP["canvas_a"]))
    return out


def _shelter(lot: _Lot, h: np.ndarray, spec, seed: int) -> dict:
    """The field shelter: a levelled pad, four posts, a striped fly and a bench. NO WALLS, NO DOOR.

    The whole complaint this design answers is buildings, so the one covered thing on the lot is a
    tent: you can see through it from every bearing, which is what stops it reading as a shed.

    **IT PITCHES ITSELF A PAD, AND THAT IS NOT DECORATION.** Seated on the height field at ONE
    corner, its bench came away as a four-cell free-floating cluster the moment the ground under
    the far side of it fell a course - which is what ground on a bank does everywhere. A tent goes
    up on flattened ground; levelling the footprint to its own lowest column is both what happens
    in the field and the only way every part of it has something under it by construction.
    """
    v, u, w, d = (int(x) for x in spec)
    out = {"pad": 0, "post": 0, "fly": 0, "bench": 0, "crate": 0}
    dv, du = h.shape
    cols = [(vv, uu) for vv in range(v, v + w) for uu in range(u, u + d)
            if 0 <= vv < dv and 0 <= uu < du]
    if not cols:
        return out
    base = min(int(h[a, b]) for a, b in cols)
    for a, b in cols:
        for y in range(int(h[a, b]), base, -1):
            lot.put(a, y, b, "air")
        out["pad"] += int(lot.put(a, base, b, ROCK[_pick(_CRUST, a, b, base, seed)]))
        for y in range(base + 1, base + 6):
            lot.put(a, y, b, "air")
    hgt = 4
    for cv in (v, v + w - 1):
        for cu in (u, u + d - 1):
            for y in range(base + 1, base + 1 + hgt):
                out["post"] += int(lot.log(cv, y, cu, CAMP["post"], axis="y"))
    for k in range(w):
        for j in range(d):
            #: THE FLY IS STRIPED ALONG ONE AXIS. Hashed per cell it is confetti - the deck
            #: soffit's own failure - and two tones at maximum contrast are what read from fifty
            #: blocks, which is the flamingo's rule and this park's frontage's.
            key = "canvas_a" if (j // 2) % 2 == 0 else "canvas_b"
            out["fly"] += int(lot.put(v + k, base + 1 + hgt, u + j, CAMP[key]))
    for j in range(1, d - 1):
        out["bench"] += int(lot.slab(v + 1, base + 1, u + j, CAMP["slab"], "bottom"))
    out["crate"] += int(lot.put(v + w - 2, base + 1, u + 1, CAMP["crate"],
                                facing="up", open="false"))
    return out


def _spoil(lot: _Lot, h: np.ndarray, off: np.ndarray, spec, seed: int) -> int:
    """A tipped heap - what came out of the pit, standing on the flat beside it.

    **IT IS A CIRCLE AND A STREET IS A STRAIGHT LINE, SO IT HAS TO BE TOLD.** Tipped at radius five
    within five of the lot's own edge, a heap spills onto the verge of the cross avenue - two
    courses of cobble in a guest walk, which every audit passes because a cobblestone is a legal
    cobblestone. `off` is the level and reserved mask, which is the one thing that knows.
    """
    v, u, r, top = (int(x) for x in spec)
    n = 0
    for dvv in range(-r, r + 1):
        for duu in range(-r, r + 1):
            vv, uu = v + dvv, u + duu
            if not lot.inside(vv, uu) or off[vv, uu]:
                continue
            dist = (dvv * dvv + duu * duu) ** 0.5
            if dist > r:
                continue
            hh = int(round(top * (1.0 - dist / (r + 0.001)) ** 1.2))
            base = int(h[vv, uu])
            for y in range(base, base + hh + 1):
                #: A HEAP IS SPOIL, SO IT IS THE PIT'S OWN ROCK - and its crust is scree, which
                #: may only ever be the top course of a column solid to the ground (rule 13).
                key = _pick(_CRUST if y == base + hh else _DARK, vv, uu, y, seed)
                n += int(lot.put(vv, y, uu, ROCK[key]))
    return n


def _arch(lot: _Lot, h: np.ndarray, spec: dict, seed: int) -> dict:
    """The land's gateway: two piers, a lintel over the avenue, a name board and two lamps.

    **IT STRADDLES A STREET AND STANDS BESIDE IT.** The piers sit on the verge either side of the
    paving; nothing is placed in the lanes themselves, because a gate a guest has to walk round is
    not a gate. The span is left OPEN - the whole point of an arch over a road is that you pass
    through it - so the lintel is carried at head height plus two and the opening is the avenue's
    own width.

    Timber on a stone footing: the ridge's own rock under the plateau's own wood, which is what
    makes the gate read as belonging to the ground rather than to a town that is no longer here.
    """
    v = int(spec["v"])
    u0, u1 = int(spec["u0"]), int(spec["u1"])
    hgt = int(spec.get("h", 6))
    depth = int(spec.get("d", 3))
    out = {"pier": 0, "lintel": 0, "lamp": 0, "sign": 0, "brace": 0}
    for cu in (u0, u1):
        base = int(h[max(0, min(lot.dv - 1, v)), max(0, min(lot.du - 1, cu))])
        for k in range(depth):
            vv = v + k
            #: the footing is masonry and the shaft is timber - two courses of the mountain's own
            #: stone under the post, which is what stops a log standing in the turf.
            for y in range(base, base + 2):
                out["pier"] += int(lot.put(vv, y, cu, ROCK[_pick(_MID, vv, cu, y, seed)]))
            for y in range(base + 2, base + hgt):
                out["pier"] += int(lot.log(vv, y, cu, CAMP["post"], axis="y"))
    top = int(h[max(0, min(lot.dv - 1, v)), max(0, min(lot.du - 1, u0))]) + hgt
    for k in range(depth):
        for u in range(u0, u1 + 1):
            out["lintel"] += int(lot.log(v + k, top, u, CAMP["beam"], axis="z"))
        # the head course above it, so the gate has a real depth rather than one beam
        for u in range(u0, u1 + 1):
            if k in (0, depth - 1):
                out["lintel"] += int(lot.slab(v + k, top + 1, u, CAMP["slab"], "bottom"))
    #: a knee brace at each springing, which is the whole difference between a portal and two
    #: posts with a stick across them.
    for cu, face in ((u0, "south"), (u1, "north")):
        step = 1 if cu == u0 else -1
        out["brace"] += int(lot.stair(v, top - 1, cu + step, CAMP["stair"],
                                      facing=face, half="top"))
        out["brace"] += int(lot.stair(v + depth - 1, top - 1, cu + step, CAMP["stair"],
                                      facing=face, half="top"))
    for cu in (u0 + 1, u1 - 1):
        out["lamp"] += int(lot.put(v, top - 1, cu, CAMP["lamp"], hanging="true",
                                   waterlogged="false"))
    #: **THE BOARD FACES THE WAY IN.** A guest reaches this land along the spine at V1-23 and
    #: turns up the avenue into rising V, so a board on the far face is one they read over their
    #: shoulder. It hangs on the gate's own entrance face, looking back down the approach.
    mid = (u0 + u1) // 2
    for u in range(mid - 1, mid + 2):
        lot.put(v, top - 1, u, CAMP["plank"])
    out["sign"] += int(lot.sign(v - 1, top - 1, mid, "west", spec["lines"]))
    return out


# --------------------------------------------------------------------------- the bones


def _skeletons(lot: _Lot, p: dict, seed: int) -> list:
    """The animals, laid out on the floor with `gen/fossils.py`'s primitives.

    **A SKELETON IS THE ONE ANIMAL SHAPE THIS MEDIUM CANNOT GET WRONG** - the rule `fossils.py`
    opens with, and the reason the dig is the right subject for the land at all: a spine is a
    line, a rib is a curve one block thick, a skull is a small box with holes in it. Every one of
    those is planar or columnar, which is what voxels render natively, and the whole thing is read
    from above, which is the view they give away free.

    The bones go down BEFORE any furniture, so a stake or a crate can never take a cell a bone
    wanted - `fossils._bone` writes through `_Lot.put`, which overwrites.
    """
    out = []
    for spec in (p.get("skeletons") or []):
        s = dict(spec)
        s.setdefault("bench", 0)
        out.append({"at": [s["v"], s["u"]], **fossils.skeleton(lot, s, seed)})
    return out


def _skulls(lot: _Lot, p: dict) -> list:
    """A skull and a stub of neck, half out of the matrix - the find that is still being worked.

    **A SHORT TRENCH CANNOT HOLD A SHORT SKELETON.** `fossils.skull` is laid from the spine's LAST
    point and needs seven cells past it, so a thirteen-deep cut leaves a spine of two or three
    vertebrae and one pair of ribs - which is not a small animal, it is a scatter. A SKULL ALONE is
    the right thing in a working trench anyway: it is the part a stranger looks for, it is what a
    gantry is rigged over, and it says the dig is mid-job in a way a tidy little skeleton does not.
    """
    out = []
    for spec in (p.get("skulls") or []):
        v, u = int(spec["v"]), int(spec["u"])
        sk = fossils.skull(lot, v, u, facing_v=int(spec.get("facing_v", 1)))
        neck = 0
        for k in range(1, int(spec.get("neck", 5)) + 1):
            neck += fossils._bone(lot, v - k, u + (0.4 * k if spec.get("bow") else 0))
        out.append({"at": [v, u], "skull": sk["cells"], "neck": neck})
    return out


def _jacket(lot: _Lot, h: np.ndarray, spec, seed: int) -> int:
    """A plaster jacket: a bone wrapped and strapped, waiting for the winch.

    White wool on a dark floor at 148 points of luminance, which is the same contrast the bones
    themselves are read by - so a jacket reads as a bone that has been PACKED rather than as a
    white box somebody left out.
    """
    v, u = int(spec[0]), int(spec[1])
    n = 0
    for a in range(2):
        for b in range(3):
            n += int(lot.put(v + a, 1, u + b, CAMP["canvas_a"]))
    for b in (0, 2):
        n += int(lot.put(v, 2, u + b, CAMP["canvas_b"]))
        n += int(lot.put(v + 1, 2, u + b, CAMP["canvas_b"]))
    return n


# --------------------------------------------------------------------------- the dressing


def _plant(lot: _Lot, h: np.ndarray, pit: np.ndarray, p: dict, seed: int) -> dict:
    """Jungle over the spoil, and vines down the benched faces.

    A RAW BANK IS A QUARRY AND A GREEN ONE IS A HILLSIDE. The land's whole re-theme is that the
    ground is jungle; a hundred-column excavation with bare grey banks would put the mining camp
    straight back, in terrain rather than in timber.
    """
    dv, du = h.shape
    cfg = p.get("plant") or {}
    keep = _reserved(p, dv, du)
    out = {"tree": 0, "fern": 0, "vine": 0, "carpet": 0}
    for v in range(dv):
        for u in range(du):
            top = int(h[v, u])
            if top <= 0:
                continue
            if pit[v, u] or keep[v, u]:
                continue                       # a working dig has no garden in it
            if lot.name_at(v, top, u) != JUNGLE["turf"]:
                continue                       # rock: nothing roots in it (rule 11)
            if lot.has(v, top + 1, u):
                continue
            r = hash01(v * 11 + 3, u * 7 + 1, 5, seed + 7)
            near = pit[max(0, v - 3):v + 4, max(0, u - 3):u + 4].any()
            if (r < float(cfg.get("tree", 0.010)) and not near
                    and 3 < v < dv - 4 and 3 < u < du - 4):
                out["tree"] += _tree(lot, v, top + 1, u, seed)
            elif r < float(cfg.get("tree", 0.010)) + float(cfg.get("fern", 0.13)):
                out["fern"] += int(lot.put(v, top + 1, u, JUNGLE["fern"]))
            elif r < 0.42:
                out["carpet"] += int(lot.put(v, top + 1, u, JUNGLE["carpet"]))
    # vines on the benched faces - a face is a column whose neighbour is two or more courses down
    for v in range(dv):
        for u in range(du):
            top = int(h[v, u])
            if top <= 1:
                continue
            for dvv, duu, side in ((1, 0, "west"), (-1, 0, "east"), (0, 1, "north"),
                                   (0, -1, "south")):
                b, c = v + dvv, u + duu
                if not (0 <= b < dv and 0 <= c < du):
                    continue
                drop = top - int(h[b, c])
                if drop < 2:
                    continue
                if hash01(v * 5, u * 13, 3, seed + 19) > float(cfg.get("vine", 0.22)):
                    continue
                #: A VINE'S FLAGS NAME THE FACE IT CLINGS TO, NOT THE WAY IT LOOKS. Written as
                #: the back of the side it grew from, 98% of a shipped design's vines named a
                #: face with open air behind it - and a vine hanging in air renders identically
                #: to one on a wall in every sheet this repo has.
                for y in range(top, max(0, top - drop), -1):
                    props = {"north": "false", "south": "false", "east": "false",
                             "west": "false", "up": "false"}
                    props[side] = "true"
                    if not lot.put(b, y, c, JUNGLE["vine"], **props):
                        break
                    out["vine"] += 1
    return out


def _tree(lot: _Lot, v: int, y: int, u: int, seed: int) -> int:
    """A jungle broadleaf: a bare trunk and a crown WIDER THAN IT IS TALL.

    A conifer narrows in steps and reads as a fir; what says jungle is a wide flat crown carried
    clear of the ground on a bare trunk, so you see UNDER it. `gen/plateau.py` draws the same
    shape on the ridge above, which is what makes the two read as one wood.
    """
    n = 0
    hgt = 4 + int(hash01(v, u, 1, seed) * 3)
    for k in range(hgt):
        n += int(lot.log(v, y + k, u, JUNGLE["trunk"], axis="y"))
    for dvv in range(-2, 3):
        for duu in range(-2, 3):
            if abs(dvv) + abs(duu) > 3:
                continue
            for k in (0, 1):
                if k == 1 and abs(dvv) + abs(duu) > 1:
                    continue
                n += int(lot.put(v + dvv, y + hgt - 1 + k, u + duu,
                                 JUNGLE["leaf"], persistent="true", distance="7"))
    return n


def _light(lot: _Lot, p: dict, seed: int) -> int:
    """Flush froglights IN the dig floor - the island's own idiom, and Jack's own.

    A lamp standing on a working floor is something to walk into; a froglight set in the paving
    is the floor. **REACH IS ONE LESS THAN THE LIGHT** for a flush emitter, because the cell a mob
    stands in is the one above it - which cost `Island Night` twenty-one dark cells to learn.
    """
    dv, du = lot.dv, lot.du
    pit, _ = _pit_mask(p, dv, du)
    step = max(3, int(p.get("light", 11)))
    keep = _reserved(p, dv, du) | _level_mask(p, dv, du)
    n = 0
    for v in range(0, dv, step):
        for u in range(0, du, step):
            if keep[v, u] or not pit[v, u]:
                continue
            if lot.has(v, 1, u):
                continue
            n += int(lot.put(v, 0, u, CAMP["glow"]))
    return n


def _boards(lot: _Lot, p: dict) -> int:
    """The interpretation boards - what a guest is looking at, and what they may do about it.

    **THE POST IS SEATED ON WHATEVER IS ACTUALLY THERE, NEVER AT A COURSE.** Placed at a computed
    y a board floats over a bench or is buried in a bank, and the second of those is silent: the
    sign is refused for having nothing in front of it and the sidecar records one fewer board than
    the config asked for. `fossils._surface` exists for exactly this and this repo has paid for
    the rule on a mane, an ossicone, a tail and a stake.

    FIFTEEN CHARACTERS IS THE LINE - this park has shipped "MINE CART ESCAP", "and prize windo"
    and "ore from the ad" - and `_Lot.sign` refuses a board with nothing behind it rather than
    hanging one in the air, so a refusal is reported rather than assumed away.
    """
    n = 0
    for spec in (p.get("boards") or []):
        v, u = int(spec["v"]), int(spec["u"])
        facing = spec.get("facing", "south")
        dv = {"east": 1, "west": -1}.get(facing, 0)
        du = {"south": 1, "north": -1}.get(facing, 0)
        base = fossils._surface(lot, v, u, cap=lot.c.sy - 4)
        base = 0 if base is None else base + 1
        top = base + int(spec.get("h", 2))
        for k in range(base, top):
            lot.log(v, k, u, CAMP["post"], axis="y")
        lot.put(v, top, u, CAMP["plank"])
        #: the face the board hangs on must be CLEAR, and on a working floor it often is not -
        #: so the near side is tried and the far side taken when the near one is occupied.
        for sgn in (1, -1):
            sv, su = v + dv * sgn, u + du * sgn
            if lot.sign(sv, top, su, facing if sgn > 0 else _flip(facing), spec["lines"]):
                n += 1
                break
    return n


def _flip(facing: str) -> str:
    return {"north": "south", "south": "north", "east": "west", "west": "east"}[facing]


# --------------------------------------------------------------------------- the build


def build(cfg: dict, donors=None) -> Canvas:
    p = {**BONEBED, **(cfg or {})}
    if not p.get("lot"):
        raise ValueError("the bone bed needs its measured lot: lot: [dv, du]")
    dv, du = int(p["lot"][0]), int(p["lot"][1])
    c = Canvas(dv, int(p.get("sy") or 30), du, donors)
    lot = _Lot(c, dv, du, seed=int(p.get("seed", 0)))
    seed = int(p.get("seed", 0))

    h = _field(p, dv, du)

    #: ORDER IS THE WHOLE THING. The mass goes in first and everything after it CUTS or STANDS ON
    #: what the mass gave, so a ramp is a slot through a real wall and a deck is seated on a real
    #: crest. Reversed, the mass fills the slot back in and the audit reports nothing at all -
    #: which is the failure `diggings.py` shipped once and records in its own build order.
    pit, _ = _pit_mask(p, dv, du)
    keep = _reserved(p, dv, du)
    parts = {"mass": _fill(lot, h, pit, seed)}
    parts["floor"] = _floor(lot, p, seed)
    parts["ramps"] = [_ramp(lot, h, s, p, seed) for s in (p.get("ramps") or [])]
    parts["grid"] = _grid(lot, h, pit, p, seed)
    off = keep | _level_mask(p, dv, du)
    parts["spoil"] = sum(_spoil(lot, h, off, s, seed) for s in (p.get("spoil") or []))
    parts["skeletons"] = _skeletons(lot, p, seed)
    parts["skulls"] = _skulls(lot, p)
    parts["jackets"] = sum(_jacket(lot, h, s, seed) for s in (p.get("jackets") or []))
    if p.get("gantry"):
        parts["gantry"] = _gantry(lot, h, p["gantry"], seed)
    if p.get("shelter"):
        parts["shelter"] = _shelter(lot, h, p["shelter"], seed)
    if p.get("gallery"):
        parts["gallery"] = _gallery(lot, h, p["gallery"], seed)
    if p.get("arch"):
        parts["arch"] = _arch(lot, h, p["arch"], seed)
    parts["crates"] = sum(int(lot.put(int(a), 1, int(b), CAMP["crate"], facing="up", open="false"))
                          for a, b in (p.get("crates") or []))
    parts["plant"] = _plant(lot, h, pit, p, seed)
    parts["light"] = _light(lot, p, seed)
    parts["boards"] = _boards(lot, p)

    av, ay, au = (int(x) for x in p["anchor"])
    at_v, at_u = (int(x) for x in (p.get("at") or (0, 0)))
    c.world_origin = (av + at_v, ay, au + at_u)
    c.meta = {
        "kind": "bonebed",
        "lot": [dv, du],
        "at": [at_v, at_u],
        "land": "frontier",
        "facing": "west",
        "profile_axis": "u",
        "signs": lot.signs,
        "refused": lot.refused,
        "parts": parts,
        "contract": (
            "one excavation across two retired building lots: a floor at the park's own plane "
            "with the relief made of SPOIL rather than of a dig list, benched walls stepped by "
            "construction, the park's own V77-79 cross walk kept level and used as the causeway "
            "into it, a timber gallery on the avenue bank that reads the skeleton in plan, and "
            "not one building with a door in it"),
    }
    return c
