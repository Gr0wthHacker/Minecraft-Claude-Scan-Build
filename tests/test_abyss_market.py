"""THE ABYSS MARKET - the fit-out of the squid's own sealed cavity.

Every test here asserts a PROPERTY rather than a snapshot. This repo has now recorded the
snapshot trap seven times - a test that pins a count against a design whose nature is remaining
work, or against a composite that has since come to contain the design, fails the moment the
work improves. What is pinned is: nothing of the animal is taken, the walk connects, the climb
has no gap, the bell can be rung, the deck is lit, every sign hangs on something, and the
entrance is where the measurements say it may be.
"""
from __future__ import annotations

import json
import os
from collections import deque

import numpy as np
import pytest

from mcbuild import nbt, nightlight, scan, schem
from mcbuild.gen import abyssmarket as am

OUT = "out"
DESIGN = os.path.join(OUT, "Abyss Market.litematic")
SQUID = os.path.join(OUT, "Abyss Squid.litematic")
PARK = os.path.join(OUT, "Park Complete.litematic")

pytestmark = pytest.mark.skipif(
    not (os.path.exists(DESIGN) and os.path.exists(SQUID)),
    reason="needs the shipped Abyss Squid and Abyss Market artifacts",
)

WELL = (97590, 80815)          # the Prism Well's axis
KEEP_OUT = 56                  # its fall column, and the squid's own standing rule


# ------------------------------------------------------------------------------------------


def _load():
    d = schem.load(DESIGN)
    s = scan.load(os.path.join(OUT, "Abyss Market.scan.json"))
    meta = json.load(open(os.path.join(OUT, "Abyss Market.scan.json")))
    return d, tuple(int(v) for v in s.origin), meta


def _composite(d, origin, meta, cave):
    """The world the printer will actually leave behind: the animal, this design over it, and
    the mouth OPEN, because the mouth is on the dig list and is air by the time anyone walks."""
    ox, oy, oz = origin
    solid = d.ids != 0
    sy, sz, sx = cave.origin[1] - oy, cave.origin[2] - oz, cave.origin[0] - ox
    solid[sy:sy + cave.shape[0], sz:sz + cave.shape[1], sx:sx + cave.shape[2]] |= cave.solid
    for x1, y1, z1, x2, y2, z2 in meta["exclude_boxes"]:
        solid[y1 - oy:y2 - oy + 1, z1 - oz:z2 - oz + 1, x1 - ox:x2 - ox + 1] = False
    solid |= d.ids != 0
    pal = [nbt.state_name(q) for q in d.palette]
    thin = {"minecraft:ladder", "minecraft:spruce_wall_sign", "minecraft:glow_lichen",
            "minecraft:bell", "minecraft:dark_oak_fence"}
    for i, n in enumerate(pal):
        if n in thin:
            solid[d.ids == i] = False
    return solid


def _walk(solid, seed):
    """Standing cells reachable on foot: step up one, down three, never through a ceiling."""
    ny, nz, nx = solid.shape
    st = np.zeros(solid.shape, bool)
    st[:-2] = solid[:-2] & ~solid[1:-1] & ~solid[2:]
    seen = np.zeros(solid.shape, bool)
    seen[seed] = True
    dq = deque([seed])
    while dq:
        a, b, c = dq.popleft()
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            for dy in (0, 1, -1, -2, -3):
                q, r, t = a + dy, b + dz, c + dx
                if not (0 <= q < ny - 2 and 0 <= r < nz and 0 <= t < nx):
                    continue
                if dy == 1 and a + 3 < ny and solid[a + 3, b, c]:
                    continue
                if st[q, r, t]:
                    if not seen[q, r, t]:
                        seen[q, r, t] = True
                        dq.append((q, r, t))
                    break
    return seen


@pytest.fixture(scope="module")
def built():
    d, origin, meta = _load()
    cave = am.Cave(SQUID)
    solid = _composite(d, origin, meta, cave)
    ox, oy, oz = origin
    if meta.get("entrance") == "mouth":
        x, y, z = meta["mouth"]["entry_floor"]
        seed = (y - oy, z - oz, x - ox)
    else:
        sh = meta["shaft"]
        seed = (sh["foot_y"] - oy, sh["z"] - oz, sh["x"] - ox)
    seen = _walk(solid, seed)
    return dict(d=d, origin=origin, meta=meta, cave=cave, solid=solid, seen=seen,
                pal=[nbt.state_name(q) for q in d.palette])


