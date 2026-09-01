"""The theme park's contracts.

Each of these pins something that shipped WRONG once, here or in a design this one borrows from,
and every one of them was invisible in a render at the time. The point of the file is that the
next person with a good idea about a gatehouse cannot quietly undo them.
"""
from collections import deque

import numpy as np
import pytest

from mcbuild import blocks, palette
from mcbuild.gen import park
from mcbuild.gen.vertical import World

KINDS = sorted(park.BUILDERS)
LANDS = sorted(park.LANDS)
FACINGS = ("east", "north", "west", "south")


# A small cross with one spur - the same shape `planner._add_paths` computes, so `paths` gets
# swept by every generic check here (legality, economy, connectivity, lanterns) rather than being
# quietly exempted from them. The spur lands ON the east-west avenue, which is the property that
# makes the whole network one piece.
_ROUTES = [{"a": [-20, 0], "b": [20, 0], "width": 5, "lamps": True},
           {"a": [0, -20], "b": [0, 20], "width": 5, "lamps": True},
           {"a": [10, 10], "b": [10, 0], "width": 3}]


def _cfg(kind, land="midway", facing="east", **kw):
    cfg = {**park.PARK, "at": [0, 64, 0], "kind": kind, "land": land, "facing": facing,
           "title": kind.upper(), "width": 11, "depth": 9, "lanes": 3, "tiers": 3,
           "height": 6, **kw}
    if kind == "paths":
        cfg.setdefault("routes", _ROUTES)
    return cfg


def _built(kind, land="midway", facing="east", **kw):
    """The raw World, so a test can ask about cells in WORLD coordinates.

    Asserting in world coordinates rather than canvas ones is a rule this repo already paid for:
    the canvas is sized to its own content, so it shifts between two builds with different
    settings and anything comparing them lines up against nothing.
    """
    p = _cfg(kind, land, facing, **kw)
    w = World()
    park.BUILDERS[kind](w, p, None)
    return w, park._Frame(p), park.LANDS[land], p


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
    c = park.build(_cfg(kind, land, facing))
    assert c.to_model().ids.size > 0


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("land", LANDS)
def test_every_block_state_is_legal(kind, land):
    m = park.build(_cfg(kind, land)).to_model()
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
    """A stray cell is a block floating in the air, and this found three of them on the first run
    - all the same fault, a sign hung on a column with an opening in it."""
    w, _f, _pal, _p = _built(kind, land, facing)
    assert _components(w) == [len(w.cells)]


# ------------------------------------------------------------------ the economy

@pytest.mark.parametrize("land", LANDS)
def test_no_land_spends_currency_or_anything_expensive(land):
    """DIRT IS MONEY ON THIS SERVER, and so is every form of it - which is most of why the zoo
    this park replaced could not have been built. `sand` and `gravel` are barred separately by
    the gravity rule; nothing here uses them."""
    for key, val in park.LANDS[land].items():
        for name in (val if isinstance(val, list) else [val]):
            if key == "wood":       # a family name, not a block
                continue
            assert blocks.spendable(name), f"{land}.{key} = {name} is CURRENCY"
            assert blocks.available(name), f"{land}.{key} = {name} is not on the 1.19 allowlist"
            assert palette.tier(name) in ("cheap", "ok"), f"{land}.{key} = {name} is expensive"


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("land", LANDS)
def test_nothing_built_is_currency_or_expensive(kind, land):
    """The palette table being clean is not the same as the BUILD being clean - a generator can
    reach past its own palette, and `_eye_ring` on the flamingo did exactly that twice."""
    m = park.build(_cfg(kind, land)).to_model()
    for n in m.names:
        base = n.split(":")[-1].split("[")[0]
        if base == "air":
            continue
        assert blocks.spendable(base), f"{kind}/{land} places CURRENCY: {base}"
        assert palette.tier(base) != "expensive", f"{kind}/{land} places expensive: {base}"


# ------------------------------------------------------------------ signs

