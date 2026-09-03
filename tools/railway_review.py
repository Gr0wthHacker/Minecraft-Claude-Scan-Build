"""Reproducible railway plan, massing, review renders and candidate assembly.

Usage: python tools/railway_review.py prepare|greybox|detail|packet|assemble
Outputs are isolated under out/railway_v2; no live schematic is shipped.
"""
from pathlib import Path
import argparse
import copy
import json
import sys
import hashlib

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
    cfg['anchors'] = [{'name':'queue_entry','kind':'queue','position':[4,13,286]},
                      {'name':'boarding','kind':'board','position':[4,13,279]},
                      {'name':'ride_exit','kind':'ride_exit','position':[7,13,295]},
                      {'name':'service_access','kind':'maintenance','position':[10,1,256]}]
    cfg['design']['narrative'] = 'Three distinct free stations on a two-track rim railway with independent exit stairs, sloped dispatch and approach holding.'
    (ROOT/'configs/park_rail_v2.yaml').write_text(yaml.safe_dump(cfg, sort_keys=False), encoding='utf-8')
    raw = json.loads((ROOT/'park_final.world.json').read_text())
    raw['name'] += ' — Railway Renewal'
    # This is a railway-only overlay. Other plots remain reserved, but their
    # legacy generator contracts are outside this change and are not rebuilt.
    raw['modules'] = [m for m in raw['modules'] if m['plot'].startswith('line_')]
    raw['routes'] = [r for r in raw['routes'] if not r['name'].startswith('railway_')]
    for plot in raw['plots']:
        if plot['name'].startswith('line_'):
            plot['bounds'][0], plot['bounds'][2] = 172, 186
    for m in raw['modules']:
        if not m['plot'].startswith('line_'):
            continue
        plot = next(p for p in raw['plots'] if p['name']==m['plot'])
        lo, hi = plot['bounds'][1], plot['bounds'][3]
        m.update(generator='parkrail', params={**copy.deepcopy(cfg['params']), 'crop_u': [lo, hi]},
                 at=[172, lo], footprint=[15, hi-lo+1],
                 budget={'blocks': 12000 if hi-lo > 100 else 3000},
                 purpose='Free park transport and elevated promenade',
                 scenarios=['public_visit','queue_board_exit','occupied_platform','restart','staff_recovery'],
                 access_points=[[172, next((s['at_u']+s['stair']*19 for s in cfg['params']['stations']
                                          if lo <= s['at_u'] <= hi), (lo+hi)//2)]],
                 anchors=[{'name':'public_entry','kind':'entry','position':[0,1, min(20,hi-lo)]},
                          {'name':'return','kind':'exit','position':[7,13, min(21,hi-lo)]},
                          {'name':'maintenance','kind':'maintenance','position':[10,1,min(22,hi-lo)]}])
        station=next((s for s in cfg['params']['stations'] if lo<=s['at_u']<=hi),None)
        if station:
            ac,step=station['at_u']-lo,station['stair']
            m['anchors']=[{'name':name,'kind':kind,'position':point} for name,kind,point in (
                ('public_entry','entry',[0,2,ac+step*19]),
                ('queue_entry','queue',[4,13,ac-step*7]),
                ('boarding','board',[4,13,ac]),
                ('ride_exit','ride_exit',[7,13,ac-step*16]),
                ('service_access','maintenance',[10,1,ac+step*23]))]
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
    if grey:
        schem.save(str(OUT/(name+'.litematic')), c.to_model(), name=name)
    else:
        from mcbuild.pipeline import run_config, Settings
        config_path=ROOT/'configs/park_rail_v2.yaml'
        cfg=yaml.safe_load(config_path.read_text())
        cfg['source_revisions']={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest()
                                 for f in ('mcbuild/gen/parkrail.py','mcbuild/gen/parkrail_v2.py',
                                           'mcbuild/gen/parkrail_signals.py','mcbuild/gen/canvas.py','mcbuild/circuit.py')}
        config_path.write_text(yaml.safe_dump(cfg,sort_keys=False),encoding='utf-8')
        _, audited=run_config(str(ROOT/'configs/park_rail_v2.yaml'), settings=Settings(out_dir=str(OUT)),
                             ship=False, render_sheet=False)
        from dataclasses import asdict
        from mcbuild.generator_contract import assess
        contract=assess(cfg,c.to_model(),mechanics={},design={'brief':cfg['design']})
        if not contract['ok']: raise ValueError(contract['failures'])
        audit_data={**asdict(audited),'bom':dict(audited.bom),'tiers':dict(audited.tiers)}
        (OUT/'audit.json').write_text(json.dumps({'audit':audit_data,
                                                 'generator_contract':contract,
                                                 'source_revisions':cfg['source_revisions'],
                                                 'server_profile':'skyblock-1.19'},indent=2,default=str))
        from mcbuild import scan
        detail_meta=json.loads((OUT/(name+'.scan.json')).read_text())
        scan.save_pair(str(OUT/(name+'.litematic')), c.to_model(),
                       {**detail_meta,'origin':{'x':97672,'y':202,'z':80300}, 'name':name,
                        'generator_contract':contract,'server_profile':'skyblock-1.19',
                        'budget_blocks':42000,'blocks':int(c.to_model().solid().sum()),
                        'anchor_status':'candidate; live proof pending',
                        'generated_by':'configs/park_rail_v2.yaml'}, name=name)
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
        if not grey:
            views={
                'arrival':render3d.Camera((-22,3.6,46+st['stair']*19),(3,7,46+st['stair']*19),58),
                'facade':render3d.orbit(crop,yaw=-90,pitch=0,dist=.8),
                'skyline':render3d.orbit(crop,yaw=-65,pitch=4,dist=1.2),
                'interior':render3d.Camera((7.5,15,46-st['stair']*12),(7.5,19,46+st['stair']*5),70),
                'voidside':render3d.orbit(crop,yaw=65,pitch=10,dist=.85),
            }
            review=[]
            for title,camera in views.items():
                shot=Image.fromarray(render3d.render(crop,camera,800,480))
                shot.save(OUT/(st['land']+'_'+title+'.png'))
                review.append((shot,title))
            grid(review,2,st['title']+' — REVIEW').save(OUT/(st['land']+'_review.png'))
    grid(panels,1,'PARK LINE — '+('MASSING REVIEW' if grey else 'RENEWAL')).save(OUT/(name+'.png'))
    if not grey:
        from mcbuild import nightlight,nbt
        from PIL import ImageDraw
        states=[]
        for tag in m.palette:
            name=nbt.state_name(tag);props=nbt.state_props(tag)
            states.append(name+'['+','.join(f'{k}={v}' for k,v in props.items())+']')
        opaque,emit,passy,spawn,water=nightlight.classify(states)
        for i,state in enumerate(states):
            if 'redstone_lamp' in state and 'lit=true' not in state: emit[i]=0
        light=nightlight.propagate(opaque[m.ids],emit[m.ids])
        walk_y=13
        # The heatmap is block light at platform foot height, with occupied
        # cells masked. It is a measurement, not a simulated night photograph.
        colors=np.zeros((600,15,3),dtype=np.uint8)
        levels=light[walk_y,:,:]
        colors[:,:,0]=np.minimum(255,levels*17)
        colors[:,:,1]=np.minimum(210,levels*14)
        colors[:,:,2]=np.minimum(130,levels*9)
        clear=passy[m.ids[walk_y]] & passy[m.ids[walk_y+1]] & ~passy[m.ids[walk_y-1]]
        colors[~clear]=[45,50,58]
        heat=Image.fromarray(colors.transpose(1,0,2)).resize((1200,180),Image.Resampling.NEAREST)
        canvas=Image.new('RGB',(1220,235),(245,245,245));canvas.paste(heat,(10,40))
        ImageDraw.Draw(canvas).text((10,10),'NIGHT CHECK — platform block light: black = 0, gold = 15, grey = occupied / stair opening',fill=(20,20,20))
        canvas.save(OUT/'night_light.png')
        measured=clear.copy();measured[:,:4]=False;measured[:,11:]=False
        report={'minimum_platform_light':int(levels[measured].min()),
                'dark_platform_cells':int(((levels==0)&measured).sum()),
                'measured_platform_cells':int(measured.sum()),
                'model':'block light only; inactive status lamps emit zero; no skylight credited'}
        (OUT/'night_light.json').write_text(json.dumps(report,indent=2))
        print('Night:',report)
    print('Rendered three station views.')


def assemble():
    """Replace only matching old railway cells in the current assembled park."""
    from mcbuild import scan, nbt, worldexport, worldassembly
    from mcbuild.world import SparseWorld
    base=scan.load(str(ROOT/'out/Park Complete.litematic'))
    old=schem.load(str(ROOT/'out/Park Rail.litematic'))
    new=scan.load(str(OUT/'Park Rail Renewal.litematic'))
    m=base.model.copy()
    ox,oy,oz=base.origin
    dy=202-oy
    keys=[nbt.state_key(t) for t in m.palette]
    names=m.names
    index={key:i for i,key in enumerate(keys)}
    removed=0
    removed_positions=set()
    for y,z,x in zip(*old.solid().nonzero()):
        at=(int(x)+172,int(y)+dy,int(z))
        xx,yy,zz=at
        if keys[m.ids[yy,zz,xx]]==nbt.state_key(old.palette[old.ids[y,z,x]]):
            m.ids[yy,zz,xx]=0
            removed+=1
            removed_positions.add(at)
    conflicts=[]
    replaceable={'minecraft:moss_carpet'}
    for y,z,x in zip(*new.model.solid().nonzero()):
        xx,yy,zz=int(x)+172,int(y)+dy,int(z)
        state=new.model.palette[new.model.ids[y,z,x]]
        key=nbt.state_key(state)
        existing=m.ids[yy,zz,xx]
        if existing and keys[existing]!=key and names[existing] not in replaceable:
            conflicts.append([xx,yy,zz,names[existing],nbt.state_name(state)])
            continue
        if key not in index:
            index[key]=len(m.palette);m.palette.append(state);keys.append(key);names.append(nbt.state_name(state))
        m.ids[yy,zz,xx]=index[key]
    if conflicts:
        (OUT/'assembly_conflicts.json').write_text(json.dumps(conflicts,indent=2))
        raise ValueError(f'{len(conflicts)} new railway cells collide with retained park; see assembly_conflicts.json')
    # Transfer sign entities while preserving every other build's tile data.
    def tilepos(t):
        return tuple(int(t.value[k].value) for k in ('x','y','z'))
    m.tile_entities=[t for t in m.tile_entities if tilepos(t) not in removed_positions]
    for tile in new.model.tile_entities:
        t=copy.deepcopy(tile)
        t.value['x'].value+=172;t.value['y'].value+=dy
        m.tile_entities.append(t)
    path=OUT/'Park Complete Railway Renewal.litematic'
    scan.save_pair(str(path),m,{**base.meta,'name':'Park Complete Railway Renewal',
                               'anchor_status':'candidate; railway live proof pending'},name='Park Complete Railway Renewal')
    # Chunk exports cover the rail and its existing public approaches. They are
    # a validation packet, not a second layer to paste over the complete park.
    world=SparseWorld()
    states=[]
    for tag in m.palette:
        name=nbt.state_name(tag);props=nbt.state_props(tag)
        states.append(name+('['+','.join(f'{k}={v}' for k,v in sorted(props.items()))+']' if props else ''))
    for y,z,x in zip(*m.solid().nonzero()):
        if x>=170 or any(abs(int(z)-u)<=6 for u in (96,260,524)) and x<=172 and y<dy+35:
            world.put(int(x)+ox,int(y)+oy,int(z)+oz,states[m.ids[y,z,x]])
    chunks=worldexport.export_chunks(world,OUT/'chunks',prefix='RailwayReview')
    # SparseWorld stores block states only; attach sign text explicitly to the
    # chunk containing each sign so the build packet retains its wayfinding.
    tile_by_chunk={}
    for tile in m.tile_entities:
        x,y,z=tilepos(tile);world_pos=(x+ox,y+oy,z+oz)
        if world.get(*world_pos)!='minecraft:air':
            tile_by_chunk.setdefault(tuple(v//16 for v in world_pos),[]).append((tile,world_pos))
    for chunk_path in chunks:
        chunk=scan.load(chunk_path)
        chunk_key=tuple(v//16 for v in chunk.origin)
        if chunk_key not in tile_by_chunk: continue
        chunk.model.tile_entities=[]
        for tile,world_pos in tile_by_chunk[chunk_key]:
            t=copy.deepcopy(tile)
            for k,value,start in zip(('x','y','z'),world_pos,chunk.origin):
                t.value[k].value=value-start
            chunk.model.tile_entities.append(t)
        scan.save_pair(chunk_path,chunk.model,chunk.meta,name='Railway Review Chunk')
    meta=json.loads((OUT/'Park Rail Renewal.meta.json').read_text())
    stops=[]
    for s in meta['renewal']['stations']:
        ac=next(t['at_u'] for t in params()['stations'] if t['title']==s['title'])
        stops.extend([[97676,215,80300+ac],
                      [97672+s['queue'][0][0],202+s['queue'][0][1],80300+s['queue'][0][2]],
                      [97672+s['exit'][0],202+s['exit'][1],80300+s['exit'][2]],
                      [97672+s['service'][0],202+s['service'][1],80300+s['service'][2]]])
    for port in meta['renewal']['signals']:
        x,y,z=port['staff_panel'];stops.append([97672+x,202+y,80300+z])
    report=worldassembly.validate(chunks,entry=[97520,203,80560],destinations=stops)
    report.update(removed_old_rail_cells=removed,candidate=str(path),chunks=chunks,
                  source_park_sha256=hashlib.sha256((ROOT/'out/Park Complete.litematic').read_bytes()).hexdigest())
    (OUT/'worldvalidate.json').write_text(json.dumps(report,indent=2))
    print('Assembly:',report['ok'],report['failures'])
    if not report['ok']: raise ValueError('assembled railway access gate failed')


if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('command', choices=['prepare','greybox','detail','packet','assemble'])
    a=ap.parse_args()
    if a.command=='prepare': prepare()
    elif a.command=='greybox': generate(True); packet(True)
    elif a.command=='detail': generate(False)
    elif a.command=='packet': packet()
    else: assemble()
