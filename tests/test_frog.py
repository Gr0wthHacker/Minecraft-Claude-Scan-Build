"""The frog: one piece, ONE CONVEX MASS, two eyes that break the head line, feet on the ground,
and a back nothing can spawn on.

Every property here failed at least once while it was being built, and every one of those
failures shipped a clean audit - 0 problems, 0 overlap, one component - which is precisely why
they are pinned rather than eyeballed:

  * the hind legs read the whole of what had been built so far to find the flank, so each pass
    answered one cell further out than the last and the animal crept from 15 wide to 19;
  * the forelegs were built after the hind FOOT, which lies exactly where the hand goes, so
    every cell found the ground course taken and it shipped with `forelegs: 0` in its own
    sidecar - a frog with no arms is still one connected piece with no placement problem;
  * the eye dome sat UNDER the back line, so the one feature that says frog was swallowed by
    the outline and the panel could not name the animal;
  * and four separate attempts to ARTICULATE the mass - a bolted-on haunch, a shoulder, a deep
    waist, a raised knee - each came out as luggage: at thirteen wide and eight tall a one-cell
    step is not modelled form, it is the seam between two objects. That is what
    `test_the_mass_only_ever_falls_away_from_the_head` exists to stop being re-invented.
  * 129 of the 149 air cells over its back stood at block light zero, and the island night
    pass cannot see them - its classifier takes each column's topmost standable cell, and this
    lot is 113 courses under the island's belly.
"""
import json
import os
import sys
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pytest
import yaml

from mcbuild import blocks, nbt, palette, plot, schem
from mcbuild.gen import GENERATORS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = yaml.safe_load(open(os.path.join(ROOT, "configs", "lowland_frog.yaml"), encoding="utf-8"))
FULL = os.path.join(ROOT, "out", "island_full.litematic")

needs_world = pytest.mark.skipif(not os.path.exists(FULL),
                                 reason="needs out/island_full.litematic (run sync first)")
pytestmark = needs_world


@pytest.fixture(scope="module")
def built():
    c = GENERATORS["frog"].build(CFG["params"], None)
    m = c.to_model()
    ox, oy, oz = c.world_origin
    cells = {}
    for i, name in enumerate(m.names):
        short = name.split(":")[-1].split("[")[0]
        if short in ("air", "cave_air", "void_air"):
            continue
        ys, zs, xs = np.where(m.ids == i)
        for y, z, x in zip(ys, zs, xs):
            cells[(int(x) + ox, int(y) + oy, int(z) + oz)] = short
    return c, cells


@pytest.fixture(scope="module")
def world():
    m = schem.load(FULL)
    o = json.load(open(FULL[:-len(".litematic")] + ".scan.json", encoding="utf-8"))["origin"]
    names = [n.split(":")[-1].split("[")[0] for n in m.names]

    def at(x, y, z):
        ix, iy, iz = x - o["x"], y - o["y"], z - o["z"]
        if not (0 <= ix < m.ids.shape[2] and 0 <= iy < m.ids.shape[0] and 0 <= iz < m.ids.shape[1]):
            return "air"
        return names[m.ids[iy, iz, ix]]
    return at


PASSABLE = {"air", "cave_air", "void_air", "vine", "short_grass", "tall_grass", "fern",
            "large_fern", "moss_carpet", "azalea", "flowering_azalea", "poppy", "dandelion",
            "glow_lichen", "hanging_roots"}


def test_the_whole_animal_is_one_piece(built):
    """6-connectivity, which is the only kind that counts: a limb whose cells meet the body at
    a corner is a separate build, and that is how the first cats lost their ear tips."""
    _, cells = built
    start = next(iter(cells))
    seen, q = {start}, deque([start])
    while q:
        x, y, z = q.popleft()
        for n in ((x+1, y, z), (x-1, y, z), (x, y+1, z), (x, y-1, z), (x, y, z+1), (x, y, z-1)):
            if n in cells and n not in seen:
                seen.add(n)
                q.append(n)
    assert len(seen) == len(cells), f"{len(cells) - len(seen)} cells are not attached"