@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("land", LANDS)
@pytest.mark.parametrize("facing", FACINGS)
def test_every_sign_has_a_block_and_a_support_behind_it(kind, land, facing):
    """THE FAULT THIS FILE EXISTS FOR. Three kinds shipped a stray and a fourth shipped a sign
    the game would refuse, all four being a sign hung on the one column that has an OPENING in
    it - a gate's map board behind a lane, a tower's nameplate behind a window slit, a
    walkthrough's EXIT behind its own exit, a stall's fascia sign on an open shopfront.

    Connectivity catches only three of the four: the stall's sign was adjacent to the canopy
    above it and so counted as connected while still having nothing to hang from."""
    w, _f, _pal, _p = _built(kind, land, facing)
    for (x, y, z) in w.signs:
        assert (x, y, z) in w.cells, "sign TEXT with no sign BLOCK is a corrupt region"
        _name, props = w.cells[(x, y, z)]
        fdx, fdz = park._STEP[props["facing"]]
        assert (x - fdx, y, z - fdz) in w.cells, f"{kind}/{land} sign at {(x, y, z)} has no support"


@pytest.mark.parametrize("kind", KINDS)
def test_no_sign_line_is_wider_than_the_sign(kind):
    """Fifteen characters is the line. 'lamps show your roll' is twenty and clips mid-word, and
    the failure only appears in a screenshot after the build is placed."""
    w, _f, _pal, _p = _built(kind, title="A VERY LONG ATTRACTION NAME INDEED")
    for t in w.signs.values():
        for line in list(t["front"]) + list(t["back"]):
            assert len(line) <= park.SIGN_WIDTH, f"{kind}: {line!r} clips"


@pytest.mark.parametrize("kind", ["gate", "arch", "tower", "stall", "booth", "walkthrough"])
def test_every_kind_that_should_be_named_is_named(kind):
    """A sign that the support guard REFUSED is a sign that silently does not exist, which is
    this project's most-repeated failure shape. Every kind with a title must actually carry it."""
    w, _f, _pal, _p = _built(kind, title="NAMEPLATE")
    assert any("NAMEPLATE" in line for t in w.signs.values() for line in t["front"]), \
        f"{kind} dropped its nameplate - the support guard refused it and nothing noticed"


# ------------------------------------------------------------------ the architecture rules

@pytest.mark.parametrize("facing", FACINGS)
def test_the_gate_lanes_are_open_all_the_way_through(facing):
    """A THRESHOLD, NOT A FACADE WITH A HOLE IN IT. Both walls carry the openings, so you pass
    THROUGH the gatehouse. The fence gate at the front is the only thing in a lane."""
    w, f, pal, p = _built("gate", facing=facing)
    meta = park._gate(World(), p, None)          # for the derived geometry
    for i in meta["lane_i"]:
        for h in (1, 2):
            assert f.at(i, 0, h) not in w.cells, "front lane is blocked"
            assert f.at(i, meta["depth"] - 1, h) not in w.cells, "back lane is blocked"
        assert w.name(*f.at(i, 0, 0)) == pal["gate"], "a lane should carry its fence gate"


def test_the_gate_ships_no_unverified_mechanism():
    """The lanes are fence gates on purpose: this kind is architecture, and nothing in it carries
    a signal that would have to be verified.

    NOT because a door cannot be simulated - that reason was recorded here and it was wrong.
    `iron_door` is in `circuit.OUTPUTS`, and `gen/ticketing.py` is a powered barrier whose
    contract is asserted by simulation. What survives is the rule this test really pins: a module
    that ships a mechanism must be able to prove it, so a module that proves nothing ships none."""
    m = park.build(_cfg("gate")).to_model()
    names = {n.split(":")[-1].split("[")[0] for n in m.names}
    for banned in ("iron_door", "redstone_wire", "repeater", "comparator", "observer",
                   "piston", "sticky_piston", "dispenser", "redstone_torch", "redstone_lamp"):
        assert banned not in names, f"the gate placed {banned} with nothing to verify it"


