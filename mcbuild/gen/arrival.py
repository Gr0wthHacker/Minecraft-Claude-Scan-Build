"""The Arrival: the twenty seconds before a visitor has walked anywhere.

**THE MEASUREMENT THAT PRODUCED THIS FILE.** `newisle`'s bedrock is at (97600, 200, 80600) - the
island's own origin, which is where a skyblock player is put down by `/is` and where the starter
pad sits. Read straight off the shipped `out/Park_Centre Complete.litematic`, the column there is:

    Y202 black_wool - Y203 stone_bricks - Y204 stone - Y205..Y213 stone_bricks - Y214+ black_wool

Solid, every course, from the floor to nine blocks over a player's head. **The Monument (33x33,
centred on (97595, 80600)) is built across the exact cell a visitor arrives in.** There is not one
standable cell within three blocks of the origin at street level. A player teleporting home does
not arrive in a theme park; they arrive inside a wall.

That is the whole reason this module exists, and it is why the anchor here is not the front-left
floor corner every other park kind uses: **`at` IS THE ARRIVAL CELL** - the cell a player's feet
occupy - and the court is built radially around it, because the one coordinate that cannot be
negotiated is the one the server chooses.

WHAT IT HAS TO DO, in the order a visitor experiences it:

    1. LAND ON SOMETHING          a level court, floor flush with the park at Y202, walking Y203,
                                  wide enough that a teleport cannot miss it
    2. SEE OUT                    nothing this design builds stands over head height within the
                                  four cardinal sightlines; `meta["sightlines"]` records how far
                                  each one actually runs, measured, not intended
    3. KNOW WHERE TO GO           a `wayfinding.mapboard` reading toward the arrival cell, a
                                  `wayfinding.fingerpost` naming real destinations, and a
                                  `wayfinding.noticeboard`. NOT ONE LINE OF NEW SIGNAGE - all
                                  three are tested generators and this is a siting job
    4. WALK OUT                   four paved spurs, one per cardinal, landing on the zone's own
                                  avenues

**THE GROUND IS STONE, NOT WOOL.** Jack, on the shipped park: wool belongs on the things that are
not the ground. Every block here is cheap, 1.19-legal and spendable, and the court draws its own
figure out of a measured value ladder rather than out of colour:

    stone_bricks               122     the field
    smooth_basalt               73     the kerb line, and the ring
    polished_blackstone_bricks  45     the spokes and the middle
    chiseled_stone_bricks      120     the arrival cell itself, one pale block in the dark middle

Steps of 49 and 28 - both well past the ~15 below which a tone stops reading as a tone. This is
the ladder CLAUDE.md records as measured ACROSS families, after three separate notes in this repo
concluded the economy has no value contrast by searching inside ONE family, where a ladder cannot
exist by construction.

**THE LIGHT IS IN THE FLOOR.** `ochre_froglight` on a fixed grid, flush in the floor course - this
island's own idiom, already carried by `Island Night`, the lowland turf and the Park Line's deck
edge. A flush froglight IS the floor, so it reaches 14 rather than 15, and the grid is set against
that. A lamp on a post in the middle of an arrival court is a lamp a visitor lands on top of.

**THE STARTER ISLAND IS IN THE WAY AND IT IS ON THE DIG LIST.** A printer places into AIR and
never replaces, so the skyblock starter pad - grass, two dirt, a tree - occupies the exact cells
this court's floor and clearance want. Those cells are emitted in `meta["dig"]`, which the
pipeline writes into the sidecar for `/cscan dig` to show. The starter CHEST is deliberately NOT
dug: a chest is a protected block everywhere else in this project and it is not this design's to
break - it is reported in `meta["unverified"]` for a human to move.
"""
from __future__ import annotations

import json

import numpy as np

from . import park
from .canvas import Canvas
from .park import LANDS, SIGN_WIDTH, _STEP
from .vertical import Ctx, World
from .. import nbt