def test_every_part_got_built(built):
    """`forelegs: 0` shipped TWICE - a frog with no arms is still one connected piece with no
    placement problem and a clean BOM, so nothing else in the pipeline noticed either time."""
    c, _ = built
    feats = c.meta["features_built"]
    # NOT `haunch`. The haunch is not a part any more - see the monotonic-mass test - and a
    # required-parts list that still names it would demand the very thing that was removed.
    for part in ("body", "toes", "eyes", "mouth", "throat", "marks", "glow"):
        assert feats[part] > 0, f"{part} was not built at all: {feats}"


def test_the_gaze_is_cardinal_and_the_face_is_flat(built):
    """A head aimed off the grid renders its 'flat' face as a diagonal staircase of corners -
    the axolotl paid three passes for this, and no orthographic render can show it."""
    c, cells = built
    fx, fz = c.meta["facing"]
    assert abs(fx) + abs(fz) == 1, f"facing {c.meta['facing']} is not one cardinal unit"
    # ...measured on the FACE, found from the pale panel - not on the bounding box, whose front
    # plane is now two splayed toe tips. A test that reads the bounding box is measuring
    # whatever happens to stick out furthest, which is not the same question.
    p = {**GENERATORS["frog"].DEFAULTS, **CFG["params"]}
    pale = [k for k, v in cells.items() if v == p["belly"]]
    axis = 0 if fx else 2
    front = min(k[axis] for k in pale) if (fx or fz) < 0 else max(k[axis] for k in pale)
    nose = [k for k in pale if k[axis] == front]
    assert len(nose) >= 6, f"the face plane is {len(nose)} cell(s) - too small to be a face"


def test_the_eyes_are_pale_with_a_dark_pupil_and_read_from_the_side(built):
    """PALE WITH A DARK PUPIL, which is the reference and the opposite of what this carried for
    six passes. The eyes were a dark band with a gold chip set in it: at any distance that reads
    as sunglasses, and it goes black at the 1/6 thumbnail. On the statue the eyes are the
    BRIGHTEST thing on the animal, which is why you can name it across a room.

    AND AN EYE MUST EXIST IN MORE THAN ONE VIEW. Left dark on its outer face it was visible
    head-on and nowhere else - every other bearing had two dark tabs and no eye at all, which is
    most of why the profile could not be named."""
    c, cells = built
    p = {**GENERATORS["frog"].DEFAULTS, **CFG["params"]}
    fx, _fz = c.meta["facing"]
    across = 2 if fx else 0
    dark = [k for k, v in cells.items() if v == p["pupil"]]
    assert dark, "no eye boxes"
    eye_y = min(k[1] for k in dark)
    pale = [k for k, v in cells.items() if v == p["belly"] and k[1] >= eye_y]
    assert len(pale) >= 8, f"only {len(pale)} pale eye cells - the eyes are not the bright thing"
    mid = (min(k[across] for k in cells) + max(k[across] for k in cells)) / 2.0
    left = [k for k in pale if k[across] < mid]
    right = [k for k in pale if k[across] > mid]
    assert left and right, "the eyes are not a pair"
    assert abs(len(left) - len(right)) <= 1, "the eyes are not symmetric"
    for side in (left, right):
        out = 1 if side is right else -1
        assert any((k[0], k[1], k[2] + out) not in cells if across == 2
                   else (k[0] + out, k[1], k[2]) not in cells for k in side), (
            "no pale eye cell on the outer face - the eye cannot be seen in profile")
    paleset = set(pale)
    pupils = [k for k in dark
              if any((k[0] + a, k[1] + b, k[2] + d) in paleset
                     for a, b, d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0),
                                     (0, -1, 0), (0, 0, 1), (0, 0, -1)))]
    assert len(pupils) >= 2, "no dark pupil set into the pale iris"


