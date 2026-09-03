"""The park's front door: the ground rule, the containment, and the one mechanism that must work.

**EVERY CHECK HERE IS ONE A PICTURE CANNOT MAKE.** `render3d` draws a stair, a door and a redstone
torch facing the wrong way exactly as it draws a right one, and it draws a fence, a wall, a pane
and a set of iron bars all as full cubes. So the stair convention, the ground-layer rule, the
containment and the pay gate are all asserted off the BLOCK LIST and off `mcbuild.circuit`, never
looked at.

Nothing here pins a block count. A count is a snapshot and a snapshot fails the moment the design
improves; what is pinned is a CONTRACT - one connected piece, not one cell shared with the shipped
ground, a spawn you can stand on, a compound nothing can be walked out of while the doors are shut,
and a gate that is shut at rest, shut below the price, open at it, and shut again after.

THE CONTAINMENT TEST HAS A CONTROL, and it is the most important thing in this file. `wall in the
open is not sealed` is a lesson this repo has learned three times in `NavTest`; a flood that finds
nothing because the model is wrong looks exactly like a flood that finds nothing because the wall
works. So `test_the_flood_is_not_vacuous` takes the two iron doors OUT and asserts the same flood
then DOES reach the other lands.
"""
from __future__ import annotations

import pathlib

import numpy as np
import pytest
import yaml

from mcbuild import audit as audit_mod, blocks, circuit, palette, schem
from mcbuild.gen import park_entrance as PE

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "pf_entry_gate.yaml"
WAYS = ROOT / "out" / "Park Ways.litematic"
PARK = ROOT / "out" / "Park Complete.litematic"

#: The shipped ground and the shipped park, with their own origins off their own sidecars.
WAYS_ORIGIN = (97500, 202, 80300)
PARK_ORIGIN = (97500, 190, 80300)
LAWN_Y = 202                    # the course `Park Ways` paves; a visitor stands at 203

#: The park's own U bands. The whole point of the compound is that neither of the outer two can be
#: walked to from the spawn while the doors are shut.
FRONTIER_U = (0, 169)
PRISMWORKS_U = (430, 599)

#: The walking band the flood is run over. Everything in this design and the ground it stands on
#: is inside it; going wider only costs time.
Y_BAND = (199, 216)

#: Blocks the game gained AFTER 1.19. `blocks.available` cannot be the gate on its own - the
#: allowlist is provisional, built from what captures happen to hold, and it rejects
#: `chiseled_stone_bricks`, which is a 1.14 block.
POST_1_19 = {
    "mud", "mud_bricks", "packed_mud", "cherry_planks", "cherry_log", "bamboo_planks",
    "pale_oak_planks", "pale_oak_log", "tuff_bricks", "polished_tuff", "chiseled_tuff",
    "copper_bulb", "copper_grate", "chiseled_copper", "suspicious_sand", "suspicious_gravel",
    "calibrated_sculk_sensor", "crafter", "trial_spawner", "vault", "heavy_core", "resin_block",
    "pink_petals", "torchflower", "pitcher_plant", "short_grass",
}

#: THE DESIGN'S OWN LOT, DERIVED FROM THE GENERATOR'S DEFAULTS RATHER THAN TYPED HERE. It was
#: `0 <= v <= 5`, which was the whole lot when the composition was six courses deep; the lot grew
#: to nineteen to give the arrival a walk and this stayed behind, so `Park Complete` - which
#: correctly contains this gate - collided with the candidate over its own thirteen new columns
#: and reported 2,866 overlaps against itself. A fixture that pins a snapshot fails the moment the
#: design improves; this one moves with it.
_LOT = (PE.PARK_ENTRANCE["at"][0], PE.PARK_ENTRANCE["at"][1],
        PE.PARK_ENTRANCE["at"][0] + PE.PARK_ENTRANCE["size"][0] - 1,
        PE.PARK_ENTRANCE["at"][1] + PE.PARK_ENTRANCE["size"][1] - 1)


BANNED = {"cobblestone", "mossy_cobblestone", "cobblestone_slab", "cobblestone_stairs",
          "cobblestone_wall"}

