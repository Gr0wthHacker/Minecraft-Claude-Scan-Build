"""THE SKY OVER THE LOST PLATEAU - the contracts that keep three floating rocks and an aeroplane
honest, and the one that says they must NOT touch."""
import json
import os
from collections import Counter, deque

import numpy as np
import pytest
import yaml

from mcbuild import scan
from mcbuild.gen import skies

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = os.path.join(ROOT, "configs", "pf_plateau_skies.yaml")
OUT = os.path.join(ROOT, "out", "PF Plateau Skies.litematic")
LAND = os.path.join(ROOT, "out", "plateau_sky_ctx.litematic")


def _params():
    with open(CFG, encoding="utf-8") as fh:
        return yaml.safe_load(fh)["params"]


def _meta():
    with open(os.path.splitext(OUT)[0] + ".scan.json", encoding="utf-8") as fh:
        return json.load(fh)


def _pieces(model):
    """Every 6-connected piece, biggest first."""
    sol = model.solid()
    H, D, W = sol.shape
    seen = np.zeros_like(sol)
    out = []
    for y0, z0, x0 in zip(*np.nonzero(sol)):
        if seen[y0, z0, x0]:
            continue
        q, cur = deque([(y0, z0, x0)]), []
        seen[y0, z0, x0] = 1
        while q:
            y, z, x = q.popleft()
            cur.append((y, z, x))
            for dy, dz, dx in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
                b, c, d = y + dy, z + dz, x + dx
                if 0 <= b < H and 0 <= c < D and 0 <= d < W and sol[b, c, d] and not seen[b, c, d]:
                    seen[b, c, d] = 1
                    q.append((b, c, d))
        out.append(cur)
    out.sort(key=len, reverse=True)
    return out


def test_a_level_wing_is_a_SHEET_and_a_banked_one_is_a_STAIRCASE():
    """THE MEASUREMENT THAT DECIDED THE AIRCRAFT'S ATTITUDE, kept so it cannot be undone by taste.

    A roll is a better attitude and a much worse aeroplane: a wing climbing a fraction of a course
    per cell of side is a flight of stairs, and at 46 cells of span every step is visible edge-on.
    What this pins is the ARITHMETIC rather than the picture - how many distinct courses the wing
    occupies - because a render of a banked wing and a level one are both perfectly good renders
    and only one of them reads as a wing.
    """
    p = {**_params()}
    #: THE AIRCRAFT ALONE. With the flock left in, the courses THEY occupy swamp the measurement
    #: and every bank angle reads identically - which is a test that has stopped testing anything
    #: while still being green, and this repo has shipped one of those.
    p["isles"] = ()
    p["birds"] = ()
    base = dict(p["plane"])
    levels = {}
    for bank in (0, 7, 16):
        q = dict(p)
        q["plane"] = {**base, "bank": bank}
        c = skies.build(q)
        ys = sorted({int(y) for y, _z, _x in zip(*np.nonzero(c.ids != 0))})
        levels[bank] = len(ys)
    assert levels[0] < levels[7] < levels[16], (
        f"the bank is meant to spread the aircraft over more courses: {levels}")
    assert base["bank"] == 0, (
        "the shipped aircraft is LEVEL - rendered at 0, 7 and 16 side by side the answer was not "
        "close, and a wing built of slats is not a wing")


@pytest.mark.skipif(not os.path.exists(OUT), reason="PF Plateau Skies is not shipped")
def test_every_piece_is_WHOLE_and_they_are_DELIBERATELY_not_one():
    """**DISCONNECTED IS THE DESIGN, so the usual contract is exactly backwards here.**

    One component would mean an isle was touching the aeroplane or another isle, which is the one
    thing a sky composition must not do. What has to be true is that each PIECE is whole - a
    detached tree crown, a propeller blade or an undercarriage leg in open air is a stray, and all
    three of those shipped once each while the audit reported 0 problems and a correct bill of
    materials.
    """
    s = scan.load(OUT)
    pieces = _pieces(s.model)
    p = _params()
    want = len(p.get("isles") or ()) + len(p.get("birds") or ()) + (1 if p.get("plane") else 0)
    assert len(pieces) == want, (
        f"{len(pieces)} pieces, wanted {want} (the aircraft and {want - 1} others): "
        f"{[len(p) for p in pieces]}")
    assert min(len(q) for q in pieces) > 120, (
        f"the smallest piece is {min(len(q) for q in pieces)} cells - something has come away")


