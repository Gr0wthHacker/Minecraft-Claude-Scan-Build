"""The theme park: attractions built as STRUCTURES, never as creatures.

**WHY A PARK AND NOT A ZOO.** A zoo makes one promise about twenty times - *a stranger walks up
and names the animal* - and this system can keep it about eight times. Every cat and both bears
are retired on panel evidence, and the failure is structural rather than a matter of effort:
compound volumetric muscle is the single thing voxels render worst, and the jaguar at 2.6x and
60,000 blocks failed exactly as the 27-block one did. A park's variety comes from ARCHITECTURE
and LAYOUT instead, which is the strongest thing in this repo - the void tower, the sanctum, the
campanile and the casino hall all settled the same rule, and it governs every kind below:

    WHAT MAKES VOXELS READ AS ARCHITECTURE IS REGULARITY AND OPENINGS, NOT DAMAGE.

**AND GRASS IS CURRENCY.** `blocks.spendable("grass_block")` is False on this server, as is every
form of dirt. A naturalistic park of lawns is not expensive, it is unbuildable in bulk. Every
material named below was checked against `palette.tier`, `blocks.spendable` and
`blocks.available` before it was written down: all are spendable, 1.19-legal, and cheap except
`blackstone`, `cobbled_deepslate` and `deepslate_bricks`, which are `ok` and are used as LINES
rather than as fields - the same way every other design on this island uses them.

**THREE LANDS, DIFFERING BY PALETTE FAMILY RATHER THAN BY SIGNAGE.** Bright / warm / dark, wool /
wood / stone - three places you could tell apart from a screenshot:

    midway     wool and stone brick        the entrance, the plaza, the carnival
    frontier   spruce and cobble           the mine, the coaster, the canyon
    hollow     blackstone and deepslate    the haunted quarter - the repo's strongest idiom

**THE EXPANSION BAND MUST BE ADDITIVE.** The inner 100x100 of each 200x200 zone is built first
and the plot expands later, so nothing in the outer band may be load-bearing for the core. If the
core's paths, plaza or sightlines have to move when the plot grows, the expansion costs a
rebuild - so the planner sites every module against the CORE radius and the band only ever adds.

**NO UNVERIFIED MECHANISM SHIPS.** The gate's lanes are fence gates, not a powered turnstile, and
that stays true - this kind is architecture and nothing in it carries a signal. This project's
cardinal sin is shipping a machine that looks like it works; `chase` and `vault` were both cut
from the casino for exactly that.

**But the REASON recorded here was wrong and is corrected.** It said `circuit.py` "does not model
DOORS, so a plate-and-iron-door turnstile could not be asserted by simulation". It does:
`iron_door` has been in `circuit.OUTPUTS` and `circuit.DRIVEN` all along, so `powered()` answers
for a door exactly as it does for a lamp or a piston. `gen/ticketing.py` is the powered turnstile
that note said was a fine thing to add "the day the simulator can judge one" - it always could.
A stale claim about a tool's limits is worse than no note: it retires a feature nobody re-checks.

GEOMETRY, stated once because getting it wrong is invisible in every render:

    at       the structure's FRONT-LEFT floor corner, in world coordinates
    facing   the direction the FRONT looks out - a visitor stands in the +facing direction
    i        runs along the frontage (the side axis)
    d        runs from the front INTO the building; d=0 is the front wall
    h        courses up from the floor

so `at(i, d, h) = (x - dx*d + sx*i, y + h, z - dz*d + sz*i)`, the same arithmetic `casino._room`
uses. A wall sign hangs in the cell IN FRONT of its wall and its `facing` is the direction the
TEXT looks, which is away from the block holding it up.
"""
from __future__ import annotations

from .canvas import Canvas, hash01
from .vertical import Ctx, World

_STEP = {"north": (0, -1), "south": (0, 1), "west": (-1, 0), "east": (1, 0)}
_BACK = {"north": "south", "south": "north", "east": "west", "west": "east"}
_LEAN = {"east": "west", "west": "east", "north": "south", "south": "north"}

SIGN_WIDTH = 15         # a sign line clips mid-word past this; asserted, never hoped for
ROOM_H = 5              # floor to ceiling: four clear courses, which is a room not a corridor

LANDS = {
    "midway": {
        "ground": "stone_bricks",
        "path": "stone",
        "wall": "white_wool",
        # WOOL OFF THE GROUND. `trim` is not only wall cornices and crenellations - it is ALSO
        # the plaza's floor grid, the path kerbs, the terrace and pool beds, and the planting
        # kerbs, all of them the ground you actually walk on. `black_wool` (21) is a fine
        # CORNICE colour and a bad thing to be standing on. `blackstone` (38, ok tier) keeps the
        # same dark line - measured across families, not within one, which is the ladder rule
        # `test_every_land_can_actually_draw_a_line` checks: 236 (wall) - 38 (trim) is 198 apart,
        # nowhere near the 15-luminance floor below which a trim course stops reading as a line.
        "trim": "blackstone",
        "post": "oak_log",
        "beam": "oak_planks",
        "stair": "stone_brick_stairs",
        "slab": "stone_brick_slab",
        "fence": "oak_fence",
        "gate": "oak_fence_gate",
        "light": "lantern",
        # A CANOPY IS TWO COLOURS ALTERNATING, which is what says fairground. One colour is a roof.
        "canopy": ["red_wool", "white_wool"],
        "accent": "yellow_wool",
        "wood": "oak",
    },
    "frontier": {
        "ground": "cobblestone",
        "path": "stone",
        "wall": "spruce_planks",
        "trim": "stone_bricks",
        "post": "spruce_log",
        "beam": "spruce_planks",
        "stair": "spruce_stairs",
        "slab": "spruce_slab",
        "fence": "spruce_fence",
        "gate": "spruce_fence_gate",
        "light": "lantern",
        "canopy": ["spruce_planks", "stripped_oak_log"],
        "accent": "orange_wool",
        "wood": "spruce",
    },
    "hollow": {
        "ground": "polished_blackstone_bricks",
        "path": "cobbled_deepslate",
        # MEASURED, NOT CHOSEN. The wall was `polished_blackstone_bricks` - the land's own ground -
        # so the Hollow had no value step at all, which is this repo's most-repeated palette
        # mistake: three separate notes concluded that the economy has no value contrast, and all
        # three had searched inside ONE material family, where a ladder cannot exist by
        # construction. Across families the rungs are real:
        #     black_wool 21  ->  polished_blackstone_bricks 45  ->  deepslate_bricks 71
        # steps of 24 and 26, against the 15 below which shading stops reading as shading.
        "wall": "black_wool",
        "trim": "deepslate_bricks",
        "post": "blackstone",
        "beam": "dark_oak_planks",
        "stair": "polished_blackstone_brick_stairs",
        "slab": "polished_blackstone_brick_slab",
        "fence": "dark_oak_fence",
        "gate": "dark_oak_fence_gate",
        # THE ONE COLD LIGHT. The lowland stair already carries warm-above / cold-below; the
        # Hollow is where that gradient lands on the park.
        "light": "soul_lantern",
        "canopy": ["black_wool", "deepslate_bricks"],
        "accent": "purple_wool",
        "wood": "dark_oak",
    },
}

