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


def _cfg(kind, land="midway", facing="east", **kw):
    return {**park.PARK, "at": [0, 64, 0], "kind": kind, "land": land, "facing": facing,
            "title": kind.upper(), "width": 11, "depth": 9, "lanes": 3, "tiers": 3,
            "height": 6, **kw}


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
    """The lanes are fence gates on purpose. `circuit.py` has no model of a DOOR, so a
    plate-and-iron-door turnstile could not be asserted by simulation - and this repo cut two
    finished casino games rather than ship a machine it could not judge."""
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


def test_an_unknown_kind_or_land_raises_rather_than_defaulting():
    """An unmatched name RAISES rather than quietly falling back to the only entry in the
    catalogue - the planner's own rule, for the same reason."""
    with pytest.raises(ValueError):
        park.build(_cfg("carousel"))
    with pytest.raises(ValueError):
        park.build(_cfg("stall", land="atlantis"))
    with pytest.raises(ValueError):
        park.build({**_cfg("stall"), "at": None})
