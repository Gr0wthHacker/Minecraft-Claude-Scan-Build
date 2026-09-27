"""Tail overlook glazing and static echolocation frames for the lower Abyss scene."""
from __future__ import annotations

import math

from .vertical import Ctx, World


SOUNDING = {
    "under": [],
    "squid": "out/Abyss Squid.litematic",
    "greybox": False,
    "viewpoint": [97600, 109, 80505],
    "target": [97558, 137, 80454],
    "ring_z": [80468, 80475, 80482],
}


def _ray(a, b, steps=120):
    out=[]
    for i in range(steps+1):
        t=i/steps
        q=tuple(round(a[j]+(b[j]-a[j])*t) for j in range(3))
        if not out or q != out[-1]: out.append(q)
    return out


def build(cfg: dict, donors=None):
    p={**SOUNDING, **(cfg or {})}
    if not p["under"]: raise ValueError("abyss sounding requires measured context")
    ctx=Ctx(p["under"]); squid=Ctx(p["squid"]); w=World(); grey=bool(p["greybox"])
    eye=tuple(int(v) for v in p["viewpoint"]); target=tuple(int(v) for v in p["target"])

    # Five by four sight bundle through the tail shell. Only squid cells become dig cells;
    # the glass itself occupies one shared plane so the reveal reads as a designed aperture.
    dig=set()
    for ex in range(-2,3):
        for ey in range(0,4):
            a=(eye[0]+ex,eye[1]+ey,eye[2])
            b=(target[0]+round(ex*.45),target[1]+round((ey-1.5)*1.2),target[2])
            for q in _ray(a,b):
                if 80496 <= q[2] <= 80505 and squid.occupied(*q): dig.add(q)
    if len(dig)>60: raise ValueError(f"tail aperture exceeds 60-cell budget: {len(dig)}")

    pane="light_gray_wool" if grey else "gray_stained_glass_pane"
    plane=min(q[2] for q in dig)
    for x in range(eye[0]-2,eye[0]+3):
        for y in range(eye[1],eye[1]+4):
            # This plane is either the newly removed skin or existing cavity air.
            if squid.occupied(x,y,plane): dig.add((x,y,plane))
            w.put(x,y,plane,pane)
    if len(dig)>60: raise ValueError(f"tail aperture exceeds 60-cell budget: {len(dig)}")

    # A modest sill and two survey lights turn an accidental tail cavity into a viewpoint.
    for x in range(eye[0]-3,eye[0]+4):
        if not ctx.occupied(x,eye[1]-1,eye[2]):
            w.put(x,eye[1]-1,eye[2],"light_gray_wool" if grey else "polished_blackstone_bricks")
    for x in (eye[0]-3,eye[0]+3):
        if not ctx.occupied(x,eye[1],eye[2]):
            w.put(x,eye[1],eye[2],"light_gray_wool" if grey else "pearlescent_froglight")

    # Three incomplete sonar rings grow toward the squid. The open lower quarter keeps the
    # sculpture from becoming a tunnel and preserves the whale's blunt-head silhouette.
    ring_counts=[]
    for ri,z in enumerate(p["ring_z"]):
        rx,ry=9+ri*3,7+ri*2; placed=0
        samples=max(40,int(2*math.pi*max(rx,ry)*2))
        for i in range(samples):
            a=2*math.pi*i/samples
            if math.sin(a)<-.48: continue
            x=round(target[0]+rx*math.cos(a)); y=round(target[1]+ry*math.sin(a))
            if ctx.occupied(x,y,z) or w.has(x,y,z): continue
            material=("light_gray_wool" if grey else
                      ("pearlescent_froglight" if i%17==0 else "oxidized_cut_copper"))
            w.put(x,y,z,material); placed+=1
        ring_counts.append(placed)

    boxes=[[x,y,z,x,y,z] for x,y,z in sorted(dig)]
    return w.canvas({
        "kind":"abyss_sounding", "viewpoint":list(eye), "target":list(target),
        "dig":[list(q) for q in sorted(dig)], "exclude_boxes":boxes,
        "aperture":{"plane_z":plane,"width":5,"height":4,"dig_budget":60},
        "features_built":{"tail_glazing":20,"sound_frames":ring_counts,"survey_lights":2},
        "public_access":"Abyss Market tail gallery only",
        "mechanics":"Static echolocation fallback; no redstone clock required.",
    })


DEFAULTS=SOUNDING
