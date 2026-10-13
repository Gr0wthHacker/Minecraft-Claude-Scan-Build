"""The sandworm in the spine's last plaza (mcbuild/gen/sandworm.py)."""
import numpy as np
import pytest
import yaml

from mcbuild.gen import sandworm

CONFIG = "configs/pf_sandworm.yaml"


def _p():
    return yaml.safe_load(open(CONFIG, encoding="utf-8"))["params"]


@pytest.fixture(scope="module")
def built():
    return sandworm.build(dict(_p()))


def test_it_is_one_connected_piece(built):
    ids = built.ids > 0
    seen = np.zeros_like(ids)
    start = tuple(np.argwhere(ids)[0])
    stack, n = [start], 0
    seen[start] = True
    while stack:
        q = stack.pop()
        n += 1
        for ax in range(3):
            for d in (-1, 1):
                r = list(q)
                r[ax] += d
                r = tuple(r)
                if all(0 <= r[i] < ids.shape[i] for i in range(3)) and ids[r] and not seen[r]:
                    seen[r] = True
                    stack.append(r)
    assert n == int(ids.sum())


def test_the_foot_is_on_the_plaza_centre(built):
    assert built.meta["foot"] == [97512, 202, 80343]
    ox, oy, oz = built.world_origin
    assert oy < 202                     # rooted below the paving


def test_it_towers_over_the_plaza(built):
    assert built.meta["height"] >= 45


def test_the_walk_round_the_foot_is_left_clear(built):
    # nothing of the worm stands in the plaza ring beyond r9 at walking height (courses 1-3)
    ox, oy, oz = built.world_origin
    ids = built.ids
    for y in (1, 2, 3):
        yy = 202 + y - oy
        for (z, x) in np.argwhere(ids[yy] > 0):
            r = np.hypot(ox + x - 97512, oz + z - 80343)
            assert r <= 9.2, (y, r)


def test_it_uses_only_spendable_blocks(built):
    from mcbuild import blocks
    names = {built.palette()[i] if callable(built.palette) else None for i in np.unique(built.ids) if i}
    assert not any("dirt" in str(n) or "mud" in str(n) for n in names)