@pytest.mark.skipif(not os.path.exists(OUT), reason="PF Plateau Skies is not shipped")
def test_the_aircraft_has_EVERY_PART_and_a_count_of_zero_would_not_say_so_by_accident():
    """A build with a part missing is still one piece with a clean audit and a correct BOM.

    The ankylosaur's horns reported 124 placements while gaining ZERO cells - they were entirely
    inside the skull - and the frog shipped with `forelegs: 0` in its own sidecar and nobody
    noticed. These counts are CHANGED cells, which is the only measure that reads 0 for a part
    that did not happen and non-zero for one that is only PAINT (a roundel recolours the wing it
    sits on, so counted as new cells it reads 0 and looks exactly like a failure).
    """
    parts = _meta()["parts"]
    for k in ("wing", "body", "tail", "fin", "cowl", "prop", "strut", "gear", "mark", "cockpit"):
        assert parts.get("plane " + k, 0) > 0, f"the aircraft has no {k}: {parts}"
    assert parts["plane clipped"] == 0, "the aircraft is clipped by the canvas"
    assert parts["plane wing"] > parts["plane body"], "a biplane is mostly wing"


def test_an_isle_is_a_LENS_AND_A_KEEL_even_though_nothing_ships_one_any_more():
    """**THE FLOATING ISLES ARE RETIRED, NOT DELETED**, and the difference is this test.

    Jack: *"I don't think floating islands are on theme in this case."* He is right - a floating
    island is a fantasy trope and the Lost Plateau is Conan Doyle, not Skyblock: the whole premise
    of the place is that it is REAL and merely unreachable, and rock that defies gravity undoes it.
    `isles:` is empty in the config rather than gone from the generator, because the shape would
    suit Prismworks, whose own fiction is a crystal that does exactly this - so the contract is
    kept and exercised on a built isle rather than on the shipped artifact.
    """
    from mcbuild.gen.canvas import Canvas
    from mcbuild.nbt import state_name
    c = Canvas(60, 60, 60)
    skies._isle(c, {"at": [30, 30], "y": 40, "r": 14, "keel": 18, "trees": 3}, 5)
    names = [state_name(t).split(":")[-1] for t in c.palette]
    cells = {}
    for y, z, x in zip(*np.nonzero(c.ids != 0)):
        cells[(int(x), int(y), int(z))] = names[int(c.ids[y, z, x])]
    for spec in ({"at": [30, 30], "y": 40, "r": 14},):
        ax = int(spec["at"][0])
        az = int(spec["at"][1])
        y0 = int(spec["y"])
        rad = float(spec["r"])
        near = [p for p in cells if abs(p[0] - ax) <= rad + 4 and abs(p[2] - az) <= rad + 4]
        by_course = Counter(p[1] for p in near)
        deck = by_course.get(y0, 0)
        low = [n for y, n in by_course.items() if y < y0 - rad * 0.6]
        assert deck, f"the isle at {ax},{az} has no deck course"
        assert low, f"the isle at {ax},{az} has no keel under it"
        # IT NARROWS TO A POINT, AND THE PROPERTY IS THE PROFILE RATHER THAN A RATIO. Three
        # readings of this were written before this one and all three are wrong: the furthest cell
        # from the centre is defeated by the outline's own wobble, which is deliberate and
        # direction-dependent; every cell below the waterline is a VOLUME, bigger than any single
        # course of anything; and a ratio between two courses is a threshold standing in for a
        # shape, which this repo has had to unlearn on a plate root, a head pinch and a crest.
        #
        # What an isle actually IS: widest at or just under its deck, narrowing every course down,
        # and ending in a keel that is a point rather than a stump.
        rock = {y: n for y, n in by_course.items() if y <= y0}
        widest = max(rock, key=lambda y: rock[y])
        assert y0 - widest <= 2, (
            f"the isle at {ax},{az} is widest at y{widest}, {y0 - widest} under its own deck - "
            f"that is a lump, not an island")
        lo = min(rock)
        assert rock[lo] < 0.06 * rock[widest], (
            f"the isle at {ax},{az} ends in a stump of {rock[lo]} cells against a {rock[widest]} "
            f"deck - a keel comes to a POINT")
        for y in range(lo + 1, widest):
            assert rock[y] >= rock[y - 1], (
                f"the isle at {ax},{az} bulges at y{y}: {rock[y - 1]} -> {rock[y]} going up")
        assert any(cells[p] == "vine" for p in near), f"the isle at {ax},{az} trails no vines"
        assert any(cells[p].endswith("_leaves") for p in near), f"the isle at {ax},{az} has no wood"


