"""Weathering drifts, and the gate that is the whole difference between weather and spatter.

The corpus finding this implements: their sculptures carry 18.5% of their cells in accents beyond
the top three blocks against our 5.8%, and those accents are NOT a light model - luminance
correlates with ambient occlusion at r=-0.15 on their best statue. The clearest case is the
`Ancient knight statue`: 829 cells of `moss_block` at +11 luminance from the body (no tonal
contribution at all) on cells whose UP face is open 80% of the time against 4% for the down face.

Everything below pins a property that a block count cannot see. A confetti pass and a drift pass
place the same number of blocks, cost the same, and audit identically - the deck soffit shipped
exactly that and stood for a week.
"""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcbuild import tone                            # noqa: E402
from mcbuild.gen import accent                      # noqa: E402


@pytest.fixture
def slab():
    """A 20x8x20 solid block. Its top course is up-facing, its sides are not."""
    solid = np.zeros((8, 20, 20), bool)
    solid[:, 2:18, 2:18] = True
    return solid


def _surface(solid):
    pad = np.pad(solid, 1, constant_values=False)
    faces = ((~pad[2:, 1:-1, 1:-1]).astype(int) + (~pad[:-2, 1:-1, 1:-1]).astype(int) +
             (~pad[1:-1, 2:, 1:-1]).astype(int) + (~pad[1:-1, :-2, 1:-1]).astype(int) +
             (~pad[1:-1, 1:-1, 2:]).astype(int) + (~pad[1:-1, 1:-1, :-2]).astype(int))
    surf = solid & (faces > 0)
    return [(int(x), int(y), int(z)) for y, z, x in np.argwhere(surf)]


# ---------------------------------------------------------------- the gate

def test_drifts_not_confetti(slab):
    """THE GATE. The most repeated lesson in this project - the deck soffit drew 215 grid runs of
    which 184 were one or two cells ("it is not a grid, it is confetti"); the lowland thicket's
    first build was 191 blobs of which 75% were one or two cells."""
    over = accent.weather(_surface(slab), slab, "moss_block", seed=1, min_blob=8)
    sizes = accent.blob_sizes(over)
    assert sizes, "placed nothing"
    assert min(sizes) >= 8
    in_big = sum(s for s in sizes if s >= 8) / sum(sizes)
    assert in_big == 1.0


def test_without_the_gate_it_is_confetti(slab):
    """The control. If the ungated pass produced the same shape the gate would be decoration."""
    loose = accent.weather(_surface(slab), slab, "moss_block", seed=1, min_blob=1)
    sizes = accent.blob_sizes(loose)
    assert min(sizes) < 8, "nothing small was ever generated; the gate is untested"
    assert len(sizes) > len(accent.blob_sizes(
        accent.weather(_surface(slab), slab, "moss_block", seed=1, min_blob=8)))


def test_the_noise_is_on_the_boundary_not_the_interior(slab):
    """`edge_noise` must roughen the coastline, never spatter the middle. Raising it a long way
    must not shatter the patches - that is the difference between a threshold on a smooth field and
    a threshold on a per-cell hash."""
    cells = _surface(slab)
    calm = accent.weather(cells, slab, "moss_block", seed=2, edge_noise=0.0, min_blob=8)
    rough = accent.weather(cells, slab, "moss_block", seed=2, edge_noise=0.9, min_blob=8)
    assert accent.blob_sizes(calm) and accent.blob_sizes(rough)
    assert max(accent.blob_sizes(rough)) >= 0.4 * max(accent.blob_sizes(calm))


# ---------------------------------------------------------------- the driver

def test_weathering_lands_on_up_facing_cells(slab):
    """Not height, not occlusion. A statue's head is high and its underarm is high, and only one of
    them collects moss."""
    cells = _surface(slab)
    over = accent.weather(cells, slab, "moss_block", seed=1, up_bias=0.9, bleed=0.0)
    up = accent.up_open(slab)
    share = np.mean([up[y, z, x] for (x, y, z) in over])
    base = np.mean([up[y, z, x] for (x, y, z) in cells])
    assert share > 0.9
    assert share > base + 0.3, f"up-bias did nothing: {share:.2f} vs surface {base:.2f}"


