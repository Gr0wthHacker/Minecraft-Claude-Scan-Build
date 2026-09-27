"""The Island Run: a parkour course is only a course if every move is makeable AND hard.

THE FIRST VERSION WAS A STAIRCASE and Jack said so: 3x3 landings four blocks apart with a
two-course drop every time - no failure mode, no variety, no jump pads. So these tests assert
BOTH halves. Legality alone is what produced the staircase; the difficulty assertions are what
stop it coming back.

  * every ledge is a ONE-BLOCK landing, so a miss is a miss
  * a real share of the jumps sit at full sprint distance
  * the plunges vary, or you learn the timing once and repeat it
  * every plunge lands on SLIME, which cancels all fall damage - that is the jump pad
  * nothing goes off the PLOT, which is found from the island's bedrock and is 99x99. The
    first build guarded against the 103x103 CAPTURE box and shipped 120 cells over the line.
"""
import collections
import json
import math
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcbuild import plot as plotmod                  # noqa: E402
from mcbuild import schem, scan                      # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FULL = os.path.join(ROOT, "out", "island_full.litematic")
WORK = os.path.join(ROOT, "out", "Island Run.work.json")
SIDE = os.path.join(ROOT, "out", "Island Run.scan.json")

needs = pytest.mark.skipif(not (os.path.exists(FULL) and os.path.exists(WORK)),
                           reason="needs the capture and the generated run")
AIRY = ("air", "cave_air", "void_air")


def _route():
    return [tuple(c) for c in json.load(open(SIDE, encoding="utf-8"))["route"]]


def _cells():
    return json.load(open(WORK, encoding="utf-8"))["cells"]


def _hops():
    r = _route()
    for a, b in zip(r, r[1:]):
        yield a, b, math.dist((a[0], a[2]), (b[0], b[2])), a[1] - b[1], b[3]


@needs
def test_every_move_is_physically_makeable():
    """A jump nobody can make is worse than no route: it reads as finished."""
    for a, b, gap, drop, kind in _hops():
        if kind == "plunge":
            assert 6 <= drop <= 16, f"plunge {a}->{b} drops {drop}"
            assert gap <= 5.75, f"plunge {a}->{b} is {gap:.1f} across"
        else:
            assert 0 <= drop <= 3, f"{kind} {a}->{b} drops {drop} - that costs health"
            assert gap <= 4.85, f"{kind} {a}->{b} is {gap:.1f} across; a sprint jump is 4.5"
        assert gap >= 2.0, f"{kind} {a}->{b} is {gap:.1f} - a step, not a jump"


@needs
def test_it_is_actually_hard():
    """The assertion that stops the staircase coming back. A course whose jumps are all short
    is a ramp, so a real share of them must sit at full sprint distance."""
    gaps = [g for _a, _b, g, _d, k in _hops() if k != "plunge"]
    assert gaps, "no ledge jumps at all"
    longs = sum(1 for g in gaps if g >= 4.0)
    assert longs / len(gaps) > 0.25, (
        f"only {100*longs/len(gaps):.0f}% of jumps are at sprint distance - this is a staircase")
    assert max(gaps) >= 4.4, f"the longest jump is {max(gaps):.1f}; nothing here is a stretch"


@needs
def test_a_ledge_is_one_block_so_a_miss_is_a_miss():
    """3x3 landings are what made the first version forgiving to the point of pointlessness."""
    cells = _cells()
    at = {(c[0], c[1], c[2]) for c in cells}
    rests = {(x, y, z) for x, y, z, k in _route() if k == "rest"}
    for x, y, z, kind in _route():
        if kind in ("rest", "plunge"):
            continue
        neigh = sum(1 for dx in (-1, 0, 1) for dz in (-1, 0, 1)
                    if (dx or dz) and (x + dx, y, z + dz) in at)
        assert neigh == 0, f"the {kind} at {(x, y, z)} has {neigh} neighbours - it is a platform"
    assert rests, "no checkpoints at all"


@needs
def test_every_plunge_lands_on_a_jump_pad():
    """Slime cancels all fall damage and bounces you. It is the reason a plunge is legal."""
    slime = {(c[0], c[1], c[2]) for c in _cells() if c[3].split("[")[0] == "slime_block"}
    plunges = [(x, y, z) for x, y, z, k in _route() if k == "plunge"]
    assert len(plunges) >= 8, f"only {len(plunges)} jump pads on the whole descent"
    for pcell in plunges:
        assert pcell in slime, f"the plunge at {pcell} has no slime under it"


@needs
def test_the_plunges_vary():
    """Every plunge the same depth teaches the timing once and then repeats it."""
    drops = [d for _a, _b, _g, d, k in _hops() if k == "plunge"]
    assert len(set(drops)) >= 3, f"plunge depths are {sorted(set(drops))} - no variety"


@needs
def test_nothing_leaves_the_plot():
    """The plot is 99x99, found from the island's bedrock. The first build checked the CAPTURE
    box - two blocks wider on every side - and put 120 cells over the line."""
    pl = plotmod.find(FULL)
    assert pl.radius == 49
    off = pl.outside(_cells())
    assert not off, f"{len(off)} cells outside {pl}, e.g. {off[:3]}"


@needs
def test_it_winds_around_and_reaches_the_bottom():
    r = _route()
    pl = plotmod.find(FULL)
    angs = [math.degrees(math.atan2(z - pl.cz, x - pl.cx)) % 360 for x, _y, z, _k in r]
    sweep = 0.0
    for a, b in zip(angs, angs[1:]):
        sweep += (b - a + 540) % 360 - 180
    assert abs(sweep) > 300, f"only {abs(sweep):.0f} degrees swept"
    assert r[0][1] - r[-1][1] > 130, "it does not descend the island"


@needs
def test_it_is_additive_and_touches_nothing_standing():
    cap = schem.load(FULL)
    sc = scan.load(FULL.replace(".litematic", ".scan.json"))
    o = sc.meta["origin"]
    pal = [n.split(":")[-1].split("[")[0] for n in cap.names]
    for x, y, z, b in _cells():
        iy, iz, ix = y - o["y"], z - o["z"], x - o["x"]
        if not (0 <= iy < cap.ids.shape[0] and 0 <= iz < cap.ids.shape[1]
                and 0 <= ix < cap.ids.shape[2]):
            continue
        here = pal[cap.ids[iy, iz, ix]]
        assert here in AIRY, f"{b} at {(x, y, z)} would replace {here}"
