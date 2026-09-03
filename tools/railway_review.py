"""Reproducible railway plan, massing, review renders and candidate assembly.

Usage: python tools/railway_review.py prepare|greybox|detail|packet|assemble
Outputs are isolated under out/railway_v2; no live schematic is shipped.
"""
from pathlib import Path
import argparse
import copy
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import yaml
import numpy as np
from PIL import Image
from mcbuild import schem, render3d, worldflow
from mcbuild.gen import parkrail

OUT = ROOT / 'out' / 'railway_v2'


def params():
    return yaml.safe_load((ROOT/'configs/park_rail_v2.yaml').read_text())['params']


def prepare():
    OUT.mkdir(parents=True, exist_ok=True)
    cfg = yaml.safe_load((ROOT/'configs/park_rail.yaml').read_text())
    cfg.update(name='Park Rail Renewal', server_profile='skyblock-1.19', world_contract=True,
               cache_dir='out/railway_v2/cache')
    cfg['params'].update(renewal=True, bay_half=0)
    cfg['anchors'] = [{'name': 'public_entry', 'kind': 'entrance', 'pos': [0, 2, 260]},
                      {'name': 'return', 'kind': 'exit', 'pos': [7, 2, 306]},
                      {'name': 'maintenance', 'kind': 'service', 'pos': [10, 1, 256]}]
    cfg['design']['narrative'] = 'Three distinct free stations on a two-track rim railway with independent exit stairs, sloped dispatch and approach holding.'
    (ROOT/'configs/park_rail_v2.yaml').write_text(yaml.safe_dump(cfg, sort_keys=False), encoding='utf-8')
    raw = json.loads((ROOT/'park_final.world.json').read_text())
    raw['name'] += ' — Railway Renewal'
    # This is a railway-only overlay. Other plots remain reserved, but their
    # legacy generator contracts are outside this change and are not rebuilt.
    raw['modules'] = [m for m in raw['modules'] if m['generator']=='transit']
    for plot in raw['plots']:
        if plot['name'].startswith('line_'):
            plot['bounds'][0], plot['bounds'][2] = 172, 186
    for m in raw['modules']:
        if m['generator'] != 'transit':
            continue
        plot = next(p for p in raw['plots'] if p['name']==m['plot'])
        lo, hi = plot['bounds'][1], plot['bounds'][3]
        m.update(generator='parkrail', params={**copy.deepcopy(cfg['params']), 'crop_u': [lo, hi]},
                 at=[172, lo], footprint=[15, hi-lo+1],
                 budget={'blocks': 16000 if hi-lo > 100 else 4500},
                 purpose='Free park transport and elevated promenade',
                 scenarios=['public_visit','queue_board_exit','occupied_platform','restart','staff_recovery'],
                 access_points=[[172, next((s['at_u']+s['stair']*19 for s in cfg['params']['stations']
                                          if lo <= s['at_u'] <= hi), (lo+hi)//2)]],
                 anchors=[{'name':'public_entry','kind':'entrance','pos':[0,2, min(20,hi-lo)]},
                          {'name':'return','kind':'exit','pos':[7,13, min(21,hi-lo)]},
                          {'name':'maintenance','kind':'service','pos':[10,1,min(22,hi-lo)]}])
        m['return_route'] = 'railway_arcade'
        m['service_access'] = 'railway_service'
        m['live_gates'] = ['minecart stopping/restart', 'close-following carts', 'chunk reload', 'operator recovery']
    raw['routes'].extend([
        {'name':'railway_arcade','kind':'path','width':3,'points':[[172,2],[172,597]]},
        {'name':'railway_service','kind':'service','width':2,'points':[[184,2],[184,597]]},
    ])
    # Existing avenue locations are retained, including the public ground layer.
    for u in (96,260,524):
        raw['routes'].append({'name':f'railway_approach_{u}','kind':'path','width':3,
                              'points':[[12,u],[172,u]]})
    path = ROOT/'park_railway_v2.world.json'
    path.write_text(json.dumps(raw, indent=2)+'\n', encoding='utf-8')
    report = worldflow.prepare(raw, OUT/'worldflow')
    (OUT/'worldflow.json').write_text(json.dumps(report, indent=2, default=str), encoding='utf-8')
    print('Prepared strict railway WorldSpec, navigation and composition gates.')


def generate(grey):
    p = params()
    p['renewal_greybox'] = grey
    c = parkrail.build(p)
    name = 'greybox' if grey else 'Park Rail Renewal'
    schem.save(str(OUT/(name+'.litematic')), c.to_model(), name=name)
    (OUT/(name+'.meta.json')).write_text(json.dumps(c.meta, indent=2), encoding='utf-8')
    print(name, int((c.ids > 0).sum()), 'blocks')


def packet(grey=False):
    from tools.look import grid
    name = 'greybox' if grey else 'Park Rail Renewal'
    m = schem.load(str(OUT/(name+'.litematic')))
    panels = []
    for st in params()['stations']:
        ac = st['at_u']
        crop = m.copy()
        crop.ids = m.ids[:, ac-46:ac+47, :].copy()
        cam = render3d.orbit(crop, yaw=-65, pitch=10, dist=.85)
        im = Image.fromarray(render3d.render(crop, cam, 1100, 620))
        im.save(OUT/(('greybox_' if grey else '')+st['land']+'.png'))
        panels.append((im, st['title']))
    grid(panels,1,'PARK LINE — '+('MASSING REVIEW' if grey else 'RENEWAL')).save(OUT/(name+'.png'))
    print('Rendered three station views.')


if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('command', choices=['prepare','greybox','detail','packet'])
    a=ap.parse_args()
    if a.command=='prepare': prepare()
    elif a.command=='greybox': generate(True); packet(True)
    elif a.command=='detail': generate(False)
    else: packet()
