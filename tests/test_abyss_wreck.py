"""The Prismworks abyssal wreck's contracts, pinned.

Every one of these is a failure this repo has shipped in some other body, or a piece of
direction it took to get here:

  one piece        it hangs in open void behind the squid, so a shed feature is not a dent,
                   it is a fragment floating in the dark - ear tips, ossicones, a dragonfly,
                   four cells off the squid's own arms, and the tower and an aft section this
                   wreck's own tears severed until they were made shallow.
  every feature    a feature that silently did not happen still audits clean, still costs a
                   correct BOM and still renders as a vessel that simply lacks it - the frog's
                   arms, the ankylosaur's horns, the squid's clubs.
  ONE rotor        Jack: "I don't think they have 2 rotors." A research submersible has one
                   ducted rotor on its centreline, dented, not a clean pair of side rings.
  a WRECK          Jack: make it feel broken. Crush craters, a shattered viewport, a snapped
                   tower and a hanging arm are what separate this from a clean sub. A crush
                   that did not remove hull ships a pristine vessel the narrative calls wrecked.
  green at wounds  Jack: "the coloring feels gimmicky... the green less concentrated." Verdigris
                   is corrosion where the sea got in, so it blooms at the caved metal and is a
                   minority accent - never a painted stripe down a dark hull.
  witnessed        the one expensive block is the viewport and is declared - not a stray
                   terracotta somebody reached for.
"""
from __future__ import annotations

import json
import math
import os
from collections import deque

import numpy as np
import pytest
import yaml

from mcbuild import palette, schem
from mcbuild.gen import abysswreck

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHIPPED = os.path.join(HERE, "out", "Abyss Prismworks Wreck.litematic")
SIDECAR = os.path.join(HERE, "out", "Abyss Prismworks Wreck.scan.json")
CONFIG = os.path.join(HERE, "configs", "abyss_wreck.yaml")

AT = [97505, 100, 80365]
SIZE = [185, 75, 90]
# the parts the generator names and the floor below which each stops being legible
FEATURES = {
    "hull": 30000, "viewport": 300, "viewport_frame": 60, "tower": 1000, "antenna": 40,
    "shaft": 100, "rotor": 500, "survey_arm": 400, "scar": 40, "breach": 200, "glass": 120,
    "fin": 400, "limber": 80,
}


@pytest.fixture(scope="module")
def built():
    return abysswreck.build({})


@pytest.fixture(scope="module")
def grey():
    return abysswreck.build({"greybox": True})


@pytest.fixture(scope="module")
def shipped():
    if not os.path.exists(SHIPPED):
        pytest.skip("Abyss Prismworks Wreck has not been generated")
    return schem.load(SHIPPED), json.load(open(SIDECAR))


def _components(occ):
    lab = np.zeros(occ.shape, np.int32)
    sizes, cur = [], 0
    for y, z, x in zip(*(a.tolist() for a in np.nonzero(occ))):
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


# --------------------------------------------------------------------- it holds together

def test_it_is_ONE_connected_piece(built):
    """It hangs in the void. A shed feature is a fragment in the dark, not a blemish.

    The tower and an aft hull section were severed by the first, deep tears; they are shallow
    top-surface peels now, clear of the tower footprint, so nothing floats.
    """
    sizes = _components(built.ids > 0)
    assert len(sizes) == 1, f"the wreck is in {len(sizes)} pieces: {sizes[:6]}"


def test_it_stays_inside_its_reservation(built, shipped):
    ys, zs, xs = np.nonzero(built.ids > 0)
    assert xs.min() >= 0 and xs.max() < SIZE[0]
    assert ys.min() >= 0 and ys.max() < SIZE[1]
    assert zs.min() >= 0 and zs.max() < SIZE[2]
    m, side = shipped
    assert (side["origin"]["x"], side["origin"]["y"], side["origin"]["z"]) == tuple(AT)


# --------------------------------------------------------------------- every feature is there

def test_every_named_feature_is_present_above_its_legible_floor(built):
    """A feature that silently did not happen audits clean and renders as a vessel lacking it."""
    counts = built.meta["features_built"]
    for name, floor in FEATURES.items():
        assert counts.get(name, 0) >= floor, (
            f"{name}={counts.get(name, 0)}, below its floor of {floor} - it did not build")


