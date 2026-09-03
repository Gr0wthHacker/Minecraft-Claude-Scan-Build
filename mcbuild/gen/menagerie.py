"""A small petting-zoo row: fenced paddocks a visitor walks past and INTO, not a redstone game.

Jack, after the shooting range's pit floor left a bare service slab trailing off its own back:
"i dont think we can do this in a clean way as specified, we should probably find something else
to put in this area, maybe a small zoo where we put actual MC animals." So this brings no hidden
machine and no concealed pit - the whole footprint is the visible thing, which is what makes it
safe to fit into a lot that already burned one design for being deeper than it looked.

**THE PENS ARE INFRASTRUCTURE, NOT LIVESTOCK.** A litematic places BLOCKS; it cannot place a
living mob, and this generator does not pretend to - `blocks.exists("sheep")` is not even a
question the block registry can answer. What ships is four fenced paddocks, each with a shelter,
a hay marker and a gate, ready for Jack to walk animals into (lead them with their breeding item,
or a spawn egg) after the build stands. Stated once here rather than found out the hard way, the
same rule `gen/arcade.py` already states about entities it cannot fire into a target block.

GEOMETRY is `gen/park.py`'s `_Frame`, unchanged - a paddock row sits on a lot exactly as a game
console or a market stall does:

    at       the row's FRONT-LEFT floor corner (world x, y, z), on the STANDING course
    facing   the direction the walkway looks out - a visitor approaching stands in +facing
    i        along the row, left to right          d   from the walkway INTO the pens

A ROW, NOT A RING. Four pens side by side behind one walkway is a shape that fits a shoulder lot
without needing depth behind it the way a hidden machine does - the whole build is `walkway (1) +
fence (1) + pen (pen_depth) + fence (1)` deep, and every course of it is something a visitor can
see, which is the property the last design in this lot did not have.
"""
from __future__ import annotations

from .canvas import Canvas
from .park import LANDS, SIGN_WIDTH, _STEP, _Frame, _sign
from .streetfurniture import _fence_props
from .vertical import Ctx, World

MENAGERIE = {
    "under": None,
    "at": None,                 # world (x, y, z): the walkway's FRONT-LEFT floor corner
    "facing": "west",
    "land": "midway",
    "title": None,
    "pens": None,                # [(name, feed), ...] - None = the default four
    "pen_width": 7,
    "pen_depth": 10,
    "sign": True,
}
DEFAULTS = MENAGERIE

#: (display name, sign lines beneath it) - what a visitor is told each pen is FOR, since a fenced
#: square of moss with nothing in it yet is not self-explanatory. `feed` names the item Jack leads
#: an animal in with, so the sign is honest about what the pen needs rather than what it has.
PENS = [
    ("SHEEP MEADOW", "lead in with wheat"),
    ("COW PASTURE", "lead in with wheat"),
    ("PIG STY", "lead in with a carrot"),
    ("CHICKEN COOP", "lead in with seeds"),
]


def _shelter(w: World, f, pal: dict, i0: int, d0: int) -> None:
    """A plain three-by-three lean-to: four posts, a flat roof. Deliberately unremarkable - the
    void tower's own rule, that regularity reads as architecture and novelty does not, applies
    just as much to a shed as to a ruin."""
    for di, dd in ((0, 0), (2, 0), (0, 2), (2, 2)):
        for h in (0, 1):
            w.put(*f.at(i0 + di, d0 + dd, h), pal["post"])
    for di in range(3):
        for dd in range(3):
            w.put(*f.at(i0 + di, d0 + dd, 2), pal["slab"], type="bottom", waterlogged="false")


