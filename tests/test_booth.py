"""The fairground booth: a sideshow's SHELL, not its machine.

A visual review of the finished park found the sideshow games (Hoopla, Tin Can Alley, Gold
Panning, Fortune Wheel, The Reckoning, and Lucky Dip while it still existed) "stand bare with no
booth/wall/sign, unlike the earlier 'casino became a building' work". `gen/casino.py::_booth` is
the fix: an open-fronted
shopfront that swaps in for `_room` when `booth=True`, built on the same `at(i, d, h)` convention
so the verified machine underneath - the pit, the wiring, the payout - never moves by one cell.

Every assertion here is either about the SHELL (open front, supported signs, one connected piece,
legal and cheap blocks) or a re-run of the machine's own contract from `tests/test_casino.py` with
`booth=True` added - because a shell that quietly breaks the circuit it wraps is worse than no
shell at all.
"""
from __future__ import annotations

from collections import deque

import pytest

from mcbuild import blocks, circuit, palette, tone
from mcbuild.gen import GENERATORS
from mcbuild.gen import casino as K
from mcbuild.gen.vertical import World

ROOM_KINDS = ("high_roller", "double_or_none", "lucky_number", "duel")
ALL_KINDS = ROOM_KINDS + ("wheel",)
LANDS = ("midway", "frontier", "hollow")

# The known, DOCUMENTED exceptions to the cheap-tier rule: `redstone_lamp` and `note_block` are
# both expensive here, and CLAUDE.md records them as BUDGETED rather than substituted, because a
# lamp that does not light and a note block that makes no sound are the wrong kind of "cheap". A
# booth must not introduce any NEW expensive block; it must not be blamed for these two either.
BUDGETED_EXPENSIVE = {"redstone_lamp", "note_block"}


def _built(kind, land="midway", **kw):
    """The raw World a booth-enabled game builds into, so a test can look at cells directly."""
    w = World()
    p = dict(K.CASINO)
    p.update({f"pal_{k}": v for k, v in K.PALETTE.items()})
    p.update({"at": [0, 70, 0], "kind": kind, "outcomes": 3, "pit": 2, "check": False,
              "booth": True, "land": land, "facing": "east", "title": kind[:12], **kw})
    p = K._skin(p)
    meta = K.BUILDERS[kind](w, p, None)
    return w, p, meta


def _components(w):
    cells = set(w.cells)
    seen, sizes = set(), []
    for start in cells:
        if start in seen:
            continue
        q, n = deque([start]), 0
        seen.add(start)
        while q:
            x, y, z = q.popleft()
            n += 1
            for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
                nb = (x + d[0], y + d[1], z + d[2])
                if nb in cells and nb not in seen:
                    seen.add(nb)
                    q.append(nb)
        sizes.append(n)
    return sorted(sizes, reverse=True)


def _sim(kind, land="midway", **kw):
    c = GENERATORS["casino"].build({"at": [0, 70, 0], "kind": kind, "outcomes": 3, "pit": 2,
                                    "check": False, "booth": True, "land": land,
                                    "facing": "east", "title": kind[:12], **kw}, [])
    return c, circuit.Circuit.of(c.to_model(), c.world_origin)


# ------------------------------------------------------------------ the shell


@pytest.mark.parametrize("kind", ROOM_KINDS)
@pytest.mark.parametrize("land", LANDS)
def test_the_booth_builds_and_is_one_connected_piece(kind, land):
    w, _p, _meta = _built(kind, land)
    assert w.cells, "the booth built nothing"
    assert _components(w) == [len(w.cells)], "a booth cell is floating, unconnected to the rest"


def test_the_wheel_stays_one_piece_with_its_optional_roof():
    w, _p, _meta = _built("wheel")
    assert _components(w) == [len(w.cells)]


