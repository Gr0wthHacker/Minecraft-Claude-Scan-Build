"""THE PARK'S HIGH POINTS: three climbable towers, one per land, and the summit is one of them.

    PF Vantage Frontier Lookout   17 x 17  at V130, U0     deck 44 above the lawn  (world Y247)
    PF Vantage Midway Belvedere   15 x 15  at V139, U228   deck 36 above the lawn  (world Y239)
    PF Vantage Prism Summit       15 x 16  at V44,  U526   deck 65 above the lawn  (world Y268)

---------------------------------------------------------------------------------------------
WHY THESE EXIST, MEASURED

Flooding every standable cell reachable on foot from the spine over `out/Park Complete.litematic`
- solid below, two clear courses above, stepping at most one course either way - gives:

    reachable standable cells                117,675
    ...in the bottom TEN courses             112,407   (95.5%)
    ...above park y30                            337
    ...above park y50                            146
    highest a visitor can WALK to                 y53   - and that is coaster structure, not a place
    the park's tallest block                      y96

**THE PARK IS 96 COURSES TALL AND 95.5% OF WHERE YOU CAN STAND IS IN THE BOTTOM TEN.** The Prism
Ascent is 83 tall and inert, the Sky Lift 76 and unclimbable. Nobody could look down on this park
from anywhere. That is the gap these three close, and `tests/test_park_vantage.py` re-derives every
number above rather than trusting this docstring.

---------------------------------------------------------------------------------------------
A SUMMIT IS A ROOM WITH A PARAPET, NOT A HEIGHT

Every one of the three is the same building type - a stair tower - and the type is chosen because
it is the only one that answers all four of the brief's demands at once: somewhere to get to, a
climb that is part of the experience, places to stand and look ON THE WAY UP, and room at the top
for more than one person. So each tower is a stack of ROOMS, not a shaft with a ladder in it:

    * a dog-leg stair - a flight up the west band, cross the landing, a flight back up the east
      band - so you turn 180 degrees and cross a room at every storey;
    * a real floor at every storey, with a stair well cut in it and a window on each outward face;
    * a LOGGIA storey partway up: the whole of one face opened into an arcade with a balustrade
      at sill height, which is a place to stop and look out rather than a place you pass;
    * a crown deck with a parapet, a light rhythm, and a crown treatment that is the land's own.

**A LOGGIA, NEVER A CANTILEVERED BALCONY.** A balcony hangs outside the shaft and therefore
outside the lot, and this park has already lost a 111-block ride to one cell of overhang. An
arcade recessed into the wall line is the same experience and cannot leave the lot by
construction: `_Lot.put` refuses anything that tries.

---------------------------------------------------------------------------------------------
THE STAIR CONVENTION, ASSERTED AND NEVER EYEBALLED

A flight that ascends toward D has every tread `facing=D, half=bottom`; built the other way the
risers face into the descent and you cannot walk up it - and this repo's renderer draws both
identically. So `_flight` derives `facing` from the step vector it is already walking, and
`tests/test_park_vantage.py` asserts the facing of every tread against its own ascent.

**AND A FLIGHT IS NOTHING WITHOUT HEADROOM.** A buried stair audits as one clean solid: every
cell legal, supported, affordable, one connected piece, and unwalkable. Two courses over every
tread and every floor cell is therefore a PLACEMENT RULE here, not a check afterwards -
`_floor` refuses to lay a slab over a tread within two courses of it, which is what cuts the
stair well without anybody drawing one.

---------------------------------------------------------------------------------------------
THE ONE DELIBERATE ATTACHMENT: THE PRISM ASCENT'S PODIUM ROOF

The Prism Ascent already carries a walkable gallery nobody can reach. Measured off
`out/Park Complete.litematic`, its podium roof is a solid annular slab at park y25 - seven cells
wide, ringing the spire's court - carrying a post-and-rail balustrade at y26, with two clear
courses over it. It is 1,100-odd cells of finished architecture standing twelve courses over the
lawn with no stair, no ramp and no bridge to it.

    park y25   podium roof slab, solid from U542 to U583 for every V51..V89
    park y26   air at U542 for every V51..V89; a rail post at U543
    park y27+  air

So the Summit's storey-one floor is at canvas y12 - park y25 - **because that is the podium's own
course**, and one cell of bridge deck at U541 lands a walker on the Ascent's roof at U542 at
exactly the same level. Nothing of this design stands in a cell the Ascent owns; the shared
surface is the roof it already built. That is why the Summit's `rise` is 13 and not 12: the
storey height is set by the thing it connects to.

`tests/test_park_vantage.py` floods from the park's ground to the podium roof and asserts it, so
if the Ascent's owner moves that course the bridge fails here rather than in game.

---------------------------------------------------------------------------------------------
WHAT IS DELIBERATELY NOT IN HERE

* **No paving, no lamp post, no bench, no spur.** `Park Ways` owns the ground and is finished; a
  building that brings its own street furniture is how the previous park became "chaos". Every
  cell of every one of these three is checked against the shipped street mask.
* **No cell in V171-199** (the protected rim reserve) and none in the reaches U170-214 or
  U385-429, which another stream's water owns.
* **No dirt family and no cobblestone** - `blocks.spendable` and the land palettes decide, and the
  test re-derives both off the registry rather than off this list.
"""
from __future__ import annotations

from .canvas import Canvas, hash01
from .parkways import LANDS as WAYS_LANDS

ANCHOR = (97500, 203, 80300)      # V0 -> world X, the first course above the lawn, U0 -> world Z

#: The park's own bands, so a vantage cannot be sited into somebody else's reserve. These are the
#: same numbers `configs/park_ways.yaml` states in its depth programme; they are duplicated here
#: only as a REFUSAL, never as a layout.
RIM_RESERVE = (171, 199)
REACHES = ((170, 214), (385, 429))


# --------------------------------------------------------------------------- the palettes
#
# THE FOUR ANCHOR MATERIALS OF EVERY LAND COME FROM `parkways.LANDS` AND ARE NOT RETYPED. A
# vantage stands on that land's own ground and has to read as the same hand; a second copy of the
# palette is a second thing to forget when the ground changes. What is added here is the
# vocabulary a tower needs and a street does not - stairs, slabs, walls, a roof, a grille.

