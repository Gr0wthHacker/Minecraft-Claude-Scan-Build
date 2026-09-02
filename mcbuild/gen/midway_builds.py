"""THE MIDWAY'S FOUR BUILDINGS: arrival, food, games, prizes - and nothing else.

`Park Ways` already draws the whole ground layer of this park - lawn, spine, avenues, the two
midway walks, the Circus, every spur to every door and every lamp on every verge - and `Park Rail`
draws the railway. The Sky Lift and the Carousel Court stand. **WHAT WAS MISSING WAS THE
BUILDINGS**, and the previous attempt's plazas, queue rails, ridegates, booths, arches, markers,
lampposts, flagpoles and benches were thrown away as chaos. So there is no street furniture in
this module at all: the ground layer owns the ground, and this owns the four buildings on it.

    PF Arrival Court    V24-69  U215-255   the park's front door - gate, ticket hall, court, turnstiles
    PF Snack Window     V77-103 U215-255   a counter under an awning, with a covered eating loggia
    PF Skill Arcade     V24-74  U346-378   one hall, three game bays, a spectator side
    PF Prize Point      V80-99  U346-378   an open-fronted kiosk where a game's result is redeemed

**EVERY CELL STAYS INSIDE ITS LOT AND THAT IS ENFORCED, NOT INTENDED.** The canvas IS the lot, so
anything past it is refused and COUNTED, and a non-zero count raises: a part cropped at placement
is a part that silently does not exist, and this park has already lost a 111-block ride to one lamp
two cells into the wrong column.

**AND THE LOT IS NOT EMPTY.** Measured off `out/Park Complete.litematic`, the ground layer's lamp
masts stand on the verges and their ARMS reach two cells into all four of these lots, three to five
courses above the lawn - twelve such cells in the Arrival Court, twelve in the Snack Window, ten in
the Skill Arcade, six in Prize Point. A wall drawn through one of those is an overlap no render can
show, because a lantern inside a wall draws exactly like a wall. Every envelope below is set in
from its lot edge far enough to clear them BY CONSTRUCTION; `blocked` is the belt to that pair of
braces; and `tests/test_midway_builds.py` reads the shipped ground layer and asserts that not one
design cell lands on a cell the world already owns.

WHAT MAKES THESE READ AS ARCHITECTURE IS REGULARITY AND OPENINGS, NOT DAMAGE - the void tower's
rule - and every elevation is built to one grammar, so the four read as one hand: a dark plinth, a
dressed field, pilasters on a rhythm, a string course, a band, a projecting cornice, and openings
whose lintel sits in the course ABOVE their jambs rather than on top of them.

    plinth      polished_blackstone_bricks   lum  45
    band        red_wool                     lum  65     the midway's own colour, off `parkways`
    field       stone_bricks                 lum 122
    pilaster    white_wool                   lum 236

**THE LADDER IS MEASURED ACROSS FAMILIES AND NEVER INSIDE ONE.** This repo has concluded four
separate times that its economy has no value contrast, and every one of those measurements was
taken inside a single material family, where a ladder cannot exist by construction - dressing a
stone does not change how much light it returns. 45 / 65 / 122 / 236 is four rungs at a minimum
step of 20, and all four are cheap tier. `cracked_stone_bricks` is dithered into the field for
TEXTURE only, hashed on the CELL: hashed on the course, a wall comes out as horizontal stripes,
which the deck soffit shipped once.

**A STAIR'S TALL SIDE IS ITS `facing`**, so every piece of trim here leans INTO the wall it grows
from and every roof course leans toward its own ridge. `render3d` draws a stair facing the wrong
way exactly as it draws one facing the right way, so this is asserted in the test file and can
never be eyeballed.

**AND A ROOF OF STAIRS IS NOT CONNECTED TO ITSELF.** Course k at (offset k, eave+k) and course k+1
at (offset k+1, eave+k+1) are diagonal neighbours, which is not 6-connectivity - the rule that once
broke a pair of ear tips off a cat. A gable roof is held together by its own solid tympanum; a hip
has no tympanum, so each of its courses carries a top slab one step in, under the stair above it.
That is why `components == 1` is a test and not a hope.
"""
from __future__ import annotations

from .canvas import Canvas, hash01

SIGN_WIDTH = 15                      # a sign line clips mid-word past this

#: The midway's masonry. Every entry is cheap tier except `smooth_stone`/`smooth_stone_slab`,
#: `glass_pane` and `iron_bars`, which are `ok` and are counters, sills, glazing and grilles - the
#: small parts. Every one is in the 1.19 server's registry, is neither currency nor a falling
#: block, and is checked in `tests/test_midway_builds.py` rather than remembered.
PAL = {
    "plinth":  "polished_blackstone_bricks",   # 45  - the dark base course
    "field":   "stone_bricks",                 # 122 - the wall
    "grain":   "cracked_stone_bricks",         # texture in the field, and no tone
    "course":  "chiseled_stone_bricks",        # the string course and every lintel
    "frame":   "white_wool",                   # 236 - pilasters, jambs, gables
    "band":    "red_wool",                     # 65  - the midway's accent
    "trim":    "stone_brick_stairs",
    "cap":     "stone_brick_slab",
    "rail":    "stone_brick_wall",
    "floor":   "stone",                        # 126 - a floor is read from ABOVE, so it carries
    "floor2":  "smooth_stone",                 # ok    its own tone, one rung off the field
    "inlay":   "polished_blackstone_bricks",
    "sill":    "smooth_stone_slab",            # ok
    "counter": "smooth_stone_slab",            # ok
    "glass":   "glass_pane",                   # ok
    "beam":    "stripped_oak_log",
    "board":   "oak_planks",
    "post":    "oak_fence",
    "shutter": "oak_trapdoor",
    "seat":    "oak_stairs",
    "shelf":   "oak_slab",
    "gate":    "oak_fence_gate",
    "light":   "lantern",
    "glow":    "ochre_froglight",              # the light that costs no metal
    "wood":    "oak",
}

MIDWAY_BUILD = {
    "kind": None,          # arrival_court | snack_window | skill_arcade | prize_point
    "lot": None,           # [v0, u0, v1, u1] in park V/U, inclusive - the canvas IS this
    "at": None,            # [x, y, z] world coords of (lot v0, first course above lawn, lot u0)
    #: [[v0, y0, u0, v1, y1, u1]] - cells the ground layer already owns (its lamp arms). A design
    #: must not want one; this refuses it and counts, so wanting one raises here instead of
    #: shipping as an overlap nobody can see.
    "blocked": (),
    "height": 24,          # the canvas ceiling, in courses above the lawn
    "seed": 0,
}

_DIRS = {(1, 0): "east", (-1, 0): "west", (0, 1): "south", (0, -1): "north"}


