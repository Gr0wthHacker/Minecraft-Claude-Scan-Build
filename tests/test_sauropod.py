"""The Lost Plateau's landmark, against the four ways it shipped wrong before it shipped right.

Every test here is a defect this build actually produced, and three of the four were invisible:
a canvas sized for the wrong axis clipped the animal to a fifth of its length and reported it only
as a refusal count; a protection set keyed on MATERIAL skipped the whole coat pass and left the
tally at four zeros; and an eye placed at a computed half-width floated proud of a head that a
sweep had already moved.
"""
from __future__ import annotations

import os

import pytest
import yaml

from mcbuild import blocks, palette
from mcbuild.gen import sauropod

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(ROOT, "configs", "pf_sauropod.yaml")
FACINGS = ("north", "south", "east", "west")


def _cells(c):
    return {(v, y, u) for v in range(c.sx) for y in range(c.sy) for u in range(c.sz)
            if c.solid(v, y, u)}


def _components(cells):
    from collections import deque
    seen, out = set(), []
    for start in cells:
        if start in seen:
            continue
        q, n = deque([start]), 0
        seen.add(start)
        while q:
            v, y, u = q.popleft()
            n += 1
            for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
                nb = (v + d[0], y + d[1], u + d[2])
                if nb in cells and nb not in seen:
                    seen.add(nb)
                    q.append(nb)
        out.append(n)
    return sorted(out, reverse=True)


@pytest.fixture(scope="module")
def built():
    return sauropod.build({"height": 34, "facing": "west", "ground": False, "seed": 3})


def test_every_material_is_cheap_legal_spendable_and_does_not_fall():
    """Rule 13 and rule 16 together: a landmark made of a gravity block pours into the void, and
    dirt is CURRENCY on this server."""
    for key, name in sauropod.HIDE.items():
        assert blocks.spendable(name), f"{key}={name} is currency here"
        assert not blocks.falls(name), f"{key}={name} falls"
        assert palette.tier(name) != "expensive", f"{key}={name} is expensive tier"


def test_the_coat_is_a_measured_hue_flip_from_the_canopy():
    """**A GREEN ANIMAL ON A GREEN PLATEAU IS THE GREEN-TURTLE MISTAKE.** The Lost Plateau's canopy
    is `jungle_leaves`; `brown_wool` sits 53 RGB from it and `gray_wool` 58 - both vanish. The
    flank has to be the tone that carries, and the three tones have to be a real ladder."""
    def rgb(n):
        return blocks.color(n, "side")

    def lum(n):
        r, g, b = rgb(n)
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    def dist(a, b):
        return sum((int(p) - int(q)) ** 2 for p, q in zip(rgb(a), rgb(b))) ** 0.5

    ladder = [lum(sauropod.HIDE[k]) for k in ("back", "flank", "belly")]
    steps = [b - a for a, b in zip(ladder, ladder[1:])]
    assert min(steps) >= 40, f"a rung nobody can see: {ladder}"
    assert dist(sauropod.HIDE["flank"], "jungle_leaves") >= 100, "the flank vanishes in the canopy"


def test_it_is_one_piece(built):
    """A swept limb whose cells are only diagonal neighbours is not connected - the ear tips of two
    different animals on this island broke off exactly that way."""
    comps = _components(_cells(built))
    assert len(comps) == 1, f"the animal is in {len(comps)} pieces: {comps[:5]}"


@pytest.mark.parametrize("facing", FACINGS)
def test_the_canvas_is_sized_by_the_facing(facing):
    """**THE BUG THIS CATCHES SHIPPED, AND ITS ONLY SYMPTOM WAS A NUMBER NOBODY READ.**

    The box was always long in X. Built facing north, the animal's length ran along Z and it was
    clipped to 22 blocks - head, neck and half the tail simply refused - while the render still
    showed a plausible small dinosaur. The frame maps forward and side onto the world; the box has
    to be mapped the same way or the two disagree.
    """
    c = sauropod.build({"height": 34, "facing": facing, "ground": False, "seed": 3})
    cells = _cells(c)
    vs = [p[0] for p in cells]
    us = [p[2] for p in cells]
    long_axis = max(max(vs) - min(vs), max(us) - min(us)) + 1
    short_axis = min(max(vs) - min(vs), max(us) - min(us)) + 1
    assert long_axis >= 44, f"{facing}: clipped to {long_axis} long"
    assert short_axis <= 14, f"{facing}: {short_axis} wide is not a sauropod"
    assert len(cells) > 2000, f"{facing}: only {len(cells)} cells survived"


