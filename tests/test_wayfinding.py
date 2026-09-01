"""Wayfinding: signage over the theme park. Every check here mirrors `tests/test_park.py`,
because a sign belongs to the same three lands and the same support-checked-not-assumed rule as
everything else it stands beside - a mismatched or floating sign is invisible in every render.
"""
from collections import deque

import pytest

from mcbuild import blocks, palette, planner
from mcbuild.gen import wayfinding as wf
from mcbuild.gen.park import LANDS as PARK_LANDS, _STEP
from mcbuild.gen.vertical import World

KINDS = sorted(wf.BUILDERS)
LANDS = sorted(PARK_LANDS)
FACINGS = ("east", "north", "west", "south")

# Zone names are always valid destinations regardless of which land a config happens to use for
# its palette - land (the palette) and zone (a destination) are different questions, exactly as
# `park.py` keeps `land` and `title` apart.
_SAFE_DEST = "Midway"


def _cfg(kind, land="midway", facing="east", **kw):
    cfg = {**wf.WAYFINDING, "at": [0, 64, 0], "kind": kind, "land": land, "facing": facing,
           "title": kind.upper()}
    # `cfg` already carries every key from WAYFINDING, `entering`/`name`/`arms` included, all
    # defaulted to None - so `setdefault` never fires. Explicit `or` is what actually supplies a
    # kind's required param when the caller did not.
    if kind == "fingerpost":
        cfg["arms"] = cfg.get("arms") or [
            {"direction": "north", "dest": "Midway", "length": 4},
            {"direction": "south", "dest": "Frontier", "length": 4},
        ]
    elif kind == "marker":
        cfg["name"] = cfg.get("name") or _SAFE_DEST
    elif kind == "archway":
        cfg["entering"] = cfg.get("entering") or _SAFE_DEST
    cfg.update(kw)
    return cfg


def _built(kind, land="midway", facing="east", **kw):
    """The raw World, in WORLD coordinates - `test_park.py`'s own rule: the canvas is sized to
    its own content and shifts between builds, so comparisons belong in world space."""
    p = {**wf.WAYFINDING, **_cfg(kind, land, facing, **kw)}
    w = World()
    meta = wf.BUILDERS[kind](w, p, None)
    return w, p, meta


def _components(w):
    cells = set(w.cells)
    seen, sizes = set(), []
    for start in cells:
        if start in seen:
            continue
        q, seen_here = deque([start]), 0
        seen.add(start)
        while q:
            x, y, z = q.popleft()
            seen_here += 1
            for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
                n = (x + d[0], y + d[1], z + d[2])
                if n in cells and n not in seen:
                    seen.add(n)
                    q.append(n)
        sizes.append(seen_here)
    return sorted(sizes, reverse=True)


# ------------------------------------------------------------------ it builds, and it is legal

@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("land", LANDS)
@pytest.mark.parametrize("facing", FACINGS)
def test_every_kind_builds_at_every_land_and_facing(kind, land, facing):
    c = wf.build(_cfg(kind, land, facing))
    assert c.to_model().ids.size > 0


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("land", LANDS)
def test_every_block_state_is_legal(kind, land):
    m = wf.build(_cfg(kind, land)).to_model()
    for n in m.names:
        spec = n.split(":")[-1]
        base = spec.split("[")[0]
        if base == "air":
            continue
        props = {}
        if "[" in spec:
            props = dict(kv.split("=", 1) for kv in spec[spec.index("[") + 1:-1].split(","))
        assert blocks.validate(base, props) == [], f"{spec} is not a legal state"


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("land", LANDS)
@pytest.mark.parametrize("facing", FACINGS)
def test_every_kind_is_one_connected_piece(kind, land, facing):
    """A stray cell is a block floating in the air - `test_park.py`'s own finding, that a sign
    on a column with an opening in it is invisible in every render."""
    w, _p, _meta = _built(kind, land, facing)
    assert _components(w) == [len(w.cells)]


# ------------------------------------------------------------------ the economy

@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("land", LANDS)
def test_nothing_built_is_currency_or_expensive(kind, land):
    """DIRT AND GRASS ARE CURRENCY, and a generator can reach past its own palette even when the
    palette table itself is clean - `_eye_ring` did exactly that twice on the flamingo."""
    m = wf.build(_cfg(kind, land)).to_model()
    for n in m.names:
        base = n.split(":")[-1].split("[")[0]
        if base == "air":
            continue
        assert blocks.spendable(base), f"{kind}/{land} places CURRENCY: {base}"
        assert blocks.available(base), f"{kind}/{land} places a block off the 1.19 allowlist: {base}"
        assert palette.tier(base) != "expensive", f"{kind}/{land} places expensive: {base}"


# ------------------------------------------------------------------ signs

