"""PF MIDWAY GARDEN - the pleasure garden that replaced the games at the head of column C.

    V24-99 x U345-384, from the east avenue to the helter skelter's forecourt

Jack, on the games row: *"the games arent playable as they are facing, theyre ugly, and just not
working, these have been a consistent issue, either identify and make them really look good, or
trash the idea and lets put something else there."*

**THE FAULT WAS IN THE CONSOLE, NOT IN THE SITING, AND IT IS WORTH WRITING DOWN BEFORE THE GARDEN
IS.** Dumped block for block off `out/PF Game Target Wall.litematic`:

    Y206   ############   the lid
    Y205   ##B#######T#   the BELL and the TARGET - the game's own INPUT - sealed inside
           ###LLLLLL###   the six score lamps - sealed inside
    Y204   ############   the plinth
           front face U357: solid at Y204, Y205 and Y206

A `park_games` console is a THREE-COURSE SEALED CABINET. Its score lamps are buried in the lid
course in every kind; the aim and striker targets are entirely enclosed, so they cannot be shot;
and the pair's two buttons sit on top of a three-course lid, above a standing player's head, with
their lamp buried eleven cells away at the far end. Only the counter's barrels are on a face a
player can touch.

**AND EVERY ONE OF THEM SIMULATES CORRECTLY.** The circuits are right. That is this repo's own
cardinal sin - a machine that looks like it works - in the one subsystem written to prevent it, and
it is why the games have been "a consistent issue" for as long as they have existed. Retiring the
Skill Arcade did not cause it; the hall was hiding it. Four more stand in the Frontier with the
same fault. Fixing it is a rewrite of `park_games` across six kinds and eleven configs with every
simulated contract to re-verify, and it is its own job - see the note in `tools/park_place.py`.

## What the garden is

    the walk       U358-370, thirteen wide, V24 -> V99 and on into the tower's forecourt
    two parterres  U351-357 and U371-377 - kerbed beds, clipped hedge, wool and flowers
    two shoulders  U345-350 and U378-384 - left informal, and `PF Park Green` already dresses them
    avenue trees   down each bed's own midline
    four pergolas  over the walk, which is the only vertical rhythm in it

**THE WALK IS THE ONE THING KEPT FROM THE GAMES ROW.** `Park Ways` paves nothing in V24-99 but the
V77 cross walk and two door spurs, because the Skill Arcade filled the column wall to wall - so
this column had a door where every other column in this park has a spine. That was true before the
games and it is the half of the row worth keeping.

**AND THE SHOULDERS ARE INFORMAL BECAUSE THE GROUND IS NOT THIS DESIGN'S ALONE.** Measured,
`PF Park Green` holds 105 cells in this lot and 98 of them are at U378-384 - it dresses the outer
band of the east flank and nothing else. Beds drawn to the lot edge would have contested every one
of them, which is a WORK problem rather than a rendering one: you place a block, the next placement
says it is wrong, you break it and place it again. So the beds stop at U377 and the wild edge stays
wild, which is what a pleasure garden's outer walk looks like anyway.
"""
from __future__ import annotations

from .canvas import Canvas, hash01
from .helter import _bench, _floor_mat, _owned, _plain, _tree   # noqa: F401 - one kit, one park
from .midway_builds import PAL, _Lot, _dir                      # noqa: F401

GARDEN = {
    "lot": None,               # [v0, u0, v1, u1] in park V/U - the canvas IS this
    "at": None,                # [x, y, z] of (lot v0, the first course above the lawn, lot u0)
    "blocked": (),             # the cross walk, the ground layer's masts, the frontage's gantry
    "height": 10,
    "seed": 0,
    "axis": None,              # U of the walk's centre line
    "walk_half": 6,            # U358-370 at axis 364 - the Welcome Court's own width
    "beds": (),                # [[v0, u0, v1, u1]] of each parterre
    "pergolas": (),            # [v] of each arch over the walk
    "plant": (),               # [[v, u]] - a tree, on ground MEASURED free rather than assumed
    "seats": (),               # [[v, side]] - a bench on the walk's verge, side -1 = -U
}

#: THE BED'S OWN PALETTE. `grass_block` and every form of dirt are CURRENCY on this server, which
#: is why the whole park's lawn is moss and why a bed here is moss too. The BOLD half of the
#: pattern is wool, because `render3d` draws a flower as one flat RGB averaged over a mostly
#: transparent texture - a bed of poppies renders here as brown-green mush and reads scarlet in
#: game - so the shape is wool and the flowers are planted in the moss between it. The Welcome
#: Court's own finding, and this is the same park.
BED = {
    "kerb": "polished_blackstone_bricks",
    "hedge": "oak_leaves",
    "soil": "moss_block",
    "bold": ("red_wool", "white_wool", "pink_wool"),
    "flower": ("poppy", "oxeye_daisy", "pink_tulip", "dandelion", "cornflower"),
}


def _walk(L, p, m) -> None:
    """The spine the column never had, and the only thing kept from the games row."""
    axis, half = int(p["axis"]), int(p["walk_half"])
    owned = _owned(L)
    for v in range(L.v0, L.v1 + 1):
        for u in range(axis - half, axis + half + 1):
            if (v, u) in owned:
                continue
            mat = PAL["inlay"] if abs(u - axis) == half else _floor_mat(v, u)
            m["paved"] += bool(L.put(v, 0, u, mat))
    for v in range(L.v0, L.v1 + 1, 7):
        for u in (axis - half + 1, axis + half - 1):
            if (v, u) not in owned and L.put(v, 0, u, PAL["glow"]):
                m["lamps"] += 1


