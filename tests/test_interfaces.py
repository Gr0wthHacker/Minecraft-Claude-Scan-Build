"""The typed interface contract PARK_OVERHAUL.md makes mandatory.

These pin the CONTRACT, not the arithmetic: which anchors a module type owes, that a queue and a
discharge are never the same cell, that a handoff anchor is recorded rather than demanded, and
that the gate refuses a plan with an empty one. Pin the offsets instead and the layout can never
be tuned without rewriting the suite.
"""
import pytest

from mcbuild import interfaces as I


def _module(gen, kind, at=(0, 64, 0), size=(9, 5, 7), facing="east", **extra):
    return {"name": f"{gen} {kind}", "gen": gen, "kind": kind, "at": list(at),
            "size": list(size), "anchor_offset": [0, 0, 0],
            "params": {"land": "midway", "facing": facing}, **extra}


ALL_TYPES = sorted(I.REQUIRED)


def test_every_declared_type_can_place_every_anchor_it_requires():
    """A type that requires an anchor its layout cannot place would fail for every module of
    that type, for ever - the schema and the geometry have to agree at import time."""
    for kind_type, required in I.REQUIRED.items():
        layout = I._LAYOUT.get(kind_type, {})
        missing = [name for name in required if name not in layout]
        assert not missing, f"{kind_type} requires {missing} and has no layout for them"


def test_a_ride_declares_the_full_brief_table():
    ride = _module("coaster", "coaster", size=(30, 12, 30))
    I.annotate([ride])
    names = {a["name"] for a in ride["interface"]["anchors"]}
    assert {"approach", "queue_entry", "boarding", "ride_exit",
            "emergency_exit", "service_access"} <= names


def test_a_queue_mouth_and_a_discharge_are_never_the_same_cell():
    """Rule 4, within one module. Two anchors that resolve to one cell is a queue you leave by
    the door you joined it at, which is not a queue."""
    for gen, kind, size in (("coaster", "coaster", (30, 12, 30)),
                            ("bigwheel", "wheel", (25, 30, 25)),
                            ("arcade", "plinko", (9, 8, 8)),
                            ("attractions", "ghosttrain", (20, 10, 20))):
        for facing in ("north", "south", "east", "west"):
            module = _module(gen, kind, size=size, facing=facing)
            I.annotate([module])
            queues = [tuple(a["at"]) for a in module["interface"]["anchors"] if a["queue"]]
            exits = [tuple(a["at"]) for a in module["interface"]["anchors"] if a["exit"]]
            assert queues and exits, f"{gen}/{kind} declares no queue or no exit"
            assert not (set(queues) & set(exits)), f"{gen}/{kind} facing {facing}: queue is exit"


def test_the_service_door_is_never_on_the_public_face():
    """A backstage door on the shopfront is not backstage. It is the rear face by construction,
    at every facing - which is the only reason the concealed service road can reach it."""
    for facing in ("north", "south", "east", "west"):
        shop = _module("frontiertown", "saloon", facing=facing)
        I.annotate([shop])
        by_name = {a["name"]: a for a in shop["interface"]["anchors"]}
        assert by_name["service_access"]["face"] == I._BACK[facing]
        assert by_name["frontage"]["face"] == facing


def test_an_anchor_off_the_owned_land_is_recorded_not_demanded():
    """An arch's connector side lies outside the land BY DEFINITION - that is what makes it a
    handoff. Dropping it hides the interface; demanding paving for it asks this land to build
    the connector's half of the threshold. It is marked, and the attachment check skips it."""
    arch = _module("park", "arch", at=(92, 64, 50), size=(9, 9, 5), facing="east", edge=True)
    I.annotate([arch], owned=(0, 100, 0, 100))
    by_name = {a["name"]: a for a in arch["interface"]["anchors"]}
    assert by_name["connector_side"]["off_land"], "the connector side is inside the owned land"
    assert not by_name["land_side"]["off_land"]
    demanded = {f["anchor"] for f in I.unattached([arch], paving=set())}
    assert "connector_side" not in demanded, "a handoff anchor was demanded of the paving"
    assert "land_side" in demanded, "the park side of the threshold was excused too"


def test_a_public_anchor_on_the_land_is_demanded():
    """The other half of the rule, or `off_land` would be a way to excuse anything."""
    shop = _module("frontiertown", "saloon", at=(50, 64, 50))
    I.annotate([shop], owned=(0, 100, 0, 100))
    assert I.unattached([shop], paving=set()), "an on-land public anchor passed with no paving"


def test_missing_anchors_names_the_module_and_the_anchor():
    """"A plan cannot be prepared or promoted when a public module has empty anchors" - so the
    failure has to be actionable, not a count."""
    ride = _module("coaster", "coaster", size=(30, 12, 30))
    I.annotate([ride])
    ride["interface"]["anchors"] = [a for a in ride["interface"]["anchors"]
                                    if a["name"] != "ride_exit"]
    failures = I.missing_anchors([ride])
    assert [f["anchor"] for f in failures] == ["ride_exit"]
    assert failures[0]["module"] == ride["name"]


