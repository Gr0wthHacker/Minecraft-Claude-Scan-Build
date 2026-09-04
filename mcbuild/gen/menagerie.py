"""A walk-through farmyard zoo that fills its whole lot: barn, pond, meadow, aviary, lookout.

Jack, on the first version: "the zoo on the park is tiny and doesnt look good, we want to use the
full space and make it much more visually interesting."

**HE WAS RIGHT ON BOTH COUNTS AND BOTH ARE MEASURED.** The first build was four IDENTICAL 7x10
fenced squares in one row - 455 columns of a 1,014-column lot, and **three courses tall at its
highest point**. `tools/park_lots.py` calls this lot `frontier|midway / exit-observation,
V128-153 x U173-211`: 26 deep by 39 wide, bounded by a park walk on all four sides. The zoo was
using 45% of it and reading as a fence lying on a lawn.

Two rules this repo already wrote, neither of which the row obeyed:

  * **ARCHITECTURE BELOW ~6 COURSES DISSOLVES INTO GROUND NOISE** (`gen/plateau.py`, the Frontier
    ruin fragments). Four 3-tall pens on moss are ground noise.
  * **A ROUTE WITH SOMEWHERE TO STAND ON IT IS SOMEWHERE TO BE** (`gen/claimrow.py`). You walked
    PAST the old pens along one edge. There was nothing to walk INTO.

So the rebuild is not a bigger row. It is a **T of paths with four different habitats round it**,
because four identical rectangles read as one rectangle however large you draw them - the same
finding `gen/casino.py` recorded when eighteen game rooms turned out to be two games wearing four
names. Each quadrant is a DIFFERENT KIND OF THING:

    THE BARN     west/front   a red timber building you WALK THROUGH, four railed stalls off a
                              cross aisle, a stair-slope gable roof
    THE POND     east/front   a SUNKEN water body - bed a course under the plate, so the surface
                              lies flush with your feet and there is no kerb to step over
    THE MEADOW   west/back    open paddock: trees, a drinking trough, an open-fronted shelter
    THE AVIARY   east/back    a CAGE of fence bars eleven courses tall under a lattice roof, with
                              a cupola on top - the landmark, and the tallest thing on the lot
    THE LOOKOUT  the axis     a raised deck that terminates the spine and looks back over it

**THE SKYLINE IS THE POINT.** The aviary's cupola, the barn's ridge, the gate towers and the
lookout's canopy all stand at different heights, and the pond is deliberately left open and low -
so the composition has a front, a middle and a back from the avenue instead of one flat plane of
fence.

**THE PENS ARE STILL INFRASTRUCTURE, NOT LIVESTOCK**, exactly as the first version said: a
litematic places BLOCKS and cannot place a living mob, and this generator does not pretend to.
Every enclosure ships empty, gated and signed with what to lead in and with what, and stocking
them is Jack's job in world. `blocks.exists("sheep")` is not a question the block registry can
answer, and a design that implied otherwise would be lying in its own sidecar.

GEOMETRY is `gen/park.py`'s `_Frame`, unchanged:

    at       the FRONT-LEFT floor corner (world x, y, z), on the STANDING course
    facing   the direction the frontage looks out - a visitor approaches from +facing
    i        left to right across the frontage       d   from the frontage INTO the lot

THE THREE STREET LAMPS IN FRONT OF THIS LOT ARE NOT OURS. `Park Ways` stands its own lamp
standards on the row in front of it (V129 at U175, U192, U209, Y203-206) and one of them is dead
on the lot's midline. The design therefore starts at V130 and leaves that row as the frontage
verge - the lamps become this zoo's entrance lighting for nothing, and the gateway is not built
round a post. Sited one row further forward, the middle lamp would have stood in the doorway.
"""
from __future__ import annotations

from .canvas import Canvas, hash01
from .park import LANDS, SIGN_WIDTH, _STEP, _Frame, _plaza_tree, _sign
from .streetfurniture import _d_dir, _fence_props, _i_dir, _off_dir, _slab, _stair
from .vertical import Ctx, World

MENAGERIE = {
    "under": None,
    "at": None,                  # world (x, y, z): the frontage's FRONT-LEFT floor corner
    "facing": "west",
    "land": "midway",
    "title": "CLAIM LAKE",
    "subtitle": "MENAGERIE",
    "width": 39,                 # across the frontage - the lot is 39 wide (U173..U211)
    "depth": 24,                 # into the lot - V130..V153, the lamp row left as verge
    "spine": 5,                  # the main path a visitor walks in on
    "seed": 11,
    "sign": True,
}
DEFAULTS = MENAGERIE

#: WHAT EACH ENCLOSURE IS FOR, and what to lead in with. A fenced square of moss with nothing in
#: it is not self-explanatory, so every pen says on its own gate what it wants - the sign is
#: honest about what the pen NEEDS rather than about what it has. Fifteen characters is the line.
STOCK = {
    "byre":   ("COW BYRE", "lead in: wheat"),
    "sty":    ("PIG STY", "lead in: carrot"),
    "coop":   ("CHICKEN RUN", "lead in: seeds"),
    "goats":  ("GOAT PEN", "lead in: wheat"),
    "meadow": ("SHEEP MEADOW", "lead in: wheat"),
    "pond":   ("THE DUCK POND", "fish, turtles"),
    "aviary": ("THE AVIARY", "parrots, hens"),
}

_FLOWERS = ("dandelion", "poppy", "oxeye_daisy", "cornflower")