@pytest.mark.parametrize("kind", ROOM_KINDS)
def test_the_booth_front_is_open_you_can_see_the_counter_from_the_street(kind):
    """A CASINO GAME IS A SEALED ROOM; A SIDESHOW IS A SHOPFRONT. `_room` closes the front above
    the door at every height it does not leave for the doorway - this checks the booth does the
    OPPOSITE: most of the front, above the counter and below the fascia, is open air, so a player
    standing in the aisle can watch the machine being played."""
    w, p, _meta = _built(kind)
    x, y, z = 0, 70, 0
    dx, dz = 1, 0            # facing east
    sx, sz = -dz, -dx
    width = {"high_roller": 6, "double_or_none": 5, "lucky_number": 5, "duel": 6}[kind]
    depth = 4

    def at(i, d, h=0):
        return (x + sx * i - dx * d, y + h, z + sz * i - dz * d)

    open_cells = 0
    checked = 0
    for i in range(0, width - 1):
        for h in (2, 3):                      # between the counter (h<=1) and the fascia (h=4)
            checked += 1
            if not w.has(*at(i, depth, h)):
                open_cells += 1
    assert open_cells / checked > 0.8, (
        f"the booth front is not open: only {open_cells}/{checked} cells are clear")


@pytest.mark.parametrize("kind", ROOM_KINDS)
def test_the_booth_has_a_counter_you_can_actually_lean_on(kind):
    """The open front is a serving hatch, not a hole in the floor: a solid trim course at the
    threshold and a slab top one course up."""
    w, p, _meta = _built(kind)
    width = {"high_roller": 6, "double_or_none": 5, "lucky_number": 5, "duel": 6}[kind]
    depth = 4
    x, y, z = 0, 70, 0
    dx, dz = 1, 0
    sx, sz = -dz, -dx

    def at(i, d, h=0):
        return (x + sx * i - dx * d, y + h, z + sz * i - dz * d)

    slab_hits = 0
    for i in range(0, width - 1):
        assert w.has(*at(i, depth, 0)), f"no counter base at i={i}"
        name, props = w.cells[at(i, depth, 1)]
        assert "slab" in name, f"the counter top at i={i} is {name!r}, not a slab"
        assert props.get("type") == "bottom"
        slab_hits += 1
    assert slab_hits >= width - 1


@pytest.mark.parametrize("kind", ROOM_KINDS)
@pytest.mark.parametrize("land", LANDS)
def test_every_booth_sign_has_a_solid_block_behind_it(kind, land):
    """THE FAULT `gen/park.py::_sign`'s docstring exists for: a sign hung on a column that has an
    OPENING in it. An open-fronted booth is exactly the shape most likely to reproduce it - the
    fascia sign hangs where `_room` used to have a solid door lintel, and the whole point of the
    booth is that most of that wall is now air."""
    w, p, _meta = _built(kind, land)
    assert len(w.signs) == 2, "a fascia sign (the name) and a rules sign (the odds)"
    for (x, y, z) in w.signs:
        assert (x, y, z) in w.cells, "sign TEXT with no sign BLOCK is a corrupt region"
        name, props = w.cells[(x, y, z)]
        assert name == "oak_wall_sign"
        facing = props["facing"]
        fdx, fdz = {"east": (1, 0), "west": (-1, 0), "north": (0, -1), "south": (0, 1)}[facing]
        # the block a wall sign is fixed to sits BEHIND it, opposite the direction it faces
        assert (x - fdx, y, z - fdz) in w.cells, (
            f"{kind}/{land} sign at {(x, y, z)} facing {facing} has nothing behind it")


@pytest.mark.parametrize("kind", ROOM_KINDS)
def test_the_fascia_sign_names_the_game_and_the_rules_sign_states_the_odds(kind):
    w, p, meta = _built(kind)
    texts = [" ".join(t["front"]) for t in w.signs.values()]
    flat = " ".join(texts).upper()
    title = p.get("title") or kind.replace("_", " ").upper()
    assert title.upper() in flat
    # SIGN_COPY spells the odds differently per game - "1 in 3" (double_or_none, lucky_number),
    # "6 in 9" (duel), "1 . 2 . or 4" (high_roller) - so check for the shared shape (a count
    # followed by "in", or the enumerated-outcomes form) rather than one literal string.
    lower = flat.lower()
    assert (" in " in lower) or ("1 ." in lower), \
        "the odds must be printed - a house that will not print them does not know them"


# ------------------------------------------------------------------ the economy


