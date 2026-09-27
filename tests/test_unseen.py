"""What `mcbuild/ops/unseen.py` promises, asserted rather than eyeballed.

Every check here is a PROPERTY, stated in a different vocabulary from the code that satisfies it.
The pass decides what is visible by flooding from the outside; these tests decide it by counting a
cell's own six neighbours. A test that re-derived the flood would agree with a broken flood -
this repo has shipped that once already, in `SplitOrderTest`, and stayed green while production
threw on every call.
"""
from __future__ import annotations

import numpy as np
import pytest

from mcbuild import nbt, schem
from mcbuild.ops.unseen import EDGE12, EDGE_PAIRS, Unseen, _connect, hollow_unseen

FACES = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]


def block(shape, *names):
    """A model of `shape` (y, z, x) full of air, with `names` available in the palette."""
    pal = [nbt.block_state("air")] + [nbt.block_state(n) for n in names]
    return schem.Model(np.zeros(shape, np.int32), pal)


def solid_box(m, y0, y1, z0, z1, x0, x1, idx=1):
    m.ids[y0:y1, z0:z1, x0:x1] = idx


def removed_cells(before: np.ndarray, after: np.ndarray) -> list[tuple[int, int, int]]:
    return [tuple(p) for p in np.argwhere(before & ~after)]


# ---------------------------------------------------------------- the invariant

def test_nothing_with_an_air_neighbour_is_ever_removed():
    """THE ONE PROMISE. A block you can see is a block that stays, and a block with air beside it
    is a block you can see - counted per cell, with no flood anywhere near it."""
    m = block((16, 16, 16), "stone")
    solid_box(m, 3, 13, 3, 13, 3, 13)
    before = m.solid()
    hollow_unseen(m, shell=1)
    after = m.solid()
    for y, z, x in removed_cells(before, after):
        for dy, dz, dx in FACES:
            assert before[y + dy, z + dz, x + dx], \
                f"removed ({x},{y},{z}) which had air on a face - that is a hole in the skin"


def test_a_solid_cube_keeps_exactly_its_skin():
    m = block((16, 16, 16), "stone")
    solid_box(m, 3, 13, 3, 13, 3, 13)
    r = hollow_unseen(m, shell=1)
    assert r.before == 10 ** 3
    assert r.after == 10 ** 3 - 8 ** 3          # the boundary, and not one cell more
    assert r.n == 8 ** 3
    # a flat-faced box has no edge-diagonal that lacks a corner, so nothing is held for the printer
    assert r.held.get("a printer needs the corner", 0) == 0


def test_it_only_ever_removes_and_never_adds_or_rewrites():
    m = block((16, 16, 16), "stone")
    solid_box(m, 3, 13, 3, 13, 3, 13)
    before, pal = m.solid(), list(m.palette)
    hollow_unseen(m, shell=1)
    assert not (m.solid() & ~before).any(), "a hiding pass placed a block"
    assert [nbt.state_name(e) for e in m.palette] == [nbt.state_name(e) for e in pal]


def test_a_deeper_skin_never_removes_more_than_a_shallow_one():
    out = []
    for shell in (1, 2, 3):
        m = block((20, 20, 20), "stone")
        solid_box(m, 2, 18, 2, 18, 2, 18)
        out.append(hollow_unseen(m, shell=shell).n)
    assert out[0] > out[1] > out[2]


# ---------------------------------------------------------------- seeing through

def test_a_block_behind_GLASS_is_visible_and_stays():
    """Air is not the test. You can see through glass, so the flood has to as well - get this
    backwards and a wall behind a window quietly disappears."""
    m = block((16, 16, 16), "stone", "glass")
    solid_box(m, 3, 13, 3, 13, 3, 13)
    m.ids[8, 8, 3] = 2                      # one pane let into the skin
    m.ids[8, 8, 4] = 1                      # the stone directly behind it
    hollow_unseen(m, shell=1)
    assert m.name_at(4, 8, 8).endswith("stone"), "a cell behind glass was treated as buried"


def test_a_block_behind_LEAVES_is_visible_and_stays():
    m = block((16, 16, 16), "stone", "oak_leaves")
    solid_box(m, 3, 13, 3, 13, 3, 13)
    m.ids[8, 8, 3] = 2
    m.ids[8, 8, 4] = 1
    hollow_unseen(m, shell=1)
    assert m.name_at(4, 8, 8).endswith("stone")


