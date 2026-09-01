import json, os, glob
from mcbuild import schem, circuit

names = set()
for z in ('park_left','park_right','park_centre'):
    p=json.load(open(f'out/plans/{z}.json'))
    for m in p['modules']:
        names.add((z, m['name'], m['kind']))

for z, n, kind in sorted(names):
    f = f'out/{n}.litematic'
    if not os.path.exists(f):
        continue
    sc = json.load(open(f'out/{n}.scan.json'))
    o = sc.get('origin')
    o = (o['x'],o['y'],o['z']) if isinstance(o,dict) else tuple(o)
    m = schem.load(f)
    fi = circuit.inspect(m, o)
    real = [x for x in fi if x[0] != 'quasi-connectivity']
    if real:
        print(f'--- {z} {n} ({kind}) origin={o}')
        for k,p,d in real:
            print(f'      {k:30s} {p}  {d}')
