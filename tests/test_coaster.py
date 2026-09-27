"""The Mine Coaster, at the scale the ledger locks it to.

`PARK_VISUAL_AND_BUDGET_SPEC.md`'s setpiece ledger gives *Mine Ridge and Coaster* 36,000-44,000
blocks over 111 by 71 of plan, "including terrain, trestles, station shell, tunnels, and support
roots", and one rule that is not a number:

    the coaster is readable as a route through terrain; terrain never becomes a generic
    mountain or hides the ride entirely.

`PARK_FULL_BUILD_SPEC.md`'s F4 card adds the interfaces: a 3-wide queue of 14-24, board and unload
on SEPARATE sides of the station each with an operator reach and a cart-removal path, and rider
headroom, powered-rail coverage and a visible support story on every track cell.

**EVERY ONE OF THOSE IS INVISIBLE IN A RENDER, WHICH IS WHY THEY ARE HERE.** A rail whose `shape`
is wrong draws identically to one that is right - this repo has the scar twice over, once on the
stair convention and once on the item sorter's comparators - and a powered rail with no source is
a brake that looks exactly like a rail. So the geometry is asserted, never eyeballed.

The rides are built HEADLESS (`under` stripped) so these run without a capture: `_coaster` never
reads `ctx`, so the geometry is the shipped geometry.
"""
from __future__ import annotations

import os

import pytest
import yaml

from mcbuild import blocks, palette
from mcbuild.gen import coaster as C
from mcbuild.gen.vertical import World

CFG = os.path.join(os.path.dirname(__file__), "..", "configs", "mine_coaster.yaml")

# THE LEDGER'S OWN NUMBERS, not ours.
#
# **THE BAND IS A FLOOR, NOT A CEILING.** Jack's direction: over budget is fine when the blocks
# are really doing something; underbuilt is the failure. So the lower bound is the assertion and
# the upper one is only a runaway guard - a ridge that doubled again would be a generic mountain,
# which is the spec's own named failure and is caught by the terrain tests below rather than by an
# arithmetic ceiling. The PLAN, by contrast, is a hard constraint: the lot is the lot.
BUDGET_FLOOR = 36_000
RUNAWAY = 90_000
PLAN = (111, 71)                 # V30-140 by U90-160
CREST_BAND = (72, 100)           # B+72 to B+100
QUEUE_CAPACITY = (14, 24)

# **THE DIRT FAMILY IS MONEY ON THIS SERVER.** The ledger's palette line says "dirt/coarse dirt/
# moss" and the dirt half of it is refused: `blocks.spendable` is False for every form of it, and
# a ridge is the one design big enough to spend a fortune of it without anybody noticing.
CURRENCY_FAMILY = ("dirt", "grass_block", "podzol", "mycelium", "mud", "farmland", "dirt_path")