def _pal(land: str) -> dict:
    if land not in WAYS_LANDS:
        raise ValueError(f"unknown land {land!r}; have {sorted(WAYS_LANDS)}")
    w = WAYS_LANDS[land]
    base = {
        # INHERITED FROM THE GROUND, so the tower is tied to the paving at its own feet: the base
        # course is the land's own kerb material and the light is the land's own light.
        "plinth": w["border"],
        "thresh": w["core"],         # the land's own paving - the door threshold and the bridge
        "post":   w["post"],
        "light":  w["light"],
        "seat":   w["seat"],
        "glow":   w["glow"],
        "grille": "iron_bars",
    }
    base.update(_WALLS[land])
    return base


#: THE WALL VOCABULARY IS NOT THE PAVING VOCABULARY, and that is the one place this file departs
#: from `parkways.LANDS` on purpose. `core` is what a land's STREET is made of - `smooth_stone`
#: for the Midway, `polished_deepslate` for Prismworks - and both are `ok` tier. A four-thousand
#: cell tower built out of a paving material would be `ok` in bulk, which is the material policy
#: every other build in this park keeps (cheap in bulk, `ok` only as trim). So the bulk here is
#: each land's own BUILDING material, the same one `frontier_builds`, `midway_builds` and
#: `prismworks_builds` already stand on that ground: spruce and dark oak over stone brick, stone
#: brick and white wool, polished blackstone and smooth basalt.
#:
#: Every entry is 1.19-legal and spendable and the bulk is cheap; `test_park_vantage` re-derives
#: all of that off `mcbuild.blocks` and `mcbuild.palette` rather than trusting this table.
_WALLS = {
    # L45 plinth, L122 masonry, L89 timber pier, L46 roof - the timber-framed watch tower
    "frontier": {
        "field": "stone_bricks", "grain": "cracked_stone_bricks", "band": "chiseled_stone_bricks",
        "trim": "spruce_planks", "column": "spruce_log", "board": "spruce_planks",
        "stair": "stone_brick_stairs", "slab": "stone_brick_slab", "wall": "stone_brick_wall",
        "roof": "dark_oak_stairs", "roof_slab": "dark_oak_slab", "roof_field": "dark_oak_planks",
        "accent": "dark_oak_planks", "crown_light": "lantern",
    },
    # L122 field, L236 frame, L65 band - the brightest land, so the pilaster is the white one
    "midway": {
        "field": "stone_bricks", "grain": "cracked_stone_bricks", "band": "chiseled_stone_bricks",
        "trim": "white_wool", "column": "white_wool", "board": "oak_planks",
        "stair": "stone_brick_stairs", "slab": "stone_brick_slab", "wall": "stone_brick_wall",
        "roof": "oak_stairs", "roof_slab": "oak_slab", "roof_field": "red_wool",
        "accent": "red_wool", "crown_light": "lantern",
    },
    # L22 recess, L45 field, L73 pier, L145 high signal - cold and mechanical, lit cold
    "prismworks": {
        "field": "polished_blackstone_bricks", "grain": "cracked_polished_blackstone_bricks",
        "band": "smooth_basalt", "trim": "smooth_basalt", "column": "smooth_basalt",
        "board": "chiseled_deepslate",
        "stair": "polished_blackstone_brick_stairs", "slab": "polished_blackstone_brick_slab",
        "wall": "polished_blackstone_brick_wall",
        "roof": "blackstone_stairs", "roof_slab": "blackstone_slab", "roof_field": "black_wool",
        "accent": "light_blue_wool", "crown_light": "soul_lantern",
        # PRISMWORKS IS THE ONE LAND WHOSE PLINTH IS NOT ITS GROUND'S BORDER. Measured,
        # `deepslate_tiles` is 55 of luminance against this field's 47 - eight apart, which is
        # not a line, and a base course that cannot be seen is not a base course. `black_wool`
        # is the land's own recess at 22, and 25 clear of the field.
        "plinth": "black_wool",
    },
}


PARK_VANTAGE = {
    "kind": "tower",
    "land": None,                # frontier | midway | prismworks
    "at": None,                  # [V, U] - the lot's near corner in park coordinates
    "size": None,                # [depth along V, width along U] - the LOT, the hard boundary
    "shaft": None,               # [depth, width] of the tower itself; defaults to `size`
    "rise": 12,                  # courses per storey, and the number of treads in a flight
    "storeys": 3,                # flights; the crown deck's walking surface is rise * storeys
    "door": "west",              # the face the ground door opens on: north | south | east | west
    #: WHICH WALL THE FIRST FLIGHT CLIMBS. It decides, storey by storey, which of the two long
    #: walls a flight is against - and therefore which face is free to be opened as a loggia,
    #: because a stair needs its stringer and an arcade cut through one is an island. See
    #: `_check_loggia`, which refuses the combination rather than shipping it.
    "stair_from": "west",        # west | east
    "loggia": None,              # [{level, face}] - a storey whose whole face is an open arcade
    "crown": "pavilion",         # gallery | cabin | pavilion
    "look": "west",              # the direction the crown frames, recorded in the sidecar
    #: {level, face, v0, v1} - a one-cell deck out of the shaft onto something already standing.
    #: Only the Summit uses it and the cells it lays are inside the lot like everything else.
    "bridge": None,
    "title": None,
    #: **AN ORIENTATION BOARD ON THE CROWN DECK, AND IT IS OFF BY DEFAULT.** Measured over the
    #: shipped park, `PF Vantage Frontier Lookout` is 15.3 blocks per column and 56 courses tall -
    #: the densest thing in its land - and carries ZERO interactive blocks: you climb it and there
    #: is nothing there. That is the complaint Jack has made of this park three separate times
    #: ("really nice to look at - but serve no actual defined purpose"), and for an observation
    #: tower the answer is not a game: it is the board that tells you what you are looking AT, and
    #: the bell a lookout rings. This module is shared with Prismworks, so it is opt-in rather than
    #: a default - a shared generator that changes under its other callers is a different bug.
    "deck_board": None,          # [[line, line, line], ...] - up to four signs, 15 chars a line
    "deck_bell": False,          # a bell on the deck: the one verb a lookout actually has
    "seed": 0,
}