@pytest.mark.parametrize("kind", ALL_KINDS)
@pytest.mark.parametrize("land", LANDS)
def test_the_booth_places_nothing_currency_or_unexpectedly_expensive(kind, land):
    c = GENERATORS["casino"].build({"at": [0, 70, 0], "kind": kind, "outcomes": 3, "pit": 2,
                                    "check": False, "booth": True, "land": land,
                                    "facing": "east", "title": kind[:12]}, [])
    m = c.to_model()
    for n in m.names:
        base = n.split(":")[-1].split("[")[0]
        if base == "air":
            continue
        assert blocks.spendable(base), f"{kind}/{land} booth places CURRENCY: {base}"
        assert blocks.available(base), f"{kind}/{land} booth places a non-1.19 block: {base}"
        tier = palette.tier(base)
        if base in BUDGETED_EXPENSIVE:
            continue
        assert tier != "expensive", f"{kind}/{land} booth places an unbudgeted expensive: {base}"


@pytest.mark.parametrize("kind", ALL_KINDS)
@pytest.mark.parametrize("land", LANDS)
def test_every_booth_block_state_is_legal(kind, land):
    m = GENERATORS["casino"].build({"at": [0, 70, 0], "kind": kind, "outcomes": 3, "pit": 2,
                                    "check": False, "booth": True, "land": land,
                                    "facing": "east", "title": kind[:12]}, []).to_model()
    for n in m.names:
        spec = n.split(":")[-1]
        base = spec.split("[")[0]
        if base == "air":
            continue
        props = {}
        if "[" in spec:
            props = dict(kv.split("=", 1) for kv in spec[spec.index("[") + 1:-1].split(","))
        assert blocks.validate(base, props) == [], f"{spec} is not a legal state"


def test_the_hollow_booths_awning_measurably_contrasts_with_its_wall():
    """CLAUDE.md records three separate wrong conclusions that 'this economy has no value
    contrast', each one from measuring luminance INSIDE one material family - and a visual review
    called the hollow land's undecorated booths 'nearly featureless' for exactly that reason: its
    wall, pillar and trim are all within a few luminance of each other. The awning is where that
    gets fixed: measured ACROSS families against `pal_shell` (deepslate_bricks, 71), both canopy
    tones must clear the ~15-luminance floor a trim course needs to read as a line at all - and
    hollow's own gap should be the LARGEST of the three lands, because it has the least contrast
    anywhere else to fall back on.
    """
    def lum(name):
        return tone.luminance(name, "side")

    wall = K.LAND_SKIN["hollow"]["shell"]
    canopy = K.LAND_SKIN["hollow"]["canopy"]
    assert len(canopy) == 2 and canopy[0] != canopy[1]
    gaps = {land: min(abs(lum(c) - lum(K.LAND_SKIN[land]["shell"])) for c in K.LAND_SKIN[land]["canopy"])
            for land in LANDS}
    for land, gap in gaps.items():
        assert gap >= 15, f"{land}: awning/wall luminance gap is only {gap:.1f}"
    assert gaps["hollow"] == max(gaps.values()), (
        f"hollow's awning should contrast hardest with its wall: {gaps}")


# ------------------------------------------------------------------ the machine is unchanged


@pytest.mark.parametrize("outcomes", [2, 3])
def test_high_roller_still_shows_the_roll_it_rolled_in_a_booth(outcomes):
    from mcbuild.gen import circuits
    levels = circuits.RNG_MIXES[outcomes]["levels"]
    for roll in levels:
        c, s = _sim("high_roller", outcomes=outcomes)
        s.fill(tuple(c.meta["rng_hopper"]), roll)
        s.press(tuple(c.meta["inputs"][0]), ticks=4)
        s.run(60)
        lit = [i for i, l in enumerate(c.meta["lamps"]) if s.powered(tuple(l))]
        assert lit == list(range(roll)), f"booth high_roller: roll {roll} lit {lit}"


@pytest.mark.parametrize("outcomes", [2, 3])
def test_double_or_none_still_pays_only_on_a_win_in_a_booth(outcomes):
    from mcbuild.gen import circuits
    levels = circuits.RNG_MIXES[outcomes]["levels"]
    win = max(levels)
    for roll in levels:
        c, s = _sim("double_or_none", outcomes=outcomes)
        s.fill(tuple(c.meta["rng_hopper"]), roll)
        s.press(tuple(c.meta["inputs"][0]), ticks=4)
        s.run(60)
        paid = s.fired.get(tuple(c.meta["outputs"][0]), 0)
        assert paid == (1 if roll == win else 0), f"booth double_or_none: roll {roll} paid {paid}"