#: Ground cover that may be walked through, and therefore may be swept out of a doorway. A plant
#: does not BLOCK a gate - the audit is right that it is passable - but a tuft standing in the one
#: cell you step through reads as an obstruction, and this repo has twice sited a prop in the very
#: way the design exists to carry. `gen/claimrow.py`: the way refuses, rather than the hand
#: remembering.
_GROUND_COVER = set(_FLOWERS) | {"short_grass", "fern", "moss_carpet", "azalea",
                                 "flowering_azalea", "lily_pad"}


# --------------------------------------------------------------------------- small helpers

def _free(w, f, i, d, h):
    return not w.has(*f.at(i, d, h))


def _put_free(w, f, i, d, h, block, **props):
    """Place only into an empty cell, so planting laid over a post does not eat the post."""
    if _free(w, f, i, d, h):
        w.put(*f.at(i, d, h), block, **props)
        return True
    return False


def _ring_of(i0, i1, d0, d1):
    """The perimeter cells of a box, as a set."""
    out = set()
    for i in range(i0, i1 + 1):
        out.add((i, d0))
        out.add((i, d1))
    for d in range(d0, d1 + 1):
        out.add((i0, d))
        out.add((i1, d))
    return out


def _rail(w, f, pal, ring, gates=(), posts=(), height=1, light=(), base=0):
    """A fence run built as ONE SET so `_fence_props` connects it, with the gates left OUT.

    A gate is not a fence cell that later gets replaced - build the ring and swap afterwards and
    the neighbouring fences still believe they connect to a fence. The gate cells are removed
    from the set before a single connection is computed, which is the same reason `park._walls`
    leaves its openings empty rather than punching them.
    """
    gate_at = {(i, d) for (i, d, _fc) in gates}
    post_set = set(posts)
    fence = set(ring) - gate_at - post_set
    known = fence | post_set                       # a fence connects to a solid post too
    for (i, d) in sorted(post_set):
        for h in range(base, base + height + 1):
            w.put(*f.at(i, d, h), pal["post"])
    for (i, d) in sorted(fence):
        for h in range(base, base + height):
            w.put(*f.at(i, d, h), pal["fence"], **_fence_props(f, known, i, d))
    for (i, d, facing) in gates:
        w.put(*f.at(i, d, base), pal["gate"], facing=facing,
              open="false", powered="false", in_wall="false")
    for (i, d) in light:
        if (i, d) in post_set:
            w.put(*f.at(i, d, base + height + 1), pal["light"],
                  hanging="false", waterlogged="false")
    return len(fence)


def _pen_sign(w, f, pal, i, d, di, dd, lines):
    """A pen's name, on ITS OWN POST in the rail line, read from the path outside it.

    THE SUPPORT IS BUILT, NOT HOPED FOR. `park._sign` returns False when there is no block behind
    the sign and this repo has shipped four silently-refused signs that way; a pen rail is fences,
    and a fence line has no cell a board can hang on until one is put there.
    """
    for h in (0, 1):
        w.put(*f.at(i, d, h), pal["post"])
    return _sign(w, f, pal, i + di, d + dd, 1, _off_dir(f, di, dd), lines)


