"""Baritone reads a litematic's air as MUST-BE-AIR; this brief keeps it from digging the world."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from mcbuild import baritone, nbt, scan, schem

OUT = "out/_test"


def _pair(path, name, origin, shape, fill):
    m = schem.Model(np.zeros(shape, np.int32),
                    [nbt.block_state("minecraft:air"), nbt.block_state("minecraft:stone"),
                     nbt.block_state("minecraft:oak_planks")])
    fill(m.ids)
    meta = {"name": name, "origin": {"x": origin[0], "y": origin[1], "z": origin[2]},
            "size": {"x": shape[2], "y": shape[0], "z": shape[1]}}
    os.makedirs(OUT, exist_ok=True)
    scan.save_pair(path, m, meta, name=name)


def _fixture():
    # world: a 6x6 stone platform at Y64 with a plank house on it, world origin (0,60,0)
    def world(ids):
        ids[4, :, :] = 1
        ids[5:7, 1:4, 1:4] = 2
    _pair(f"{OUT}/bworld.litematic", "bworld", (0, 60, 0), (10, 6, 6), world)

    # design: same box, remaining work = a stone pillar at (5, 65..68, 5) plus one cell already standing
    def design(ids):
        ids[5:9, 5, 5] = 1
        ids[4, 0, 0] = 1      # already stone in the world
    _pair(f"{OUT}/b design.litematic", "b design", (0, 60, 0), (10, 6, 6), design)


def test_it_measures_what_an_unguarded_baritone_would_dig():
    _fixture()
    b = baritone.brief(f"{OUT}/b design.litematic", world=f"{OUT}/bworld.litematic")
    # platform 36 + house 18 = 54 world blocks; one is under a design cell that matches, so 53 are under design AIR
    assert b["would_break_unguarded"] == 53
    assert b["already_standing"] == 1
    assert b["blocks"] == 5


def test_the_settings_make_the_design_additive_and_the_layer_is_schematic_relative():
    _fixture()
    b = baritone.brief(f"{OUT}/b design.litematic")
    s = dict(b["settings"])
    assert s["buildSkipBlocks"] == "air" and s["buildIgnoreExisting"] == "true" and s["allowBreak"] == "false"
    assert s["layerOrder"] == "false", "a printer builds bottom-up"
    assert b["lowest_layer"] == 4 and b["lowest_world_y"] == 64 and s["startAtLayer"] == "4"
    txt = baritone.render(b)
    assert "#build b_design.litematic 0 60 0" in txt
    assert "--copy" in txt, "a name with a space must be flagged, Baritone reads one token"


def test_copy_writes_a_space_free_twin_with_the_same_bytes():
    _fixture()
    b = baritone.brief(f"{OUT}/b design.litematic", copy=True)
    assert b["copied"] and b["copied"].endswith("b_design.litematic") and not b["needs_copy"]
    assert open(b["copied"], "rb").read() == open(f"{OUT}/b design.litematic", "rb").read()
    assert baritone.safe_name("Park Complete.litematic") == "Park_Complete.litematic"
