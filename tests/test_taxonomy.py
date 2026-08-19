"""taxonomy: a species is its family's proportions x its height, and nothing may short-circuit that.

The regression these guard against is real and cost a session. All three felids carried a hand-tuned
`body_r` in absolute blocks from before proportions were derived; `build` overrides whatever
`derive()` computes, so the absolute silently won and every cat built 23-33% too narrow. Worse, the
error GREW with height, because an absolute among ratios does not scale - the jaguar's proportion
score fell from 0.75 to 0.50 as it was made bigger.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
from mcbuild.gen import taxonomy

# Keys that name a LENGTH IN BLOCKS. `derive()` computes each of these from the family proportion
# table x height, so a species or family `build` block that sets one overrides a derived value with
# a constant, and the animal stops scaling.
DERIVED_BLOCK_KEYS = {"leg", "body_len", "withers", "hips", "body_r", "leg_r",
                      "neck", "head_len", "head_r", "neck_r0", "neck_r1"}


def test_every_species_resolves():
    assert taxonomy.species(), "no species defined"
    for name in taxonomy.species():
        p = taxonomy.resolve(name)
        assert p["body_len"] > 0 and p["leg"] > 0 and p["head_len"] > 0, name


def test_no_absolute_block_dimensions_in_build():
    """The bug that broke all three felids. `build` is for ratios and switches, never for blocks."""
    for name, sp in taxonomy.species().items():
        bad = DERIVED_BLOCK_KEYS & set((sp.get("build") or {}))
        assert not bad, (f"species {name!r} sets {sorted(bad)} as an absolute in `build`; that "
                         f"overrides the derived value and stops the animal scaling with height")
    for name, fam in taxonomy.families().items():
        bad = DERIVED_BLOCK_KEYS & set((fam.get("build") or {}))
        assert not bad, f"family {name!r} sets {sorted(bad)} as an absolute in `build`"


@pytest.mark.parametrize("name", sorted(taxonomy.species()))
def test_dimensions_scale_with_height(name):
    """Double the height, and every derived length should roughly double. An absolute would not."""
    sp = taxonomy.species()[name]
    fam = taxonomy.families()[sp["family"]]
    build = {**(fam.get("build") or {}), **(sp.get("build") or {})}
    h = float(sp["height"])
    small = taxonomy.derive(fam, h, build, {})
    big = taxonomy.derive(fam, h * 2, build, {})
    for k in DERIVED_BLOCK_KEYS:
        if k not in small:
            continue
        # rounding to whole blocks and the `max(...)` floors make this approximate, not exact
        assert big[k] >= small[k] * 1.7, (f"{name}: {k} went {small[k]} -> {big[k]} when height "
                                          f"doubled; it is not scaling")


@pytest.mark.parametrize("name", sorted(taxonomy.species()))
def test_derived_dimensions_match_the_family_table(name):
    """What `derive` emits must be what `proportions.py` will later measure against."""
    p = taxonomy.resolve(name)
    pr = taxonomy.proportions(name)
    h = float(taxonomy.species()[name]["height"])
    assert p["body_len"] == max(4, round(pr["body length"] * h))
    assert p["leg"] == max(2, round(pr["leg (ground->belly)"] * h))
    assert p["head_len"] == max(3, round(pr["head length"] * h))
    assert p["body_r"] == pytest.approx(max(1.0, pr["body width"] * h / 2.0))


# Species allowed to stand below their own floor, and why. Keep this list SHORT and justified -
# it is the one place the size rule may be broken, and every entry is a known compromise.
UNDERSIZED = {
    # 57 against a floor of 59. It is the only animal actually built in the world, so raising it
    # would orphan the blocks already placed. Jack's call, not a silent fix. Its ossicones and mane
    # are the features the shortfall costs - `features` scores 0.83 rather than 1.00 because of it.
    "giraffe": "already built in the world at 57; resizing is Jack's decision",
}


def test_species_heights_clear_their_family_floor():
    """A species built at its family's bare floor has every feature at minimum and no structure.
    polar_bear sat at exactly 26 - the ursid floor - and the silhouette test read it as a rodent."""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
    import scale
    for name, sp in taxonomy.species().items():
        try:
            floor = max(scale.floors(name).values())
        except KeyError:
            continue                                  # no per-species reference table; skip
        if name in UNDERSIZED:
            assert float(sp["height"]) < floor, (
                f"{name} now clears its floor - drop it from UNDERSIZED")
            continue
        assert float(sp["height"]) >= floor, (
            f"{name} is {sp['height']} tall but its finest feature needs {floor:.0f}")


def test_family_of_and_required_features():
    assert taxonomy.family_of("lion") == "felid"
    assert taxonomy.family_of("polar_bear") == "ursid"
    feats = taxonomy.required_features("lion")
    assert "mane" in feats, "lion must inherit felid features AND add its own"
    assert "eyes" in feats