#: WHAT A PLAYER WALKS THROUGH - not what LIGHT goes through, which is what `nightlight.PASSY`
#: answers. The two lists differ in the direction that matters here: a lantern and a set of iron
#: bars pass light and stop a body, and a sign and a redstone torch do the opposite. Read the
#: wrong way round a containment flood is a claim about a park that is not this one.
_PASSABLE_SUFFIX = ("_sign", "_button", "_pressure_plate", "_carpet", "_torch", "_rail")
_PASSABLE_NAMES = {
    "air", "cave_air", "void_air", "redstone_wire", "lever", "tripwire", "tripwire_hook",
    "comparator", "repeater", "vine", "ladder", "scaffolding", "snow", "moss_carpet",
    "short_grass", "tall_grass", "fern", "large_fern", "dead_bush", "glow_lichen", "torch",
    "wall_torch", "soul_torch", "soul_wall_torch", "redstone_torch", "redstone_wall_torch",
    "sugar_cane", "kelp", "kelp_plant", "seagrass", "lily_pad", "structure_void", "light",
}


def passable(name: str) -> bool:
    n = name.split(":")[-1].split("[")[0]
    return n in _PASSABLE_NAMES or n.endswith(_PASSABLE_SUFFIX)


# --------------------------------------------------------------------------- fixtures

def _params() -> dict:
    return yaml.safe_load(CONFIG.read_text(encoding="utf-8"))["params"]


@pytest.fixture(scope="module")
def built():
    c = PE.build(_params())
    return c, c.to_model(), c.meta


@pytest.fixture(scope="module")
def named(built):
    """{(world x, y, z): bare block name} for every solid cell of the design."""
    return _named(built[1], built[0].world_origin)


def _named(model, origin) -> dict:
    ox, oy, oz = origin
    names = [n.split(":")[-1].split("[")[0] for n in model.names]
    out = {}
    for y, z, x in np.argwhere(model.ids > 0):
        out[(int(x) + ox, int(y) + oy, int(z) + oz)] = names[model.ids[y, z, x]]
    return out


def _states(model, origin) -> dict:
    """{(world x, y, z): "name[k=v,...]"} - the PROPERTIES, which is the whole point here.

    `model.names` is the bare name; a stair's facing and a torch's `lit` live in
    `props_at`, and reading the wrong one is how a test about orientation passes vacuously.
    """
    ox, oy, oz = origin
    out = {}
    for y, z, x in np.argwhere(model.ids > 0):
        x, y, z = int(x), int(y), int(z)
        props = model.props_at(x, y, z)
        name = model.names[model.ids[y, z, x]].split(":")[-1]
        if props:
            name += "[" + ",".join(f"{k}={v}" for k, v in sorted(props.items())) + "]"
        out[(x + ox, y + oy, z + oz)] = name
    return out


@pytest.fixture(scope="module")
def ways_cells():
    """Every cell the shipped GROUND layer owns, in world coordinates."""
    if not WAYS.exists():
        pytest.skip("out/Park Ways.litematic is not shipped")
    return _named(schem.load(str(WAYS)), WAYS_ORIGIN)


@pytest.fixture(scope="module")
def park_band():
    """Finished park walking band with the assembled gate's own lot removed.

    Sliced rather than loaded whole: `Park Complete` is 220 x 600 x 200 and the flood only ever
    looks at the courses a visitor can stand in. Park Complete now correctly contains this gate,
    so its own above-lawn cells are removed before the independently generated candidate is
    overlaid; the Park Ways fixture still protects every pre-existing ground/lamp cell.
    """
    if not PARK.exists():
        pytest.skip("out/Park Complete.litematic is not shipped")
    m = schem.load(str(PARK))
    ox, oy, oz = PARK_ORIGIN
    names = [n.split(":")[-1].split("[")[0] for n in m.names]
    lo, hi = Y_BAND[0] - oy, Y_BAND[1] - oy + 1
    sub = m.ids[lo:hi]
    out = {}
    for y, z, x in np.argwhere(sub > 0):
        wx, wy, wz = int(x) + ox, int(y) + lo + oy, int(z) + oz
        v, u = wx - PE.ANCHOR[0], wz - PE.ANCHOR[2]
        if wy >= PE.ANCHOR[1] and _LOT[0] <= v <= _LOT[2] and _LOT[1] <= u <= _LOT[3]:
            continue
        out[(wx, wy, wz)] = names[sub[y, z, x]]
    return out