def _dir(nv: int, nu: int) -> str:
    """A compass word from a (dV, dU) step. Canvas x is V (+x east) and z is U (+z south)."""
    return _DIRS[(int(nv), int(nu))]


def _opp(nv: int, nu: int) -> str:
    return _DIRS[(-int(nv), -int(nu))]


# ---------------------------------------------------------------------------- the lot


class _Lot:
    """The lot, as a drawing surface. Everything is placed through it, so an axis bug is one bug.

    Coordinates are the park's own V/U rather than canvas indices: every measurement in the plan,
    every obstacle read off the shipped ground layer and every lot boundary is quoted in V/U, and a
    generator that converts at each call site converts one of them wrong.
    """

    def __init__(self, c: Canvas, lot, blocked=()):
        self.c = c
        self.v0, self.u0, self.v1, self.u1 = (int(q) for q in lot)
        self.sx, self.sy, self.sz = c.sx, c.sy, c.sz
        self.refused = 0                    # a cell outside the lot: must stay ZERO
        self.blocked_hits = 0               # a cell the world owns: must stay ZERO
        self._blocked = set()
        for bv0, by0, bu0, bv1, by1, bu1 in (blocked or ()):
            for v in range(int(bv0), int(bv1) + 1):
                for y in range(int(by0), int(by1) + 1):
                    for u in range(int(bu0), int(bu1) + 1):
                        self._blocked.add((v, y, u))
        self._state: dict = {}

    def blk(self, name: str) -> int:
        if name not in self._state:
            self._state[name] = self.c.state(name)
        return self._state[name]

    def put(self, v: int, y: int, u: int, name: str, **props) -> bool:
        v, y, u = int(v), int(y), int(u)
        if (v, y, u) in self._blocked:
            self.blocked_hits += 1
            return False
        x, z = v - self.v0, u - self.u0
        if not (0 <= x < self.sx and 0 <= z < self.sz and 0 <= y < self.sy):
            self.refused += 1
            return False
        self.c.ids[y, z, x] = self.c.raw_state(name, **props) if props else self.blk(name)
        return True

    def has(self, v: int, y: int, u: int) -> bool:
        return self.c.solid(int(v) - self.v0, int(y), int(u) - self.u0)

    def name_at(self, v: int, y: int, u: int) -> str:
        return self.c.get_name(int(v) - self.v0, int(y), int(u) - self.u0)

    def sign(self, v, y, u, nv, nu, lines) -> bool:
        """A wall sign in the cell IN FRONT of its wall, its text facing away from its support.

        THE SUPPORT IS CHECKED, NOT ASSUMED. Four of an earlier park's seven building kinds shipped
        a sign hung on the one column that has an opening in it, and the mistake is invisible in
        every render: a wall sign floating in air draws exactly like one on a wall.
        """
        if not self.has(v - nv, y, u - nu):
            return False
        if not self.put(v, y, u, f"{PAL['wood']}_wall_sign", facing=_dir(nv, nu),
                        waterlogged="false"):
            return False
        text = [str(t)[:SIGN_WIDTH] for t in list(lines)[:4]]
        self.c.sign_text(v - self.v0, y, u - self.u0, front=text, colour="white", glowing=True)
        return True


# ---------------------------------------------------------------------------- the kit


def _line(v0, u0, v1, u1):
    """The cells of a straight run, inclusive, in order."""
    if v0 == v1:
        return [(v0, u) for u in range(min(u0, u1), max(u0, u1) + 1)]
    return [(v, u0) for v in range(min(v0, v1), max(v0, v1) + 1)]


def _field(seed, v, y, u):
    """The wall's own material, dithered per CELL. Hashed on the COURSE a wall comes out striped."""
    return PAL["grain"] if hash01(v, y, u, seed + 91) < 0.10 else PAL["field"]


def _pave(L, v0, u0, v1, u1, y, seed, *, border=True):
    """A floor is read from ABOVE, so it carries its own pattern rather than the wall's tone.

    A field of one block over a thousand cells is a slab and not a floor - the casino hall's own
    finding. This is a dressed border, a light grid every eight, and a two-tone ground between,
    all set in WORLD coordinates so the pattern stays aligned from room to room of one building.
    """
    n = 0
    for v in range(v0, v1 + 1):
        for u in range(u0, u1 + 1):
            if border and (v in (v0, v1) or u in (u0, u1)):
                mat = PAL["inlay"]
            elif v % 8 == 0 or u % 8 == 0:
                mat = PAL["floor2"]
            elif (v + u) % 2 == 0:
                mat = PAL["floor"]
            else:
                mat = PAL["floor2"] if hash01(v, u, seed) < 0.16 else PAL["floor"]
            n += bool(L.put(v, y, u, mat))
    return n


def _wall(L, cells, y0, top, nv, nu, seed, *, pilaster=0, band=None, course=None,
          skirt=True, cornice=True, opens=None, pil_offset=0, cap=True):
    """One straight wall run, in the grammar every elevation in this module is built to.

    `cells` is the run's footprint in order and `(nv, nu)` is its OUTWARD normal, which decides
    which way every piece of trim leans. `opens(v, u, y)` leaves a cell EMPTY as the loop runs,
    rather than letting the loop fill it and something else cut it back out afterwards: the void
    tower shipped a plain drum for exactly that reason and nothing about the code looked wrong.
    """
    made = {"field": 0, "pilaster": 0, "trim": 0}
    into = _opp(nv, nu)
    for i, (v, u) in enumerate(cells):
        pil = bool(pilaster) and (i + pil_offset) % pilaster == 0
        for y in range(y0, top + 1):
            if opens and opens(v, u, y):
                continue
            if y == y0:
                mat = PAL["plinth"]
            elif pil:
                mat = PAL["frame"]
            elif band is not None and y == band:
                mat = PAL["band"]
            elif course is not None and y == course:
                mat = PAL["course"]
            else:
                mat = _field(seed, v, y, u)
            if L.put(v, y, u, mat):
                made["pilaster" if pil and y > y0 else "field"] += 1
        # The skirt and the cornice both PROJECT one cell and lean INTO the wall they grow from,
        # which is why every envelope in this module sits at least one cell inside its own lot.
        if skirt and L.put(v + nv, y0, u + nu, PAL["trim"], facing=into, half="bottom",
                           shape="straight", waterlogged="false"):
            made["trim"] += 1
        if cornice and L.put(v + nv, top, u + nu, PAL["trim"], facing=into, half="top",
                             shape="straight", waterlogged="false"):
            made["trim"] += 1
        if cap and L.put(v, top + 1, u, PAL["cap"], type="bottom", waterlogged="false"):
            made["trim"] += 1
    return made


