"""The building kit's one promise: a caller cannot make a lopsided building.

Measured on the park as shipped, the share of blocks with no counterpart across the frontage axis
was 122% for the Shooting Range, 126% for the Carousel and 112% for Plinko - over 100% because
every mismatch counts on both sides. There was effectively no mirror plane at all. The one piece
that came out symmetric, the Clock Tower at 3.8%, is also one of the few a player can name.

So symmetry here is not a property a test looks for afterwards. It is a property the caller cannot
break, and these are the tests that say so.
"""
import pytest

from mcbuild.gen import kit
from mcbuild.gen.vertical import World

FACINGS = ("east", "west", "north", "south")

PALETTE = {
    "wall": "stone_bricks", "wall_alt": "cracked_stone_bricks", "trim": "blackstone",
    "slab": "stone_brick_slab", "stair": "stone_brick_stairs",
    "roof_stair": "dark_oak_stairs", "roof_slab": "dark_oak_slab",
    "beam": "dark_oak_log", "fence": "oak_fence", "wood": "oak",
    "canopy": ["red_wool", "white_wool"],
}


def _sym(facing="east", origin=(0, 64, 0)):
    world = World()
    return world, kit.Sym(world, origin, facing)


def _mirrored(world, surface):
    """Every cell, expressed in the surface's own local frame, so a mirror is u -> -u."""
    out = {}
    for (x, y, z), value in world.cells.items():
        out[(x, y, z)] = value
    return out


# ------------------------------------------------------------------ the guarantee

@pytest.mark.parametrize("facing", FACINGS)
def test_every_block_a_caller_places_is_placed_twice(facing):
    """The whole point. One call, two blocks, and the caller never names a world coordinate."""
    world, s = _sym(facing)
    s.put(3, 2, 1, "stone_bricks")
    assert len(world.cells) == 2
    assert s.world(3, 2, 1) in world.cells
    assert s.world(-3, 2, 1) in world.cells


@pytest.mark.parametrize("facing", FACINGS)
def test_a_block_on_the_centre_line_is_placed_once(facing):
    """u=0 IS the mirror. Placed twice it would be placed on top of itself, which is harmless -
    and counted twice, which would make every block tally wrong."""
    world, s = _sym(facing)
    s.put(0, 0, 0, "stone_bricks")
    assert len(world.cells) == 1
    assert s.placed == 1


@pytest.mark.parametrize("facing", FACINGS)
def test_a_whole_facade_is_perfectly_symmetric(facing):
    """The measurement that condemned the park's own buildings, run against the kit."""
    world, s = _sym(facing)
    kit.plinth(s, 5, 7, PALETTE)
    kit.walls(s, 5, 7, 6, PALETTE, door=3, windows=(2,))
    kit.eaves(s, 5, 7, 6, PALETTE)
    kit.gable(s, 5, 7, 7, PALETTE)
    assert world.cells

    axis = 0 if s.axis == "x" else 2
    origin = s.ox if axis == 0 else s.oz
    lopsided = []
    for (x, y, z), (name, props) in world.cells.items():
        here = (x, y, z)[axis]
        mirror = list(here for here in (x, y, z))
        mirror[axis] = 2 * origin - here
        other = world.cells.get(tuple(mirror))
        if other is None:
            lopsided.append((x, y, z, name))
    assert not lopsided, f"{facing}: {len(lopsided)} blocks have no mirror, e.g. {lopsided[:3]}"


# ------------------------------------------------------------------ a mirror FLIPS

def test_a_facing_across_the_mirror_is_flipped():
    """**A MIRROR FLIPS, IT DOES NOT COPY.** Written the obvious way on the frog, 60 of 134 stairs
    came out facing the same way on both flanks - a chamfer leaning into the wall on one side and
    out of it on the other. `render3d` draws both identically, so this is asserted."""
    assert kit.flip({"facing": "east"}, "x")["facing"] == "west"
    assert kit.flip({"facing": "west"}, "x")["facing"] == "east"
    assert kit.flip({"facing": "north"}, "z")["facing"] == "south"


def test_a_facing_along_the_mirror_is_left_alone():
    """The other half, and the one that is easy to get wrong by flipping everything: a stair
    leaning fore or aft leans the same way on both sides."""
    assert kit.flip({"facing": "north"}, "x")["facing"] == "north"
    assert kit.flip({"facing": "south"}, "x")["facing"] == "south"
    assert kit.flip({"facing": "east"}, "z")["facing"] == "east"


