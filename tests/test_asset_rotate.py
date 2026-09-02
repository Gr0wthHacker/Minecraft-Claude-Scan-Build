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
def test_the_skull_in_the_park_faces_the_midway():
    """WHICH WAY IT FACES IS A SITING DECISION AND IT IS PINNED HERE.

    The Prism Reach is U385-429, forty-five columns, and the full-resolution skull is 40 wide - so
    at 90 or 270 the module measures 54 across and does not fit at all. Only 0 and 180 are
    available, which means the face points ALONG the reach, and 180 turns it toward the Midway:
    the park's centre, and the busier of the two approaches. A visitor walking in from the Midway
    walks straight at the face; from Prismworks they arrive behind it, into the chamber.
    """
    import yaml
    cfg = ROOT / "out" / "park_final" / "configs" / "wyrm_s_crossing.yaml"
    if not cfg.exists():
        pytest.skip("the module config is not built here")
    c = yaml.safe_load(cfg.read_text(encoding="utf-8"))
    skull = [p for p in c["params"]["parts"]
             if str((p.get("params") or {}).get("source", "")).endswith("bone_ruins_skull.litematic")]
    assert skull, "the module no longer contains the bone skull"
    pr = skull[0]["params"]
    assert pr.get("rotate") == 180, "the skull must face the Midway approach"
    assert not pr.get("downscale") or int(pr["downscale"]) == 1, \
        "the skull must be FULL resolution - halving it turns every curve into a two-block step"