def _plant(w, f, i, d, seed, salt, density=0.55):
    """Ground cover on moss, in DRIFTS rather than confetti - the noise is on the drift's own
    boundary, never a per-cell threshold. `gen/thicket.py` shipped 191 blobs of which 75% were
    one or two cells the first time this repo thresholded a falloff per cell."""
    if hash01(i // 3, d // 3, seed, salt) > density:
        return 0
    roll = hash01(i, d, seed, salt + 1)
    if roll < 0.10:
        return int(_put_free(w, f, i, d, 0, _FLOWERS[int(roll * 400) % len(_FLOWERS)]))
    if roll < 0.30:
        return int(_put_free(w, f, i, d, 0, "fern"))
    if roll < 0.62:
        return int(_put_free(w, f, i, d, 0, "short_grass"))
    if roll < 0.72:
        return int(_put_free(w, f, i, d, 0, "moss_carpet"))
    return 0


def _lamp(w, f, pal, i, d, h=3):
    """A standard on the kerb: a post with the lantern STANDING on its own top face.

    `park._hang_light` needs a full block above the lamp to hang from, and nothing out on a path
    reaches that high - the first menagerie hung six lanterns off nothing and shipped six
    free-floating clusters. A lantern on a post top needs no second support at all.
    """
    for k in range(h):
        w.put(*f.at(i, d, k), pal["post"])
    w.put(*f.at(i, d, h), pal["light"], hanging="false", waterlogged="false")


def _mast(w, f, pal, i, d, h=6):
    """A pennant mast: the land's canopy colours, at the corners where the lot is otherwise flat.

    THE PENNANT IS HORIZONTALLY ADJACENT TO THE MAST, never diagonal - a flag hung off the corner
    is the ear-tip failure this repo has shipped in cloth, in leaves and in bunting.
    """
    for k in range(h):
        w.put(*f.at(i, d, k), pal["post"])
    w.put(*f.at(i + 1, d, h - 1), pal["canopy"][0])
    w.put(*f.at(i + 1, d, h - 2), pal["canopy"][1])
    w.put(*f.at(i + 2, d, h - 2), pal["canopy"][0])


def _bed(w, f, pal, ci, cd, seed):
    """A raised planting bed on paving: a kerb ring, moss inside, azalea and ferns over it."""
    n = 0
    for i in range(ci - 1, ci + 2):
        for d in range(cd - 1, cd + 2):
            if i in (ci - 1, ci + 1) or d in (cd - 1, cd + 1):
                w.put(*f.at(i, d, 0), pal["trim"])
                continue
            w.put(*f.at(i, d, 0), "moss_block")
            w.put(*f.at(i, d, 1),
                  "flowering_azalea" if hash01(i, d, seed, 9) < 0.5 else "azalea")
            n += 1
    return n


def _board(w, f, pal, i0, i1, d, lines):
    """An orientation board: two posts, a beam, and the signs hung on the beam's own front face."""
    for i in (i0, i1):
        for h in range(3):
            w.put(*f.at(i, d, h), pal["post"])
    for i in range(i0, i1 + 1):
        w.put(*f.at(i, d, 2), pal["beam"])
    ok = True
    for k, i in enumerate(range(i0 + 1, i1)):
        ok &= _sign(w, f, pal, i, d - 1, 2, f.facing, lines[k] if k < len(lines) else ["", ""])
    return ok


# --------------------------------------------------------------------------- the ground

def _ground(w, f, pal, W, D, paved):
    """The pad. A skyblock plot is VOID, so every module brings its own floor - and this one
    brings the whole lot's, because the design IS the lot now rather than a strip inside it.

    The paving takes a kerb wherever it meets something that is not paving, so the path edge is
    drawn by the LAYOUT rather than by a hand-typed list of kerb rows; move a pen and the kerb
    moves with it.
    """
    n = 0
    for i in range(W):
        for d in range(D):
            x, y, z = f.at(i, d, -1)
            if i in (0, W - 1) or d in (0, D - 1):
                w.put(x, y, z, pal["trim"])                     # the boundary course
            elif (i, d) in paved:
                edge = any((i + di, d + dd) not in paved
                           for (di, dd) in ((1, 0), (-1, 0), (0, 1), (0, -1)))
                w.put(x, y, z, pal["trim"] if edge else
                      (pal["ground"] if (x + z) % 2 == 0 else pal["path"]))
                n += 1
            else:
                w.put(x, y, z, "moss_block")
    return n


# --------------------------------------------------------------------------- the gateway

def _gateway(w, f, pal, ci, spine, title, subtitle, seed):
    """Two capped towers with a beam between them. The name goes on the BEAM'S OWN FRONT FACE, so
    the board has something to hang from - `park._sign` refuses a sign with no support and returns
    False, and four of `park.py`'s seven kinds once shipped a sign hung on a column that has an
    opening in it."""
    sp0, sp1 = ci - spine // 2, ci + spine // 2
    signed = True
    for side in (-1, 1):
        c = sp0 - 3 if side < 0 else sp1 + 3                    # tower centres, clear of the gap
        # SOLID, not a hollow ring. A 3x3 tower's only interior cell is its centre, and that is
        # exactly the cell the name board on the front face has to hang from - built hollow, the
        # sign is refused and `_sign` returns False without a word. Filling it also spares the
        # design a cavity nobody can ever see into.
        for i in range(c - 1, c + 2):
            for d in range(0, 3):
                corner = i in (c - 1, c + 1) and d in (0, 2)
                for h in range(8):
                    w.put(*f.at(i, d, h), pal["post"] if corner else pal["wall"])
        for h, blk, r in ((8, pal["canopy"][0], 1), (9, pal["canopy"][1], 0)):
            for i in range(c - r, c + r + 1):
                for d in range(1 - r, 2 + r):
                    if 0 <= d <= 2:
                        w.put(*f.at(i, d, h), blk)
        w.put(*f.at(c, 1, 10), pal["light"], hanging="false", waterlogged="false")
        # the tower's own board goes on its INNER face, read as you walk under the beam - put on
        # the front face it would replace a wall block and leave a hole in the tower.
        signed &= _sign(w, f, pal, c + 2 * side, 1, 4, _i_dir(f, side),
                        ["THE ZOO", "walk in" if side > 0 else "free entry"])
    # the beam over the gap - one cell deep, so the sign course in front of it has a support
    for i in range(sp0 - 2, sp1 + 3):
        w.put(*f.at(i, 1, 6), pal["beam"])
        w.put(*f.at(i, 1, 7), pal["canopy"][(i + seed) % 2])
        _slab(w, f, i, 0, 7, pal["slab"], "bottom")             # the board's own cornice
    for k, i in enumerate(range(sp0, sp1 + 1)):
        lines = [title[:SIGN_WIDTH], subtitle[:SIGN_WIDTH]] if k == spine // 2 else ["", ""]
        signed &= _sign(w, f, pal, i, 0, 6, f.facing, lines)
    return signed


# --------------------------------------------------------------------------- the barn

def _barn(w, f, pal, i0, i1, d0, d1, seed):
    """A RED timber barn you walk through: a cross aisle, four railed stalls, a stair roof.

    THE ROOF IS STAIRS, not a stack of full blocks. Against the download corpus this repo places
    stairs at a seventh of the rate outside builders do, and a 1:1 stair slope is what makes a
    roof read as a roof from the ground rather than as a stepped wall. Every tread leans UPHILL,
    toward the ridge - `streetfurniture._stair`'s contract is that `facing` is the tall side, and
    our renderer draws both directions identically, so this is asserted rather than eyeballed.

    THE THREE DOORWAYS ARE LEFT EMPTY BY THE WALL LOOP. Building the ring and cutting the holes
    afterwards repaints cells that already exist - the void tower's crenellations shipped as a
    plain drum for exactly that reason and nothing about the code looked wrong.
    """
    wall, frame, eaves = "red_wool", pal["post"], 5
    aisle_d0, aisle_d1 = d0 + 4, d0 + 5                          # the aisle across the barn
    aisle_i0, aisle_i1 = i0 + 6, i0 + 8                          # ...and the one down it
    ridge = (d0 + d1) // 2
    rise = (d1 - d0) // 2

    holes = set()
    for d in range(aisle_d0, aisle_d1 + 1):                      # the gable-end door, on the spine
        holes |= {(i1, d, h) for h in range(4)}
    for i in range(aisle_i0, aisle_i1 + 1):                      # front and back doors
        holes |= {(i, d0, h) for h in range(4)} | {(i, d1, h) for h in range(4)}

    for i in range(i0, i1 + 1):
        for d in range(d0, d1 + 1):
            if not (i in (i0, i1) or d in (d0, d1)):
                continue
            post = (i - i0) % 4 == 0 or (d - d0) % 4 == 0
            for h in range(eaves):
                if (i, d, h) in holes:
                    continue
                w.put(*f.at(i, d, h), frame if (post and h < eaves - 1) or h == 0 else wall)

    # ---- the gable ends, closed course by course under the roof line...
    for i in (i0, i1):
        for k in range(1, rise + 1):
            for d in range(d0 + k, d1 - k + 1):
                w.put(*f.at(i, d, eaves + k - 1), wall)
    # ...with a loft opening in each, shuttered with OPEN TRAPDOORS - the vertical panel the
    # corpus says this repo has never once placed, and the one detail that says hay loft.
    for i in (i0, i1):
        face = _i_dir(f, -1) if i == i0 else _i_dir(f, 1)
        for d in (ridge - 1, ridge, ridge + 1):
            w.put(*f.at(i, d, eaves + 1), f"{pal['wood']}_trapdoor", facing=face,
                  half="bottom", open="true", powered="false", waterlogged="false")

    # ---- the roof, and one cell of eave oversailing the wall on both long sides
    stair = f"{pal['wood']}_stairs"
    up_in, up_out = _d_dir(f, 1), _d_dir(f, -1)
    for i in range(i0, i1 + 1):
        _stair(w, f, i, d0 - 1, eaves, stair, up_in)
        _stair(w, f, i, d1 + 1, eaves, stair, up_out)
        for k in range(0, rise):
            _stair(w, f, i, d0 + k, eaves + k, stair, up_in)
            _stair(w, f, i, d1 - k, eaves + k, stair, up_out)
        _slab(w, f, i, ridge, eaves + rise, f"{pal['wood']}_slab", "bottom")

    # ---- the floor: a beaten aisle and bedded stalls
    for i in range(i0 + 1, i1):
        for d in range(d0 + 1, d1):
            aisle = aisle_d0 <= d <= aisle_d1 or aisle_i0 <= i <= aisle_i1
            w.put(*f.at(i, d, -1), pal["path"] if aisle else "moss_block")

    # ---- four stalls, each railed off the aisle with its own gate and its own sign
    stalls = [(i0 + 1, aisle_i0 - 1, d0 + 1, aisle_d0 - 1, "byre"),
              (aisle_i1 + 1, i1 - 1, d0 + 1, aisle_d0 - 1, "sty"),
              (i0 + 1, aisle_i0 - 1, aisle_d1 + 1, d1 - 1, "coop"),
              (aisle_i1 + 1, i1 - 1, aisle_d1 + 1, d1 - 1, "goats")]
    signed, hay = True, 0
    for (a, b, c, e, kind) in stalls:
        north = c < aisle_d0
        side_d = e if north else c                               # the stall's own aisle-side row
        run = [(i, side_d) for i in range(a, b + 1)]
        gi = (a + b) // 2
        board = gi + 2 if gi + 2 <= b else a
        _rail(w, f, pal, run, gates=[(gi, side_d, _d_dir(f, 1))],
              posts=[(a, side_d), (b, side_d), (board, side_d)], height=1)
        w.put(*f.at(a, (c + e) // 2 if north else c + 1, -1), "hay_block", axis="y")
        hay += 1
        # THE BOARD HANGS ON ITS OWN POST IN THE RAIL. Written over the gate it was refused four
        # times in silence - a fence gate occupies one course and there is nothing above it.
        signed &= _pen_sign(w, f, pal, board, side_d, 0, 1 if north else -1,
                            list(STOCK[kind]))
    # ---- TIE BEAMS WALL TO WALL, and the lanterns hung under them. Written as a single beam
    # cell over each lamp, the four of them shipped as two free-floating clusters: the barn is
    # open from the floor to the wall plate, so a block at plate height touches nothing unless
    # it actually spans. A tie beam is what a barn has there anyway.
    for d in (d0 + 2, ridge, d1 - 2):
        for i in range(i0, i1 + 1):
            w.put(*f.at(i, d, eaves - 1), pal["beam"])
        for i in (aisle_i0 - 2, aisle_i1 + 2):
            w.put(*f.at(i, d, eaves - 2), pal["light"], hanging="true", waterlogged="false")
    # ...and the building's own name, on the WALL rather than in front of a doorway: a sign
    # needs a block behind it, and a door is the one column that has none.
    signed &= _sign(w, f, pal, aisle_i0 - 2, d0 - 1, 4, f.facing, ["THE BARN", "walk through"])
    signed &= _sign(w, f, pal, i1 + 1, ridge - 2, 4, _i_dir(f, 1), ["THE BARN", "cows & pigs"])
    return {"stalls": len(stalls), "hay": hay, "signed": bool(signed)}


# --------------------------------------------------------------------------- the pond

def _pond(w, f, pal, i0, i1, d0, d1, seed):
    """A SUNKEN pond: the bed a course under the plate, so the water lies flush with the ground.

    `park._plaza_pool` raises its water into the standing course behind a kerb, which is right for
    a formal basin and wrong for a pond - you would step over a rim to reach it. Here the plate is
    the wall: every non-water cell of the pad is already solid at the water's own course, so the
    only thing that has to be added is the bed beneath, and the body is enclosed BY CONSTRUCTION.

    IT MUST BE BOTH BEDDED AND ENCLOSED or it is not still water in six months. Every water cell
    gets a bed under it and a wall wherever it meets a cell nothing has filled.
    """
    ci, cd = (i0 + i1) / 2, (d0 + d1) / 2
    ri, rd = (i1 - i0) / 2 - 1.2, (d1 - d0) / 2 - 1.2
    water = {(i, d) for i in range(i0, i1 + 1) for d in range(d0, d1 + 1)
             if ((i - ci) / ri) ** 2 + ((d - cd) / rd) ** 2
             <= 0.84 + 0.34 * hash01(i // 2, d // 2, seed, 3)}
    island = {(i, d) for (i, d) in water if abs(i - (ci + 3)) <= 1 and abs(d - cd) <= 1}
    water -= island

    for (i, d) in sorted(water):
        w.put(*f.at(i, d, -1), "water", level="0")
    for (i, d) in sorted(island):
        w.put(*f.at(i, d, -1), "mossy_cobblestone")
    isle_c = (int(round(ci + 3)), int(round(cd)))
    if isle_c in island:
        w.put(*f.at(*isle_c, -1), "moss_block")      # A TREE ROOTS IN THE DIRT FAMILY AND NOWHERE
                                                      # ELSE, and mossy cobble is not in it.
    for (i, d) in sorted(water | island):
        w.put(*f.at(i, d, -2), "stone")                          # the bed
    for (i, d) in sorted(water):
        for (di, dd) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if (i + di, d + dd) not in water and _free(w, f, i + di, d + dd, -1):
                w.put(*f.at(i + di, d + dd, -1), pal["ground"])  # the wall

    # ---- the shore: sand and gravel against the water, drifted moss beyond
    shore = 0
    for i in range(i0, i1 + 1):
        for d in range(d0, d1 + 1):
            if (i, d) in water or (i, d) in island:
                continue
            near = any((i + di, d + dd) in water
                       for di in (-1, 0, 1) for dd in (-1, 0, 1))
            if not near:
                _plant(w, f, i, d, seed, 40)
                continue
            r = hash01(i, d, seed, 4)
            w.put(*f.at(i, d, -1),
                  "sand" if r < 0.45 else ("gravel" if r < 0.70 else "mossy_cobblestone"))
            shore += 1

    # ---- lilies, reeds, and a rock the herons would use. A lily pad carries NO properties at
    # all in 26.2 - the taproot's own note, and the reason nothing is passed here.
    lily = reed = 0
    for (i, d) in sorted(water):
        if hash01(i, d, seed, 5) < 0.14 and _free(w, f, i, d, 0):
            w.put(*f.at(i, d, 0), "lily_pad")
            lily += 1
    for i in range(i0, i1 + 1):
        for d in range(d0, d1 + 1):
            if w.name(*f.at(i, d, -1)) != "sand" or not _free(w, f, i, d, 0):
                continue
            if hash01(i, d, seed, 6) < 0.22:
                for h in range(0, 1 + int(hash01(i, d, seed, 7) > 0.5)):
                    w.put(*f.at(i, d, h), "sugar_cane", age="0")
                reed += 1
    for (i, d) in sorted(island):
        if _free(w, f, i, d, 0) and hash01(i, d, seed, 8) < 0.7:
            w.put(*f.at(i, d, 0), "mossy_cobblestone")
    for (i, d) in sorted(island)[:1]:
        if _free(w, f, i, d, 1):
            w.put(*f.at(i, d, 1), pal["light"], hanging="false", waterlogged="false")
    return {"water": len(water), "shore": shore, "lily": lily, "reeds": reed}


def _jetty(w, f, pal, i, d0, d1, canopy=True):
    """A plank walk out over the pond on its own piles, railed with open trapdoors.

    THE PILES GO IN BEFORE THE DECK and only where the deck actually runs, so no plank ever stands
    over nothing - a deck laid first and propped afterwards is how a walkway ships as a
    free-floating cluster.
    """
    laid = 0
    for d in range(d0, d1 + 1):
        for k in (-1, 0, 1):
            w.put(*f.at(i + k, d, -1), pal["beam"])
            laid += 1
        for k in (-1, 1):
            w.put(*f.at(i + k, d, 0), f"{pal['wood']}_trapdoor",
                  facing=_i_dir(f, 1) if k > 0 else _i_dir(f, -1),
                  half="bottom", open="true", powered="false", waterlogged="false")
    if canopy:
        for (k, d) in ((-1, d0), (1, d0), (-1, d1), (1, d1)):
            for h in range(0, 3):
                w.put(*f.at(i + k, d, h), pal["post"])
        for k in (-1, 0, 1):
            for d in range(d0, d1 + 1):
                w.put(*f.at(i + k, d, 3), pal["canopy"][(k + d) % 2])
        w.put(*f.at(i, d0, 2), pal["light"], hanging="true", waterlogged="false")
    return laid


# --------------------------------------------------------------------------- the meadow

def _meadow(w, f, pal, land, i0, i1, d0, d1, seed):
    """Open paddock: two trees, a drinking trough, an open-fronted shelter, drifted planting."""
    si, sd = i0 + 1, d0 + 1
    for (di, dd) in ((0, 0), (3, 0), (0, 2), (3, 2)):
        for h in range(3):
            w.put(*f.at(si + di, sd + dd, h), pal["post"])
    for di in range(4):
        for dd in range(3):
            w.put(*f.at(si + di, sd + dd, 3), pal["canopy"][(di + dd) % 2])
        _stair(w, f, si + di, sd + 3, 3, pal["stair"], _d_dir(f, -1))
    w.put(*f.at(si + 1, sd + 1, -1), "hay_block", axis="y")

    # the trough: a filled cauldron between two kerb stones, which needs no enclosure of its own
    ti, td = i1 - 3, (d0 + d1) // 2
    for k in (-1, 1):
        w.put(*f.at(ti + k, td, 0), pal["trim"])
    w.put(*f.at(ti, td, 0), "water_cauldron", level="3")

    _plaza_tree(w, f, pal, land, i0 + 4, d1 - 1, seed)
    _plaza_tree(w, f, pal, land, i1 - 5, d0 + 2, seed + 1)
    n = 0
    for i in range(i0, i1 + 1):
        for d in range(d0, d1 + 1):
            n += _plant(w, f, i, d, seed, 20, density=0.72)
    return {"trees": 2, "planting": n}


# --------------------------------------------------------------------------- the aviary

def _aviary(w, f, pal, land, i0, i1, d0, d1, seed, door_i):
    """A CAGE, and the tallest thing on the lot: bars eleven courses under a lattice roof, a
    cupola on top, a tree and two perches inside.

    A cage is the one enclosure whose whole identity is a VERTICAL PLANE OF THIN MEMBERS, which is
    a shape voxels render natively - the same reason `gen/bat.py` and the sky bird work where
    eight mammals did not. The bars are the land's own fence, so the aviary costs nothing but
    height, and height is the thing this lot had none of.
    """
    bars, tall = pal["fence"], 11
    ring = _ring_of(i0, i1, d0, d1)
    full = {(i, d) for i in range(i0, i1 + 1) for d in range(d0, d1 + 1)}
    posts = {(i, d) for (i, d) in ring
             if (i in (i0, i1) and (d - d0) % 3 == 0)
             or (d in (d0, d1) and (i - i0) % 4 == 0)
             or (i in (i0, i1) and d in (d0, d1))}
    door = {(door_i - 1, d0), (door_i, d0), (door_i + 1, d0)}
    posts -= door
    ring_bars = ring - posts - door

    for (i, d) in sorted(ring):
        w.put(*f.at(i, d, 0), pal["trim"])
    # THE FRAME IS THE LAND'S WALL COLOUR, NOT ITS POST. Built in oak on oak the whole cage read
    # as one brown crate at every bearing - measured across families, white_wool 236 against
    # oak_fence 134 against polished_blackstone_bricks 45 is the ladder that makes a frame a
    # frame, and searching inside the wood family for it is this repo's most-repeated palette
    # mistake.
    for (i, d) in sorted(posts):
        for h in range(1, tall):
            w.put(*f.at(i, d, h), pal["wall"])
        w.put(*f.at(i, d, tall), pal["trim"])
    for (i, d) in sorted(ring_bars):
        for h in range(1, tall):
            w.put(*f.at(i, d, h), bars, **_fence_props(f, ring, i, d))
        w.put(*f.at(i, d, tall), pal["trim"])
    # ...and an overhanging cornice one cell proud of the wall on every side. A vertical slab of
    # anything reads as a crate; the overhang is what puts a shadow line under the roof.
    for (i, d) in sorted(_ring_of(i0 - 1, i1 + 1, d0 - 1, d1 + 1)):
        if i in (i0 - 1, i1 + 1) and d in (d0 - 1, d1 + 1):
            w.put(*f.at(i, d, tall), pal["trim"])
            continue
        face = (_i_dir(f, 1) if i == i0 - 1 else _i_dir(f, -1)) if i in (i0 - 1, i1 + 1)             else (_d_dir(f, 1) if d == d0 - 1 else _d_dir(f, -1))
        _stair(w, f, i, d, tall, pal["stair"], face, half="top")

    # ---- the doorway: jambs, a gate, a lintel, and bars above it so the cage is still a cage
    for di in (door_i - 1, door_i + 1):
        for h in range(0, 4):
            w.put(*f.at(di, d0, h), pal["post"])
    w.put(*f.at(door_i, d0, -1), pal["path"])
    w.put(*f.at(door_i, d0, 0), pal["gate"], facing=_d_dir(f, -1),
          open="false", powered="false", in_wall="false")
    for h in range(1, 3):
        w.put(*f.at(door_i, d0, h), bars, **_fence_props(f, ring, door_i, d0))
    w.put(*f.at(door_i, d0, 3), pal["trim"])
    for h in range(4, tall):
        w.put(*f.at(door_i, d0, h), bars, **_fence_props(f, ring, door_i, d0))
    w.put(*f.at(door_i, d0, tall), pal["trim"])

    # ---- the lattice roof: the mesh you look up through
    mesh = 0
    for i in range(i0 + 1, i1):
        for d in range(d0 + 1, d1):
            w.put(*f.at(i, d, tall), bars, **_fence_props(f, full, i, d))
            mesh += 1

    # ---- the cupola: what makes it a landmark rather than a big cage
    ci, cd = (i0 + i1) // 2, (d0 + d1) // 2
    for (di, dd) in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        for h in range(tall + 1, tall + 4):
            w.put(*f.at(ci + di, cd + dd, h), pal["post"])
    for di in range(-1, 2):
        for dd in range(-1, 2):
            w.put(*f.at(ci + di, cd + dd, tall + 4), pal["canopy"][(di + dd) % 2])
    w.put(*f.at(ci, cd, tall + 5), pal["canopy"][0])
    w.put(*f.at(ci, cd, tall + 3), pal["light"], hanging="true", waterlogged="false")

    # ---- inside: a tree, two perches strung wall to wall, and a moss floor
    _plaza_tree(w, f, pal, land, i0 + 4, cd, seed + 5)
    perches = 0
    for h, pd in ((5, d0 + 2), (7, d1 - 2)):
        run = {(i, pd) for i in range(i0 + 1, i1)}
        for (i, dd) in sorted(run):
            if _free(w, f, i, dd, h):
                w.put(*f.at(i, dd, h), bars, **_fence_props(f, run | ring, i, dd))
                perches += 1
    n = 0
    for i in range(i0 + 1, i1):
        for d in range(d0 + 1, d1):
            n += _plant(w, f, i, d, seed, 60, density=0.5)
    return {"height": tall + 5, "mesh": mesh, "perches": perches, "planting": n}


# --------------------------------------------------------------------------- the lookout

def _lookout(w, f, pal, i0, i1, d0, d1):
    """A raised deck that TERMINATES THE SPINE, so the walk in arrives somewhere instead of
    stopping at a fence. Three courses up is enough to see over every rail on the lot.

    THE RAIL AND THE POSTS STAND ON THE DECK, NOT AT THE PAD. Written the obvious way - `_rail`
    at its default base - the whole balustrade was built INSIDE the deck's own solid fill, the
    canopy posts began three courses above nothing, and the roof and its posts shipped as a
    32-cell free-floating cluster. `_rail` takes a base course for exactly this.
    """
    deck = 3
    for i in range(i0, i1 + 1):
        for d in range(d0, d1 + 1):
            for h in range(deck):
                w.put(*f.at(i, d, h), pal["trim"] if h < deck - 1 else pal["ground"])
    # the flight up, laid on the spine in front of the deck: a tread per course, ascending inward
    for k in range(deck):
        d = d0 - deck + k
        for i in range(i0 + 1, i1):
            for h in range(0, k):
                w.put(*f.at(i, d, h), pal["trim"])
            _stair(w, f, i, d, k, pal["stair"], _d_dir(f, 1))
    ring = _ring_of(i0, i1, d0, d1) - {(i, d0) for i in range(i0 + 1, i1)}
    corners = [(i0, d0), (i1, d0), (i0, d1), (i1, d1)]
    _rail(w, f, pal, ring, posts=corners, height=1, base=deck)
    for (i, d) in corners:                                       # the posts carry the canopy
        for h in range(deck + 2, deck + 5):
            w.put(*f.at(i, d, h), pal["post"])
    for i in range(i0, i1 + 1):
        for d in range(d0, d1 + 1):
            w.put(*f.at(i, d, deck + 5), pal["canopy"][(i + d) % 2])
    for (i, d) in ((i0, d1), (i1, d1)):
        w.put(*f.at(i, d, deck + 5 - 1), pal["light"], hanging="true", waterlogged="false")
    return {"deck": deck, "height": deck + 5}


# --------------------------------------------------------------------------- the build

def build(cfg: dict, donors=None) -> Canvas:
    p = {**MENAGERIE, **cfg}
    if not p.get("at"):
        raise ValueError("menagerie needs params.at = [x, y, z] of the frontage's left corner")
    if p["facing"] not in _STEP:
        raise ValueError(f"facing must be one of {sorted(_STEP)}")
    if p["land"] not in LANDS:
        raise ValueError(f"unknown land {p['land']!r}; have {sorted(LANDS)}")

    W, D = int(p["width"]), int(p["depth"])
    if W < 29 or D < 20:
        raise ValueError(f"a menagerie needs at least 29x20; asked for {W}x{D}")
    f, pal, seed = _Frame(p), LANDS[p["land"]], int(p["seed"])
    w = World()
    Ctx(p["under"]) if p.get("under") else None   # unused here; the generator protocol wants it

    # ---- the layout, DERIVED from the lot rather than typed. The front band is deeper than the
    # back one because the barn and the pond need the depth and the meadow and the aviary do not.
    spine = int(p["spine"]) | 1
    ci = W // 2
    sp0, sp1 = ci - spine // 2, ci + spine // 2
    court0, court1 = 1, 3
    front_d = max(9, (D - 8) * 5 // 8)          # ...and 10 of the lot's 24, not a bare half
    fr0, fr1 = court1 + 1, court1 + front_d
    cr0, cr1 = fr1 + 1, fr1 + 3
    bk0, bk1 = cr1 + 1, D - 2
    wi0, wi1 = 1, sp0 - 2
    ei0, ei1 = sp1 + 2, W - 2
    look0 = bk1 - 3

    paved = set()
    for i in range(1, W - 1):
        for d in list(range(court0, court1 + 1)) + list(range(cr0, cr1 + 1)):
            paved.add((i, d))
    for i in range(sp0 - 1, sp1 + 2):
        for d in range(court1 + 1, look0):
            paved.add((i, d))
    n_paved = _ground(w, f, pal, W, D, paved)

    # ---- the four habitats. Ground cover goes in with each one and the structures over it,
    # because planting laid afterwards would need a guard at every one of a hundred call sites.
    pond = _pond(w, f, pal, ei0, ei1, fr0, fr1, seed)
    _jetty(w, f, pal, ei0 + 2, fr0 + 3, fr0 + 5)
    meadow = _meadow(w, f, pal, p["land"], wi0, wi1, bk0, bk1, seed)
    barn = _barn(w, f, pal, wi0, wi1, fr0, fr1, seed)
    aviary = _aviary(w, f, pal, p["land"], ei0, ei1, bk0, bk1, seed, (ei0 + ei1) // 2)
    look = _lookout(w, f, pal, sp0, sp1, look0, bk1)

    # ---- the rails: the pond's viewing edge, the paddock fence, and the boundary. Every pen
    # sign gets its own post IN the rail line, because a fence has nothing a board can hang on.
    signed = True
    pond_ring = [(i, fr0 - 1) for i in range(ei0, ei1 + 1)]         + [(i, fr1 + 1) for i in range(ei0, ei1 + 1)]         + [(ei0 - 1, d) for d in range(fr0 - 1, fr1 + 2)]
    pond_sign = (ei0 + 4, fr0 - 1)
    _rail(w, f, pal, pond_ring,
          posts=[(ei0 - 1, fr0 - 1), (ei0 - 1, fr1 + 1), pond_sign], height=1)
    signed &= _pen_sign(w, f, pal, *pond_sign, 0, -1, list(STOCK["pond"]))

    mead_ring = _ring_of(wi0 - 1, wi1 + 1, bk0 - 1, bk1 + 1)
    mead_sign = ((wi0 + wi1) // 2 - 4, bk0 - 1)
    _rail(w, f, pal, mead_ring,
          # THE SPINE STOPS AT THE LOOKOUT, so the paddock's side gate must too - opened onto
          # d beyond it, the gate lets out onto the deck's own solid flank and leads nowhere.
          gates=[((wi0 + wi1) // 2, bk0 - 1, _d_dir(f, 1)),
                 (wi1 + 1, min(bk0 + 1, look0 - 1), _i_dir(f, 1))],
          posts=[(wi0 - 1, bk0 - 1), (wi1 + 1, bk0 - 1), (wi0 - 1, bk1 + 1), (wi1 + 1, bk1 + 1),
                 mead_sign],
          height=1, light=[(wi1 + 1, bk0 - 1)])
    signed &= _pen_sign(w, f, pal, *mead_sign, 0, -1, list(STOCK["meadow"]))
    signed &= _pen_sign(w, f, pal, ei0 - 1, bk0 + 1, -1, 0, list(STOCK["aviary"]))

    bound = _ring_of(0, W - 1, 0, D - 1)
    tower = {(i, d) for i in range(sp0 - 4, sp1 + 5) for d in range(0, 3)}
    bposts = {(i, d) for (i, d) in bound
              if (i in (0, W - 1) and d in (0, D - 1))
              or (i in (0, W - 1) and d % 6 == 0)
              or (d in (0, D - 1) and i % 6 == 0)}
    _rail(w, f, pal, sorted(bound - tower), posts=sorted(bposts - tower), height=1,
          light=sorted({(i, d) for (i, d) in bposts if d == D - 1 and i in (0, W - 1)}))

    signed &= _gateway(w, f, pal, ci, spine, str(p["title"]), str(p["subtitle"]), seed)

    # ---- the street furniture, which is what turns 300 columns of paving from a surface you
    # cross into somewhere you stand. Lamps on the kerb lines, beds at the court's two ends,
    # benches facing the pens, an orientation board, and a pennant mast at each corner of the lot.
    lamps = [(sp0 - 1, court1 + 2), (sp1 + 1, court1 + 2), (sp0 - 1, cr1 - 1), (sp1 + 1, cr1 - 1),
             (sp0 - 1, look0 - 2), (sp1 + 1, look0 - 2), (4, cr0 + 1), (W - 5, cr0 + 1)]
    for (i, d) in lamps:
        _lamp(w, f, pal, i, d)
    for (i, d) in ((3, court0 + 1), (W - 4, court0 + 1), (3, cr1 - 1), (W - 4, cr1 - 1)):
        _bed(w, f, pal, i, d, seed)
    for i in (sp0 - 7, sp1 + 7):
        for k in (-1, 0, 1):
            w.put(*f.at(i + k, court0 + 1, 0), pal["slab"], type="bottom", waterlogged="false")
        for k in (-2, 2):
            w.put(*f.at(i + k, court0 + 1, 0), pal["post"])
    signed &= _board(w, f, pal, 6, 10, court1, [["BARN >", "POND >"], ["MEADOW >", "AVIARY >"],
                                                ["LOOKOUT >", "at the end"]])
    for (i, d) in ((1, 1), (W - 4, 1), (1, D - 2), (W - 4, D - 2)):
        _mast(w, f, pal, i, d)

    # ---- and the last thing: sweep the ground cover out of every doorway. Planting is laid
    # before the rails, so a drift can land in the cell you step through.
    for (x, y, z), (name, _pr) in list(w.cells.items()):
        if not name.endswith("_fence_gate"):
            continue
        for (dx, dz) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = w.cells.get((x + dx, y, z + dz))
            if n and n[0] in _GROUND_COVER:
                w.cells.pop((x + dx, y, z + dz))

    signed &= bool(barn["signed"])
    return w.canvas({
        "kind": "menagerie",
        "footprint": [W, D],
        "land": p["land"],
        "facing": p["facing"],
        "habitats": ["barn", "pond", "meadow", "aviary", "lookout"],
        "paved": n_paved,
        "barn": barn,
        "pond": pond,
        "meadow": meadow,
        "aviary": aviary,
        "lookout": look,
        "signed": bool(signed),
        "contract": ("a walk-through zoo filling its whole lot: a barn with four railed stalls "
                     "off a cross aisle, a sunken pond, an open paddock, a cage aviary and a "
                     "raised lookout, joined by a T of paths from a gated frontage; no animal "
                     "is placed by this generator - a litematic is blocks, not entities"),
        "unverified": ["NOTHING HERE IS LIVE STOCK. Every enclosure is empty on paste; each gate "
                       "sign names what to lead in and with what."],
    })
