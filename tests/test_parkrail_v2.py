"""Renewal gates exercise the emitted model, not descriptive metadata alone."""
import json
from pathlib import Path

import pytest
import yaml

from mcbuild import schem, worldschema, worldspec, worldnav, composition
from mcbuild.circuit import Circuit
from mcbuild.gen import parkrail

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def params():
    return yaml.safe_load((ROOT/'configs/park_rail_v2.yaml').read_text())['params']


@pytest.fixture(scope='module')
def canvas(params):
    return parkrail.build(params)


def test_strict_railway_overlay_matches_actual_corridor():
    raw = json.loads((ROOT/'park_railway_v2.world.json').read_text())
    assert not worldschema.validate(raw)
    plan = worldspec.compile(raw)
    assert worldnav.audit(plan)['ok']
    assert composition.assess(plan)['ok']
    assert len(plan['modules']) == 5
    covered = []
    for m in plan['modules']:
        assert m['generator'] == 'parkrail'
        assert m['at'][0] == 172 and m['footprint'][0] == 15
        covered.extend(range(m['at'][1], m['at'][1]+m['footprint'][1]))
    assert sorted(covered) == list(range(600))


def test_comparator_memory_holds_resets_and_repeats():
    from mcbuild.gen.parkrail_signals import memory_cell
    cells, ports = memory_cell()
    c = Circuit.from_cells(cells)
    c.run(10)
    assert not c.powered(ports['output'])
    for _ in range(2):
        c.set_signal(ports['set'],15)
        c.run(8)
        c.set_signal(ports['set'],0)
        c.run(30)
        assert c.powered(ports['output']), 'occupancy must survive the arriving cart leaving the detector'
        c.set_signal(ports['reset'],15)
        c.run(8)
        c.set_signal(ports['reset'],0)
        c.run(30)
        assert not c.powered(ports['output']), 'clearance must reset persistent occupancy'


def test_all_six_integrated_signals_hold_clear_and_isolate(canvas):
    model=canvas.to_model()
    # Exercise each emitted station independently to keep the solver bounded.
    for port in canvas.meta['renewal']['signals']:
        ac=port['brake'][2]
        crop=model.copy()
        crop.ids=model.ids[:,ac-48:ac+49,:].copy()
        sim=Circuit.of(crop,origin=(0,0,ac-48))
        sim.run(12)
        assert sim.powered(port['hold'])
        assert not sim.powered(port['brake'])
        for _ in range(2):
            sim.set_signal(port['set'],15)
            sim.run(25)
            sim.set_signal(port['set'],0)
            sim.run(20)
            assert sim.powered(port['memory'])
            assert not sim.powered(port['hold'])
            assert not sim.powered(port['brake'])
            other=next(q for q in canvas.meta['renewal']['signals']
                       if q['station']==port['station'] and q['track']!=port['track'])
            assert sim.powered(other['hold']), 'a busy platform must not stop the opposite line'
            sim.press(port['button'], ticks=15)
            sim.run(2)
            assert sim.powered(port['brake'])
            assert not sim.powered(port['hold']), 'departure button must not release a following cart'
            sim.run(20)
            assert not sim.powered(port['brake'])
            sim.set_signal(port['reset'],15)
            sim.run(25)
            sim.set_signal(port['reset'],0)
            sim.run(20)
            assert not sim.powered(port['memory'])
            assert sim.powered(port['hold'])


def test_power_only_brakes_at_declared_station_cells(canvas, params):
    model=canvas.to_model()
    sim=Circuit.of(model)
    sim.run(15)
    actual={pos for pos,cell in sim.cells.items() if cell.name=='powered_rail' and not sim.powered(pos)}
    expected={q['brake'] for q in canvas.meta['renewal']['signals']}
    assert actual==expected, f'unintended brakes: {sorted(actual-expected)}; live station brakes: {sorted(expected-actual)}'
    for port in canvas.meta['renewal']['signals']:
        shape=model.props_at(*port['brake'])['shape']
        assert shape==('ascending_north' if port['track']=='a' else 'ascending_south')


def test_current_rail_is_supported_clear_and_one_continuous_loop(canvas,params):
    model=canvas.to_model()
    planned=parkrail.plan(params)
    rails={tuple(c[:3]) for c in planned}
    from mcbuild import blocks
    for i,(x,y,z,corner) in enumerate(planned):
        assert model.names[model.ids[y,z,x]].split('[')[0].endswith('rail')
        assert blocks.is_full_cube(model.names[model.ids[y-1,z,x]].split(':')[-1].split('[')[0])
        assert not model.ids[y+1:y+3,z,x].any(), (x,y,z,'blocked rider headroom')
        a=planned[(i+1)%len(planned)]
        assert abs(x-a[0])+abs(z-a[2])==1 and abs(y-a[1])<=1
        if corner:
            assert y==a[1]==planned[i-1][1]
    actual={(int(x),int(y),int(z)) for y,z,x in zip(*model.solid().nonzero())
            if model.names[model.ids[y,z,x]].split('[')[0].endswith('rail')}
    assert actual==rails


def test_reaches_are_preserved_above_and_below_deck(canvas,params):
    old=parkrail.build({**params,'renewal':False,'bay_half':3}).to_model()
    new=canvas.to_model()
    # Compare state strings: palette indices are deliberately not assumed stable.
    for lo,hi in ((170,214),(385,429)):
        for y in range(new.ids.shape[0]):
            for z in range(lo,hi+1):
                for x in range(15):
                    a=new.names[new.ids[y,z,x]]
                    b=old.names[old.ids[y,z,x]] if y<old.ids.shape[0] else 'minecraft:air'
                    assert a==b,(x,y,z)
