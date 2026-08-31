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
that is a deliberate refusal. `circuit.py` models wire, torches, levers, plates, repeaters,
comparators, observers, pistons and dispensers - it does not model DOORS, so a plate-and-iron-door
turnstile could not be asserted by simulation. This project's cardinal sin is shipping a machine
that looks like it works; `chase` and `vault` were both cut from the casino for exactly that. A
powered turnstile is a fine thing to add the day the simulator can judge one.

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
        "trim": "black_wool",
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


def _plaza(w: World, p: dict, ctx) -> dict:
    """The hub: paving with a radial pattern, a ring of lamp posts, and seating.

    A COVERING MODULE IS NOT COMPETING FOR SPACE, IT IS THE SPACE. Sited by the planner with
    `anchor: cover` exactly as the casino hall is, so it claims the ground between attractions
    rather than trying to find a free bay in a plane that is already full of them.
    """
    f = _Frame(p)
    pal = LANDS[p["land"]]
    width = max(9, int(p["width"]))
    depth = max(9, int(p["depth"]))
    cx, cd = width // 2, depth // 2

    # SEVEN THOUSAND IDENTICAL CELLS IS NOT A FLOOR, IT IS A SLAB - the casino hall's own lesson.
    # A world-aligned grid of dark lines with a checker between them, and an accent ring, takes
    # the dominant block well under half and costs nothing: all three materials are cheap.
    for i in range(width):
        for d in range(depth):
            wx, _wy, wz = f.at(i, d, -1)
            r = max(abs(i - cx), abs(d - cd))
            if r == min(cx, cd) - 2:
                blk = pal["accent"]
            elif wx % 8 == 0 or wz % 8 == 0:
                blk = pal["trim"]
            elif (wx + wz) % 2 == 0:
                blk = pal["ground"]
            else:
                blk = pal["path"]
            w.put(wx, f.y - 1, wz, blk)

    # Lamp posts on the ring. A POST CARRIES ITS OWN LANTERN from a full block, never from air.
    posts = 0
    step = max(4, min(width, depth) // 3)
    for i in range(2, width - 2, step):
        for d in range(2, depth - 2, step):
            if max(abs(i - cx), abs(d - cd)) != min(cx, cd) - 2:
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

    return {"kind": "plaza", "width": width, "depth": depth, "posts": posts,
            "contract": "the ground between attractions, paved on a world-aligned grid so it "
                        "stays aligned across module boundaries"}


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


BUILDERS = {
    "gate": _gate,
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
