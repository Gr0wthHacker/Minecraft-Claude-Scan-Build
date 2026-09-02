"""What the park's frontage must never do, and what it must always be.

**THE ONE RULE WHOSE BREACH PRODUCED THE "CHAOS" VERDICT** is that nothing in front of or between
the park's buildings may collide with the ground layer or with a building. The earlier attempt at
this work was thrown away for exactly that, not for existing - so the first four tests here are
cell-by-cell measurements against the two shipped litematics rather than assertions about the
generator's own arithmetic.

Everything else pins a CONTRACT rather than a block count. A snapshot test on a design whose whole
nature is "remaining work beside somebody else's build" fails the moment either neighbour moves,
which this repo has been bitten by three times.
"""
from __future__ import annotations

import glob
import os
import sys

import numpy as np
import pytest
import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcbuild import blocks, palette, schem                      # noqa: E402
from mcbuild.gen import park_frontage as pf                     # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WAYS = os.path.join(ROOT, "out", "Park Ways.litematic")
COMPLETE = os.path.join(ROOT, "out", "Park Complete.litematic")
CONFIGS = sorted(glob.glob(os.path.join(ROOT, "configs", "pf_front_*.yaml")))

#: `Park Ways` lays a moss carpet over every lot at the course this design builds on. It is what
#: a builder clears with one swing, and every `pf_front_*` config declares it replaceable - so it
#: is not a collision, here or in the pipeline's own `verify_against`.
REPLACEABLE = {"moss_carpet"}

#: The nineteen placed modules. A theme park names EVERYTHING at the front; the complaint that
#: started this work was that not one of them did.
MODULES = [
    "Trailhead Gate", "Prospecting Porch", "Boomtown Spine", "Mining Square",
    "Assay and Prize Office", "Mine Coaster", "Works Yard",
    "Arrival Court", "Snack Window", "Carousel Court", "Sky Lift", "Skill Arcade", "Prize Point",
    "Foundry Gate", "Prism Array", "Resonance Vault", "Prism Ascent", "Forge Deck",
    "Service Gallery",
]

#: Which piece answers for which module. A marquee names it; a staff gate marks a back-of-house
#: yard, which is what a park does instead of marqueeing its service road.
NAMED_BY = {
    "Trailhead Gate": "Trailhead Gate", "Prospecting Porch": "Prospecting Porch",
    "Boomtown Spine": "Boomtown Spine", "Mining Square": "Mining Square",
    "Assay and Prize Office": "Assay and Prize Office", "Mine Coaster": "Mine Coaster",
    "Works Yard": "Works Yard staff gate",
    "Arrival Court": "Arrival Court", "Snack Window": "Snack Window",
    "Carousel Court": "Circus Gate", "Sky Lift": "Sky Lift", "Skill Arcade": "Skill Arcade",
    "Prize Point": "Prize Point",
    "Foundry Gate": "Foundry Gate", "Prism Array": "Prism Array",
    "Resonance Vault": "Resonance Vault", "Prism Ascent": "Prism Ascent",
    "Forge Deck": "Forge Deck", "Service Gallery": "Service Gallery staff gate",
}

#: THE FOUR MEASURED TROUGHS. Built columns per 20-wide U band across the public floor swing from
#: near 2,000 down to near 250, and that alternation is what reads as "clusters then empty space".
#: These four are the emptiest bands a visitor actually walks through; the two reaches are being
#: filled by another stream (a lake and the Wyrm) and are not this design's to answer for.
TROUGHS = [(320, 339), (420, 439), (520, 539), (580, 599)]


# --------------------------------------------------------------------------- fixtures


def _named(model):
    return {i: e.value["Name"].value.split(":")[-1] for i, e in enumerate(model.palette)}


