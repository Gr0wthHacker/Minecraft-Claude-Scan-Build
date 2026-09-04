"""The park's entrance zone (`civic.py`): legality, connectivity, and the two pieces this pass
made functional - a fountain whose water actually cascades, and a bandstand you can ring."""
from collections import deque

import pytest

from mcbuild import blocks, fluids, palette
from mcbuild.gen import civic
from mcbuild.gen.vertical import World

KINDS = sorted(civic.BUILDERS)
LANDS = sorted(civic.LANDS)
FACINGS = ("east", "north", "west", "south")


def _cfg(kind, land="midway", facing="east", **kw):
    return {**civic.CIVIC, "at": [0, 64, 0], "kind": kind, "land": land, "facing": facing,
            "title": kind.upper(), **kw}


def _built(kind, land="midway", facing="east", **kw):
    p = _cfg(kind, land, facing, **kw)
    w = World()
    meta = civic.BUILDERS[kind](w, p, None)
    return w, civic._Frame(p), civic.LANDS[land], p, meta


def _reachable(cells, seed):
    seen = {seed}
    q = deque([seed])
    while q:
        x, y, z = q.popleft()
        for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            n = (x + dx, y + dy, z + dz)
            if n in cells and n not in seen:
                seen.add(n)
                q.append(n)
    return seen


# ------------------------------------------------------------------ it builds, and it is legal

@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("land", LANDS)
@pytest.mark.parametrize("facing", FACINGS)
def test_every_kind_builds_at_every_land_and_facing(kind, land, facing):
    from mcbuild.gen.civic import build
    c = build(_cfg(kind, land, facing))
    assert c.to_model().ids.size > 0


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("land", LANDS)
def test_every_block_state_is_legal(kind, land):
    from mcbuild.gen.civic import build
    m = build(_cfg(kind, land)).to_model()
    for n in m.names:
        spec = n.split(":")[-1]
        base = spec.split("[")[0]
        if base == "air":
            continue
        props = {}
        if "[" in spec:
            props = dict(kv.split("=", 1) for kv in spec[spec.index("[") + 1:-1].split(","))
        assert blocks.validate(base, props) == [], f"{kind}/{land}: {spec} is not a legal state"


#: EXPENSIVE BLOCKS A KIND IS ALLOWED, WITH THE REASON AND A CEILING. The default is none, and it
#: stays none for every kind but one: the bandstand's playable feature is a second BELL rather than
#: a note block precisely because note blocks are `expensive` tier here.
#:
#: The Cascade is the exception and it is Jack's call - *"yes add note blocks its fine"*. The park
#: holds ZERO note blocks in 273,356, so its five-note chime is the first sound in it, and this is
#: the same posture `configs/island_run.yaml` takes for its thirteen slime blocks: where the
#: expensive material IS the feature, it is declared with its reason and a number rather than
#: smuggled past a check. Five, and the check still catches a sixth.
EXPENSIVE_ALLOWED = {"cascade": {"note_block": 5}}


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("land", LANDS)
def test_nothing_built_is_currency_or_expensive(kind, land):
    """Currency is never allowed, the 1.19 allowlist is never optional, and `expensive` is allowed
    only where `EXPENSIVE_ALLOWED` names the block AND the count stays inside its ceiling."""
    from mcbuild.gen.civic import build
    m = build(_cfg(kind, land)).to_model()
    allowed = EXPENSIVE_ALLOWED.get(kind, {})
    from collections import Counter
    seen = Counter()
    for n in m.names:
        base = n.split(":")[-1].split("[")[0]
        if base == "air":
            continue
        assert blocks.spendable(base), f"{kind}/{land} places CURRENCY: {base}"
        assert blocks.available(base), f"{kind}/{land} places a block off the 1.19 allowlist: {base}"
        if palette.tier(base) == "expensive":
            assert base in allowed, f"{kind}/{land} places expensive: {base}"
            seen[base] += 1
    for base, n in seen.items():
        assert n <= allowed[base],             f"{kind}/{land} places {n}x {base} against a declared allowance of {allowed[base]}"


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("land", LANDS)
@pytest.mark.parametrize("facing", FACINGS)
def test_every_kind_is_one_connected_piece(kind, land, facing):
    w, _f, _pal, _p, _meta = _built(kind, land, facing)
    cells = set(w.cells)
    seed = next(iter(cells))
    assert _reachable(cells, seed) == cells


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("land", LANDS)
@pytest.mark.parametrize("facing", FACINGS)
def test_every_sign_has_a_block_and_a_support_behind_it(kind, land, facing):
    from mcbuild.gen.park import _STEP as WORLD_STEP
    w, _f, _pal, _p, _meta = _built(kind, land, facing)
    for (x, y, z) in w.signs:
        assert (x, y, z) in w.cells, f"{kind}: sign TEXT with no sign BLOCK is a corrupt region"
        _name, props = w.cells[(x, y, z)]
        fdx, fdz = WORLD_STEP[props["facing"]]
        assert (x - fdx, y, z - fdz) in w.cells, f"{kind}: sign at {(x, y, z)} has no support"


