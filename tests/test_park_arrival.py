"""The Arrival Court's contracts - the ground under a visitor's feet in their first second.

WHAT THIS EXISTS TO STOP HAPPENING AGAIN. Measured off the shipped `Park_Centre Complete`, the
column at `newisle`'s own bedrock - (97600, 200, 80600), where `/is` puts a player down - is solid
from Y202 to Y213: the Monument is built across it. Every check in this pipeline passed that. The
blocks are legal, supported, cheap, 1.19-legal and one connected piece; the zone's own street
network audits as one connected walk reaching every door. **Nothing anywhere asked whether the
cell a player ARRIVES IN is a cell a player can stand in**, so the answer had been no since the
park shipped and no test could see it.

So the first three cases here are about one cell.
"""
# **THE PLANNER OWNS THIS CONFIG NOW.** `park_arrival.yaml` was a standalone duplicate of
# the module the midway theme sites at `anchor: "origin"`; two configs writing one design
# is how a design gets placed twice. `arrival_court.yaml` is what `plan --emit` writes.
import os
from collections import deque

import numpy as np
import pytest
import yaml

from mcbuild import blocks, nbt, nightlight, palette, scan as scan_mod, walk
from mcbuild.gen import arrival, wayfinding
from mcbuild.gen.park import SIGN_WIDTH, _STEP

CONFIG = "configs/arrival_court.yaml"
ZONE = "Park_Centre Complete"
GATE = "Park Gate"

# THE MONUMENT'S OWN 33x33 FOOTPRINT, measured off the shipped plan (`at` [97611, 203, 80616],
# size [33, 53, 33] -> centred on (97595, 80600)). It is removed from the composite in the route
# test below, which is exactly what relocating it means for the walk - see that test's docstring.
MONUMENT_BOX = (97579, 97611, 80584, 80616)


@pytest.fixture(scope="module")
def cfg():
    with open(CONFIG, encoding="utf-8") as fh:
        return yaml.safe_load(fh)["params"]


@pytest.fixture(scope="module")
def built(cfg):
    c = arrival.build(dict(cfg))
    ox, oy, oz = c.world_origin
    states = []
    for e in c.palette:
        n = nbt.state_name(e).split(":")[-1]
        pr = nbt.state_props(e)
        states.append((n, pr))
    ys, zs, xs = np.nonzero(c.ids > 0)
    cells = {(int(x) + ox, int(y) + oy, int(z) + oz): states[int(c.ids[y, z, x])]
             for y, z, x in zip(ys.tolist(), ys.tolist() and zs.tolist(), xs.tolist())}
    return c, cells


@pytest.fixture(scope="module")
def at(cfg):
    return tuple(int(v) for v in cfg["at"])


# ------------------------------------------------------------------------------- the arrival cell

def test_the_arrival_cell_is_clear_to_head_height(built, at, cfg):
    """THE ONE CELL. Nothing this design builds may occupy the cell a player is put down in, or
    the courses their body and their view need."""
    _c, cells = built
    for h in range(int(cfg.get("clear", 3))):
        p = (at[0], at[1] + h, at[2])
        assert p not in cells, f"the arrival cell is filled at {p} with {cells[p][0]}"


def test_a_visitor_actually_STANDS_on_the_arrival_cell(built, at):
    """Clear is not the same as standable: a hole in the paving is clear too. The full movement
    model, from `mcbuild.walk` - a solid block under the feet and two courses for the body."""
    _c, cells = built
    world = {k: v[0] for k, v in cells.items()}
    assert walk.stands(world, at), "a player would not be standing on anything"
    assert world.get((at[0], at[1] - 1, at[2])) is not None


def test_the_court_refuses_to_build_over_its_own_arrival_cell():
    """The guard, fired directly rather than hoped for. This is the exact fault the whole module
    exists because of, so it may not be left to the shape of the figure to avoid by accident."""
    from mcbuild.gen.vertical import World
    w = World()
    w.put(97600, 203, 80600, "stone")
    p = {**arrival.ARRIVAL, "at": [97600, 203, 80600], "land": "midway", "gate": "west"}
    with pytest.raises(ValueError, match="arrival cell"):
        arrival._court(w, p, None)


# ------------------------------------------------------------------------------------- can you see

