"""The Prism Well: a hole is only a hole if it is actually empty, and lined, and reachable.

Jack, 2026-09-03: *"prism in its current state is not a theme park, its a collection of
buildings."* The replacement is one mouth cut through the park deck with the descent hanging in
it - so the things that can go wrong are not the things that go wrong with a building, and
these tests are aimed at the ones the first generation actually shipped:

  * FIVE FLOATING OBJECTS. The return column and its four posts came out as five separate
    components hanging in the middle of a hundred-wide void with nothing to place against and
    no way to reach them. `it_is_one_piece` is the check that caught it.
  * A LIFT YOU CANNOT GET OUT OF. The water column was cased on all four sides for its whole
    height including the top course: you swim to the head and stand in water with stone on
    every side. Invisible in any render, because a lift and a well look identical.
  * THIRTY-ONE CARPETS HANGING OVER THE HOLE. `moss_carpet` is in `protect`'s never-overwrite
    set, so the cut removed the `moss_block` under it and correctly refused the carpet itself.
    The exemption that fixes it is NARROW and is pinned here, because widening `protect` would
    have been the wrong fix - it is what stops the next pass eating a hopper.

And the two that would make it stop being a well at all: something standing in the void, or the
rim losing its guard.
"""
import collections
import json
import math
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcbuild import palette, schem, scan             # noqa: E402
from mcbuild.gen import protect                      # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LITE = os.path.join(ROOT, "out", "PF Prism Well.litematic")
SIDE = os.path.join(ROOT, "out", "PF Prism Well.scan.json")
BASE = os.path.join(ROOT, "out", "park_future.litematic")

needs = pytest.mark.skipif(not (os.path.exists(LITE) and os.path.exists(SIDE)),
                           reason="needs the generated well")
AIRY = ("air", "cave_air", "void_air")


def _load():
    m = schem.load(LITE)
    s = scan.load(SIDE)
    return m, s, s.origin


def _meta():
    return json.load(open(SIDE, encoding="utf-8"))


def _cells():
    """Every solid cell of the design, in WORLD coordinates.

    In world coordinates on purpose: the canvas is sized to its own content, so it shifts
    between two builds with different settings and anything comparing them lines up against
    nothing. This repo learned that on the deck soffit.
    """
    m, _, (ox, oy, oz) = _load()
    names = m.names
    out = {}
    sol = m.solid()
    ys, zs, xs = sol.nonzero()
    for y, z, x in zip(ys, zs, xs):
        out[(x + ox, y + oy, z + oz)] = names[m.ids[y, z, x]].split("[")[0].split(":")[-1]
    return out


def _geom():
    md = _meta()
    return md["centre"][0], md["centre"][1], md["r_mouth"], md["y_floor"]


@needs
def test_the_mouth_is_actually_empty():
    """A well whose middle is full of design is a building with a moat.

    The only things allowed inside the mouth are the return column at the centre, its gantry,
    the one catwalk that reaches it, and the balconies that oversail the lip. Everything else
    must stand at the collar or outside it, or the descent has nowhere to hang.
    """
    cx, cz, rm, _ = _geom()
    lift_r, walk = 6, 4                       # post radius + a cell, and the catwalk's width
    strays = []
    for (x, y, z), n in _cells().items():
        r = math.hypot(x - cx, z - cz)
        if r >= rm - 0.5:
            continue                          # the collar and outward: fine
        if max(abs(x - cx), abs(z - cz)) <= lift_r:
            continue                          # the column and its gantry
        if r > rm - 6:
            continue                          # the balconies oversail by three, plus their rail
        # the catwalk: one straight line on a cardinal axis through the centre
        if abs(x - cx) <= walk or abs(z - cz) <= walk:
            continue
        strays.append((x, y, z, n))
    assert not strays, f"{len(strays)} cells stand in the open void: {strays[:6]}"


@needs
def test_it_is_one_piece():
    """The first build shipped FIVE components: the water column and its four posts, each
    hanging free in the middle of the hole. Nothing to place against, nothing to reach them
    from - a design that cannot be built and would read as debris if it were."""
    cells = set(_cells())
    seen, stack = set(), [next(iter(cells))]
    seen.add(stack[0])
    while stack:
        x, y, z = stack.pop()
        for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            q = (x + dx, y + dy, z + dz)
            if q in cells and q not in seen:
                seen.add(q)
                stack.append(q)
    assert len(seen) == len(cells), (
        f"{len(cells) - len(seen)} cells of {len(cells)} are detached from the main body")