@pytest.mark.parametrize("land", LANDS)
def test_the_crenellations_are_actually_crenellated(land):
    """The void tower built a full ring on the crown course and then alternated merlons OVER it -
    which repaints cells that already exist, alternates perfectly, and changes nothing. The crown
    shipped as a plain drum and nothing about the code looked wrong."""
    w, f, _pal, p = _built("tower", land=land)
    top = max(y for (_x, y, _z) in w.cells)
    crown = {(x, z) for (x, y, z) in w.cells if y == top}
    below = {(x, z) for (x, y, z) in w.cells if y == top - 1}
    assert crown, "no crown course at all"
    assert len(crown) < len(below), \
        "the crown is as full as the course under it - that is a drum, not a parapet"


@pytest.mark.parametrize("land", LANDS)
def test_the_stall_front_is_open(land):
    """A STALL IS A SHOPFRONT, NOT A CELL. The casino's eighteen sealed grey cubes are the
    failure being avoided - you must be able to see in over the counter."""
    w, f, _pal, p = _built("stall", land=land)
    meta = park._stall(World(), p, None)
    open_cells = [i for i in range(1, meta["width"] - 1)
                  if f.at(i, 0, 2) not in w.cells and f.at(i, 0, 3) not in w.cells]
    assert len(open_cells) >= meta["width"] - 2, "the shopfront is walled up"


@pytest.mark.parametrize("land", LANDS)
def test_the_walkthrough_has_a_way_in_and_a_different_way_out(land):
    """One way in at the front, one out at the back, and a switchback between them - never an
    empty box with two doors."""
    w, f, _pal, p = _built("walkthrough", land=land)
    meta = park._walkthrough(World(), p, None)
    front = [i for i in range(meta["width"]) if f.at(i, 0, 1) not in w.cells]
    back = [i for i in range(meta["width"]) if f.at(i, meta["depth"] - 1, 1) not in w.cells]
    assert len(front) == 1 and len(back) == 1, "exactly one way in and one way out"
    assert front != back, "the exit is the entrance - that is a dead end, not a route"
    assert meta["turns"] >= 2, "no baffles: an empty box with two doors is not a walkthrough"


@pytest.mark.parametrize("kind", ["stall", "booth", "walkthrough", "gate"])
def test_no_trim_stair_is_left_stranded(kind):
    """A course shorter than `min_run` gets NOTHING. The deck soffit drew a grid per cell and
    produced 215 runs of which 184 were one or two cells - confetti, in the loudest block
    available - and the run gate has to fire on what is PLACED, not on the candidates."""
    w, _f, pal, _p = _built(kind, min_run=3)
    stairs = {pos for pos, (name, _pr) in w.cells.items() if name == pal["stair"]}
    for (x, y, z) in stairs:
        neighbours = sum(1 for d in ((1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1))
                         if (x + d[0], y, z + d[2]) in stairs)
        assert neighbours >= 1, f"{kind}: a lone stair at {(x, y, z)} is confetti"


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("land", LANDS)
def test_every_lantern_hangs_from_a_full_block(kind, land):
    """Rule 9, and the lowland's own note: a lamp under a SLAB cap reads as 'hanging from air' in
    the audit, because a slab is not a full block."""
    w, _f, pal, _p = _built(kind, land=land)
    for (x, y, z), (name, props) in list(w.cells.items()):
        if name not in ("lantern", "soul_lantern"):
            continue
        if props.get("hanging") != "true":
            continue
        above = w.cells.get((x, y + 1, z))
        assert above, f"{kind}/{land}: a hanging lantern at {(x, y, z)} has nothing over it"
        assert blocks.is_full_cube(above[0]), \
            f"{kind}/{land}: lantern hangs from {above[0]}, which is not a full block"


def test_the_lands_do_not_share_a_palette_family():
    """Three lands that differ by SIGNAGE rather than by palette family are one land three times
    - which is exactly what made the casino read as the same room eighteen times.

    `light` is deliberately NOT compared: two lands are warm and one is cold, which is the
    warm-above / cold-below gradient the lowland stair already carries, and forcing three
    different lights would be inventing a distinction to satisfy a test."""
    fields = ("ground", "wall", "trim", "post", "stair")
    for key in ("ground", "wall", "trim"):
        vals = [park.LANDS[land][key] for land in LANDS]
        assert len(set(vals)) == len(vals), f"two lands share their {key}: {vals}"
    for a in LANDS:
        for b in LANDS:
            if a >= b:
                continue
            shared = {park.LANDS[a][k] for k in fields} & {park.LANDS[b][k] for k in fields}
            assert len(shared) <= 1, f"{a} and {b} share {shared} - they are the same land"


