import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from mcbuild import scan
from mcbuild.gen.parkrefinement import piece
base=scan.load('out/premium_refinement/base.litematic')
cap=scan.load('out/park_stitch_audit.litematic')
def at(s,p):
 x,y,z=[a-b for a,b in zip(p,s.origin)]
 if min(x,y,z)<0 or y>=s.model.ids.shape[0] or z>=s.model.ids.shape[1] or x>=s.model.ids.shape[2]:return 'outside'
 return s.model.names[s.model.ids[y,z,x]].split(':')[-1]
areas=[('arrival south','planter',(25,270,45,291)),('arrival north','planter',(25,309,45,330)),('garden south','screen',(34,351,45,357)),('garden north','screen',(52,371,62,377)),('orientation','board',(24,278,33,292)),('coaster','desk',(24,105,40,122)),('fossil','desk',(126,51,150,78)),('prism','lens',(24,456,43,467))]
chosen=[];occupied=set()
for title,kind,(v0,u0,v1,u1) in areas:
 found=[]
 for y in (203,204):
  for v in range(v0,v1):
   for u in range(u0,u1):
    sp={'name':title,'kind':kind,'at':[v,y,u],'land':'frontier' if kind=='desk' else 'prismworks' if kind=='lens' else 'midway','text':[['WELCOME','LOST PLATEAU','NORTH AVENUE'],['PRISMWORKS','SOUTH AVENUE','MIDWAY AHEAD']] if kind=='board' else ['FIELD NOTES','SPECIMEN STUDY']}
    cells=piece(sp).cells
    if any(at(base,p)!='air' or at(cap,p) not in ('air','cave_air') or p in occupied for p in cells):continue
    roots=[p for p in cells if p[1]==y]
    if not all(at(base,(x,h-1,z)) in ('moss_block','grass_block','dirt','stone','andesite','coarse_dirt','podzol') for x,h,z in roots):continue
    if any(not(v0<=x-97500<=v1 and u0<=z-80300<=u1) for x,h,z in cells):continue
    found.append(sp)
 if found:
  sp=found[len(found)//2];chosen.append(sp);occupied.update(piece(sp).cells);print(title,len(found),sp['at'])
 else:print('NO SITE',title)
Path('out/premium_refinement/sites.json').write_text(json.dumps(chosen,indent=2))