@pytest.fixture(scope="module")
def ground():
    """The shipped ground layer and the whole placed park, as cell lookups in PARK coordinates.

    `Park Ways` starts at Y202 - its surface course, which is every path, plaza, verge, spur and
    kerb in the park - and `Park Complete` at Y190.
    """
    if not (os.path.exists(WAYS) and os.path.exists(COMPLETE)):
        pytest.skip("the shipped park litematics are not in out/")
    W, C = schem.load(WAYS), schem.load(COMPLETE)
    wn, cn = _named(W), _named(C)
    lawn_ids = [i for i, n in wn.items() if n == "moss_block"]
    top = W.ids[0]
    lawn = np.isin(top, lawn_ids).T                       # [V, U]
    paved = (top.T != 0) & ~lawn
    return {"W": W, "C": C, "wn": wn, "cn": cn, "paved": paved, "lawn": lawn,
            "wy0": 202, "cy0": 190}


def _occupant(g, V, Y, U):
    """What the shipped park already holds at this PARK cell, or None. Carpet is not an occupant."""
    for model, names, y0 in ((g["W"], g["wn"], g["wy0"]), (g["C"], g["cn"], g["cy0"])):
        ly = Y - y0
        if 0 <= ly < model.ids.shape[0] and 0 <= U < model.ids.shape[1] and 0 <= V < model.ids.shape[2]:
            i = int(model.ids[ly, U, V])
            if i and names[i] not in REPLACEABLE:
                return names[i]
    return None


@pytest.fixture(scope="module")
def designs():
    """Every shipped `pf_front_*` design, as (name, canvas, cells) with cells in PARK coords."""
    assert CONFIGS, "no configs/pf_front_*.yaml - this design ships as one config per land"
    out = []
    for path in CONFIGS:
        cfg = yaml.safe_load(open(path, encoding="utf-8"))
        c = pf.build(cfg["params"])
        ox, oy, oz = c.world_origin
        names = _named(c)
        cells = {}
        ys, zs, xs = (c.ids != 0).nonzero()
        for y, z, x in zip(ys.tolist(), zs.tolist(), xs.tolist()):
            cells[(ox - 97500 + x, oy + y, oz - 80300 + z)] = names[int(c.ids[y, z, x])]
        out.append((cfg["name"], cfg, c, cells))
    return out


# --------------------------------------------------------------------------- the collision rules


def test_not_one_cell_is_emitted_below_the_build_plane(designs):
    """Y202 IS THE GROUND LAYER'S OWN SURFACE - every path, plaza, verge, spur and kerb in the
    park is that one course. This design's h=0 is Y203, so a paved cell cannot be touched BY
    CONSTRUCTION rather than by care, and the generator raises rather than emitting one."""
    for name, _cfg, _c, cells in designs:
        low = min(Y for _V, Y, _U in cells)
        assert low >= 203, f"{name} emits at Y{low}, inside the ground layer"


def test_nothing_touches_a_street_a_plaza_a_verge_a_lamp_or_a_building(ground, designs):
    """THE RULE WHOSE BREACH PRODUCED THE 'CHAOS' VERDICT, measured cell by cell against both
    shipped litematics rather than reasoned about."""
    for name, _cfg, _c, cells in designs:
        hits = {}
        for (V, Y, U), _mine in cells.items():
            theirs = _occupant(ground, V, Y, U)
            if theirs:
                hits.setdefault(theirs, []).append((V, Y, U))
        assert not hits, (
            f"{name} shares {sum(len(v) for v in hits.values())} cells with the placed park: "
            + "; ".join(f"{k} x{len(v)} eg {v[0]}" for k, v in sorted(hits.items())))


def test_nothing_stands_in_a_walkway(ground, designs):
    """A marquee is an ARCH over the spur that already leads to the door it names, so it crosses
    paving on purpose - and a guest has to be able to walk under it. Every cell of this design
    standing over a paved column is at or above `HEAD_CLEAR`, which is measured here rather than
    trusted: three clear courses is a player who does not flinch."""
    assert pf.HEAD_CLEAR >= 3, "two courses is a player; three is a player with room"
    paved = ground["paved"]
    for name, _cfg, _c, cells in designs:
        bad = [(V, Y, U, n) for (V, Y, U), n in cells.items()
               if 0 <= V < paved.shape[0] and 0 <= U < paved.shape[1]
               and paved[V, U] and Y - 203 < pf.HEAD_CLEAR]
        assert not bad, f"{name} blocks a walkway at {bad[:5]}"