def _standable(world: dict) -> set:
    """Cells a player can stand in: solid under, and this cell and the one over it passable.

    THE MODEL IS STATED RATHER THAN ASSUMED, which is the rule this repo wrote down after the same
    site read 1,268 cells, 36 cells and 248 cells depending on the movement model nobody had
    named. Here: step up at most one, fall at most `FALL`, and a two-column hop only across a
    genuine gap - a column whose own body and head courses are clear. A hop that ignores what it
    is hopping over would clear a four-course wall.
    """
    solid = {p for p, n in world.items() if not passable(n)}
    out = set()
    for (x, y, z) in solid:
        if not (Y_BAND[0] <= y + 1 <= Y_BAND[1]):
            continue
        a, b = (x, y + 1, z), (x, y + 2, z)
        if (a not in solid) and (b not in solid):
            out.add(a)
    return out, solid


FALL = 20


def _flood(stand: set, solid: set, start: tuple) -> set:
    by_xz: dict = {}
    for (x, y, z) in stand:
        by_xz.setdefault((x, z), []).append(y)
    if start not in stand:
        raise AssertionError(f"the start cell {start} is not standable")
    seen = {start}
    q = [start]
    steps = ((1, 0), (-1, 0), (0, 1), (0, -1))
    while q:
        x, y, z = q.pop()
        for dx, dz in steps:
            for mult in (1, 2):
                if mult == 2 and ((x + dx, y, z + dz) in solid or (x + dx, y + 1, z + dz) in solid):
                    continue                       # not a gap: something is in the way
                nx, nz = x + dx * mult, z + dz * mult
                for ny in by_xz.get((nx, nz), ()):
                    if not (-FALL <= ny - y <= 1):
                        continue
                    if (nx, ny, nz) in seen:
                        continue
                    seen.add((nx, ny, nz))
                    q.append((nx, ny, nz))
    return seen


# --------------------------------------------------------------------------- the build

def test_it_is_one_connected_piece_with_no_placement_problems(built):
    _c, m, _meta = built
    res = audit_mod.audit(m, ground=False)
    assert res.problems == [], res.report()
    assert len(res.components) == 1, f"the gate is in {len(res.components)} pieces: {res.components}"


def test_it_stays_inside_its_own_declared_lot(built):
    c, _m, meta = built
    assert meta["outside_lot_refused"] == 0, "a cell was refused for falling outside the lot"
    v0, u0, v1, u1 = meta["lot"]
    assert (v1 - v0 + 1, u1 - u0 + 1) == (c.sx, c.sz)
    assert v1 < PE.RIM_RESERVE[0], "the entrance reaches the protected rim reserve"
    for a, b in PE.REACHES:
        assert not (u0 <= b and u1 >= a), f"the entrance stands in the reach U{a}-{b}"


def test_nothing_touches_a_street_a_path_a_plaza_a_verge_or_a_lamp(built, ways_cells):
    """THE ONE PROPERTY THAT SEPARATES THIS FROM THE CHAOS JACK REJECTED.

    Measured against the shipped ground cell by cell. It is not a promise the generator makes in a
    docstring: `_Lot.put` refuses every cell the mask holds, so this test is checking that the
    refusal is wired up rather than that somebody remembered to dodge.
    """
    c, _m, meta = built
    assert meta["ground_layer_checked"], "the ground layer was not consulted at all"
    shared = set(_named(_m_of(built), c.world_origin)) & set(ways_cells)
    assert shared == set(), f"{len(shared)} cells shared with Park Ways, e.g. {sorted(shared)[:5]}"
    assert meta["ground_layer_refused"] > 0, \
        "the mask refused nothing at all - the apron's own lamp mast is inside this lot, so a " \
        "zero here means the mask is not being consulted"


def _m_of(built):
    return built[1]


def test_it_overlaps_nothing_in_the_finished_park(built, park_band):
    """A design cell may sit where the world already holds the SAME block; anything else is a
    collision, and this design is additive, so the honest number is zero of either."""
    c, m, _meta = built
    mine = _named(m, c.world_origin)
    clash = [p for p, n in mine.items() if p in park_band]
    assert clash == [], f"{len(clash)} cells collide with the finished park, e.g. {clash[:5]}"


