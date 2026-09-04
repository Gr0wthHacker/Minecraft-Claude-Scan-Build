from __future__ import annotations
import numpy as np
from mcbuild import nbt, schem, symmetry


def test_intent_aware_symmetry_accepts_asymmetric_door_but_not_broken_core():
    ids = np.ones((3, 1, 5), dtype=np.int32); ids[1, 0, 0] = 2
    model = schem.Model(ids, [nbt.block_state("minecraft:air"), nbt.block_state("minecraft:stone"), nbt.block_state("minecraft:oak_door")])
    assert not symmetry.assess(model, min_core_match=1.0)["ok"]
    assert symmetry.assess(model, exceptions=[[0, 1, 0, 0, 1, 0]], min_core_match=1.0)["ok"]
