"""The pterosaur and the bone bed - the two halves of the Lost Plateau's dinosaur content.

Both are built ON this repo's central sculpture rule rather than against it: planar and columnar
against volumetric. A membrane hung from one finger is a sheet; a skeleton is nothing but sheets
and tapers. The failures pinned here are the ones that shipped: three separate joins that came
apart at some sizes and not others, a femur that landed in a guest walk, and a grid of stakes that
was silently refused because it looked for the floor of a trench under the lip of one.
"""
from __future__ import annotations

import os
from collections import deque

import pytest
import yaml

from mcbuild import blocks, palette
from mcbuild.gen import fossils, pterosaur

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(ROOT, "configs", "pf_pterosaur.yaml")
DIGGINGS = os.path.join(ROOT, "configs", "pf_frontier_diggings.yaml")


def _cells(c):
    return {(v, y, u) for v in range(c.sx) for y in range(c.sy) for u in range(c.sz)
            if c.solid(v, y, u)}


def _pieces(cells):
    seen, n = set(), 0
    for start in cells:
        if start in seen:
            continue
        n += 1
        q = deque([start])
        seen.add(start)
        while q:
            v, y, u = q.popleft()
            for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
                nb = (v + d[0], y + d[1], u + d[2])
                if nb in cells and nb not in seen:
                    seen.add(nb)
                    q.append(nb)
    return n


@pytest.fixture(scope="module")
def built():
    return pterosaur.build({"span": 38, "spread": 0.72, "facing": "west",
                            "perch_h": 10, "seed": 5})


# --------------------------------------------------------------------------- palette


@pytest.mark.parametrize("table", [pterosaur.HIDE, fossils.BONE])
def test_every_material_is_legal_spendable_and_not_expensive(table):
    """Rule 16 - real, on the 1.19 server, and still CURRENCY here are three different questions."""
    for key, name in table.items():
        assert blocks.spendable(name), f"{key}={name} is currency on this server"
        assert palette.tier(name) != "expensive", f"{key}={name} is expensive tier"


def test_the_membrane_is_dark_and_the_beak_is_pale():
    """**A WING IS A SILHOUETTE BEFORE IT IS ANYTHING ELSE**, and the only thing behind one is sky -
    so the sheet is dark. The head then has to read against the sheet, which is why the beak is the
    palest block on the animal and the crest is the one warm note."""
    def lum(n):
        r, g, b = blocks.color(n, "side")
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    assert lum(pterosaur.HIDE["wing"]) < 90, "the membrane is not dark enough to be an outline"
    assert lum(pterosaur.HIDE["beak"]) - lum(pterosaur.HIDE["wing"]) > 100, (
        "the head does not separate from the wing")


def test_the_bone_reads_against_the_trench_floor():
    """The contrast IS the exhibit. This repo has laid four separate greys on top of each other
    before it learned to measure across families."""
    def lum(n):
        r, g, b = blocks.color(n, "side")
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    assert lum(fossils.BONE["bone"]) - lum(fossils.BONE["floor"]) > 120


# --------------------------------------------------------------------------- the animal


def test_it_is_one_piece_at_every_size_and_facing():
    """**CHASING EACH ARITHMETIC CORNER DID NOT CONVERGE.** A head came apart at span 38 while 34
    and 40 were whole; both wingtips came apart at 30 and 46. A bug that passes the example you
    tried is the worst kind, so the contract is guaranteed by a final stitch rather than hoped for,
    and this sweeps every size and facing the design can be asked for.
    """
    for span in range(24, 49, 4):
        for facing in ("north", "south", "east", "west"):
            c = pterosaur.build({"span": span, "spread": 0.72, "facing": facing,
                                 "perch_h": 8, "seed": 5})
            assert _pieces(_cells(c)) == 1, f"span={span} facing={facing} is in pieces"


def test_the_stitch_is_a_safety_net_and_not_the_geometry(built):
    """A build needing twenty cells of stitching is a build whose geometry is wrong. The count is
    reported for exactly that reason, so the ceiling is asserted."""
    st = built.meta["parts"]["stitch"]
    assert st["bridged"] <= 6, f"the geometry is leaning on the stitch: {st}"


def test_the_span_is_the_span(built):
    """`span` is WINGTIP TO WINGTIP, which is the measurement anybody actually means."""
    cells = _cells(built)
    us = [p[2] for p in cells]
    assert abs((max(us) - min(us) + 1) - 38) <= 3


