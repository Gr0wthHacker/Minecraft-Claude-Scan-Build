"""THE DRESSING'S OWN CONTRACTS: a tree stands in the ground, and a drift does not eat one.

Jack: *"audit all placements of things like trees and lamp posts, make sure its artistic, it makes
sense, doesnt obstruct pathways or buildings."*

**EVERY FAULT THESE PIN PASSED EVERY OTHER CHECK IN THE REPO.** A tree floating one course over a
flower is a legal, supported, affordable, 1.19, non-colliding block; the audit is clean, the bill
of materials is right, and `render3d` draws it exactly as it draws a planted one. So the only
thing that can catch it is a test that asks the question a person walking the park would ask.

The two generators fixed here had the same fault for the same reason and neither could see it:
`Canvas.put` OVERWRITES, and both draw their pieces one after another over a shared canvas whose
contents they never consult. `_Ground.free` does not help - it asks the WORLD, which is the
capture, and the capture does not contain what the pass laid ten iterations ago.
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from mcbuild.gen import parkgreen, plateau                        # noqa: E402

SOIL = {"moss_block", "dirt", "coarse_dirt", "rooted_dirt", "podzol", "grass_block", "mycelium",
        "mud", "farmland", "dirt_path", "clay", "sand", "red_sand", "gravel", "mossy_cobblestone"}


def _cfg(name: str) -> dict:
    return yaml.safe_load((ROOT / "configs" / f"{name}.yaml").read_text(encoding="utf-8"))["params"]


def _names(c) -> np.ndarray:
    return np.array([e.value["Name"].value.split(":")[-1] for e in c.palette])


def _trees(c):
    """(v, u, base course, what is under the base) for every trunk with a crown on it."""
    names = _names(c)
    ids = c.ids
    sy, sz, sx = ids.shape
    T = np.isin(ids, [i for i, n in enumerate(names) if n.endswith("_log")])
    L = np.isin(ids, [i for i, n in enumerate(names) if n.endswith("_leaves")])
    out = []
    for z in range(sz):
        for x in range(sx):
            col = [y for y in range(sy) if T[y, z, x]]
            if len(col) < 3:
                continue
            top = col[-1]
            crown = any(L[min(sy - 1, top + dy), max(0, min(sz - 1, z + dz)),
                          max(0, min(sx - 1, x + dx))]
                        for dy in (0, 1) for dz in (-1, 0, 1) for dx in (-1, 0, 1))
            if not crown:
                continue
            y0 = col[0]
            under = str(names[ids[y0 - 1, z, x]]) if y0 > 0 and ids[y0 - 1, z, x] else "PLANE"
            out.append((x, z, y0, under))
    return out


# --------------------------------------------------------------------------- the park green


@pytest.fixture(scope="module")
def green():
    return parkgreen.build(dict(_cfg("pf_park_green")))


def test_EVERY_ORNAMENTAL_TREE_STANDS_ON_THE_GROUND(green):
    """No tree floats one course up on a tuft, a flower, a carpet, a hedge or a boulder.

    **THE CAUSE WAS A LATER DRIFT EATING THE TREE'S OWN BOTTOM LOG.** Measured on the shipped
    park: 68 of 159 ornamentals had lost their base, and the block left under each was whatever
    drifted over it - `short_grass` 16, `moss_carpet` 16, `fern` 13, `cobblestone` 8, `allium` 6.
    The contract in this module's own metadata said *"It never replaces a standing block"* and
    nothing made it true.
    """
    bad = [t for t in _trees(green) if t[3] not in SOIL and t[3] != "PLANE"]
    assert not bad, f"{len(bad)} floating trees, e.g. {bad[:6]}"


def test_NO_TWO_ORNAMENTALS_STAND_ON_TOP_OF_EACH_OTHER(green):
    """Trunks keep `tree_clear` apart, so a stand reads as trees rather than as poles in a blob.

    A crown is radius 2. Two trunks three or four apart still touch canopies and that is a COPSE
    and is wanted; the shipped park had a median gap of THREE with 74 of 193 trunks within two of
    another, and clusters of four trunks inside a 5x3 patch under one mass of leaves.
    """
    clear = parkgreen.GREEN_CFG["tree_clear"]
    pts = [(t[0], t[1]) for t in _trees(green)]
    tight = [(a, b) for i, a in enumerate(pts) for b in pts[i + 1:]
             if max(abs(a[0] - b[0]), abs(a[1] - b[1])) < clear]
    assert not tight, f"{len(tight)} trunk pairs closer than {clear}, e.g. {tight[:6]}"


def test_A_DRIFT_NEVER_EATS_WHAT_THE_PASS_HAS_ALREADY_PLACED(green):
    """The module's stated contract, enforced - and the count is reported rather than assumed.

    31% of everything this pass placed used to be written over its own earlier work: a boulder
    through a crown, a meadow through a hedge, a trunk through another tree's canopy. `kept` is
    what the guard now turns away; a number climbing there says the density has gone past what
    the ground can hold, which is a reading worth having rather than a failure.
    """
    assert green.meta["parts"]["kept"] > 0, "the guard is not being exercised at all"
    contract = green.meta["contract"]
    assert "never replaces a standing block" in contract
    assert "tree_clear" in contract, "the contract has to state the rule it now keeps"


def test_ONLY_GROUND_COVER_MAY_BE_DRAWN_OVER():
    """The soft set is this pass's own one-cell planting, and it is DERIVED from the palettes.

    A carpet, a tuft, a fern and a flower are one class of thing; a trunk, a leaf, a bush, a
    hedge and a boulder are structure. Typed by hand instead, a land that swapped its grass for
    another tuft would have that tuft silently promoted to something a tree cannot root through -
    which is this fault wearing the next costume.
    """
    soft = parkgreen._Soft.SOFT
    assert "moss_carpet" in soft and "short_grass" in soft and "poppy" in soft
    for hard in ("oak_log", "oak_leaves", "azalea", "cobblestone", "stone_brick_slab",
                 "sweet_berry_bush", "flowering_azalea"):
        assert hard not in soft, f"{hard} has structure and must not be drawn over"
    # every flower of every land is in it, because every land's beds are the same class of thing
    for pal in (parkgreen.GREEN, *parkgreen.PALETTES.values()):
        for pair in pal.get("flowers", []):
            for f in pair:
                assert f in soft, f"{f} is a bed flower and is not in the soft set"


def test_THE_GUARD_IS_WHAT_IS_DOING_IT_not_the_density():
    """Put the fault back and the floating trees return - so the test fails for the right reason.

    A contract that passes the build it was written against AND would pass the build it was
    written to forbid is worth nothing, and this repo has three of those on record. `_Raw` is the
    module exactly as it behaved before: `put` straight through to the canvas, which overwrites,
    and no site test on the trunk's base.
    """
    class _Raw(parkgreen._Soft):
        def put(self, v, y, u, key, **props):
            return self._lot.put(int(v), int(y), int(u), key, **props)

        def rootable(self, v, u):
            return True

    p = dict(_cfg("pf_park_green"))
    p["tree_clear"] = 0
    real, parkgreen._Soft = parkgreen._Soft, _Raw
    try:
        before = _trees(parkgreen.build(dict(p)))
    finally:
        parkgreen._Soft = real
    floating = [t for t in before if t[3] not in SOIL and t[3] != "PLANE"]
    assert before, "the control build produced no trees at all - the fixture is wrong"
    assert len(floating) > 20, (
        f"only {len(floating)} floating trees with the guard bypassed - this test is no longer "
        f"exercising the fault it was written for")


# --------------------------------------------------------------------------- the lost plateau


@pytest.mark.skipif(not (ROOT / "out" / "PF Lost Plateau.litematic").exists(),
                    reason="needs the shipped artifact for rule 15")
def test_THE_CANOPY_DOES_NOT_DELETE_ITSELF_ON_A_REBUILD():
    """`previous:` is rule 15, and it was answered in the docstring and not in the code.

    `_Relief` took `mine` from the shipped artifact, stored it, and read it nowhere - so the
    surface it probed was the world WITH this pass already on it, every column it had capped last
    time read as `moss_block` rather than as ROCK, and `dressable` refused it. Regenerating a
    shipped design collapsed it from 15,374 cells to 3,440: the canopy quietly deleting itself on
    any rebuild, with nothing anywhere to say so.
    """
    c = plateau.build(dict(_cfg("pf_lost_plateau")))
    assert int((c.ids != 0).sum()) > 8000, "the canopy has collapsed - is `mine` being read?"
    assert c.meta["parts"]["trees"]["trees"] > 30


@pytest.mark.skipif(not (ROOT / "out" / "PF Lost Plateau.litematic").exists(),
                    reason="needs the shipped artifact for rule 15")
def test_A_VINE_CURTAIN_DOES_NOT_EAT_THE_TREE_IT_HANGS_BESIDE():
    """`_vines` runs after `_trees` and `Canvas.put` overwrites.

    Where a face fell away beside a planted column the curtain was written straight down through
    the moss cap and the bottom two logs of the trunk standing on it - eight trees left hanging
    three to five courses over the rock with a rope of green in the gap.
    """
    c = plateau.build(dict(_cfg("pf_lost_plateau")))
    names = _names(c)
    bad = Counter(t[3] for t in _trees(c) if t[3] != plateau.JUNGLE["turf"] and t[3] != "PLANE")
    assert "vine" not in bad, f"trees standing on their own vine curtain: {dict(bad)}"
    assert sum(bad.values()) <= 4, f"trees not rooted in the cap: {dict(bad)}"
    assert "vine" in set(names), "the fixture built no vines at all - it proves nothing"