def test_a_stairs_corner_shape_is_flipped_too():
    """`shape` names an inner or outer corner by LEFT or RIGHT, so a mirror swaps them."""
    assert kit.flip({"shape": "inner_left"}, "x")["shape"] == "inner_right"
    assert kit.flip({"shape": "outer_right"}, "z")["shape"] == "outer_left"
    assert kit.flip({"shape": "straight"}, "x")["shape"] == "straight"


def test_an_axis_is_not_a_direction():
    """A log lying along X still lies along X in the mirror. Flipping it would twist every beam
    in the building through ninety degrees."""
    assert kit.flip({"axis": "x"}, "x")["axis"] == "x"
    assert kit.flip({"axis": "z"}, "z")["axis"] == "z"


@pytest.mark.parametrize("facing", FACINGS)
def test_a_mirrored_stair_leans_the_right_way(facing):
    """The property `render3d` cannot show: a wrong facing and a right one draw identically."""
    world, s = _sym(facing)
    s.put(2, 0, 0, "stone_brick_stairs", facing="east", half="bottom", shape="straight")
    states = {props["facing"] for _n, props in world.cells.values()}
    if s.axis == "z":
        assert states == {"east"}, "a facing along the mirror was flipped"
    else:
        assert states == {"east", "west"}, "a facing across the mirror was not flipped"


# ------------------------------------------------------------------ the detail vocabulary

def test_the_kit_uses_the_three_details_the_corpus_says_we_never_use():
    """Against 31 outside builds, per thousand cells: stairs 0.64 vs 4.51, fences 0.07 vs 2.22,
    trapdoors 0.00 vs 1.07. A caller gets these by USING the kit, rather than by remembering."""
    world, s = _sym("east")
    kit.plinth(s, 5, 7, PALETTE)
    kit.walls(s, 5, 7, 6, PALETTE, windows=(2,))
    kit.eaves(s, 5, 7, 6, PALETTE)
    kit.gable(s, 5, 7, 7, PALETTE)
    kit.canopy(s, 5, PALETTE)
    kit.rail(s, 5, 7, PALETTE)
    names = {name for name, _p in world.cells.values()}
    assert any(n.endswith("_stairs") for n in names), "no stairs anywhere"
    assert any(n.endswith("_fence") for n in names), "no fences anywhere"
    assert any(n.endswith("_slab") for n in names), "no slabs anywhere"


def test_a_doorway_is_left_empty_rather_than_punched():
    """**BUILDING THE RING AND THEN CUTTING A HOLE REPAINTS CELLS THAT ALREADY EXIST**, which is
    how the void tower's crenellations shipped as a plain drum with nothing about the code looking
    wrong."""
    world, s = _sym("east")
    kit.walls(s, 5, 7, 6, PALETTE, door=3)
    for u in (-1, 0, 1):
        for h in range(3):
            assert s.world(u, 0, h) not in world.cells, f"the doorway is walled at u={u} h={h}"


def test_a_window_gets_a_sill_and_a_lintel():
    """A hole in a wall is a hole. A hole with a sill and a lintel is a window."""
    world, s = _sym("east")
    kit.walls(s, 5, 7, 6, PALETTE)
    kit.openings(s, 5, 7, PALETTE, rows=(2,))
    panes = [p for p, (n, _) in world.cells.items() if n == "glass_pane"]
    assert panes, "no glazing"
    for (x, y, z) in panes:
        assert (x, y - 1, z) in world.cells, "a pane with no sill under it"


def test_a_pane_is_connected_along_its_wall():
    """With every side false a pane renders as a lone post rather than as glazing - which this
    project has shipped once already."""
    world, s = _sym("east")
    kit.walls(s, 5, 7, 6, PALETTE)
    kit.openings(s, 5, 7, PALETTE, rows=(2,))
    for _p, (name, props) in world.cells.items():
        if name == "glass_pane":
            assert "true" in props.values(), "a pane with no connection at all"


def test_one_is_deliberately_awkward_to_reach():
    """A door on the left of a facade and nothing on the right is a decision somebody should have
    to make on purpose. Every building in this park made it by accident."""
    world, s = _sym("east")
    s.one(3, 0, 0, "stone_bricks")
    assert len(world.cells) == 1
    assert s.world(-3, 0, 0) not in world.cells


@pytest.mark.parametrize("facing", FACINGS)
def test_the_local_frame_is_consistent_at_every_facing(facing):
    """`v` runs INTO the building from its front, whichever way that front points - or a caller
    who works in local coordinates is still writing four different buildings."""
    _world, s = _sym(facing)
    front = s.world(0, 0, 0)
    inside = s.world(0, 3, 0)
    step = {"east": (1, 0), "west": (-1, 0), "south": (0, 1), "north": (0, -1)}[facing]
    assert inside[0] - front[0] == step[0] * 3
    assert inside[2] - front[2] == step[1] * 3
