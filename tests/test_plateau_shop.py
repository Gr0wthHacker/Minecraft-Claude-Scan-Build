"""THE FIELD SHOP - the contracts that keep it a shop rather than another closed hall.

Jack, on the lot the Vantage Lookout was retired from: *"what can go there ... maybe we keep 1
building and put another shop there"*, and on where: *"tower lot"*.

Three of this park's buildings have been retired for one shape - a hall on a lot, good inside and
saying nothing on the street - so what is pinned hardest here is the OPEN FRONT. The rest is the
Abyss Market's rule about what a public shop may hold (nothing), the re-theme leak this land is
one config away from (spruce), and the two failures this design actually shipped: a terrace paved
two courses short of its own building, and a board hung on the one face that has no wall.
"""
from __future__ import annotations

from collections import deque

import numpy as np
import pytest
import yaml

from mcbuild import blocks, palette
from mcbuild.gen import plateaushop
from mcbuild.nbt import state_name

CONFIG = "configs/pf_plateau_shop.yaml"


@pytest.fixture(scope="module")
def p():
    return {**plateaushop.SHOP, **yaml.safe_load(open(CONFIG, encoding="utf-8"))["params"]}


@pytest.fixture(scope="module")
def canvas(p):
    return plateaushop.build(dict(p))


@pytest.fixture(scope="module")
def names(canvas):
    return [state_name(e).split(":")[-1] for e in canvas.palette]


@pytest.fixture(scope="module")
def used(canvas, names):
    return {n for i, n in enumerate(names) if n and int((canvas.ids == i).sum())}


# --------------------------------------------------------------------------- what it IS


def test_the_FRONT_IS_OPEN_and_there_is_no_fourth_wall(p, canvas, names):
    """A hall reads as a building; a counter reads as a shop.

    `Arrival Court`, `Boomtown Spine` and the `Skill Arcade` were all retired for the same shape,
    and the last of them measured 84% of its footprint solid and twenty-one courses tall with
    three working games inside that nothing on the street mentioned. The one thing that cannot be
    allowed back is a wall across this face.
    """
    v0, v1, u0, u1 = (int(x) for x in p["shop"])
    front, hgt = int(p["front"]), int(p["height"])
    #: the counter is one course; everything from waist height to the fascia has to be open, or a
    #: guest cannot see into it and it stops being a shopfront.
    #: A FITTING IS NOT A WALL. The bell is bolted to the counter face on purpose - that is the
    #: verb - so what is forbidden here is the WALL MATERIAL, not every block in the plane.
    for u in range(u0, u1 + 1):
        for y in range(2, hgt - 1):
            n = names[canvas.ids[y, u, front]]
            assert n in ("", "air", "bell"), (
                f"the shopfront is walled with {n} at u{u} y{y} - this is a hall again")


def test_it_HOLDS_NOTHING(used):
    """The Abyss Market settled it: no container anywhere in a public shop.

    *"A barrel standing empty in a public build reads as a shop somebody has already looted, and a
    chest anyone can reach is a chest anyone can empty."* The trade is the server's own `/shops`.
    """
    bad = [n for n in used
           if any(k in n for k in ("barrel", "chest", "shulker", "hopper", "dropper",
                                   "dispenser", "furnace"))]
    assert not bad, f"containers in a public shop: {bad}"


def test_there_is_SOMETHING_TO_DO_AT_THE_COUNTER(used):
    """A counter with no verb is a prop, which is the complaint this whole land is answering.

    A bell is one block, needs no circuit, is cheap and on the 1.19 server, and is what the
    Menagerie's muster yard settled on for exactly the same reason.
    """
    assert "bell" in used, "the counter has no verb at all"


def test_EVERY_BOARD_IS_ACTUALLY_PLACED(canvas):
    """`_Lot.sign` refuses a board with nothing behind it, and a refusal is SILENT.

    The trade board shipped once hung on the open face - which is the one face with no wall by
    construction - so the design carried one fewer sign than its config asked for and nothing
    reported it. This park has shipped that failure in four separate generators.
    """
    want = 3           # the shopfront title, the /shops board, the terrace plaque
    assert len(canvas.meta["signs"]) == want, (
        f"{len(canvas.meta['signs'])} boards placed of {want} - one was refused in silence")


def test_every_sign_line_fits_the_board(p):
    """Fifteen characters. This park has shipped "MINE CART ESCAP" and "and prize windo"."""
    lines = [p["title"]] + list(p.get("lines") or []) + list(p.get("shops_lines") or [])
    lines += list((p.get("plaque") or {}).get("lines") or [])
    over = [x for x in lines if len(x) > 15]
    assert not over, f"clipped mid-word: {over}"


# --------------------------------------------------------------------------- the rim


