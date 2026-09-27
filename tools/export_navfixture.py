"""Turn a real capture into a navigation test fixture for the Java side.

The routing tests were written against fixtures I invented — a wall with a hole in it, a tunnel, an
L-bend — and they only ever test the cases I thought of. **The island is the real test ground**: it
is where the loop actually runs, and it has the variance that hand-built worlds do not. Chests
recessed into walls, three-wide necks, a deck of slabs and stairs and hoppers, vines hanging in open
air, a plate with 25 interior holes in it, a machine room, rails.

So this exports the capture's own geometry as a solidity bitmap the Java tests can load:

    python tools/export_navfixture.py                       # newest capture -> test resources
    python tools/export_navfixture.py --capture out/island_now.litematic

The format is deliberately dumb — a short header and one bit per cell — so the Java reader is
twenty lines and cannot itself be the thing that fails.

**WHAT IT MODELS.** The client asks ``BlockState.blocksMotion()``. We do not have the client here, so
the model below is stated rather than assumed: a block blocks motion unless its registry TYPE (or its
name) is in ``PASSABLE``. It is close, not exact — a snow layer's height and a repeater's two pixels
are not knowable from the registry alone — and it is applied to BOTH sides of every test, so the
connectivity a test asserts is connectivity under the same model the route is found under. Where it
differs from the game it is biased toward calling things SOLID, which makes the router refuse a route
it could have flown rather than fly one it could not.
"""

from __future__ import annotations

import argparse
import gzip
import struct
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcbuild import blocks, scan

MAGIC = b"CSNAV1\0\0"

#: Registry TYPES whose blocks do not stop a player. See the module docstring.
PASSABLE_TYPES = {
    "air", "cave_air", "void_air", "structure_void", "light",
    # NOT fluids. `Nav.open` refuses anything with a fluid state: lava is death and `blocksMotion`
    # is false for it, and water is somewhere a flight arrives slower and lower than it meant to.
    # The fixture has to model the world the ROUTER sees or the island tests are about a different
    # island.
    # growing things
    "flower", "tall_flower", "flower_bed", "tall_grass", "dry_vegetation", "bush",
    "sapling", "mushroom", "crop", "stem", "attached_stem", "sugar_cane", "nether_wart", "cocoa",
    "hanging_roots", "roots", "sculk_vein", "glow_lichen", "multiface", "vine",
    "weeping_vines", "twisting_vines", "cave_vines", "cave_vines_plant", "pitcher_crop",
    "frogspawn", "spore_blossom", "dead_bush",
    # attachments and wiring
    "torch", "wall_torch", "redstone_torch", "redstone_wall_torch", "redstone_wire",
    "repeater", "comparator", "rail", "powered_rail", "detector_rail", "activator_rail",
    "lever", "button", "pressure_plate", "weighted_pressure_plate", "tripwire",
    "trip_wire_hook", "web", "fire", "soul_fire", "ladder", "carpet", "wool_carpet",
    "mossy_carpet", "leaf_litter", "snow_layer",
    "standing_sign", "wall_sign", "ceiling_hanging_sign", "wall_hanging_sign",
    "banner", "wall_banner", "flower_pot", "end_rod", "lightning_rod",
    "weathering_lightning_rod", "amethyst_cluster", "pointed_dripstone",
}

#: ...and a few by name, where the type is shared with something solid.
PASSABLE_NAMES = {"air", "cave_air", "void_air", "structure_void", "light"}


def blocks_motion(name: str) -> bool:
    """Our stand-in for ``BlockState.blocksMotion()``. See the module docstring."""
    short = str(name).split("[")[0].split(":")[-1]
    if short in PASSABLE_NAMES:
        return False
    try:
        return blocks.kind(short) not in PASSABLE_TYPES
    except Exception:
        return True                      # unknown block: assume it is in the way


def solidity(capture: Path) -> tuple[np.ndarray, tuple[int, int, int]]:
    """``(solid[y][z][x] as bool, world origin)`` for a capture."""
    s = scan.load(str(capture.with_suffix(".scan.json")))
    m = s.model
    # `names`, not `palette` - the palette holds NBT compounds and the property list with them.
    passable_ids = {i for i, n in enumerate(m.names) if not blocks_motion(n)}
    solid = np.ones(m.ids.shape, dtype=bool)
    for i in passable_ids:
        solid &= m.ids != i
    return solid, s.origin


def pack(solid: np.ndarray, origin: tuple[int, int, int]) -> bytes:
    """Header plus one bit per cell, in the capture's own ``[y][z][x]`` order."""
    sy, sz, sx = solid.shape
    head = MAGIC + struct.pack(">6i", origin[0], origin[1], origin[2], sx, sy, sz)
    return head + np.packbits(solid.reshape(-1)).tobytes()


def newest_capture(out: Path) -> Path:
    # `islandlow` first: it is the capture taken from INSIDE the lowland and it spans Y-64..270 —
    # the whole vertical, lowland through deck through sky bird. `island_now` starts at Y150, so a
    # fixture built from it cannot exercise the descent that actually crashed a flight.
    for name in ("islandlow.litematic", "island_now.litematic"):
        named = out / name
        if named.exists():
            return named
    scans = sorted(out.glob("*.litematic"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not scans:
        raise SystemExit("no capture in out/")
    return scans[0]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--capture", type=Path, default=None)
    ap.add_argument("--out", type=Path,
                    default=Path("chunkscan/src/test/resources/island_nav.bin.gz"))
    args = ap.parse_args()

    capture = args.capture or newest_capture(Path("out"))
    solid, origin = solidity(capture)
    sy, sz, sx = solid.shape
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(gzip.compress(pack(solid, origin), 9))

    filled = int(solid.sum())
    total = solid.size
    print(f"{capture.name}: {sx}x{sy}x{sz} at {origin}")
    print(f"  {filled:,} of {total:,} cells block motion ({100.0 * filled / total:.1f}%)")
    print(f"  -> {args.out} ({args.out.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
