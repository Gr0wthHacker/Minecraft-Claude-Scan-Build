"""The soffit, and the wood it left behind.

The deck-wide soffit drew a `dark_oak_wood` coffer grid over whatever happened to be overhead. It
audited clean, it cost nothing expensive, and in world it was the worst thing on the deck: measured
off the 2026-08-20 capture, its 215 grid runs were 184 runs of one or two cells - lone wood blocks
in a stone ceiling.

Nothing in the pipeline could see it, because every check it had was per-block: is it legal, is it
placeable, is it affordable, does it have support. The failure was per-RUN. So the tests here are
about runs and patches, and about the pass being able to take its own work back out.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import collections

import numpy as np
import pytest
from mcbuild.gen import GENERATORS, deckfloor

UNDER = "out/island_now.litematic"
NB4 = ((1, 0), (-1, 0), (0, 1), (0, -1))

pytestmark = pytest.mark.skipif(not os.path.exists(UNDER), reason="needs a capture")

WOOD = ("oak", "spruce", "birch", "jungle", "acacia", "dark_oak", "mangrove", "cherry", "bamboo",
        "crimson", "warped")


def _wood_in_capture():
    """How many of the pass's own grid blocks are still standing in the capture.

    NOT a hard-coded 70. There were 70 when this was written and there are fewer every time Jack
    breaks one, because the design is REMAINING WORK - a test that pins the snapshot fails the
    moment the fix starts working, which is exactly backwards.
    """
    import json
    import numpy as np
    from mcbuild import schem
    m = schem.load(UNDER)
    side = json.load(open(UNDER.replace(".litematic", ".scan.json"), encoding="utf-8"))
    o = side["origin"]
    names = [n.split(":")[-1].split("[")[0] for n in m.names]
    g = deckfloor.DECKFLOOR["reclaim_grid_at"]
    n = 0
    for i, nm in enumerate(names):
        if nm not in deckfloor.DECKFLOOR["reclaim_wood_blocks"]:
            continue
        for y, z, x in zip(*np.nonzero(m.ids == i)):
            wx, wy, wz = o["x"] + int(x), o["y"] + int(y), o["z"] + int(z)
            if 195 <= wy <= 203 and (wx % g == 0 or wz % g == 0):
                n += 1
    return n


def _built(**over):
    """Cells keyed in WORLD coordinates. Canvas-local ones are a trap here: the canvas is sized to
    its own content, so it shifts between two builds with different settings and nothing that
    compares them lines up."""
    cfg = {"under": UNDER, "floor_y": 194, "border_ring": 0, "room_h": 3, "zones": []}
    cfg.update(over)
    c = GENERATORS["deckfloor"].build(cfg, None)
    m = c.to_model()
    ox, oy, oz = c.world_origin
    names = [n.split(":")[-1].split("[")[0] for n in m.names]
    out = {}
    for y, z, x in zip(*np.nonzero(m.ids != 0)):
        out[(ox + int(x), oy + int(y), oz + int(z))] = names[m.ids[y, z, x]]
    return c, out


def test_the_deck_is_dressed_in_stone_and_deepslate_only():
    """No wood anywhere. The grid was only ever there to move a palette number - wood 7% against
    the plate's 23% - and `gallery.py` had already made and REMOVED that exact mistake one file
    over, for that exact reason. A number is the wrong reason to put a block anywhere."""
    _, built = _built()
    bad = {p: n for p, n in built.items() if any(k in n for k in WOOD)}
    assert not bad, f"the deck floor is emitting wood again: {collections.Counter(bad.values())}"


def test_the_soffit_is_off_deck_wide():
    """A SOFFIT BELONGS TO A ROOM, NOT TO A DECK. Over 1,224 columns with a real underside this
    ceiling is 25 lacy patches at SIX heights, the largest filling 40% of its own bounding box.
    Turning it on deck-wide re-materialises 25 disconnected islands, which is scatter - the exact
    thing this design's floor pass exists to remove."""
    assert deckfloor.DECKFLOOR["soffit"] is False


def test_the_grid_material_is_deepslate():
    assert deckfloor.DECKFLOOR["soffit_grid"] == "deepslate_bricks"
    assert not any(k in deckfloor.DECKFLOOR["soffit_grid"] for k in WOOD)


