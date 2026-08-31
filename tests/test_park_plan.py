"""The park's three THEMES, and the two planner faults they exposed.

Both faults produced a plan that looked completely reasonable and was wrong, which is the only
kind this project keeps shipping.
"""
import pytest

from mcbuild import planner
from mcbuild.gen import GENERATORS, park

ZONES = ["midway", "frontier", "hollow"]


def test_a_theme_name_in_the_brief_beats_another_themes_keyword():
    """THE FAULT: `_theme_for` tested a theme's NAME and its KEYWORDS together, and returned on
    the first theme where either passed. `midway` carries the generic keyword "theme park", so
    "theme park frontier" and "theme park hollow" both matched `midway` before the loop ever
    reached their own entries, and all three zones planned as the centre.

    It was caught only because two different briefs produced byte-identical 10,403-block plans.
    An explicit name is the strongest signal a brief can carry, so it is resolved first, across
    ALL themes, before any keyword is considered.
    """
    assert planner._theme_for("theme park frontier") == "frontier"
    assert planner._theme_for("theme park hollow") == "hollow"
    assert planner._theme_for("theme park midway") == "midway"
    # the generic keyword still works on its own, which is why it is allowed to exist
    assert planner._theme_for("build me a theme park") == "midway"


def test_an_unmatched_brief_raises_rather_than_defaulting():
    with pytest.raises(ValueError):
        planner._theme_for("an aquarium")


@pytest.mark.parametrize("zone", ZONES)
def test_every_module_of_every_zone_names_a_real_generator_and_land(zone):
    for m in planner.THEMES[zone]["modules"]:
        assert m["gen"] in GENERATORS, f"{m['name']}: no generator {m['gen']!r}"
        assert m["kind"] in park.BUILDERS, f"{m['name']}: no park kind {m['kind']!r}"
        assert m["params"]["land"] in park.LANDS, f"{m['name']}: no land"
        assert m["params"]["facing"] in park._STEP, f"{m['name']}: bad facing"


@pytest.mark.parametrize("zone", ZONES)
def test_the_covering_module_is_last(zone):
    """A COVERING MODULE IS NOT COMPETING FOR SPACE, IT IS THE SPACE - and laid first it would
    take the floor out from under everything sited after it. The casino hall settled this."""
    mods = planner.THEMES[zone]["modules"]
    covers = [i for i, m in enumerate(mods) if m.get("anchor") == "cover"]
    assert covers == [len(mods) - 1], f"{zone}: the covering module must be last, got {covers}"


@pytest.mark.parametrize("zone", ZONES)
def test_the_biggest_module_is_sited_first(zone):
    """`bays` packs in LIST ORDER, so a big module listed late finds the grid full of booths and
    reports NO SITE - the Colour Wheel did exactly that three times. A module is not unsiteable
    because it is late.

    **MEASURED, NOT DECLARED, AND THE DIFFERENCE IS THE WHOLE TEST.** Ordered by the hand-typed
    `size` all three zones looked right and all three were wrong: a tower declared 15x15 measures
    13x13 while a walkthrough declared 15x15 measures 15x15, so the tower was listed first in
    every zone while actually being the SMALLER module. `measured_footprint` is what the planner
    packs with, so it is what the ordering has to be judged against - rule 11 pointed at
    ourselves, exactly as that function's own docstring says.
    """
    mods = [m for m in planner.THEMES[zone]["modules"]
            if m.get("anchor") not in ("cover", "edge")]
    areas = []
    for m in mods:
        _fx, _fy, _fz, fw, _fh, fd = planner.measured_footprint(
            m["gen"], m["kind"], dict(m.get("params", {})), m["size"])
        areas.append(fw * fd)
    assert areas[0] == max(areas), (
        f"{zone}: {mods[0]['name']} is {areas[0]} but the largest is "
        f"{mods[areas.index(max(areas))]['name']} at {max(areas)}")


@pytest.mark.parametrize("zone", ZONES)
def test_every_edge_module_names_the_side_it_is_pinned_to(zone):
    """An arch to the west that is not ON the western edge does not lead anywhere, and a gate
    sited by `bays` is a gatehouse in the middle of a field: you walk round it."""
    for m in planner.THEMES[zone]["modules"]:
        if m.get("anchor") != "edge":
            continue
        assert m.get("side") in ("north", "south", "east", "west"), f"{m['name']}: no side"
        # ...and it must FACE outward, or the doorway opens into the zone it is leaving
        assert m["params"]["facing"] == m["side"], \
            f"{m['name']} is pinned {m['side']} but faces {m['params']['facing']}"