# ------------------------------------------------------------------------------------------


def test_not_one_cell_of_the_animal_is_taken(built):
    """The refusal is STRUCTURAL, and this is what makes the squid regenerable under it.

    A fit-out hanging inside another design cannot be checked for overlap afterwards and then
    patched - the two would fight cell by cell in game and the loser is whoever places second.
    The only cells of the animal this design may write are the mouth, which is on the dig list.
    """
    d, (ox, oy, oz), meta = built["d"], built["origin"], built["meta"]
    cave = built["cave"]
    dig = {tuple(c) for c in meta["dig"]}
    clash = []
    for y, z, x in zip(*np.nonzero(d.ids)):
        w = (x + ox, y + oy, z + oz)
        if cave.rock(*w) and w not in dig:
            clash.append(w)
    assert not clash, f"{len(clash)} cell(s) of the squid taken, e.g. {clash[:5]}"


def test_the_walk_reaches_every_room_from_the_shaft_foot(built):
    """One journey, on foot, from where a visitor lands - not six rooms that each exist."""
    seen, (ox, oy, oz) = built["seen"], built["origin"]
    zs = np.nonzero(seen)[1] + oz
    for name, z0, z1 in (("the tail", *am.TAIL), ("the sounding hall", *am.SOUND),
                         ("the arcade", *am.ARCADE), ("the collar", *am.COLLAR),
                         ("the gullet", *am.GULLET), ("the bazaar", *am.BAZAAR),
                         ("the prow", *am.PROW)):
        n = int(((zs >= z0) & (zs <= z1)).sum())
        assert n > 20, f"{name} has {n} cells reachable on foot from the shaft"


def test_the_configured_entrance_is_complete(built):
    """A ladder that stops looks exactly like a ladder that starts.

    The shaft is built above the animal and the rig below it, and each stopped at its own end -
    so the two courses of skin between them, which are the dig, had no rung at all. Nothing in
    a render, a BOM or an audit can see a gap in a climb.
    """
    d, meta, pal = built["d"], built["meta"], built["pal"]
    if meta.get("entrance") == "mouth":
        assert meta["shaft"]["enabled"] is False
        assert not any(n == "minecraft:ladder" for n in pal), \
            "mouth-only market still contains a hidden surface climb"
        assert meta["mouth"]["entry_floor"] != meta["mouth"]["exit_floor"]
        return
    (ox, oy, oz) = built["origin"]
    sh = meta["shaft"]
    rungs = set()
    for i, n in enumerate(pal):
        if n == "minecraft:ladder":
            rungs.update(int(y) + oy for y in np.nonzero(d.ids == i)[0])
    missing = [y for y in range(sh["foot_y"] + 1, sh["surface"]) if y not in rungs]
    assert not missing, f"no rung at Y{missing}"


def test_the_bell_can_actually_be_rung(built):
    """The one verb in the biggest room, and the first build put it out of reach.

    Hung from the cavity's own ceiling it sat five and a half blocks over a standing player's
    eye against a reach of about four and a half. Every offline check passed it, because a bell
    nobody can touch is a legal, supported, affordable, correctly-stated bell.
    """
    d, pal, seen = built["d"], built["pal"], built["seen"]
    (ox, oy, oz) = built["origin"]
    bells = [i for i, n in enumerate(pal) if n == "minecraft:bell"]
    assert bells, "the sounding hall has no bell"
    by, bz, bx = (int(v[0]) for v in np.nonzero(d.ids == bells[0]))
    best = min((((x - bx) ** 2 + ((y + 1.62) - (by + 0.5)) ** 2 + (z - bz) ** 2) ** 0.5)
               for y, z, x in zip(*np.nonzero(seen)))
    assert best <= 4.5, f"the nearest place anyone can stand is {best:.2f} from the bell"


