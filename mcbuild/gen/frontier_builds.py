"""THE FRONTIER LAND'S BUILDINGS: a gold-rush mining town on the six lots the grid leaves it.

`Park Ways` shipped the ground - lawn, spine, avenues, the back promenade, the cross walk, every
spur and every lamp - and `Park Rail` shipped the railway. `Mine Coaster` is the land's headline
ride and already stands. What was missing is the TOWN, and this module is it: six designs, one per
measured lot, and nothing else.

    Trailhead Gate       45 x 39  V24  U0    the threshold; faces west onto the spine
    Prospecting Porch    51 x 40  V69  U0    two game bays under one veranda; enters east, U39
    Boomtown Spine       53 x 46  V24  U47   Main Street, a real 5-wide street with real doors
    Mining Square        41 x 46  V80  U47   the choice point - an open SQUARE, not a building
    Assay & Prize Office 20 x 46  V130 U47   the civic range on the back promenade
    Works Yard           13 x 36  V157 U125  back of house, off the service lane

**EVERY CELL STAYS INSIDE ITS LOT, AND THAT IS ENFORCED HERE RATHER THAN HOPED FOR.** `_Lot.put`
refuses anything outside, because a cell over the boundary is CROPPED at placement and simply
disappears - so a part sitting past the line is not a collision you can see, it is a missing
gable that audits clean. This park has already lost the Mine Coaster's 71st column to a single
lamp post two cells outside an avenue; the whole grid was re-cut because of it.

**NO STREET FURNITURE.** No lamp post, bench, marker, notice pillar or apron belongs here: the
ground layer draws all of it across all 600 blocks, and a second pass of it on top is exactly the
"tons of stuff jumbled together" that got the previous park thrown away. Two things that look like
furniture are not, and both are program:

  * BOOMTOWN'S STREET IS INSIDE THE MODULE. `PARK_GRID_PLAN` §6.5(c) says so in as many words -
    "the Boomtown street is inside the module and belongs to whoever builds it. *No grid change
    wanted*" - so the boardwalk between its two terraces is the building, not paving added to it.
  * MINING SQUARE IS PAVING BY DEFINITION. Its role in `park_final.world.json` is `path`, and the
    grid re-specced it to 41 x 46 precisely so that an open square would fit. A square with no
    floor is a lawn.

**WHAT MAKES VOXELS READ AS ARCHITECTURE IS REGULARITY AND OPENINGS, NOT DAMAGE** - the void
tower's rule, settled when a jagged ruin was rejected on sight and a plain regular one with a door
and window slits worked immediately. So every building here has a plinth, a masonry base, a
string course, a framed timber storey, a head beam, real openings with jambs and a lintel, an
eave, and a roof that steps. Weathering is a hash on the CELL - hashed on the course, a course
comes out all one material and the wall is horizontal stripes, which the deck soffit shipped once.

THE VALUE LADDER IS MEASURED ACROSS FAMILIES, never inside one. Four separate notes in CLAUDE.md
conclude this economy has no value contrast and every one of them searched inside a single
material family, where a ladder cannot exist by construction. Measured with `blocks.color`:

    polished_blackstone_bricks  45  -> spruce_planks  89  -> stone_bricks 122 -> smooth_stone 159
                                   44                   33                   37

with `dark_oak` 46 for the roof against the 89 of the walls it sits on, `red_wool` 65 for paint
and `white_wool` 236 for a sign board. Every step is at least 33, against the ~15 below which a
trim course stops being a line at all.

**A STAIR'S TALL SIDE IS ITS `facing`.** Our renderer draws a backwards stair identically to a
right one, so every riser here is asserted in `tests/test_frontier_builds.py` rather than
eyeballed: a roof stair leans toward its ridge, an eave stair is `half=top` and leans toward the
wall it hangs off, and a step tread ascends toward its `facing`.
"""
from __future__ import annotations

from .canvas import Canvas, hash01

SIGN_WIDTH = 15                     # a sign line clips mid-word past this

#: ONE palette for the whole land, so six designs read as one hand. Every entry is checked by
#: `tests/test_frontier_builds.py` against `blocks.available` (the 1.19 server, not the 26.2
#: client), `blocks.spendable` (dirt and grass are CURRENCY here) and `palette.tier` (nothing
#: expensive), and none of it is cobblestone.
PAL = {
    # --- the ladder ---------------------------------------------------------------------
    "plinth": "polished_blackstone_bricks",   # L45   the dark base course everything stands on
    "base": "stone_bricks",                   # L122  masonry
    "band": "smooth_stone",                   # L159  the string course, and the only `ok` bulk
    "timber": "spruce_planks",                # L89   the framed storey
    "roof_field": "dark_oak_planks",          # L46   the roof, dark against the walls
    # --- masonry variants, hashed per CELL ----------------------------------------------
    "base_worn": "cracked_stone_bricks",
    "base_carved": "chiseled_stone_bricks",
    "base_moss": "mossy_stone_bricks",
    # --- the detail vocabulary ----------------------------------------------------------
    "base_stair": "stone_brick_stairs",
    "base_slab": "stone_brick_slab",
    "base_wall": "stone_brick_wall",
    "post": "spruce_log",                     # L41 on the side - a corner post reads as a post
    "beam": "stripped_spruce_log",            # L93 - the head beam and every lintel
    "timber_stair": "spruce_stairs",
    "timber_slab": "spruce_slab",
    "fence": "spruce_fence",
    "gate": "spruce_fence_gate",
    "shutter": "spruce_trapdoor",
    "door": "spruce_door",
    "roof": "dark_oak_stairs",
    "roof_slab": "dark_oak_slab",
    "glass": "glass_pane",
    "grille": "iron_bars",
    "chain": "iron_chain",
    # --- accents ------------------------------------------------------------------------
    "paint": "red_wool",
    "board": "white_wool",
    "lamp": "lantern",
    "glow": "ochre_froglight",                # a flush light IS the floor; nobody can knock it off
    "sign": "spruce_wall_sign",
    "rail": "rail",
    # --- THE SHOW LAYER -----------------------------------------------------------------
    #: A TOWN IS MASONRY. A FAIRGROUND IS CANVAS. Measured on the first build of these six
    #: lots, the whole land ran 0.0-2.6% coloured or lit blocks - stone brick, spruce and dark
    #: oak, which is exactly how you build a village. These are the blocks that say SHOW, and
    #: every one is cheap, spendable and on the 1.19 server (`tests/test_frontier_builds.py`
    #: asks the registry rather than this comment).
    "canvas_a": "red_wool",                   # L65   the stripe that reads from the spine
    "canvas_b": "white_wool",                 # L236  236 - 65 = 171 of luminance in one step
    "canvas_c": "yellow_wool",                # L197  the third tone, for a board field
    "pennant": "orange_wool",                 # L137  a flag, and the only warm mid tone
    "mast": "spruce_fence",                   # a flag pole is a fence, not a log: it is thin
    "finial": "lightning_rod",                # L255  a white point on a skyline, one block
    "flag": "red_banner",                     # a banner IS a flag, and nothing else in the game is
}

#: THE CANVAS STRIPE, and why it is two tones and not three. `red_wool` 65 against `white_wool`
#: 236 is 171 points of luminance - the biggest cheap step this economy has - and the flamingo
#: settled the general rule for exactly this problem: three tones of one hue beat two tones and
#: a third hue, but two tones at maximum contrast beat both when the job is READING FROM FIFTY
#: BLOCKS. Yellow is a FIELD colour here (a board behind a name), never a third stripe.
STRIPE = ("canvas_a", "canvas_b")

#: The masonry variants and how often each shows. Plain dominates or the wall reads as rubble.
_WEATHER = (("base", 0.72), ("base_worn", 0.14), ("base_moss", 0.09), ("base_carved", 0.05))

#: V is the 200-deep axis and U the 600-long one; canvas x is V and canvas z is U. Minecraft's
#: +x is EAST and +z is SOUTH, so a face looking toward the spine (falling V) looks WEST.
WEST, EAST, NORTH, SOUTH = "west", "east", "north", "south"


def _v_face(sign: int) -> str:
    """The compass name of a face normal along V. Toward the spine is west."""
    return EAST if sign > 0 else WEST


def _u_face(sign: int) -> str:
    return SOUTH if sign > 0 else NORTH


FRONTIER = {
    "kind": None,                  # trailhead | porch | boomtown | square | assay | works
    "lot": None,                   # [dv, du] - the measured lot, and the hard boundary
    "at": None,                    # [V, U] - the lot's near corner in park coordinates
    "anchor": [97500, 203, 80300],  # V0,U0 -> world X,Z, and the course a guest stands on
    "entry_u": None,               # the door's U inside the lot (defaults per kind)
    "entry_v": None,               # ...or its V, for a kind entered off a flank
    "title": None,
    "seed": 0,
}


# --------------------------------------------------------------------------- the lot frame