def test_an_anchor_with_no_world_point_counts_as_empty():
    """A named anchor that resolves to nothing is the "decorative doorway" rule 2 forbids,
    wearing the schema's own clothes."""
    ride = _module("coaster", "coaster", size=(30, 12, 30))
    I.annotate([ride])
    for anchor in ride["interface"]["anchors"]:
        if anchor["name"] == "boarding":
            anchor["at"] = None
    assert any(f["anchor"] == "boarding" for f in I.missing_anchors([ride]))


def test_two_modules_may_not_own_one_anchor_address():
    a = _module("coaster", "coaster", size=(30, 12, 30))
    b = _module("coaster", "coaster", at=(100, 64, 100), size=(30, 12, 30))
    b["name"] = a["name"]
    I.annotate([a, b])
    with pytest.raises(ValueError, match="duplicate anchor"):
        I.anchor_index([a, b])


def test_an_exit_into_a_neighbours_queue_is_caught():
    """The arrangement problem no single module can see about itself."""
    shop = _module("arcade", "prizecounter", at=(0, 64, 0), size=(6, 5, 6), facing="east")
    # Sited so its neighbour's queue mouth lands on this one's collection point - which is
    # exactly the Reliquary/Vault arrangement the Hollow plan shipped with.
    ride = _module("arcade", "safe", at=(9, 64, 3), size=(6, 5, 6), facing="west")
    ride["name"] = "The Vault"
    I.annotate([shop, ride])
    hits = I.exit_queue_collisions([shop, ride])
    assert hits, "a discharge landing on the neighbour's queue mouth read as clear"
    assert "The Vault" in hits[0]["reason"]


def test_a_land_specs_own_anchor_name_resolves_to_the_park_wide_one():
    """PARK_HOLLOW says `boarding_or_entry` and `wet_exit`; PARK_FRONTIER says `maintenance_
    access`. One validator serves all three lands or each land grows its own."""
    assert I.resolve("boarding_or_entry") == "boarding"
    assert I.resolve("wet_exit") == "ride_exit"
    assert I.resolve("maintenance_access") == "service_access"
    assert I.resolve("service_boundary") == "service_access"
    assert I.resolve("queue_entry") == "queue_entry"


def test_signage_owes_a_cell_it_is_read_from():
    """Rule 7 makes wayfinding part of the path graph. Three map boards across the three lands
    were standing off the street when this was first measured."""
    sign = _module("wayfinding", "mapboard", size=(3, 9, 11))
    I.annotate([sign])
    assert I.module_type(sign) == "sign"
    names = {a["name"] for a in sign["interface"]["anchors"]}
    assert names == {"read_from"}
    assert all(a["public"] for a in sign["interface"]["anchors"])


def test_a_bench_owes_nothing():
    """Street furniture is dressing placed along an avenue after it is drawn. Demanding a service
    door from a planter is the check that cries wolf."""
    bench = _module("streetfurniture", "bench", size=(3, 2, 1))
    I.annotate([bench])
    assert bench["interface"]["anchors"] == []
    assert not I.missing_anchors([bench])


def test_a_service_door_moves_to_a_flank_when_its_rear_is_off_the_land():
    """**A SERVICE DOOR ON A FACE THAT IS OFF THE LAND CAN NEVER HAVE A YARD.** The layout puts
    the backstage on the rear by construction, which is right until the rear IS the boundary: the
    Midway's admission sequence is pinned to its west edge facing east, so five of its rear doors
    opened onto the neighbour's ground and no backstage road could legally reach them.

    A shopfront's direction is a decision and stays where it is put; a service door only has to
    be somewhere a road can get to."""
    # Hard against the western boundary, facing east: its rear is off the land.
    shop = _module("frontiertown", "saloon", at=(0, 64, 50), size=(11, 6, 9), facing="east")
    I.annotate([shop], owned=(0, 100, 0, 100))
    door = next(a for a in shop["interface"]["anchors"] if a["name"] == "service_access")
    x, _y, z = door["at"]
    assert 0 <= x <= 100 and 0 <= z <= 100, "the service door is still off the land"
    assert door["face"] != "west", "it stayed on the rear face that cannot be reached"


def test_a_service_door_stays_on_the_rear_when_the_rear_is_reachable():
    """The fallback is for a door that CANNOT exist where it belongs, not a licence to put the
    backstage wherever. A module with land behind it keeps its rear door."""
    shop = _module("frontiertown", "saloon", at=(50, 64, 50), size=(11, 6, 9), facing="east")
    I.annotate([shop], owned=(0, 100, 0, 100))
    door = next(a for a in shop["interface"]["anchors"] if a["name"] == "service_access")
    assert door["face"] == "west"


def test_a_shopfront_never_moves_to_a_flank():
    """The asymmetry is the point: where a customer entrance faces is a design decision, and
    silently turning it to suit the plot is how a building ends up addressing nothing."""
    shop = _module("frontiertown", "saloon", at=(0, 64, 50), size=(11, 6, 9), facing="east")
    I.annotate([shop], owned=(0, 100, 0, 100))
    for name in ("frontage", "customer_entry", "queue_entry", "collection_or_exit"):
        anchor = next(a for a in shop["interface"]["anchors"] if a["name"] == name)
        assert anchor["face"] == "east", f"{name} was moved off the shopfront"