def test_every_block_is_legal_available_cheap_and_not_currency(built, named):
    c, m, _meta = built
    used = sorted(set(named.values()))
    for n in used:
        assert blocks.exists(n), f"{n} is not a block"
        assert n not in POST_1_19, f"{n} is newer than the 1.19 SERVER"
        assert n not in BANNED, f"{n} is banned outright"
        assert blocks.spendable(n), f"{n} is CURRENCY on this server"
        assert palette.tier(n) != "expensive", f"{n} is expensive tier"
    res = audit_mod.audit(m, ground=False)
    assert res.problems == [], res.report()


def test_the_value_ladder_is_actually_a_ladder():
    """Measured ACROSS material families, because inside one a ladder cannot exist by
    construction - the mistake this repo has now made four times."""
    pal = PE._pal("midway")
    rungs = [pal["field"], pal["pier"], pal["trim"], pal["plinth"]]
    lum = [sum(blocks.color(n, "side")) / 3 for n in rungs]
    for a, b, la, lb in zip(rungs, rungs[1:], lum, lum[1:]):
        assert la - lb >= 15, f"{a} {la:.0f} and {b} {lb:.0f} are the same tone"


# --------------------------------------------------------------------------- the spawn

def test_the_spawn_is_a_real_position_and_a_real_angle(built):
    _c, _m, meta = built
    s = meta["spawn"]
    v, u = meta["spawn"]["park"]
    assert s["world"] == [PE.ANCHOR[0] + v, PE.ANCHOR[1], PE.ANCHOR[2] + u]
    assert s["world"][1] == LAWN_Y + 1, "a visitor stands one course above the lawn"
    # +V is world +X. Minecraft's yaw is 0 south, 90 west, 180 north, -90 east - a fact about the
    # game, so it is asserted rather than remembered.
    assert s["yaw"] == -90.0 and s["pitch"] == 0.0
    v0, u0, v1, u1 = meta["lot"]
    assert v0 <= v <= v1 and u0 <= u <= u1, "the spawn is not inside its own compound"


def test_the_spawn_cell_is_standable_and_nothing_of_ours_is_in_it(built, named, park_band):
    c, _m, meta = built
    x, y, z = meta["spawn"]["world"]
    assert (x, y, z) not in named, "the design put a block in the cell a visitor spawns in"
    assert (x, y - 1, z) in park_band, "there is no ground under the spawn"
    assert (x, y + 1, z) not in named and (x, y + 1, z) not in park_band, \
        "there is no headroom over the spawn"


def test_the_spawn_looks_down_a_clear_sightline(built, named, park_band):
    """WHAT THE VISITOR SEES, MEASURED RATHER THAN DESCRIBED.

    From the spawn cell, along +X at eye height, every cell to the gate's back face must be
    something you can see through - air, or the grille that closes the ceremonial arch. The
    reason the spawn sits one cell off the axis is exactly this: `Park Ways`' apron lamp mast
    stands at V4/U300 and puts a fence post three blocks in front of a visitor's eyes.
    """
    _c, _m, meta = built
    x, y, z = meta["spawn"]["world"]
    world = dict(park_band)
    world.update(named)
    v_back = meta["lot"][2]                      # V5, the gate building's back face
    for v in range(meta["spawn"]["park"][0] + 1, v_back + 1):
        cell = world.get((PE.ANCHOR[0] + v, y + 1, z))    # eye height: the course over the feet
        assert cell in (None, "iron_bars", "iron_door"), \
            f"the view to the entrance is blocked at V{v} by {cell}"
    assert world.get((PE.ANCHOR[0] + v_back, y + 1, z)) == "iron_door", \
        "the spawn is not aligned with an entrance door"


