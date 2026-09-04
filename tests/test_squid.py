"""The Abyss Squid's contracts, pinned.

Every one of these is a failure this repo has actually shipped, in some other body:

  the keep-out        a truncated tentacle club renders as a perfectly good short club, and the
                      first siting cut 1,443 cells off two of them in silence
  one piece           a swept limb sheds its tip as a diagonal neighbour - ear tips, ossicones,
                      a whole dragonfly, and four cells off this animal's own arms
  the mirror          the frog shipped 104 unmirrored cells from a mass that was symmetric by
                      construction, because its coat carried a signed offset per drift
  witnessed blocks    `nether_wart_block` is cheap by the tier table, legal in 1.19 and has
                      NEVER been seen in this world. 90,766 of them shipped once. And the first
                      photophore was `verdant_froglight`, which is "witnessed" only because one
                      of our own designs in `out/` places it - a witness set built from `out/`
                      is circular, so this reads the CAPTURES
  every feature       a feature that silently did not happen still audits clean, still costs a
                      correct BOM and still renders as an animal that simply lacks it
"""
from __future__ import annotations

import json
import math
import os
from collections import deque

import numpy as np
import pytest

from mcbuild import blocks, palette, schem
from mcbuild.gen import squid

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHIPPED = os.path.join(HERE, "out", "Abyss Squid.litematic")
SIDECAR = os.path.join(HERE, "out", "Abyss Squid.scan.json")
CAPTURES = ("island_full.litematic", "island_now.litematic", "islandlow.litematic")

AT = [97522, 98, 80485]
KEEP_OUT = [97590.0, 80815.0, 56.0]      # the Prism Well's fall column: x, z, r


@pytest.fixture(scope="module")
def built():
    return squid.build({"at": list(AT), "keep_out": list(KEEP_OUT)})


@pytest.fixture(scope="module")
def shipped():
    if not os.path.exists(SHIPPED):
        pytest.skip("Abyss Squid has not been generated")
    return schem.load(SHIPPED), json.load(open(SIDECAR))


def _components(occ):
    lab = np.zeros(occ.shape, np.int32)
    sizes, cur = [], 0
    ys, zs, xs = np.nonzero(occ)
    for y, z, x in zip(ys.tolist(), zs.tolist(), xs.tolist()):
        if lab[y, z, x]:
            continue
        cur += 1
        q, n = deque([(y, z, x)]), 0
        lab[y, z, x] = cur
        while q:
            Y, Z, X = q.popleft()
            n += 1
            for dy, dz, dx in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
                a, b, c = Y + dy, Z + dz, X + dx
                if (0 <= a < occ.shape[0] and 0 <= b < occ.shape[1] and 0 <= c < occ.shape[2]
                        and occ[a, b, c] and not lab[a, b, c]):
                    lab[a, b, c] = cur
                    q.append((a, b, c))
        sizes.append(n)
    return sorted(sizes, reverse=True)


def _witnessed():
    seen = set()
    for name in CAPTURES:
        p = os.path.join(HERE, "out", name)
        if not os.path.exists(p):
            continue
        m = schem.load(p)
        names = [t.value["Name"].value.split(":")[-1] for t in m.palette]
        used = np.bincount(m.ids.ravel(), minlength=len(names))
        seen |= {n for i, n in enumerate(names) if used[i]}
    return seen


# --------------------------------------------------------------------- the fall column


def test_NOTHING_ENTERS_THE_PRISM_WELLS_FALL_COLUMN(built):
    """The one contract a person could be hurt by.

    Below Y187 the well is open void with two parkour helices at r19-35 in it, and a runner who
    misses a landing falls eighty-six courses. A surface inside that column does not save one,
    it strands one sixty blocks out in the void with no way back.
    """
    ys, zs, xs = np.nonzero(built.ids > 0)
    ox, _, oz = built.world_origin
    d = np.hypot(ox + xs - KEEP_OUT[0], oz + zs - KEEP_OUT[1])
    assert d.min() >= KEEP_OUT[2], f"closest cell is {d.min():.1f} from the well axis"


def test_the_siting_refuses_NOTHING_so_no_limb_is_silently_truncated(built):
    """A refusal is not a safe failure - it is a shorter tentacle nobody can see is shorter.

    At Z80491 this design refused 1,443 cells off the two tentacle clubs, reported `problems: 0`,
    a correct BOM and one connected piece. The siting was swept back until the count was zero.
    """
    assert built.meta["refused_by_keep_out"] == 0


def test_the_reported_clearance_is_the_MEASURED_one(built):
    """The sidecar's number and the blocks must agree, or the number is decoration."""
    ys, zs, xs = np.nonzero(built.ids > 0)
    ox, _, oz = built.world_origin
    d = np.hypot(ox + xs - KEEP_OUT[0], oz + zs - KEEP_OUT[1]).min()
    assert abs(built.meta["closest_to_keep_out"] - d) < 0.15


# --------------------------------------------------------------------- the band it hangs in