def test_nothing_reaches_the_protected_rim_reserve_or_leaves_the_plot(designs):
    """V171-199 is the protected rim and void reserve and NOTHING is placed in it - a rule the
    ground layer asserts about itself, and one a design standing on its lawn inherits."""
    for name, _cfg, _c, cells in designs:
        for (V, Y, U) in cells:
            assert 0 <= V <= 169, f"{name} reaches V{V}, outside the buildable depth band"
            assert 0 <= U <= 599, f"{name} reaches U{U}, off the plot"


def test_the_three_lands_do_not_share_a_cell(designs):
    """Three configs, one park. Cross-design overlap is a DIFFERENT question from overlap with
    the capture, and it needs its own check: `verify_against` audits each design against the
    world, and the world does not contain its siblings."""
    seen = {}
    for name, _cfg, _c, cells in designs:
        for pos in cells:
            other = seen.get(pos)
            assert other is None, f"{name} and {other} both claim {pos}"
            seen[pos] = name


# --------------------------------------------------------------------------- materials


def test_every_material_is_legal_cheap_and_spendable():
    """ASK THE REGISTRY, NEVER A MEMORY. The palettes here are copied from the three land builders
    rather than imported, because three streams are editing this park at once - so what keeps them
    honest is this, not the copying: every entry must exist, be in the 1.19 SERVER's list, not be
    currency (dirt and grass are money here), not be expensive, and not be cobblestone."""
    for land, table in pf.PAL.items():
        for key, name in table.items():
            if key == "wood":                       # a sign prefix, not a block
                name = f"{name}_wall_sign"
            assert blocks.exists(name), f"{land}.{key}: {name} is not a block"
            assert blocks.available(name), f"{land}.{key}: {name} is not on the 1.19 server"
            assert blocks.spendable(name), f"{land}.{key}: {name} is CURRENCY on this server"
            assert palette.tier(name) in ("cheap", "ok"), \
                f"{land}.{key}: {name} is {palette.tier(name)} tier"
            assert "cobblestone" not in name, f"{land}.{key}: {name} is cobblestone"
            assert not blocks.falls(name), f"{land}.{key}: {name} falls"


def test_every_land_can_actually_draw_a_line():
    """A VALUE LADDER CANNOT EXIST INSIDE ONE MATERIAL FAMILY, and this repo has concluded four
    separate times that the economy has no contrast after searching inside one. Across families
    the rungs are real, and a marquee's fascia has to read against its own piers from the spine."""
    for land, table in pf.PAL.items():
        lum = {}
        for key in ("plinth", "pier", "band", "board", "accent"):
            r, g, b = blocks.color(table[key], "side")
            lum[key] = 0.2126 * r + 0.7152 * g + 0.0722 * b
        assert abs(lum["board"] - lum["pier"]) >= 15, \
            f"{land}: the fascia is {abs(lum['board'] - lum['pier']):.0f} off its own piers"
        assert abs(lum["plinth"] - lum["pier"]) >= 15, \
            f"{land}: the plinth course does not read as a line under the pier"


def test_a_property_the_block_does_not_have_is_a_typo_and_raises():
    """A palette key is an abstraction - one land's `post` is a log and another's is basalt - so
    `axis` may be asked for and not got. Every OTHER unknown property is a typo, and a silently
    dropped `facing` is a stair pointing the wrong way, which this renderer draws identically to
    a right one."""
    assert pf._state("smooth_basalt", {"axis": "y"}) == {}
    assert pf._state("spruce_log", {"axis": "y"}) == {"axis": "y"}
    with pytest.raises(ValueError):
        pf._state("stone_bricks", {"facing": "west"})


# --------------------------------------------------------------------------- what a park has


