"""The Mine Ridge, against the one thing it must never do: touch the ride it exists to support.

Everything else here is a shape, and a shape is judged by looking. What cannot be judged by
looking is whether a mountain wrapping a 31,000-block coaster has taken a cell of it - two designs
contending for one cell is a work problem you discover with a pickaxe in your hand - and whether
the gallery bored through its foot has rock over it or is a trench with two walls, which renders
as a tunnel from the one bearing that looks down it.
"""
from __future__ import annotations

import os

import numpy as np
import pytest
import yaml

from mcbuild import blocks, palette
from mcbuild.gen import mineridge

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(ROOT, "configs", "pf_mine_ridge.yaml")
RIDE = os.path.join(ROOT, "out", "park_final", "artifacts", "Mine Coaster.litematic")


@pytest.fixture(scope="module")
def cfg():
    with open(CONFIG, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


@pytest.fixture(scope="module")
def built(cfg):
    if not os.path.exists(RIDE):
        pytest.skip("the Mine Coaster artifact is not shipped")
    canvas = mineridge.build(cfg["params"])
    return canvas, canvas.to_model()


@pytest.fixture(scope="module")
def ride(cfg):
    if not os.path.exists(RIDE):
        pytest.skip("the Mine Coaster artifact is not shipped")
    dv, du = cfg["params"]["lot"]
    occ, face, rails = mineridge._ride_columns(cfg["params"], int(dv), int(du))
    return occ, face


@pytest.fixture(scope="module")
def rails(cfg):
    if not os.path.exists(RIDE):
        pytest.skip("the Mine Coaster artifact is not shipped")
    dv, du = cfg["params"]["lot"]
    return mineridge._ride_columns(cfg["params"], int(dv), int(du))[2]


def _tunnel_boxes(cfg):
    return [tuple(int(x) for x in b) for b in (cfg["params"].get("tunnels") or [])]


def _in_tunnel(cfg, v, u) -> bool:
    return any(a <= v <= b and c <= u <= d for a, b, c, d in _tunnel_boxes(cfg))


# --------------------------------------------------------------------------- the palette


def test_every_rock_is_legal_spendable_and_not_expensive():
    """Rule 16: a block can be real, in 1.19 and still be CURRENCY on this server. Dirt in every
    form is money here, and a mountain is exactly the kind of build that would spend a lot of it."""
    for key, name in mineridge.ROCK.items():
        assert blocks.exists(name), f"{key} -> {name} is not a block"
        assert blocks.spendable(name), f"{key} -> {name} is currency on this server"
        assert palette.tier(name) in ("cheap", "ok"), f"{key} -> {name} is {palette.tier(name)}"


def test_the_strata_actually_draw_a_line():
    """**THE VALUE LADDER IS MEASURED ACROSS FAMILIES, NEVER INSIDE ONE**, and the first build of
    this file got it wrong: stone 126, andesite 136, cobblestone 127 and gravel 128 are four
    materials inside ten points of luminance, so a mass built out of them is one grey whatever the
    mix. Each band's dominant material must be a real step from the ones either side of it."""
    def lum(key):
        r, g, b = blocks.color(mineridge.ROCK[key], "side")
        return 0.2126 * r + 0.7152 * g + 0.0722 * b
    dominant = [max(table, key=lambda t: t[1])[0] for table in mineridge._STRATA]
    tones = [lum(k) for k in dominant]
    assert max(tones) - min(tones) >= 30, \
        f"the strata span only {max(tones) - min(tones):.0f} of luminance: {list(zip(dominant, tones))}"


# --------------------------------------------------------------------------- the ride


def test_NOT_ONE_CELL_THE_RIDE_OWNS_IS_TAKEN(built, ride):
    """**THE CONTRACT THIS DESIGN EXISTS UNDER.** The ridge is a mountain wrapped round a ride
    that is already standing; a cell taken from the coaster is a block somebody places, is told
    is wrong, breaks and places again. Refusing them is what makes `overlap 0` a property of the
    construction rather than a number to hope for.

    **AND IT IS A CELL TEST, NOT A COLUMN TEST** - which it was written as first, and that is a
    real distinction rather than pedantry. Outside a tunnel the generator refuses the ride's whole
    COLUMN, because a talus growing up between two trestle legs is a talus that swallows them.
    Inside a tunnel it must fill the column and refuse only the cells the ride actually occupies,
    or the track's own column stays open to the sky and the result is a cutting with two walls.
    Asserted per column, this test forbids the tunnel the design exists to have.
    """
    canvas, _model = built
    occ, _face = ride
    ny = occ.shape[2]
    taken = [(int(v), int(y), int(u))
             for v, u, y in zip(*np.nonzero(occ))
             if y < ny and canvas.solid(int(v), int(y), int(u))]
    assert not taken, f"{len(taken)} cells of the ride were built over, e.g. {taken[:5]}"


def test_the_talus_reaches_the_ride_and_the_crest_does_not(built, ride, cfg):
    """The two halves of the shape, and they pull opposite ways: the apron's whole job is to hug
    the ride's faces, and the crag's is to stand clear of them. Without the stand-off the crest
    grew right up against the track and the first build swallowed the coaster whole."""
    canvas, _model = built
    occ, _face = ride
    footprint = occ.any(axis=2)
    stand = int(cfg["params"]["stand_off"])
    away = mineridge._away(footprint, stand + 2)
    hugging, near_top, far_top = 0, 0, 0
    for v in range(canvas.sx):
        for u in range(canvas.sz):
            top = max((y for y in range(canvas.sy) if canvas.solid(v, y, u)), default=-1)
            if top < 0:
                continue
            if away[v, u] <= 1.0:
                hugging += 1
            if _in_tunnel(cfg, v, u):
                continue           # inside a tunnel the mass is MEANT to close over the ride
            if away[v, u] <= 2.0:
                near_top = max(near_top, top)
            else:
                far_top = max(far_top, top)
    assert hugging > 200, "the talus does not reach the ride's own faces"
    # THE BOUND IS A RATIO AND IT IS MEASURED RIGHT AGAINST THE RIDE. A talus under a forty-course
    # face legitimately reaches the low twenties - that IS the apron doing its job - and the crest
    # ramps up across the whole stand-off, so a bound taken anywhere inside that ramp would fail a
    # correct build. What must be true is that where the track actually is, the mass beside it is
    # apron rather than crag: the tallest thing within two cells is a fraction of the summit.
    assert near_top < 0.62 * far_top, \
        f"the mass beside the ride reaches {near_top} against a crest of {far_top}"


def test_nothing_is_built_on_ground_that_belongs_to_somebody_else(built, cfg):
    """271 columns of this lot carry `PF Front Frontier`'s queue, water tower and ore-cart props.
    A mountain deferring round a 7 x 30 switchback queue is a mountain with a rectangular bite out
    of it, so those boxes are kept out rather than deferred."""
    canvas, _model = built
    for v0, v1, u0, u1 in cfg["params"]["keep_out"]:
        for v in range(int(v0), int(v1) + 1):
            for u in range(int(u0), int(u1) + 1):
                if not (0 <= v < canvas.sx and 0 <= u < canvas.sz):
                    continue
                for y in range(canvas.sy):
                    assert not canvas.solid(v, y, u), f"built at ({v},{y},{u}) inside a keep-out"


def test_THE_RIDE_RUNS_THROUGH_THE_MOUNTAIN(built, cfg, rails):
    """**THE ASSERTION JACK'S OWN EYE MADE FIRST.** The first build held a seven-cell stand-off
    round the whole ride, and the track's easternmost point is V96 while the summit sat at V108-118
    - so the mountain stood BESIDE the coaster. His words: *"the coaster doesnt even go into the
    mountain you built."*

    Two halves, and both have to be true or it is not a tunnel:
      * every rail cell inside a tunnel zone carries ROCK OVER IT - otherwise it is a cutting;
      * and NOTHING SOLID stands in the four courses a cart runs through - otherwise it is a wall.
    The second half is not hypothetical: the timber sets' axis is derived from the track's own run
    and that derivation is wrong at a CORNER, so two posts came down on the rail itself on a build
    that audited clean and rendered as a perfectly good tunnel. It is the adit's cross-cut bug met
    a second time.
    """
    canvas, _model = built
    boxes = _tunnel_boxes(cfg)
    assert boxes, "the ridge declares no tunnel, so the ride goes nowhere near it"
    inside = [(v, y, u) for v, y, u in rails if _in_tunnel(cfg, v, u)]
    assert len(inside) >= 20, f"only {len(inside)} rail cells are inside the mountain"

    blocked = [(v, y + k, u) for v, y, u in inside for k in range(0, 4)
               if canvas.solid(v, y + k, u)]
    assert not blocked, f"{len(blocked)} cells stand in the cart's own lane, e.g. {blocked[:3]}"

    roofed = [c for c in inside if any(canvas.solid(c[0], c[1] + k, c[2]) for k in range(5, 12))]
    assert len(roofed) == len(inside),         f"only {len(roofed)} of {len(inside)} rail cells have rock over them - the rest is a cutting"


def test_the_tunnel_is_lined_and_timbered(built):
    """A bored hole in rock reads as a cave; dressed walls and a cap beam every fourth cell read
    as a MINE. It is the adit's own rule applied to the ride."""
    canvas, _model = built
    lining = canvas.meta["parts"]["lining"]
    assert lining["bore_cells"] > 500, "the bore is too small to be a tunnel"
    assert lining["dressed"] > 200, "the tunnel's walls are raw rock, so it reads as a cave"
    assert lining["sets"] >= 6, "a tunnel with no timber sets in it is a hole"


# --------------------------------------------------------------------------- the adit


def test_the_gallery_is_a_tunnel_and_not_a_trench(built, cfg):
    """**A TUNNEL IS A VOID WITH ROCK ON TOP, AND THE ROCK HAS TO BE PUT THERE FIRST.** Carved out
    of whatever the talus happened to give, a gallery under a thin part of the apron is an open
    slot with two walls - and it renders as a gallery from the one bearing that looks down it,
    which is exactly the class of error this project's own notes say an orthographic view cannot
    show. So the cover is forced into the height field before a single cell is filled, and this
    is the assertion that it stayed forced.
    """
    canvas, _model = built
    plan = mineridge._adit_plan(cfg["params"], canvas.sx, canvas.sz)
    assert plan, "the ridge has no adit"
    bare = []
    for lane in plan["lanes"]:
        for v, u in lane["cells"]:
            roof = sum(1 for y in range(plan["clear"] + 2, canvas.sy) if canvas.solid(v, y, u))
            if roof < 2:
                bare.append((v, u, roof))
    assert len(bare) <= 2, f"{len(bare)} gallery cells have no rock over them, e.g. {bare[:4]}"


def test_the_gallery_is_walkable_end_to_end(built, cfg):
    """A U with a portal at each end, so it is a walk-THROUGH rather than a dead end you turn
    round in - the ruinway's own rule that a way is real when both of its ends are places."""
    canvas, _model = built
    plan = mineridge._adit_plan(cfg["params"], canvas.sx, canvas.sz)
    # **PASSABLE IS NOT EMPTY**, and this project has been bitten by the converse twice. The
    # gallery carries rail down its middle and a lantern every seventh set; both are things a
    # guest walks through, so what is asserted is that nothing SOLID stands in the two courses a
    # body needs - and that there is a floor to stand on, which is the other half of the question.
    passable = {"air", "rail", "lantern", "ochre_froglight", "spruce_fence"}
    for lane in plan["lanes"]:
        for v, u in lane["cells"]:
            for y in (1, 2):
                name = canvas.get_name(v, y, u).split(":")[-1]
                assert name in passable, \
                    f"the gallery is blocked by {name} at ({v},{y},{u})"
            assert canvas.solid(v, 0, u), f"the gallery has no floor at ({v},{u})"


def test_both_portals_are_framed_and_named(built):
    canvas, _model = built
    adit = canvas.meta["parts"]["adit"]
    assert adit["portals"] == 2
    assert adit["portal_signs"] == 2, \
        "a portal sign was refused, which means it was hung on a column with an opening in it"
    assert adit["sets"] >= 10, "a bored hole with no timber sets in it reads as a cave"
    assert adit["ore_face"] > 10, "the chamber has no ore face - there is nothing to have come for"


# --------------------------------------------------------------------------- the mass


def test_gravel_is_only_ever_a_crust(built):
    """Rule 13: a falling block may not be used with air under it. Scree is the top course of a
    column that is solid to the ground, and never a face."""
    canvas, _model = built
    for v in range(canvas.sx):
        for u in range(canvas.sz):
            for y in range(canvas.sy):
                if canvas.get_name(v, y, u).split(":")[-1] != "gravel":
                    continue
                assert y == 0 or canvas.solid(v, y - 1, u), \
                    f"gravel at ({v},{y},{u}) has air under it"


def test_the_crag_is_the_tallest_thing_in_the_land(built):
    """The Frontier measured 3.8% of its columns over twenty courses with exactly two things
    breaking twenty-five - the Vantage Lookout at 44 and the ride at 42. A mountain that does not
    clear both of them is a hill nobody notices."""
    canvas, _model = built
    top = max((y for v in range(canvas.sx) for u in range(canvas.sz)
               for y in range(canvas.sy) if canvas.solid(v, y, u)), default=0)
    assert top >= 45, f"the crag tops out at {top}, under the ride and the lookout"


def test_nothing_is_built_outside_the_lot(built):
    canvas, _model = built
    assert canvas.meta["refused"] == 0
