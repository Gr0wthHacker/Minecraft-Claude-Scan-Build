from __future__ import annotations

import json, math, os
import numpy as np
import pytest

from mcbuild import nbt, scan, schem

OUT="out"; DESIGN=os.path.join(OUT,"Abyss Mouth Access.litematic")
pytestmark=pytest.mark.skipif(not os.path.exists(DESIGN),reason="needs generated mouth access")


def _cells(path):
    m=schem.load(path); s=scan.load(path.replace(".litematic",".scan.json"))
    yy,zz,xx=np.nonzero(m.ids)
    return m,{(int(x+s.origin[0]),int(y+s.origin[1]),int(z+s.origin[2])) for x,y,z in zip(xx,yy,zz)}


def test_access_is_mouth_only_and_each_jump_is_reachable():
    meta=json.load(open(DESIGN.replace(".litematic",".scan.json")))
    assert meta["entrance"] == "parkour_only"
    assert meta["mouth_entry"] == [97596,142,80713]
    assert meta["mouth_exit"] == [97604,142,80713]
    for route in meta["routes"].values():
        for a,b in zip(route,route[1:]):
            assert 0 < math.hypot(b[0]-a[0],b[2]-a[2]) <= 4.8
            assert 0 <= a[1]-b[1] <= 3


def test_access_has_real_miss_recovery_and_no_context_overlap():
    m,cells=_cells(DESIGN); meta=json.load(open(DESIGN.replace(".litematic",".scan.json")))
    f=meta["features_built"]
    assert f["in_recovery_ladder"] == 1 and f["out_recovery_ladder"] == 1
    names={nbt.state_name(q).split(":")[-1] for q in m.palette[1:]}
    assert "slime_block" in names and "ladder" in names
    for path in ("Park Complete.litematic","PF Prism Well.litematic","PF Prism Rig.litematic",
                 "PF Crown Descent.litematic","PF Prism Descent.litematic",
                 "Abyss Squid.litematic","Abyss Market.litematic"):
        _,other=_cells(os.path.join(OUT,path))
        assert not cells & other, f"mouth access overlaps {path}"


def test_access_never_creates_a_surface_entrance():
    _,cells=_cells(DESIGN)
    assert max(y for _,y,_ in cells) < 170

