"""THE PLEASURE GARDEN AT THE HEAD OF MIDWAY COLUMN C, and the four things about it that matter.

`PF Midway Garden` replaced `PF Games Row` and its six consoles - see `mcbuild/gen/midgarden.py`
for the block-by-block reason. What it keeps is the walk, which is the only thing the column ever
actually needed: `Park Ways` paves nothing in V24-99 but the V77 cross walk and two door spurs.

    THE WALK RUNS END TO END     in CONTEXT, because the cross walk that splits it is not ours
    THE BEDS HAVE A WAY IN       a hedged rectangle you cannot step into is a fence
    THE PATTERN IS A PATTERN     mirrored across the walk, and legible rather than scattered
    NOTHING CONTESTS A NEIGHBOUR `PF Park Green` dresses the outer band and keeps it
"""
from __future__ import annotations

import json
from collections import Counter, deque
from functools import lru_cache
from pathlib import Path

import pytest
import yaml

from mcbuild import blocks, palette, schem
from mcbuild.gen import midgarden

ROOT = Path(__file__).resolve().parents[1]
CFG = ROOT / "configs" / "pf_midway_garden.yaml"
WORLD = ROOT / "out" / "Park Complete.litematic"
V0, U0 = 24, 345
LAWN = 202


@lru_cache(maxsize=1)
def _park_y() -> int:
    """A composite's y is a function of the deepest thing in it, not a constant: it went 190 -> 94
    the day a stream put a design under Prismworks. Read from the sidecar, never typed."""
    return int(json.loads((ROOT / "out" / "Park Complete.scan.json").read_text())["origin"]["y"])


def _index(course: int) -> int:
    return course + (LAWN + 1 - _park_y())


def _course(y: int) -> int:
    return y - (LAWN + 1 - _park_y())


@pytest.fixture(scope="module")
def cfg():
    return yaml.safe_load(CFG.read_text())


@pytest.fixture(scope="module")
def built(cfg):
    return midgarden.build(cfg["params"])


@pytest.fixture(scope="module")
def cells(built):
    pal = [e.value["Name"].value.split(":")[-1] for e in built.palette]
    return {(x + V0, y, z + U0): pal[int(built.ids[y, z, x])]
            for y in range(built.sy) for z in range(built.sz) for x in range(built.sx)
            if built.ids[y, z, x]}


PASSABLE = {"air", "moss_carpet", "short_grass", "fern", "poppy", "dandelion", "azalea",
            "oxeye_daisy", "pink_tulip", "cornflower", "glow_lichen", "oak_leaves", "vine",
            "lantern", "oak_wall_sign", "oak_fence", "oak_fence_gate", "torch", "wall_torch"}


def _solid(comp, p):
    n = comp.get(p)
    return n is not None and n.split("[")[0] not in PASSABLE


def _stands(comp, p):
    v, y, u = p
    return (_solid(comp, (v, y - 1, u))
            and not _solid(comp, p) and not _solid(comp, (v, y + 1, u)))


# --------------------------------------------------------------------------- the walk


def test_the_walk_runs_from_the_avenue_to_the_towers_forecourt(cells, cfg):
    """IN CONTEXT. `Park Ways`' cross walk splits this lot at V76-78 and the helter skelter's
    forecourt closes it at V100; the design alone is two pieces and the WALK is one or it is not
    a walk. This is also the test that the column has a spine at all, which is what the Skill
    Arcade took away by filling it wall to wall."""
    if not WORLD.exists():
        pytest.skip("out/Park Complete.litematic is not built")
    m = schem.load(str(WORLD))
    pal = [e.value["Name"].value.split(":")[-1] for e in m.palette]
    comp = {}
    for v in range(V0 - 2, 130):
        for u in range(U0 - 2, U0 + 42):
            for y in range(_index(-1), _index(10)):
                i = int(m.ids[y, u, v])
                if i:
                    comp[(v, _course(y), u)] = pal[i]
    comp.update(cells)
    axis = int(cfg["params"]["axis"])
    start = (V0 + 1, 1, axis)
    assert _stands(comp, start), "the head of the walk is not somewhere a visitor can stand"
    seen, q = {start}, deque([start])
    while q:
        v, y, u = q.popleft()
        for dv, du in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            for dy in (1, 0, -1):
                p = (v + dv, y + dy, u + du)
                if p in seen or not (V0 - 2 <= p[0] < 130 and U0 <= p[2] < U0 + 40
                                     and 0 <= p[1] < 10):
                    continue
                if _stands(comp, p):
                    seen.add(p)
                    q.append(p)
                    break
    for v in (30, 50, 70, 80, 95, 105, 118):
        assert any((v, y, axis) in seen for y in (1, 2)), f"the walk breaks at V{v}"