def test_there_is_exactly_ONE_ducted_rotor_on_the_centreline(built):
    """Jack: a research sub has one rotor, not two.

    One ducted rotor centres on the hull axis (z43); two side rings would cluster at z29 and z57
    and leave the centre band nearly empty. A single ring passes through the centre band via its
    top and bottom arcs, its hub and its blades.
    """
    solid, parts = set(), {}
    abysswreck._hull(solid, parts)
    zr = [q[2] for q in parts if parts[q] == "rotor"]
    assert zr, "no rotor built"
    assert 39 <= sum(zr) / len(zr) <= 47, "the rotor is not on the hull centreline"
    centre_band = sum(1 for z in zr if 40 <= z <= 46) / len(zr)
    assert centre_band >= 0.15, (
        f"only {centre_band:.0%} of rotor cells cross the centre - this reads as two side rings")


def test_the_rotor_shroud_is_DENTED_not_a_clean_ring(built):
    """A wreck's shroud is caved in - a whole angular sector is missing."""
    solid, parts = set(), {}
    abysswreck._hull(solid, parts)
    cy, cz = 32, 43
    angs = sorted(math.degrees(math.atan2(q[1] - cy, q[2] - cz)) % 360
                  for q in parts if parts[q] == "rotor"
                  and math.hypot(q[1] - cy, q[2] - cz) > 9)
    gap = max((b - a) for a, b in zip(angs, angs[1:])) if len(angs) > 1 else 360
    gap = max(gap, 360 - (angs[-1] - angs[0]) if angs else 0)
    assert gap >= 30, "the shroud ring is complete - a clean rotor, not a caved-in one"


def test_it_has_control_surfaces_at_BOTH_the_bow_and_the_stern(built):
    """The hardware that reads as SUBMARINE: bow foreplanes and a stern cruciform.

    A fin only at the stern is a rudder; a submarine needs the forward pair too. So fin cells
    must appear near the bow (x<40) AND around the stern shaft (x>160), or one set silently
    failed to build and the vessel reads as a plain hull with a tail.
    """
    solid, parts = set(), {}
    abysswreck._hull(solid, parts)
    fx = [q[0] for q in parts if parts[q] == "fin"]
    assert fx, "no control surfaces built"
    assert min(fx) < 40, "no bow foreplanes - only a stern fin, which reads as a bare hull"
    assert max(fx) > 160, "no stern cruciform around the rotor shaft"


def test_the_viewport_is_a_glazed_GRID_recessed_into_the_hull(built):
    """The window must read as a mullioned port SET INTO the flank, not a bulging blister.

    Two contracts. (1) The glass sits on the hull's own south surface (a shallow z-band), not
    proud of it on a dome - so a regression that re-adds a protruding blister spreads the glass
    across many z and fails. (2) A frame and glazing bars break the panes, so the pane count
    stays in a gridded-window band rather than a solid field of static.
    """
    import numpy as np
    names = [t.value["Name"].value.split(":")[-1] for t in built.palette]
    ys, zs, xs = np.nonzero(built.ids == names.index("cyan_stained_glass"))
    assert zs.max() - zs.min() <= 3, (
        f"glass spans z[{zs.min()},{zs.max()}] - it is bulging off the hull, not recessed into it")
    glass = built.meta["features_built"]["glass"]
    assert 120 <= glass <= 350, (
        f"glass={glass}: outside the gridded-window band - the grid was lost or over-shattered")


def test_the_limber_holes_are_a_row_aft_of_the_viewport(built):
    """Flood slots along the lower south flank, clear of the observation blister (x<76)."""
    solid, parts = set(), {}
    limber = abysswreck._hull(solid, parts)
    assert limber >= 80, f"only {limber} limber cells carved - the flood-slot row did not build"


# --------------------------------------------------------------------- it is a wreck

