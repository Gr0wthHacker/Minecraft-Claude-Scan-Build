"""Capacity-aware circulation: rule 4 and rule 6, as geometry.

The properties here are the two the brief will not trade away - a queue is never a through-route,
and every declared public interface is on the network - plus the widths rule 6 states. They are
asserted against the three REAL lands as well as against fixtures, because a rule that holds on a
synthetic three-module park and fails on the shipped one is a rule nobody is keeping.
"""
import pytest

from mcbuild import circulation, interfaces as I, pathgraph as P

ZONES = ("midway", "frontier", "hollow")


def _module(gen, kind, at, size, facing="east", **extra):
    return {"name": extra.pop("name", f"{gen} {kind} {at[0]}"), "gen": gen, "kind": kind,
            "at": list(at), "size": list(size), "anchor_offset": [0, 0, 0],
            "params": {"land": "midway", "facing": facing}, **extra}


@pytest.fixture(scope="module")
def planned():
    import sys
    sys.path.insert(0, "tests")
    import test_park_plan as T
    return {zone: T._planned(zone) for zone in ZONES}


# ------------------------------------------------------------------ the rules, on real lands

@pytest.mark.parametrize("zone", ZONES)
def test_every_declared_public_interface_is_on_the_network(planned, zone):
    """Rule 2, measured against the interface schema rather than against front doors.

    The pass this replaced ran one spur to one front-of-building point per module, and that left
    61 public anchors across the three lands standing on nothing - every ride exit, every
    emergency exit, every flank queue mouth, every view approach.
    """
    plan = planned[zone]
    walkable = P.walkable(P.normalise(plan.routes))
    stranded = I.unattached(plan.modules, walkable)
    assert not stranded, (f"{zone}: {len(stranded)} public anchors off the network, "
                          f"e.g. {stranded[:3]}")


@pytest.mark.parametrize("zone", ZONES)
def test_a_queue_never_carries_a_through_route(planned, zone):
    """Rule 4. A queue cell that is also a through-route cell IS the queue being used as one;
    there is no other way for that to happen."""
    routes = P.normalise(planned[zone].routes)
    assert not (P.public(routes) & P.footprint(routes, {"queue"}))


@pytest.mark.parametrize("zone", ZONES)
def test_the_walkable_network_is_one_piece(planned, zone):
    routes = P.normalise(planned[zone].routes)
    groups = P.components(P.walkable(routes))
    assert len(groups) == 1, f"{zone}: the network is in {len(groups)} pieces"


@pytest.mark.parametrize("zone", ZONES)
def test_every_route_meets_its_roles_minimum_width(planned, zone):
    """Rule 6: 5-block spine, 3-block secondary, 2-3-block queues, hidden 2-block service."""
    for route in P.normalise(planned[zone].routes):
        minimum, _through, _concealed = P.ROLES[route["role"]]
        assert route["width"] >= minimum, f"{zone}: {route.get('name')} is {route['width']} wide"


@pytest.mark.parametrize("zone", ZONES)
def test_the_land_declares_every_capacity_role_it_needs(planned, zone):
    """A land with no declared roles is a land whose circulation has not been designed, and the
    capacity gate would grade it compliant by defaulting every route to a street."""
    routes = planned[zone].routes
    assert routes, f"{zone}: no circulation at all"
    assert all("role" in r for r in routes)
    roles = {r["role"] for r in routes}
    assert "main_spine" in roles and "secondary" in roles and "service" in roles


@pytest.mark.parametrize("zone", ZONES)
def test_the_service_road_never_becomes_the_street(planned, zone):
    """A crossing is not a conflict - a road to a back door has to cross the guest paths between
    it and the perimeter, and real parks do exactly that. What is forbidden is a backstage route
    that RUNS ALONG a public one, because that is not a backstage route, it is the street."""
    routes = P.normalise(planned[zone].routes)
    parallel = [o for o in P.service_overlaps(routes) if o["parallel"]]
    assert not parallel, f"{zone}: {parallel[:2]}"