def test_every_hard_step_in_the_mass_is_chamfered(built):
    """THE RELIEF PASS, and it is the last big gap the corpus measured: outside sculpture runs
    about 17% detail blocks and this animal ran 0.5%. Every plane met the next at a hard right
    angle, which is what makes a voxel mass read as a CRATE however well it is proportioned.

    The rule is general and places no cell by hand: wherever a course steps IN, the shelf it
    leaves gets a stair leaning into the wall above it; wherever it steps OUT, the overhang gets
    an upside-down stair tucked under it. So what is pinned is that the steps ARE chamfered -
    not where - because the profile table will keep moving and hand-listed positions would rot.
    """
    c, cells = built
    p = {**GENERATORS["frog"].DEFAULTS, **CFG["params"]}
    relief = c.meta["features_built"].get("relief", 0)
    assert relief >= 60, f"only {relief} steps were chamfered - the mass is still a crate"
    both = {nbt.state_props(e).get("half") for nm, e in
            zip(c.to_model().names, c.to_model().palette)
            if nm.split(":")[-1].split("[")[0] == p["stair"].split("[")[0]}
    assert both == {"bottom", "top"}, (
        f"the relief only uses {both} - a shelf wants a stair and an OVERHANG wants an "
        f"upside-down one, and half the steps on this animal are overhangs")
    detail = sum(1 for v in cells.values() if v.endswith("_stairs") or v.endswith("_slab"))
    assert detail / len(cells) >= 0.05, (
        f"detail blocks are {detail / len(cells):.1%} of the build; the corpus median is 17%")


def test_the_eye_boxes_sit_on_the_head(built):
    """FLUSH WITH THE FACE, AND EVERY COLUMN ON THE HEAD.

    They used to stand one station proud of the front plane, and Jack read that against the
    reference immediately: the reference's eyes sit ON the head with their front in the same
    plane as the face, and a cell of overhang is a sixth of this head's depth - it gives the
    animal a jutting brow with a shadow under it.

    Set back, nothing about the box hangs over air any more, so this pins ZERO rather than the
    half it used to tolerate. A box standing on nothing is a lamp on a bracket, which is what
    four earlier versions were - and 26 of 46 lid cells hung over the crown's own rounding
    once, which passed a clean audit."""
    _c, cells = built
    p = {**GENERATORS["frog"].DEFAULTS, **CFG["params"]}
    lids = [k for k, v in cells.items() if v == p["back"]
            and cells.get((k[0], k[1] - 1, k[2])) == p["pupil"]]
    assert len(lids) >= 8, f"only {len(lids)} lid cells over a dark box"
    loose = [k for k in lids if (k[0], k[1] - 2, k[2]) not in cells]
    assert not loose, f"{len(loose)} of {len(lids)} eye-box cells stand over nothing: {loose}"


def test_it_is_upright_and_the_head_is_a_third_of_it(built):
    """THE POSTURE IS THE REBUILD, so it is pinned rather than left to drift back.

    This test used to assert 0.55 <= h/w <= 0.92 - a crouching loaf - because an earlier note
    said "too tall and square" about a near-CUBIC build and I read it as "make it flatter". The
    loaf was then built three times and called a crate three times. At eight courses of body
    height there is no room for a head, arms or haunches: every feature is one or two cells and
    reads as a seam between two objects. Upright is what buys the room, and the lot was measured
    for it - 15x13 is the largest pad at roll <= 1 and it carries 107 courses of headroom, so
    height was always free and the footprint was the only constraint.

    AND UPRIGHT IS NOT THE SAME AS TALL. Measured off the picture the head and eyes are about
    forty per cent of the total and the body below is WIDER THAN IT IS TALL. Built at a third of
    that over a long torso it came out as a gravestone with a frog's head on it."""
    c, cells = built
    p = {**GENERATORS["frog"].DEFAULTS, **CFG["params"]}
    W = int(CFG["params"]["width"])
    lo = c.meta["base_y"]
    H = max(k[1] for k in cells) - lo + 1
    assert 1.15 <= H / W <= 1.75, f"height/width is {H / W:.2f}; the reference is about 1.4"

    mouth = [k for k, v in cells.items() if v == p["mark"]]
    assert mouth, "no mouth line to measure the head against"
    head = (max(k[1] for k in cells) - max(k[1] for k in mouth)) + 1
    assert 0.28 <= head / H <= 0.55, (
        f"the head and eyes are {head / H:.0%} of the animal; the reference is about 40% - "
        f"under a third it reads as a totem pole")
    eye_y = min(k[1] for k, v in cells.items() if v == p["pupil"])
    assert eye_y > lo + H * 0.6, "the eyes are not on top of the head"