def test_every_reachable_cell_of_the_DECK_is_lit(built):
    """PROPAGATED, never spaced, and scoped to the deck rather than to the whole cavity.

    A lamp every six courses is a rhythm and was not an answer: 912 of 4,064 walkable cells
    came out at block light 3 or under, 622 of them in the room a visitor is meant to shop in.
    A sealed cavity under a park with no sky light at any hour has no dim corners, only
    invisible ones.

    The scope is the deck THIS DESIGN LAID. The animal's own trough either side of the walkway
    stays dark on purpose - a lit path through a dark body is the design, and Jack's own note
    that mobs do not spawn here (which is why the squid was hollowed at all) is what makes
    that atmosphere rather than a hazard.
    """
    d, meta, cave = built["d"], built["meta"], built["cave"]
    (ox, oy, oz) = built["origin"]
    names = [nbt.state_name(q) for q in d.palette]
    lookup = {n: i for i, n in enumerate(names)}
    merged = list(names)
    remap = {}
    for i, n in enumerate(cave.names):
        if n not in lookup:
            lookup[n] = len(merged)
            merged.append(n)
        remap[i] = lookup[n]
    grid = np.zeros(d.ids.shape, np.int32)
    sy, sz, sx = cave.origin[1] - oy, cave.origin[2] - oz, cave.origin[0] - ox
    sub = grid[sy:sy + cave.shape[0], sz:sz + cave.shape[1], sx:sx + cave.shape[2]]
    lut = np.zeros(len(cave.names), np.int32)
    for i in remap:
        lut[i] = remap[i]
    sub[:] = np.where(cave.solid, lut[cave.ids], 0)
    grid[d.ids != 0] = d.ids[d.ids != 0]
    for x1, y1, z1, x2, y2, z2 in meta["exclude_boxes"]:
        box = grid[y1 - oy:y2 - oy + 1, z1 - oz:z2 - oz + 1, x1 - ox:x2 - ox + 1]
        box[d.ids[y1 - oy:y2 - oy + 1, z1 - oz:z2 - oz + 1, x1 - ox:x2 - ox + 1] == 0] = 0
    opq, emit, *_ = nightlight.classify(merged)
    light = nightlight.propagate(opq[grid], emit[grid].astype(np.int16))
    ys, zs, xs = np.nonzero(built["seen"] & (d.ids != 0))
    assert len(ys) > 500, "the deck all but vanished - the walk is not being measured"
    lv = light[ys + 1, zs, xs]
    dark = int((lv < meta.get("light_min", 8)).sum())
    assert dark == 0, f"{dark} of {len(lv)} reachable deck cells below block light 8"


def test_every_sign_hangs_on_something_and_no_line_clips(built):
    """A wall sign with nothing behind it renders identically to one on a wall, and the game
    simply refuses it - so the line is lost with nothing to say so. The first build shipped two
    of them, because `_W.sign` described the check in its docstring and did not make it.
    """
    d, pal = built["d"], built["pal"]
    (ox, oy, oz) = built["origin"]
    solid = built["solid"] | (d.ids != 0)
    hung = 0
    for i, n in enumerate(pal):
        if not n.endswith("_wall_sign"):
            continue
        for y, z, x in zip(*np.nonzero(d.ids == i)):
            facing = nbt.state_props(d.palette[i]).get("facing")
            dx, dz = am._BEHIND[facing]
            assert solid[y, z + dz, x + dx], \
                f"sign at X{x + ox} Y{y + oy} Z{z + oz} facing {facing} has nothing behind it"
            hung += 1
    assert hung >= 8, f"only {hung} signs placed - a room nobody can be told the rules in"
    # AND NOT ONE LINE CLIPS. This park has shipped `MINE CART ESCAP`, `and prize windo` and
    # `ore from the ad` from four different routes, and every offline check passes a clipped
    # sign: the block is legal, supported, affordable and in 1.19, and `render3d` draws it
    # identically to a whole one. It shows only in a screenshot of the placed build.
    lines = 0
    for tile in (d.tile_entities or []):
        for side in ("front_text", "back_text"):
            blk = tile.value.get(side)
            if blk is None:
                continue
            for msg in blk.value["messages"].value:
                txt = json.loads(msg.value).get("text", "")
                assert len(txt) <= am.SIGN_W, f"sign line clips: {txt!r}"
                if txt:
                    lines += 1
    assert lines >= 8, f"only {lines} sign lines carried into the artifact"


