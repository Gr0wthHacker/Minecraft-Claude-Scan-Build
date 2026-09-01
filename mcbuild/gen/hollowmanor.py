"""The Hollow: a haunted gothic quarter - a manor, its crypt, a clocktower, a graveyard.

**THE QUARTER IS THE UNIT, NOT THE BUILDING.** The park's Hollow was a palette with nothing in it
big enough to carry the land: `stall`, `booth` and `walkthrough` are all one-storey boxes, and a
zone made of them reads as *"single small structures, some infrastructure and some huts"*, which
is what it was rejected as. What a land needs is a SIGNATURE MASS - one building that dominates
its skyline and gives every smaller piece something to be near. The manor is that mass: three
storeys, a gabled roof with cross-gables, and a corner tower that stands clear above the ridge.

Everything here follows the rule this repo has settled four separate times - on the void tower,
the deck soffit, the sanctum and the casino:

    WHAT MAKES VOXELS READ AS ARCHITECTURE IS REGULARITY AND OPENINGS, NOT DAMAGE.

So the manor is INTACT AND IMPOSING FIRST. It has boarded lights and one missing shutter, and
they are two windows out of thirty - the ruin is a note played over a building that is complete,
never the building itself. The void tower's first attempt was a sheared jagged stub and was
rejected on sight as *"a tossed grouping of vague blocks"*; the second stood full height with a
door, a lintel, glazed slits, a string course, a corbel and a parapet, and read immediately.

**PALETTE BY MEASUREMENT, ACROSS FAMILIES.** Three notes in CLAUDE.md concluded this economy has
no value contrast, and all three had searched inside ONE material family, where a ladder cannot
exist by construction. The Hollow's rungs are real and cheap-or-ok:

    black_wool 21 · blackstone 38 · cracked p.b.brick 40 · p.blackstone_bricks 45
    deepslate_tiles 55 · deepslate_bricks 71 · light_gray_wool 141 · white_wool 236

The walls sit at the dark end, the roof one rung up (55), the trim two (71), and the ONLY bright
things in the whole quarter are the clock face and the headstones - which is exactly what should
draw the eye. `GOTHIC` is checked against `blocks.spendable`, `blocks.available` and
`palette.tier` for every land; nothing here is dirt, nothing falls, nothing is expensive.

**RELIEF IS THE POINT, AND IT IS STAIRS.** The corpus measured this repo placing stairs at a
SEVENTH the rate outside builders do, and flat walls are its known weakness. Every string course
here is a proud ring with an upside-down stair corbel under it, every roof slope is stairs, every
window head has a springer, every cornice is a run - and a run shorter than `min_run` gets
NOTHING, because the deck soffit drew a coffer grid per cell and produced 215 runs of which 184
were one or two cells: confetti in the loudest block available.

GEOMETRY, identical to `gen/park.py` and stated once because getting it wrong is invisible in
every render:

    at       the structure's FRONT-LEFT floor corner, in world coordinates
    facing   the direction the FRONT looks out
    i        runs along the frontage;  d runs from the front INTO the building;  h is up

    at(i, d, h) = (x - dx*d + sx*i,  y + h,  z - dz*d + sz*i)

**RULE 11: THE PLOT IS VOID.** Every kind lays its own pad at h=-1 and its own plinth; nothing
here assumes terrain, and nothing is raised without something carrying it to the ground.

**SCALE: THE MINIMUMS, MEASURED RATHER THAN INTENDED.** Each kind clamps its `width` / `depth` /
`height` to its own floor and there is no way to ask for less - a manor at `width: 20` is a manor
at 32. The floor is not the footprint, though, and the difference is what a siting search has to
reserve: the pads, the porch steps, the plinth skirt and the engaged tower all stand OUTSIDE the
nominal box. The right-hand columns are the built envelope at the clamped minimum, in the
structure's own axes (i along the frontage, d into the building, h up from the pad at -1):

    kind         clamps to           envelope  i  x   d  x   h     cells   default
    manor        width 32, depth 24            42  x  35  x  52   11,139   as clamped
    ossuary      width 15, depth 17            23  x  25  x  10    2,265   as clamped
    crypt        width  9, depth 11            17  x  19  x  15    1,586   as clamped
    clocktower   width  9 (odd)                17  x  17  x  49    2,463   as clamped
    graveyard    width 21, depth 17            23  x  19  x  13      714   25 x 21 -> 27 x 23
    deadtree     height 9                      13  x  13  x  11      228   height 15 -> h 17
    irongate     width 15                      19  x   7  x  12      228   width 23 -> i 27

The manor is 42 across where its walls are 32, and 35 deep where its rooms are 24: eight of those
courses are the porch and its approach, in front of `d=0`, and six are the tower engaged past the
right-hand wall. Siting it on 32x24 puts the front steps and the tower over the edge of whatever
was measured for it. The clocktower is the tall one and the manor the wide one; nothing here is
small, which is the point - the quarter's whole argument is that a land needs one signature mass.

**THE MANOR GREW SEVEN COURSES DOWNWARD AND NOT AN INCH SIDEWAYS**, which is a siting fact and is
why it is recorded here rather than left to be discovered: its three set pieces hide their wiring
at h = -1 and at CELL_FLOOR - 1, and each wire cell carries its own floor a course below that. It
now occupies h = -8 .. 43 against -6 .. 43. Nothing above ground moved.

## THINGS TO DO IN IT

The quarter was rejected a second time - *"it feels like it's just an abandoned town vs a theme
park"* - and the measurement behind that is blunt: THREE BUTTONS AND THREE SCULK SENSORS in a
zone of a dozen structures, against 215 cells of redstone wire. Wiring with almost nothing for a
player to touch. Two answers, and they are deliberately different mechanisms so that a visitor
who has met both knows the difference without being told:

    `_scare`     A MONOSTABLE. Fires once and resets, however long the trigger is held. Three of
                 them along the manor's walkthrough, on three different inputs.
    `_ossuary`   A COMBINATIONAL AND. Three shroud-levers, and the vault is open only WHILE all
                 three are up. It has no memory at all: let one go and it shuts.

Neither invents a circuit. The first is `circuits.pulse`, the second is `arcade.and_gate`, and
both have contracts asserted by simulation in `tests/test_hollow_play.py` - including that they
RESET, which is the half of a set piece a render cannot show and a block count cannot count.
"""
from __future__ import annotations

from .. import blocks
from .canvas import Canvas, hash01
from .vertical import Ctx, World
from .park import LANDS, SIGN_WIDTH, _STEP, _Frame, _sign

_NAME = {(0, -1): "north", (0, 1): "south", (-1, 0): "west", (1, 0): "east"}


# ---------------------------------------------------------------------------- palette

# THE EXTRAS, one table per land. Every entry was checked with `blocks.spendable`,
# `blocks.available` and `palette.tier` before it was written down; all are cheap or ok, none is
# dirt (currency on this server), none falls, and the only glass is `glass_pane` - plain `glass`,
# every stained pane and all of quartz/concrete/terracotta are expensive here.
#
# THE ROOF IS SLATE IN ALL THREE LANDS, deliberately. A manor's roof is the one surface read from
# every angle and from above, and `deepslate_tiles` (55) is the one cheap-or-ok material that
# sits a clean rung over black_wool (21) and under deepslate_bricks (71) - so the roof, the walls
# and the trim are three distinguishable values whatever land the manor is built in.
GOTHIC = {
    "hollow": {
        "stone": "polished_blackstone_bricks",      # 45 - the storey-0 field
        "dressed": "chiseled_polished_blackstone",  # 51 - jambs, caps, mullions
        "rough": "cracked_polished_blackstone_bricks",   # 40 - the weathering variant
        "roof": "deepslate_tiles", "roof_stair": "deepslate_tile_stairs",
        "roof_slab": "deepslate_tile_slab", "roof_alt": "deepslate_bricks",
        "timber": "dark_oak_planks", "timber_stair": "dark_oak_stairs",
        "timber_slab": "dark_oak_slab", "log": "dark_oak_log",
        "trapdoor": "dark_oak_trapdoor", "door": "dark_oak_door",
        "railwall": "deepslate_brick_wall", "urn": "chiseled_deepslate",
        "pale": "light_gray_wool", "bright": "white_wool", "dark": "black_wool",
        "torch": "soul_torch",
        "stones": ["stone_bricks", "cracked_stone_bricks", "mossy_stone_bricks",
                   "chiseled_stone_bricks", "andesite", "polished_andesite",
                   "smooth_basalt", "light_gray_wool", "bone_block", "deepslate_tiles"],
    },
    "midway": {
        "stone": "stone_bricks", "dressed": "chiseled_stone_bricks",
        "rough": "cracked_stone_bricks",
        "roof": "deepslate_tiles", "roof_stair": "deepslate_tile_stairs",
        "roof_slab": "deepslate_tile_slab", "roof_alt": "deepslate_bricks",
        "timber": "oak_planks", "timber_stair": "oak_stairs", "timber_slab": "oak_slab",
        "log": "oak_log", "trapdoor": "oak_trapdoor", "door": "oak_door",
        "railwall": "stone_brick_wall", "urn": "chiseled_stone_bricks",
        "pale": "light_gray_wool", "bright": "white_wool", "dark": "black_wool",
        "torch": "torch",
        "stones": ["stone_bricks", "cracked_stone_bricks", "mossy_stone_bricks",
                   "chiseled_stone_bricks", "andesite", "polished_andesite",
                   "smooth_basalt", "light_gray_wool", "bone_block", "deepslate_tiles"],
    },
    "frontier": {
        "stone": "cobblestone", "dressed": "chiseled_stone_bricks",
        "rough": "mossy_cobblestone",
        "roof": "deepslate_tiles", "roof_stair": "deepslate_tile_stairs",
        "roof_slab": "deepslate_tile_slab", "roof_alt": "deepslate_bricks",
        "timber": "spruce_planks", "timber_stair": "spruce_stairs", "timber_slab": "spruce_slab",
        "log": "spruce_log", "trapdoor": "spruce_trapdoor", "door": "spruce_door",
        "railwall": "cobblestone_wall", "urn": "chiseled_stone_bricks",
        "pale": "light_gray_wool", "bright": "white_wool", "dark": "black_wool",
        "torch": "torch",
        "stones": ["stone_bricks", "cracked_stone_bricks", "mossy_stone_bricks",
                   "chiseled_stone_bricks", "andesite", "polished_andesite",
                   "smooth_basalt", "light_gray_wool", "bone_block", "deepslate_tiles"],
    },
}

HOLLOW = {
    "under": None,
    "at": None,                 # world (x, y, z): the FRONT-LEFT floor corner
    "kind": "manor",
    "facing": "east",
    "land": "hollow",
    "title": None,
    "lines": None,
    "width": None,              # each kind clamps to its own minimum
    "depth": None,
    "height": None,
    "min_run": 3,               # a trim course shorter than this is not drawn at all
    "sign": True,
}


# ---------------------------------------------------------------------------- helpers

def _ax(f) -> dict:
    """The four world directions in the structure's own terms.

    `ip` is the direction of increasing i, which is the SIDE vector - `at` steps by (sx, sz) per
    i and by (-dx, -dz) per d, so `back` is the direction of increasing d.
    """
    return {"fwd": f.facing, "back": f.back,
            "ip": _NAME[(f.sx, f.sz)], "im": _NAME[(-f.sx, -f.sz)]}


def _pane(a: str, b: str) -> dict:
    """Connection state for a pane or a bar run.

    A `glass_pane` with every side false renders as a lone POST rather than as glazing - the
    campanile's own note - so the run's axis is always stated, never left to default.
    """
    p = {"north": "false", "south": "false", "east": "false", "west": "false",
         "waterlogged": "false"}
    p[a] = "true"
    p[b] = "true"
    return p


def _ground(w, f, i0, i1, d0, d1, block, h=-1, alt=None, mix=0.0, holes=()):
    """The pad. RULE 11: a skyblock plot is VOID, so every structure brings its own floor.

    `holes` is what a STAIR DOWN needs and nothing else could give it. A World is sparse, so an
    empty cell is air - but the pad is laid first and covers the whole footprint, so a flight
    that descends through it has to be left out of the pad rather than carved out afterwards.
    `w.put` overwrites, so a later carve would have to DELETE, and a generator that deletes cells
    it has already placed is one whose output depends on the order two unrelated passes ran in.
    """
    holes = set(holes)
    n = 0
    for i in range(i0, i1 + 1):
        for d in range(d0, d1 + 1):
            if (i, d) in holes:
                continue
            x, y, z = f.at(i, d, h)
            # THE WEATHERING HASH IS ON THE CELL, never on the course - hashed on the course a
            # whole row comes out one material and the surface is horizontal stripes, which the
            # deck soffit shipped once.
            w.put(x, y, z, alt if (alt and hash01(x, y, z) < mix) else block)
            n += 1
    return n


def _fill(w, f, i0, i1, d0, d1, h, block, holes=()):
    holes = set(holes)
    n = 0
    for i in range(i0, i1 + 1):
        for d in range(d0, d1 + 1):
            if (i, d) in holes:
                continue
            w.put(*f.at(i, d, h), block)
            n += 1
    return n


def _weathered(w, f, i, d, h, main, alt, p=0.12):
    x, y, z = f.at(i, d, h)
    w.put(x, y, z, alt if hash01(x, y, z) < p else main)


def _box(w, f, i0, i1, d0, d1, h0, h1, wall, corner=None, holes=(), alt=None, mix=0.12):
    """Four walls with corner pilasters. THE OPENINGS ARE LEFT EMPTY BY THE LOOP.

    Building the ring first and cutting the holes afterwards repaints cells that already exist -
    the void tower's crenellations shipped as a plain drum for exactly that reason and nothing
    about the code looked wrong.
    """
    holes = set(holes)
    n = 0
    for i in range(i0, i1 + 1):
        for d in range(d0, d1 + 1):
            if not (i in (i0, i1) or d in (d0, d1)):
                continue
            is_corner = i in (i0, i1) and d in (d0, d1)
            for h in range(h0, h1 + 1):
                if (i, d, h) in holes:
                    continue
                if is_corner and corner:
                    w.put(*f.at(i, d, h), corner)
                else:
                    _weathered(w, f, i, d, h, wall, alt or wall, mix if alt else 0.0)
                n += 1
    return n


def _run(w, f, cells, block, facing, half="top", min_run=3):
    """A stair course, laid only where it makes a RUN.

    `min_run` is the deck soffit's gate: a course of one or two cells is not a line, it is
    confetti, and the fix there was to draw nothing at all rather than to draw it in a quieter
    block. The gate runs on what is PLACED, so a caller cannot filter afterwards and ship three
    scattered stairs out of a five-cell run.
    """
    cells = list(cells)
    if len(cells) < min_run:
        return 0
    for (i, d, h) in cells:
        w.put(*f.at(i, d, h), block, facing=facing, half=half, shape="straight",
              waterlogged="false")
    return len(cells)


def _proud_ring(w, f, i0, i1, d0, d1, h, block):
    """A string course or cornice standing one cell PROUD of the wall it belongs to.

    Blackstone cannot draw a value line on itself - the family sits within 12 RGB - so every line
    in this quarter is GEOMETRY as well as tone: it is the paler trim AND it projects.
    """
    n = 0
    for i in range(i0 - 1, i1 + 2):
        w.put(*f.at(i, d0 - 1, h), block)
        w.put(*f.at(i, d1 + 1, h), block)
        n += 2
    for d in range(d0, d1 + 1):
        w.put(*f.at(i0 - 1, d, h), block)
        w.put(*f.at(i1 + 1, d, h), block)
        n += 2
    return n


def _corbel_ring(w, f, i0, i1, d0, d1, h, block, min_run=3):
    """The upside-down stair course UNDER a proud ring: what turns a ledge into a moulding.

    Each stair's tall side (`facing`) points at the wall it grows from, so the taper reads
    outward. Our renderer draws both directions identically, which is why this is computed from
    the geometry and never eyeballed.
    """
    a = _ax(f)
    laid = 0
    laid += _run(w, f, [(i, d0 - 1, h) for i in range(i0 - 1, i1 + 2)], block, a["back"],
                 min_run=min_run)
    laid += _run(w, f, [(i, d1 + 1, h) for i in range(i0 - 1, i1 + 2)], block, a["fwd"],
                 min_run=min_run)
    laid += _run(w, f, [(i0 - 1, d, h) for d in range(d0, d1 + 1)], block, a["ip"],
                 min_run=min_run)
    laid += _run(w, f, [(i1 + 1, d, h) for d in range(d0, d1 + 1)], block, a["im"],
                 min_run=min_run)
    return laid


def _crenels(w, f, i0, i1, d0, d1, h, block):
    """Merlons on a course the wall loop LEFT EMPTY, in the DARK trim.

    From directly above a merlon in the parapet's own colour is invisible - a plan view sees only
    the topmost cell - so the crown is the one place the palette steps DOWN rather than up.
    """
    n = 0
    for i in range(i0, i1 + 1):
        for d in range(d0, d1 + 1):
            if not (i in (i0, i1) or d in (d0, d1)):
                continue
            if (i + d) % 2:
                continue
            w.put(*f.at(i, d, h), block)
            n += 1
    return n