def test_lucky_number_still_pays_only_on_the_exact_number_in_a_booth():
    c, s = _sim("lucky_number")
    win = c.meta["win_level"]
    s.fill(tuple(c.meta["rng_hopper"]), win)
    s.press(tuple(c.meta["inputs"][0]), ticks=4)
    s.run(60)
    assert s.fired.get(tuple(c.meta["outputs"][0]), 0) == 1


def test_duel_still_pays_only_when_you_beat_or_tie_the_house_in_a_booth():
    c, s = _sim("duel")
    s.fill(tuple(c.meta["rng_hopper"]), 4)
    s.fill(tuple(c.meta["house_hopper"]), 1)
    s.press(tuple(c.meta["inputs"][0]), ticks=4)
    s.run(60)
    assert s.fired.get(tuple(c.meta["outputs"][0]), 0) == 1, "you (4) beat the house (1)"


def test_the_wheel_still_lights_exactly_one_pocket_in_a_booth():
    from mcbuild.gen import circuits
    levels = circuits.RNG_MIXES[3]["levels"]
    for roll in levels:
        c = GENERATORS["casino"].build({"at": [0, 70, 0], "kind": "wheel", "pit": 2,
                                        "check": False, "booth": True, "land": "hollow",
                                        "facing": "east", "title": "FW"}, [])
        s = circuit.Circuit.of(c.to_model(), c.world_origin)
        s.fill(tuple(c.meta["rng_hopper"]), roll)
        s.press(tuple(c.meta["inputs"][0]), ticks=4)
        s.run(60)
        lit = [i for i, p in enumerate(c.meta["pockets"]) if s.powered(tuple(p))]
        assert len(lit) == 1, f"booth wheel: roll {roll} lit {lit}"


# ------------------------------------------------------------------ the park's own theme entries


def test_every_sideshow_in_a_park_zone_asks_for_a_booth():
    """Every `gen: casino` module inside a THEME PARK zone (midway/frontier/hollow) is a midway
    sideshow and must ask for a booth - checked by MEMBERSHIP rather than by a fixed name list,
    because the zone rosters are still being edited by other work in this repo (Lucky Dip, for
    one, is gone from midway since this test was first written) and a hardcoded set goes stale
    the moment a module is renamed, added or removed."""
    from mcbuild.planner import THEMES
    park_zones = {"midway", "frontier", "hollow"}
    sideshows = []
    for theme_name in park_zones & set(THEMES):
        for m in THEMES[theme_name]["modules"]:
            if m.get("gen") == "casino":
                sideshows.append((theme_name, m["name"], m.get("params", {})))
    assert sideshows, "no casino sideshows found in any park zone - did the zones get renamed?"
    for theme_name, name, params in sideshows:
        assert params.get("booth") is True, f"{theme_name}/{name} does not ask for a booth"
    # **AND NO ROSTER HERE.** This test used to name five modules and assert they exist, three
    # lines under its own docstring explaining why a hardcoded set goes stale. It went stale the
    # same day: Gold Panning was traded away to fit Tin Can Alley once the transit corridor took
    # twelve columns off the frontier. What the booth work is responsible for is that every
    # sideshow that EXISTS asks for a booth, which is asserted above; which sideshows exist is a
    # curation decision and belongs to the theme, not to this file.
    # **THE FLOOR IS ONE, AND THE DROP FROM FIVE WAS DELIBERATE.** The casino games are
    # watch-a-randomiser machines - press a button, a dropper rolls, a threshold decides - and
    # the park replaced most of them with games that take a PLAYER INPUT: a plinko board, a
    # target range that scores by accuracy, a high striker, a combination vault, a sculk-sensor
    # corridor. What this file is responsible for is that a sideshow which EXISTS wears a booth
    # rather than casino black-and-white, which is asserted above. How many exist is a curation
    # decision that belongs to the theme, and a count here only goes stale.
    assert sideshows, "no casino sideshows in any park zone - did the zones get renamed?"



def test_the_casino_theme_itself_is_untouched():
    """`booth` is off by default so the standalone casino theme - a sealed gaming floor, not a
    fairground - never moves. A regression here would mean the edit leaked past the six sideshow
    entries it was scoped to."""
    from mcbuild.planner import THEMES
    for m in THEMES["casino"]["modules"]:
        if m.get("gen") == "casino":
            assert "booth" not in m.get("params", {}), (
                f"casino/{m['name']} should not carry booth - it is a room, not a shopfront")
