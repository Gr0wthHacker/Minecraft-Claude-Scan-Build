import sys,json,yaml
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from mcbuild import scan,render,blocks,palette
from mcbuild.gen import parkrefinement as gen
from PIL import Image,ImageDraw
cfg=yaml.safe_load(Path('configs/pf_premium_refinement.yaml').read_text())['params']
base=scan.load('out/premium_refinement/base.litematic')
c=gen.build({**cfg,'greybox':True});m=c.to_model();meta={'origin':dict(zip(('x','y','z'),c.world_origin)),'kind':'park_refinement'}
scan.save_pair('out/premium_refinement/greybox.litematic',m,meta)
merged,n=scan.merge(base,m,c.world_origin);assert n==0
views=[]
for label,box in [('Arrival',(18,270,50,331)),('Garden',(30,346,64,380)),('Coaster',(22,107,39,126)),('Lab',(125,60,153,83)),('Prism',(22,450,44,468))]:
 from mcbuild.scan import Scan
 # Temporary scan uses the original origin because additions are fully inside its bounds.
 import copy
 s=copy.copy(base);s.model=merged
 crop,_=scan.cut(s,97500+box[0],202,80300+box[1],97500+box[2],218,80300+box[3])
 im=Image.fromarray(render.elevation(crop,'top'));im.thumbnail((280,480));im=im.resize((im.width*4,im.height*4));ImageDraw.Draw(im).text((2,2),label,fill='white',stroke_width=1,stroke_fill='black');views.append(im)
out=Image.new('RGB',(sum(i.width for i in views),max(i.height for i in views)),(30,30,30));x=0
for im in views:out.paste(im,(x,0));x+=im.width
out.save('out/premium_refinement/greybox.png')
print('greybox cells',int((m.ids>0).sum()),'overlap',n)
for s in cfg['pieces']:
 for name,props in gen.piece(s).cells.values():
  assert blocks.exists(name) and blocks.available(name) and blocks.spendable(name),name
print('palette legal')