@pytest.mark.parametrize("kind", KINDS)
def test_no_sign_line_is_wider_than_the_sign(kind):
    w, _f, _pal, _p, _meta = _built(kind, title="A VERY LONG ATTRACTION NAME INDEED FOR SURE")
    for t in w.signs.values():
        for line in list(t["front"]) + list(t["back"]):
            assert len(line) <= civic.SIGN_WIDTH, f"{kind}: {line!r} clips"


# ------------------------------------------------------------------ the fountain actually flows

def test_the_fountain_notches_are_real_gaps_not_solid_rim():
    """The two cascade notches are left OPEN by the loop - no block at all - because in-game a
    source next to open air spreads there and falls on its own. A design that plugs the gap with
    a block for tidiness would be a fountain that looks identical here and never flows there."""
    w, f, _pal, p, _meta = _built("fountain", radius=8)
    r0 = max(8, int(p["radius"]))
    r1 = max(4, r0 - 3)
    r2 = 2
    c = r0 + 4
    notch2 = f.at(c, c - r1, 4)
    notch3 = f.at(c, c - r2, 6)
    below3 = f.at(c, c - r2, 5)
    assert notch2 not in w.cells
    assert notch3 not in w.cells
    assert below3 not in w.cells, "the column under the upper notch must stay open for a fall"


def test_water_actually_cascades_between_tiers():
    """THE LOG FLUME'S OWN LESSON, applied to a fountain: three basins of nothing but source
    blocks look exactly like a working fountain and never move. `fluids.spread`, seeded from
    ONLY the top basin's own sources, is asked whether the middle basin's own floor - not the top
    basin, not a source the middle basin declared for itself - receives real, non-source,
    non-absent water. If it does, water is physically leaving the top tier and falling, which is
    the property a static render or a block count cannot show.
    """
    w, f, _pal, p, meta = _built("fountain", radius=8)
    assert meta["water"] > 0
    r0 = max(8, int(p["radius"]))
    r2 = 2
    c = r0 + 4

    cells = {pos: name for pos, (name, _props) in w.cells.items()}
    top_sources = [pos for pos, (name, props) in w.cells.items()
                   if name == "water" and props.get("level") == "0" and pos[1] == p["at"][1] + 6]
    assert len(top_sources) > 0, "basin three has no declared source to cascade from"

    levels = fluids.spread(cells, top_sources)

    notch3 = f.at(c, c - r2, 6)
    below3 = f.at(c, c - r2, 5)
    assert notch3 in levels, "basin three's water never reaches its own open notch"
    assert 0 < levels[notch3] < fluids.FALLING, "the notch should be FLOWING water, not a source"
    assert levels.get(below3) == fluids.FALLING, \
        "water dropped through the open column below basin three should be FALLING, not still"

    # and it lands somewhere in basin two that basin two never claimed for itself
    basin2_own_sources = {pos for pos, (name, props) in w.cells.items()
                          if name == "water" and props.get("level") == "0"
                          and pos[1] == p["at"][1] + 4}
    reached_in_basin2 = {pos for pos, lv in levels.items()
                        if pos[1] == p["at"][1] + 4 and pos not in cells}
    assert reached_in_basin2, "basin three's cascade never actually reaches basin two's level"


