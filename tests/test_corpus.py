"""The corpus reader: what it measures, and the one distinction it must not blur.

Fixtures are built here rather than loaded, so the numbers are known by construction and no
downloaded file has to be checked in. The property that matters most is the DECIDED/DERIVED split:
a stair's `shape` and a wall's connections are computed by the game from the neighbourhood, and
counting them as technique invents work nobody has to do.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

import corpus                                    # noqa: E402
from mcbuild import nbt, schem                   # noqa: E402


def _build(tmp_path, name, fill):
    """`fill(ids, index_of)` paints an 8x8x8 model; returns a loaded corpus.Build."""
    ids = np.zeros((8, 8, 8), np.int32)
    palette = [nbt.block_state("minecraft:air")]
    idx = {}

    def index_of(bname, **props):
        key = (bname, tuple(sorted(props.items())))
        if key not in idx:
            palette.append(nbt.block_state(bname, **props))
            idx[key] = len(palette) - 1
        return idx[key]

    fill(ids, index_of)
    p = tmp_path / f"{name}.litematic"
    schem.save(str(p), schem.Model(ids, palette), name=name, author="test")
    return corpus.Build(p)


# ---------------------------------------------------------------- geometry

def test_a_solid_cube_is_mostly_interior_and_a_hollow_one_is_all_shell(tmp_path):
    """The number that separates the two disciplines with no judgement in it: their architecture
    runs 78-100% shell, their sculpture 20-45%."""
    solid = _build(tmp_path, "solid", lambda a, ix: a.__setitem__(
        (slice(1, 7), slice(1, 7), slice(1, 7)), ix("minecraft:stone")))
    # 6x6x6 = 216 cells, of which a 4x4x4 = 64 core is enclosed
    assert solid.total == 216
    assert round(solid.shell_pct()) == round(100 * (216 - 64) / 216)

    def hollow(a, ix):
        s = ix("minecraft:stone")
        a[1:7, 1:7, 1:7] = s
        a[2:6, 2:6, 2:6] = 0
    assert _build(tmp_path, "hollow", hollow).shell_pct() == 100.0


def test_the_bounding_box_counts_as_open_air(tmp_path):
    """A build cropped to its own content would read as more solid than it is if the box edge were
    treated as neighbouring rock. Every download arrives cropped."""
    full = _build(tmp_path, "full", lambda a, ix: a.__setitem__(
        (slice(None), slice(None), slice(None)), ix("minecraft:stone")))
    assert full.shell_pct() == 100 * (8 ** 3 - 6 ** 3) / 8 ** 3


def test_dims_are_of_the_content_not_the_region(tmp_path):
    b = _build(tmp_path, "corner", lambda a, ix: a.__setitem__(
        (slice(0, 2), slice(0, 3), slice(0, 4)), ix("minecraft:stone")))
    assert b.dims == (4, 2, 3)


# ---------------------------------------------------------------- detail

def test_detail_counts_the_non_cube_families(tmp_path):
    def mixed(a, ix):
        a[0, :, :] = ix("minecraft:stone")                       # 64 cubes
        a[1, 0, :] = ix("minecraft:stone_brick_slab", type="top")  # 8 slabs
    b = _build(tmp_path, "mixed", mixed)
    assert b.total == 72
    assert round(b.detail_pct(), 1) == round(100 * 8 / 72, 1)


# ---------------------------------------------------------------- states

def test_a_stairs_shape_is_reported_as_derived_not_as_technique():
    """CLAUDE.md settled this for `work.INTENTIONAL`: `shape` comes from what is beside the stair,
    connections from what a wall touches. Reading 190 corner stairs in a corpus as a decision sends
    someone off to implement resolution the game does for free."""
    for p in ("shape", "up", "north", "south", "east", "west", "waterlogged", "distance"):
        assert p in corpus.DERIVED, p


def test_the_properties_a_builder_actually_chooses_are_not_in_the_derived_set():
    for p in ("half", "type", "open", "facing", "axis", "persistent"):
        assert p not in corpus.DERIVED, p
        assert p in corpus.DECIDED, p


def test_states_are_split_and_weighted_by_cells(tmp_path):
    def flight(a, ix):
        a[0, 0, :4] = ix("minecraft:stone_brick_stairs",
                         facing="east", half="top", shape="inner_left", waterlogged="false")
    b = _build(tmp_path, "flight", flight)
    dec, der = b.states()
    assert dec["half=top"] == 4 and dec["facing=east"] == 4
    assert der["shape=inner_left"] == 4 and der["waterlogged=false"] == 4
    assert "shape=inner_left" not in dec and "half=top" not in der


def test_air_contributes_no_state(tmp_path):
    b = _build(tmp_path, "sparse", lambda a, ix: a.__setitem__((0, 0, 0), ix("minecraft:stone")))
    dec, der = b.states()
    assert sum(dec.values()) == 0 and sum(der.values()) == 0
    assert b.total == 1


# ---------------------------------------------------------------- palette

def test_tone_spread_is_weighted_by_cells_not_by_palette_length(tmp_path):
    """Forty blocks in a palette is not tonal variety if 90% of the cells are one of them - which
    is the difference between our sculptures and theirs, so the weighting is the measurement."""
    def lopsided(a, ix):
        a[:, :, :] = ix("minecraft:white_wool")
        a[0, 0, 0] = ix("minecraft:black_wool")
    dom, sd, rng = _build(tmp_path, "lopsided", lopsided).tone_spread()
    assert dom > 99
    assert rng > 200, "white to black is the full range"
    assert sd < 25, "one black cell in 512 must not read as tonal range"
