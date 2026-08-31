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
    manor        width 32, depth 24            42  x  35  x  45   10,362   as clamped
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


def _ground(w, f, i0, i1, d0, d1, block, h=-1, alt=None, mix=0.0):
    """The pad. RULE 11: a skyblock plot is VOID, so every structure brings its own floor."""
    n = 0
    for i in range(i0, i1 + 1):
        for d in range(d0, d1 + 1):
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


# ---------------------------------------------------------------------------- the manor

def _manor(w: World, p: dict, ctx) -> dict:
    """THE SIGNATURE MASS. Three storeys, a gabled roof with three cross-gables, a corner tower.

    It is built in the order a mason would: pad, plinth, walls, floors, string courses, cornice,
    roof, then the entrance bay, the tower and the chimneys OVER the top of them - so the bay
    interrupts the string course exactly as a projecting bay does in stone, and the turret grows
    THROUGH the gable end rather than standing beside it.
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

    # ---- pad and plinth. A stepped plinth is what stops a wall meeting the ground at a line.
    _ground(w, f, -3, W + 2, -8, D + 2, pal["path"], alt=pal["ground"], mix=0.30)
    _ground(w, f, W - 4, W + 6, -3, 7, pal["path"], alt=pal["ground"], mix=0.30)
    _fill(w, f, -1, W, -4, D, 0, pal["trim"])
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

    # ---- floors, a ceiling, partitions and the stair turret. AN INTERIOR, NOT A SHELL.
    holes_floor = {(2, D - 4), (2, D - 5)}
    for k in (1, 2):
        _fill(w, f, 1, W - 2, 1, D - 2, F0 + k * SH - 1, kit["timber"], holes=holes_floor)
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

    # ---- the nameplate, over the porch, on the bay's own front wall
    title = str(p.get("title") or "HOLLOW MANOR").upper()
    signed = 0
    if p.get("sign", True):
        signed += _sign(w, f, pal, bmid, -4, F0 + 3, f.facing,
                        [title[:SIGN_WIDTH], "", "", ""])
        signed += _sign(w, f, pal, bi0 + 1, -4, F0 + 2, f.facing,
                        ["THE HOLLOW", "no callers", "after dusk", ""])

    return {"kind": "manor", "width": W, "depth": D, "storeys": STOREYS,
            "wall_top": TOP, "ridge": RIDGE, "tower_top": TW + 3 + len(spire),
            "windows": len(windows), "chimneys": stacks, "signs": signed,
            "contract": "three storeys with a floor at each, a gabled roof carrying three "
                        "cross-gables, and a corner tower standing clear above the ridge - "
                        "intact and imposing first, with two boarded lights as the only damage"}


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

def _clocktower(w: World, p: dict, ctx) -> dict:
    """A square tower with a stage per string course, a clock on all four faces, and a belfry.

    THE CLOCK IS THE ONLY BRIGHT THING FOR A HUNDRED BLOCKS, which is the whole reason it reads:
    white_wool (236) on a blackstone shaft (45) is the widest value step this economy has at
    cheap tier, and the hands are the dark end of the same ladder (21).
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
    for (i, d, h) in louvres:
        face = a["back"] if d == 0 else a["fwd"] if d == S - 1 else (
            a["ip"] if i == 0 else a["im"])
        w.put(*f.at(i, d, h), kit["trapdoor"], facing=face, half="top" if h % 2 else "bottom",
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

    # the belfry floor and a real bell hanging from it, then the crown. THE FLOOR AND THE DECK
    # BOTH NEED A HATCH where the ladder passes, or the climb stops at a solid plate.
    _fill(w, f, 1, S - 2, 1, S - 2, BELFRY - 5, kit["timber"], holes={(1, S - 3)})
    # A BELL HANGS FROM A BEAM, and the beam has to reach the walls. Hung from a single block in
    # the middle of the belfry, the bell and its block were two cells floating in mid-air - the
    # audit passes them and the component count is the only thing that ever says so.
    for i in range(S):
        w.put(*f.at(i, mid, BELFRY - 1), kit["timber"])
    w.put(*f.at(mid, mid, BELFRY - 2), "bell", attachment="ceiling", facing=f.facing,
          powered="false")
    for h in range(2, TW + 2):
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

    title = str(p.get("title") or "THE HOUR").upper()
    signed = 0
    if p.get("sign", True):
        signed += _sign(w, f, pal, mid, -1, 6, f.facing,
                        [title[:SIGN_WIDTH], "", "it strikes", "thirteen"])
    return {"kind": "clocktower", "side": S, "height": top + 1, "faces": 4, "signs": signed,
            "contract": "a square tower of four stages: string courses, glazed slits, a clock "
                        "face on every side, a louvred belfry with a bell, and a crenellated "
                        "crown carrying a spire"}


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
    """A railed enclosure, a crossing of paths, a monument, and a field of unrepeated stones."""
    f = _Frame(p)
    pal = LANDS[p["land"]]
    kit = GOTHIC[p["land"]]
    a = _ax(f)

    W = max(21, int(p["width"] or 25))
    D = max(17, int(p["depth"] or 21))
    mi, md = W // 2, D // 2
    seed = abs(int(p["at"][0]) * 31 + int(p["at"][2]))

    _ground(w, f, -1, W, -1, D, pal["ground"], alt=kit["rough"], mix=0.22)
    for i in range(-1, W + 1):
        for d in range(-1, D + 1):
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
        if abs(d - md) <= 2:
            continue
        _lamp_post(w, f, kit, pal, mi, d, 0, tall=2)

    title = str(p.get("title") or "HOLLOW GROUND").upper()
    signed = 0
    if p.get("sign", True):
        # ON THE LINTEL, NOT IN THE GATEWAY. `mi` at h=4 is the opening the wall loop left
        # empty, so a sign there has nothing behind it - the park's own four-sign bug.
        signed += _sign(w, f, pal, mi, -1, 5, f.facing, [title[:SIGN_WIDTH], "", "", ""])
    return {"kind": "graveyard", "width": W, "depth": D, "stones": stones, "shapes": kinds,
            "looks": len(looks), "signs": signed,
            "contract": "a railed enclosure with one gate, a crossing of paths, a lit monument "
                        "at the centre, and at least twelve grave markers of which no two share "
                        "a shape, a height and a material - guaranteed by construction up to the "
                        "110 markers the vocabulary holds (six shapes, their real heights, ten "
                        "stones), which a field of 37x33 does not reach",
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


BUILDERS = {
    "manor": _manor,
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