def test_it_reads_as_a_WRECK_not_a_clean_sub(built):
    """The crush, the breach light and the hanging arm are what the narrative promises."""
    counts = built.meta["features_built"]
    assert counts["scar"] >= 40, "the squid sucker-scars did not land on the hull"
    assert counts["breach"] >= 200, "the crushed panels left no illuminated breach"
    solid, parts = set(), {}
    abysswreck._hull(solid, parts)
    arm_y = [q[1] for q in parts if parts[q] == "survey_arm"]
    assert max(arm_y) - min(arm_y) >= 20, "no arm hangs broken; they are all at one height"


def test_the_crush_craters_actually_REMOVED_hull(built):
    """A crater is a hole. The main crush volume must be near-empty where it caved the flank."""
    ys, zs, xs = np.nonzero(built.ids > 0)
    occ = set(zip(xs.tolist(), ys.tolist(), zs.tolist()))
    cx, cy, cz = abysswreck.CRUSH[0][:3]
    core = [(x, y, z) for x in range(cx - 3, cx + 4) for y in range(cy - 3, cy + 4)
            for z in range(cz, cz + 5)]
    filled = sum(1 for q in core if q in occ)
    assert filled <= len(core) * 0.25, "the main crush did not cave the hull - it reads intact"


# --------------------------------------------------------------------- the palette is honest

def test_the_green_is_a_minority_accent_not_a_stripe(built):
    """Jack: less concentrated. All copper corrosion together is a small fraction of the skin,
    so a future change that paints a waterline stripe back on fails here."""
    shown = int((built.ids > 0).sum())
    corr = built.meta["features_built"].get("corrosion", 0)
    assert corr / shown <= 0.15, f"corrosion is {corr / shown:.0%} of the skin - too concentrated"


def test_every_expensive_block_is_a_DECLARED_instrument_and_stays_confined(built):
    """The expensive materials are the viewport and the fine instruments a Prismworks vessel
    carries - nothing spent on skin. Each is pinned to the region it belongs to, so a stray
    prismarine block on the flank (the classic 'someone reached for a nicer block') fails here,
    and the whole expensive spend stays within the config's declared allowance.
    """
    names = [t.value["Name"].value.split(":")[-1] for t in built.palette]
    expensive = {n for i, n in enumerate(names)
                 if n != "air" and (built.ids == i).any() and palette.tier(n) == "expensive"}
    # exactly the declared set - viewport glass, instrument accents, and the Prismworks insignia
    assert expensive == {"cyan_stained_glass", "dark_prismarine", "tinted_glass",
                         "amethyst_block", "sea_lantern", "prismarine_bricks"}, (
        f"undeclared expensive blocks: {expensive}")

    def box(blk, x0, x1, y0, y1, z0=0, z1=90):
        ys, zs, xs = np.nonzero(built.ids == names.index(blk))
        assert (xs.min() >= x0 and xs.max() <= x1 and ys.min() >= y0 and ys.max() <= y1
                and zs.min() >= z0 and zs.max() <= z1), f"{blk} escaped its region"

    box("cyan_stained_glass", 38, 80, 20, 55, z0=55)       # the observation blister
    box("dark_prismarine", 84, 116, 61, 71)                 # bridge coaming + scope housing
    box("tinted_glass", 98, 104, 65, 71)                    # the scope's optic
    box("prismarine_bricks", 100, 110, 50, 60)              # the sail insignia
    # amethyst is two points: the dead bow sensor and the insignia core
    ys, zs, xs = np.nonzero(built.ids == names.index("amethyst_block"))
    for x, y in zip(xs.tolist(), ys.tolist()):
        assert (6 <= x <= 14 and 13 <= y <= 21) or (100 <= x <= 110 and 50 <= y <= 60), (
            f"amethyst loose at x={x} y={y}")
    # sea lanterns (exterior build) are two points: the scope glint and the live bow sensor
    ys, zs, xs = np.nonzero(built.ids == names.index("sea_lantern"))
    for x, y in zip(xs.tolist(), ys.tolist()):
        assert (98 <= x <= 104 and 68 <= y <= 72) or (1 <= x <= 7 and 40 <= y <= 46), (
            f"a sea lantern is loose at x={x} y={y}")

    total = sum(int((built.ids == names.index(n)).sum()) for n in expensive)
    cfg = yaml.safe_load(open(CONFIG))
    assert cfg.get("expensive_allowance", 0) >= total, (
        f"expensive spend {total} exceeds the declared allowance")