ARRIVAL = {
    "under": None,
    # THE ARRIVAL CELL, not a corner: the cell a player's feet occupy when the server puts them
    # down. The floor block goes one course under it.
    "at": None,
    "land": "midway",
    "kind": "court",
    "radius": 11,              # half-width of the court, before the corners are chamfered
    "chamfer": 5,              # how deep each corner is cut back, so the court reads as a place
    "spur": 5,                 # how far each cardinal spur runs past the rim
    "spur_half": 2,            # half-width of a spur: 5 columns
    "clear": 3,                # courses of air kept over the arrival cell and every spur
    "lamp_grid": 7,            # froglight spacing in the floor course
    "gate": "west",            # the cardinal the park's own front gate lies on
    "title": None,
    "arms": None,              # fingerpost arms; defaults below
    "rules": None,
    "legend": None,
    "dig_radius": 4,           # the starter pad + its tree, cleared before printing
    "sign": True,
}

FIELD = "stone_bricks"
KERB = "smooth_basalt"
SPOKE = "polished_blackstone_bricks"
HERE = "chiseled_stone_bricks"
PATH = "stone"
LAMP = "ochre_froglight"

# The arms a midway arrival court points with. Every `dest` is checked against
# `wayfinding.known_destinations()` when the post is built, so a module renamed upstream fails
# HERE rather than shipping a sign to a building nobody can find.
DEFAULT_ARMS = [
    {"direction": "west", "dest": "Park Gate", "length": 4},
    {"direction": "north", "dest": "FRONTIER", "length": 4},
    {"direction": "south", "dest": "HOLLOW", "length": 4},
]


# --------------------------------------------------------------------------------- the footprint

def _court_cells(r: int, chamfer: int):
    """The court's own columns as offsets from the arrival cell - an octagon, not a square.

    A square court in an open plot reads as a slab with four corners nobody uses; cutting the
    corners back is what makes it a PLACE. `|dx| + |dz| <= r + (r - chamfer)` is the octagon whose
    corner cut is exactly `chamfer` cells deep along each diagonal.
    """
    lim = r + (r - chamfer)
    return [(dx, dz) for dx in range(-r, r + 1) for dz in range(-r, r + 1)
            if abs(dx) + abs(dz) <= lim]


def _spur_cells(r: int, spur: int, half: int):
    """The four cardinal spurs, as offsets - the paved runs that join the court to the avenues."""
    out = []
    for (dx, dz) in _STEP.values():
        for k in range(1, spur + 1):
            for s in range(-half, half + 1):
                # step out along the cardinal, spread across the perpendicular
                px = dx * (r + k) + (-dz) * s
                pz = dz * (r + k) + (-dx) * s
                out.append((px, pz))
    return sorted(set(out))


def _figure(dx: int, dz: int, r: int) -> str:
    """Which block a court column takes. The figure is drawn in the FLOOR, so nothing a visitor
    can trip on, walk into or lose a sightline to draws any part of it."""
    a, b = abs(dx), abs(dz)
    if a <= 1 and b <= 1:
        return HERE if (a == 0 and b == 0) else SPOKE
    if a == 0 or b == 0:                       # the four spokes, aimed down the four spurs
        return SPOKE if max(a, b) <= r - 2 else KERB
    if max(a, b) >= r - 1:
        return KERB                            # the rim line: a kerb you can SEE, never one you
    if a + b >= (r + (r - 5)) - 1:             # have to walk around - see the module docstring
        return KERB                            # ...and the same line round the chamfered corners
    if a + b in (r - 2, r - 3):
        return SPOKE                           # the ring, broken where the spokes cross it
    return FIELD


def _lamp_at(dx: int, dz: int, grid: int) -> bool:
    """A froglight goes in the floor on a fixed grid - never on the arrival cell itself, which a
    visitor is standing on and which carries the one pale block in the middle of the figure."""
    return dx % grid == 0 and dz % grid == 0 and not (dx == 0 and dz == 0)


# ------------------------------------------------------------------------------ pasting signage

def _canvas_cells(canvas: Canvas) -> dict:
    names = []
    for e in canvas.palette:
        names.append((nbt.state_name(e).split(":")[-1], nbt.state_props(e)))
    ys, zs, xs = np.nonzero(canvas.ids > 0)
    return {(int(x), int(y), int(z)): names[int(canvas.ids[y, z, x])]
            for y, z, x in zip(ys.tolist(), zs.tolist(), xs.tolist())}