def test_the_belly_is_an_oval_and_the_mouth_turns_up(built):
    """THE BELLY IS A LENS, NOT A RECTANGLE, and that is the fix for the doorway.

    A pale rectangle with hard vertical edges, inset in a darker frame, IS a door - and no amount
    of retuning the body shifted that reading. Four passes went into making the mass squatter,
    tapering it, darkening the arms and shortening the torso, and it stayed a gravestone until
    the panel itself stopped being a rectangle. The straight line is what says architecture; the
    curve is what says creature.

    And the mouth turns UP at the ends or it is a frown, and it carries on round the jaw or it
    is a head-on-only feature."""
    c, cells = built
    p = {**GENERATORS["frog"].DEFAULTS, **CFG["params"]}
    fx, _fz = c.meta["facing"]
    across, along = (2, 0) if fx else (0, 2)
    eye_y = min(k[1] for k, v in cells.items() if v == p["pupil"])
    belly = [k for k, v in cells.items() if v == p["belly"] and k[1] < eye_y - 2]
    assert belly, "no pale belly"
    # THE PLANE WITH THE MOST PALE CELLS ON IT, not the frontmost. The head's face stands
    # forward of the chest's, so `min(along)` picks the CHIN - which is a band, is supposed to
    # be a band, and fails an oval test for being one.
    from collections import Counter
    plane = Counter(k[along] for k in belly).most_common(1)[0][0]
    rows = {}
    for k in belly:
        if k[along] == plane:
            rows.setdefault(k[1], []).append(k[across])
    wide = {y: max(vs) - min(vs) + 1 for y, vs in rows.items()}
    ys = sorted(wide)
    peak = max(wide.values())
    assert wide[ys[0]] < peak and wide[ys[-1]] < peak, (
        f"the belly is a RECTANGLE - {wide[ys[0]]} wide at the bottom, {peak} at its widest, "
        f"{wide[ys[-1]]} at the top; a pale rectangle in a frame is a door")

    line = [k for k, v in cells.items() if v == p["mark"]]
    assert len(line) >= 7, f"the mouth line is {len(line)} cell(s) - too short to read"
    mid = (min(k[across] for k in cells) + max(k[across] for k in cells)) / 2.0
    front = min(k[along] for k in line) if fx < 0 else max(k[along] for k in line)
    on_face = [k for k in line if k[along] == front]
    inner = [k for k in on_face if abs(k[across] - mid) <= 2]
    outer = [k for k in on_face if abs(k[across] - mid) >= 4]
    assert inner and outer, "the mouth line does not reach from the middle to the corners"
    assert max(k[1] for k in outer) > max(k[1] for k in inner), (
        "the mouth line does not turn UP at the ends - that is a frown")
    assert [k for k in line if k[along] != front], "the mouth does not carry round the jaw"


def test_the_mass_is_one_piece_with_nothing_hanging_off_it(built):
    """WHAT THE OLD MONOTONIC TEST WAS REALLY BUYING, restated for an upright animal.

    It used to assert that the back line and the plan only ever FALL going back from the face -
    one convex loaf - because four attempts to articulate an eight-course body came out as
    luggage: a bolted-on haunch, a shoulder, a two-course waist, a raised knee. THAT WAS A SCALE
    LAW WRITTEN DOWN AS A UNIVERSAL ONE. Upright the animal is twenty-two courses, every one of
    those parts has the room to be a mass rather than a seam, and the profile is a STACK that
    rises and falls by design.

    What must still hold is that nothing hangs off it: one piece, and no fringe of cells
    attached by a single face. That is the property the old test was actually protecting."""
    _c, cells = built
    from collections import deque
    first = next(iter(cells))
    seen, q = {first}, deque([first])
    while q:
        x, y, z = q.popleft()
        for n in ((x+1, y, z), (x-1, y, z), (x, y+1, z), (x, y-1, z), (x, y, z+1), (x, y, z-1)):
            if n in cells and n not in seen:
                seen.add(n)
                q.append(n)
    assert len(seen) == len(cells), f"{len(cells) - len(seen)} cells hang off the animal"
    lonely = [k for k in cells
              if sum(((k[0]+a, k[1]+b, k[2]+d) in cells)
                     for a, b, d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0),
                                     (0, -1, 0), (0, 0, 1), (0, 0, -1))) < 2]
    assert len(lonely) * 100 < len(cells), (
        f"{len(lonely)} cells of {len(cells)} touch the animal on ONE face - that is fringe")


