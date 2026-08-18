"""Hollow a model to a shell, guaranteed sealed.

Lessons baked in (each cost a broken ship during development):
  * do ALL morphology on a padded array -- models cropped flush to their
    bbox otherwise misclassify boundary cells and you carve through a flank
  * exterior must be computed with the model's real context: `ground=True`
    for statues that sit on ground (so the floor is not "outside") but air
    under overhangs IS outside; `ceiling=True` for underside kits
  * keep the y0 floor when grounded
  * verify by re-flooding after the carve; if any carved cell is reachable
    from outside, the shell is broken -- fail loudly rather than ship
"""
from __future__ import annotations

import numpy as np

from .. import morph
from ..schem import Model


def hollow(m: Model, *, shell: int = 2, ground: bool = True, ceiling: bool = False,
           keep_floor: bool = True, keep_top_layers: int = 0,
           carve_only: np.ndarray | None = None) -> dict:
    """Carve interior cells deeper than `shell` from any exterior air.

    `carve_only`: optional bool mask (same shape as m.ids) restricting which
    cells may be carved -- use when the model contains foreign structure that
    must be treated as context but never modified.
    Returns stats dict; raises RuntimeError if the result is not sealed.
    """
    s = m.solid()
    P = shell + 1
    sp = np.pad(s, P, constant_values=False)
    if ground:
        sp[:P, :, :] = True
    if ceiling:
        sp[-P:, :, :] = True
    ext = morph.flood_outside(sp, pad=False)
    near = ext.copy()
    for _ in range(shell):
        near = morph.dilate(near, 1, conn=6)
    interior = sp & ~near
    if keep_floor:
        interior[:P + 1, :, :] = False
    if keep_top_layers:
        interior[-(P + keep_top_layers):, :, :] = False
    if carve_only is not None:
        allowed = np.pad(carve_only, P, constant_values=False)
        interior &= allowed
    sp2 = sp & ~interior
    ext2 = morph.flood_outside(sp2, pad=False)
    leaks = int((interior & ext2).sum())
    if leaks:
        raise RuntimeError(f"hollow would leak: {leaks} carved cells reachable from outside")
    m.ids[interior[P:-P, P:-P, P:-P]] = 0
    cav = (~sp2) & ~ext2
    return {"carved": int(interior.sum()), "cavity": int(cav.sum()),
            "blocks": int(m.solid().sum())}
