"""The Park Line's OPERATION: what makes a cart move, stop, and start again by itself.

**`tests/test_parkrail.py` PINS A MODEL THAT IS NOT THE ONE THAT SHIPS.** It overrides the config
to `renewal: False, bay_half: 3` and asserts the legacy, level-track contract; run against the
shipped params, twelve of its thirty-six assertions fail. Some of those are retired canopy work
and are meant to. The rest are the rail-correctness ones its own docstring calls *"the only checks
that can catch"* a line that cannot be ridden - because `shape` and `powered` are DERIVED by the
game, `work.INTENTIONAL` does not compare them, and `render3d` draws a wrong rail exactly like a
right one. Those are re-asserted here against the model that is actually placed.

And two things the line could not do at all:

**IT HAD NO CARTS.** A minecart is an ENTITY, so no litematic anywhere in this project can contain
one - and nothing said so. Measured across the whole shipped park: zero minecarts, zero
dispensers, zero activator rails. Six brake bays, six departure buttons, twelve detectors and a
full signalling system, with nothing to run on them. The fleet is a stocking contract now, the way
the menagerie ships its enclosures empty and names what to lead into each one.

**AND AN ABANDONED CART STOPPED A RUNNING LINE FOR GOOD.** The occupancy memory is set by the
arrival detector and cleared by the EXIT detector, which a cart nobody dispatches never reaches;
the approach hold forty cells back is dead for as long as that memory stands. Simulated on the
shipped model: still dead at 20, 100, 400 and 2000 ticks. The staff panel clears the MEMORY and
not the CART, so the recovery it offers opens the hold in front of a platform that is still
blocked. `dwell` is the cure and `test_a_cart_nobody_dispatches_still_leaves` is the proof.
"""
from pathlib import Path

import numpy as np
import pytest
import yaml

from mcbuild import blocks
from mcbuild.circuit import Circuit
from mcbuild.gen import parkrail

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def params():
    """The SHIPPED params, defaults merged - a test that reads only the config file is a test
    that cannot see any value the generator supplies for itself."""
    cfg = yaml.safe_load((ROOT / 'configs/park_rail.yaml').read_text(encoding='utf-8'))['params']
    return {**parkrail.PARKRAIL, **cfg}


@pytest.fixture(scope='module')
def canvas(params):
    return parkrail.build(dict(params))


@pytest.fixture(scope='module')
def model(canvas):
    return canvas.to_model()


@pytest.fixture(scope='module')
def named(model):
    """{(x, y, z): bare block name} for the shipped model."""
    names = [n.split(':')[-1].split('[')[0] for n in model.names]
    out = {}
    for y, z, x in np.argwhere(model.ids > 0):
        out[(int(x), int(y), int(z))] = names[int(model.ids[y, z, x])]
    return out


@pytest.fixture(scope='module')
def ports(canvas):
    return canvas.meta['renewal']['signals']


# ------------------------------------------------------------------ the shipped model's own rails

def test_every_shipped_rail_is_the_right_kind_in_a_legal_state(model, named, params):
    """A powered rail on the straights and the humps, a PLAIN rail at a corner because a powered
    one has no curve shape at all, and a detector rail only where a bay wants one."""
    cells = parkrail.plan(params)
    rails = {p: n for p, n in named.items() if n.endswith('rail')}
    assert len(rails) == len(cells)
    corners = {(x, z) for (x, _y, z, corner) in cells if corner}
    for (x, y, z), name in rails.items():
        props = model.props_at(x, y, z)
        assert blocks.validate(name, props) == [], f'{name}{props} at {(x, y, z)}'
        if (x, z) in corners:
            assert name == 'rail', 'a powered rail cannot hold a curve shape'
            assert props['shape'] in ('south_east', 'south_west', 'north_west', 'north_east')
        else:
            assert name in ('powered_rail', 'detector_rail')
            assert props['shape'] in ('north_south', 'east_west', 'ascending_north',
                                      'ascending_south', 'ascending_east', 'ascending_west')
            if name == 'detector_rail':
                assert props['shape'] in ('north_south', 'east_west'), \
                    'a detector rail is a BREAK in the powered chain, so one on a slope would '\
                    'put a break in the middle of a hump'


