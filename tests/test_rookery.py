"""The rim rookery: the palette, the pieces, and the walk that goes under the dinosaur.

The two things worth pinning hardest are the ones a render cannot judge and an audit cannot see.
A **walk with a hole in it** is a legal, supported, affordable path - and this one threads a
one-cell gap between a sauropod's feet, so a single refused cell breaks the only route to half the
strip. A **refused sign** draws exactly like no sign at all. Both shipped once during this build.
"""
from __future__ import annotations

import json
import os
from collections import deque

import numpy as np
import pytest
import yaml

from mcbuild import blocks, palette, schem
from mcbuild.gen import rookery as rk

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(ROOT, "configs", "pf_frontier_rim.yaml")
OUT = os.path.join(ROOT, "out")
ART = os.path.join(OUT, "PF Frontier Rim.litematic")
PARK = os.path.join(OUT, "Park Complete.litematic")
SAUROPOD = os.path.join(OUT, "PF Sauropod.litematic")


def cfg():
    return yaml.safe_load(open(CONFIG, encoding="utf-8"))


@pytest.fixture(scope="module")
def built():
    """The design, built. It reads the shipped park, so this is skipped without one."""
    if not os.path.exists(PARK):
        pytest.skip("the park is not shipped")
    return rk.build(cfg()["params"])


def _origin(path):
    return json.load(open(os.path.splitext(path)[0] + ".scan.json"))["origin"]


# --------------------------------------------------------------------------- the palette


def test_every_material_is_legal_spendable_and_cheap_or_ok():
    """Rule 16. Dirt and grass are CURRENCY on this server, and a rookery is mostly ground."""
    for key, name in rk.KIT.items():
        assert blocks.exists(name), f"{key}={name} is not a block"
        assert blocks.spendable(name), f"{key}={name} is CURRENCY on this server"
        assert palette.tier(name) != "expensive", f"{key}={name} is expensive tier"


def test_the_stone_is_a_real_value_ladder_across_families():
    """**MEASURED, NOT TRUSTED.** This repo has concluded five separate times that the economy has
    no value contrast, and every one of those measurements searched inside ONE material family,
    where a ladder cannot exist by construction. Across families it is real - and a stack with no
    tonal step in it is a grey post."""
    def lum(name):
        r, g, b = blocks.color(name, "side")
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    # THE GREY LADDER. `warm` is deliberately NOT a rung of it - dripstone's job is HUE, so that
    # five stones are not five greys - and it is asserted separately below.
    rungs = [lum(rk.KIT[k]) for k in ("dark", "wash", "pale", "guano")]
    assert rungs == sorted(rungs), f"the ladder is not monotonic: {rungs}"
    steps = [b - a for a, b in zip(rungs, rungs[1:])]
    assert min(steps) >= 15, f"a step under 15 is not a tone: {steps}"


def test_the_warm_stone_is_actually_warm():
    """**FIVE MATERIALS INSIDE TWENTY-ONE POINTS OF LUMINANCE IS ONE GREY**, which is the mistake
    this repo has recorded in five places. `dripstone_block` sits between two of the grey rungs on
    luminance and is 30 warmer in red-minus-blue, which is what stops the mass reading as a
    monochrome heap however the tones are mixed."""
    def warmth(name):
        r, _g, b = blocks.color(name, "side")
        return r - b

    warm = warmth(rk.KIT["warm"])
    for k in ("dark", "wash", "pale"):
        assert warm - warmth(rk.KIT[k]) > 15, f"{k} is as warm as the warm stone"


def test_the_guano_reads_against_the_rock_it_caps():
    """A rookery is WHITE ON TOP or it is a pile of rocks."""
    def lum(name):
        r, g, b = blocks.color(name, "side")
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    assert lum(rk.KIT["guano"]) - lum(rk.KIT["dark"]) > 120


# --------------------------------------------------------------------------- what was measured


