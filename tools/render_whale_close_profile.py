"""Tight side-profile review of the current Abyss leviathan."""
from __future__ import annotations

import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from PIL import Image,ImageDraw
from mcbuild import render3d,scan

item=scan.load(str(ROOT/"out"/"Abyss Sperm Whale.litematic"))
cam=render3d.Camera((-120,48,108),(57,39,108),fov=42)
im=Image.fromarray(render3d.render(item.model,cam,1600,900,ground=False))
d=ImageDraw.Draw(im);d.rectangle((0,0,1600,42),fill=(8,11,17))
d.text((18,14),"ABYSS LEVIATHAN — CLOSE SIDE PROFILE",fill="white")
path=ROOT/"out"/"under_squid_plan"/"leviathan_close_side_profile.png"
im.save(path);print(path)
