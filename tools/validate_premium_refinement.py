import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from mcbuild import scan
from tools import park_place as pp
base=scan.load('out/premium_refinement/base.litematic');add=scan.load('out/PF Premium Refinement.litematic')
merged,n=scan.merge(base,add.model,add.origin);assert n==0
assert np.array_equal(merged.ids[base.model.ids>0],base.model.ids[base.model.ids>0])
meta=dict(base.meta);meta['refinement']={'added':int(add.model.solid().sum()),'removed':0,'replaced':0,'source':'configs/pf_premium_refinement.yaml'}
scan.save_pair('out/premium_refinement/candidate.litematic',merged,meta,name='Park Complete')
raw,origin,_=pp.complete(pp.modules());ox,oy,oz=97500+origin[0],202+origin[1],80300+origin[2]
conflicts=[]
for y,z,x in zip(*add.model.solid().nonzero()):
 X,Y,Z=add.origin[0]+int(x),add.origin[1]+int(y),add.origin[2]+int(z)
 i=raw.ids[Y-oy,Z-oz,X-ox]
 if i:conflicts.append([X,Y,Z,raw.names[i]])
print('RAW COLLISIONS',conflicts)
print('old blocks',int(base.model.solid().sum()),'new blocks',int(merged.solid().sum()),'overlap',n)