def test_the_fountain_top_basin_alone_does_not_drain_dry():
    """A cascade that lets the WHOLE fountain drain into the void would be worse than three
    static pools. Basin one - the biggest, bottom pool - keeps its rim solid all the way round,
    so the water this design loses out of its own bottom tier is zero."""
    w, f, _pal, p, meta = _built("fountain", radius=8)
    r0 = max(8, int(p["radius"]))
    c = r0 + 4
    coping = {f.at(c + di, c + dd, 1) for (di, dd) in civic._annulus(r0, civic._disc)}
    assert coping <= set(w.cells), "basin one's outer rim must be fully solid - it is not a spill tier"


# ------------------------------------------------------------------ the bandstand can be played

def test_the_bandstand_has_two_bells_and_no_circuit():
    """A bell rings on a right-click whatever powers it - it needs nothing wired, unlike a note
    block, which this economy prices as `expensive`. Two bells, at two different mounts, is a
    small carillon rather than one single chime."""
    from mcbuild.gen.civic import build
    m = build(_cfg("bandstand", radius=8)).to_model()
    names = [n.split(":")[-1].split("[")[0] for n in m.names]
    bells = sum(int((m.ids == i).sum()) for i, n in enumerate(names) if n == "bell")
    assert bells == 2
    for banned in ("redstone_wire", "repeater", "comparator", "observer", "redstone_torch",
                   "note_block"):
        assert banned not in names, f"the bandstand placed {banned} with nothing to verify it"


@pytest.mark.parametrize("land", LANDS)
@pytest.mark.parametrize("facing", FACINGS)
@pytest.mark.parametrize("plan", ["square", "octagon"])
def test_both_bells_have_real_support(land, facing, plan):
    w, f, _pal, _p, _meta = _built("bandstand", land, facing, radius=8, plan=plan)
    from mcbuild.gen.park import _STEP as WORLD_STEP
    bells = [(pos, props) for pos, (name, props) in w.cells.items() if name == "bell"]
    assert len(bells) == 2
    for pos, props in bells:
        att = props["attachment"]
        if att == "ceiling":
            assert (pos[0], pos[1] + 1, pos[2]) in w.cells
        elif att == "single_wall":
            fdx, fdz = WORLD_STEP[props["facing"]]
            assert (pos[0] - fdx, pos[1], pos[2] - fdz) in w.cells, \
                f"wall-mounted bell at {pos} has nothing behind it"


# ------------------------------------------------------------------ guest services is a real building

def test_guest_services_has_lockers_with_room_to_stand():
    """Rule 10: roughly three blocks of working room around anything you use. `lost property` is
    one of the room's own default sign lines - this makes it a real container rather than only a
    word, and checks the approach in front of it is clear rather than assuming it."""
    w, f, _pal, p, _meta = _built("guestservices", width=15)
    width = max(13, int(p["width"]) | 1)
    barrels = [pos for pos, (name, _props) in w.cells.items() if name == "barrel"]
    assert len(barrels) == 2
    for pos in barrels:
        _name, props = w.cells[pos]
        assert props.get("facing") == "up"
    # the interior floor between the door and the barrels (d=0 is the front wall itself) is
    # clear at head height, which is the actual "room to stand" a visitor needs
    lock_i = (width - 4, width - 3)
    for i in lock_i:
        for d in (1, 2):
            assert f.at(i, d, 1) not in w.cells, \
                f"no clear approach to the locker at column {i} - rule 10 is not honoured"


