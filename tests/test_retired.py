"""Retirement is a judgement the rubric cannot make, so it has to be recorded rather than computed.

The three cats and both bears score 0.79-0.86 and were retired anyway. The panel is what retired
them - *"you cannot name it from the silhouette - it reads as a low table, or a bull"* - and the
scores are what failed to notice. Without a flag, the next session opens `compare.py`, sees eight
animals at GOOD, and starts tuning the ones that cannot work.

The flag is a RECORD, not a threshold. Nothing computes it and nothing should.
"""
import os
import sys

import pytest
import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from mcbuild.gen import taxonomy                    # noqa: E402

# The line: identity carried by MUSCLE AND PROPORTION, which voxels render worst of anything.
VOLUMETRIC = {"jaguar", "leopard", "lion", "bear", "polar_bear"}
# ...against identity carried by HARDWARE - a trunk, a neck, a genuinely blocky rodent.
HARDWARE = {"elephant", "giraffe", "capybara"}


def test_the_cats_and_bears_are_retired():
    assert {k for k in taxonomy.species() if taxonomy.is_retired(k)} == VOLUMETRIC


def test_the_hardware_animals_are_not():
    """The elephant's trunk and ears, the giraffe's neck, the capybara being a blocky rodent. The
    giraffe is also the only animal standing in the world and one of the two builds players picked
    out - retiring it would be retiring a success."""
    assert set(taxonomy.live()) == HARDWARE
    for n in HARDWARE:
        assert not taxonomy.is_retired(n)


def test_a_retired_species_still_resolves():
    """Nothing is deleted. `X jaguar` is in `out/`, the rubric can still score it, and a build that
    exists must keep loading - retirement stops it being LIVE WORK, not being a thing."""
    for n in VOLUMETRIC:
        p = taxonomy.resolve(n)
        assert p, f"{n} no longer resolves"
        assert p.get("body_len"), f"{n} resolved to nothing usable"


def test_scale_still_answers_for_a_retired_species():
    """`tools/scale.py` must keep working on them: the family floors are shared, and the ursid floor
    is what the bear's height is evidence for even though no bear is being built."""
    from mcbuild.gen import taxonomy as t
    assert t.family_of("jaguar") == "felid"
    assert t.family_of("bear") == "ursid"


def test_the_reason_is_written_down_where_it_will_be_found():
    """A flag with no reason beside it gets removed by whoever finds it inconvenient."""
    text = open(os.path.join(ROOT, "mcbuild/data/species.yaml"), encoding="utf-8").read()
    assert "RETIRED" in text
    assert "PLANAR" in text or "VOLUMETRIC" in text, "the line itself must be stated, not just the verdict"
    assert "2.6x" in text or "60,000" in text, "the evidence that scale does not rescue it must survive"


def test_the_jaguar_config_is_marked_so_the_suite_skips_it():
    """`tests/test_designs.py` skips any config whose FIRST LINE says RETIRED. That mechanism
    already existed; this is the first animal to use it."""
    first = open(os.path.join(ROOT, "configs/jaguar.yaml"), encoding="utf-8").readline()
    assert "RETIRED" in first


def test_retired_species_are_still_valid_entries():
    """The flag must not have broken the table it sits in."""
    sp = yaml.safe_load(open(os.path.join(ROOT, "mcbuild/data/species.yaml"), encoding="utf-8"))
    for n in VOLUMETRIC:
        assert sp[n].get("family"), f"{n} lost its family"
        assert sp[n].get("height"), f"{n} lost its height"
        assert sp[n].get("coat"), f"{n} lost its coat"
