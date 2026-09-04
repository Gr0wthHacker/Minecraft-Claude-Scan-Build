"""The Frontier's mine works, against its own contract - and the battery by SIMULATION.

A redstone build is the one thing in this project whose wrongness is invisible in every render,
every audit and every bill of materials. This machine proved it three times while it was being
written: it latched ON for as long as the button was held (twice, from two different causes) and
before that it did nothing at all, and on all three occasions the design audited clean, rendered
identically and reported a correct BOM. Nothing here is asserted by eye.
"""
from __future__ import annotations

import os

import pytest
import yaml

from mcbuild import blocks, palette
from mcbuild.circuit import Circuit
from mcbuild.gen import mineworks

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(ROOT, "configs", "pf_mine_works.yaml")


@pytest.fixture(scope="module")
def cfg():
    with open(CONFIG, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


@pytest.fixture(scope="module")
def built(cfg):
    canvas = mineworks.build(cfg["params"])
    return canvas, canvas.to_model()


# --------------------------------------------------------------------------- the palette


def test_every_block_is_legal_spendable_and_on_the_server():
    """Rule 12 and rule 16 together: a block can be real, in 1.19, and still be CURRENCY here."""
    for key, name in mineworks.WORKS.items():
        assert blocks.exists(name), f"{key} -> {name} is not a block"
        assert blocks.spendable(name), f"{key} -> {name} is currency on this server"
        assert palette.tier(name) in ("cheap", "ok") or name == "redstone_lamp", \
            f"{key} -> {name} is {palette.tier(name)}"


def test_the_only_expensive_block_is_declared(cfg, built):
    """`redstone_lamp` is expensive and a froglight cannot be switched. The trade is in the config
    rather than smuggled into the BOM."""
    _canvas, model = built
    lamps = sum(1 for n in model.names if n.split("[")[0].endswith("redstone_lamp"))
    assert lamps <= int(cfg["expensive_allowance"])


# --------------------------------------------------------------------------- the ore line


#: **THE LINE'S ASSERTIONS SKIP WHEN THE LINE IS OFF, RATHER THAN PASSING VACUOUSLY.** It was
#: deleted on sight - a third elevated railway in a land that already has the coaster and the park
#: line, and it pierced the mill's own wall five courses up. The machinery and its contract stay;
#: what must not happen is a suite that reports green because there is nothing left to check.
def _needs_line(cfg):
    if not cfg["params"].get("line"):
        pytest.skip("the ore line is off in this config (see mineworks.WORKSDEF)")


def test_a_powered_rail_has_no_corner_shape_in_the_registry():
    """The registry fact the whole line's geometry rests on, asked of the game rather than
    remembered. Every direction change on this line is plain `rail` BECAUSE of this."""
    powered = set(blocks.props("powered_rail").get("shape", []))
    plain = set(blocks.props("rail").get("shape", []))
    assert "south_east" not in powered and "north_west" not in powered,         "a powered rail has no corner shape - every direction change here is plain rail"
    assert {"south_east", "north_west", "south_west", "north_east"} <= plain


def test_every_corner_is_plain_rail(cfg, built):
    _needs_line(cfg)
    canvas, model = built
    line = canvas.meta["parts"]["line"]
    ly = 5
    for v, u in line["corners"]:
        name = canvas.get_name(v, ly, u).split(":")[-1]
        assert name == "rail", f"corner ({v},{u}) is {name}, and a powered rail cannot curve"


def test_no_powered_rail_ever_runs_further_than_the_spacing_from_a_source(built, cfg):
    """AN UNPOWERED POWERED RAIL IS A BRAKE, and a dead rail is a cart stopped in mid-air."""
    _needs_line(cfg)
    canvas, _model = built
    ly, every = 5, int(cfg["params"]["power_every"])
    powered, sources = [], set()
    for v in range(canvas.sx):
        for u in range(canvas.sz):
            name = canvas.get_name(v, ly, u).split(":")[-1]
            if name == "powered_rail":
                powered.append((v, u))
            if canvas.get_name(v, ly - 1, u).split(":")[-1] == "redstone_block":
                sources.add((v, u))
    assert powered and sources
    for v, u in powered:
        near = min(abs(v - a) + abs(u - b) for a, b in sources)
        assert near <= every, f"powered rail at ({v},{u}) is {near} from any source"


def test_no_trestle_leg_stands_in_the_service_lane_or_the_guest_walk(built, cfg):
    """Both are somebody else's ground and both are CROSSED, never stood on.

    THE DECK ITSELF IS ALLOWED OVER THEM - that is what a bridge IS - so what this asserts is
    that a guest walking either of them has clear headroom under it: nothing in courses 0-3, with
    the deck at 4 and the rail at 5.
    """
    _needs_line(cfg)
    canvas, _model = built
    lane = range(cfg["params"]["lane"][0], cfg["params"]["lane"][1] + 1)
    walk = range(cfg["params"]["walk"][0], cfg["params"]["walk"][1] + 1)
    for y in range(0, 4):
        for v in lane:
            for u in range(canvas.sz):
                assert not canvas.solid(v, y, u), f"a cell stands in the lane at ({v},{y},{u})"
        for u in walk:
            for v in range(canvas.sx):
                assert not canvas.solid(v, y, u), f"a cell stands in the walk at ({v},{y},{u})"


def test_the_line_is_level_for_its_whole_length(cfg, built):
    """A corner has no ascending shape either, so the surest way to keep a four-corner line legal
    is to give it no gradient at all."""
    _needs_line(cfg)
    canvas, _model = built
    for v in range(canvas.sx):
        for u in range(canvas.sz):
            name = canvas.get_name(v, 5, u).split(":")[-1]
            if name in ("rail", "powered_rail", "detector_rail"):
                continue
            for y in (4, 6):
                assert canvas.get_name(v, y, u).split(":")[-1] not in ("powered_rail", "rail"), \
                    f"a rail off the line's own course at ({v},{y},{u})"


# --------------------------------------------------------------------------- the stamp battery


def _fire(model, mach, ticks=30, hold=True):
    circuit = Circuit.of(model)
    circuit.run(6)
    rest = [circuit.powered(tuple(h)) for h in mach["heads"]]
    circuit.set(tuple(mach["button"]), hold)
    out = []
    for _ in range(ticks):
        circuit.step()
        out.append((sum(circuit.powered(tuple(h)) for h in mach["heads"]),
                    circuit.powered(tuple(mach["lamp"])),
                    circuit.powered(tuple(mach["bell"]))))
    return rest, out


def test_the_battery_is_at_rest_until_it_is_pressed(built):
    canvas, model = built
    rest, _ = _fire(model, canvas.meta["parts"]["mill"]["machine"])
    assert not any(rest), "a stamp battery that runs by itself is a mill nobody switched on"


def test_every_head_drops(built):
    canvas, model = built
    mach = canvas.meta["parts"]["mill"]["machine"]
    _rest, hist = _fire(model, mach)
    assert max(h for h, _l, _b in hist) == mach["n"], \
        "a head that never fires is a stamp the drive line does not reach"


def test_the_bell_rings_and_the_running_lamp_lights(built):
    canvas, model = built
    _rest, hist = _fire(model, canvas.meta["parts"]["mill"]["machine"])
    assert any(lamp for _h, lamp, _b in hist), "nothing tells a guest the mill ran"
    assert any(bell for _h, _l, bell in hist)


def test_A_HELD_BUTTON_GIVES_ONE_STROKE_AND_THE_BATTERY_RESETS(built):
    """**THE ONE ASSERTION THIS FILE EXISTS FOR.** A machine that runs for as long as somebody
    leans on it is the mill's version of a house paying while a player holds a slot button, and
    this build shipped it TWICE from two different causes - once because the pulse's own delay leg
    ran beside the step-across into the climb and fed fifteen straight round the gate, and once
    because the drive line's first repeater stood on the climb's own dust. Both audited clean.

    The bound is deliberately tight: "off within twenty ticks while still HELD". A bound looser
    than the bug is what let `circuits.pulse` ship as a repeater, and this repo has written that
    lesson down once already.
    """
    canvas, model = built
    _rest, hist = _fire(model, canvas.meta["parts"]["mill"]["machine"], ticks=30, hold=True)
    assert max(h for h, _l, _b in hist) > 0, "it never fired at all"
    assert all(h == 0 for h, _l, _b in hist[20:]), \
        "the battery is still running twenty ticks into a held press"


def test_a_second_press_fires_it_again(built):
    """A monostable that cannot be re-triggered is a fuse."""
    canvas, model = built
    mach = canvas.meta["parts"]["mill"]["machine"]
    circuit = Circuit.of(model)
    btn = tuple(mach["button"])
    fired = []
    for _round in range(2):
        circuit.set(btn, True)
        peak = 0
        for _ in range(14):
            circuit.step()
            peak = max(peak, sum(circuit.powered(tuple(h)) for h in mach["heads"]))
        circuit.set(btn, False)
        for _ in range(8):
            circuit.step()
        fired.append(peak)
    assert all(f == mach["n"] for f in fired), f"presses fired {fired} heads"


def test_no_quasi_connectivity_anywhere_in_the_machine(built):
    """A piston fires from the block ABOVE it as well as from a neighbour, and most people do not
    expect that. Every head here is driven by dust on its own course, so the machine survives
    being modelled - and a build that quietly came to depend on QC would be one nobody could
    reason about."""
    canvas, _model = built
    mach = canvas.meta["parts"]["mill"]["machine"]
    for v, y, u in mach["heads"]:
        above = canvas.get_name(v, y + 1, u).split(":")[-1]
        assert above not in ("redstone_wire", "repeater", "comparator", "redstone_block"),             f"the head at ({v},{y},{u}) is driven from the block above it"
        beside = [canvas.get_name(v + dv, y, u + du).split(":")[-1]
                  for dv, du in ((1, 0), (-1, 0), (0, 1), (0, -1))]
        assert "redstone_wire" in beside,             f"the head at ({v},{y},{u}) has no dust on its own course to drive it"


# --------------------------------------------------------------------------- the building


def test_the_mill_steps_down_the_way_the_ore_travels(built):
    """Bin, battery, tables - three masses of three heights, because one box of one height is a
    shed and this land already has six of those."""
    canvas, _model = built
    steps = canvas.meta["parts"]["mill"]["steps"]
    tops = [t for _n, _a, _b, t in steps]
    assert tops == sorted(tops, reverse=True), f"the mill does not step down: {tops}"
    assert tops[0] - tops[-1] >= 6, "the steps are too close to read as separate masses"


def test_every_sign_is_on_a_wall_that_is_there(built):
    """`_Lot.sign` REFUSES a cell with nothing behind it, so a missing sign is the failure rather
    than a floating one - which is why the counts are asserted rather than the placements."""
    canvas, _model = built
    parts = canvas.meta["parts"]
    assert parts["mill"]["signs"] >= 1, "the mill does not say what it is"
    assert parts["dock"]["signs"] >= 1, "the dock does not say what it is"
    for sign in canvas.meta["signs"]:
        for line in sign["lines"]:
            assert len(line) <= 15, f"{line!r} clips mid-word on a sign"


def test_nothing_is_built_outside_the_lot(built):
    canvas, _model = built
    assert canvas.meta["refused"] == 0, "the works tried to build outside its own lot"