@pytest.mark.parametrize("width", [13, 17, 21])
def test_guest_services_lockers_never_collide_with_the_hatch(width):
    w, f, _pal, p, _meta = _built("guestservices", width=width)
    cx = width // 2
    hatch = set(range(cx - 2, cx + 3))
    lock_i = {width - 4, width - 3}
    assert not (hatch & lock_i), \
        f"width={width}: the lockers sit inside the counter hatch's own column range"


# ------------------------------------------------------------------ walking into the buildings

# What a player can move through. Everything else placed counts as SOLID, which is the
# conservative direction: a room that is walkable with a lantern treated as a wall really is one.
_PASSABLE = ("_sign",)


def _solid(w, pos):
    v = w.cells.get(pos)
    return bool(v) and not v[0].endswith(_PASSABLE)


def _standable(w, pos):
    x, y, z = pos
    return (_solid(w, (x, y - 1, z)) and not _solid(w, pos) and not _solid(w, (x, y + 1, z)))


def _walk(w, seed):
    """Every standing position reachable from `seed`, one cell at a time, at most a course up or
    down. `_reachable` above floods the BLOCKS and answers "is this one printable piece"; it
    cannot tell a room from a solid box with a doorway drawn on it."""
    seen = {seed}
    q = deque([seed])
    while q:
        x, y, z = q.popleft()
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            for dy in (0, 1, -1):
                n = (x + dx, y + dy, z + dz)
                if n not in seen and _standable(w, n):
                    seen.add(n)
                    q.append(n)
    return seen


@pytest.mark.parametrize("land", LANDS)
@pytest.mark.parametrize("facing", FACINGS)
def test_every_shop_can_be_walked_into_from_its_own_door(land, facing):
    """**A SHOPFRONT IS NOT A SHOP.** The complaint that started this pass - "we dont need a
    bakery" - was about a building whose interior was a counter and a lamp. Each shop is entered
    at the column the generator itself records as its doorway, never one picked because it
    worked, and the reached region is asserted LARGE before any claim about the interior is
    trusted: a flood seeded in open air is trivially connected to nothing.
    """
    w, f, _pal, p, meta = _built("shopstreet", land, facing, shops=2)
    depth = max(6, int(p["shop_depth"]))
    for k, cols in enumerate(meta["doors"]):
        assert cols, f"shop {k} has no doorway at all"
        seed = f.at(cols[0], 0, 0)
        assert _standable(w, seed), f"shop {k}'s own doorway is not standable"
        reached = _walk(w, seed)
        assert len(reached) > 100, f"only {len(reached)} standing cells - too small to trust"
        inside = [f.at(i, d, 0) for i in range(meta["frontage"]) for d in range(1, depth - 2)
                  if f.at(i, d, 0) in reached]
        assert len(inside) >= 12, \
            f"shop {k}: only {len(inside)} cells of floor behind the door can be stood on"


@pytest.mark.parametrize("land", LANDS)
@pytest.mark.parametrize("facing", FACINGS)
def test_every_shop_has_its_trades_own_tool_on_the_counter(land, facing):
    """A trade is a word on a sign until something in the room does it. Every shop names a real
    workstation and every one of those is placed, legal, cheap and 1.19."""
    w, _f, _pal, _p, meta = _built("shopstreet", land, facing, shops=2)
    assert len(meta["tools"]) == 2 and all(meta["tools"])
    placed = {n for n, _props in w.cells.values()}
    for tool in meta["tools"]:
        assert tool in placed, f"{tool} is named as a trade's tool and was never placed"
        assert blocks.available(tool) and blocks.spendable(tool)
        assert palette.tier(tool) != "expensive"


def test_a_two_shop_street_is_two_shops_worth_entering():
    """`_deal` hands out `options[0], options[1], ...` before it shuffles, so on a two-shop
    street the head of the width table IS the street - and it used to be 5 and 6, which is a
    three-cell room. It is also why the trade table's head matters: the shop that was cut by
    name was the one at the top of it."""
    _w, _f, _pal, _p, meta = _built("shopstreet", shops=2)
    assert min(meta["widths"]) >= 9, f"a two-shop terrace of {meta['widths']} is two cupboards"
    assert "BAKERY" not in {t for t, _tag, _tool in civic._TRADES}
    assert meta["stock"] >= 4, "no stock on the floor of either shop"
    assert meta["shelves"] >= 4, "no shelving in either shop"