def test_the_BRINK_IS_RAILED_the_whole_way_across(p, canvas, names):
    """U0 is the park's own edge with open void past it, and the terrace runs to it."""
    #: A POST IS PART OF A RAIL. Every fifth column carries a lamp standard instead of a fence
    #: panel, and counting only the panels reports a complete guard as four cells short.
    guard = [i for i, n in enumerate(names) if n in ("jungle_fence", "jungle_log")]
    railed = sum(1 for v in range(p["lot"][0]) if canvas.ids[1, 0, v] in guard)
    assert railed == p["lot"][0], (
        f"only {railed} of {p['lot'][0]} columns of the rim are guarded")


def test_NOTHING_BLOCKS_THE_VIEW_over_the_rim(p, canvas):
    """The terrace is where the belvedere is seen from, so the building keeps off it.

    A shop pushed to the boundary would put its back wall where the view is - which is the whole
    reason the lot is laid out front-to-back rather than filled.
    """
    #: NOTHING ON IT STANDS OVER THREE COURSES - a lamp standard, a bench, a planter and the
    #: plaque are all under a walker's sightline. Written as "nothing at all above y3" the test
    #: forbids the plaque, which is the one thing on the terrace that is supposed to be read.
    rim = int(p.get("rim", 3))
    tall = [(v, u, y) for v in range(p["lot"][0]) for u in range(rim)
            for y in range(4, canvas.ids.shape[0]) if canvas.ids[y, u, v]]
    assert not tall, f"the terrace's own furniture blocks the view: {tall[:4]}"


def test_the_TERRACE_MEETS_THE_BUILDING(p, canvas):
    """It paves up to the plinth, not to its own declared depth.

    Stopped at `rim` it came away as a ninety-cell island: one empty course between the terrace
    and the building's footing, which is legal, supported, perfectly clean paving that nothing
    joins to anything.
    """
    #: MEASURED WHERE THEY MEET, over the building's own width: the terrace's last row and the
    #: plinth's first must BOTH be laid, or there is an empty course between them and the terrace
    #: is an island however well paved it is.
    v0, v1 = int(p["shop"][0]), int(p["shop"][1])
    last, first = int(p["shop"][2]) - 2, int(p["shop"][2]) - 1
    for v in range(v0, v1 + 1):
        assert canvas.ids[0, last, v] and canvas.ids[0, first, v], (
            f"terrace and plinth do not meet at v{v}")


# --------------------------------------------------------------------------- the palette


def test_it_is_the_LANDS_OWN_KIT_and_not_the_retired_mining_towns(used):
    """`park.py`'s `frontier` palette is still spruce and cobblestone - the theme this land LEFT.

    Everything standing across the avenue is `bonebed.CAMP`: jungle timber and canvas. Two
    buildings in one land in two woods is how a re-theme leaks, and this land's signage audit
    already caught the same thing in words.
    """
    leak = [n for n in used if n.startswith("spruce_") and n != "spruce_wall_sign"]
    assert not leak, f"the retired mining town's wood is back: {leak}"
    assert any(n.startswith("jungle_") for n in used)


def test_it_is_cheap_spendable_and_on_the_1_19_server(used):
    """Rule 12 and rule 16, asked of the registry rather than of the comment beside the table."""
    dear = [n for n in used if palette.tier(n) == "expensive"]
    assert not dear, f"expensive blocks in a field shop: {dear}"
    unspendable = [n for n in used if not blocks.spendable(n)]
    assert not unspendable, f"currency on this server: {unspendable}"


def test_every_plant_roots_in_the_dirt_family(canvas, names):
    """Rule 11. A fern set on `deepslate_bricks` is a placement problem a render draws happily."""
    soil = ("moss_block", "grass_block", "dirt", "coarse_dirt", "podzol", "rooted_dirt", "mud")
    for i, n in enumerate(names):
        if n not in ("fern", "short_grass", "moss_carpet", "azalea"):
            continue
        ys, us, vs = np.where(canvas.ids == i)
        for y, u, v in zip(ys, us, vs):
            under = names[canvas.ids[y - 1, u, v]] if y else ""
            assert under in soil, f"{n} at v{v} y{y} u{u} is rooted in {under!r}"


def test_it_is_ONE_CONNECTED_PIECE(canvas):
    s = canvas.ids > 0
    sy, su, sv = s.shape
    seen = np.zeros_like(s)
    ys, us, vs = np.where(s)
    q = deque([(int(ys[0]), int(us[0]), int(vs[0]))])
    seen[q[0]] = True
    n = 0
    while q:
        y, u, v = q.popleft()
        n += 1
        for dy, du, dv in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            a, b, c = y + dy, u + du, v + dv
            if 0 <= a < sy and 0 <= b < su and 0 <= c < sv and s[a, b, c] and not seen[a, b, c]:
                seen[a, b, c] = True
                q.append((a, b, c))
    assert n == int(s.sum()), f"{int(s.sum()) - n} cells in strays"


def test_it_stays_INSIDE_ITS_OWN_LOT(canvas):
    """`_Lot.put` is the one boundary check, and a refusal is counted rather than clipped."""
    assert canvas.meta["refused"] == 0, (
        f"{canvas.meta['refused']} cells fell outside the declared lot")
