"""PF GAMES ROW - what replaces the Skill Arcade and the Prize Point.

    V24-99 x U345-384, the head of Midway column C

Jack, on the two buildings: *"i dont like these and they feel out of place/useless unclear."*
Measured over the shipped park before either was retired:

    Skill Arcade   6,364 blocks, 51 x 33, 84% of its footprint solid, 21 courses, THREE games
    Prize Point    1,927 blocks, 20 x 33, a nine-barrel counter forty courses away from them

Three things made them read that way and every one is a number:

- **THE ARCADE WAS A CLOSED HALL** - the shape the Arrival Court and Boomtown Spine were retired
  for. Its inside was good (a lit aisle, timber trusses, three working bays, 1,160 standable
  cells) and NOTHING on the street said so. A hall reads as a building; a counter reads as a game.
- **its own marquee promised "five games" over three**, in `PF Front Midway`;
- **and the column had no route through it.** `Park Ways` paves nothing in V24-99 but the V77
  cross walk and two door spurs, because the hall filled the column wall to wall. Every other
  Midway column has a spine; this one had a door.

`PARK_MIDWAY.md` has asked for the replacement in its own words all along: *"Merge Plinko, High
Striker, and arcade functions into a single awning/facade-backed games frontage. Each bay has a
standing spot, input, outcome, clear prize or score path, and protected redstone rear. Place the
prize counter as the natural next step."*

## THIS MODULE IS THE STREET. THE BAYS BUILD THEMSELVES.

`arcade._shell` gives every `park_games` console its own corner posts, back wall, roof beam and
fascia - they are self-contained open-fronted booths, and they sign themselves. So there is no
building in this file at all: it lays the walk the column never had, the colonnade that turns six
separate booths into one frontage, the bunting between them and the seats on its verges.

    -U flank, front U357   TARGET WALL  V26-37 . THE MARK V41-51 . THE STRIKER V55-66
                           PRIZE POINT  V85-97, past the cross walk - the natural next step
    +U flank, front U371   THE DOUBLE   V28-42 . THE SIGNAL V48-63
    between them           the walk, U358-370, V24 -> V99 and on into the tower's forecourt

**FIVE GAMES NOW, AND THE MARQUEE STOPS LYING.** The Striker and the Signal are the two kinds
`park_games` already had and the Midway never built - and `PARK_MIDWAY.md` names the high striker
by name. All five and the counter carry a contract asserted by simulation in
`tests/test_park_games.py`; nothing in this file places a mechanism.

**EVERY BAY IS RESERVED, NOT DEFERRED.** The six boxes are in `blocked`, so wanting one of their
cells RAISES here rather than shipping as an overlap: a console missing a cell is a console that
does nothing, and `park_games` counts its own refusals for the same reason from the other side.
"""
from __future__ import annotations

from .canvas import Canvas
from .helter import _bench, _floor_mat, _owned, _plain, _tree   # noqa: F401 - one kit, one park
from .midway_builds import PAL, _Lot, _dir                      # noqa: F401

GAMES_ROW = {
    "lot": None,               # [v0, u0, v1, u1] in park V/U - the canvas IS this
    "at": None,                # [x, y, z] of (lot v0, the first course above the lawn, lot u0)
    "blocked": (),             # the cross walk, the ground layer's masts, and the six bays
    "height": 12,
    "seed": 0,
    "axis": None,              # U of the walk's centre line
    "walk_half": 6,            # U358-370 at axis 364 - the Welcome Court's own width
    "facade_top": 6,           # the screen's cap course, level with the consoles' own fascias
    "fronts": None,            # [low, high] - the U of each flank's bay front line
    "bays": (),                # [[v0, u0, v1, u1]] - the consoles' boxes, reserved
    "bay_tops": (),            # each console's own top course, so its awning clears its board
    "gaps": (),                # [[v0, v1]] of the walk where bunting may be strung
    "seats": (),               # [[v, side]] - a bench on the verge, side -1 = -U
    "plant": (),               # [[v, u]] - a tree, on ground MEASURED free rather than assumed
    "cross": None,             # [v0, v1] of `Park Ways`' cross walk through this lot
}


# ---------------------------------------------------------------------------- the street


def _walk(L, p, m) -> None:
    """The spine the column never had: the Welcome Court's own thirteen-wide walk, carried from
    the avenue at V24 to the helter skelter's forecourt at V100.

    It runs between the two bay FRONT LINES, so it can never take a console's cell however the
    bays are re-sited: at U358-370 with fronts at U357 and U371 there is no cell in common.
    """
    v0, u0, v1, u1 = L.v0, L.u0, L.v1, L.u1
    axis, half = int(p["axis"]), int(p["walk_half"])
    owned = _owned(L)
    for v in range(v0, v1 + 1):
        for u in range(axis - half, axis + half + 1):
            if (v, u) in owned:
                continue
            mat = PAL["inlay"] if abs(u - axis) == half else _floor_mat(v, u)
            m["paved"] += bool(L.put(v, 0, u, mat))
    for v in range(v0, v1 + 1, 7):                     # the light, flush, as the park's own is
        for u in (axis - half + 1, axis + half - 1):
            if (v, u) not in owned and L.put(v, 0, u, PAL["glow"]):
                m["lamps"] += 1


