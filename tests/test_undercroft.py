"""The deep journeys, walked rather than measured.

PARK_VERTICAL_MASTERPLAN.md sections 6 and 7: the deep route "is optional and meaningful. It
offers a puzzle, a reveal, a reward, and a different return location. It must not simply be a long
dark corridor below surface attractions."

Every property here is the kind a render cannot show. A sealed chamber looks exactly like an open
one from outside; a corridor with a block left in it looks finished; a room nobody can spawn in
and a room nobody has lit are the same picture in daylight. So the journey is WALKED.
"""
from collections import deque

import pytest

from mcbuild import nightlight
from mcbuild.gen import undercroft as U

KINDS = sorted(U.STORIES)


def _built(kind, at=(0, 100, 0), facing="east", **extra):
    return U.build({"kind": kind, "land": "frontier" if kind == "mine" else "hollow",
                    "at": list(at), "facing": facing, **extra})


def _cells(canvas):
    """{(x, y, z): name} in WORLD coordinates - the canvas is stored at its own origin."""
    ox, oy, oz = canvas.world_origin
    # A Canvas is not a Model - its palette lives behind `to_model()`, and reading `names` off it
    # is reading an attribute it has never had.
    model = canvas.to_model()
    names = [n.split(":")[-1].split("[")[0] for n in model.names]
    out = {}
    for y in range(model.ids.shape[0]):
        for z in range(model.ids.shape[1]):
            for x in range(model.ids.shape[2]):
                i = model.ids[y, z, x]
                if i:
                    out[(x + ox, y + oy, z + oz)] = names[i]
    return out


def _air(cells, box):
    """Every cell inside a box that is NOT solid - the space a guest can be in."""
    x0, y0, z0, x1, y1, z1 = box
    return {(x, y, z)
            for x in range(x0, x1 + 1) for y in range(y0, y1 + 1) for z in range(z0, z1 + 1)
            if _passable(cells.get((x, y, z)))}


def _passable(name):
    return name is None or name in nightlight.PASSY


def _walk(cells, start, box):
    """Every cell a guest can reach from `start`, standing in a two-course body.

    Deliberately the simplest model that can answer "is this room joined to that corridor": a
    cell is standable when it and the cell above it are passable and the cell below is not. That
    is the same rule `walk.stands` uses, and it is what makes a doorway a doorway.
    """
    x0, y0, z0, x1, y1, z1 = box

    def ok(p):
        x, y, z = p
        if not (x0 <= x <= x1 and y0 <= y <= y1 and z0 <= z <= z1):
            return False
        return (_passable(cells.get((x, y, z))) and _passable(cells.get((x, y + 1, z)))
                and not _passable(cells.get((x, y - 1, z))))

    seen, queue = {start}, deque([start])
    while queue:
        x, y, z = queue.popleft()
        for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1),
                           (1, 1, 0), (-1, 1, 0), (0, 1, 1), (0, 1, -1),
                           (1, -1, 0), (-1, -1, 0), (0, -1, 1), (0, -1, -1)):
            nxt = (x + dx, y + dy, z + dz)
            if nxt not in seen and ok(nxt):
                seen.add(nxt)
                queue.append(nxt)
    return seen


def _bounds(canvas):
    ox, oy, oz = canvas.world_origin
    h, d, w = canvas.ids.shape
    return (ox, oy, oz, ox + w - 1, oy + h - 1, oz + d - 1)


# ------------------------------------------------------------------ the journey

@pytest.mark.parametrize("kind", KINDS)
def test_every_chamber_is_reachable_from_the_start(kind):
    """**THE ONE CHECK A RENDER CANNOT GIVE.** A sealed chamber looks exactly like an open one
    from outside, and a deep route whose reward room has no doorway is the exact failure the
    masterplan's "must not simply be a long dark corridor" is guarding against - it would be
    worse than a corridor, because it would look like more."""
    canvas = _built(kind)
    cells = _cells(canvas)
    box = _bounds(canvas)
    start = (0, 100, 0)
    reached = _walk(cells, start, box)
    assert len(reached) > 100, f"{kind}: the spine itself is not walkable ({len(reached)} cells)"
    for chamber in canvas.meta["chambers"]:
        cx, cy, cz = chamber["at"]
        near = [(cx + dx, cy, cz + dz)
                for dx in range(-2, 3) for dz in range(-2, 3)]
        assert any(p in reached for p in near), \
            f"{kind}: {chamber['name']} at {chamber['at']} cannot be reached from the entrance"


