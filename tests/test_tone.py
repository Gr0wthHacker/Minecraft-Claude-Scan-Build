"""Value, ladders, and the coat ramps that were wrong for the whole project's life.

`coat.shade` paints a form's light with a `ramp`, and the ramp is the whole mechanism: shading with
a ladder whose rungs are one luminance apart is shading with one colour. Every ramp in
`species.yaml` was hand-written, and measuring them found all five defective - three OUT OF ORDER
(so the shader paints the crevice tone onto a lit cell), one with a block listed twice, minimum
adjacent steps of 0.0 to 10.1.

What is pinned here is the PROPERTIES, not the numbers - a rescan moves colours and a re-tuned
species moves a ramp. The properties are: a ladder is scored on its smallest step; the pool is
witnessed rather than remembered; the coat's own block survives into its own ramp; and wool is not
thrown away by a filter meant to catch machines.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest                                       # noqa: E402
from mcbuild import blocks, tone                    # noqa: E402
from mcbuild.gen import protect                     # noqa: E402


def _pool():
    return tone.pool()


# ---------------------------------------------------------------- scoring

def test_a_ladder_is_scored_on_its_smallest_step_not_its_range():
    """0/10/200 has a huge range and two rungs nobody can separate. 0/100/200 is strictly better and
    must win, which ranking on range gets backwards."""
    crowded = [("a", (0, 0, 0), 0.0, 0.0, 0.0),
               ("b", (0, 0, 0), 10.0, 0.0, 0.0),
               ("c", (0, 0, 0), 100.0, 0.0, 0.0),
               ("d", (0, 0, 0), 200.0, 0.0, 0.0)]
    rungs, gap = tone.best_ladder(crowded, 3)
    assert [r[0] for r in rungs] == ["a", "c", "d"]
    assert gap == 100.0


def test_best_ladder_returns_darkest_first():
    """`coat.shade` takes a ramp dark to light. Handing it a bright-first list silently inverts
    every animal's lighting, and our own renderer draws both identically."""
    rungs, _ = tone.best_ladder(_pool(), 4)
    lums = [r[2] for r in rungs]
    assert lums == sorted(lums)


def test_best_ladder_is_optimal_not_greedy():
    """Brute force over a real candidate set. Greedy-from-one-end agrees on most inputs and loses
    the ladder whenever one end of the range is crowded."""
    import itertools
    c = blocks.color("oak_log", "side")
    kin = [x for x in _pool() if tone._chroma_dist(c, x[1]) <= tone.MAX_CHROMA_DRIFT]
    _rungs, gap = tone.best_ladder(kin, 4)
    best = max(min(combo[i + 1][2] - combo[i][2] for i in range(3))
               for combo in itertools.combinations(sorted(kin, key=lambda x: x[2]), 4))
    assert gap == pytest.approx(best, abs=1e-6)


# ---------------------------------------------------------------- the pool

def test_the_pool_holds_no_block_this_server_has_never_seen():
    """`blocks.available()` is a no-op while the allowlist is provisional, so an unwitnessed pool
    proposes post-1.19 blocks - rule 12's failure, shipped twice here already."""
    names = {c[0] for c in _pool()}
    for n in ("dried_ghast", "chiseled_cinnabar", "test_instance_block", "pale_oak_planks"):
        assert n not in names, f"{n} is not on a 1.19 server"


def test_the_witness_gate_is_doing_work():
    """A control: if the unwitnessed pool were the same, the test above would pass vacuously."""
    wide = {c[0] for c in tone.pool(witnessed=False)}
    assert wide - {c[0] for c in _pool()}


def test_wool_survives_the_machine_filter():
    """`protect.is_protected` holds `wool` - it is the never-OVERWRITE set, because a wool block may
    be a sculk sensor's silencer. Used as "may I build with this" it deletes every wool in the game,
    which is most of this island's sculpture. `Island Night` made this mistake and 523 cells stayed
    dark."""
    assert protect.is_protected("gray_wool"), "the trap this test guards has moved"
    names = {c[0] for c in _pool()}
    assert {"gray_wool", "black_wool", "white_wool"} <= names


def test_workstations_do_not_survive_it():
    """The other half. Without the machine filter the lion's ladder came back containing
    `fletching_table`, `smithing_table` and `cartography_table`."""
    names = {c[0] for c in _pool()}
    for n in ("fletching_table", "smithing_table", "cartography_table", "furnace", "barrel"):
        assert n not in names


def test_containers_and_bedrock_are_not_material():
    names = {c[0] for c in _pool()}
    assert not [n for n in names if "shulker_box" in n]
    assert "bedrock" not in names


def test_a_dyed_family_is_admitted_whole():
    """The witness list holds black_terracotta and brown_terracotta but not gray_terracotta.
    Minecraft ships a dyed family complete, so one member is evidence for sixteen - the same
    inference `shell.trusted_slabs` makes about a material family, and nothing beyond it."""
    from mcbuild.gen import shell
    conf = set(shell._confirmed())
    assert "black_terracotta" in conf and "gray_terracotta" not in conf, \
        "the allowlist changed; re-choose the example"
    assert "gray_terracotta" in tone.witnessed_blocks()


def test_family_expansion_over_generates_harmlessly():
    """It proposes `black_tulip`, which is not a block. Safe only because the set is intersected
    with the real registry before it reaches an answer - so the intersection is what is asserted."""
    assert "black_tulip" in tone.witnessed_blocks()
    assert "black_tulip" not in {c[0] for c in tone.pool(full_only=False)}