PARK = {
    "under": None,
    "at": None,                 # world (x, y, z): the FRONT-LEFT floor corner
    "kind": "stall",
    "facing": "east",
    "land": "midway",
    "title": None,              # what the sign over the door reads
    "lines": None,              # the four lines of the interior sign
    "width": 9,
    "depth": 7,
    "height": None,             # tower only; otherwise derived from the kind
    "lanes": 3,                 # gate: how many ways in
    "tiers": 4,                 # tower: how many storeys
    "min_run": 3,               # trim courses shorter than this are not drawn at all
    "sign": True,
}


# ---------------------------------------------------------------------------- geometry helpers

class _Frame:
    """The structure's own axes. Everything is placed through this, so a facing bug is one bug."""

    def __init__(self, p):
        self.x, self.y, self.z = (int(v) for v in p["at"])
        self.dx, self.dz = _STEP[p["facing"]]
        self.sx, self.sz = -self.dz, -self.dx
        self.facing = p["facing"]
        self.back = _BACK[p["facing"]]

    def at(self, i, d, h=0):
        return (self.x - self.dx * d + self.sx * i,
                self.y + h,
                self.z - self.dz * d + self.sz * i)

    def inward(self, i, d, width, depth):
        """Which way a wall cell's INTERIOR side faces, so a cornice stair leans into the room."""
        if d == 0:
            return self.back
        if d == depth - 1:
            return self.facing
        left = {"east": "north", "west": "south", "north": "west", "south": "east"}[self.facing]
        if i == 0:
            return _BACK[left]
        if i == width - 1:
            return left
        return None


def _pad(w, f, pal, width, depth, margin=1, block=None):
    """The floor the structure stands on. A skyblock plot is VOID, so every module brings its own."""
    n = 0
    for i in range(-margin, width + margin):
        for d in range(-margin, depth + margin):
            w.put(*f.at(i, d, -1), block or pal["ground"])
            n += 1
    return n


def _sign(w, f, pal, i, d, h, facing, front, back=()):
    """A wall sign in the cell IN FRONT of its wall, its text facing away from its support.

    **THE SUPPORT IS CHECKED, NOT ASSUMED, AND THIS IS WHY.** Written without the check, three of
    the seven kinds shipped a stray cell and a fourth shipped a sign attached to nothing - every
    one of them a sign hung on a column that has an OPENING in it. A gate's map board sat behind
    a lane, a tower's nameplate behind a window slit, a walkthrough's EXIT behind its own exit.
    The wall exists everywhere except the one column somebody chose to sign, and the mistake is
    invisible in every render: a wall sign floating in air draws exactly like one on a wall.

    A connectivity check catches only some of it - the stall's sign was 6-adjacent to the canopy
    above it and so counted as connected, while still having no block behind it to hang from, so
    the game would simply refuse to place it. The support test is the one that catches all four.

    Returns True if the sign was placed. A caller that ignores a False is asking for the bug back.
    """
    fdx, fdz = _STEP[facing]
    x, y, z = f.at(i, d, h)
    if not w.has(x - fdx, y, z - fdz):
        return False
    lines = [str(s)[:SIGN_WIDTH] for s in list(front)[:4]]
    lines += [""] * (4 - len(lines))
    w.put(x, y, z, f"{pal['wood']}_wall_sign", facing=facing, waterlogged="false")
    w.sign(x, y, z, front=lines,
           back=[str(s)[:SIGN_WIDTH] for s in list(back)[:4]], colour="white", glowing=True)
    return True


def _hang_light(w, f, pal, i, d, h):
    """A lantern hangs from a FULL block, so the cell above it is filled first.

    The lowland's own note: a lamp under a slab cap reads as 'hanging from air' in the audit,
    because a slab is not a full block.
    """
    w.put(*f.at(i, d, h + 1), pal["trim"])
    w.put(*f.at(i, d, h), pal["light"], hanging="true", waterlogged="false")


def _flush(w, f, pal, run, d, h, min_run, half="top"):
    if len(run) < min_run:
        return 0
    for (i, face) in run:
        w.put(*f.at(i, d, h), pal["stair"],
              facing=_LEAN[face], half=half, shape="straight", waterlogged="false")
    return len(run)


def _trim_run(w, f, pal, cells, h, min_run=3, half="top"):
    """Lay a stair course only where it makes a RUN, never on scattered cells.

    The deck soffit drew a coffer grid per cell and produced 215 runs of which 184 were one or two
    cells - confetti, in the loudest block available. A course shorter than `min_run` gets nothing.
    The gate runs on what is PLACED rather than on the candidates, because filtering after grouping
    ships a five-cell run as three scattered stairs - the soffit's bug wearing a different hat.
    """
    by_d = {}
    for (i, d, face) in cells:
        by_d.setdefault(d, []).append((i, face))
    laid = 0
    for d, row in by_d.items():
        row.sort()
        run = []
        for (i, face) in row:
            if run and i == run[-1][0] + 1:
                run.append((i, face))
            else:
                laid += _flush(w, f, pal, run, d, h, min_run, half)
                run = [(i, face)]
        laid += _flush(w, f, pal, run, d, h, min_run, half)
    return laid


def _walls(w, f, pal, width, depth, height, openings=(), corner=None, wall=None):
    """Four walls with corner pilasters. THE OPENINGS ARE LEFT EMPTY BY THE LOOP, never punched.

    Building the ring first and cutting a hole afterwards repaints cells that already exist - the
    void tower's crenellations shipped as a plain drum for exactly this reason, and nothing about
    the code looked wrong.
    """
    holes = set(openings)
    for i in range(width):
        for d in range(depth):
            if not (i in (0, width - 1) or d in (0, depth - 1)):
                continue
            is_corner = i in (0, width - 1) and d in (0, depth - 1)
            for h in range(height):
                if (i, d, h) in holes:
                    continue
                w.put(*f.at(i, d, h),
                      (corner or pal["trim"]) if is_corner else (wall or pal["wall"]))


def _cornice(w, f, pal, width, depth, height, min_run, skip=()):
    """The upside-down stair course under a ceiling. The vocabulary the corpus says we are seven
    times short of, and what stops a wall being a flat plane of one block."""
    holes = set(skip)
    cells = []
    for i in range(width):
        for d in range(depth):
            if not (i in (0, width - 1) or d in (0, depth - 1)):
                continue
            if (i, d) in holes:
                continue
            face = f.inward(i, d, width, depth)
            if face:
                cells.append((i, d, face))
    return _trim_run(w, f, pal, cells, height - 1, min_run)


