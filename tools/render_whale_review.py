"""Four-view anatomy review for the Abyss sperm whale."""
from __future__ import annotations

import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from PIL import Image,ImageDraw
from mcbuild import render3d,scan

source=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/"out"/"Abyss Sperm Whale.litematic"
item=scan.load(str(source)); m=item.model
views=[
 ("PROFILE — 200-course open-mouth leviathan",(-260,55,110),(57,40,110),46),
 ("THREE-QUARTER",(-205,105,315),(57,40,135),48),
 ("HEAD-ON OPEN GAPE",(57,44,355),(57,38,175),43),
 ("TAIL-ON BANKED FLUKES",(57,50,-235),(57,40,95),43),
]
page=Image.new("RGB",(1280,900),(10,13,20))
for i,(title,pos,target,fov) in enumerate(views):
    im=Image.fromarray(render3d.render(m,render3d.Camera(pos,target,fov=fov),640,450,ground=False))
    d=ImageDraw.Draw(im);d.rectangle((0,0,640,30),fill=(8,11,17));d.text((12,9),title,fill="white")
    page.paste(im,((i%2)*640,(i//2)*450))
name="leviathan_greybox_review.png" if "Greybox" in source.name else "whale_anatomy_review.png"
path=ROOT/"out"/"under_squid_plan"/name;page.save(path)
print(path)