def test_the_sauropods_ground_footprint_really_is_four_feet(built):
    """**THE WHOLE LAYOUT RESTS ON THIS.** If the animal's ground footprint were its silhouette
    the walk could not pass at all and the belly deck would be inside a leg. Re-derived off the
    animal's own artifact rather than quoted from the config's comment."""
    if not os.path.exists(SAUROPOD):
        pytest.skip("the sauropod is not shipped")
    m = schem.load(SAUROPOD)
    o = _origin(SAUROPOD)
    names = [n.split(":")[-1] for n in m.names]
    y = 203 - o["y"]
    occ = np.array([[names[m.ids[y, z, x]] != "air" for x in range(m.ids.shape[2])]
                    for z in range(m.ids.shape[1])])
    us = sorted({int(z) + o["z"] - 80300 for z, _x in zip(*occ.nonzero())})
    assert us, "the animal has no ground footprint at all"
    # two rows of feet and nothing between them
    runs = []
    for u in us:
        if runs and u == runs[-1][-1] + 1:
            runs[-1].append(u)
        else:
            runs.append([u])
    assert len(runs) == 2, f"a sauropod stands on two rows of feet, measured {len(runs)}: {runs}"
    # ...and the lane between the near and far leg of each row is clear
    for run in runs:
        for u in run:
            z = u + 80300 - o["z"]
            open_v = [x + o["x"] - 97500 for x in range(occ.shape[1]) if not occ[z, x]]
            assert 193 in open_v, f"V193 is blocked at U{u} - the walk cannot pass"


# --------------------------------------------------------------------------- the walk


def test_the_walk_reaches_every_column_of_the_strip(built):
    """**A WALK WITH A HOLE IN IT IS A LEGAL PATH**, which is why this is a flood and not a
    count. The route threads a one-cell gap between the animal's feet, so one refused cell cuts
    the sauropod end off from the colony and nothing in the audit says a word."""
    c = built
    m = schem.load(PARK)
    o = _origin(PARK)
    names = np.array([n.split(":")[-1] for n in m.names])
    passable = {"air", "cave_air", "void_air", "moss_carpet", "short_grass", "fern", "tall_grass",
                "vine", "glow_lichen", "poppy", "dandelion", "azalea", "flowering_azalea",
                "oxeye_daisy", "cornflower", "allium", "blue_orchid", "white_tulip", "red_tulip",
                "orange_tulip", "pink_tulip", "azure_bluet", "lily_of_the_valley",
                "sweet_berry_bush", "spruce_fence", "spruce_wall_sign"}
    y0, y1 = 200, 215
    dv, du = c.sx, c.sz
    solid = np.zeros((y1 - y0 + 1, du, dv), bool)
    for y in range(y0, y1 + 1):
        solid[y - y0] = ~np.isin(names[m.ids[y - o["y"], 0:du, 187:187 + dv]], list(passable))
    for y, z, x in zip(*c.ids.nonzero()):
        n = c.get_name(int(x), int(y), int(z)).split(":")[-1]
        wy = 203 + int(y)
        if y0 <= wy <= y1 and n not in passable:
            solid[wy - y0, int(z), int(x)] = True
    stand = np.zeros_like(solid)
    stand[1:-1] = solid[:-2] & ~solid[1:-1] & ~solid[2:]

    seeds = [(y, du - 3, 1) for y in range(stand.shape[0]) if stand[y, du - 3, 1]]
    assert seeds, "nowhere to stand at the colony end of the walk"
    seen = np.zeros_like(stand)
    q = deque([seeds[0]])
    seen[seeds[0]] = True
    while q:
        y, u, v = q.popleft()
        for a, b in ((u + 1, v), (u - 1, v), (u, v + 1), (u, v - 1)):
            if not (0 <= a < du and 0 <= b < dv):
                continue
            for dy in (0, 1, -1):
                if 0 <= y + dy < stand.shape[0] and stand[y + dy, a, b] and not seen[y + dy, a, b]:
                    seen[y + dy, a, b] = True
                    q.append((y + dy, a, b))
                    break
    reached = {int(u) for _y, u, _v in zip(*seen.nonzero())}
    missing = sorted(set(range(du)) - reached)
    assert not missing, f"{len(missing)} columns of the strip are unreachable on foot: {missing}"


