"""THE GRAMMAR THAT TURNS BUILDINGS INTO ATTRACTIONS: what stands IN FRONT OF and BETWEEN them.

Jack, looking at the placed park: *"they are visually great - but all serve no actual defined
purpose - it feels more like multiple villages or towns than a theme park or amusement
destination."* Measured, he is right, and the gap is not in the buildings:

    queue lines            0        marquees / ride signs  0
    ride entrances/exits   0        themed props           0

**A TOWN IS BUILDINGS ON STREETS. A THEME PARK IS EVERYTHING BETWEEN THEM.** Nineteen modules
stand on a finished ground layer and not one of them says what it is from outside, nobody queues
for anything, no threshold reads as a ride entrance rather than a shop door, and between the
clusters are measured troughs of empty lawn twenty and thirty blocks wide.

An earlier attempt at exactly this was rejected as *"chaos"*. **The chaos was not that queues,
gates, arches and markers existed - it was that they were scattered ON TOP OF the streets and
collided with the ground layer.** So the rule this whole module is built around, and the one that
`tests/test_park_frontage.py` proves cell by cell against the shipped `Park Ways`:

    NOTHING HERE MAY OCCUPY A CELL THE GROUND LAYER OR A BUILDING ALREADY OWNS,
    AND NOTHING HERE MAY STAND IN A WALKWAY.

Two mechanisms enforce it and they are different in kind:

* **NOT ONE CELL IS EMITTED BELOW THE BUILD PLANE.** `Y202` is the ground layer's own surface -
  every path, plaza, verge, spur and kerb in the park is that one course - and this module's
  `h=0` is `Y203`. So a paved cell cannot be touched *by construction*, not by care.
* **OVER PAVING, ONLY ABOVE HEAD HEIGHT.** A marquee is an ARCH over the spur that already leads
  to the door it names; that is what an entrance arch is for. Its piers stand on lawn either
  side and its head beam crosses at `HEAD_CLEAR` courses up, so a walker passes under it. Any
  cell of this design standing over a paved column is asserted to be at `h >= HEAD_CLEAR`.

WHAT IS DELIBERATELY NOT BUILT: street lamps, benches, kerbs and paving. `Park Ways` draws all
of it - 27 promenade lamps, a mast every 22 along every verge, a bench every 18 - and a second
copy of somebody else's street furniture is precisely the chaos that was thrown away. **A queue
here has no floor of its own either**: it is fence rails, turn posts and a canopy standing on the
lawn, which reads as a queue instantly and cannot be mistaken for a duplicate street.

GEOMETRY, stated once because it is invisible in a render
--------------------------------------------------------
Park coordinates throughout, exactly as `frontier_builds` and `midway_builds` use them:

    V   the 200-deep axis; V0 is the connector edge, V6-18 the spine, V170+ protected reserve
    U   the 600-long axis; frontier U0-169, midway U215-384, prismworks U430-599
    h   courses above the lawn. h=0 is Y203, the course a guest stands on

and world is `anchor + (V, h, U)` with `anchor = (97500, 203, 80300)`. Canvas x is V and canvas z
is U, so Minecraft's +x is EAST and +z is SOUTH: **a face looking toward the spine (falling V)
looks WEST**, which is the facing every attraction in this park records.

Each piece carries a `_Frame`: `facing` is the direction its FRONT looks out, `d` runs from the
front INTO the piece, `i` runs along its frontage. One frame, so a facing bug is one bug.

WHY A FLUSH FROGLIGHT IS NOT USED HERE, THOUGH IT IS THIS ISLAND'S OWN IDIOM
---------------------------------------------------------------------------
A flush froglight IS the floor - an opaque emitter one course down - and the floor here belongs
to `Park Ways` at Y202. Setting one would be writing into the ground layer, which is the one
thing this module may not do. So every light is a LANTERN HUNG FROM A FULL BLOCK (rule 6: a
lantern cannot stand on iron bars, and a lamp under a slab cap reads as hanging from air), at
`h >= 3` so nobody walks into it, or a froglight built into a pier's own masonry where it is a
block of the structure rather than a fixture in a floor.
"""
from __future__ import annotations

import math

from .. import blocks as _blocks, nbt, schem
from .canvas import Canvas
from .vertical import World

SIGN_WIDTH = 15          # a sign line clips mid-word past this; asserted, never hoped for

#: Courses of clear air a walker is owed under anything that crosses a path. Two is a player;
#: three is a player who does not flinch. Every cell of this design standing over a cell the
#: ground layer paved must be at or above this, and the test measures it rather than trusting it.
HEAD_CLEAR = 3

#: V is the 200-deep axis and U the 600-long one. Minecraft's +x is EAST and +z is SOUTH, so a
#: face looking toward the spine (falling V) looks WEST. Same table as `park._STEP`, in (dv, du).
_STEP = {"west": (-1, 0), "east": (1, 0), "north": (0, -1), "south": (0, 1)}
_BACK = {"west": "east", "east": "west", "north": "south", "south": "north"}
#: A stair's TALL side IS its `facing`, so a stair that LEANS INTO a wall faces away from it.
#: Our renderer draws both directions identically - `tests/test_park_frontage.py` asserts this
#: rather than anybody eyeballing a render.
_LEAN = _BACK