def test_stock_never_stands_where_you_cannot_walk_past_it():
    """**Rule 10, measured on the build rather than argued from the widths.** Three cells of
    clear, standable floor beside every barrel, checked against the same flood a visitor's feet
    would take - not against a claim in the width table, which cannot know what else the shop
    put on its floor."""
    w, f, _pal, _p, meta = _built("shopstreet", shops=2)
    reached = set()
    for cols in meta["doors"]:
        reached |= _walk(w, f.at(cols[0], 0, 0))
    barrels = [(i, d) for i in range(-2, meta["frontage"] + 2) for d in range(0, meta["depth"])
               if w.cells.get(f.at(i, d, 0), ("", {}))[0] == "barrel"]
    assert len(barrels) == meta["stock"] >= 4, "no stock on the floor of either shop"
    for (i, d) in barrels:
        clear = [k for k in (1, 2, 3) if f.at(i + k, d, 0) in reached]
        assert len(clear) == 3, \
            f"the barrel at {(i, d)} has only {len(clear)} cells to stand in front of it"


def test_a_shop_too_narrow_for_a_barrel_is_given_none():
    """The other half of rule 10, and the half no width in the current table exercises: the guard
    has to still be there for the day somebody deals a five-wide shop again. A five-wide shop is
    a three-cell room, and a barrel down one flank of it is a corridor you cannot turn round in.
    """
    p = _cfg("shopstreet")
    w = World()
    f = civic._Frame(p)
    spec = dict(width=5, storeys=1, roof="flat", jetty=False, awning="none", door="centre",
                windows="pair", field="white_wool", accent="red_wool",
                trade=civic._TRADES[0], shutters=False)
    built = civic._one_shop(w, f, civic.LANDS["midway"], civic._Plaques(True), spec, 0, 8, 3)
    assert built["stock"] == 0, "a five-wide shop was given barrels it has no room for"
    assert built["tool"], "...and it still gets its trade's own tool, which takes no floor"


# ------------------------------------------------------------------ the hall of fame

@pytest.mark.parametrize("land", LANDS)
@pytest.mark.parametrize("facing", FACINGS)
def test_the_hall_of_fame_can_be_walked_into_and_reaches_every_fitting(land, facing):
    """The building this replaced could not do anything a player could use. This one is only
    worth having if a visitor can reach all of it: the podium's top step, the lecterns, and the
    floor in front of the record wall."""
    w, f, _pal, p, meta = _built("hallofame", land, facing)
    width, depth, cx = meta["width"], meta["depth"], meta["width"] // 2
    seed = f.at(meta["door"][0], 0, 0)
    assert _standable(w, seed), "the hall's own doorway is not standable"
    reached = _walk(w, seed)
    assert len(reached) > 150, f"only {len(reached)} standing cells - too small to trust"
    assert f.at(cx, 3, 2) in reached, "the winners' podium cannot be stood on"
    assert f.at(cx, depth - 5, 0) in reached, "there is no standing room at the lecterns"
    assert f.at(cx, depth - 3, 0) in reached, "the record wall cannot be walked up to"


@pytest.mark.parametrize("land", LANDS)
@pytest.mark.parametrize("facing", FACINGS)
def test_the_rail_leaves_exactly_one_bay_open_as_the_door(land, facing):
    """An open front with a rail across every bay is a fence; with none it is a shed with a hole
    in it. The gap is left by the loop, never punched afterwards."""
    w, f, _pal, _p, meta = _built("hallofame", land, facing)
    assert meta["door"], "the colonnade has no opening at all"
    for i in meta["door"]:
        for h in (0, 1, 2):
            assert f.at(i, 0, h) not in w.cells, f"the doorway is blocked at course {h}"
    assert meta["rails"] >= 4, "the rest of the front is not railed, so nothing reads as a door"


