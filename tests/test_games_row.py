"""THE MIDWAY'S GAMES STREET, AND THE THREE THINGS ABOUT IT THAT ARE NOT VISIBLE.

`PF Games Row` replaced a 6,364-block closed hall and a kiosk doing half a job. It builds no
building at all: six `park_games` consoles bring their own shells, and this design is the walk they
stand on, the screen that fills the gaps between them and the bunting over it.

That split is exactly where it can go wrong in ways nothing renders:

    THE RESERVATION GUARDS NOTHING   if a bay box drifts off the console it was measured from
    THE STREET IS NOT A STREET       if the walk does not run end to end, in CONTEXT
    A GAME NOBODY CAN REACH          if a screen or a bench stands in front of a counter

**A PIN MUST COME FROM THE WORLD, NOT FROM THE CODE THAT DRIFTED** - the ruin ring's seat lesson.
So the bay boxes are asserted against the consoles' own shipped artifacts rather than against the
numbers that were typed into the config beside them.
"""
from __future__ import annotations

import json
from collections import deque
from functools import lru_cache
from pathlib import Path

import pytest
import yaml

from mcbuild import blocks, palette, schem
from mcbuild.gen import gamesrow

#: **THE ROW AND ITS SIX CONSOLES ARE RETIRED, AND THE REASON IS IN THE MARKER RATHER THAN IN A
#: DELETED FILE.** Jack: "the games arent playable as they are facing, theyre ugly, and just not
#: working." The fault is in `park_games` - a console is a three-course SEALED cabinet whose score
#: lamps are buried in its lid course and whose aim/striker targets cannot be shot - so the row was
#: a street of machines nobody can operate. `PF Midway Garden` holds the lot; see
#: `mcbuild/gen/midgarden.py` for the block-by-block dump and `tests/test_midway_garden.py` for
#: what is asserted now. This file stands as the record of what the row was and is not run,
#: because a green test for a design nobody places is a green test that means nothing.
pytestmark = pytest.mark.skip(
    reason="PF Games Row is retired: park_games consoles are sealed cabinets - see "
           "mcbuild/gen/midgarden.py and tools/park_place.py")

ROOT = Path(__file__).resolve().parents[1]
CFG = ROOT / "configs" / "pf_games_row.yaml"
WORLD = ROOT / "out" / "Park Complete.litematic"
V0, U0 = 24, 345
LAWN = 202

#: name -> the config's own bay box, in the order the config lists them.
CONSOLES = ["PF Game Target Wall", "PF Game The Mark", "PF Game The Striker",
            "PF Game The Double", "PF Game The Signal", "PF Game Prize Point"]


@lru_cache(maxsize=1)
def _park_y() -> int:
    """The composite's y is a function of the deepest thing in the park, not a constant - it went
    190 -> 94 the day a stream put a design under Prismworks. Read, never typed."""
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
    return gamesrow.build(cfg["params"])


@pytest.fixture(scope="module")
def cells(built):
    out = {}
    pal = [e.value["Name"].value.split(":")[-1] for e in built.palette]
    for y in range(built.sy):
        for z in range(built.sz):
            for x in range(built.sx):
                i = int(built.ids[y, z, x])
                if i:
                    out[(x + V0, y, z + U0)] = pal[i]
    return out


def _console_cells():
    """Every shipped console as {(V, course, U) -> name}, read off its own artifact."""
    out = {}
    for n in CONSOLES:
        f = ROOT / "out" / f"{n}.litematic"
        if not f.exists():
            pytest.skip(f"{n} is not built")
        m = schem.load(str(f))
        o = json.loads((ROOT / "out" / f"{n}.scan.json").read_text())["origin"]
        pal = [e.value["Name"].value.split(":")[-1] for e in m.palette]
        for y, z, x in zip(*m.solid().nonzero()):
            out[(int(x) + o["x"] - 97500, int(y) + o["y"] - (LAWN + 1),
                 int(z) + o["z"] - 80300)] = pal[int(m.ids[y, z, x])]
    return out