def test_the_shipped_iron_budget_is_still_four_corners(named):
    """Iron is the scarce metal here and gold is farmable, so a corner and a detector are the only
    expensive cells in the track:

        rail          6 iron -> 16 rails   0.375 iron each
        powered_rail  6 gold ->  6 rails   1.0   gold each

    The dwell bought a THIRD detector per bay - six ingots, and the entire metal cost of the
    automation. This is the test a future corridor bend would fail first.
    """
    plain = sum(1 for n in named.values() if n == 'rail')
    detectors = sum(1 for n in named.values() if n == 'detector_rail')
    assert plain == 4, 'two turnbacks, two corners each, and no more'
    assert detectors == 18, 'arrival, clearance and dwell trigger, one of each per bay'
    ingots = plain * 0.375 + detectors * 1.0
    assert ingots <= 20, f'{ingots} ingots of iron in the track'


def test_the_shipped_line_is_one_closed_circuit(model, params):
    """Every rail has exactly two rail neighbours and the whole ring is ONE cycle - which is a
    thing a line with a missing cell cannot be, and the reason a closed circuit needs no stop
    block. The renewal raises the cell before each brake and each hold, so neighbours are matched
    across a course as well as along one."""
    cells = parkrail.plan(params)
    rails = {(x, y, z) for (x, y, z, _c) in cells}
    assert len(rails) == len(cells)
    for i, (x, y, z, _c) in enumerate(cells):
        nxt = cells[(i + 1) % len(cells)]
        assert abs(x - nxt[0]) + abs(z - nxt[2]) == 1, 'the ring must not jump'
        assert abs(y - nxt[1]) <= 1, 'and may only step one course'


# ---------------------------------------------------------------------------------- the dwell

def _window(ports):
    return max(q['dwell_ticks'] for q in ports)


def _crop(model, ac, back=62, on=50):
    crop = model.copy()
    crop.ids = model.ids[:, ac - back:ac + on, :].copy()
    return Circuit.of(crop, origin=(0, 0, ac - back))


def test_a_cart_nobody_dispatches_still_leaves(model, ports):
    """THE DEADLOCK, and what the whole mechanism exists for. Nobody touches a button here: the
    cart arrives, is abandoned, and the line has to get itself going again."""
    window = _window(ports)
    for port in ports:
        ac = port['brake'][2]
        sim = _crop(model, ac)
        sim.run(15)
        assert not sim.powered(port['brake']), 'a bay is DEAD until something releases it'
        assert sim.powered(port['hold']), 'and the approach is open'

        sim.set_signal(port['trigger'], 15)       # the cart runs over the dwell trigger...
        sim.run(10)
        sim.set_signal(port['trigger'], 0)
        sim.set_signal(port['set'], 15)           # ...and then the arrival detector
        sim.run(6)
        sim.set_signal(port['set'], 0)
        sim.run(30)                               # the memory-to-hold cable is forty cells long
        assert sim.powered(port['memory'])
        assert not sim.powered(port['hold']), 'a platform in use closes its own approach'

        fired = None
        for t in range(20, window + 80, 4):
            sim.run(4)
            if sim.powered(port['brake']):
                fired = t
                break
        assert fired is not None, f"{port['station']} {port['track']}: the dwell never released"
        assert fired > window * 0.6, 'a dwell short enough to miss is not a dwell'

        sim.run(40)
        assert not sim.powered(port['brake']), 'the release is a PULSE; the bay goes dead again'
        sim.set_signal(port['reset'], 15)         # the departed cart clears the exit detector
        sim.run(6)
        sim.set_signal(port['reset'], 0)
        sim.run(25)
        assert not sim.powered(port['memory'])
        assert sim.powered(port['hold']), 'the line reopens with nobody having touched anything'


def test_the_dwell_does_not_release_a_bay_nothing_has_arrived_at(model, ports):
    """The counter-test, and the one that stops the cure becoming the fault: a bay that releases
    on its own with no cart in it is a bay that cannot hold one."""
    port = ports[0]
    sim = _crop(model, port['brake'][2])
    sim.run(_window(ports) + 80)
    assert not sim.powered(port['brake'])
    assert not sim.powered(port['release']), 'the kerb block is ordinary stone until it is fed'
    assert sim.powered(port['hold'])