def test_a_door_with_room_behind_it_gets_a_yard():
    """The positive case, on a module with open land at its back: a service door earns backstage
    paving. Without this the reporting test below would pass on a build that never lays any."""
    shop = _module("frontiertown", "saloon", (0, 64, 0), (11, 6, 9), name="Saloon")
    I.annotate([shop])
    routes = circulation.build([shop], (60, 60), (-40, 120, -40, 120))
    assert not circulation.unserviced_doors([shop], routes)


@pytest.mark.parametrize("zone", ZONES)
def test_a_door_with_no_backstage_is_reported_by_name(planned, zone):
    """**THE BACKSTAGE YIELDS, SO SOME DOORS GENUINELY GET NOTHING.** On a 99x99 plot with ten
    columns already reserved for the transit corridor, the land behind one building is often
    under the path to the next - measured over the three lands, 19 service doors and 9 of them
    with no yard. Inventing a road down a guest path to make that number zero would be the
    decorative-doorway failure with the roles reversed, so what is asserted is that the tool
    NAMES them: a reviewer can act on "The Plummet, The Seance, Mirror Maze" and cannot act on
    a silence.
    """
    plan = planned[zone]
    for entry in circulation.unserviced_doors(plan.modules, plan.routes):
        assert entry["module"] and entry["at"], entry
        assert "backstage" in entry["reason"]



# ------------------------------------------------------------------ the rules, as fixtures

def test_a_queue_route_that_carries_a_through_route_fails_the_gate():
    """The check has to be able to FAIL, or every land passes it by accident."""
    routes = [{"a": [0, 0], "b": [20, 0], "width": 5, "role": "main_spine"},
              {"a": [10, 0], "b": [10, 10], "width": 3, "role": "queue"}]
    report = P.check(routes)
    assert not report["ok"]
    assert any("queue" in f for f in report["failures"])


def test_a_narrow_spine_fails_the_gate():
    routes = [{"a": [0, 0], "b": [20, 0], "width": 3, "role": "main_spine"}]
    report = P.check(routes)
    assert not report["ok"]
    assert any("5-block minimum" in f for f in report["failures"])


def test_a_split_network_fails_the_gate():
    routes = [{"a": [0, 0], "b": [10, 0], "width": 5, "role": "main_spine"},
              {"a": [50, 50], "b": [60, 50], "width": 5, "role": "main_spine"}]
    report = P.check(routes)
    assert not report["ok"]
    assert any("disconnected" in f for f in report["failures"])


def test_a_land_with_undeclared_roles_is_reported_not_excused():
    """The old plans have routes with widths and no roles. Defaulting them silently would grade
    an undesigned circulation as compliant; defaulting them LOUDLY is the honest version."""
    report = P.check([{"a": [0, 0], "b": [20, 0], "width": 5}])
    assert any("no declared capacity role" in w for w in report["warnings"])


def test_an_l_route_lays_both_of_its_legs():
    """A frontage walk beyond the avenue's own span has to travel along the avenue's axis to get
    onto it. Drawing only the dominant axis silently loses the second half and leaves the walk
    joined to nothing."""
    cells = P.cells({"a": [0, 0], "b": [10, 10], "width": 1})
    assert (5, 0) in cells and (10, 5) in cells


def test_a_frontage_walk_serves_every_anchor_on_its_face():
    """One pavement past every door on a face, rather than one spur to the middle of it - which
    is what makes a queue mouth at 0.20 and an exit at 0.80 both reachable."""
    ride = _module("coaster", "coaster", (0, 64, 0), (30, 12, 30), name="Ride")
    I.annotate([ride])
    routes = circulation.build([ride], (60, 60), (-40, 120, -40, 120))
    walkable = P.walkable(P.normalise(routes))
    assert not I.unattached([ride], walkable)


def test_the_join_from_an_exit_walk_is_an_ordinary_street():
    """Rule 4's second half: an exit route running onto the spine IS a ride discharging into a
    primary promenade. The discharge happens on the walk; what joins it to the park is a street."""
    ride = _module("attractions", "ghosttrain", (0, 64, 0), (20, 10, 20), name="Train")
    I.annotate([ride])
    routes = circulation.build([ride], (60, 60), (-40, 120, -40, 120))
    for route in routes:
        if route["role"] == "exit":
            assert "frontage" in (route.get("name") or ""), \
                f"an exit-typed route is a join, not a walk: {route.get('name')}"
