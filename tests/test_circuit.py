"""The redstone simulator, against hand-worked cases.

Every assertion here is a fact about Minecraft that can be checked by hand on a workbench, not a
snapshot of what the code currently prints. That distinction matters more here than anywhere else
in this repo: a simulator that agrees with itself is what would certify a broken casino.
"""
from __future__ import annotations

import pytest

from mcbuild.circuit import Circuit


def line(n, y=0, z=0, start=0, block="redstone_wire"):
    return {(start + i, y, z): block for i in range(n)}


def test_wire_loses_one_per_block():
    """The single most load-bearing number in redstone: 15 reaches 15 blocks and dies."""
    c = Circuit.from_cells({**line(16), (-1, 0, 0): "redstone_block"})
    c.step()
    assert c.level((0, 0, 0)) == 15
    assert c.level((1, 0, 0)) == 14
    assert c.level((14, 0, 0)) == 1
    assert c.level((15, 0, 0)) == 0, "a signal must die at 15 blocks, not 16"


def test_a_lever_you_have_not_flipped_powers_nothing():
    c = Circuit.from_cells({(0, 0, 0): "lever[face=floor,facing=north]", **line(3, start=1)})
    c.step()
    assert not c.powered((1, 0, 0))
    c.set((0, 0, 0), True)
    c.step()
    assert c.powered((1, 0, 0)), "a flipped lever must reach the wire beside it"


def test_a_torch_inverts_what_it_stands_on():
    """The whole of redstone logic is this one fact."""
    # THE LEVER MUST BE ON THE TORCH'S OWN BLOCK. The first version of this test put it on the
    # block NEXT to it and expected the torch to react - but power does not flow from one solid
    # block to another, so that circuit does nothing in Minecraft either. The test was wrong and
    # the simulator was right, which is the outcome a hand-worked case exists to produce.
    c = Circuit.from_cells({
        (1, -1, 0): "stone",
        (0, -1, 0): "lever[face=wall,facing=west]",     # attached to the stone at (1,-1,0)
        (1, 0, 0): "redstone_torch",
        (2, 0, 0): "redstone_wire",
    })
    c.run(3)
    assert c.powered((2, 0, 0)), "an unpowered torch is LIT and powers its wire"
    c.set((0, -1, 0), True)
    c.run(4)
    assert not c.powered((2, 0, 0)), "powering the block under a torch must switch it OFF"


def test_a_torch_powers_the_block_above_it():
    """Strong power upward is how every torch tower and every inverter stack works."""
    c = Circuit.from_cells({
        (0, 0, 0): "redstone_torch",
        (0, 1, 0): "stone",
        (1, 1, 0): "redstone_wire",
    })
    c.run(2)
    assert c.level((1, 1, 0)) == 15, "the block above a lit torch is STRONGLY powered"


def test_a_repeater_points_where_it_faces():
    """Backwards is the commonest redstone mistake and it is invisible in a render."""
    c = Circuit.from_cells({
        (0, 0, 0): "redstone_block",
        (1, 0, 0): "repeater[facing=east,delay=1]",
        (2, 0, 0): "redstone_wire",
        (-1, 0, 0): "redstone_wire",
    })
    c.run(4)
    assert c.powered((2, 0, 0)), "a repeater must drive the cell it FACES"


def test_a_repeater_restores_a_dying_signal():
    c = Circuit.from_cells({
        (-1, 0, 0): "redstone_block", **line(15),
        (15, 0, 0): "repeater[facing=east,delay=1]",
        **line(5, start=16),
    })
    c.run(5)
    assert c.level((14, 0, 0)) == 1, "the signal should be nearly dead at the repeater"
    assert c.level((16, 0, 0)) == 15, "and full strength again after it"


def test_a_repeater_delay_is_honoured():
    """A delay of 4 must take longer than a delay of 1, or every clock built here is wrong."""
    def ticks_to_fire(delay):
        c = Circuit.from_cells({
            (0, 0, 0): "lever[face=floor,facing=north]",
            (1, 0, 0): f"repeater[facing=east,delay={delay}]",
            (2, 0, 0): "redstone_lamp",
        })
        c.set((0, 0, 0), True)
        for t in range(1, 30):
            c.step()
            if c.powered((2, 0, 0)):
                return t
        return -1
    fast, slow = ticks_to_fire(1), ticks_to_fire(4)
    assert fast > 0 and slow > 0, "both delays must eventually fire"
    assert slow > fast, "delay 4 must be slower than delay 1"