def test_the_button_still_dispatches_early_and_does_not_open_the_approach(model, ports):
    """The dwell is a floor on how long a cart waits, never a ceiling. And a departure button must
    not release the cart QUEUED BEHIND it - that isolation is what the hold is for."""
    port = ports[0]
    sim = _crop(model, port['brake'][2])
    sim.run(15)
    sim.set_signal(port['set'], 15)
    sim.run(10)
    sim.set_signal(port['set'], 0)
    sim.run(30)
    assert not sim.powered(port['hold'])
    sim.press(port['button'], ticks=15)
    sim.run(2)
    assert sim.powered(port['brake']), 'the button is the early dispatch'
    assert not sim.powered(port['hold']), 'and it may not let a following cart in'


def test_the_dwell_trigger_lies_between_the_hold_and_the_arrival_detector(ports, params):
    """WHERE the trigger sits is the whole of it. Beyond the hold, a cart stopped there would have
    passed it already and would never start its own dwell; inside the arrival readout, the chain
    it feeds would have to start behind its own output."""
    for port in ports:
        ac = port['brake'][2]
        assert 10 < int(params['dwell_at']) < 40
        assert abs(port['trigger'][2] - ac) == int(params['dwell_at'])
        assert abs(port['hold'][2] - ac) == 40
        assert abs(port['set'][2] - ac) == 10
        assert (port['trigger'][2] - ac) * (port['hold'][2] - ac) > 0, \
            'the trigger is on the APPROACH, the same side as the hold'


def test_the_dwell_chain_is_unbroken_and_never_stands_on_the_running_line(named, ports):
    """A repeater outputs from its front and nowhere else, which is the only reason a chain of
    them may lie beside a live rail at all; redstone dust beside a powered rail can activate it.
    So the chain is repeaters, its four dust cells are the bridge over the arrival readout a
    course up, and no cell of it is a rail."""
    rails = {p for p, n in named.items() if n.endswith('rail')}
    for port in ports:
        x = port['release'][0]
        ac, tr = port['brake'][2], port['trigger'][2]
        for z in range(min(ac, tr), max(ac, tr) + 1):
            n = named.get((x, 13, z))
            assert n is not None, f'a gap in the dwell chain at {(x, 13, z)}'
            assert n in ('repeater', 'redstone_wire', 'stone_bricks'), f'{n} at {(x, 13, z)}'
            assert (x, 13, z) not in rails


def test_nothing_but_the_release_can_reach_the_brake_through_the_TRACK(named, ports):
    """THE FAULT THIS FIXES RELEASED THE BRAKE THIRTY-FIVE TICKS EARLY, by a route nothing in the
    chain could see. The bridge over the arrival readout used to come down onto a dust cell at
    -8; dust beside a powered rail activates that rail, an activated powered rail carries its own
    state EIGHT rails each way, and -8 plus eight is the platform. The cart left before it had
    stopped, and in simulation it read as a perfectly good second pulse.

    So: nothing in the chain that can power a rail at all - a dust cell, or a block a repeater
    strongly powers - may lie within eight rails of the brake. A repeater may, because a repeater
    outputs from its front and nowhere else. The release block is the one exception and is the
    whole point of it.
    """
    for port in ports:
        x, ac = port['release'][0], port['brake'][2]
        for z in range(min(ac, port['trigger'][2]), max(ac, port['trigger'][2]) + 1):
            for y in (13, 14, 15):
                n = named.get((x, y, z))
                if n in (None, 'repeater'):
                    continue
                if (x, y, z) == tuple(port['release']):
                    continue
                assert abs(z - ac) > 8,                     f'{n} at {(x, y, z)} is {abs(z - ac)} rails from the brake: it can light it'


def test_the_release_block_touches_its_own_brake_and_no_other_bay(named, ports):
    """A powered rail carries its own activated state eight rails each way, so what the release
    block must be is HORIZONTALLY ADJACENT to the brake - and what it must not be is within reach
    of the opposite track."""
    for port in ports:
        rx, ry, rz = port['release']
        bx, by, bz = port['brake']
        assert (abs(rx - bx), abs(ry - by), abs(rz - bz)) == (1, 0, 0)
        other = next(q for q in ports
                     if q['station'] == port['station'] and q['track'] != port['track'])
        assert abs(other['brake'][0] - rx) > 8


# ------------------------------------------------------------------------------- the fleet