_FACES = {"north": (0, -1), "south": (0, 1), "west": (-1, 0), "east": (1, 0)}
#: V is world X and U is world Z, so +V is east and +U is south. A tread ascending toward D is
#: `facing=D`; this is the only place the mapping is written down.
_DIR_OF_STEP = {(1, 0): "east", (-1, 0): "west", (0, 1): "south", (0, -1): "north"}
SIGN_WIDTH = 15                  # a sign line clips mid-word past this


class _Lot:
    """The lot, and the only way a block reaches the canvas.

    Everything is placed through `put`, so the boundary is one check in one place - and it is
    counted rather than cropped, because a cropped parapet is not a fault anything downstream can
    report. `treads` is kept as it goes so `_floor` can refuse to bury a stair without anybody
    having to draw a stair well.
    """

    def __init__(self, c: Canvas, dv: int, du: int, seed: int = 0):
        self.c, self.dv, self.du, self.seed = c, dv, du, seed
        self.refused = 0
        self.treads: dict[tuple[int, int], list[int]] = {}
        self.lights = 0
        self._state: dict[str, int] = {}

    def blk(self, name: str) -> int:
        if name not in self._state:
            self._state[name] = self.c.state(name)
        return self._state[name]

    def put(self, v: int, u: int, y: int, name: str, **props) -> bool:
        v, u, y = int(v), int(u), int(y)
        if not (0 <= v < self.dv and 0 <= u < self.du and 0 <= y < self.c.sy):
            self.refused += 1
            return False
        blk = self.c.raw_state(name, **props) if props else self.blk(name)
        return self.c.put(v, y, u, blk)

    def has(self, v: int, u: int, y: int) -> bool:
        if not (0 <= v < self.dv and 0 <= u < self.du and 0 <= y < self.c.sy):
            return False
        return self.c.solid(int(v), int(y), int(u))

    def clear(self, v: int, u: int, y: int) -> None:
        if 0 <= v < self.dv and 0 <= u < self.du and 0 <= y < self.c.sy:
            self.c.put(int(v), int(y), int(u), 0)

    def tread(self, v: int, u: int, y: int, name: str, facing: str) -> bool:
        ok = self.put(v, u, y, name, facing=facing, half="bottom",
                      shape="straight", waterlogged="false")
        if ok:
            self.treads.setdefault((int(v), int(u)), []).append(int(y))
        return ok

    def tread_near(self, v: int, u: int, y: int, within: int) -> bool:
        """Is there a tread in this column within `within` courses at or below y?

        The rule that cuts every stair well in this file. A floor slab at y over a tread at y-1
        leaves one clear course, and one clear course is a stair you cannot climb."""
        return any(y - within <= t <= y for t in self.treads.get((int(v), int(u)), ()))

    def lamp(self, v: int, u: int, y: int, name: str, **props) -> bool:
        if self.put(v, u, y, name, **props):
            self.lights += 1
            return True
        return False


# --------------------------------------------------------------------------- the tower


def _tower(L: _Lot, p: dict, pal: dict, sv: int, su: int) -> dict:
    """A stair tower: shell, dog-leg flights, a floor per storey, loggias, and a crown.

    `sv`/`su` are the SHAFT's footprint inside the lot; anything the lot has beyond it is the
    bridge column, which the shaft must not wall itself off from.
    """
    rise, storeys = int(p["rise"]), int(p["storeys"])
    top = rise * storeys                       # the crown deck's walking surface
    land = p["land"]
    accent = pal["accent"]
    vi0, vi1 = 1, sv - 2                       # interior, one cell in from the shell
    ui0, ui1 = 1, su - 2
    if rise > (ui1 - ui0 + 1):
        raise ValueError(f"rise {rise} needs an interior at least {rise} long along U; "
                         f"this shaft gives {ui1 - ui0 + 1}")
    if sv < 11 or su < 11:
        raise ValueError("a vantage shaft under 11 across has no room for a dog-leg stair")

    loggias = {(int(g["level"]), g["face"]) for g in (p.get("loggia") or ())}
    loggia_levels = {lv for lv, _ in loggias}

    # 1. the flights, first, because every floor is cut around them --------------------
    flights = []
    for k in range(storeys):
        west = _band_is_west(k, p)
        band = (vi0, vi0 + 2) if west else (vi1 - 2, vi1)
        step = 1 if west else -1                      # +u climbing south, -u climbing north
        u_from = ui0 if west else ui1
        flights.append(_flight(L, pal, band, u_from, step, k * rise, rise))

    # 2. the shell ---------------------------------------------------------------------
    _shell(L, p, pal, sv, su, top, accent, loggias)

    # 3. a floor at every storey, and the crown deck -----------------------------------
    for k in range(1, storeys + 1):
        y = k * rise - 1                              # the floor BLOCK; you stand at y + 1
        crown = (k == storeys)
        _floor(L, pal, vi0, ui0, vi1, ui1, y, pal["board"] if not crown else pal["thresh"])
        if not crown:
            _storey_fit(L, p, pal, sv, su, vi0, ui0, vi1, ui1, y, k, rise, top, accent,
                        k in loggia_levels)

    # 4. the climb's own light ----------------------------------------------------------
    _stair_lights(L, pal, sv, su, flights)

    # 5. the crown ---------------------------------------------------------------------
    crown_cells = _crown(L, p, pal, sv, su, vi0, ui0, vi1, ui1, top, accent)

    return {"flights": flights, "top_surface": top, "crown": p["crown"],
            "crown_cells": crown_cells}


def _stair_lights(L: _Lot, pal: dict, sv: int, su: int, flights: list) -> int:
    """The land's own emitter SET INTO the wall beside the flight, every sixth tread.

    A sixty-five course stairwell lit only by a lantern on each landing is a dark hole with two
    lit ends, and dark on this server is not a mood - it is where things spawn. The emitter is a
    full block and the wall is already solid behind every tread (that is the stringer), so it
    costs no structure and hangs from nothing: it is simply a course of the wall that gives
    light. A cell that is not solid is skipped rather than filled, so a window is never bricked
    up to make room for a lamp."""
    n = 0
    for f in flights:
        west = f["band"][0] <= 1
        v = 0 if west else sv - 1
        du = 1 if f["u_to"] > f["u_from"] else -1
        for i in range(0, abs(f["u_to"] - f["u_from"]) + 1, 6):
            u, y = f["u_from"] + du * i, f["from"] + i + 1
            if L.has(v, u, y):
                n += bool(L.lamp(v, u, y, pal["glow"]))
    return n


