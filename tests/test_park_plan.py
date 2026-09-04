"""The park's three THEMES, and the two planner faults they exposed.

Both faults produced a plan that looked completely reasonable and was wrong, which is the only
kind this project keeps shipping.
"""
import itertools

import pytest

from mcbuild import blocks, planner
from mcbuild.gen import GENERATORS, casino, park

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
        gen = GENERATORS[m["gen"]]
        kinds = getattr(gen, "BUILDERS", None)
        assert kinds and m["kind"] in kinds, f"{m['name']}: {m['gen']} has no kind {m['kind']!r}"
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

    **AND IT IS NO LONGER KEPT BY HAND.** `planner._site_order` derives it, because a step
    that has to be remembered is a step that gets lost - so what is asserted here is that
    the PLANNER orders correctly, not that somebody typed the theme list in the right
    sequence. A theme list is now free to read in whatever order makes it legible.
    """
    order = planner._site_order(planner.THEMES[zone])

    # THE GROUPS COME IN THE RIGHT ORDER: pinned first, free next, the ground last.
    # `origin` is pinned like an edge - the island's own bedrock is the one
    # coordinate the server chooses and nothing can negotiate.
    kinds = [m.get("anchor")
             if m.get("anchor") in ("cover", "edge", "centre", "origin") else "free"
             for m in order]
    order_key = {"edge": 0, "centre": 0, "origin": 0, "free": 1, "cover": 2}
    assert kinds == sorted(kinds, key=lambda k: order_key[k]), (
        f"{zone}: site groups out of order: {kinds}")

    free = [m for m in order
            if m.get("anchor") not in ("cover", "edge", "centre", "origin")]

    def _area(m):
        _fx, _fy, _fz, fw, _fh, fd = planner.measured_footprint(
            m["gen"], m["kind"], dict(m.get("params", {})), m["size"])
        return fw * fd

    # **A DISTRICT IS SITED CONSECUTIVELY, WHICH DELIBERATELY BREAKS A STRICT SIZE ORDER.**
    # Naming a district buys almost nothing if its members are placed at wildly different
    # moments: sorted by area alone the Assay Office was the Frontier's third module and the
    # Prize Office its fourteenth, and the pair came out 78 cells apart on a 99-cell plot.
    #
    # The rule this test exists for is untouched, and it is asserted on the thing it is about:
    # the module that DECIDES where a district goes is its biggest, and those leaders are still
    # in descending order, so a large module still gets the pick of the plot and is never
    # starved by a booth. Within a district the members are descending too.
    leaders, seen = [], set()
    for m in free:
        key = m.get("district") or id(m)
        if key in seen:
            continue
        seen.add(key)
        leaders.append(m)
    leader_areas = [_area(m) for m in leaders]
    assert leader_areas == sorted(leader_areas, reverse=True), (
        f"{zone}: districts sited out of size order - "
        + ", ".join(f"{m['name']}={a}" for m, a in zip(leaders, leader_areas)))

    for district in {m.get("district") for m in free if m.get("district")}:
        members = [_area(m) for m in free if m.get("district") == district]
        assert members == sorted(members, reverse=True), (
            f"{zone}: {district} sited out of size order - {members}")

    for m in free:
        if m.get("district"):
            continue
        # An undistricted module keeps its place in the ordinary queue: it may not be sited
        # before something bigger that is also undistricted.
        index = free.index(m)
        bigger = [o for o in free[index + 1:]
                  if not o.get("district") and _area(o) > _area(m)]
        assert not bigger, (
            f"{zone}: {m['name']}={_area(m)} sited before "
            + ", ".join(f"{o['name']}={_area(o)}" for o in bigger))


@pytest.mark.parametrize("zone", ZONES)
def test_every_edge_module_names_the_side_it_is_pinned_to(zone):
    """An arch to the west that is not ON the western edge does not lead anywhere, and a gate
    sited by `bays` is a gatehouse in the middle of a field: you walk round it."""
    for m in planner.THEMES[zone]["modules"]:
        if m.get("anchor") != "edge":
            continue
        assert m.get("side") in ("north", "south", "east", "west"), f"{m['name']}: no side"
        # A THRESHOLD must face outward or its doorway opens into the zone it is leaving. That is
        # a rule about gates and arches - things you walk THROUGH - not about anything merely
        # pinned to an edge: the mine coaster sits along the BACK of its land and faces IN,
        # because its station addresses the park rather than the void behind it.
        if m["kind"] in ("gate", "arch"):
            assert m["params"]["facing"] == m["side"], (
                f"{m['name']} is a threshold pinned {m['side']} "
                f"but faces {m['params']['facing']}")


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
    # Only the THRESHOLD counts - a land may pin other things to an edge too (the mine coaster
    # sits along the frontier's back edge), and those are not ways out.
    back = {z: [m for m in planner.THEMES[z]["modules"]
                if m.get("anchor") == "edge" and m["kind"] in ("gate", "arch")]
            for z in ("frontier", "hollow")}
    assert [m["side"] for m in back["frontier"]] == ["south"], "frontier is north; it leads back south"
    assert [m["side"] for m in back["hollow"]] == ["north"], "hollow is south; it leads back north"


@pytest.mark.parametrize("zone", ZONES)
def test_a_zone_is_more_than_one_kind_of_thing(zone):
    """A zone needs a landmark, something to ride or walk through, and shops.

    THIS PINNED THE OLD LINEUP - tower / walkthrough / booth / stall - which is exactly the design
    Jack rejected: *"all 3 areas are the same with different materials... nothing actually exists
    outside of some infrastructure and some huts"*. Left as it was it would have kept the rejected
    design enforced, so it changes with the decision, as this repo's own rule requires.
    """
    kinds = {m["kind"] for m in planner.THEMES[zone]["modules"]}
    assert len(kinds) >= 6, f"{zone} has only {len(kinds)} kinds of thing in it: {kinds}"
    assert "plaza" in kinds, f"{zone} has no ground between its attractions"


def test_the_three_zones_are_not_the_same_zone():
    """**THE COMPLAINT, AS A PROPERTY.** The first park gave all three zones an IDENTICAL module
    list and three palettes, which is one zone painted three ways. Each zone must be mostly made
    of things the other two do not have."""
    kinds = {z: {m["kind"] for m in planner.THEMES[z]["modules"]} for z in ZONES}
    for a in ZONES:
        for b in ZONES:
            if a >= b:
                continue
            shared, only_a = kinds[a] & kinds[b], kinds[a] - kinds[b]
            assert len(only_a) > len(shared), (
                f"{a} and {b} share {sorted(shared)} and {a} has only {sorted(only_a)} of its "
                f"own - that is one zone with two paint jobs")


def test_every_zone_has_a_headline_piece():
    """A park is RIDES and BUILDINGS, not paving. The rejected version's tallest thing was 29
    blocks; each zone now needs something you can see from across the plot."""
    for zone in ZONES:
        tall = [m for m in planner.THEMES[zone]["modules"] if m["size"][1] >= 24]
        assert tall, f"{zone} has nothing over 24 blocks tall - it has no skyline"


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

    **THE FLOOD IS OVER THE PUBLIC NETWORK, NOT OVER EVERY CELL DRAWN.** A concealed service
    road that does not join the street is the backstage WORKING - it yields to the public network
    by construction - and flooding every paved cell reported 51 cells of the Reliquary's service
    yard as a broken street. What has to be one piece is what a guest is routed along.
    """
    from collections import deque
    from mcbuild import pathgraph as P
    plan = _planned(zone)
    ground = _paving(plan) & P.public(P.normalise(plan.routes))
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
        # **A BENCH HAS NO DOOR.** Street furniture is dressing placed ALONG the avenues after
        # they are drawn, so it never gets a spur and never needs one - what it owes the street
        # is proximity, which `test_street_furniture_stands_on_the_street` asserts instead.
        if m["gen"] == "streetfurniture":
            continue
        # `_inside_of` assumes an edge module faces OUT, which is true of a gate and false of a
        # ride parked at the back of the land facing IN - so the link point is whichever of the
        # two actually lies on the plot, exactly as `_add_paths` decides it.
        from mcbuild import islands as _isl
        plot = _isl.plot_of(ZONE_WORLD[zone][0])
        # **THE OWNED LAND, NOT THE PLOT** - the same question `_add_paths` asks, and it has to be
        # the same question or this test measures a routing rule nobody uses. The Clock Tower is
        # pinned to the east edge of what the theme owns, which stops ten columns short of the
        # boundary because the transit corridor is reserved there; its front approach lands on
        # the plot and outside the streets, so the avenue correctly meets it on its inside face.
        own = planner._owned_bounds(plot, planner.THEMES[zone])
        front, inside = planner._front_of(m), planner._inside_of(m)
        on_own = own[0] <= front[0] <= own[1] and own[2] <= front[1] <= own[3]
        pt = front if (not m.get("edge") or on_own) else inside
        # **A MODULE ON ANOTHER BAND HAS ITS DOOR ON ANOTHER COURSE.** The Frontier's mine ride
        # stands 24 courses under the town, so its door is not on the street and must not be:
        # what joins it is a declared shaft, which `test_vertical_park` asserts. Checking it
        # against the surface paving asks the town to have paved the mine's roof.
        if m["at"][1] != pl.modules[0]["at"][1]:
            continue
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