def _crenellate(w, f, pal, width, depth, h):
    """Merlons on a course the wall loop LEFT EMPTY.

    Building a full ring here first and then alternating merlons over it repaints cells that
    already exist - it alternates perfectly and changes nothing, and the crown is a plain drum.
    And from directly above a merlon in the parapet's own colour is invisible, so the merlons
    take the dark trim: a plan view sees only the topmost cell.
    """
    n = 0
    for i in range(width):
        for d in range(depth):
            if not (i in (0, width - 1) or d in (0, depth - 1)):
                continue
            if (i + d) % 2:
                continue
            w.put(*f.at(i, d, h), pal["trim"])
            n += 1
    return n


# ---------------------------------------------------------------------------- the attractions

def _gate(w: World, p: dict, ctx) -> dict:
    """THE FRONT DOOR OF THE WHOLE PARK. Ticket booths, lanes you walk through, a name over it.

    A gatehouse rather than an arch, because you should pass THROUGH something: the front wall
    carries the lanes and the back wall carries matching openings, so the building is a threshold
    and not a facade with a hole in it.
    """
    f = _Frame(p)
    pal = LANDS[p["land"]]
    lanes = max(1, int(p["lanes"]))
    booth = 4
    # lanes separated by one-wide piers, a booth block at each end
    span = lanes * 2 + 1
    width = booth * 2 + span
    depth = max(5, int(p["depth"]))
    height = 7

    _pad(w, f, pal, width, depth, margin=2)

    lane_i = [booth + 1 + k * 2 for k in range(lanes)]
    holes = []
    for i in lane_i:
        for h in range(3):
            holes.append((i, 0, h))
            holes.append((i, depth - 1, h))

    _walls(w, f, pal, width, depth, height, openings=holes, corner=pal["post"])

    # A FENCE GATE, NOT A TURNSTILE. See the module docstring: a plate-and-iron-door turnstile
    # cannot be asserted by `circuit.py`, which has no model of a door, and an unverified
    # mechanism does not ship from this repo.
    for i in lane_i:
        w.put(*f.at(i, 0, 0), pal["gate"], facing=f.facing, open="false", in_wall="false")

    # THE LINTEL BAND over the lanes, so the openings read as an arcade rather than as damage.
    for i in range(booth, booth + span):
        w.put(*f.at(i, 0, 3), pal["trim"])
        w.put(*f.at(i, depth - 1, 3), pal["trim"])

    # Roof and parapet. The wall stops at `height`; the crenellation course is left EMPTY for
    # `_crenellate` to alternate into.
    for i in range(width):
        for d in range(depth):
            w.put(*f.at(i, d, height), pal["trim"])
    _crenellate(w, f, pal, width, depth, height + 1)
    _cornice(w, f, pal, width, depth, height, int(p["min_run"]))

    # TICKET BOOTHS: a counter and a window in each end block, facing the queue.
    for side in (0, 1):
        i0 = 1 if side == 0 else width - booth
        for i in range(i0, i0 + booth - 1):
            w.put(*f.at(i, 0, 1), pal["slab"], type="top", waterlogged="false")
        _sign(w, f, pal, i0, -1, 2, f.facing, ["TICKETS", "", "ask inside", ""])

    # LIGHT on the piers, and the park's name over the middle lane.
    for i in (booth, booth + span - 1):
        _hang_light(w, f, pal, i, -1, 3)
    title = str(p.get("title") or "THE PARK").upper()
    _sign(w, f, pal, booth + span // 2, -1, 4, f.facing,
          [title[:SIGN_WIDTH], "", "welcome", ""])

    # THE MAP BOARD, on the inside back wall where you arrive.
    # ON A PIER, NOT ON A LANE. `width // 2` lands on the middle lane, whose wall is an
    # OPENING for three courses - the map board hung there had nothing behind it and shipped as
    # the gate's one stray cell. `lane_i[0] - 1` is a pier and is solid by construction.
    _sign(w, f, pal, lane_i[0] - 1, depth, 2, f.back,
          ["PARK MAP", "left  frontier", "right hollow", "here  midway"])

    return {"kind": "gate", "width": width, "depth": depth, "height": height,
            "lanes": lanes, "lane_i": lane_i,
            "contract": "a threshold: lanes through the front wall and matching ones through the "
                        "back, so a visitor passes through the building rather than past it",
            "unverified": []}