def _paste(w: World, canvas: Canvas) -> int:
    """Copy a finished wayfinding canvas into `w` at its own recorded world origin.

    A SIGN IS TWO THINGS IN TWO HALVES OF THE FILE - `_canvas_cells` reads only the block states,
    so a pasted board would ship its wall-sign block with no text on it unless the tile entity
    comes across too. `isthmus._paste` learned this the same way; the decode is the same.
    """
    ox, oy, oz = getattr(canvas, "world_origin", (0, 0, 0))
    cells = _canvas_cells(canvas)
    for (x, y, z), (name, props) in cells.items():
        w.put(x + ox, y + oy, z + oz, name, **props)

    def _plain(msgs):
        out = []
        for m in msgs:
            try:
                out.append(json.loads(m).get("text", ""))
            except (TypeError, ValueError):
                out.append(str(m))
        return out

    for (x, y, z), t in getattr(canvas, "tiles", {}).items():
        if (x, y, z) not in cells:
            continue
        w.sign(x + ox, y + oy, z + oz, front=_plain(t["front"]), back=_plain(t["back"]),
               colour=t.get("colour", "black"), glowing=bool(t.get("glowing")))
    return len(cells)


def _wayfinding(kind: str, **cfg) -> Canvas:
    from . import wayfinding as wf
    return wf.build({"kind": kind, **cfg})


# ------------------------------------------------------------------------------------ sightlines

def _sightline(w: World, at, direction, limit: int) -> int:
    """How far a visitor standing on the arrival cell can actually SEE along one cardinal, at eye
    level, through what this design builds. Measured, never intended: a court whose own map board
    stands in the sightline it was sited to preserve looks identical in every render.
    """
    x, y, z = at
    dx, dz = _STEP[direction]
    for k in range(1, limit + 1):
        for h in (0, 1):                       # feet course and eye course
            if w.has(x + dx * k, y + h, z + dz * k):
                return k - 1
    return limit


# ----------------------------------------------------------------------------------- the builder

