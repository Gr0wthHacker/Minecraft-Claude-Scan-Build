"""The nav fixture: the island's own geometry, handed to the Java routing tests.

The Java side reads this with twenty lines of bit-shifting and no library, so the two halves agree
only as long as the format does. These pin the format and the solidity model — not the numbers,
which move with every rescan.
"""

from __future__ import annotations

import gzip
import struct
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import export_navfixture as nf  # noqa: E402

FIXTURE = ROOT / "chunkscan" / "src" / "test" / "resources" / "island_nav.bin.gz"


def test_air_and_water_do_not_stop_you():
    assert not nf.blocks_motion("air")
    assert not nf.blocks_motion("minecraft:cave_air")
    assert not nf.blocks_motion("water")
    # ...and the things this island is draped in. `vine` reading as solid is the same class of bug
    # as the rim stair's `PASSABLE` set: a curtain hanging in open air is not footing, and it is not
    # a wall either.
    assert not nf.blocks_motion("vine")
    assert not nf.blocks_motion("glow_lichen")
    assert not nf.blocks_motion("torch")
    assert not nf.blocks_motion("rail")


def test_the_things_you_walk_into_do():
    for name in ("stone", "stone_bricks", "oak_slab", "stone_brick_stairs", "stone_brick_wall",
                 "oak_fence", "glass_pane", "chest", "hopper", "oak_leaves", "ice"):
        assert nf.blocks_motion(name), name


def test_a_block_state_is_read_by_its_name():
    # Work lists and palettes carry `name[facing=east,half=bottom]`; the model is per BLOCK.
    assert nf.blocks_motion("stone_brick_stairs[facing=east,half=bottom]")
    assert not nf.blocks_motion("vine[east=true,north=false]")


def test_an_unknown_block_is_assumed_to_be_in_the_way():
    # The safe direction: a router that refuses a route it could have flown beats one that flies a
    # route it could not.
    assert nf.blocks_motion("some_block_from_a_future_version")


def test_the_packing_round_trips():
    # Exactly the arithmetic the Java reader does: index = ((y * sz) + z) * sx + x, MSB first.
    solid = np.zeros((3, 4, 5), dtype=bool)          # [y][z][x]
    solid[2, 1, 4] = True
    solid[0, 0, 0] = True
    raw = nf.pack(solid, (-24251, 150, 29949))

    assert raw[:8] == nf.MAGIC
    ox, oy, oz, sx, sy, sz = struct.unpack(">6i", raw[8:32])
    assert (ox, oy, oz) == (-24251, 150, 29949)
    assert (sx, sy, sz) == (5, 3, 4)

    body = raw[32:]

    def bit(x, y, z):
        i = ((y * sz) + z) * sx + x
        return (body[i >> 3] >> (7 - (i & 7))) & 1

    assert bit(4, 2, 1) == 1
    assert bit(0, 0, 0) == 1
    assert bit(1, 1, 1) == 0
    assert bit(4, 2, 2) == 0


@pytest.mark.skipif(not FIXTURE.exists(), reason="fixture not exported yet")
def test_the_checked_in_fixture_is_an_island():
    # A fixture that decoded as an empty box would make every Java routing test pass over nothing,
    # which is the quiet way for a test suite to stop meaning anything.
    raw = gzip.decompress(FIXTURE.read_bytes())
    assert raw[:8] == nf.MAGIC
    _, _, _, sx, sy, sz = struct.unpack(">6i", raw[8:32])
    cells = sx * sy * sz
    solid = int(np.unpackbits(np.frombuffer(raw[32:], dtype=np.uint8))[:cells].sum())
    assert 0.005 < solid / cells < 0.5, f"{solid} of {cells} solid is not an island"
    assert sy > 100, "too short to hold the deck and the plate"