def test_nothing_enters_the_prism_wells_fall_column(built):
    """The squid's own standing rule, and the reason this entrance comes off Prismworks
    instead of off the parkour. A surface in a column a runner falls eighty-six courses down
    does not save one, it strands one sixty blocks out in the void with no way back.
    """
    d, (ox, oy, oz) = built["d"], built["origin"]
    ys, zs, xs = np.nonzero(d.ids)
    r = np.hypot((xs + ox) - WELL[0], (zs + oz) - WELL[1])
    assert r.min() > KEEP_OUT, f"{int((r <= KEEP_OUT).sum())} cell(s) inside the fall column"


def test_the_shaft_is_DRY(built):
    """The best-scoring column by drop alone is under a pond, and cutting it drops that pond
    forty-two courses into a sealed animal. This repo has drained 199,959 cells to Y-1908 once.
    """
    if built["meta"].get("entrance") == "mouth":
        d, (ox, oy, oz), meta = built["d"], built["origin"], built["meta"]
        sh = meta["shaft"]
        cells=[]
        for y,z,x in zip(*np.nonzero(d.ids)):
            wx,wy,wz=x+ox,y+oy,z+oz
            if abs(wx-sh["x"])<=1 and abs(wz-sh["z"])<=1 and sh["foot_y"]<wy<sh["surface"]:
                cells.append((wx,wy,wz))
        assert not cells, f"mouth-only market still builds {len(cells)} surface-shaft cells"
        return
    if not os.path.exists(PARK):
        pytest.skip("needs Park Complete for the surface")
    m = schem.load(PARK)
    s = scan.load(os.path.join(OUT, "Park Complete.scan.json"))
    px, py, pz = (int(v) for v in s.origin)
    pal = [nbt.state_name(q) for q in m.palette]
    wet = {i for i, n in enumerate(pal)
           if n.split(":")[-1] in {"water", "kelp", "kelp_plant", "seagrass",
                                   "tall_seagrass", "bubble_column"}}
    sx, sz = built["meta"]["shaft"]["x"], built["meta"]["shaft"]["z"]
    box = m.ids[:, sz - pz - 5:sz - pz + 6, sx - px - 5:sx - px + 6]
    found = sorted({pal[i] for i in np.unique(box) if i in wet})
    assert not found, f"standing water within five of the shaft: {found}"


def test_every_dig_cell_is_a_declared_entrance_cut_or_window(built):
    """A dig is the one operation with no undo, so what it may take is STATED.

    This used to assert a flat count of thirty-six - the shaft's 3x3 mouth - and that was the
    right contract until the prow needed windows. A count is the weakest possible form of the
    rule: it fails when the design improves and it says nothing about WHERE. What is asserted
    now is the two kinds and their bounds, which is what a reviewer actually wants to know.
    """
    meta, cave = built["meta"], built["cave"]
    dig = [tuple(c) for c in meta["dig"]]
    sx, sz = meta["shaft"]["x"], meta["shaft"]["z"]
    mouth = [c for c in dig if abs(c[0] - sx) <= 1 and abs(c[2] - sz) <= 1]
    window = [c for c in dig if c not in set(mouth)]

    if meta.get("entrance") == "mouth":
        assert not mouth, "mouth-only access must not retain the obsolete surface shaft cut"
    else:
        assert len(mouth) == 36, f"{len(mouth)} mouth cells - it is a 3x3 through four courses"
        assert len({y for _, y, _ in mouth}) == 4

    budget = int(meta["prow"]["dig"])
    assert len(window) == budget, f"{len(window)} window cells against a declared {budget}"
    assert budget <= 60, f"the window budget has grown to {budget} - that is an excavation"
    for x, y, z in window:
        assert am.PROW[0] <= z <= am.PROW[1], f"window dig at Z{z} is outside the prow"


