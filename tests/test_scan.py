"""chunkscan capture reader: world-coordinate cuts keep placement and tile entities."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from mcbuild import nbt, scan, schem
from mcbuild.nbt import Tag, TAG_COMPOUND, TAG_INT, TAG_STRING

OUT = "out/_test"


def _capture_pair(path):
    """8x4x6 box at world origin (100, 64, -200): stone floor, glass column at world (103,65..67,-198), chest at (105,65,-197)."""
    m = schem.Model(np.zeros((4, 6, 8), np.int32),
                    [nbt.block_state("minecraft:air"), nbt.block_state("minecraft:stone"),
                     nbt.block_state("minecraft:glass"), nbt.block_state("minecraft:chest", facing="north")])
    m.ids[0, :, :] = 1
    m.ids[1:4, 2, 3] = 2
    m.ids[1, 3, 5] = 3
    m.tile_entities = [Tag(TAG_COMPOUND, {"id": Tag(TAG_STRING, "minecraft:chest"),
                                          "x": Tag(TAG_INT, 5), "y": Tag(TAG_INT, 1), "z": Tag(TAG_INT, 3)})]
    meta = {"name": "t", "origin": {"x": 100, "y": 64, "z": -200}, "size": {"x": 8, "y": 4, "z": 6},
            "server": {"name": "sb", "ip": "play.example"}, "dimension": "minecraft:overworld",
            "chunks_included": [[6, -13]], "chunk_radius": 0, "non_air_blocks": 52, "palette_size": 4}
    os.makedirs(OUT, exist_ok=True)
    scan.save_pair(path, m, meta, name="t")


def test_load_and_summary():
    _capture_pair(f"{OUT}/cap.litematic")
    s = scan.load(f"{OUT}/cap.litematic")
    assert s.origin == (100, 64, -200) and s.size == (8, 4, 6)
    txt = scan.summary(s)
    assert "origin 100 64 -200  ->  107 67 -195" in txt and "play.example" in txt


def test_cut_by_world_coords_keeps_placement_and_tiles():
    _capture_pair(f"{OUT}/cap.litematic")
    s = scan.load(f"{OUT}/cap.litematic")
    # box around the glass column and the chest, corners given in the "wrong" order
    m, meta = scan.cut(s, 106, 67, -197, 102, 65, -199)
    assert meta["origin"] == {"x": 102, "y": 65, "z": -199}
    assert m.shape_xyz == (5, 3, 3)
    names = m.names
    assert m.name_at(1, 0, 1) == "minecraft:glass"      # world (103,65,-198)
    assert m.name_at(1, 2, 1) == "minecraft:glass"      # world (103,67,-198)
    assert m.name_at(3, 0, 2) == "minecraft:chest"      # world (105,65,-197)
    assert "minecraft:stone" not in names                # floor (y=64) excluded -> palette compacted
    assert len(m.tile_entities) == 1
    te = m.tile_entities[0].value
    assert (te["x"].value, te["y"].value, te["z"].value) == (3, 0, 2)
    side = scan.save_pair(f"{OUT}/cap_cut.litematic", m, meta, name="cut")
    back = scan.load(f"{OUT}/cap_cut.litematic")
    assert back.origin == (102, 65, -199) and back.model.name_at(3, 0, 2) == "minecraft:chest"
    assert json.load(open(side))["cut_from"] == "cap.litematic"


def test_cut_outside_raises():
    _capture_pair(f"{OUT}/cap.litematic")
    s = scan.load(f"{OUT}/cap.litematic")
    try:
        scan.cut(s, 0, 0, 0, 5, 5, 5)
    except ValueError:
        return
    raise AssertionError("expected ValueError")