def test_the_crest_and_both_eyes_survive(built):
    """**THE CREST MUST BREAK THE OUTLINE OR IT DOES NOTHING** - the lion's mane taught this island
    that a feature inside the silhouette is not a feature, and half of what names a pteranodon is
    the crest."""
    head = built.meta["parts"]["head"]
    assert head["crest"] >= 8, f"no crest, so no pteranodon: {head}"
    assert head["eyes"] == 2, f"a one-eyed pterosaur: {head}"


def test_it_carries_its_own_perch(built):
    """The bat's recorded lesson. The obvious perch here - the Vantage Lookout - is measured and
    refused: its deck is 8 x 15 and this animal reaches eight cells past the park's boundary on
    it. A crag means the design is self-contained."""
    crag = built.meta["parts"]["crag"]
    assert crag["cells"] > 100 and crag["height"] >= 6
    assert built.meta["parts"]["feet"] > 0, "nothing grips the rock"


def test_a_span_too_small_to_hold_a_membrane_raises():
    with pytest.raises(ValueError):
        pterosaur.build({"span": 10})
    with pytest.raises(ValueError):
        pterosaur.build({"span": 34, "facing": "up"})


def test_spread_changes_the_shape_rather_than_only_the_size():
    """**HALF-SPREAD BEATS SPREAD**, measured on the bat: fully spread a wing is one flat plate.
    The two builds must genuinely differ in profile, not just in cell count."""
    a = pterosaur.build({"span": 38, "spread": 0.72, "facing": "west", "perch_h": 8, "seed": 5})
    b = pterosaur.build({"span": 38, "spread": 1.0, "facing": "west", "perch_h": 8, "seed": 5})
    # measured on the WING TIP, not on the whole animal: the crest is the tallest thing on it
    # either way, so the animal's own height says nothing about how the wing is held.
    ta = a.meta["parts"]["wings"][0]["tip"][2]
    tb = b.meta["parts"]["wings"][0]["tip"][2]
    assert ta > tb + 1, f"a half-spread wing is held UP; flat it is a plate ({ta} vs {tb})"


# --------------------------------------------------------------------------- the bone bed


@pytest.fixture(scope="module")
def dig():
    from mcbuild.gen import diggings
    with open(DIGGINGS, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    return diggings.build(cfg["params"]), cfg


def test_the_skeleton_is_a_skeleton(dig):
    """Spine, rib cage, girdles, skull. **A RIB CAGE HANGS BETWEEN TWO GIRDLES** - without them it
    is a fan of loose curves rather than one animal."""
    canvas, _cfg = dig
    bed = canvas.meta["parts"]["bone_bed"]
    sk = bed["skeleton"]
    assert sk["spine"]["vertebrae"] >= 10, f"too few vertebrae to read as a spine: {sk['spine']}"
    assert sk["ribs"]["pairs"] >= 6, f"a rib cage of {sk['ribs']['pairs']} pairs is not a cage"
    assert sk["girdles"] > 20, "no pelvis or shoulder, so the ribs hang between nothing"
    assert sk["skull"]["cells"] > 20, "no skull, which is the part a stranger looks for"


def test_the_dig_is_gridded_and_lit(dig):
    """**A STAKE STANDS ON THE BENCH, NOT ON THE TRENCH FLOOR.** The first build asked for a cell
    with the floor under it and nothing on top, which is true nowhere on a benched lip - every
    stake, crate and light was silently refused and the design shipped `stakes: 0`."""
    canvas, _cfg = dig
    f = canvas.meta["parts"]["bone_bed"]["furniture"]
    assert f["stakes"] >= 20, f"the grid is what says EXCAVATION: {f}"
    assert f["lights"] >= 2, f"an unlit trench: {f}"


def test_no_bone_leaves_the_trench(dig):
    """**A FEMUR LANDED IN THE TRAIL** - `bone_block at (16,1,21)`, in the one walk the whole block
    exists to carry. It is the fourth time this land has needed the rule that a way is stated and
    refused rather than remembered."""
    canvas, cfg = dig
    t = cfg["params"]["trench"]
    v0, u0, w, d = int(t["v"]), int(t["u"]), int(t["w"]), int(t["d"])
    bone = canvas.state(fossils.BONE["bone"])
    stray = [(v, y, u) for v in range(canvas.sx) for y in range(canvas.sy)
             for u in range(canvas.sz)
             if canvas.get(v, y, u) == bone
             and not (v0 <= v < v0 + w and u0 <= u < u0 + d)]
    assert not stray, f"{len(stray)} bone cell(s) outside the trench: {stray[:6]}"
