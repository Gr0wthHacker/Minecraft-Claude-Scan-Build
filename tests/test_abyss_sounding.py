from __future__ import annotations

import json, os
import numpy as np
import pytest

from mcbuild import nbt, scan, schem
from mcbuild.gen import abysssound

OUT="out"; DESIGN=os.path.join(OUT,"Abyss Sounding.litematic")
pytestmark=pytest.mark.skipif(not os.path.exists(DESIGN),reason="needs generated tail sounding")


def _cells(path):
    m=schem.load(path); s=scan.load(path.replace(".litematic",".scan.json"))
    yy,zz,xx=np.nonzero(m.ids)
    return m,{(int(x+s.origin[0]),int(y+s.origin[1]),int(z+s.origin[2])) for x,y,z in zip(xx,yy,zz)}


def test_tail_window_has_a_small_exact_excavation():
    meta=json.load(open(DESIGN.replace(".litematic",".scan.json")))
    dig={tuple(q) for q in meta["dig"]}
    assert 1 <= len(dig) <= 60
    assert all(97597<=x<=97603 and 107<=y<=114 and 80496<=z<=80505 for x,y,z in dig)
    _,squid=_cells(os.path.join(OUT,"Abyss Squid.litematic"))
    assert dig <= squid, "dig manifest contains cells that are not squid skin"


def test_every_overlap_is_an_explicit_window_cut():
    _,cells=_cells(DESIGN); meta=json.load(open(DESIGN.replace(".litematic",".scan.json")))
    dig={tuple(q) for q in meta["dig"]}
    for path in ("Park Complete.litematic","Abyss Squid.litematic","Abyss Market.litematic",
                 "Abyss Sperm Whale.litematic","Abyss Mouth Access.litematic"):
        _,other=_cells(os.path.join(OUT,path))
        assert cells & other <= dig, f"undeclared sounding overlap with {path}"


def test_sonar_frames_leave_the_whale_and_squid_separate():
    m,cells=_cells(DESIGN); meta=json.load(open(DESIGN.replace(".litematic",".scan.json")))
    assert meta["features_built"]["sound_frames"] and min(meta["features_built"]["sound_frames"]) >= 20
    names={nbt.state_name(q).split(":")[-1] for q in m.palette[1:]}
    assert {"oxidized_cut_copper","pearlescent_froglight","gray_stained_glass_pane"} <= names
    frame={q for q in cells if q[2] in set(abysssound.SOUNDING["ring_z"])}
    assert len(frame) >= 100