def test_it_stays_inside_the_parks_own_shadow_and_under_its_floor(shipped):
    """X within the park's placed 200-wide shadow, and clear of the plate overhead.

    The lowest park block over this footprint is Y196, and the well's own lining runs Y187-195
    within r52. Nothing here may reach either.
    """
    m, side = shipped
    o = side["origin"]
    ys, zs, xs = np.nonzero(m.ids > 0)
    assert 97500 <= o["x"] + xs.min() and o["x"] + xs.max() <= 97699
    assert o["y"] + ys.max() <= 190, "reaches into the park's underside"
    assert o["y"] + ys.min() >= 96


def test_it_clears_the_frontiers_own_shaft(shipped):
    """Twelve columns at Z80399..80443 are the only other thing in the whole deep band."""
    m, side = shipped
    o = side["origin"]
    _, zs, _ = np.nonzero(m.ids > 0)
    assert o["z"] + zs.min() > 80455


# --------------------------------------------------------------------- one animal


def test_it_is_ONE_connected_piece(shipped):
    """6-connected, on the artifact the printer is actually handed.

    A swept ball of radius 0.55 at an arm's tip covers one cell, and two consecutive centres
    can round to cells that are only DIAGONAL neighbours. That shed four cells off three arms
    here and the component count was the only thing that could see it.
    """
    m, _ = shipped
    comps = _components(m.ids > 0)
    assert len(comps) == 1, f"components {comps[:6]}"


def test_the_SHAPE_is_symmetric_by_construction(built):
    """The enforcement is a guarantee, not the fix, and it reports the two halves separately.

    The real fault was a half-block: the limbs were swept about `float(XC)`, which is the
    column's EDGE, while `Canvas` tests cell CENTRES at x + 0.5 - so the mirror plane sat half a
    block off and 3,521 cells of SHAPE came out different left to right, a tenth of the animal.
    Fixed, that is 36, all of them cell-boundary rounding ties.

    Colour is a different fact and the enforcement legitimately owns it: an arm's stripe and its
    suckers are found by walking a ray that can start exactly on a cell boundary, and `round()`
    is banker's rounding, which does not mirror at a .5 tie. Bounded, not zero.
    """
    f = built.meta["features_built"]
    assert f["mirror_shape_fixed"] < 60, "the mass itself has stopped being symmetric"
    assert f["mirror_paint_fixed"] < 2000


def test_the_mirror_holds_in_GEOMETRY_AND_IN_COLOUR(built):
    """Mirrored by construction about an integer centre column, so it cannot drift.

    Colour as well as shape: a dark patch reads as a RECESS, so an unmirrored coat looks like a
    body dented down one side. The frog shipped 104 such cells.
    """
    ids = built.ids
    xc = built.sx // 2
    half = min(xc, built.sx - 1 - xc)
    left = ids[:, :, xc - half:xc]
    right = ids[:, :, xc + 1:xc + 1 + half][:, :, ::-1]
    bad = int((left != right).sum())
    assert bad == 0, f"{bad} cells differ across the sagittal plane"


def test_the_body_axis_never_wanders_off_the_block_grid(built):
    """All of the curve is in Y. A head aimed off cardinal is a diagonal staircase of corners in
    game and reads as a blob, while every orthographic sheet de-jags it by construction - the
    axolotl's recorded failure, and the reason this animal's gaze is due +Z."""
    assert list(built.meta["facing"]) == [0, 1]


# --------------------------------------------------------------------- the shape


def _girth_profile(ids):
    """The body's own height at the centre column, per z.

    Measured at x = the sagittal plane and NOT as a bounding width, because the fins are a sheet
    45 cells out and they are legitimately the widest thing on the animal - a width profile
    reports them as the mantle and calls a correct cone a cigar.
    """
    occ = ids > 0
    xc = occ.shape[2] // 2
    out = []
    for z in range(occ.shape[1]):
        ys = np.nonzero(occ[:, z, xc])[0]
        out.append(0 if not len(ys) else ys.max() - ys.min() + 1)
    return out


def test_the_mantle_is_a_CONE_and_never_a_cigar(built):
    """Widest at the collar and tapering all the way to the point - MEASURED, not declared.

    The first build peaked at 0.60 of its own length, which is a cigar, and the panel read it as
    a constant-depth wedge with no line in it: the jaguar's own recorded failure. Asserted
    against the generator's own table it would have passed either way, so it is asserted against
    the blocks.
    """
    g = _girth_profile(built.ids)
    zs = [z for z, v in enumerate(g) if v > 0]
    run = [g[z] for z in range(zs[0], zs[0] + 166)]
    assert run[-1] >= max(run) - 1, "the mantle is not widest at its collar"
    smooth = [max(run[max(0, i - 5):i + 6]) for i in range(len(run))]
    drops = sum(1 for a, b in zip(smooth, smooth[1:]) if b < a - 1)
    assert drops == 0, f"the mantle's own outline falls back {drops} times before the collar"