def test_the_centre_zone_leads_to_both_others():
    """The park is three islands and `newisle` is the middle one. If the centre does not carry an
    arch to each neighbour, the zones are three separate parks."""
    lands = {m["params"]["land"] for m in planner.THEMES["midway"]["modules"]
             if m["kind"] == "arch"}
    assert lands == {"frontier", "hollow"}, f"the centre leads to {lands}"
    # THE ISLANDS RUN ALONG Z, measured off the three captures: bedrock 97600 at Z 80400, 80600
    # and 80800. So "left" is NORTH and "right" is SOUTH, and the first version of this - arches
    # east and west - was pointing them at empty void on the wrong axis entirely.
    sides = {m["side"] for m in planner.THEMES["midway"]["modules"] if m.get("anchor") == "edge"}
    assert {"north", "south"} <= sides, "the two arches must be on opposite edges along Z"
    assert "west" in sides, "the main gate takes the free axis"


def test_the_side_zones_lead_back_to_the_centre():
    """A one-way park is a bug. The frontier is WEST of the centre, so its way back is EAST."""
    back = {z: [m for m in planner.THEMES[z]["modules"] if m.get("anchor") == "edge"]
            for z in ("frontier", "hollow")}
    assert [m["side"] for m in back["frontier"]] == ["south"], "frontier is north; it leads back south"
    assert [m["side"] for m in back["hollow"]] == ["north"], "hollow is south; it leads back north"


@pytest.mark.parametrize("zone", ZONES)
def test_a_zone_is_more_than_one_kind_of_thing(zone):
    """Three zones of six identical booths would be the casino's eighteen identical grey rooms
    again. A zone needs a landmark, something to walk through, and something to do."""
    kinds = {m["kind"] for m in planner.THEMES[zone]["modules"]}
    assert {"tower", "walkthrough", "booth", "stall", "plaza"} <= kinds, \
        f"{zone} is missing {({'tower','walkthrough','booth','stall','plaza'} - kinds)}"


# ---------------------------------------------------------------- the street network

ZONE_WORLD = {"midway": ("newisle", "out/newisle.litematic"),
              "frontier": ("islandleft", "out/islandleft.litematic"),
              "hollow": ("islandright", "out/islandright.litematic")}


def _planned(zone):
    isl, world = ZONE_WORLD[zone]
    return planner.make(zone, world, name=f"_t_{zone}", theme=zone, island=isl, plane=203)


def _paving(pl):
    from mcbuild.gen.vertical import World
    m = next(x for x in pl.modules if x["kind"] == "paths")
    w = World()
    park.BUILDERS["paths"](w, {**park.PARK, **m["params"], "at": m["at"]}, None)
    y0 = m["at"][1] - 1
    return {(x, z) for (x, y, z) in w.cells if y == y0}


@pytest.mark.parametrize("zone", ZONES)
def test_the_street_network_is_one_connected_walk(zone):
    """A park whose paving is in five pieces is not a park, it is five patios.

    The first version ran an avenue from each EDGE module to the hub, which covers only the half
    of its axis that its gate is on - so a spur from a door on the far side ran out to a
    coordinate with no avenue to land on, and a side zone (one edge module) never got a second
    axis at all. Full-length cross axes make it connected by construction.
    """
    from collections import deque
    ground = _paving(_planned(zone))
    assert ground
    start = next(iter(ground))
    seen, q = {start}, deque([start])
    while q:
        x, z = q.popleft()
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if (x + dx, z + dz) in ground and (x + dx, z + dz) not in seen:
                seen.add((x + dx, z + dz))
                q.append((x + dx, z + dz))
    assert len(seen) == len(ground), f"{zone}: paving is in {len(ground) - len(seen)} stray cells"


@pytest.mark.parametrize("zone", ZONES)
def test_every_door_is_on_the_street(zone):
    """A path that does not reach the doors is decoration. An EDGE module is joined on its INSIDE
    face - a gate faces out of the park by definition, so its front approach is a cell beyond the
    plot boundary that no avenue may legally reach."""
    pl = _planned(zone)
    ground = _paving(pl)
    for m in pl.modules:
        if m["kind"] in ("paths", "plaza"):
            continue
        pt = planner._inside_of(m) if m.get("edge") else planner._front_of(m)
        assert pt in ground, f"{zone}: {m['name']} has no path to its door at {pt}"


@pytest.mark.parametrize("zone", ZONES)
def test_the_paving_stays_inside_the_plot(zone):
    from mcbuild import islands
    pl = _planned(zone)
    plot = islands.plot_of(ZONE_WORLD[zone][0])
    outside = [(x, z) for (x, z) in _paving(pl) if not plot.contains(x, z)]
    assert not outside, f"{zone}: {len(outside)} paving cells off the plot, e.g. {outside[:3]}"


def test_paths_refuses_to_draw_a_network_nobody_computed():
    """The planner owns the routes because it is the only thing that knows where the modules
    ended up. Asked to draw with none, this RAISES rather than emitting an empty design."""
    with pytest.raises(ValueError):
        park.build({**park.PARK, "at": [0, 64, 0], "kind": "paths", "land": "midway"})
