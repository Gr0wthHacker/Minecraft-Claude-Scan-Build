"""The Island Run: a parkour descent is only a route if every hop is actually makeable.

The physics settled this design's shape before any of it was drawn. Steering a fall buys about
2.0 blocks of horizontal reach for a two-course drop and 5.0 for a thirteen-course one; one
turn of this island at r=52 is 320 blocks of travel, and there are 152 courses between the
plate rim and the lowland floor. A falling course on slime pads therefore winds about a QUARTER
of a turn before it runs out of island, and a jumping course of two-course drops winds a full
one in almost exactly the height available. That is why this is a jump course with no slime in
it anywhere.

Which makes the tests below the whole design, not decoration around it:

  * NO HOP MAY COST HEALTH. Fall damage is max(0, blocks - 3) half-hearts, so three courses is
    free and four is not, and a 77-hop run that bleeds you half a heart at a time is a run
    nobody finishes.
  * NO HOP MAY BE UNJUMPABLE, and none may be a hidden fall. The first build answered a failed
    site search by dropping two courses and swinging on WITHOUT placing a pad, which quietly
    put a 118-course drop in the middle of an otherwise finished-looking route.
  * EVERY PAD IS INSIDE THE CAPTURE. `Ctx.name_at` answers "air" for anything outside the
    scanned box, so the first build sited its opening pad a block past the scan's east edge -
    in space nobody has ever looked at. Out of the capture is not empty, it is unknown.
"""
import json
import math
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcbuild import schem, scan                      # noqa: E402
from mcbuild.gen.parkour import PARKOUR              # noqa: E402

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


@needs
def test_no_hop_costs_health():
    """Fall damage is max(0, blocks - 3) half-hearts. Three is free; four is not."""
    r = _route()
    assert len(r) > 40, f"only {len(r)} hops - the run does not reach the bottom"
    for a, b in zip(r, r[1:]):
        drop = a[1] - b[1]
        assert 0 < drop <= 3, f"hop {a} -> {b} drops {drop} courses"


@needs
def test_every_hop_is_jumpable_and_none_is_a_hidden_fall():
    """A route with an unreachable hop is worse than no route: it reads as finished."""
    r = _route()
    for a, b in zip(r, r[1:]):
        d = math.dist((a[0], a[2]), (b[0], b[2]))
        assert d <= PARKOUR["max_reach"] + 0.01, f"hop {a} -> {b} is {d:.1f} blocks"
        assert d >= 1.0, f"hop {a} -> {b} does not go anywhere"


@needs
def test_it_winds_around_the_island():
    """The brief was 'wind all the way around, all the way down'. Both halves are measurable."""
    r = _route()
    cx, cz = PARKOUR["centre"]
    angs = [math.degrees(math.atan2(z - cz, x - cx)) % 360 for x, _y, z in r]
    sweep = 0.0
    for a, b in zip(angs, angs[1:]):
        sweep += (b - a + 540) % 360 - 180
    assert abs(sweep) > 270, f"only {abs(sweep):.0f} degrees swept - it does not wind around"
    assert r[0][1] - r[-1][1] > 130, "it does not descend the island"


@needs
def test_every_pad_is_inside_the_capture():
    """Out of the capture is not empty, it is UNKNOWN - and name_at answers 'air' out there."""
    sc = scan.load(FULL.replace(".litematic", ".scan.json"))
    cap = schem.load(FULL)
    o = sc.meta["origin"]
    sy, sz, sx = cap.ids.shape
    for x, y, z, _b in _cells():
        assert o["x"] <= x < o["x"] + sx, f"pad cell at x={x} is outside the scan"
        assert o["y"] <= y < o["y"] + sy, f"pad cell at y={y} is outside the scan"
        assert o["z"] <= z < o["z"] + sz, f"pad cell at z={z} is outside the scan"


@needs
def test_it_is_additive_and_touches_nothing():
    """The run hangs in open void. A pad grafted onto the giraffe is not a stepping stone."""
    cap = schem.load(FULL)
    sc = scan.load(FULL.replace(".litematic", ".scan.json"))
    o = sc.meta["origin"]
    pal = [n.split(":")[-1].split("[")[0] for n in cap.names]

    def at(x, y, z):
        iy, iz, ix = y - o["y"], z - o["z"], x - o["x"]
        if not (0 <= iy < cap.ids.shape[0] and 0 <= iz < cap.ids.shape[1]
                and 0 <= ix < cap.ids.shape[2]):
            return "OOB"
        return pal[cap.ids[iy, iz, ix]]
    for x, y, z, b in _cells():
        assert at(x, y, z) in AIRY, f"{b} at {(x, y, z)} would replace {at(x, y, z)}"


@needs
def test_every_pad_carries_its_own_light():
    """A pad is a new walkable surface hanging in the void. Unlit, this design would be 77 new
    places for a mob to stand and the night pass would have to grow by 77 fixtures."""
    route = _route()
    lights = {(x, y, z) for x, y, z, b in _cells()
              if b.split("[")[0] == PARKOUR["light"]}
    assert len(lights) >= len(route), (
        f"{len(lights)} lights for {len(route)} pads")
    for (x, y, z) in route:
        assert (x, y, z) in lights, f"the pad at {(x, y, z)} has no light in it"