def test_the_toes_taper_and_they_lean_the_right_way(built):
    """THE FEET ARE BUILT OF STAIRS, which was Jack's own reading of the reference: *"this one
    had feet done by using stairs."* It is the thing four earlier foot shapes were missing and
    no arrangement of full blocks could supply - a cube toe ENDS, at a vertical face one block
    high, which is a plate; that is why every version read as a rake, a comb or a plus sign
    however the prongs were placed. A stair TAPERS to the ground, which is what a toe does.

    AND WHICH WAY IT LEANS IS NOT EYEBALLABLE. A stair's tall side is its `facing` - the
    convention this repo settled off a real flight and pinned in `test_stairhead.py` - and the
    3-D renderer drew stairs as full cubes until this same session, so a toe leaning backwards
    would have looked identical in every sheet here. A toe tapers DOWN and FORWARD, so its tall
    side faces BACK toward the body: the direction of increasing station, opposite the gaze."""
    c, _cells = built
    p = {**GENERATORS["frog"].DEFAULTS, **CFG["params"]}
    m = c.to_model()
    fx, fz = c.meta["facing"]
    want = {(1, 0): "east", (-1, 0): "west", (0, 1): "south", (0, -1): "north"}[(-fx, -fz)]
    # THE TOES' OWN STAIRS ONLY. The relief pass now puts stairs all over the body facing
    # every direction - chamfering a step means leaning INTO whichever wall is there - so a
    # test that asserts every stair faces one way is testing the wrong stairs.
    toe = p["toe_stair"].split("[")[0]
    stairs = [(nm, nbt.state_props(e)) for nm, e in zip(m.names, m.palette)
              if nm.split(":")[-1].split("[")[0] == toe]
    assert stairs, "the toes are not built of stairs"
    for nm, props in stairs:
        assert props.get("facing") == want, (
            f"{nm} faces {props.get('facing')}, not {want} - its tall side is its facing, so "
            f"this toe tapers the wrong way, and no render here would show it")
        assert props.get("half") == "bottom", f"{nm} is half={props.get('half')}, not bottom"