def test_exactly_one_land_is_lit_cold():
    """The gradient is a decision, so it is pinned. Two warm, one cold."""
    cold = [land for land in LANDS if park.LANDS[land]["light"].startswith("soul_")]
    assert len(cold) == 1, f"expected one cold-lit land, got {cold}"


@pytest.mark.parametrize("land", LANDS)
def test_every_land_can_actually_draw_a_line(land):
    """THE VALUE STEP IS MEASURED, NOT ASSUMED. This file's own history records the same wrong
    conclusion three times - *'this economy has almost no value contrast'* - and every one of
    those measurements searched inside ONE material family, where a ladder cannot exist: a family
    is one material shown four ways, and dressing a stone does not change how much light it
    returns. Across families the cheap neutral range is 215 luminance in five stops.

    Below about 15 a trim course stops being a line and becomes the same colour as the wall,
    which is what made `cracked_stone_brick` weathering invisible and the void tower tonally flat.
    """
    def lum(name):
        r, g, b = blocks.color(name, "side")
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    pal = park.LANDS[land]
    step = abs(lum(pal["wall"]) - lum(pal["trim"]))
    assert step >= 15, (f"{land}: wall {pal['wall']} and trim {pal['trim']} are {step:.1f} apart "
                        f"- that carries texture but no tone, and cannot draw a line")


# WOOL IS A WALL, A CANOPY, AN ACCENT - NEVER THE GROUND. `ground` and `path` are what every
# `_pad` and every plaza/terrace/pool floor is built from, and `trim` is the SAME key used for
# wall cornices AND for the plaza's floor grid, the path kerbs, the terrace and pool beds, and
# the planting kerbs (`_plaza`, `_plaza_terrace`, `_plaza_pool`, `_plaza_bed`, `_paths`) - so it
# has to satisfy both jobs at once. `wall`, `accent` and `canopy` are deliberately NOT checked
# here: they are vertical (a building's own wall, a target board, a striped awning) and wool is
# exactly what this economy has for them.
@pytest.mark.parametrize("land", LANDS)
def test_no_land_stands_on_wool(land):
    pal = park.LANDS[land]
    for key in ("ground", "path", "trim"):
        assert "_wool" not in pal[key], (
            f"{land}.{key} is {pal[key]!r} - wool doing a floor's job")


def test_an_unknown_kind_or_land_raises_rather_than_defaulting():
    """An unmatched name RAISES rather than quietly falling back to the only entry in the
    catalogue - the planner's own rule, for the same reason."""
    with pytest.raises(ValueError):
        park.build(_cfg("carousel"))


# ------------------------------------------------------------------ the plaza's landscaping
#
# The generic KINDS-parametrized tests above use `_cfg`'s tiny 11x9 default, which is too small
# for any of the set-pieces below to place at all (the grid needs a 9-block margin on every side
# just to try). These build the plaza at its REAL size - the one every land actually ships,
# `width: 80, depth: 80` in `planner.THEMES` - so the landscaping is exercised at all.

_PLANTED = {"azalea", "flowering_azalea", "fern", "short_grass", "moss_carpet"}
_PARK_SOIL = {"moss_block"}


def _big_plaza(land="midway", facing="east", **kw):
    p = {**park.PARK, "at": [0, 64, 0], "kind": "plaza", "land": land, "facing": facing,
         "width": 80, "depth": 80, **kw}
    w = World()
    meta = park.BUILDERS["plaza"](w, p, None)
    return w, park._Frame(p), park.LANDS[land], meta