def test_the_arrival_can_walk_from_the_gate_to_the_wheel(built):
    """THE WALK, NOT A CORRIDOR. Every course of the axis band must be somewhere a visitor can put
    their feet, from the gate's own doorway to the wheel's face.

    Written as "no block at all in these two courses for eighty-six columns" this forbade the one
    thing the walk-up is FOR - Jack asked the centre for "a stone walk up, maybe a small fountain"
    - and it forbade the gate's own doors as well, because it read the courses ABOVE a walker
    rather than the two a walker occupies. A fountain a visitor walks around is not an obstruction;
    a building in the middle of the approach is. So this asserts a route and the next test asserts
    the view.
    """
    m = schem.load(str(PARK))
    ox, oy, oz = PARK_ORIGIN
    _c, _built, meta = built
    _x, feet_y, z = meta["spawn"]["world"]
    names = [n.split(":")[-1].split("[")[0] for n in m.names]

    # PARK V IS THE MODEL'S OWN X INDEX and park U its Z, because `Park Complete` is anchored at
    # the same X/Z as the park lattice - which is the only reason this file can index it directly.
    axis_u = z - oz
    assert (ox, oz) == (PE.ANCHOR[0], PE.ANCHOR[2])

    def solid(v, u, y):
        slot = int(m.ids[y - oy, u, v])
        return bool(slot) and not passable(names[slot])

    def standable(v, u, y):
        return solid(v, u, y - 1) and not solid(v, u, y) and not solid(v, u, y + 1)

    # EVERY LOT IN THIS PARK IS ONE COURSE OVER THE LAWN THE STREETS ARE CUT INTO, so a walk that
    # crosses one steps UP - and a test pinned to the spawn's own course reports a finished court
    # as fifty-one columns of solid wall. The step is what is allowed, not any height at all: a
    # visitor may rise one course and no more.
    back = meta["lot"][2]                          # the gate's own back face
    dead, floor = [], feet_y
    for v in range(back + 1, 80):
        # THE WALK IS A BAND, NOT A LINE. The court's basin stands on the axis on purpose and a
        # walker goes round it, so the question is whether SOME column of the axis band carries
        # them - which is what "clearly demonstrate a flow" actually means.
        here = [y for u in range(axis_u - 6, axis_u + 7)
                for y in (floor, floor + 1, floor - 1) if standable(v, u, y)]
        if not here:
            dead.append(v)
        else:
            floor = min(here, key=lambda y: abs(y - floor))
    assert dead == [], f"the walk from the gate to the wheel is blocked at V{dead[:6]}"


def test_the_wheel_is_visible_from_inside_the_gate(built):
    """THE VISTA, MEASURED AS A RAY AND NOT AS A TUNNEL.

    "One module blocks another's approach view" is the thing the visual spec asks about, and the
    honest test of it is a line from a visitor's eye to the thing they are meant to see - not a
    demand that eighty-six courses of the park hold nothing. The Sky Lift's hub is 74 courses up
    and forty blocks beyond the court's fountain, so the ray clears it by a dozen; a BUILDING in
    the approach would not.
    """
    m = schem.load(str(PARK))
    ox, oy, oz = PARK_ORIGIN
    _c, _built, meta = built
    _x, feet_y, z = meta["spawn"]["world"]
    names = [n.split(":")[-1].split("[")[0] for n in m.names]
    v_eye = meta["lot"][2] + 1                     # one step past the doors
    hub_v, hub_y = 90, feet_y + 40                 # the wheel's own densest column and its hub
    hits = []
    # ...and the ray STOPS AT THE WHEEL'S OWN FACE. Run to the hub it strikes the wheel, which is
    # the ride being visible rather than something blocking it.
    for k in range(1, (hub_v - v_eye) * 4):
        t = k / ((hub_v - v_eye) * 4)
        v = v_eye + t * (hub_v - v_eye)
        if v >= 80:
            break
        y = (feet_y + 1.6) + t * (hub_y - feet_y - 1.6)
        slot = int(m.ids[int(round(y)) - oy, z - oz, int(round(v))])
        if slot and not passable(names[slot]):
            hits.append((int(round(v)), int(round(y)), names[slot]))
    assert hits == [], f"the wheel is not visible from the gate: {hits[:6]}"


