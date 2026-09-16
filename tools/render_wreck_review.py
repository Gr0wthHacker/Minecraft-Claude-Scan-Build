"""Four-view review sheet for the Prismworks abyssal wreck."""
from __future__ import annotations

import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from PIL import Image,ImageDraw
from mcbuild import render3d,scan
from mcbuild.gen import abysswreck

if len(sys.argv)>1:
    m=scan.load(sys.argv[1]).model; grey="Greybox" in Path(sys.argv[1]).name
else:
    m=abysswreck.build({"greybox":True}).to_model();grey=True
views=[
 ("OVERLOOK BROADSIDE",(92,47,245),(92,35,45),49),
 ("THREE-QUARTER",(-125,105,225),(88,34,44),52),
 ("BOW + SURVEY ARMS",(-155,50,48),(28,32,48),48),
 ("STERN + DUCTED ROTOR",(330,52,45),(155,32,43),48),
]
page=Image.new("RGB",(1280,900),(10,13,20))
for i,(title,pos,target,fov) in enumerate(views):
    im=Image.fromarray(render3d.render(m,render3d.Camera(pos,target,fov=fov),640,450,ground=False))
    d=ImageDraw.Draw(im);d.rectangle((0,0,640,30),fill=(8,11,17));d.text((12,9),title,fill="white")
    page.paste(im,((i%2)*640,(i//2)*450))
name="wreck_greybox_review.png" if grey else "wreck_detailed_review.png"
path=ROOT/"out"/"under_squid_plan"/name;page.save(path);print(path)