@pytest.mark.parametrize("land", LANDS)
def test_the_plaza_is_no_longer_a_bare_slab(land):
    """The finding that started this: a rendered midway plaza was one flat grey platform. A real
    plaza at 80x80 must carry a tree, a bed, a sunken court and a pool - not always all four at
    every land/seed, but the grid is generous enough that all four should land somewhere."""
    w, _f, _pal, meta = _big_plaza(land)
    assert meta["terrace"], f"{land}: no sunken court - still a flat slab"
    assert meta["pool"], f"{land}: no pool"
    assert meta["trees"] + meta["beds"] >= 3, f"{land}: only {meta['trees']} trees, " \
        f"{meta['beds']} beds - still mostly bare ground"


@pytest.mark.parametrize("land", LANDS)
def test_the_plaza_is_still_one_connected_piece_at_real_size(land):
    """The generic connectivity test only ever sees the tiny 11x9 default, where none of this
    landscaping fires at all. At 80x80 every set-piece is drawn AFTER the floor loop and must
    still land on it, or a tree or a terrace tread ships as a floating fragment."""
    w, _f, _pal, _meta = _big_plaza(land)
    cells = set(w.cells)
    start = next(iter(cells))
    seen, q = {start}, deque([start])
    while q:
        x, y, z = q.popleft()
        for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            n = (x + d[0], y + d[1], z + d[2])
            if n in cells and n not in seen:
                seen.add(n)
                q.append(n)
    assert len(seen) == len(cells), f"{land}: plaza landscaping is in {len(cells) - len(seen)} " \
        f"stray cells at real size"


@pytest.mark.parametrize("land", LANDS)
def test_every_block_the_landscaping_places_is_legal_spendable_and_cheap(land):
    """The generic economy tests run at the tiny default size too, so the drift, tree and pool
    palette has never actually been checked against the server."""
    w, _f, _pal, _meta = _big_plaza(land)
    for (name, props) in w.cells.values():
        assert blocks.validate(name, props) == [], f"{land}: {name}{props} is not a legal state"
        assert blocks.spendable(name), f"{land}: plaza places CURRENCY: {name}"
        assert blocks.available(name), f"{land}: plaza places {name}, not on the 1.19 allowlist"
        assert palette.tier(name) != "expensive", f"{land}: plaza places expensive: {name}"


@pytest.mark.parametrize("land", LANDS)
def test_the_drifts_are_patches_not_confetti(land):
    """The Thicket's own number, copied rather than re-derived: a drift that fills solid and
    noises only its own boundary reads as a patch; thresholded per cell it was 191 blobs of which
    75% were one or two cells. 26-connectivity, exactly as `tests/test_thicket.py` uses it."""
    w, _f, _pal, meta = _big_plaza(land, width=80, depth=80)
    assert meta["beds"] >= 1, f"{land}: no beds landed at all - nothing to measure"
    pts = {pos for pos, (name, _pr) in w.cells.items() if name in _PLANTED}
    seen, sizes = set(), []
    for start in pts:
        if start in seen:
            continue
        stack, n = [start], 0
        seen.add(start)
        while stack:
            c = stack.pop()
            n += 1
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for dz in (-1, 0, 1):
                        q = (c[0] + dx, c[1] + dy, c[2] + dz)
                        if q in pts and q not in seen:
                            seen.add(q)
                            stack.append(q)
        sizes.append(n)
    assert pts, f"{land}: nothing planted at all"
    big = sum(s for s in sizes if s >= 8)
    assert big / len(pts) > 0.60, (
        f"{land}: only {100*big/len(pts):.0f}% of planted cells live in blobs of 8 or more "
        f"(sizes {sorted(sizes, reverse=True)[:8]}) - that is the deck floor's confetti again")
    assert max(sizes) >= 15, f"{land}: largest drift is {max(sizes)} cells - too small to read"


@pytest.mark.parametrize("land", LANDS)
def test_every_plant_roots_in_moss_and_nowhere_else(land):
    """A PLANT ROOTS IN THE DIRT FAMILY AND NOWHERE ELSE - and moss_block, laid by this same
    module, is the only soil it ever puts down. 173 placement problems came from listing a
    mossy STONE as soil because it looks like ground; this checks the actual neighbour."""
    w, _f, _pal, _meta = _big_plaza(land)
    for (x, y, z), (name, _props) in w.cells.items():
        if name not in (_PLANTED - {"moss_carpet"}):
            continue
        below = w.cells.get((x, y - 1, z))
        assert below and below[0] in _PARK_SOIL, \
            f"{land}: {name} at {(x, y, z)} roots in {below[0] if below else 'air'}"