#: ONE PALETTE PER LAND, taken block for block from the land's own shipped builder so a marquee
#: reads as the same hand as the building behind it - `frontier_builds.PAL`, `midway_builds.PAL`
#: and `prismworks_builds.PRISM`. It is a COPY rather than an import on purpose: three streams are
#: editing this park at once and a KeyError in a neighbour's refactor must not stop this design
#: building. What keeps it honest is not the copy, it is
#: `test_every_material_is_legal_cheap_and_spendable`, which asks the registry - never a memory -
#: whether each entry exists, is in the 1.19 SERVER's list, is not currency, and is not expensive.
PAL = {
    "frontier": {
        "plinth": "polished_blackstone_bricks",   # L45  the dark base course
        "pier": "stone_bricks",                   # L122 masonry
        "band": "smooth_stone",                   # L159 the string course
        "worn": "cracked_stone_bricks",
        "carved": "chiseled_stone_bricks",
        "post": "spruce_log",                     # a corner post reads as a post
        "beam": "stripped_spruce_log",            # every head beam and lintel
        "board": "spruce_planks",                 # the fascia field
        "roof": "dark_oak_planks",
        "accent": "red_wool",
        "accent2": "white_wool",
        "stair": "spruce_stairs",
        "roof_stair": "dark_oak_stairs",
        "pier_stair": "stone_brick_stairs",
        "slab": "spruce_slab",
        "pier_slab": "stone_brick_slab",
        "balustrade": "stone_brick_wall",
        "fence": "spruce_fence",
        "gate": "spruce_fence_gate",
        "shutter": "spruce_trapdoor",
        "canopy_a": "spruce_planks",
        "canopy_b": "dark_oak_planks",
        "light": "lantern",
        "glow": "ochre_froglight",
        "wood": "spruce",
    },
    "midway": {
        "plinth": "polished_blackstone_bricks",   # 45
        "pier": "stone_bricks",                   # 122
        "band": "chiseled_stone_bricks",
        "worn": "cracked_stone_bricks",
        "carved": "chiseled_stone_bricks",
        "post": "stripped_oak_log",
        "beam": "stripped_oak_log",
        "board": "white_wool",                    # 236 - the fairground board
        "roof": "red_wool",
        "accent": "red_wool",                     # 65 - the midway's own accent
        "accent2": "white_wool",
        "stair": "oak_stairs",
        "roof_stair": "stone_brick_stairs",
        "pier_stair": "stone_brick_stairs",
        "slab": "oak_slab",
        "pier_slab": "stone_brick_slab",
        "balustrade": "stone_brick_wall",
        "fence": "oak_fence",
        "gate": "oak_fence_gate",
        "shutter": "oak_trapdoor",
        "canopy_a": "red_wool",                   # a canopy is TWO colours alternating; one
        "canopy_b": "white_wool",                 # colour is a roof, and a roof is not a fair
        "light": "lantern",
        "glow": "ochre_froglight",
        "wood": "oak",
    },
    "prismworks": {
        # `blackstone` 38 IS SEVEN LUMINANCE OFF THE PIER'S 45 - the same family, and a
        # ladder cannot exist inside one family. Across families the rung is real:
        # black_wool 21 -> polished_blackstone_bricks 45 -> smooth_basalt 73.
        "plinth": "black_wool",                   # 21 - the dark base course
        "pier": "polished_blackstone_bricks",     # 45 - the wall
        "band": "smooth_basalt",                  # 73 - the vertical rhythm
        "worn": "cracked_polished_blackstone_bricks",
        "carved": "chiseled_polished_blackstone",
        "post": "smooth_basalt",
        "beam": "smooth_basalt",
        "board": "black_wool",                    # 22 - the recess the signal reads against
        "roof": "polished_blackstone_bricks",
        "accent": "cyan_wool",                    # 104
        "accent2": "light_blue_wool",             # 145 - the crown band
        "stair": "polished_blackstone_brick_stairs",
        "roof_stair": "polished_blackstone_brick_stairs",
        "pier_stair": "polished_blackstone_brick_stairs",
        "slab": "polished_blackstone_brick_slab",
        "pier_slab": "polished_blackstone_brick_slab",
        "balustrade": "polished_blackstone_brick_wall",
        "fence": "warped_fence",
        "gate": "warped_fence_gate",
        "shutter": "warped_trapdoor",
        "canopy_a": "black_wool",
        "canopy_b": "cyan_wool",
        "light": "soul_lantern",                  # the one cold light
        "glow": "pearlescent_froglight",
        "wood": "warped",
        "rod": "end_rod",
    },
}

PARK_FRONTAGE = {
    "land": None,                 # frontier | midway | prismworks - the palette, one per design
    "anchor": [97500, 203, 80300],   # V0, the course a guest stands on, U0
    "pieces": None,               # [{kind, at: [V, U], ...}]
    "seed": 0,
}

#: Defaults per piece kind, merged under whatever the config names.
PIECE = {
    "kind": None,
    "at": None,                   # [V, U] - the piece's FRONT-CENTRE (marquee/portal) or
                                  # FRONT-LEFT corner (queue/sight/pergola/stamp)
    "facing": "west",             # the direction the FRONT looks out; west is toward the spine
    "land": None,                 # overrides the design's land - a reach piece may borrow one
    "title": None,
    "lines": None,
    "seed": 0,
}


# --------------------------------------------------------------------------- the frame


class _Frame:
    """A piece's own axes in PARK coordinates, and the only way a block reaches the world.

    `facing` is the direction the FRONT looks out; `d` runs from the front INTO the piece and
    `i` along its frontage, so `at(i, d, h)` is the same arithmetic `park._Frame` uses with
    (V, U) in place of (x, z). One frame per piece means a facing bug is one bug rather than
    eleven, and the twelfth invisible.
    """

    def __init__(self, at, facing, anchor):
        self.v, self.u = int(at[0]), int(at[1])
        if facing not in _STEP:
            raise ValueError(f"facing must be one of {sorted(_STEP)}, got {facing!r}")
        self.facing = facing
        self.back = _BACK[facing]
        self.dv, self.du = _STEP[facing]
        self.sv, self.su = -self.du, -self.dv
        self.ax, self.ay, self.az = (int(a) for a in anchor)

    def at(self, i, d, h=0):
        """(V, U, h) of the cell at frontage `i`, depth `d`, course `h`."""
        return (self.v - self.dv * d + self.sv * i,
                self.u - self.du * d + self.su * i,
                int(h))

    def world(self, i, d, h=0):
        v, u, y = self.at(i, d, h)
        return (self.ax + v, self.ay + y, self.az + u)

    def side(self, sign: int) -> str:
        """The compass name of the frontage direction: +1 is increasing `i`."""
        for name, (dv, du) in _STEP.items():
            if (dv, du) == (self.sv * sign, self.su * sign):
                return name
        raise AssertionError("frontage axis is not a compass direction")


#: Properties a CALLER MAY ASK FOR AND NOT GET. A palette key is an abstraction - one land's
#: `post` is `spruce_log` and another's is `smooth_basalt` - so `axis="y"` means *stand this up if
#: it is the kind of block that can stand up*, and a basalt block simply has no axis. Every OTHER
#: unknown property is a typo and raises, because a silently-dropped `facing` is a stair pointing
#: the wrong way and this repo's renderer draws that identically to a right one.
_OPTIONAL = {"axis"}


def _state(name: str, props: dict) -> dict:
    legal = _blocks.props(name)
    out = {}
    for k, v in props.items():
        if k in legal:
            out[k] = str(v)
        elif k not in _OPTIONAL:
            raise ValueError(f"{name} has no property {k!r}; it has {sorted(legal)}")
    return out


def _put(w, f, pal, i, d, h, key, **props):
    """One block, named through the land palette. `key` may be a palette key or a block name."""
    x, y, z = f.world(i, d, h)
    name = pal.get(key, key)
    w.put(x, y, z, name, **_state(name, props))


def _has(w, f, i, d, h) -> bool:
    return w.has(*f.world(i, d, h))


def _sign(w, f, pal, i, d, h, facing, lines, back=()):
    """A wall sign in the cell IN FRONT of its wall, its text facing away from its support.

    **THE SUPPORT IS CHECKED, NOT ASSUMED.** A wall sign floating in air draws exactly like one
    on a wall in every render this repo has, and the game simply refuses to place it - so a
    silently-refused sign is this project's most-repeated failure shape. Returns True if it was
    placed; a caller that ignores a False is asking for the bug back.
    """
    fdv, fdu = _STEP[facing]
    x, y, z = f.world(i, d, h)
    if not w.has(x - fdv, y, z - fdu):
        # A REFUSED SIGN IS SILENT, and silence is the failure. Every refusal is recorded and the
        # build reports the count, so a name board that quietly is not there shows up as a number
        # rather than as a photograph taken after somebody placed the design.
        getattr(w, "refused_signs", []).append((x, y, z, facing, list(lines)[:1]))
        return False
    # NOT TRUNCATED. Trimming here makes the build-time width check dead code and turns a config
    # typo into a name that clips mid-word - which only shows in a screenshot taken after somebody
    # has placed the design, the most expensive place in this pipeline to find one.
    front = [str(s) for s in list(lines)[:4]]
    front += [""] * (4 - len(front))
    w.put(x, y, z, f"{pal['wood']}_wall_sign", facing=facing, waterlogged="false")
    w.sign(x, y, z, front=front, back=[str(s) for s in list(back)[:4]],
           colour="white", glowing=True)
    return True


