"""The void ladybird, and the Canvas trap that nearly shipped it wrong.

A ladybird is here because its identity is a PATTERN on a convex dome - the category this medium
renders well - rather than compound volumetric muscle, which is the category eight mammals failed
in. Everything worth pinning is about the pattern being legible, not about proportion.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import pytest
from mcbuild import blocks, morph, palette
from mcbuild.gen import GENERATORS, ladybug
from mcbuild.gen.canvas import Canvas

CFG = {"scale": 1.0, "seed": 0}


def _solid(c):
    return c.to_model().ids > 0


def _labels(mask):
    r = morph.components(mask, conn=6)
    return r[0] if isinstance(r, (list, tuple)) else r


def test_canvas_solid_is_false_out_of_bounds():
    """`get` returns -1 outside the canvas so `get_name` can say OOB - and -1 is TRUTHY, so every
    `if c.get(x, y, z):` in a generator reads everything beyond the edge as solid rock.

    That is not hypothetical. The ladybird searched downward for the top of its shell starting two
    courses above the canvas ceiling, "found" a block there every single time, and painted all
    seven spot caps into thin air above the beetle. The shell came out plain red, and the audit,
    the BOM and the component count all reported a clean build.
    """
    c = Canvas(4, 4, 4)
    c.put(1, 1, 1, c.state("stone"))
    assert c.solid(1, 1, 1)
    assert not c.solid(0, 0, 0)                  # in bounds, empty
    assert not c.solid(99, 99, 99)               # out of bounds - the whole point
    assert not c.solid(-1, 1, 1)
    assert c.get(99, 99, 99) == -1, "get must keep signalling OOB for get_name"
    assert bool(c.get(99, 99, 99)) is True, "...and that -1 is truthy is exactly the trap"


def test_it_is_registered_and_builds():
    assert "ladybug" in GENERATORS
    c = GENERATORS["ladybug"].build(CFG, None)
    assert _solid(c).sum() > 800


def test_one_connected_piece():
    """A design in pieces cannot be built. The clod alone came out as eighteen separate one-wide
    towers when its centre landed on x.5 - round() is banker's rounding, so round(11.5) and
    round(12.5) are both 12 and every other column of the lump was skipped."""
    c = GENERATORS["ladybug"].build(CFG, None)
    sizes = np.bincount(_labels(_solid(c)).ravel())[1:]
    assert (sizes > 0).sum() == 1, f"{(sizes > 0).sum()} pieces: {sorted(sizes[sizes > 0])[-5:]}"


def test_all_seven_spots_land_on_the_shell():
    """Seven is the species. A spot whose column has no shell under it is not drawn at all, and
    the rear pair fell off the edge for exactly that reason - their z offset was a fraction of the
    shell's WIDEST half-width, taken at a point where the dome had already tapered past it."""
    c = GENERATORS["ladybug"].build(CFG, None)
    assert c.meta["features_built"]["spots"] == 7


def test_the_spots_do_not_swallow_the_shell():
    """At radius 2.4 the seven caps overlapped into one black mass with red showing through as
    veins - a black beetle. The elytra has to stay mostly RED, which is the one thing a ladybird
    cannot be without."""
    c = GENERATORS["ladybug"].build(CFG, None)
    ids = c.to_model().ids
    names = {i: c.palette[i].value["Name"].value.split(":")[-1] for i in np.unique(ids) if i}
    red = sum(int((ids == i).sum()) for i, n in names.items() if n == "red_wool")
    black = sum(int((ids == i).sum()) for i, n in names.items() if n == "black_wool")
    assert red > black * 1.5, f"red {red} vs black {black}: that is a black beetle"


def test_the_leaf_stays_visible_past_the_beetle():
    """The leaf is the SCALE REFERENCE, not decoration - a red dome alone in the void is an object
    of unknown size. The first build had a 26-long leaf under a 17-long beetle and all that showed
    was a green fringe."""
    p = ladybug.LADYBUG
    assert p["leaf_l"] >= p["shell_l"] * 1.3, "the blade cannot read past the beetle"
    assert p["leaf_w"] >= p["shell_w"] * 1.3
    c = GENERATORS["ladybug"].build(CFG, None)
    ids = c.to_model().ids
    blade = c.state("lime_wool")
    shell = c.state("red_wool")
    bx = np.nonzero((ids == shell).any(axis=(0, 1)))[0]
    lx = np.nonzero((ids == blade).any(axis=(0, 1)))[0]
    bz = np.nonzero((ids == shell).any(axis=(0, 2)))[0]
    lz = np.nonzero((ids == blade).any(axis=(0, 2)))[0]
    # The beetle stands near the leaf's BASE with the blade sweeping out ahead of it, which is how
    # a ladybird actually sits and which shows the leaf's whole taper. So what has to be true is
    # that the blade reads AROUND and AHEAD of it - not that some arbitrary margin trails behind.
    assert lx.max() >= bx.max() + 4, "the blade and its point must run out past the head"
    assert lz.min() <= bz.min() - 2 and lz.max() >= bz.max() + 2, "the beetle overhangs the blade"


def test_nothing_falls_and_nothing_is_currency():
    """It hangs in OPEN VOID. A gravity block would pour the design into the abyss, and dirt in
    every form is money on this server - the lion once shipped with a coat of 5,173 dirt."""
    for k, v in ladybug.LADYBUG.items():
        for name in ([v] if isinstance(v, str) else v if isinstance(v, list) else []):
            if not isinstance(name, str) or name in ("vine",) or "/" in name:
                continue
            full = "minecraft:" + name
            if not blocks.exists(full):
                continue
            assert not blocks.falls(full), f"{k}={name} is a gravity block over open void"
            assert blocks.spendable(full), f"{k}={name} is CURRENCY on this server"
            assert palette.tier(full) == "cheap", f"{k}={name} is not cheap tier"
