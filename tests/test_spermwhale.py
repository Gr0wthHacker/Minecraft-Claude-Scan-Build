from __future__ import annotations

import json, os
import numpy as np
import pytest

from mcbuild import nbt, scan, schem

OUT="out"; DESIGN=os.path.join(OUT,"Abyss Sperm Whale.litematic")
pytestmark=pytest.mark.skipif(not os.path.exists(DESIGN),reason="needs generated whale")


def _cells(path):
    m=schem.load(path); s=scan.load(path.replace(".litematic",".scan.json"))
    yy,zz,xx=np.nonzero(m.ids)
    return m,s,{(int(x+s.origin[0]),int(y+s.origin[1]),int(z+s.origin[2])) for x,y,z in zip(xx,yy,zz)}


def test_whale_is_one_large_anatomical_silhouette():
    m,s,cells=_cells(DESIGN); meta=json.load(open(DESIGN.replace(".litematic",".scan.json")))
    assert 50000 <= len(cells) <= 85000
    xs,ys,zs=zip(*cells)
    assert max(zs)-min(zs) >= 195 and max(xs)-min(xs) >= 95 and max(ys)-min(ys) >= 50
    features=meta["features_built"]
    for part in ("body","head","jaw","fin","fluke","peduncle","eye","mouth","teeth","blowhole","scar"):
        assert features[part] > 0, f"missing diagnostic whale feature: {part}"
    assert meta["profile_view"] == "side"
    assert meta["mouth_open"]["nose_gape_courses"] >= 10
    assert meta["mouth_open"]["tooth_rows"] == 2


def test_whale_keeps_the_measured_void_reservation():
    _,_,cells=_cells(DESIGN)
    x1,y1,z1,x2,y2,z2=(97500,95,80255,97614,179,80469)
    assert all(x1<=x<=x2 and y1<=y<=y2 and z1<=z<=z2 for x,y,z in cells)
    for path in ("Park Complete.litematic","Abyss Squid.litematic","Abyss Market.litematic"):
        _,_,other=_cells(os.path.join(OUT,path))
        assert not cells & other, f"whale overlaps {path}"


def test_whale_palette_is_restrained_and_119_safe():
    m,_,_=_cells(DESIGN)
    names={nbt.state_name(q).split(":")[-1] for q in m.palette[1:]}
    assert names == {"gray_wool","black_wool","light_gray_wool","white_wool","bone_block",
                     "red_wool","pink_wool"}


def test_open_mouth_is_real_negative_space_not_painted_skin():
    m,_,_=_cells(DESIGN)
    z=205; x=round(53.0+0.025*z)
    ys=np.where(m.ids[:,z,x] != 0)[0].tolist()
    gaps=[b-a-1 for a,b in zip(ys,ys[1:])]
    assert gaps and max(gaps) >= 10, f"largest physical gape is only {max(gaps,default=0)} courses"