PASSABLE = {"air", "water", "moss_carpet", "short_grass", "fern", "poppy", "dandelion", "azalea",
            "glow_lichen", "oak_leaves", "vine", "chain", "iron_chain", "rail", "torch",
            "wall_torch", "lantern", "oak_wall_sign", "spruce_wall_sign", "red_wall_banner",
            "oak_fence", "oak_fence_gate"}


def _solid(comp, p):
    n = comp.get(p)
    return n is not None and n.split("[")[0] not in PASSABLE


def _stands(comp, p):
    v, y, u = p
    return (_solid(comp, (v, y - 1, u))
            and not _solid(comp, p) and not _solid(comp, (v, y + 1, u)))


# --------------------------------------------------------------------------- the reservation


def test_every_bay_box_matches_the_console_it_reserves(cfg):
    """**THE PIN COMES FROM THE ARTIFACT.** A reservation measured off a console and then left
    behind when the console moves guards nothing at all - and it fails SILENTLY, because a box
    round empty ground raises on nothing. This is the check that the six boxes are still the six
    consoles."""
    bays = [tuple(b) for b in cfg["params"]["bays"]]
    assert len(bays) == len(CONSOLES)
    for name, (bv0, bu0, bv1, bu1) in zip(CONSOLES, bays):
        f = ROOT / "out" / f"{name}.litematic"
        if not f.exists():
            pytest.skip(f"{name} is not built")
        m = schem.load(str(f))
        o = json.loads((ROOT / "out" / f"{name}.scan.json").read_text())["origin"]
        ny, nz, nx = m.ids.shape
        v0, v1 = o["x"] - 97500, o["x"] - 97500 + nx - 1
        u0, u1 = o["z"] - 80300, o["z"] - 80300 + nz - 1
        assert (bv0, bu0, bv1, bu1) == (v0, u0, v1, u1), \
            f"{name} stands at V{v0}-{v1} U{u0}-{u1}; the row reserves V{bv0}-{bv1} U{bu0}-{bu1}"


def test_the_row_takes_not_one_cell_of_a_console(cells):
    """`blocked` raises on a hit, so reaching this at all means it did not want one. This measures
    the other direction - that no cell of the finished street lands inside a finished console."""
    theirs = _console_cells()
    assert not [p for p in cells if p in theirs]


def test_no_console_refused_a_cell_of_its_own(cfg):
    """`park_games` drops a cell the world already owns and COUNTS it, because a machine missing a
    cell is a machine that does nothing. A non-zero count is a siting error - and it caught one:
    `PF Game The Double` lost four cells to the Arcade Bunting, which is why the bunting moved
    into this design."""
    for name in CONSOLES:
        side = ROOT / "out" / f"{name}.scan.json"
        if not side.exists():
            pytest.skip(f"{name} is not built")
        d = json.loads(side.read_text())
        assert not d.get("refused"), f"{name} refused {len(d['refused'])} of its own cells"
        assert d.get("signed") is not False, f"{name} shipped without its own board"


# --------------------------------------------------------------------------- the street


def test_the_walk_runs_from_the_avenue_to_the_towers_forecourt(cells, cfg):
    """IN CONTEXT, because the cross walk that splits this lot is `Park Ways`' ground and the
    forecourt at the far end is the helter skelter's. The design alone is two pieces; the street
    is one walk or it is not a street."""
    if not WORLD.exists():
        pytest.skip("out/Park Complete.litematic is not built")
    m = schem.load(str(WORLD))
    pal = [e.value["Name"].value.split(":")[-1] for e in m.palette]
    comp = {}
    for v in range(V0 - 2, 130):
        for u in range(U0 - 2, U0 + 42):
            for y in range(_index(-1), _index(12)):
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
                                     and 0 <= p[1] < 12):
                    continue
                if _stands(comp, p):
                    seen.add(p)
                    q.append(p)
                    break
    for v in (30, 45, 60, 75, 80, 95, 105, 118):
        assert any((v, y, axis) in seen for y in (1, 2)), f"the walk breaks at V{v}"