def _hang(w, f, pal, i, d, h):
    """A lantern hangs from a FULL block, so the cell above it is filled first (rule 6).

    The lowland's own note: a lamp under a slab cap reads as 'hanging from air' in the audit,
    because a slab is not a full block.
    """
    _put(w, f, pal, i, d, h + 1, "beam")
    _put(w, f, pal, i, d, h, pal["light"], hanging="true", waterlogged="false")


def _hash01(*args) -> float:
    h = 2166136261
    for a in args:
        h ^= (int(a) * 2654435761) & 0xFFFFFFFF
        h = (h * 16777619) & 0xFFFFFFFF
        h ^= h >> 13
    return (h & 0xFFFFFF) / 16777216.0


def _weathered(pal, seed, *cell):
    """Masonry variety hashed on the CELL, never on the course.

    Hashed on the course, every block in a course comes out identical and the wall is horizontal
    stripes of one material - the deck soffit shipped exactly that once.
    """
    r = _hash01(seed, *cell)
    if r < 0.10:
        return pal["worn"]
    if r < 0.14:
        return pal["carved"]
    return pal["pier"]


# --------------------------------------------------------------------------- marquee

MARQUEE = {
    "span": 3,            # the clear opening, in frontage cells - a spur is 3 wide
    "pier": 2,            # pier width along the frontage
    # THREE, NOT FOUR. The verge band is V19-23 and the sign hangs one cell in FRONT of the
    # fascia, so a marquee whose front stands at V20 reads its front sign at V19 and its back
    # sign at V23 - both lawn, and neither one course into the lot the building already owns.
    "depth": 3,
    # SIX, BECAUSE A LAMP MAST IS SIX. `Park Ways` puts a mast every 22 cells along each verge
    # lamp line and the tallest cell of one is its slab cap at Y208 - h=5. A marquee's opening
    # may cross a mast, and often must: the spur it straddles and the mast beside it are on the
    # same line. So the head beam goes ABOVE the tallest thing the ground layer builds, and the
    # opening is six clear courses rather than five.
    "height": 6,          # the head beam's course. Clear opening is h=0..height-1
    "board": 2,           # courses of fascia over the head
    "wing": 0,            # extra outer piers, each `pier` wide, with `span`-wide bays between
    "crown": True,        # the cornice course and the two crown lamps
    "style": "gantry",    # gantry (straddles a path) | board (freestanding, no opening)
    "width": 7,           # board style only: the whole fascia, in frontage cells
}