def test_the_dye_prefix_is_matched_longest_first():
    assert tone.dye_family("light_gray_wool") == "wool"
    assert tone.dye_family("light_blue_concrete") == "concrete"
    assert tone.dye_family("stone_bricks") is None


# ---------------------------------------------------------------- check_ramp

def test_check_ramp_catches_all_three_real_defects():
    """Each of these shipped in `species.yaml` and none was visible in any score."""
    assert any("out of order" in p for p in tone.check_ramp(
        ["spruce_planks", "stripped_spruce_wood", "acacia_log", "oak_log", "stripped_oak_log"]))
    assert any("repeated" in p for p in tone.check_ramp(["bone_block", "bone_block", "snow_block"]))
    assert any("cannot separate" in p for p in tone.check_ramp(["stone", "andesite"]))


def test_check_ramp_passes_an_honest_ramp():
    assert tone.check_ramp(["black_wool", "gray_wool", "stone", "smooth_stone", "white_wool"]) == []


def test_check_ramp_reports_an_unknown_block_and_stops():
    probs = tone.check_ramp(["stone", "not_a_real_block"])
    assert len(probs) == 1 and "no colour recorded" in probs[0]


# ---------------------------------------------------------------- coat_ladder

@pytest.mark.parametrize("base", ["stone", "oak_log", "bone_block", "jungle_log", "mangrove_wood"])
def test_a_coat_ramp_is_ordered_distinct_and_separated(base):
    r = tone.coat_ladder(base, 5)
    assert len(r) == len(set(r))
    assert tone.check_ramp(r) == [], f"{base}: {tone.check_ramp(r)}"


@pytest.mark.parametrize("base", ["stone", "oak_log", "bone_block", "jungle_log"])
def test_the_coat_block_survives_into_its_own_ramp(base):
    """It is the colour the species is defined by. A ladder free to drop it returns a ramp for some
    other animal - `stripped_oak_log` fell out of the lion's and the lion stopped being oak."""
    assert base in tone.coat_ladder(base, 5)


def test_two_brown_siblings_do_not_get_the_same_ramp():
    """Unanchored, the lion (oak_log) and the bear (mangrove_wood) came back with the SAME five
    blocks, because the search only ever saw "brown". `compare.py` measures within-family
    distinction and reports the bears carrying it entirely on coat; one shared ramp deletes that."""
    assert tone.coat_ladder("oak_log", 5) != tone.coat_ladder("mangrove_wood", 5)


def test_stops_is_a_maximum_and_a_thin_material_returns_fewer():
    """The brown wood families cannot supply five tones 15 apart at any setting - they clump at
    88/89/93. Padding to five is how species.yaml got four rungs inside a ten-luminance band.
    `blocks.ramp` already states the principle for duplicates: better to know the palette had four
    usable rungs than to pretend it had six."""
    r = tone.coat_ladder("oak_log", 5)
    assert len(r) < 5
    assert tone.check_ramp(r) == []


def test_a_coat_ramp_stays_on_its_own_material():
    """Unleashed, maximising the smallest step over a hue band proposed a lion of `spruce_log`,
    `cut_red_sandstone` and `yellow_wool` - the largest possible steps and no lion in it."""
    c = blocks.color("oak_log", "side")
    for n in tone.coat_ladder("oak_log", 5):
        d = tone._chroma_dist(c, blocks.color(n, "side"))
        assert d <= tone.MAX_CHROMA_DRIFT * 1.5 + 1e-9, f"{n} drifted {d:.3f}"


def test_a_white_coat_still_gets_a_ramp():
    """A white animal sits near the ceiling of the range - bone_block is 225 against 253 - so half a
    window above it is empty number line. Taken literally that left the polar bear TWO rungs, which
    is not shading; what is unreachable on one side is spent on the other."""
    r = tone.coat_ladder("bone_block", 5)
    assert len(r) >= 4
    assert tone.check_ramp(r) == []
    assert min(tone.luminance(n) for n in r) < 180, "a white coat must reach down into grey to shade"


def test_chroma_divides_brightness_out():
    """Two tones of one material must sit on top of each other in chroma; that is what makes the
    leash a MATERIAL leash rather than a colour-distance one."""
    dark, light = (40, 30, 20), (200, 150, 100)         # same hue, very different brightness
    assert tone._chroma_dist(dark, light) < 0.1
    assert tone._chroma_dist((100, 100, 100), (100, 40, 40)) > 0.3


# ---------------------------------------------------------------- the shipped ramps

def test_every_shipped_coat_ramp_is_honest():
    """THE GATE. This failed 5 of 5 when first written; the ramps in `species.yaml` were repaired
    against it. If it fails again, a hand-edited ramp has gone back to being unshadeable - which is
    invisible in every other check the pipeline has."""
    import pathlib

    import yaml
    data = pathlib.Path(__file__).resolve().parent.parent / "mcbuild/data/species.yaml"
    sp = yaml.safe_load(data.read_text(encoding="utf-8"))
    bad = {}
    for name, cfg in sp.items():
        ramp = ((cfg or {}).get("coat") or {}).get("coat_ramp")
        if ramp:
            probs = tone.check_ramp(ramp)
            if probs:
                bad[name] = probs
    assert not bad, "defective coat ramps: " + "; ".join(f"{k}: {v[0]}" for k, v in bad.items())
