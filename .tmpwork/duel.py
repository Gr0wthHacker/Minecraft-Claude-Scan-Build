import yaml
from mcbuild.gen import casino, circuits
cfg=yaml.safe_load(open('configs/duel_1.yaml')); p=dict(cfg['params']); p.pop('under',None)
import mcbuild.gen.casino as C
orig = C._link
def link(w,p2,ctx,a,b):
    print('LINK', a, b, 'cells:', len(circuits.connect(a,b)["cells"]))
    return orig(w,p2,ctx,a,b)
C._link = link
C.build(p)
