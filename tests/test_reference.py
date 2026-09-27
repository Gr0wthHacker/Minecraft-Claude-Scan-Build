"""Large-reference inspection stays metadata-only and preserves scale evidence."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcbuild import nbt, reference, schem


def test_inspector_reads_region_dimensions_without_dense_load(tmp_path):
    model = schem.Model(
        np.zeros((3, 5, 4), np.int32),
        [nbt.block_state("minecraft:air"), nbt.block_state("minecraft:stone")],
    )
    model.ids[:, :, :] = 1
    path = tmp_path / "reference.litematic"
    schem.save(str(path), model, name="reference")

    report = reference.inspect_litematic(str(path))

    assert report.envelope_volume == 60
    assert len(report.regions) == 1
    region = report.regions[0]
    assert region.size == (4, 3, 5)
    assert region.palette_states == 2