def test_all_four_sightlines_run_the_whole_court(built, cfg):
    """A court whose own signage stands in the view it was sited to keep open renders exactly
    like one that does not. `_sightline` walks the built cells at eye level; every cardinal must
    reach the far end of its own spur."""
    c, _cells = built
    want = int(cfg.get("radius", 11)) + int(cfg.get("spur", 5))
    for d, run in c.meta["sightlines"].items():
        assert run == want, f"the {d} sightline stops after {run} of {want} blocks"


def test_nothing_stands_at_feet_or_eye_level_on_a_spoke(built, at, cfg):
    """The same property from the other side: measured on the CELLS rather than by walking a ray,
    so a change that puts a block on a spoke fails here even if the ray happens to miss it.

    **ONLY THE TWO COURSES A BODY OCCUPIES.** Written as "nothing above the floor" this failed on
    the fingerpost's own arms, which cross the spokes three and four courses up - and an arm you
    walk under is not an obstruction, it is a fingerpost. The property that matters is the one
    `_sightline` measures: the feet course and the eye course, and nothing else.
    """
    _c, cells = built
    r = int(cfg.get("radius", 11)) + int(cfg.get("spur", 5))
    over = [k for k in cells
            if k[1] in (at[1], at[1] + 1)
            and ((k[0] == at[0] and abs(k[2] - at[2]) <= r)
                 or (k[2] == at[2] and abs(k[0] - at[0]) <= r))]
    assert over == [], f"{len(over)} cells stand in a cardinal sightline, first {over[:3]}"


# ------------------------------------------------------------------------------ shape and material

def test_it_is_one_connected_piece(built):
    _c, cells = built
    keys = set(cells)
    seen, q = {next(iter(keys))}, deque([next(iter(keys))])
    while q:
        x, y, z = q.popleft()
        for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            t = (x + d[0], y + d[1], z + d[2])
            if t in keys and t not in seen:
                seen.add(t)
                q.append(t)
    assert len(seen) == len(keys), f"{len(keys) - len(seen)} cells are a separate piece"


def test_every_block_is_affordable_spendable_and_on_the_1_19_server(built):
    """Three different questions, and this project has shipped a design that passed two of them:
    `exists` is not `available` and neither is `spendable` - dirt and grass are CURRENCY here."""
    _c, cells = built
    for name in {v[0] for v in cells.values()}:
        assert blocks.available(name), f"{name} is not on the 1.19 server list"
        assert blocks.spendable(name), f"{name} is currency on this server"
        # **CHEAP-OR-OK, which is the gate the rest of this repo uses.** `ok` is a real tier -
        # the whole quarter's blackstone, every deepslate brick and the casino's own panes are
        # `ok` - and only `expensive` is refused. Written cheap-only this went red the moment the
        # ground palettes moved off wool onto stone, which is the change it should have welcomed:
        # `blackstone` is `ok`, and it is exactly what the user asked for in place of black wool.
        assert palette.tier(name) in ("cheap", "ok"), (
            f"{name} is {palette.tier(name)} tier")


def test_the_ground_is_stone_and_not_wool(built, at):
    """Jack, on the shipped park: wool belongs on the things that are NOT the ground. The whole
    floor course is checked, not a sample - a single wool cell in a paving figure is exactly the
    kind of thing that reads from the air and from nowhere else."""
    _c, cells = built
    floor = at[1] - 1
    woolly = sorted(k for k, v in cells.items() if k[1] == floor and v[0].endswith("_wool"))
    assert woolly == [], f"{len(woolly)} wool cells in the floor, first {woolly[:3]}"


def test_the_figure_is_drawn_on_a_real_value_ladder():
    """MEASURED, NOT CHOSEN, and measured ACROSS material families - this repo has three separate
    notes concluding the economy has no value contrast, every one of them arrived at by searching
    inside ONE family, where a ladder cannot exist by construction."""
    rungs = [arrival.FIELD, arrival.KERB, arrival.SPOKE]
    lum = [sum(blocks.color(n, "top")) / 3 for n in rungs]
    steps = [abs(lum[i] - lum[i + 1]) for i in range(len(lum) - 1)]
    assert min(steps) >= 20, f"the ladder {list(zip(rungs, lum))} has a rung nobody can see: {steps}"


# ------------------------------------------------------------------------------------- the signage

def test_every_sign_has_a_block_behind_it(built):
    """`park._sign`'s own rule. Four of the park's seven kinds shipped a sign hung on a column
    with an opening in it, and a floating wall sign draws exactly like a mounted one - the game
    simply refuses to place it."""
    _c, cells = built
    for k, (name, props) in cells.items():
        if not name.endswith("_wall_sign"):
            continue
        dx, dz = _STEP[props["facing"]]
        back = (k[0] - dx, k[1], k[2] - dz)
        assert back in cells, f"the sign at {k} facing {props['facing']} has nothing behind it"