def _arch(w: World, p: dict, ctx) -> dict:
    """A land's entry portal: two piers and a lintel over the path, with the land's name on it."""
    f = _Frame(p)
    pal = LANDS[p["land"]]
    width = max(5, int(p["width"]) | 1)
    height = max(5, int(p["height"] or 6))
    depth = 3

    _pad(w, f, pal, width, depth, margin=1, block=pal["path"])

    for d in range(depth):
        for h in range(height):
            w.put(*f.at(0, d, h), pal["post"])
            w.put(*f.at(width - 1, d, h), pal["post"])
    # the lintel, and a course of trim over it so the top reads as a line rather than an edge
    for i in range(width):
        for d in range(depth):
            w.put(*f.at(i, d, height), pal["wall"])
            w.put(*f.at(i, d, height + 1), pal["trim"])
    for i in (0, width - 1):
        _hang_light(w, f, pal, i, -1, height - 2)

    title = str(p.get("title") or p["land"]).upper()
    _sign(w, f, pal, width // 2, -1, height, f.facing, [title[:SIGN_WIDTH], "", "", ""])
    return {"kind": "arch", "width": width, "depth": depth, "height": height,
            "contract": "an opening you walk through, with the land's name over it"}


# ---------------------------------------------------------------------------- plaza landscaping
#
# THE PLAZA WAS A CAR PARK. A rendered establishing view of the midway showed one flat grey
# platform with a ferris wheel standing on it, and the numbers said the same thing measured: 81%
# of the ground was paved and only 48% carried anything three blocks tall - most of every zone was
# bare ground. This is the fix: planting beds, trees, a sunken court, a bedded pool, and a floor
# whose pattern actually changes near the hub.
#
# **GRASS AND DIRT ARE CURRENCY, SO NOTHING HERE ROOTS IN THEM.** Every plant is on `moss_block`,
# exactly as `gen/thicket.py` and `gen/streetfurniture.py::_planter` already do - the same
# `blocks.spendable` rule that kept the zoo out of this project keeps a lawn out of it too.
#
# **A DRIFT IS A PATCH, NEVER A DUSTING.** `_bed` copies the Thicket's own idiom rather than
# reinventing it: the interior fills SOLID and only the boundary is noised, because thresholding
# every cell against a falloff is what produced 191 blobs of which 75% were one or two cells the
# first time this project tried it.
#
# **THE TWO MAIN AVENUES ALWAYS CROSS THIS MODULE'S OWN CENTRE.** `planner._add_paths` sites the
# hub (this module, `anchor: cover`) and then runs both avenues through the hub's centre on the
# cardinal axes - so a plaza can compute exactly where they are with no plan data at all, and
# `_AVENUE_HALF` is kept well clear of the real avenue's own half-width (2) plus a spur's (1).
# What a plaza CANNOT know from here is where every other building's door and spur ended up - see
# the docstring on `_plaza` itself for what that costs and the one-line fix for it.
_AVENUE_HALF = 4

# Leaves per land, kept LOCAL rather than imported from `streetfurniture` - that module already
# imports FROM this one, and importing back would be circular. A few duplicated lines are cheaper
# than a coupling neither module needs.
_CANOPY = {
    "midway": ["oak_leaves", "azalea_leaves", "flowering_azalea_leaves"],
    "frontier": ["spruce_leaves", "oak_leaves"],
    "hollow": ["dark_oak_leaves", "spruce_leaves"],
}


def _clear_of(x, z, obstacles, span=0):
    """True if (x, z) is at least `span` clear of every obstacle box (world x0,z0,x1,z1)."""
    return not any(x0 - span <= x <= x1 + span and z0 - span <= z <= z1 + span
                   for (x0, z0, x1, z1) in obstacles)


def _plaza_tree(w, f, pal, land, ci, cd, seed):
    """A trunk and a wind-noised leaf blob - the ORGANIC counterpart to `streetfurniture`'s
    clipped topiary, so a plaza has both a gardener's hand and something that just grew.

    Rooted in the land's own wood (`pal['wood']`), so a midway tree is oak, a frontier tree is
    spruce and a hollow tree is dark oak - the same three-material discipline the rest of the
    park keeps.
    """
    trunk = f"{pal['wood']}_log"
    leaves = _CANOPY[land]
    leaf = leaves[int(hash01(ci, cd, seed, 1) * len(leaves)) % len(leaves)]
    trunk_h = 3 + int(hash01(ci, cd, seed, 2) * 3)          # 3..5 - small, a plaza tree not a ride
    for h in range(trunk_h):
        w.put(*f.at(ci, cd, h), trunk)
    top, r, n = trunk_h - 1, 2, 0
    for di in range(-r, r + 1):
        for dd in range(-r, r + 1):
            for dh in range(0, r + 2):
                dist = (di * di + dd * dd + (dh - 1) * (dh - 1)) ** 0.5
                if dist > r * (0.72 + 0.45 * hash01(ci + di, cd + dd, top + dh, seed, 3)):
                    continue
                i, d, h = ci + di, cd + dd, top + dh
                if not w.has(*f.at(i, d, h)):
                    w.put(*f.at(i, d, h), leaf, persistent="true", waterlogged="false")
                    n += 1
    return {"trunk": trunk_h, "leaves": n}


def _plaza_bed(w, f, pal, ci, cd, seed):
    """A flush planting bed: a low kerb, moss soil, a drift planting inside - never confetti.

    THE DRIFT FILLS SOLID AND ONLY THE EDGE IS NOISED, the Thicket's own rule
    (`gen/thicket.py::build_thicket`, the floor-drift loop): thresholding every cell against a
    falloff is what turned a planting pass into 191 mostly one- and two-cell blobs the first time
    this repo tried it. A PLANT ROOTS IN THE DIRT FAMILY AND NOWHERE ELSE - moss_block, laid by
    this same function, is the only soil anything here is ever planted in.
    """
    rad = 2.7
    n = 0
    for di in range(-4, 5):
        for dd in range(-4, 5):
            dist = (di * di + dd * dd) ** 0.5
            if dist > rad + 1.0:
                continue
            i, d = ci + di, cd + dd
            if dist > rad:
                w.put(*f.at(i, d, 0), pal["trim"])                     # the kerb ring
                continue
            if dist > rad * (0.62 + 0.5 * hash01(i, d, seed, 5)):
                w.put(*f.at(i, d, 0), "moss_carpet")                   # the ragged fringe
            else:
                w.put(*f.at(i, d, 0), "moss_block")
                roll = hash01(i, d, seed, 6)
                if roll < 0.30:
                    w.put(*f.at(i, d, 1),
                          "flowering_azalea" if hash01(i, d, seed, 7) < 0.35 else "azalea")
                elif roll < 0.60:
                    w.put(*f.at(i, d, 1), "fern")
                elif roll < 0.82:
                    w.put(*f.at(i, d, 1), "short_grass")
                # else: bare moss - a drift is not solid planting either
            n += 1
    return n


def _terrace_sunk(ci, cd, r=4):
    """The (i, d) cells a sunken terrace will leave OPEN, so the main floor loop can skip them.

    A LITEMATIC CANNOT EXPRESS REMOVAL. If the plaza's own floor loop writes a solid block into
    every one of these cells first - which it does, by default, across the whole footprint - a
    later `w.put` for the terrace's kerb and steps cannot un-place it: the dict just keeps the
    newest write, and the pit's own floor already has a lid on it. So the deep interior is
    computed BEFORE the floor loop runs and excluded from it, the same way `Falls`'s dig list is
    computed before anything is placed.
    """
    W = D = 2 * r + 1
    return {(ci - r + li, cd - r + ld)
            for li in range(W) for ld in range(D)
            if 2 <= li <= W - 3 and 2 <= ld <= D - 3}


def _plaza_terrace(w, f, pal, ci, cd, r=4):
    """A one-course sunken court: a rim you can sit on, a ring of steps down, a floor a course
    below the plaza's own. THE LEVEL CHANGE this park has never had.

    Three rings, each a different job: the RIM stays at the plaza's own floor height with a seat
    slab on it, so the court reads as part of the plaza rather than a hole cut into it; the TREAD
    ring is the step down, one stair per cell, leaning in the direction `_Frame.inward` already
    uses for every cornice in this file; the deep INTERIOR is a course lower again, left open by
    `_terrace_sunk` before the floor loop ever runs.
    """
    W = D = 2 * r + 1
    n = 0
    for li in range(W):
        for ld in range(D):
            i, d = ci - r + li, cd - r + ld
            if li in (0, W - 1) or ld in (0, D - 1):
                w.put(*f.at(i, d, -1), pal["ground"])
                w.put(*f.at(i, d, 0), pal["slab"], type="bottom", waterlogged="false")
            elif li in (1, W - 2) or ld in (1, D - 2):
                w.put(*f.at(i, d, -2), pal["trim"])
                if li == 1:
                    face = f.inward(0, ld, W, D)
                elif li == W - 2:
                    face = f.inward(W - 1, ld, W, D)
                elif ld == 1:
                    face = f.inward(li, 0, W, D)
                else:
                    face = f.inward(li, D - 1, W, D)
                w.put(*f.at(i, d, -1), pal["stair"], facing=_LEAN[face] if face else f.back,
                      half="bottom", shape="straight", waterlogged="false")
            else:
                w.put(*f.at(i, d, -2), pal["trim"] if (i + d) % 2 == 0 else pal["path"])
            n += 1
    # corner piers, so the rim carries light as well as somewhere to sit
    for (li, ld) in ((0, 0), (0, D - 1), (W - 1, 0), (W - 1, D - 1)):
        i, d = ci - r + li, cd - r + ld
        for h in range(3):
            w.put(*f.at(i, d, h), pal["post"])
        w.put(*f.at(i, d, 3), pal["light"], hanging="false", waterlogged="false")
    return n


def _plaza_pool(w, f, pal, ci, cd, r=3):
    """A bedded, kerbed still pool, flush with the plaza floor.

    MUST BE BOTH BEDDED AND ENCLOSED, or it is not still water in six months. `_SOIL`-style rules
    do not apply to a fluid: what a pool needs is a SOLID block under every water cell (the bed,
    laid here before the water) and a solid wall on every side at the water's own height (the
    kerb ring), because a source with an open lateral neighbour spreads and a source with an open
    cell beneath it drains. Both are true here by construction - the ring is drawn first and the
    interior is entirely enclosed by it.
    """
    W = D = 2 * r + 1
    n = 0
    for li in range(W):
        for ld in range(D):
            i, d = ci - r + li, cd - r + ld
            if li in (0, W - 1) or ld in (0, D - 1):
                w.put(*f.at(i, d, -1), pal["ground"])
                w.put(*f.at(i, d, 0), pal["trim"])                     # the kerb, one block tall
            else:
                w.put(*f.at(i, d, -1), pal["trim"])                    # the bed
                w.put(*f.at(i, d, 0), "water")
                n += 1
    for (di, dd) in ((-1, -1), (1, 1)):
        i, d = ci + di, cd + dd
        if w.name(*f.at(i, d, 0)) == "water":
            # lily_pad carries no properties at all in 26.2 - the taproot's own note.
            w.put(*f.at(i, d, 1), "lily_pad")
    for (li, ld) in ((0, 0), (W - 1, D - 1)):
        i, d = ci - r + li, cd - r + ld
        for h in range(2):
            w.put(*f.at(i, d, h), pal["post"])
        w.put(*f.at(i, d, 2), pal["light"], hanging="false", waterlogged="false")
    return n


def _plaza(w: World, p: dict, ctx) -> dict:
    """The hub: paving with a radial pattern, a ring of lamp posts, planting, a sunken court, a
    pool, and trees - the ground between attractions, not a car park under them.

    A COVERING MODULE IS NOT COMPETING FOR SPACE, IT IS THE SPACE. Sited by the planner with
    `anchor: cover` exactly as the casino hall is, so it claims the ground between attractions
    rather than trying to find a free bay in a plane that is already full of them.

    **THE PLAZA CANNOT SEE THE OTHER BUILDINGS, AND THAT IS A REAL LIMIT, STATED RATHER THAN
    HIDDEN.** It always knows exactly where the two main avenues are - they always cross this
    module's own centre, by construction of `planner._add_paths` - so raised landscaping (trees,
    bed kerbs, the terrace, the pool) never stands on either of them. What it cannot know without
    help is where every OTHER building's door and spur ended up, because that is decided by
    `planner.make`'s siting pass and never reaches this generator. `params.obstacles` - a list of
    world `[x0, z0, x1, z1]` boxes, the exact shape `planner._box_of` already produces for every
    sibling module - closes that gap when supplied: any landscaping slot within `span` of an
    obstacle is skipped rather than placed blind. **THE RECOMMENDED WIRING** is one line in
    `planner._add_paths`, right where it already computes `obstacles` for the paths module: set
    `hub["params"]["obstacles"] = obstacles` on the same line. Left unwired, this module falls
    back to what the rest of the plaza has always done - the floor and the lamp ring have laid
    across the whole footprint with no obstacle awareness since the day this kind was written,
    and a building simply wins the cells it needs via `layers.slice_plan`'s first-writer-wins.
    """
    f = _Frame(p)
    pal = LANDS[p["land"]]
    land = p["land"]
    width = max(9, int(p["width"]))
    depth = max(9, int(p["depth"]))
    cx, cd = width // 2, depth // 2
    obstacles = [tuple(int(v) for v in b) for b in (p.get("obstacles") or [])]
    seed_base = int(hash01(cx, cd, sum(map(ord, land)), 97) * 1_000_000)

    def on_spine(i, d):
        """Both main avenues always cross this module's own centre - see the docstring."""
        return abs(i - cx) <= _AVENUE_HALF or abs(d - cd) <= _AVENUE_HALF

    def on_spine_near(i, d, pad):
        """...and the same question asked with room for the feature that will stand there."""
        return abs(i - cx) <= _AVENUE_HALF + pad or abs(d - cd) <= _AVENUE_HALF + pad

    # ---- lay out the set-pieces on a coarse grid, clear of the avenue cross and of any
    # obstacle the caller supplied. A grid rather than a hand-placed layout because a plaza this
    # size (up to 80x80) needs many independent tries at finding open ground, and each individual
    # try is cheap to lose - exactly the same reasoning `Island Night`'s greedy cover uses.
    margin = 9
    # **A COARSE GRID OF CANDIDATES IS NOT A SEARCH, AND IT WENT SILENT.** At a stride of 20 an
    # 80x80 plaza offers sixteen slots, and a real zone has fifteen buildings standing in it - so
    # every slot collided, the plaza planted NOTHING, and its own meta reported `trees: 0,
    # beds: 0, terrace: False, pool: False` while the design audited clean and shipped 6,405
    # cells of bare paving. That is this project's cardinal failure shape: a thing that does
    # nothing, quietly.
    #
    # The gaps between buildings are real ground and they are not on a 20-grid. Scan finely,
    # then thin the result so the set-pieces stay spread out rather than clustering in whichever
    # corner happens to be empty - which is what the coarse grid was really buying.
    # ...and the stride is 2, because 4 has a PARITY. With span 5 this plaza has exactly twelve
    # legal positions and a stride of 4 stepped over every one of them - the third time today a
    # stride hid the answer it was searching for. A clearance of 4 is what a bed and a tree
    # actually need; 5 was a guess, and on a zone this full a guess of one cell is the whole
    # feature.
    step = 2
    found = []
    i = margin
    while i <= width - margin:
        d = margin
        while d <= depth - margin:
            x0, _y0, z0 = f.at(i, d, 0)
            # **THE SLOT'S CENTRE CLEARING THE SPINE IS NOT ENOUGH - ITS RADIUS MUST.** A bed
            # is about four cells across from its centre, so a slot three cells off the avenue
            # puts planting IN the avenue. It passed while the candidate stride was 20 and
            # nothing ever landed that close; at a stride of 2 it fired immediately.
            if not on_spine_near(i, d, 5) and _clear_of(x0, z0, obstacles, span=4):
                found.append((i, d))
            d += step
        i += step
    # The thinning keeps set-pieces apart; too large a separation and a packed zone yields two
    # slots, which the terrace and the pool take, leaving nothing planted at all.
    spread = 10
    slots = []
    for (si, sd) in found:
        if all(max(abs(si - ai), abs(sd - ad)) >= spread for (ai, ad) in slots):
            slots.append((si, sd))

    sunk = set()
    terrace_at = pool_at = None
    features = []
    if slots:
        terrace_at = slots[0]
        pool_at = slots[-1] if len(slots) > 1 else None
        sunk = _terrace_sunk(*terrace_at, r=4)
        rest = [s for s in slots if s not in (terrace_at, pool_at)]
        for (si, sd) in rest:
            roll = hash01(si, sd, seed_base, 8)
            if roll < 0.38:
                features.append(("tree", si, sd))
            elif roll < 0.74:
                features.append(("bed", si, sd))
            # else: bare paving on purpose - not every corner of a real plaza is planted

    # SEVEN THOUSAND IDENTICAL CELLS IS NOT A FLOOR, IT IS A SLAB - the casino hall's own lesson.
    # A world-aligned grid of dark lines with a checker between them, and an accent ring, takes
    # the dominant block well under half and costs nothing: all three materials are cheap.
    #
    # AND THE PATTERN CHANGES NEAR THE HEART, so the ground itself says where you are: a finer
    # lattice within a few paces of the crossing, the ordinary coarse grid past it. `sunk` cells
    # are skipped here - see `_terrace_sunk` - or the terrace's own pit gets paved shut before it
    # is ever dug.
    for i in range(width):
        for d in range(depth):
            if (i, d) in sunk:
                continue
            wx, _wy, wz = f.at(i, d, -1)
            r = max(abs(i - cx), abs(d - cd))
            heart = r <= _AVENUE_HALF + 6
            if r == min(cx, cd) - 2:
                # THE OUTER RING IS FLOOR, NOT AN ACCENT. `pal["accent"]` is a wool the booth's
                # target board and the game rooms' rugs are for - a colour that means something
                # off the ground. On the ground it is the same "wool doing a floor's job" as the
                # grid lines it circles, so it draws with the same stone `trim` rather than its
                # own wool.
                blk = pal["trim"]
            elif heart and (wx % 4 == 0 or wz % 4 == 0):
                blk = pal["trim"]
            elif (not heart) and (wx % 8 == 0 or wz % 8 == 0):
                blk = pal["trim"]
            elif (wx + wz) % 2 == 0:
                blk = pal["ground"]
            else:
                blk = pal["path"]
            w.put(wx, f.y - 1, wz, blk)

    # Lamp posts on the ring. A POST CARRIES ITS OWN LANTERN from a full block, never from air.
    posts = 0
    step2 = max(4, min(width, depth) // 3)
    for i in range(2, width - 2, step2):
        for d in range(2, depth - 2, step2):
            if max(abs(i - cx), abs(d - cd)) != min(cx, cd) - 2:
                continue
            px, _py, pz = f.at(i, d, 0)
            if not _clear_of(px, pz, obstacles, span=2):
                continue
            for h in range(3):
                w.put(*f.at(i, d, h), pal["post"])
            w.put(*f.at(i, d, 3), pal["trim"])
            # A LANTERN ON TOP OF A POST STANDS ON IT; it does not hang. Written `hanging=true`
            # the lamp is looking for a block ABOVE it, finds open sky, and is a lantern hanging
            # from nothing - the exact fault rule 9 exists for, and the test caught it on all
            # three lands at once.
            w.put(*f.at(i, d, 4), pal["light"], hanging="false", waterlogged="false")
            posts += 1

    # ---- the set-pieces themselves, drawn after the floor so their own geometry wins
    if terrace_at:
        _plaza_terrace(w, f, pal, *terrace_at, r=4)
    if pool_at:
        _plaza_pool(w, f, pal, *pool_at, r=3)
    trees = beds = 0
    for (kind, si, sd) in features:
        seed = seed_base + si * 1009 + sd
        if kind == "tree":
            _plaza_tree(w, f, pal, land, si, sd, seed)
            trees += 1
        else:
            _plaza_bed(w, f, pal, si, sd, seed)
            beds += 1

    return {"kind": "plaza", "width": width, "depth": depth, "posts": posts,
            "trees": trees, "beds": beds, "terrace": bool(terrace_at), "pool": bool(pool_at),
            "contract": "the ground between attractions: a paved grid that changes near the "
                        "heart, planting beds and trees rooted in moss, a sunken seating court, "
                        "and a bedded pool - never a flat slab, and never dirt or grass"}


def _tower(w: World, p: dict, ctx) -> dict:
    """The landmark: a square tower with string courses, window slits and a crenellated deck.

    The void tower settled the shape of this and it is followed here: a flared plinth, regular
    coursework, real openings, a string course per tier, a corbelled overhang and a parapet. Its
    first attempt was a sheared jagged stub and was rejected on sight as *"a tossed grouping of
    vague blocks"*; what makes voxels read as a building is regularity, not damage.
    """
    f = _Frame(p)
    pal = LANDS[p["land"]]
    side = max(5, int(p["width"]) | 1)
    tiers = max(2, int(p["tiers"]))
    storey = 5
    height = tiers * storey

    _pad(w, f, pal, side, side, margin=2)
    # a flared plinth: one course proud of the shaft on every face
    for i in range(-1, side + 1):
        for d in range(-1, side + 1):
            w.put(*f.at(i, d, 0), pal["trim"])

    holes = []
    for t in range(tiers):
        base = 1 + t * storey
        # WINDOW SLITS, one per face per tier, two courses tall - an opening, not a hole
        for h in (base + 2, base + 3):
            holes.append((side // 2, 0, h))
            holes.append((side // 2, side - 1, h))
            holes.append((0, side // 2, h))
            holes.append((side - 1, side // 2, h))
    _walls(w, f, pal, side, side, height + 1, openings=holes, corner=pal["post"])

    # A STRING COURSE PER TIER. Blackstone cannot draw a value line on itself - the family sits
    # within 12 RGB - so the line is GEOMETRY here as well as tone: it is the darker trim AND it
    # stands one cell proud of the shaft.
    for t in range(1, tiers):
        h = t * storey
        for i in range(-1, side + 1):
            for d in range(-1, side + 1):
                if i in (-1, side) or d in (-1, side):
                    w.put(*f.at(i, d, h), pal["trim"])

    # The deck: a corbelled overhang, a floor, then a parapet whose crown course is left EMPTY.
    top = height + 1
    for i in range(-1, side + 1):
        for d in range(-1, side + 1):
            w.put(*f.at(i, d, top), pal["trim"])
    for i in range(-1, side + 1):
        for d in range(-1, side + 1):
            if i in (-1, side) or d in (-1, side):
                w.put(*f.at(i, d, top + 1), pal["wall"])
    for i in range(-1, side + 1):
        for d in range(-1, side + 1):
            if not (i in (-1, side) or d in (-1, side)):
                continue
            if (i + d) % 2:
                continue
            w.put(*f.at(i, d, top + 2), pal["trim"])

    # A LADDER, so the tower is a place you can be rather than a shape you look at. It climbs the
    # back wall inside, which is the one face carrying no window slit at its middle column.
    for h in range(1, top):
        w.put(*f.at(1, side - 2, h), "ladder", facing=f.facing, waterlogged="false")
    for i in (0, side - 1):
        _hang_light(w, f, pal, i, -1, top - 2)

    title = str(p.get("title") or "LOOKOUT").upper()
    # h=2, NOT h=3: the first tier's window slit occupies the middle column at h=3 and h=4,
    # which is exactly where a nameplate wants to go and exactly where there is no wall.
    _sign(w, f, pal, side // 2, -1, 2, f.facing, [title[:SIGN_WIDTH], "", "", ""])
    return {"kind": "tower", "side": side, "tiers": tiers, "height": top + 2,
            "contract": "a climbable landmark: a ladder to a crenellated deck, visible across "
                        "the zone"}


def _stall(w: World, p: dict, ctx) -> dict:
    """A food or souvenir stall: an open front, a counter, and a striped canopy.

    A STALL IS A SHOPFRONT, NOT A CELL. The casino's eighteen sealed grey cubes are the failure
    this avoids - you must be able to see in, and the canopy is what makes a row of them read as
    a street rather than as storage.
    """
    f = _Frame(p)
    pal = LANDS[p["land"]]
    width = max(5, int(p["width"]))
    depth = max(3, int(p["depth"]))
    height = 5

    _pad(w, f, pal, width, depth, margin=1)

    # back and sides only - the front is the shop window
    for i in range(width):
        for d in range(depth):
            back_or_side = d == depth - 1 or i in (0, width - 1)
            if not back_or_side:
                continue
            for h in range(height):
                w.put(*f.at(i, d, h), pal["wall"] if d == depth - 1 else pal["post"])

    # THE COUNTER, a top slab across the front so the opening is a serving hatch and not a hole.
    for i in range(1, width - 1):
        w.put(*f.at(i, 0, 0), pal["trim"])
        w.put(*f.at(i, 0, 1), pal["slab"], type="top", waterlogged="false")

    # THE FASCIA: the board a shop's name goes on, across the top of the opening. It is also the
    # only thing a front sign can hang from - an open front has no wall to attach one to, and
    # without it the nameplate is a sign floating in air that the game will not place.
    for i in range(width):
        w.put(*f.at(i, 0, height - 1), pal["trim"])

    # THE CANOPY: two colours alternating, overhanging the counter by one. One colour is a roof.
    a, b = pal["canopy"]
    for i in range(-1, width + 1):
        for d in range(-1, depth):
            w.put(*f.at(i, d, height), a if i % 2 == 0 else b)

    _hang_light(w, f, pal, width // 2, 1, height - 2)
    title = str(p.get("title") or "STALL").upper()
    signed = False
    if p.get("sign", True):
        signed = _sign(w, f, pal, width // 2, -1, height - 1, f.facing,
                       [title[:SIGN_WIDTH], "", "", ""])
    return {"kind": "stall", "width": width, "depth": depth, "height": height,
            "signed": signed,
            "contract": "an open-fronted shop: you can see in, the counter is reachable, and the "
                        "name hangs on a fascia that actually exists"}


def _booth(w: World, p: dict, ctx) -> dict:
    """A midway game booth: a stall with a target board and a prize shelf.

    THE ODDS GO ON THE SIGN. A house that will not print its odds does not know them - the rule
    the casino settled, and it applies to a coconut shy as much as to a slot machine. This kind
    builds the BOOTH; a verified `gen/casino.py` machine is what gets sited inside it, so nothing
    here invents a circuit.
    """
    f = _Frame(p)
    pal = LANDS[p["land"]]
    meta = _stall(w, p, ctx)
    width, depth, height = meta["width"], meta["depth"], meta["height"]

    # THE TARGET BOARD on the back wall, in the land's accent - the thing you actually look at.
    board = []
    for i in range(1, width - 1):
        for h in range(1, height - 1):
            blk = pal["accent"] if (i + h) % 2 == 0 else pal["trim"]
            w.put(*f.at(i, depth - 2, h), blk)
            board.append((i, h))

    # THE RULES GO INSIDE, ON THE BACK WALL, facing whoever is standing at the counter. It
    # replaces one board cell deliberately - the board is drawn first so the sign wins - because
    # the alternative is hanging it on the open front, which has nothing to hang it from.
    lines = list(p.get("lines") or ["", "", ""])
    _sign(w, f, pal, width // 2, depth - 2, 2, f.facing,
          [str(p.get("title") or "GAME").upper()[:SIGN_WIDTH]] + lines)
    return {**meta, "kind": "booth", "board": len(board),
            "contract": "a booth whose rules and odds are printed on its own sign",
            "unverified": ["the game machine inside is a separate, simulated module"]}


def _walkthrough(w: World, p: dict, ctx) -> dict:
    """A building you walk through: one way in, one way out, and a route between them.

    The Hollow's haunted house and the Frontier's mineshaft are the same structure with different
    palettes, which is the whole argument for a park over a zoo - the variety is in the shell.
    """
    f = _Frame(p)
    pal = LANDS[p["land"]]
    width = max(9, int(p["width"]))
    depth = max(9, int(p["depth"]))
    height = ROOM_H

    _pad(w, f, pal, width, depth, margin=1)

    door_i = width // 2
    exit_i = max(1, width // 4)
    holes = []
    for h in range(3):
        holes.append((door_i, 0, h))
        holes.append((exit_i, depth - 1, h))
    _walls(w, f, pal, width, depth, height, openings=holes, corner=pal["post"])

    # A CEILING, AND IT IS DARK. A bright lid over a dark floor reads as a lightwell; and a room
    # has a ceiling where a deck does not, which is the distinction the deck soffit settled after
    # a deck-wide "ceiling" came out as 25 lacy patches at six different heights.
    for i in range(width):
        for d in range(depth):
            w.put(*f.at(i, d, height), pal["trim"])

    # THE ROUTE: baffle walls that make you turn, rather than an empty box with two doors. Each
    # leaves a gap at the opposite end, so the path is a switchback and the building has an inside.
    turns = 0
    for k, d in enumerate(range(2, depth - 2, 3)):
        for i in range(width):
            near = i < width - 3 if k % 2 == 0 else i > 2
            if not near:
                continue
            for h in range(height):
                w.put(*f.at(i, d, h), pal["wall"])
        turns += 1

    _cornice(w, f, pal, width, depth, height, int(p["min_run"]))
    for d in range(1, depth - 1, 3):
        _hang_light(w, f, pal, width - 2 if (d // 3) % 2 else 1, d, height - 1)

    title = str(p.get("title") or "WALKTHROUGH").upper()
    _sign(w, f, pal, door_i, -1, 3, f.facing, [title[:SIGN_WIDTH], "", "", ""])
    # ABOVE the opening, not in it: the exit is a hole for three courses, so h=2 had nothing
    # behind it. A sign over a door is where one goes anyway.
    _sign(w, f, pal, exit_i, depth, 3, f.back, ["EXIT", "", "", ""])
    return {"kind": "walkthrough", "width": width, "depth": depth, "height": height,
            "turns": turns,
            "contract": "one way in at the front, one way out at the back, and a switchback "
                        "route between them - never an empty box with two doors"}


def _paths(w: World, p: dict, ctx) -> dict:
    """The streets: role-typed routes drawn at their declared capacity.

    **THE ROUTES ARE COMPUTED BY THE PLANNER, NOT HERE, AND THAT SPLIT IS THE POINT.** A path
    connects things, so the only place that can draw one is the place that knows where everything
    ended up - and a generator is handed one module's `at` and nothing else. `planner._add_paths`
    reads the sited plan, hands it to `circulation.build`, and passes the network in; this draws
    it.

    Without this the park was PACKED rather than COMPOSED: `bays` fills a grid, everything fit,
    nothing collided, and there was no street. A visitor arrived at a gate and faced a field with
    buildings scattered across it.

    **AND A ROLE IS DRAWN, NOT ONLY DECLARED.** A queue that looks exactly like a promenade is a
    queue nobody recognises as one, and rule 6 asks for queues that are separated and service
    routes that are hidden. So a queue gets a fenced kerb, an exit gets the land's own accent
    down its middle so it reads as a way OUT rather than a way in, and a service road is laid in
    the land's ground material with no kerb and no lamps - a back lane, not a street.
    """
    pal = LANDS[p["land"]]
    y = int(p["at"][1])
    routes = list(p.get("routes") or [])
    if not routes:
        raise ValueError("park/paths needs params.routes - the planner computes them")
    obstacles = [tuple(int(v) for v in b) for b in (p.get("obstacles") or [])]

    def blocked(x, z):
        return any(x0 <= x <= x1 and z0 <= z <= z1 for (x0, z0, x1, z1) in obstacles)

    laid, lamps, rails = 0, 0, 0

    def _leg(ax, az, bx, bz, route, y):
        """One straight run at its own course. An L is two of these; the corner belongs to both."""
        nonlocal laid, lamps, rails
        role = route.get("role", "secondary")
        half = max(1, int(route.get("width", 3))) // 2
        along_x = abs(bx - ax) >= abs(bz - az)
        n = max(abs(bx - ax), abs(bz - az))
        surface = pal["ground"] if role == "service" else pal["path"]
        for k in range(n + 1):
            cx = ax + (1 if bx > ax else -1) * min(k, abs(bx - ax)) if along_x else ax
            cz = az if along_x else az + (1 if bz > az else -1) * min(k, abs(bz - az))
            for o in range(-half, half + 1):
                x, z = (cx, cz + o) if along_x else (cx + o, cz)
                # THE PAVING IS LAID EVEN UNDER A BUILDING, deliberately: skipping obstacle cells
                # can SPLIT a route in two, and a network that is not connected is not a network.
                # A building's own pad occupies the same course and wins in `layers.slice_plan`,
                # so the overlap is invisible and the connectivity is guaranteed.
                if role == "service":
                    block = surface
                elif abs(o) == half:
                    block = pal["trim"]
                elif role == "exit" and o == 0:
                    block = pal["accent"]
                else:
                    block = surface
                w.put(x, y - 1, z, block)
                laid += 1
            # **A QUEUE IS FENCED, WHICH IS WHAT MAKES IT A QUEUE.** Rule 6 asks for queues
            # "separated"; a 3-wide strip of the same paving as the street beside it is not
            # separated by anything a guest can see. The rail goes on the kerb, and it stops at
            # anything already standing so it cannot fence off somebody's door.
            if role == "queue":
                for o in (-half, half):
                    x, z = (cx, cz + o) if along_x else (cx + o, cz)
                    if blocked(x, z):
                        continue
                    w.put(x, y, z, pal["fence"])
                    rails += 1
            # LAMP POSTS ON THE KERB, and only where the route asks for them - a lit spur to
            # every food stall is a lamp every four blocks, which reads as a fence rather than
            # as a street. A service road is never lit: it is meant to be missed.
            if route.get("lamps") and k and k % int(route.get("lamp_every", 12)) == 0:
                for o in (-half, half):
                    x, z = (cx, cz + o) if along_x else (cx + o, cz)
                    if blocked(x, z):
                        continue
                    for h in range(3):
                        w.put(x, y + h, z, pal["post"])
                    w.put(x, y + 3, z, pal["trim"])
                    # standing, not hanging: there is no block above a post top to hang from
                    w.put(x, y + 4, z, pal["light"], hanging="false", waterlogged="false")
                    lamps += 1

    for r in routes:
        # **A ROUTE MAY CARRY ITS OWN COURSE.** An underground landing is `[x, y, z]` and drawing
        # it at the paths module's own plane paves the mine's floor on top of the town - which is
        # what happened the first time a module moved off the plane. A two-element endpoint is
        # still the street.
        a, b = r["a"], r["b"]
        ax, az = (int(a[0]), int(a[2])) if len(a) > 2 else (int(a[0]), int(a[1]))
        bx, bz = (int(b[0]), int(b[2])) if len(b) > 2 else (int(b[0]), int(b[1]))
        ry = int(a[1]) if len(a) > 2 else y
        if r.get("role") == "shaft":
            # A shaft is a vertical run in one column: a landing at each end and the courses
            # between them left open, because what fills them is a stair the module's own
            # generator builds. Paving its whole column would seal the thing it exists to be.
            for course in (ry, int(b[1]) if len(b) > 2 else y):
                _leg(ax, az, bx, bz, r, course)
            continue
        if ax != bx and az != bz:
            # AN L IS TWO LEGS. The circulation builder emits them for a frontage walk that has
            # to travel along the avenue's own axis to get onto it, and drawing only the dominant
            # axis - which is what a single-leg walk does - silently loses the second half and
            # leaves the walk joined to nothing.
            _leg(ax, az, bx, az, r, ry)
            _leg(bx, az, bx, bz, r, ry)
        else:
            _leg(ax, az, bx, bz, r, ry)

    from collections import Counter
    by_role = Counter(r.get("role", "secondary") for r in routes)
    return {"kind": "paths", "routes": len(routes), "cells": laid, "lamps": lamps,
            "queue_rails": rails, "roles": dict(by_role),
            "contract": "every declared public interface is joined to the network, queues are "
                        "fenced and off the through-route, and the service road runs behind the "
                        "buildings unlit"}


BUILDERS = {
    "gate": _gate,
    "paths": _paths,
    "arch": _arch,
    "plaza": _plaza,
    "tower": _tower,
    "stall": _stall,
    "booth": _booth,
    "walkthrough": _walkthrough,
}


def build(cfg: dict, donors=None) -> Canvas:
    p = {**PARK, **cfg}
    if not p.get("at"):
        raise ValueError("park needs params.at = [x, y, z] of the front-left floor corner")
    if p["facing"] not in _STEP:
        raise ValueError(f"facing must be one of {sorted(_STEP)}")
    if p["kind"] not in BUILDERS:
        raise ValueError(f"unknown park kind {p['kind']!r}; have {sorted(BUILDERS)}")
    if p["land"] not in LANDS:
        raise ValueError(f"unknown land {p['land']!r}; have {sorted(LANDS)}")

    w = World()
    ctx = Ctx(p["under"]) if p.get("under") else None
    meta = BUILDERS[p["kind"]](w, p, ctx)

    return w.canvas({
        "kind": f"park/{p['kind']}",
        "land": p["land"],
        "facing": p["facing"],
        "contract": meta.get("contract", ""),
        "unverified": meta.get("unverified", []),
        **{k: v for k, v in meta.items() if k not in ("contract", "unverified")},
    })