def test_every_one_of_the_nineteen_modules_is_named(designs):
    """THE COMPLAINT THAT STARTED THIS WORK: not one of the park's nineteen modules said what it
    was from outside."""
    built = set()
    for _name, _cfg, c, _cells in designs:
        built |= {p.get("name") for p in c.meta["pieces"]}
    missing = [m for m in MODULES if NAMED_BY[m] not in built]
    assert not missing, f"nothing announces {missing}"


def test_a_sign_line_never_clips(designs):
    """Fifteen characters. A line that clips only shows in a screenshot taken after the thing is
    placed, which is the most expensive place in this pipeline to find a typo."""
    for name, _cfg, c, _cells in designs:
        for pos, tile in c.tiles.items():
            for side in ("front", "back"):
                for line in tile[side]:
                    text = line.split('"text":')[-1].strip('}" ')
                    assert len(text) <= pf.SIGN_WIDTH, f"{name} {pos}: {text!r}"


def test_the_generator_refuses_a_sign_line_that_would_clip():
    """...and it is checked in the BUILD, not only here, because a config is where the typo is."""
    with pytest.raises(ValueError, match="chars"):
        pf.build({"land": "midway", "pieces": [
            {"kind": "marquee", "at": [20, 40], "title": "A NAME FAR TOO LONG TO FIT"}]})


def test_not_one_sign_was_refused(designs):
    """A REFUSED SIGN IS SILENT. `_sign` will not hang a board on a cell that does not exist -
    the game refuses one too, and a wall sign floating in air draws exactly like one on a wall in
    every render this repo has. So each refusal is RECORDED, and this is the check that reads the
    record. It caught eight the first time it ran: four back signs on one-course pieces whose own
    building stood behind them, a bandstand whose plaque was placed before the board that carries
    it, and two lens plaques facing the wrong way off their plinth."""
    for name, _cfg, c, _cells in designs:
        assert c.meta["refused_signs"] == [], \
            f"{name} silently dropped {len(c.meta['refused_signs'])} name boards: " \
            f"{c.meta['refused_signs']}"


def test_every_sign_hangs_on_a_block_of_this_design(designs):
    """A WALL SIGN FLOATING IN AIR DRAWS EXACTLY LIKE ONE ON A WALL, and the game simply refuses
    to place it - so a silently-refused sign is this project's most-repeated failure shape. Every
    sign this design places must have its own support, not somebody else's."""
    for name, _cfg, c, cells in designs:
        ox, oy, oz = c.world_origin
        for (x, y, z), _tile in c.tiles.items():
            V, Y, U = ox - 97500 + x, oy + y, oz - 80300 + z
            props = c.palette[int(c.ids[y, z, x])]
            facing = None
            for k, v in (props.value.get("Properties").value.items()
                         if props.value.get("Properties") else {}.items()):
                if k == "facing":
                    facing = v.value
            assert facing, f"{name}: a wall sign at {(V, Y, U)} has no facing"
            dv, du = pf._STEP[facing]
            assert (V - dv, Y, U - du) in cells, \
                f"{name}: the sign at {(V, Y, U)} facing {facing} hangs on nothing"


def test_every_attraction_with_a_queue_also_has_a_way_out(designs):
    """A SWITCHBACK WHOSE LAST LEG IS CLOSED IS A PEN, and it looks identical. Every queue in this
    design declares an entrance at the near end and an exit at the far one, and the two are
    different KINDS of portal - which is what tells them apart at a distance, where the words
    cannot be read."""
    queues = 0
    for _name, _cfg, c, _cells in designs:
        for piece in c.meta["pieces"]:
            if piece.get("kind") != "queue":
                continue
            queues += 1
            assert piece["entrance"]["kind"] == "portal/entrance"
            assert piece["exit"]["kind"] == "portal/exit"
            assert piece["legs"] >= 3, "a two-leg switchback is a corridor"
            assert piece["lamps"] >= piece["legs"], "every turn carries its own light"
    assert queues >= 3, "the rides that genuinely wait each need a line"


