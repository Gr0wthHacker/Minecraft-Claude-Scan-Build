"""The heron and the bat: the two builds that play to what this medium is good at.

Both exist because of a finding, not a preference. Players picked out the sky bird (planar wings)
and the giraffe (a column) as the best animals on the island; every mammal that read badly read
badly for the same reason - a cat's shoulder and a bear's haunch are COMPOUND VOLUMETRIC MUSCLE,
which voxels describe worst of anything. These two have no volumetric component at all.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import pytest
from mcbuild import morph
from mcbuild.gen import GENERATORS, bat, heron


def _solid(c):
    return c.to_model().ids > 0


@pytest.mark.parametrize("name", ["heron", "bat"])
def test_it_is_registered_and_builds(name):
    assert name in GENERATORS
    c = GENERATORS[name].build({"scale": 1.0, "seed": 0}, None)
    assert _solid(c).sum() > 400, "a bird that small is not a bird"


@pytest.mark.parametrize("name", ["heron", "bat"])
def test_one_connected_piece(name):
    """A design in pieces cannot be built, whatever it looks like."""
    c = GENERATORS[name].build({"scale": 1.0, "seed": 0}, None)
    _lab, sizes = morph.components(_solid(c), conn=6)
    assert len(sizes) == 1, f"{name} came out in {len(sizes)} pieces"


@pytest.mark.parametrize("name", ["heron", "bat"])
def test_scale_adds_DETAIL_not_just_size(name):
    """The whole argument for these two is that they get better with blocks rather than blurrier.
    Feather courses and finger struts are counted, so more scale must mean MORE of them."""
    small = GENERATORS[name].build({"scale": 1.0, "seed": 0}, None).meta["features_built"]
    big = GENERATORS[name].build({"scale": 2.0, "seed": 0}, None).meta["features_built"]
    grew = [k for k in small if big[k] > small[k]]
    assert grew, f"{name} gains no extra detail at 2x: {small} -> {big}"


def test_the_heron_is_TALLER_than_it_is_wide():
    """A wading bird's whole silhouette claim is that it is a column with a beak. If it ever comes
    out wider than it is tall, something has collapsed."""
    c = GENERATORS["heron"].build({"scale": 1.0, "seed": 0}, None)
    s = _solid(c)
    ys, zs, xs = np.nonzero(s)
    assert (ys.max() - ys.min()) > (xs.max() - xs.min()) * 1.5


def test_the_bat_hangs_from_the_TOP_of_its_box():
    """It grips a ceiling. If the feet drift off the top course it is a bat falling, not hanging,
    and it will not meet the roof it is placed against."""
    c = GENERATORS["bat"].build({"scale": 1.0, "seed": 0}, None)
    s = _solid(c)
    assert s[-1].any(), "nothing touches the roof"


def test_the_bat_is_WIDER_than_it_is_deep():
    """Its wings spread across x and it is a sheet front-to-back. A bat as deep as it is wide has
    become a volume, which is the exact thing these builds exist to avoid."""
    c = GENERATORS["bat"].build({"scale": 1.0, "seed": 0}, None)
    ys, zs, xs = np.nonzero(_solid(c))
    assert (xs.max() - xs.min()) > (zs.max() - zs.min()) * 2


def test_a_build_can_name_its_own_best_view():
    """A hanging bat's head points at the FLOOR, so `facing` says nothing useful about it - the
    panel's facing rule rendered it edge-on as a sliver two blocks wide."""
    c = GENERATORS["bat"].build({"scale": 1.0, "seed": 0}, None)
    assert c.meta.get("profile_view") == "face"


@pytest.mark.parametrize("name", ["heron", "bat"])
def test_world_origin_is_set_when_asked(name):
    """A bespoke generator must state its own world origin or the pipeline writes no sidecar - and
    without a sidecar there is no in-context audit and no `/cscan place`."""
    c = GENERATORS[name].build({"scale": 1.0, "seed": 0, "at": [-24200, 37, 29990]}, None)
    assert getattr(c, "world_origin", None) == (-24200, 37, 29990)


def test_palettes_avoid_functional_blocks():
    bad = ("furnace", "chest", "barrel", "hopper", "spawner", "lantern", "campfire", "bee_nest")
    # The rule bans a functional block used for its COLOUR - `bee_nest` is the closest golden tan
    # in the game and it carries a face texture and bee states. A light source used AS A LIGHT is
    # not that: the ruin on the bat's perch burns a lantern because nothing else out there does,
    # and `lowland` stands 71 of them for the same reason. So light params are exempt BY NAME -
    # never by relaxing `bad`, which is what stops the next tan-coloured bee nest.
    lights = {"ruin_lamp"}
    for mod in (heron.HERON, bat.BAT):
        for k, v in mod.items():
            if isinstance(v, str) and k not in lights:
                assert not any(b in v for b in bad), f"{k}={v} is a functional block"


_RUIN = {"scale": 1.0, "seed": 0, "perch": True, "perch_h": 8, "perch_r": 8.5,
         "ruin": True, "ruin_h": 10, "ruin_r": 4.6}


def test_the_ruin_never_builds_off_the_rock():
    """The wall walks a circle, and the rock under it is deliberately RAGGED. A column with no
    rock beneath it is masonry hanging in the air - which is how the perch's own vines came away
    as nine floating threads the first time."""
    c = GENERATORS["bat"].build(_RUIN, None)
    s = _solid(c)
    floating = [(x, y, z) for y in range(1, s.shape[0])
                for z in range(s.shape[1]) for x in range(s.shape[2])
                if s[y, z, x] and not s[y - 1, z, x]
                and not (s[y, z, max(0, x - 1)] or s[y, z, min(s.shape[2] - 1, x + 1)]
                         or s[y, max(0, z - 1), x] or s[y, min(s.shape[1] - 1, z + 1), x])]
    assert not floating, f"{len(floating)} unsupported cells, e.g. {floating[:3]}"


def test_the_ruin_leaves_the_bat_gripping_the_roof():
    """Sizing the canvas for the ruin moves the ceiling the claws hold. Grown by one course too
    many, every bat in the repo quietly stopped touching its roof - including the ones with no
    ruin at all, because the growth was unconditional."""
    for cfg in ({"scale": 1.0, "seed": 0}, _RUIN):
        c = GENERATORS["bat"].build(cfg, None)
        s = _solid(c)
        ph = int(cfg.get("perch_h", 0)) if cfg.get("perch") else 0
        rh = int(cfg.get("ruin_h", 0)) if cfg.get("ruin") else 0
        assert s[s.shape[0] - 1 - ph - rh].any(), f"nothing grips the roof for {cfg.get('ruin')}"


def test_the_ruin_is_dressed_stone_against_the_rock_s_rough_stone():
    """The contrast IS the design: it is what says `built` rather than `more rock`. If the wall
    ever shares its palette with the perch the ruin stops reading as a ruin."""
    c = GENERATORS["bat"].build(_RUIN, None)
    names = {c.palette[i].value["Name"].value.split(":")[-1]
             for i in np.unique(c.to_model().ids) if i}
    assert names & {"stone_bricks", "deepslate_bricks"}, "the wall lost its masonry"
    assert not ({"stone_bricks", "deepslate_bricks"} & set(bat.BAT["rock"])),         "the ruin and the rock now share blocks - the contrast is gone"