def test_the_prow_windows_actually_SEE_OUT(built):
    """THE WHOLE POINT, AND THE ONE THING A BLOCK COUNT CANNOT CHECK.

    Jack asked for glass "so interior can see out". Measured, that does not pay anywhere
    obvious: a nine-by-seven aperture in the prow's FORWARD wall costs seventy-one cells of the
    animal and fifty-seven of its sixty-three sightlines end on nothing at all, because the arm
    crown's forty lights are off to the sides rather than in the cone.

    Where it does pay is the INNER wall, and only because of what the animal already is: its
    mouth is OPEN - a shaft of outside running down the axis, with the body cavity forming a
    ring around it one to three cells away. So every pane is asserted to have open void within
    a few cells of it. A pane with rock behind it is a black tile, and it would look exactly
    like a window in every render this repo can make.
    """
    d, cave = built["d"], built["cave"]
    (ox, oy, oz) = built["origin"]
    panes = [i for i, n in enumerate(built["pal"]) if "glass_pane" in n]
    assert panes, "the prow has no glazing at all"
    seen = 0
    for i in panes:
        for y, z, x in zip(*np.nonzero(d.ids == i)):
            wx, wy, wz = x + ox, y + oy, z + oz
            # toward the axis, which is where the mouth is - a pane whose open side is the
            # OUTER flank is a hole in the animal's skin, which is the bug this caught
            step = 1 if wx < am.XC else -1
            xx, rock = wx + step, 0
            while cave.rock(xx, wy, wz) and rock < 5:
                xx += step
                rock += 1
            j = cave._ix(xx, wy, wz)
            assert j is not None and not cave.solid[j] and not cave.inside[j], (
                f"the pane at X{wx} Y{wy} Z{wz} does not look into the mouth - it is either a "
                f"black tile or a hole cut out through the animal's flank")
            seen += 1
    # A FLOOR ON WINDOWS, NOT A TARGET. The count is whatever the animal's own mouth allows
    # once the run and one-plane rules are honoured: forty-six placed per cell became fourteen
    # on a shared plane and eight in real runs, and eight is TWO tall slit windows, which is
    # what the geometry supports. Asserting a bigger number would be asserting a wish - the
    # property that matters is below, and it is that every pane is part of a window.
    assert seen >= 6, f"only {seen} panes - that is a porthole, not a gallery"

    # AND EACH ONE BELONGS TO A RUN ON ONE PLANE, which is the property a count cannot state.
    # Placed per cell wherever the rule allowed, forty-six panes came out as a scatter of black
    # blobs at three different depths, because the mouth's wall is jagged and each pane sat
    # where its own cut happened to end. It rendered as damage. A window is a RUN.
    cells = set()
    for i in panes:
        for y, z, x in zip(*np.nonzero(d.ids == i)):
            cells.add((x + ox, y + oy, z + oz))
    for (x, y, z) in cells:
        run = 1
        for step in (1, -1):
            k = y + step
            while (x, k, z) in cells:
                run += 1
                k += step
        assert run >= 3, f"the pane at X{x} Y{y} Z{z} stands alone - that is a speckle"


def test_a_landing_is_checked_for_ROOM_and_not_merely_for_cavity():
    """The second-best shaft column reports a two-cell cavity ceiling under a two-cell shell
    and looks perfect. It is the inside of an ARM BASE - a hollow tube running up into the
    crown - and a visitor dropped into it lands in a chimney they cannot get out of.
    """
    cave = am.Cave(SQUID)
    # the arm base at the front of the head: real cavity, and no room in it
    assert cave.cave(97583, 170, 80739)
    assert am._room_span(cave, 80739, 169, 3, 8) is None or \
        (am._room_span(cave, 80739, 169, 3, 8) or (0, 0))[1] - \
        (am._room_span(cave, 80739, 169, 3, 8) or (0, 0))[0] < 3
    # the collar, where the shaft actually lands
    sp = am._room_span(cave, 80665, 137, 2, 3)
    assert sp and sp[1] - sp[0] >= 4, "the shaft lands somewhere a body cannot stand"


def test_the_palette_draws_a_REAL_value_ladder(built):
    """Measured ACROSS families, which is the only place this economy's contrast has ever been.

    CLAUDE.md records four separate times that "there is no value contrast here", and all four
    searched INSIDE one material family, where a ladder cannot exist by construction. The one
    that matters is the structure against the FLESH: deepslate at 71 would vanish into the red
    and mangrove walls it is bolted to, and copper at 123 does not.
    """
    from mcbuild import blocks

    def lum(n):
        r, g, b = blocks.color(n, "side")
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    rungs = ["polished_blackstone_bricks", "deepslate_bricks", "spruce_planks",
             "cut_copper", "ochre_froglight"]
    vals = [lum(n) for n in rungs]
    assert vals == sorted(vals)
    steps = [b - a for a, b in zip(vals, vals[1:])]
    assert min(steps) >= 15, f"a step of {min(steps):.1f} is not a line: {list(zip(rungs, vals))}"
    for flesh in ("mangrove_planks", "red_wool"):
        assert abs(lum("cut_copper") - lum(flesh)) >= 40, \
            f"the structure vanishes into {flesh}"


