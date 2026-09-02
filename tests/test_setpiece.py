"""Set pieces: the one thing they must do is be nameable, and the one thing they must not do is
need explaining.

Jack's verdict on the park as shipped was that the rides and the sculptures work and *"basically
everything else is terrible"* - and the failures were all one category: a box with redstone in it
and a button on the front. So these tests assert the properties that separate a set piece from
that: no mechanism, a silhouette made of distinct masses, symmetry by construction, and the detail
vocabulary this project measured itself as thirty times short on.
"""
import pytest

from mcbuild.gen import setpiece

KINDS = sorted(setpiece.BUILDERS)
LAND = {"watertower": "frontier", "bigtop": "midway"}


def _model(kind, land=None, facing="east"):
    canvas = setpiece.build({"land": land or LAND[kind], "kind": kind,
                             "at": [0, 64, 0], "facing": facing})
    return canvas, canvas.to_model()


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("facing", ("east", "west", "north", "south"))
def test_a_set_piece_is_symmetric_at_every_facing(kind, facing):
    """The measurement that condemned the park's own buildings - Shooting Range 122%, Carousel
    126% - run against every set piece. What is allowed through is only what a builder reached for
    `Sym.one` to place: a spout, a ladder, a pennant."""
    _canvas, model = _model(kind, facing=facing)
    solid = model.solid()
    axis = 1 if facing in ("east", "west") else 2      # model axes are (y, z, x)
    flipped = solid[:, ::-1, :] if axis == 1 else solid[:, :, ::-1]
    off = int((solid ^ flipped).sum()) / max(int(solid.sum()), 1)
    assert off < 0.06, f"{kind} facing {facing} is {off:.1%} asymmetric"


@pytest.mark.parametrize("kind", KINDS)
def test_a_set_piece_has_no_mechanism_at_all(kind):
    """**THE CATEGORY THAT FAILED WAS THE ONE WITH A BUTTON ON IT.** Scenery that has to be
    figured out has already failed, so a set piece carries no redstone, no button and no
    container - there is nothing to work out and nothing to press."""
    _canvas, model = _model(kind)
    banned = ("redstone", "repeater", "comparator", "observer", "piston", "dispenser", "dropper",
              "button", "lever", "hopper", "chest", "barrel", "target", "note_block")
    found = [n for n in model.names if any(b in n for b in banned)]
    assert not found, f"{kind} carries a mechanism: {found}"


@pytest.mark.parametrize("kind", KINDS)
def test_a_set_piece_is_one_connected_piece(kind):
    """A silhouette in fragments is not a silhouette."""
    from mcbuild import morph
    _canvas, model = _model(kind)
    _labels, sizes = morph.components(model.solid(), conn=6)
    assert len(sizes) == 1, f"{kind} is in {len(sizes)} pieces: {sorted(sizes, reverse=True)[:5]}"


@pytest.mark.parametrize("kind", KINDS)
def test_a_set_piece_is_cheap_and_the_server_can_supply_it(kind):
    """Rules 12 and 16 together: the 1.19 server must have it, and dirt is currency here."""
    from mcbuild import blocks, palette
    _canvas, model = _model(kind)
    for name in model.names:
        bare = name.split(":")[-1].split("[")[0]
        if bare == "air":
            continue
        assert palette.tier(bare) != "expensive", f"{kind} spends {bare}"
        assert blocks.spendable(bare), f"{kind} builds out of currency: {bare}"


@pytest.mark.parametrize("kind", KINDS)
def test_a_set_piece_uses_the_details_we_are_short_on(kind):
    """Against 31 outside builds, per thousand cells: stairs 0.64 vs 4.51, fences 0.07 vs 2.22."""
    _canvas, model = _model(kind)
    names = {n.split(":")[-1].split("[")[0] for n in model.names}
    assert any(n.endswith("_stairs") for n in names), f"{kind} places no stairs"
    assert any(n.endswith("_fence") for n in names), f"{kind} places no fences"


def test_the_tower_is_three_masses_and_the_middle_one_is_the_widest():
    """**THE TANK HAS TO BE ROUND AND FAT.** Built square the first time the whole thing read as a
    pagoda on stilts: thin legs, a fat drum and a point only name a water tower when the middle
    mass is genuinely the widest. A silhouette of three equal boxes is a different object."""
    canvas, model = _model("watertower")
    solid = model.solid()
    legs, tank = canvas.meta["legs"], canvas.meta["tank"]
    # Measured as MASS per course, not as width. A cross-brace spans the full trestle and is two
    # cells of timber, so by width a braced course reads exactly as wide as the tank it carries -
    # which is true of the bounding box and false of anything a viewer sees.
    mass = lambda h: int(solid[h].sum())
    trestle = max(mass(h) for h in range(1, legs - 1))
    barrel = max(mass(h) for h in range(legs, legs + tank))
    assert barrel > 2 * trestle, f"the tank ({barrel}) is no fatter than the trestle ({trestle})"

    # And it must OVERHANG: a tank flush with its own legs is a silo.
    span = lambda h: int(solid[h].any(axis=0).sum())
    assert max(span(h) for h in range(legs, legs + tank)) > span(0) + 1, "the tank does not overhang"


def test_the_tents_cone_is_watertight():
    """**A CONE OF ONE-CELL RINGS IS SEE-THROUGH.** The first build had daylight between every
    band, because consecutive radii step in by about one and a shell that thin leaves a diagonal
    gap. Looking straight down, the canvas must cover its own floor."""
    canvas, model = _model("bigtop")
    solid = model.solid()
    radius = canvas.meta["radius"]
    covered = solid.any(axis=0)
    cy, cx = covered.shape[0] // 2, covered.shape[1] // 2
    holes = [(dz, dx) for dz in range(-radius + 2, radius - 1)
             for dx in range(-radius + 2, radius - 1)
             if dz * dz + dx * dx <= (radius - 2) ** 2 and not covered[cy + dz, cx + dx]]
    assert not holes, f"{len(holes)} cells of the tent are open to the sky, e.g. {holes[:4]}"


def test_a_set_piece_refuses_a_land_it_has_no_palette_for():
    with pytest.raises(ValueError):
        setpiece.build({"land": "nowhere", "kind": "bigtop", "at": [0, 64, 0]})
    with pytest.raises(ValueError):
        setpiece.build({"land": "midway", "kind": "not_a_thing", "at": [0, 64, 0]})
    with pytest.raises(ValueError):
        setpiece.build({"land": "midway", "kind": "bigtop"})