def _parterre(L, p, bed, m) -> None:
    """A kerbed bed with a clipped hedge on its rim and a pattern inside it.

    **THE PATTERN IS DRAWN ON A COARSE LATTICE, NOT PER CELL.** Per cell, three colours over a
    thousand columns is static - the deck floor's confetti, in wool - so the bold blocks come in
    blocks of four and the flowers fill the moss between them.
    """
    v0, u0, v1, u1 = (int(q) for q in bed)
    seed = int(p["seed"])
    owned = _owned(L)
    for v in range(v0, v1 + 1):
        for u in range(u0, u1 + 1):
            if (v, u) in owned:
                continue
            rim = v in (v0, v1) or u in (u0, u1)
            if rim:
                m["bed"] += bool(L.put(v, 0, u, BED["kerb"]))
                # THE HEDGE IS BROKEN AT EVERY ENTRANCE, and the entrances are the bed's ends: a
                # bed you cannot step into is a fenced-off rectangle rather than a garden.
                if not (u in (u0, u1) and (v - v0) % 9 in (4, 5)):
                    m["bed"] += bool(L.put(v, 1, u, BED["hedge"],
                                           persistent="true", distance="1"))
                continue
            m["bed"] += bool(L.put(v, 0, u, BED["soil"]))
            # **A PARTERRE IS A MOTIF, NOT A SCATTER.** Hashed per cell it came out as random
            # patches of colour - the deck floor's confetti, in wool - and a bed you cannot read a
            # pattern in is a flowerbed rather than a parterre. This is a lozenge every six cells
            # along the bed, and because it is a function of the DISTANCE from the bed's own
            # midline the two beds mirror each other across the walk for free.
            mid = (u0 + u1) / 2.0
            k, r = (v - v0) % 6, abs(u - mid)
            if abs(k - 2.5) + r <= 1.6:
                m["bed"] += bool(L.put(v, 1, u, BED["bold"][((v - v0) // 6) % 3]))
            elif hash01(v, u, 1, seed) < 0.55:
                m["bed"] += bool(L.put(v, 1, u,
                                       BED["flower"][int(hash01(v, u, 2, seed) * 5) % 5]))


def _pergola(L, p, v, m) -> None:
    """Two posts and a beam over the walk. **THE ONLY VERTICAL RHYTHM IN A GARDEN IS ITS
    STRUCTURES**, and a pleasure garden's are arches - which is also the one shape that gives this
    column something to read against the tower at the end of it without building anything."""
    axis, half = int(p["axis"]), int(p["walk_half"])
    owned = _owned(L)
    for u in (axis - half, axis + half):
        if (v, u) in owned:
            return
    for u in (axis - half, axis + half):
        for y in range(1, 5):
            m["pergola"] += bool(L.put(v, y, u, PAL["post"]))
    for u in range(axis - half, axis + half + 1):
        if (v, u) in owned:
            continue
        m["pergola"] += bool(L.put(v, 5, u, PAL["band"] if (u // 2) % 2 else PAL["frame"]))
    for u in (axis - half + 1, axis + half - 1):        # the braces that make it an arch
        if (v, u) not in owned:
            m["pergola"] += bool(L.put(v, 4, u, PAL["shelf"], type="top", waterlogged="false"))


def build(cfg: dict, donors=None) -> Canvas:
    p = {**GARDEN, **(cfg or {})}
    if not p.get("lot"):
        raise ValueError("the garden needs params.lot = [v0, u0, v1, u1]")
    v0, u0, v1, u1 = (int(q) for q in p["lot"])
    if p.get("axis") is None:
        p["axis"] = (u0 + u1) // 2
    c = Canvas(v1 - v0 + 1, int(p["height"]), u1 - u0 + 1, donors)
    L = _Lot(c, (v0, u0, v1, u1), p.get("blocked") or ())
    m = {"paved": 0, "lamps": 0, "bed": 0, "pergola": 0, "benches": 0, "trees": 0}

    _walk(L, p, m)
    for bed in p["beds"]:
        _parterre(L, p, bed, m)
    for v in p["pergolas"]:
        _pergola(L, p, int(v), m)
    owned = _owned(L)
    axis, half = int(p["axis"]), int(p["walk_half"])
    for v, side in p["seats"]:
        u = axis - half + 1 if int(side) < 0 else axis + half - 1
        if (int(v), u) not in owned:
            m["benches"] += _bench(L, int(v), u, u, 1, "south" if int(side) < 0 else "north")
    for v, u in p["plant"]:
        if (int(v), int(u)) not in owned:
            m["trees"] += bool(_tree(L, int(v), int(u), owned=owned))

    if L.refused or L.blocked_hits:
        raise ValueError(f"garden: {L.refused} cell(s) outside lot {p['lot']}, "
                         f"{L.blocked_hits} on cells the park already owns")
    if p.get("at"):
        c.world_origin = tuple(int(q) for q in p["at"])
    c.meta = {
        "kind": "path", "build": "midway_garden", "name": "PF Midway Garden",
        "lot": [v0, u0, v1, u1], "axis": int(p["axis"]),
        # THE FACING IS A COMPASS WORD, as `park.py` records it: the garden is entered from the
        # east avenue at V24, so its front looks -V.
        "facing": "west",
        "beds": [list(b) for b in p["beds"]],
        **m,
        "contract": (
            "a walk from V%d to V%d with a kerbed bed either side of it, a hedge with a way in "
            "every nine, and NO BUILDING anywhere in it" % (v0, v1)),
        "note": "no mechanism, nothing to stock; the games that stood here are retired - see the "
                "module docstring for why",
    }
    return c