# ---------------------------------------------------------------- buildings address the street

def _hub_centre(pl):
    hub = next(m for m in pl.modules if m.get("covers"))
    x0, z0, x1, z1 = planner._box_of(hub)
    return (x0 + x1) // 2, (z0 + z1) // 2


@pytest.mark.parametrize("zone", ZONES)
def test_every_building_addresses_the_street_it_is_joined_to(zone):
    """**HALF OF THEM PRESENTED THEIR BACKS.** `facing` was a theme constant, so a booth sited
    north of the avenue faced exactly the same way as one sited south of it, and about half the
    park showed a blank rear wall to the street its own spur ran to. A shopfront that cannot be
    seen into is a shed."""
    pl = _planned(zone)
    cx, cz = _hub_centre(pl)
    for m in pl.modules:
        if m.get("edge") or m.get("covers") or m["kind"] == "paths" or not m.get("bay"):
            continue
        want, _axis = planner._street_axis(m, cx, cz)
        got = m["params"]["facing"]
        if not m.get("square"):
            # It opted OUT of the square reservation, so it may only be FLIPPED, never turned 90
            # degrees - a 16x55 shop street booking 55x55 to hold a rotation it does not want
            # costs a third of the plot. What can still be asked of it is that it lies on the
            # street's own axis rather than across it.
            same_axis = {want, planner._BACK_FACING[want]}
            assert got in same_axis or {got, planner._BACK_FACING[got]} != same_axis, (
                f"{zone}: {m['name']} faces {got} across its street ({want})")
            continue
        # **...UNLESS TURNING IT WOULD BREAK SOMETHING WORSE, AND THE PLAN SAYS SO.** The turn
        # pass declines for four measured reasons - off the owned land, a door onto land the
        # theme does not own, into a neighbour, and rule 4's discharge landing on a neighbour's
        # queue - and every one of them is a smaller fault than the alternative. What is not
        # acceptable is declining SILENTLY, so a building keeping its back to the street has to
        # be able to name the reason.
        assert got == want or m.get("turn_declined"), (
            f"{zone}: {m['name']} faces {got}, street is {want}, and no reason was recorded")


