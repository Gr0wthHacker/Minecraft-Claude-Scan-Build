"""Half-block surfacing: which cells get halved, which blocks may be used, and why not more.

Every rule here exists because breaking it produced a visible defect: an orange stripe down a
brown bear's back, a half-block crack the length of its belly, or a foot hovering off the ground.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
from mcbuild import blocks
from mcbuild.gen import shell


def _plate(w=7, d=7, y=5):
    """A flat slab of cells - the case that must NOT be halved."""
    return {(x, y, z) for x in range(w) for z in range(d)}


def _step(w=7, d=8, y=5):
    """Two plateaus one course apart, on a SOLID mass.

    Solid all the way down, because a cell is only halved when there is material behind the face
    being cut - halving a one-course sheet is a hole, not a smoothing.
    """
    out = {(x, yy, z) for x in range(w) for z in range(d) for yy in range(y + 1)}
    out |= {(x, y + 1, z) for x in range(w) for z in range(d // 2, d)}
    return out


# ---------------------------------------------------------------- material choice

def test_a_pillar_is_never_slabbed():
    """The colour DB samples a block's TOP face. On a log that is end grain while the side - the
    face a statue shows - is bark, so matching `acacia_log`'s orange top to `acacia_slab` drew a
    bright orange line down a grey-brown bear. `blocks.kind` settles it, not a rule of thumb."""
    for n in ("oak_log", "mangrove_wood", "bone_block", "stripped_dark_oak_wood"):
        assert blocks.kind(n) == "rotated_pillar", f"{n} is no longer a pillar - revisit this rule"
        assert shell.slab_for(n, witnesses=(n,)) is None, f"{n} must not be slabbed"


def test_a_uniform_block_matches_its_own_family_exactly():
    assert shell.slab_for("spruce_planks", witnesses=("spruce_planks",)) == "spruce_slab"
    assert shell.slab_for("stone", witnesses=("stone",)) == "stone_slab"


def test_no_slab_is_offered_when_nothing_is_close_enough():
    """Better a full cube than a visible colour seam down the animal's back.

    Self-calibrating, because an exact match (`spruce_planks` -> `spruce_slab`, distance 0) is
    rightly still offered at zero tolerance - the threshold has to be tested against a block that
    actually costs something.
    """
    import math
    wit = ("dirt", "spruce_planks")
    got = shell.slab_for("dirt", witnesses=wit)
    if got is None:
        return                                        # already refused at the default tolerance
    d = math.dist(blocks.color("dirt"), blocks.color(got))
    assert d > 0, "pick a block whose best match is not exact"
    assert shell.slab_for("dirt", max_shift=d - 0.01, witnesses=wit) is None


def test_only_witnessed_families_are_used():
    """`blocks.available()` is a no-op while the allowlist is provisional - it answers True for
    1.21 blocks on a 1.19 server. Availability is inferred from families the server was SEEN to
    have, because Minecraft ships a material family complete."""
    trusted = shell.trusted_slabs(())
    assert trusted, "the confirmed list should always yield something"
    assert "pale_oak_slab" not in trusted, "an unwitnessed family must not be used"
    with_oak = shell.trusted_slabs(("dark_oak_planks",))
    assert "dark_oak_slab" in with_oak, "witnessing dark oak must unlock its slab"
    assert "pale_oak_slab" not in with_oak


def test_family_of():
    assert shell.family_of("stripped_dark_oak_wood") == "dark_oak"
    assert shell.family_of("minecraft:oak_slab") == "oak"
    assert shell.family_of("spruce_planks") == "spruce"
    assert shell.family_of("stone") == "stone"


def test_volume_fraction():
    assert shell.volume_fraction("minecraft:oak_slab[type=top]") == 0.5
    assert shell.volume_fraction("oak_stairs") == 0.75
    assert shell.volume_fraction("minecraft:stone") == 1.0


# ---------------------------------------------------------------- geometry

def test_a_flat_plateau_is_left_alone():
    """Halving a whole flat surface lowers it uniformly: it costs blocks and smooths nothing.
    The first version counted 'nothing above the neighbour' as a step, which is true right across
    a plateau, and drew a half-block crack the length of the bear's belly."""
    cells = _plate()
    skin = {c: "spruce_planks" for c in cells}
    interior = {c for c in cells if all((c[0]+dx, c[1], c[2]+dz) in cells
                                        for dx, dz in ((1,0),(-1,0),(0,1),(0,-1)))}
    assert interior, "test plate has no interior"
    over = shell.slab_shell(cells, skin, "spruce_planks")
    assert not (set(over) & interior), "the middle of a flat plate must stay full blocks"


def test_a_step_is_halved():
    cells = _step()
    skin = {c: "spruce_planks" for c in cells}
    over = shell.slab_shell(cells, skin, "spruce_planks")
    assert over, "a one-course step is exactly what this is for"
    assert all(v[0] == "spruce_slab" for v in over.values())


def test_a_cell_in_a_hollow_is_left_alone():
    """Halving a cell whose neighbour is higher digs a notch rather than smoothing a step."""
    cells = {(x, 5, z) for x in range(5) for z in range(5)}
    cells |= {(0, 6, z) for z in range(5)}                   # a wall along one edge
    skin = {c: "spruce_planks" for c in cells}
    over = shell.slab_shell(cells, skin, "spruce_planks")
    assert (1, 5, 2) not in over, "the cell against the wall is in a hollow"


def test_the_feet_are_never_lifted_off_the_ground():
    """An underside cell becomes a TOP slab, which sits in the upper half of its cell. Do that to
    the course the animal stands on and it hovers - and the `grounded` gate cannot see it, because
    the cell is still occupied."""
    cells = {(x, y, z) for x in range(4) for y in range(6) for z in range(4)}
    cells |= {(9, y, 9) for y in range(6)}                   # a separate post, exposed all round
    skin = {c: "spruce_planks" for c in cells}
    over = shell.slab_shell(cells, skin, "spruce_planks", under=True)
    for (x, y, z), (name, props) in over.items():
        if props.get("type") == "top":
            assert y > 1, f"a top slab at y={y} would lift the model off the ground"


def test_under_can_be_turned_off():
    cells = _step()
    skin = {c: "spruce_planks" for c in cells}
    over = shell.slab_shell(cells, skin, "spruce_planks", under=False)
    assert all(v[1]["type"] == "bottom" for v in over.values())


def test_every_emitted_state_is_legal():
    """An illegal state fails here rather than being silently refused by Litematica in game."""
    cells = _step()
    skin = {c: "spruce_planks" for c in cells}
    for name, props in shell.slab_shell(cells, skin, "spruce_planks").values():
        assert blocks.validate(name, props) == [], f"{name}{props} is not a legal state"


def test_shell_only_ever_returns_cells_that_exist():
    cells = _step()
    skin = {c: "spruce_planks" for c in cells}
    assert set(shell.slab_shell(cells, skin, "spruce_planks")) <= cells
