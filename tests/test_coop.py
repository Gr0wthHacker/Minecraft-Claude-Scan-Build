"""progress / remaining / diff / merge on synthetic captures."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from mcbuild import coop, nbt, scan, schem

OUT = "out/_test"


def _model(shape, states, cells):
    pal = [nbt.block_state("minecraft:air")] + [nbt.block_state("minecraft:" + n) for n in states]
    m = schem.Model(np.zeros(shape, np.int32), pal)
    for (x, y, z), i in cells.items():
        m.ids[y, z, x] = i
    return m


def _pair(path, m, origin, chunks=None, created="2026-01-01T00:00:00Z"):
    os.makedirs(OUT, exist_ok=True)
    meta = {"name": os.path.basename(path), "origin": dict(zip("xyz", origin)), "created": created,
            "chunks_included": chunks or []}
    scan.save_pair(path, m, meta)


def test_progress_and_remaining():
    design = _model((3, 4, 4), ["cobblestone", "stone", "lantern"], {(0, 0, 0): 1, (1, 0, 0): 1, (2, 0, 0): 2, (3, 1, 0): 3})
    _pair(f"{OUT}/d.litematic", design, (10, 100, 20))
    world = _model((3, 4, 4), ["cobblestone", "stone", "oak_planks"], {(0, 0, 0): 1, (1, 0, 0): 2, (2, 0, 0): 3})  # built, variant, wrong
    _pair(f"{OUT}/w.litematic", world, (10, 100, 20))
    p = coop.progress(f"{OUT}/d.litematic", f"{OUT}/w.litematic")
    assert (p.total, p.built, p.wrong) == (4, 2, 1)           # loose rock: cobble<->stone counts as built; planks is a deviation
    assert p.missing_by == {"lantern": 1}
    side, p2 = coop.remaining(f"{OUT}/d.litematic", f"{OUT}/w.litematic", f"{OUT}/d_rem.litematic")
    r = scan.load(f"{OUT}/d_rem.litematic")
    assert r.origin == (10, 100, 20) and int((r.model.ids > 0).sum()) == 1 and r.model.name_at(3, 1, 0) == "minecraft:lantern"
    assert json.load(open(side))["built_pct"] == 50.0


def test_diff():
    a = _model((2, 3, 3), ["stone", "vine"], {(0, 0, 0): 1, (1, 0, 0): 2})
    b = _model((2, 3, 3), ["stone", "vine", "moss_block"], {(0, 0, 0): 3, (2, 1, 2): 1})
    _pair(f"{OUT}/a.litematic", a, (0, 0, 0)); _pair(f"{OUT}/b.litematic", b, (0, 0, 0))
    d = coop.diff(f"{OUT}/a.litematic", f"{OUT}/b.litematic")
    assert d["added"] == {"stone": 1} and d["removed"] == {"vine": 1} and d["swapped"] == {("stone", "moss_block"): 1}


def test_merge_newest_wins_per_chunk():
    # chunk (0,0) = x 0..15, z 0..15. old scan has a block at (1,0,1) and (20,0,1) [chunk (1,0)]; new scan loaded only chunk (0,0)
    old = _model((2, 4, 24), ["stone"], {(1, 0, 1): 1, (20, 0, 1): 1})
    new = _model((2, 4, 16), ["stone", "moss_block"], {(2, 0, 2): 2})          # (1,0,1) is now air -> removed for real
    _pair(f"{OUT}/old.litematic", old, (0, 0, 0), chunks=[[0, 0], [1, 0]], created="2026-01-01T00:00:00Z")
    _pair(f"{OUT}/new.litematic", new, (0, 0, 0), chunks=[[0, 0]], created="2026-02-01T00:00:00Z")
    coop.merge_scans([f"{OUT}/old.litematic", f"{OUT}/new.litematic"], f"{OUT}/merged.litematic")
    m = scan.load(f"{OUT}/merged.litematic")
    assert m.origin == (0, 0, 0) and m.size == (24, 2, 4)
    assert m.model.name_at(2, 0, 2) == "minecraft:moss_block"     # from new
    assert m.model.name_at(1, 0, 1) == "minecraft:air"            # new scan is authoritative for chunk (0,0): block gone
    assert m.model.name_at(20, 0, 1) == "minecraft:stone"         # chunk (1,0) only in old: kept
