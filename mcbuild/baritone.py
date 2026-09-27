"""Hand a design to Baritone's builder WITHOUT letting it break what is already standing.

**A LITEMATIC CANNOT EXPRESS "DON'T CARE", AND BARITONE READS AIR AS "MUST BE AIR".** Every one of
our designs is REMAINING WORK padded to `origin_lock`: a box of mostly air with the unbuilt cells in
it, where the air lies over the finished island, the friend's platform, the park's own streets.
Baritone's `BuilderProcess.valid()` treats a desired `air` state inside a region as a placement
to satisfy - `assemble()` files every world block standing under one into `breakable` - so fed one
of our files as it stands it would dig the world back to the design's air. Measured before this
existed: the four Friend Stair designs sit over **1,064 / 2,159 / 2,118 / 4,111** blocks of the
platform they are meant to hang off. Only cells OUTSIDE every sub-region are `null` to Baritone
(skipped), and ours are one region.

So the design is not changed - a `structure_void` marker would be a block Baritone tries to PLACE -
and Baritone is TOLD, with three of its own settings, read off its source rather than remembered:

    #buildSkipBlocks air        "a list of blocks to be treated as correct": every air cell is
                                correct whatever stands there, so the design becomes additive
    #buildIgnoreExisting true   "treat all non-air blocks as correct. It will only place new
                                blocks" - a wrong block stays and is /cscan check's amber, never
                                a dig
    #allowBreak false           the guarantee under the other two: nothing is broken for any
                                reason, so a dropped block cannot fall into the void

**`startAtLayer` IS SCHEMATIC-RELATIVE**, not a world Y - layer 0 is the region's bottom course -
so this prints the index of the design's lowest unbuilt course, and `layerOrder false` so it builds
bottom-up (a printer's order: every course stands on the one before it).

**A FILE NAME WITH A SPACE CANNOT BE GIVEN TO `#build`**: Baritone's argument parser splits on
spaces and reads one token as the file, so `Park Complete.litematic` is looked up as `Park`.
`--copy` writes a space-free twin beside the original (same bytes, so nothing else drifts).

The origin handed to `#build` is the sidecar's, because our writer puts every region at Position
(0,0,0): the region's min corner IS the design origin.
"""
from __future__ import annotations
import os, re, shutil
import numpy as np
from . import scan, schem
from .pipeline import DEFAULT_SCHEM_DIR

AIRY = {"air", "cave_air", "void_air"}

SETTINGS = (
    ("buildSkipBlocks", "air"),
    ("buildIgnoreExisting", "true"),
    ("allowBreak", "false"),
    ("buildInLayers", "true"),
    ("layerOrder", "false"),
)


def safe_name(file: str) -> str:
    """`Park Complete.litematic` -> `Park_Complete.litematic` - one token for Baritone's parser."""
    return re.sub(r"\s+", "_", file)


def _air_mask(m: schem.Model) -> np.ndarray:
    idx = [i for i, n in enumerate(m.names) if n.split(":")[-1] in AIRY]
    return np.isin(m.ids, idx)


def would_break(design: scan.Scan, world: scan.Scan) -> tuple[int, int]:
    """(world blocks standing under the design's AIR, design cells already matching a world block).

    The first number is what an unguarded Baritone digs; the second is built progress it would
    leave alone. Both measured in WORLD coordinates over the overlap of the two boxes."""
    d, w = design.model, world.model
    dair, wair = _air_mask(d), _air_mask(w)
    do, wo = design.origin, world.origin
    Y, Z, X = d.ids.shape
    ylo, yhi = max(0, wo[1] - do[1]), min(Y, wo[1] + w.ids.shape[0] - do[1])
    zlo, zhi = max(0, wo[2] - do[2]), min(Z, wo[2] + w.ids.shape[1] - do[2])
    xlo, xhi = max(0, wo[0] - do[0]), min(X, wo[0] + w.ids.shape[2] - do[0])
    if ylo >= yhi or zlo >= zhi or xlo >= xhi:
        return 0, 0
    dsl = (slice(ylo, yhi), slice(zlo, zhi), slice(xlo, xhi))
    wsl = (slice(do[1] - wo[1] + ylo, do[1] - wo[1] + yhi),
           slice(do[2] - wo[2] + zlo, do[2] - wo[2] + zhi),
           slice(do[0] - wo[0] + xlo, do[0] - wo[0] + xhi))
    da, wa = dair[dsl], wair[wsl]
    dig = int(np.sum(da & ~wa))
    dn, wn = np.array(list(d.names)), np.array(list(w.names))
    same = int(np.sum((~da) & (~wa) & (dn[d.ids[dsl]] == wn[w.ids[wsl]])))
    return dig, same


def brief(name: str, world: str | None = None, schem_dir: str = DEFAULT_SCHEM_DIR, copy: bool = False) -> dict:
    s = scan.load(name, schem_dir)
    m = s.model
    air = _air_mask(m)
    courses = np.where((~air).any(axis=(1, 2)))[0]
    lowest = int(courses[0]) if len(courses) else 0
    highest = int(courses[-1]) if len(courses) else 0
    file = os.path.basename(s.litematic_path)
    target = safe_name(file)
    copied = None
    if copy and target != file:
        copied = os.path.join(os.path.dirname(s.litematic_path), target)
        shutil.copyfile(s.litematic_path, copied)
    out = {
        "name": name, "file": file, "build_file": target, "copied": copied,
        "origin": s.origin, "blocks": int(np.sum(~air)),
        "lowest_layer": lowest, "highest_layer": highest, "layers": highest - lowest + 1,
        "lowest_world_y": s.origin[1] + lowest,
        "settings": list(SETTINGS) + [("startAtLayer", str(lowest))],
        "needs_copy": target != file and copied is None,
    }
    if world:
        w = scan.load(world, schem_dir)
        dig, same = would_break(s, w)
        out["would_break_unguarded"] = dig
        out["already_standing"] = same
    return out


def render(b: dict) -> str:
    x, y, z = b["origin"]
    lines = [f"{b['name']}: {b['blocks']} blocks, courses {b['lowest_layer']}..{b['highest_layer']} "
             f"of the box (world Y {b['lowest_world_y']} up)"]
    if "would_break_unguarded" in b:
        lines.append(f"  unguarded, Baritone would BREAK {b['would_break_unguarded']} world blocks under "
                     f"this design's air ({b['already_standing']} design cells already stand)")
    lines.append("  say these in chat first, in this order:")
    for k, v in b["settings"]:
        lines.append(f"    #{k} {v}")
    if b["needs_copy"]:
        lines.append(f"  the file name has a space and #build takes one token: run with --copy, "
                     f"which writes {b['build_file']}")
    elif b["copied"]:
        lines.append(f"  wrote {b['copied']}")
    lines.append(f"  then:  #build {b['build_file']} {x} {y} {z}")
    lines.append("  startAtLayer counts from the schematic's bottom course, not from world Y")
    return "\n".join(lines)