def test_the_shop_holds_no_stock_anybody_can_empty(built):
    """The shop is SIGNAGE, on Jack's own choice.

    A barrel standing empty in a public build reads as a shop somebody has already looted, and
    a chest on a build anyone can reach is a chest anyone can empty. Nothing here is a
    container, so there is nothing to restock and nothing to lose.
    """
    pal = built["pal"]
    holders = {"chest", "trapped_chest", "barrel", "shulker_box", "hopper", "dispenser",
               "dropper", "furnace", "blast_furnace", "smoker"}
    bad = [n for n in pal if n.split(":")[-1] in holders or n.endswith("shulker_box")]
    assert not bad, f"the market holds containers: {bad}"


def test_it_is_all_cheap_or_ok_and_holds_no_currency(built):
    """Dirt is money on this server, and the blocks are placeable, legal and in 1.19 - so every
    check in the pipeline passes a coat of it. `blocks.spendable` is the third axis.
    """
    from mcbuild import blocks, palette

    for n in built["pal"]:
        b = n.split(":")[-1]
        assert palette.tier(b) != "expensive", f"{b} is expensive tier"
        assert blocks.spendable(b), f"{b} is currency on this server"


def test_the_copper_is_UNWAXED_so_it_ages(built):
    """Jack asked for normal copper, and the whole point of it is that it does not stay orange.

    A waxed block is pinned to its stage for ever. What makes a salvage rig inside a carcass
    read is that it goes green over weeks, patchily, through exposed and weathered - and the
    palette gets BETTER on the way: oxidised copper is 71 clear of the animal's flesh in
    luminance where fresh copper is 56, and green against red is complementary.
    """
    waxed = [n for n in built["pal"] if "waxed" in n]
    assert not waxed, f"these are pinned and will never age: {waxed}"


def test_the_walk_can_be_WALKED_without_jumping(built):
    """Jack, twice. First: *"the stairs arent aligned ... dont connect to lead to the upper
    areas."* Then, after the first fix: *"you walk up stairs, have to jump then walk then jump
    its very strange."*

    THE SECOND COMPLAINT WAS MY FIX BEING WRONG, AND THE TEST I WROTE FOR THE FIRST ONE SAID
    IT WAS FINE. That test asserted a tread at the LOWER of the two courses, which is where I
    had put them, so it was checking my mistake against itself - 276 transitions, 0 bad, and
    unwalkable. A test that encodes the rule the code encodes cannot catch the rule being
    wrong.

    So this does not assert a convention at all. It models the SURFACE HEIGHTS - a full block
    is one, a bottom stair is a half at the front and a whole at the back - and asserts that
    nothing on the walk rises more than half a block, which is what a player can step up
    without jumping. Whatever the right arrangement of treads is, this is the thing it has to
    achieve, and it fails on the wrong one:

        low deck Y+1 -> tread at the LOW course, top Y+1 -> high deck Y+2   = a 1.0 rise, JUMP
        low deck Y+1 -> tread at the HIGH course, front Y+1.5, back Y+2.0   = two 0.5s, walk

    CLAUDE.md had the convention written down correctly the whole time, read off Jack's own
    flight: "four consecutive treads, each ONE COURSE UP AND ONE STEP east". The tread climbs
    WITH the step.
    """
    d = built["d"]
    (ox, oy, oz) = built["origin"]
    pal, props = built["pal"], [nbt.state_props(q) for q in d.palette]
    walk = {i for i, n in enumerate(pal)
            if n == "minecraft:spruce_planks" or n.endswith("_stairs")}

    # per column: the top walk block, and the surface heights a body can stand at on it
    surf = {}
    for y, z, x in zip(*np.nonzero(np.isin(d.ids, list(walk)))):
        if d.ids[y + 1, z, x] or d.ids[y + 2, z, x]:
            continue
        k = (x + ox, z + oz)
        if k in surf and surf[k][0] >= y + oy:
            continue
        i = d.ids[y, z, x]
        if pal[i].endswith("_stairs"):
            hs = (y + oy + 0.5, y + oy + 1.0)      # front half, then the full back
        else:
            hs = (y + oy + 1.0,)
        surf[k] = (y + oy, hs)

    jumps, steep, checked = [], [], 0
    for (x, z), (ay, ah) in surf.items():
        nxt = surf.get((x, z + 1))
        if nxt is None:
            continue
        by, bh = nxt
        if ay == by:
            continue
        checked += 1
        if abs(ay - by) > 1:
            steep.append((x, z, by - ay))
            continue
        # going forward: from the highest you can stand on here to the lowest there, and back
        up = min(bh) - max(ah)
        down = min(ah) - max(bh)
        if up > 0.5 + 1e-9 or down > 0.5 + 1e-9:
            jumps.append((x, z, ay, by, round(max(up, down), 2)))

    assert checked > 100, f"only {checked} transitions - the walk is not being measured"
    assert not steep, (
        f"{len(steep)} step(s) of more than one course, e.g. {steep[:4]} - that is a wall. "
        f"The gullet shipped a SEVEN-course one and the only way past it was climbing the "
        f"animal's own raw throat.")
    assert not jumps, (
        f"{len(jumps)} transition(s) need a JUMP, e.g. {jumps[:4]} (x, z, from, to, rise). "
        f"A tread laid at the LOWER course drops you half a block and then asks for a whole "
        f"one, which is walk-jump-walk-jump.")


