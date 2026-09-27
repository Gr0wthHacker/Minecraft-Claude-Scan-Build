"""Assemble and render the review packet for the completed under-squid scene."""
from __future__ import annotations

import json, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from PIL import Image, ImageDraw
from mcbuild import render3d, scan

OUT=ROOT/"out"; REVIEW=OUT/"under_squid_plan"; REVIEW.mkdir(parents=True,exist_ok=True)


def _origin_meta(origin,name,model,extra=None):
    return {"name":name,"origin":{"x":origin[0],"y":origin[1],"z":origin[2]},
            "size":{"x":model.shape_xyz[0],"y":model.shape_xyz[1],"z":model.shape_xyz[2]},
            "non_air_blocks":int(model.solid().sum()),"palette_size":len(model.palette),
            "tile_entities":len(model.tile_entities or []),**(extra or {})}


def assemble():
    squid=scan.load(str(OUT/"Abyss Squid.litematic")); model=squid.model.copy()
    # Apply exact excavation manifests before additions. The new artifacts then win only in air.
    digs=[]
    for name in ("Abyss Market","Abyss Sounding"):
        meta=json.load(open(OUT/f"{name}.scan.json",encoding="utf-8")); digs += meta.get("dig",[])
    for x,y,z in digs:
        lx,ly,lz=x-squid.origin[0],y-squid.origin[1],z-squid.origin[2]
        if 0<=ly<model.ids.shape[0] and 0<=lz<model.ids.shape[1] and 0<=lx<model.ids.shape[2]:
            model.ids[ly,lz,lx]=0
    model.compact_palette(); origin=squid.origin; overlaps={}
    for name in ("Abyss Sperm Whale","Abyss Market","Abyss Mouth Access","Abyss Sounding"):
        item=scan.load(str(OUT/f"{name}.litematic"))
        holder=scan.Scan(model,_origin_meta(origin,"working",model),"","")
        model,overlaps[name]=scan.merge(holder,item.model,item.origin)
        origin=(min(origin[0],item.origin[0]),min(origin[1],item.origin[1]),min(origin[2],item.origin[2]))
    path=REVIEW/"Abyss Expansion Complete.litematic"
    scan.save_pair(str(path),model,_origin_meta(origin,"Abyss Expansion Complete",model,
        {"kind":"review_composite","parts":5,"dig":digs,"overlaps":overlaps}),
        name="Abyss Expansion Complete")
    return scan.load(str(path))


def render_packet(item):
    ox,oy,oz=item.origin
    def cam(pos,target,fov=55):
        return render3d.Camera((pos[0]-ox,pos[1]-oy,pos[2]-oz),
                               (target[0]-ox,target[1]-oy,target[2]-oz),fov=fov)
    views=[
      ("FULL ABYSS — three-quarter",(97180,245,80920),(97590,137,80435),56),
      ("SILHOUETTE — leviathan and squid",(96880,170,80410),(97590,136,80410),52),
      ("MOUTH-ONLY PARKOUR APPROACH",(97625,177,80845),(97600,145,80715),58),
      # The software renderer treats panes as opaque full cubes, so this camera sits one
      # course beyond the glazing while preserving the exact overlook sightline.
      ("TAIL OVERLOOK — open-mouth encounter",(97600.5,111.5,80500.5),(97558,137,80454),78),
    ]
    page=Image.new("RGB",(1280,900),(10,13,20))
    for i,(title,pos,target,fov) in enumerate(views):
        im=Image.fromarray(render3d.render(item.model,cam(pos,target,fov),640,450,ground=False))
        d=ImageDraw.Draw(im); d.rectangle((0,0,640,30),fill=(8,11,17));
        d.text((12,9),title,fill="white")
        page.paste(im,((i%2)*640,(i//2)*450))
    page.save(REVIEW/"abyss_expansion_review.png")


if __name__=="__main__":
    render_packet(assemble())
