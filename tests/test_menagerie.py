"""The Claim Lake Menagerie: the whole lot, four DIFFERENT habitats, and no silent refusals.

The first build of this design was four identical pens in a row on 45% of its lot, and every
offline check in this repo passed it - because nothing here asks whether a design uses the ground
it was given or whether its four parts are four different things. Both are contracts now.

The rest of this file pins the failures the rebuild actually shipped before it worked, each of
which produced a clean audit and a wrong build:

  * FIVE SIGNS WERE REFUSED IN SILENCE. `park._sign` returns False when there is no block behind
    the board, and four stall signs were written over a fence GATE - a gate is one course tall
    and there is nothing above it to hang from.
  * THE LOOKOUT'S BALUSTRADE WAS BUILT INSIDE ITS OWN DECK. `_rail` had no base course, so the
    posts and the canopy above them shipped as a 32-cell free-floating cluster.
  * THE BARN'S AISLE LANTERNS HUNG OFF SINGLE BEAM CELLS IN MID-AIR. A barn is open from the
    floor to the wall plate; a block at plate height touches nothing unless it actually spans.

Run: python -m pytest tests/test_menagerie.py -q
"""
import os
import sys
from collections import Counter, deque

import numpy as np
import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcbuild import blocks, palette                                        # noqa: E402
from mcbuild.gen import menagerie as M                                     # noqa: E402
from mcbuild.gen.park import _Frame                                        # noqa: E402

CFG = os.path.join(os.path.dirname(__file__), "..", "configs", "claim_lake_menagerie.yaml")

#: The lot `tools/park_lots.py` measures here, and the frontage verge that is NOT part of it -
#: `Park Ways` stands three lamp standards on V129, one of them on the lot's own midline.
LOT_V, LOT_U = (128, 153), (173, 211)
LAMP_ROW = 129
LAMP_U = (175, 192, 209)

_CACHE = {}


def _built():
    if "c" not in _CACHE:
        params = {**M.MENAGERIE, **yaml.safe_load(open(CFG, encoding="utf-8"))["params"]}
        c = M.build(dict(params))
        names = {i: e.value["Name"].value.split(":")[-1] for i, e in enumerate(c.palette)}
        ox, oy, oz = c.world_origin
        cells = {}
        for x in range(c.sx):
            for y in range(c.sy):
                for z in range(c.sz):
                    v = int(c.ids[y, z, x])
                    if v and "air" not in names[v]:
                        cells[(x + ox, y + oy, z + oz)] = names[v]
        _CACHE["c"] = (c, params, _Frame(params), cells)
    return _CACHE["c"]


def _at(f, i, d, h):
    return f.at(i, d, h)


# ------------------------------------------------------------------ it uses the ground it has

def test_it_fills_the_whole_lot_and_stays_inside_it():
    """THE COMPLAINT WAS THE FOOTPRINT, so the footprint is the first thing asserted.

    Four pens in a row used 455 of this lot's 1,014 columns. A design that shrinks back into a
    strip passes every other check in this repo, which is exactly why this one exists.
    """
    _c, p, _f, cells = _built()
    cols = {(x - 97500, z - 80300) for (x, _y, z) in cells}
    vs = {v for (v, _u) in cols}
    us = {u for (_v, u) in cols}
    assert LOT_V[0] <= min(vs) and max(vs) <= LOT_V[1], f"outside the lot in V: {min(vs)}-{max(vs)}"
    assert LOT_U[0] <= min(us) and max(us) <= LOT_U[1], f"outside the lot in U: {min(us)}-{max(us)}"
    assert len(cols) == p["width"] * p["depth"] == 936, len(cols)
    lot = (LOT_V[1] - LOT_V[0] + 1) * (LOT_U[1] - LOT_U[0] + 1)
    assert len(cols) / lot > 0.90, f"only {100 * len(cols) / lot:.0f}% of the lot is used"


