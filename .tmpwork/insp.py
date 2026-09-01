import json, sys
from mcbuild import schem, circuit

def orig(name):
    sc = json.load(open(f'out/{name}.scan.json'))
    o = sc.get('origin')
    if isinstance(o, dict):
        return (o['x'], o['y'], o['z'])
    return tuple(o)

for name in ['Park_Centre Complete','Park_Left Complete','Park_Right Complete']:
    m = schem.load(f'out/{name}.litematic')
    o = orig(name)
    f = circuit.inspect(m, o)
    print(f'=== {name} origin={o} findings={len(f)}')
    for k,p,d in f:
        edge = circuit.near_edge(m, o, p)
        print(f'    {k:32s} {p} edge={edge}  {d}')