# ---------------------------------------------------------------- the guards

def test_the_cell_under_a_GRAVITY_block_is_kept():
    """Rule 13 from underneath: the gravel crust stays because it is the skin, and pulling the
    block out from under it pours the crust into the mountain."""
    m = block((16, 16, 16), "stone", "gravel")
    solid_box(m, 3, 13, 3, 13, 3, 13)
    m.ids[12, 8, 8] = 2                     # gravel ON the top face - a surface cell
    r = hollow_unseen(m, shell=1)
    assert m.name_at(8, 11, 8).endswith("stone"), "the block under the gravel went"
    assert r.held.get("under a gravity block", 0) >= 1


def test_a_POOL_WALL_is_kept():
    m = block((16, 16, 16), "stone", "water")
    solid_box(m, 3, 13, 3, 13, 3, 13)
    m.ids[11, 8, 8] = 2                     # a cell of water let into the mass
    hollow_unseen(m, shell=1)
    for dy, dz, dx in FACES:
        assert m.ids[11 + dy, 8 + dz, 8 + dx] != 0, "opened a wall of a pool"


def test_a_MECHANISM_keeps_the_blocks_it_reads_and_stands_on():
    m = block((16, 16, 16), "stone", "repeater")
    solid_box(m, 3, 13, 3, 13, 3, 13)
    m.ids[8, 8, 8] = 2
    r = hollow_unseen(m, shell=1, mech_clear=2)
    for dy, dz, dx in FACES:
        assert m.ids[8 + dy, 8 + dz, 8 + dx] != 0, "took a block a repeater needs"
    assert r.held.get("near a mechanism", 0) >= 1


def test_WOOL_IS_NOT_A_MECHANISM_on_its_own():
    """`protect.MECHANISM` holds `wool` because wool can be a sculk sensor's silencer. Read as a
    general keep-out it deletes every wool block in the park - 12,500 cells of dinosaur - which is
    the mistake CLAUDE.md records twice. Fabric is protected by being NEAR a machine."""
    m = block((16, 16, 16), "light_gray_wool")
    solid_box(m, 3, 13, 3, 13, 3, 13)
    r = hollow_unseen(m, shell=1)
    assert r.n == 8 ** 3, "buried wool was kept for being wool"


def test_a_BURIED_PARTIAL_BLOCK_keeps_whatever_holds_it_up():
    m = block((16, 16, 16), "stone", "stone_slab")
    solid_box(m, 3, 13, 3, 13, 3, 13)
    m.ids[8, 8, 8] = 2
    hollow_unseen(m, shell=1)
    assert m.ids[7, 8, 8] != 0, "took the block a buried slab stands on"


def test_a_buried_LIGHT_is_kept():
    m = block((16, 16, 16), "stone", "ochre_froglight")
    solid_box(m, 3, 13, 3, 13, 3, 13)
    m.ids[8, 8, 8] = 2
    r = hollow_unseen(m, shell=1)
    assert m.name_at(8, 8, 8).endswith("froglight")
    assert r.held.get("emits light", 0) >= 1


def test_only_and_keep_name_the_blocks_that_move():
    m = block((16, 16, 16), "stone", "cobblestone")
    solid_box(m, 3, 13, 3, 13, 3, 13)
    m.ids[6:10, 6:10, 6:10] = 2                       # a cobble core inside a stone mass
    r = hollow_unseen(m, shell=1, only={"cobblestone"})
    assert set(r.removed) == {"cobblestone"}

    m2 = block((16, 16, 16), "stone")
    solid_box(m2, 3, 13, 3, 13, 3, 13)
    assert hollow_unseen(m2, shell=1, keep={"stone"}).n == 0


# ---------------------------------------------------------------- the printer

def terrain(n: int = 22):
    """Rough ground, which is what the park's mass actually is.

    Not a wedge and not a cube: both of those are convex enough that their skin stays connected
    however deep you carve, so they pass whatever `_connect` does and prove nothing. A heightmap
    that steps by two or three is where a hollow skin comes apart - the top of one column and the
    exposed flank of its neighbour meet at an EDGE, and the cell that used to bridge them was
    interior. The pattern is arithmetic rather than seeded noise so it cannot drift with numpy.
    """
    m = block((18, n + 4, n + 4), "stone")
    for z in range(n):
        for x in range(n):
            h = 3 + ((z * 7 + x * 13 + (z * x) % 5) % 10)
            m.ids[1:1 + h, z + 2, x + 2] = 1
    return m


