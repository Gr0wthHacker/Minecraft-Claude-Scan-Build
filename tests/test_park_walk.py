"""CAN YOU WALK THE WHOLE PARK WITHOUT THE TRAIN?

Jack, on the shipped park: *"strange land gaps between the zones, all land needs to be connected,
the train is just fast transport - not the only way to reach these areas."*

Nothing in this repo could answer that. `tests/test_park_plan.py` proves each zone's own street
network against the PLANNED routes; `tools/park_flow.py` proved the built ones - and composited
`Park Line` while omitting `Isthmus`, so every "all doors reached" it ever printed was a fact
about a park whose three islands are joined only by a viaduct. The audit agreed with the
complaint and nobody could see it, because the shortcut was in the evidence.

So: the railway is EXCLUDED from the composite here, deliberately and by default, and one test
adds it back only to prove it changes nothing about which zones you can get to.

THE MOVEMENT MODEL IS `mcbuild.walk`, and this file uses no other. CLAUDE.md's own rule, from the
court stair: *a reachability number means nothing without the movement model stated beside it* -
the same site read 1,268 standable cells on a fixed course, 36 with four-block falls allowed, and
248 on a true walk. `walk.stands` requires a solid block under the feet AND two clear courses for
the body, so headroom is asserted by construction on every cell in every flood here; the
`test_..._two_clear_courses...` case pins that separately rather than trusting it, because
"assert blocks, not headroom" is the bug class that has bitten this project five times.
"""
import os
from collections import deque

import pytest

from mcbuild import planner, scan as scan_mod, walk

# The walkable park: three zones, the causeway between them, and the pieces sited on the midway.
LAND = ["Park_Left Complete", "Park_Centre Complete", "Park_Right Complete", "Isthmus"]
EXTRA = ["Park Gate", "Park Notices", "Park Arrival"]
RAIL = "Park Line"

ZONE_Z = {"frontier": (80351, 80449), "midway": (80551, 80649), "hollow": (80751, 80849)}
GAP_Z = {"causeway N": (80450, 80550), "causeway S": (80650, 80750)}

# Inside the Park Gate on the midway's west edge - real built ground, checked below.
GATE_SEED_BOX = (97556, 97580, 80590, 80610)

pytestmark = pytest.mark.skipif(
    not all(os.path.exists(f"out/{n}.litematic") for n in LAND),
    reason="the shipped park litematics are not in out/ - run `python -m mcbuild gen` first")


def _cells(name: str) -> dict:
    s = scan_mod.load(f"out/{name}.litematic")
    m = s.model
    ox, oy, oz = s.origin
    ys, zs, xs = m.solid().nonzero()
    names, ids = m.names, m.ids
    return {(int(x) + ox, int(y) + oy, int(z) + oz): names[ids[y, z, x]].split(":")[-1]
            for y, z, x in zip(ys, zs, xs)}


def _composite(names) -> dict:
    world = {}
    for n in names:
        if os.path.exists(f"out/{n}.litematic"):
            world.update(_cells(n))
    return world


@pytest.fixture(scope="module")
def world():
    return _composite(LAND + EXTRA)


@pytest.fixture(scope="module")
def seed(world):
    """A standable cell on the midway's own paving, just inside the Park Gate.

    SEEDED FROM REAL GROUND, and the region is checked for size two tests down: a previous test
    in this project seeded in the void and proved nothing at all while passing.
    """
    x0, x1, z0, z1 = GATE_SEED_BOX
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            p = (x, 203, z)
            if walk.stands(world, p):
                return p
    pytest.fail("no standable cell anywhere inside the Park Gate seed box")


@pytest.fixture(scope="module")
def reached(world, seed):
    return walk.reachable(world, seed, limit=2_000_000)


def _street(cells: dict) -> set:
    """Every standable cell at street level, over the whole composite - the denominator."""
    out = set()
    for (x, y, z) in cells:
        p = (x, y + 1, z)
        if 202 <= p[1] <= 204 and walk.stands(cells, p):
            out.add(p)
    return out


def _zone_of(z: int) -> str:
    for zone, (lo, hi) in {**ZONE_Z, **GAP_Z}.items():
        if lo <= z <= hi:
            return zone
    return "off-park"


# ------------------------------------------------------------------- the seed, and the denominator

def test_the_seed_stands_on_real_ground_and_the_region_is_large(world, seed, reached):
    """A flood that starts nowhere reports nothing and passes. Both halves are checked: the seed
    is a cell a body can occupy with a solid block under it, and what it reaches is most of a
    park rather than a pocket."""
    assert walk.stands(world, seed)
    assert world.get((seed[0], seed[1] - 1, seed[2])) is not None, "the seed is standing on air"
    assert len(reached) > 20_000, \
        f"only {len(reached)} cells reached from the gate - the flood is proving nothing"


def test_every_reached_cell_really_has_two_clear_courses(reached, world):
    """HEADROOM, ASSERTED RATHER THAN INHERITED. `walk.stands` already demands it, so this can
    only fail if the model itself is changed - which is exactly what it is here to catch. Five
    separate bugs in this project have come from a check that counted BLOCKS where it should have
    counted the space a body occupies."""
    bad = [c for c in reached
           if not (walk._open(world, c) and walk._open(world, (c[0], c[1] + 1, c[2])))]
    assert bad == [], f"{len(bad)} 'walkable' cells with no room for a body, first {bad[:3]}"


# ------------------------------------------------------------------------ the walk, with no train