def test_the_whole_walk_is_on_BUILT_FLOOR_not_the_animal_s_raw_rock(built):
    """The other half of Jack's complaint, and the half a tread check cannot see.

    `test_..._RIGHT_TREAD` validates the steps that EXIST. It says nothing about a stretch
    where the design laid nothing at all - and the gullet shipped exactly that: six courses
    where `_room_span` refused the flat profile height, the builder shrugged, and the only way
    from the mantle to the head was scrambling up the animal's own raw throat. The walk flood
    passed the whole time, because scrambling over rock IS walking.

    So this floods from the shaft's foot across cells whose FLOOR THIS DESIGN PLACED, and
    demands it still reaches every room. A route that needs the animal's own geometry to be
    walkable is a route that was never built.

    (It also catches the measurement that hid it three separate times in one session: reading
    the LOWEST standable cell in a column finds the raw throat under a built deck and reports
    the deck as missing. CLAUDE.md records that classifier being wrong three times already.)
    """
    d, meta, cave = built["d"], built["meta"], built["cave"]
    (ox, oy, oz) = built["origin"]
    solid = built["solid"]
    mine = d.ids != 0

    ny, nz, nx = solid.shape
    st = np.zeros(solid.shape, bool)
    st[:-2] = solid[:-2] & ~solid[1:-1] & ~solid[2:] & mine[:-2]   # the block you stand ON is OURS
    sh = meta["shaft"]
    seed = (sh["foot_y"] - oy, sh["z"] - oz, sh["x"] - ox)
    assert st[seed], "the shaft's own foot is not built floor"
    seen = np.zeros(solid.shape, bool)
    seen[seed] = True
    dq = deque([seed])
    while dq:
        a, b, c = dq.popleft()
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            for dy in (0, 1, -1, -2, -3):
                q, r, t = a + dy, b + dz, c + dx
                if not (0 <= q < ny - 2 and 0 <= r < nz and 0 <= t < nx):
                    continue
                if dy == 1 and a + 3 < ny and solid[a + 3, b, c]:
                    continue
                if st[q, r, t]:
                    if not seen[q, r, t]:
                        seen[q, r, t] = True
                        dq.append((q, r, t))
                    break
    zs = np.nonzero(seen)[1] + oz
    for name, z0, z1 in (("the tail", *am.TAIL), ("the sounding hall", *am.SOUND),
                         ("the arcade", *am.ARCADE), ("the collar", *am.COLLAR),
                         ("the gullet", *am.GULLET), ("the bazaar", *am.BAZAAR),
                         ("the prow", *am.PROW)):
        n = int(((zs >= z0) & (zs <= z1)).sum())
        assert n > 15, (
            f"{name} has {n} cells reachable on floor this design BUILT - the walk gets there "
            f"by scrambling over the animal instead")