def _band_is_west(k: int, p: dict) -> bool:
    """Which wall storey `k`'s flight climbs. Alternating, from whichever wall the config names."""
    first = p.get("stair_from", "west")
    if first not in ("west", "east"):
        raise ValueError(f"stair_from must be west or east, got {first!r}")
    return (k % 2 == 0) == (first == "west")


def _check_loggia(p: dict) -> None:
    """AN ARCADE MAY NOT BE CUT THROUGH A STAIR'S OWN STRINGER, and this refuses rather than
    silently patching it.

    A flight's outer column touches the shell and is held on by it. Open that wall at a course
    where a tread meets it and the tread comes away as an island with nothing to place it
    against; leave one block of masonry in the opening instead and it is a step a visitor climbs
    onto and walks off the tower. Both were built and measured. The only answer is to put the
    loggia on a wall that storey's flight is not against - and since the flights alternate,
    `stair_from` is the dial that makes any face available at any level."""
    for g in (p.get("loggia") or ()):
        level, face = int(g["level"]), g["face"]
        if face not in ("west", "east"):
            continue                            # north and south are met only at a flight's ends
        west = _band_is_west(level, p)
        if (face == "west") == west:
            other = "east" if west else "west"
            raise ValueError(
                f"the loggia at level {level} faces {face}, and that storey's flight climbs the "
                f"{face} wall - the arcade would cut its own stringer. Put it on the {other} "
                f"face, on the north or south, at an odd level, or set stair_from to "
                f"{'east' if p.get('stair_from', 'west') == 'west' else 'west'}")


def _flight(L: _Lot, pal: dict, band: tuple[int, int], u_from: int, step: int,
            y_from: int, n: int) -> dict:
    """`n` treads, three wide, rising one course a cell along U.

    The FACING IS DERIVED FROM THE STEP, never chosen: a flight ascending toward D has every tread
    facing D, and picking it by hand is how a flight ships that cannot be walked up while every
    render in this repo draws it correctly."""
    facing = _DIR_OF_STEP[(0, step)]
    v0, v1 = band
    for i in range(n):
        u = u_from + step * i
        y = y_from + i
        for v in range(v0, v1 + 1):
            L.tread(v, u, y, pal["stair"], facing)
    return {"from": y_from, "to": y_from + n - 1, "facing": facing,
            "band": [v0, v1], "u_from": u_from, "u_to": u_from + step * (n - 1)}


def _floor(L: _Lot, pal: dict, vi0: int, ui0: int, vi1: int, ui1: int, y: int,
           name: str) -> int:
    """A storey floor - and the stair well is what this REFUSES to lay, not something drawn.

    A slab at y over a tread at y-1 or y-2 leaves the climber one clear course or none. So the
    floor simply skips any column carrying a tread within two courses below it, and the opening
    that leaves is the well. Where a tread sits AT y it is already the floor there."""
    n = 0
    for v in range(vi0, vi1 + 1):
        for u in range(ui0, ui1 + 1):
            if L.has(v, u, y) or L.tread_near(v, u, y, 2):
                continue
            n += bool(L.put(v, u, y, name))
    return n


def _shell(L: _Lot, p: dict, pal: dict, sv: int, su: int, top: int, accent: str,
           loggias: set) -> None:
    """The wall: a plinth, a pier rhythm, a string course at every storey, and openings.

    REGULARITY AND OPENINGS ARE WHAT MAKE VOXELS READ AS ARCHITECTURE, not damage - so the field
    is weathered by a hash on the CELL (hashed on the course it comes out as horizontal stripes,
    which this project has shipped once) and every line is a PROJECTION: a plinth that oversails,
    a string course of slabs, a corbel of upside-down stairs under the crown.
    """
    rise, storeys, seed = int(p["rise"]), int(p["storeys"]), int(p["seed"])
    door = p["door"]
    #: THE WALL STOPS AT THE DECK'S OWN COURSE AND THE PARAPET TAKES OVER. Run up one course
    #: further and the deck is a room you cannot see out of: a solid course at a standing
    #: visitor's feet AND another at their head is a wall, and a summit that cannot be looked
    #: out of is the one thing this design must not build.
    hi = top - 1
    ring = [(v, u) for v in range(sv) for u in range(su)
            if v in (0, sv - 1) or u in (0, su - 1)]
    corner = {(0, 0), (0, su - 1), (sv - 1, 0), (sv - 1, su - 1)}
    # the ground door: three cells wide, two courses high, centred on its face
    door_cells = _door_cells(sv, su, door)
    for (v, u) in ring:
        pier = (v in (0, sv - 1) and u % 4 == 0) or (u in (0, su - 1) and v % 4 == 0)
        slot = not pier and (v, u) not in corner and (
            (v in (0, sv - 1) and u % 4 == 2) or (u in (0, su - 1) and v % 4 == 2))
        for y in range(0, hi + 1):
            if (v, u) in door_cells and y <= 1:
                continue                       # the way in
            if _is_loggia(v, u, sv, su, y, rise, loggias) and not pier and (v, u) not in corner:
                continue                       # the arcade's open bay
            k, base, h = _window_course(y, rise, storeys, top)
            # A WINDOW IS ALL OR NOTHING. Where a tread meets this wall cell the masonry has to
            # stay - a stair needs a stringer - and patching just that ONE course of an otherwise
            # open slot is worse than both: it leaves a solid block in the middle of an opening,
            # which is a step a visitor climbs onto and walks off the tower. Measured both ways;
            # the whole slot closes.
            if slot and k is not None and not any(
                    _abuts_tread(L, v, u, sv, su, base + 1 + i) for i in range(h + 1)):
                if k == 0:
                    # A GUARD AT THE SILL, NEVER AN OPEN ONE. A one-course step is a legal step,
                    # so an opening that begins at the sill is a window a visitor can climb into
                    # and fall out of - and the flood proof would find that route and call the
                    # tower connected. A `wall` block is a block and a half: it cannot be stood
                    # on, and an eye at 1.62 still sees over it.
                    L.put(v, u, y, pal["wall"], up="true", north="none", south="none",
                          east="none", west="none", waterlogged="false")
                continue                       # ...and the two courses over it are the view
            L.put(v, u, y, _face_block(pal, accent, v, u, y, rise, storeys, top,
                                       pier, (v, u) in corner, seed))
    _portal(L, pal, sv, su, door, door_cells)
    _corbel(L, pal, sv, su, top)