def test_up_bias_zero_removes_the_weather(slab):
    """A control on the control: with the driver off, selection must fall back to the surface's own
    up-face share rather than staying high by accident."""
    cells = _surface(slab)
    over = accent.weather(cells, slab, "moss_block", seed=1, up_bias=0.0, bleed=0.0)
    up = accent.up_open(slab)
    share = np.mean([up[y, z, x] for (x, y, z) in over])
    base = np.mean([up[y, z, x] for (x, y, z) in cells])
    assert abs(share - base) < 0.25


def test_bleed_runs_a_drift_down_a_face(slab):
    """Without it a drift ends in a line along the topline, which is what the first render of the
    weathered elephant looked like in profile. The knight measures 4% down-face, so this is small."""
    cells = _surface(slab)
    up = accent.up_open(slab)
    dry = accent.weather(cells, slab, "moss_block", seed=1, bleed=0.0, min_blob=1)
    wet = accent.weather(cells, slab, "moss_block", seed=1, bleed=0.6, min_blob=1)
    side_dry = sum(1 for (x, y, z) in dry if not up[y, z, x])
    side_wet = sum(1 for (x, y, z) in wet if not up[y, z, x])
    assert side_wet > side_dry


# ---------------------------------------------------------------- contracts

def test_forbid_is_honoured(slab):
    """The face-zone rule, unchanged from the animal work: a pattern across a skull buries the eye
    among a dozen identical cells, and this repo shipped that once."""
    cells = _surface(slab)
    ban = set(cells[: len(cells) // 2])
    over = accent.weather(cells, slab, "moss_block", seed=1, forbid=ban, min_blob=1)
    assert not (set(over) & ban)


def test_it_never_places_into_air_or_off_the_model(slab):
    cells = _surface(slab) + [(999, 999, 999), (0, 0, 0)]
    over = accent.weather(cells, slab, "moss_block", seed=1, min_blob=1)
    for (x, y, z) in over:
        assert slab[y, z, x], f"placed at {(x, y, z)}, which is not solid"


def test_it_is_deterministic(slab):
    cells = _surface(slab)
    a = accent.weather(cells, slab, "moss_block", seed=7)
    b = accent.weather(cells, slab, "moss_block", seed=7)
    assert a == b
    assert accent.weather(cells, slab, "moss_block", seed=8) != a


def test_coverage_zero_places_nothing(slab):
    assert accent.weather(_surface(slab), slab, "moss_block", coverage=0.0) == {}


# ---------------------------------------------------------------- the material

def test_weathering_material_is_near_in_value():
    """The knight's moss is +11 from its body and contributes no tonal contrast at all. A block
    that also changes the value is doing shading's job, badly."""
    for base in ("stone", "stone_bricks"):
        mat = accent.weathering_for(base)
        assert mat, base
        d = abs(tone.luminance(mat) - tone.luminance(base))
        assert d <= accent.WEATHER_DLUM


def test_it_refuses_a_tonal_near_duplicate():
    """Nearest-in-chroma alone picked `light_gray_wool` for `stone` (drift 0.046), which is not
    weather - it is the same grey in another material."""
    assert accent.weathering_for("stone") != "light_gray_wool"
    assert accent.weathering_for("stone") == "mossy_stone_bricks"


def test_it_returns_none_rather_than_inventing_one():
    """Not every material has a weathered form in this economy. Inventing one is how `moss_block`
    ends up painted down a grey elephant's spine."""
    assert accent.weathering_for("deepslate") is None
    assert accent.weathering_for("not_a_real_block") is None


def test_ranked_offers_the_alternatives_nearest_first():
    ranked = accent.weathering_for("stone", ranked=True)
    assert ranked[0] == "mossy_stone_bricks"
    assert "mossy_cobblestone" in ranked


def test_prefer_wins_when_it_qualifies():
    assert accent.weathering_for("stone", prefer=("mossy_cobblestone",)) == "mossy_cobblestone"
    assert accent.weathering_for("stone", prefer=("obsidian",)) == "mossy_stone_bricks"