def _slope(w, f, field, base, block, stair, ridge_block, alt=None):
    """Place a roof from a height field, and GUARANTEE 6-CONNECTIVITY.

    A stair at (d, h) and the next one at (d+1, h+1) are DIAGONAL neighbours and are not one
    piece - this repo has lost ear tips, ossicones and a whole mane to exactly that. So every
    column is filled from its own height DOWN TO the lowest of its four neighbours (never higher
    than h-1), which makes every pair of adjacent columns share at least one level by
    construction: if the neighbour is taller it shares this column's top, and if it is shorter
    this column reaches down past it.

    `field` maps (i, d) -> (height, facing, is_ridge). Returns the lowest course used per column
    so the caller can fill a gable end under it.
    """
    lo_of = {}
    for (i, d), (h, dirn, ridge) in field.items():
        lo = h - 1
        for nb in ((i + 1, d), (i - 1, d), (i, d + 1), (i, d - 1)):
            if nb in field:
                lo = min(lo, field[nb][0])
        lo = max(lo, base)
        lo_of[(i, d)] = lo
        for y in range(lo, h):
            _weathered(w, f, i, d, y, block, alt or block, 0.10 if alt else 0.0)
        if ridge:
            w.put(*f.at(i, d, h), ridge_block)
        else:
            w.put(*f.at(i, d, h), stair, facing=dirn, half="bottom", shape="straight",
                  waterlogged="false")
    return lo_of


def _lancet(w, f, kit, pal, i0, d, h0, wall_axis, glaze, boarded=False, shutter=None):
    """One tall arched window: two lights, a mullion between them, an arched head.

    Three cells wide and four courses tall, occupying (i0..i0+2, h0..h0+3):

        h0+3   glass glass glass      the head, sprung off a stair either side
        h0+2   glass  MULL  glass
        h0+1   glass  MULL  glass
        h0     glass  MULL  glass     the sill course is the wall below

    The springers at i0-1 and i0+3 are upside-down stairs cut INTO the wall, which is what makes
    the head read as an arch rather than as a square hole with glass in it.
    """
    a = _ax(f)
    for k in range(3):
        for r in range(h0, h0 + 4):
            if k == 1 and r < h0 + 3:
                w.put(*f.at(i0 + k, d, r), kit["dressed"])          # the mullion
            elif boarded:
                w.put(*f.at(i0 + k, d, r), kit["timber"])
            else:
                w.put(*f.at(i0 + k, d, r), glaze, **_pane(*wall_axis))
    w.put(*f.at(i0 - 1, d, h0 + 3), kit["roof_stair"], facing=a["ip"], half="top",
          shape="straight", waterlogged="false")
    w.put(*f.at(i0 + 3, d, h0 + 3), kit["roof_stair"], facing=a["im"], half="top",
          shape="straight", waterlogged="false")
    if shutter is not None:
        # ONE SHUTTER, NOT TWO. A lopsided pair is a note; a missing pair is damage, and damage
        # does not read as architecture. `shutter` is the outward d of the wall's face.
        for r in (h0 + 1, h0 + 2):
            w.put(*f.at(i0 - 1, shutter, r), kit["trapdoor"], facing=f.facing, half="bottom",
                  open="true", powered="false", waterlogged="false")
    if boarded and shutter is not None:
        for r in (h0 + 1, h0 + 3):
            for k in (0, 2):
                w.put(*f.at(i0 + k, shutter, r), kit["trapdoor"], facing=f.facing,
                      half="bottom", open="true", powered="false", waterlogged="false")


def _urn(w, f, kit, pal, i, d, h):
    """A funerary urn: a plinth, a waisted baluster, a bowl and a cap. Four cells, and it is the
    difference between a mausoleum and a shed."""
    w.put(*f.at(i, d, h), kit["dressed"])
    w.put(*f.at(i, d, h + 1), kit["railwall"], up="true", north="none", south="none",
          east="none", west="none", waterlogged="false")
    w.put(*f.at(i, d, h + 2), kit["urn"])
    w.put(*f.at(i, d, h + 3), kit["roof_slab"], type="bottom", waterlogged="false")


def _lamp_post(w, f, kit, pal, i, d, h, tall=2):
    """A standing lamp. A LANTERN ON TOP OF A POST STANDS ON IT - written `hanging=true` it is
    looking for a block ABOVE it, finds open sky, and hangs from nothing."""
    for k in range(tall):
        w.put(*f.at(i, d, h + k), kit["dressed"])
    w.put(*f.at(i, d, h + tall), pal["light"], hanging="false", waterlogged="false")


def _hang(w, f, pal, i, d, h, above):
    """A hanging lantern, and the FULL block it hangs from GUARANTEED.

    A lamp under a slab cap reads as 'hanging from air' in the audit - the lowland's own note -
    because a slab is not a full block, and this is the one rule about a lantern that a render
    cannot show: a lantern hanging off nothing draws exactly like a lantern hanging off a beam.

    **IT ASKS BEFORE IT WRITES.** Written as a bare `put` of `above` it was a helper nobody could
    use over a finished surface - it would repaint the string course or the floor it hangs from,
    in whatever block the caller happened to name. So it keeps a full block that is already there
    and supplies one only where there is none, which is what let all four hanging lanterns in this
    file - two on the porch, the facade run, the crypt's tomb - stop hand-rolling the same three
    lines and route through here instead. The invariant is now structural rather than incidental.
    """
    x, y, z = f.at(i, d, h + 1)
    if not blocks.is_full_cube(w.name(x, y, z) or "air"):
        w.put(x, y, z, above)
    w.put(*f.at(i, d, h), pal["light"], hanging="true", waterlogged="false")


# ---------------------------------------------------------------------------- circulation
#
# THE THREE HELPERS BELOW ARE WHY THIS QUARTER HAS A ROUTE AT ALL, and they exist as helpers
# rather than as three hand-rolled flights because every one of them is a place a build can be
# legal, connected, affordable and NOT WALKABLE - which is the one failure nothing in this
# pipeline has ever looked for. A flight whose treads rise two courses at a time audits clean and
# renders identically to one that rises one; a stair under a floor plane nobody holed audits
# clean and dead-ends at a plank ceiling. `tests/test_hollow_flow.py` floods from the door.
#
# THE STAIR CONVENTION, which our renderer draws identically either way and which is therefore
# asserted rather than eyeballed: A FLIGHT THAT ASCENDS TOWARD D HAS EVERY TREAD `facing=D`,
# `half=bottom`. Built the other way the risers face into the descent and you cannot walk up it.


def _flight(w, f, kit, pal, i0, i1, d_from, h_from, steps, down=False, step=1,
            support=None, floor_to=None):
    """One straight flight along d, ONE COURSE PER CELL, with the stringer under it.

    A player standing on a solid cell at height `h` occupies `h+1`; a tread at `h+1` is therefore
    one step up and a tread at `h-1` one step down. So `h_from` is the WALKING level at the head
    of the flight and the arithmetic below is stated once here rather than four times at the
    call sites, where it was got wrong twice while this was being written.

    Returns (d_landing, h_landing) - the cell the flight delivers you to and the level you walk
    at there - so a caller never has to re-derive where its own stair came out.

    `support` fills every column under a tread down to `floor_to`, which is what makes a
    descending flight into open ground stand on something instead of being six stairs in a shaft.
    """
    # THE TREAD'S FACING IS DERIVED, NEVER TYPED. Increasing d runs INTO the building, which is
    # `f.back`; so a flight walked with `step` while going `down` ascends along `-step`, and the
    # convention names the tread after the direction of ASCENT.
    up_along_d = (-step) if down else step
    face = f.back if up_along_d > 0 else f.facing
    treads = []
    d, h = d_from, h_from
    for _k in range(steps):
        d += step
        h += -1 if down else 1
        # the tread block sits one course BELOW the level you walk at when standing on it
        for i in range(i0, i1 + 1):
            w.put(*f.at(i, d, h - 1), kit["roof_stair"], facing=face,
                  half="bottom", shape="straight", waterlogged="false")
            if support is not None and floor_to is not None:
                for y in range(floor_to, h - 1):
                    w.put(*f.at(i, d, y), support)
        treads.append((d, h))
    return (d, h)


def _undercroft(w, f, kit, pal, i0, i1, d0, d1, floor_h, walk_h, ceil_h, shaft=()):
    """A lit vault under a building: a floor, a wall ring, niches, and lanterns on the ceiling.

    `ceil_h` is the course the vault's LID occupies and it is normally somebody else's - the
    manor's own pad - so it is never re-laid here, only hung from. `shaft` names the (i, d)
    columns the stair comes down, which the wall ring must not close off.

    THE HEADROOM IS A CONTRACT, not a consequence: `walk_h` to `ceil_h - 1` must be at least
    three courses or the vault is a crawlspace that the walk test correctly refuses to enter.
    """
    shaft = set(shaft)
    niches, lamps = 0, 0
    # THE NICHES ARE DECIDED BEFORE THE RING IS DRAWN, never carved out of it afterwards. `put`
    # overwrites and cannot remove, so a recess cut after the wall exists would have to DELETE
    # cells - and the void tower shipped a plain drum once for exactly this: it built the full
    # ring and then "alternated" merlons over cells that were already there.
    recess = set()
    for d in range(d0 + 1, d1, 3):
        recess |= {(i0 - 1, d), (i1 + 1, d)}
    for i in range(i0 - 1, i1 + 2):
        for d in range(d0 - 1, d1 + 2):
            w.put(*f.at(i, d, floor_h), kit["stone"])
            if not (i in (i0 - 1, i1 + 1) or d in (d0 - 1, d1 + 1)) or (i, d) in shaft:
                continue
            for h in range(walk_h, ceil_h):
                if (i, d) in recess and h in (walk_h, walk_h + 1):
                    continue                       # left EMPTY by the ring loop - the niche
                _weathered(w, f, i, d, h, kit["stone"], kit["rough"], 0.18)
    for (i, d) in sorted(recess):
        out = -1 if i == i0 - 1 else 1
        for h in range(walk_h - 1, ceil_h):        # the niche's own back, floor and head
            _weathered(w, f, i + out, d, h, kit["stone"], kit["rough"], 0.2)
        w.put(*f.at(i, d, walk_h), "skeleton_skull", rotation="0")
        niches += 1
    for i in range(i0 + 2, i1, 5):
        for d in range(d0 + 2, d1, 5):
            if (i, d) in shaft:
                continue
            _hang(w, f, pal, i, d, ceil_h - 1, kit["stone"])
            lamps += 1
    return niches, lamps


def _cobwebs(w, f, cells):
    """Cobwebs, and every one of them ANCHORED to a cell that is already built.

    A cobweb hanging in open interior air with nothing beside it is a floating singleton and its
    own component - the chapel's own note, and the same 6-connectivity trap that broke the
    leopard's ear tips. It is also the one prop here a player walks THROUGH, so it may never be
    placed in a cell the route needs: every call site passes ceiling corners, not doorways.
    """
    n = 0
    for (i, d, h) in cells:
        x, y, z = f.at(i, d, h)
        if w.has(x, y, z):
            continue
        if any(w.has(*f.at(i + a, d + b, h + c))
               for (a, b, c) in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0),
                                 (0, 0, 1), (0, 0, -1))):
            w.put(x, y, z, "cobweb")
            n += 1
    return n


def _candle(w, f, i, d, h, count=2):
    """A candle needs a full block under it, so the support is checked and never assumed."""
    x, y, z = f.at(i, d, h - 1)
    if not blocks.is_full_cube(w.name(x, y, z) or "air"):
        return False
    if w.has(*f.at(i, d, h)):
        return False
    w.put(*f.at(i, d, h), "candle", candles=str(count), lit="true", waterlogged="false")
    return True


# ---------------------------------------------------------------------------- set pieces

def _put_spec(w, pos, spec: str) -> None:
    """Place a `"name[k=v,...]"` string. Every circuit module in this repo speaks that dialect."""
    name, _, rest = spec.partition("[")
    props = {}
    if rest:
        for kv in rest.rstrip("]").split(","):
            k, _, v = kv.partition("=")
            props[k] = v
    w.put(pos[0], pos[1], pos[2], name, **props)


# The three set-piece outputs, and what each one is FOR. All three are full cubes, which is the
# property that lets them sit IN a floor a player walks over: at rest they are the floor.
_VENTS = {
    # A bare piston head punching up out of the boards under your feet. It has nothing to push,
    # deliberately: a sticky piston with a block on it would leave that block standing in the
    # walkway at rest, which is an obstacle rather than a scare.
    "piston": ("piston", {"facing": "up", "extended": "false"}),
    # THE ONLY SWITCHABLE LIGHT IN THE GAME, and `expensive` on this economy - so it is counted
    # into `budget` and declared, never smuggled. In a black-walled quarter it is also the single
    # strongest piece of feedback available: the floor lights under you.
    "lamp": ("redstone_lamp", {"lit": "false"}),
    # Something comes out of the floor. WHAT it dispenses is an entity and therefore unverifiable
    # here, so the loading instruction travels in `stock` exactly as the randomiser's mix does.
    "dispenser": ("dispenser", {"facing": "up", "triggered": "false"}),
}

# What a set piece can be TRIGGERED by, and the block that makes each one obvious. All three are
# `face=floor` on their own accent pad, and all three strongly power the block BENEATH them -
# which is where the machine takes its signal from, and the reason `circuit._sources` had to stop
# reading a pressure plate as if it were mounted on a wall.
#
# **A PLATE HAS NO `facing`, AND A LEVER AND A BUTTON DO.** Handing every trigger the structure's
# own facing put an illegal property on the plate - which `blocks.validate` catches here and
# Litematica would simply have refused in game an hour later. So the state is a property of the
# trigger, stated once, rather than something the call site adds.
_TRIGGERS = {
    "plate": ("stone_pressure_plate", {"powered": "false"}, False),
    "lever": ("lever", {"face": "floor", "powered": "false"}, True),
    "button": ("stone_button", {"face": "floor", "powered": "false"}, True),
}


def _scare(w, f, kit, pal, ti, d, h, *, kind="plate", vents=("piston", "lamp", "dispenser"),
           length=2, side=1):
    """A SET PIECE: a visible trigger, a monostable, and things that move ONCE and then reset.

    **A HAUNTED HOUSE IS A SEQUENCE OF EVENTS, AND THE MANOR HAD NONE.** It was 10,362 blocks of
    correct gothic architecture with a walkthrough drawn through it, and the verdict on the zone
    was still that it reads as an abandoned town: three buttons and three sculk sensors in a
    quarter of a dozen structures. A route is not an activity. What makes a walk into a ride is
    that the building DOES something when you reach a particular cell of it.

    A scare is a MONOSTABLE - it fires once and resets - and that is not a flourish, it is the
    contract. Wired straight through, a plate held down by a player standing on it holds the
    piston out and the lamp on for as long as they stand there, which is a stuck prop rather than
    a scare, and a dispenser wired the same way empties itself. `circuits.pulse` is the AND-NOT
    that turns any input, held or not, into a fixed edge; its own docstring records that the first
    version of it was a bare repeater, that a repeater delays BOTH edges, and that a held lever
    therefore drove a casino payout for 21 ticks out of 24. Every one of those failures is
    invisible in a render and none of them is a placement problem.

    THE GEOMETRY, three courses and no climbing anywhere:

        h + 2   the trigger        a plate, a lever or a button, `face=floor`
        h + 1   the trigger's PAD, and the vents - all full cubes, so the walkway is unbroken
        h       the machine        pulse -> boost -> a dust spine, running along +i
        h - 1   a floor for it

    **THE COUPLING IS THE ONE PART THAT CANNOT BE DONE ANY OTHER WAY.** A floor-mounted trigger
    strongly powers the block directly beneath it, and a strongly powered opaque block passes 15
    to any wire touching it - so the dust under the pad is fed and nothing else on the course is.
    Anything else would need the signal to CLIMB out of the machine's course into the floor, and
    dust only climbs the side of a block whose own lid is not opaque: under a floor, it never is.
    That is the fault `circuits.climb` exists for and the reason it is not needed here.

    Laid LAST, and it overwrites. The pad and the plinth are continuous surfaces poured before it;
    a machine that yielded to them would be swallowed cell by cell, which is `casino._link`'s
    composition bug and the one the seance shipped once with a dropper wired to nothing.

    CONTRACT: nothing is powered at rest; the trigger fires every vent exactly once; a trigger
    HELD DOWN fires them exactly once and they go dark again; releasing and triggering again
    fires them again.
    """
    from . import circuits

    a = _ax(f)
    ip = a["ip"]
    vents = [v for v in vents if v in _VENTS]
    tri = f.at(ti, d, h + 2)
    pad = f.at(ti, d, h + 1)

    laid = {}
    pul = circuits.pulse(f.at(ti + 1, d, h), length=length, facing=ip, side=side)
    amp = circuits.boost(f.at(ti + 6, d, h), facing=ip)
    laid.update(pul["cells"])
    laid.update(amp["cells"])
    # THE ENDS OF A MODULE ARE ADDRESSES, NOT CELLS. `pulse["in"]` and `boost["in"]` say where a
    # signal must ARRIVE and neither module emits a block there; left alone each is a one-cell gap
    # that the chain dies in, and every block of it is correct.
    laid[tuple(pul["in"])] = "redstone_wire"          # ...directly under the trigger's own pad
    laid[tuple(amp["in"])] = "redstone_wire"          # ...bridging the pulse to the boost
    spine = [f.at(ti + 7 + k, d, h) for k in range(max(1, len(vents)))]
    for c in spine:
        laid[c] = "redstone_wire"

    for pos, spec in laid.items():
        _put_spec(w, pos, spec)
    for pos in laid:
        if not w.has(pos[0], pos[1] - 1, pos[2]):
            w.put(pos[0], pos[1] - 1, pos[2], kit["stone"])

    made = {}
    for k, name in enumerate(vents):
        block, props = _VENTS[name]
        cell = (spine[k][0], spine[k][1] + 1, spine[k][2])
        w.put(cell[0], cell[1], cell[2], block, **props)
        made.setdefault(name, []).append(list(cell))

    w.put(*pad, kit["dressed"])
    block, props, aimed = _TRIGGERS[kind]
    w.put(tri[0], tri[1], tri[2], block, **(dict(props, facing=f.facing) if aimed else props))
    return {"trigger": list(tri), "kind": kind, "pad": list(pad),
            "vents": made, "cells": len(laid) + len(vents) + 2,
            "lamps": len(made.get("lamp", [])),
            "dispensers": [list(c) for c in made.get("dispenser", [])]}