def face_components(s: np.ndarray) -> int:
    seen = np.zeros_like(s)
    n = 0
    for start in map(tuple, np.argwhere(s)):
        if seen[start]:
            continue
        n += 1
        stack = [start]
        seen[start] = True
        while stack:
            y, z, x = stack.pop()
            for dy, dz, dx in FACES:
                p = (y + dy, z + dz, x + dx)
                if all(0 <= p[i] < s.shape[i] for i in range(3)) and s[p] and not seen[p]:
                    seen[p] = True
                    stack.append(p)
    return n


def test_A_CELL_VISIBLE_THROUGH_A_DIAGONAL_SLIT_IS_KEPT():
    """THE SECOND THING THAT SHIPPED BROKEN. Minecraft culls a face whose neighbour is an opaque
    cube, so a block with all six faces covered draws nothing and looks safe to take. It is not:
    taking it exposes its NEIGHBOURS' faces to the cavity, and where two blocks meet along an edge
    there is a slit you can see straight through. Jack: *"a lot of the rail way on the side of the
    prism etc is all hollowed out and empty."* Measured then: 8,500 removed cells had a see-through
    cell among their 26, 5,820 of them in Prismworks.

    So the rule is 26 and not 6 - all twenty-six neighbours opaque, or the cell stays."""
    m = block((20, 20, 20), "stone")
    solid_box(m, 2, 18, 2, 18, 2, 18)
    m.ids[9, 9, 9] = 0                       # one cell of air buried in the mass
    hollow_unseen(m, shell=1)
    # (10,10,9) has six opaque faces and touches that air along an EDGE
    assert m.ids[10, 10, 9] != 0, "took a cell you can see through the slit at the air's edge"
    assert m.ids[10, 10, 10] != 0, "took a cell you can see through the slit at the air's corner"


def test_the_hollowed_skin_is_ONE_PIECE_a_printer_can_walk():
    """A PRINTER CLICKS A FACE, so two cells that meet only along an edge leave everything behind
    them unreachable. It was the whole reason `_connect` exists: with the rule at 6 a one-deep skin
    took the park's printing islands from 1,582 to 3,409.

    At 26 the rule mostly carries this by itself - nothing is taken next to a slit, so the corners
    of a staircase survive anyway, and no fixture here breaks with `connect` off. `_connect` still
    fires (233 cells on the shipped park) and is kept as the GUARANTEE rather than the mechanism:
    what is asserted is the property, not which pass delivered it."""
    for conn in (False, True):
        m = terrain()
        assert face_components(m.solid()) == 1, "the ground was broken before it was hollowed"
        hollow_unseen(m, shell=1, connect=conn)
        n = face_components(m.solid())
        assert n == 1, f"connect={conn}: the printer cannot walk this skin - {n} separate pieces"


def test_connect_restores_the_CORNER_of_a_diagonal_join():
    """The mechanism on its own, on a join built by hand so it cannot stop being exercised."""
    surv = np.zeros((7, 7, 7), bool)
    surv[3, 3, 3] = surv[4, 4, 3] = True          # edge-diagonal: they share an edge, no face
    removed = np.zeros((7, 7, 7), bool)
    removed[4, 3, 3] = removed[3, 4, 3] = True    # both corners that would join them

    back = _connect(surv, removed)
    assert back.sum() == 1, f"expected exactly one corner back, got {int(back.sum())}"
    assert back[4, 3, 3] or back[3, 4, 3]
    assert not (back & ~removed).any(), "put back a cell that was never removed"

    # ...and it leaves a join alone when one corner is already standing
    surv2 = surv.copy(); surv2[4, 3, 3] = True
    assert not _connect(surv2, removed).any()


def test_connect_only_ever_puts_back_a_cell_that_was_there():
    m = terrain()
    before = m.solid()
    hollow_unseen(m, shell=1, connect=True)
    assert not (m.solid() & ~before).any()


def test_every_edge_diagonal_is_covered_and_none_of_them_is_a_face():
    assert len(EDGE12) == 12
    for d in EDGE12:
        assert sum(1 for c in d if c) == 2, f"{d} is not an edge diagonal"
        assert d not in FACES


