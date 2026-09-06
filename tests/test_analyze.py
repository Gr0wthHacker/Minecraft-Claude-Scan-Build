"""Materials ranked by what can be placed against the world TODAY, not by count."""
import collections, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from mcbuild import analyze, nbt, scan, schem

OUT = "out/_test"


def _pair(path, name, shape, fill):
    m = schem.Model(np.zeros(shape, np.int32),
                    [nbt.block_state("minecraft:air"), nbt.block_state("minecraft:stone"),
                     nbt.block_state("minecraft:oak_planks"), nbt.block_state("minecraft:red_wool")])
    fill(m.ids)
    meta = {"name": name, "origin": {"x": 0, "y": 60, "z": 0}, "size": {"x": shape[2], "y": shape[0], "z": shape[1]}}
    os.makedirs(OUT, exist_ok=True)
    scan.save_pair(path, m, meta, name=name)


def _fixture():
    # world: a stone floor 6x6 at Y60, nothing else
    _pair(f"{OUT}/aworld.litematic", "aworld", (5, 6, 6), lambda ids: ids.__setitem__((0, slice(None), slice(None)), 1))

    # design: the same floor (built), a planks wall on the floor (placeable), a wool roof on the wall
    # (nothing to place against yet), and one stone pillar cell floating in mid-air
    def design(ids):
        ids[0, :, :] = 1                # floor: already built
        ids[1, 0, :] = 2                # 6 planks along one edge, on the floor
        ids[2, 0, :] = 3                # 6 wool on top of the planks: blocked until the planks go in
        ids[3, 5, 5] = 1                # a stone cell with air on every side
    _pair(f"{OUT}/adesign.litematic", "adesign", (5, 6, 6), design)


def test_placeable_is_ranked_above_count():
    _fixture()
    a = analyze.analyze(f"{OUT}/adesign.litematic", f"{OUT}/aworld.litematic")
    m = a.materials
    assert m["stone"].total == 37 and m["stone"].built == 36 and m["stone"].remaining == 1
    assert m["stone"].placeable == 0, "the floating stone has nothing to place against"
    assert m["oak_planks"].remaining == 6 and m["oak_planks"].placeable == 6
    assert m["red_wool"].remaining == 6 and m["red_wool"].placeable == 0, "the roof waits for the wall"
    assert m["oak_planks"].unlocks == 6, "each plank gives one wool cell its face"
    ranked = [x.item for x in a.ranked()]
    assert ranked[0] == "oak_planks", "the wall is what a trip should fetch, not the roof or the commonest block"
    assert a.placeable == 6 and a.remaining == 13
    assert m["oak_planks"].where == (0, 0) and m["oak_planks"].where_n == 6


def test_the_report_names_what_is_blocked_and_what_is_short():
    _fixture()
    a = analyze.analyze(f"{OUT}/adesign.litematic", f"{OUT}/aworld.litematic")
    txt = analyze.render(a, have=collections.Counter({"oak_planks": 2}))
    assert "oak_planks" in txt.splitlines()[2], "top row is the placeable one"
    assert "red_wool:6" in txt and "nothing to place against yet" in txt
    assert "     2       4" in txt, "have 2, short 4"
    assert analyze.item_of("minecraft:stone_brick_stairs[facing=east,half=top]") == "stone_brick_stairs"