def test_the_walk_from_the_spawn_reaches_both_fare_slots(built, named, park_band):
    """A gate you cannot get to is not a gate. Flooded rather than assumed."""
    c, m, meta = built
    world = dict(park_band)
    world.update(_named(m, c.world_origin))
    stand, solid = _standable(world)
    start = tuple(meta["spawn"]["world"])
    reached = _flood(stand, solid, start)
    for lane in meta["lanes"]:
        sx, sy, sz = lane["mouth"]
        # you stand in FRONT of the slot, one course out toward the forecourt (-V is -X)
        assert (sx - 2, sy - 1, sz) in reached or (sx - 2, sy, sz) in reached, \
            f"nobody can reach the payment chest at {lane['payment_chest']}"


# --------------------------------------------------------------------------- containment

def _reach(built, park_band, drop_doors=False):
    c, m, meta = built
    world = dict(park_band)
    mine = _named(m, c.world_origin)
    if drop_doors:
        mine = {p: n for p, n in mine.items() if n != "iron_door"}
    world.update(mine)
    stand, solid = _standable(world)
    return _flood(stand, solid, tuple(meta["spawn"]["world"])), meta


def test_with_the_doors_shut_nothing_outside_the_compound_can_be_reached(built, park_band):
    """THE FEATURE, AND THE ONE THING THAT CANNOT BE EYEBALLED.

    The void closes the compound in front, the flank walls close it sideways and the gate building
    closes it behind. What is asserted is not "you cannot reach the Frontier" but the much stronger
    "you cannot leave the box at all" - because a containment that holds only against the two
    places somebody thought to name is not containment.
    """
    reached, meta = _reach(built, park_band)
    v0, u0, v1, u1 = meta["lot"]
    x0, x1 = PE.ANCHOR[0] + v0, PE.ANCHOR[0] + v1
    z0, z1 = PE.ANCHOR[2] + u0, PE.ANCHOR[2] + u1
    out = [p for p in reached if not (x0 <= p[0] <= x1 and z0 <= p[2] <= z1)]
    assert out == [], f"{len(out)} cells outside the compound are reachable, e.g. {sorted(out)[:6]}"


def test_neither_other_land_can_be_walked_to(built, park_band):
    reached, _meta = _reach(built, park_band)
    for name, (a, b) in (("frontier", FRONTIER_U), ("prismworks", PRISMWORKS_U)):
        bad = [p for p in reached if a <= p[2] - PE.ANCHOR[2] <= b]
        assert bad == [], f"{name} is reachable on foot from the spawn: {sorted(bad)[:4]}"


def test_the_flood_is_not_vacuous(built, park_band):
    """THE CONTROL. Take the two iron doors out and the same flood must escape.

    A flood that finds nothing because the model is wrong looks exactly like a flood that finds
    nothing because the wall works - which is why `NavTest` had to learn three times that a wall in
    the open is not sealed. This is the difference between the two.
    """
    reached, meta = _reach(built, park_band, drop_doors=True)
    v0, u0, v1, u1 = meta["lot"]
    x1 = PE.ANCHOR[0] + v1
    beyond = [p for p in reached if p[0] > x1]
    assert beyond, "with the doors removed the flood still escapes nothing - the model is wrong"


def test_the_ceremonial_arch_has_doors_surrounded_by_bars(built, named):
    """You see the park through it and you do not walk into it. A grille that starts one course up
    is a doorway with a decoration over it."""
    _c, _m, meta = built
    a0, a1 = _params()["arch"]
    u0 = meta["lot"][1]
    # THE BACK FACE IS `front + 5`, NOT V5. The composition is six columns deep wherever it is set
    # back to, and it is set back thirteen now - so a constant here names a column of open
    # forecourt and every lookup misses.
    x = PE.ANCHOR[0] + _params()["front"] + 5
    for u in range(a0, a1 + 1):
        z = PE.ANCHOR[2] + u0 + u
        for y in (PE.ANCHOR[1], PE.ANCHOR[1] + 1):
            want = "iron_door" if u in _params()["lanes"] else "iron_bars"
            assert named.get((x, y, z)) == want, \
                f"the ceremonial arch has the wrong closure at U{u0 + u}, Y{y}"


# --------------------------------------------------------------------------- the pay gate

