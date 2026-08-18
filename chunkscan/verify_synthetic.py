"""Cross-implementation check: decode build/test-out/synthetic.litematic (written by the Java
writer) with mcbuild's reader and compare against the expected ids the test wrote.

Run from C:/Users/Jack/mctest:  python chunkscan/verify_synthetic.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from mcbuild import schem, nbt  # noqa: E402

OUT = Path(__file__).resolve().parent / "build" / "test-out"


def main() -> int:
    lit = OUT / "synthetic.litematic"
    expected = [int(x) for x in (OUT / "synthetic.ids").read_text().split()]

    m = schem.load(str(lit))
    sx, sy, sz = m.shape_xyz
    got = m.ids.ravel().tolist()  # [y, z, x] order == (y*sz+z)*sx+x
    print(f"size xyz={sx}x{sy}x{sz}  palette={m.names}")
    print(f"tile entities: {len(m.tile_entities)}")

    problems = []
    if (sx, sy, sz) != (4, 3, 5):
        problems.append(f"size mismatch {sx, sy, sz}")
    if got != expected:
        bad = [i for i, (a, b) in enumerate(zip(got, expected)) if a != b][:10]
        problems.append(f"ids differ at {bad}")
    if m.names[0] != "minecraft:air":
        problems.append("palette[0] is not air")
    if m.props_at(0, 0, 0) != {} and m.name_at(0, 0, 0) == "minecraft:air":
        problems.append("air has props")
    stairs = [i for i, n in enumerate(m.names) if n == "minecraft:oak_stairs"]
    if not stairs:
        problems.append("stairs missing from palette")
    else:
        props = m.palette[stairs[0]].value.get("Properties")
        facing = props.value["facing"].value if props else None
        if facing != "east":
            problems.append(f"stairs facing={facing!r}, expected east")
    if len(m.tile_entities) != 1:
        problems.append("expected 1 tile entity")

    _, root = nbt.read(str(lit))
    md = root.value["Metadata"].value
    print("metadata:", {k: md[k].value for k in ("Name", "Author", "TotalBlocks", "TotalVolume")})

    if problems:
        print("FAIL:", *problems, sep="\n  ")
        return 1
    print("OK — Java writer output decodes identically in mcbuild")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
