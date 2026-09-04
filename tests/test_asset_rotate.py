"""An outside build arrives facing wherever its author left it, and turning it must turn its STATES.

Jack, on the bone skull placed in the Prism Reach: "its still facing a weird way and is more flat
than original, i think it can be slightly more rounded/circular."

It was not flat. Measured, the built skull carries the same 38,235 cells as the reference and only
its palette differs (concrete and dirt are not spendable on this server). What a visitor was
getting was the PROFILE - and a skull seen edge-on is thin, which is exactly what reads as flat.
The face is round; it was pointing the wrong way, and `asset` had no way to turn anything.

THE ARRAY IS THE EASY HALF. The half that goes wrong silently is the block states: a stair, a
trapdoor, a wall sign, a lantern and an axis pillar all carry a direction, and rotating the cells
while leaving the states behind gives a build whose every stair leans the wrong way. **Our renderer
draws all of those identically whichever way they face**, so it is invisible in every sheet in this
repo and wrong in game for ever - which is why this is a test and not a look.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mcbuild import schem  # noqa: E402
from mcbuild.gen import asset  # noqa: E402

SOURCE = ROOT / "reference" / "bone_ruins_skull.litematic"


def _built(rotate: int):
    return asset.build({"source": str(SOURCE), "rotate": rotate})


@pytest.mark.skipif(not SOURCE.exists(), reason="the reference asset is not checked out here")
def test_a_turn_loses_no_blocks():
    """A rotation moves cells; it does not spend them. If a count moves, the array walk is wrong."""
    counts = {r: int((_built(r).ids > 0).sum()) for r in (0, 90, 180, 270)}
    assert len(set(counts.values())) == 1, f"a turn changed the block count: {counts}"


@pytest.mark.skipif(not SOURCE.exists(), reason="the reference asset is not checked out here")
def test_a_quarter_turn_swaps_the_footprint_and_a_half_turn_does_not():
    """The one property that says the array really turned rather than being copied."""
    base = _built(0).ids.shape
    assert _built(180).ids.shape == base
    sy, sz, sx = base
    assert _built(90).ids.shape == (sy, sx, sz)
    assert _built(270).ids.shape == (sy, sx, sz)


@pytest.mark.skipif(not SOURCE.exists(), reason="the reference asset is not checked out here")
def test_a_facing_turns_with_the_block_it_belongs_to():
    """EVERY directional state advances by the same quarter turns as the cells do.

    Asserted as a HISTOGRAM rather than per block: the set of facings in the model must be the
    original set with every member advanced, so a rotation that turned the array and forgot the
    palette shows up as an unchanged histogram against a changed shape.
    """
    cw = {"north": "east", "east": "south", "south": "west", "west": "north"}

    def facings(model_or_canvas):
        out = {}
        pal = model_or_canvas.palette if hasattr(model_or_canvas, "palette") else None
        for entry in pal[1:]:
            props = entry.value.get("Properties")
            if props is None:
                continue
            tag = props.value.get("facing")
            if tag is not None and tag.value in cw:
                out[tag.value] = out.get(tag.value, 0) + 1
        return out

    src = facings(schem.load(str(SOURCE)))
    if not src:
        pytest.skip("this reference carries no facing states to turn")
    got = facings(_built(90))
    want = {}
    for k, n in src.items():
        want[cw[k]] = want.get(cw[k], 0) + n
    assert got == want, f"facings did not turn with the blocks: {got} against {want}"


@pytest.mark.skipif(not SOURCE.exists(), reason="the reference asset is not checked out here")
def test_an_axis_pillar_lies_down_the_other_way_on_an_odd_turn():
    """A log, a bone block and basalt carry `axis` rather than `facing`; x and z swap on a quarter
    turn and y never moves. Left alone, every pillar in a turned build runs across its own grain."""
    def axes(c):
        out = {}
        for entry in c.palette[1:]:
            props = entry.value.get("Properties")
            if props is None:
                continue
            tag = props.value.get("axis")
            if tag is not None:
                out[tag.value] = out.get(tag.value, 0) + 1
        return out

    src, turned = axes(_built(0)), axes(_built(90))
    if not src:
        pytest.skip("this reference carries no axis pillars")
    assert src.get("y", 0) == turned.get("y", 0), "a vertical pillar must not move"
    assert src.get("x", 0) == turned.get("z", 0) and src.get("z", 0) == turned.get("x", 0)


@pytest.mark.skipif(not SOURCE.exists(), reason="the reference asset is not checked out here")
def test_the_open_mouth_skull_straddles_the_RAILWAY_and_faces_the_park():
    """The FULL-RESOLUTION skull is turned to face the park, straddles the rim railway, and is whole.

    THIS TEST HAS NOW BEEN REWRITTEN TWICE FOR THE SAME REASON, WHICH IS THE RULE: it pins a
    DECISION about where the skull stands, and when Jack changes that decision the test changes
    with it or the suite quietly enforces the arrangement he just replaced.

    * v1 asserted the full-resolution skull must NOT be used, from when it had been swapped for
      `bone_ruins.litematic` at downscale 3 because it shipped detached. Jack reversed that.
    * v2 asserted `rotate: 180` on `Wyrm's Crossing`, the paved crossing out on the Prism Reach
      causeway, so the face addressed the Midway approach along U.
    * v3 is this one. Jack: *"are we able to place the skull so that the mouth 'opens' around the
      railway, the back of the skeleton is towards the void and the mouth gap is where the railway
      passes through sideways"*. The mouth is a tunnel along the face's own normal, so a railway
      can only cross it SIDEWAYS - which needs the 54-wide axis along U and the 40-deep axis
      across V, and that is a quarter turn from where it stood. It is `configs/pf_wyrm_gate.yaml`
      now, on the line, and `Wyrm's Crossing` keeps the crossing and no longer carries a skull.

    What is asserted here is what has been asserted all along and is the reason this test exists:
    ONE PIECE, at full resolution, from the pruned export. Where it stands and which way it looks
    belong to `tests/test_wyrmgate.py`, which can measure them against the railway.
    """
    import yaml
    cfg = ROOT / "configs" / "pf_wyrm_gate.yaml"
    if not cfg.exists():
        pytest.skip("the gate config is not built here")
    p = yaml.safe_load(cfg.read_text(encoding="utf-8"))["params"]
    assert str(p["source"]).endswith("bone_ruins_skull.litematic"), "the skull is the asset"
    assert p.get("downscale") in (None, 1), "the skull is placed at full resolution"
    assert int(p.get("prune") or 0) >= 3,         "without a prune floor the export's own crop debris ships as floating lumps"

    # AND THE SKULL IS GONE FROM THE CROSSING, so it is not standing in two places at once.
    old = ROOT / "out" / "park_final" / "configs" / "wyrm_s_crossing.yaml"
    if old.exists():
        parts = yaml.safe_load(old.read_text(encoding="utf-8"))["params"]["parts"]
        assert not [q for q in parts if q.get("gen") == "asset"],             "Wyrm's Crossing still carries an asset - the skull would be built twice"

    # ...and the prune actually does it: one 6-connected piece, measured on the built asset.
    import numpy as np
    from mcbuild.gen import asset
    canvas = asset.build({"source": p["source"], "rotate": p["rotate"], "prune": p["prune"]})
    solid = canvas.ids > 0
    sy, sz, sx = solid.shape
    seen = np.zeros(solid.shape, bool)
    nb = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))
    sizes = []
    for start in map(tuple, np.argwhere(solid)):
        if seen[start]:
            continue
        stack, n = [start], 0
        seen[start] = True
        while stack:
            cy, cz, cx = stack.pop()
            n += 1
            for dy, dz, dx in nb:
                q = (cy + dy, cz + dz, cx + dx)
                if (0 <= q[0] < sy and 0 <= q[1] < sz and 0 <= q[2] < sx
                        and solid[q] and not seen[q]):
                    seen[q] = True
                    stack.append(q)
        sizes.append(n)
    assert len(sizes) == 1, f"the skull ships in {len(sizes)} pieces: {sorted(sizes)[-6:]}"
