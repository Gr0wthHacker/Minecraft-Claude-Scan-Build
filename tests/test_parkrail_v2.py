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
