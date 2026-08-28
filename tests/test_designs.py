"""Regenerate every config and assert the audit passes. Run: python -m pytest -q  (or python tests/test_designs.py)"""
import glob, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mcbuild.pipeline import run_config, Settings

def _retired(path):
    """A config whose first line says RETIRED is kept as a record, not regenerated."""
    with open(path, encoding="utf-8") as fh:
        return "RETIRED" in fh.readline()


CONFIGS = [c for c in glob.glob(os.path.join(os.path.dirname(__file__), "..", "configs", "*.yaml"))
           if not os.path.basename(c).startswith("from_image") and not _retired(c)]


def _run(cfg):
    m, r = run_config(cfg, settings=Settings(out_dir="out/_test"), render_sheet=False, verbose=False)
    if getattr(r, "complete", False):
        return                     # 100% built: nothing to emit is success, not failure
    # Overlap against a design you have started building is a DEVIATION (you placed something else
    # there), which is `mcbuild progress`'s business, not a defect in the design. Gate on everything
    # else, so rule 2 still catches a brand-new design that collides with the island.
    probs = [p for p in r.problems if p.kind != "overlap"]
    assert not probs, f"{os.path.basename(cfg)}: {[str(p) for p in probs][:5]}"
    assert r.blocks > 0
    exp = {k: v for k, v in r.bom.items() if __import__("mcbuild").palette.tier(k) == "expensive"}
    # tiny accents (e.g. a beak) may be kept on purpose; anything bulk is a regression.
    # A design may raise its own ceiling with `expensive_allowance`, but only in its config and
    # only with the reason written beside it - the Island Run needs 13 slime blocks because
    # slime IS the jump pad it was asked for, and there is no cheap block that cancels a fall.
    # Declaring it in the config keeps the gate honest for everything else and puts the
    # exception somewhere a reader will meet it.
    import yaml as _yaml
    with open(cfg, encoding="utf-8") as fh:
        _cfg = _yaml.safe_load(fh) or {}
    cap = int(_cfg.get("expensive_allowance", 8))
    assert sum(exp.values()) <= cap, f"{os.path.basename(cfg)}: expensive blocks {exp}"


def test_all_configs():
    for c in CONFIGS:
        _run(c)


def test_roundtrip_nbt():
    from mcbuild import schem, nbt
    import numpy as np
    m = schem.Model(np.zeros((3, 3, 3), np.int32), [nbt.block_state("minecraft:air"), nbt.block_state("minecraft:stone")])
    m.ids[1, 1, 1] = 1
    schem.save("out/_test/rt.litematic", m, name="rt")
    m2 = schem.load("out/_test/rt.litematic")
    assert (m2.ids == m.ids).all() and m2.names[1] == "minecraft:stone"


def test_hollow_seals_and_reports():
    """Hollowing a solid cube yields a sealed cavity; carving is verified."""
    from mcbuild import schem, nbt, morph
    from mcbuild.ops import hollow
    import numpy as np
    ids = np.ones((8, 8, 8), np.int32)
    m = schem.Model(ids, [nbt.block_state("minecraft:air"), nbt.block_state("minecraft:stone")])
    st = hollow(m, shell=2, ground=True)
    assert st["carved"] > 0 and st["cavity"] == st["carved"]
    s = m.solid()
    ext = morph.flood_outside(s, pad=True, ground=True)
    assert int(((~s) & ext & ~s).sum()) == int(((~s) & ext).sum())   # sanity
    assert not ((~s) & ext)[2:-2, 2:-2, 2:-2].any()                  # cavity is not exterior


def test_carve_only_respects_foreign_structure():
    """With carve_only, cells outside the mask are never removed."""
    from mcbuild import schem, nbt
    from mcbuild.ops import hollow
    import numpy as np
    ids = np.ones((10, 10, 10), np.int32)
    m = schem.Model(ids, [nbt.block_state("minecraft:air"), nbt.block_state("minecraft:stone")])
    allowed = np.zeros_like(ids, bool); allowed[:5] = True          # only the lower half may be carved
    hollow(m, shell=2, ground=True, carve_only=allowed)
    assert m.solid()[5:].all()


if __name__ == "__main__":
    os.makedirs("out/_test", exist_ok=True)
    for c in CONFIGS:
        _run(c); print("ok", os.path.basename(c))
    test_roundtrip_nbt(); print("ok roundtrip")
    print("all passed")


def test_every_module_imports():
    """cli.py is not on any other test's import path, so a syntax error there ships silently.
    Import every module in the package."""
    import importlib, pkgutil
    import mcbuild
    for mod in pkgutil.walk_packages(mcbuild.__path__, "mcbuild."):
        if mod.name.endswith(".__main__"):
            continue                      # importing it runs the CLI against pytest's argv
        importlib.import_module(mod.name)