def _marquee(w, f, pal, p) -> dict:
    """THE NAME BOARD OVER AN ATTRACTION'S OWN APPROACH.

    Not one of the park's nineteen modules says what it is from outside. This is the fix, and its
    form is decided by where it has to stand: the ground layer already draws a 3-wide paved SPUR
    from the street to every attraction's front door, and the five courses of lawn either side of
    that spur are the only ground in front of a building that is not somebody else's.

    So a marquee STRADDLES the spur: piers on the lawn either side, a head beam across at
    `height`, and the fascia the name is written on above that. It is an entrance arch, which is
    what a theme park puts at the head of an attraction, and it costs no walkable ground at all -
    every cell over the paving is at `h >= height`, which is checked rather than hoped for.

    `style: board` drops the opening and stands the whole thing as one freestanding fascia, for
    the four modules whose front has no spur to straddle.
    """
    q = {**MARQUEE, **p}
    span, pw = max(0, int(q["span"])), max(1, int(q["pier"]))
    depth, height = max(1, int(q["depth"])), max(4, int(q["height"]))
    board_h, wing = max(1, int(q["board"])), max(0, int(q["wing"]))
    seed = int(q.get("seed", 0))
    board = q["style"] == "board"
    if board:
        # A FREESTANDING BOARD IS A GANTRY WITH NO OPENING. Four of the park's attractions front
        # onto a walk or a promenade with no spur to straddle - there is nothing to arch over -
        # so the same piece is built solid and stands beside the door instead of over the path.
        span, wing = 0, 0
        pw = max(2, (int(q["width"]) + 1) // 2)

    # THE FRONTAGE, LAID OUT SYMMETRICALLY ABOUT `at`. A gantry whose two piers are different
    # distances from the path it straddles is the asymmetry the park railway was rebuilt to cure;
    # every offset below is mirrored, so it cannot happen by arithmetic.
    half = span // 2
    piers = []                                    # (i0, i1) inclusive, in frontage cells
    edge = half + (1 if span else 0)
    for k in range(wing + 1):
        lo = edge + k * (pw + span)
        piers.append((-(lo + pw - 1), -lo))
        piers.append((lo, lo + pw - 1))
    i_lo = min(a for a, _b in piers)
    i_hi = max(b for _a, b in piers)

    # -- the piers ---------------------------------------------------------------------------
    for (a, b) in piers:
        for i in range(a, b + 1):
            for d in range(depth):
                _put(w, f, pal, i, d, 0, "plinth")
                for h in range(1, height):
                    _put(w, f, pal, i, d, h, _weathered(pal, seed, i, d, h))
                _put(w, f, pal, i, d, height - 2, "band")
        # a log at each pier's own front-outer corner: a corner post reads as a post
        outer = a if abs(a) > abs(b) else b
        for h in range(1, height - 1):
            _put(w, f, pal, outer, 0, h, "post", axis="y")
        # THE BRACKET UNDER THE BEAM, CUT INTO THE PIER RATHER THAN HUNG OFF IT. A corbel that
        # projects into the opening is the obvious way to give an arch a head, and on this park it
        # is the one place it cannot go: the opening straddles a spur, the ground layer's lamp mast
        # stands on the same line, and its slab cap reaches exactly the course a corbel wants. An
        # upside-down stair course inside the pier's OWN footprint adds the same shadow line and
        # occupies no cell the piece did not already own. Detail blocks are 7-30x under-used in
        # this repo against outside builds; this is where they earn their keep.
        for i in range(a, b + 1):
            _put(w, f, pal, i, 0, height - 1, pal["pier_stair"], facing=_LEAN[f.facing],
                 half="top", shape="straight", waterlogged="false")
            if depth > 1:
                _put(w, f, pal, i, depth - 1, height - 1, pal["pier_stair"],
                     facing=_LEAN[f.back], half="top", shape="straight", waterlogged="false")

    # -- the head beam, and the fascia the name is written on --------------------------------
    for i in range(i_lo, i_hi + 1):
        for d in range(depth):
            _put(w, f, pal, i, d, height, "beam", axis=_axis_of(f, "i"))
        for h in range(height + 1, height + 1 + board_h):
            _put(w, f, pal, i, 0, h, "board")
            _put(w, f, pal, i, depth - 1, h, "board")
    # the accent band across the top of the fascia - the one line that says fairground
    for i in range(i_lo, i_hi + 1):
        _put(w, f, pal, i, 0, height + board_h, "accent")
        _put(w, f, pal, i, depth - 1, height + board_h, "accent")

    # -- the cornice, and the crown lamps ----------------------------------------------------
    if q["crown"]:
        for i in range(i_lo, i_hi + 1):
            _put(w, f, pal, i, 0, height + board_h + 1, pal["roof_stair"],
                 facing=_LEAN[f.facing], half="bottom", shape="straight", waterlogged="false")
            if depth > 1:
                _put(w, f, pal, i, depth - 1, height + board_h + 1, pal["roof_stair"],
                     facing=_LEAN[f.back], half="bottom", shape="straight", waterlogged="false")
        for (a, b) in piers:
            _put(w, f, pal, (a + b) // 2, depth // 2, height + board_h + 1, "accent2")
            _put(w, f, pal, (a + b) // 2, depth // 2, height + board_h + 2, "glow")

    # -- the lights, hung UNDER the head beam and INSIDE the opening -------------------------
    lamps = 0
    if span:
        for s in (-1, 1):
            i = s * (half + 1)
            _put(w, f, pal, i, 0, height - 1, pal["light"], hanging="true", waterlogged="false")
            _put(w, f, pal, i, depth - 1, height - 1, pal["light"], hanging="true",
                 waterlogged="false")
            lamps += 2

    # -- the name ----------------------------------------------------------------------------
    title = str(q.get("title") or "").upper()
    lines = [title] + [str(s) for s in (q.get("lines") or [])]
    # A ONE-COURSE PIECE HAS ONE FACE. Four of the park's attractions front onto a walk with a
    # spur exactly one course deep, so their marquee is one course deep too - and a back sign on
    # such a piece has the BUILDING behind it, not its own fascia: it is refused, silently, which
    # is this project's most-repeated failure shape. It is simply not drawn.
    faces = [(-1, f.facing)] + ([(depth, f.back)] if depth >= 2 else [])
    signs = 0
    for sign_d, facing in faces:
        # the sign hangs in the cell in FRONT of the fascia, so its support is the fascia itself
        if _sign(w, f, pal, 0, sign_d, height + 1, facing, lines):
            signs += 1
    return {"kind": "marquee", "title": title, "signs": signs, "lamps": lamps,
            "span": span, "piers": len(piers), "frontage": (i_lo, i_hi),
            "height": height + board_h + 2}


def _axis_of(f, which: str) -> str:
    """The pillar axis of a log laid along the frontage (`i`) or into the piece (`d`)."""
    if which == "i":
        return "z" if f.su else "x"
    return "z" if f.du else "x"


# --------------------------------------------------------------------------- portal

PORTAL = {
    "span": 3,
    "pier": 1,
    "depth": 2,
    "height": 4,
    "mode": "entrance",       # entrance | exit
}


def _portal(w, f, pal, p) -> dict:
    """A RIDE THRESHOLD, and the thing that makes it not a shop door.

    A shop door is a hole in a wall. A ride threshold is a FREESTANDING FRAME you pass through
    with nothing either side of it, and it comes in two kinds that a visitor must be able to tell
    apart from twenty blocks away without reading anything:

        entrance   the land's accent colour across the head, a lamp each side, and the name
        exit       no colour at all, a plain slab head, and one word

    Colour is the whole of the distinction, because at distance the word is unreadable and the
    shape is not.
    """
    q = {**PORTAL, **p}
    span, pw = max(1, int(q["span"])), max(1, int(q["pier"]))
    depth, height = max(1, int(q["depth"])), max(3, int(q["height"]))
    entrance = q["mode"] != "exit"
    half = span // 2
    lo = half + 1
    piers = [(-(lo + pw - 1), -lo), (lo, lo + pw - 1)]

    for (a, b) in piers:
        for i in range(a, b + 1):
            for d in range(depth):
                _put(w, f, pal, i, d, 0, "plinth")
                for h in range(1, height):
                    _put(w, f, pal, i, d, h, "post" if entrance else "pier",
                         **({"axis": "y"} if entrance else {}))
    for i in range(piers[0][0], piers[1][1] + 1):
        for d in range(depth):
            _put(w, f, pal, i, d, height, "accent" if entrance else "band")
    # the head's own cap: a stair course leaning off both faces, which is what gives a frame a
    # shadow line rather than a flat top
    for i in range(piers[0][0], piers[1][1] + 1):
        _put(w, f, pal, i, 0, height + 1, pal["pier_stair"], facing=_LEAN[f.facing],
             half="bottom", shape="straight", waterlogged="false")
        if depth > 1:
            _put(w, f, pal, i, depth - 1, height + 1, pal["pier_stair"], facing=_LEAN[f.back],
                 half="bottom", shape="straight", waterlogged="false")

    lamps = 0
    if entrance:
        for s in (-1, 1):
            i = s * lo
            _put(w, f, pal, i, 0, height - 1, pal["light"], hanging="true", waterlogged="false")
            lamps += 1

    title = str(q.get("title") or ("ENTRANCE" if entrance else "EXIT")).upper()
    lines = [title] + [str(s) for s in (q.get("lines") or [])]
    signs = int(_sign(w, f, pal, 0, -1, height, f.facing, lines))
    return {"kind": f"portal/{q['mode']}", "title": title, "signs": signs, "lamps": lamps,
            "height": height + 2}


# --------------------------------------------------------------------------- queue

QUEUE = {
    "width": 9,           # cells along the frontage
    "depth": 21,          # cells into the park - the long axis of the switchback
    "leg_every": 3,       # a rail every this many courses of depth
    "canopy_from": 0.5,   # fraction of the depth after which the canopy runs
    "height": 5,          # canopy soffit
    "entrance": True,     # a portal at the near end
    "exit": True,         # ...and one at the far end
}


def _queue(w, f, pal, p) -> dict:
    """A SWITCHBACK LINE: rails folded back on themselves, a shaded run, and two ends.

    Architecture only, so there is no circuit to verify - but there IS a contract and it is the
    one a queue can fail: **ONE CONNECTED WALK, an entrance at one end and an exit at the other,
    and no dead end.** A switchback whose last leg is closed is a pen, and it looks identical.

    **IT HAS NO FLOOR.** The lawn is the floor. That is not a saving, it is the rule this module
    is built around: `Park Ways` owns every paved cell in the park and a second field of paving
    beside its own is exactly the duplication that got the first attempt at this thrown away. A
    fenced switchback standing on grass reads as a queue from any distance, and cannot be
    mistaken for a street.
    """
    q = {**QUEUE, **p}
    width, depth = max(5, int(q["width"])), max(7, int(q["depth"]))
    every, height = max(2, int(q["leg_every"])), max(4, int(q["height"]))
    legs = 0
    turns = []
    for k, d in enumerate(range(every, depth - 1, every)):
        near = k % 2 == 0
        for i in range(width):
            # THE GAP IS THE END THE WALK TURNS AT, and it alternates. Without it every leg is a
            # closed rail and the queue is a set of pens.
            if near and i >= width - 1:
                continue
            if not near and i <= 0:
                continue
            _put(w, f, pal, i, d, 0, pal["fence"], north="false", south="false",
                 east="false", west="false", waterlogged="false")
        turns.append((width - 1 if near else 0, d))
        legs += 1

    # the outer rail, so the line is a line rather than a field of rails
    for d in range(depth):
        for i in (-1, width):
            _put(w, f, pal, i, d, 0, pal["fence"], north="false", south="false",
                 east="false", west="false", waterlogged="false")

    # -- the turn posts, and the only light a queue gets -------------------------------------
    # A LANTERN AT h=2 IS AT HEAD HEIGHT. A player occupies h=0 and h=1, so a fixture in the
    # walk's own courses is something to bump into; every lamp here hangs at h=3 under a full
    # block at h=4, which is the same rule `_hang` states and the reason the post is 4 tall.
    lamps = 0
    for (i, d) in turns:
        for h in range(4):
            _put(w, f, pal, i, d, h, "post", axis="y")
        _put(w, f, pal, i, d, 4, "beam", axis=_axis_of(f, "i"))
        # the lantern hangs on the AISLE side of the post, clear of the post's own column
        side = 1 if i <= 0 else -1
        _put(w, f, pal, i + side, d, 4, "beam", axis=_axis_of(f, "i"))
        _put(w, f, pal, i + side, d, 3, pal["light"], hanging="true", waterlogged="false")
        lamps += 1

    # -- the canopy: shade over the back of the line -----------------------------------------
    d0 = int(depth * float(q["canopy_from"]))
    posts = []
    for i in (-1, width):
        for d in (d0, depth - 1):
            for h in range(height):
                _put(w, f, pal, i, d, h, "post", axis="y")
            posts.append((i, d))
    for i in range(-1, width + 1):
        for d in range(d0, depth):
            _put(w, f, pal, i, d, height, "canopy_a" if (i + d) % 2 == 0 else "canopy_b")
    for i in range(-1, width + 1):
        _put(w, f, pal, i, d0 - 1, height, pal["roof_stair"], facing=_LEAN[f.facing],
             half="bottom", shape="straight", waterlogged="false")

    meta = {"kind": "queue", "width": width, "depth": depth, "legs": legs, "lamps": lamps,
            "turns": turns,
            "contract": "a switchback line on open lawn: one entrance at the near end, one exit "
                        "at the far end, every leg open at the end it turns at, a canopy over "
                        "the back, and no floor of its own"}
    # -- the two ends -------------------------------------------------------------------------
    if q.get("entrance"):
        ef = _Frame(f.at((width - 1) // 2, -2)[:2], f.facing, (f.ax, f.ay, f.az))
        meta["entrance"] = _portal(w, ef, pal, {
            "mode": "entrance", "span": 3, "pier": 1, "depth": 2, "height": 4,
            "title": q.get("title") or "ENTRANCE",
            "lines": q.get("lines") or ["join the line", "", "one at a time"]})
    if q.get("exit"):
        xv, xu = f.at((width - 1) // 2, depth + 1)[:2]
        xf = _Frame((xv, xu), f.back, (f.ax, f.ay, f.az))
        meta["exit"] = _portal(w, xf, pal, {
            "mode": "exit", "span": 3, "pier": 1, "depth": 2, "height": 4,
            "title": "WAY OUT", "lines": ["", "", "no re-entry"]})
    return meta


# --------------------------------------------------------------------------- sight pieces

SIGHT = {
    "motif": None,        # water_tower | bandstand | pylon | ore_cart | bunting | lens
    "height": None,       # motif default if unset
    "radius": 4,
}


def _water_tower(w, f, pal, q) -> dict:
    """FRONTIER: a timber tank on a braced trestle. ~21 courses, and it is a LANDMARK.

    The measured trough bands of this park are 20-30 blocks of open lawn a visitor walks past and
    sees nothing in. `95.5% of everywhere a guest can stand is in the bottom ten courses`, so a
    thing three blocks tall does not carry twenty blocks of walking - a sight piece has to be
    tall, and a water tower is the tallest thing the frontier's own vocabulary owns.
    """
    legs = [(0, 0), (0, 5), (5, 0), (5, 5)]
    top = int(q.get("height") or 12)
    for (i, d) in legs:
        _put(w, f, pal, i, d, 0, "plinth")
        for h in range(1, top):
            _put(w, f, pal, i, d, h, "post", axis="y")
    # THE BRACING IS WHAT MAKES A TRESTLE A TRESTLE. Four posts alone are a table; the diagonals
    # are the only thing in the silhouette that says structure rather than furniture.
    for h in (3, 7):
        for i in range(6):
            _put(w, f, pal, i, 0, h, pal["fence"], waterlogged="false")
            _put(w, f, pal, i, 5, h, pal["fence"], waterlogged="false")
        for d in range(6):
            _put(w, f, pal, 0, d, h, pal["fence"], waterlogged="false")
            _put(w, f, pal, 5, d, h, pal["fence"], waterlogged="false")
    # the deck
    for i in range(-1, 7):
        for d in range(-1, 7):
            _put(w, f, pal, i, d, top, "board")
    # the tank: five courses of plank with two dark hoops, then a stepped cap
    for h in range(top + 1, top + 6):
        for i in range(6):
            for d in range(6):
                if (i in (0, 5)) or (d in (0, 5)):
                    _put(w, f, pal, i, d, h, "roof" if h in (top + 2, top + 4) else "board")
                elif h == top + 5:
                    _put(w, f, pal, i, d, h, "roof")
    for i in range(6):
        _put(w, f, pal, i, -1, top + 5, pal["roof_stair"], facing=_LEAN[f.facing],
             half="bottom", shape="straight", waterlogged="false")
        _put(w, f, pal, i, 6, top + 5, pal["roof_stair"], facing=_LEAN[f.back],
             half="bottom", shape="straight", waterlogged="false")
    for d in range(6):
        _put(w, f, pal, -1, d, top + 5, pal["roof_stair"], facing=_LEAN[f.side(-1)],
             half="bottom", shape="straight", waterlogged="false")
        _put(w, f, pal, 6, d, top + 5, pal["roof_stair"], facing=_LEAN[f.side(1)],
             half="bottom", shape="straight", waterlogged="false")
    for i in range(2, 4):
        for d in range(2, 4):
            _put(w, f, pal, i, d, top + 6, "roof")
    _put(w, f, pal, 2, 2, top + 7, "accent")
    _put(w, f, pal, 3, 3, top + 7, "accent")
    # the name band, and a lamp under the deck so the thing is a lantern at night
    for i in range(6):
        _put(w, f, pal, i, -1, top + 3, "accent")
    _sign(w, f, pal, 2, -2, top + 3, f.facing, [str(q.get("title") or "WATER TOWER")])
    for (i, d) in ((0, 0), (5, 0), (0, 5), (5, 5)):
        _put(w, f, pal, i, d, top - 1, pal["light"], hanging="true", waterlogged="false")
    _put(w, f, pal, 2, 2, top + 8, "glow")
    return {"kind": "sight/water_tower", "height": top + 8, "footprint": [8, 8]}


def _bandstand(w, f, pal, q) -> dict:
    """MIDWAY: a raised stand with a striped canopy. The fairground's own shape.

    A canopy is TWO COLOURS ALTERNATING - one colour is a roof, and a roof is not a fair. The
    stand is a place as well as an object: it has a step up, standing room, and a rail, so a
    group can stand on it rather than walk round it.
    """
    r = max(3, int(q.get("radius", 4)))
    n = 2 * r + 1
    tall = int(q.get("height") or 6)

    def inside(i, d, rad):
        di, dd = i - r, d - r
        return di * di + dd * dd <= rad * rad + rad * 0.5

    for i in range(n):
        for d in range(n):
            if not inside(i, d, r):
                continue
            _put(w, f, pal, i, d, 0, "plinth" if not inside(i, d, r - 1) else "pier")
            if inside(i, d, r - 1):
                _put(w, f, pal, i, d, 1, "band")
    # the step up, on the front - a platform you cannot get onto is a plinth
    for i in range(r - 1, r + 2):
        _put(w, f, pal, i, -1, 0, pal["pier_stair"], facing=_LEAN[f.back], half="bottom",
             shape="straight", waterlogged="false")
    # posts and rail
    posts = [(r + int(round(r * c)), r + int(round(r * s)))
             for c, s in ((1, 0), (0.7, 0.7), (0, 1), (-0.7, 0.7),
                          (-1, 0), (-0.7, -0.7), (0, -1), (0.7, -0.7))]
    # A POST STARTS AT h=1, NOT h=2. The deck's upper course is only laid inside r-1 and a post
    # stands ON the rim at r, so a post beginning at 2 has its own plinth two courses below it and
    # nothing between - eight free-floating clusters that every other check passed.
    for (i, d) in posts:
        for h in range(1, tall):
            _put(w, f, pal, i, d, h, "post", axis="y")
        _put(w, f, pal, i, d, 2, pal["balustrade"], up="true", north="none", south="none",
             east="none", west="none", waterlogged="false")
    # THE STRIPED CANOPY IS A STEPPED CONE, NOT A STACK OF RINGS. Drawn as rings, each course sits
    # diagonally inside the one below it and the whole roof comes apart: a rasterised ring at
    # radius 2 and one at radius 1 share no face. Each course is a full disc, coloured by its own
    # step, so the stripes read from above AND in elevation - and every course rests on the last.
    for k in range(r + 1):
        rad = r - k
        for i in range(n):
            for d in range(n):
                if inside(i, d, rad):
                    _put(w, f, pal, i, d, tall + k, "canopy_a" if k % 2 == 0 else "canopy_b")
    _put(w, f, pal, r, r, tall + r + 1, "accent2")
    _put(w, f, pal, r, r, tall + r + 2, "glow")
    # light under the canopy, hung from the ridge
    for (i, d) in ((r - 2, r), (r + 2, r), (r, r - 2), (r, r + 2)):
        _put(w, f, pal, i, d, tall - 1, pal["light"], hanging="true", waterlogged="false")
        _put(w, f, pal, i, d, tall, "beam", axis="y")
    # THE BOARD FIRST, THEN THE SIGN ON IT. Written the other way round the sign is placed against
    # a cell that does not exist yet, `_sign` correctly refuses it, and the bandstand ships
    # nameless with nothing anywhere saying so.
    _put(w, f, pal, r, -1, 2, "board")
    _sign(w, f, pal, r, -2, 2, f.facing, [str(q.get("title") or "BANDSTAND")] +
          [str(s) for s in (q.get("lines") or [])])
    return {"kind": "sight/bandstand", "height": tall + r + 2, "footprint": [n, n]}


def _pylon(w, f, pal, q) -> dict:
    """PRISMWORKS: a signal mast. Cold, tall, regular, and lit from inside.

    The land's identity is machine architecture, so its sight piece is a piece of apparatus
    rather than an ornament: a stepped basalt mast, a signal band at each stage, a lens head, and
    four end rods off the crown. `end_rod` is the only cold spike this economy has cheap.
    """
    top = int(q.get("height") or 18)
    for h in range(top):
        rad = 1 if h < top - 6 else 0
        for i in range(-rad, rad + 1):
            for d in range(-rad, rad + 1):
                key = "plinth" if h == 0 else ("band" if h % 5 == 4 else "pier")
                _put(w, f, pal, i, d, h, key)
    # the signal bands, on the mast's four faces
    for h in range(4, top - 6, 5):
        for (i, d) in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            _put(w, f, pal, i * 2, d * 2, h, "accent")
            _put(w, f, pal, i * 2, d * 2, h - 1, "pier")
            _put(w, f, pal, i * 2, d * 2, h + 1, pal["slab"], type="bottom",
                 waterlogged="false")
    # the lens head
    for h in range(top, top + 3):
        for i in (-1, 0, 1):
            for d in (-1, 0, 1):
                _put(w, f, pal, i, d, h, "accent" if (i or d) else "glow")
    for i in (-1, 0, 1):
        for d in (-1, 0, 1):
            if abs(i) + abs(d) == 1:
                _put(w, f, pal, i, d, top + 3, "accent2")
    _put(w, f, pal, 0, 0, top + 3, "accent2")
    _put(w, f, pal, 0, 0, top + 4, "glow")
    for (i, d) in ((-2, 0), (2, 0), (0, -2), (0, 2)):
        _put(w, f, pal, i, d, top + 1, pal.get("rod", "end_rod"), facing="up")
    # the base: a broad plinth so a 3-wide mast does not read as a stick
    for i in range(-3, 4):
        for d in range(-3, 4):
            if abs(i) + abs(d) <= 4 and (abs(i) > 1 or abs(d) > 1):
                _put(w, f, pal, i, d, 0, "plinth")
                if abs(i) + abs(d) <= 2:
                    _put(w, f, pal, i, d, 1, "band")
    _put(w, f, pal, 0, -2, 1, "pier")
    _put(w, f, pal, 0, -2, 2, "pier")
    _sign(w, f, pal, 0, -3, 2, f.facing, [str(q.get("title") or "PYLON")] +
          [str(s) for s in (q.get("lines") or [])])
    # THE FOOT LAMPS HANG OFF THE LOWEST SIGNAL BRACKET, NOT OFF THE CORNERS. At the corners they
    # are two cells clear of a mast whose radius is one, so each lamp and its own cap came out as
    # a free-floating pair - eight of them, in a design with no placement problem and a clean bill
    # of materials. A bracket at (+-2, 0) touches the mast; a corner at (+-2, +-2) does not.
    for (i, d) in ((-2, 0), (2, 0), (0, -2), (0, 2)):
        _put(w, f, pal, i, d, 2, pal["light"], hanging="true", waterlogged="false")
    return {"kind": "sight/pylon", "height": top + 4, "footprint": [7, 7]}


def _ore_cart(w, f, pal, q) -> dict:
    """FRONTIER, small: a tipped ore cart on a stub of track, and its spoil.

    A prop earns its place by being a THING THAT HAPPENED rather than an ornament: a length of
    sleepered rail running out of nothing, a cart at the end of it, and the heap it dropped.
    """
    length = max(5, int(q.get("length", 9)))
    for d in range(length):
        for i in (-1, 0, 1):
            _put(w, f, pal, i, d, 0, "plinth" if i else "beam", **({} if i else {"axis": _axis_of(f, "i")}))
        _put(w, f, pal, 0, d, 1, "rail", shape="north_south" if f.du else "east_west",
             waterlogged="false")
    # THE CART IS A RIM AND A HEAP, NOT A BOX. A dark crate on a dark sleeper bed reads as a
    # crate; what says ORE CART is the pale lip round the top and the load standing proud of it,
    # because those are the two things the eye can separate from the body at any distance.
    d0 = length - 3
    for i in (-1, 0, 1):
        for d in range(d0, d0 + 3):
            for h in (2, 3):
                if i or d in (d0, d0 + 2):
                    _put(w, f, pal, i, d, h, "roof")
            if i or d != d0 + 1:
                _put(w, f, pal, i, d, 4, "band")           # the rim
    _put(w, f, pal, 0, d0 + 1, 2, "worn")
    _put(w, f, pal, 0, d0 + 1, 3, "worn")
    _put(w, f, pal, 0, d0 + 1, 4, "worn")                  # the load, heaped over the rim
    # the spoil heap beside it
    for (i, d, h) in ((2, d0, 0), (2, d0 + 1, 0), (3, d0 + 1, 0), (2, d0 + 2, 0),
                      (2, d0 + 1, 1)):
        _put(w, f, pal, i, d, h, "worn")
    # a lamp on a post, so the prop is visible at night and reads as a place
    for h in range(4):
        _put(w, f, pal, -3, 1, h, "post", axis="y")
    _put(w, f, pal, -3, 1, 4, "beam", axis=_axis_of(f, "i"))
    _put(w, f, pal, -3, 1, 3, pal["light"], hanging="true", waterlogged="false")
    _put(w, f, pal, -3, 0, 3, "board")
    _sign(w, f, pal, -3, -1, 3, f.facing, [str(q.get("title") or "ORE ROAD")] +
          [str(s) for s in (q.get("lines") or [])])
    return {"kind": "sight/ore_cart", "height": 5, "footprint": [7, length]}


def _bunting(w, f, pal, q) -> dict:
    """MIDWAY, small: a run of masts with pennants strung between them.

    Bunting is the cheapest thing in this document and the one that most says FAIR. It is drawn
    as a run because a single string is washing: `span` masts, a strung line at `height`, and a
    trapdoor pennant hanging off each course of it.
    """
    span = max(2, int(q.get("span", 3)))
    step = max(6, int(q.get("step", 8)))
    height = max(5, int(q.get("height") or 6))
    masts = 0
    for k in range(span + 1):
        d = k * step
        for h in range(height):
            _put(w, f, pal, 0, d, h, "post", axis="y")
        _put(w, f, pal, 0, d, height, "accent" if k % 2 else "accent2")
        _put(w, f, pal, 0, d, height + 1, pal["pier_slab"], type="bottom", waterlogged="false")
        _put(w, f, pal, 0, d, height - 1, pal["light"], hanging="true", waterlogged="false")
        masts += 1
    # THE LINE ITSELF SAGS, AND THE STEP IN THE SAG HAS TO BE FILLED. A dead-level string is a
    # beam; one course of droop over each bay is what tells the eye it is a rope with flags on it.
    # But two cells one course apart and one cell along share only an EDGE, so drawn as a bare
    # step the whole sagging run comes away from its own masts - eight cells of fence and bunting
    # hanging in mid air, in a design that audits clean and reports no placement problem at all.
    for k in range(span):
        prev = 0
        for j in range(1, step):
            d = k * step + j
            sag = 1 if step // 4 <= j <= step - step // 4 else 0
            h = height - sag
            for hh in range(h, height - min(sag, prev) + 1):
                _put(w, f, pal, 0, d, hh, pal["fence"], waterlogged="false")
            if j % 2 == 0:
                _put(w, f, pal, 0, d, h - 1, pal["shutter"], facing=f.facing, half="top",
                     open="false", powered="false", waterlogged="false")
            prev = sag
    return {"kind": "sight/bunting", "height": height + 1, "footprint": [1, span * step + 1],
            "masts": masts}


def _lens(w, f, pal, q) -> dict:
    """PRISMWORKS, small: a lens frame on a plinth - apparatus left standing in the open.

    A ring you can look THROUGH is the one small shape that works at distance, because what
    reads is the hole rather than the mass. Regularity and openings, not damage.
    """
    r = max(2, int(q.get("radius", 3)))
    for i in range(-r - 1, r + 2):
        for d in range(-1, 2):
            _put(w, f, pal, i, d, 0, "plinth")
    for h in range(1, 3):
        for i in (-r - 1, r + 1):
            _put(w, f, pal, i, 0, h, "band")
    # A RASTERISED RING MUST BE 4-CONNECTED OR IT IS NOT A RING. Stepped round by angle, the
    # circle comes out as a set of cells that touch only at their CORNERS - it draws perfectly and
    # it is five separate pieces of masonry hanging in the air. Walking the columns and filling the
    # vertical run between each pair gives an arc every cell of which shares a face with the next.
    ring = set()
    prev = None
    for i in range(-r, r + 1):
        j = int(round(math.sqrt(max(0.0, r * r - i * i))))
        span = range(min(j, prev), max(j, prev) + 1) if prev is not None else (j,)
        for jj in span:
            ring.add((i, jj))
            ring.add((i, -jj))
        prev = j
    for (i, j) in sorted(ring):
        _put(w, f, pal, i, 0, j + r + 3, "pier")
    # THE SPOKE, AND IT IS STRUCTURE RATHER THAN DECORATION. A glowing core at the ring's centre
    # is three cells clear of the ring itself, so on its own it is one floating block; the bar it
    # sits on is what carries it, and it is also what makes a ring read as a LENS rather than as
    # a hoop.
    for i in range(-(r - 1), r):
        _put(w, f, pal, i, 0, r + 3, "accent")
    _put(w, f, pal, 0, 0, r + 3, "glow")
    for s in (-1, 1):
        _put(w, f, pal, s * (r + 1), 0, 3, "pier")
        _put(w, f, pal, s * (r + 1), 0, 4, pal["light"], hanging="false", waterlogged="false")
    # THE PLAQUE READS OUT THE WAY THE PIECE FACES, and its support is the cell BEHIND it - which
    # is at d=+1, deeper into the piece. Faced the other way it hangs on the empty cell in front
    # of the plinth and is refused.
    _put(w, f, pal, 0, 1, 1, "band")
    _sign(w, f, pal, 0, 0, 1, f.facing, [str(q.get("title") or "ARRAY LENS")] +
          [str(s) for s in (q.get("lines") or [])])
    return {"kind": "sight/lens", "height": 2 * r + 4, "footprint": [2 * r + 3, 3]}


_MOTIFS = {"water_tower": _water_tower, "bandstand": _bandstand, "pylon": _pylon,
           "ore_cart": _ore_cart, "bunting": _bunting, "lens": _lens}


def _sight(w, f, pal, p) -> dict:
    q = {**SIGHT, **p}
    motif = q.get("motif")
    if motif not in _MOTIFS:
        raise ValueError(f"unknown sight motif {motif!r}; have {sorted(_MOTIFS)}")
    return _MOTIFS[motif](w, f, pal, q)


# --------------------------------------------------------------------------- pergola + stamp

PERGOLA = {
    "size": [46, 24],      # [dV, dU] of the frame it carries
    "top": 22,             # the course the piers reach; the load sits at top + 1
    "pier_v": None,        # [V offsets] along the long axis where a pier pair stands
    "pier_u": [1, 21],     # the two U offsets the piers stand under (2 cells each)
}


def _putvu(w, f, pal, v, u, h, key, **props):
    """A block at a park-coordinate OFFSET from the piece's own corner, never through `i`/`d`.

    `_Frame` is right for a thing with a FRONT; a pergola and a stamped litematic are neither -
    they are axis-aligned rectangles in V and U, and routing them through a frontage axis is how
    a 46-long lattice comes out 46 wide. `at` is the near corner and (v, u) count from it.
    """
    name = pal.get(key, key) if pal else key
    w.put(f.ax + f.v + int(v), f.ay + int(h), f.az + f.u + int(u), name, **_state(name, props))


def _pergola(w, f, pal, p) -> dict:
    """THE PIERS AND STAIRS UNDER A HANGING SET PIECE, AND NOTHING ELSE.

    `out/park_final/artifacts/Sky Lift Sloth.litematic` is 5,300 blocks - a brown-wool sloth slung
    under a 46x22 spruce lattice - and it used to hang from the Sky Lift's arch. That arch is
    gone: the Sky Lift is the wheel alone now, so the best-reading kind of object this repo has
    (*a body slung UNDER a line*) has been homeless. This is its home.

    **THE PIERS GO UNDER CELLS THAT ACTUALLY EXIST.** The lattice is a grid: its two long rails
    at local U1-2 and U21-22 run the full 46, and everything between them is open. A pier under a
    hole carries nothing and reads as a post standing beside a sculpture - so the pier columns are
    a parameter and `tests/test_park_frontage.py` asserts every pier top is directly under a solid
    cell of the piece it carries.
    """
    q = {**PERGOLA, **p}
    dv, du = (int(a) for a in q["size"])
    top = int(q["top"])
    pv = q.get("pier_v") or [0, dv // 3, 2 * dv // 3, dv - 2]
    pu = [int(a) for a in q["pier_u"]]
    piers = []
    # THE VERTICAL FACE OF A PIER IS A LADDER OF THREE MATERIALS, not one column of log. A 22-course
    # post in one block is a stick; a plinth, a shaft banded every fifth course and a capital is a
    # pier, and it is the same regularity rule the void tower settled.
    for v0 in pv:
        for u0 in pu:
            for a in (0, 1):
                for b in (0, 1):
                    vv, uu = v0 + a, u0 + b
                    _putvu(w, f, pal, vv, uu, 0, "plinth")
                    for h in range(1, top + 1):
                        key = "band" if (h % 5 == 0 and h < top - 1) else (
                            "post" if (a + b) % 2 == 0 else "pier")
                        _putvu(w, f, pal, vv, uu, h, key, axis="y")
                    _putvu(w, f, pal, vv, uu, top, "band")
                    piers.append((vv, uu))
            # THE CAPITAL. A frame landing on four bare posts reads as a frame that fell there;
            # a corbel course under it reads as a frame something was built to carry.
            for k in (-1, 2):
                for b in (0, 1):
                    _putvu(w, f, pal, v0 + k, u0 + b, top, pal["stair"],
                           facing="south" if k < 0 else "north", half="top",
                           shape="straight", waterlogged="false")
    lamps = 0
    for v0 in pv:
        for u0 in pu:
            inner = u0 + (2 if u0 < du // 2 else -1)
            _putvu(w, f, pal, v0, inner, top - 2, "band")
            _putvu(w, f, pal, v0, inner, top - 3, pal["light"], hanging="true",
                   waterlogged="false")
            lamps += 1
    return {"kind": "pergola", "piers": sorted(set(piers)), "top": top, "lamps": lamps,
            "pier_v": list(pv), "pier_u": pu, "size": [dv, du]}


STAMP = {"source": None, "lift": 0, "keep": None}


def _stamp(w, f, p) -> dict:
    """Copy an existing litematic in at this piece's corner, block state for block state.

    **STATE IS CARRIED, NEVER RE-DERIVED.** A stair's `facing`, a rail's `shape` and a trapdoor's
    `half` are decisions, and this repo's renderer draws a wrong one identically to a right one.
    """
    q = {**STAMP, **p}
    src = q.get("source")
    if not src:
        raise ValueError("stamp needs params.source = a .litematic path")
    m = schem.load(src)
    lift = int(q.get("lift", 0))
    names = [nbt.state_name(e).split(":")[-1] for e in m.palette]
    props = [nbt.state_props(e) for e in m.palette]
    n = 0
    ys, zs, xs = m.solid().nonzero()
    for y, z, x in zip(ys.tolist(), zs.tolist(), xs.tolist()):
        idx = int(m.ids[y, z, x])
        # THE SOURCE'S OWN AXES, NOT THIS PIECE'S FRONTAGE. A litematic's x is V and its z is U,
        # exactly as this park's canvases are, so a stamp is a translation and nothing else -
        # routed through `i`/`d` a 46-long lattice comes out 46 wide and the piers miss it.
        w.put(f.ax + f.v + int(x), f.ay + int(y) + lift, f.az + f.u + int(z),
              names[idx], **{k: str(v) for k, v in props[idx].items()})
        n += 1
    sy, sz, sx = m.ids.shape
    return {"kind": "stamp", "source": src, "cells": n, "lift": lift,
            "size": [int(sx), int(sy), int(sz)]}


# --------------------------------------------------------------------------- build

_KINDS = {"marquee": _marquee, "portal": _portal, "queue": _queue, "sight": _sight,
          "pergola": _pergola}


def build(cfg: dict, donors=None) -> Canvas:
    p = {**PARK_FRONTAGE, **cfg}
    land = p.get("land")
    if land not in PAL:
        raise ValueError(f"park_frontage needs params.land in {sorted(PAL)}, got {land!r}")
    pieces = p.get("pieces")
    if not pieces:
        raise ValueError("park_frontage needs params.pieces = [{kind, at, ...}, ...]")
    anchor = tuple(int(a) for a in p["anchor"])

    w = World()
    w.refused_signs = []
    built = []
    for k, spec in enumerate(pieces):
        q = {**PIECE, "seed": int(p.get("seed", 0)) + k, **spec}
        if not q.get("at"):
            raise ValueError(f"piece {k} ({q.get('kind')}) has no `at`")
        pal = PAL[q.get("land") or land]
        f = _Frame(q["at"], q["facing"], anchor)
        kind = q.get("kind")
        if kind == "stamp":
            meta = _stamp(w, f, q)
        elif kind in _KINDS:
            meta = _KINDS[kind](w, f, pal, q)
        else:
            raise ValueError(f"unknown park_frontage kind {kind!r}; "
                             f"have {sorted(list(_KINDS) + ['stamp'])}")
        meta = {**meta, "at": [int(q['at'][0]), int(q['at'][1])], "facing": q["facing"],
                "land": q.get("land") or land, "name": q.get("name") or meta.get("title") or kind}
        built.append(meta)

    # EVERY SIGN LINE IS FIFTEEN CHARACTERS, AND THE CHECK IS HERE RATHER THAN IN A TEST. A line
    # that clips only shows in a screenshot taken after the thing is placed, which is the most
    # expensive place in this whole pipeline to find a typo.
    for pos, t in w.signs.items():
        for line in list(t["front"]) + list(t["back"]):
            if len(line) > SIGN_WIDTH:
                raise ValueError(f"sign line {line!r} at {pos} is {len(line)} chars, "
                                 f"over the {SIGN_WIDTH} a sign can show")

    lowest = min(y for _x, y, _z in w.cells)
    if lowest < anchor[1]:
        raise ValueError(
            f"park_frontage emitted a cell at Y{lowest}, below the build plane Y{anchor[1]}. "
            f"Y{anchor[1] - 1} is the ground layer's own surface - every path, plaza, verge and "
            f"spur in the park is that one course, and this module may not write into it.")

    return w.canvas({
        "kind": "park_frontage",
        "land": land,
        "pieces": built,
        "piece_count": len(built),
        "signs": len(w.signs),
        "refused_signs": list(w.refused_signs),
        "contract": "everything in front of and between the park's attractions: a name board on "
                    "every one, queues at the rides, entrance and exit thresholds, and sight "
                    "pieces in the measured empty bands - none of it below the build plane, and "
                    "nothing over a paved column below head height",
        "unverified": [
            "not placed in game: every judgement here is off the shipped litematics and the "
            "repo's own renderer, which draws a fence, a wall and an end rod as full cubes",
        ],
    })