@pytest.mark.parametrize("land", LANDS)
def test_the_hall_of_fame_is_made_of_things_a_player_uses(land):
    """Every fitting in it works on a right-click with nothing wired to it - which is the reason
    a bell is here and a note block is not, and the reason this can ship at all: nothing that
    carries a signal leaves this repo unverified."""
    w, _f, _pal, _p, meta = _built("hallofame", land)
    names = [n for n, _props in w.cells.values()]
    assert meta["lecterns"] >= 2 and names.count("lectern") == meta["lecterns"]
    assert names.count("bell") == 1
    assert meta["plaques"] >= 4, "the record wall has fewer than four named records on it"
    assert meta["trophies"] >= 4
    redstone = {"redstone_wire", "repeater", "comparator", "observer", "piston", "dispenser",
                "dropper", "note_block", "redstone_torch", "redstone_block"}
    assert not (redstone & set(names)), "this design carries a signal and nothing verifies it"


def test_the_hall_of_fame_names_itself_and_says_how_it_works():
    w, _f, _pal, _p, meta = _built("hallofame", title="HALL OF FAME")
    text = " ".join(" ".join(list(t["front"]) + list(t["back"])).lower()
                    for t in w.signs.values())
    for want in ("hall of fame", "how it works", "the podium", "ring the bell"):
        assert want in text, f"no sign in the hall says {want!r}"
    assert meta["signs_placed"] == meta["signs"], \
        "a sign was silently refused - `park._sign` places nothing when its wall has a hole in it"


# ------------------------------------------------------------------ the shop street's shutters

def test_shop_shutters_are_open_trapdoors_not_painted_wool():
    """The corpus measurement CLAUDE.md records: outside builders place trapdoors at 1.07 per
    thousand cells against this project's 0.00. `_one_shop`'s shutters were a flat wool square;
    they are open trapdoors now, mounted proud of the wall the way `hollowmanor._facade` already
    does it, and this asserts the vocabulary actually shipped rather than trusting the diff."""
    from mcbuild.gen.civic import build
    for land in LANDS:
        m = build(_cfg("shopstreet", land, shops=8)).to_model()
        names = [n.split(":")[-1].split("[")[0] for n in m.names]
        assert any(n.endswith("_trapdoor") for n in names), f"{land}: no trapdoor shutters shipped"


@pytest.mark.parametrize("land", LANDS)
@pytest.mark.parametrize("facing", FACINGS)
def test_every_trapdoor_shutter_touches_its_wall(land, facing):
    w, f, _pal, _p, _meta = _built("shopstreet", land, facing, shops=8)
    for pos, (name, props) in w.cells.items():
        if not name.endswith("_trapdoor"):
            continue
        # the wall is one step further IN (increasing d) from the shutter, which sits at d=-1
        from mcbuild.gen.park import _STEP as WORLD_STEP
        # the shutter faces OUTWARD (f.facing); its support is the wall one step further in
        wdx, wdz = WORLD_STEP[civic._BACK[props["facing"]]]
        assert (pos[0] + wdx, pos[1], pos[2] + wdz) in w.cells, \
            f"trapdoor shutter at {pos} has no wall behind it"


# ------------------------------------------------------------------ detail vocabulary, measured

_DETAIL_SUFFIXES = ("_stairs", "_slab", "_trapdoor", "_fence", "_fence_gate", "_wall", "_pane")


@pytest.mark.parametrize("kind", KINDS)
def test_detail_vocabulary_is_present(kind):
    """Not a hard floor per kind (the fountain is mostly water and ground, not trim), but every
    kind must place SOME of the vocabulary the corpus says this project under-uses."""
    from mcbuild.gen.civic import build
    m = build(_cfg(kind)).to_model()
    names = {n.split(":")[-1].split("[")[0] for n in m.names}
    assert any(n.endswith(_DETAIL_SUFFIXES) for n in names), f"{kind} has no detail blocks at all"