def _opening(L, v, u, nv, nu, y0, y1, half_w, seed, *, glazed=True, sill=True, arch=True):
    """A real opening: dressed jambs, and a lintel in the course ABOVE their tops.

    An opening whose lintel sits ON its jambs is a hole with a beam over it. The lintel belongs
    BETWEEN the jamb tops - one course higher, spanning the gap - which is what makes a voxel wall
    read as built rather than as punched.
    """
    tv, tu = (0, 1) if nv else (1, 0)              # the direction along the wall
    lo, hi = -half_w, half_w
    made = 0
    for k in (lo - 1, hi + 1):                     # the jambs
        for y in range(y0, y1 + 1):
            made += bool(L.put(v + tv * k, y, u + tu * k, PAL["frame"]))
    for k in range(lo, hi + 1):                    # ...and the lintel over the gap between them
        made += bool(L.put(v + tv * k, y1 + 1, u + tu * k, PAL["course"]))
    if arch:                                       # carried on a pair of stairs at the springing
        for k, s in ((lo, 1), (hi, -1)):
            made += bool(L.put(v + tv * k, y1, u + tu * k, PAL["trim"],
                               facing=_dir(tv * s, tu * s), half="top", shape="straight",
                               waterlogged="false"))
    if sill:
        for k in range(lo, hi + 1):
            made += bool(L.put(v + tv * k, y0 - 1, u + tu * k, PAL["sill"], type="top",
                               waterlogged="false"))
    if glazed:
        for k in range(lo, hi + 1):
            for y in range(y0, y1 + (0 if arch else 1)):
                made += bool(L.put(v + tv * k, y, u + tu * k, PAL["glass"],
                                   **_pane(bool(tv), bool(tu))))
    return made


def _pane(along_v: bool, along_u: bool) -> dict:
    """A pane's connections run ALONG its wall. Every side false and it renders as a lone post."""
    return {"north": str(along_u).lower(), "south": str(along_u).lower(),
            "east": str(along_v).lower(), "west": str(along_v).lower(), "waterlogged": "false"}


def _gable(L, v0, u0, v1, u1, eave, seed, *, axis, pitch=1, tympanum=True):
    """A gabled roof. `axis` names the direction the RIDGE runs: 'v' or 'u'.

    Every roof course leans toward its own ridge, which is the same rule as a flight ascending
    toward its landing. The solid tympanum under each gable end is what holds the whole roof
    together as one 6-connected piece: a stair at (k, eave+k) and one at (k+1, eave+k+1) touch
    each other only at a corner, which is not a connection.

    **THE PITCH IS A PARAMETER BECAUSE A 1:1 ROOF ON A WIDE BUILDING IS A SPIRE.** The Skill
    Arcade is 27 across, so a one-course-per-cell slope puts its ridge THIRTEEN courses over its
    eaves - taller than the building under it, and past this park's own landmark rule, which
    reserves the crown bands for the Sky Lift and two rides in other lands. At `pitch=2` a course
    covers two cells - a bottom slab and then a stair, which is the classic 1:2 voxel slope - and
    the same hall roofs at six.
    """
    made = {"roof": 0, "tympanum": 0}
    if axis == "v":
        span, lo, hi = u1 - u0, u0, u1
    else:
        span, lo, hi = v1 - v0, v0, v1
    half = span // 2
    for j in range(half + 1):
        k, y = j // pitch, eave + j // pitch
        step = (j % pitch == pitch - 1)
        for s, edge in ((1, lo), (-1, hi)):
            w = edge + s * j
            if s * (w - (lo + half)) > 0:
                continue
            for (v, u) in (_line(v0, w, v1, w) if axis == "v" else _line(w, u0, w, u1)):
                if j == half or not step:
                    made["roof"] += bool(L.put(v, y, u, PAL["cap"], type="bottom",
                                               waterlogged="false"))
                else:
                    face = _dir(0, s) if axis == "v" else _dir(s, 0)
                    made["roof"] += bool(L.put(v, y, u, PAL["trim"], facing=face, half="bottom",
                                               shape="straight", waterlogged="false"))
        if tympanum:
            for e in ((v0, v1) if axis == "v" else (u0, u1)):
                for s, edge in ((1, lo), (-1, hi)):
                    w = edge + s * j
                    if s * (w - (lo + half)) > 0:
                        continue
                    v, u = (e, w) if axis == "v" else (w, e)
                    for yy in range(eave, y):
                        made["tympanum"] += bool(L.put(v, yy, u, _field(seed, v, yy, u)))
    return made


def _hip(L, v0, u0, v1, u1, eave, seed):
    """A hipped or pyramidal roof: concentric rings of stairs, each carrying the ring above it.

    THE UNDER-SLAB IS STRUCTURAL AND NOT DECORATION. Without it every ring touches the next only
    at a corner and the roof ships as one component per course - the ear-tip failure, on a roof.
    """
    made = 0
    k = 0
    while True:
        a0, a1, b0, b1 = v0 + k, v1 - k, u0 + k, u1 - k
        if a0 > a1 or b0 > b1:
            break
        y = eave + k
        last = (a0 >= a1 - 1) or (b0 >= b1 - 1)
        for v in range(a0, a1 + 1):
            for u in range(b0, b1 + 1):
                if not (v in (a0, a1) or u in (b0, b1)):
                    continue
                if last:
                    made += bool(L.put(v, y, u, PAL["cap"], type="bottom", waterlogged="false"))
                else:
                    # A ROOF COURSE LEANS TOWARD ITS OWN APEX, and the apex of a hip is inboard of
                    # every edge - so the ring's west side faces EAST. Written the obvious way
                    # round, all four slopes lean off the building and our renderer draws them
                    # exactly as it draws the right ones.
                    face = ("east" if v == a0 else "west" if v == a1
                            else "south" if u == b0 else "north")
                    made += bool(L.put(v, y, u, PAL["trim"], facing=face, half="bottom",
                                       shape="straight", waterlogged="false"))
                if k:
                    made += bool(L.put(v, y - 1, u, PAL["cap"], type="top", waterlogged="false"))
        if last:
            for v in range(a0, a1 + 1):
                for u in range(b0, b1 + 1):
                    made += bool(L.put(v, y, u, PAL["cap"], type="bottom", waterlogged="false"))
            break
        k += 1
    return made


def _ceiling(L, v0, u0, v1, u1, y, seed):
    """A flat ceiling, coffered on a 4-grid, so a room has a fifth surface worth looking at."""
    n = 0
    for v in range(v0, v1 + 1):
        for u in range(u0, u1 + 1):
            if v % 4 == 0:
                n += bool(L.put(v, y, u, PAL["beam"], axis="x"))
            elif u % 4 == 0:
                n += bool(L.put(v, y, u, PAL["beam"], axis="z"))
            else:
                n += bool(L.put(v, y, u, PAL["board"]))
    return n