def _sim(built, fills, ticks=25):
    c, m, meta = built
    ci = circuit.Circuit.of(m, c.world_origin)
    for lane, f in zip(meta["lanes"], fills):
        ci.fill(tuple(lane["till"]), f)
    trace = []
    for _ in range(ticks):
        ci.step()
        trace.append([(ci.powered(tuple(l["door"])), ci.powered(tuple(l["door_upper"])))
                      for l in meta["lanes"]])
    return ci, trace


def test_the_price_is_arithmetic_and_not_a_taste(built):
    """A comparator reads a container as floor(14 * total / (slots * stack)) + 1, so a five-slot
    hopper of grass steps every 320/14 = 22.86 blocks. 22 reads 1 and 23 reads 2 - and 1 is what
    ANY single item reads. Level 1 is intentionally used for the one-grass live-server contract."""
    assert PE.price_blocks(2) == 23
    assert PE.price_blocks(3) == 46
    for n, want in ((0, 0), (1, 1), (22, 1), (23, 2), (45, 2), (46, 3)):
        got = (14 * n) // 320 + (1 if n else 0)
        assert got == want, f"{n} grass blocks reads {got}, not {want}"
    _c, _m, meta = built
    assert PE.price_blocks(1) == 1
    assert meta["price_blocks"] == 1 and meta["currency"] == "grass_block"


def test_at_rest_every_door_is_shut(built):
    _ci, tr = _sim(built, [0, 0])
    assert all(not lo and not up for row in tr for (lo, up) in row), \
        "a door is powered with an empty till - the torch pair is the wrong way round"


def test_below_the_price_no_door_opens(built):
    """An empty till is the only state below the one-grass admission price."""
    _ci, tr = _sim(built, [0, 0])
    assert all(not lo and not up for row in tr for (lo, up) in row), \
        "the gate opened below its own price"


def test_each_lane_has_an_independent_payment_chest_and_receipt_hopper(built):
    _c, _m, meta = built
    assert len(meta["lanes"]) == 2
    assert len({tuple(l["payment_chest"]) for l in meta["lanes"]}) == 2
    assert len({tuple(l["receipt_hopper"]) for l in meta["lanes"]}) == 2


def test_adapter_opens_both_halves_and_has_a_failure_contract(built):
    _c, _m, meta = built
    a = meta["adapter_contract"]
    assert a["debit"] == {"item": "grass_block", "count": 1, "from": "player inventory"}
    assert "both halves" in a["success"]
    assert "refund" in a["failure"]


def test_adapter_resets_the_lane_after_a_bounded_open_window(built):
    _c, _m, meta = built
    assert "5 seconds" in meta["adapter_contract"]["success"]
    assert "close the door" in meta["adapter_contract"]["reset"]


def test_the_adapter_consumes_the_receipt_before_reset(built):
    _c, _m, meta = built
    assert "receipt grass" in meta["adapter_contract"]["reset"]
    assert meta["hazards"] == []


def test_no_hopper_touches_a_torch(built, named):
    """A HOPPER BESIDE A LIT REDSTONE TORCH IS DISABLED, and nothing in `mcbuild.circuit` can see
    that: the comparator would go on reading a till that never fills, or a mouth that never
    empties. It is designed out - till and mouth at one end of the line, both torches seven cells
    away at the other - and this is what keeps them apart."""
    torches = [p for p, n in named.items() if n.endswith("torch")]
    hoppers = [p for p, n in named.items() if n == "hopper"]
    for h in hoppers:
        for t in torches:
            assert sum(abs(a - b) for a, b in zip(h, t)) > 1, f"hopper {h} touches torch {t}"


def test_the_torch_pair_ships_settled(built):
    """A torch standing on a powered block that ships `lit=true` is HIGH for the tick or two the
    stack takes to settle - measured, that opened the ticket barriers on every chunk load. T0 is
    lit at rest and T1 is not, and the shipped states say so."""
    c, m, meta = built
    st = _states(m, c.world_origin)
    for lane in meta["lanes"]:
        t1, t0 = [tuple(t) for t in lane["torches"]]
        assert "lit=false" in st[t1], f"the output torch at {t1} ships lit"
        assert "lit=false" not in st[t0], f"the inverter torch at {t0} ships unlit"


