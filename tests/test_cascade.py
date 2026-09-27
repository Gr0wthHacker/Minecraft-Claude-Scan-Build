"""THE MIDWAY CASCADE's contracts - the ones that can be proved offline, and no more.

`civic._cascade` is the park's centrepiece: an arcaded drum in a moat, six of its eight bays
carrying a waterfall, a dry chamber inside, and a chime. Four of those are checkable here and one
is not, and the split is the point of this file.
"""
import json
import math
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcbuild import fluids, schem                                  # noqa: E402
from mcbuild.gen import civic                                      # noqa: E402
from mcbuild.gen.vertical import World                             # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHIPPED = os.path.join(ROOT, "out", "PF Midway Cascade.litematic")
WORLD = os.path.join(ROOT, "out", "Park Complete.litematic")

R_DRUM, R_BOWL, R_DISH, R_KERB, R_PAD = 8, 10, 4, 11, 13
PIER_TOP, TOP = 8, 9


def _cfg(**kw):
    return {**civic.CIVIC, "at": [0, 64, 0], "kind": "cascade", "land": "midway",
            "facing": "west", "width": 71, "depth": 41, "centre_i": -1, "seed": 7, **kw}


@pytest.fixture(scope="module")
def built():
    p = _cfg()
    w = World()
    meta = civic.BUILDERS["cascade"](w, p, None)
    return w, civic._Frame(p), p, meta


def _cells(w):
    return {pos: name for pos, (name, _pr) in w.cells.items()}


def _ci_cd(p):
    return p["width"] // 2 + int(p.get("centre_i", 0)), p["depth"] // 2


# --------------------------------------------------------------------------- the water

def test_the_basin_is_watertight_on_its_own(built):
    """THE ONE CONTAINMENT PROPERTY THAT CAN BE PROVED HERE, and it is proved rather than argued.

    Every moat cell has a solid bed one course under it and a full one-radius `_annulus` rim on
    both sides, so flooding from the moat's own sources must reach the moat's own cells and
    nothing else. The park is a ONE-BLOCK SKIN over open void and a hole here is a drain; the log
    flume drained 199,959 cells to Y-1908 while every render, audit and bill of materials passed.
    """
    w, f, p, _meta = built
    cells = _cells(w)
    # THE LAWN IS THE MOAT'S BED AND THIS DESIGN PLACES NONE OF IT, so the generator's raw output
    # has open void under the water and would "leak" by construction. The park's own lawn is what
    # goes there; the test supplies it, and `test_the_shipped_basin_has_ground_under_every_water
    # _cell` is what proves the real one is present.
    for dx in range(-40, 41):
        for dz in range(-50, 51):
            cells.setdefault((f.x + dx, f.y - 2, f.z + dz), "moss_block")
    moat_water = [q for q, n in cells.items() if n == "water" and q[1] < f.y]
    assert moat_water, "the moat has no water at all"
    lv = fluids.spread(cells, moat_water)
    stray = [q for q in lv if cells.get(q) != "water"]
    assert not stray, f"the moat leaks into {len(stray)} cells, e.g. {sorted(stray)[:5]}"


def test_every_moat_cell_stands_on_something(built):
    """ITS BED IS THE PARK'S OWN LAWN, WHICH IS A DEPENDENCY, SO IT IS CHECKED.

    The design deliberately places no bed - that is what keeps it free of a dig list - so the lawn
    under it has to be there. Here that is asserted against the design's own pad; the composite
    check against the shipped park is `test_the_shipped_basin_has_ground_under_every_water_cell`.
    """
    w, f, p, _meta = built
    cells = _cells(w)
    ci, cd = _ci_cd(p)
    for (di, dd) in set(civic._cells(0, R_BOWL, civic._disc)) - set(
            civic._cells(0, R_DRUM, civic._disc)):
        pos = f.at(ci + di, cd + dd, -1)
        if cells.get(pos) != "water":
            continue
        under = (pos[0], pos[1] - 1, pos[2])
        assert under not in cells or cells[under] != "water", \
            "a moat cell is stacked on another - the moat is one course deep by design"


def test_the_falls_actually_fall(built):
    """THREE STILL POOLS IS THE LOG FLUME'S OWN FAILURE - it audits clean, costs nothing, looks
    exactly like a fountain in every render here, and never moves. Seeded from ONLY the bowl's own
    sources, water must genuinely leave it and be FALLING several courses down."""
    w, f, p, meta = built
    cells = _cells(w)
    ci, cd = _ci_cd(p)
    bowl = [f.at(ci + di, cd + dd, TOP + 1)
            for (di, dd) in civic._cells(0, R_BOWL - 1, civic._disc)]
    bowl = [q for q in bowl if cells.get(q) == "water"]
    lv = fluids.spread(cells, bowl)
    falling = [q for q, l in lv.items() if l == fluids.FALLING]
    assert len(falling) > 60, f"only {len(falling)} falling cells - the bowl is a still pond"
    drop = (f.y + TOP + 1) - min(q[1] for q in falling)
    assert drop >= 8, f"the water only falls {drop} courses; it should clear the whole drum"