def _can_hang(name: str) -> bool:
    """Whether a lantern may hang under this block. `LanternBlock` overrides `canSurvive` and asks
    `canSupportCenter` of the block ABOVE - so a slab, a stair, a fence, a wall or a chain all
    qualify and a TRAPDOOR, a pane and a set of iron bars do not. Asked, not assumed: the first
    build hung four lanterns off the valance over the box office and the audit named all four."""
    from .. import blocks as _b
    return (name.endswith(("_fence", "_wall", "_chain")) or name in ("chain", "end_rod")
            or _b.supports_top(name))


def _lamp(L, v, y, u) -> bool:
    """A lantern hung from whatever is directly over it - if that block can actually hold one."""
    if not L.has(v, y + 1, u) or not _can_hang(L.name_at(v, y + 1, u)):
        return False
    return L.put(v, y, u, PAL["light"], hanging="true", waterlogged="false")


def _valance(L, v, y, u, nv, nu) -> bool:
    """The scalloped edge under an awning or a fascia: a top-half trapdoor, hung off the block
    above it. Trapdoors are the family this repo places least and outside builders place most."""
    return L.put(v, y, u, PAL["shutter"], facing=_dir(nv, nu), half="top", open="false",
                 powered="false", waterlogged="false")


def _awning(L, v, u0, u1, y) -> int:
    """A striped awning - the one thing on a midway that is red and white by right."""
    n = 0
    for u in range(u0, u1 + 1):
        n += bool(L.put(v, y, u, PAL["band"] if (u // 2) % 2 else PAL["frame"]))
    return n


def _counter_front(L, v0, mid, serve, seed, title_left, title_right, m):
    """The shared ordering frontage: counter, shutter head, striped awning on two posts, valance,
    a name either side of it and a lantern over each. The Snack Window and Prize Point are the
    same kind of thing at the same scale and there is no reason for two of this."""
    for u in range(mid - serve, mid + serve + 1):
        L.put(v0, 1, u, PAL["counter"], type="top", waterlogged="false")
        L.put(v0, 4, u, PAL["course"])
    for u in (mid - serve - 1, mid + serve + 1):
        for y in range(1, 5):
            L.put(v0, y, u, PAL["frame"])
        for y in range(1, 5):
            L.put(v0 - 1, y, u, PAL["post"], north="false", south="false", east="true",
                  west="false", waterlogged="false")
    # THE AWNING REACHES THE LAMPS. Stopped at the posts it left the two lanterns beyond it with
    # nothing over them, `_lamp` refused both, and the frontage shipped unlit in silence - which
    # is the "a thing that does nothing, quietly" failure this repo keeps writing rules about.
    m["awning"] = _awning(L, v0 - 1, mid - serve - 2, mid + serve + 2, 5)
    for u in range(mid - serve, mid + serve + 1):
        _valance(L, v0 - 1, 4, u, -1, 0)
    m["signs"] += bool(L.sign(v0 - 1, 3, mid - serve - 2, -1, 0, title_left))
    m["signs"] += bool(L.sign(v0 - 1, 3, mid + serve + 2, -1, 0, title_right))
    m["lamps"] += bool(_lamp(L, v0 - 1, 4, mid - serve - 2))
    m["lamps"] += bool(_lamp(L, v0 - 1, 4, mid + serve + 2))


def _service_door(L, v1, mid, seed, m, sign_y=4):
    """The rear door every build card asks for: an opening with a real door in it, and a sign."""
    m["openings"] += _opening(L, v1, mid, 1, 0, 1, 3, 1, seed, glazed=False, sill=False)
    L.put(v1, 1, mid, "oak_door", facing="south", half="lower", hinge="left", open="false",
          powered="false")
    L.put(v1, 2, mid, "oak_door", facing="south", half="upper", hinge="left", open="false",
          powered="false")
    m["signs"] += bool(L.sign(v1 + 1, sign_y, mid, 1, 0, ["STAFF ONLY", "", "SERVICE", "ACCESS"]))


# ---------------------------------------------------------------------------- the buildings


def _arrival_court(L, p) -> dict:
    """THE PARK'S FRONT DOOR: gate, ticket hall, open court, turnstile screen - in that order.

    `PARK_MIDWAY.md` asks this lot for one west-edge sequence - arrival, rules and map, box office,
    covered queue, turnstiles, then a post-gate welcome threshold - and asks that its centre stay
    visually open with no vendor clutter in it. So the built mass is a RING: a deep front range
    against the spine, two long flanking arcades, a rear loggia carrying the turnstiles, and 23 by
    27 of open paved court in the middle of it. Two fifths of the footprint is roofless, which is
    what stops 44 by 35 of building reading as a block.
    """
    seed = int(p["seed"])
    v0, u0, v1, u1 = 25, 218, 68, 252              # the envelope; trim projects one cell outside it
    mid = (u0 + u1) // 2                           # U235 - the spine spur's own column
    hall_v1, court_v1 = 33, 60                     # front range | court | rear loggia
    arc_w = 5                                      # the flanking arcades' inside depth
    top = 11                                       # the front range's wall head
    m = {"signs": 0, "lamps": 0, "gates": 0, "openings": 0, "roof": 0}

    # -- 1. the floors ------------------------------------------------------------------------
    m["floor"] = _pave(L, v0, u0, v1, u1, 0, seed)
    for v in range(v0, v1 + 1):                    # the axis a visitor walks, gate to turnstiles
        for u in range(mid - 2, mid + 3):
            L.put(v, 0, u, PAL["band"] if abs(u - mid) == 2 else PAL["floor2"])

    # -- 2. the west front: a screen wall, a monumental gateway, two corner pavilions -----------
    gate_h, gate_w = 6, 3

    def front_open(v, u, y):
        return abs(u - mid) <= gate_w and 1 <= y <= gate_h

    _wall(L, _line(v0, u0, v0, u1), 0, top, -1, 0, seed, pilaster=6, band=7, course=4,
          opens=front_open)
    m["openings"] += _opening(L, v0, mid, -1, 0, 1, gate_h, gate_w, seed, glazed=False, sill=False)
    for du in (-9, 9):                             # a window either side of the gateway
        m["openings"] += _opening(L, v0, mid + du, -1, 0, 3, 5, 1, seed)
    m["signs"] += bool(L.sign(v0 - 1, gate_h + 3, mid - 1, -1, 0,
                              ["", "THE MIDWAY", "PARK ENTRANCE", ""]))
    m["signs"] += bool(L.sign(v0 - 1, gate_h + 3, mid + 1, -1, 0,
                              ["", "FREE TO ENTER", "ALL LANDS", ""]))

    # -- 3. the ticket hall behind it -----------------------------------------------------------
    for u, n in ((u0, -1), (u1, 1)):
        _wall(L, _line(v0 + 1, u, hall_v1, u), 0, top, 0, n, seed, pilaster=6, band=7, course=4)
    _wall(L, _line(hall_v1, u0, hall_v1, u1), 0, top, 1, 0, seed, pilaster=6, band=7, course=4,
          opens=front_open)
    m["openings"] += _opening(L, hall_v1, mid, 1, 0, 1, gate_h, gate_w, seed, glazed=False,
                              sill=False)
    m["ceiling"] = _ceiling(L, v0 + 1, u0 + 1, hall_v1 - 1, u1 - 1, top, seed)
    m["roof"] += _gable(L, v0, u0, hall_v1, u1, top + 2, seed, axis="u")["roof"]
    for u in range(u0 + 4, u1 - 3, 6):
        m["lamps"] += bool(_lamp(L, v0 + 3, top - 1, u))
        m["lamps"] += bool(_lamp(L, hall_v1 - 3, top - 1, u))

    # -- 3b. the frontispiece over the gateway, and the two end piers ---------------------------
    # BOTH ARE BUILT AFTER THE ROOF, and that order is the whole of it: each exists to BREAK the
    # eave line, and a roof laid afterwards would put its own eave course straight back through
    # them. An earlier version raised two corner PAVILIONS here instead, and their hipped caps
    # stood over the three cells of each corner that have no wall under them at all - twenty-two
    # cells of roof in mid-air, reported as a second component and invisible in any render.
    fw = 5
    for u in range(mid - fw, mid + fw + 1):
        for y in range(top + 1, top + 5):
            L.put(v0, y, u, PAL["frame"] if abs(u - mid) == fw
                  else (PAL["band"] if y == top + 2 else _field(seed, v0, y, u)))
    for k in range(fw + 1):                        # the pediment: a raking cornice, and its field
        y = top + 5 + k
        for s in (1, -1):
            if k == fw:
                L.put(v0, y, mid, PAL["cap"], type="bottom", waterlogged="false")
            else:
                L.put(v0, y, mid + s * (fw - k), PAL["trim"], facing=_dir(0, -s), half="bottom",
                      shape="straight", waterlogged="false")
        for u in range(mid - fw + k + 1, mid + fw - k):
            L.put(v0, y, u, _field(seed, v0, y, u))
    for outer, a, b in ((u0, u0, u0 + 2), (u1, u1 - 2, u1)):
        for (v, u) in _line(v0, a, v0, b) + _line(v0 + 1, outer, v0 + 2, outer):
            for y in range(top + 1, top + 4):
                L.put(v, y, u, PAL["frame"] if y == top + 3 else _field(seed, v, y, u))
            L.put(v, top + 4, u, PAL["cap"], type="bottom", waterlogged="false")

    # THE BOX OFFICE and GUEST SERVICES: two counters flanking the gateway, inside the hall, so
    # the whole ticketing sequence is in one place instead of scattered round the land.
    for side, lines in ((-1, ["BOX OFFICE", "", "TICKETS FREE", "ASK HERE"]),
                        (1, ["GUEST SERVICES", "", "LOST PROPERTY", "FIRST AID"])):
        cu = mid + side * 8
        for u in range(cu - 3, cu + 4):
            L.put(v0 + 5, 0, u, PAL["plinth"])
            L.put(v0 + 5, 1, u, PAL["counter"], type="top", waterlogged="false")
            L.put(v0 + 6, 2, u, PAL["board"])
            L.put(v0 + 6, 3, u, PAL["frame"])
            L.put(v0 + 6, 4, u, PAL["board"])
            _valance(L, v0 + 4, 4, u, -1, 0)
        for u in (cu - 4, cu + 4):
            for y in range(0, 5):
                L.put(v0 + 5, y, u, PAL["beam"], axis="y")
                L.put(v0 + 6, y, u, PAL["beam"], axis="y")
        for u in range(cu - 3, cu + 4):
            L.put(v0 + 5, 4, u, PAL["beam"], axis="z")
        L.put(v0 + 6, 1, cu - 2, "barrel", facing="west", open="false")
        L.put(v0 + 6, 1, cu + 2, "barrel", facing="west", open="false")
        m["signs"] += bool(L.sign(v0 + 4, 3, cu, -1, 0, lines))
        m["lamps"] += bool(_lamp(L, v0 + 5, 3, cu - 3))
        m["lamps"] += bool(_lamp(L, v0 + 5, 3, cu + 3))
    # THE MAP AND THE RULES GO ON THE HALL'S FLANKS, NOT ACROSS ITS BACK WALL. The first version
    # hung the map panel one cell in front of the inner gateway - which is an opening, so the
    # panel stood in the doorway with nothing behind it and shipped as a 22-cell second component
    # blocking the one route through the building. A board belongs on the wall that HAS no door.
    for u, n, lines in ((u0 + 1, 1, ["PARK MAP", "FRONTIER WEST", "MIDWAY HERE", "HOLLOW EAST"]),
                        (u1 - 1, -1, ["PARK RULES", "FREE TO ENTER", "MIND THE RIDES", "NO CLIMBING"])):
        for v in range(v0 + 2, v0 + 7):
            for y in range(2, 5):
                L.put(v, y, u, PAL["frame"] if (y == 4 or v in (v0 + 2, v0 + 6)) else PAL["band"])
        m["signs"] += bool(L.sign(v0 + 4, 3, u + n, 0, n, lines))

    # -- 4. the court: two arcades, and 23 by 27 of open sky between them -----------------------
    for u, n in ((u0, -1), (u1, 1)):
        _wall(L, _line(hall_v1 + 1, u, court_v1, u), 0, 8, 0, n, seed, pilaster=5, band=6,
              course=3, opens=lambda v, uu, y: (v % 5 == 3 and 3 <= y <= 5))
        for v in range(hall_v1 + 1, court_v1 + 1):
            if v % 5 == 3:
                m["openings"] += _opening(L, v, u, 0, n, 3, 5, 0, seed)
        inner = u - n * arc_w                      # the colonnade facing the court, INBOARD of
        #                                            the outer wall: `n` is the OUTWARD normal, so
        #                                            a colonnade at `u + n * arc_w` is five cells
        #                                            off the lot and every cell of it is refused.
        for v in range(hall_v1 + 1, court_v1 + 1):
            if v % 4 == 1:
                for y in range(0, 5):
                    L.put(v, y, inner, PAL["frame"] if y == 4 else PAL["field"])
                L.put(v, 5, inner, PAL["course"])
            else:
                L.put(v, 5, inner, PAL["cap"], type="bottom", waterlogged="false")
                L.put(v, 4, inner, PAL["rail"], up="true", waterlogged="false",
                      north="low" if v > hall_v1 + 1 else "none",
                      south="low" if v < court_v1 else "none", east="none", west="none")
            for k in range(arc_w + 1):             # the lean-to, rising toward the outer wall
                # ...and therefore leaning toward it: the outer wall is the high side, so the
                # tall half of every tread points OUTWARD, which is `n` and not `-n`.
                L.put(v, 6 + k // 3, u - n * (arc_w - k), PAL["trim"],
                      facing=_dir(0, n), half="bottom", shape="straight", waterlogged="false")
                L.put(v, 5 + k // 3, u - n * (arc_w - k), PAL["board"])
        for v in range(hall_v1 + 3, court_v1, 6):
            m["lamps"] += bool(_lamp(L, v, 4, inner + n))
    for v in range(hall_v1 + 4, court_v1, 6):      # the court's own light, and nothing else in it
        for u in (mid - 8, mid + 8):
            L.put(v, 0, u, PAL["glow"])

    # -- 5. the rear loggia, and the turnstile screen -------------------------------------------
    def screen_open(v, u, y):
        return (u - mid) % 4 == 0 and abs(u - mid) <= 8 and 1 <= y <= 3

    for u, n in ((u0, -1), (u1, 1)):
        _wall(L, _line(court_v1 + 1, u, v1, u), 0, 9, 0, n, seed, pilaster=5, band=6, course=3)
    _wall(L, _line(v1, u0, v1, u1), 0, 9, 1, 0, seed, pilaster=5, band=6, course=3,
          opens=screen_open)
    for k in (-8, -4, 0, 4, 8):
        m["openings"] += _opening(L, v1, mid + k, 1, 0, 1, 3, 0, seed, glazed=False, sill=False)
        if L.put(v1, 1, mid + k, PAL["gate"], facing="south", in_wall="false", open="false",
                 powered="false"):
            m["gates"] += 1
    _wall(L, _line(court_v1 + 1, u0, court_v1 + 1, u1), 0, 9, -1, 0, seed, pilaster=5, band=6,
          course=3, opens=lambda v, u, y: abs(u - mid) <= 10 and 1 <= y <= 6)
    m["openings"] += _opening(L, court_v1 + 1, mid, -1, 0, 1, 6, 10, seed, glazed=False,
                              sill=False)
    m["ceiling"] += _ceiling(L, court_v1 + 2, u0 + 1, v1 - 1, u1 - 1, 9, seed)
    m["roof"] += _gable(L, court_v1 + 1, u0, v1, u1, 11, seed, axis="u")["roof"]
    for u in range(u0 + 4, u1 - 3, 7):
        m["lamps"] += bool(_lamp(L, v1 - 3, 7, u))
    m["signs"] += bool(L.sign(v1 + 1, 5, mid, 1, 0,
                              ["TURNSTILES", "", "TO THE MIDWAY", "AND ALL RIDES"]))
    m["signs"] += bool(L.sign(court_v1, 5, mid - 3, -1, 0, ["KEEP LEFT", "TO EXIT", "", ""]))
    return m


def _snack_window(L, p) -> dict:
    """A COUNTER UNDER AN AWNING, and a covered loggia behind it with six seats and no more.

    The build card is explicit that this is the small one - "build last; max 6 seats" - and the
    land's own spec calls the food court a recovery node with an ordering frontage and seating
    BEHIND it, not a second attraction. So the mass is low: eaves at six courses, a ridge at nine,
    and the tallest thing on the lot is its own chimney.
    """
    seed = int(p["seed"])
    v0, u0, v1, u1 = 80, 224, 96, 246
    mid = (u0 + u1) // 2                           # U235 - midway walk 1's own spur column
    top = 6
    m = {"signs": 0, "lamps": 0, "seats": 0, "openings": 0, "floor": 0}

    for v in (77, 78, 79):                         # the threshold: the spur's paving to the counter
        for u in range(mid - 6, mid + 7):
            m["floor"] += bool(L.put(v, 0, u, PAL["inlay"] if v == 77 else PAL["floor2"]))
    m["floor"] += _pave(L, v0, u0, v1, u1, 0, seed)

    serve = 4

    def front_open(v, u, y):
        return abs(u - mid) <= serve and 1 <= y <= 3

    _wall(L, _line(v0, u0, v0, u1), 0, top, -1, 0, seed, pilaster=4, band=4, course=2,
          opens=front_open)
    _counter_front(L, v0, mid, serve, seed,
                   ["SNACK WINDOW", "", "HOT FOOD", "AND DRINK"],
                   ["SNACK WINDOW", "", "SEATING", "BEHIND"], m)
    m["openings"] += 1
    for du in (-8, 8):
        m["openings"] += _opening(L, v0, mid + du, -1, 0, 3, 4, 1, seed)

    for u, n in ((u0, -1), (u1, 1)):
        _wall(L, _line(v0 + 1, u, v1, u), 0, top, 0, n, seed, pilaster=4, band=4, course=2,
              opens=lambda v, uu, y: v in (v0 + 5, v0 + 11) and 3 <= y <= 4)
        for v in (v0 + 5, v0 + 11):
            m["openings"] += _opening(L, v, u, 0, n, 3, 4, 0, seed)
    _wall(L, _line(v1, u0, v1, u1), 0, top, 1, 0, seed, pilaster=4, band=4, course=2,
          opens=lambda v, u, y: abs(u - mid) <= 1 and 1 <= y <= 3)
    _service_door(L, v1, mid, seed, m)
    m["ceiling"] = _ceiling(L, v0 + 1, u0 + 1, v1 - 1, u1 - 1, top, seed)
    m["roof"] = _gable(L, v0, u0, v1, u1, top + 2, seed, axis="u")["roof"]

    # -- the kitchen, its chimney, and the loggia that six people eat in ------------------------
    for u in range(mid - 3, mid + 4):
        L.put(v0 + 2, 1, u, "smoker", facing="west", lit="false")
    for u in (mid - 5, mid + 5):
        for y in (1, 2):
            L.put(v0 + 2, y, u, "barrel", facing="up", open="false")
    L.put(v0 + 2, 1, mid - 4, "composter", level="0")
    L.put(v0 + 2, 1, mid + 4, "cauldron")
    for k in range(4):                             # the chimney, and the one plume of smoke here
        L.put(v0 + 2, top + 1 + k, mid, PAL["field"])
        for du in (-1, 1):
            if k < 2:
                L.put(v0 + 2, top + 1 + k, mid + du, PAL["plinth"])
    L.put(v0 + 2, top + 5, mid, PAL["cap"], type="bottom", waterlogged="false")
    L.put(v0 + 2, top + 6, mid, "campfire", facing="north", lit="true", signal_fire="false",
          waterlogged="false")

    for u in range(mid - 7, mid + 8):              # the eating shelf, and its own timber posts
        L.put(v0 + 11, 1, u, PAL["shelf"], type="bottom", waterlogged="false")
        L.put(v0 + 11, 0, u, PAL["beam"], axis="y")
    for u in range(mid - 7, mid + 9, 3):           # six seats, facing it, and no more
        if m["seats"] >= 6:
            break
        L.put(v0 + 9, 1, u, PAL["seat"], facing="south", half="bottom", shape="straight",
              waterlogged="false")
        m["seats"] += 1
    for u in range(mid - 6, mid + 7, 4):
        m["lamps"] += bool(_lamp(L, v0 + 10, top - 1, u))
    for u in (mid - 7, mid + 7):
        L.put(v0 + 9, 0, u, PAL["glow"])
    return m


def _skill_arcade(L, p) -> dict:
    """ONE HALL, THREE BAYS, AND A SIDE TO WATCH FROM. Not three sheds on a lawn.

    The build card allows exactly three bays and demands of each a stated player action, one
    visible result, a bounded reset, a service hatch and a spectator edge. Three separate booths
    would have been three of everything with a plaza between them, which is the arrangement Jack
    threw away; one hall gives the three a shared roof, a shared aisle to queue in, and a single
    frontage on the spine that says what the building is from the far side of it.
    """
    seed = int(p["seed"])
    v0, u0, v1, u1 = 25, 349, 70, 375
    mid = (u0 + u1) // 2                           # U362 - the spine spur's own column
    top = 11
    bays = [(v0 + 8, ["HIGH STRIKER", "SWING THE MAUL", "RING THE BELL", "ONE GO EACH"]),
            (v0 + 19, ["TARGET WALL", "HIT THE TARGET", "LAMPS SHOW HITS", "ONE GO EACH"]),
            (v0 + 30, ["RING TOSS", "LAND THE RING", "THREE ATTEMPTS", "ONE GO EACH"])]
    m = {"signs": 0, "lamps": 0, "bays": 0, "openings": 0}

    m["floor"] = _pave(L, v0, u0, v1, u1, 0, seed)
    for v in range(v0, v1 + 1):                    # the aisle, running the length of the hall
        for u in range(mid - 3, mid + 4):
            L.put(v, 0, u, PAL["band"] if abs(u - mid) == 3 else PAL["floor2"])

    # -- 1. the west gable front ----------------------------------------------------------------
    door = 3

    def front_open(v, u, y):
        return abs(u - mid) <= door and 1 <= y <= 6

    _wall(L, _line(v0, u0, v0, u1), 0, top, -1, 0, seed, pilaster=6, band=7, course=4,
          opens=front_open)
    m["openings"] += _opening(L, v0, mid, -1, 0, 1, 6, door, seed, glazed=False, sill=False)
    for du in (-8, 8):
        m["openings"] += _opening(L, v0, mid + du, -1, 0, 3, 5, 1, seed)

    # -- 2. the long flanks: the north carries the bays, the south is glazed for watching --------
    for u, n in ((u0, -1), (u1, 1)):
        _wall(L, _line(v0 + 1, u, v1, u), 0, top, 0, n, seed, pilaster=6, band=7, course=4,
              opens=lambda v, uu, y, n=n: (n > 0 and v % 6 == 1 and 3 <= y <= 6))
        if n > 0:
            for v in range(v0 + 1, v1 + 1):
                if v % 6 == 1:
                    m["openings"] += _opening(L, v, u, 0, n, 3, 6, 0, seed)
    _wall(L, _line(v1, u0, v1, u1), 0, top, 1, 0, seed, pilaster=6, band=7, course=4,
          opens=lambda v, u, y: abs(u - mid) <= 1 and 1 <= y <= 3)
    _service_door(L, v1, mid, seed, m, sign_y=5)

    # -- 3. the roof: one ridge the length of the hall, so the west elevation is a gable ---------
    m["roof"] = _gable(L, v0, u0, v1, u1, top + 2, seed, axis="v", pitch=2)["roof"]
    for u in range(mid - 4, mid + 5, 4):           # the oculus in the gable, over the sign band
        for k in (-1, 1):
            L.put(v0, top + 5, u + k, PAL["frame"])
    for u in range(mid - 2, mid + 3):
        L.put(v0, top + 6, u, PAL["frame"] if abs(u - mid) == 2 else PAL["band"])
    m["signs"] += bool(L.sign(v0 - 1, top + 6, mid - 1, -1, 0,
                              ["", "SKILL ARCADE", "THREE GAMES", ""]))
    m["signs"] += bool(L.sign(v0 - 1, top + 6, mid + 1, -1, 0,
                              ["", "FREE TO PLAY", "NO WAGERS", ""]))
    # A HALL WITH NO CEILING HAS NOTHING TO HANG A LANTERN FROM. The first build asked for twelve
    # and got none: `_lamp` checks its support and the roof's own eave course only exists over the
    # two flank columns, so every lamp over the aisle was hanging off open air and was refused,
    # silently. A tie beam every six is what an open-roofed hall has anyway - it is the truss.
    m["trusses"] = 0
    for v in range(v0 + 4, v1 - 2, 6):
        for u in range(u0 + 1, u1):
            L.put(v, top, u, PAL["beam"], axis="z")
            m["trusses"] += 1
        for u in (mid - 6, mid + 6):
            m["lamps"] += bool(_lamp(L, v, top - 1, u))

    # -- 4. the three bays, and the spectator side opposite them --------------------------------
    back = u0 + 1
    for (bv, lines) in bays:
        for v in range(bv - 3, bv + 4):            # the bay's back board, and its counter
            for y in range(1, 6):
                L.put(v, y, back, PAL["frame"] if y == 5 else PAL["band"])
            L.put(v, 0, back + 1, PAL["plinth"])
            L.put(v, 1, back + 1, PAL["counter"], type="top", waterlogged="false")
        for v in (bv - 4, bv + 4):
            for y in range(1, 6):
                L.put(v, y, back, PAL["beam"], axis="y")
                L.put(v, y, back + 1, PAL["beam"], axis="y")
        for v in range(bv - 4, bv + 5):            # the bay's own head and its valance
            L.put(v, 6, back, PAL["beam"], axis="x")
            L.put(v, 6, back + 1, PAL["board"])
            _valance(L, v, 6, back + 2, 0, -1)
        L.put(bv, 3, back, "target", power="0")    # the visible result, and the reset behind it
        for dv in (-2, 2):
            L.put(bv + dv, 3, back, PAL["glow"])
        L.put(bv, 2, back + 1, PAL["shutter"], facing="south", half="bottom", open="true",
              powered="false", waterlogged="false")
        m["signs"] += bool(L.sign(bv, 4, back + 2, 0, 1, lines))
        m["lamps"] += bool(_lamp(L, bv - 3, 5, back + 2))
        m["lamps"] += bool(_lamp(L, bv + 3, 5, back + 2))
        m["bays"] += 1
        for v in range(bv - 4, bv + 5):            # ...and the spectator edge opposite it
            L.put(v, 1, u1 - 1, PAL["cap"], type="bottom", waterlogged="false")
            L.put(v, 1, u1 - 2, PAL["seat"], facing="north", half="bottom", shape="straight",
                  waterlogged="false")
            L.put(v, 1, u1 - 3, PAL["inlay"])
            L.put(v, 2, u1 - 3, PAL["rail"], up="false", waterlogged="false",
                  north="low" if v > bv - 4 else "none", south="low" if v < bv + 4 else "none",
                  east="none", west="none")
    return m


def _prize_point(L, p) -> dict:
    """AN OPEN-FRONTED KIOSK, downstream of the arcade, and small on purpose.

    "Prize Point is downstream, small, and open to public circulation. It is a collection/result
    place, not retail." So it has one counter, one wall of shelves behind it and a hipped cap -
    nineteen by fifteen, which is a third of the lot it stands in.
    """
    seed = int(p["seed"])
    v0, u0, v1, u1 = 83, 353, 97, 371
    mid = (u0 + u1) // 2                           # U362 - midway walk 2's own spur column
    top = 6
    m = {"signs": 0, "lamps": 0, "openings": 0, "floor": 0}

    for v in (80, 81, 82):                         # the threshold, spur paving to counter
        for u in range(mid - 5, mid + 6):
            m["floor"] += bool(L.put(v, 0, u, PAL["inlay"] if v == 80 else PAL["floor2"]))
    m["floor"] += _pave(L, v0, u0, v1, u1, 0, seed)

    serve = 4

    def front_open(v, u, y):
        return abs(u - mid) <= serve and 1 <= y <= 3

    _wall(L, _line(v0, u0, v0, u1), 0, top, -1, 0, seed, pilaster=4, band=4, course=2,
          opens=front_open)
    _counter_front(L, v0, mid, serve, seed,
                   ["PRIZE POINT", "", "COLLECT HERE", ""],
                   ["PRIZE POINT", "", "SHOW YOUR", "SCORE"], m)
    m["openings"] += 1

    for u, n in ((u0, -1), (u1, 1)):
        _wall(L, _line(v0 + 1, u, v1, u), 0, top, 0, n, seed, pilaster=4, band=4, course=2,
              opens=lambda v, uu, y: v == v0 + 7 and 3 <= y <= 4)
        m["openings"] += _opening(L, v0 + 7, u, 0, n, 3, 4, 1, seed)
    _wall(L, _line(v1, u0, v1, u1), 0, top, 1, 0, seed, pilaster=4, band=4, course=2,
          opens=lambda v, u, y: abs(u - mid) <= 1 and 1 <= y <= 3)
    _service_door(L, v1, mid, seed, m)
    m["ceiling"] = _ceiling(L, v0 + 1, u0 + 1, v1 - 1, u1 - 1, top, seed)
    m["roof"] = _hip(L, v0, u0, v1, u1, top + 2, seed)

    for u in range(mid - 5, mid + 6):              # the shelf wall the prizes actually stand on
        L.put(v1 - 1, 1, u, PAL["board"])
        for y in (2, 4):
            L.put(v1 - 1, y, u, PAL["shelf"], type="bottom", waterlogged="false")
    for u in range(mid - 4, mid + 5, 4):
        L.put(v1 - 1, 3, u, "barrel", facing="west", open="false")
        L.put(v1 - 1, 5, u, "barrel", facing="west", open="false")
        m["lamps"] += bool(_lamp(L, v1 - 2, top - 1, u))
    for u in (mid - 6, mid + 6):
        L.put(v0 + 3, 0, u, PAL["glow"])
    return m


_KINDS = {
    "arrival_court": (_arrival_court, "PF Arrival Court"),
    "snack_window": (_snack_window, "PF Snack Window"),
    "skill_arcade": (_skill_arcade, "PF Skill Arcade"),
    "prize_point": (_prize_point, "PF Prize Point"),
}


def build(cfg: dict, donors=None) -> Canvas:
    p = {**MIDWAY_BUILD, **(cfg or {})}
    kind = p.get("kind")
    if kind not in _KINDS:
        raise ValueError(f"unknown midway build {kind!r}; have {sorted(_KINDS)}")
    if not p.get("lot"):
        raise ValueError("a midway build needs params.lot = [v0, u0, v1, u1]")
    v0, u0, v1, u1 = (int(q) for q in p["lot"])
    if v1 < v0 or u1 < u0:
        raise ValueError(f"lot {p['lot']} is empty")
    c = Canvas(v1 - v0 + 1, int(p["height"]), u1 - u0 + 1, donors)
    L = _Lot(c, (v0, u0, v1, u1), p.get("blocked") or ())
    meta = _KINDS[kind][0](L, p)
    # A CELL OUTSIDE THE LOT IS NOT A LOST CELL, IT IS A LOST PART: anything past the lot is
    # cropped at placement, so a refusal is a wall with a hole in it that nothing downstream can
    # see. A cell the ground layer already owns is the same failure from the other side.
    if L.refused or L.blocked_hits:
        raise ValueError(f"{kind}: {L.refused} cell(s) outside lot {p['lot']}, "
                         f"{L.blocked_hits} on cells the ground layer already owns")
    if p.get("at"):
        c.world_origin = tuple(int(q) for q in p["at"])
    c.meta = {
        "kind": "midway_build", "build": kind, "name": _KINDS[kind][1],
        "lot": [v0, u0, v1, u1],
        # THE FACING IS A COMPASS WORD, which is what `park.py` records and what `tools/look.py`
        # and `tools/panel.py` both read: "the direction the FRONT looks out; a visitor stands in
        # the +facing direction". Every one of these four fronts WEST onto the street it addresses,
        # so bearing 0 is head-on. A design with no facing makes both tools say so and pick a
        # bearing for themselves, which is how this repo got a profile view wrong twice in a day.
        "facing": "west",
        **meta,
        "contract": "one connected building inside lot V%d-%d U%d-%d, fronting west, with a real "
                    "doorway, a lit interior, a named sign, and no street furniture"
                    % (v0, v1, u0, u1),
    }
    return c