class _Lot:
    """The lot, and the only way a block reaches the canvas.

    Everything goes through `put`, so the boundary is one check in one place. A generator that
    checks its own arithmetic instead gets it right in eleven places and wrong in the twelfth,
    and the twelfth is invisible: a cropped gable is not a fault anything downstream can report.
    """

    def __init__(self, c: Canvas, dv: int, du: int, seed: int = 0):
        self.c, self.dv, self.du, self.seed = c, dv, du, seed
        self.refused = 0
        self.doors: list[dict] = []
        self.signs: list[dict] = []
        self.stairs: list[dict] = []
        #: EVERY ROOF DECLARES ITS OWN SLOPE, so a reversed tread is caught by a test rather than
        #: by somebody standing under it in game. There are three idioms here and they obey three
        #: different rules - a gable's two slopes face each other, a cap's face its centre, a
        #: lean-to's all face one way - and a single geometric rule cannot separate them from a
        #: pediment or a false front standing proud of the roof behind it.
        self.roofs: list[dict] = []

    # -- cells -----------------------------------------------------------
    def put(self, v: int, y: int, u: int, key: str, **props) -> bool:
        v, y, u = int(v), int(y), int(u)
        if not (0 <= v < self.dv and 0 <= u < self.du and 0 <= y < self.c.sy):
            self.refused += 1
            return False
        name = PAL.get(key, key)
        blk = self.c.raw_state(name, **props) if props else self.c.state(name)
        return self.c.put(v, y, u, blk)

    def has(self, v: int, y: int, u: int) -> bool:
        return self.c.solid(int(v), int(y), int(u))

    def name_at(self, v: int, y: int, u: int) -> str:
        return self.c.get_name(int(v), int(y), int(u)).split(":")[-1]

    def inside(self, v: int, u: int) -> bool:
        return 0 <= v < self.dv and 0 <= u < self.du

    # -- the vocabulary --------------------------------------------------
    def weather(self, v: int, u: int, y: int = 0) -> str:
        """A masonry variant, hashed on the CELL.

        Hashed on the COURSE every block in a course comes out identical and the wall is
        horizontal stripes of one material - which the deck soffit shipped, and which nothing in
        an audit can see.
        """
        r = hash01(v * 7 + 3, u * 13 + 5, y * 29 + 11, self.seed)
        acc = 0.0
        for key, share in _WEATHER:
            acc += share
            if r < acc:
                return key
        return "base"

    def stair(self, v: int, y: int, u: int, key: str, facing: str, half: str = "bottom") -> bool:
        ok = self.put(v, y, u, key, facing=facing, half=half, shape="straight",
                      waterlogged="false")
        if ok:
            self.stairs.append({"at": [v, y, u], "facing": facing, "half": half, "block": key})
        return ok

    def slab(self, v: int, y: int, u: int, key: str, kind: str = "bottom") -> bool:
        return self.put(v, y, u, key, type=kind, waterlogged="false")

    def log(self, v: int, y: int, u: int, key: str, axis: str = "y") -> bool:
        return self.put(v, y, u, key, axis=axis)

    def pane(self, v: int, y: int, u: int, key: str, along: str) -> bool:
        """A pane, CONNECTED ALONG ITS WALL.

        With every side false a pane renders as a lone post in the middle of an opening rather
        than as glazing - the campanile's slits shipped that once. `along` is the wall's own axis:
        "u" for a wall running along U, "v" for one running along V.
        """
        n = s = e = w = "false"
        if along == "u":
            n = s = "true"
        else:
            e = w = "true"
        return self.put(v, y, u, key, north=n, south=s, east=e, west=w, waterlogged="false")

    def bars(self, v: int, y: int, u: int, along: str) -> bool:
        n = s = e = w = "false"
        if along == "u":
            n = s = "true"
        else:
            e = w = "true"
        return self.put(v, y, u, "grille", north=n, south=s, east=e, west=w, waterlogged="false")

    def fence(self, v: int, y: int, u: int, along: str, key: str = "fence") -> bool:
        n = s = e = w = "false"
        if along == "u":
            n = s = "true"
        else:
            e = w = "true"
        return self.put(v, y, u, key, north=n, south=s, east=e, west=w, waterlogged="false")

    def hang(self, v: int, y: int, u: int) -> bool:
        """A lantern hanging from the cell above it - and the support is CHECKED.

        Placed blind, a hanging lantern with nothing over it comes away as a loose fitting and
        the audit calls it out as a cluster with nothing to place against. Same failure as the
        bat perch's vines and the stair head's chains.
        """
        if not self.has(v, y + 1, u):
            return False
        return self.put(v, y, u, "lamp", hanging="true", waterlogged="false")

    def sign(self, v: int, y: int, u: int, facing: str, lines) -> bool:
        """A wall sign in the cell IN FRONT of its wall, its text facing away from its support.

        THE SUPPORT IS CHECKED, NOT ASSUMED. Four of the park's seven building kinds once shipped
        a sign hung on the one column of a wall that has an opening in it, and it is invisible in
        every render: a wall sign floating in air draws exactly like one on a wall.
        """
        dv = {EAST: 1, WEST: -1}.get(facing, 0)
        du = {SOUTH: 1, NORTH: -1}.get(facing, 0)
        if not self.has(v - dv, y, u - du):
            return False
        if self.has(v, y, u):
            return False
        if not self.put(v, y, u, "sign", facing=facing, waterlogged="false"):
            return False
        text = [str(t)[:SIGN_WIDTH] for t in list(lines)[:4]]
        self.c.sign_text(v, y, u, front=text, colour="white", glowing=True)
        self.signs.append({"at": [v, y, u], "facing": facing, "lines": text})
        return True


# --------------------------------------------------------------------------- the kit


def _fill(lot: _Lot, v0, v1, u0, u1, y0, y1, key, weathered=False):
    for y in range(y0, y1 + 1):
        for v in range(v0, v1 + 1):
            for u in range(u0, u1 + 1):
                lot.put(v, y, u, lot.weather(v, u, y) if weathered else key)


def _ring(lot: _Lot, v0, v1, u0, u1, y0, y1, key, weathered=False):
    """The perimeter of a rectangle - a wall, not a solid."""
    for y in range(y0, y1 + 1):
        for v in range(v0, v1 + 1):
            for u in range(u0, u1 + 1):
                if v in (v0, v1) or u in (u0, u1):
                    lot.put(v, y, u, lot.weather(v, u, y) if weathered else key)


def _clear(lot: _Lot, v0, v1, u0, u1, y0, y1):
    for y in range(y0, y1 + 1):
        for v in range(v0, v1 + 1):
            for u in range(u0, u1 + 1):
                if lot.inside(v, u):
                    lot.c.put(v, y, u, 0)


def _opening(lot: _Lot, v0, v1, u0, u1, y0, y1, *, jamb: str, lintel: str,
             axis: str, kind: str = "door") -> dict:
    """AN OPENING WITH A WHOLE FRAME: two jambs to their full height, a lintel BETWEEN their tops.

    A hole punched in a wall reads as damage; a framed one reads as a door. The lintel spans the
    opening only - never the jambs - so the frame is legible as three parts rather than as a
    smear, and the jambs run the opening's whole height so no course of the frame is missing.
    Recorded in the design's meta, because `tests/test_frontier_builds.py` checks the CONTRACT
    (jambs whole, lintel strictly between their tops) rather than a block count.
    """
    _clear(lot, v0, v1, u0, u1, y0, y1)
    if axis == "u":                                   # the wall runs along U; jambs sit at u0-1/u1+1
        ja, jb = u0 - 1, u1 + 1
        for y in range(y0, y1 + 1):
            for v in range(v0, v1 + 1):
                lot.log(v, y, ja, jamb, axis="y")
                lot.log(v, y, jb, jamb, axis="y")
        for v in range(v0, v1 + 1):
            for u in range(u0, u1 + 1):
                lot.log(v, y1 + 1, u, lintel, axis="z")
        frame = {"jambs": [[v0, ja], [v0, jb]], "span": [u0, u1]}
    else:
        ja, jb = v0 - 1, v1 + 1
        for y in range(y0, y1 + 1):
            for u in range(u0, u1 + 1):
                lot.log(ja, y, u, jamb, axis="y")
                lot.log(jb, y, u, jamb, axis="y")
        for u in range(u0, u1 + 1):
            for v in range(v0, v1 + 1):
                lot.log(v, y1 + 1, u, lintel, axis="x")
        frame = {"jambs": [[ja, u0], [jb, u0]], "span": [v0, v1]}
    rec = {"kind": kind, "axis": axis, "v": [v0, v1], "u": [u0, u1],
           "y": [y0, y1], "lintel_y": y1 + 1, **frame}
    lot.doors.append(rec)
    return rec


def _gable(lot: _Lot, v0, v1, u0, u1, wall_top: int, *, ridge: str, eaves: bool = True) -> int:
    """A stepped gable roof. Returns the ridge course.

    THE STAIR LEANS TOWARD THE RIDGE, because a stair's tall side is its `facing` - so the step
    rises up the slope the way a roof tile laps. The eave is `half=top` leaning back over the
    wall, which is the one thing in the outside corpus we place at a seventh of their rate and
    the single cheapest way to stop a wall meeting a roof at a bare right angle.
    """
    if ridge == "u":                                  # ridge runs along U; slopes fall along V
        a0, a1, lo, hi = v0, v1, u0, u1
    else:
        a0, a1, lo, hi = u0, u1, v0, v1
    top = wall_top
    span = (a1 - a0) // 2

    def place(a, b, y, key, **kw):
        if ridge == "u":
            return lot.stair(a, y, b, key, **kw) if kw else lot.slab(a, y, b, key)
        return lot.stair(b, y, a, key, **kw) if kw else lot.slab(b, y, a, key)

    def plain(a, b, y, key):
        if ridge == "u":
            lot.put(a, y, b, key)
        else:
            lot.put(b, y, a, key)

    up = EAST if ridge == "u" else SOUTH               # toward the ridge, from the low side
    dn = WEST if ridge == "u" else NORTH

    if eaves:                                          # the overhang, one cell past the wall
        for b in range(lo, hi + 1):
            place(a0 - 1, b, wall_top + 1, "roof", facing=up, half="top")
            place(a1 + 1, b, wall_top + 1, "roof", facing=dn, half="top")

    for k in range(span + 1):
        y = wall_top + 1 + k
        a, b = a0 + k, a1 - k
        top = y
        if a > b:
            break
        if a == b:
            for j in range(lo, hi + 1):
                place(a, j, y, "roof_slab")
            break
        for j in range(lo, hi + 1):
            place(a, j, y, "roof", facing=up)
            place(b, j, y, "roof", facing=dn)
        for j in (lo, hi):                             # the gable wall, filling under the slope
            for m in range(a + 1, b):
                plain(m, j, y, "timber")
    lot.roofs.append({
        "style": "gable", "axis": "v" if ridge == "u" else "u",
        "v": [v0 - 1, v1 + 1] if ridge == "u" else [v0, v1],
        "u": [u0, u1] if ridge == "u" else [u0 - 1, u1 + 1],
        "y0": wall_top + 1, "y1": top, "mid": (a0 + a1) / 2, "up": up, "dn": dn})
    return top