@pytest.mark.parametrize("land", LANDS)
def test_the_pool_is_bedded_and_cannot_leak(land):
    """MUST BE BOTH BEDDED AND ENCLOSED, or it is not still water in six months. A solid block
    under every water cell (the bed), and every lateral neighbour of a water cell is either more
    water or a solid kerb - never open air, or the source spreads past its own rim."""
    w, _f, _meta_pal, meta = _big_plaza(land)
    assert meta["pool"], f"{land}: no pool landed - nothing to check"
    water = {pos for pos, (name, _pr) in w.cells.items() if name == "water"}
    assert water, f"{land}: pool reported but no water cells found"
    for (x, y, z) in water:
        below = w.cells.get((x, y - 1, z))
        assert below and blocks.is_full_cube(below[0]), \
            f"{land}: water at {(x, y, z)} has no solid bed under it - it will drain"
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nb = (x + dx, y, z + dz)
            if nb in water:
                continue
            nb_v = w.cells.get(nb)
            assert nb_v and blocks.is_full_cube(nb_v[0]), \
                f"{land}: water at {(x, y, z)} is open toward {nb} - it will spread"


@pytest.mark.parametrize("land", LANDS)
def test_nothing_raised_stands_on_the_avenue_cross(land):
    """Both main avenues always cross this module's own centre - `planner._add_paths` sites the
    hub and then runs them through its centre on the cardinal axes. The plaza can compute exactly
    where that is with no plan data at all, so raised landscaping must never stand there, however
    the dice fall on tree/bed placement."""
    w, f, _pal, _meta = _big_plaza(land)
    cx, cd = 40, 40                          # width=depth=80, matching `_plaza`'s own cx, cd
    # The avenue cross is a property of (i, d) local coordinates, not of world (x, z), and the
    # mapping between them depends on facing - so it is rebuilt through the same `_Frame.at` the
    # generator itself uses, rather than re-derived by hand for every facing.
    on_spine_cells = set()
    for i in range(80):
        for d in range(80):
            if abs(i - cx) <= park._AVENUE_HALF or abs(d - cd) <= park._AVENUE_HALF:
                on_spine_cells.add(f.at(i, d, 0)[0::2])          # (x, z), any height
    for (x, y, z), (_name, _props) in w.cells.items():
        if y <= f.y - 1:
            continue
        assert (x, z) not in on_spine_cells, \
            f"{land}: raised plaza cell {(x, y, z)} stands on the avenue cross"


@pytest.mark.parametrize("land", LANDS)
def test_obstacles_are_actually_avoided_when_supplied(land):
    """`params.obstacles` is the hook a future planner wiring uses (see the `_plaza` docstring for
    the one-line change that closes the gap). Prove the mechanism itself works: a synthetic
    obstacle box dropped right over the plaza's whole landscaped half must leave nothing raised
    inside it."""
    f = park._Frame({"at": [0, 64, 0], "facing": "east"})
    x0, _y0, z0 = f.at(0, 0, 0)
    x1, _y1, z1 = f.at(80, 80, 0)
    box = [min(x0, x1) - 2, min(z0, z1) - 2, max(x0, x1) // 2, max(z0, z1) + 2]
    w, _f, _pal, meta = _big_plaza(land, obstacles=[box])
    for (x, y, z), (_name, _props) in w.cells.items():
        if y <= _f.y - 1:
            continue
        bx0, bz0, bx1, bz1 = box
        assert not (bx0 <= x <= bx1 and bz0 <= z <= bz1), \
            f"{land}: raised cell {(x, y, z)} sits inside the supplied obstacle box {box}"
    with pytest.raises(ValueError):
        park.build(_cfg("stall", land="atlantis"))
    with pytest.raises(ValueError):
        park.build({**_cfg("stall"), "at": None})