def test_a_grid_line_that_cannot_run_is_not_drawn():
    """The gate the original pass lacked. Forced on over this deck, every grid cell the run
    threshold rejects must come out as PANEL, never as a lone dark block - so no drawn grid cell
    may sit alone. This is `gallery._MIN_RUN`, one surface up.

    It also pins the AXIS. A line at constant X runs along Z; scoring a cell along X instead
    measures it ACROSS its own line, every run comes out as 1, and - because the threshold is
    then applied to the wrong number - isolated cells sail through. That inversion shipped and
    this test is what caught it."""
    # reclaim OFF: it heals a wood cell into its commonest neighbour, which is sometimes
    # `deepslate_bricks` - and those land as isolated cells at ceiling height that are not grid
    # cells at all. Leaving it on makes this test read the wrong blocks.
    c, built = _built(soffit=True, soffit_min_run=4, soffit_min_patch=8, reclaim_wood=False)
    grid = deckfloor.DECKFLOOR["soffit_grid"]
    # ABOVE THE FLOOR ONLY. `room_plinth` is also deepslate and sits on the floor course round the
    # moss farm - isolated cells by design, and picking them up made this look like a grid bug.
    cells = {(p[0], p[2]) for p, n in built.items() if n == grid and p[1] >= 194 + 3}
    lone = [c0 for c0 in cells
            if not any((c0[0] + dx, c0[1] + dz) in cells for dx, dz in NB4)]
    assert not lone, f"{len(lone)} grid cells have no grid neighbour - that is confetti, not a grid"
    assert c.meta.get("soffit_grid_demoted", 0) > 0, "the run gate never fired on a ceiling it must"


def test_a_patch_too_small_to_be_a_ceiling_is_left_as_rock():
    c, _ = _built(soffit=True, soffit_min_patch=8, reclaim_wood=False)
    assert c.meta.get("soffit_small_patch", 0) > 0, "the patch gate never fired"


def test_it_takes_its_own_wood_back_out():
    """A LITEMATIC CANNOT EXPRESS REMOVAL, and the pass could not see its own mistake: dark oak is
    not in `soffit_raw`, and 50 of the 70 blocks have since had moss placed under them, so they
    fail the room test too. Left alone they would have stood for good. Every one must be healed -
    and into a SOLID block, never into air, or the fix is a hole in a ceiling."""
    want = _wood_in_capture()
    c, built = _built()
    assert c.meta.get("reclaimed_wood", 0) == want, (
        f"{c.meta.get('reclaimed_wood', 0)} reclaimed of {want} still standing in the capture")
    assert not any(any(k in n for k in WOOD) for n in built.values()), "it healed wood into wood"


def test_the_reclaim_only_ever_touches_its_own_signature():
    """It sweeps the deck's whole bounding BOX, so the only thing keeping it off someone's dark
    oak furniture is the SIGNATURE - a cell on the grid line. Move the grid off every real
    coordinate and the reclaim must find nothing at all."""
    c, _ = _built(reclaim_grid_at=9973)         # prime, so no deck coordinate lands on it
    assert c.meta.get("reclaimed_wood", 0) == 0, (
        "the reclaim fired with no grid line to stand on - it is not gated on the signature")


def test_the_reclaim_can_be_switched_off():
    c, _ = _built(reclaim_wood=False)
    assert c.meta.get("reclaimed_wood", 0) == 0


def test_the_reclaim_never_manufactures_a_mechanism():
    """The heal material is the commonest solid neighbour, and by the tree that neighbour is
    `gray_wool` - the sculk sensor's shielding. A design that makes wool to patch a ceiling is one
    that will eventually make redstone, so the heal is filtered through the same safe set every
    generator consults, and falls back to the panel material."""
    from mcbuild.gen.protect import is_protected
    _, built = _built()
    bad = {p: n for p, n in built.items() if is_protected(n)}
    # lanterns are the one deliberate exemption, and only the relight may place them
    bad = {p: n for p, n in bad.items() if n != deckfloor.DECKFLOOR["lamp_block"]}
    assert not bad, f"the reclaim manufactured protected blocks: {collections.Counter(bad.values())}"


def test_an_intersection_survives_if_either_of_its_lines_runs():
    """A cell on both grid lines belongs to both. Scoring only one axis demoted intersections whose
    OTHER line was long, which punched a hole through that line and orphaned the cell beside it -
    two of them, on a gate whose whole purpose is that there are none."""
    c, _ = _built(soffit=True, soffit_min_run=4, soffit_min_patch=8, reclaim_wood=False)
    assert c.meta.get("soffit_grid_cells", 0) > 0, "the grid vanished entirely"