def test_a_visitor_can_stand_at_every_console(cells, cfg):
    """A game behind a screen is a game nobody plays. Each console fronts onto the walk's own
    kerb, so the cell in front of its face must be somewhere a visitor stands - and this design
    must not have put a bench, a post or a screen in it."""
    theirs = _console_cells()
    comp = dict(theirs)
    comp.update(cells)
    lo, hi = (int(q) for q in cfg["params"]["fronts"])
    for name, bay in zip(CONSOLES, cfg["params"]["bays"]):
        bv0, bu0, bv1, bu1 = bay
        front, step = (lo, 1) if bu1 <= lo else (hi, -1)
        col = [(v, 1, front + step) for v in range(bv0, bv1 + 1)]
        free = [p for p in col if not _solid(comp, p)]
        assert len(free) >= 0.8 * len(col), \
            f"{name}'s frontage is blocked at {len(col) - len(free)} of {len(col)} cells"


def test_the_facade_has_an_opening_at_every_bay_and_a_screen_between(cells, cfg):
    """WHAT MAKES VOXELS READ AS ARCHITECTURE IS REGULARITY AND OPENINGS. The screen fills the
    gaps between consoles and stops dead at each one; a screen drawn across a mouth is a boarded-up
    shopfront, and it renders exactly like a wall that is supposed to be there."""
    lo, hi = (int(q) for q in cfg["params"]["fronts"])
    for bay in cfg["params"]["bays"]:
        bv0, bu0, bv1, bu1 = bay
        front = lo if bu1 <= lo else hi
        assert not [v for v in range(bv0, bv1 + 1)
                    if any((v, y, front) in cells for y in range(1, 8))], \
            f"the screen crosses the mouth of the bay at V{bv0}-{bv1}"
    assert any((v, 2, lo) in cells for v in range(24, 100)), "there is no screen at all"


def test_the_cross_walk_is_untouched(cells, cfg):
    """`Park Ways` runs the back cross walk through V76-78 of this lot. A remedial design's damage
    is measured in what it REPLACES; this replaces one street: none."""
    assert not [p for p in cells if 76 <= p[0] <= 78]


# --------------------------------------------------------------------------- what it is for


def test_the_row_carries_five_games_and_a_counter(cfg):
    """The Arcade's own marquee said "five games" over THREE. `PF Front Midway` still says five;
    this is what makes that true, and it is asserted rather than trusted because a sign is the
    one thing in this park that has been wrong twice without anybody noticing."""
    kinds = []
    for name in CONSOLES:
        side = ROOT / "out" / f"{name}.scan.json"
        if not side.exists():
            pytest.skip(f"{name} is not built")
        kinds.append(json.loads(side.read_text())["kind"].split("/")[-1])
    assert kinds.count("counter") == 1, kinds
    assert len(kinds) - kinds.count("counter") == 5, kinds
    assert len(set(kinds)) == 6, f"two bays are the same game: {kinds}"
    front = yaml.safe_load((ROOT / "configs" / "pf_front_midway.yaml").read_text())
    board = [b for b in front["params"]["pieces"]
             if isinstance(b, dict) and b.get("name") == "Games Row"]
    assert board and "five games" in board[0]["lines"], "the marquee no longer names the row"


def test_every_material_is_cheap_available_and_neither_currency_nor_a_faller(cells):
    names = {n.split("[")[0] for n in cells.values()}
    assert not [n for n in names if palette.tier(n) == "expensive"], sorted(names)
    for n in names:
        assert blocks.spendable(n), f"{n} is currency on this server"
        assert not blocks.falls(n), f"{n} would pour off its own kerb"


def test_it_builds_no_building(built):
    """The whole point. Jack retired the Arcade for being one, and a street that grows a shed is
    the same failure with a new name - so the tallest thing this design places is a bunting line."""
    assert max(p[1] for p in
               [(0, y, 0) for y in range(built.sy)
                if built.ids[y].any()]) <= 7, "the row has built something tall"
    assert "no building" in built.meta["note"] or built.meta["kind"] == "path"
