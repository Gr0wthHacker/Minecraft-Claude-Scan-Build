"""Mouth-only parkour connection between the Prism descents and Abyss Market."""
from __future__ import annotations

import math

from .canvas import hash01
from .vertical import Ctx, World


ACCESS = {
    "under": [],
    "greybox": False,
    # The animal's arm crown blocks the tempting flanking curves.  Its anatomical
    # mouth axis is the clear measured corridor through the crown.
    "inbound": [[97606,162,80801],[97598,158,80776],[97598,151,80730],
                [97599,144,80716],[97596,142,80713]],
    "outbound": [[97604,142,80713],[97600,142,80714],[97600,140,80718],
                 [97602,136,80736],[97602,130,80770],
                 [97613,124,80791]],
    "spacing": 4.0,
    "seed": 23,
}


def _dense(points, spacing):
    out = [tuple(points[0])]
    for a,b in zip(points,points[1:]):
        dx,dy,dz = b[0]-a[0],b[1]-a[1],b[2]-a[2]
        n=max(1,int(math.ceil(math.hypot(dx,dz)/spacing)))
        for i in range(1,n+1):
            t=i/n
            q=(round(a[0]+dx*t),round(a[1]+dy*t),round(a[2]+dz*t))
            if q != out[-1]: out.append(q)
    return out


def _clear(ctx,x,y,z,half=0):
    for dx in range(-half,half+1):
        for dz in range(-half,half+1):
            for dy in range(4):
                if ctx.occupied(x+dx,y+dy,z+dz): return False
    return True


def _fit(ctx, raw):
    """Keep the authored curve, moving a landing at most two cells around anatomy."""
    out=[raw[0]]
    for i,q in enumerate(raw[1:-1],1):
        px,py,pz=out[-1]
        choices=[]
        for r in range(3):
            for dx in range(-r,r+1):
                for dz in range(-r,r+1):
                    x,y,z=q[0]+dx,q[1],q[2]+dz
                    d=math.hypot(x-px,z-pz)
                    if 2.0 <= d <= 4.8 and py-y in (0,1,2,3) and _clear(ctx,x,y,z):
                        choices.append((abs(dx)+abs(dz),abs(d-4.0),x,y,z))
            if choices: break
        if not choices:
            raise ValueError(f"no clear parkour landing near {q}")
        _,_,x,y,z=min(choices)
        out.append((x,y,z))
    out.append(raw[-1])
    if math.hypot(out[-1][0]-out[-2][0],out[-1][2]-out[-2][2]) > 4.8:
        raise ValueError("last jump does not reach the existing interface")
    return out


def _strand(w,ctx,points,label,grey,seed):
    route=_fit(ctx,_dense(points,4.0))
    feats={"ledge":0,"rest":0,"gate":0,"recovery":0,"recovery_ladder":0}
    rest_centres=[]

    def put_clear(x,y,z,name,**props):
        if ctx.occupied(x,y,z):
            return False
        w.put(x,y,z,name,**props)
        return True
    # Endpoints belong to the two existing courses and market; this artifact joins them.
    for i,(x,y,z) in enumerate(route[1:-1],1):
        rest=(i%8==0)
        gate=(i%6==3 and not rest)
        if rest:
            for dx in range(-1,2):
                for dz in range(-1,2):
                    put_clear(x+dx,y,z+dz,"light_gray_wool" if grey else
                              ("deepslate_bricks" if (dx+dz)&1 else "polished_blackstone_bricks"))
            if not grey:put_clear(x,y,z,"pearlescent_froglight")
            rest_centres.append((i,x,y,z))
            feats["rest"]+=1
        else:
            put_clear(x,y,z,"light_gray_wool" if grey else
                      ("pearlescent_froglight" if i%3 else "cyan_wool"))
            feats["ledge"]+=1
        if gate:
            # Side posts make the move legible without obstructing the landing cell.
            for s in (-1,1):
                put_clear(x+s,y+1,z,"light_gray_wool" if grey else "deepslate_brick_wall")
                put_clear(x+s,y+2,z,"light_gray_wool" if grey else "deepslate_brick_wall")
            feats["gate"]+=1

    # A narrow recovery spine ten courses below the exposed half. It stops short of
    # both interfaces, so it cannot be walked into the market as a bypass.
    exposed=route[max(2,len(route)//3):max(3,len(route)-3)]
    for a,b in zip(exposed,exposed[1:]):
        n=max(1,int(math.ceil(math.dist((a[0],a[2]),(b[0],b[2])))))
        for j in range(n+1):
            t=j/n; x=round(a[0]+(b[0]-a[0])*t); z=round(a[2]+(b[2]-a[2])*t)
            y=round(a[1]+(b[1]-a[1])*t)-10
            for dx in (-1,0,1):
                if not ctx.occupied(x+dx,y,z):
                    w.put(x+dx,y,z,"light_gray_wool" if grey else "slime_block")
                    feats["recovery"]+=1

    # Recovery is useful only when it returns a miss to the course.  One compact ladder
    # tower per strand rises from the slime spine to a real rest, and its backing doubles
    # as an unmistakable course marker.  Try four sides so existing anatomy always wins.
    candidates=[q for q in rest_centres if q[0] >= max(2,len(route)//3) and q[0] < len(route)-3]
    for _,x,y,z in candidates:
        for lx,lz,bx,bz,facing in ((x+1,z,x+2,z,"west"),(x-1,z,x-2,z,"east"),
                                   (x,z+1,x,z+2,"north"),(x,z-1,x,z-2,"south")):
            if all(not ctx.occupied(px,yy,pz) and not w.has(px,yy,pz)
                   for yy in range(y-9,y)
                   for px,pz in ((lx,lz),(bx,bz))):
                for yy in range(y-9,y):
                    w.put(bx,yy,bz,"light_gray_wool" if grey else "polished_blackstone_bricks")
                    if grey:
                        w.put(lx,yy,lz,"light_gray_wool")
                    else:
                        w.put(lx,yy,lz,"ladder",facing=facing)
                feats["recovery_ladder"]+=1
                break
        if feats["recovery_ladder"]:
            break
    return route,feats


def build(cfg:dict,donors=None):
    p={**ACCESS,**(cfg or {})}
    if not p["under"]:raise ValueError("abyss access requires measured context artifacts")
    ctx=Ctx(p["under"])
    w=World();grey=bool(p.get("greybox"));seed=int(p["seed"])
    inbound,fi=_strand(w,ctx,p["inbound"],"hunt",grey,seed)
    outbound,fo=_strand(w,ctx,p["outbound"],"wake",grey,seed+1)
    return w.canvas({"kind":"abyss_mouth_access","entrance":"parkour_only",
      "inbound_anchor":p["inbound"][0],"mouth_entry":p["inbound"][-1],
      "mouth_exit":p["outbound"][0],"outbound_anchor":p["outbound"][-1],
      "routes":{"inbound":[list(q) for q in inbound],"outbound":[list(q) for q in outbound]},
      "features_built":{"inbound":len(inbound)-2,"outbound":len(outbound)-2,
                        **{f"in_{k}":v for k,v in fi.items()},
                        **{f"out_{k}":v for k,v in fo.items()}},
      "contract":"No surface entrance. Every guest interface is parkour or recovery."})


DEFAULTS=ACCESS