def test_a_queue_leg_is_open_at_the_end_it_turns_at(designs):
    """THE GAP IS THE FEATURE. Each leg leaves a gap at the OPPOSITE end from the last, so the
    walk folds instead of stopping; drawn without it, every leg is a closed rail and the queue is
    a set of pens that audits perfectly."""
    for _name, _cfg, c, _cells in designs:
        for piece in c.meta["pieces"]:
            if piece.get("kind") != "queue":
                continue
            ends = [i for i, _d in piece["turns"]]
            assert len(set(ends)) == 2, f"the turns do not alternate: {piece['turns']}"
            for a, b in zip(ends, ends[1:]):
                assert a != b, f"two legs turn at the same end: {piece['turns']}"


def test_an_entrance_does_not_look_like_an_exit():
    """At twenty blocks the word is unreadable and the shape is not, so the two are told apart by
    COLOUR: an entrance carries the land's accent across its head and a lamp each side, an exit
    carries neither. Colour is the whole of the distinction and it is asserted, not hoped for."""
    pal = pf.PAL["midway"]
    got = {}
    for mode in ("entrance", "exit"):
        c = pf.build({"land": "midway",
                      "pieces": [{"kind": "portal", "at": [40, 40], "mode": mode}]})
        names = {i: e.value["Name"].value.split(":")[-1] for i, e in enumerate(c.palette)}
        got[mode] = {names[int(v)] for v in np.unique(c.ids) if v}
    assert pal["accent"] in got["entrance"] and pal["accent"] not in got["exit"]
    assert pal["light"] in got["entrance"] and pal["light"] not in got["exit"]


def test_a_marquee_is_symmetric_about_its_own_opening():
    """A GANTRY WHOSE TWO PIERS ARE DIFFERENT DISTANCES FROM THE PATH IT STRADDLES is the exact
    asymmetry the park railway had to be rebuilt to cure. Here it cannot happen by arithmetic -
    every offset is mirrored - and this measures the emitted cells rather than the arithmetic."""
    c = pf.build({"land": "frontier", "pieces": [
        {"kind": "marquee", "at": [20, 100], "span": 5, "pier": 2, "wing": 1, "title": "X"}]})
    ox, _oy, oz = c.world_origin
    solid = {(int(x), int(z)) for _y, z, x in zip(*(c.ids != 0).nonzero())}
    centre = 2 * (100 - (oz - 80300))
    unmirrored = [(x, z) for (x, z) in solid if (x, centre - z) not in solid]
    # the two SIGNS are single cells on the centre line and mirror onto themselves; everything
    # else is structure and must have a twin.
    assert not unmirrored, f"{len(unmirrored)} cells have no mirror image: {unmirrored[:6]}"


def test_a_stair_leans_the_way_it_was_built():
    """A STAIR'S TALL SIDE IS ITS `facing`, and this repo's renderer draws a backwards flight
    identically to a right one - so the convention is asserted here rather than eyeballed. A
    marquee's front cornice leans INTO its own fascia, which means it faces the way the piece's
    BACK looks."""
    c = pf.build({"land": "frontier", "pieces": [
        {"kind": "marquee", "at": [20, 100], "facing": "west", "depth": 3, "title": "X"}]})
    names = {i: e.value["Name"].value.split(":")[-1] for i, e in enumerate(c.palette)}
    ox, _oy, _oz = c.world_origin
    by_v = {}
    for y, z, x in zip(*(c.ids != 0).nonzero()):
        e = c.palette[int(c.ids[y, z, x])]
        if names[int(c.ids[y, z, x])].endswith("_stairs"):
            by_v.setdefault(ox - 97500 + x, set()).add(e.value["Properties"].value["facing"].value)
    # a west-facing marquee stands at V20-22: the cornice on its FRONT face leans back into the
    # fascia (east) and the one on its BACK face leans forward (west). Both must be present, and
    # each must be on the right face - which is what a render cannot show.
    assert by_v.get(20) == {pf._LEAN["west"]}, f"the front cornice faces {by_v.get(20)}"
    assert by_v.get(22) == {pf._LEAN["east"]}, f"the back cornice faces {by_v.get(22)}"


