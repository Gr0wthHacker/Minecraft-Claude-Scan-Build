"""The tonal-ladder finder, and the three traps it exists on the other side of.

This repo wrote down three times that its economy has no value contrast - and each time the
measurement was taken inside ONE material family, where a value ladder cannot exist. What is pinned
here is not the numbers (a rescan moves those) but the PROPERTIES that make the answer honest:

  * a ladder is scored on its smallest step, never its range;
  * the pool is witnessed rather than remembered, so it cannot propose a block that is not on a
    1.19 server;
  * and the pool is NOT filtered through `protect.is_protected`, which holds `wool` and would
    silently delete most of this island's sculpture material.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

import ladder                                   # noqa: E402
from mcbuild import blocks                      # noqa: E402
from mcbuild.gen import protect                 # noqa: E402


def _pool():
    return ladder.pool({"cheap", "ok"})


# ---------------------------------------------------------------- scoring

def test_a_ladder_is_scored_on_its_smallest_step_not_its_range():
    """Three stops at 0/10/200 have a huge range and two indistinguishable rungs. A ladder at
    0/100/200 is strictly better and must win, which ranking on range would get backwards."""
    crowded = [("a", (0, 0, 0), 0.0, 0.0, 0.0),
               ("b", (0, 0, 0), 10.0, 0.0, 0.0),
               ("c", (0, 0, 0), 100.0, 0.0, 0.0),
               ("d", (0, 0, 0), 200.0, 0.0, 0.0)]
    rungs, gap = ladder.ladder(crowded, 3)
    assert [r[0] for r in rungs] == ["d", "c", "a"]
    assert gap == 100.0


def test_the_ladder_comes_back_brightest_first():
    rungs, _ = ladder.ladder(_pool(), 4)
    lums = [r[2] for r in rungs]
    assert lums == sorted(lums, reverse=True)


def test_asking_for_more_stops_than_exist_does_not_raise():
    tiny = [("a", (0, 0, 0), 0.0, 0.0, 0.0), ("b", (0, 0, 0), 50.0, 0.0, 0.0)]
    rungs, gap = ladder.ladder(tiny, 5)
    assert len(rungs) == 2 and gap == 50.0


# ---------------------------------------------------------------- the pool

def test_the_pool_holds_no_block_this_server_has_never_seen():
    """`blocks.available()` is a no-op while the allowlist is provisional, so an unwitnessed pool
    proposes post-1.19 blocks. This is rule 12's failure and the repo has shipped it twice."""
    names = {c[0] for c in _pool()}
    for n in ("dried_ghast", "chiseled_cinnabar", "test_instance_block", "pale_oak_planks"):
        assert n not in names, f"{n} is not on a 1.19 server"


def test_the_unwitnessed_pool_is_the_one_that_lets_them_in():
    """The guard has to be doing the work - if `--any` produced the same answer it would be
    decoration. Stated as a control so the previous test cannot pass vacuously."""
    wide = {c[0] for c in ladder.pool({"cheap", "ok"}, witnessed=False)}
    assert wide - {c[0] for c in _pool()}, "witnessing removed nothing"


def test_wool_survives_the_functional_filter():
    """`protect.is_protected` holds `wool` - it is the never-OVERWRITE set, because a wool block may
    be a sculk sensor's silencer. Using it as 'may I build with this' deletes every wool in the
    game. `Island Night` made exactly this mistake and 523 cells stayed dark."""
    assert protect.is_protected("gray_wool"), "the trap this test guards has moved"
    names = {c[0] for c in _pool()}
    assert {"gray_wool", "black_wool", "white_wool"} <= names


def test_a_dyed_family_is_admitted_whole():
    """The witness list holds black_terracotta and brown_terracotta but not gray_terracotta.
    Minecraft ships a dyed family complete, so one member is evidence for sixteen - the same
    inference `trusted_slabs` makes about a material family, and nothing beyond it."""
    from mcbuild.gen import shell
    conf = set(shell._confirmed())
    assert "black_terracotta" in conf and "gray_terracotta" not in conf, \
        "the allowlist changed; re-choose the example"
    assert "gray_terracotta" in ladder.witnessed_blocks()


def test_family_expansion_over_generates_harmlessly():
    """The expansion is a NAME set: it proposes `black_tulip`, which is not a block. That is only
    safe because the set is intersected with the real registry before it reaches an answer, so the
    intersection is what is asserted rather than the set."""
    assert "black_tulip" in ladder.witnessed_blocks()
    assert "black_tulip" not in {c[0] for c in ladder.pool({"cheap", "ok"}, full_only=False)}


def test_containers_and_bedrock_are_not_material():
    names = {c[0] for c in _pool()}
    assert not [n for n in names if "shulker_box" in n]
    assert "bedrock" not in names


def test_the_dye_prefix_is_matched_longest_first():
    """`light_gray_wool` must not be read as the `gray` family plus a stray `light_`."""
    assert ladder.dye_family("light_gray_wool") == "wool"
    assert ladder.dye_family("light_blue_concrete") == "concrete"
    assert ladder.dye_family("stone_bricks") is None


# ---------------------------------------------------------------- the claim it refutes

def test_a_family_cannot_draw_a_line_against_itself_but_the_registry_can():
    """The finding this tool was written for. Inside the blackstone family every stop is within a
    few points of luminance - which is what CLAUDE.md measured and correctly reported. Across
    families at the same hue the ladder is an order of magnitude wider, which is what CLAUDE.md
    then wrongly concluded was impossible."""
    def lum(n):
        return ladder.lum(blocks.color(n, "side"))

    base = lum("polished_blackstone_bricks")
    family = max(abs(lum(n) - base) for n in
                 ("blackstone", "chiseled_polished_blackstone", "cracked_polished_blackstone_bricks"))
    assert family < 15, "the blackstone family used to be flat; re-read this test"

    _rungs, gap = ladder.ladder([c for c in _pool() if c[4] < 0.12], 4)
    assert gap > 3 * family, f"neutral ladder step {gap:.0f} should dwarf the family's {family:.0f}"
