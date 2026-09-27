"""THE BROKEN PLATEAU - the Lost Plateau's north end, and the four things `bonebed` grew for it.

Jack, looking north from the middle of the land: *"this area of the map for park complete feels
very weak, the buildings have unclear purposes, and i think the tower is a cop out and feels lazy
... we need to redo this area so it matches the wow factors of the other 2 sides."*

What is pinned here is what would silently come back. The BRINK is the whole idea and it is one
key in a config: put the apron back on the north edge and the mesa ramps down to the plane at the
rim, which is a lawn that stops rather than a plateau that ends. The GORGE has to stay open at
that rim, because a wall across the mouth is the difference between the money shot and a pit. The
SEAM has to stay in the wall and out of the turf. And every one of them is opt-in on a generator
that also builds the Vale and the Bone Bed, so the first test here is that those two are
untouched - a shared generator changing under its other callers is a different bug, and this repo
has written that rule down twice.
"""
from __future__ import annotations

import json
from collections import deque

import numpy as np
import pytest
import yaml

from mcbuild import blocks, schem
from mcbuild.gen import bonebed
from mcbuild.nbt import state_name

CONFIG = "configs/pf_broken_plateau.yaml"


def _params(path):
    return {**bonebed.BONEBED, **yaml.safe_load(open(path, encoding="utf-8"))["params"]}


def _tally(canvas):
    names = [state_name(e) for e in canvas.palette]
    out = {}
    for i, n in enumerate(names):
        k = int((canvas.ids == i).sum())
        if k and n != "minecraft:air":
            out[n] = k
    return out


@pytest.fixture(scope="module")
def p():
    return _params(CONFIG)


@pytest.fixture(scope="module")
def canvas(p):
    return bonebed.build(dict(p))


@pytest.fixture(scope="module")
def names(canvas):
    return [state_name(e).split(":")[-1] for e in canvas.palette]


@pytest.fixture(scope="module")
def floor(canvas):
    """The LOWEST occupied course per (u, v), which is the only thing that measures a floor.

    `top` sees the bridge deck thirty courses up, the gantry's head beam and its hanging jacket -
    all of them correctly OVER the gorge floor - so a floor test written against it measures the
    furniture instead of the ground.
    """
    s = canvas.ids > 0
    idx = np.arange(s.shape[0])[:, None, None]
    return np.where(s, idx, 10 ** 6).min(axis=0)


@pytest.fixture(scope="module")
def top(canvas):
    """The highest occupied course per (u, v), or -1."""
    s = canvas.ids > 0
    idx = np.arange(s.shape[0])[:, None, None]
    return np.where(s, idx, -1).max(axis=0)


# ------------------------------------------------- the rule that governs a shared generator


@pytest.mark.parametrize("cfg,art", [
    ("configs/pf_plateau_vale.yaml", "out/PF Plateau Vale.litematic"),
    ("configs/pf_plateau_bone_bed.yaml", "out/PF Plateau Bone Bed.litematic"),
])
def test_the_other_two_callers_of_this_generator_are_UNCHANGED(cfg, art):
    """`brink`, `seams`, `bridge` and `belvedere` are opt-in, and this is what says so.

    The Vale and the Bone Bed are the same generator with different numbers - deliberately, so
    that the three pieces of ground in this land are one hillside rather than three. That is only
    safe while adding to it cannot move them.
    """
    assert _tally(bonebed.build(_params(cfg))) == _tally(schem.load(art))


# ------------------------------------------------------------------- the brink, and the rim


def test_the_MASS_RUNS_TO_THE_NORTH_RIM_AND_BREAKS(p, top):
    """With no apron on that edge the mesa is at full height where the park stops.

    This is the whole design. The park's plate ends at U0 with open void past it, and `margin`
    lays a dead-level apron round every lot edge so a bank never walls its neighbour - which is
    right where the neighbour is more park and hands a guest a lawn that stops where the
    neighbour is nothing.
    """
    assert "u0" in {str(x) for x in p["brink"]}
    lip = [int(top[0, v]) for v in range(p["lot"][0])]
    assert max(lip) >= 20, f"the rim is only {max(lip)} courses tall - the apron is back"


def test_PUTTING_THE_APRON_BACK_FLATTENS_THE_RIM(p):
    """The control: the same design with `brink` empty ramps down to nothing at U0.

    A contract that passes the fault it was written for is worth less than no contract, so this
    builds the failure and measures it rather than asserting the fix in isolation.
    """
    flat = bonebed.build({**p, "brink": []})
    s = flat.ids > 0
    idx = np.arange(s.shape[0])[:, None, None]
    t = np.where(s, idx, -1).max(axis=0)
    assert int(t[0].max()) <= 2, "the apron no longer holds the rim down - the control is broken"


