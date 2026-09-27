"""THE RIB WALK - the colossal skeleton the causeway is cut through.

WHAT THIS FILE IS FOR. `tests/test_isthmus.py` owns the causeway's own contracts and
`tests/test_causeway_sculptures.py` owns the pieces that stand ON it. This one owns the piece
that the causeway goes THROUGH, and every check here is about that relationship rather than about
the shape in isolation - because the shape in isolation is a ribcage in six pieces with a hole in
the middle of it, and that is CORRECT.

**THE DESIGN ALONE IS IN MANY PIECES AND THE COMPOSITE IS THE TRUTH.** The Mine Ridge records the
same situation in its own words - "the design alone is in six pieces and that is correct... the
composite is the truth" - and it arises here for the same reason: the deck cuts every rib in two,
which is the whole effect. A test that demanded one piece from the design alone would be demanding
that the causeway not pass through it.

Six subjects were block-out and rejected for this stop before this one - an ankylosaur, an
ammonite, a pterosaur skull, a hatching egg, a giant dragonfly, a claw, a tree fern - and the
fault they shared was the REGISTER: each was an object standing BESIDE the walk. What is asserted
here is the thing that makes this one different, which is that it uses its site.
"""
import json

import numpy as np
import pytest

from mcbuild import blocks, morph, nbt, palette, schem
from mcbuild.gen import ribwalk

CAUSEWAY = 'out/Isthmus.litematic'
DESIGN = 'out/PF Rib Walk.litematic'


def _at():
    return tuple(int(v) for v in ribwalk.RIBWALK["at"] or (0, 0, 0))


@pytest.fixture(scope="module")
def built():
    """The shipped design, with the causeway refused - which is how it is actually generated."""
    cfg = json.load(open('out/PF Rib Walk.scan.json'))
    o = cfg["origin"]
    c = ribwalk.build_ribwalk({"length": 75, "facing": "north",
                               "at": [o["x"], o["y"], o["z"]],
                               "skull": False, "refuse": [CAUSEWAY]})
    return c, c.to_model(), (o["x"], o["y"], o["z"])


def _world_cells(path):
    m = schem.load(path)
    sc = json.load(open(path.rsplit('.', 1)[0] + '.scan.json'))
    ox, oy, oz = sc["origin"]["x"], sc["origin"]["y"], sc["origin"]["z"]
    ys, zs, xs = (m.ids > 0).nonzero()
    return {(ox + int(x), oy + int(y), oz + int(z))
            for y, z, x in zip(ys.tolist(), zs.tolist(), xs.tolist())}, m


def test_it_takes_NOT_ONE_CELL_THE_CAUSEWAY_OWNS(built):
    """**REFUSED CELL BY CELL, so `overlap 0` is a property of the construction.** The Wyrm Gate
    does the same to a live railway. It is not politeness: the refusal IS the effect, because a rib
    that stops at the paving and picks up again underneath is what makes the bridge read as a cut
    through a fossil rather than as a hoop over a path."""
    c, m, (ox, oy, oz) = built
    cause, _cm = _world_cells(CAUSEWAY)
    ys, zs, xs = (m.ids > 0).nonzero()
    mine = {(ox + int(x), oy + int(y), oz + int(z))
            for y, z, x in zip(ys.tolist(), zs.tolist(), xs.tolist())}
    clash = mine & cause
    assert not clash, f"{len(clash)} cells of the causeway taken, e.g. {sorted(clash)[:4]}"
    assert c.meta["declined"] > 0, \
        "nothing was declined at all - the cage is not passing through the deck, it is beside it"


def test_the_WALK_STAYS_CLEAR(built):
    """A sculpture the causeway goes through must not be a sculpture the causeway stops at.

    The spine walk is the middle of the deck; nothing of this design may stand in it, at foot or
    at head height. Measured as the corridor a guest occupies rather than as a cell count, because
    a single rib in the middle of a path is a wall however few blocks it is.
    """
    _c, m, (ox, oy, oz) = built
    ys, zs, xs = (m.ids > 0).nonzero()
    bad = [(ox + int(x), oy + int(y), oz + int(z))
           for y, z, x in zip(ys.tolist(), zs.tolist(), xs.tolist())
           if abs(ox + int(x) - 97595) <= 7 and 203 <= oy + int(y) <= 205]
    assert not bad, f"{len(bad)} cells stand in the walking corridor, e.g. {bad[:4]}"