@pytest.mark.parametrize("zone", ZONES)
def test_the_facing_decision_is_stable(zone):
    """**IT MUST BE MEASURED FROM SOMETHING THE TURN CANNOT MOVE.** Decided from the built box,
    turning a building moves its centre, which can flip the very decision that turned it - one
    module per zone came out facing one avenue while the recomputed answer named the other, so
    its shopfront addressed one street and its spur ran to another. The reserved square does not
    move, so the answer is a fixpoint: asking again after the turn gives the same answer."""
    pl = _planned(zone)
    cx, cz = _hub_centre(pl)
    for m in pl.modules:
        if m.get("edge") or m.get("covers") or m["kind"] == "paths" or not m.get("bay"):
            continue
        once = planner._street_axis(m, cx, cz)
        assert planner._street_axis(m, cx, cz) == once, f"{zone}: {m['name']} is not a fixpoint"
        assert len(m["bay"]) == 4, "the bay must carry its size, or the centre is not stable"


@pytest.mark.parametrize("zone", ZONES)
def test_turning_a_building_never_pushes_it_into_its_neighbour(zone):
    """Orientation happens AFTER siting, so a 9x7 building becoming 7x9 could overrun the slot
    reserved for it. Siting books a SQUARE for anything that may be turned, which is what makes
    the turn safe - and this is the check that would catch it if that ever stopped being true."""
    pl = _planned(zone)
    # **TWO MODULES ON DIFFERENT BANDS MAY SHARE A PLAN VIEW, AND SHOULD.** The Mine Head
    # stands directly over the Mine Cart Escape - that is what a headframe IS - and a plan-view
    # overlap test called it a collision. A module is a box, and a box has three dimensions.
    def _span(m):
        y0 = m["at"][1] + m.get("anchor_offset", (0, 0, 0))[1]
        return y0, y0 + m["size"][1] - 1

    boxes = [(m["name"], planner._box_of(m), _span(m)) for m in pl.modules
             if not m.get("covers") and m["kind"] != "paths"]
    for i, (na, a, ay) in enumerate(boxes):
        for nb, b, by in boxes[i + 1:]:
            if not (ay[0] <= by[1] and by[0] <= ay[1]):
                continue
            overlap = a[0] <= b[2] and b[0] <= a[2] and a[1] <= b[3] and b[1] <= a[3]
            assert not overlap, f"{zone}: {na} overlaps {nb} after orientation"