def _params():
    with open(CFG, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    p = {**C.COASTER, **cfg["params"]}
    p["under"] = None            # headless: `_coaster` never reads the capture
    return p


@pytest.fixture(scope="module")
def built():
    p = _params()
    w = World()
    meta = C._coaster(w, p, None)
    return p, w, meta


def _plan_extent(w):
    xs = [c[0] for c in w.cells]
    zs = [c[2] for c in w.cells]
    return max(xs) - min(xs) + 1, max(zs) - min(zs) + 1


# --------------------------------------------------------------------------- scale

def test_the_shipped_ride_clears_the_ledgers_block_floor(built):
    _p, w, meta = built
    n = len(w.cells)
    assert n >= BUDGET_FLOOR, (
        f"the ledger's floor for Mine Ridge and Coaster is {BUDGET_FLOOR:,} blocks and this is "
        f"{n:,}; it shipped at 4,812 once, which was a track on stilts over a paved yard. "
        f"`ridge_scale` is the dial; the ridge alone is {meta['ridge_blocks']:,}.")
    assert n <= RUNAWAY, f"{n:,} blocks - that is no longer a ridge, it is a mountain"


def test_the_plan_footprint_fits_the_lot(built):
    _p, w, _meta = built
    a, b = sorted(_plan_extent(w))
    assert (b, a) <= PLAN, f"plan is {b} x {a}; F4 is {PLAN[0]} x {PLAN[1]}"


def test_the_crest_stands_in_its_own_vertical_band(built):
    """B+72 to B+100 is the F4 card's crest band, and the ride's own floor is B."""
    p, _w, meta = built
    lo, hi = CREST_BAND
    assert lo <= meta["top"] <= hi, f"crest at B+{meta['top']}, band is B+{lo}..B+{hi}"


def test_the_terrain_does_not_hide_the_ride(built):
    """**THE LEDGER'S ONE UNMEASURED RULE, MEASURED.** A route through terrain is a route that
    comes back out of it: the ridge crown must stand UNDER the crest, so the lift and the crest
    ride in the open, and the tunnels must be short enough to be tunnels rather than a hole the
    ride disappears into. The first build had the massif peaking over the lift and rendered as a
    vertical curtain with the whole circuit inside it."""
    _p, _w, meta = built
    assert meta["ridge_top"] < meta["top"], (
        f"the ridge crowns at B+{meta['ridge_top']} and the crest is B+{meta['top']}: the terrain "
        f"is over the ride, which is the one thing the ledger forbids")
    assert meta["tunnels"] * C._TUNNEL_RUN < meta["track"] * 0.34, (
        "more than a third of the circuit is roofed; that is a mountain with a ride in it")


# --------------------------------------------------------------------------- the ridge

def test_the_ride_is_actually_a_route_through_terrain(built):
    """The other half of the same rule: terrain that the track never enters is scenery beside a
    coaster, not a ridge the coaster runs through."""
    _p, _w, meta = built
    assert meta["ridge_blocks"] > 20_000, "there is no ridge here worth the name"
    assert meta["tunnel_mouths"] >= 2, (
        f"{meta['tunnel_mouths']} tunnel mouths; the ledger's form line names them explicitly")
    assert meta["tunnels"] >= 1


def test_the_ridge_spends_no_currency(built):
    """Rule 16. Dirt, grass, podzol, mud and every relative of them are money here, and a terrain
    generator is exactly the thing that spends a shulker of it while auditing clean."""
    _p, w, _meta = built
    spent = {name.split("[")[0] for (name, _props) in w.cells.values()}
    bad = sorted(n for n in spent if not blocks.spendable(n))
    assert not bad, f"currency spent as building material: {bad}"
    named = sorted(n for n in spent for fam in CURRENCY_FAMILY if fam in n)
    assert not named, f"the dirt family is currency on this server: {named}"


def test_nothing_expensive_and_the_mass_is_cheap(built):
    """The material policy: 78-86% cheap, 10-16% ok, and decorative bulk in an expensive block is
    prohibited outright."""
    _p, w, _meta = built
    tiers = {}
    for (name, _props) in w.cells.values():
        tiers[palette.tier(name.split("[")[0])] = tiers.get(
            palette.tier(name.split("[")[0]), 0) + 1
    assert tiers.get("expensive", 0) == 0, f"expensive blocks in the mass: {tiers}"
    assert tiers.get("cheap", 0) / float(len(w.cells)) > 0.75, tiers


# --------------------------------------------------------------------------- the rails

def _path(p):
    wps = C._coaster_plan(p)
    full, marks = C._trace(wps)
    pts = full[:-1]
    corners = C._corners(pts, True)
    seam = corners | ({len(full) - 1} if 0 in corners else set())
    hs = C._profile(full, marks, wps, seam)[:-1]
    return pts, hs, corners


def test_every_corner_is_a_plain_rail_and_flat_on_both_sides(built):
    """**A POWERED RAIL CANNOT CURVE**, and a corner that changes height loses its turn: the game
    re-derives the shape as a slope and the line dead-ends. Both are registry facts and both are
    invisible in every render this repo owns, so both are asserted rather than looked at."""
    p, w, _meta = built
    f = C._Frame(p)
    pts, hs, corners = _path(p)
    legal_powered = set(blocks.props("powered_rail")["shape"])
    curves = set(blocks.props("rail")["shape"]) - legal_powered
    assert curves == {"south_east", "south_west", "north_west", "north_east"}, curves
    assert not (curves & legal_powered), (
        "the registry says a powered rail can curve; the whole plan shape rests on it not being "
        "able to, so this is read from `blocks.json` rather than remembered")
    n = len(pts)
    for j in corners:
        i, d = pts[j]
        name, props = w.cells[f.at(i, d, hs[j])]
        assert name == "rail", f"corner {j} at {pts[j]} is {name}, not a plain (iron) rail"
        assert props.get("shape") in {"north_east", "north_west", "south_east", "south_west"}, (
            f"corner {j} carries shape {props.get('shape')!r}, which is not a curve")
        assert hs[(j - 1) % n] == hs[j] == hs[(j + 1) % n], (
            f"corner {j} at {pts[j]} is not flat on both sides: "
            f"{hs[(j - 1) % n]}/{hs[j]}/{hs[(j + 1) % n]} - the game will re-derive the turn as a "
            f"slope and the circuit dead-ends there")


def test_every_powered_rail_carries_a_legal_shape(built):
    p, w, _meta = built
    for (name, props) in w.cells.values():
        if name != "powered_rail":
            continue
        assert props.get("shape") in set(blocks.props("powered_rail")["shape"]), props


def test_no_powered_rail_is_further_from_a_source_than_the_spacing(built):
    """**AN UNPOWERED POWERED_RAIL IS A BRAKE.** Counted between CORNERS, because a plain rail does
    not propagate the chain - a flat spacing leaves a dead rail on the far side of every turn."""
    p, w, _meta = built
    f = C._Frame(p)
    pts, hs, corners = _path(p)
    every = int(p["power_every"])
    for (a, b) in C._runs(len(pts), corners):
        srcs = [j for j in range(a, b)
                if w.cells.get(f.at(pts[j][0], pts[j][1], hs[j] - 1), ("",))[0] == "redstone_block"]
        assert srcs, f"the run {a}..{b} has no redstone_block at all: every cell of it is a brake"
        assert srcs[0] == a and srcs[-1] == b - 1, (
            f"run {a}..{b} is unpowered at one end ({srcs[0]}, {srcs[-1]}); the far cell of a run "
            f"is the one a cart leaves a corner onto")
        for x, y in zip(srcs, srcs[1:]):
            assert y - x <= every, f"run {a}..{b} has a {y - x}-cell gap, spacing is {every}"


def test_every_track_cell_keeps_its_rider(built):
    """Two clear courses over every rail, in the open cuttings and inside the tunnels alike. The
    generator asserts this itself; it is asserted from outside too, because a generator that can
    only be told it is wrong by its own raise is one nobody else's caller ever hears from."""
    p, w, _meta = built
    f = C._Frame(p)
    pts, hs, _corners = _path(p)
    track = [f.at(i, d, hs[j]) for j, (i, d) in enumerate(pts)]
    bad = C._rail_clearance(w, track)
    assert not bad, f"{len(bad)} track cell(s) with something in the rider, e.g. {bad[:3]}"


def test_the_circuit_closes_and_returns_to_its_own_station(built):
    _p, _w, meta = built
    assert meta["corners"] == 6
    assert meta["track"] > 250


# --------------------------------------------------------------------------- one piece

def test_the_whole_ride_is_one_six_connected_piece(built):
    """Diagonal is not connected. A ridge is a mass with holes cut in it and a stair walked down
    its own cut face, and both of those are exactly the operations that leave a stray - 1,340 of
    them in one build, every one a perfectly ordinary block in every render."""
    _p, w, _meta = built
    stray = C._floating(w)
    assert not stray, f"{len(stray)} cell(s) joined to nothing, e.g. {sorted(stray)[:4]}"


# --------------------------------------------------------------------------- the guest interfaces

def test_board_and_unload_are_separate_sides_of_the_station(built):
    """The F4 card asks for it in one line. A queue feeding onto the edge riders are climbing off
    is a crowd that cannot move in either direction, and no amount of signage fixes it."""
    p, w, meta = built
    f = C._Frame(p)
    i0, i1, dt = C._station_run(p)
    mid = (i0 + i1) // 2
    board = [d for d in range(dt + 1, dt + 6) if w.has(*f.at(mid, d, 0))]
    unload = [d for d in range(dt - 5, dt) if w.has(*f.at(mid, d, 0))]
    assert len(board) >= 3, f"no boarding platform behind the track: {board}"
    assert len(unload) >= 3, f"no unload platform in front of the track: {unload}"
    assert meta["board_side"] != meta["unload_side"]
    # ...AND THEY ARE ON OPPOSITE FLANKS OF THE RAIL, not two strips of the same one.
    assert min(board) > dt > max(unload)


def test_each_platform_has_an_operator_within_reach_of_the_track(built):
    p, _w, meta = built
    f = C._Frame(p)
    i0, i1, dt = C._station_run(p)
    stands = [tuple(c) for c in meta["operator_stands"]]
    assert len(stands) == 2, stands
    rail_row = [f.at(i, dt, 0) for i in range(i0, i1 + 1)]
    for s in stands:
        near = min(max(abs(s[0] - r[0]), abs(s[1] - r[1]), abs(s[2] - r[2])) for r in rail_row)
        assert near <= 6, f"operator stand {s} is {near} from the nearest track cell"
    # one on each side of the rail, or it is two operators watching the same platform
    sides = {tuple(sorted((s[0], s[2]))) for s in stands}
    assert len(sides) == 2


def test_there_is_a_cart_removal_path_off_the_unload_side(built):
    _p, _w, meta = built
    assert meta["cart_removal_cells"] >= 12, meta["cart_removal_cells"]


def test_the_queue_is_three_wide_and_holds_a_stated_number_of_people(built):
    """CAPACITY IS ROWS AND A ROW IS THREE CELLS ACROSS, stated in `_queue` and reported in the
    sidecar, because a number with no definition beside it is read differently by the next person.
    """
    _p, _w, meta = built
    lo, hi = QUEUE_CAPACITY
    assert lo <= meta["queue_rows"] <= hi, (
        f"queue holds {meta['queue_rows']}; the F4 card asks for {lo}-{hi}")
    assert meta["queue_cells"] >= meta["queue_rows"] * 3, (
        "the queue is narrower than three cells somewhere, so its rows are not rows")


def test_the_queue_can_actually_be_walked_and_reaches_the_platform(built):
    """**A 3-WIDE QUEUE WITH A POST IN IT IS A 1-WIDE QUEUE.** The head canopy's four posts stood
    on the lane's own cells - a perfectly ordinary spruce log, invisible to the audit, the block
    count and every render, and it halved the width the sidecar claims. So the lane is walked:
    every queue cell keeps two clear courses, and the walk from the far end reaches the boarding
    platform."""
    from mcbuild import walk
    p, w, meta = built
    f = C._Frame(p)
    i0, i1, dt = C._station_run(p)
    plain = {pos: name for pos, (name, _pr) in w.cells.items()}
    blocked = []
    for (i, d) in _queue_cells(p, w, f, meta):
        for h in (1, 2):
            pos = f.at(i, d, h)
            if pos in plain:
                blocked.append((i, d, h, plain[pos]))
    assert not blocked, f"{len(blocked)} queue cell(s) with something standing in them: {blocked[:4]}"
    far = _queue_cells(p, w, f, meta)[-1]
    start = f.at(far[0], far[1], 1)
    reach = walk.reachable(plain, start)
    board = f.at((i0 + i1) // 2, dt + 3, 1)
    assert board in reach, "the queue does not reach the boarding platform"


def _queue_cells(p, w, f, meta):
    """The queue's own floor cells, re-derived from the same rule `_queue` builds them with."""
    i0, i1, dt = C._station_run(p)
    rows = meta["queue_rows"]
    per = (rows + 1) // 2
    base_i = i1 + 3
    out = set()
    for lane in range(2):
        d0 = dt + 1 + lane * 4
        for k in range(per):
            for d in range(d0, d0 + 3):
                out.add((base_i + k, d))
    return sorted(out)


def test_the_queue_is_not_boxed_indoors(built):
    """"covered only where it improves the station silhouette; do not box the entire queue
    indoors" - so the covered share is asserted, not the presence of a roof."""
    _p, _w, meta = built
    covered = meta["queue_covered"] / float(meta["queue_cells"])
    assert 0.05 < covered < 0.6, f"{covered:.0%} of the queue is roofed"


def test_there_is_a_named_stuck_cart_recovery_point(built):
    """"accessible stuck-cart recovery" on an eighty-course lift means a route to the top. A
    recovery point nobody can name is one nobody checks, so it is recorded and its distance to the
    track is measured."""
    p, _w, meta = built
    f = C._Frame(p)
    pts, hs, _c = _path(p)
    at = tuple(meta["recovery_at"])
    assert meta["recovery_blocks"] > 20, "a catwalk with no way down is not a recovery point"
    near = min(max(abs(at[0] - c[0]), abs(at[1] - c[1]), abs(at[2] - c[2]))
               for c in (f.at(i, d, hs[j]) for j, (i, d) in enumerate(pts)))
    assert near <= 5, f"the recovery catwalk is {near} blocks from the nearest track cell"


def test_the_station_is_not_a_sealed_shed(built):
    """**A SECOND PLATFORM MEANT A SECOND WALL, AND THE SHED CAME OUT SEALED.** With end walls
    running the full depth there was no way from the queue onto the boarding platform and no way
    off the unload platform at all - a station with a door in none of its four sides. Nothing in
    the audit, the bill of materials or any render said so; a walk did, on the first run. So the
    walk is the test: from the boarding platform every rail is reachable, and from the unload
    platform you can get out of the building."""
    from mcbuild import walk
    p, w, _meta = built
    f = C._Frame(p)
    i0, i1, dt = C._station_run(p)
    plain = {pos: name for pos, (name, _pr) in w.cells.items()}
    pts, hs, _c = _path(p)
    rails = {f.at(i, d, hs[j]) for j, (i, d) in enumerate(pts)}

    mid = (i0 + i1) // 2
    board = f.at(mid, dt + 3, 0)
    reach = walk.reachable(plain, (board[0], board[1] + 1, board[2]))
    assert len(rails & reach) > len(rails) * 0.9, (
        f"only {len(rails & reach)} of {len(rails)} track cells can be walked to from the "
        f"boarding platform")

    unload = f.at(mid, dt - 3, 0)
    out = walk.reachable(plain, (unload[0], unload[1] + 1, unload[2]))
    # ...onto the apron, which is a course LOWER than the platform: the pad is laid at h=-1, so a
    # guest standing on it has their feet at h=0 and stepping out of the door is a one-block drop.
    far = {f.at(i, dt - 8, 0) for i in range(i0, i1 + 1)}
    assert far & out, "the unload platform has no way out of the station"


def test_the_station_says_which_side_is_which(built):
    _p, w, meta = built
    text = " ".join(" ".join(t["front"]) for t in w.signs.values()).upper()
    for word in ("MINE COASTER", "BOARD", "UNLOAD", "QUEUE", "WORKS"):
        assert word in text, f"{word!r} is not written anywhere: {text}"
    # **A REFUSED SIGN IS SILENT.** `_sign` returns False when it has no block to hang from, and
    # a queue with no sign and a works lane with no sign render exactly like ones that have them.
    # Two of these five were being refused; the count is what caught it.
    assert meta["signs"] == 5, meta["signs"]


# --------------------------------------------------------------------------- it still builds small

@pytest.mark.parametrize("span,top", [(58, 45), (44, 34)])
@pytest.mark.parametrize("land", ["frontier", "midway", "hollow"])
def test_the_square_circuit_every_other_caller_asks_for_still_builds(span, top, land):
    """`span_i` defaults to `span`, so `planner.py` and every config written before the rectangle
    keep the square they had. This is the compatibility half of that claim."""
    c = C.build({"kind": "coaster", "land": land, "at": [0, 100, 0], "facing": "east",
                 "span": span, "top": top})
    assert c.meta["span_i"] == span
    assert c.meta["corners"] == 6
