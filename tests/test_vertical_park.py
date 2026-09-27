"""The park is vertical: PARK_VERTICAL_MASTERPLAN.md, as circulation rather than as a diagram.

Every property here failed at least once on the way to being true, and each failure was the same
shape: a plan-view check saying yes about a thing that lives somewhere else in Y. A module twenty
four courses under the town read as being on its street; the street's shadow is not the street.
"""
import pytest

from mcbuild import bands as B, circulation, interfaces as I, pathgraph as P, planner

ZONES = ("midway", "frontier", "hollow")
PLANE = 203


@pytest.fixture(scope="module")
def planned():
    import sys
    sys.path.insert(0, "tests")
    import test_park_plan as T
    return {zone: T._planned(zone) for zone in ZONES}


def _module(gen, kind, at, size, facing="east", name=None):
    return {"name": name or f"{gen} {kind}", "gen": gen, "kind": kind, "at": list(at),
            "size": list(size), "anchor_offset": [0, 0, 0],
            "params": {"land": "frontier", "facing": facing}}


# ------------------------------------------------------------------ anchors carry elevation

def test_an_anchor_stands_on_its_own_modules_course():
    """Pinning every anchor to the land's plane was harmless while every module sat on it, and
    wrong the moment one did not: an underground ride's queue mouth was reported at street
    level, so the route gate saw a ride nobody could reach as perfectly served."""
    below = _module("attractions", "runawaymine", (0, PLANE - 24, 0), (26, 12, 23))
    above = _module("attractions", "runawaymine", (0, PLANE, 0), (26, 12, 23))
    I.annotate([below, above], PLANE)
    # **AND THE BUILD PLANE IS THE COURSE YOU STAND ON.** `tools/parkship.py` states it: the
    # FLOOR is the course the floor blocks occupy, one under it. An anchor a course higher was
    # consistent with everything that only compared anchors to anchors, and wrong the moment
    # anything compared one to a BLOCK.
    assert below["interface"]["anchors"][0]["at"][1] == PLANE - 24
    assert above["interface"]["anchors"][0]["at"][1] == PLANE


def test_a_plan_view_hit_is_not_an_attachment():
    """The load-bearing property. A cell of paving directly over an anchor is rock between
    them, and the check has to say so rather than counting the column."""
    below = _module("attractions", "runawaymine", (0, PLANE - 24, 0), (26, 12, 23))
    I.annotate([below], PLANE)
    paving = {(a["at"][0], a["at"][2]) for a in below["interface"]["anchors"]}
    assert not I.unattached([below], paving), "the plan-view check is what it always was"
    levels = {cell: {PLANE} for cell in paving}
    stranded = I.unattached([below], paving, levels)
    assert stranded, "an anchor 24 courses under the paving read as served"
    assert all("elevation" in u["reason"] for u in stranded)


def test_a_single_step_is_still_reachable():
    """One course is a step, not a climb - demanding a stair for it is the check that cries
    wolf, and every doorway in the park is one course up from its street."""
    module = _module("frontiertown", "saloon", (0, PLANE, 0), (11, 6, 9))
    I.annotate([module], PLANE)
    paving = {(a["at"][0], a["at"][2]) for a in module["interface"]["anchors"]}
    levels = {cell: {PLANE} for cell in paving}
    assert not I.unattached([module], paving, levels)


# ------------------------------------------------------------------ shafts

def test_an_off_plane_module_gets_a_shaft_and_a_landing():
    surface = _module("frontiertown", "saloon", (40, PLANE, 40), (11, 6, 9), name="Saloon")
    below = _module("attractions", "runawaymine", (0, PLANE - 24, 0), (26, 12, 23), name="Mine")
    I.annotate([surface, below], PLANE)
    routes = circulation.build([surface, below], (60, 60), (-40, 140, -40, 140), PLANE)
    shafts = [r for r in routes if r["role"] == "shaft"]
    assert len(shafts) == 1, [r.get("name") for r in shafts]
    shaft = shafts[0]
    assert shaft["a"][1] == PLANE and shaft["b"][1] == PLANE - 24
    assert (shaft["a"][0], shaft["a"][2]) == (shaft["b"][0], shaft["b"][2]), \
        "a shaft that moves horizontally is a ramp, and has to say so"
    landings = [r for r in routes if "landing" in (r.get("name") or "")]
    assert landings, "the underground module got no circulation of its own"
    assert all(len(r["a"]) == 3 and r["a"][1] == PLANE - 24 for r in landings)