def _portal(L: _Lot, pal: dict, sv: int, su: int, door: str, door_cells: set) -> None:
    """A jamb, a lintel and two lights, so the way in reads as a way in.

    A three-cell hole in a blank field is not a door at any distance - what tells you a building
    can be entered is the FRAME round the hole, which is the same rule the whole park is built on:
    regularity and openings, never damage."""
    dv, du = _FACES[door]
    for (v, u) in door_cells:
        L.put(v, u, 2, pal["band"])            # the lintel, one course over the opening
    jam = []
    if dv:
        us = sorted(u for _, u in door_cells)
        jam = [(next(iter(door_cells))[0], us[0] - 1), (next(iter(door_cells))[0], us[-1] + 1)]
    else:
        vs = sorted(v for v, _ in door_cells)
        jam = [(vs[0] - 1, next(iter(door_cells))[1]), (vs[-1] + 1, next(iter(door_cells))[1])]
    for (v, u) in jam:
        for y in (0, 1, 2):
            L.put(v, u, y, pal["column"])
        # THE DOOR'S LIGHT IS SET INTO THE JAMB, NOT HUNG BESIDE IT. A lantern outside the wall
        # would stand in the lawn the park's own ground owns, and one hung inside would want a
        # ceiling this storey does not have for another eleven courses. The land's own emitter is
        # a full block, so it can simply be a course of the jamb.
        L.lamp(v, u, 1, pal["glow"])


def _face_block(pal: dict, accent: str, v: int, u: int, y: int, rise: int, storeys: int,
                top: int, pier: bool, corner: bool, seed: int) -> str:
    if y <= 1:
        return pal["plinth"]                   # the dark base, two courses, oversailing nothing
    if y == top - 1:
        return pal["band"]                     # the deck's own course, and the last of the wall
    if y == top - 3:
        return accent                          # the crown band - the one course of colour
    if y % rise == rise - 1 and y < top:
        return pal["band"]                     # a string course at every storey floor
    if corner:
        return pal["column"]
    if pier:
        return pal["trim"]
    return pal["grain"] if hash01(v, u * 7 + y, 17, seed) < 0.14 else pal["field"]


def _abuts_tread(L: _Lot, v: int, u: int, sv: int, su: int, y: int) -> bool:
    """Is the interior cell against this wall cell a tread at exactly this course?

    **A STAIR NEEDS A STRINGER.** The flights are three wide and their outer column touches the
    shell, which is the only thing holding them on: open a window at the course a tread meets the
    wall and that tread's three cells come away as an island joined to the rest of the tower by
    nothing but a diagonal. The connectivity check found sixteen such islands the first time this
    ran, and a printer would have had nothing to place any of them against."""
    if v == 0:
        inner = (1, u)
    elif v == sv - 1:
        inner = (sv - 2, u)
    elif u == 0:
        inner = (v, 1)
    else:
        inner = (v, su - 2)
    return L.tread_near(inner[0], inner[1], y, 0)


def _window_course(y: int, rise: int, storeys: int, top: int):
    """(role, the storey's surface, the opening's height) - role 0 is the sill guard, 1 an open
    course, and None means this course is plain masonry.

    A window belongs to a STOREY, so it is measured off that storey's own walking surface: sill
    guard at S+1, open from S+2 up."""
    h = max(2, min(4, rise - 5))               # the opening's own height, under the string course
    for k in range(storeys):
        s = k * rise
        if s + 1 + h > top - 2:
            break                              # no room under the deck for a full window
        if y == s + 1:
            return 0, s, h
        if s + 2 <= y <= s + 1 + h:
            return 1, s, h
    return None, 0, h


def _is_loggia(v: int, u: int, sv: int, su: int, y: int, rise: int, loggias: set) -> bool:
    """The open courses of an arcaded face: the two above its balustrade sill."""
    for level, face in loggias:
        base = level * rise                    # the storey's walking surface
        if not (base + 1 <= y <= base + 3):
            continue
        if face == "west" and v == 0:
            return True
        if face == "east" and v == sv - 1:
            return True
        if face == "north" and u == 0:
            return True
        if face == "south" and u == su - 1:
            return True
    return False


def _door_cells(sv: int, su: int, door: str) -> set:
    if door not in _FACES:
        raise ValueError(f"door must be one of {sorted(_FACES)}, got {door!r}")
    if door in ("west", "east"):
        v = 0 if door == "west" else sv - 1
        mid = su // 2
        return {(v, mid - 1), (v, mid), (v, mid + 1)}
    u = 0 if door == "north" else su - 1
    mid = sv // 2
    return {(mid - 1, u), (mid, u), (mid + 1, u)}


def _corbel(L: _Lot, pal: dict, sv: int, su: int, top: int) -> None:
    """An upside-down stair course under the crown, leaning into the wall it grows from.

    A projection reads at a hundred blocks where a tone step reads at ten, and this is the one
    line that tells the crown from the shaft at the distance a tower is actually seen from."""
    y = top - 2
    for v in range(sv):
        for u in range(su):
            if not (v in (0, sv - 1) or u in (0, su - 1)):
                continue
            if v == 0:
                f = "east"
            elif v == sv - 1:
                f = "west"
            elif u == 0:
                f = "south"
            else:
                f = "north"
            L.put(v, u, y, pal["stair"], facing=f, half="top", shape="straight",
                  waterlogged="false")


