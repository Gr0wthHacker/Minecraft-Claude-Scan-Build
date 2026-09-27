"""THE FIELD SHOP - what stands on the lot the Vantage Lookout was retired from.

Jack, on the north end after the tower came out: *"so now the lot where the tower was is empty,
just hanging vines - what can go there ... maybe we keep 1 building and put another shop there"*,
and then, choosing between the two candidate sites: *"tower lot"*.

---------------------------------------------------------------------------------------------
WHY A SHOP HERE AND NOT ON EITHER BUILDING'S GROUND

The lot is 17 x 17 at V130-146 x U0-16 - the LAND'S CLIMAX. A guest enters the Lost Plateau from
the Midway at U169 and walks north, so this is the last ground they reach, and it sits on the east
verge of the V123-127 avenue looking straight across at the Broken Plateau's gorge mouth and the
belvedere cantilevered over it. That is the one place in the land where somebody would actually
stop, which is what makes it a shop site rather than a building plot.

**SO IT IS TWO THINGS AND THE SECOND ONE IS FREE.** The north two courses of this lot are the
park's own rim - open void past U0 - so the terrace that fronts the shop is also the place the
belvedere is seen FROM. A shop with a view is a reason to stand still; a shop on a verge is a
kiosk nobody notices.

---------------------------------------------------------------------------------------------
IT IS OPEN-FRONTED, AND THAT IS THE WHOLE ARGUMENT THIS PARK HAS ALREADY HAD THREE TIMES

`Arrival Court`, `Boomtown Spine` and the `Skill Arcade` were all retired for the same shape - a
closed hall on a lot, good inside, saying nothing on the street. `PARK_MIDWAY.md`'s own words for
what replaced the last of them: *"a single awning/facade-backed games frontage. Each bay has a
standing spot, input, outcome."* A hall reads as a building; a COUNTER reads as a shop. So there
is no door and no fourth wall: the west face is a counter under a fly, and you can see the whole
inside of it from the avenue.

**AND IT HOLDS NOTHING.** The Abyss Market settled this: *"no container anywhere, asserted,
because a barrel standing empty in a public build reads as a shop somebody has already looted and
a chest anyone can reach is a chest anyone can empty."* The trade is real, so the board names the
server's own `/shops` and the counter carries a bell somebody can actually ring.

---------------------------------------------------------------------------------------------
THE PALETTE IS THE LAND'S, NOT `park.py`'s

`park.py` has a `frontier` palette and it is still spruce and cobblestone - the mining town this
land was re-themed away from. Everything standing here now is `bonebed.CAMP`: jungle timber with
white-and-red canvas, the same kit as the dig's tents, gantry and gallery across the avenue. Two
buildings in one land in two woods is how a re-theme leaks.
"""
from __future__ import annotations

import numpy as np

from .. import blocks
from .bonebed import CAMP
from .canvas import Canvas, hash01
from .frontier_builds import _Lot
from .mineridge import ROCK

#: The one stone in it: a dressed plinth so the timber is not standing in the turf, and the
#: terrace's own paving. `deepslate_bricks` is 51 darker than `stone_bricks` and is the one real
#: value contrast this economy has at cheap-or-ok tier - the same line the stair head, the void
#: tower and the zone bands are all drawn with, which is what makes them one hand.
STONE = {
    "plinth": "stone_bricks",
    "plinth_c": "cracked_stone_bricks",
    "kerb": "deepslate_bricks",
    "pave": "cobblestone",
    "pave_b": "stone",
    "step": "stone_brick_stairs",
    "slab": "stone_brick_slab",
}