def test_a_shaft_spans_the_courses_between_its_ends():
    """`levels` is what makes an anchor below the street reachable from it, and a shaft is the
    only route whose cells belong to more than one course."""
    routes = [{"a": [0, 100, 0], "b": [0, 80, 0], "width": 3, "role": "shaft"}]
    reach = P.levels(routes, 100)
    assert reach[(0, 0)] == set(range(80, 101))


def test_a_shaft_occupies_one_column_not_a_diagonal():
    """Swept as an ordinary run between its two endpoints it would pave a line nobody walks."""
    cells = P.cells({"a": [10, 100, 10], "b": [10, 60, 10], "width": 3, "role": "shaft"})
    assert cells == {(x, z) for x in range(9, 12) for z in range(9, 12)}


def test_a_land_with_an_underground_module_is_one_walk(planned):
    """**THE SHAFT HEAD HAS TO BE ON THE STREET, or the whole lower level is an island.** The
    shaft stands in its module's own column, which on the surface is not anywhere the town
    paved, so the network came out in two pieces - correctly: a guest could reach the landing
    only by already being on it."""
    plan = planned["frontier"]
    routes = P.normalise(plan.routes)
    assert any(r["role"] == "shaft" for r in routes), "the Frontier has no vertical circulation"
    assert len(P.components(P.walkable(routes))) == 1


@pytest.mark.parametrize("zone", ZONES)
def test_every_public_anchor_is_reachable_in_elevation_too(planned, zone):
    plan = planned[zone]
    routes = P.normalise(plan.routes)
    hub = next(m for m in plan.modules if m.get("covers") and m["kind"] == "plaza")
    levels = P.levels(routes, int(hub["at"][1]))
    stranded = I.unattached(plan.modules, P.walkable(routes), levels)
    assert not stranded, f"{zone}: {stranded[:2]}"


def test_a_shaft_is_declared_as_stairs_so_the_grade_rule_allows_it():
    """A lift down twenty-four courses is steeper than one-in-one by construction. Section 4
    permits that only when the route says what it is."""
    routes = [{"a": [0, 100, 0], "b": [0, 76, 0], "width": 3, "role": "shaft"}]
    assert B.grade_failures(routes), "an undeclared vertical run passed the grade rule"
    routes[0]["vertical"] = "stairs"
    assert not B.grade_failures(routes)


# ------------------------------------------------------------------ districts

def test_a_district_is_sited_together(planned):
    """PARK_HOLLOW.md: "stop treating eleven small modules as equal attractions". Grouping is a
    preference, not a guarantee - a plot already holding a 47x47 coaster sometimes has no
    contiguous land left - so what is asserted is that naming a district MOVES the members
    closer than not naming one would."""
    plan = planned["hollow"]
    market = [m for m in plan.modules if m.get("district") == "Crypt Market"]
    assert len(market) >= 5
    spread = planner._district_spread(market)
    assert spread <= 99, f"the market spans {spread} cells, wider than the plot"


def test_a_district_that_could_not_be_grouped_says_so(planned):
    """Sited apart and silent, a theme claims a street it does not have."""
    for zone in ZONES:
        plan = planned[zone]
        for name, members in planner._districts_of(plan.modules).items():
            if planner._district_spread(members) > planner.DISTRICT_SPREAD:
                assert any(f"district {name!r}" in note for note in plan.notes), \
                    f"{zone}: {name} is spread and nothing said so"


def test_siting_refuses_a_spot_that_breaks_rule_four():
    """The check has to be able to REFUSE, and its first version could not: interfaces are
    annotated after siting, so a freshly-annotated candidate was compared against modules with
    no anchors at all - nineteen checks, zero refusals."""
    counter = _module("arcade", "prizecounter", (0, 64, 0), (6, 5, 6), facing="east")
    counter["name"] = "Counter"
    vault = _module("arcade", "safe", (9, 64, 3), (6, 5, 6), facing="west")
    vault["name"] = "The Vault"
    assert not planner._rule_four_clear([vault], counter)
    far = dict(counter, at=[0, 64, 60])
    assert planner._rule_four_clear([vault], far)