def test_no_sign_line_is_wider_than_a_sign(cfg):
    c = arrival.build(dict(cfg))
    for (_x, _y, _z), t in getattr(c, "tiles", {}).items():
        for raw in list(t["front"]) + list(t["back"]):
            import json
            try:
                line = json.loads(raw).get("text", "")
            except (TypeError, ValueError):
                line = str(raw)
            assert len(line) <= SIGN_WIDTH, f"{line!r} clips mid-word on a sign"


def test_the_fingerpost_points_only_at_things_that_exist():
    """`wayfinding.known_destinations()` reads the live theme rosters out of `planner.THEMES`, so
    a module renamed upstream fails HERE rather than shipping a sign to a building nobody can
    find. A fingerpost pointing at nothing is worse than no fingerpost at all."""
    known = wayfinding.known_destinations()
    for arm in arrival.DEFAULT_ARMS:
        assert str(arm["dest"]).upper() in known, f"{arm['dest']!r} names nothing real"
        assert arm["direction"] in _STEP


def test_the_signage_is_sited_and_not_rewritten(built):
    """All three boards are `gen/wayfinding.py`'s own tested kinds, pasted. If any of them ever
    stops arriving, this design has quietly started writing its own signage."""
    c, _cells = built
    for kind in ("mapboard", "noticeboard", "fingerpost"):
        assert c.meta["signage"][kind] > 0, f"no {kind} was pasted into the court"


# --------------------------------------------------------------------------------- light and dirt

def test_zero_spawnable_cells_are_dark(cfg):
    """An arrival court is where a visitor stands still and looks around. Unlit it is where a
    visitor stands still and is shot at."""
    c = arrival.build(dict(cfg))
    states = []
    for e in c.palette:
        n = nbt.state_name(e).split(":")[-1]
        pr = nbt.state_props(e)
        states.append(f"{n}[{','.join(f'{k}={v}' for k, v in sorted(pr.items()))}]" if pr else n)
    opaque, emit, passy, spawn, _water = nightlight.classify(states)
    ids = c.ids
    light = nightlight.propagate(opaque[ids], emit[ids])
    clear = passy[ids] | (ids == 0)
    standable = spawn[ids]
    ny = ids.shape[0]
    dark = []
    for y in range(ny - 1):
        zz, xx = np.nonzero(standable[y])
        for z, x in zip(zz.tolist(), xx.tolist()):
            head = clear[y + 2, z, x] if y + 2 < ny else True
            if clear[y + 1, z, x] and head and light[y + 1, z, x] < 1:
                dark.append((x, y + 1, z))
    assert dark == [], f"{len(dark)} spawnable cells at block light 0, first {dark[:3]}"


def test_no_lamp_is_capped_by_a_full_block(built):
    """A froglight flush in the floor IS the floor - put a block on top of it and it lights
    nothing, which is invisible in every render this project has."""
    c, cells = built
    for lamp in c.meta["lamps"]:
        above = (lamp[0], lamp[1] + 1, lamp[2])
        state = cells.get(above)
        assert not (state and blocks.is_full_cube(state[0])), \
            f"the lamp at {lamp} is capped by {state} and lights nothing"


def test_the_starter_pad_and_its_tree_are_on_the_dig_list(built, at, cfg):
    """A printer places into AIR and never replaces, so the skyblock starter pad's grass and its
    tree are cells this court can never fill. They are emitted as work to BREAK rather than left
    to be discovered by a player standing in a stone plaza with a hole of grass in the middle."""
    c, _cells = built
    dig = {tuple(d) for d in c.meta["dig"]}
    floor = at[1] - 1
    for dx in (-3, 0, 3):
        for dz in (-3, 0, 3):
            for h in range(0, 3):
                assert (at[0] + dx, floor + h, at[2] + dz) in dig, \
                    "the starter pad's own footprint is not on the dig list"
    assert any("chest" in u.lower() for u in c.meta["unverified"]), \
        "the starter chest must be REPORTED - a chest is not this design's to break"


# ------------------------------------------------------------------------------------ the boundary