def test_a_repeater_is_locked_from_the_side():
    """Every memory cell in the game is built from this, and a simulator without it reports
    every latch as a piece of wire."""
    c = Circuit.from_cells({
        (0, 0, 0): "lever[face=floor,facing=north]",
        (1, 0, 0): "repeater[facing=east,delay=1]",
        (2, 0, 0): "redstone_lamp",
        # a second repeater pointing INTO the side of the first
        (1, 0, 1): "repeater[facing=north,delay=1]",
        (1, 0, 2): "lever[face=floor,facing=north]",
    })
    c.set((1, 0, 2), True)
    c.run(6)
    assert c.state.get((1, 0, 1)), "the locking repeater must be on"
    c.set((0, 0, 0), True)
    c.run(8)
    assert not c.powered((2, 0, 0)), "a LOCKED repeater must not pass its new input"


def test_a_comparator_subtracts():
    c = Circuit.from_cells({
        (0, 0, 0): "comparator[facing=east,mode=subtract]",
        (1, 0, 0): "redstone_wire",
    })
    c.fill((-1, 0, 0), 12)                    # rear input, as a container reading
    c.cells[(-1, 0, 0)] = c.cells.get((-1, 0, 0)) or __import__(
        "mcbuild.circuit", fromlist=["Cell"]).Cell("barrel")
    c.fill((0, 0, 1), 4)                      # side input
    c.cells[(0, 0, 1)] = __import__("mcbuild.circuit", fromlist=["Cell"]).Cell("barrel")
    c.run(3)
    assert c.state.get((0, 0, 0)) == 8, "subtract mode is rear minus the greater side"


def test_a_comparator_compares():
    from mcbuild.circuit import Cell
    c = Circuit.from_cells({
        (0, 0, 0): "comparator[facing=east,mode=compare]",
        (1, 0, 0): "redstone_wire",
    })
    c.cells[(-1, 0, 0)] = Cell("barrel")
    c.cells[(0, 0, 1)] = Cell("barrel")
    c.fill((-1, 0, 0), 9)
    c.fill((0, 0, 1), 4)
    c.run(3)
    assert c.state.get((0, 0, 0)) == 9, "rear wins when it is the greater"
    c.fill((0, 0, 1), 12)
    c.run(3)
    assert c.state.get((0, 0, 0)) == 0, "a greater side input silences a comparator"


def test_container_fullness_is_an_input_not_a_guess():
    """This simulator has no entities. Pretending a hopper fills itself would certify a sorter
    that has never seen an item."""
    from mcbuild.circuit import Cell
    c = Circuit.from_cells({(0, 0, 0): "comparator[facing=east,mode=compare]"})
    c.cells[(-1, 0, 0)] = Cell("hopper")
    c.run(2)
    assert c.state.get((0, 0, 0), 0) == 0, "an unstated container reads as empty"
    c.fill((-1, 0, 0), 5)
    c.run(2)
    assert c.state.get((0, 0, 0)) == 5


def test_a_button_is_a_pulse_and_a_lever_is_not():
    """Half the circuits that exist only work on an EDGE, and a test that holds a button forever
    is silently testing a lever."""
    c = Circuit.from_cells({
        (0, 0, 0): "stone_button[face=floor,facing=north]",
        (1, 0, 0): "redstone_lamp",
    })
    c.press((0, 0, 0), ticks=3)
    c.step()
    assert c.powered((1, 0, 0))
    c.run(5)
    assert not c.powered((1, 0, 0)), "a button must release itself"


def test_a_dispenser_fires_on_the_rising_edge_only():
    """A held signal dispenses ONCE. A dispenser that fired every tick would empty a chest into
    the void, which is exactly the kind of thing a casino payout must not do."""
    c = Circuit.from_cells({
        (0, 0, 0): "lever[face=floor,facing=north]",
        (1, 0, 0): "dispenser[facing=east]",
    })
    c.set((0, 0, 0), True)
    c.run(10)
    assert c.fired[(1, 0, 0)] == 1, "held on: one shot, not ten"
    c.set((0, 0, 0), False)
    c.run(3)
    c.set((0, 0, 0), True)
    c.run(3)
    assert c.fired[(1, 0, 0)] == 2, "a second rising edge fires again"


def test_wire_connections_are_derived_not_read():
    """`work.INTENTIONAL` drops wire connections because the GAME computes them. A simulator that
    trusted a recorded `north=side` would be grading the design's own guess."""
    c = Circuit.from_cells({
        (-1, 0, 0): "redstone_block",
        (0, 0, 0): "redstone_wire[north=side,south=none,east=none,west=none]",
        (1, 0, 0): "redstone_wire[north=none,south=none,east=none,west=none]",
    })
    c.step()
    assert c.level((1, 0, 0)) == 14, "the wire connects because the geometry says so"