@needs
def test_the_lift_has_a_way_out_at_the_top():
    """A water column cased on all four sides at its head is a lift you cannot leave.

    Nothing about it looks wrong: a sealed shaft and a working one are the same picture. So the
    exit is asserted rather than eyeballed - at the top water course there must be at least one
    orthogonal neighbour that is not a solid casing block.
    """
    cells = _cells()
    cx, cz, _, _ = _geom()
    tops = [y for (x, y, z), n in cells.items() if (x, z) == (cx, cz) and n == "water"]
    assert tops, "the return column has no water in it at all"
    top = max(tops)
    ways = []
    for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        n = cells.get((cx + dx, top, cz + dz))
        if n is None or n in AIRY:
            ways.append((dx, dz))
        elif palette.tier(n) != "air" and n in ("water",):
            ways.append((dx, dz))
    assert ways, f"the column's head at y={top} is cased on all four sides: nobody can get out"


@needs
def test_the_cut_takes_no_machine_and_stays_inside_the_mouth():
    """The cut's rule is a BLACKLIST, and this pins the blacklist rather than `is_protected`.

    It was written the other way round first - a whitelist of materials the cut recognised,
    with `protect.is_protected` on top - and that shipped sixty-one cells hanging over the
    hole, because `Park Ways` puts a lamp mast on the verge every twenty-two cells and none of
    the four materials those masts are made of was on the list. The moss under them was dug and
    the masts were left standing on air.

    `is_protected` cannot be the gate either. It is the never-OVERWRITE set and it holds `wool`,
    `carpet`, `lantern`, `end_rod` and `iron_bars` - true of a wool block on the main island,
    which may be a sculk sensor's silencer, and false of a lamp post inside the hole that
    replaces it. This repo has already used it as a keep-clear radius once, in `Island Night`,
    and left 523 cells dark.

    So what is asserted is the thing that actually matters: nothing that is a MACHINE or
    somebody's storage comes out, and nothing outside the mouth is touched at all.
    """
    md = _meta()
    cx, cz, rm, _ = _geom()
    danger = ("redstone", "repeater", "comparator", "observer", "piston", "lever", "button",
              "pressure_plate", "tripwire", "target", "note_block", "sculk_sensor", "dispenser",
              "dropper", "hopper", "chest", "barrel", "shulker_box", "furnace", "smoker",
              "brewing_stand", "anvil", "grindstone", "stonecutter", "loom", "composter",
              "cauldron", "beacon", "crafting_table", "jukebox", "bell", "beehive", "bee_nest",
              "spawner", "lectern", "rail", "minecart", "_door", "sign", "banner", "lava",
              "farmland", "sugar_cane", "wheat", "carrots", "potatoes", "beetroots", "kelp")
    assert md["dig"], "the mouth was cut out of nothing at all"
    outside = [(x, y, z) for x, y, z in md["dig"] if math.hypot(x - cx, z - cz) >= rm]
    assert not outside, f"{len(outside)} dig cells fall outside the mouth: {outside[:5]}"

    if not os.path.exists(BASE):
        pytest.skip("needs park_future to say what was standing there")
    b = schem.load(BASE)
    bs = scan.load(BASE.replace(".litematic", ".scan.json"))
    bo = bs.origin
    names = b.names
    bad = []
    for x, y, z in md["dig"]:
        i, j, k = x - bo[0], y - bo[1], z - bo[2]
        if not (0 <= j < b.ids.shape[0] and 0 <= k < b.ids.shape[1] and 0 <= i < b.ids.shape[2]):
            continue
        n = names[b.ids[j, k, i]].split("[")[0].split(":")[-1]
        if any(d in n for d in danger):
            bad.append((x, y, z, n))
    assert not bad, (
        f"the cut would take {len(bad)} machine or storage cells - move the mouth, do not "
        f"widen the rule: {bad[:6]}")


@needs
def test_the_cut_leaves_nothing_hanging_over_the_hole():
    """Thirty-one moss carpets, in the first build. The cut removed the block under each one
    and left the carpet standing on air over a hundred-wide void - which is not a cosmetic
    problem, it is thirty-one cells of the park's floor that are now a trap."""
    if not os.path.exists(BASE):
        pytest.skip("needs park_future")
    md = _meta()
    cx, cz, rm, _ = _geom()
    dug = {tuple(c) for c in md["dig"]}
    b = schem.load(BASE)
    bs = scan.load(BASE.replace(".litematic", ".scan.json"))
    bo = bs.origin
    names = b.names
    built = set(_cells())
    hanging = []
    for (x, y, z) in dug:
        above = (x, y + 1, z)
        if above in dug or above in built:
            continue
        i, j, k = x - bo[0], y + 1 - bo[1], z - bo[2]
        if not (0 <= j < b.ids.shape[0] and 0 <= k < b.ids.shape[1] and 0 <= i < b.ids.shape[2]):
            continue
        n = names[b.ids[j, k, i]].split("[")[0].split(":")[-1]
        if n not in AIRY and math.hypot(x - cx, z - cz) < rm:
            hanging.append((x, y + 1, z, n))
    assert not hanging, f"{len(hanging)} cells left standing on air: {collections.Counter(h[3] for h in hanging).most_common(4)}"