def test_the_head_PINCHES_behind_the_eyes(built):
    """A neck, or the animal reads as a worm with a face - the axolotl's own finding.

    Measured on the built model: between the mantle's collar and the eye bulge there has to be
    a course that is genuinely narrower than both.
    """
    f = built.meta["features_built"]
    assert f["head"] > 0
    g = _girth_profile(built.ids)
    zs = [z for z, v in enumerate(g) if v > 0]
    # the head occupies the last stretch before the arm crown widens the profile again
    tail = g[zs[0] + 150:zs[0] + 200]
    tail = [v for v in tail if v > 0]
    assert min(tail) < max(tail) * 0.92, "no neck between the mantle and the head"


def test_EVERY_FEATURE_ACTUALLY_EXISTS(built):
    """A feature that silently did not happen audits clean and costs a correct BOM.

    This repo has shipped a frog with no arms, a ladybird with no spots, an axolotl whose gills
    were inside its own skull and two feet whose lamps were never placed - every one of them
    reported zero problems.
    """
    f = built.meta["features_built"]
    for part in ("mantle", "head", "fin", "arm", "tentacle", "club", "funnel",
                 "eye", "eye_organ", "sucker", "photophore", "arm_stripe", "beak"):
        assert f.get(part, 0) > 0, f"{part} was never built"


def test_there_are_eight_arms_and_two_LONGER_tentacles(built):
    p = squid.SQUID
    assert p["arms"] == 8
    assert p["tent_len"] > p["arm_len"], "the hunting tentacles must be the long pair"
    assert p["club_r"] > p["tent_r"] * 1.6, "a club has to be visibly wider than its stalk"


def test_BOTH_eyes_are_built(built):
    """The wyrm shipped with ONE eye, twice, because the probe was a computed offset onto a
    course whose two sides are asymmetric about the midline. Here the mirror test would catch a
    missing one, so this asserts the pupils exist as real discs on both flanks."""
    f = built.meta["features_built"]
    assert f["eye"] > 200, "the eyes are too small to be eye-shaped"
    assert f["eye"] % 2 == 0, "an odd cell count means one eye differs from the other"
    assert f["eye_organ"] > 0, "the light organs under the eyes were never placed"


# --------------------------------------------------------------------- what it is made of


def test_EVERY_BLOCK_IS_WITNESSED_IN_A_WORLD_CAPTURE(shipped):
    """Rule 12, and the one that would have sunk this build.

    The first coat was `nether_wart_block` - cheap by the tier table, legal in 1.19, and it has
    never been seen in this world: 90,766 blocks of a material with no evidence behind it. The
    witness has to come from a CAPTURE and never from `out/`, because `out/` contains our own
    unbuilt designs - which is how `verdant_froglight` "passed" the first time.
    """
    seen = _witnessed()
    if not seen:
        pytest.skip("no world capture available to witness against")
    m, _ = shipped
    for t in m.palette:
        n = t.value["Name"].value.split(":")[-1]
        if n == "air":
            continue
        assert n in seen, f"{n} has never been seen in this world"


def test_nothing_in_it_is_expensive_or_currency(shipped):
    m, _ = shipped
    for t in m.palette:
        n = t.value["Name"].value.split(":")[-1]
        if n == "air":
            continue
        assert palette.tier(n) == "cheap", f"{n} is {palette.tier(n)} tier"
        assert blocks.spendable(n), f"{n} is currency on this server"


def test_the_coat_is_a_REAL_VALUE_LADDER(built):
    """Measured ACROSS families, never inside one - this repo drew the opposite conclusion four
    times by searching within a single material, where a ladder cannot exist by construction."""
    def lum(n):
        r, g, b = blocks.color(n, "side")
        return 0.299 * r + 0.587 * g + 0.114 * b
    rungs = sorted(lum(squid.SQUID[k]) for k in ("dark", "deep", "lift", "pale", "sucker"))
    steps = [b - a for a, b in zip(rungs, rungs[1:])]
    assert min(steps) >= 40, f"rungs {[round(r) for r in rungs]} step {[round(s) for s in steps]}"


def test_deep_and_mid_are_a_MOTTLE_rather_than_a_second_rung(built):
    """They sit at the same luminance on purpose: a chromatophore changes the colour of a skin
    without breaking the form the value gradient describes."""
    def rgb(n):
        return blocks.color(n, "side")
    def lum(n):
        r, g, b = rgb(n)
        return 0.299 * r + 0.587 * g + 0.114 * b
    a, b = squid.SQUID["deep"], squid.SQUID["mid"]
    assert abs(lum(a) - lum(b)) < 12, "a mottle must not also be a value step"
    assert math.dist(rgb(a), rgb(b)) > 30, "...and it must still be a visible change of colour"


def test_it_carries_its_own_light_because_the_void_has_none(shipped):
    """114,267 of the park's 120,000 shadow columns have something overhead, so there is no sky
    light down there at any hour. An unlit animal in that void is not a dark animal, it is an
    absent one."""
    m, _ = shipped
    names = [t.value["Name"].value.split(":")[-1] for t in m.palette]
    used = np.bincount(m.ids.ravel(), minlength=len(names))
    lamps = sum(int(used[i]) for i, n in enumerate(names)
                if n.endswith("froglight") or n == "glow_lichen")
    assert lamps > 300, f"only {lamps} light-emitting cells"