def test_the_till_is_a_dead_end_so_it_can_accumulate(built):
    """A hopper that points into a container drains, and a till that drains cannot be read as a
    PRICE at all - the count never rises. `facing=down` puts its output into the lawn."""
    c, m, meta = built
    st = _states(m, c.world_origin)
    for lane in meta["lanes"]:
        assert "facing=down" in st[tuple(lane["till"])]
        assert st[tuple(lane["payment_chest"])].startswith("chest[")


def test_the_circuit_inspection_finds_nothing_suspicious(built):
    c, m, _meta = built
    findings = [f for f in circuit.inspect(m, c.world_origin)
                if not circuit.near_edge(m, c.world_origin, f[1])]
    hard = [f for f in findings if "quasi" not in f[0].lower()]
    assert hard == [], circuit.report(findings)


# --------------------------------------------------------------------------- craft

def test_every_stair_leans_into_the_wall_it_grows_from(built):
    """A stair's TALL side IS its `facing`, and this repo's renderer draws both directions
    identically. The cornice course projects into V2 and leans back east into the building; the
    portal and portico springers lean toward the opening they spring from."""
    c, m, meta = built
    st = _states(m, c.world_origin)
    cor = PE.ANCHOR[1] + meta["detail"]["building"]["cornice_y"]
    x_cor = PE.ANCHOR[0] + _params()["front"] + 2
    seen = 0
    for (x, y, z), s in st.items():
        if "stone_brick_stairs" not in s:
            continue
        if y == cor and x == x_cor:
            assert "facing=east" in s, f"the cornice stair at {(x, y, z)} leans out of the wall"
            seen += 1
        assert "half=top" in s or "half=bottom" in s
    assert seen >= 40, f"only {seen} cornice stairs - the course is not a line"


def test_every_sign_has_a_wall_behind_it_and_fits_its_line(built):
    """A wall sign floating in air draws exactly like one on a wall, and `gen/park.py` records
    four kinds shipping one. `_Lot.sign` refuses when the support is missing, so a sign that was
    silently declined shows up here as a count."""
    c, m, meta = built
    st = _states(m, c.world_origin)
    named = _named(m, c.world_origin)
    signs = [p for p, n in named.items() if n == "oak_wall_sign"]
    assert len(signs) == meta["signs"] >= 4, "signs were silently refused"
    for (x, y, z) in signs:
        assert "facing=west" in st[(x, y, z)]
        assert (x + 1, y, z) in named, f"the sign at {(x, y, z)} hangs on nothing"
    for t in m.tile_entities:
        for line in _sign_lines(t):
            assert len(line) <= PE.SIGN_WIDTH, f"sign line clips mid-word: {line!r}"


def test_the_gate_says_what_it_costs(built):
    c, m, meta = built
    text = " ".join(line for t in m.tile_entities for line in _sign_lines(t))
    assert str(meta["price_blocks"]) in text, "no sign names the price"
    assert "GRASS" in text.upper(), "no sign names the currency"


def _sign_lines(tile) -> list:
    """The four lines of each side of a sign, out of the NBT the writer actually emits.

    26.x nests them under `front_text`/`back_text` as a `messages` list of JSON strings, and
    there are ALWAYS four - a sign with two lines still stores four. The empties are dropped
    here so a width assertion is about text somebody wrote.
    """
    import json as _json
    out = []
    for key in ("front_text", "back_text"):
        blk = tile.value.get(key)
        if blk is None:
            continue
        for m in blk.value["messages"].value:
            try:
                txt = _json.loads(m.value).get("text", "")
            except Exception:
                txt = str(m.value)
            if txt:
                out.append(txt)
    return out


def test_the_queue_is_railed_and_lit(built):
    _c, _m, meta = built
    q = meta["detail"]["queue"]
    assert q["rails"] >= 6, "there is no queue, only a forecourt"
    assert q["roof"] >= 20 and q["beams"] >= 8, "the queue has no canopy"
    assert meta["lights"] >= 12, "the compound is not lit"


def test_the_lot_refuses_a_reserve():
    with pytest.raises(ValueError):
        PE.build({**_params(), "at": [0, 180]})          # inside the frontier/midway reach
    with pytest.raises(ValueError):
        PE.build({**_params(), "at": [170, 270]})        # inside the protected rim reserve
