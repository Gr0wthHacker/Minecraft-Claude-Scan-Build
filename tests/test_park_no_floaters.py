"""NOTHING IN THE ASSEMBLED PARK HANGS IN THE AIR UNLESS A RIDE MEANT IT TO.

Jack, on the shipped composite: *"lots of floating lamp posts and random things arches etc that
arent part of prism or meant to be there."* Measured, he was right and the cause was one line of
`park_place.complete()`: `lay(honour_dig=)` skips a ground cell the dig NAMES, and a dig names the
PLATE COURSE, never the eight-course lamp standard bolted to it. Twelve of them hung over the
mouth of the Prism Well with 300 cells of moss carpet between them, and every check this repo owns
passed - legal states, clean economy, zero module clashes, a correct bill - because a lamp post
renders identically whether or not there is anything underneath it.

THE TEST IS OVER THE COMPOSITE, because that is the only artifact that knows all three digs. A
module cannot see this about itself: `Park Ways` paves and lamps a 200x600 plate and is entirely
right to, and `PF Prism Well` cuts a hundred-wide mouth through it and is entirely right to. The
fault only exists where they meet.

AND A RIDE IS ENTITLED TO FLOAT. `PF Crown Descent` is a parkour course whose whole vocabulary is
one-block ledges and slime pads hanging in the well's own shaft - so a sweep that judged the
composite as a whole would eat it and report a tidier number for having broken the thing the hole
is there for. What is asserted is the scoping, not just the count.
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter, deque

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcbuild import schem                                            # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMPOSITE = os.path.join(ROOT, "out", "Park Complete.litematic")
PLATE_Y = 202                       #: the park's own build plane, `park_place.ANCHOR[1]`

#: A MATERIAL LIST CANNOT ANSWER THIS AND THE FIRST VERSION OF THIS FILE TRIED. Naming the ground
#: layer's furniture by block flags `PF Prism Rig` - 476 iron bars and 260 copper of gantry that
#: hangs in the well on purpose, in the same blocks `Park Ways` builds a lamp cage out of. A
#: design's own cells are knowable exactly, because they are in its own litematic; that is the
#: rule `claimrow.shipped_cells` already states, met here from the other side.
GROUND = "Park Ways"


def _model():
    if not os.path.exists(COMPOSITE):
        pytest.skip("out/Park Complete.litematic not built - run tools/park_place.py --ship")
    side = COMPOSITE.replace(".litematic", ".scan.json")
    with open(side, encoding="utf-8") as fh:
        meta = json.load(fh)
    return schem.load(COMPOSITE), meta["origin"]


@pytest.fixture(scope="module")
def park():
    return _model()


def _plain(names, i):
    return names[i].split("[")[0].split(":")[-1]


def _airborne(ids, plane):
    """Every solid cell with no 6-connected path down to the plate - `park_place._unsupported`.

    Restated here rather than imported on purpose: a test that calls the code it is checking can
    only ever agree with it. What is shared is the RULE, and the rule is short enough to write out.

    IT FLOODS FROM THE PLATE AND EVERYTHING UNDER IT, not from the composite's own y0. This box
    reaches down to Y94 for the mine ride and the well's shaft, so seeding at index 0 seeds a
    course of empty sky and reports the entire park as airborne.
    """
    solid = ids > 0
    ny, nz, nx = solid.shape
    seen = np.zeros_like(solid)
    q = deque()
    for y, z, x in zip(*solid[:plane + 1].nonzero()):
        seen[y, z, x] = True
        q.append((int(y), int(z), int(x)))
    nb = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))
    while q:
        y, z, x = q.popleft()
        for dy, dz, dx in nb:
            a, b, c = y + dy, z + dz, x + dx
            if 0 <= a < ny and 0 <= b < nz and 0 <= c < nx and solid[a, b, c] and not seen[a, b, c]:
                seen[a, b, c] = True
                q.append((a, b, c))
    return solid & ~seen


def test_the_ground_layer_never_furnishes_a_hollow_column(park):
    """A dug column carries no lawn, no carpet and no lamp. This is the one Jack saw."""
    m, o = park
    src = os.path.join(ROOT, "out", f"{GROUND}.litematic")
    side = os.path.join(ROOT, "out", f"{GROUND}.scan.json")
    if not (os.path.exists(src) and os.path.exists(side)):
        pytest.skip(f"{GROUND} not built")
    g = schem.load(src)
    with open(side, encoding="utf-8") as fh:
        go = json.load(fh)["origin"]
    plate = PLATE_Y - o["y"]
    hollow = ~(m.ids[plate] > 0)
    bad = Counter()
    for a, b, c in zip(*np.nonzero(g.ids > 0)):
        y, z, x = int(a) + go["y"] - o["y"], int(b) + go["z"] - o["z"], int(c) + go["x"] - o["x"]
        if y <= plate or not (0 <= z < hollow.shape[0] and 0 <= x < hollow.shape[1]):
            continue
        if not (hollow[z, x] and m.ids[y, z, x]):
            continue
        # ...and it is still the GROUND'S cell. The layer is laid last and wins only what nobody
        # else took, so a cell holding a different block was contested away - `PF Prism Rig`'s
        # copper takes exactly one of these, and a gantry hanging in the well is what the well is
        # for. Comparing the block is what tells "my lamp survived" from "somebody else built here".
        if _plain(m.names, m.ids[y, z, x]) == _plain(g.names, g.ids[a, b, c]):
            bad[_plain(m.names, m.ids[y, z, x])] += 1
    assert not bad, f"{GROUND} furniture left standing over a dug column: {dict(bad)}"


def test_the_only_thing_left_hanging_is_the_parkour(park):
    """Everything airborne belongs to a design whose ride IS the hanging.

    The bound is a CEILING and not an equality: the descent is generated, so its ledge count moves
    when its own parameters do, and a test that pinned the number would fail on somebody else's
    correct change. What must not move is the KINDS - a froglight landing and a slime pad are the
    course; a lamp standard, a sign, a bell or a wall is somebody's build come loose.
    """
    m, o = park
    loose = _airborne(m.ids, PLATE_Y - o["y"])
    kinds = Counter(_plain(m.names, m.ids[a, b, c])
                    for a, b, c in zip(*np.nonzero(loose)))
    allowed = {"ochre_froglight", "slime_block", "stone_brick_wall", "stone_bricks",
               "mossy_stone_bricks",
               #: a vine clings to a SIDE face, so a strand whose wall went to another design
               #: reads as airborne and is that design's to re-anchor, not this sweep's to eat
               "vine"}
    strays = {k: v for k, v in kinds.items() if k not in allowed}
    assert not strays, f"airborne cells that are not a ride: {strays}"
    assert sum(kinds.values()) < 200, f"the airborne set has grown: {dict(kinds)}"


def test_the_parkour_ledges_survive_the_sweep(park):
    """...and the sweep did not quietly buy its number by breaking the descent."""
    m, o = park
    loose = _airborne(m.ids, PLATE_Y - o["y"])
    kinds = Counter(_plain(m.names, m.ids[a, b, c])
                    for a, b, c in zip(*np.nonzero(loose)))
    assert kinds["ochre_froglight"] >= 40, (
        "the Crown Descent's landings are gone - its ledges ARE froglights, so a sweep that "
        f"removes them removes the ride: {dict(kinds)}")
    assert kinds["slime_block"] >= 4, f"the descent's jump pads are gone: {dict(kinds)}"


def test_a_ceiling_bell_has_a_ceiling():
    """`PF Mine Works`' tipple bell hung at `ly + 1` with air above it and, once the line went,
    air below - one cell of free-floating bronze in a design reporting 0 problems."""
    p = os.path.join(ROOT, "out", "PF Mine Works.litematic")
    if not os.path.exists(p):
        pytest.skip("PF Mine Works not built")
    m = schem.load(p)
    for a, b, c in zip(*np.nonzero(m.ids > 0)):
        if _plain(m.names, m.ids[a, b, c]) != "bell":
            continue
        props = m.palette[int(m.ids[a, b, c])].value.get("Properties")
        att = props.value["attachment"].value if props and "attachment" in props.value else "floor"
        if att != "ceiling":
            continue
        assert a + 1 < m.ids.shape[0] and m.ids[a + 1, b, c], (
            f"a ceiling bell at local y{a} z{b} x{c} hangs from nothing")


def test_the_lookouts_deck_fittings_stand_on_the_deck():
    """`s` is the course a visitor STANDS IN, not the floor under them, and both fittings started
    at `s + 1` - a signed orientation board and a bell hovering off a 56-course tower."""
    p = os.path.join(ROOT, "out", "PF Vantage Frontier Lookout.litematic")
    if not os.path.exists(p):
        pytest.skip("PF Vantage Frontier Lookout not built")
    m = schem.load(p)
    solid = m.ids > 0
    ny, nz, nx = solid.shape
    seen = np.zeros_like(solid)
    q = deque()
    for y, z, x in zip(*solid[:1].nonzero()):
        seen[y, z, x] = True
        q.append((int(y), int(z), int(x)))
    nb = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))
    while q:
        y, z, x = q.popleft()
        for dy, dz, dx in nb:
            a, b, c = y + dy, z + dz, x + dx
            if 0 <= a < ny and 0 <= b < nz and 0 <= c < nx and solid[a, b, c] and not seen[a, b, c]:
                seen[a, b, c] = True
                q.append((a, b, c))
    stray = int((solid & ~seen).sum())
    assert stray == 0, f"{stray} cells of the lookout do not reach its own base course"