def _facade(L, p, m) -> None:
    """WHAT TURNS SIX BOOTHS INTO A FRONTAGE - and the first attempt did the opposite.

    It was a colonnade: posts on the walk's kerb carrying a canopy three cells out over the walk,
    down both verges. Every console stands BEHIND that line, so what it actually built was a
    covered arcade with the games hidden behind its own posts - the exact opposite of the point,
    and one render settled it. A booth already has its own roof beam and fascia from
    `arcade._shell`; it does not need a second roof, and it must not have anything in front of it.

    So the frontage is a SCREEN ON THE BAY FRONT LINE, filling the gaps between the consoles at
    their own height, and the consoles are the openings in it. **WHAT MAKES VOXELS READ AS
    ARCHITECTURE IS REGULARITY AND OPENINGS, NOT DAMAGE** - the void tower's rule, and it is what
    `PARK_MIDWAY.md` means by a "facade-backed games frontage": one wall, six holes, nothing
    standing in front of any of them.
    """
    axis = int(p["axis"])
    top = int(p["facade_top"])
    owned = _owned(L)
    for side in (-1, 1):
        front = int(p["fronts"][0] if side < 0 else p["fronts"][1])
        bays = [b for b in p["bays"] if (b[1] < axis) == (side < 0)]
        if not bays:
            continue
        a0, a1 = min(x[0] for x in bays) - 2, max(x[2] for x in bays) + 2
        mouths = {v for x in bays for v in range(x[0], x[2] + 1)}
        for v in range(max(a0, L.v0), min(a1, L.v1) + 1):
            if v in mouths or (v, front) in owned:
                continue                                  # a console's own front is the opening
            # LOW, AND PALE. At six courses it was a wall either side of a thirteen-wide walk -
            # a canyon, with the consoles hidden behind it, which is the colonnade's own mistake
            # made a second time in a different material. A frontage a visitor SEES OVER is a
            # frontage; one they cannot is a fence. Dark plinth, white field, red top rail: the
            # fairground hoarding this land is already built out of.
            for y in range(1, top + 1):
                mat = (PAL["plinth"] if y == 1 else
                       PAL["band"] if y == top else
                       (PAL["field"] if (v % 6 == 0) else PAL["frame"]))
                m["facade"] += bool(L.put(v, y, front, mat))
            # ...and it OVERSAILS by one, so the screen and the booths share a shadow line rather
            # than meeting in a flat plane. A fascia is what a fairground name goes on.
            u = front - side
            if (v, u) not in owned:
                m["facade"] += bool(L.put(v, top, u, PAL["band"]))