def test_quasi_connectivity_is_reported_rather_than_modelled():
    """Java pistons also fire when the block ABOVE is powered. Nothing here models that, so the
    cells where it would matter are NAMED instead of quietly ignored."""
    c = Circuit.from_cells({
        (0, 0, 0): "piston[facing=east]",
        (0, 1, 0): "redstone_wire",
    })
    risky = c.quasi_connectivity_risk()
    assert (0, 0, 0) in risky, "a piston with something overhead is a QC risk and must be flagged"
    c2 = Circuit.from_cells({(0, 0, 0): "piston[facing=east]"})
    assert not c2.quasi_connectivity_risk()


def test_quasi_connectivity_fires_a_piston_from_above():
    """minecraft.wiki, Redstone mechanics: a piston "can also be activated if a redstone signal is
    supplied to the block above them, even if that block is air" — and the same for dispensers and
    droppers. It is REAL behaviour, so it is modelled; the first version only warned about it,
    which was right while it was unverified and wrong once the source was to hand."""
    # THE FIXTURE IS THE WHOLE TEST. Dust sitting DIRECTLY on a piston powers it by ordinary
    # adjacency and proves nothing about QC - which is what the first version of this test did.
    # The real case is dust that never touches the piston at all: the cell above it is AIR, and
    # the dust is adjacent to that air.
    c = Circuit.from_cells({
        (0, 0, 0): "piston[facing=east]",
        (1, 1, 0): "redstone_wire",              # beside the air cell above the piston
        (2, 1, 0): "redstone_block",
    })
    c.run(2)
    assert c.name((0, 1, 0)) == "air", "the cell above the piston must be empty for this to be QC"
    out = c.step()
    assert out.get((0, 0, 0)), "QC must fire a piston through the AIR block above it"


def test_quasi_connectivity_can_be_switched_off_to_prove_a_circuit_does_not_rely_on_it():
    """A build that works only by accident of QC is worth knowing about."""
    cells = {
        (0, 0, 0): "dispenser[facing=east]",
        (1, 1, 0): "redstone_wire",              # again: never touching the dispenser itself
        (2, 1, 0): "redstone_block",
    }
    with_qc = Circuit.from_cells(cells)
    with_qc.run(3)
    without = Circuit.from_cells(cells)
    without.qc = False
    without.run(3)
    assert with_qc.fired[(0, 0, 0)] == 1
    assert without.fired[(0, 0, 0)] == 0, "with QC off, only a direct signal should fire it"


# --------------------------------------------------------------------------- what a component reads
#
# Two over-reads lived in `_read`/`_drives` and both made the simulator AGREE with a broken build,
# which is the worst failure a checker can have. Each is pinned by a fixture that is unambiguous in
# Minecraft, so a future "simplification" back to `_block_power` fails here.


def test_a_repeater_only_powers_the_cell_it_faces():
    """**A REPEATER IS NOT A CONDUCTOR.** `_read` fell through to `_block_power` at the repeater's
    own cell, which is the maximum of everything touching it - so a repeater standing beside an
    unrelated dust run reported that run's level to whatever was reading it. On `window(5, 9)` the
    gate's side read 12 instead of 15 and `15 - 12 = 3` passed a level the gate exists to block."""
    # A comparator reading a repeater that faces AWAY from it, with a loud dust run beside them.
    cells = {
        (0, 0, 0): "comparator[facing=east,mode=subtract]",
        (-1, 0, 0): "redstone_block",                       # rear: a clean 15
        (0, 0, 1): "repeater[facing=south,delay=1]",         # at the comparator's SIDE, facing away
        (0, 0, 2): "redstone_wire",
        (1, 0, 1): "redstone_wire",                          # ...and dust right beside it
        (2, 0, 1): "redstone_block",
    }
    for p in list(cells):
        cells.setdefault((p[0], p[1] - 1, p[2]), "smooth_stone")
    c = Circuit.from_cells(cells)
    c.run(20)
    assert c.state.get((0, 0, 0)) == 15, \
        "a repeater facing away delivers nothing to the side it is not aimed at"