@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("land", LANDS)
@pytest.mark.parametrize("facing", FACINGS)
def test_every_sign_has_a_block_and_a_support_behind_it(kind, land, facing):
    """THE FAULT `test_park.py` EXISTS FOR, restated here because this module writes its own
    signs with its own local `_sign` (raw world coordinates rather than a single `_Frame`, since
    a fingerpost's arms are not all on one axis) and could reintroduce it independently."""
    w, _p, _meta = _built(kind, land, facing)
    for (x, y, z) in w.signs:
        assert (x, y, z) in w.cells, "sign TEXT with no sign BLOCK is a corrupt region"
        _name, props = w.cells[(x, y, z)]
        fdx, fdz = _STEP[props["facing"]]
        assert (x - fdx, y, z - fdz) in w.cells, f"{kind}/{land} sign at {(x, y, z)} has no support"


@pytest.mark.parametrize("kind", KINDS)
def test_no_sign_line_is_wider_than_the_sign(kind):
    """Fifteen characters is the line - clips mid-word past it, and the failure only shows up in
    a screenshot after the build is placed."""
    w, _p, _meta = _built(kind, title="A VERY LONG SIGN TITLE INDEED TOO")
    for t in w.signs.values():
        for line in list(t["front"]) + list(t["back"]):
            assert len(line) <= wf.SIGN_WIDTH, f"{kind}: {line!r} clips"


@pytest.mark.parametrize("kind", ["mapboard", "noticeboard"])
def test_every_titled_kind_actually_carries_its_title(kind):
    """A sign the support guard REFUSED is a sign that silently does not exist - this project's
    most-repeated failure shape. Every kind with a title must actually build it."""
    w, _p, _meta = _built(kind, title="NAMEPLATE")
    assert any("NAMEPLATE" in line for t in w.signs.values() for line in t["front"]), \
        f"{kind} dropped its title - the support guard refused it and nothing noticed"


def test_the_marker_carries_the_name_it_was_given():
    w, _p, meta = _built("marker", name="Mine Coaster")
    assert meta["signed"]
    assert any("MINE COASTER" in line for t in w.signs.values() for line in t["front"])


def test_the_marker_also_says_WHAT_YOU_DO_THERE():
    """A nameplate reading only "THE VAULT" tells a visitor which building they are looking at
    and nothing about whether it is worth going in - which is half of the verdict the Hollow was
    rejected on. A sign has four lines and the marker was using one of them.

    `does` takes a string or a list, and the four-line limit is enforced by TRUNCATION rather
    than by a raise: a nameplate is worth standing whatever its second line says, and a raise
    here would take the name down with the blurb.
    """
    w, _p, meta = _built("marker", name="Mine Coaster", does=["1 in 3", "win a prize"])
    assert meta["signed"]
    front = [t["front"] for t in w.signs.values()]
    assert any(f[:3] == ["MINE COASTER", "1 in 3", "win a prize"] for f in front), front
    for f in front:
        assert len(f) == 4 and all(len(line) <= wf.SIGN_WIDTH for line in f)

    # a name and a number still leave room for one line, and never for five
    w2, _p2, _m2 = _built("marker", name="Mine Coaster", number=3,
                          does=["ride it", "then ride it again", "and again"])
    for t in w2.signs.values():
        assert len(t["front"]) == 4
        assert t["front"][:3] == ["MINE COASTER", "NO 3", "ride it"]


# -------------------------------------------------------------- the destination roster

def test_known_destinations_covers_every_theme_module_and_every_zone():
    known = wf.known_destinations()
    assert {"MIDWAY", "FRONTIER", "HOLLOW"} <= known
    for zone in ("midway", "frontier", "hollow"):
        for m in planner.THEMES[zone]["modules"]:
            assert m["name"].upper() in known, f"{m['name']} is missing from the roster"


@pytest.mark.parametrize("kind,key", [("marker", "name"), ("archway", "entering")])
def test_a_destination_that_is_not_real_is_refused(kind, key):
    """A fingerpost, marker or archway pointing at something that does not exist is worse than
    none at all - it sends a visitor looking for a building that was renamed or never built, and
    nothing about the placement would look wrong."""
    with pytest.raises(ValueError):
        wf.build(_cfg(kind, **{key: "Nonexistent Ride"}))


def test_a_fingerpost_arm_pointing_at_nothing_real_is_refused():
    with pytest.raises(ValueError):
        wf.build(_cfg("fingerpost", arms=[
            {"direction": "north", "dest": "Nonexistent Ride"},
            {"direction": "south", "dest": "Frontier"},
        ]))


def test_a_real_module_name_is_accepted_as_a_destination():
    """The roster is not just the zone names - a fingerpost may point at any real attraction."""
    c = wf.build(_cfg("fingerpost", arms=[
        {"direction": "east", "dest": "Mine Coaster"},
        {"direction": "west", "dest": "Haunted Manor"},
    ]))
    assert c.to_model().ids.size > 0