def _cap(lot: _Lot, v0, v1, u0, u1, y0: int, *, courses=2, key="roof",
         fill="roof_field") -> int:
    """A stepped pyramid cap that is actually CONNECTED.

    A staircase of single blocks is 6-connected to NOTHING - each cell touches its neighbour only
    at a diagonal - and that is the ear-tip failure this repo has now paid for four times. A
    gable gets away with it because its gable ends fill the triangle and bridge the courses; a
    free-standing cap has no gable end, so every course but the last is laid SOLID and the ring
    above it lands on a course that is really there.
    """
    y = y0
    cv, cu = (v0 + v1) / 2, (u0 + u1) / 2
    a, b, c, d = v0, v1, u0, u1
    for k in range(courses):
        y = y0 + k
        for v in range(a, b + 1):
            for u in range(c, d + 1):
                if v in (a, b):                       # A CAP CLIMBS TOWARD ITS OWN CENTRE
                    lot.stair(v, y, u, key, facing=_v_face(-1 if v > cv else 1))
                elif u in (c, d):
                    lot.stair(v, y, u, key, facing=_u_face(-1 if u > cu else 1))
                else:
                    lot.put(v, y, u, fill)
        a, b, c, d = a + 1, b - 1, c + 1, d - 1
        if a > b or c > d:
            break
    lot.roofs.append({"style": "cap", "v": [v0, v1], "u": [u0, u1], "y0": y0, "y1": y,
                      "cv": cv, "cu": cu})
    return y


def _shed(lot: _Lot, v0, v1, u0, u1, *, h=7, ridge="u", title=None, doors=(),
          windows=True, floor=True, eaves=True, false_front=None, glass="glass",
          band_y=3, sign_face=None, sign_lines=None, show=True, show_rise=4,
          awning=None, awning_y=None) -> dict:
    """A frontier building: plinth, masonry base, string course, framed storey, head beam, roof.

    `doors` are (face, centre, width) where face is "-v"/"+v"/"-u"/"+u" - the face's own outward
    normal in lot coordinates, so a door on "-v" opens toward the spine.
    """
    # 0. the plinth and the floor
    for v in range(v0, v1 + 1):
        for u in range(u0, u1 + 1):
            edge = v in (v0, v1) or u in (u0, u1)
            lot.put(v, 0, u, "plinth" if edge else ("timber" if floor else "plinth"))

    # 1. the masonry base, its string course, and the framed storey over it
    for y in range(1, h + 1):
        for v in range(v0, v1 + 1):
            for u in range(u0, u1 + 1):
                if not (v in (v0, v1) or u in (u0, u1)):
                    continue
                corner = v in (v0, v1) and u in (u0, u1)
                if y < band_y:
                    lot.put(v, y, u, lot.weather(v, u, y))
                elif y == band_y:
                    lot.put(v, y, u, "band")
                elif y == h:
                    lot.log(v, y, u, "beam", axis="z" if v in (v0, v1) else "x")
                elif corner or (y > band_y and _is_stud(v, u, v0, v1, u0, u1)):
                    lot.log(v, y, u, "post", axis="y")
                else:
                    lot.put(v, y, u, "timber")

    # 2. the openings
    made = []
    for face, centre, width in doors:
        made.append(_face_opening(lot, v0, v1, u0, u1, face, centre, width, y1=3))

    # 3. windows in the framed storey, between the studs, with a sill and a lintel
    if windows and h >= band_y + 4:
        _windows(lot, v0, v1, u0, u1, band_y, h, glass)

    # 4. the roof
    ridge_y = _gable(lot, v0, v1, u0, u1, h, ridge=ridge, eaves=eaves)

    # 5. THE SHOW FRONT - the parapet that makes a frontier shop an ATTRACTION rather than a
    #    house. `show=False` falls back to the plain three-course false front, which is what a
    #    SERVICE building wants: the Works Yard must not announce itself, and a back-of-house
    #    shed wearing a name board is the "everything is an attraction" failure from the other
    #    side. The show front OWNS the name when it carries one, or the shed signs the same
    #    face twice and the second sign is silently refused - this project's most-repeated
    #    failure shape.
    front = None
    if false_front:
        if show:
            front = _showfront(lot, v0, v1, u0, u1, false_front, h, title, rise=show_rise,
                               lines=(list(sign_lines)[1:] if sign_lines else None))
        else:
            _false_front(lot, v0, v1, u0, u1, false_front, h, title)

    # 6. the canvas, over the face a guest walks up to
    canvas = None
    if awning:
        canvas = _canvas(lot, v0, v1, u0, u1, awning,
                         int(awning_y if awning_y is not None else band_y + 2))

    # 7. the name, on a wall that is actually there
    signed = bool(front and front.get("signed"))
    if sign_face and sign_lines and not (signed and sign_face == false_front):
        _face_sign(lot, v0, v1, u0, u1, sign_face, sign_lines)

    return {"v": [v0, v1], "u": [u0, u1], "wall_top": h, "ridge_y": ridge_y,
            "title": title, "openings": made, "showfront": front, "canvas": canvas}


def _is_stud(v, u, v0, v1, u0, u1) -> bool:
    """A framing stud every four cells along a wall - regularity, which is what reads."""
    if v in (v0, v1):
        return (u - u0) % 4 == 0 or u == u1
    return (v - v0) % 4 == 0 or v == v1


def _face_span(v0, v1, u0, u1, face, centre, width):
    """(v0, v1, u0, u1, axis) for an opening of `width` centred on `centre` in a named face."""
    half = width // 2
    if face in ("-v", "+v"):
        v = v0 if face == "-v" else v1
        a, b = centre - half, centre - half + width - 1
        return v, v, a, b, "u"
    u = u0 if face == "-u" else u1
    a, b = centre - half, centre - half + width - 1
    return a, b, u, u, "v"


#: (outside offset, the way a step in front of that face climbs) per face name.
_OUT = {"-v": ((-1, 0), EAST), "+v": ((1, 0), WEST),
        "-u": ((0, -1), SOUTH), "+u": ((0, 1), NORTH)}


def _face_opening(lot: _Lot, v0, v1, u0, u1, face, centre, width, y1=3, kind="door",
                  step=True):
    """An opening, and the half-step up into it.

    EVERY FLOOR HERE STANDS ONE COURSE PROUD OF THE LAWN, because the ground layer's own moss is
    the course below and a building's floor sits on it - which is what a frontier boardwalk on
    piers actually is. So a door without a step is a block to climb; the tread outside it
    ASCENDS TOWARD THE DOOR, and a stair ascending toward D has facing=D.
    """
    a, b, c, d, axis = _face_span(v0, v1, u0, u1, face, centre, width)
    rec = _opening(lot, a, b, c, d, 1, y1, jamb="post", lintel="beam", axis=axis, kind=kind)
    if step and face in _OUT:
        (dv_, du_), climb = _OUT[face]
        for v in range(a, b + 1):
            for u in range(c, d + 1):
                lot.stair(v + dv_, 0, u + du_, "base_stair", facing=climb)
        rec["step"] = {"facing": climb, "v": [a + dv_, b + dv_], "u": [c + du_, d + du_]}
    return rec


