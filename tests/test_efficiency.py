from __future__ import annotations
import numpy as np
from mcbuild import efficiency, nbt, schem


def test_efficiency_records_quality_cost_and_enforces_budget():
    model = schem.Model(np.array([[[1, 2]]], dtype=np.int32), [nbt.block_state("minecraft:air"), nbt.block_state("minecraft:stone"), nbt.block_state("minecraft:oak_planks")])
    report = efficiency.assess(model, 0.5, {"max_blocks": 2, "min_materials": 2})
    assert report["ok"] and report["blocks_per_second"] == 4.0
    assert not efficiency.assess(model, 2, {"max_seconds": 1})["ok"]