SHOP = {
    "kind": "plateaushop",
    "lot": None,                  # [dv, du] - the measured lot, and the hard boundary
    "at": None,                   # [V, U] - the lot's near corner in park coordinates
    "anchor": [97500, 203, 80300],
    "sy": 18,

    #: **THE RIM IS LEFT OPEN.** U0 is the park's edge with void past it, so the first courses of
    #: this lot are the terrace and its rail - nothing is BUILT on them. A shop pushed to the
    #: boundary would put its back wall where the view is.
    "rim": 3,                     # cells of terrace between the brink and the building
    "shop": [3, 14, 5, 12],       # [v0, v1, u0, u1] - the building, in LOCAL cells
    "front": 3,                   # the local v of the open face - a guest stands at v-1
    "height": 5,
    "verge": 2,                   # cells of the avenue's own verge left alone at v0

    "benches": [],                # [[v, u], ...] on the terrace
    "planters": [],
    #: GROUND ANOTHER DESIGN STANDS ON, and here it is the land dressing: `PF Frontier Scatter`
    #: took this lot back the day the tower was retired and planted two jungle trees on it. A
    #: keep-out in ITS config is the fix; this is the belt to that pair of braces.
    "reserve": [],
    "title": "THE FIELD SHOP",
    "lines": [],                  # the shopfront board
    "shops_lines": [],            # the board that names the server's own trade
    "plaque": None,               # {v, u, facing, lines} on the terrace
    "seed": 0,
}


def _weather(lot: _Lot, v: int, u: int, y: int) -> str:
    """A masonry variant hashed on the CELL.

    Hashed on the COURSE every block in a course comes out identical and the wall is horizontal
    stripes of one material, which the deck soffit shipped once and nothing in an audit can see.
    """
    return "plinth_c" if hash01(v * 7 + 3, u * 13 + 5, y * 29 + 11, lot.seed) < 0.24 else "plinth"


# --------------------------------------------------------------------------- the ground


def _terrace(lot: _Lot, p: dict) -> dict:
    """The rim overlook: paving, a rail at the brink, benches, and the plaque.

    **THE RAIL IS AT THE BRINK AND NOWHERE ELSE.** Railing the other three sides would fence the
    terrace off the avenue it is entered from, which is the one thing an overlook must not do -
    the bone bed's gallery records the same rule from the other side.
    """
    dv, du = lot.dv, lot.du
    rim = int(p.get("rim", 3))
    #: **IT PAVES UP TO THE PLINTH, NOT TO `rim`.** Stopped at its own declared depth the terrace
    #: came away as a ninety-cell island - one empty course between it and the building's footing,
    #: which is a legal, supported, perfectly clean patch of paving that nothing joins.
    reach = max(rim, int(p["shop"][2]) - 1)
    out = {"pave": 0, "rail": 0, "post": 0, "bench": 0, "lamp": 0}
    for v in range(dv):
        for u in range(reach):
            r = hash01(v * 5, u * 11, 1, lot.seed)
            out["pave"] += int(lot.put(v, 0, u, STONE["pave" if r < 0.62 else "pave_b"]))
        #: THE BRINK ITSELF. A fence on the last row and nothing beyond it - the void is the
        #: exhibit, so the guard has to be the thinnest thing that stops a fall.
        out["rail"] += int(lot.fence(v, 1, 0, "v", key=CAMP["fence"]))
        if v % 5 == 0:
            out["post"] += int(lot.log(v, 1, 0, CAMP["post"], axis="y"))
            out["lamp"] += int(lot.put(v, 2, 0, CAMP["lamp"], hanging="false",
                                       waterlogged="false"))
    for v, u in (p.get("benches") or []):
        #: a bench is a stair facing the view, which here is NORTH - out over the rim.
        out["bench"] += int(lot.stair(int(v), 1, int(u), CAMP["stair"], facing="south"))
    return out


def _plinth(lot: _Lot, p: dict) -> int:
    """One course of dressed stone under the building, so the timber is not standing in turf."""
    v0, v1, u0, u1 = (int(x) for x in p["shop"])
    n = 0
    for v in range(v0 - 1, v1 + 2):
        for u in range(u0 - 1, u1 + 2):
            n += int(lot.put(v, 0, u, STONE[_weather(lot, v, u, 0)]))
    return n


# --------------------------------------------------------------------------- the building