def test_it_CARRIES_ON_BELOW_THE_DECK_into_the_void(built):
    """**THE MOVE ONLY THIS BRIDGE CAN OFFER.** A guest at the rail looks down and the cage is
    still there with nothing under it. Anything less is a hoop over a path, which is what every
    rejected subject before this one was - an object standing beside the walk."""
    _c, m, (ox, oy, oz) = built
    ys = (m.ids > 0).nonzero()[0]
    below = int(((ys + oy) < 202).sum())
    above = int(((ys + oy) > 202).sum())
    assert below > 400, f"only {below} cells hang below the deck: the void is not being used"
    assert below > above * 0.20, \
        f"{below} below against {above} above - the drop reads as a fringe rather than as half a cage"


def test_it_is_a_CAGE_and_not_a_tunnel(built):
    """**THE SKY BETWEEN THE RIBS IS THE FEATURE**, the same rule as the frog's hand and the
    ladybird's spot spacing. Twenty hoops touching each other are a culvert with stripes on it,
    which is what the first block-out was: at four cells thick per rib the arch closed over and
    the whole point went with it, and thinning them to one cell is what took the model from seven
    pieces to three hundred and sixty until the ribs were THREADED rather than swept.

    **MEASURED AT A WALKER'S OWN EYE HEIGHT.** The first version of this check sampled six courses
    under the crown and reported 31% sky - which is true and is not the question, because near the
    spine every rib converges on it by construction and the neural spines fill what is left. What
    a guest sees is the band just over the deck, where the ribs are furthest apart: 21 ribs across
    85 columns, three quarters of it open.
    """
    _c, m, (ox, oy, oz) = built
    solid = m.ids > 0
    worst = 1.0
    for wy in (204, 206, 208, 212):
        y = wy - oy
        if not (0 <= y < solid.shape[0]):
            continue
        zs = [z for z in range(solid.shape[1]) if solid[y, z, :].any()]
        if len(zs) < 4:
            continue
        worst = min(worst, 1.0 - len(zs) / float(max(zs) - min(zs) + 1))
    assert worst > 0.55,         f"only {worst:.0%} of the cage's length is sky at eye height: that is a tunnel"


@pytest.mark.parametrize("facing", ["north", "south", "east", "west"])
def test_it_builds_whole_at_every_facing(facing):
    """Nothing clipped and nothing refused, at every orientation it could be sited at. A refusal
    off the end of the box is the sauropod's recorded disaster - clipped to 22 blocks of 48, with
    a render that still showed a plausible animal - and it cost this design 25,565 cells before
    the deck's height was derived from the drop rather than passed in."""
    c = ribwalk.build_ribwalk({"length": 75, "facing": facing, "skull": False})
    assert c.meta["clipped"] == 0, f"facing {facing} clips {c.meta['clipped']} cells"
    assert c.meta["refused"] == 0, f"facing {facing} refuses {c.meta['refused']} below the floor"
    _lab, sz = morph.components(c.to_model().ids > 0, conn=6)
    assert len(sz) == 1, f"facing {facing} builds in {len(sz)} pieces - unrefused it is one cage"


def test_every_block_is_spendable_available_and_not_dear():
    """Rule 16 and rule 12: real, in 1.19, not currency, and not `expensive` on this economy."""
    c = ribwalk.build_ribwalk({"length": 75, "skull": False})
    names = {nbt.state_name(e).split(":")[-1] for e in c.palette} - {"air"}
    for n in names:
        assert blocks.exists(n), n
        assert blocks.spendable(n), f"{n} is CURRENCY on this server"
        assert palette.tier(n) != "expensive", f"{n} is dear"


def test_it_REFUSES_a_length_it_cannot_be_walked_through_at():
    """Below the size at which the arch clears a guest's head over a deck that is already thirteen
    wide, it is a hoop over a path rather than a cage you are inside - so it says so."""
    with pytest.raises(ValueError, match="walked through"):
        ribwalk.build_ribwalk({"length": 40})