def test_a_repeater_aimed_into_a_comparators_side_delivers_a_full_fifteen():
    """The other half of the same rule, and the one the exact-value gate is built on."""
    cells = {
        (0, 0, 0): "comparator[facing=east,mode=subtract]",
        (-1, 0, 0): "redstone_block",
        (0, 0, 1): "repeater[facing=north,delay=1]",         # aimed INTO the comparator
        (0, 0, 2): "redstone_block",
    }
    for p in list(cells):
        cells.setdefault((p[0], p[1] - 1, p[2]), "smooth_stone")
    c = Circuit.from_cells(cells)
    c.run(20)
    assert c.state.get((0, 0, 0)) == 0, "15 - 15 is the zero a subtract gate promises"


def test_an_empty_cell_is_not_an_input():
    """**AIR CARRIES NOTHING, and reading it as the maximum of its neighbours is how dust two cells
    away became a side input.** `_block_power` answers "how hard is this cell driven", which for an
    empty cell is right for quasi-connectivity and quite wrong for a component's own back or side:
    dust running past one cell out is DIAGONAL and powers nothing.

    Read the other way it cost two casino games. The button's descent passed within two cells of
    the pulse's subtract, the empty cell between them reported a permanent 14, the monostable never
    opened, and `double_or_none` and `lucky_number` reported a randomiser that never fired."""
    cells = {
        (0, 0, 0): "comparator[facing=east,mode=subtract]",
        (-1, 0, 0): "redstone_block",                       # rear 15
        # (0, 0, 1) is the SIDE and is deliberately left EMPTY
        (0, 0, 2): "redstone_wire",                          # dust one cell past it
        (1, 0, 2): "redstone_block",
    }
    for p in list(cells):
        cells.setdefault((p[0], p[1] - 1, p[2]), "smooth_stone")
    c = Circuit.from_cells(cells)
    c.run(20)
    assert c.state.get((0, 0, 0)) == 15, "an empty side cell provides no side input"


# The counterpart - that an empty cell is STILL read for quasi-connectivity - is already pinned by
# `test_quasi_connectivity_fires_a_piston_from_above` above, which is exactly this fixture.


def test_an_observer_watches_its_front_and_pulses_out_of_its_back():
    """The observer's arrow faces the watched block; its red-dot face is the output.

    The old model documented observers but never accepted an observation event, then sent a
    hypothetical pulse out of the watched face.  That certifies a circuit reflected through the
    observer -- an especially nasty render-clean failure.
    """
    c = Circuit.from_cells({
        (0, 0, 0): "observer[facing=east]",
        (-1, 0, 0): "redstone_wire",
        (-2, 0, 0): "redstone_lamp",
    })
    assert c.observe((1, 0, 0)) == 1
    assert c.step()[(-2, 0, 0)]
    assert not c.step()[(-2, 0, 0)], "an observer is a one-redstone-tick pulse"


def test_an_observer_does_not_trigger_for_an_update_behind_it():
    c = Circuit.from_cells({(0, 0, 0): "observer[facing=east]"})
    assert c.observe((-1, 0, 0)) == 0
    assert not c.step()


def test_an_external_analogue_source_powers_the_real_circuit():
    """A target is not a container: an arrow creates a signal that can drive dust directly."""
    c = Circuit.from_cells({
        (0, 0, 0): "target",
        (1, 0, 0): "redstone_wire",
        (2, 0, 0): "redstone_lamp",
    })
    c.set_signal((0, 0, 0), 7)
    assert c.step()[(2, 0, 0)]
    assert c.level((1, 0, 0)) == 7
    c.set_signal((0, 0, 0), 0)
    assert not c.step()[(2, 0, 0)]


def test_a_signal_can_only_be_supplied_to_a_real_external_source():
    c = Circuit.from_cells({(0, 0, 0): "redstone_lamp"})
    with pytest.raises(ValueError, match="external redstone source"):
        c.set_signal((0, 0, 0), 15)


def test_powered_rail_carries_power_for_eight_rails_past_its_source():
    """A run does not need a redstone block under every rail, but it does have a hard limit."""
    cells = {(i, 0, 0): "powered_rail[shape=east_west]" for i in range(10)}
    cells[(0, -1, 0)] = "redstone_block"
    c = Circuit.from_cells(cells)
    c.step()
    assert all(c.powered((i, 0, 0)) for i in range(9))
    assert not c.powered((9, 0, 0)), "the ninth rail past a source is an unpowered brake"


def test_detector_rail_is_an_explicit_minecart_event_source():
    """A cart event may energise its neighbouring powered rail without inventing a minecart."""
    c = Circuit.from_cells({
        (0, 0, 0): "detector_rail[shape=east_west]",
        (1, 0, 0): "powered_rail[shape=east_west]",
    })
    c.set_signal((0, 0, 0), 15)
    c.step()
    assert c.powered((1, 0, 0))