@pytest.mark.skipif(not os.path.exists(OUT), reason="PF Plateau Skies is not shipped")
def test_the_flock_IS_THE_LAND_S_OWN_ANIMAL_and_none_of_them_is_PERCHED():
    """**WHAT WOULD BE A REUSED ASSET IS THE ROOSTING ANIMAL AGAIN, NOT THE SPECIES.**

    Jack refused two of those on the causeway - *"get rid of the gecko and bat - those are used
    assets, we want NEW things"* - and both were creatures lifted out of the lowland into a place
    with no claim on them. This land already has a pteranodon on its summit and a nesting colony
    on its rim, so adults on the wing over it is that story finished. The thing that has to be
    true is that they read as a DIFFERENT POSE: no crag under any of them, and every one spread
    wider than the roosting animal's 0.72.
    """
    p = _params()
    birds = p.get("birds") or ()
    assert len(birds) >= 3, "a flock is not one bird"
    for i, b in enumerate(birds):
        assert not b.get("perch"), f"bird {i + 1} carries a crag - that is the roosting one again"
        assert float(b.get("spread", 0)) > 0.72, (
            f"bird {i + 1} is at spread {b.get('spread')} - the animal on the summit is 0.72 and "
            f"these have to read as a different attitude, not only a different altitude")
    spans = sorted(float(b["span"]) for b in birds)
    assert spans[0] < spans[-1] * 0.6, (
        f"the flock is all one size ({spans}) - a group without a size ladder is a row")
    assert spans[-1] > float(p["plane"]["span"]), (
        "the biggest thing in this sky should be an ANIMAL, which is the Lost World's whole point "
        "and is what the floating rock was doing badly")

    parts = _meta()["parts"]
    for i in range(len(birds)):
        assert parts.get(f"bird{i + 1} cells", 0) > 100, f"bird {i + 1} placed almost nothing"


@pytest.mark.skipif(not (os.path.exists(OUT) and os.path.exists(LAND)),
                    reason="the design or the land context is not shipped")
def test_NOTHING_IN_THE_SKY_TOUCHES_THE_LAND():
    """The whole point is that they hang free, so a single shared cell is the design failing.

    And a capture cannot say so: `plateau_sky_ctx` is a cut of `Park Complete`, which is the park's
    DESIGN - the world as built holds only 62% of the coaster and would report a collision with an
    unbuilt module as clean. That is the fault the canopy walk shipped with.
    """
    s = scan.load(OUT)
    ox, oy, oz = s.origin
    ys, zs, xs = np.nonzero(s.model.solid())
    mine = set(zip((xs + ox).tolist(), (ys + oy).tolist(), (zs + oz).tolist()))
    w = scan.load(LAND)
    wx, wy, wz = w.origin
    wys, wzs, wxs = np.nonzero(w.model.solid())
    land = set(zip((wxs + wx).tolist(), (wys + wy).tolist(), (wzs + wz).tolist()))
    hit = sorted(mine & land)
    assert not hit, f"{len(hit)} cells of the sky stand in the land, e.g. {hit[:4]}"
    # ...and there is real air under every piece, not a one-cell gap that reads as touching
    lowest = min(p[1] for p in mine)
    below = {(x, z) for (x, y, z) in mine if y <= lowest + 2}
    for (x, z) in list(below)[:200]:
        top = max((y for (a, y, b) in land if a == x and b == z), default=None)
        if top is not None:
            assert lowest - top > 4, f"the sky comes within {lowest - top} of the land at {x},{z}"


@pytest.mark.skipif(not os.path.exists(OUT), reason="PF Plateau Skies is not shipped")
def test_it_stays_under_the_BUILD_LIMIT_and_inside_the_LAND():
    s = scan.load(OUT)
    ox, oy, oz = s.origin
    ys, zs, xs = np.nonzero(s.model.solid())
    assert int((ys + oy).max()) <= 317, "past the build limit"
    assert 97500 <= int((xs + ox).min()) and int((xs + ox).max()) <= 97699, "off the land in X"
    assert 80300 <= int((zs + oz).min()) and int((zs + oz).max()) <= 80469, "off the land in Z"


@pytest.mark.skipif(not os.path.exists(OUT), reason="PF Plateau Skies is not shipped")
def test_it_is_all_CHEAP_and_all_1_19():
    from mcbuild import blocks, palette
    from mcbuild.nbt import state_name
    s = scan.load(OUT)
    for t in s.model.palette:
        b = state_name(t).split(":")[-1].split("[")[0]
        if b == "air":
            continue
        assert palette.tier(b) in ("cheap", "ok"), f"{b} is {palette.tier(b)}"
        assert blocks.exists(b), b