def test_a_walk_needs_headroom_and_not_sky(built):
    """**`_Ground.lawn` DEMANDS NINE CLEAR COURSES, WHICH IS RIGHT FOR A TREE AND WRONG FOR A
    PATH.** The sauropod's legs merge into its barrel as they rise, so the gap the boardwalk
    threads between its feet is open at the ground and closed nine courses up - and using `lawn`
    for both put a one-cell hole in the walk under the animal."""
    if not os.path.exists(PARK):
        pytest.skip("the park is not shipped")
    from mcbuild.gen.frontier_scatter import _Ground, flora_for
    from mcbuild.gen.vertical import Ctx
    p = cfg()["params"]
    g = _Ground(Ctx(p["under"]), p.get("anchor", [97500, 203, 80300]), 13, 173, p["at"],
                1, (), flora=flora_for("jungle"))
    under = [u for u in range(26, 53) if rk.underfoot(g, 6, u)]
    lawn = [u for u in range(26, 53) if g.lawn(6, u)]
    assert len(under) > len(lawn), (
        "the headroom rule should open cells `lawn` refuses - if it does not, either the animal "
        f"has moved or the rule is doing nothing ({len(under)} vs {len(lawn)})")


def test_the_deck_does_not_fence_the_walk_off(built):
    """A GATE IN THE WRONG WALL IS A WALL. The deck stands in the middle of the walk's own lane
    under the animal; its rail's openings were on the sides, so it ran a complete fence across
    both ends of the walk and the whole sauropod end became unreachable."""
    d = built.meta["parts"]["deck"]
    assert d and d["rail"], "the deck has no rail at all"
    v0, u0 = d["at"]
    dv, du = d["size"]
    mid = v0 + dv // 2
    for b in (u0 - 1, u0 + du):
        assert not built.solid(mid, 1, b), f"the deck's rail closes its own gate at U{b}"


# --------------------------------------------------------------------------- the content


def test_it_has_the_skyline_it_was_built_for(built):
    """**THE MEASUREMENT THIS DESIGN EXISTS TO ANSWER.** The colony was 102 blocks long with
    NOTHING over three courses tall - `tallest 5, zero columns over 6`."""
    parts = built.meta["parts"]
    assert parts["skyline"] >= 10, f"the tallest stack is {parts['skyline']} courses"
    assert len(parts["stacks"]) >= 5
    assert all(s["h"] >= 6 for s in parts["stacks"]), \
        f"a stack under six courses dissolves into ground noise: {[s['h'] for s in parts['stacks']]}"


def test_a_stack_is_a_pillar_with_a_head_and_not_a_spike(built):
    """Tapered smoothly to nothing it came out as a chimney - a one-wide column with a white cap,
    which reads as a smokestack or a totem. The shape is a flared foot, a WAIST, and a crown that
    overhangs it, and the crown is corbelled because a strict directly-below support rule cannot
    widen a column at all."""
    c = built
    tall = max(c.meta["parts"]["stacks"], key=lambda s: s["h"])
    v0, u0 = tall["at"]
    h = tall["h"]

    # **MEASURE THE STACK, NOT WHATEVER IS STANDING NEXT TO IT.** Counted as "any solid cell" the
    # waist read as WIDER than the foot, because a jungle crown from the planting sweep hangs over
    # the shaft at exactly that height - the same shape of error as measuring an animal's barrel
    # and getting its mane.
    rock = {rk.KIT[k] for k in ("dark", "warm", "wash", "pale", "guano")}

    def width(y):
        return sum(1 for dv in range(-5, 6)
                   if c.get_name(v0 + dv, y, u0).split(":")[-1] in rock)

    foot, waist, head = width(0), width(int(h * 0.55)), width(h - 1)
    assert foot >= 4, f"no flared foot: {foot}"
    assert waist < foot, f"no waist: foot {foot}, waist {waist}"
    assert head > waist, f"the crown does not overhang the waist: waist {waist}, head {head}"


def test_the_eggs_are_there_and_some_nests_have_hatched(built):
    """Jack: "i like the eggs". A colony reads over a SEASON rather than as one photograph
    repeated, so some scrapes carry a clutch and some carry the shell it came out of."""
    nests = built.meta["parts"]["nests"]
    assert built.meta["parts"]["eggs"] >= 12, f"only {built.meta['parts']['eggs']} eggs"
    assert any(n["hatched"] for n in nests), "no hatched scrape - the colony is one moment"
    assert any(not n["hatched"] for n in nests), "no clutch at all"
    assert all(n["cells"] for n in nests), "a scrape that placed nothing is a scrape nobody sees"


def test_every_sign_it_asks_for_is_actually_PLACED(built):
    """**A REFUSED SIGN DRAWS EXACTLY LIKE NO SIGN AT ALL**, and both of this design's shipped
    refused on the first build: the hide's board was written at the doorway's own column, which is
    the one column of that wall with nothing in it, and the deck's post landed in the cell its own
    sign then needed. This park has shipped that failure in four building kinds already."""
    parts = built.meta["parts"]
    assert parts["hide"]["signed"], "the hide's board was refused"
    assert parts["deck"]["signed"], "the deck's board was refused"
    for p in parts["plaques"]:
        assert p["signed"], f"a plaque was refused at {p['at']}: {p.get('refused')}"