def test_nothing_reaches_the_railway_corridor(built):
    """`transit.py` reserves X 97640..97649 for the skyway's piers and arches. A landform cell and
    a pier cell are both perfectly legal blocks; only the two designs together disagree."""
    _c, cells = built
    over = sorted(k for k in cells if k[0] >= 97640)
    assert over == [], f"{len(over)} cells in the railway's corridor, first {over[:3]}"


@pytest.mark.skipif(not os.path.exists(f"out/{ZONE}.litematic"), reason="the zone is not shipped")
def test_the_floor_is_flush_with_the_park(built, at):
    """Y202, edge to edge, like every other floor in the park - so there is not one step anywhere
    on the walk out of the court."""
    _c, cells = built
    assert at[1] - 1 == 202
    s = scan_mod.load(f"out/{ZONE}.litematic")
    m = s.model
    ox, oy, oz = s.origin
    ys, zs, xs = m.solid().nonzero()
    zone_floor = {(int(x) + ox, int(z) + oz) for y, z, x in zip(ys, zs, xs) if int(y) + oy == 202}
    rim = [k for k in cells if k[1] == 202]
    assert rim, "the court has no floor course at all"
    assert any((k[0], k[2]) in zone_floor for k in rim), \
        "the court's floor course does not lie on the same plane the zone paves"


# ---------------------------------------------------------------------------------- the walk in

@pytest.mark.skipif(
    not all(os.path.exists(f"out/{n}.litematic") for n in (ZONE, GATE)),
    reason="the midway zone and gate are not shipped")
def test_you_can_walk_from_the_arrival_cell_to_the_park_gate(cfg, at):
    """THE ROUTE, end to end, under the full movement model.

    **THE MONUMENT IS REMOVED FROM THE COMPOSITE, AND THAT IS THE POINT OF THE TEST.** As shipped
    it is built across the arrival cell and thirty-three columns around it, so this walk is not
    merely blocked, it starts inside a wall. Removing its own 33x33 footprint is exactly what
    relocating it means for the walk - so what this pins is the arrival court's contract *given
    that the Monument moves*, which is the change this design asks the planner for. If the two
    are ever both wired at these coordinates, the arrival generator's own guard raises first.
    """
    world = {}
    s = scan_mod.load(f"out/{ZONE}.litematic")
    m = s.model
    ox, oy, oz = s.origin
    ys, zs, xs = m.solid().nonzero()
    for y, z, x in zip(ys, zs, xs):
        k = (int(x) + ox, int(y) + oy, int(z) + oz)
        if (MONUMENT_BOX[0] <= k[0] <= MONUMENT_BOX[1]
                and MONUMENT_BOX[2] <= k[2] <= MONUMENT_BOX[3] and k[1] >= 202):
            continue                      # the Monument, relocated
        world[k] = m.names[m.ids[y, z, x]].split(":")[-1]
    for name in (GATE,):
        s2 = scan_mod.load(f"out/{name}.litematic")
        m2 = s2.model
        o2 = s2.origin
        ys2, zs2, xs2 = m2.solid().nonzero()
        for y, z, x in zip(ys2, zs2, xs2):
            world[(int(x) + o2[0], int(y) + o2[1], int(z) + o2[2])] = \
                m2.names[m2.ids[y, z, x]].split(":")[-1]
    c = arrival.build(dict(cfg))
    cox, coy, coz = c.world_origin
    ys3, zs3, xs3 = np.nonzero(c.ids > 0)
    for y, z, x in zip(ys3.tolist(), zs3.tolist(), xs3.tolist()):
        world[(x + cox, y + coy, z + coz)] = nbt.state_name(c.palette[int(c.ids[y, z, x])]).split(":")[-1]

    assert walk.stands(world, at), "a visitor does not even stand on the arrival cell"
    reach = walk.reachable(world, at, limit=500_000)
    assert len(reach) > 3_000, f"only {len(reach)} cells reachable from the arrival cell"

    gate = next(((x, 203, z) for x in range(97553, 97566) for z in range(80565, 80585)
                 if walk.stands(world, (x, 203, z))), None)
    assert gate is not None, "no standable cell inside the Park Gate"
    assert gate in reach, "you cannot walk from where you arrive to the park's front gate"

    # ...and out to both zone arches, which is how you leave the midway on foot
    for name, (x, z) in (("Frontier Arch", (97595, 80552)), ("Hollow Arch", (97595, 80648))):
        near = [p for p in ((x + dx, 203, z + dz) for dx in range(-4, 5) for dz in range(-3, 4))
                if p in reach]
        assert near, f"the {name} threshold is not reachable from the arrival cell"