# --------------------------------------------------------------------------- the sloth's home


def test_the_arbour_piers_stand_under_solid_cells_of_the_piece_they_carry(designs):
    """`Sky Lift Sloth` is a 46 x 22 lattice, and a lattice is mostly HOLES: its two long rails
    run at its own U1-2 and U21-22 and everything between them is open air. A pier under a hole
    carries nothing and reads as a post standing beside a sculpture, so every pier top is measured
    against the cell above it."""
    for name, _cfg, c, cells in designs:
        for piece in c.meta["pieces"]:
            if piece.get("kind") != "pergola":
                continue
            top = piece["top"]
            for (v, u) in piece["piers"]:
                V, U = piece["at"][0] + v, piece["at"][1] + u
                assert (V, 203 + top, U) in cells, f"{name}: pier at {(V, U)} is not a pier"
                assert (V, 203 + top + 1, U) in cells, \
                    f"{name}: the pier at {(V, U)} carries nothing - the frame above it is a hole"


def test_you_can_walk_under_the_sloth(designs):
    """A five-thousand-block animal two courses off the lawn is a wall. The whole point of hanging
    it is the space beneath, so every column of its body keeps at least four clear courses."""
    for name, _cfg, c, cells in designs:
        for piece in c.meta["pieces"]:
            if piece.get("kind") != "stamp":
                continue
            v0, u0 = piece["at"]
            floor = min(Y for (V, Y, U) in cells
                        if v0 <= V < v0 + piece["size"][0] and u0 <= U < u0 + piece["size"][2]
                        and not _is_pier(c, V, U))
            assert floor >= 203 + 4, f"{name}: the sloth's lowest cell is at Y{floor}"


def _is_pier(c, V, U) -> bool:
    for piece in c.meta["pieces"]:
        if piece.get("kind") != "pergola":
            continue
        for (v, u) in piece["piers"]:
            if (piece["at"][0] + v, piece["at"][1] + u) == (V, U):
                return True
    return False


# --------------------------------------------------------------------------- the empty bands


def test_every_measured_trough_gains_something_to_look_at(designs):
    """Built columns per 20-wide U band swing from near 2,000 to near 250, and that alternation IS
    what reads as clusters and then empty space. These four bands are the emptiest a visitor walks
    through, and a sight piece three blocks tall cannot carry twenty blocks of walking - so each
    is checked for BOTH: that something stands there, and that it stands tall enough to see."""
    cols, tall = {}, {}
    for _name, _cfg, _c, cells in designs:
        for (V, Y, U) in cells:
            if 24 <= V <= 127:
                cols.setdefault(U, set()).add(V)
                tall[U] = max(tall.get(U, 203), Y)
    for (u0, u1) in TROUGHS:
        placed = sum(len(cols.get(u, ())) for u in range(u0, u1 + 1))
        height = max([tall.get(u, 203) for u in range(u0, u1 + 1)] or [203]) - 203
        assert placed >= 100, f"U{u0}-{u1} is still empty: only {placed} cells"
        assert height >= 12, f"U{u0}-{u1} gains only {height} courses - too low to walk toward"


def test_no_street_furniture_is_duplicated(designs):
    """`Park Ways` draws every lamp, bench, kerb and paved cell in the park and a second copy of
    somebody else's street furniture is precisely the chaos that was thrown away. Nothing here is
    laid in the walking course over a path, and nothing here is a floor: a queue's floor is the
    lawn, which is why it can never be mistaken for a street."""
    for name, _cfg, c, cells in designs:
        for piece in c.meta["pieces"]:
            if piece.get("kind") != "queue":
                continue
            v0, u0 = piece["at"]
            floor = [(V, U) for (V, Y, U) in cells if Y == 203
                     and v0 <= V < v0 + piece["depth"] and u0 <= U < u0 + piece["width"]]
            # only the fence rails and the turn posts sit in the walking course, never a pavement
            assert len(floor) < piece["width"] * piece["depth"] // 2, \
                f"{name}: the queue at {piece['at']} has laid itself a floor"