def _booth(L, p, m) -> None:
    """A BOOTH ROUND EVERY CONSOLE, and it is the whole reason the first two attempts failed.

    Jack, on the row as first built: *"the games arent playable as they are facing, theyre ugly,
    and just not working, these have been a consistent issue."* All three, and one root cause.

    **A `park_games` CONSOLE IS FURNITURE, NOT A BOOTH.** Its own docstring says so - *"a console
    is furniture ... it needs no ceiling because the building already has one"* - and measured off
    the artifact it is a THREE-COURSE SOLID CABINET (plinth, machine course, lid) with a six-course
    board behind it. Standing on the walk a player's feet are at the cabinet's own base course, so
    the counter is a wall ABOVE THEIR HEAD: they can see the score board over it and cannot see or
    comfortably reach the controls on top of it. Retiring the Skill Arcade took away the room these
    were designed for and left the furniture in the street.

    So each bay gets what a fairground booth actually is:

        a DECK one course above the walk   - the player steps UP, so the counter is waist high
        side walls to the roof             - the board is the back, so there is no back wall
        a striped awning over the whole    - oversailing the front by one, which is what an awning IS
        a fascia across the front          - the board a booth's name goes on

    **THE DECK IS THE FIX FOR "not playable".** One course up puts the player's feet level with the
    cabinet's base, so its lid is one course above them and the controls on top are at chest
    height - which is what a counter is.
    """
    axis = int(p["axis"])
    owned = _owned(L)
    for bay, top in zip(p["bays"], p["bay_tops"]):
        bv0, bu0, bv1, bu1 = (int(q) for q in bay)
        side = -1 if bu1 < axis else 1                  # which flank, and so which way it faces
        front = bu1 if side < 0 else bu0
        back = bu0 if side < 0 else bu1
        step = 1 if side < 0 else -1                    # from the console toward the walk
        roof = int(top) + 1
        wv0, wv1 = bv0 - 1, bv1 + 1                     # the booth's own side walls
        lo_u, hi_u = min(back, front + step), max(back, front + step)
        for v in range(wv0, wv1 + 1):
            for u in range(lo_u, hi_u + 1):
                if (v, u) in owned:
                    continue
                edge = v in (wv0, wv1)
                # the boards you stand on, and the step down to the walk
                if not (bv0 <= v <= bv1 and bu0 <= u <= bu1):
                    m["booth"] += bool(L.put(v, 0, u, PAL["inlay"]))
                    if u != front + step:
                        m["booth"] += bool(L.put(v, 1, u, PAL["floor2"] if not edge
                                                 else PAL["field"]))
                if edge:
                    for y in range(2, roof):
                        m["booth"] += bool(L.put(v, y, u, PAL["field"] if y % 2 else PAL["frame"]))
                # THE AWNING, striped ALONG the row so it reads as one frontage from the walk
                m["booth"] += bool(L.put(v, roof, u, PAL["band"] if (v // 2) % 2 else PAL["frame"]))
        # ...and the fascia hangs UNDER the awning's own oversail, which is where a name goes.
        for v in range(wv0, wv1 + 1):
            u = front + step
            if (v, u) not in owned:
                m["booth"] += bool(L.put(v, roof - 1, u, PAL["plinth"]))


def _bunting(L, p, m) -> None:
    """Strung across the walk in the gaps between bays, and NOWHERE ELSE.

    **A SAG IS NOT 6-CONNECTED UNLESS THE STEP IS FILLED** - the helter skelter's swags shipped as
    free-floating clusters for exactly this, and so did the midway row's. Each line runs level and
    is carried at both ends by the colonnade's own beam course.
    """
    axis, half = int(p["axis"]), int(p["walk_half"])
    owned = _owned(L)
    for g in p["gaps"]:
        v = (int(g[0]) + int(g[1])) // 2
        if not (L.v0 <= v <= L.v1):
            continue
        n = 0
        for u in range(axis - half, axis + half + 1):
            if (v, u) in owned:
                continue
            n += bool(L.put(v, 6, u, PAL["band"] if (u // 2) % 2 else PAL["frame"]))
        if n:
            m["bunting"] += n
            for u in (axis - half, axis + half):        # the two ends it hangs from
                for y in range(1, 6):
                    if (v, u) not in owned:
                        L.put(v, y, u, PAL["post"])


def _green(L, p, m) -> None:
    """The seats and the planting, on ground MEASURED free rather than assumed.

    Every tree here is a coordinate in the config taken off the shipped park, because this lot
    already carries `PF Park Green`'s own trees and the ground layer's lamp masts - and a canopy
    is CELLS while a lawn test is a COLUMN, which is the guard that has already been got wrong
    twice in this park.
    """
    axis, half = int(p["axis"]), int(p["walk_half"])
    owned = _owned(L)
    for v, side in p["seats"]:
        u = axis - half + 1 if int(side) < 0 else axis + half - 1
        if (int(v), u) in owned:
            continue
        m["benches"] += _bench(L, int(v), u, u, 1, "south" if int(side) < 0 else "north")
    for v, u in p["plant"]:
        if (int(v), int(u)) in owned or L.has(int(v), 0, int(u)):
            continue
        m["trees"] += bool(_tree(L, int(v), int(u), owned=owned))


def build(cfg: dict, donors=None) -> Canvas:
    p = {**GAMES_ROW, **(cfg or {})}
    if not p.get("lot"):
        raise ValueError("the games row needs params.lot = [v0, u0, v1, u1]")
    v0, u0, v1, u1 = (int(q) for q in p["lot"])
    if p.get("axis") is None:
        p["axis"] = (u0 + u1) // 2
    if not p.get("fronts"):
        raise ValueError("the games row needs params.fronts = [low U, high U] of the bay fronts")
    c = Canvas(v1 - v0 + 1, int(p["height"]), u1 - u0 + 1, donors)
    L = _Lot(c, (v0, u0, v1, u1), p.get("blocked") or ())
    m = {"paved": 0, "lamps": 0, "facade": 0, "booth": 0, "bunting": 0,
         "benches": 0, "trees": 0}

    _walk(L, p, m)
    _facade(L, p, m)
    _booth(L, p, m)
    _bunting(L, p, m)
    _green(L, p, m)

    if L.refused or L.blocked_hits:
        raise ValueError(f"games row: {L.refused} cell(s) outside lot {p['lot']}, "
                         f"{L.blocked_hits} on cells the ground layer or a console already owns")
    if p.get("at"):
        c.world_origin = tuple(int(q) for q in p["at"])
    c.meta = {
        "kind": "path", "build": "games_row", "name": "PF Games Row",
        "lot": [v0, u0, v1, u1], "axis": int(p["axis"]),
        # THE FACING IS A COMPASS WORD, as `park.py` records it and as `tools/look.py` reads it.
        # The row is entered from the avenue at V24, so its front looks -V.
        "facing": "west",
        "bays": [list(b) for b in p["bays"]],
        **m,
        "contract": (
            "a walk from V%d to V%d between two lines of self-contained consoles, under one "
            "colonnade, taking no cell of any bay and none of the cross walk that crosses it"
            % (v0, v1)),
        # WHAT THIS MODULE DOES NOT BUILD, stated so nobody looks for it here: every console,
        # its counter, its board and its sign come from `park_games`, which asserts its own
        # contract by simulation. This is the street they stand on.
        "note": "six park_games consoles stand in this row; none of them is built here",
    }
    return c