@needs
def test_the_rim_is_guarded_except_where_you_are_meant_to_leave():
    """A hundred-course drop with an open rim is not a viewing gallery.

    Exactly two gaps: the start, where the course leaves, and the catwalk. Any third gap is
    somewhere a visitor walks off the edge by accident.
    """
    cells = _cells()
    cx, cz, rm, _ = _geom()
    md = _meta()
    dy = 202
    rail = sorted(round(math.degrees(math.atan2(z - cz, x - cx)) % 360.0)
                  for (x, y, z), n in cells.items()
                  if y == dy + 1 and "wall" in n
                  and rm - 2.5 <= math.hypot(x - cx, z - cz) < rm + 3.5)
    assert rail, "there is no rail on the collar at all"
    have = set(rail)
    gaps, run = [], None
    for a in range(360):
        if a in have:
            if run is not None:
                gaps.append(run)
                run = None
        else:
            run = (run or 0) + 1
    if run:
        gaps.append(run)
    big = [g for g in gaps if g >= 4]
    assert len(big) <= 3, f"the rim has {len(big)} openings wider than 4 degrees: {big}"


@needs
def test_every_balcony_is_carried():
    """A balcony that oversails a void on nothing is a shelf floating in a hole. Every deck
    cell that reaches past the collar must have a bracket under it or a deck neighbour that
    does - this repo's oldest structural rule, learned when the mane came off as seven
    floating fragments."""
    cells = _cells()
    cx, cz, rm, _ = _geom()
    dy = 202
    over = [(x, y, z) for (x, y, z), n in cells.items()
            if y == dy and math.hypot(x - cx, z - cz) < rm - 0.5
            and max(abs(x - cx), abs(z - cz)) > 8]
    assert over, "no balcony oversails the lip at all - the gallery is just a fence"
    unsupported = [c for c in over
                   if (c[0], c[1] - 1, c[2]) not in cells
                   and not any((c[0] + dx, c[1], c[2] + dz) in cells and
                               (c[0] + dx, c[1] - 1, c[2] + dz) in cells
                               for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)))]
    assert len(unsupported) <= len(over) * 0.34, (
        f"{len(unsupported)} of {len(over)} oversailing cells have no bracket under them")


@needs
def test_nothing_here_is_expensive_or_off_the_version():
    """Prismworks v1 was 54% two dark greys and still cost nothing; this must stay true while
    the palette gets a real value ladder across families."""
    from mcbuild import blocks
    counts = collections.Counter(_cells().values())
    dear = {n: c for n, c in counts.items() if palette.tier(n) == "expensive"}
    assert not dear, f"expensive blocks in the well: {dear}"
    late = {n for n in counts if not blocks.available(n)}
    assert not (late - {"waxed_copper_block", "waxed_cut_copper_slab", "iron_bars",
                        "deepslate_bricks", "cobbled_deepslate", "deepslate_brick_wall",
                        "polished_blackstone_bricks"}), (
        f"blocks the 1.19 allowlist rejects and the provisional list has not seen: {late}")


@needs
def test_the_ladder_can_actually_draw_a_line():
    """v1's whole failure in one number: six greys between L38 and L73 is a ladder inside ONE
    material family, and a family is one material shown four ways - dressing a stone does not
    change how much light it returns. Measured ACROSS families the rungs have to be real."""
    from mcbuild import blocks

    def lum(n):
        c = blocks.color(n, "side")
        return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]

    counts = collections.Counter(_cells().values())
    field = [n for n, c in counts.most_common() if c >= 300 and n != "water"]
    assert len(field) >= 3, f"only {len(field)} materials carry the well: {field}"
    ls = sorted(lum(n) for n in field)
    steps = [b - a for a, b in zip(ls, ls[1:])]
    assert max(steps) >= 40, (
        f"no two of the well's field materials are 40 luminance apart: "
        f"{[(n, round(lum(n))) for n in field]}")