def _court(w: World, p: dict, ctx) -> dict:
    cx, cy, cz = (int(v) for v in p["at"])
    pal = LANDS[p["land"]]
    r = max(7, int(p["radius"]))
    chamfer = max(0, min(int(p["chamfer"]), r - 3))
    spur = max(1, int(p["spur"]))
    half = max(1, int(p["spur_half"]))
    clear = max(2, int(p["clear"]))
    grid = max(3, int(p["lamp_grid"]))
    floor = cy - 1

    # 1. THE COURT FLOOR, with the figure drawn in it.
    court = _court_cells(r, chamfer)
    lamps = []
    for (dx, dz) in court:
        if _lamp_at(dx, dz, grid):
            w.put(cx + dx, floor, cz + dz, LAMP)
            lamps.append([cx + dx, floor, cz + dz])
        else:
            w.put(cx + dx, floor, cz + dz, _figure(dx, dz, r))

    # 2. THE SPURS. Paved in plain stone so they read as road rather than as court, which is what
    #    tells a visitor these are the ways out. Anything already laid stays: a spur crossing the
    #    court's own kerb must not punch a hole in the figure.
    spurs = []
    for (dx, dz) in _spur_cells(r, spur, half):
        if not w.has(cx + dx, floor, cz + dz):
            w.put(cx + dx, floor, cz + dz, PATH)
            spurs.append((dx, dz))

    # 3. THE LAMP STANDARDS, on the chamfered corners - off every spoke and every spur, so no
    #    sightline pays for them. A standing lantern on a capped post: a HANGING lantern needs a
    #    full block over it, which in the open air of a court is a block hanging on nothing.
    posts = []
    k = r - 3
    for sx in (-1, 1):
        for sz in (-1, 1):
            x, z = cx + sx * k, cz + sz * k
            for h in range(0, 3):
                w.put(x, cy + h, z, pal["trim"] if h == 2 else FIELD)
            w.put(x, cy + 3, z, pal["light"], hanging="false", waterlogged="false")
            posts.append([x, cy, z])

    # 4. THE SIGNAGE, all three pieces sited rather than written. They stand on the far rim from
    #    the gate: the gate is west, so east is what a visitor turns to look at when they have
    #    finished looking down the avenue, and nothing that matters is east of here - X 97640+ is
    #    the railway's own corridor.
    gate = p.get("gate") if p.get("gate") in _STEP else "west"
    board_face = park._BACK[gate]              # the boards read back down the gate axis
    bdx, bdz = _STEP[board_face]
    edge = r - 1
    title = str(p.get("title") or f"{p['land'].upper()} MAP").upper()

    built = {}
    mb = _wayfinding("mapboard", land=p["land"], zone=p["land"], facing=gate,
                     at=[cx + bdx * edge - bdz * 2, cy, cz + bdz * edge + bdx * 2],
                     width=9, rows=5, title=title,
                     legend=list(p.get("legend") or ["YOU ARE HERE", "", "", ""]))
    built["mapboard"] = _paste(w, mb)

    nb = _wayfinding("noticeboard", land=p["land"], facing=gate,
                     at=[cx + bdx * edge + bdz * 7, cy, cz + bdz * edge - bdx * 7],
                     rules=list(p.get("rules") or
                                ["OPEN ALL HOURS", "RIDES ARE FREE", "MIND THE VOID"]))
    built["noticeboard"] = _paste(w, nb)

    # THE FINGERPOST STANDS ON A DIAGONAL, never on a spoke: on one it would be the first thing a
    # visitor walks into leaving the court, and it would close the sightline the court exists to
    # keep open. Four cells out on the diagonal is inside the court and outside every spur.
    arms = list(p.get("arms") or DEFAULT_ARMS)
    fp = _wayfinding("fingerpost", land=p["land"], at=[cx + 4, cy, cz + 4], arms=arms)
    built["fingerpost"] = _paste(w, fp)

    # 5. THE ARRIVAL CELL ITSELF IS LEFT EMPTY, and it is asserted rather than assumed - the whole
    #    finding this module exists for is a design that filled it without noticing.
    for h in range(clear):
        if w.has(cx, cy + h, cz):
            raise ValueError(f"the arrival cell ({cx},{cy + h},{cz}) is not clear - "
                             "a visitor would arrive inside this design")

    sight = {d: _sightline(w, (cx, cy, cz), d, r + spur) for d in _STEP}

    # 6. THE DIG LIST: the starter pad and its tree, which a printer can never place over.
    dr = max(0, int(p["dig_radius"]))
    dig = [[cx + dx, floor + h, cz + dz]
           for dx in range(-dr, dr + 1) for dz in range(-dr, dr + 1)
           for h in range(0, clear + 1)]

    return {
        "kind": "arrival", "radius": r, "chamfer": chamfer, "spur": spur,
        "arrival_cell": [cx, cy, cz], "floor_y": floor,
        "court_columns": len(court), "spur_columns": len(spurs),
        "lamps": lamps, "posts": posts, "signage": built,
        "sightlines": sight, "gate": gate, "headroom": clear,
        "footprint": [cx - r - spur, cz - r - spur, cx + r + spur, cz + r + spur],
        "dig": dig,
        "contract": "a level court centred on the island's own arrival cell, that cell left "
                    "clear to the sky, four paved ways out, and a map, a post and a board "
                    "naming real destinations - so a visitor lands on ground and can see where "
                    "to walk",
        "unverified": [
            "the skyblock starter CHEST is not on the dig list - a chest is a protected block "
            "everywhere else in this project and is not this design's to break. Move it before "
            "printing.",
        ],
    }


BUILDERS = {"court": _court}


def build(cfg: dict, donors=None) -> Canvas:
    p = {**ARRIVAL, **cfg}
    if not p.get("at"):
        raise ValueError("arrival needs params.at = [x, y, z] of the ARRIVAL CELL - the island's "
                         "own origin, one course above the floor block")
    if p["kind"] not in BUILDERS:
        raise ValueError(f"unknown arrival kind {p['kind']!r}; have {sorted(BUILDERS)}")
    if p["land"] not in LANDS:
        raise ValueError(f"unknown land {p['land']!r}; have {sorted(LANDS)}")
    if p.get("gate") not in _STEP:
        raise ValueError(f"gate must name a cardinal, one of {sorted(_STEP)}")

    w = World()
    ctx = Ctx(p["under"]) if p.get("under") else None
    meta = BUILDERS[p["kind"]](w, p, ctx)

    for (x, y, z), t in w.signs.items():
        for line in list(t["front"]) + list(t["back"]):
            if len(str(line)) > SIGN_WIDTH:
                raise ValueError(f"sign line {line!r} at {(x, y, z)} is wider than a sign")

    return w.canvas({
        "kind": f"arrival/{p['kind']}",
        "land": p["land"],
        "facing": p.get("gate"),
        "contract": meta.get("contract", ""),
        "unverified": meta.get("unverified", []),
        **{k: v for k, v in meta.items() if k not in ("contract", "unverified")},
    })