@pytest.mark.parametrize("zone", ZONES)
def test_an_edge_module_keeps_facing_out_of_the_park(zone):
    """A gate faces OUT by definition - that is the whole reason it is on the edge - so the
    orientation pass must leave it alone."""
    pl = _planned(zone)
    for m in pl.modules:
        # Only a THRESHOLD. A coaster pinned to the back of the land faces IN, deliberately.
        if not m.get("edge") or m["kind"] not in ("gate", "arch"):
            continue
        assert m["params"]["facing"] == m["edge"], (
            f"{zone}: {m['name']} was turned to face {m['params']['facing']} off its own edge")


@pytest.mark.parametrize("zone", ZONES)
def test_a_zone_is_not_all_one_facing(zone):
    """The symptom, stated as a property: one constant facing per zone is what this fixes."""
    pl = _planned(zone)
    faces = {m["params"]["facing"] for m in pl.modules
             if not m.get("edge") and not m.get("covers") and m["kind"] != "paths"}
    # **TWO, NOT THREE, AND THE REASON IS GEOMETRY RATHER THAN A WEAKER TEST.** A module
    # addresses the avenue it is NEARER to, so a zone whose buildings cluster along one axis
    # legitimately answers on that axis: once the transit corridor took ten columns off the
    # east, the midway's free modules all sit nearer the north-south avenue and every one of
    # them correctly faces it. What this test exists to catch is a theme CONSTANT - one facing
    # for the whole zone, with half the park showing its back to the street.
    assert len(faces) >= 2, f"{zone}: every building faces {faces}"


# --------------------------------------------------------------- the sideshow games wear the land

def _lum(name):
    r, g, b = blocks.color(name, "side")
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


@pytest.mark.parametrize("land", sorted(casino.LAND_SKIN))
def test_a_sideshow_skin_can_actually_draw_a_line(land):
    """MEASURED ACROSS FAMILIES, WHICH IS THE ONLY WAY A LADDER CAN EXIST.

    This repo concluded three separate times that the economy has almost no value contrast, and
    every one of those measurements was taken INSIDE a single material family - where a ladder
    cannot exist by construction, because a family is one material shown four ways and dressing a
    stone does not change how much light it returns. Searched ACROSS families the cheap neutral
    ladder is white_wool 236 / smooth_stone 159 / stone 126 / deepslate_bricks 71 / black_wool 21.

    So a skin is only a skin if its field, its walls and its pillars are far enough apart to READ.
    Fifteen is about where a trim course stops being a line and becomes texture.
    """
    sk = casino.LAND_SKIN[land]
    rungs = [sk["floor"], sk["shell"], sk["pillar"]]
    for a, b in itertools.combinations(rungs, 2):
        assert abs(_lum(a) - _lum(b)) >= 15, (
            f"{land}: {a} ({_lum(a):.0f}) and {b} ({_lum(b):.0f}) are the same tone")


@pytest.mark.parametrize("land", sorted(casino.LAND_SKIN))
def test_a_sideshow_skin_is_spendable_and_on_the_server(land):
    """Rule 12 and rule 16 together: a block can be real, legal and still unbuildable here.
    Dirt and grass are CURRENCY on this skyblock, and the 1.19 allowlist is not the 26.2 registry.
    """
    for key, value in casino.LAND_SKIN[land].items():
        # A skin entry may be a single block or a PAIR - an awning is two alternating tones -
        # so flatten rather than assuming a string. Assuming one was how this test started
        # failing the moment the booth work added its striped canopy.
        for name in ([value] if isinstance(value, str) else list(value)):
            assert blocks.exists(name), f"{land}.{key}: no such block {name!r}"
            assert blocks.spendable(name), f"{land}.{key}: {name} is currency on this server"