def test_it_is_symmetric_and_the_stairs_mirror(built):
    """A STATUE IS SYMMETRIC, and this one was not: Jack read it straight off the render -
    *"one side is more lumpy than the other."* Measured, 104 of 1,615 cells differed across the
    sagittal plane. The mass was symmetric BY CONSTRUCTION - every part is built for
    `s in (1, -1)` - and two things still broke it:

      * the coat's drifts each carried their own SIGNED offset, so the dark blotches landed in
        different places left and right. A dark patch reads as a RECESS, so an unmirrored coat
        is a body that looks dented down one side.
      * `put` refuses a cell the TERRAIN owns, and this lot rolls a course, so a foot cell
        existed on one side and not the other. One cell; it only takes one.

    AND A FACING MIRRORS, IT DOES NOT COPY. The sweep that fixes the above assigned each cell's
    state verbatim to its twin, and 60 of 134 stairs came out facing the SAME way on both sides
    - a chamfer leaning into the wall on one flank and out of it on the other. The renderer had
    only just learned to draw a stair as anything but a cube, so a day earlier this would have
    been invisible offline and wrong in game for ever.

    THE GROUND FILL IS EXEMPT AND MUST BE, and it is the last thing Jack caught: it fills each
    column down to its OWN ground, the ground here rolls two courses, and ALL 34 of its columns
    came out on one flank in the body's dark tone - a fringe hanging off one set of feet. A fill
    cannot be mirrored downward, because `put` refuses a cell the terrain owns, so the high side
    can never be given what the low side needs; equalising the other way leaves the low side
    floating. What CAN be fixed is the site and the colour, and both were: reseated on the
    flattest ground the lot allows that still clears the church, and every fill cell now takes
    the material of the cell it carries, so it reads as the toe REACHING the ground."""
    c, cells = built
    p = {**GENERATORS["frog"].DEFAULTS, **CFG["params"]}
    m = c.to_model()
    fx, fz = c.meta["facing"]
    ax, az = CFG["params"]["at"]
    BY = c.meta["base_y"]
    sx, sz = -fz, fx

    def loc(k):
        x, y, z = k
        return (fx * (x - ax) + fz * (z - az), sx * (x - ax) + sz * (z - az), y)

    occ = {}
    for k, v in cells.items():
        if k[1] < BY:
            continue                       # the skirt follows the ground, not the animal
        occ[loc(k)] = v
    geo = [k for k in occ if (k[0], -k[1], k[2]) not in occ]
    assert not geo, f"{len(geo)} cells above the belly plane have no mirror, e.g. {geo[:4]}"

    # ...and what IS unmirrored below it must be ground fill, colour-matched to what it carries
    below = {}
    for k, v in cells.items():
        if k[1] < BY:
            below[loc(k)] = v
    stray = [k for k in below if (k[0], -k[1], k[2]) not in below]
    assert len(stray) < 40, f"{len(stray)} unmirrored fill cells - reseat it on flatter ground"
    for k in stray:
        above = occ.get((k[0], k[1], BY))
        assert above is None or below[k] in (above, p["foot"], p["back"]), (
            f"the fill at {k} is {below[k]} under {above} - it must take the material of the "
            f"cell it carries, or it reads as a dark fringe hanging off one set of feet")
    col = [k for k in occ if occ[k] != occ[(k[0], -k[1], k[2])]]
    assert not col, f"{len(col)} cells differ in block across the mirror, e.g. {col[:4]}"

    # ...and the stairs LEAN the mirrored way, which the block-name check above cannot see
    NS = {(1, 0): "east", (-1, 0): "west", (0, 1): "south", (0, -1): "north"}
    flip = {NS[(sx, sz)]: NS[(-sx, -sz)], NS[(-sx, -sz)]: NS[(sx, sz)]}
    ox, oy, oz = c.world_origin
    st = {}
    for i, e in enumerate(m.palette):
        if "_stairs" not in nbt.state_name(e):
            continue
        f = nbt.state_props(e).get("facing")
        ys, zs, xs = np.where(m.ids == i)
        for y, z, x in zip(ys, zs, xs):
            st[loc((int(x) + ox, int(y) + oy, int(z) + oz))] = f
    assert st, "no stairs to check"
    bad = [(k, f, st.get((k[0], -k[1], k[2]))) for k, f in st.items()
           if k[1] and flip.get(f, f) != st.get((k[0], -k[1], k[2]))]
    assert not bad, f"{len(bad)} stairs do not mirror their facing, e.g. {bad[:3]}"


def test_every_foot_sits_on_its_own_ground(built, world):
    """One level per foot AND filled down to the turf. Held at the belly plane over ground that
    rolls away a pad floats; seated per column, its neighbours land on two courses and touch
    only diagonally - the turtle's flippers came off as four pieces that way."""
    _, cells = built
    floor = min(y for (_, y, _) in cells)
    for (x, y, z) in cells:
        if y != floor:
            continue
        assert world(x, y - 1, z) not in PASSABLE, f"the lowest cell at {(x, y, z)} stands on air"


def test_nothing_stands_in_water_and_nothing_is_covered(built, world):
    _, cells = built
    for (x, y, z), b in cells.items():
        here = world(x, y, z)
        assert here in PASSABLE, f"{b} at {(x, y, z)} covers {here}"


def test_it_keeps_off_the_church(built):
    """Nose 3 clear of the sanctum's east wall: a frog with its face against a wall is not
    looking at the building, it is stuck to it."""
    _, cells = built
    sanctum = os.path.join(ROOT, "out", "Lowland Sanctum.work.json")
    if not os.path.exists(sanctum):
        pytest.skip("needs the sanctum's work list")
    wall = {(c[0], c[2]) for c in json.load(open(sanctum, encoding="utf-8"))["cells"]}
    near = min(max(abs(x - sx), abs(z - sz)) for (x, _, z) in cells for (sx, sz) in wall)
    assert near >= 3, f"the frog comes within {near} of the sanctum"


def test_it_stays_on_the_plot(built):
    _, cells = built
    pl = plot.find(FULL)
    off = [k for k in cells if not pl.contains(k[0], k[2])]
    assert not off, f"{len(off)} cells outside the plot, e.g. {off[:3]}"