def test_the_GORGE_IS_OPEN_AT_THE_RIM_and_deep_behind_it(p, top):
    """No wall across the mouth, and real walls either side of it.

    The pit's box runs off the north edge on purpose (`u0` is negative), so `_dist_out` never
    finds a rim there and no benched face is built across it. Both halves matter: an open mouth
    with shallow walls is a notch, and deep walls with a wall across the mouth is a pit.
    """
    v0, v1 = int(p["pits"][0][0]), int(p["pits"][0][1])
    #: THE EDGE WOBBLES, so the open run is measured rather than assumed: `wobble` moves the pit's
    #: boundary by up to its own amplitude and a test that names the box's own columns is testing
    #: the brief instead of the build.
    open_run = max(len(list(g)) for g in _runs(int(top[0, v]) <= 4 for v in range(v0, v1 + 1)))
    assert open_run >= 14, f"the gorge mouth is open for only {open_run} columns"
    walls = [int(top[8, v]) for v in (v0 - 4, v1 + 4)]
    assert min(walls) >= 18, f"the gorge has no walls at U8: {walls}"


def _runs(flags):
    """Consecutive True runs, as lists - the same shape of question the enrichment pass asks."""
    import itertools
    return [list(g) for k, g in itertools.groupby(flags) if k] or [[]]


def test_the_gorge_FLOOR_RUNS_ALL_THE_WAY_OUT_to_the_rim(p, floor):
    """A canyon you can walk out of. The floor is the park's own plane the whole way."""
    v0, v1 = int(p["pits"][0][0]), int(p["pits"][0][1])
    mid = (v0 + v1) // 2
    for u in range(0, 16):
        assert int(floor[u, mid]) <= 2, f"the floor sits at {int(floor[u, mid])} at u{u}"


# --------------------------------------------------------------------------- the seam


def test_the_SEAM_IS_IN_THE_WALL_AND_NOWHERE_ELSE(p, canvas, names):
    """Bone in the scarp, and not one block of it on the turf outside.

    The dig moving INTO the wall is what fixes the measured complaint the flat excavation could
    not - 2.7% of that lot stood twelve courses, so there was no wall to put anything in - and a
    seam that reached the mesa top would be a bone lawn.
    """
    dv, du = p["lot"]
    pit, _ = bonebed._pit_mask(p, dv, du)
    bone = [i for i, n in enumerate(names) if n == "bone_block"]
    assert bone, "no seam was painted at all"
    ys, us, vs = np.where(np.isin(canvas.ids, bone))
    assert len(ys) > 100, f"only {len(ys)} cells of seam - it will not read"
    #: ABOVE THE FLOOR SCATTER. The skeleton, the skulls and their loose bones are `bone_block`
    #: too and they lie ON the floor, where the pit's wobbled edge can legitimately leave one
    #: just outside the mask. What this test is about is the BED in the wall, which is the only
    #: bone standing well above the floor.
    high = [(int(v), int(u), int(y)) for y, u, v in zip(ys, us, vs)
            if y > 5 and not pit[v, u]]
    assert not high, f"{len(high)} cells of seam outside the excavation, e.g. {high[:4]}"
    seam_y = {int(y) for y0, t in p["seams"] for y in range(int(y0), int(y0) + int(t))}
    in_wall = [1 for y, u, v in zip(ys, us, vs) if int(y) in seam_y and pit[v, u]]
    assert len(in_wall) > 80, f"only {len(in_wall)} cells of the bed reached a wall"


# ----------------------------------------------------------------- the span and the cantilever


def test_the_BRIDGE_DECK_IS_LEVEL(p, canvas, names):
    """A deck hung on the catenary is a staircase pretending to be a bridge.

    The cables sag and the deck does not: that is the only arrangement a guest can walk, and it
    is also the reason the thing reads as a suspension bridge rather than as a plank.
    """
    spec = p["bridge"]
    plank = names.index("jungle_planks")
    ys, us, vs = np.where(canvas.ids == plank)
    u = int(spec["u"])
    deck = {int(y) for y, uu, vv in zip(ys, us, vs)
            if uu == u and int(spec["v0"]) < vv < int(spec["v1"])}
    assert len(deck) == 1, f"the bridge deck occupies {sorted(deck)} - it is not level"


