import json
from pathlib import Path
import pytest
from mcbuild import nbt, schem
import numpy as np
from tools import park_dressing as dressing
from tools.park_dressing_repairs import apply
from mcbuild.gen import park_frontage


def test_repair_refuses_a_changed_source(tmp_path):
    m = schem.Model(np.ones((1, 1, 1), dtype=np.int32),
                    [nbt.block_state('minecraft:air'), nbt.block_state('minecraft:stone')])
    p = tmp_path / 'repair.json'
    p.write_text(json.dumps([{'owner': 'land', 'world': [97500, 203, 80300],
                            'expected': ['minecraft:moss_block', []], 'replace': 'air'}]))
    with pytest.raises(ValueError, match='needs review'):
        apply([('land', 0, 0, m, 0)], p)
    assert int(m.ids[0, 0, 0]) == 1


def test_assembled_dressing_has_clear_routes_and_rooted_trees():
    p = dressing.Park()
    trees = dressing.trees(p)
    assert not dressing.in_street(p)
    assert not dressing.in_doorway(p)
    assert not dressing.not_rooted(p, trees)
    assert not dressing.unsupported(p, trees)
    assert all(lamp['lit'] for lamp in dressing.lamps(p))
    assert not dressing.damaged_lamp_masts(p)
    assert not dressing.buried_lights(p)


def test_single_bunting_bay_keeps_the_avenue_open():
    c = park_frontage.build({'land': 'midway', 'pieces': [
        {'kind': 'sight', 'motif': 'bunting', 'at': [58, 254],
         'facing': 'north', 'span': 1, 'step': 12, 'height': 8}]})
    assert c.meta['pieces'][0]['masts'] == 2
    ox, oy, oz = c.world_origin
    for y, z, x in zip(*(c.ids != 0).nonzero()):
        if 257 <= oz + z - 80300 <= 263:
            assert oy + y >= 209