def _storey_fit(L: _Lot, p: dict, pal: dict, sv: int, su: int, vi0: int, ui0: int,
                vi1: int, ui1: int, y: int, level: int, rise: int, top: int, accent: str,
                is_loggia: bool) -> None:
    """What makes a storey a ROOM: a light, a bench, and a loggia balustrade.

    A tower with a floor every twelve courses and nothing on any of them is a fire escape.

    **EVERY FITTING IS PLACED AGAINST SOMETHING, AND CHECKED.** A hanging lantern wants a block
    over it and a bench wants a floor under it, and this storey has neither everywhere: the well
    is a hole in the floor by construction and the storey above it may be a hole in the ceiling
    for the same reason. Placed blind, both come out as single free-floating cells - which is
    exactly what the connectivity check found the first time this ran.
    """
    s = y + 1                                  # the walking surface of this storey
    ceiling = min((level + 1) * rise - 1, top - 1)   # the floor of the storey above
    for (v, u) in ((vi0, ui1), (vi1, ui0)):
        if L.has(v, u, ceiling) and not L.has(v, u, ceiling - 1):
            L.lamp(v, u, ceiling - 1, pal["light"], hanging="true", waterlogged="false")
    # a bench facing the window, on the side the flight is not on - and only over real floor
    bv = vi1 - 1 if level % 2 == 0 else vi0 + 1
    for u in (ui0 + 2, ui0 + 3):
        if L.has(bv, u, y) and not L.has(bv, u, s):
            L.put(bv, u, s, pal["seat"], facing="west" if level % 2 == 0 else "east",
                  half="bottom", shape="straight", waterlogged="false")
    if not is_loggia:
        return
    # the arcade's balustrade: a wall course at sill height across every open bay, so the storey
    # is open to look out of and cannot be walked out of
    for g in (p.get("loggia") or ()):
        if int(g["level"]) != level:
            continue
        cells = _face_line(sv, su, g["face"])
        for (v, u) in cells:
            if L.has(v, u, s):
                L.clear(v, u, s)
            L.put(v, u, s, pal["wall"], up="true", north="none", south="none",
                  east="none", west="none", waterlogged="false")
        # A COLONNETTE, THREE COURSES - never one full block in the balustrade line. A single
        # block there is a step: a visitor climbs onto it out of a `wall` run they cannot climb,
        # and walks off the tower. The flood found exactly that, which is what it is for.
        for (v, u) in cells[2::5]:
            for dy in (0, 1, 2):
                L.put(v, u, s + dy, accent)


def _face_line(sv: int, su: int, face: str) -> list:
    if face == "west":
        return [(0, u) for u in range(1, su - 1)]
    if face == "east":
        return [(sv - 1, u) for u in range(1, su - 1)]
    if face == "north":
        return [(v, 0) for v in range(1, sv - 1)]
    if face == "south":
        return [(v, su - 1) for v in range(1, sv - 1)]
    raise ValueError(f"unknown face {face!r}")


# --------------------------------------------------------------------------- the crowns


def _crown(L: _Lot, p: dict, pal: dict, sv: int, su: int, vi0: int, ui0: int,
           vi1: int, ui1: int, top: int, accent: str) -> int:
    """The land's own crown, and then the parapet that keeps a visitor on the deck.

    **THE PARAPET IS ONE COURSE, AT THE VISITOR'S FEET.** A `wall` block is a block and a half
    tall and an eye is a little over one and a half up, so a single course of it cannot be walked
    through and CAN be seen over. Two solid courses would be a room with no view, which is the
    one thing a summit must not be.

    The crown is laid FIRST and the parapet skips whatever it finds, so a corner pier and a
    parapet pier can never fight over the same cell - the failure that would otherwise show up
    only as a light count being quietly wrong."""
    s = top                                    # the deck's walking surface
    kind = p["crown"]
    if kind == "cabin":
        n = _crown_cabin(L, pal, sv, su, vi0, ui0, vi1, ui1, s, accent)
    elif kind == "pavilion":
        n = _crown_pavilion(L, pal, sv, su, vi0, ui0, vi1, ui1, s, accent)
    elif kind == "gallery":
        n = _crown_gallery(L, pal, sv, su, vi0, ui0, vi1, ui1, s, accent)
    else:
        raise ValueError(f"unknown crown {kind!r}; have cabin | pavilion | gallery")
    for v in range(sv):
        for u in range(su):
            if not (v in (0, sv - 1) or u in (0, su - 1)):
                continue
            if L.has(v, u, s):
                continue
            if (v + u) % 5 == 0:
                n += bool(L.put(v, u, s, pal["column"]))
                n += bool(L.put(v, u, s + 1, pal["column"]))
                n += bool(L.lamp(v, u, s + 2, pal["crown_light"], hanging="false",
                                 waterlogged="false"))
            else:
                n += bool(L.put(v, u, s, pal["wall"], up="true", north="none", south="none",
                                east="none", west="none", waterlogged="false"))
    n += _deck_fittings(L, p, pal, sv, su, vi0, ui0, vi1, ui1, s)
    return n


