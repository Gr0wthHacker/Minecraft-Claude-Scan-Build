"""THE SKY OVER THE MIDWAY - the fair's airship and the display over the wheel."""
import json
import os
from collections import Counter, deque

import numpy as np
import pytest
import yaml

from mcbuild import scan
from mcbuild.nbt import state_name

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = os.path.join(ROOT, "configs", "pf_midway_skies.yaml")
OUT = os.path.join(ROOT, "out", "PF Midway Skies.litematic")
LAND = os.path.join(ROOT, "out", "midway_sky_ctx.litematic")


def _params():
    with open(CFG, encoding="utf-8") as fh:
        return yaml.safe_load(fh)["params"]


def _meta():
    with open(os.path.splitext(OUT)[0] + ".scan.json", encoding="utf-8") as fh:
        return json.load(fh)


def _cells():
    s = scan.load(OUT)
    ox, oy, oz = s.origin
    m = s.model
    names = [state_name(t).split(":")[-1] for t in m.palette]
    ys, zs, xs = np.nonzero(m.solid())
    ids = m.ids[ys, zs, xs]
    return {(x, y, z): names[i] for x, y, z, i in
            zip((xs + ox).tolist(), (ys + oy).tolist(), (zs + oz).tolist(), ids.tolist())}, s


def _pieces(model):
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


@pytest.mark.skipif(not os.path.exists(OUT), reason="PF Midway Skies is not shipped")
def test_the_airship_and_every_burst_is_ITS_OWN_WHOLE_PIECE():
    """**DISCONNECTED IS THE DESIGN, so the usual contract is backwards**, and what has to be true
    is that each piece is WHOLE. The gondola shipped as a 199-cell island under its own airship
    once: its struts were a fixed height and the hull's underside is a course higher at the flanks
    than it is on the centreline, because a hull is a sphere."""
    s = scan.load(OUT)
    pieces = _pieces(s.model)
    want = 1 + len(_params()["bursts"])
    assert len(pieces) == want, (
        f"{len(pieces)} pieces, wanted {want} (the airship and {want - 1} bursts): "
        f"{[len(p) for p in pieces]}")
    assert min(len(p) for p in pieces) > 90, "something has come away"
    assert len(pieces[0]) > max(len(p) for p in pieces[1:]), (
        "the airship should be the biggest piece")


@pytest.mark.skipif(not os.path.exists(OUT), reason="PF Midway Skies is not shipped")
def test_the_airship_has_EVERY_PART_and_reads_as_the_FAIR_S():
    """A build with a part missing is still one piece with a clean audit and a correct BOM, so the
    counts are CHANGED cells - the only measure that reads 0 for a part that did not happen and
    non-zero for one that is only PAINT."""
    parts = _meta()["parts"]
    for k in ("hull", "paint", "fins", "car", "pods"):
        assert parts.get("ship " + k, 0) > 0, f"the airship has no {k}: {parts}"
    assert parts["ship clipped"] == 0, "the airship is clipped by the canvas"

    cells, _ = _cells()
    hull = Counter(b for b in cells.values() if b.endswith("_wool"))
    total = sum(hull.values())
    plain = hull.get("white_wool", 0)
    assert plain < 0.55 * total, (
        f"the airship is {100 * plain / total:.0f}% plain white - five one-cell rings round a "
        f"fifty-six block hull is not a livery, and a band seen end-on is a band nobody sees")
    assert hull.get("red_wool", 0) > 300, "the fair's own red is missing from the livery"


@pytest.mark.skipif(not os.path.exists(OUT), reason="PF Midway Skies is not shipped")
def test_a_burst_is_RADIAL_and_its_spokes_reach_in_every_direction():
    """**A BURST WITH A BALD PATCH READS AS A DEAD SPIDER.** Hashed per spoke the directions clump;
    a Fibonacci sphere spaces them by construction, and what this pins is the OUTCOME - that the
    spokes are spread over the whole sphere rather than that a particular formula was used."""
    cells, _ = _cells()
    for i, spec in enumerate(_params()["bursts"]):
        ax = 97500 + int(spec["at"][0])
        az = 80470 + int(spec["at"][1])
        y0 = int(spec["y"])
        rad = float(spec["r"])
        near = [p for p in cells if abs(p[0] - ax) <= rad + 3 and abs(p[2] - az) <= rad + 3
                and abs(p[1] - y0) <= rad + 3]
        assert near, f"burst {i + 1} placed nothing at {ax},{y0},{az}"
        # every octant of the sphere carries something
        octs = {(p[0] >= ax, p[1] >= y0, p[2] >= az) for p in near}
        assert len(octs) == 8, f"burst {i + 1} only reaches {len(octs)} of 8 octants"
        # ...and it is SPOKES, not a ball: most of its bounding sphere is empty
        vol = (4 / 3) * 3.14159 * rad ** 3
        assert len(near) < 0.12 * vol, (
            f"burst {i + 1} is {len(near)} cells in a sphere of {vol:.0f} - that is a ball, "
            f"not a burst")
        # the tips are the bright end of the ladder
        far = [p for p in near if max(abs(p[0] - ax), abs(p[1] - y0), abs(p[2] - az)) >= rad * 0.75]
        assert far, f"burst {i + 1} has no spoke reaching its own radius"


@pytest.mark.skipif(not (os.path.exists(OUT) and os.path.exists(LAND)),
                    reason="the design or the land context is not shipped")
def test_NOTHING_IN_THE_SKY_TOUCHES_THE_LAND_OR_THE_WHEEL():
    """A capture cannot say so - it holds only what is BUILT - so the context is a cut of `Park
    Complete`, which is the park's DESIGN. That distinction is the fault the canopy walk shipped
    with: it reported overlap 0 honestly against a coaster that is 62% placed."""
    cells, s = _cells()
    mine = set(cells)
    w = scan.load(LAND)
    wx, wy, wz = w.origin
    wys, wzs, wxs = np.nonzero(w.model.solid())
    land = set(zip((wxs + wx).tolist(), (wys + wy).tolist(), (wzs + wz).tolist()))
    hit = sorted(mine & land)
    assert not hit, f"{len(hit)} cells of the sky stand in the land, e.g. {hit[:4]}"
    lowest = min(p[1] for p in mine)
    tallest = max((y for (_x, y, _z) in land), default=0)
    assert lowest > tallest, (
        f"the sky starts at Y{lowest} and the land reaches Y{tallest} - these are meant to be "
        f"the first things in this land that are higher than the wheel")


@pytest.mark.skipif(not os.path.exists(OUT), reason="PF Midway Skies is not shipped")
def test_it_stays_under_the_BUILD_LIMIT_and_on_the_MIDWAY():
    s = scan.load(OUT)
    ox, oy, oz = s.origin
    ys, zs, xs = np.nonzero(s.model.solid())
    assert int((ys + oy).max()) <= 317, "past the build limit"
    assert 97500 <= int((xs + ox).min()) and int((xs + ox).max()) <= 97699, "off the land in X"
    assert 80470 <= int((zs + oz).min()) and int((zs + oz).max()) <= 80699, "off the land in Z"


@pytest.mark.skipif(not os.path.exists(OUT), reason="PF Midway Skies is not shipped")
def test_it_is_all_CHEAP_and_all_1_19():
    from mcbuild import blocks, palette
    s = scan.load(OUT)
    for t in s.model.palette:
        b = state_name(t).split(":")[-1].split("[")[0]
        if b == "air":
            continue
        assert palette.tier(b) in ("cheap", "ok"), f"{b} is {palette.tier(b)}"
        assert blocks.exists(b), b