def build(cfg: dict, donors=None) -> Canvas:
    p = {**MENAGERIE, **cfg}
    if not p.get("at"):
        raise ValueError("menagerie needs params.at = [x, y, z] of the walkway's front-left corner")
    if p["facing"] not in _STEP:
        raise ValueError(f"facing must be one of {sorted(_STEP)}")
    if p["land"] not in LANDS:
        raise ValueError(f"unknown land {p['land']!r}; have {sorted(LANDS)}")

    f = _Frame(p)
    pal = LANDS[p["land"]]
    w = World()
    Ctx(p["under"]) if p.get("under") else None  # unused here; kept for the generator protocol

    pens = p.get("pens") or PENS
    pen_w = max(5, int(p["pen_width"]))
    pen_d = max(6, int(p["pen_depth"]))
    n = len(pens)

    # ---- the plots. divider column i, per pen: i0 = divider + 1, i1 = i0 + pen_w - 1
    dividers = [k * (pen_w + 1) for k in range(n + 1)]
    width = dividers[-1] + 1
    depth = pen_d + 2               # fence row (d=0) + pen interior + fence row (d=pen_d+1)

    # ---- the ground. EVERY course of this design brings its own floor, pens included - the
    # first attempt left the pens on the world's own moss with nothing under a shelter or a hay
    # marker in the design's OWN cells, and it shipped as six free-floating clusters needing
    # scaffold. `moss_block` is the pasture surface (grass and dirt are both currency here), so
    # paving the pens costs nothing and reads as ground rather than as a paved plaza.
    for i in range(-1, width + 1):
        for d in range(-1, depth):
            w.put(*f.at(i, d, -1), pal["trim"] if i in (-1, width)
                  else (pal["path"] if d == -1 else "moss_block"))

    # ---- the fence network, built as ONE set so `_fence_props` connects it correctly rather
    # than leaving lone-post nubs at every pen boundary.
    fence, posts, gates = set(), set(), []
    for k, div in enumerate(dividers):
        for d in range(0, depth):
            fence.add((div, d))
        posts.add((div, 0))
        posts.add((div, depth - 1))
    gate_is = []
    for k in range(n):
        i0, i1 = dividers[k] + 1, dividers[k + 1] - 1
        gate_i = (i0 + i1) // 2
        gate_is.append(gate_i)
        for i in range(i0, i1 + 1):
            fence.add((i, 0))
            fence.add((i, depth - 1))
        fence.discard((gate_i, 0))          # the gate itself, not a fence cell
        gates.append((gate_i, 0))

    for (i, d) in sorted(fence):
        if (i, d) in posts:
            for h in (0, 1):
                w.put(*f.at(i, d, h), pal["post"])
            continue
        w.put(*f.at(i, d, 0), pal["fence"], **_fence_props(f, fence, i, d))
    for (i, d) in gates:
        w.put(*f.at(i, d, 0), pal["gate"], facing=f.back, open="false", powered="false")

    # ---- each pen: a shelter toward the back, a hay marker, a sign on its own post at the gate
    signed = True
    for k, (name, feed) in enumerate(pens):
        i0 = dividers[k] + 1
        mid = (dividers[k] + dividers[k + 1]) // 2
        _shelter(w, f, pal, mid - 1, depth - 5)
        w.put(*f.at(mid, depth - 6, 0), "hay_block", axis="y")
        w.put(*f.at(mid - 2, 2, 0), "hay_block", axis="y")

        gate_i = gate_is[k]
        w.put(*f.at(gate_i, 0, 1), pal["post"])
        title = str(name).upper()
        signed &= _sign(w, f, pal, gate_i, -1, 1, f.facing,
                         [title[:SIGN_WIDTH], feed[:SIGN_WIDTH]])
        # A STANDING LANTERN ON THE SIGN'S OWN POST, not a hung one. `_hang_light` needs a solid
        # block ABOVE it for the lantern to hang from, and nothing this generator builds reaches
        # that high in open air - the first pass hung six of them from nothing, and they shipped
        # as six free-floating clusters. Standing on the post's own top face needs no second
        # support block at all.
        w.put(*f.at(gate_i, 0, 2), pal["light"], hanging="false", waterlogged="false")

    for i in (dividers[0], dividers[-1]):
        w.put(*f.at(i, 0, 2), pal["light"], hanging="false", waterlogged="false")

    return w.canvas({
        "kind": "menagerie",
        "footprint": [width, depth + 1],
        "land": p["land"],
        "facing": p["facing"],
        "pens": [n for n, _f in pens],
        "signed": bool(signed),
        "contract": (f"{n} fenced paddocks, each with a shelter, a feed marker, a gate and a "
                      "named sign; no animal is placed by this generator - a litematic is "
                      "blocks, not entities, and the pens are stocked in world, by hand"),
        "unverified": ["NOTHING HERE IS LIVE STOCK. Every pen is empty on paste; the sign names "
                        "what to lead in and with what."],
    })