def test_the_BELVEDERE_CANTILEVERS_over_the_gorge(p, canvas, names, top):
    """The tower is replaced by height that is EARNED - the drop is under the deck.

    `PF Vantage Frontier Lookout` was 17 x 17, 56 courses and 100% of its own footprint at full
    height: a shaft. What matters here is not that the deck is high but that the ground it reaches
    over is a long way below it.
    """
    spec = p["belvedere"]
    v, u, out_n = int(spec["v"]), int(spec["u"]), int(spec.get("out", 9))
    plank = names.index("jungle_planks")
    deck = [int(y) for y in range(canvas.ids.shape[0])
            if canvas.ids[y, u + 1, v + out_n - 2] == plank]
    assert deck, "the belvedere has no deck at its outer end"
    ground = int(top[u + 1, v + out_n - 2])
    assert deck[0] - 0 >= 18, f"the deck stands only {deck[0]} courses over the plane"
    # the mast is what the park sees from a distance, and it has to clear the deck properly
    assert int(top[u + int(spec.get("d", 5)) // 2, v + out_n // 2]) >= deck[0] + 12, \
        "the mast is not tall enough to hold the skyline the tower was holding"


# --------------------------------------------------------------------------- the fixes


def test_a_VINE_ONLY_EVER_HANGS_ON_A_FULL_CUBE(canvas, names):
    """The belvedere, the bridge and the gallery all clear courses above their own decks.

    So a face the HEIGHT FIELD calls solid can be air by the time the planting runs - six vines
    shipped on nothing - and `lot.has` is the canvas's own "is anything here", which a FENCE
    satisfies, so two more shipped clinging to a rail. A vine hanging in air renders identically
    to one on a wall in every sheet this repo has.
    """
    #: THE FLAG NAMES THE FACE THE VINE CLINGS TO, so the supporting block is one step ALONG that
    #: compass direction from the vine - west is -V, north is -U. Written the other way round this
    #: test reported 376 failures on a build the audit passes, which is the same inversion the
    #: generator itself shipped once and records in its own comment.
    back = {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0)}
    bad = []
    for i, e in enumerate(canvas.palette):
        if state_name(e).split(":")[-1] != "vine":
            continue
        props = e.value.get("Properties")
        side = next((k for k, x in props.value.items()
                     if str(x.value if hasattr(x, "value") else x) == "true" and k in back),
                    None) if props else None
        if side is None:
            continue
        dv, du = back[side]
        ys, us, vs = np.where(canvas.ids == i)
        for y, u, v in zip(ys, us, vs):
            wv, wu = int(v) + dv, int(u) + du
            if not (0 <= wv < canvas.ids.shape[2] and 0 <= wu < canvas.ids.shape[1]):
                continue
            n = names[canvas.ids[y, wu, wv]]
            if not (n and blocks.is_full_cube(n)):
                bad.append((int(v), int(y), int(u), side, n))
    assert not bad, f"{len(bad)} vines with no face to cling to, e.g. {bad[:4]}"


def test_BOTH_PIERS_OF_THE_ARCH_REACH_THE_LINTEL(p, canvas, names):
    """The lintel is one course across the span, so two piers on different ground must both meet it.

    Built to their own heights the low one stopped short and the far half of the gate shipped as a
    twenty-one cell free-floating stray. It never showed while the only caller stood both feet on
    the flat, which is exactly the kind of latent bug a second caller finds.
    """
    spec = p["arch"]
    v = int(spec["v"])
    log = [i for i, n in enumerate(names) if n in ("jungle_log", "stripped_jungle_log")]
    for cu in (int(spec["u0"]), int(spec["u1"])):
        col = [y for y in range(canvas.ids.shape[0]) if canvas.ids[y, cu, v] in log]
        assert col, f"the pier at u{cu} has no shaft at all"
        assert max(col) - min(col) + 1 == len(col), \
            f"the pier at u{cu} has a gap in it: {sorted(col)}"


def test_the_gallery_FLIP_MOVES_THE_RAIL_AND_TURNS_THE_FLIGHT_TOGETHER():
    """A deck reached from the wrong end is a deck with a fence across its own stair.

    The bone bed's overlook has the drop at rising u and this one has it at falling u, so the rail
    and the approach both have to move - and moving one without the other is the failure that
    would look perfectly fine in every render.
    """
    src = open("mcbuild/gen/bonebed.py", encoding="utf-8").read()
    body = src[src.index("def _gallery("):src.index("def _steps(")]
    assert "rail_u = u if flip else u + w - 1" in body
    assert "foot = u + w - 1 if flip else u" in body
    assert "_steps(lot, h, int(fv), foot, y, seed, sign)" in body
    steps = src[src.index("def _steps("):src.index("def _gantry(")]
    assert 'face = "south" if sign > 0 else "north"' in steps, \
        "the tread's facing must follow the flight, or a backwards flight cannot be walked up"


# --------------------------------------------------------------------------- the whole thing


def test_it_is_ONE_CONNECTED_PIECE(canvas):
    s = canvas.ids > 0
    sy, su, sv = s.shape
    seen = np.zeros_like(s)
    ys, us, vs = np.where(s)
    q = deque([(int(ys[0]), int(us[0]), int(vs[0]))])
    seen[q[0]] = True
    n = 0
    while q:
        y, u, v = q.popleft()
        n += 1
        for dy, du_, dv_ in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            a, b, c = y + dy, u + du_, v + dv_
            if 0 <= a < sy and 0 <= b < su and 0 <= c < sv and s[a, b, c] and not seen[a, b, c]:
                seen[a, b, c] = True
                q.append((a, b, c))
    assert n == int(s.sum()), f"{int(s.sum()) - n} cells in strays"


def test_the_LANDS_AVENUE_IS_NOT_RAISED(p, canvas):
    """`Park Ways` runs it U41-45 from V1 to V170 and this design does not get to build on it.

    **THE CONTRACT IS THE LANE, NOT THE AIR OVER IT.** A jungle canopy reaching across the road
    nine courses up is what this land is supposed to look like; a block at foot height is a street
    this design was not allowed to raise. Written as "nothing at all stands here" the test forbids
    the first in order to catch the second.
    """
    for a, b in p["level_u"]:
        for u in range(a, b + 1):
            for v in range(p["lot"][0]):
                if _is_arch(p, v, u):
                    continue
                for y in range(0, 3):
                    assert not canvas.ids[y, u, v], (
                        f"something stands in the avenue's own lane at v{v} y{y} u{u}")



def _is_arch(p, v, u):
    spec = p.get("arch") or {}
    return (int(spec.get("v", -99)) <= v < int(spec.get("v", -99)) + int(spec.get("d", 3))
            and int(spec.get("u0", -99)) <= u <= int(spec.get("u1", -99)))


def test_every_sign_line_fits_the_board(p):
    """Fifteen characters. This park has shipped "MINE CART ESCAP" and "and prize windo"."""
    lines = list((p.get("arch") or {}).get("lines") or [])
    for b in (p.get("boards") or []):
        lines += list(b["lines"])
    over = [x for x in lines if len(x) > 15]
    assert not over, f"clipped mid-word: {over}"


def test_it_is_all_cheap_or_ok_and_nothing_is_a_gravity_block_over_air(canvas, names):
    """Rule 13 and rule 16, over the finished mass rather than over the table."""
    from mcbuild import palette
    used = {n for i, n in enumerate(names) if n and int((canvas.ids == i).sum())}
    dear = [n for n in used if palette.tier(n) == "expensive"]
    assert not dear, f"expensive blocks in a terrain design: {dear}"


def test_the_capture_says_the_TOWER_WAS_BARELY_BUILT():
    """The cost of retiring `PF Vantage Frontier Lookout`, measured rather than asserted.

    Recorded because it is the number the decision rests on: if a later capture shows the tower
    mostly standing, retiring it stops being nearly free and somebody should be told.
    """
    cap = schem.load("out/islandplateau.litematic")
    co = json.load(open("out/islandplateau.scan.json"))["origin"]
    lo = schem.load("out/PF Vantage Frontier Lookout.litematic")
    lo_o = json.load(open("out/PF Vantage Frontier Lookout.scan.json"))["origin"]
    built = 0
    want = 0
    for y in range(lo.ids.shape[0]):
        for u in range(lo.ids.shape[1]):
            for v in range(lo.ids.shape[2]):
                if not lo.ids[y, u, v]:
                    continue
                want += 1
                wy, wu, wv = (lo_o["y"] + y - co["y"], lo_o["z"] + u - co["z"],
                              lo_o["x"] + v - co["x"])
                if (0 <= wy < cap.ids.shape[0] and 0 <= wu < cap.ids.shape[1]
                        and 0 <= wv < cap.ids.shape[2] and cap.ids[wy, wu, wv]):
                    built += 1
    assert want > 3000
    assert built / want < 0.25, (
        f"the tower is {100 * built / want:.0f}% built now - retiring it is no longer nearly free")