def test_every_block_is_cheap_spendable_and_1_19(built):
    _, cells = built
    for b in sorted(set(cells.values())):
        assert palette.tier(b) == "cheap", f"{b} is {palette.tier(b)} tier"
        assert blocks.spendable(b), f"{b} is currency on this server"
        assert blocks.available(b), f"{b} is not in the 1.19 allowlist"


def test_the_coat_is_a_ladder_and_it_is_not_the_ground(built):
    """Three tones of one hue beat two tones and a third - the flamingo's bruise - and the
    ladder has to be a ladder: every step visible.

    AND THE GROUND TEST IS COLOUR DISTANCE, NOT LUMINANCE. The turtle already proved the point
    on this floor: `brown_wool` is within five of moss in luminance and reads perfectly, because
    what separates them is a full hue flip. Testing luminance would have failed the reference's
    own palette and passed a green frog.
    """
    p = {**GENERATORS["frog"].DEFAULTS, **CFG["params"]}
    lum = [sum(blocks.color(p[k])) / 3 for k in ("back", "flank", "mark")]
    assert lum[0] > lum[1] > lum[2], f"back/flank/mark are not a descending ladder: {lum}"
    assert min(lum[i] - lum[i + 1] for i in range(2)) >= 20, f"two rungs look alike: {lum}"
    assert sum(blocks.color(p["belly"])) / 3 > lum[0] + 30, "the belly does not read as pale"
    moss = blocks.color("moss_block")
    body = blocks.color(p["back"])
    dist = sum((a - b) ** 2 for a, b in zip(moss, body)) ** 0.5
    assert dist >= 60, f"the body is {dist:.0f} from the moss it sits on - it will vanish"


def test_nothing_can_spawn_on_its_back(built):
    """THE ISLAND NIGHT PASS CANNOT SEE THIS ANIMAL. Its classifier takes the topmost standable
    cell in a column, and this lot lies 113 courses under the island's belly - so the frog, the
    lot and everything in it are invisible to it. Measured directly instead: block light
    propagated through the finished world, over every cell the frog itself puts a top on."""
    from mcbuild import nightlight
    c, cells = built
    Y_LO, Y_HI = 20, 60
    cap = schem.load(FULL)
    o = json.load(open(FULL[:-len(".litematic")] + ".scan.json", encoding="utf-8"))["origin"]
    ox, oy, oz = o["x"], o["y"], o["z"]
    pal = [n.split(":")[-1] for n in cap.names]
    x0 = max(ox, min(k[0] for k in cells) - 18)
    x1 = min(ox + cap.ids.shape[2] - 1, max(k[0] for k in cells) + 18)
    z0 = max(oz, min(k[2] for k in cells) - 18)
    z1 = min(oz + cap.ids.shape[1] - 1, max(k[2] for k in cells) + 18)
    NY, NZ, NX = Y_HI - Y_LO + 1, z1 - z0 + 1, x1 - x0 + 1
    name = np.empty((NY, NZ, NX), dtype=object)
    for y in range(Y_LO, Y_HI + 1):
        for z in range(z0, z1 + 1):
            for x in range(x0, x1 + 1):
                name[y - Y_LO, z - z0, x - x0] = pal[cap.ids[y - oy, z - oz, x - ox]]
    for (x, y, z), b in cells.items():
        if Y_LO <= y <= Y_HI:
            name[y - Y_LO, z - z0, x - x0] = b

    flat = name.reshape(-1)
    states = sorted(set(flat.tolist()))
    ix = {st: i for i, st in enumerate(states)}
    ids = np.array([ix[st] for st in flat], np.int32).reshape(name.shape)
    opaque, emit, _passy, _spawn, _water = nightlight.classify(states)
    light = nightlight.propagate(opaque[ids], emit[ids])

    tops = {}
    for (x, y, z) in cells:
        tops[(x, z)] = max(tops.get((x, z), -999), y)
    dark = [(x, y + 1, z) for (x, z), y in tops.items()
            if Y_LO <= y + 1 <= Y_HI and light[y + 1 - Y_LO, z - z0, x - x0] == 0]
    assert not dark, f"{len(dark)} cells over the frog are at block light 0, e.g. {dark[:5]}"