def test_a_one_cell_notch_would_not_have_worked_on_a_diagonal(built):
    """THE BUG THIS PINS SHIPPED ONCE AND PASSED EVERY CHECK. `_annulus` is one RADIUS wide, which
    on a diagonal is more than one CELL wide: a single notch at (7,7) has r 9.90 and all four of
    its orthogonal neighbours are at 9.22, still rim, so the bowl's water never reached it. Four of
    the six falls existed only in the block count. Every notch must touch water."""
    w, f, p, _meta = built
    cells = _cells(w)
    ci, cd = _ci_cd(p)
    rim = set(civic._annulus(R_BOWL, civic._disc))
    gaps = [(di, dd) for (di, dd) in rim
            if f.at(ci + di, cd + dd, TOP + 1) not in cells]
    assert gaps, "the bowl has no notches at all"
    for (di, dd) in gaps:
        touching = any(
            cells.get(f.at(ci + di + ax, cd + dd + az, TOP + 1)) == "water"
            for (ax, az) in ((1, 0), (-1, 0), (0, 1), (0, -1)))
        assert touching or any(
            (di + ax, dd + az) in gaps for (ax, az) in ((1, 0), (-1, 0), (0, 1), (0, -1))), \
            f"notch {(di, dd)} touches neither water nor another notch: it can never spill"


# --------------------------------------------------------------------------- the structure

def test_it_is_one_piece(built):
    """A crown standing on the dish's WATER is not standing on anything, and shipped as a
    fifteen-cell floating component the first time."""
    w, _f, _p, _meta = built
    cells = _cells(w)
    # WATER COUNTS, which is what the pipeline's own component check does: the moat is a ring of it
    # between the drum and the plaza, so excluding it cuts the model in two and reports a defect
    # that is not there.
    solid = set(cells)
    seen, stack = {next(iter(solid))}, [next(iter(solid))]
    while stack:
        x, y, z = stack.pop()
        for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            n = (x + d[0], y + d[1], z + d[2])
            if n in solid and n not in seen:
                seen.add(n)
                stack.append(n)
    assert len(seen) == len(solid), f"{len(solid) - len(seen)} cells are detached from the mass"


def test_the_two_doors_stay_dry(built):
    """You never have to walk through a waterfall to get in: the two bays on the cross axis carry
    the causeways and are the two that do not spill."""
    _w, _f, _p, meta = built
    assert meta["falls"] > 0
    assert meta["bays"] == 8


def test_the_walk_arms_reach_both_ends_of_the_lot(built):
    """This lot has no street through it - `Park Ways` draws the spine and the back promenade and
    nothing between - so the walk from the Welcome Court's back edge to the promenade in front of
    the wheel is this design's to lay, and it has to reach both ends or it joins nothing."""
    w, f, p, _meta = built
    cells = _cells(w)
    D = p["depth"]
    for d in (0, D - 1):
        row = [i for i in range(p["width"])
               if f.at(i, d, -1) in cells]
        assert row, f"nothing at all is laid at depth {d} - the arms do not reach the lot's edge"


# --------------------------------------------------------------------------- the chime

def test_the_chime_is_wired_and_sounds_in_sequence(built):
    """Five note blocks, each next to a wire cell, with a repeater between every pair - so they
    sound one after another off one button rather than all at once."""
    w, _f, _p, meta = built
    cells = _cells(w)
    notes = [q for q, n in cells.items() if n == "note_block"]
    assert len(notes) == 5 == meta["notes"]
    assert len(set(meta["chime_notes"])) == 5, "two notes are the same pitch"
    for q in notes:
        under = cells.get((q[0], q[1] - 1, q[2]))
        assert under == "packed_ice", \
            "the instrument comes from the block underneath; packed ice is what makes it a chime"
        assert (q[0], q[1] + 1, q[2]) not in cells, "a note block needs air above it to sound"
        assert any(cells.get((q[0] + dx, q[1], q[2] + dz)) == "redstone_wire"
                   for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1))), \
            "a note block with no wire beside it is never powered"
    assert len([q for q, n in cells.items() if n == "repeater"]) >= 4, \
        "no repeaters means all five sound at once, which is a chord and not a chime"
    assert [q for q, n in cells.items() if n == "stone_button"], "nothing plays it"


# --------------------------------------------------------------------------- against the world

@pytest.mark.skipif(not (os.path.exists(SHIPPED) and os.path.exists(WORLD)),
                    reason="the design or the park is not shipped")
def test_the_shipped_basin_has_ground_under_every_water_cell():
    """THE DEPENDENCY, CHECKED IN THE COMPOSITE. The moat's bed is the park's own lawn and this
    design places none of it. The park is a one-block skin over open void, so a single missing
    lawn cell under the moat is not a blemish, it is a drain."""
    m = schem.load(SHIPPED)
    o = json.load(open(SHIPPED.replace(".litematic", ".scan.json")))["origin"]
    names = {i: e.value["Name"].value.split(":")[-1] for i, e in enumerate(m.palette)}
    ms = m.solid()
    design = {}
    for y, z, x in zip(*ms.nonzero()):
        design[(int(x) + o["x"], int(y) + o["y"], int(z) + o["z"])] = names[int(m.ids[y, z, x])]

    w = schem.load(WORLD)
    wo = json.load(open(WORLD.replace(".litematic", ".scan.json")))["origin"]
    ws = w.solid()

    def solid_at(x, y, z):
        iy, iz, ix = y - wo["y"], z - wo["z"], x - wo["x"]
        return (0 <= iy < ws.shape[0] and 0 <= iz < ws.shape[1] and 0 <= ix < ws.shape[2]
                and bool(ws[iy, iz, ix]))

    holes = []
    for (x, y, z), n in design.items():
        if n != "water":
            continue
        under = (x, y - 1, z)
        if design.get(under) is None and not solid_at(*under):
            holes.append((x, y, z))
    assert not holes, f"{len(holes)} water cells have nothing under them, e.g. {holes[:5]}"
