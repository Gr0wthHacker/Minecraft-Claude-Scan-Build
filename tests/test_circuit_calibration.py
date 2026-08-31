"""The inspection, measured against builds that DEMONSTRABLY WORK.

Every other test here asks whether a rule is implemented. This one asks the only question that
decides whether anyone will use the tool: **does it stay quiet on a machine that works?** A check
that cries wolf is a check nobody runs — this project's own rule, learned on the audit and then
again on the deck soffit — and a redstone inspector has more chances to cry wolf than anything
else in the repo.

The numbers below are a CEILING, not a snapshot. They may fall as the model improves; if one
rises, something started shouting at a working build and that is the regression worth catching.
"""
from __future__ import annotations

import pathlib

import pytest

from mcbuild import circuit, sponge

REF = pathlib.Path("reference")
# Tightened after the seeding bug was fixed: these four independent working builds now produce
# ONE informational line each, where the farm alone once produced 74. Every point of that came
# from a false positive in the tool, not from a fault in the build.
BUILDS = {
    "item_filter.schem": 2,
    "bonemeal_farm_shulker_loader.litematic": 2,
    "contraption_31323.litematic": 2,
    "contraption_24829.litematic": 2,
    # A 185,198-block casino with 5,000 redstone cells. 37 findings is 0.7% of its components and
    # a human-made build that size genuinely has leftovers - chasing this to zero would be buying
    # quiet by going blind, which is the failure the last test on this page exists to prevent.
    "casino_chirurg.litematic": 45,
    # Pre-1.13: two findings, one of which is the READER saying it cannot see orientation.
    "mcedit_1216.schematic": 3,
}

pytestmark = pytest.mark.skipif(not REF.exists(), reason="no reference builds checked in")


@pytest.mark.parametrize("name,ceiling", sorted(BUILDS.items()))
def test_a_working_build_produces_almost_no_findings(name, ceiling):
    f = REF / name
    if not f.exists():
        pytest.skip(f"{name} not checked in")
    m = sponge.load_any(str(f))
    found = circuit.inspect(m)
    assert len(found) <= ceiling, (
        f"{name}: {len(found)} findings on a build known to work — "
        + "; ".join(f"{k} at {p}" for k, p, _ in found[:6]))


def test_a_moving_redstone_block_is_not_reported_as_unwired():
    """HALF THE COMPACT MACHINES IN THE GAME are driven by a redstone block a piston pushes: at
    rest the driver is not next to the thing it drives. Found twice in real builds — seven
    "unwired" pistons in one row of a bonemeal farm, and a repeater pointing at empty air with a
    redstone block on a sticky piston one cell above."""
    c = circuit.Circuit.from_cells({
        (0, 0, 0): "piston[facing=east]",
        (0, 1, 0): "redstone_block",
    })
    assert circuit.moving_driver_near(c, (0, 0, 0))
    lone = circuit.Circuit.from_cells({(0, 0, 0): "piston[facing=east]"})
    assert not circuit.moving_driver_near(lone, (9, 9, 9)), "it must not fire on the whole world"


def test_our_own_broken_lane_is_still_caught():
    """The calibration must not have been bought by going blind. A comparator with nothing behind
    it and nothing to drive is exactly what the sorter shipped for months, and it must still
    report."""
    c = circuit.Circuit.from_cells({
        (0, 0, 0): "comparator[facing=east,mode=compare]",
        (5, 0, 0): "redstone_wire",
    })
    kinds = {k for k, _, _ in circuit.inspect(c)}
    assert any("comparator" in k for k in kinds), "a stranded comparator must still be reported"


def test_a_pre_1_13_file_says_it_cannot_see_orientation():
    """MCEdit `.schematic` keeps facing in the `Data` nibbles, which this reader does not decode.
    Run blind, one such file produced 66 direction findings - every one about the READER rather
    than the build. Detected rather than declared, so it is right for any source."""
    f = REF / "mcedit_1216.schematic"
    if not f.exists():
        pytest.skip("not checked in")
    from mcbuild import sponge as _s
    m, info = _s.load_mcedit(str(f))
    kinds = {k for k, _, _ in circuit.inspect(m)}
    assert "orientation unknown" in kinds, "it must SAY it is blind rather than guessing north"
    assert not any("drives nothing" in k or "reads nothing" in k for k in kinds),         "direction findings must be skipped, not reported, when facing is unknown"


def test_an_unmapped_old_id_is_named_not_guessed():
    """A reader that quietly renders an unknown id as stone produces a build that looks imported
    and is wrong, and nothing downstream can tell."""
    from mcbuild import nbt as _n, sponge as _s
    f = REF / "mcedit_1216.schematic"
    if not f.exists():
        pytest.skip("not checked in")
    m, info = _s.load_mcedit(str(f))
    assert info["unmapped"], "this file has an id outside the table; it must be reported"
    names = {_n.state_name(e).split(":")[-1] for e in m.palette}
    assert any(n.startswith("unknown_") for n in names), "and named so it is visible in the model"