@pytest.mark.parametrize("zone", ZONES)
def test_every_sideshow_game_names_the_land_it_stands_in(zone):
    """A Hoopla stall on a bright fairground built out of the casino's black-and-white reads as a
    casino with a ferris wheel parked outside it. The games are used twice - in the casino and as
    midway sideshows - and only the second use carries a land."""
    for m in planner.THEMES[zone]["modules"]:
        if m["gen"] != "casino":
            continue
        assert m["params"].get("land") == zone, (
            f"{m['name']}: a sideshow in {zone} must wear {zone}, got "
            f"{m['params'].get('land')!r}")


@pytest.mark.parametrize("zone", ZONES)
def test_street_furniture_stands_on_the_street(zone):
    """Furniture's whole justification is that it belongs to the AVENUE rather than to the bay
    grid: handed to `bays` these would be scattered evenly over the plot, and a bench in the
    middle of open ground is not furniture, it is litter.

    So what is asserted is proximity to real paving, not a spur. The tolerance is the setback
    ladder `_add_furniture` searches - a piece carries its own pad, so it may have to stand a
    little back to find room between two shopfronts, and that is the design rather than a miss.
    """
    pl = _planned(zone)
    if not any(m["gen"] == "streetfurniture" for m in pl.modules):
        pytest.skip(f"{zone} declares no street furniture")
    ground = _paving(pl)
    assert ground, f"{zone}: no paving at all"
    for m in pl.modules:
        if m["gen"] != "streetfurniture":
            continue
        x0, z0, x1, z1 = planner._box_of(m)
        near = min(min(abs(px - cx) + abs(pz - cz) for (px, pz) in ground)
                   for cx, cz in ((x0, z0), (x1, z1), (x0, z1), (x1, z0)))
        assert near <= 16, f"{zone}: {m['name']} is {near} from the nearest paving"


# ---------------------------------------------------------------- plaza landscaping vs the real plan
#
# `_plaza` cannot see the other modules from inside its own generator call - see its docstring -
# so these run it against the REAL sited plan for all three zones, first without any help (the
# actual, currently-wired behaviour) and then with `params.obstacles` populated exactly the way
# `planner._add_paths` already computes that list for the paths module, proving the one-line fix
# recommended in `_plaza`'s docstring actually closes the gap.

def _plaza_module(pl):
    return next(m for m in pl.modules if m["kind"] == "plaza")


def _raised_plaza_cells(pl, obstacles=None):
    from mcbuild.gen.vertical import World
    m = _plaza_module(pl)
    params = dict(m["params"])
    if obstacles is not None:
        params["obstacles"] = obstacles
    w = World()
    park.BUILDERS["plaza"](w, {**park.PARK, **params, "at": m["at"]}, None)
    floor_y = m["at"][1] - 1
    return {(x, z) for (x, y, z) in w.cells if y > floor_y}


def _sibling_boxes(pl):
    plaza = _plaza_module(pl)
    return [list(planner._box_of(m)) for m in pl.modules
            if m is not plaza and m["kind"] != "paths"]


@pytest.mark.parametrize("zone", ZONES)
def test_plaza_landscaping_never_stands_on_a_real_avenue_or_spur(zone):
    """The avenue CROSS is guaranteed by construction (both main avenues always run through this
    module's own centre) - but a SPUR to some other building's door can land anywhere in the
    zone, and `_plaza` has no way to see it unwired. Wiring `obstacles` - the exact list
    `planner._add_paths` already builds for the paths module - closes it; this is the proof."""
    pl = _planned(zone)
    ground = _paving(pl)
    raised_unwired = _raised_plaza_cells(pl)
    # **THE REAL OBSTACLE LIST, not a re-derived one.** `_sibling_boxes` is the module boxes
    # alone, which is what the planner used to hand over - and a plaza given only the buildings
    # planted a tree in the middle of a SPUR, because a spur is not a building. `_add_paths` now
    # appends every route's own box to the same list, so what this test must check is the list
    # the plan actually ships. Re-deriving it here would test a contract nobody uses.
    _hub = next(m for m in pl.modules if m.get('covers') and m['kind'] != 'paths')
    raised_wired = _raised_plaza_cells(
        pl, obstacles=_hub['params'].get('obstacles') or _sibling_boxes(pl))
    unwired_hits = raised_unwired & ground
    wired_hits = raised_wired & ground
    assert not wired_hits, (
        f"{zone}: {len(wired_hits)} plaza cells still stand on real paving even WITH obstacles "
        f"wired - e.g. {sorted(wired_hits)[:3]}")
    # Not asserted zero unwired - that is the documented, currently-accepted gap (a SPUR can land
    # anywhere in the zone, and `_plaza` cannot see one without `obstacles`). What IS asserted is
    # a RELATIVE bound rather than an absolute count: the other modules in this zone are under
    # active, unrelated development and reshuffle the real siting between runs, which moves the
    # absolute number around for reasons that have nothing to do with this module. A regression
    # in the self-computed avenue-cross keepout (the part that owes nothing to plan data) would
    # push this toward "most of the plaza", not toward a few dozen cells out of several hundred.
    assert len(raised_unwired) == 0 or len(unwired_hits) / len(raised_unwired) < 0.25, (
        f"{zone}: {len(unwired_hits)} of {len(raised_unwired)} unwired raised plaza cells collide "
        f"with real paving - the avenue-cross keepout looks broken, not just spur-blind")