def test_each_join_is_visited_from_ONE_END_ONLY():
    """Walking all twelve offsets sees {A, B} twice and puts BOTH corners back where one does the
    job. The six whose leading step is +1 cover every join exactly once - asserted as a partition,
    so neither a missing direction nor a duplicated one can creep back."""
    assert len(EDGE_PAIRS) == 6
    assert set(EDGE_PAIRS) <= set(EDGE12)
    for d in EDGE_PAIRS:
        assert tuple(-c for c in d) not in EDGE_PAIRS, f"{d} and its mirror are both in the set"
    covered = set(EDGE_PAIRS) | {tuple(-c for c in d) for d in EDGE_PAIRS}
    assert covered == set(EDGE12), "some edge diagonal is reachable from neither end"


def test_connect_is_a_no_op_where_there_is_nothing_to_join():
    surv = np.zeros((6, 6, 6), bool)
    surv[2:4, 2:4, 2:4] = True
    assert not _connect(surv, np.zeros_like(surv)).any()


# ---------------------------------------------------------------- reporting

def test_the_report_says_what_it_traded():
    m = block((16, 16, 16), "stone")
    solid_box(m, 3, 13, 3, 13, 3, 13)
    r = hollow_unseen(m, shell=1)
    text = r.report()
    assert "sealed cavity" in text, "a pass that opens dark volume has to say so"
    assert f"{r.n:,}" in text
    assert isinstance(r, Unseen) and r.cavity == r.n


@pytest.mark.parametrize("shell", [1, 2])
def test_a_model_with_nothing_hidden_is_left_alone(shell):
    m = block((10, 10, 10), "stone")
    m.ids[5, 5, 5] = 1                       # one lonely block: all six faces are outside
    assert hollow_unseen(m, shell=shell).n == 0


# ---------------------------------------------------------------- the shipped bug

def sealed_room():
    """A mass with a room inside it and NO WAY IN. The shape that broke a shipped park."""
    m = block((20, 20, 20), "stone")
    solid_box(m, 2, 18, 2, 18, 2, 18)
    m.ids[7:13, 7:13, 7:13] = 0              # the room, sealed on all six sides
    return m


def test_A_SEALED_ROOM_KEEPS_ITS_WALLS():
    """THE ONE THAT SHIPPED BROKEN. The first version asked whether a cell was adjacent to air the
    OUTSIDE CAN REACH, so the lining of a station room, a coaster's tunnel bore or a cavity in the
    rock read as buried - and taking the lining exposed the next course, which the same mask had
    already condemned. On the park that was 8,523 cells of tunnel and station masonry.

    Neither guard could see it: the reachable set really was unchanged, because gutting a sealed
    room does not connect it to anything, and every render matched because it is all behind the
    outer skin. Jack found it by walking inside."""
    m = sealed_room()
    before = m.solid()
    hollow_unseen(m, shell=1)
    after = m.solid()

    # the six wall planes - the cells that share a FACE with the room's air. The twelve edges and
    # eight corners are NOT lining: every face of an edge cell is covered by a wall cell, so it
    # renders nothing to anyone standing inside, and removing it is the pass working.
    lining = set()
    for a in range(7, 13):
        for bb in range(7, 13):
            lining |= {(6, a, bb), (13, a, bb), (a, 6, bb), (a, 13, bb), (a, bb, 6), (a, bb, 13)}
    for y, z, x in sorted(lining):
        assert after[y, z, x], (f"stripped ({x},{y},{z}), which lines a sealed room - a wall you "
                                "can stand next to is a wall you can see")
    assert (before & ~after).any(), "the fixture has no buried mass at all - it tests nothing"


def test_a_sealed_room_does_not_cascade_outward():
    """The failure was not one course, it was every course: the mask is computed once, so the
    cell behind the lining was condemned in the same pass as the lining."""
    m = sealed_room()
    hollow_unseen(m, shell=1)
    s = m.solid()
    # the six courses of mass between the room and the outside must all still be there somewhere
    assert s[2:18, 2:18, 2].all() and s[2:18, 2:18, 17].all(), "the outer skin came away"
    assert s[6, 10, 10] and s[13, 10, 10], "the room's floor or ceiling lining came away"