def test_a_transit_station_name_is_accepted_as_a_destination():
    """Off the shipped `configs/park_line.yaml`, if one exists - the one place a station is
    actually named. Skipped rather than failed when the config has not been generated, because a
    missing yaml file must never crash a generator's import."""
    stations = wf._station_titles()
    if not stations:
        pytest.skip("no configs/park_line.yaml on disk to read station names from")
    title = sorted(stations)[0]
    c = wf.build(_cfg("marker", name=title))
    assert c.to_model().ids.size > 0


# -------------------------------------------------------------------- the fingerpost's own rules

@pytest.mark.parametrize("facing", FACINGS)
def test_every_arms_direction_matches_its_own_signs_facing(facing):
    """THE ARM AND ITS SIGN MUST AGREE, and it is checked from the design's own recorded meta
    rather than trusted - a placard mounted facing the wrong way sends a visitor the wrong way,
    and nothing about the render would look wrong."""
    _w, _p, meta = _built("fingerpost", facing=facing, arms=[
        {"direction": "north", "dest": "Midway"},
        {"direction": "south", "dest": "Frontier"},
        {"direction": "east", "dest": "Hollow"},
        {"direction": "west", "dest": "Grand Plaza"},
    ])
    assert len(meta["arms"]) == 4
    for arm in meta["arms"]:
        assert arm["placed"], f"arm to {arm['dest']} had nothing to hang its sign from"
        assert arm["direction"] == arm["sign_facing"], (
            f"arm points {arm['direction']} but its sign faces {arm['sign_facing']}")


def test_a_fingerpost_needs_between_two_and_four_arms():
    with pytest.raises(ValueError):
        wf.build(_cfg("fingerpost", arms=[{"direction": "north", "dest": "Midway"}]))
    with pytest.raises(ValueError):
        wf.build(_cfg("fingerpost", arms=[
            {"direction": d, "dest": "Midway"} for d in ("north", "south", "east", "west")
        ] + [{"direction": "north", "dest": "Frontier"}]))


def test_a_fingerpost_cannot_repeat_a_direction():
    with pytest.raises(ValueError):
        wf.build(_cfg("fingerpost", arms=[
            {"direction": "north", "dest": "Midway"},
            {"direction": "north", "dest": "Frontier"},
        ]))


def test_a_fingerpost_carries_a_light_on_top():
    """Not hanging - a lamp on a post stands, it does not hang from air over its own top block."""
    w, _p, meta = _built("fingerpost")
    lights = [(pos, props) for pos, (name, props) in w.cells.items()
              if name in ("lantern", "soul_lantern")]
    assert lights, "no light on the post"
    for (x, y, z), props in lights:
        assert props.get("hanging") == "false"
        assert (x, y - 1, z) in w.cells, "the light has nothing to stand on"


# ------------------------------------------------------------------------- the map board

@pytest.mark.parametrize("zone", ["midway", "frontier", "hollow"])
def test_the_mapboard_highlights_the_zone_it_stands_in(zone):
    w, _p, meta = _built("mapboard", land=zone, zone=zone)
    assert meta["zone"] == zone
    accent = PARK_LANDS[zone]["accent"]
    marked = [pos for pos, (name, _pr) in w.cells.items() if name == accent]
    assert marked, f"no 'you are here' marker for {zone}"


def test_the_mapboard_draws_all_three_lands():
    """A layout with only one colour on it is not a map."""
    w, _p, _meta = _built("mapboard", land="midway", zone="midway")
    names = {name for (name, _pr) in w.cells.values()}
    for land in ("frontier", "midway", "hollow"):
        assert PARK_LANDS[land]["wall"] in names, f"{land}'s own tone never appears on the board"


# ------------------------------------------------------------------------- misc kinds

def test_an_unknown_kind_or_land_raises_rather_than_defaulting():
    with pytest.raises(ValueError):
        wf.build(_cfg("carousel"))
    with pytest.raises(ValueError):
        wf.build({**_cfg("marker"), "land": "no-such-land"})


def test_the_archway_names_what_you_are_entering():
    w, _p, meta = _built("archway", entering="Hollow")
    assert meta["signed"]
    assert any("HOLLOW" in line for t in w.signs.values() for line in t["front"])


def test_the_noticeboard_carries_its_rules_within_the_sign_limit():
    w, _p, meta = _built("noticeboard", rules=["OPEN 9AM TO 9PM", "NO RUNNING PLEASE",
                                                "HAVE A GREAT DAY", "MIND THE GAP EAST"])
    assert meta["signed"] >= 2
    for t in w.signs.values():
        for line in list(t["front"]) + list(t["back"]):
            assert len(line) <= wf.SIGN_WIDTH
