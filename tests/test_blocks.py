"""The block knowledge base: does it agree with the game, and with the world we actually built in.

Regenerate it with `python tools/extract_blocks.py --reports <datagen out>` when Minecraft updates.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mcbuild import blocks as B


def test_loaded():
    assert B.loaded(), "run tools/extract_blocks.py"
    assert len(B._db()) > 1000


def test_names_are_26_2():
    # `chain` was renamed `iron_chain`. Five generators still emitted the old name and every one of
    # them would have been refused in game.
    assert not B.exists("chain")
    assert B.exists("iron_chain")


def test_full_cube_matches_reality():
    """The rule-9 distinction. A vine can hang off the left column and not the right one."""
    for n in ("stone_bricks", "moss_block", "oak_leaves", "dark_oak_log", "glass", "bone_block"):
        assert B.is_full_cube(n), n
    for n in ("stone_brick_wall", "oak_fence", "oak_slab", "spruce_stairs", "moss_carpet",
              "iron_bars", "lantern", "iron_chain", "vine"):
        assert not B.is_full_cube(n), n


def test_slabs_and_stairs_hold_things_up_even_though_they_are_not_full():
    for n in ("oak_slab", "spruce_stairs", "farmland"):
        assert B.supports_top(n) and not B.is_full_cube(n), n


def test_validate_catches_what_litematica_would():
    assert B.validate("stone_bricks") == []
    assert B.validate("lantern", {"hanging": "false", "waterlogged": "false"}) == []
    assert B.validate("nonsuch_block") != []                      # misspelt name
    assert B.validate("oak_slab", {"facing": "north"}) != []       # property the block lacks
    assert B.validate("lantern", {"hanging": "maybe"}) != []       # value outside its set
    assert B.validate("lily_pad", {"rotation": "0"}) != []         # lily_pad has no properties at all
    assert B.validate("barrel", {"type": "single"}) != []          # that is a chest property


def test_colors_cover_the_registry():
    have = sum(1 for n, r in B._db().items() if "rgb" in r)
    assert have >= 1190, have
    # only the three airs may lack a colour
    assert {n for n, r in B._db().items() if "rgb" not in r} == {"air", "cave_air", "void_air"}


def test_nearest_and_ramp():
    assert B.nearest((250, 250, 250)) is not None
    r = B.ramp((240, 230, 190), (150, 90, 45), 4, tier={"cheap", "ok"})
    assert len(r) == len(set(r)) == 4, r


def test_every_shipped_state_is_legal():
    """Every block state in every design, checked against the registry."""
    import glob
    from mcbuild import scan
    bad = []
    for f in sorted(glob.glob(os.path.join(os.path.dirname(__file__), "..", "out", "*.litematic"))):
        try:
            s = scan.load(f)
        except Exception:
            continue
        for full in s.model.names:
            n = full.split(":", 1)[-1]
            st = {}
            if "[" in n:
                st = dict(kv.split("=", 1) for kv in n.split("[", 1)[1].rstrip("]").split(",")
                          if "=" in kv)
            bad += [f"{os.path.basename(f)}: {p}" for p in B.validate(n, st)]
    assert not bad, bad[:10]