def test_the_hide_has_a_door_and_a_slit_and_the_loop_left_them_empty(built):
    """What makes voxels read as architecture is REGULARITY AND OPENINGS. Building the ring first
    and cutting a hole afterwards repaints cells that already exist - the void tower shipped a
    plain drum that way and nothing about the code looked wrong."""
    h = built.meta["parts"]["hide"]
    assert h["door"] >= 4, f"the hide's doorway is {h['door']} cells"
    assert h["slit"] >= 3, f"the hide's viewing slit is {h['slit']} cells"


def test_the_hatchlings_read_as_animals_and_not_as_lumps(built):
    """A juvenile is one convex mass with a pattern on it - the ladybird's category. What carries
    it at five blocks is the HEAD and the crest, not the wings."""
    chicks = built.meta["parts"]["hatchlings"]
    assert len(chicks) >= 2
    assert all(h["cells"] >= 12 for h in chicks), [h["cells"] for h in chicks]


def test_the_bone_find_stands_proud_of_its_matrix(built):
    """A SKELETON LAID FLAT ON MOSS IS A FLOOR DECAL. What makes a bone bed read is that the bones
    stand a course above the rock they are weathering out of, and that the ribs ARC."""
    c = built
    b = c.meta["parts"]["bones"][0]
    v0, u0 = b["at"]
    assert b["ribs"] >= 8, f"only {b['ribs']} rib cells"
    spine = [u for u in range(u0, u0 + 9) if c.get_name(v0, 1, u).split(":")[-1] == "bone_block"]
    assert len(spine) >= 6, f"the spine is {len(spine)} cells at the raised course"
    for u in spine:
        assert c.solid(v0, 0, u), f"the spine at U{u} floats over its own matrix"


def test_nothing_floats(built):
    """Every cell either sits on the one below it or on the world's own ground."""
    c = built
    floating = [(int(x), int(y), int(z)) for y, z, x in zip(*c.ids.nonzero())
                if y > 0 and not c.solid(int(x), int(y) - 1, int(z))
                and not any(c.solid(int(x) + a, int(y), int(z) + b)
                            for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1)))]
    # a wall sign, a lantern and a fence hang off a neighbour, which the check above allows
    assert not floating, f"{len(floating)} cells with nothing under or beside them: {floating[:6]}"


# --------------------------------------------------------------------------- what shipped


@pytest.mark.skipif(not os.path.exists(ART), reason="PF Frontier Rim is not shipped")
def test_the_shipped_design_stays_inside_the_rim_reserve():
    m = schem.load(ART)
    o = _origin(ART)
    ys, zs, xs = m.ids.nonzero()
    v = xs + o["x"] - 97500
    u = zs + o["z"] - 80300
    assert int(v.min()) >= 187, f"it reaches V{int(v.min())}, inside the railway band"
    assert int(v.max()) <= 199, f"it reaches V{int(v.max())}, off the plot"
    assert int(u.max()) <= 172, f"it reaches U{int(u.max())}, into the claim reach"


@pytest.mark.skipif(not os.path.exists(ART), reason="PF Frontier Rim is not shipped")
def test_it_never_takes_a_cell_the_sauropod_owns():
    """The animal is the reason anybody walks out here. Nothing keeps out of it by BOX - its
    silhouette is 11 of the band's 13 courses - so the ground probe is the only thing standing
    between a perch stack and a hole through a fifty-block dinosaur."""
    if not os.path.exists(SAUROPOD):
        pytest.skip("the sauropod is not shipped")
    m, o = schem.load(ART), _origin(ART)
    s, so = schem.load(SAUROPOD), _origin(SAUROPOD)
    mine = {(int(x) + o["x"], int(y) + o["y"], int(z) + o["z"])
            for y, z, x in zip(*m.ids.nonzero())}
    theirs = {(int(x) + so["x"], int(y) + so["y"], int(z) + so["z"])
              for y, z, x in zip(*s.ids.nonzero())}
    assert not (mine & theirs), f"{len(mine & theirs)} cells inside the sauropod"