def test_it_meets_its_own_material_and_size_quality_bar(built):
    names = [t.value["Name"].value.split(":")[-1] for t in built.palette]
    used = [n for i, n in enumerate(names) if n != "air" and (built.ids == i).any()]
    assert len(used) >= 7
    assert int((built.ids > 0).sum()) >= 30000


# --------------------------------------------------------------------- both review views agree

# --------------------------------------------------------------------- the walkable interior

@pytest.fixture(scope="module")
def interior():
    return abysswreck.build({"interior": True})


def _reachable_air(occ):
    """Flood-fill air from a definite-exterior corner; returns the reached mask."""
    seen = np.zeros(occ.shape, bool)
    air = ~occ
    s = (occ.shape[0] - 1, 0, 0)
    seen[s] = True
    q = deque([s])
    while q:
        y, z, x = q.popleft()
        for dy, dz, dx in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            a, b, c = y + dy, z + dz, x + dx
            if (0 <= a < occ.shape[0] and 0 <= b < occ.shape[1] and 0 <= c < occ.shape[2]
                    and air[a, b, c] and not seen[a, b, c]):
                seen[a, b, c] = True
                q.append((a, b, c))
    return seen


def test_the_fitted_interior_is_ONE_connected_piece(interior):
    """Furniture must be anchored - the whole hull, decks and fittings are one body. This has
    regressed twice (floating bunks, pipe runs, diagonal stairs), so it is pinned."""
    sizes = _components(interior.ids > 0)
    assert len(sizes) == 1, f"the fitted interior is in {len(sizes)} pieces: {sizes[:8]}"


def test_you_can_walk_from_the_breach_into_every_dry_compartment(interior):
    """The crush breach is the ONLY way in; from it the deck of each dry compartment is reachable.

    The engine room is deliberately flooded, so it is reached by wading (water, not air) and is
    excluded from the air-reachability check."""
    seen = _reachable_air(interior.ids > 0)
    dy = abysswreck.DECK_Y + 1
    for name, mx in (("bow_trim", 29), ("observation_lounge", 61),
                     ("control_room", 95), ("crew_quarters", 126)):
        assert seen[dy, 43, mx], f"{name} is not reachable on foot from the breach"


def test_the_deck_has_standing_headroom(interior):
    """Two clear cells above the deck at each compartment centre - a player fits."""
    occ = interior.ids > 0
    dy = abysswreck.DECK_Y
    for mx in (29, 61, 95, 126):
        assert not occ[dy + 1, 43, mx] and not occ[dy + 2, 43, mx], f"no headroom at x={mx}"


def test_every_compartment_is_actually_furnished(interior):
    """A silently empty compartment audits clean and ships as a bare tube. Pin the fittings."""
    fb = interior.meta["features_built"]
    for k, floor in {"deck": 3000, "bulkhead": 2000, "mezz": 200, "machine": 300,
                     "console": 200, "bunk": 50, "pipe": 200, "water": 3000}.items():
        assert fb.get(k, 0) >= floor, f"{k}={fb.get(k, 0)} below its floor {floor} - it did not build"


def test_the_hull_carries_its_commissioned_markings(built):
    """Hull number, draft marks and the Prismworks insignia - the vessel is a ship, not a shape."""
    fb = built.meta["features_built"]
    assert fb.get("mark", 0) >= 40, "the hull number / draft marks did not paint"
    assert fb.get("insignia", 0) >= 8, "the Prismworks insignia did not paint"


def test_the_greybox_and_the_detailed_wreck_are_the_same_object(built, grey):
    """The sheet is reviewed as the greybox; the world gets the detailed one. Same silhouette.

    The detailed pass recolours the shell and lights a few cells; every one must sit within the
    greybox's solid, or a review approved a shape that was not shipped.
    """
    det = built.ids > 0
    solid = grey.ids > 0
    stray = int((det & ~solid).sum())
    assert stray == 0, f"{stray} detailed cells lie outside the greybox solid"