@pytest.mark.parametrize("kind", KINDS)
def test_the_journey_tells_its_own_story_in_order(kind):
    """A reveal that comes before the work it rewards is not a reveal. The order is the
    masterplan's, and a shuffle would still build and still walk."""
    canvas = _built(kind)
    told = [c["holds"] for c in canvas.meta["chambers"]]
    assert told == [holds for _n, _l, _w, holds in U.STORIES[kind]]
    assert len(set(told)) == len(told), f"{kind} repeats a chamber's job: {told}"


@pytest.mark.parametrize("kind", KINDS)
def test_every_chamber_does_exactly_one_thing(kind):
    """"A puzzle, a reveal, a reward, and a different return location" is four rooms with four
    jobs, not one long room with four kinds of decoration in it."""
    for _name, length, width, _holds in U.STORIES[kind]:
        assert 9 <= length <= 21 and 9 <= width <= 15, "a chamber is a room, not a hall"


@pytest.mark.parametrize("kind", KINDS)
def test_nothing_is_left_standing_in_the_corridor(kind):
    """A block in a walkway is invisible in a plan and stops a guest dead."""
    canvas = _built(kind)
    cells = _cells(canvas)
    x, y, z = 0, 100, 0
    for step in range(canvas.meta["spine_length"]):
        for h in range(2):
            name = cells.get((x + step, y + h, z))
            assert _passable(name), f"{kind}: {name} at {(x + step, y + h, z)} blocks the spine"


@pytest.mark.parametrize("kind", KINDS)
def test_the_water_sits_in_a_basin(kind):
    """A flooded chamber with no bed or an open side pours into the corridor. This project has
    shipped that once already - 199,959 wet cells reaching Y-1908 - and every render, audit and
    bill of materials passed it."""
    from mcbuild import fluids
    canvas = _built(kind)
    cells = _cells(canvas)
    if not any(n == "water" for n in cells.values()):
        pytest.skip(f"{kind} has no water")
    loose = fluids.unenclosed(cells)
    assert not loose, f"{kind}: {len(loose)} water cell(s) with no bed or an open side: {loose[:2]}"


@pytest.mark.parametrize("kind", KINDS)
def test_every_lantern_has_something_to_hang_from_or_stand_on(kind):
    """A lantern needs one or the other, and this project has shipped both mistakes - a lamp
    under a slab cap reading as "hanging from air" and a floating one over a hollow."""
    canvas = _built(kind)
    cells = _cells(canvas)
    lamps = [(p, n) for p, n in cells.items() if "lantern" in n]
    assert lamps, f"{kind} placed no light at all"
    for (x, y, z), _name in lamps:
        assert (x, y + 1, z) in cells or (x, y - 1, z) in cells, \
            f"{kind}: the lantern at {(x, y, z)} hangs from nothing"


@pytest.mark.parametrize("kind", KINDS)
def test_the_two_stories_are_not_the_same_journey(kind):
    """Two land specs, two palettes and two stories - written as one generator precisely so they
    can be compared. If they came out the same, the data would be doing no work."""
    other = "crypt" if kind == "mine" else "mine"
    mine = {h for _n, _l, _w, h in U.STORIES[kind]}
    crypt = {h for _n, _l, _w, h in U.STORIES[other]}
    assert mine != crypt
    assert U.PALETTES[kind]["rock"] != U.PALETTES[other]["rock"]


def test_it_refuses_a_journey_it_cannot_place():
    with pytest.raises(ValueError, match="params.at"):
        U.build({"kind": "mine", "land": "frontier"})
    with pytest.raises(ValueError, match="unknown undercroft kind"):
        U.build({"kind": "sewer", "land": "frontier", "at": [0, 100, 0]})
    with pytest.raises(ValueError, match="cardinal"):
        U.build({"kind": "mine", "land": "frontier", "at": [0, 100, 0], "facing": "up"})