# ---------------------------------------------------------------------------- the manor

def _manor(w: World, p: dict, ctx) -> dict:
    """THE SIGNATURE MASS, AND A WALKTHROUGH THROUGH IT.

    It is built in the order a mason would: pad, plinth, walls, floors, string courses, cornice,
    roof, then the entrance bay, the tower and the chimneys OVER the top of them - so the bay
    interrupts the string course exactly as a projecting bay does in stone, and the turret grows
    THROUGH the gable end rather than standing beside it.

    **AND THEN IT WAS 10,362 BLOCKS OF NOTHING TO DO.** The verdict on the shipped Hollow was
    that it "serves low function and feels confusing" - you arrive, and there is nothing to do
    and no idea where to go. The manor is the zone's headline and it was a facade with a ladder
    in the corner: three floors, one vertical link, no exit, no set pieces and no route. The
    building is unchanged above the cornice; everything added here is CIRCULATION.

        front door  ->  THE HALL       ground, front half, hearth and candles
                    ->  grand stair    five treads up the left wall
                    ->  THE LIBRARY    first floor, front half, barrels and lecterns
                    ->  partition door first floor, into the back half
                    ->  back stair     five treads down the right wall
                    ->  THE BACK HALL  ground, back half
                    ->  cellar stair   six treads down, through the plinth and the pad
                    ->  THE CELLAR     a lit vault of niches under the back half - a DEAD END
                    ->  back door      out into the graveyard, on the far side from the porch

    A visitor therefore enters at one face and leaves at the other, which is what makes it a
    walkthrough and not a room. **THE ROUTE IS ASSERTED BY FLOOD FILL FROM THE DOOR**, because
    every one of the four ways it can be wrong - a flight rising two courses at a time, a floor
    plane nobody holed over a stair, a doorway two cells wide in a wall three cells thick, a
    cellar with a ceiling one course over its floor - is legal, connected, affordable, and
    renders identically to the version that works. `meta["route"]` carries the waypoints the
    test walks between, so the contract and the check read the same list.
    """
    f = _Frame(p)
    pal = LANDS[p["land"]]
    kit = GOTHIC[p["land"]]
    a = _ax(f)
    mr = int(p["min_run"])

    W = max(32, int(p["width"] or 32))
    D = max(24, int(p["depth"] or 24))
    SH, STOREYS = 5, 3
    F0 = 1                                  # the ground floor walks at h=1, on the plinth top
    TOP = F0 + STOREYS * SH - 1             # 15: the cornice course
    EAVE = TOP + 1                          # 16: the first roof course
    RIDGE = EAVE + (D - 1) // 2

    bw = 7
    bi0 = (W - bw) // 2                     # the entrance bay, centred on the frontage
    bmid = bi0 + bw // 2
    ti0, ti1 = W - 1, W + 5                 # the corner tower, ENGAGED with the right wall
    td0, td1 = -1, 5

    # ---- THE CIRCULATION, decided before anything is laid, because two planes have to be left
    # open for it: the plinth at h=0 and the pad at h=-1 are both continuous surfaces and the
    # cellar stair goes THROUGH them.
    gs_i0, gs_i1, gs_d = 1, 2, 1            # grand stair: up the left wall, front half
    bs_i0, bs_i1, bs_d = W - 3, W - 2, D - 2  # back stair: down the right wall, back half
    cs_i0, cs_i1, cs_d = 4, 5, D // 2 + 1   # cellar stair: down out of the back hall
    CELL_FLOOR, CELL_WALK, CELL_CEIL = -6, -5, -1
    shaft = {(i, d) for i in range(cs_i0, cs_i1 + 1)
             for d in range(cs_d + 1, cs_d + 7)}
    back_door_i = set(range(bmid, bmid + 3))

    # ---- pad and plinth. A stepped plinth is what stops a wall meeting the ground at a line.
    _ground(w, f, -3, W + 2, -8, D + 2, pal["path"], alt=pal["ground"], mix=0.30, holes=shaft)
    _ground(w, f, W - 4, W + 6, -3, 7, pal["path"], alt=pal["ground"], mix=0.30)
    _fill(w, f, -1, W, -4, D, 0, pal["trim"], holes=shaft)
    _fill(w, f, ti0 - 2, ti1 + 1, td0 - 1, td1 + 1, 0, pal["trim"])

    # ---- the walls, storey by storey. THE BASE IS HEAVIER THAN THE UPPER STOREYS, in material
    # as well as in tone: dressed blackstone brick (45) below, black field (21) above, so the
    # building has a plinth storey and is not one flat drum of a single block.
    # A window is a RECORD, and the hole set is derived from it - not written twice. The springer
    # cells (kk = -1 and 3) are holes for ONE course only, because that is the only course a
    # stair is placed in; holed for all four they would be four empty cells in the wall, which
    # audits clean and looks exactly like a window.
    windows = []
    holes = []
    for k in range(STOREYS):
        base = F0 + k * SH
        for i in range(2, W - 4, 5):
            in_bay = bi0 - 1 <= i <= bi0 + bw and k < 2
            in_tower = i >= ti0 - 5
            if not (in_bay or in_tower):
                windows.append((i, 0, base, (a["ip"], a["im"]), -1, False))
            # THE BACK DOOR TAKES PRECEDENCE OVER A BACK WINDOW, and it has to: the back-wall
            # rhythm puts a three-cell light every five columns, so the widest clear gap in it
            # is TWO - a three-cell doorway cannot fit between two windows anywhere on that
            # wall. Left in, the window's own glazing pass would fill the door opening with
            # panes after the wall loop had correctly left it empty, and the walkthrough would
            # dead-end at a window nobody could see was a window.
            if not (k == 0 and set(range(i, i + 3)) & back_door_i):
                windows.append((i, D - 1, base, (a["ip"], a["im"]), D, False))
        # `out` is the cell OUTSIDE this window's own wall, and for a side wall that is an i and
        # not a d. Written as -1/D for all four walls the shutters on the side windows landed in
        # the middle of the third storey, floating: two cells, and a component count found them.
        for dd in range(2, D - 4, 5):
            windows.append((0, dd, base, (a["fwd"], a["back"]), -1, True))
            if dd > 6:                       # the right wall's front half is inside the tower
                windows.append((W - 1, dd, base, (a["fwd"], a["back"]), W, True))
    for (i, dd, base, _axis, _out, side) in windows:
        for kk in range(3):
            for r in range(base, base + 4):
                holes.append((i, dd + kk, r) if side else (i + kk, dd, r))
        for kk in (-1, 3):
            holes.append((i, dd + kk, base + 3) if side else (i + kk, dd, base + 3))
    # the front door: a three-course arched opening, left EMPTY by the wall loop
    for i in range(bmid - 1, bmid + 2):
        for h in range(F0, F0 + 3):
            holes.append((i, 0, h))
    # ...and the BACK door, the walkthrough's exit, on the far wall from the porch
    for i in sorted(back_door_i):
        for h in range(F0, F0 + 3):
            holes.append((i, D - 1, h))

    for k in range(STOREYS):
        base = F0 + k * SH
        field = kit["stone"] if k == 0 else pal["wall"]
        alt = kit["rough"] if k == 0 else kit["stone"]
        _box(w, f, 0, W - 1, 0, D - 1, base, base + SH - 2, field, pal["post"],
             holes=holes, alt=alt)
        # the floor plane's own course is the string course, and is trim all the way round
        _box(w, f, 0, W - 1, 0, D - 1, base + SH - 1, base + SH - 1, pal["trim"], pal["post"])

    # ---- the windows themselves, cut into the walls the loop left open
    for (i, dd, base, axis, out, side) in windows:
        wx, wy, wz = f.at(i, dd, base)
        r = hash01(wx, wy, wz)
        boarded = r < 0.09
        shutter = None
        if 0.09 <= r < 0.17 or boarded:
            shutter = out
        if side:
            # the window runs along d, so it is drawn with i and d exchanged
            for kk in range(3):
                for rr in range(base, base + 4):
                    if kk == 1 and rr < base + 3:
                        w.put(*f.at(i, dd + kk, rr), kit["dressed"])
                    elif boarded:
                        w.put(*f.at(i, dd + kk, rr), kit["timber"])
                    else:
                        w.put(*f.at(i, dd + kk, rr), "glass_pane", **_pane(*axis))
            w.put(*f.at(i, dd - 1, base + 3), kit["roof_stair"], facing=a["back"],
                  half="top", shape="straight", waterlogged="false")
            w.put(*f.at(i, dd + 3, base + 3), kit["roof_stair"], facing=a["fwd"],
                  half="top", shape="straight", waterlogged="false")
            if shutter is not None:
                for rr in (base + 1, base + 2):
                    w.put(*f.at(out, dd - 1, rr), kit["trapdoor"], facing=f.facing,
                          half="bottom", open="true", powered="false", waterlogged="false")
        else:
            _lancet(w, f, kit, pal, i, dd, base, axis, "glass_pane",
                    boarded=boarded, shutter=shutter)

    # ---- floors, a ceiling, partitions and the three flights. AN INTERIOR WITH A ROUTE IN IT.
    #
    # THE HOLES COME FIRST AND THE FLIGHTS SECOND. A floor plane is laid across the whole storey
    # and a stair passing through it needs BOTH the course it lands on and the course over the
    # walker's head left open - so the openings are part of the floor's own definition, never
    # something repainted afterwards. Written the other way round the flight is built, the floor
    # is laid over it, and the manor audits clean with a staircase into a plank ceiling.
    holes_floor = {(2, D - 4), (2, D - 5)}                    # the attic ladder
    holes_first = set(holes_floor)
    holes_first |= {(i, d) for i in range(gs_i0, gs_i1 + 1) for d in range(gs_d + 1, gs_d + 6)}
    holes_first |= {(i, d) for i in range(bs_i0, bs_i1 + 1) for d in range(bs_d - 4, bs_d)}
    _fill(w, f, 1, W - 2, 1, D - 2, F0 + SH - 1, kit["timber"], holes=holes_first)
    _fill(w, f, 1, W - 2, 1, D - 2, F0 + 2 * SH - 1, kit["timber"], holes=holes_floor)
    _fill(w, f, 1, W - 2, 1, D - 2, TOP, kit["timber"])
    for h in range(F0, TOP):
        w.put(*f.at(2, D - 3, h), pal["post"])
        w.put(*f.at(2, D - 4, h), "ladder", facing=f.facing, waterlogged="false")
    for k in range(STOREYS):
        base = F0 + k * SH
        for i in range(1, W - 2):
            if abs(i - W // 2) <= 1:
                continue                       # the doorway between the two halves of the plan
            for r in range(base, base + SH - 1):
                _weathered(w, f, i, D // 2, r, kit["timber"], pal["wall"], 0.10)

    # ---- THE CELLAR, dug before the flight that reaches it, because `_undercroft` lays a floor
    # plane across its whole rectangle and would otherwise bury the bottom tread under it.
    niches, vault_lamps = _undercroft(w, f, kit, pal, gs_i0 + 2, W - 4, cs_d + 1, D - 3,
                                      CELL_FLOOR, CELL_WALK, CELL_CEIL, shaft=shaft)
    # THE SARCOPHAGUS, at the far end, so the cellar has something at the bottom of it. It is a
    # dead end on purpose: a dare with a reason to turn round is better than a loop with nothing
    # in it, and the exit is the back door upstairs.
    for i in range(W // 2 - 1, W // 2 + 2):
        w.put(*f.at(i, D - 5, CELL_WALK), kit["dressed"])
        w.put(*f.at(i, D - 5, CELL_WALK + 1), kit["roof_slab"], type="bottom",
              waterlogged="false")

    # ---- the three flights
    gs_land = _flight(w, f, kit, pal, gs_i0, gs_i1, gs_d, F0, 5,
                      support=kit["stone"], floor_to=F0)
    bs_land = _flight(w, f, kit, pal, bs_i0, bs_i1, bs_d, F0 + SH, 4, down=True, step=-1,
                      support=kit["stone"], floor_to=F0)
    cs_land = _flight(w, f, kit, pal, cs_i0, cs_i1, cs_d, F0, 6, down=True,
                      support=kit["stone"], floor_to=CELL_FLOOR)

    # A BALUSTRADE ROUND EVERY OPENING, and every post of it standing on a real floor cell. A
    # stairwell in a plank floor with no rail is a hole you walk into in the dark, and a rail
    # placed at the tread's own level is a rail in mid-air - so both runs are laid on the floor
    # plane beside the opening, never over the flight.
    rails = 0
    for d in range(gs_d + 1, gs_d + 7):
        for (i, h) in ((gs_i1 + 1, F0 + SH),):
            if w.has(*f.at(i, d, h - 1)) and not w.has(*f.at(i, d, h)):
                w.put(*f.at(i, d, h), pal["fence"], north="false", south="false",
                      east="false", west="false", waterlogged="false")
                rails += 1
    for d in range(cs_d + 1, cs_d + 7):
        for i in (cs_i0 - 1, cs_i1 + 1):
            if w.has(*f.at(i, d, F0 - 1)) and not w.has(*f.at(i, d, F0)):
                w.put(*f.at(i, d, F0), pal["fence"], north="false", south="false",
                      east="false", west="false", waterlogged="false")
                rails += 1

    # ---- string courses and the cornice: a proud ring on a stair corbel, at every floor line
    for k in range(1, STOREYS):
        h = F0 + k * SH - 1
        _proud_ring(w, f, 0, W - 1, 0, D - 1, h, pal["trim"])
        _corbel_ring(w, f, 0, W - 1, 0, D - 1, h - 1, kit["roof_stair"], mr)
    _proud_ring(w, f, 0, W - 1, 0, D - 1, TOP, pal["trim"])
    _corbel_ring(w, f, 0, W - 1, 0, D - 1, TOP - 1, kit["roof_stair"], mr)

    # ---- the roof. A main gable across the depth, plus THREE cross-gables on the front slope:
    # the entrance bay's, and one either side of it. Where a cross is higher than the main slope
    # it wins, and `_slope`'s neighbour rule closes the valley between them by construction.
    crosses = [(3, 9, EAVE + 6, 7), (W - 11, W - 5, EAVE + 6, 7)]
    field = {}
    for i in range(W):
        for d in range(D):
            h = EAVE + min(d, D - 1 - d)
            dirn = a["back"] if d * 2 < D - 1 else a["fwd"]
            ridge = min(d, D - 1 - d) == (D - 1) // 2
            for (c0, c1, peak, cd) in crosses:
                if c0 <= i <= c1 and d <= cd:
                    cm = (c0 + c1) // 2
                    ch = peak - abs(i - cm)
                    if ch > h:
                        h, ridge = ch, (i == cm)
                        dirn = a["ip"] if i < cm else a["im"]
            field[(i, d)] = (h, dirn, ridge)
    lo_of = _slope(w, f, field, EAVE, kit["roof"], kit["roof_stair"], kit["roof"],
                   alt=kit["roof_alt"])

    # THE GABLE ENDS: the wall carried on up under the roof, which is what makes a cross-gable a
    # gable rather than a bump.
    for i in range(W):
        for d in range(D):
            if not (i in (0, W - 1) or d in (0, D - 1)):
                continue
            for y in range(EAVE, lo_of[(i, d)]):
                _weathered(w, f, i, d, y, pal["wall"], kit["stone"], 0.12)
    # ...and an attic lancet in each cross-gable's own peak, so it has an eye. It is placed LAST
    # and overwrites: at d=0 a cross gable's shell already fills the triangle, so a window drawn
    # before it is a window nobody can see.
    for (c0, c1, peak, cd) in crosses:
        cm = (c0 + c1) // 2
        for rr in range(EAVE + 1, EAVE + 4):
            w.put(*f.at(cm, 0, rr), "glass_pane", **_pane(a["ip"], a["im"]))
        w.put(*f.at(cm, 0, EAVE + 4), kit["dressed"])

    # ---- the entrance bay: a two-storey projection with its own gable, a porch and steps
    _box(w, f, bi0, bi0 + bw - 1, -3, -1, F0, F0 + 2 * SH - 1, kit["stone"], kit["dressed"],
         holes=[(i, -3, h) for i in range(bi0 + 2, bi0 + 5) for h in range(F0, F0 + 3)],
         alt=kit["rough"])
    _fill(w, f, bi0 + 1, bi0 + bw - 2, -2, -1, F0 + SH - 1, kit["timber"])
    _proud_ring(w, f, bi0, bi0 + bw - 1, -3, -1, F0 + SH - 1, pal["trim"])
    _lancet(w, f, kit, pal, bmid - 1, -3, F0 + SH + 1, (a["ip"], a["im"]), "glass_pane")

    bay_field = {}
    for i in range(bi0, bi0 + bw):
        for d in range(-3, 0):
            bh = F0 + 2 * SH + (bw // 2 - abs(i - bmid))
            bay_field[(i, d)] = (bh, a["ip"] if i < bmid else a["im"], i == bmid)
    bay_lo = _slope(w, f, bay_field, F0 + 2 * SH, kit["roof"], kit["roof_stair"], kit["roof"],
                    alt=kit["roof_alt"])
    for (i, d), lo in bay_lo.items():
        if not (d == -3 or i in (bi0, bi0 + bw - 1)):
            continue
        for y in range(F0 + 2 * SH, lo):
            _weathered(w, f, i, d, y, pal["wall"], kit["stone"], 0.12)

    # the front door: a double door standing open in the opening the wall loop left empty
    for h in range(F0, F0 + 3):
        for i in (bmid - 2, bmid + 2):
            w.put(*f.at(i, 0, h), kit["dressed"])
    for (i, hinge) in ((bmid - 1, "right"), (bmid + 1, "left")):
        w.put(*f.at(i, 0, F0), kit["door"], facing=f.facing, half="lower", hinge=hinge,
              open="true", powered="false")
        w.put(*f.at(i, 0, F0 + 1), kit["door"], facing=f.facing, half="upper", hinge=hinge,
              open="true", powered="false")
        w.put(*f.at(i, 0, F0 + 2), kit["roof_stair"],
              facing=a["im"] if i < bmid else a["ip"], half="top", shape="straight",
              waterlogged="false")

    # THE BACK DOOR - the walkthrough's exit, and the reason it is a walkthrough. Doors on the
    # outer pair, standing open, and the middle column left clear: exactly the front door's own
    # arrangement, so a visitor recognises it as a way out rather than as a cupboard.
    bd = sorted(back_door_i)
    for (i, hinge) in ((bd[0], "right"), (bd[2], "left")):
        w.put(*f.at(i, D - 1, F0), kit["door"], facing=f.back, half="lower", hinge=hinge,
              open="true", powered="false")
        w.put(*f.at(i, D - 1, F0 + 1), kit["door"], facing=f.back, half="upper", hinge=hinge,
              open="true", powered="false")
    w.put(*f.at(bd[1], D - 1, F0 + 2), kit["dressed"])
    # ...and steps down off the plinth on the far side, or the exit is a one-course drop into
    # void: the pad reaches to D+2, so the ground is there, but the plinth's top is a course
    # above it and nothing had ever walked off the back of this building.
    _run(w, f, [(i, D + 1, 0) for i in bd], kit["roof_stair"], a["fwd"],
         half="bottom", min_run=1)
    _lamp_post(w, f, kit, pal, bd[0] - 2, D + 1, 0, tall=2)
    _lamp_post(w, f, kit, pal, bd[2] + 2, D + 1, 0, tall=2)

    # the porch: steps up onto the plinth, newel posts with lamps, and lit under the bay ceiling
    _run(w, f, [(i, -5, 0) for i in range(bmid - 2, bmid + 3)], kit["roof_stair"], a["back"],
         half="bottom", min_run=mr)
    _lamp_post(w, f, kit, pal, bi0 - 1, -4, 1)
    _lamp_post(w, f, kit, pal, bi0 + bw, -4, 1)
    for i in (bi0 + 2, bi0 + 4):
        _hang(w, f, pal, i, -2, F0 + 3, kit["timber"])

    # facade lamps, hung under the first string course where there is a full block to hang from
    for i in range(4, W - 4, 9):
        if bi0 - 1 <= i <= bi0 + bw:
            continue
        _hang(w, f, pal, i, -1, F0 + SH - 2, pal["trim"])

    # ---- the corner tower: taller than the ridge, corbelled, crenellated, with a spire
    TW = RIDGE + 5
    slits = []
    for stage in range(1, (TW - 1) // 8 + 1):
        base = stage * 8
        for h in range(base, base + 3):
            slits += [(ti0 + 3, td0, h), (ti0 + 3, td1, h), (ti0, td0 + 3, h), (ti1, td0 + 3, h)]
    door = [(ti0 + 3, td0, h) for h in range(1, 4)]
    _box(w, f, ti0, ti1, td0, td1, 1, TW, kit["stone"], kit["dressed"],
         holes=slits + door, alt=kit["rough"])
    for (i, d, h) in slits:
        axis = (a["ip"], a["im"]) if d in (td0, td1) else (a["fwd"], a["back"])
        w.put(*f.at(i, d, h), "iron_bars" if h > 16 else "glass_pane", **_pane(*axis))
    w.put(*f.at(ti0 + 3, td0, 3), kit["roof_stair"], facing=a["back"], half="top",
          shape="straight", waterlogged="false")
    for stage in range(1, (TW - 1) // 8 + 1):
        h = stage * 8 - 1
        _proud_ring(w, f, ti0, ti1, td0, td1, h, pal["trim"])
        _corbel_ring(w, f, ti0, ti1, td0, td1, h - 1, kit["roof_stair"], mr)
    for h in range(1, TW + 2):
        w.put(*f.at(ti1 - 1, td1 - 1, h), pal["post"])
        w.put(*f.at(ti1 - 1, td1 - 2, h), "ladder", facing=f.facing, waterlogged="false")

    # THE DECK NEEDS A HATCH, or the ladder ends against a solid plate and the climb is a lie.
    _corbel_ring(w, f, ti0, ti1, td0, td1, TW, kit["roof_stair"], mr)
    _fill(w, f, ti0 - 1, ti1 + 1, td0 - 1, td1 + 1, TW + 1, pal["trim"],
          holes={(ti1 - 1, td1 - 2)})
    _box(w, f, ti0 - 1, ti1 + 1, td0 - 1, td1 + 1, TW + 2, TW + 3, kit["stone"], kit["dressed"])
    _crenels(w, f, ti0 - 1, ti1 + 1, td0 - 1, td1 + 1, TW + 4, pal["trim"])
    spire = [5, 5, 3, 3, 3, 1, 1, 1]
    for k, s in enumerate(spire):
        r = s // 2
        for i in range(ti0 + 3 - r, ti0 + 3 + r + 1):
            for d in range(td0 + 3 - r, td0 + 3 + r + 1):
                _weathered(w, f, i, d, TW + 2 + k, kit["roof"], kit["roof_alt"], 0.14)
    w.put(*f.at(ti0 + 3, td0 + 3, TW + 2 + len(spire)), kit["dressed"])
    w.put(*f.at(ti0 + 3, td0 + 3, TW + 3 + len(spire)), pal["light"],
          hanging="false", waterlogged="false")

    # ---- chimneys. Two, at different heights on the roof, so the skyline is not symmetrical.
    stacks = 0
    for (ci, cd) in ((4, 3), (W - 8, D // 2 - 1)):
        cap = field[(ci, cd)][0] + 5
        for i in range(ci, ci + 2):
            for d in range(cd, cd + 2):
                for h in range(F0, cap):
                    _weathered(w, f, i, d, h, kit["stone"], kit["rough"], 0.16)
        for i in range(ci - 1, ci + 3):
            for d in range(cd - 1, cd + 3):
                if ci <= i < ci + 2 and cd <= d < cd + 2:
                    continue
                w.put(*f.at(i, d, cap - 1), kit["dressed"])
                w.put(*f.at(i, d, cap), kit["roof_slab"], type="bottom", waterlogged="false")
        # the hearth: an opening in the stack on the ground storey, with soul fire in it
        w.put(*f.at(ci, cd - 1, F0), kit["stone"])
        w.put(*f.at(ci, cd - 1, F0 + 1), "soul_campfire", facing=f.facing, lit="true",
              signal_fire="false", waterlogged="false")
        stacks += 1

    # ---- THE THREE SET PIECES, one on each leg of the route, and the reason this is a
    # walkthrough rather than a corridor with signs in it.
    #
    # **THE MACHINE HAS TO HIDE IN A COURSE THAT ALREADY EXISTS**, and on this building there are
    # exactly two: the pad at h=-1 under the ground floor, and the void under the cellar's own
    # floor at CELL_FLOOR - 1. The library was tried and abandoned: its floor plane is ONE course
    # thick with the hall's open air under it, so a machine there would hang from the hall's
    # ceiling in full view and lower it by two courses. A set piece with nowhere honest to put its
    # wiring is a set piece that does not get built.
    #
    # THE THREE ARE DELIBERATELY DIFFERENT AT THE ONE END A PLAYER TOUCHES. The mechanism is the
    # same monostable in all three - one verified primitive, three times, rather than three
    # inventions - and what changes is the INPUT, because that is the part a visitor reads:
    #
    #   the hall     a PLATE  you cannot avoid it: it is the third cell inside the front door
    #   the back     a LEVER  you choose to pull it, at the head of the cellar stair - and it is
    #                         the one that PROVES the monostable, because a lever can be left on
    #                         and the vents still go dark
    #   the cellar   a BUTTON you knock on the sarcophagus, at the dead end, which is the climax
    #
    # **WHERE THEY ARE NOT IS A MEASUREMENT, NOT AN OVERSIGHT.** The back half of the ground
    # floor and the whole first floor carry no set piece, and both refusals are geometric:
    #
    #   the back half   the undercroft runs d = cs_d .. D-2 and its LID IS THIS SAME PAD at
    #                   h = -1. A machine there punches its wiring through the cellar's ceiling
    #                   and stands its own floor course inside the cellar's headroom.
    #   the partition   d = D//2 is a solid wall except the three doorway columns, so a trigger
    #                   on that line lands INSIDE it.
    #   the first floor its floor plane is ONE course thick with the hall's open air under it.
    #                   A machine there hangs off the hall's ceiling in full view and lowers it.
    #
    # So the front half gets one and the cellar gets two - which is also the right dramatic
    # shape, since the cellar is the dead end and the thing a visitor turns round in.
    scares = []
    scares.append({"where": "the hall", "sign": ["MIND THE FLOOR", "it is not", "as sound as",
                                                 "it looks"],
                   **_scare(w, f, kit, pal, bmid - 1, 3, F0 - 2, kind="plate")})
    scares.append({"where": "the cellar stair foot",
                   "sign": ["PULL IT", "the house", "answers once", "then forgets"],
                   **_scare(w, f, kit, pal, 8, D - 9, CELL_FLOOR - 1, kind="lever")})
    scares.append({"where": "the sarcophagus",
                   "sign": ["KNOCK", "something", "down here", "keeps count"],
                   **_scare(w, f, kit, pal, W // 2 - 3, D - 6, CELL_FLOOR - 1, kind="button")})

    # ---- THE SET DRESSING. It is placed LAST and it never places into an occupied cell, so
    # nothing here can eat a tread, a rail or a doorway - the casino's own lesson, where a
    # pocket's colour ring was painted into cells a gate had not reached and the gate shipped
    # with its comparator replaced by red wool.
    props = 0
    for (i, d, h) in ((3, 2, F0), (W - 4, 2, F0), (3, D - 3, F0), (W - 4, D - 3, F0),
                      (gs_i1 + 2, gs_d + 6, F0 + SH), (W - 5, 3, F0 + SH),
                      (W // 2 + 3, D - 6, CELL_WALK), (W // 2 - 3, D - 6, CELL_WALK)):
        props += int(_candle(w, f, i, d, h, count=2 + (i % 3)))
    for (i, d, h) in ((6, 2, F0), (6, D - 4, F0 + SH)):
        if not w.has(*f.at(i, d, h)):
            w.put(*f.at(i, d, h), "lectern", facing=f.facing, has_book="false",
                  powered="false")
            props += 1
    # THE LIBRARY: barrels along the first-floor front wall, which is what a shelf is on this
    # economy - `bookshelf` is EXPENSIVE here and `chiseled_bookshelf` is a 1.20 block, so a wall
    # of either is a wall this server cannot supply. A barrel is cheap, 1.19, and reads as
    # storage from across a room.
    shelves = 0
    for i in range(4, W - 4):
        if abs(i - bmid) <= 4 or gs_i0 - 1 <= i <= gs_i1 + 1:
            continue                    # clear of the bay's attic window and the stairwell
        for h in (F0 + SH, F0 + SH + 1):
            if not w.has(*f.at(i, 1, h)):
                w.put(*f.at(i, 1, h), "barrel", facing=f.back, open="false")
                shelves += 1
    webs = _cobwebs(w, f, [(1, 1, TOP - 1), (W - 2, 1, TOP - 1), (1, D - 2, TOP - 1),
                           (W - 2, D - 2, TOP - 1), (1, 1, F0 + SH - 2),
                           (W - 2, D - 2, F0 + SH - 2), (gs_i0, cs_d, F0 + 3),
                           (cs_i0 - 1, cs_d + 2, CELL_WALK + 2),
                           (cs_i1 + 1, cs_d + 4, CELL_WALK + 2),
                           (W // 2, D - 4, CELL_WALK + 2)])

    # ---- the nameplate, over the porch, and the room signs the route is told apart by. EVERY
    # ONE OF THESE HANGS ON A NAMED WALL, and the wall is chosen for being solid THERE: the back
    # wall's window rhythm leaves only two-wide gaps, so a sign put on it by eye lands on glass.
    title = str(p.get("title") or "HOLLOW MANOR").upper()
    signed = 0
    if p.get("sign", True):
        signed += _sign(w, f, pal, bmid, -4, F0 + 3, f.facing,
                        [title[:SIGN_WIDTH], "", "", ""])
        # WHAT YOU DO HERE, not just what it is called. "Haunted Manor" over a door tells a
        # visitor nothing they could not see; "walk through it" is the whole difference between
        # a building you pass and one you enter.
        signed += _sign(w, f, pal, bi0 + 1, -4, F0 + 2, f.facing,
                        ["WALK THROUGH", "in at the front", "out at the back", "mind the cellar"])
        # the hall, read walking in - hung on the partition's front face
        signed += _sign(w, f, pal, bmid - 3, D // 2 - 1, F0 + 2, f.facing,
                        ["THE HALL", "stair on your", "left", ""])
        signed += _sign(w, f, pal, bmid + 3, D // 2 - 1, F0 + 2, f.facing,
                        ["WAY THROUGH", "up, round, and", "down again", ""])
        # the library, on the same wall one storey up
        signed += _sign(w, f, pal, bmid - 3, D // 2 - 1, F0 + SH + 2, f.facing,
                        ["THE LIBRARY", "nothing here", "is lent twice", ""])
        # the back hall, read walking out of the partition door - hung on its BACK face
        signed += _sign(w, f, pal, cs_i1 + 2, D // 2 + 1, F0 + 2, f.back,
                        ["THE CELLAR", "steps down", "on your left", ""])
        # the way out, on the back wall in a column the window rhythm leaves solid
        signed += _sign(w, f, pal, bmid - 4, D - 2, F0 + 2, f.facing,
                        ["WAY OUT", "to the", "graveyard", ""])
        # THE SET PIECES NAME THEMSELVES, because a trigger nobody knows is a trigger is a plate
        # you walk over and a lever you walk past. **AND EACH ONE HANGS ON A WALL CHOSEN FOR
        # BEING SOLID THERE**, which on this building means the partition (open only at the three
        # doorway columns) and the cellar's own side wall (open only at its three niches). A sign
        # placed by eye beside its trigger lands in a doorway or a recess, `_sign` silently
        # refuses it, and the count is the only thing that would ever say so.
        signed += _sign(w, f, pal, bmid + 5, D // 2 - 1, F0 + 2, f.facing, scares[0]["sign"])
        signed += _sign(w, f, pal, gs_i0 + 2, D - 10, CELL_WALK + 1, a["ip"], scares[1]["sign"])
        signed += _sign(w, f, pal, gs_i0 + 2, D - 7, CELL_WALK + 1, a["ip"], scares[2]["sign"])

    # THE ROUTE, as world coordinates, so the contract and the walk test read ONE list. A test
    # that re-derives the waypoints from its own reading of the geometry is a second opinion
    # about what was built, not a check on it.
    route = [("front door", f.at(bmid, 0, F0)),
             ("the hall", f.at(bmid, 3, F0)),
             ("grand stair foot", f.at(gs_i0, gs_d, F0)),
             ("first landing", f.at(gs_i0, gs_land[0] + 1, gs_land[1])),
             ("the library", f.at(bmid, 2, F0 + SH)),
             ("first floor, back half", f.at(bs_i0, D // 2 + 2, F0 + SH)),
             ("back stair foot", f.at(bs_i0, bs_land[0] - 1, F0)),
             ("the back hall", f.at(cs_i0, cs_d, F0)),
             ("the cellar", f.at(cs_i0, cs_land[0] + 2, CELL_WALK)),
             ("back door", f.at(bmid, D - 1, F0))]

    return {"kind": "manor", "width": W, "depth": D, "storeys": STOREYS,
            "wall_top": TOP, "ridge": RIDGE, "tower_top": TW + 3 + len(spire),
            "windows": len(windows), "chimneys": stacks, "signs": signed,
            "route": [[n, list(c)] for (n, c) in route],
            "entry_at": list(f.at(bmid, 0, F0)), "exit_at": list(f.at(bmid, D - 1, F0)),
            "niches": niches, "vault_lamps": vault_lamps, "shelves": shelves,
            "props": props, "cobwebs": webs, "rails": rails,
            "scares": scares,
            "inputs": [s["trigger"] for s in scares],
            "outputs": [c for s in scares for cs in s["vents"].values() for c in cs],
            "lamps": sum(s["lamps"] for s in scares),
            "stock": {"dispenser": ["anything the house should spit out of the floor - a "
                                    "firework, a snowball, an arrow. The dispenser fires ONE "
                                    "item per trigger, so what is in it decides the scare."]},
            "contract": "a WALKTHROUGH WITH THINGS IN IT: in at the front door, through the "
                        "hall, up the grand stair to the library, across the first floor, down "
                        "the back stair, down again into a lit cellar of niches, and out of the "
                        "back door on the far side - every leg of it walkable, the rooms named "
                        "on signs, and THREE SET PIECES on the way: a plate in the hall, a lever "
                        "at the head of the cellar stair and a button on the sarcophagus, each "
                        "firing a piston, a lamp and a dispenser ONCE and resetting, however "
                        "long it is held down",
            "unverified": ["WHAT A DISPENSER SPITS OUT is an entity and the simulator has none. "
                           "That it fires exactly once per trigger IS verified; what comes out "
                           "of it is whatever `stock` was loaded with."]}


# ---------------------------------------------------------------------------- the ossuary

def _ossuary(w: World, p: dict, ctx) -> dict:
    """THE OSSUARY: a tomb chamber you walk into, three shroud-pulls, and a vault that opens.

    **THE ZONE LOST ITS ONLY OUTDOOR SET PIECE WHEN THE GRAVEYARD AND THE CRYPT WERE DROPPED, AND
    NEITHER OF THEM WAS SOMETHING YOU DID ANYTHING IN.** The graveyard was a field of stones and
    the crypt states in its own docstring that it is sealed - *"you look in, you do not go in"*.
    That is a defensible thing for a mausoleum to be and it is the wrong thing for a zone whose
    verdict is that it reads as an abandoned town. So this is the crypt's opposite number rather
    than a change to it: the same masonry, the same palette, and a way in.

    **IT IS A PUZZLE, WHICH IS THE ONE PLAYER ACTION THE HOLLOW DID NOT HAVE.** The zone's five
    machines are a decoder (Fortune Wheel), a window gate (The Reckoning), an analog meter (The
    Seance), a lectern combination (The Vault) and a sculk corridor (The Quiet Room). Four of
    those five are *press a thing and read what happened*; the fifth is a corridor you cross.
    Nothing asked a visitor to do two things at ONCE, and that is what an AND gate is:

        three levers, on three tombs, and the vault opens only while ALL THREE are pulled

    `arcade.and_gate` is that gate and it is already verified - one torch per input inverts it,
    the inversions merge onto one dust line, and one more torch inverts the merge. It is reused
    here rather than re-derived, which is this repo's standing rule about not inventing a
    mechanism when a tested one fits.

    **AND IT RESETS BY BEING COMBINATIONAL.** There is no memory in it at all: drop any lever and
    the doors shut again. That is the difference between this and the manor's set pieces, which
    are monostables - and it is deliberate that the zone now has one of each, because a player who
    has met both knows the difference without being told.

    THE GEOMETRY, and the reason every part of the machine is on ONE course:

        h = 4   the ceiling, and the vault's lid
        h = 3   the lever lamps, and the prize barrels on the vault's shelf
        h = 2   THE WHOLE MACHINE - the levers, the gate, the route, the doors, the vault feed
        h = 1   the walking course, and the machine's own floor slab in the service void
        h = 0   the floor

    A boolean can travel where an analog value cannot, but neither can CLIMB: dust only goes up
    the side of a block whose lid is not opaque, and under a floor it never is. Every failed
    display in the casino and every dead link in the first four of its games was that one fact. So
    the levers are on the WALL at the machine's own course rather than on the floor - a floor
    lever strongly powers the block BENEATH it, which is a course this gate cannot reach.

    **THE SERVICE VOID IS BEHIND THE BACK WALL, WHICH IS ALSO WHERE THE LEVERS HANG.** A wall
    lever strongly powers the block it is attached to, and a strongly powered opaque block passes
    15 to any wire touching it - so each feed sits directly on the far side of the wall from its
    own lever and nothing has to be routed to it at all. Three levers, three feeds, no crossings:
    which is the arrangement `and_gate`'s docstring asks for and the one the first `safe` could
    not lay.

    CONTRACT: the vault doors are SHUT and the vault lamp dark while any lever is down, and open
    and lit only while all three are up; letting any one go shuts it again.
    """
    from .arcade import and_gate, _run as _wire_run

    f = _Frame(p)
    pal = LANDS[p["land"]]
    kit = GOTHIC[p["land"]]
    a = _ax(f)
    mr = int(p["min_run"])

    # THE MINIMUMS ARE THE MACHINE'S, NOT A STYLE CHOICE. The gate is eight cells deep behind the
    # wall and its merge column is five wide; the route needs a lane clear of every `keep_clear`
    # cell, and the vault has to sit past that lane. Ask for less and you get this.
    W = max(15, int(p["width"] or 15))
    D = max(17, int(p["depth"] or 17))
    CD = 7                                  # the chamber's own depth; the service void is behind
    H = 3                                   # interior courses: h = 1, 2, 3
    mid = W // 2
    MACH = 2                                # the ONE course the whole machine lives on
    pulls = [2, 4, 6]                       # `and_gate` spaces its feeds exactly TWO apart
    vi = [W - 4, W - 3]                     # the vault's two columns
    lane = 8                                # the route's lane, clear of every keep_clear cell

    # ---- pad and plinth
    _ground(w, f, -4, W + 3, -4, D + 3, pal["path"], alt=pal["ground"], mix=0.35)
    _fill(w, f, -2, W + 1, -2, D + 1, 0, kit["stone"])

    # ---- THE MACHINE FIRST. The walls, the floor slab and the roof are all continuous surfaces
    # laid with `w.put`, which overwrites; a machine laid after them is swallowed cell by cell and
    # audits clean. The seance shipped exactly that once - 997 correct blocks and a dropper wired
    # to nothing - so the order is stated here rather than left to whoever edits next.
    gate = and_gate(f.at(pulls[0], CD + 2, MACH), facing=a["back"], side=a["ip"], inputs=3)
    for pos, spec in gate["cells"].items():
        _put_spec(w, pos, spec)
    for pos in gate["cells"]:
        if not w.has(pos[0], pos[1] - 1, pos[2]):
            w.put(pos[0], pos[1] - 1, pos[2], kit["stone"])

    # ---- the route: gate out -> the lane -> along the back of the wall -> the vault's feed.
    # It runs at the machine's own course the whole way and turns twice, and `arcade._run` puts a
    # repeater ONE CELL PAST each corner - never on it, because a repeater standing on a bend
    # reads along its outgoing axis and takes the incoming leg on its SIDE, which LOCKS it rather
    # than feeding it. Two of the reaction game's routes died at their first corner that way.
    _wire_run(w, pal, f, [(pulls[0], CD + 8), (lane, CD + 8), (lane, CD + 1), (vi[1], CD + 1)],
              MACH)

    # ---- the floor slab under the service void, laid ROUND the machine and never over it
    for i in range(1, W - 1):
        for d in range(CD + 1, D - 1):
            if not w.has(*f.at(i, d, 1)):
                w.put(*f.at(i, d, 1), kit["stone"])

    # ---- the chamber and the service void: one box each, sharing the back wall at d = CD
    door = [(i, 0, h) for i in range(mid - 1, mid + 2) for h in range(1, H + 1)]
    vault = [(i, CD, h) for i in vi for h in (MACH, MACH + 1)]
    _box(w, f, 0, W - 1, 0, CD, 1, H, pal["wall"], pal["post"], holes=door + vault,
         alt=kit["stone"])
    _box(w, f, 0, W - 1, CD, D - 1, 1, H, kit["stone"], pal["post"], alt=kit["rough"])
    for i in range(-1, W + 1):
        for d in range(-1, D + 1):
            if not w.has(*f.at(i, d, H + 1)):
                w.put(*f.at(i, d, H + 1), pal["trim"])
    for i in range(1, W - 1):
        for d in range(1, CD):
            if not w.has(*f.at(i, d, 0)):
                w.put(*f.at(i, d, 0), pal["ground"])

    # ---- THE THREE PULLS. A wall lever's `facing` is the way it LOOKS, which is AWAY from the
    # block it hangs on - so a lever in the chamber on the back wall faces the front. Written the
    # other way round it hangs on the air in front of it: a legal state, an identical render, and
    # a block the game refuses to place.
    levers, lamps = [], []
    for li in pulls:
        for h in (1, H):                          # a dressed panel, so a pull reads as a tomb
            w.put(*f.at(li, CD, h), kit["dressed"])
        cell = f.at(li, CD - 1, MACH)
        w.put(cell[0], cell[1], cell[2], "lever", face="wall", facing=f.facing, powered="false")
        levers.append(list(cell))
        # ...and a light OVER each pull, so a visitor can see which of the three are up. It is
        # driven by nothing but the lever's own six-neighbour radiation and costs no wiring.
        lamp = f.at(li, CD - 1, MACH + 1)
        w.put(lamp[0], lamp[1], lamp[2], "redstone_lamp", lit="false")
        lamps.append(list(lamp))

    # ---- THE VAULT: two iron doors in the back wall at chest height, a lit alcove behind them,
    # and the prize on a shelf inside it. **BOTH DOOR COLUMNS GET THEIR OWN FEED CELL**, because
    # the route's last two cells are the alcove's own floor: fed at one column only, the second
    # door is a door nothing drives - legal, supported, affordable, and shut for ever.
    doors = []
    for i in vi:
        for (h, half) in ((MACH, "lower"), (MACH + 1, "upper")):
            c = f.at(i, CD, h)
            w.put(c[0], c[1], c[2], "iron_door", facing=f.facing, half=half,
                  hinge="left" if i == vi[0] else "right", open="false", powered="false")
            if half == "lower":
                doors.append(list(c))
    vault_lamp = f.at(vi[0], CD + 1, 1)
    w.put(vault_lamp[0], vault_lamp[1], vault_lamp[2], "redstone_lamp", lit="false")
    prizes = 0
    for i in vi:
        c = f.at(i, CD + 1, MACH + 1)
        w.put(c[0], c[1], c[2], "barrel", facing=f.back, open="false")
        prizes += 1
    for h in range(1, H + 1):                     # the alcove's own sides and back
        for i in (vi[0] - 1, vi[1] + 1):
            if not w.has(*f.at(i, CD + 1, h)):
                w.put(*f.at(i, CD + 1, h), kit["stone"])
        for i in vi:
            if not w.has(*f.at(i, CD + 2, h)):
                w.put(*f.at(i, CD + 2, h), kit["stone"])

    # ---- the front hood, the cornice, the roof and the urns: the crypt's own language, so the
    # two read as one hand and a visitor knows this is the same kind of building with a way in.
    for i in range(mid - 2, mid + 3):
        w.put(*f.at(i, -1, H + 1), pal["trim"])
    _corbel_ring(w, f, 0, W - 1, 0, D - 1, H, kit["roof_stair"], mr)
    _proud_ring(w, f, 0, W - 1, 0, D - 1, H + 1, pal["trim"])
    field = {}
    for i in range(W):
        t = mid - abs(i - mid)
        for d in range(D):
            field[(i, d)] = (H + 2 + min(3, t), a["ip"] if i < mid else a["im"], i == mid)
    lo_of = _slope(w, f, field, H + 2, kit["roof"], kit["roof_stair"], kit["roof"],
                   alt=kit["roof_alt"])
    for i in range(W):
        for d in (0, D - 1):
            for y in range(H + 2, lo_of[(i, d)]):
                _weathered(w, f, i, d, y, kit["stone"], kit["rough"], 0.14)
    for (i, d) in ((-2, -2), (W + 1, -2), (-2, D + 1), (W + 1, D + 1)):
        _urn(w, f, kit, pal, i, d, 1)
    lit = 0
    for (i, d) in ((2, 2), (W - 3, 2)):
        _hang(w, f, pal, i, d, H, pal["trim"])
        lit += 1

    # ---- the signs. THE SUPPORT IS CHOSEN FOR BEING SOLID THERE, which on this building means
    # the back wall away from the three pull panels and the vault, and the cornice course over
    # the doorway - the front wall's own middle three columns ARE the way in.
    title = str(p.get("title") or "THE OSSUARY").upper()
    signed = 0
    if p.get("sign", True):
        signed += _sign(w, f, pal, mid, -1, H + 1, f.facing,
                        [title[:SIGN_WIDTH], "pull all three", "at once", "and it opens"])
        signed += _sign(w, f, pal, pulls[-1] + 2, CD - 1, MACH, f.facing,
                        ["THREE PULLS", "one lamp each", "all three lit", "and it opens"])
        signed += _sign(w, f, pal, vi[0] - 2, CD - 1, MACH, f.facing,
                        ["THE VAULT", "let one go", "and it shuts", "again"])

    # `lamps` is a COUNT everywhere else in this module (`_seance`, `_manor`), so the positions
    # get their own name rather than shadowing it. A sidecar key that means a number in one kind
    # and a list of cells in another is a tool downstream reading whichever it happened to meet.
    return {"kind": "ossuary", "width": W, "depth": D, "height": H + 1,
            "levers": levers, "pull_lamps": lamps, "vault_lamp": list(vault_lamp),
            "lamps": len(lamps) + 1,
            "doors": doors, "prizes": prizes, "lanterns": lit, "signs": signed,
            "inputs": levers, "outputs": doors + lamps + [list(vault_lamp)],
            "entry_at": list(f.at(mid, 0, 1)),
            "contract": "an AND of three: the vault doors are shut and the vault lamp dark while "
                        "any of the three shroud-levers is down, and open and lit only while all "
                        "three are up - and each lever lights its own lamp on the way",
            "unverified": ["WHAT IS IN THE PRIZE BARRELS is the operator's business; the barrels "
                           "are placed here and stocked by hand."]}



# ---------------------------------------------------------------------------- the crypt

def _crypt(w: World, p: dict, ctx) -> dict:
    """A mausoleum: a stepped plinth, pilasters flanking a barred door, urns, an inscription.

    THE ROOF IS CHOSEN BY A HASH OF ITS OWN POSITION, so a row of crypts is a row of DIFFERENT
    crypts and never a repeated box - deterministic, reproducible, and never `random`.
    """
    f = _Frame(p)
    pal = LANDS[p["land"]]
    kit = GOTHIC[p["land"]]
    a = _ax(f)
    mr = int(p["min_run"])

    W = max(9, int(p["width"] or 9))
    D = max(11, int(p["depth"] or 11))
    mid = W // 2
    F0, WT = 3, 9                          # floor course, wall top

    _ground(w, f, -4, W + 3, -4, D + 3, pal["path"], alt=pal["ground"], mix=0.35)
    _fill(w, f, -3, W + 2, -3, D + 2, 0, kit["stone"])
    _fill(w, f, -2, W + 1, -2, D + 1, 1, kit["stone"])
    _fill(w, f, -1, W, -1, D, 2, pal["trim"])

    # THE DOOR IS THREE WIDE AND FOUR TALL, and it needed to be: at one cell it was a slot you
    # could not find in a render from ten blocks away, which is the whole point of a mausoleum
    # front. Barred, because a crypt is sealed - you look in, you do not go in.
    door = [(mid + k, 0, h) for k in (-1, 0, 1) for h in range(F0, F0 + 4)]
    # SLIT LANCETS down the flanks, so the long walls are not two blank planes.
    slits = []
    for dd in range(3, D - 2, 3):
        for h in (F0 + 3, F0 + 4):
            slits += [(0, dd, h), (W - 1, dd, h)]
    _box(w, f, 0, W - 1, 0, D - 1, F0, WT, kit["stone"], kit["dressed"],
         holes=door + slits, alt=kit["rough"])
    for (i, d, h) in door:
        w.put(*f.at(i, d, h), "iron_bars", **_pane(a["ip"], a["im"]))
    for (i, d, h) in slits:
        w.put(*f.at(i, d, h), "iron_bars", **_pane(a["fwd"], a["back"]))
    for i in (mid - 1, mid + 1):
        w.put(*f.at(i, 0, F0 + 4), kit["roof_stair"],
              facing=a["im"] if i < mid else a["ip"], half="top", shape="straight",
              waterlogged="false")

    # PILASTERS, projecting one cell, with a capital - the order that says this is a tomb and
    # not a hut. They stand on the plinth's own top step, so nothing floats. ENGAGED ON EVERY
    # WALL, not only beside the door: two blank flanks are what made the first build a bunker.
    for i in (mid - 2, mid + 2):
        for h in range(F0, WT):
            w.put(*f.at(i, -1, h), kit["dressed"])
        w.put(*f.at(i, -1, WT), kit["roof_slab"], type="bottom", waterlogged="false")
    for dd in range(1, D - 1, 3):
        for (i, out) in ((0, -1), (W - 1, W)):
            for h in range(F0, WT):
                w.put(*f.at(out, dd, h), kit["dressed"])
            w.put(*f.at(out, dd, WT), kit["roof_slab"], type="bottom", waterlogged="false")
    for i in range(1, W - 1, 3):
        for h in range(F0, WT):
            w.put(*f.at(i, D, h), kit["dressed"])
        w.put(*f.at(i, D, WT), kit["roof_slab"], type="bottom", waterlogged="false")

    # THE HOOD over the door: a proud lintel on a stair corbel, which is what makes the opening
    # look framed rather than punched.
    for i in range(mid - 2, mid + 3):
        w.put(*f.at(i, -1, F0 + 5), pal["trim"])

    # the roof: a pediment or a barrel, decided by the crypt's own world position
    ox, oy, oz = f.at(0, 0, 0)
    barrel = hash01(ox, oy, oz) < 0.5
    field = {}
    for i in range(W):
        t = mid - abs(i - mid)
        if barrel:
            rise = 0 if t == 0 else (2 if t == 1 else 3)
        else:
            rise = min(3, t)
        for d in range(D):
            field[(i, d)] = (WT + 1 + rise, a["ip"] if i < mid else a["im"], i == mid)
    lo_of = _slope(w, f, field, WT + 1, kit["roof"], kit["roof_stair"], kit["roof"],
                   alt=kit["roof_alt"])
    for i in range(W):
        for d in (0, D - 1):
            for y in range(WT + 1, lo_of[(i, d)]):
                _weathered(w, f, i, d, y, kit["stone"], kit["rough"], 0.14)
    _corbel_ring(w, f, 0, W - 1, 0, D - 1, WT, kit["roof_stair"], mr)
    _proud_ring(w, f, 0, W - 1, 0, D - 1, WT + 1, pal["trim"])

    # urns on the plinth corners, and a tomb inside under a hanging soul lantern
    for (i, d) in ((-2, -2), (W + 1, -2), (-2, D + 1), (W + 1, D + 1)):
        _urn(w, f, kit, pal, i, d, 2)
    _fill(w, f, 1, W - 2, 1, D - 2, WT + 1, pal["trim"])
    for i in range(mid - 1, mid + 2):
        w.put(*f.at(i, D // 2, F0), kit["stone"])
        w.put(*f.at(i, D // 2, F0 + 1), kit["roof_slab"], type="bottom", waterlogged="false")
    _hang(w, f, pal, mid, D // 2 - 2, WT, pal["trim"])

    title = str(p.get("title") or "IN MEMORIAM").upper()
    lines = list(p.get("lines") or ["they went down", "into the dark", "and did not", "come back"])
    signed = 0
    if p.get("sign", True):
        signed += _sign(w, f, pal, mid, -1, F0 + 4, f.facing,
                        [title[:SIGN_WIDTH]] + [str(s)[:SIGN_WIDTH] for s in lines[:3]])
    return {"kind": "crypt", "width": W, "depth": D, "roof": "barrel" if barrel else "pediment",
            "signs": signed,
            "contract": "a sealed mausoleum: a stepped plinth, pilasters flanking an iron-barred "
                        "door, urns at the corners and its inscription on the front"}


# ---------------------------------------------------------------------------- the clocktower

def _ring(S):
    """The interior perimeter of an S x S tower, walked in order, each cell ONE STEP from the last.

    That property is what a spiral stair is made of and it is asserted rather than assumed: two
    consecutive treads that are only diagonal neighbours are two stairs that happen to line up,
    which is the 6-connectivity trap that broke the leopard's ear tips and detached the giraffe's
    ossicones - and here it would also be unwalkable, because a diagonal step up is not a step.
    """
    lo, hi = 1, S - 2
    cells = [(i, lo) for i in range(lo, hi + 1)]
    cells += [(hi, d) for d in range(lo + 1, hi + 1)]
    cells += [(i, hi) for i in range(hi - 1, lo - 1, -1)]
    cells += [(lo, d) for d in range(hi - 1, lo, -1)]
    return cells


def _dir_of(f, a, di, dd):
    if dd:
        return f.back if dd > 0 else f.facing
    return a["ip"] if di > 0 else a["im"]


def _clocktower(w: World, p: dict, ctx) -> dict:
    """A square tower with a stage per string course, a clock on all four faces, and a belfry -
    AND A STAIR YOU CAN ACTUALLY CLIMB, TO A GALLERY WORTH CLIMBING TO.

    THE CLOCK IS THE ONLY BRIGHT THING FOR A HUNDRED BLOCKS, which is the whole reason it reads:
    white_wool (236) on a blackstone shaft (45) is the widest value step this economy has at
    cheap tier, and the hands are the dark end of the same ladder (21).

    **AND THE VERDICT ON IT WAS THAT A CLOCK DOES NOT SERVE A REAL PURPOSE.** It did not: it was
    a 2,463-block landmark with a service ladder up the inside of it and a bell nobody could get
    to. What it has now is the one thing a tower is FOR - height you can be at:

        door  ->  a SPIRAL STAIR round the inside face, one course per tread, 29 of them
              ->  THE BELFRY GALLERY at h=31: the bell, and the lower two courses of every
                  louvred opening taken out so you can see the whole zone from inside it
              ->  a short ladder to the CROWN DECK inside the crenellations at h=37

    Two things make the spiral work and neither is visible in a render. **CONSECUTIVE TREADS ARE
    ONE STEP APART**, which `_ring` guarantees by construction; and **EVERY TREAD TOUCHES THE
    SHAFT WALL**, which is what keeps the flight one 6-connected piece - a tread and the one
    above it are diagonal neighbours and share no face, so a free-standing helix audits as
    twenty-nine floating stairs. `gen/monument.py` solves the same problem with a riser block
    above the previous tread; that riser stands in the cell a walker's legs occupy, so it makes
    a spiral that LOOKS right and cannot be climbed. Against a wall, no riser is needed at all.
    """
    f = _Frame(p)
    pal = LANDS[p["land"]]
    kit = GOTHIC[p["land"]]
    a = _ax(f)
    mr = int(p["min_run"])

    S = max(9, int(p["width"] or 9)) | 1
    mid = S // 2
    SHAFT, CLOCK, BELFRY = 20, 28, 35      # stage tops
    TW = BELFRY

    _ground(w, f, -4, S + 3, -4, S + 3, pal["path"], alt=pal["ground"], mix=0.32)
    _fill(w, f, -2, S + 1, -2, S + 1, 0, kit["stone"])
    _fill(w, f, -1, S, -1, S, 1, pal["trim"])

    door = [(mid, 0, h) for h in range(2, 5)]
    slits, louvres, clock = [], [], []
    for base in (9, 16):
        for h in range(base, base + 3):
            slits += [(mid, 0, h), (mid, S - 1, h), (0, mid, h), (S - 1, mid, h)]
    for h in range(BELFRY - 4, BELFRY):
        for k in range(mid - 1, mid + 2):
            louvres += [(k, 0, h), (k, S - 1, h), (0, k, h), (S - 1, k, h)]
    # THE CLOCK FACE: a disc of radius three, quarter marks at its rim, two hands out of its
    # centre. THREE TONES, NOT TWO, and that is the whole of why it reads. Drawn with the marks
    # and the hands both in `dark` they MERGE - a hand at r=1..2 is face-adjacent to the mark at
    # r=3, so the 3 and the 6 became the ends of two solid spokes and only the 9 and the 12
    # survived as marks at all. The ladder this land already owns has a rung between:
    #
    #     white_wool 236 (the dial) -- light_gray_wool 141 (the marks) -- black_wool 21 (the hands)
    #
    # steps of 95 and 120, either of which is six times the 15 below which shading stops reading.
    # And THE HANDS MEET AT THE CENTRE: drawn from r=1 outward with a bright cell left between
    # them they were an L floating clear of its own pivot, which reads as damage, not as a clock.
    cy = CLOCK - 4
    for du in range(-3, 4):
        for dv in range(-3, 4):
            if du * du + dv * dv > 9:
                continue
            mark = (du == 0 or dv == 0) and du * du + dv * dv == 9
            hand = (du == 0 and 0 <= dv <= 2) or (dv == 0 and 0 <= du <= 2)
            blk = kit["dark"] if hand else kit["pale"] if mark else kit["bright"]
            clock.append((mid + du, cy + dv, blk))

    holes = door + slits + louvres
    holes += [(i, 0, h) for (i, h, _b) in clock]
    holes += [(i, S - 1, h) for (i, h, _b) in clock]
    holes += [(0, i, h) for (i, h, _b) in clock]
    holes += [(S - 1, i, h) for (i, h, _b) in clock]
    _box(w, f, 0, S - 1, 0, S - 1, 2, TW, kit["stone"], kit["dressed"],
         holes=holes, alt=kit["rough"])

    for (i, h, blk) in clock:
        w.put(*f.at(i, 0, h), blk)
        w.put(*f.at(i, S - 1, h), blk)
        w.put(*f.at(0, i, h), blk)
        w.put(*f.at(S - 1, i, h), blk)
    for (i, d, h) in slits:
        axis = (a["ip"], a["im"]) if d in (0, S - 1) else (a["fwd"], a["back"])
        w.put(*f.at(i, d, h), "glass_pane", **_pane(*axis))
    # LOUVRES ARE TRAPDOORS, closed, alternating half - horizontal slats in a vertical opening,
    # which is the shape a belfry actually has and a vocabulary this repo has never used.
    #
    # **BUT THE BOTTOM TWO COURSES ARE THE VIEW, so they are not louvred at all.** The belfry is
    # the gallery this climb exists to reach, and a closed trapdoor at eye height is a wall with
    # a texture on it: the whole point of getting up here is seeing the zone. `GALLERY_SILL` is
    # a rail of bars you lean on and the course above it is left open, so the louvres start at
    # the walker's own head height and the tower still reads as a belfry from the ground.
    gallery_sill = BELFRY - 4
    for (i, d, h) in louvres:
        face = a["back"] if d == 0 else a["fwd"] if d == S - 1 else (
            a["ip"] if i == 0 else a["im"])
        if h == gallery_sill:
            axis = (a["ip"], a["im"]) if d in (0, S - 1) else (a["fwd"], a["back"])
            w.put(*f.at(i, d, h), "iron_bars", **_pane(*axis))
        elif h == gallery_sill + 1:
            continue                    # OPEN - this is the view, and it is the only one
        else:
            w.put(*f.at(i, d, h), kit["trapdoor"], facing=face,
                  half="top" if h % 2 else "bottom",
                  open="false", powered="false", waterlogged="false")
    w.put(*f.at(mid, 0, 5), kit["roof_stair"], facing=a["back"], half="top",
          shape="straight", waterlogged="false")

    # THE STRING COURSES, AND THE ONE THAT WAS STANDING IN FRONT OF THE CLOCK. A proud ring and
    # its corbel are laid one cell OUTSIDE the wall, so the two courses (h, h-1) they occupy are
    # in front of the wall plane, not in it - and the clock stage's ring sat at CLOCK=28 with its
    # corbel at 27, which is exactly the course the dial's 12 o'clock mark is painted on. The
    # mark was built, was legal, was connected, and could not be seen from anywhere: an
    # upside-down stair hung a block in front of it. Nothing in an audit, a BOM or a component
    # count can see an occlusion, and neither could the elevation, which draws the wall plane.
    #
    # So the clock stage's cornice is at CLOCK + 1, which leaves the wall clear over the whole
    # dial (cy-3 .. cy+3 = 21..27) with the corbel one course above it - and the ring that used
    # to sit at BELFRY-5 is gone rather than doubled, because at 30 its corbel would land at 29
    # on top of this one's proud course. Four stages, one cornice each.
    for h in (SHAFT // 3, SHAFT * 2 // 3, SHAFT, CLOCK + 1):
        _proud_ring(w, f, 0, S - 1, 0, S - 1, h, pal["trim"])
        _corbel_ring(w, f, 0, S - 1, 0, S - 1, h - 1, kit["roof_stair"], mr)

    # ---- THE SPIRAL. One tread per ring cell, one course per tread, starting at the door so
    # the first thing a visitor sees inside is the way up. The ring is ROTATED to the door
    # rather than the door moved to the ring: the door's position is a facade decision and the
    # stair's is not, and letting the stair pick would have put the entrance on a corner.
    ring = _ring(S)
    start = ring.index((mid, 1))
    ring = ring[start:] + ring[:start]
    BELFRY_FLOOR = BELFRY - 5
    treads = []
    for k in range(BELFRY_FLOOR - 1):            # tread block heights 1 .. BELFRY_FLOOR - 1
        ci, cd = ring[k % len(ring)]
        ni, nd = ring[(k + 1) % len(ring)]
        w.put(*f.at(ci, cd, 1 + k), kit["roof_stair"],
              facing=_dir_of(f, a, ni - ci, nd - cd), half="bottom", shape="straight",
              waterlogged="false")
        treads.append((ci, cd, 1 + k))
    # THE NEWEL, and the only reason it is here is the LIGHT. It is not load-bearing - every
    # tread keys off the shaft wall - but a stair bracket hung in the middle of an open well is
    # a floating two-cell component, so the lanterns need a column to be attached to.
    stair_lamps = 0
    for h in range(1, BELFRY_FLOOR + 1):
        w.put(*f.at(mid, mid, h), kit["stone"])
    for h in range(6, BELFRY_FLOOR - 2, 7):
        _hang(w, f, pal, mid + 1, mid, h, kit["stone"])
        stair_lamps += 1

    # the belfry floor and a real bell hanging from it, then the crown. THE FLOOR NEEDS A HATCH
    # WHERE THE SPIRAL ARRIVES and the DECK ONE WHERE THE LADDER DOES, or each climb stops at a
    # solid plate - which is legal, connected, affordable and a dead end.
    # THE HATCH IS TWO CELLS, NOT ONE. A walker on the second-to-last tread stands one course
    # below the floor plane and their HEAD is in it - so holing only the cell the flight lands
    # on leaves the last step blocked by a plank ceiling, which is what the first build did and
    # what a render cannot show. The rule is that every tread within two courses of a plane
    # needs that plane open over it.
    _fill(w, f, 1, S - 2, 1, S - 2, BELFRY_FLOOR, kit["timber"],
          holes={(t[0], t[1]) for t in treads[-2:]} | {(mid, mid)})
    # A BELL HANGS FROM A BEAM, and the beam has to reach the walls. Hung from a single block in
    # the middle of the belfry, the bell and its block were two cells floating in mid-air - the
    # audit passes them and the component count is the only thing that ever says so.
    for i in range(S):
        w.put(*f.at(i, mid, BELFRY - 1), kit["timber"])
    w.put(*f.at(mid, mid, BELFRY - 2), "bell", attachment="ceiling", facing=f.facing,
          powered="false")
    # THE LAST LEG IS A LADDER, and only the last leg: from the gallery floor to the crown deck
    # is six courses in a chamber a bell already occupies, and a second spiral in there would be
    # a spiral you cannot stand up in. It runs one course PAST the deck plane on purpose - a
    # ladder that stops level with the hatch leaves you climbing out onto a cell you are
    # standing in, and the step onto the deck is then a step you cannot take.
    for h in range(BELFRY_FLOOR + 1, TW + 3):
        w.put(*f.at(1, S - 2, h), pal["post"])
        w.put(*f.at(1, S - 3, h), "ladder", facing=f.facing, waterlogged="false")

    _corbel_ring(w, f, 0, S - 1, 0, S - 1, TW, kit["roof_stair"], mr)
    _fill(w, f, -1, S, -1, S, TW + 1, pal["trim"], holes={(1, S - 3)})
    _box(w, f, -1, S, -1, S, TW + 2, TW + 3, kit["stone"], kit["dressed"])
    _crenels(w, f, -1, S, -1, S, TW + 4, pal["trim"])
    spire = [5, 5, 3, 3, 3, 1, 1, 1, 1]
    for k, s in enumerate(spire):
        r = s // 2
        for i in range(mid - r, mid + r + 1):
            for d in range(mid - r, mid + r + 1):
                _weathered(w, f, i, d, TW + 2 + k, kit["roof"], kit["roof_alt"], 0.14)
    top = TW + 2 + len(spire)
    w.put(*f.at(mid, mid, top), kit["dressed"])
    w.put(*f.at(mid, mid, top + 1), pal["light"], hanging="false", waterlogged="false")
    for (i, d) in ((-1, -1), (S, -1), (-1, S), (S, S)):
        _lamp_post(w, f, kit, pal, i, d, 2)

    # THE GALLERY IS LIT, or the one place worth climbing to is the darkest cell in the zone -
    # AND EVERY LANTERN HANGS FROM THE BEAM, not from a plank it brought with it. Placed at the
    # chamber's four corners each one supplied its own block and the pair floated: three
    # two-cell components in a design whose contract is that it is one piece. `_hang` guarantees
    # a FULL block overhead and cannot guarantee that the block is attached to anything, which
    # is the distinction a component count exists to catch and a render never shows.
    for d in range(S):
        if d != mid:
            w.put(*f.at(mid, d, BELFRY - 1), kit["timber"])
    for (gi, gd) in ((2, mid), (S - 3, mid), (mid, 2), (mid, S - 3)):
        _hang(w, f, pal, gi, gd, BELFRY - 2, kit["timber"])

    title = str(p.get("title") or "THE HOUR").upper()
    signed = 0
    if p.get("sign", True):
        signed += _sign(w, f, pal, mid, -1, 6, f.facing,
                        [title[:SIGN_WIDTH], "climb it:", "the gallery", "is 29 steps"])
        # Inside, at the foot of the spiral. ON THE SHAFT WALL, because the whole interior ring
        # is stair and the only solid thing at head height in this room is the wall itself - the
        # park's four floating signs were every one of them hung on a column with a hole in it.
        signed += _sign(w, f, pal, 1, 1, 4, a["ip"],
                        ["UP TO THE BELL", "and the deck", "over the roofs", ""])
    return {"kind": "clocktower", "side": S, "height": top + 1, "faces": 4, "signs": signed,
            "treads": len(treads), "stair_lamps": stair_lamps,
            # THE TREADS THEMSELVES, in WORLD coordinates, so the headroom check and the build
            # read ONE list. Re-derived in a test from `_ring` and a remembered base course, the
            # check agrees with the build by repeating its arithmetic - and a flight whose whole
            # failure mode is arithmetic is the last place to allow that.
            "tread_cells": [list(f.at(ci, cd, th)) for (ci, cd, th) in treads],
            "climb_from": list(f.at(mid, 0, 2)),
            "gallery_at": list(f.at(mid, mid - 1, BELFRY_FLOOR + 1)),
            "deck_at": list(f.at(0, S - 3, TW + 2)),
            "contract": "a square tower of four stages - string courses, glazed slits, a clock "
                        "face on every side, a louvred belfry with a bell and a crenellated "
                        "crown - and A CLIMB THROUGH IT: a spiral stair off the door, one "
                        "course per tread, to a lit gallery you can see the zone out of, and a "
                        "ladder on to the crown deck"}


# ---------------------------------------------------------------------------- the graveyard

_SHAPES = ("round", "cross", "obelisk", "slab", "broken", "lean")


# What a marker actually LOOKS like, per shape: the properties a passer-by can tell apart. A
# `slab` and a `broken` are two cells whatever `tall` says, so their look is the stone alone - and
# a uniqueness rule keyed on (shape, tall, stone) therefore calls two identical slabs different.
_HEIGHTLESS = {"slab", "broken"}


def _headstone(w, f, kit, pal, i, d, seed, used=None):
    """One grave marker. NO TWO ARE THE SAME, and every cell is FACE-ADJACENT to another.

    A cell that touches its neighbour only at a corner is not attached to it - the trap that has
    cost this repo ear tips, ossicones and a detached tail - so the lean is built as two columns
    side by side rather than as a diagonal, and the broken stone's fallen piece lies on the
    ground beside its stump.

    **"NO TWO ARE THE SAME" IS A CONTRACT, SO IT IS ENFORCED AND NOT HOPED FOR.** Three
    independent hashes over 6 shapes, 3 heights and 10 stones is 110 distinguishable markers, and
    a field of 27 drawn from it by birthday collides: measured at the default site it shipped a
    matching pair, and the contract this build PRINTS said it could not. `used` carries the looks
    already standing and the salt is bumped until the look is new - deterministic, reproducible,
    and never `random`. The retry is bounded, because a field bigger than the vocabulary must
    repeat and looping for ever is a worse answer than repeating - and when it does repeat the
    build SAYS SO in `unverified` rather than printing a contract it has not kept.
    """
    used = used if used is not None else set()
    for salt in range(64):
        r = hash01(seed, i, d, salt)
        shape = _SHAPES[int(r * len(_SHAPES)) % len(_SHAPES)]
        stone = kit["stones"][int(hash01(seed, i, d, 7, salt) * len(kit["stones"]))
                              % len(kit["stones"])]
        tall = 1 + int(hash01(seed, i, d, 13, salt) * 3)
        look = (shape, stone) if shape in _HEIGHTLESS else (shape, stone, max(2, tall)
                                                            if shape != "round" else tall)
        if look not in used:
            break
    used.add(look)
    n = 0
    if shape == "round":
        for h in range(tall):
            w.put(*f.at(i, d, h), stone)
            n += 1
        w.put(*f.at(i, d, tall), kit["roof_slab"], type="bottom", waterlogged="false")
        n += 1
    elif shape == "cross":
        for h in range(max(2, tall) + 1):
            w.put(*f.at(i, d, h), stone)
            n += 1
        for k in (-1, 1):
            w.put(*f.at(i + k, d, max(2, tall) - 1), stone)
            n += 1
    elif shape == "obelisk":
        for h in range(max(2, tall) + 1):
            w.put(*f.at(i, d, h), stone)
            n += 1
        w.put(*f.at(i, d, max(2, tall) + 1), kit["railwall"], up="true", north="none",
              south="none", east="none", west="none", waterlogged="false")
        n += 1
    elif shape == "slab":
        w.put(*f.at(i, d, 0), stone)
        w.put(*f.at(i, d, 1), kit["roof_slab"], type="bottom", waterlogged="false")
        n += 2
    elif shape == "broken":
        w.put(*f.at(i, d, 0), stone)
        w.put(*f.at(i + 1, d, 0), kit["roof_slab"], type="bottom", waterlogged="false")
        n += 2
    else:
        # LEAN: two columns joined along their shared FACE, never a diagonal - a diagonal is not
        # a leaning stone, it is two stones that happen to line up. It needs two courses to lean
        # at all: at tall=1 the upper column had nothing beside it and shipped as a stray cell.
        t = max(2, tall)
        for h in range(t):
            w.put(*f.at(i, d, h), stone)
            n += 1
        for h in range(t - 1, t + 1):
            w.put(*f.at(i + 1, d, h), stone)
            n += 1
    return shape, n


def _graveyard(w: World, p: dict, ctx) -> dict:
    """A railed enclosure, a crossing of paths, a monument, a field of unrepeated stones - AND
    THE VAULT UNDER IT, which is the only thing here a visitor can do rather than look at.

    A graveyard is scenery by nature and this one was 991 blocks of it: you walked in through
    the gate, round the obelisk, and out again. What it has now is a WAY DOWN - a lit undercroft
    of niches with a sarcophagus in it, reached by six steps behind the monument and left the
    same way. It is a dead end on purpose. A dare with a reason to turn round is a better thing
    to put at the bottom of a stair than a loop with nothing in it, and it means the vault costs
    the enclosure no second gate.

    THE WELL IS CUT OUT OF THE GROUND PLANE, NOT INTO IT. `w.put` overwrites and cannot remove,
    so the six columns the steps descend through are named before the ground is laid and left
    out of it - and out of the path overlay, and out of the headstone grid, which would
    otherwise plant a marker in mid-air over the stair.
    """
    f = _Frame(p)
    pal = LANDS[p["land"]]
    kit = GOTHIC[p["land"]]
    a = _ax(f)

    W = max(21, int(p["width"] or 25))
    D = max(17, int(p["depth"] or 21))
    mi, md = W // 2, D // 2
    seed = abs(int(p["at"][0]) * 31 + int(p["at"][2]))

    vault = bool(p.get("vault", True))
    # THE HEAD OF THE STAIR CLEARS THE MONUMENT'S OWN BASE, which reaches to d = md + 2. Set one
    # cell nearer, the doorcase stood on the plinth and the first step was a block you could not
    # walk off - a build that audits clean, renders correctly and has no way into its own vault.
    v_d0, v_steps = md + 3, 6
    V_FLOOR, V_WALK, V_CEIL = -7, -6, -1
    well = ({(i, d) for i in range(mi - 1, mi + 2)
             for d in range(v_d0 + 1, v_d0 + 1 + v_steps)} if vault else set())

    _ground(w, f, -1, W, -1, D, pal["ground"], alt=kit["rough"], mix=0.22, holes=well)
    for i in range(-1, W + 1):
        for d in range(-1, D + 1):
            if (i, d) in well:
                continue
            if abs(i - mi) <= 1 or abs(d - md) <= 1:
                w.put(*f.at(i, d, -1), pal["path"])

    # THE ENCLOSURE: a dwarf wall carrying a railing, with piers on a rhythm and a gate opening.
    gate = set(range(mi - 1, mi + 2))
    for i in range(W):
        for d in range(D):
            if not (i in (0, W - 1) or d in (0, D - 1)):
                continue
            if d == 0 and i in gate:
                continue
            pier = (i % 6 == 0 and d in (0, D - 1)) or (d % 6 == 0 and i in (0, W - 1))
            if pier:
                for h in range(3):
                    w.put(*f.at(i, d, h), kit["dressed"])
                w.put(*f.at(i, d, 3), kit["roof_slab"], type="bottom", waterlogged="false")
            else:
                w.put(*f.at(i, d, 0), kit["stone"])
                axis = (a["ip"], a["im"]) if d in (0, D - 1) else (a["fwd"], a["back"])
                w.put(*f.at(i, d, 1), "iron_bars", **_pane(*axis))

    for i in (mi - 2, mi + 2):
        for h in range(5):
            w.put(*f.at(i, 0, h), kit["dressed"])
        _lamp_post(w, f, kit, pal, i, 0, 5, tall=1)
    for i in range(mi - 2, mi + 3):
        w.put(*f.at(i, 0, 5), kit["dressed"] if abs(i - mi) == 2 else pal["trim"])
    for i in (mi - 1, mi + 1):
        w.put(*f.at(i, 0, 4), kit["roof_stair"],
              facing=a["im"] if i < mi else a["ip"], half="top", shape="straight",
              waterlogged="false")

    # THE MONUMENT at the crossing: a stepped base and an obelisk with a lit corner at each foot.
    _fill(w, f, mi - 2, mi + 2, md - 2, md + 2, 0, kit["stone"])
    _fill(w, f, mi - 1, mi + 1, md - 1, md + 1, 1, pal["trim"])
    for h in range(2, 10):
        _weathered(w, f, mi, md, h, kit["dressed"], kit["stone"], 0.15)
    w.put(*f.at(mi, md, 10), kit["railwall"], up="true", north="none", south="none",
          east="none", west="none", waterlogged="false")
    w.put(*f.at(mi, md, 11), kit["bright"])
    for (i, d) in ((mi - 2, md - 2), (mi + 2, md - 2), (mi - 2, md + 2), (mi + 2, md + 2)):
        w.put(*f.at(i, d, 1), kit["dressed"])
        w.put(*f.at(i, d, 2), pal["light"], hanging="false", waterlogged="false")

    # THE STONES ARE ON A GRID THAT IS JITTERED AND THINNED, both by hash of the cell - a perfect
    # lattice is a car park and `random` is not reproducible. The jitter is in d only, so the
    # rows survive as rows and the whole field still reads as laid out by somebody.
    stones, kinds, looks = 0, {}, set()
    for i in range(2, W - 2, 3):
        for d0 in range(3, D - 2, 3):
            d = d0 + int(hash01(seed, i, d0, 3) * 3) - 1
            if abs(i - mi) <= 1 or abs(d - md) <= 1:
                continue                                    # the paths stay clear
            if abs(i - mi) <= 2 and abs(d - md) <= 2:
                continue                                    # ...and so does the monument's base
            if vault and abs(i - mi) <= 3 and d >= v_d0:
                continue                                    # ...and the vault's well and its rail
            if i + 1 > W - 2 or not 1 <= d <= D - 2:
                continue
            if hash01(seed, i, d0, 11) < 0.12:
                continue                                    # thinned, so the grid does not show
            shape, _n = _headstone(w, f, kit, pal, i, d, seed, used=looks)
            kinds[shape] = kinds.get(shape, 0) + 1
            stones += 1
    # LAMPS ON THE PATH, not among the stones: anywhere else and a post lands on a grave, which
    # `put` would happily overwrite and nothing would report.
    for i in range(3, W - 3, 7):
        if abs(i - mi) <= 2:
            continue
        _lamp_post(w, f, kit, pal, i, md, 0, tall=2)
    for d in range(3, D - 3, 7):
        if abs(d - md) <= 2 or (mi, d) in well:
            continue                       # ...and a post over the open well stands on nothing
        _lamp_post(w, f, kit, pal, mi, d, 0, tall=2)

    # ---- THE VAULT. Dug first, then the flight, because `_undercroft` lays a floor plane across
    # its whole rectangle and would bury the bottom tread under it.
    niches = lamps = 0
    v_land = None
    if vault:
        niches, lamps = _undercroft(w, f, kit, pal, mi - 5, mi + 5, v_d0 + 1, D - 2,
                                    V_FLOOR, V_WALK, V_CEIL, shaft=well)
        for i in range(mi + 3, mi + 6):
            w.put(*f.at(i, D - 3, V_WALK), kit["dressed"])
            w.put(*f.at(i, D - 3, V_WALK + 1), kit["roof_slab"], type="bottom",
                  waterlogged="false")
        v_land = _flight(w, f, kit, pal, mi - 1, mi + 1, v_d0, 0, v_steps, down=True,
                         support=kit["stone"], floor_to=V_FLOOR)
        # THE HEAD OF THE STAIR IS A DOORCASE, not a hole in the lawn. Two piers and a lintel is
        # the whole difference between "somebody dug here" and "there is a way down here" - the
        # void tower's rule, which is that openings and regularity are what read as built.
        for i in (mi - 2, mi + 2):
            for h in range(4):
                _weathered(w, f, i, v_d0, h, kit["dressed"], kit["stone"], 0.16)
            _lamp_post(w, f, kit, pal, i, v_d0, 4, tall=1)
        for i in range(mi - 2, mi + 3):
            w.put(*f.at(i, v_d0, 4), pal["trim"] if abs(i - mi) < 2 else kit["dressed"])
        # ...and a rail down both sides of the well, standing on the ground it borders.
        for d in range(v_d0 + 1, v_d0 + 1 + v_steps):
            for i in (mi - 2, mi + 2):
                if w.has(*f.at(i, d, -1)) and not w.has(*f.at(i, d, 0)):
                    w.put(*f.at(i, d, 0), pal["fence"], north="false", south="false",
                          east="false", west="false", waterlogged="false")

    title = str(p.get("title") or "HOLLOW GROUND").upper()
    signed = 0
    if p.get("sign", True):
        # ON THE LINTEL, NOT IN THE GATEWAY. `mi` at h=4 is the opening the wall loop left
        # empty, so a sign there has nothing behind it - the park's own four-sign bug.
        signed += _sign(w, f, pal, mi, -1, 5, f.facing,
                        [title[:SIGN_WIDTH], "there is a way", "down, behind", "the monument"])
        if vault:
            # ON THE PIER, because the doorcase's opening has nothing behind it - the same
            # column-with-a-hole-in-it that shipped four floating signs in `gen/park.py`.
            signed += _sign(w, f, pal, mi - 1, v_d0, 3, a["ip"],
                            ["THE VAULT", "six steps down", "and the same", "six back up"])
    return {"kind": "graveyard", "width": W, "depth": D, "stones": stones, "shapes": kinds,
            "looks": len(looks), "signs": signed,
            "vault": bool(vault), "niches": niches, "vault_lamps": lamps,
            "gate_at": list(f.at(mi, 0, 0)),
            "vault_at": (list(f.at(mi, v_land[0], V_WALK)) if v_land else None),
            "sarcophagus_at": (list(f.at(mi + 4, D - 4, V_WALK)) if v_land else None),
            "contract": "a railed enclosure with one gate, a crossing of paths, a lit monument "
                        "at the centre, at least twelve grave markers of which no two share "
                        "a shape, a height and a material - guaranteed by construction up to the "
                        "110 markers the vocabulary holds (six shapes, their real heights, ten "
                        "stones), which a field of 37x33 does not reach - and a VAULT under it, "
                        "walkable down from the gate and back",
            "unverified": ([] if len(looks) == stones else
                           ["%d of %d markers repeat a look: the field is bigger than the "
                            "110-marker vocabulary" % (stones - len(looks), stones)])}


# ---------------------------------------------------------------------------- the dead tree

def _deadtree(w: World, p: dict, ctx) -> dict:
    """A bare tree. EVERY CELL IS PLACED BY A SINGLE-AXIS STEP, so the whole thing is one piece.

    A branch drawn as a diagonal line is not a branch, it is a row of separate blocks that
    happen to line up - the same 6-connectivity trap that broke the leopard's ear tips and
    detached the giraffe's ossicones. The walker below moves ONE axis per step and nothing else,
    so connectivity is a property of the algorithm rather than something to test for afterwards.
    """
    f = _Frame(p)
    pal = LANDS[p["land"]]
    kit = GOTHIC[p["land"]]

    H = max(9, int(p["height"] or 15))
    seed = abs(int(p["at"][0]) * 17 + int(p["at"][2]) * 3)
    _ground(w, f, -3, 9, -3, 9, pal["ground"], alt=kit["rough"], mix=0.30)

    ax_i = "x" if f.sx else "z"
    ax_d = "x" if f.dx else "z"

    def log(i, d, h, axis="y"):
        w.put(*f.at(i, d, h), kit["log"], axis=axis)

    # THE TRUNK IS ONE CELL FOR MOST OF ITS HEIGHT. Built with a five-cell buttress for the
    # bottom quarter it came out as a stump with twigs on it - at this scale a trunk two cells
    # thick anywhere above the foot is a tower, not a tree. The flare is the bottom TWO courses
    # and nothing else, and the taper after that is the whole silhouette.
    ci, cd = 3, 3
    for h in range(H):
        log(ci, cd, h)
        if h == 0:
            for (di, dd) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                log(ci + di, cd + dd, 0)
        elif h == 1:
            log(ci, cd + 1, h)
        if h in (H // 3, 2 * H // 3):        # the lean: BOTH cells exist at the step course
            log(ci + 1, cd, h)
            ci += 1
            log(ci, cd, h)

    # ROOTS, so the trunk meets the ground in something other than a line.
    roots = 0
    for (di, dd) in ((2, 0), (-2, 0), (0, 2), (0, -2)):
        log(3 + di, 3 + dd, 0, axis=ax_i if di else ax_d)
        roots += 1

    # THE BRANCHES. Six, from six heights up the leader, each a single-axis walk - and every one
    # of them REACHES OUT rather than up, with a droop at the end, because a dead tree's line is
    # horizontal. Steps are one axis at a time, so connectivity is a property of the walk.
    branches, tips = 0, []
    for b in range(6):
        h = H // 3 + (b * (H - H // 3 - 2)) // 5
        si = 1 if b % 2 else -1
        sd = 1 if (b // 2) % 2 else -1
        i, d, y = ci if h > 2 * H // 3 else ci - 1, cd, h
        if h <= H // 3:
            i = 3
        steps = 5 + int(hash01(seed, b, 5) * 4)
        for k in range(steps):
            r = hash01(seed, b, k)
            droop = k > steps - 3
            if r < 0.42:
                i += si
                log(i, d, y, axis=ax_i)
            elif r < 0.66:
                d += sd
                log(i, d, y, axis=ax_d)
            elif r < 0.86 and not droop:
                y += 1
                log(i, d, y)
            elif droop:
                y -= 1
                log(i, d, y)
            else:
                i += si
                log(i, d, y, axis=ax_i)
        tips.append((i, d, y))
        branches += 1

    # twigs at the tips, and one lantern hung from a branch - a full log above it, by definition
    for k, (i, d, y) in enumerate(tips):
        w.put(*f.at(i, d, y - 1), pal["fence"], north="false", south="false", east="false",
              west="false", waterlogged="false")
        if k == 0:
            _hang(w, f, pal, i, d, y - 1, kit["log"])
        if k == 3:
            w.put(*f.at(i, d, y - 1), "cobweb")
    return {"kind": "deadtree", "height": H, "branches": branches, "roots": roots,
            "contract": "a tapering leaning trunk with six branches, every one of them walked "
                        "one axis at a time so the whole tree is a single 6-connected piece"}


# ---------------------------------------------------------------------------- the iron gate

def _irongate(w: World, p: dict, ctx) -> dict:
    """A gothic railing with piers, spear finials and one arched gate opening."""
    f = _Frame(p)
    pal = LANDS[p["land"]]
    kit = GOTHIC[p["land"]]
    a = _ax(f)
    mr = int(p["min_run"])

    L = max(15, int(p["width"] or 23))
    gm = L // 2
    _ground(w, f, -2, L + 1, -3, 3, pal["path"], alt=pal["ground"], mix=0.28)
    for i in range(-1, L + 1):
        w.put(*f.at(i, 0, 0), kit["stone"])

    # THE PIER RHYTHM IS MEASURED OUT FROM THE GATE, not from i=0, so every railing panel between
    # two piers is the same width. On a plain `i % 5` rhythm the gate fell wherever it fell and
    # left panels of one and two cells beside it - `min_run`'s confetti, in ironwork.
    pier_at = {i for i in range(L) if (i - (gm + 2)) % 4 == 0} | {0, L - 1}
    pier_at |= {gm - 2, gm + 2}
    pier_at = {i for i in pier_at if 0 <= i < L and abs(i - gm) >= 2}
    # ...and any panel the rhythm still leaves short becomes solid pier rather than a stub run.
    run, short = [], set()
    for i in list(range(L)) + [None]:
        if i is not None and i not in pier_at and abs(i - gm) > 2:
            run.append(i)
        else:
            if 0 < len(run) < 3:
                short |= set(run)
            run = []
    pier_at |= short

    piers, bars, spikes, panel = 0, 0, 0, 0
    for i in range(L):
        if abs(i - gm) <= 2:
            continue
        if i in pier_at:
            for h in range(1, 4):
                _weathered(w, f, i, 0, h, kit["dressed"], kit["stone"], 0.18)
            w.put(*f.at(i, 0, 4), kit["roof_slab"], type="bottom", waterlogged="false")
            piers += 1
        else:
            for h in range(1, 4):
                w.put(*f.at(i, 0, h), "iron_bars", **_pane(a["ip"], a["im"]))
                bars += 1
            # SPEAR FINIALS: every other BAR carries a fourth, counted off the bars themselves
            # and not off `i`. On `i % 2` the rhythm is measured against the frame rather than
            # against the railing, and since the panels between piers are three bars wide and
            # start on whatever parity the gate's own offset produced, exactly ONE bar in three
            # got a spike - a run of finials the docstring described and the build did not have.
            panel += 1
            if panel % 2:
                w.put(*f.at(i, 0, 4), "iron_bars", **_pane(a["ip"], a["im"]))
                spikes += 1

    # THE GATE: two tall piers, an arch sprung off a stair either side, and a lit finial on each.
    for i in (gm - 2, gm + 2):
        for h in range(1, 7):
            _weathered(w, f, i, 0, h, kit["dressed"], kit["stone"], 0.16)
        w.put(*f.at(i, 0, 8), kit["railwall"], up="true", north="none", south="none",
              east="none", west="none", waterlogged="false")
        w.put(*f.at(i, 0, 9), kit["dressed"])
        w.put(*f.at(i, 0, 10), pal["light"], hanging="false", waterlogged="false")
        piers += 1
    for i in (gm - 1, gm + 1):
        w.put(*f.at(i, 0, 6), kit["roof_stair"], facing=a["im"] if i < gm else a["ip"],
              half="top", shape="straight", waterlogged="false")
    for i in range(gm - 2, gm + 3):
        w.put(*f.at(i, 0, 7), pal["trim"])
    # a coping over the lintel - three cells, which is exactly `min_run`, so it draws
    _run(w, f, [(i, 0, 8) for i in range(gm - 1, gm + 2)], kit["roof_stair"], a["back"],
         half="bottom", min_run=mr)

    # BUTTRESSES, standing on their own plinth cells - a pier and a lintel with nothing at the
    # foot is two posts with a beam balanced on them.
    for i in (gm - 2, gm + 2):
        for d in (-1, 1):
            w.put(*f.at(i, d, 0), kit["stone"])
            w.put(*f.at(i, d, 1), kit["stone"])
            w.put(*f.at(i, d, 2), kit["roof_stair"],
                  facing=a["fwd"] if d < 0 else a["back"], half="bottom", shape="straight",
                  waterlogged="false")

    title = str(p.get("title") or "THE HOLLOW").upper()
    signed = 0
    if p.get("sign", True):
        signed += _sign(w, f, pal, gm, -1, 7, f.facing, [title[:SIGN_WIDTH], "", "", ""])
    return {"kind": "irongate", "length": L, "piers": piers, "bars": bars, "spikes": spikes,
            "signs": signed,
            "contract": "an iron railing on a stone plinth with piers on a rhythm, spear "
                        "finials, and one arched walk-through gate lit from both sides"}


# ---------------------------------------------------------------------------- the seance

def _seance(w: World, p: dict, ctx) -> dict:
    """THE SEANCE: press the bell-pull and the veil answers - one lamp, two, or all four.

    **THE ZONE HAD TWO BUTTON GAMES AND BOTH WERE THE SAME THING TO LOOK AT.** Fortune Wheel is a
    decoder (`casino.wheel`: one roll, three pockets, exactly one lights) and The Reckoning is a
    window gate (`casino.lucky_number`: one roll, pays on one value). Both are "press a button,
    a light comes on", and the casino's own record says what that produces - four verified
    mechanics in four identical booths read as four identical rooms. A third decoder would have
    been the same mistake a third time.

    So this is the ONE mechanic in the casino's library that the Hollow does not already have and
    that reads as a MAGNITUDE rather than as a pick: `circuits.bar`, where the analog level IS the
    display. The randomiser gives 1, 2 or 4 at equal odds and dust loses one per block, so a roll
    of L lights exactly the first L of four lamps - a meter, not a winner. A visitor learns the
    reading from the four signs above it and there is nothing to work out.

    **AN ANALOG VALUE CANNOT TRAVEL**, which is the constraint the whole casino turned on and the
    reason the meter is set FLUSH IN THE FLOOR rather than up the shrine's back wall where it
    would be easier to read. A roll of 4 reaches four blocks of dust; any climb, link or fan-out
    spends exactly the magnitude being displayed, and a repeater carries the signal only by
    destroying its value. So the bar sits at the comparator, at the machine's own course, and the
    signs come to it.

    NOT VERIFIED, and it travels in the sidecar: the DISTRIBUTION. Redstone is deterministic and
    the randomness comes from a dropper choosing uniformly among its occupied slots, which this
    simulator has no entities to model. `stock` names the exact item mix the odds rest on -
    minecraft.wiki's own 3-outcome mix - and a dropper loaded with anything else is a meter with
    made-up odds.
    """
    from . import circuits

    f = _Frame(p)
    pal = LANDS[p["land"]]
    kit = GOTHIC[p["land"]]
    a = _ax(f)
    mr = int(p["min_run"])

    W = max(13, int(p["width"] or 13))
    D = max(9, int(p["depth"] or 9))
    mid = W // 2
    LAMPS = 4

    # ---- THE MACHINE FIRST, AND THE PAD AFTER IT. Laid the other way round, the pad at h=-2
    # was already standing where the hopper, the comparator and all four lamps go, every one of
    # them was skipped by the never-overwrite rule, and what shipped was a dropper wired to
    # nothing: 997 correct blocks, a clean audit and a meter that could not light. The order is
    # the fix; a never-overwrite rule is only safe if the thing that must win goes down first.

    # ---- THE MACHINE, IN THE FLOOR PLANE. It is laid FIRST and the floor is filled round it, so
    # nothing of the paving can land on a component - `casino._link`'s fifth composition bug in a
    # row was a game drawing its floor first and swallowing every wire that crossed it.
    dirn = a["ip"]                                   # the bar runs along the frontage
    btn_at = f.at(mid - 3, 2, 0)
    # THE BUTTON STANDS ON A BLOCK AND THE WIRE STARTS BESIDE THAT BLOCK. A button on the floor
    # powers its own support STRONGLY, and a strongly powered block drives adjacent dust - so
    # there is no wire under the button to turn the pad into redstone, which is the placement the
    # casino's floor button shipped once and the game does not allow.
    pulse = circuits.pulse(f.at(mid - 3, 4, -1), length=2, facing=f.back)
    # THE DROPPER SITS IN THE FLOOR PLANE, NOT ON IT, and that is a wiring decision rather than a
    # styling one: the trigger cell is at the dropper's own course, so with the dropper standing
    # a course proud of the pulse the two were one cell apart VERTICALLY and nothing joined them.
    # `connect` is planar, so it ran the L happily at the wrong height and delivered nothing -
    # the fault that broke four casino games in a row, each time looking like a different bug.
    # Sunk, the whole logic path is one plane and the meter lands one course under the paving,
    # which is where a meter you look DOWN at belongs.
    rnd = circuits.randomiser(f.at(mid - 2, 7, -1), outputs=3, facing=dirn)
    bar = circuits.bar(rnd["out"], lamps=LAMPS, facing=dirn)

    laid = {}
    for mod in (pulse, rnd, bar):
        laid.update(mod["cells"])
    # THE ENDS OF A LINK ARE ADDRESSES, NOT CELLS. `pulse["in"]` and `rnd["in"]` say where a
    # signal must ARRIVE; neither module emits a block there, and `connect` refuses to stand on
    # either endpoint - so left alone both are a one-cell gap that the floor pass then paves over.
    # The chain simulated as completely dead and every block in it was correct.
    for e in (pulse["in"], rnd["in"]):
        laid.setdefault(tuple(e), "redstone_wire")
    for pos, spec in circuits.connect(pulse["out"], rnd["in"])["cells"].items():
        laid.setdefault(pos, spec)
    for pos, spec in laid.items():
        if w.has(*pos):
            continue
        name, _, rest = spec.partition("[")
        props = {}
        if rest:
            for kv in rest.rstrip("]").split(","):
                k, _, v = kv.partition("=")
                props[k] = v
        w.put(pos[0], pos[1], pos[2], name, **props)
    for pos in list(laid):
        if not w.has(pos[0], pos[1] - 1, pos[2]):
            w.put(pos[0], pos[1] - 1, pos[2], kit["stone"])

    # ---- the shrine: a stone floor, a back screen with a gable, two returns, an open front.
    # **THE FLOOR IS LAID ROUND THE MACHINE, NEVER OVER IT.** `_fill` overwrites, and the first
    # build of this used it: the paving swallowed the hopper, the comparator and all four lamps,
    # and what shipped was a shrine with a dropper in it and no circuit at all - clean audit,
    # correct block count, and every lamp dark for ever. That is `casino._link`'s fifth
    # composition bug arriving from the opposite direction.
    # the pad, laid round whatever the machine already occupies
    for i in range(-3, W + 3):
        for d in range(-3, D + 3):
            x, y, z = f.at(i, d, -2)
            if not w.has(x, y, z):
                w.put(x, y, z, pal["ground"] if hash01(x, y, z) < 0.30 else pal["path"])

    # ...and the four lamps sit a course BELOW the paving, so the columns over them are left open:
    # a four-cell slot in the shrine floor that you stand in and read from above. Paved over, the
    # meter is a perfectly working machine nobody can see, which is this project's own favourite
    # way of shipping something broken.
    slot = {(c[0], c[2]) for c in bar["lamps"]}
    for i in range(-1, W + 1):
        for d in range(-1, D + 1):
            x, y, z = f.at(i, d, -1)
            if (x, z) in slot or w.has(x, y, z):
                continue
            w.put(x, y, z, pal["ground"])
    _box(w, f, 0, W - 1, 0, D - 1, 0, 4, pal["wall"], pal["post"],
         holes=[(i, 0, h) for i in range(1, W - 1) for h in range(5)]
               + [(i, d, h) for i in (0, W - 1) for d in range(1, 4) for h in range(5)],
         alt=kit["stone"])
    _proud_ring(w, f, 0, W - 1, 0, D - 1, 5, pal["trim"])
    _corbel_ring(w, f, 0, W - 1, 0, D - 1, 4, kit["roof_stair"], mr)
    for i in range(W):
        for d in range(D):
            w.put(*f.at(i, d, 6), kit["roof"])
    field = {(i, d): (7 + min(i, W - 1 - i) // 2, a["ip"] if i < mid else a["im"], i == mid)
             for i in range(W) for d in range(D)}
    _slope(w, f, field, 7, kit["roof"], kit["roof_stair"], kit["roof"], alt=kit["roof_alt"])

    # ---- the pedestal and the bell-pull. THE BUTTON DOES NOT STAND ON THE WIRE: the link starts
    # one cell away and the button powers it from the side, which is the fix the casino's floor
    # button needed after it turned its own pad into redstone dust.
    for h in range(0, 2):
        w.put(*f.at(mid - 3, 1, h), kit["dressed"])
    w.put(btn_at[0], btn_at[1] - 1, btn_at[2], kit["dressed"])
    w.put(btn_at[0], btn_at[1], btn_at[2], "stone_button", face="floor",
          facing=f.facing, powered="false")

    # ---- the readings, one sign per lamp, on the back wall above the meter
    reading = [["FAINT", "one lamp:", "nothing here", "but a draught"],
               ["STIRRING", "two lamps:", "something", "is listening"],
               ["", "", "", ""],
               ["THEY ARE HERE", "four lamps:", "do not turn", "round"]]
    signed = 0
    if p.get("sign", True):
        signed += _sign(w, f, pal, mid, D - 1, 3, f.facing,
                        [str(p.get("title") or "THE SEANCE")[:SIGN_WIDTH],
                         "press the pull", "1 in 3 each", "read the lamps"])
        for k, lamp in enumerate(bar["lamps"]):
            if not any(reading[k]):
                continue
            # THE SIGN GOES WHERE THE WALL IS, not where the lamp is. A lamp set in the floor has
            # nothing over it to hang from; the back screen is two cells behind and solid.
            si = mid - 3 + k
            if 0 < si < W - 1:
                signed += _sign(w, f, pal, si, D - 2, 2, f.facing, reading[k])

    lit = 0
    for (i, d) in ((1, D - 2), (W - 2, D - 2), (1, 1), (W - 2, 1)):
        _hang(w, f, pal, i, d, 4, pal["trim"])
        lit += 1
    for (i, d, h) in ((2, D - 3, 0), (W - 3, D - 3, 0)):
        _candle(w, f, i, d, h, count=3)
    _cobwebs(w, f, [(1, D - 2, 4), (W - 2, D - 2, 4)])

    return {"kind": "seance", "width": W, "depth": D, "signs": signed, "lamps": LAMPS,
            "inputs": [list(btn_at)], "outputs": [list(c) for c in bar["lamps"]],
            "rng_hopper": list(rnd["hopper"]), "lanterns": lit,
            "stock": {"dropper": rnd["stock"]},
            "contract": "press the pull once and the meter answers: a roll of 1, 2 or 4 at equal "
                        "odds lights exactly the first 1, 2 or 4 of four lamps, and nothing is "
                        "lit at rest",
            "unverified": [circuits.RANDOM_NOTE]}


BUILDERS = {
    "manor": _manor,
    "seance": _seance,
    "ossuary": _ossuary,
    "crypt": _crypt,
    "clocktower": _clocktower,
    "graveyard": _graveyard,
    "deadtree": _deadtree,
    "irongate": _irongate,
}


def build(cfg: dict, donors=None) -> Canvas:
    p = {**HOLLOW, **cfg}
    if not p.get("at"):
        raise ValueError("hollowmanor needs params.at = [x, y, z] of the front-left floor corner")
    if p["facing"] not in _STEP:
        raise ValueError(f"facing must be one of {sorted(_STEP)}")
    # AN UNKNOWN KIND RAISES. Defaulting to the first builder is how a config typo ships a manor
    # where a crypt was asked for, silently, and looks like the planner siting the wrong module.
    if p["kind"] not in BUILDERS:
        raise ValueError(f"unknown hollowmanor kind {p['kind']!r}; have {sorted(BUILDERS)}")
    if p["land"] not in LANDS or p["land"] not in GOTHIC:
        raise ValueError(f"unknown land {p['land']!r}; have {sorted(GOTHIC)}")

    w = World()
    ctx = Ctx(p["under"]) if p.get("under") else None
    meta = BUILDERS[p["kind"]](w, p, ctx)

    return w.canvas({
        "kind": f"hollow/{p['kind']}",
        "land": p["land"],
        "facing": p["facing"],
        "contract": meta.get("contract", ""),
        "unverified": meta.get("unverified", []),
        **{k: v for k, v in meta.items() if k not in ("contract", "unverified")},
    })
