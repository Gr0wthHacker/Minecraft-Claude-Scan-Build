"""Surface-aware downscale by any factor (integer or not).

Why not a plain box filter: most detailed builds are a thin decorated skin
over a bulk filler (white/light-gray concrete). A majority vote over whole
cubes lets the filler win, and you get the filler block wearing the build's
shape. So geometry and material are decided separately:

  geometry  <- volume fraction of the sealed body per output cell
  material  <- rarity-weighted vote among ORIGINAL VISIBLE SURFACE blocks
               only (rare accents like eyes/beak get a boost so bulk hull
               can't outvote them), widening the window until it finds one
  interior  <- the source's own dominant hidden material
  accents   <- optional presence-based rescue for tiny focal features that
               volume rules would delete (a hanging ornament, a gold sigil)
"""
from __future__ import annotations

import numpy as np

from .. import morph, nbt
from ..schem import Model


def _cube(F: float, o: int) -> tuple[int, int]:
    return int(o * F), int(np.ceil((o + 1) * F))


def downscale(src: Model, factor: float, *, threshold: float = 0.42,
              rarity_power: float = 0.35, rarity_cap: float = 4.0,
              accents: dict[str, int] | None = None,
              collapse_partials: bool = True, mirror_x: bool = False,
              min_component: int = 6) -> Model:
    F = float(factor)
    m = src.copy().crop_to_content()
    s = m.solid()
    ids = m.ids
    names = m.names
    sy, sz, sx = s.shape
    ny, nz, nx = [int(np.ceil(d / F)) for d in (sy, sz, sx)]

    ext = morph.flood_outside(s, pad=True)
    body = s | ~(s | ext)
    surf = morph.surface(s, ext)

    # ---- geometry
    occ = np.zeros((ny, nz, nx), bool)
    for oy in range(ny):
        y0, y1 = _cube(F, oy)
        for oz in range(nz):
            z0, z1 = _cube(F, oz)
            for ox in range(nx):
                x0, x1 = _cube(F, ox)
                cube = body[y0:y1, z0:z1, x0:x1]
                occ[oy, oz, ox] = cube.size > 0 and cube.mean() >= threshold
    if mirror_x:
        occ |= occ[:, :, ::-1]
    occ |= ~(occ | morph.flood_outside(occ, pad=True))          # seal pockets
    n26 = morph.neighbor_count(occ, conn=26)
    occ = np.where(~occ & (n26 >= 21), True, occ)               # pinholes
    n26 = morph.neighbor_count(occ, conn=26)
    occ = np.where(occ & (n26 <= 3), False, occ)                # spurs
    if min_component > 1:
        occ = morph.drop_small_components(occ, min_component)

    # ---- accents by presence
    if accents:
        for aname, need in accents.items():
            aname = aname if ":" in aname else "minecraft:" + aname
            aidx = [i for i, n in enumerate(names) if n == aname]
            if not aidx:
                continue
            am = np.zeros_like(occ)
            src_mask = np.isin(ids, aidx) & surf
            for oy in range(ny):
                y0, y1 = _cube(F, oy)
                for oz in range(nz):
                    z0, z1 = _cube(F, oz)
                    for ox in range(nx):
                        x0, x1 = _cube(F, ox)
                        if src_mask[y0:y1, z0:z1, x0:x1].sum() >= need:
                            am[oy, oz, ox] = True
            occ |= am

    # ---- material vote
    u, cnt = np.unique(ids[surf], return_counts=True)
    weight = np.zeros(len(names), np.float32)
    base = (cnt.sum() / cnt.max()) ** rarity_power
    for pi, n in zip(u, cnt):
        weight[pi] = min(rarity_cap, (cnt.sum() / n) ** rarity_power / base)
    out_name = [_base_block(n) if collapse_partials else n for n in names]

    inner = ids[s & ~surf]
    filler = names[int(np.bincount(inner).argmax())] if inner.size else names[int(ids[surf][0])]

    sm = np.where(surf, ids, -1)
    ext2 = morph.flood_outside(occ, pad=True)
    osurf = morph.surface(occ, ext2)
    interior = occ & ~osurf

    out = np.zeros((ny, nz, nx), np.int32)
    src_counts = np.bincount(ids[s].ravel(), minlength=len(names))
    palette: list = [nbt.block_state("minecraft:air")]
    index: dict[str, int] = {"minecraft:air": 0}

    def get(nm: str) -> int:
        if nm not in index:
            index[nm] = len(palette)
            cands = [i for i, e in enumerate(m.palette) if nbt.state_name(e) == nm]
            if cands:
                palette.append(m.palette[max(cands, key=lambda i: src_counts[i])])
            else:
                palette.append(nbt.block_state(nm))
        return index[nm]

    def vote(oy, oz, ox) -> str | None:
        for r in (0, 1, 2, 4):
            y0, y1 = int(max(0, oy - r) * F), int(np.ceil((oy + r + 1) * F))
            z0, z1 = int(max(0, oz - r) * F), int(np.ceil((oz + r + 1) * F))
            x0, x1 = int(max(0, ox - r) * F), int(np.ceil((ox + r + 1) * F))
            box = sm[y0:y1, z0:z1, x0:x1]
            hit = box[box >= 0]
            if hit.size == 0:
                continue
            if r == 0 and accents:
                for aname, need in accents.items():
                    aname = aname if ":" in aname else "minecraft:" + aname
                    if sum(1 for pi in hit.tolist() if names[pi] == aname) >= need:
                        return aname
            scores: dict[str, float] = {}
            for pi, w in zip(hit.tolist(), weight[hit].tolist()):
                scores[out_name[pi]] = scores.get(out_name[pi], 0.0) + w
            return max(scores.items(), key=lambda kv: kv[1])[0]
        return None

    for oy, oz, ox in zip(*np.where(osurf)):
        out[oy, oz, ox] = get(vote(oy, oz, ox) or filler)
    out[interior] = get(filler)

    res = Model(out, palette, src.root, src.root_name, src.region_name)
    return res


def _base_block(name: str) -> str:
    """stone_brick_stairs -> stone_bricks, oak_slab -> oak_planks, x_wall -> x."""
    for suf in ("_stairs", "_slab", "_wall"):
        if name.endswith(suf):
            b = name[: -len(suf)]
            if b.endswith("_brick") or b.endswith("_tile"):
                return b + "s"
            woods = ("oak", "spruce", "birch", "jungle", "acacia", "dark_oak", "mangrove",
                     "cherry", "pale_oak", "bamboo", "crimson", "warped")
            if b.split(":")[-1] in woods:
                return b + "_planks"
            return b
    return name