def _shop(lot: _Lot, p: dict) -> dict:
    """Posts, three walls, a canvas fly and a counter across the open face.

    **THE FRONT IS A COUNTER, NOT A WALL WITH A DOOR IN IT.** Every closed hall this park has
    built has been retired for saying nothing on the street; what a guest can see into, they can
    tell what it is from twenty blocks away.
    """
    v0, v1, u0, u1 = (int(x) for x in p["shop"])
    hgt = int(p.get("height", 5))
    front = int(p.get("front", v0))
    out = {"post": 0, "wall": 0, "roof": 0, "counter": 0, "beam": 0, "lamp": 0, "shelf": 0}

    # the frame: a post at every corner and every fourth cell of the closed walls
    for v in range(v0, v1 + 1):
        for u in (u0, u1):
            if v == front:
                continue
            if v in (v0, v1) or v % 4 == 0:
                for y in range(1, hgt):
                    out["post"] += int(lot.log(v, y, u, CAMP["post"], axis="y"))
    for u in range(u0, u1 + 1):
        for y in range(1, hgt):
            if u in (u0, u1) or u % 4 == 0:
                out["post"] += int(lot.log(v1, y, u, CAMP["post"], axis="y"))

    # the three closed walls, boarded between the posts
    for v in range(v0, v1 + 1):
        for u in (u0, u1):
            if v == front:
                continue
            for y in range(1, hgt):
                if not lot.has(v, y, u):
                    out["wall"] += int(lot.put(v, y, u, CAMP["plank"]))
    for u in range(u0, u1 + 1):
        for y in range(1, hgt):
            if not lot.has(v1, y, u):
                out["wall"] += int(lot.put(v1, y, u, CAMP["plank"]))

    # THE FLY. Striped canvas on a beam frame - the land's own tent kit rather than a shingled
    # roof, because everything else standing in this camp is canvas and timber.
    for v in range(v0 - 1, v1 + 2):
        for u in range(u0 - 1, u1 + 2):
            key = "canvas_a" if ((v + u) // 3) % 2 == 0 else "canvas_b"
            out["roof"] += int(lot.put(v, hgt, u, CAMP[key]))
    for u in range(u0 - 1, u1 + 2):
        out["beam"] += int(lot.log(v1 + 1, hgt, u, CAMP["beam"], axis="z"))
    for v in (v0 - 1, v1 + 1):
        for u in (u0 - 1, u1 + 1):
            for y in range(1, hgt):
                out["post"] += int(lot.log(v, y, u, CAMP["post"], axis="y"))

    # THE COUNTER, across the open face at waist height, with a shelf behind it.
    for u in range(u0, u1 + 1):
        out["counter"] += int(lot.slab(front, 1, u, CAMP["slab"], "top"))
    for u in range(u0 + 1, u1):
        out["shelf"] += int(lot.put(v1 - 1, 2, u, CAMP["plank"]))
    for u in (u0 + 1, u1 - 1):
        out["lamp"] += int(lot.put(front + 1, hgt - 1, u, CAMP["lamp"], hanging="true",
                                   waterlogged="false"))
    return out


def _signs(lot: _Lot, p: dict) -> dict:
    """The shopfront board, the board that names the server's own trade, and the terrace plaque.

    FIFTEEN CHARACTERS IS THE LINE - this park has shipped "MINE CART ESCAP" and "and prize
    windo" - and `_Lot.sign` refuses a board with nothing behind it rather than hanging one in
    the air, so a refusal is REPORTED rather than assumed away.
    """
    v0, v1, u0, u1 = (int(x) for x in p["shop"])
    front = int(p.get("front", v0))
    hgt = int(p.get("height", 5))
    mid = (u0 + u1) // 2
    out = {"board": 0, "shops": 0, "plaque": 0, "bell": 0}

    # the fascia the shopfront board hangs on: a header across the open face
    for u in range(u0, u1 + 1):
        lot.put(front, hgt - 1, u, CAMP["plank"])
    out["board"] += int(lot.sign(front - 1, hgt - 1, mid, "west",
                                 [p["title"]] + list(p.get("lines") or [])))
    #: THE TRADE IS THE SERVER'S. `prices.json` is empty and `/cscan buy` is inert until somebody
    #: walks the shop, so this names the command rather than pretending to hold stock.
    #: ON THE BACK WALL AND ABOVE THE SHELF. Hung on the open face it had nothing behind it - the
    #: whole point of that face is that there is no wall there - and `_Lot.sign` refuses a board
    #: with nothing to hang on, so it shipped as one fewer sign than the config asked for and
    #: nothing said so. A guest at the counter reads it across the shop.
    out["shops"] += int(lot.sign(v1 - 1, 3, mid, "west", list(p.get("shops_lines") or [])))

    #: **THE VERB.** A counter with nothing to do at it is a prop. A bell is one block, needs no
    #: circuit, is cheap and 1.19, and is what the Menagerie's muster yard settled on for exactly
    #: the same reason.
    out["bell"] += int(lot.put(front, 2, mid, "bell", facing="west", attachment="single_wall"))

    spec = p.get("plaque")
    if spec:
        v, u = int(spec["v"]), int(spec["u"])
        for y in (1, 2):
            lot.log(v, y, u, CAMP["post"], axis="y")
        lot.put(v, 3, u, CAMP["plank"])
        out["plaque"] += int(lot.sign(v, 3, u + 1, "south", list(spec["lines"])))
    return out


def _yard(lot: _Lot, p: dict, seed: int) -> int:
    """Planters on the terrace - the only dressing, and NOT ONE CONTAINER anywhere on the lot."""
    n = 0
    for v, u in (p.get("planters") or []):
        v, u = int(v), int(u)
        #: **SOIL, NOT THE KERB.** Rule 11: a plant roots in the dirt family and nowhere else, and
        #: a fern set on `deepslate_bricks` is a placement problem the audit reports and a render
        #: draws perfectly happily. The box is moss; the dark rim is the course BESIDE it.
        for a in range(2):
            for b in range(2):
                n += int(lot.put(v + a, 1, u + b, "moss_block"))
        n += int(lot.put(v, 2, u, "fern"))
        n += int(lot.put(v + 1, 2, u + 1, "moss_carpet"))
    return n


def build(cfg: dict, donors=None) -> Canvas:
    p = {**SHOP, **(cfg or {})}
    if not p.get("lot"):
        raise ValueError("the field shop needs its measured lot: lot: [dv, du]")
    dv, du = int(p["lot"][0]), int(p["lot"][1])
    c = Canvas(dv, int(p.get("sy") or 18), du, donors)
    lot = _Lot(c, dv, du, seed=int(p.get("seed", 0)))
    seed = int(p.get("seed", 0))

    #: ORDER: the ground first, then the frame, then what hangs on it. Reversed, the plinth fills
    #: the counter back in and the audit reports nothing at all.
    parts = {"terrace": _terrace(lot, p)}
    parts["plinth"] = _plinth(lot, p)
    parts["shop"] = _shop(lot, p)
    parts["signs"] = _signs(lot, p)
    parts["planters"] = _yard(lot, p, seed)

    av, ay, au = (int(x) for x in p["anchor"])
    at_v, at_u = (int(x) for x in (p.get("at") or (0, 0)))
    c.world_origin = (av + at_v, ay, au + at_u)
    c.meta = {
        "kind": "plateaushop",
        "lot": [dv, du],
        "at": [at_v, at_u],
        "land": "frontier",
        "facing": "west",
        "profile_axis": "v",
        "signs": lot.signs,
        "refused": lot.refused,
        "parts": parts,
        "contract": (
            "an open-fronted field shop on the lot the Vantage Lookout was retired from, with a "
            "counter instead of a fourth wall, a bell somebody can ring, a board naming the "
            "server's own /shops rather than stock it does not hold, NOT ONE CONTAINER, and a "
            "rim terrace in front of it that is also where the belvedere is seen from"),
    }
    return c