def test_every_bed_can_be_stepped_into(cells, cfg):
    """A hedged rectangle you cannot enter is a fence with flowers behind it. The hedge is broken
    every nine along each long side, and the gaps have to be REAL - `_Lot.put` returning False on
    a blocked cell would close one silently."""
    for bed in cfg["params"]["beds"]:
        bv0, bu0, bv1, bu1 = bed
        gaps = [v for v in range(bv0, bv1 + 1)
                for u in (bu0, bu1)
                if (v, 1, u) not in cells and (v, 0, u) in cells]
        assert len(gaps) >= 2, f"the bed at V{bv0}-{bv1} U{bu0}-{bu1} has no way in"


def test_the_two_beds_mirror_each_other_across_the_walk(cells, cfg):
    """The motif is a function of the DISTANCE from a bed's own midline, so the pair either side
    of the walk are mirror images by construction. A parterre that differs left and right reads as
    a mistake rather than as a pattern - the frog's own coat lesson, in wool."""
    beds = [tuple(b) for b in cfg["params"]["beds"]]
    west = [b for b in beds if b[1] < int(cfg["params"]["axis"])]
    east = [b for b in beds if b[1] > int(cfg["params"]["axis"])]
    assert len(west) == len(east)
    for w, e in zip(west, east):
        wm, em = (w[1] + w[3]) / 2.0, (e[1] + e[3]) / 2.0
        bad = 0
        for v in range(w[0] + 1, w[2]):
            for d in (-1, 0, 1):
                a = cells.get((v, 1, int(wm + d)))
                b = cells.get((v, 1, int(em + d)))
                aw = (a or "").split("[")[0].endswith("_wool")
                bw = (b or "").split("[")[0].endswith("_wool")
                bad += aw != bw
        assert bad == 0, f"the beds at V{w[0]}-{w[2]} differ in {bad} cells across the walk"


def test_the_pattern_is_a_pattern_and_not_a_scatter(cells, cfg):
    """Hashed per cell the bed came out as random patches of colour - the deck floor's confetti,
    in wool. A motif has RUNS: every bold block belongs to a lozenge, so almost none of them is
    alone."""
    wool = {p for p, n in cells.items() if n.split("[")[0].endswith("_wool")}
    assert wool, "there is no pattern in the beds at all"
    lone = [p for p in wool
            if not any((p[0] + dv, p[1], p[2] + du) in wool
                       for dv, du in ((1, 0), (-1, 0), (0, 1), (0, -1)))]
    assert len(lone) <= 0.05 * len(wool), f"{len(lone)} of {len(wool)} bold blocks stand alone"


# --------------------------------------------------------------------------- the neighbours


def test_it_contests_nothing_that_PF_Park_Green_owns(cells):
    """MEASURED, not assumed: `PF Park Green` holds 105 cells in this lot and 98 of them are at
    U378-384. The beds stop at U377 for exactly that reason, and this is the check that they still
    do. Two designs sharing a cell is a WORK problem - you place a block, the next placement says
    it is wrong, you break it and place it again."""
    f = ROOT / "out" / "PF Park Green.litematic"
    if not f.exists():
        pytest.skip("PF Park Green is not built")
    m = schem.load(str(f))
    o = json.loads((ROOT / "out" / "PF Park Green.scan.json").read_text())["origin"]
    theirs = {(int(x) + o["x"] - 97500, int(y) + o["y"] - (LAWN + 1), int(z) + o["z"] - 80300)
              for y, z, x in zip(*m.solid().nonzero())}
    assert not [p for p in cells if p in theirs]


def test_the_cross_walk_is_untouched(cells):
    """A remedial design's damage is measured in what it REPLACES. This replaces one street:
    none."""
    assert not [p for p in cells if 76 <= p[0] <= 78]


# --------------------------------------------------------------------------- what it is


def test_it_builds_no_building(built, cells):
    """The whole point of the choice. The tallest thing in a pleasure garden is its arches, and a
    garden that grows a shed is the failure this lot has now been cleared of twice."""
    assert max(p[1] for p in cells) <= 6, "something in the garden is building-height"
    assert built.meta["kind"] == "path"
    assert "no mechanism" in built.meta["note"]


def test_every_material_is_cheap_available_and_neither_currency_nor_a_faller(cells):
    """Rule 12 and rule 16. `grass_block` and every form of dirt are CURRENCY here, which is why a
    bed's soil is moss - a lion once shipped with a coat of 5,173 dirt."""
    names = {n.split("[")[0] for n in cells.values()}
    assert not [n for n in names if palette.tier(n) == "expensive"], sorted(names)
    for n in names:
        assert blocks.spendable(n), f"{n} is currency on this server"
        assert not blocks.falls(n), f"{n} would pour off its own kerb"


def test_the_garden_is_mostly_ground(cells, cfg):
    """A pleasure garden is a floor with planting on it. If this ever measures like a building
    somebody has put one in it."""
    v0, u0, v1, u1 = cfg["params"]["lot"]
    cols = (v1 - v0 + 1) * (u1 - u0 + 1)
    c = Counter(p[1] for p in cells)
    assert c[0] > 0.55 * len(cells), "most of the garden should be the course you walk on"
    assert len(cells) / cols < 1.2, "too dense for a garden"