def _face_sign(lot: _Lot, v0, v1, u0, u1, face, lines, y=5):
    """Hang a name on a face, one cell PROUD of it, and try along the face until it sticks."""
    if face in ("-v", "+v"):
        v = (v0 - 1) if face == "-v" else (v1 + 1)
        facing = WEST if face == "-v" else EAST
        mid = (u0 + u1) // 2
        order = [mid] + [mid + d * s for d in range(1, (u1 - u0) // 2 + 1) for s in (1, -1)]
        for u in order:
            if lot.sign(v, y, u, facing, lines):
                return True
        return False
    u = (u0 - 1) if face == "-u" else (u1 + 1)
    facing = NORTH if face == "-u" else SOUTH
    mid = (v0 + v1) // 2
    order = [mid] + [mid + d * s for d in range(1, (v1 - v0) // 2 + 1) for s in (1, -1)]
    for v in order:
        if lot.sign(v, y, u, facing, lines):
            return True
    return False


def _windows(lot: _Lot, v0, v1, u0, u1, band_y, h, glass):
    """Two-course glazing between the studs, with a slab sill under it and a beam lintel over."""
    lo, hi = band_y + 2, band_y + 3
    if hi >= h:
        lo = hi = band_y + 1
    for v, u in _wall_cells(v0, v1, u0, u1):
        if _is_stud(v, u, v0, v1, u0, u1):
            continue
        nxt = (v, u + 1) if v in (v0, v1) else (v + 1, u)
        if not _on_wall(nxt, v0, v1, u0, u1) or _is_stud(nxt[0], nxt[1], v0, v1, u0, u1):
            continue
        if (hash01(v, u, 91, lot.seed) > 0.55):
            continue
        along = "u" if v in (v0, v1) else "v"
        for (a, b) in ((v, u), nxt):
            for y in range(lo, hi + 1):
                lot.c.put(a, y, b, 0)
                lot.pane(a, y, b, glass, along)
            lot.slab(a, lo - 1, b, "timber_slab", "top")
            lot.log(a, hi + 1, b, "beam", axis="z" if along == "u" else "x")


def _wall_cells(v0, v1, u0, u1):
    for v in range(v0, v1 + 1):
        for u in range(u0, u1 + 1):
            if v in (v0, v1) or u in (u0, u1):
                yield v, u


def _on_wall(cell, v0, v1, u0, u1) -> bool:
    v, u = cell
    return v0 <= v <= v1 and u0 <= u <= u1 and (v in (v0, v1) or u in (u0, u1))


def _false_front(lot: _Lot, v0, v1, u0, u1, face, h, title):
    """The parapet that turns a shed into a shop: the street wall carried three courses past the
    roof, capped with a cornice, and a painted board between them for the name."""
    top = h + 3
    if face in ("-v", "+v"):
        v = v0 if face == "-v" else v1
        cells = [(v, u) for u in range(u0, u1 + 1)]
    else:
        u = u0 if face == "-u" else u1
        cells = [(v, u) for v in range(v0, v1 + 1)]
    for (v, u) in cells:
        for y in range(h + 1, top):
            lot.put(v, y, u, "timber")
        lot.put(v, top, u, "band")
    mid = len(cells) // 2
    if title:
        for k in range(max(0, mid - 3), min(len(cells), mid + 4)):
            v, u = cells[k]
            lot.put(v, h + 2, u, "paint")


def _porch_run(lot: _Lot, v0, v1, u0, u1, *, out: str, h=4, rail=True, deck=True,
               lamp_every=6) -> dict:
    """A veranda: a plank deck, a post every three, a head beam, a roof sloping to the open side.

    A COVERED PORCH IS THE FRONTIER'S ONE PIECE OF PUBLIC SHELTER and it is what the Transit
    Landing and the Prospecting Row both ask for by name. It is deliberately mostly air: posts,
    a beam and a roof over an open deck, which is 20-30% of the columns it covers.
    """
    lamps = 0
    for v in range(v0, v1 + 1):
        for u in range(u0, u1 + 1):
            lot.put(v, 0, u, "timber")
    if out in ("-u", "+u"):
        line = u0 if out == "-u" else u1
        step = -1 if out == "-u" else 1
        for v in range(v0, v1 + 1):
            if (v - v0) % 3 == 0 or v == v1:
                for y in range(1, h):
                    lot.log(v, y, line, "post", axis="y")
                lot.log(v, h, line, "beam", axis="x")
                lot.stair(v, h, line - step, "timber_stair", facing=_u_face(-step), half="top")
            elif rail:
                lot.fence(v, 1, line, "v")
            if (v - v0) % lamp_every == 2:
                if lot.hang(v, h - 1, line - step):
                    lamps += 1
        # THE LEAN-TO RISES ONE COURSE EVERY OTHER CELL AND CARRIES A RISER WHERE IT STEPS. A row
        # of stairs that simply jumps a course touches its neighbour at a diagonal, which is not
        # connected at all; the riser under each step is what makes the roof one piece.
        prev = h + 1
        for v in range(v0, v1 + 1):
            lot.stair(v, prev, line, "roof", facing=_u_face(-step))
        for k, u in enumerate(range(line - step, line - step * (u1 - u0 + 1), -step)):
            y = h + 1 + (k + 1) // 2
            for v in range(v0, v1 + 1):
                if y > prev:
                    lot.put(v, y - 1, u, "roof_field")
                lot.stair(v, y, u, "roof", facing=_u_face(-step))
            prev = y
    else:
        line = v0 if out == "-v" else v1
        step = -1 if out == "-v" else 1
        for u in range(u0, u1 + 1):
            if (u - u0) % 3 == 0 or u == u1:
                for y in range(1, h):
                    lot.log(line, y, u, "post", axis="y")
                lot.log(line, h, u, "beam", axis="z")
                lot.stair(line - step, h, u, "timber_stair", facing=_v_face(-step), half="top")
            elif rail:
                lot.fence(line, 1, u, "u")
            if (u - u0) % lamp_every == 2:
                if lot.hang(line - step, h - 1, u):
                    lamps += 1
        prev = h + 1
        for k, v in enumerate(range(line, line - step * (v1 - v0 + 1), -step)):
            y = h + 1 + k // 2
            for u in range(u0, u1 + 1):
                if y > prev:
                    lot.put(v, y - 1, u, "roof_field")
                lot.stair(v, y, u, "roof", facing=_v_face(-step))
            prev = y
    lot.roofs.append({"style": "lean", "v": [v0, v1], "u": [u0, u1],
                      "y0": h + 1, "y1": prev,
                      "up": _u_face(-step) if out in ("-u", "+u") else _v_face(-step)})
    return {"v": [v0, v1], "u": [u0, u1], "lamps": lamps}


def _arch(lot: _Lot, v0, v1, u0, u1, *, axis, pier=2, clear_h=5, title=None,
          face=None) -> dict:
    """A portal: two masonry piers, a timber head, a keystone band and a name over the opening.

    An arch is the one structure in a theme park whose whole job is to be walked THROUGH, so the
    opening is cut to full headroom and the piers stand clear of it - never a hole in a wall.
    """
    if axis == "u":                                   # the opening runs along U, walked along V
        pa = (u0, u0 + pier - 1)
        pb = (u1 - pier + 1, u1)
        span = (pa[1] + 1, pb[0] - 1)
        for (a, b) in (pa, pb):
            for u in range(a, b + 1):
                for v in range(v0, v1 + 1):
                    lot.put(v, 0, u, "plinth")
                    for y in range(1, clear_h + 1):
                        lot.put(v, y, u, lot.weather(v, u, y))
                    lot.put(v, clear_h + 1, u, "band")
        for u in range(span[0], span[1] + 1):
            for v in range(v0, v1 + 1):
                lot.log(v, clear_h + 1, u, "beam", axis="z")
                lot.put(v, clear_h + 2, u, "timber")
                lot.put(v, clear_h + 3, u, "board" if title else "timber")
            lot.stair(v0, clear_h + 2, u, "timber_stair", facing=WEST, half="top")
            lot.stair(v1, clear_h + 2, u, "timber_stair", facing=EAST, half="top")
        for v in (v0, v1):
            for u in range(u0, u1 + 1):
                lot.slab(v, clear_h + 4, u, "timber_slab", "bottom")
        head = {"span": list(span), "piers": [list(pa), list(pb)]}
        if title:
            mid = (span[0] + span[1]) // 2
            lot.sign(v0 - 1, clear_h + 3, mid, WEST, [title])
            lot.sign(v1 + 1, clear_h + 3, mid, EAST, [title])
        for u in (span[0], span[1]):
            lot.hang(v0, clear_h, u)
            lot.hang(v1, clear_h, u)
    else:
        pa = (v0, v0 + pier - 1)
        pb = (v1 - pier + 1, v1)
        span = (pa[1] + 1, pb[0] - 1)
        for (a, b) in (pa, pb):
            for v in range(a, b + 1):
                for u in range(u0, u1 + 1):
                    lot.put(v, 0, u, "plinth")
                    for y in range(1, clear_h + 1):
                        lot.put(v, y, u, lot.weather(v, u, y))
                    lot.put(v, clear_h + 1, u, "band")
        for v in range(span[0], span[1] + 1):
            for u in range(u0, u1 + 1):
                lot.log(v, clear_h + 1, u, "beam", axis="x")
                lot.put(v, clear_h + 2, u, "timber")
                lot.put(v, clear_h + 3, u, "board" if title else "timber")
            lot.stair(v, clear_h + 2, u0, "timber_stair", facing=NORTH, half="top")
            lot.stair(v, clear_h + 2, u1, "timber_stair", facing=SOUTH, half="top")
        for u in (u0, u1):
            for v in range(v0, v1 + 1):
                lot.slab(v, clear_h + 4, u, "timber_slab", "bottom")
        head = {"span": list(span), "piers": [list(pa), list(pb)]}
        if title:
            mid = (span[0] + span[1]) // 2
            lot.sign(mid, clear_h + 3, u0 - 1, NORTH, [title])
            lot.sign(mid, clear_h + 3, u1 + 1, SOUTH, [title])
        for v in (span[0], span[1]):
            lot.hang(v, clear_h, u0)
            lot.hang(v, clear_h, u1)
    head["title"] = title
    head["axis"] = axis
    head["clear_h"] = clear_h
    return head


def _tower(lot: _Lot, v0, v1, u0, u1, *, top=16, ridge="u", title=None) -> dict:
    """A gate tower: masonry to a string course, a framed belfry with slit lights, a pitched cap."""
    for v in range(v0, v1 + 1):
        for u in range(u0, u1 + 1):
            lot.put(v, 0, u, "plinth")
    for y in range(1, top + 1):
        for v in range(v0, v1 + 1):
            for u in range(u0, u1 + 1):
                if y <= top - 5:
                    lot.put(v, y, u, lot.weather(v, u, y))
                elif y == top - 4:
                    lot.put(v, y, u, "band")
                elif v in (v0, v1) and u in (u0, u1):
                    lot.log(v, y, u, "post", axis="y")
                elif y == top:
                    lot.log(v, y, u, "beam", axis="z" if v in (v0, v1) else "x")
                elif v in (v0, v1) or u in (u0, u1):
                    lot.put(v, y, u, "timber")
    for v, u in _wall_cells(v0, v1, u0, u1):          # the belfry's slit lights
        if (v in (v0, v1) and u in (u0, u1)):
            continue
        lot.c.put(v, top - 2, u, 0)
        lot.bars(v, top - 2, u, "u" if v in (v0, v1) else "v")
    ridge_y = _gable(lot, v0, v1, u0, u1, top, ridge=ridge, eaves=True)
    if title:
        _face_sign(lot, v0, v1, u0, u1, "-v", [title], y=top - 6)
    return {"v": [v0, v1], "u": [u0, u1], "top": top, "ridge_y": ridge_y}


def _water_tower(lot: _Lot, cv: int, cu: int, *, leg=6, r=3) -> dict:
    """A frontier water tower: four legs, cross braces, a hooped tank and a conical cap.

    IT IS THE LAND'S SECOND SILHOUETTE and it costs 200 blocks. A gold-rush town without one
    reads as a generic village; with one it reads from the spine.
    """
    v0, v1, u0, u1 = cv - r, cv + r, cu - r, cu + r
    for (v, u) in ((v0 + 1, u0 + 1), (v0 + 1, u1 - 1), (v1 - 1, u0 + 1), (v1 - 1, u1 - 1)):
        for y in range(0, leg + 1):
            lot.log(v, y, u, "post", axis="y")
        # the knee brace under the tank, LEANING BACK ON ITS OWN POST
        step = 1 if u < cu else -1
        lot.stair(v, leg - 2, u + step, "timber_stair", facing=_u_face(-step), half="top")
    for y in (2, leg - 1):                            # the cross braces
        for u in range(u0 + 1, u1):
            lot.fence(v0 + 1, y, u, "u")
            lot.fence(v1 - 1, y, u, "u")
        for v in range(v0 + 1, v1):
            lot.fence(v, y, u0 + 1, "v")
            lot.fence(v, y, u1 - 1, "v")
    for y in range(leg + 1, leg + 6):                 # the tank
        for v in range(v0, v1 + 1):
            for u in range(u0, u1 + 1):
                if abs(v - cv) + abs(u - cu) > r + 1:
                    continue
                edge = abs(v - cv) + abs(u - cu) >= r
                if y in (leg + 1, leg + 5) or edge:
                    lot.put(v, y, u, "beam" if y in (leg + 2, leg + 4) else "timber")
    for k in range(3):                                # the conical cap, climbing to its centre
        y = leg + 6 + k
        for v in range(v0 + k, v1 - k + 1):
            for u in range(u0 + k, u1 - k + 1):
                d = abs(v - cv) + abs(u - cu)
                if d > r + 1 - k:
                    continue
                if d >= r - k:
                    if abs(v - cv) >= abs(u - cu):
                        lot.stair(v, y, u, "roof", facing=_v_face(-1 if v > cv else 1))
                    else:
                        lot.stair(v, y, u, "roof", facing=_u_face(-1 if u > cu else 1))
                elif k == 2:
                    lot.slab(v, y, u, "roof_slab", "bottom")
    lot.roofs.append({"style": "cap", "v": [v0, v1], "u": [u0, u1],
                      "y0": leg + 6, "y1": leg + 8, "cv": cv, "cu": cu, "diagonal": True})
    return {"at": [cv, cu], "top": leg + 8}


def _kerb(lot: _Lot, cells, key="plinth", y=0):
    for (v, u) in cells:
        lot.put(v, y, u, key)


def _pave(lot: _Lot, v0, v1, u0, u1, *, field="base", border="plinth", inlay="timber",
          glow_every=0) -> int:
    """The square's floor: a bordered field with an inlaid cross, and its light IN the paving.

    A FLUSH FROGLIGHT IS THE FLOOR, not a fixture on it - an opaque emitter a course down, so it
    reaches 14 rather than 15 - which is this island's own idiom and the only lamp on an open
    square nobody can knock off. It is paving, not street furniture.
    """
    lit = 0
    cv, cu = (v0 + v1) // 2, (u0 + u1) // 2
    for v in range(v0, v1 + 1):
        for u in range(u0, u1 + 1):
            edge = v in (v0, v0 + 1, v1 - 1, v1) or u in (u0, u0 + 1, u1 - 1, u1)
            cross = abs(v - cv) <= 3 or abs(u - cu) <= 3
            key = border if edge else (inlay if cross else field)
            if glow_every and not edge and (v - v0) % glow_every == 0 and (u - u0) % glow_every == 0:
                key = "glow"
                lit += 1
            lot.put(v, 0, u, key)
    return lit


# --------------------------------------------------------------------------- the show layer
#
# WHAT SEPARATES A THEME PARK FROM A TOWN IS NOT THE BUILDINGS, IT IS WHAT IS ON THE FRONT OF
# THEM. Jack, looking at the first build of these six lots: "they are visually great - but all
# serve no actual defined purpose - it feels more like multiple villages or towns than a theme
# park", and then "we need this to be a theme park, and amusement area, beautiful, not just
# full of buildings." Measured, the whole land ran 0.0-2.6% coloured-or-lit blocks. Stone
# brick, spruce and dark oak with a plinth, a string course and a cornice IS how you build a
# village; it is a correct answer to a question nobody asked.
#
# Four pieces, and each does one job a masonry facade cannot:
#
#   _showfront   a SHAPED parapet with a name board and a lit band - says WHAT HAPPENS INSIDE
#   _canvas      a striped awning that projects and slopes - says CANVAS, breaks the wall
#   _bunting     a strung line between two fixed points - says FAIRGROUND, and costs nothing
#   _flagpole    / _cupola - the silhouette, the only thing that survives to a quarter scale
#
# THE SHAPE CARRIES, NOT THE WORD. `park_frontage._portal` settled this for the park's own
# thresholds - "colour is the whole of the distinction, because at distance the word is
# unreadable and the shape is not" - and it is why a show front is SHAPED rather than merely
# painted: at a quarter scale the name board is four pixels and the stepped outline is not.


def _shape(n: int, rise: int) -> list:
    """The stepped profile of a show front, in courses above the wall top, symmetric about its
    own middle.

    A FLAT PARAPET IS A PARAPET; A SHAPED ONE IS A SHOPFRONT. The middle third stands at full
    `rise` and each cell beyond it steps down one, so the outline is a plateau with shoulders -
    which is what a false front on a frontier street actually is, and it is legible as a
    silhouette when nothing else about the building is.
    """
    if n <= 0:
        return []
    mid = (n - 1) / 2.0
    inner = max(0.0, (max(1, n // 3) - 1) / 2.0)
    return [max(1, rise - max(0, int(abs(k - mid) - inner))) for k in range(n)]


def _front_cells(v0, v1, u0, u1, face):
    """The cells of one named face, in order along it, and the outward step from it."""
    if face in ("-v", "+v"):
        v = v0 if face == "-v" else v1
        return [(v, u) for u in range(u0, u1 + 1)], ((-1, 0) if face == "-v" else (1, 0))
    u = u0 if face == "-u" else u1
    return [(v, u) for v in range(v0, v1 + 1)], ((0, -1) if face == "-u" else (0, 1))


def _face_dir(face: str) -> str:
    return {"-v": WEST, "+v": EAST, "-u": NORTH, "+u": SOUTH}[face]


def _showfront(lot: _Lot, v0, v1, u0, u1, face, h, title, *, rise=4, lines=None,
               field="canvas_c", frame="canvas_a", lit=True, board=True) -> dict:
    """THE FACADE THAT ANNOUNCES ITSELF: a shaped parapet, a painted name board, a lit band.

    This replaces the flat three-course false front the first build carried. That parapet was
    correct architecture and it said nothing: a guest twenty blocks away saw a rectangle of
    spruce with a rectangle of red in the middle of it, and every shop on the street had one.

    Three things are added and every one of them is measurable in a render:

      * the top is SHAPED (`_shape`), so the outline differs from its neighbours;
      * the name board is a `canvas_c` FIELD inside a `canvas_a` FRAME - a panel rather than a
        painted patch, which is what carries a name at distance;
      * two `glow` blocks sit IN the frame, one at each end of the board. A froglight built
        into the board is part of the structure and cannot be knocked off, which is the rule
        this park lights everything by - and it is what makes the name readable at night.

    NOTHING PROJECTS. Every cell is in the face's own column, so a show front standing on a lot
    boundary cannot leave the lot - which is the one way a facade quietly stops existing.
    """
    cells, _step = _front_cells(v0, v1, u0, u1, face)
    prof = _shape(len(cells), max(2, int(rise)))
    for k, (v, u) in enumerate(cells):
        top = h + prof[k]
        for y in range(h + 1, top):
            lot.put(v, y, u, "timber")
        lot.put(v, top, u, "band")                     # the coping, following the shaped outline

    made = {"face": face, "profile": prof, "cells": len(cells), "board": None, "lit": 0}
    if not board or len(cells) < 7:
        return made

    # -- the name board: a field inside a frame, centred, three courses of it ----------------
    mid = len(cells) // 2
    half = min(3, (len(cells) - 3) // 2)
    lo, hi = mid - half, mid + half
    by = h + 1                                         # the board's own bottom course
    for k in range(lo, hi + 1):
        v, u = cells[k]
        edge = k in (lo, hi)
        for y in (by, by + 1, by + 2):
            if y > h + prof[k]:
                continue
            rim = edge or y in (by, by + 2)
            lot.put(v, y, u, frame if rim else field)
    made["board"] = {"span": [lo, hi], "y": [by, by + 2]}

    if lit:
        for k in (lo, hi):
            v, u = cells[k]
            if h + prof[k] >= by + 1:
                lot.put(v, by + 1, u, "glow")
                made["lit"] += 1

    if title:
        made["signed"] = _face_sign(lot, v0, v1, u0, u1, face,
                                    [title] + [str(x) for x in (lines or [])], y=by + 1)
    return made


def _canvas(lot: _Lot, v0, v1, u0, u1, face, y, *, depth=2, stripe=STRIPE, fringe=True,
            phase=0, run=2) -> dict:
    """A STRIPED AWNING: two courses of canvas sloping out from a wall, with a hanging valance.

    IT SLOPES, WHICH IS THE WHOLE POINT. A flat coloured shelf projecting from a wall reads as
    a shelf; an awning that drops a course as it comes out reads as fabric, and it is the one
    element here that breaks a facade's vertical silhouette at EYE level rather than at roof
    level. The stripe runs in `run`-wide bands - one-wide stripes are noise past ten blocks,
    which is the ladybird's own spot-spacing finding in a different body.

    THE VALANCE IS A TRAPDOOR AND ONLY A TRAPDOOR CAN DO IT: a thin vertical panel on a block
    face, which is the vertical slab this game never shipped. We place them at a seventh of the
    outside corpus's rate, and this is where they earn it.
    """
    cells, (sv, su) = _front_cells(v0, v1, u0, u1, face)
    out = _face_dir(face)
    laid = valance = 0
    for k, (v, u) in enumerate(cells):
        if not lot.has(v, y - 1, u) and not lot.has(v, y, u):
            continue                                   # no wall here - a gap, a door, a corner
        key = stripe[((k + phase) // max(1, run)) % len(stripe)]
        for d in range(1, depth + 1):
            if lot.put(v + sv * d, y - (d - 1), u + su * d, key):
                laid += 1
        if fringe:
            d = depth + 1
            if lot.put(v + sv * d, y - (depth - 1), u + su * d, "shutter", facing=out,
                       half="top", open="true", powered="false", waterlogged="false"):
                valance += 1
    return {"face": face, "y": y, "depth": depth, "cells": laid, "valance": valance}


def _bunting(lot: _Lot, a: int, b: int, fixed: int, y: int, axis: str, *, sag=1,
             stripe=("canvas_a", "canvas_b", "canvas_c")) -> int:
    """A STRUNG LINE BETWEEN TWO FIXED POINTS, dipping in the middle.

    Bunting is the cheapest thing in this file and the loudest: a line of alternating colour
    strung high over a street says fairground before a guest has read one sign.

    IT DIPS, AND A DIP NEEDS A RISER. A run that simply steps down a course touches its
    neighbour only at a diagonal, which is not connected at all - the ear-tip failure this repo
    has now paid for five times, and the reason `_porch_run`'s lean-to carries a riser under
    every step. Both ends must land on something the caller has already built, or the line is
    a second component hanging in the air.
    """
    lo, hi = (a, b) if a <= b else (b, a)
    n = hi - lo + 1
    if n < 5:
        return 0
    laid = 0
    prev = y
    for k in range(n):
        t = min(k, n - 1 - k) / max(1.0, (n - 1) / 2.0)   # 0 at the ends, 1 in the middle
        cy = y - int(round(sag * t))
        key = stripe[k % len(stripe)]
        for yy in range(min(cy, prev), max(cy, prev) + 1):
            if axis == "u":
                laid += bool(lot.put(fixed, yy, lo + k, key))
            else:
                laid += bool(lot.put(lo + k, yy, fixed, key))
        prev = cy
    return laid


def _flagpole(lot: _Lot, v: int, u: int, y0: int, *, h=6, colour="pennant", along="u") -> dict:
    """A POLE WITH A PENNANT ON IT, AND A WHITE POINT AT THE TOP OF IT.

    THE SILHOUETTE IS THE ONLY THING THAT SURVIVES TO A QUARTER SCALE. A roofline of similar
    gables is a town whatever colour it is painted; a mast standing six courses clear of one is
    the cheapest legible difference this file can buy - about a dozen blocks.

    THE PENNANT IS WOOL, NOT A BANNER. A banner is the right object in the game and it renders
    as a thin sheet our own tools draw as a cube, so it cannot be judged offline at all; three
    wool cells rigid against the mast are a shape both a render and a player can see.
    """
    # A FREE POST CONNECTS TO NOTHING. `_Lot.fence` forces two sides true, which is right for a
    # rail running along a wall and wrong for a mast: a fence drawn as connected to open air
    # renders with two stubs sticking out of it, and our own tools draw a fence as a full cube
    # so nothing offline would ever have shown it.
    for y in range(y0, y0 + h):
        lot.put(v, y, u, "mast", north="false", south="false", east="false", west="false",
                waterlogged="false")
    lot.put(v, y0 + h, u, "finial", facing="up", waterlogged="false")
    flown = 0
    dv, du = (0, 1) if along == "u" else (1, 0)
    for k in range(3):                                 # a tapering pennant off the mast's side
        for j in range(3 - k):
            flown += bool(lot.put(v + dv * (j + 1), y0 + h - 2 - k, u + du * (j + 1), colour))
    return {"at": [v, u], "top": y0 + h, "pennant": flown}


def _cupola(lot: _Lot, cv: int, cu: int, y0: int, *, r=1, h=4) -> dict:
    """A LIT LANTERN ON A RIDGE: four posts, glazed sides, a stepped cap and a point.

    A cupola is the one roof element that changes a building's OUTLINE rather than its surface,
    and it is what tells one shed from the next at the distance a guest actually chooses which
    door to walk to.
    """
    v0, v1, u0, u1 = cv - r, cv + r, cu - r, cu + r
    for v in range(v0, v1 + 1):                        # the deck it stands on, so it is one piece
        for u in range(u0, u1 + 1):
            lot.put(v, y0, u, "band")
    for y in range(y0 + 1, y0 + h):
        for v in range(v0, v1 + 1):
            for u in range(u0, u1 + 1):
                if v in (v0, v1) and u in (u0, u1):
                    lot.log(v, y, u, "post", axis="y")
                elif v in (v0, v1) or u in (u0, u1):
                    lot.bars(v, y, u, "u" if v in (v0, v1) else "v")
    lot.put(cv, y0 + h - 1, cu, "glow")
    top = _cap(lot, v0, v1, u0, u1, y0 + h, courses=1)
    # THE POINT SITS ON THE CAP, NOT A COURSE ABOVE IT. A finial with a course of air under it
    # is a second component, which is the one failure this file's own connectivity test exists
    # to catch and the one a render cannot show.
    lot.put(cv, top + 1, cu, "finial", facing="up", waterlogged="false")
    return {"at": [cv, cu], "top": top + 1}


# --------------------------------------------------------------------------- the six lots


def _trailhead(lot: _Lot, p: dict) -> dict:
    """F1 - the land's threshold. A walled forecourt with a portal on the spine face and a way
    out to the avenue on the east flank, so it is a THRESHOLD you pass through rather than a
    facade with a dead doorway.

    THE GATE'S SILHOUETTE MUST NOT EAT THE MINE RIDGE. The spec forbids the gate roof consuming
    the corridor in which the coaster reads, so the towers stop at 21 courses and the portal head
    at 14: the coaster's crest, seventy blocks east, still stands clear above it.
    """
    dv, du = lot.dv, lot.du
    eu = int(p.get("entry_u") or 19)                  # the spur lands at U18-20
    out = {}

    # 1. the west range - the portal, its towers, the trail office and the waiting porch
    out["portal"] = _arch(lot, 1, 7, eu - 6, eu + 6, axis="u", pier=3, clear_h=7,
                          title="FRONTIER")
    out["tower_n"] = _tower(lot, 1, 7, eu - 12, eu - 7, top=15, ridge="v", title=None)
    out["tower_s"] = _tower(lot, 1, 7, eu + 7, eu + 12, top=15, ridge="v", title=None)
    out["office"] = _shed(lot, 1, 12, 1, eu - 13, h=7, ridge="v", title="TRAIL OFFICE",
                          doors=(("-v", (1 + eu - 13) // 2, 2),), sign_face="-v",
                          sign_lines=["TRAIL OFFICE", "maps and lost", "property"])
    out["porch"] = _porch_run(lot, 1, 12, eu + 13, du - 1, out="-u", h=5, lamp_every=5)

    # 2. the stockade - the flanks and the back, with buttress piers so a long wall has a rhythm
    for v in range(7, dv):
        for u in (0, du - 1):
            if u == du - 1 and 24 <= v <= 26:         # the way out, onto the avenue
                continue
            lot.put(v, 0, u, "plinth")
            for y in (1, 2):
                lot.put(v, y, u, lot.weather(v, u, y))
            lot.put(v, 3, u, "band")
            if v % 5 == 0:
                for y in (4, 5):
                    lot.log(v, y, u, "post", axis="y")
                lot.slab(v, 6, u, "base_slab", "bottom")
            else:
                lot.fence(v, 4, u, "v")
    for u in range(0, du):
        v = dv - 1
        lot.put(v, 0, u, "plinth")
        for y in (1, 2):
            lot.put(v, y, u, lot.weather(v, u, y))
        lot.put(v, 3, u, "band")
        if u % 5 == 0:
            for y in (4, 5):
                lot.log(v, y, u, "post", axis="y")
            lot.slab(v, 6, u, "base_slab", "bottom")
        else:
            lot.fence(v, 4, u, "u")
    out["exit"] = _arch(lot, 21, 29, du - 4, du - 2, axis="v", pier=3, clear_h=5,
                        title="TO THE MINE")

    # 3. inside the court: the water tower against the flank wall, and the trail store
    out["water_tower"] = _water_tower(lot, dv - 6, 3, leg=7, r=3)
    out["store"] = _shed(lot, dv - 11, dv - 2, du - 12, du - 1, h=6, ridge="u",
                         title="TRAIL STORE", doors=(("-v", du - 7, 2),),
                         sign_face="-v", sign_lines=["TRAIL STORE"])
    return out


def _porch_lot(lot: _Lot, p: dict) -> dict:
    """F5 - Prospecting Porch: two playable bays under one shared veranda.

    IT IS ENTERED OFF ITS EAST FLANK, not its front. Column A stacks 45 + 51 into 97 courses with
    one to spare, so this module's declared west door opens into the BACK OF TRAILHEAD GATE - the
    grid's own measurement - and `PARK_ATTRACTIONS_PLAN` re-anchors it to the U39 flank against
    the avenue at U41-45. The veranda therefore runs the full length of that flank and the two
    bays open onto it, which is also what a prospecting row looks like.

    THE BAYS ARE SHELLS. `PARK_FULL_BUILD_SPEC` states their build state as "shell/circuits
    separately", and this repo does not ship a machine it cannot verify - two finished casino
    games were cut for exactly that. Both bays are built with their counter, backboard, result
    panel and reset hatch in place and NO circuit behind them.
    """
    dv, du = lot.dv, lot.du
    out = {}
    ev = int(p.get("entry_v") or 16)

    # the veranda down the avenue flank, and the gap in its rail that is the way in.
    # THE GAP FALLS BETWEEN POSTS, BY ARITHMETIC. The colonnade stands every third cell, so a
    # three-wide gap always eats a post and leaves a beam over a hole; two cells between two
    # posts is a framed opening instead, which is what a way in has to look like.
    out["veranda"] = _porch_run(lot, 4, dv - 5, du - 7, du - 1, out="+u", h=5, lamp_every=7)
    for v in range(ev, ev + 2):
        lot.c.put(v, 1, du - 1, 0)
        lot.slab(v, 0, du - 1, "base_slab", "top")
    lot.doors.append({"kind": "entry", "axis": "v", "v": [ev, ev + 1],
                      "u": [du - 1, du - 1], "y": [1, 1], "lintel_y": 5,
                      "jambs": [[ev - 1, du - 1], [ev + 2, du - 1]], "span": [ev, ev + 1]})

    # bay A - the shooting range, its backboard away from the walk
    out["range"] = _shed(lot, 6, 22, du - 20, du - 8, h=7, ridge="v", title="SHOOTING RANGE",
                         doors=(("+u", 14, 3),), sign_face="+u",
                         sign_lines=["SHOOTING RANGE", "five shots", "prizes at the", "assay office"])
    for v in range(8, 21):                            # the backboard and the result ladder
        lot.put(v, 4, du - 20, "paint")
        lot.put(v, 5, du - 20, "board")
    for k, v in enumerate(range(9, 20, 2)):
        lot.put(v, 6, du - 19, "glow")
    for u in range(du - 19, du - 9):                  # the firing counter
        lot.slab(11, 1, u, "timber_slab", "top")
        lot.put(10, 1, u, "timber")

    # bay B - the gold sluice, a launder on trestles and a settling pool below it
    out["sluice"] = _shed(lot, 28, 44, du - 20, du - 8, h=7, ridge="v", title="GOLD SLUICE",
                          doors=(("+u", 14, 3),), sign_face="+u",
                          sign_lines=["GOLD SLUICE", "wash your own", "pay dirt"])
    for k, u in enumerate(range(du - 18, du - 9)):    # the launder, falling toward the pool
        y = 4 - k // 3
        for v in (31, 33):
            lot.put(v, y, u, "beam")
        lot.slab(32, y, u, "timber_slab", "bottom")
        if k % 3 == 0:
            for yy in range(1, y):
                lot.log(32, yy, u, "post", axis="y")
    for v in range(36, 42):                           # the settling pool, a stone kerb, no water
        for u in range(du - 18, du - 10):
            edge = v in (36, 41) or u in (du - 18, du - 11)
            lot.put(v, 1 if edge else 0, u, "base_slab" if edge else "plinth")
            if edge:
                lot.slab(v, 1, u, "base_slab", "top")

    # the ore bin at the back, and the covered walk that ties it to the range
    out["ore_bin"] = _bin(lot, 14, 22, 4, 12)
    for u in range(12, du - 19):
        for v in range(16, 21):
            lot.put(v, 0, u, "timber")
            lot.slab(v, 5, u, "roof_slab", "bottom")
        if (u - 12) % 3 == 0:
            for v in (16, 20):
                for y in range(1, 4):
                    lot.log(v, y, u, "post", axis="y")
                lot.log(v, 4, u, "beam", axis="z")
    return out


def _bin(lot: _Lot, v0, v1, u0, u1) -> dict:
    """An ore bin: a stone hopper on timber legs, shuttered at the front. It is a PROP with a job -
    the sluice's own feed - and it is the one place trapdoors do what only trapdoors can, which is
    a thin vertical panel on a block face."""
    for v in range(v0, v1 + 1):
        for u in range(u0, u1 + 1):
            lot.put(v, 0, u, "plinth")
    for y in range(1, 4):
        for v in range(v0, v1 + 1):
            for u in range(u0, u1 + 1):
                if v in (v0, v1) or u in (u0, u1):
                    lot.put(v, y, u, lot.weather(v, u, y))
    for y in range(4, 7):
        for v in range(v0, v1 + 1):
            for u in range(u0, u1 + 1):
                if v in (v0, v1) or u in (u0, u1):
                    lot.put(v, y, u, "timber" if y < 6 else "beam")
    # THE SHUTTERS FACE AWAY FROM THE WALL THEY HANG ON. A trapdoor's `facing` points out of the
    # block it is attached to, so a panel one cell west of an east wall faces WEST; written the
    # other way round it hangs off nothing and our renderer draws it as a cube either way.
    for u in range(u0 + 1, u1):
        for y in (4, 5):
            lot.put(v0 - 1, y, u, "shutter", facing=WEST, half="top", open="true",
                    powered="false", waterlogged="false")
    _cap(lot, v0, v1, u0, u1, 7, courses=2)
    return {"v": [v0, v1], "u": [u0, u1]}


def _boomtown(lot: _Lot, p: dict) -> dict:
    """F2 - Main Street: a real 5-wide street with real doors, running the lot's whole depth.

    THE STREET IS THE MODULE. It enters at the spine spur (U69-71 in park coordinates), runs east
    the full 53 courses and comes out on the cross walk at V77-79 that the grid cut for exactly
    this - so the street has a place at BOTH ends, which is the whole difference between a street
    and a cul-de-sac of false fronts. Every frontage on it is a shed with a door, a window and a
    name; `PARK_FRONTIER` requires that every false front have a real use behind it.
    """
    dv, du = lot.dv, lot.du
    eu = int(p.get("entry_u") or 23)
    out = {"shops": []}
    su0, su1 = eu - 2, eu + 2                         # the 5-wide street

    for v in range(0, dv):                            # the boardwalk, kerbed both sides
        for u in range(su0, su1 + 1):
            edge = u in (su0, su1)
            lot.put(v, 0, u, "plinth" if edge else "timber")
        if v % 8 == 4:
            lot.put(v, 0, su0 + 2, "glow")

    north = [(1, 12, "TELEGRAPH ROOM"), (14, 25, "GENERAL STORE"),
             (27, 33, "LIVERY STABLE"), (35, 45, "STAGE OFFICE")]
    south = [(1, 15, "SALOON"), (17, 30, "MINERS REST"), (32, 45, "POWDER AGENT")]
    nu0, nu1 = max(1, su0 - 13), su0 - 1
    su_0, su_1 = su1 + 1, min(du - 2, su1 + 13)

    for i, (a, b, name) in enumerate(north):
        h = 7 if i % 2 else 8
        out["shops"].append(_shed(
            lot, a, b, nu0, nu1, h=h, ridge="v", title=name,
            doors=(("+u", (a + b) // 2, 2),), false_front="+u",
            sign_face="+u", sign_lines=[name]))
    for i, (a, b, name) in enumerate(south):
        h = 8 if i % 2 else 7
        out["shops"].append(_shed(
            lot, a, b, su_0, su_1, h=h, ridge="v", title=name,
            doors=(("-u", (a + b) // 2, 2),), false_front="-u",
            sign_face="-u", sign_lines=[name]))

    # the awnings over the boardwalk, which is what a frontier street actually looks like
    for v in range(0, dv):
        for (line, step) in ((nu1 + 1, 1), (su_0 - 1, -1)):
            if not lot.has(v, 1, line - step):
                continue
            lot.stair(v, 4, line, "timber_stair", facing=_u_face(step), half="top")
            if v % 4 == 0:
                for y in range(1, 4):
                    lot.log(v, y, line, "post", axis="y")
            elif v % 4 == 2:
                lot.fence(v, 1, line, "v")

    # THE STREET HAS A PLACE AT BOTH ENDS. The east portal stands clear of the last shop fronts
    # and opens straight onto the V77-79 cross walk, which is the whole reason the grid cut one.
    out["gate"] = _arch(lot, dv - 6, dv - 2, su0 - 1, su1 + 1, axis="u", pier=1, clear_h=5,
                        title="MINING SQUARE")
    out["water_tower"] = _water_tower(lot, 30, 4, leg=7, r=3)
    for u in range(7, nu0 + 1):                       # the tower's own yard, back of the terrace
        for v in (28, 32):
            lot.put(v, 0, u, "timber")
    return out


def _square(lot: _Lot, p: dict) -> dict:
    """F3 - Mining Square: the choice point, and an open SQUARE rather than a building.

    Its role in `park_final.world.json` is `path`. The grid re-specced it from 56 x 46 to 41 x 46
    for exactly this: at 56 it ran through the back promenade and 184 cells into the Assay office,
    including the cell that is Assay's own front door. At 41, column B reads Boomtown 53 + the
    V77-79 walk + this 41 = exactly 97, and it fronts a real street.

    THE QUEUE AND THE EXIT ARE ON THE EAST FLANK, TWENTY COURSES APART. That flank faces the
    U95-97 alley and, past it, the Mine Coaster's own column - so a guest reads "queue" and "exit"
    as two separate doors to the same ride, which is what the spec asks for by name and what the
    old module got wrong by putting both on one face.
    """
    dv, du = lot.dv, lot.du
    out = {}
    out["lights"] = _pave(lot, 2, dv - 3, 2, du - 3, glow_every=8)
    out["queue"] = _arch(lot, 5, 12, du - 5, du - 2, axis="v", pier=2, clear_h=5,
                         title="COASTER QUEUE")
    out["exit"] = _arch(lot, dv - 13, dv - 6, du - 5, du - 2, axis="v", pier=2, clear_h=5,
                        title="RIDE EXIT")

    # the show board on the west side - the square's one piece of architecture, and it faces the
    # walk a guest arrives on
    v0, v1 = (dv // 2) - 5, (dv // 2) + 5
    for v in range(v0, v1 + 1):
        for y in range(1, 6):
            lot.put(v, y, 2, lot.weather(v, 2, y) if y < 3 else "timber")
        lot.log(v, 6, 2, "beam", axis="x")
    for v in (v0, v1):
        for y in range(1, 7):
            lot.log(v, y, 2, "post", axis="y")
    for v in range(v0 + 1, v1):
        lot.put(v, 4, 2, "board")
    _cap(lot, v0, v1, 2, 4, 7, courses=1)             # a canopy over the board, out over the square
    lot.sign(v0 + 2, 4, 3, SOUTH, ["MINE COASTER", "queue north", "exit south"])
    lot.sign(v1 - 2, 4, 3, SOUTH, ["MINING SQUARE", "boomtown west", "works east"])
    out["board"] = {"v": [v0, v1], "u": 2}

    # the claim marker: a low ore cart on a stub of rail, POINTING at the ride it names
    cv, cu = dv // 2, du // 2
    for u in range(cu - 3, cu + 4):
        lot.put(cv, 1, u, "plinth")
        lot.put(cv, 2, u, "rail", shape="east_west", waterlogged="false")
    for u in (cu - 4, cu + 4):
        lot.put(cv, 1, u, "base_slab")
        lot.slab(cv, 1, u, "base_slab", "bottom")
    for v in (cv - 1, cv + 1):
        for u in range(cu - 1, cu + 2):
            lot.put(v, 1, u, "plinth")
            lot.put(v, 2, u, "beam")
    for u in (cu - 1, cu + 1):
        lot.put(cv, 3, u, "shutter", facing=NORTH if u < cu else SOUTH, half="bottom",
                open="true", powered="false", waterlogged="false")
    out["marker"] = {"at": [cv, cu], "points": "east, to the Mine Coaster"}

    # THE SQUARE STANDS ONE COURSE PROUD OF THE LAWN, so it needs an edge and a way up onto it.
    # A kerb of low wall with a slab coping reads as a paved terrace; a bare cut edge reads as a
    # mistake. The north face - the one the V77-79 cross walk delivers a guest to - is opened for
    # a seven-wide flight instead, which is the width the spec asks a decision point for.
    steps = 0
    approach = range(cu - 3, cu + 4)
    for u in range(2, du - 2):
        if u in approach:
            lot.stair(u * 0 + 1, 0, u, "base_stair", facing=EAST)
            steps += 1
            continue
        lot.put(1, 0, u, "base_slab")
        lot.slab(1, 0, u, "base_slab", "bottom")
    for v in range(2, dv - 2):
        for u in (1, du - 2):
            if lot.has(v, 1, u):
                continue
            lot.put(v, 1, u, "base_wall", north="low" if v > 2 else "none",
                    south="low" if v < dv - 3 else "none", east="none", west="none",
                    up="true", waterlogged="false")
    for v in (2, dv - 3):
        for u in range(1, du - 1):
            if lot.has(v, 1, u):
                continue
            lot.slab(v, 1, u, "base_slab", "bottom")
    out["approach_steps"] = steps
    return out


def _assay(lot: _Lot, p: dict) -> dict:
    """F6 - the Assay and Prize Office: the land's one civic range, on the back promenade.

    Twenty courses deep and forty-six long is a STREET RANGE, not a pavilion, so it is built as
    one long masonry block with a centre pavilion and a stepped pediment over the door - the
    portico is what tells a guest which of forty-six columns is the way in.

    THE WINDOWS ARE BARRED AND THAT IS THE STORY. An assay office weighs gold; iron bars on the
    ground floor say what the building is for at a distance no sign is readable from.
    """
    dv, du = lot.dv, lot.du
    eu = int(p.get("entry_u") or 23)
    out = {}
    v0, v1 = 3, dv - 4
    out["range"] = _shed(lot, v0, v1, 4, du - 5, h=8, ridge="u", title="ASSAY OFFICE",
                         doors=(("-v", eu, 3), ("+v", du - 9, 2)),
                         sign_face="-v", sign_lines=["ASSAY OFFICE", "and prize window"])

    # the entrance pavilion: piers proud of the range, a lintel, a stepped pediment
    for u in (eu - 3, eu + 3):
        for y in range(0, 7):
            lot.put(v0 - 1, y, u, "plinth" if y == 0 else lot.weather(v0 - 1, u, y))
        lot.put(v0 - 1, 7, u, "band")
    for u in range(eu - 2, eu + 3):
        lot.log(v0 - 1, 7, u, "beam", axis="z")
        lot.stair(v0 - 2, 7, u, "roof", facing=EAST, half="top")
    for k in range(3):                                # the pediment, stepping in as it rises
        for u in range(eu - 2 + k, eu + 3 - k):
            lot.put(v0 - 1, 8 + k, u, "timber" if k < 2 else "board")
        lot.stair(v0 - 1, 8 + k, eu - 3 + k, "roof", facing=SOUTH)
        lot.stair(v0 - 1, 8 + k, eu + 3 - k, "roof", facing=NORTH)
    # A PEDIMENT IS A RAKE, NOT A ROOF, and it stands PROUD of the roof behind it - which is why
    # a purely local "the roof ahead is never lower than the roof behind" rule flags it. It
    # declares its own apex, and being declared last it owns the cells it shares with the gable.
    lot.roofs.append({"style": "rake", "v": [v0 - 1, v0 - 1], "u": [eu - 3, eu + 3],
                      "y0": 8, "y1": 10, "apex": eu, "axis": "u"})
    lot.slab(v0 - 1, 11, eu, "roof_slab", "bottom")
    lot.hang(v0 - 1, 5, eu - 3)
    lot.hang(v0 - 1, 5, eu + 3)

    # barred ground-floor lights along the promenade face
    for u in range(6, du - 6):
        if (u - 6) % 5 or abs(u - eu) < 5:
            continue
        for y in (1, 2):
            lot.c.put(v0, y, u, 0)
            lot.bars(v0, y, u, "u")
        lot.slab(v0, 0, u, "base_slab", "top")
        lot.log(v0, 3, u, "beam", axis="z")

    # the prize window at the south end: a counter under a shuttered hatch
    wu = du - 10
    for u in range(wu, du - 6):
        lot.c.put(v0, 1, u, 0)
        lot.c.put(v0, 2, u, 0)
        lot.slab(v0, 1, u, "base_slab", "top")
        lot.put(v0 - 1, 1, u, "band")
        # THE AWNING HANGS OFF THE WALL, NOT INSIDE IT. A trapdoor set in the wall plane has the
        # room's own air behind it and attaches to nothing; one cell proud of the band, facing
        # away from it, is a shutter over a counter.
        lot.put(v0 - 1, 3, u, "shutter", facing=WEST, half="top", open="false",
                powered="false", waterlogged="false")
    lot.sign(v0 - 1, 4, wu + 1, WEST, ["PRIZE WINDOW", "range and", "sluice results"])
    out["prize_window"] = {"v": v0, "u": [wu, du - 7]}

    # a cupola on the ridge, so a 46-long range has a centre from the skyline too
    ridge_v = (v0 + v1) // 2
    for y in range(out["range"]["ridge_y"], out["range"]["ridge_y"] + 4):
        for u in range(eu - 2, eu + 3):
            for v in range(ridge_v - 2, ridge_v + 3):
                if v in (ridge_v - 2, ridge_v + 2) or u in (eu - 2, eu + 2):
                    lot.put(v, y, u, "timber" if y < out["range"]["ridge_y"] + 3 else "beam")
    for u in range(eu - 1, eu + 2):
        for v in range(ridge_v - 1, ridge_v + 2):
            lot.c.put(v, out["range"]["ridge_y"] + 1, u, 0)
            lot.c.put(v, out["range"]["ridge_y"] + 2, u, 0)
    for u in (eu - 2, eu + 2):
        for v in range(ridge_v - 1, ridge_v + 2):
            lot.bars(v, out["range"]["ridge_y"] + 1, u, "v")
    for v in (ridge_v - 2, ridge_v + 2):
        for u in range(eu - 1, eu + 2):
            lot.bars(v, out["range"]["ridge_y"] + 1, u, "u")
    top = _cap(lot, ridge_v - 2, ridge_v + 2, eu - 2, eu + 2,
               out["range"]["ridge_y"] + 4, courses=2)
    lot.slab(ridge_v, top + 1, eu, "roof_slab", "bottom")
    lot.hang(ridge_v, out["range"]["ridge_y"], eu)
    out["cupola"] = {"at": [ridge_v, eu]}
    return out


def _works(lot: _Lot, p: dict) -> dict:
    """F9 - the Works Yard: back of house, and it looks it.

    `PARK_FULL_BUILD_SPEC`: "hidden from normal guest view except one controlled glimpse of
    track/reset work." So the shed's open front faces the SERVICE LANE at V154-156 and its back
    is a blank yard wall against the rim - a guest on the promenade sees a roof and a chimney,
    which is exactly the glimpse, and nothing else.

    Thirteen deep is what the grid actually has: the service band is exactly 18 courses (V152-169)
    and the lane takes three of them, so a lane inside the band and an 18-deep yard behind it
    cannot both exist. It gained five of width instead, which the band has.
    """
    dv, du = lot.dv, lot.du
    out = {}
    out["shed"] = _shed(lot, 1, dv - 2, 5, 18, h=6, ridge="u", title="WORKS",
                        doors=(("-v", 12, 4),), windows=True,
                        sign_face="-v", sign_lines=["WORKS YARD", "staff only"])
    out["store"] = _shed(lot, 2, dv - 2, 25, 33, h=5, ridge="u", title=None,
                         doors=(("-v", 29, 2),), windows=False)

    # the yard wall along the rim face, tying the two sheds and the gantry into one piece
    for u in range(1, du - 1):
        v = dv - 1
        lot.put(v, 0, u, "plinth")
        for y in (1, 2):
            lot.put(v, y, u, lot.weather(v, u, y))
        if u % 4 == 1:
            lot.log(v, 3, u, "post", axis="y")
            lot.slab(v, 4, u, "base_slab", "bottom")
        else:
            lot.fence(v, 3, u, "u")

    # the gantry: two legs off the yard wall, a head beam and a chain - a cart lift, which is what
    # a works yard is for, and the one glimpse of work the spec allows a guest to get.
    gv = dv - 2
    for u in (1, 3):
        for y in range(0, 6):
            lot.log(gv, y, u, "post", axis="y")
        lot.stair(gv, 5, u, "timber_stair", facing=_u_face(1 if u == 1 else -1), half="top")
    for u in range(1, 4):
        lot.log(gv, 6, u, "beam", axis="z")
    lot.put(gv, 5, 2, "chain", axis="y", waterlogged="false")
    lot.put(gv, 4, 2, "chain", axis="y", waterlogged="false")
    lot.slab(gv, 3, 2, "base_slab", "top")

    # the chimney, rising out of the store's own gable wall - the only thing on this lot a guest
    # on the promenade is meant to see over the roofline
    cv, cu = 2, 30
    for y in range(0, 10):
        lot.put(cv, y, cu, "plinth" if y == 0 else lot.weather(cv, cu, y))
    for d in ((0, -1), (0, 1)):                       # the corbel, in the wall's own plane
        lot.stair(cv, 8, cu + d[1], "base_stair", facing=_u_face(d[1]), half="top")
    lot.slab(cv, 9, cu, "base_slab", "top")
    out["chimney"] = {"at": [cv, cu], "top": 9}
    return out


KINDS = {
    "trailhead": _trailhead,
    "porch": _porch_lot,
    "boomtown": _boomtown,
    "square": _square,
    "assay": _assay,
    "works": _works,
}


# --------------------------------------------------------------------------- entry point


def build(cfg: dict, donors=None) -> Canvas:
    p = {**FRONTIER, **(cfg or {})}
    kind = p.get("kind")
    if kind not in KINDS:
        raise ValueError(f"unknown frontier build kind {kind!r}; have {sorted(KINDS)}")
    if not p.get("lot"):
        raise ValueError("a frontier build needs its measured lot: lot: [dv, du]")
    dv, du = int(p["lot"][0]), int(p["lot"][1])
    if dv < 8 or du < 8:
        raise ValueError(f"lot {dv}x{du} is too small to build anything on")
    c = Canvas(dv, 30, du, donors)
    lot = _Lot(c, dv, du, seed=int(p.get("seed", 0)))
    parts = KINDS[kind](lot, p)

    av, ay, au = (int(v) for v in p["anchor"])
    at_v, at_u = (int(v) for v in (p.get("at") or (0, 0)))
    c.world_origin = (av + at_v, ay, au + at_u)
    c.meta = {
        "kind": f"frontier_{kind}",
        "lot": [dv, du],
        "at": [at_v, at_u],
        "land": "frontier",
        "facing": "west",
        "profile_axis": "u",
        "doors": lot.doors,
        "signs": lot.signs,
        "roofs": lot.roofs,
        "stairs": len(lot.stairs),
        "refused": lot.refused,
        "parts": parts,
        "contract": (
            f"one connected frontier build filling no cell outside its {dv}x{du} lot, every "
            "opening framed with two whole jambs and a lintel between their tops, every stair "
            "leaning the way it climbs, every sign on a wall that is there, and no street "
            "furniture - the ground layer already draws all of it"),
    }
    return c