def test_it_keeps_off_the_park_ways_lamp_row():
    """The frontage verge is not spare ground: one of `Park Ways`' three lamp standards stands on
    this lot's own midline, and a gateway built round a lamp post is a gateway with a post in the
    doorway. The design starts a row behind them, so the lamps light the frontage for free."""
    _c, _p, _f, cells = _built()
    for u in LAMP_U:
        clash = [(x, y, z) for (x, y, z) in cells if x - 97500 == LAMP_ROW and z - 80300 == u]
        assert not clash, f"stands in a Park Ways lamp column at U{u}: {clash[:3]}"
    assert min(x for (x, _y, _z) in cells) - 97500 > LAMP_ROW


# ------------------------------------------------------------------ four things, not one thing

def _quadrant(cells, f, i0, i1, d0, d1):
    box = {f.at(i, d, 0)[0::2] for i in range(i0, i1 + 1) for d in range(d0, d1 + 1)}
    return Counter(n for (x, _y, z), n in cells.items() if (x, z) in box)


def test_the_four_habitats_are_four_different_things():
    """THE POINT OF THE REBUILD. Four identical rectangles read as one rectangle however large
    you draw them - `gen/casino.py` measured eighteen game rooms at 94-99% alike and found two
    games wearing four names. Every pair of quadrants here must differ in what it is MADE OF.
    """
    _c, p, f, cells = _built()
    W, D = p["width"], p["depth"]
    sp0, sp1 = W // 2 - p["spine"] // 2, W // 2 + p["spine"] // 2
    front_d = max(9, (D - 8) * 5 // 8)
    fr0, fr1 = 4, 3 + front_d
    bk0, bk1 = fr1 + 4, D - 2
    quads = {
        "barn":   _quadrant(cells, f, 1, sp0 - 2, fr0, fr1),
        "pond":   _quadrant(cells, f, sp1 + 2, W - 2, fr0, fr1),
        "meadow": _quadrant(cells, f, 1, sp0 - 2, bk0, bk1),
        "aviary": _quadrant(cells, f, sp1 + 2, W - 2, bk0, bk1),
    }
    for name, q in quads.items():
        assert sum(q.values()) > 120, f"{name} is nearly empty: {sum(q.values())}"
    names = sorted(quads)
    for a in range(len(names)):
        for b in range(a + 1, len(names)):
            x, y = quads[names[a]], quads[names[b]]
            shared = sum((x & y).values()) / max(sum(x.values()), sum(y.values()))
            assert shared < 0.60, f"{names[a]} and {names[b]} are {100 * shared:.0f}% the same"


def test_the_skyline_is_not_flat():
    """Architecture below ~6 courses dissolves into ground noise on this palette - the Frontier's
    own finding. The first build topped out at THREE, so height is a contract, not a hope."""
    _c, _p, _f, cells = _built()
    top = {}
    for (x, y, z) in cells:
        top[(x, z)] = max(top.get((x, z), -99), y)
    hs = [h - 202 for h in top.values()]
    assert max(hs) >= 15, f"nothing reaches 15 courses; tallest is {max(hs)}"
    assert sum(1 for h in hs if h >= 6) >= 120, "too little of the lot stands 6 courses or more"
    assert len({h for h in hs if h >= 4}) >= 5, "the tall half is all at one height"


# ------------------------------------------------------------------ it is buildable and honest

def test_it_is_one_piece_with_nothing_floating():
    """A litematic that ships in three pieces ships two of them hanging in void. The barn's aisle
    lanterns and the lookout's canopy each did exactly that before this passed."""
    c, _p, _f, _cells = _built()
    solid = c.ids != 0
    seen = np.zeros_like(solid)
    start = tuple(int(v) for v in np.argwhere(solid)[0])
    q, n = deque([start]), 0
    seen[start] = True
    while q:
        y, z, x = q.popleft()
        n += 1
        for dy, dz, dx in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            p = (y + dy, z + dz, x + dx)
            if all(0 <= p[k] < solid.shape[k] for k in range(3)) and solid[p] and not seen[p]:
                seen[p] = True
                q.append(p)
    assert n == int(solid.sum()), f"{int(solid.sum()) - n} cells in other components"


def test_every_sign_is_actually_PLACED():
    """`park._sign` returns False rather than raising when there is nothing behind the board, and
    this repo has shipped four silently-refused signs that way. Five of this design's sixteen were
    refused on the first pass and the only symptom was a `signed: false` nobody reads."""
    c, _p, _f, cells = _built()
    assert c.meta["signed"] is True, "a sign was refused - see the barn and the gateway"
    assert c.meta["barn"]["signed"] is True
    assert sum(1 for n in cells.values() if n.endswith("_wall_sign")) >= 14


def test_the_pond_is_bedded_and_enclosed():
    """A pool must be BOTH bedded and enclosed or it is not still water in six months: a solid
    block under every water cell, and a solid cell on every horizontal side."""
    _c, _p, _f, cells = _built()
    water = {k for k, n in cells.items() if n == "water"}
    assert len(water) > 40, f"the pond is only {len(water)} cells"
    for (x, y, z) in water:
        assert (x, y - 1, z) in cells, f"no bed under the water at {(x, y, z)}"
        for (dx, dz) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            p = (x + dx, y, z + dz)
            assert p in cells, f"the pond leaks at {p}"


def test_every_plant_roots_in_the_dirt_family():
    """Rule 11, and the Lowland Thicket's 173 placement problems: a plant roots in the dirt family
    and nowhere else. Moss carpet is the exception - a carpet sits on anything."""
    _c, _p, _f, cells = _built()
    from mcbuild.audit import DIRT_LIKE
    growing = {"short_grass", "fern", "large_fern", "azalea", "flowering_azalea", "dandelion",
               "poppy", "oxeye_daisy", "cornflower", "sugar_cane"}
    for (x, y, z), n in cells.items():
        if n not in growing:
            continue
        below = cells.get((x, y - 1, z))
        ok = below in DIRT_LIKE or below == n or (n == "sugar_cane" and below == "sand")
        assert ok, f"{n} rooted in {below} at {(x, y, z)}"


def test_nothing_expensive_is_used_in_bulk():
    """The park's material policy. Hay is the one expensive block here and it is the one block
    that says farmyard, so it is a handful of markers and never a surface."""
    _c, _p, _f, cells = _built()
    exp = Counter(n for n in cells.values() if palette.tier(n) == "expensive")
    assert sum(exp.values()) <= 8, exp
    bad = [n for n in set(cells.values()) if blocks.exists(n) and not blocks.spendable(n)]
    assert not bad, f"currency blocks used as material: {bad}"


def test_every_enclosure_has_a_gate_onto_a_path():
    """A pen with no gate is a fence you look over; the point of this rebuild is that you walk
    INTO it. Every gate must also open onto a cell you can stand on."""
    _c, _p, _f, cells = _built()
    gates = [k for k, n in cells.items() if n.endswith("_fence_gate")]
    assert len(gates) >= 6, f"only {len(gates)} gates"
    for (x, y, z) in gates:
        open_side = [(dx, dz) for (dx, dz) in ((1, 0), (-1, 0), (0, 1), (0, -1))
                     if (x + dx, y, z + dz) not in cells and (x + dx, y - 1, z + dz) in cells]
        assert len(open_side) >= 2, f"the gate at {(x, y, z)} is not a way through"


def test_the_sidecar_still_says_it_places_no_animal():
    """A litematic is blocks, not entities. The first version said so and the rebuild must keep
    saying it - a design that implied otherwise would be lying in its own sidecar."""
    c, _p, _f, _cells = _built()
    assert any("LIVE STOCK" in u for u in c.meta["unverified"])
    assert "no animal is placed" in c.meta["contract"]