def _deck_fittings(L, p, pal, sv, su, vi0, ui0, vi1, ui1, s) -> int:
    """The orientation board and the bell, on the open half of the crown deck.

    **A SIGN'S SUPPORT IS CHECKED, NOT ASSUMED**, and this module's own `SIGN_WIDTH` is 15 - a line
    past that clips mid-word, which this park has shipped twice. **AND A BELL HANGS FROM A CEILING
    ATTACHMENT**, so its head beam goes in first: the same rule as a chain and a hanging lantern,
    and the reason a fitting placed blind comes away as a cluster with nothing to place against.
    """
    lines = p.get("deck_board") or []
    if not lines and not p.get("deck_bell"):
        return 0
    n = 0
    # the OPEN half of the deck - the cabin takes vi0..vi0+6, so the board goes at the far end
    bv = vi1 - 2
    mid = (ui0 + ui1) // 2
    if lines:
        for du in (-2, 2):                       # two posts
            for y in (s + 1, s + 2, s + 3):
                n += bool(L.put(bv, mid + du, y, pal["column"]))
        for du in range(-1, 2):                  # the board between them
            for y in (s + 2, s + 3):
                n += bool(L.put(bv, mid + du, y, pal["board"]))
        for k, text in enumerate(lines[:3]):
            du = -1 + k
            over = [t for t in text if isinstance(t, str) and len(t) > SIGN_WIDTH]
            if over:
                raise ValueError(f"a deck sign line clips past {SIGN_WIDTH} chars: {over}")
            if L.has(bv, mid + du, s + 3) and not L.has(bv - 1, mid + du, s + 3):
                # the sign's block is taken from the land's own timber rather than a palette key
                # this module does not have - only the Frontier opts in, and a `sign` key added to
                # all three palettes would be a change to two lands that asked for nothing.
                sign = pal.get("sign") or (
                    "spruce_wall_sign" if "spruce" in pal.get("column", "") else "oak_wall_sign")
                if L.put(bv - 1, mid + du, s + 3, sign, facing="west",
                         waterlogged="false"):
                    L.c.sign_text(bv - 1, s + 3, mid + du,
                                  front=[str(t)[:SIGN_WIDTH] for t in list(text)[:4]] + [""] * 4,
                                  colour="white", glowing=True)
                    n += 1
    if p.get("deck_bell"):
        cv = vi1 - 5
        for du in (-1, 1):
            for y in (s + 1, s + 2, s + 3):
                n += bool(L.put(cv, mid + du, y, pal["column"]))
        for du in (-1, 0, 1):
            n += bool(L.put(cv, mid + du, s + 4, pal["column"]))
        if L.has(cv, mid, s + 4):
            n += bool(L.put(cv, mid, s + 3, "bell", attachment="ceiling", facing="west",
                            powered="false"))
    return n