@pytest.mark.parametrize("zone", sorted(ZONE_Z))
def test_every_zone_is_reachable_from_the_gate_on_foot(reached, zone):
    """THE HEADLINE. No `Park Line` anywhere in the composite - if this passes, the land is
    connected and the railway is what it was always meant to be: a shortcut."""
    lo, hi = ZONE_Z[zone]
    here = [c for c in reached if lo <= c[2] <= hi]
    assert len(here) > 2_000, f"{zone} is reached by only {len(here)} cells without the railway"


@pytest.mark.parametrize("gap", sorted(GAP_Z))
def test_the_causeway_itself_is_walked_end_to_end(reached, gap):
    """Not merely touched at its ends: a walk that reaches the first row of a causeway and stops
    is a walk that never crossed it. Both extreme rows of each gap must be on the route."""
    lo, hi = GAP_Z[gap]
    rows = {c[2] for c in reached if lo <= c[2] <= hi}
    assert rows, f"{gap} is not walked at all"
    assert min(rows) <= lo + 2 and max(rows) >= hi - 2, \
        f"{gap} is walked only from z={min(rows)} to z={max(rows)}, not across"


def test_without_the_causeway_the_zones_come_apart(seed):
    """THE CONTROL, and the reason the test above means anything. Take the Isthmus out and the
    walk must FAIL to leave the midway - otherwise something else is carrying the connection and
    this file is measuring the wrong thing."""
    world = _composite([n for n in LAND if n != "Isthmus"] + EXTRA)
    if not walk.stands(world, seed):
        pytest.skip("the gate seed does not stand without the causeway in the composite")
    reach = walk.reachable(world, seed, limit=2_000_000)
    for zone in ("frontier", "hollow"):
        lo, hi = ZONE_Z[zone]
        stray = [c for c in reach if lo <= c[2] <= hi]
        assert len(stray) < 100, \
            f"{zone} is still reachable with the causeway removed - the walk is not crossing it"


@pytest.mark.skipif(not os.path.exists(f"out/{RAIL}.litematic"), reason="the line is not shipped")
def test_the_railway_only_ever_adds_to_the_walk(world, seed, reached):
    """A shortcut may make the walk shorter. It may not be what makes the walk POSSIBLE, and it
    may not take anything away either - a viaduct pier dropped through a street would do exactly
    that and every design would still audit clean on its own."""
    with_rail = dict(world)
    with_rail.update(_cells(RAIL))
    reach2 = walk.reachable(with_rail, seed, limit=2_000_000)
    lost = reached - reach2
    assert len(lost) < 50, \
        f"{len(lost)} cells walkable without the railway stop being walkable with it, e.g. {sorted(lost)[:3]}"
    assert len(reach2) >= len(reached), "the line adds no reachable cell at all - is it sited?"


# --------------------------------------------------------------------------- every attraction door

def _doors():
    """Every real module's link point, exactly as `planner._add_paths` joins it to the street -
    `_front_of`, or `_inside_of` for an edge module whose front lies off the owned land. A gate or
    an arch faces OUT of the park by definition, so its front point is over open void on purpose
    and only its inside face is ever meant to be walked to."""
    from mcbuild import islands as islands_mod
    out = []
    for zone, plan_name, island in (("frontier", "park_left", "islandleft"),
                                    ("midway", "park_centre", "newisle"),
                                    ("hollow", "park_right", "islandright")):
        try:
            pl = planner.Plan.load(plan_name)
        except (FileNotFoundError, OSError):
            continue
        plot = islands_mod.plot_of(island)
        own = planner._owned_bounds(plot, planner.THEMES[zone]) if plot is not None else None
        for m in pl.modules:
            if m["kind"] == "paths" or m.get("covers") or m["gen"] == "streetfurniture":
                continue
            front = planner._front_of(m)
            if m.get("edge") and own is not None and not (
                    own[0] <= front[0] <= own[1] and own[2] <= front[1] <= own[3]):
                front = planner._inside_of(m)
            out.append((zone, m["name"], front))
    return out


def test_every_attraction_door_is_reachable_without_the_railway(reached):
    """The whole roster, on foot. A door reached only by riding to the far station and walking
    back is a door this park does not really have."""
    doors = _doors()
    if not doors:
        pytest.skip("no park plans on disk to read doors from")
    reached_xz = {(x, z) for (x, _y, z) in reached}
    missing = [(zone, name, pt) for zone, name, pt in doors
               if not any((pt[0] + dx, pt[1] + dz) in reached_xz
                          for dx in (-2, -1, 0, 1, 2) for dz in (-2, -1, 0, 1, 2))]
    assert missing == [], f"{len(missing)} doors unreachable on foot: {missing[:4]}"


# ------------------------------------------------------------------------------ what is left over

def test_the_only_sealed_ground_is_a_ride_interior(world, reached):
    """A cell you can stand on and cannot reach is either a roof (fine - nobody walks to a roof)
    or a hole in the park. Restricted to STREET level, so the roofs are out of it by construction,
    what remains must be small and must be the inside of something you are carried into rather
    than a piece of street nobody can get to.

    Measured when this was written: 125 cells in 30 pockets, the largest being the Ghost Train's
    own 72-cell interior. The bound is generous; the point is that it cannot become a courtyard.
    """
    orphans = _street(world) - reached
    if not orphans:
        return
    seen, biggest = set(), 0
    for start in orphans:
        if start in seen:
            continue
        q, n = deque([start]), 0
        seen.add(start)
        while q:
            x, y, z = q.popleft()
            n += 1
            for dx in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        t = (x + dx, y + dy, z + dz)
                        if t in orphans and t not in seen:
                            seen.add(t)
                            q.append(t)
        biggest = max(biggest, n)
    assert len(orphans) < 400, \
        f"{len(orphans)} street cells are walled off from the park - that is a hole, not a ride"
    assert biggest < 200, f"a sealed street pocket of {biggest} cells is a room nobody can enter"
