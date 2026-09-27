"""Vertical zoning: PARK_VERTICAL_MASTERPLAN.md section 3, as measurements.

The properties worth pinning are the ones that were got WRONG on the way here: a module that
spans bands is a connector rather than a violation, a bounding box is not a building, and an
estimate may not fail a build. Each of those was a version of this gate that reported a correct
park as broken.
"""
import pytest

from mcbuild import bands as B, interfaces as I

PLANE = 203


def _module(gen, kind, y, height, size=(9, 9), blocks=None, name=None):
    module = {"name": name or f"{gen} {kind}", "gen": gen, "kind": kind,
              "at": [0, y, 0], "size": [size[0], height, size[1]],
              "anchor_offset": [0, 0, 0], "params": {"land": "midway", "facing": "east"}}
    if blocks is not None:
        module["blocks"] = blocks
    return module


def test_the_six_bands_tile_the_world_with_no_gap_and_no_overlap():
    """A course that belongs to no band, or to two, is a course the gate cannot judge."""
    seen = {}
    for y in range(B.WORLD_FLOOR, B.WORLD_CEILING + 1):
        band = B.band_of(y, PLANE)
        assert band in {name for name, _l, _h in B.BANDS}
        seen[band] = seen.get(band, 0) + 1
    assert len(seen) == len(B.BANDS), f"only {sorted(seen)} are reachable at plane {PLANE}"


def test_a_band_is_relative_to_the_build_plane():
    """The three lands sit on three islands. A band written as an absolute Y is a band that is
    wrong on two of them the day the third one moves."""
    for plane in (0, 64, 203, 300):
        low, high = B.limits("public_park", plane)
        assert low == max(B.WORLD_FLOOR, plane - 8)
        assert high == min(B.WORLD_CEILING, plane + 28)


def test_a_band_never_resolves_outside_the_server():
    for plane in (B.WORLD_FLOOR, 0, 203, B.WORLD_CEILING):
        for name, _low, _high in B.BANDS:
            low, high = B.limits(name, plane)
            assert B.WORLD_FLOOR <= low <= B.WORLD_CEILING
            assert B.WORLD_FLOOR <= high <= B.WORLD_CEILING


def test_a_plane_too_low_for_a_band_says_so_rather_than_inventing_room():
    """An island at Y0 has no void-edge band at all: B-160 is a hundred courses below the world
    floor. The first version clamped only the top end and produced -64..-224 - a band whose low
    is above its high, which every consumer would then measure as negative volume.

    Deep adventure at the same plane is TRUNCATED rather than absent: -64..-48 is sixteen real
    courses. Reporting it as empty would be the opposite error, and the distinction is the point
    - one island has less room beneath it, another has none.
    """
    assert not B.has_band("void_edge", 0)
    assert B.has_band("deep_adventure", 0)
    assert B.limits("deep_adventure", 0) == (B.WORLD_FLOOR, -48)
    assert B.has_band("void_edge", 203)
    shares = B.occupancy([], 0, 9801)
    assert shares["void_edge"]["cells"] == 0
    assert shares["void_edge"]["share"] == 0.0


def test_a_module_that_spans_bands_is_a_connector_not_a_violation():
    """**THIS GATE HAD IT BACKWARDS FIRST.** Checking every band a module touches failed the
    Mine Head for reaching the hidden core - which is the entire point of a headframe - and the
    Haunted Manor for being three storeys tall. What the masterplan forbids is a module sited
    WHOLLY in a band whose function it does not answer."""
    headframe = _module("frontiertown", "minehead", PLANE - 20, 40, blocks=239)
    report = B.check([headframe], PLANE, 9801, I.module_type)
    assert report["ok"], report["failures"]
    assert report["connectors"], "a module crossing two bands was not reported as a connector"
    assert set(report["connectors"][0]["bands"]) == {"hidden_core", "public_park"}


def test_a_module_wholly_in_the_wrong_band_is_caught():
    """The other half, or the connector rule would excuse anything tall."""
    shop = _module("spectacle", "foodcourt", PLANE + 120, 6, blocks=400)
    report = B.check([shop], PLANE, 9801, I.module_type)
    assert not report["ok"]
    assert any("skyline" in f for f in report["failures"])


def test_a_module_outside_the_server_range_is_caught():
    tower = _module("hollowmanor", "clocktower", B.WORLD_CEILING - 5, 40, blocks=100)
    report = B.check([tower], PLANE, 9801, I.module_type)
    assert not report["ok"]
    assert any("outside the server" in f for f in report["failures"])


def test_a_bounding_box_is_not_a_building():
    """The Big Wheel is 19 x 85 x 77 and is mostly the air a wheel turns in. Counted as its box
    it filled 22% of the whole upper band on its own."""
    wheel = _module("bigwheel", "wheel", PLANE, 85, size=(19, 77), blocks=6446)
    boxed = _module("bigwheel", "wheel", PLANE, 85, size=(19, 77))
    real = B.occupancy([wheel], PLANE, 9801)
    estimate = B.occupancy([boxed], PLANE, 9801)
    assert real["upper_attraction"]["cells"] < estimate["upper_attraction"]["cells"] / 10


def test_an_estimate_warns_where_a_measurement_would_fail():
    """Before a module is generated there is no block count to read, and failing an occupancy
    ceiling on a bounding box blocks a plan for the SHAPE of a wheel rather than for anything
    anyone built."""
    boxed = _module("bigwheel", "wheel", PLANE, 85, size=(19, 77))
    report = B.check([boxed], PLANE, 9801, I.module_type)
    assert report["ok"], "an estimate failed a build"
    assert any("estimated" in w for w in report["warnings"])
    assert report["estimated_modules"] == 1

    measured = dict(boxed, blocks=boxed["size"][0] * boxed["size"][1] * boxed["size"][2])
    hard = B.check([measured], PLANE, 9801, I.module_type)
    assert not hard["ok"], "a measured overfill did not fail"


def test_a_land_in_one_band_is_reported_as_flat():
    """The masterplan's whole premise: "It is not a flat fairground with extra tunnels."""
    ground = [_module("arcade", "plinko", PLANE, 8, blocks=200)]
    report = B.check(ground, PLANE, 9801, I.module_type)
    assert any("flat fairground" in w for w in report["warnings"])


# ------------------------------------------------------------------ the grade rule

def test_a_level_route_has_no_grade_to_check():
    assert B.grade_failures([{"a": [0, 0], "b": [20, 0], "width": 5, "role": "main_spine"}]) == []


def test_a_public_route_steeper_than_one_in_one_is_caught():
    steep = [{"a": [0, 64, 0], "b": [4, 80, 0], "width": 5, "role": "main_spine"}]
    assert B.grade_failures(steep)


def test_a_steep_route_declared_as_stairs_is_allowed():
    """A steeper change is legitimate - it is simply a different thing, and has to say so, so
    the build knows to put treads on it."""
    stairs = [{"a": [0, 64, 0], "b": [4, 80, 0], "width": 5, "role": "main_spine",
               "vertical": "stairs"}]
    assert B.grade_failures(stairs) == []


def test_a_service_route_is_not_held_to_the_public_grade():
    """The rule is about a GUEST walking. A maintenance ladder is not a promenade."""
    steep = [{"a": [0, 64, 0], "b": [1, 90, 0], "width": 3, "role": "service"}]
    assert B.grade_failures(steep) == []