def _crown_cabin(L, pal, sv, su, vi0, ui0, vi1, ui1, s, accent) -> int:
    """FRONTIER: a timber watch cabin over half the deck, the other half open to the weather.

    Half and half on purpose - a cabin filling the deck is a room with windows, and the thing a
    lookout is for is standing outside in the wind."""
    n = 0
    v0, v1 = vi0, vi0 + 6
    u0, u1 = ui0, ui1
    for y in range(s, s + 4):
        for v in range(v0, v1 + 1):
            for u in range(u0, u1 + 1):
                if not (v in (v0, v1) or u in (u0, u1)):
                    continue
                if v == v1 and u in (u0 + 3, u0 + 4, u0 + 5) and y < s + 3:
                    continue                   # the cabin door, onto the open deck
                if y in (s + 1, s + 2) and (u % 3 == 1) and v == v0:
                    n += bool(L.put(v, u, y, pal["grille"], north="true", south="true",
                                    east="false", west="false", waterlogged="false"))
                    continue
                corner = v in (v0, v1) and u in (u0, u1)
                n += bool(L.put(v, u, y, pal["column"] if corner else pal["board"],
                                **({"axis": "y"} if corner and "log" in pal["column"] else {})))
    # A HIPPED ROOF, AND IT IS SOLID BEHIND ITS STAIRS. Two concentric rings a course apart touch
    # only DIAGONALLY, so a roof built as rings is an island with nothing to place it against -
    # which is exactly what the connectivity check reported: 179 cells of dark oak floating over
    # a cabin that audited clean. The stair edge is what is seen; the plate behind it is what
    # holds it on.
    for i, y in enumerate((s + 4, s + 5)):
        a0, a1 = v0 - 1 + i, v1 + 1 - i
        b0, b1 = u0 - 1 + i, u1 + 1 - i
        for v in range(a0, a1 + 1):
            for u in range(b0, b1 + 1):
                if v in (a0, a1) or u in (b0, b1):
                    f = ("east" if v == a0 else "west" if v == a1 else
                         "south" if u == b0 else "north")
                    n += bool(L.put(v, u, y, pal["roof"], facing=f, half="bottom",
                                    shape="straight", waterlogged="false"))
                else:
                    n += bool(L.put(v, u, y, pal["roof_field"]))
    for v in range(v0 + 1, v1):
        for u in range(u0 + 1, u1):
            n += bool(L.put(v, u, s + 6, pal["roof_slab"], type="bottom", waterlogged="false"))
    n += bool(L.lamp(vi0 + 3, (ui0 + ui1) // 2, s - 1, pal["glow"]))
    return n


def _crown_pavilion(L, pal, sv, su, vi0, ui0, vi1, ui1, s, accent) -> int:
    """MIDWAY: eight posts and a banded canopy, open on every side.

    The brightest land gets the lightest crown - a fairground awning, not a room. Its stripes run
    across the roof rather than round it, so the band reads from the ground rather than only from
    the deck."""
    n = 0
    posts = [(vi0, ui0), (vi0, (ui0 + ui1) // 2), (vi0, ui1),
             (vi1, ui0), (vi1, (ui0 + ui1) // 2), (vi1, ui1),
             ((vi0 + vi1) // 2, ui0), ((vi0 + vi1) // 2, ui1)]
    for (v, u) in posts:
        for y in range(s, s + 4):
            n += bool(L.put(v, u, y, pal["column"]))
    for v in range(vi0, vi1 + 1):
        for u in range(ui0, ui1 + 1):
            stripe = accent if ((u - ui0) // 2) % 2 == 0 else pal["board"]
            n += bool(L.put(v, u, s + 4, stripe))
    for u in range(ui0, ui1 + 1):
        n += bool(L.put(vi0 - 1, u, s + 4, pal["roof"], facing="east", half="bottom",
                        shape="straight", waterlogged="false"))
        n += bool(L.put(vi1 + 1, u, s + 4, pal["roof"], facing="west", half="bottom",
                        shape="straight", waterlogged="false"))
    for v in range(vi0, vi1 + 1):
        n += bool(L.put(v, ui0 - 1, s + 4, pal["roof"], facing="south", half="bottom",
                        shape="straight", waterlogged="false"))
        n += bool(L.put(v, ui1 + 1, s + 4, pal["roof"], facing="north", half="bottom",
                        shape="straight", waterlogged="false"))
    for (v, u) in posts[:6:2]:
        n += bool(L.lamp(v, u, s + 3, pal["glow"]))
    return n


def _crown_gallery(L, pal, sv, su, vi0, ui0, vi1, ui1, s, accent) -> int:
    """PRISMWORKS: no roof at all - four corner piers, a signal band, and open sky.

    **THE SUMMIT OF THE PARK IS THE ONE PLACE THAT SHOULD HAVE NOTHING OVER IT.** A canopy here
    would be sixty-five courses of climb to arrive under a ceiling. What marks it instead is four
    piers rising six courses past the parapet, banded with the land's own high signal and lit at
    the top, so the crown reads from the spine at night and the room reads as open from inside.

    The mast is `end_rod` - the finial vocabulary the Ascent beside it already uses - carried on
    the deck's own centre so the two read as one hand from the ground."""
    n = 0
    for (v, u) in ((0, 0), (0, su - 1), (sv - 1, 0), (sv - 1, su - 1)):
        for y in range(s, s + 6):
            n += bool(L.put(v, u, y, accent if (y - s) == 4 else pal["column"]))
        n += bool(L.put(v, u, s + 6, pal["slab"], type="bottom", waterlogged="false"))
        n += bool(L.lamp(v, u, s + 7, pal["glow"]))
    cv, cu = (vi0 + vi1) // 2, (ui0 + ui1) // 2
    n += bool(L.put(cv, cu, s, accent))
    for y in range(s + 1, s + 4):
        n += bool(L.put(cv, cu, y, pal["column"]))
    n += bool(L.lamp(cv, cu, s + 4, pal["glow"]))
    n += bool(L.put(cv, cu, s + 5, "end_rod", facing="up"))
    return n


# --------------------------------------------------------------------------- the bridge


def _bridge(L: _Lot, p: dict, pal: dict, sv: int, su: int) -> dict:
    """One cell of deck out of the shaft's east wall onto something already standing.

    IT LAYS ONLY IN ITS OWN LOT. The thing it reaches is the Prism Ascent's podium roof, whose
    own slab is the far half of the crossing - so this places a floor at the shaft's own storey
    course and a doorway through the wall, and nothing beyond the lot line.
    """
    b = p["bridge"]
    level, face = int(b["level"]), b.get("face", "east")
    if face != "east":
        raise ValueError("only an east bridge is implemented; the Summit's podium is east of it")
    y = level * int(p["rise"]) - 1              # the floor BLOCK; you walk at y + 1
    v0, v1 = int(b["v0"]), int(b["v1"])
    reach = int(b.get("reach", 1))
    n = 0
    for i in range(reach):
        u = su + i                              # beyond the shaft, inside the lot
        for v in range(v0, v1 + 1):
            n += bool(L.put(v, u, y, pal["thresh"]))
        for v in (v0, v1):
            n += bool(L.put(v, u, y + 1, pal["wall"], up="true", north="none", south="none",
                            east="none", west="none", waterlogged="false"))
    # the doorway through the shaft wall, two courses over the storey floor
    for v in range(v0 + 1, v1):
        for dy in (1, 2):
            L.clear(v, su - 1, y + dy)
    L.lamp(v0, su + reach - 1, y + 2, pal["crown_light"], hanging="false", waterlogged="false")
    return {"level": level, "floor_y": y, "walk_y": y + 1, "v": [v0, v1], "reach": reach,
            "cells": n}


# --------------------------------------------------------------------------- entry point


def build(cfg: dict, donors=None) -> Canvas:
    p = {**PARK_VANTAGE, **(cfg or {})}
    if p.get("kind") != "tower":
        raise ValueError(f"unknown vantage kind {p.get('kind')!r}; have 'tower'")
    for k in ("land", "at", "size"):
        if not p.get(k):
            raise ValueError(f"a vantage needs params.{k}")
    v, u = int(p["at"][0]), int(p["at"][1])
    dv, du = int(p["size"][0]), int(p["size"][1])
    sv, su = (int(p["shaft"][0]), int(p["shaft"][1])) if p.get("shaft") else (dv, du)
    if sv > dv or su > du:
        raise ValueError("a vantage's shaft must fit inside its lot")
    _refuse_reserves(v, u, dv, du)
    _check_loggia(p)
    pal = _pal(p["land"])
    rise, storeys = int(p["rise"]), int(p["storeys"])
    top = rise * storeys
    c = Canvas(dv, top + 12, du)
    L = _Lot(c, dv, du, int(p["seed"]))
    detail = _tower(L, p, pal, sv, su)
    if p.get("bridge"):
        detail["bridge"] = _bridge(L, p, pal, sv, su)

    c.world_origin = (ANCHOR[0] + v, ANCHOR[1], ANCHOR[2] + u)
    c.meta = {
        "kind": "park_vantage",
        "land": p["land"],
        "lot": [v, u, v + dv - 1, u + du - 1],
        "size": [dv, du], "shaft": [sv, su],
        "height": top + 12,
        "facing": p["look"],
        "look": p["look"],
        "deck_surface_above_lawn": top,
        "deck_world_y": ANCHOR[1] + top,
        "storeys": storeys, "rise": rise,
        "door": p["door"],
        "lights": L.lights,
        "outside_lot_refused": L.refused,
        **detail,
        "contract": (
            f"a climbable vantage: {storeys} flights of {rise} treads, a room at every storey, "
            f"and a deck whose walking surface is {top} courses over the lawn at world "
            f"Y{ANCHOR[1] + top} - reached on foot from the park's own ground and walkable back "
            f"down, inside V{v}-{v + dv - 1} / U{u}-{u + du - 1} and not one cell outside it"),
        "requires_in_game": [
            "colour and the read of the crown against the sky can only be judged in world",
            "no mechanism is claimed by this geometry: there is no lift, no gate and no circuit",
        ],
    }
    return c


def _refuse_reserves(v: int, u: int, dv: int, du: int) -> None:
    """The park's reserves, refused at the door rather than discovered in an audit."""
    if v + dv - 1 >= RIM_RESERVE[0]:
        raise ValueError(f"a vantage may not reach V{RIM_RESERVE[0]}-{RIM_RESERVE[1]}, "
                         f"the protected rim reserve; this lot ends at V{v + dv - 1}")
    for a, b in REACHES:
        if u <= b and u + du - 1 >= a:
            raise ValueError(f"a vantage may not stand in the reach U{a}-{b}; "
                             f"this lot is U{u}-{u + du - 1}")
