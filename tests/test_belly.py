"""belly generator: fits under a capture, never overlaps it, encases what hangs below the plate."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from mcbuild import nbt, scan, schem
from mcbuild.gen import belly

OUT = "out/_test"


def _capture(path):
    """14x9x14 box, world origin (1000, 100, 2000): plate at world y=106 (12x12), a 4x2x4 box hanging
    below it (y 102..103), and a 'walkway' sticking out past the plate edge at y=104."""
    m = schem.Model(np.zeros((9, 14, 14), np.int32),
                    [nbt.block_state("minecraft:air"), nbt.block_state("minecraft:cobblestone"),
                     nbt.block_state("minecraft:lime_wool"), nbt.block_state("minecraft:oak_planks")])
    m.ids[6, 1:13, 1:13] = 1                     # plate
    m.ids[2:4, 5:9, 5:9] = 2                     # hanging box under the plate
    m.ids[4, 7, 12:14] = 3                       # walkway leaving the plate footprint at the east edge
    os.makedirs(OUT, exist_ok=True)
    scan.save_pair(path, m, {"name": "t", "origin": {"x": 1000, "y": 100, "z": 2000}, "size": {"x": 14, "y": 9, "z": 14}})
    return m


def _hug(**over):
    _capture(f"{OUT}/cap_belly.litematic")
    cfg = {"under": f"{OUT}/cap_belly.litematic", "encase_below": 106, "depth_max": 6, "depth_min": 1,
           "ramp": 4, "wall": 1, "side_gap": 1, "min_fragment": 1, "min_plate_width": 1, "lanterns_out": 0,
           "lanterns_in": 0, "vine_rate": 0.0, **over}
    c = belly.build(cfg, [])
    m = c.to_model(); ox, oy, oz = c.world_origin
    def at(wx, wy, wz):
        y, z, x = wy - oy, wz - oz, wx - ox
        return int(m.ids[y, z, x]) if 0 <= y < m.ids.shape[0] else 0
    s = scan.load(f"{OUT}/cap_belly.litematic")
    assert scan.merge(s, m, c.world_origin)[1] == 0
    return at, oy


def test_hug_default_leaves_subplate_structures_bare():
    at, oy = _hug()
    assert any(at(1002, wy, 2002) > 0 for wy in range(oy, 106))     # rock under the plate where nothing hangs
    assert not any(at(1007, wy, 2007) > 0 for wy in range(oy, 106))  # nothing under the hanging box
    assert not any(at(1012, wy, 2007) > 0 for wy in range(oy, 106))  # nothing under the walkway (a bridge)
    for wy in (102, 103, 104, 105):                                  # and rock never rises beside the box
        assert at(1004, wy, 2007) == 0 and at(1009, wy, 2007) == 0


def test_hug_skin_puts_one_block_under_the_box():
    at, oy = _hug(sub_plate="skin", skin_depth=1, skin_boxes=[[1005, 2005, 1008, 2008]])
    assert at(1007, 101, 2007) > 0 and at(1007, 100, 2007) == 0      # exactly one block under the box
    assert not any(at(1012, wy, 2007) > 0 for wy in range(oy, 106))  # walkway still bare (outside skin box)


def test_hug_cut_boxes_and_min_width():
    at, oy = _hug(cut_boxes=[[1001, 2001, 1003, 2012]])
    assert not any(at(1002, wy, 2002) > 0 for wy in range(oy, 106))  # cut column bare
    assert any(at(1010, wy, 2002) > 0 for wy in range(oy, 106))      # rest of the plate still hung
