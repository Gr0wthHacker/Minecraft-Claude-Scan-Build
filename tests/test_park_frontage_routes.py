"""A clear arch must lead along a road, not merely avoid overlapping it."""
from pathlib import Path
import yaml
import pytest

from mcbuild import scan
from mcbuild.gen import park_frontage
from tools import park_place
from tools.park_frontage_audit import block

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def context():
    items = [i for i in park_place.modules() if not i[0].startswith('PF Front ')]
    model, origin, _ = park_place.complete(items)
    return scan.Scan(model, {'origin': dict(zip(('x', 'y', 'z'),
                     (97500 + origin[0], 202 + origin[1], 80300 + origin[2])))}, '', '')


@pytest.mark.parametrize('land,names', [
    ('frontier', ['Broken Plateau', 'Plateau Bone Bed']),
    ('prismworks', ['Prismworks Gate', 'Prism Well']),
])
def test_land_arches_address_surviving_avenues(context, land, names):
    ways = yaml.safe_load((ROOT / 'configs/park_ways.yaml').read_text(encoding='utf-8'))
    streets = ways['params']['parts'][0]['params']['lands']
    avenues = {a['at'] for l in streets if l['name'] == land for a in l['avenues']}
    cfg = yaml.safe_load((ROOT / f'configs/pf_front_{land}.yaml').read_text(encoding='utf-8'))
    for piece in cfg['params']['pieces']:
        if piece['name'] not in names:
            continue
        v, u = piece['at']
        assert u in avenues
        assert piece.get('facing', 'west') == 'west'
        for x in range(v, v + 16):
            for z in range(u - 1, u + 2):
                assert block(context, x, 202, z) not in ('air', 'moss_block')
                for y in (203, 204, 205):
                    assert block(context, x, y, z) == 'air', (piece['name'], x, y, z)
        c = park_frontage.build({**cfg['params'], 'pieces': [piece]})
        ox, oy, oz = c.world_origin
        for y, z, x in zip(*(c.ids != 0).nonzero()):
            assert block(context, int(ox+x-97500), int(oy+y), int(oz+z-80300)) in ('air', 'moss_carpet')


def test_no_remote_descent_queue_or_duplicate_carousel_entrance():
    prism = yaml.safe_load((ROOT / 'configs/pf_front_prismworks.yaml').read_text(encoding='utf-8'))
    assert not any(p['kind'] == 'queue' or p['name'] in
                   ('Prism Descent', 'Prism Well entrance', 'Prism Well exit')
                   for p in prism['params']['pieces'])
    midway = yaml.safe_load((ROOT / 'configs/pf_front_midway.yaml').read_text(encoding='utf-8'))
    pieces = {p['name']: p for p in midway['params']['pieces']}
    assert 'Carousel entrance' not in pieces
    assert pieces['Sky Lift']['style'] == 'board'