@pytest.mark.parametrize("facing", ("north", "south", "east", "west"))
def test_the_length_runs_along_the_axis_the_facing_names(facing):
    """North and south run along U; east and west along V. Our renderer draws a facing and its
    opposite identically, so this is asserted rather than eyeballed."""
    c = sauropod.build({"height": 30, "facing": facing, "ground": False, "seed": 1})
    cells = _cells(c)
    span_v = max(p[0] for p in cells) - min(p[0] for p in cells)
    span_u = max(p[2] for p in cells) - min(p[2] for p in cells)
    if facing in ("east", "west"):
        assert span_v > span_u, f"{facing} should run along V, got V{span_v} U{span_u}"
    else:
        assert span_u > span_v, f"{facing} should run along U, got V{span_v} U{span_u}"


def test_the_coat_pass_actually_paints(built):
    """**A PROTECTION SET KEYED ON MATERIAL PROTECTS EVERY CELL MADE OF THAT MATERIAL.**

    The crest is `light_gray_wool` and so is the flank the whole animal is swept in, so "keep the
    crest" kept all 2,333 cells: the countershading ran, skipped everything, and returned a tally
    of four zeros. It is the same mistake as answering rule 15 with a material list, one level
    down - a set of things is not a set of cells - and the only symptom was a monochrome animal.
    """
    coat = built.meta["parts"]["coat"]
    total = sum(coat.values())
    assert total > 1800, f"the coat painted only {total} cells: {coat}"
    for band in ("back", "flank", "belly"):
        assert coat[band] > 200, f"no {band} at all: {coat}"
    assert coat["mark"] > 50, "the dorsal blotching never landed"


def test_the_head_keeps_its_eyes_and_its_crest(built):
    """An eye is a BEAD ON THE SURFACE and it is FOUND, not computed - a sweep moves the surface,
    so a bead at a calculated half-width either floats proud of the head or is buried inside it.
    Both have shipped on this island's animals."""
    head = built.meta["parts"]["head"]
    assert head["eyes"] == 2, f"a one-eyed sauropod: {head}"
    assert head["crest"] >= 10, f"no crest, so no brachiosaur: {head}"


def test_the_front_legs_are_longer_than_the_back(built):
    """**THE WHOLE PROFILE DEPENDS ON IT.** A level-backed sauropod is a log on legs; the
    brachiosaur's back falls away to the tail because its forelimbs are longer, and that diagonal
    plus the vertical neck is what you name the animal from at a quarter scale."""
    d = sauropod._dims(34)
    assert d["shoulder"] > d["hip"], "the back does not fall away"
    assert d["shoulder"] - d["hip"] >= 2.5, "the slope is too slight to read"


def test_the_neck_reaches_higher_than_anything_else(built):
    """It is the landmark; if the tail or the back is the tallest thing, it is not."""
    cells = _cells(built)
    top = max(p[1] for p in cells)
    d = sauropod._dims(34)
    assert top >= d["head_y"], f"the crown is at {top}, under the head line {d['head_y']:.0f}"


def test_it_refuses_a_size_it_cannot_carry():
    with pytest.raises(ValueError):
        sauropod.build({"height": 12, "facing": "west", "ground": False})
    with pytest.raises(ValueError):
        sauropod.build({"height": 34, "facing": "up", "ground": False})


def test_the_shipped_config_stands_on_the_rim_and_inside_the_park():
    """The land had no other site and that is measured - the largest clear rectangle anywhere else
    in the Frontier is 6 x 49 against an animal 48 x 11."""
    with open(CONFIG, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    p = cfg["params"]
    v, u = p["at"]
    assert p["facing"] in ("north", "south"), (
        "the rim band is 13 rows deep and the animal is 48 long, so its length must run along U")
    c = sauropod.build({**p, "ground": False})
    cells = _cells(c)
    lo_v = v - (c.sx // 2 - min(p2[0] for p2 in cells))
    hi_v = v + (max(p2[0] for p2 in cells) - c.sx // 2)
    assert 187 <= lo_v and hi_v <= 199, f"the animal spans V{lo_v}-{hi_v}, outside the rim band"
    assert 0 <= lo_v and hi_v <= 199, "off the plot"
