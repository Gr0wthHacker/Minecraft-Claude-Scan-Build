"""Make a voxel body FLOW: measure how lumpy it is, then relax it until it is not.

    roughness(cells)     objective numbers for "does this look smooth" - spikes, notches, jerk
    relax(cells, ...)    cellular smoothing: fill the dents, shave the pimples, keep the silhouette

Why measure at all: "it looks lumpy" is not actionable and my eye kept passing shapes that were not
smooth. Three numbers cover it, and each names a defect you can see once you know to look:

  spikes   solid cells with few solid neighbours. Single blocks poking out of a surface. These are
           what read as "pixelly" - a limb that seems to have gravel stuck to it.
  notches  air cells nearly surrounded by solid. One-block dents. The eye reads these as damage.
  jerk     mean |second difference| of cross-section area up the body. A cone has jerk ~0; a stack of
           boxes has a spike at every step. This is the number that catches "it goes in and out".

`relax` is a 26-neighbour cellular pass: an air cell with at least `fill` solid neighbours becomes
solid, a solid cell with fewer than `keep` is removed. Run twice it turns a lofted-but-steppy shape
into a continuous one. THIN FEATURES MUST BE PROTECTED - an ossicone, an ear or a tail has few
neighbours by nature and the same rule that shaves a pimple will eat them whole.
"""
from __future__ import annotations

import numpy as np

from .. import morph


def _grid(cells) -> tuple[np.ndarray, tuple[int, int, int]]:
    """Pack a cell set into a padded boolean array, with the origin it was shifted by."""
    xs = [c[0] for c in cells]
    ys = [c[1] for c in cells]
    zs = [c[2] for c in cells]
    ox, oy, oz = min(xs) - 2, min(ys) - 2, min(zs) - 2
    a = np.zeros((max(ys) - oy + 3, max(zs) - oz + 3, max(xs) - ox + 3), dtype=bool)
    for (x, y, z) in cells:
        a[y - oy, z - oz, x - ox] = True
    return a, (ox, oy, oz)


def _unpack(a: np.ndarray, origin) -> set:
    ox, oy, oz = origin
    ys, zs, xs = np.where(a)
    return {(int(x) + ox, int(y) + oy, int(z) + oz)
            for x, y, z in zip(xs.tolist(), ys.tolist(), zs.tolist())}


def roughness(cells, *, spike_below: int = 11, notch_above: int = 18) -> dict:
    """Objective lumpiness. Lower is smoother; `jerk` is the one that catches stacked boxes."""
    a, _ = _grid(cells)
    n26 = morph.neighbor_count(a, conn=26)
    solid = a
    air = ~a
    spikes = int((solid & (n26 < spike_below)).sum())
    notches = int((air & (n26 > notch_above)).sum())
    area = [int(a[y].sum()) for y in range(a.shape[0]) if a[y].any()]
    jerk = 0.0
    if len(area) > 2:
        d2 = [abs(area[i - 1] - 2 * area[i] + area[i + 1]) for i in range(1, len(area) - 1)]
        jerk = sum(d2) / len(d2)
    # SCALE-FREE forms. The raw counts both grow with the model, so ranking variants by them quietly
    # prefers the smallest one - a sweep over girth "found" that thinner was smoother when it had only
    # found that thinner was smaller. `spike_rate` is per 1000 blocks; `jerk_rel` is the area jerk as a
    # percentage of mean cross-section, which is what "does the outline wobble" actually means.
    n_blocks = int(solid.sum())
    mean_area = (sum(area) / len(area)) if area else 1.0
    # Spikes live on the SURFACE, so the denominator has to be surface cells. Dividing by volume
    # still rewarded fattening, because surface-to-volume falls as a shape thickens - the sweep kept
    # drifting to the fattest variant and calling it the smoothest.
    n6 = morph.neighbor_count(a, conn=6)
    skin = int((solid & (n6 < 6)).sum())
    return {"blocks": n_blocks, "skin": skin, "spikes": spikes, "notches": notches,
            "jerk": round(jerk, 2), "courses": len(area),
            "spike_rate": round(100.0 * spikes / max(1, skin), 2),
            "jerk_rel": round(100.0 * jerk / max(1.0, mean_area), 2)}


def relax(cells, *, rounds: int = 2, fill: int = 15, keep: int = 8, protect=()) -> set:
    """Cellular smoothing. `protect` is never removed and never used to justify removal elsewhere.

    Order matters: fill first, then shave. Shaving first can disconnect a thin waist before the fill
    pass has had a chance to thicken it.
    """
    keepset = set(protect)
    out = set(cells)
    for _ in range(max(0, rounds)):
        a, origin = _grid(out | keepset)
        n26 = morph.neighbor_count(a, conn=26)
        grown = a | (~a & (n26 >= fill))
        n2 = morph.neighbor_count(grown, conn=26)
        kept = grown & (n2 >= keep)
        out = _unpack(kept, origin) | keepset
    return out