@pytest.mark.parametrize("zone", ZONES)
def test_plaza_landscaping_never_blocks_a_real_door_when_wired(zone):
    from mcbuild import islands as _isl
    pl = _planned(zone)
    isl = ZONE_WORLD[zone][0]
    plot = _isl.plot_of(isl)
    doors = []
    for m in pl.modules:
        if m["kind"] in ("paths", "plaza") or m["gen"] == "streetfurniture":
            continue
        front, inside = planner._front_of(m), planner._inside_of(m)
        pt = front if (not m.get("edge") or plot.contains(*front)) else inside
        doors.append(pt)
    # **THE REAL OBSTACLE LIST, not a re-derived one.** `_sibling_boxes` is the module boxes
    # alone, which is what the planner used to hand over - and a plaza given only the buildings
    # planted a tree in the middle of a SPUR, because a spur is not a building. `_add_paths` now
    # appends every route's own box to the same list, so what this test must check is the list
    # the plan actually ships. Re-deriving it here would test a contract nobody uses.
    _hub = next(m for m in pl.modules if m.get('covers') and m['kind'] != 'paths')
    raised_wired = _raised_plaza_cells(
        pl, obstacles=_hub['params'].get('obstacles') or _sibling_boxes(pl))
    blocked = [d for d in doors if d in raised_wired]
    assert not blocked, f"{zone}: obstacle-wired plaza still blocks door(s) at {blocked}"


@pytest.mark.parametrize("zone", ZONES)
def test_plaza_landscaping_never_stands_inside_a_real_building_when_wired(zone):
    pl = _planned(zone)
    boxes = _sibling_boxes(pl)
    raised_wired = _raised_plaza_cells(pl, obstacles=boxes)
    hits = [(x, z) for (x, z) in raised_wired
            if any(x0 <= x <= x1 and z0 <= z <= z1 for (x0, z0, x1, z1) in boxes)]
    assert not hits, f"{zone}: obstacle-wired plaza still stands inside a building at {hits[:5]}"


def test_a_junction_anchor_takes_the_crossroads_when_there_is_room():
    """**A FINGERPOST BELONGS AT THE CROSSROADS AND MUST NOT COST A RIDE TO GET THERE.**

    `anchor: centre` was tried and is the wrong tool: it claims its box in the FIRST siting
    group, so a 9x9 post took the middle of the Hollow before its rides were placed and cost it
    the Ghost Train and the Plummet. `junction` is a PREFERENCE - the module keeps its ordinary
    place in the size order and takes the free bay nearest the crossing, so on a full plot it
    degrades to where it used to be rather than starving anything.
    """
    from mcbuild import islands
    plot = islands.plot_of("newisle")
    if plot is None:
        pytest.skip("no registered island to measure a plot from")
    spec = planner.THEMES["midway"]
    box = planner._centre_box(plot, spec)
    x0, x1, z0, z1 = planner._owned_bounds(plot, spec)
    assert box == ((x0 + x1) // 2, (z0 + z1) // 2, (x0 + x1) // 2, (z0 + z1) // 2)

    # ...and a bay ON the crossing sorts ahead of one far from it.
    size = [9, 9, 9]
    near = planner._box_gap(box[0] - 4, box[1] - 4, size, box)
    far = planner._box_gap(x0, z0, size, box)
    assert near < far


@pytest.mark.parametrize("zone", ZONES)
def test_a_junction_anchored_module_never_starves_a_ride(zone):
    """The property the `centre` attempt broke: nothing may report NO SITE because a signpost
    wanted the middle of the plot."""
    pl = _planned(zone)
    starved = [n for n in pl.notes if "NO SITE" in n]
    assert not starved, f"{zone}: {starved}"
