import sys; sys.path.insert(0, r"C:\Users\Jack\mctest")
"""Rebuild the night pass's base world: the capture, plus every design the night solve must
assume final. Order matters - the DIG first, then the blocks, or a froglight's own cell gets
re-filled by the turf it was meant to replace."""
import json, os
import numpy as np
from mcbuild import schem, scan
DESIGNS = ["out/Falls", "out/Lowland Thicket"]
m = schem.load("out/island_full.litematic"); s = scan.load("out/island_full.scan.json")
o = s.meta['origin']; ox,oy,oz = o['x'],o['y'],o['z']
names = list(m.names)
idx = {n.split(":")[-1]: i for i,n in enumerate(names)}
def slot(state):
    if state in idx: return idx[state]
    proto = m.palette[0]
    Tag = type(proto)
    inner = proto.value['Name']
    ent = Tag(10, {'Name': type(inner)(8, 'minecraft:' + state.split('[')[0])})
    m.palette.append(ent); idx[state] = len(m.palette)-1
    return idx[state]
air = idx.get("air", 0)
dug = placed = 0
for d in DESIGNS:
    for x,y,z in (json.load(open(d+".scan.json",encoding="utf-8")).get("dig") or []):
        iy,iz,ix = y-oy,z-oz,x-ox
        if 0<=iy<m.ids.shape[0] and 0<=iz<m.ids.shape[1] and 0<=ix<m.ids.shape[2]:
            m.ids[iy,iz,ix] = air; dug += 1
for d in DESIGNS:
    for x,y,z,b in json.load(open(d+".work.json",encoding="utf-8"))["cells"]:
        iy,iz,ix = y-oy,z-oz,x-ox
        if 0<=iy<m.ids.shape[0] and 0<=iz<m.ids.shape[1] and 0<=ix<m.ids.shape[2]:
            m.ids[iy,iz,ix] = slot(b); placed += 1
scan.save_pair("out/island_night_base.litematic", m, s.meta, name="island_night_base")
print(f"night base: {placed} design cells, {dug} dug, palette {len(m.palette)}")