def test_the_line_says_what_to_stock_it_with(canvas, named, ports):
    """A MINECART IS AN ENTITY AND A LITEMATIC IS BLOCKS, so no railway this project builds can
    ever ship with a cart in it. Until this contract existed nothing said so, and the park held
    six bays, six buttons, eighteen detectors and not one minecart, dispenser or activator rail
    anywhere in it."""
    fleet = canvas.meta['renewal']['fleet']
    assert fleet['item'] == 'minecart'
    assert fleet['count'] == len(ports)
    assert 'ONE cart' in fleet['first_proof'], 'the first live proof is a single cart'
    for port in ports:
        assert named[port['brake']].endswith('rail'), 'a cart is stocked onto its own bay'


def test_a_cart_set_down_on_a_bay_waits_for_a_rider(model, ports):
    """Stocking is one cart per brake bay, and that is not arbitrary: a cart placed there has not
    run over its own dwell trigger, so nothing has started a timer and it waits for somebody
    rather than leaving on a clock with nobody aboard. From its first dispatch it circulates under
    the dwell like any other."""
    port = ports[0]
    sim = _crop(model, port['brake'][2])
    sim.run(_window(ports) + 80)
    assert not sim.powered(port['brake']), 'nothing releases a bay whose trigger never fired'


def test_the_design_declares_a_world_origin_so_it_ships_a_SIDECAR_AND_A_WORK_LIST(canvas, params):
    """A LITEMATIC ON ITS OWN IS NOT A DESIGN. `pipeline._save_outputs` writes the sidecar and the
    work list only when the generator declares a `world_origin`, and this one never did - the
    review tool had supplied the origin by hand once, so every regeneration afterwards replaced
    the .litematic and left a `Park Rail.scan.json` and a `Park Rail.work.json` describing a model
    that no longer existed. In game that is `/cscan check` and `/cscan follow` grading the new
    railway against the old one, silently, and it is why the shipped work list still named twelve
    detector rails when the model had eighteen."""
    assert canvas.world_origin == tuple(int(v) for v in params['origin'])
    v0, u0, _v1, _u1 = params['bounds']
    assert canvas.world_origin[0] == v0 + 97500, 'V172 is x=97672 on the park lattice'
    assert canvas.world_origin[2] == u0 + 80300, 'U0 is z=80300'


def test_a_crop_moves_the_origin_by_exactly_what_it_cut(params):
    """The renewal ships five crops of one continuous model, so a crop that kept the whole
    circuit's origin would place every one of them at the start of the line."""
    lo, hi = 100, 199
    c = parkrail.build({**params, 'crop_u': [lo, hi]})
    assert c.world_origin[2] == int(params['origin'][2]) + lo - params['bounds'][1]
    assert c.world_origin[0] == int(params['origin'][0])


# -------------------------------------------------------------------------------- the signs

def test_no_sign_on_the_line_clips_mid_word(model):
    """The shipped railway carried four signs cut mid-word - BOARD THEN PRES, BOARD WHEN CLEA,
    CHECK LINE EMPT and > PRISMWORKS 50 - because the writer truncated silently and the damage
    shows only in a screenshot of the placed build."""
    import json
    for tile in model.tile_entities:
        for i in range(1, 5):
            raw = tile.value[f'Text{i}'].value
            text = json.loads(raw).get('text', '') if raw.startswith('{') else raw
            assert len(text) <= parkrail.SIGN_WIDTH, repr(text)


def test_a_sign_line_too_long_is_refused_rather_than_shortened(params):
    """...and the cure is that the generator refuses the line instead of shortening it behind the
    author's back."""
    from mcbuild.gen.canvas import Canvas
    deck = parkrail._Deck(Canvas(15, 20, 40), {**params, 'bounds': [172, 0, 186, 39]})
    with pytest.raises(ValueError, match='clip'):
        deck.sign(174, 5, 5, 'east', 'oak', ['SHORT', 'A LINE THAT IS FAR TOO LONG'])


def test_the_boards_describe_the_service_that_actually_runs(model):
    """A board that still said BOARD THEN PRESS would be telling a rider the ride does not start
    without them, which is exactly what an abandoned cart used to prove false."""
    import json
    text = []
    for tile in model.tile_entities:
        for i in range(1, 5):
            raw = tile.value[f'Text{i}'].value
            text.append(json.loads(raw).get('text', '') if raw.startswith('{') else raw)
    joined = ' '.join(text)
    assert 'BOARD - IT GOES' in joined and 'PRESS TO GO NOW' in joined
    assert 'DEPARTS ITSELF' in joined
    assert 'STOCK THE CARTS' in joined, 'the stocking contract is on the staff panel too'
    assert 'BOARD THEN PRES' not in joined
