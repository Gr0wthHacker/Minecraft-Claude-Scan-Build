"""A real 3D view of a build: perspective camera, cast shadows, corner ambient occlusion.

    from mcbuild import render3d, scan
    s = scan.load("X elephant")
    img = render3d.render(s.model, render3d.orbit(s.model, yaw=215, pitch=20))

WHY THIS EXISTS, AND WHY THE ORTHOGRAPHIC VIEWS COULD NOT DO IT.

`render.elevation` and `tools/views.py` take the nearest surface along an AXIS and shade it by depth.
That is a projection, and a projection along an axis cannot show three of the four things that have
actually gone wrong with animals in this project:

  * THE AXOLOTL'S HEAD. Jack: "head on it looks like a blob." The skull was aimed 40 degrees off the
    block grid, so in game its flat face was a diagonal staircase of corners - eyes at different
    depths, the smile stepping cell by cell. An orthographic render ALONG THE BODY AXIS cannot show
    this: projecting down the diagonal de-jags it by construction. Every sheet looked right while
    the game looked wrong. A camera at an arbitrary angle sees the staircase.
  * MASS AND WEIGHT. "There is no weight anywhere: the outline is a constant-depth rectangle."
    Depth-shading fakes roundness by distance from the camera plane; it darkens a recess whether or
    not anything is occluding it. Contact shadow and corner AO are what actually say that a haunch
    stands proud of a flank.
  * "DOES IT LOOK BUILT." A voxel build reads as built because of how light breaks over its steps.
    Flat fill shaded by depth has no steps in it.

WHAT IT IS NOT. This is not Minecraft's renderer. No smooth lighting, no biome sky, no textures -
every block is a flat colour from the same DB `nearest()` picks against, so the CIRCULARITY CLAUDE.md
records is not fixed here, only narrowed: what is new is GEOMETRY and OCCLUSION, which are ground
truth about the shape whatever the colours are. Judge form, silhouette and mass with this. Do not
judge palette with it, and still look at the thing in game.

THE LIGHTING IS MINECRAFT'S, PLUS A SUN. Vanilla shades a face by which way it points and nothing
else - top 1.0, north/south 0.8, east/west 0.6, bottom 0.5 - and that fixed ladder is most of why
builds read in game at all. It is used verbatim, so a face that is flat here is flat there. On top
of it: corner AO by Minecraft's own algorithm, and a directional sun with hard cast shadows, which
vanilla does not have and which is the single most informative thing you can add when the question
is "where is the weight".
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from . import palette
from .schem import Model

# Vanilla's face brightness ladder, keyed (normal axis, sign) with axis 0=x, 1=y, 2=z. This is not a
# taste choice: it is what the game does, so it decides which faces of a build can carry a detail.
FACE_SHADE = {(1, 1): 1.00, (1, -1): 0.50,          # +y top, -y bottom
              (2, 1): 0.80, (2, -1): 0.80,          # +-z
              (0, 1): 0.60, (0, -1): 0.60}          # +-x

SUN = (-0.62, 0.72, -0.31)          # high and over the viewer's left shoulder: a raking sun
SKY = (150, 176, 214)
GROUND_RGB = (176, 172, 162)


@dataclass
class Camera:
    pos: tuple[float, float, float]
    target: tuple[float, float, float]
    fov: float = 42.0
    up: tuple[float, float, float] = (0.0, 1.0, 0.0)


def content_box(m: Model) -> tuple[np.ndarray, np.ndarray]:
    """(lo, hi) in xyz block coords of the cells that are actually solid, hi exclusive."""
    s = m.solid()
    if not s.any():
        sy, sz, sx = s.shape
        return np.zeros(3), np.array([sx, sy, sz], float)
    ys, zs, xs = np.where(s)
    lo = np.array([xs.min(), ys.min(), zs.min()], float)
    hi = np.array([xs.max() + 1, ys.max() + 1, zs.max() + 1], float)
    return lo, hi


def orbit(m: Model, yaw: float = 215.0, pitch: float = 20.0, dist: float = 1.0,
          fov: float = 42.0, look_high: float = 0.5) -> Camera:
    """Frame the whole build from a compass bearing and an elevation.

    `yaw` is the direction the CAMERA SITS in, in degrees, 0 = +z and 90 = +x, so it reads like a
    bearing walked around the model rather than like a rotation of the model. `pitch` is how far
    above the horizon the camera is lifted: 0 is a player's eye, 90 is the plan. `dist` scales the
    auto-framed distance, so 0.6 is a close look at a head and 4 is the far thumbnail.
    """
    lo, hi = content_box(m)
    centre = (lo + hi) / 2
    centre[1] = lo[1] + (hi[1] - lo[1]) * look_high
    radius = float(np.linalg.norm(hi - lo)) / 2
    back = radius / max(0.15, math.sin(math.radians(fov) / 2)) * 1.02 * dist
    ry, rp = math.radians(yaw), math.radians(pitch)
    off = np.array([math.sin(ry) * math.cos(rp), math.sin(rp), math.cos(ry) * math.cos(rp)])
    return Camera(tuple(centre + off * back), tuple(centre), fov=fov)


# ------------------------------------------------------------------------- the cast

def _rays(cam: Camera, W: int, H: int):
    p = np.array(cam.pos, np.float64)
    fwd = np.array(cam.target, np.float64) - p
    fwd /= np.linalg.norm(fwd)
    up = np.array(cam.up, np.float64)
    right = np.cross(fwd, up)
    if np.linalg.norm(right) < 1e-9:                 # looking straight down: any right will do
        right = np.cross(fwd, np.array([0.0, 0.0, 1.0]))
    right /= np.linalg.norm(right)
    cup = np.cross(right, fwd)
    th = math.tan(math.radians(cam.fov) / 2)
    nx = ((np.arange(W) + 0.5) / W * 2 - 1) * th * (W / H)
    ny = (1 - (np.arange(H) + 0.5) / H * 2) * th
    d = (fwd[None, None, :] + right[None, None, :] * nx[None, :, None]
         + cup[None, None, :] * ny[:, None, None])
    d /= np.linalg.norm(d, axis=2, keepdims=True)
    return p, d.reshape(-1, 3)


def _box_range(org: np.ndarray, dirs: np.ndarray, dims: np.ndarray):
    """Slab test against the grid box. A ray that never enters costs nothing after this."""
    hi = dims.astype(float)
    with np.errstate(divide="ignore", invalid="ignore"):
        inv = 1.0 / np.where(np.abs(dirs) < 1e-12, 1e-12, dirs)
        o = org if org.ndim == 2 else org[None, :]
        ta = (0.0 - o) * inv
        tb = (hi[None, :] - o) * inv
    lo_t = np.minimum(ta, tb)
    tmin = np.maximum(lo_t.max(axis=1), 0.0)
    tmax = np.maximum(ta, tb).min(axis=1)
    # WHICH FACE THE RAY CAME IN THROUGH. A ray whose very first voxel is solid never takes a step,
    # so without this it reports whatever axis the march was initialised with - and every surface
    # touching the grid's own bounding box then shades as an east/west face. A cropped model touches
    # that box by definition, so this was wrong for the outermost shell of every design.
    return tmin, tmax, lo_t.argmax(axis=1).astype(np.int8)


def _dda(occ: np.ndarray, org: np.ndarray, dirs: np.ndarray, dims: np.ndarray,
         t0: np.ndarray, t1: np.ndarray, max_steps: int, first_only: bool = False,
         entry_axis: np.ndarray | None = None):
    """Amanatides-Woo grid march, vectorised over rays with ACTIVE-SET COMPACTION.

    Compaction is what makes this affordable. A ray that has hit, or has left the box, is dropped
    from the working set, so the arrays shrink every step instead of every ray paying for the
    longest one. Without it a 300-step bound over 300k rays is 90M steps whatever the scene; with
    it an animal - which most rays either miss outright or hit early - costs a small fraction.

    `occ` is indexed [y, z, x]; voxel coordinates here are xyz. Returns arrays over ALL input rays.
    `first_only` skips recording WHERE, for shadow rays that only ask whether.
    """
    n = len(dirs)
    hit = np.zeros(n, bool)
    vox = np.zeros((n, 3), np.int32)
    thit = np.full(n, np.inf)
    axis = np.zeros(n, np.int8)
    sign = np.zeros(n, np.int8)

    live = np.where(t0 < t1)[0]
    if not len(live):
        return hit, vox, thit, axis, sign

    d = dirs[live]
    base = org[live] if org.ndim == 2 else np.broadcast_to(org, (len(live), 3))
    p = base + d * (t0[live][:, None] + 1e-4)
    v = np.clip(np.floor(p).astype(np.int32), 0, dims - 1)

    step = np.where(d > 0, 1, -1).astype(np.int32)
    ad = np.abs(d)
    safe = np.where(ad < 1e-12, 1e-12, ad)
    tdelta = 1.0 / safe
    bound = np.where(d > 0, v + 1, v)
    tnext = np.where(ad < 1e-12, np.inf, (bound - p) / np.where(ad < 1e-12, 1e-12, d))
    tnext = tnext + t0[live][:, None]
    tend = t1[live]
    cur_t = t0[live].copy()
    cur_ax = (np.zeros(len(live), np.int8) if entry_axis is None
              else entry_axis[live].astype(np.int8))

    for _ in range(max_steps):
        if not len(live):
            break
        solid = occ[v[:, 1], v[:, 2], v[:, 0]]
        if solid.any():
            idx = live[solid]
            hit[idx] = True
            if not first_only:
                vox[idx] = v[solid]
                thit[idx] = cur_t[solid]
                axis[idx] = cur_ax[solid]
                r = np.arange(len(live))[solid]
                sign[idx] = -step[r, cur_ax[solid]]
            keep = ~solid
            live, v, step, tdelta, tnext, tend, cur_t, cur_ax = (
                live[keep], v[keep], step[keep], tdelta[keep], tnext[keep],
                tend[keep], cur_t[keep], cur_ax[keep])
            if not len(live):
                break
        a = np.argmin(tnext, axis=1)
        r = np.arange(len(live))
        cur_t = tnext[r, a]
        cur_ax = a.astype(np.int8)
        v[r, a] += step[r, a]
        tnext[r, a] += tdelta[r, a]
        ok = ((cur_t <= tend) & (v[:, 0] >= 0) & (v[:, 0] < dims[0])
              & (v[:, 1] >= 0) & (v[:, 1] < dims[1]) & (v[:, 2] >= 0) & (v[:, 2] < dims[2]))
        if not ok.all():
            live, v, step, tdelta, tnext, tend, cur_t, cur_ax = (
                live[ok], v[ok], step[ok], tdelta[ok], tnext[ok],
                tend[ok], cur_t[ok], cur_ax[ok])
    return hit, vox, thit, axis, sign


# ------------------------------------------------------------------------- shading

def _corner_ao(occ, vox, axis, sign, hitp, dims):
    """Minecraft's own vertex AO, bilinearly blended by where in the face the ray landed.

    For each corner of the face: the two edge neighbours and the diagonal one, in the layer IN FRONT
    of the face. Two edges occluded is fully dark whatever the diagonal does - that is the game's
    rule, and it is what makes an inside corner read as a corner rather than as a smudge.

    THIS IS THE STRONGEST MASS CUE A VOXEL BUILD HAS. It is the only thing that separates a shoulder
    standing proud of a flank from a flat wall painted two colours, which is the exact failure the
    panel recorded against the jaguar: "a constant-depth rectangle from shoulder to rump".
    """
    n = len(vox)
    if not n:
        return np.zeros(0)
    a = axis.astype(np.int64)
    b, c = (a + 1) % 3, (a + 2) % 3
    r = np.arange(n)
    front = vox.copy()
    front[r, a] += sign.astype(np.int32)

    def occ_at(v):
        ok = ((v[:, 0] >= 0) & (v[:, 0] < dims[0]) & (v[:, 1] >= 0) & (v[:, 1] < dims[1])
              & (v[:, 2] >= 0) & (v[:, 2] < dims[2]))
        out = np.zeros(len(v), bool)
        vv = v[ok]
        if len(vv):
            out[ok] = occ[vv[:, 1], vv[:, 2], vv[:, 0]]
        return out

    ao = np.zeros((n, 2, 2))
    for i in (0, 1):
        for j in (0, 1):
            db, dc = (1 if i else -1), (1 if j else -1)
            s1 = front.copy(); s1[r, b] += db
            s2 = front.copy(); s2[r, c] += dc
            cn = front.copy(); cn[r, b] += db; cn[r, c] += dc
            o1, o2, oc = occ_at(s1), occ_at(s2), occ_at(cn)
            lvl = np.where(o1 & o2, 0, 3 - (o1.astype(int) + o2.astype(int) + oc.astype(int)))
            ao[:, i, j] = lvl / 3.0
    fb = hitp[r, b] - np.floor(hitp[r, b])
    fc = hitp[r, c] - np.floor(hitp[r, c])
    return (ao[:, 0, 0] * (1 - fb) * (1 - fc) + ao[:, 1, 0] * fb * (1 - fc)
            + ao[:, 0, 1] * (1 - fb) * fc + ao[:, 1, 1] * fb * fc)


def render(m: Model, cam: Camera, width: int = 640, height: int = 480, *,
           sun=SUN, shadows: bool = True, ao: bool = True, ground: bool = True,
           silhouette: bool = False, value: bool = False, bg=SKY,
           ao_strength: float = 0.62, shadow_strength: float = 0.34) -> np.ndarray:
    """One image, HxWx3 uint8."""
    ids = m.ids
    occ = m.solid()
    sy, sz, sx = ids.shape
    dims = np.array([sx, sy, sz], np.int32)

    names = m.names
    ctop = np.array([palette.color_of(n, "top") for n in names], np.float64)
    cside = np.array([palette.color_of(n, "side") for n in names], np.float64)

    org, dirs = _rays(cam, width, height)
    npix = len(dirs)
    tmin, tmax, entry = _box_range(org, dirs, dims)
    steps = int(sx + sy + sz) * 2 + 8
    hit, vox, tin, axis, sign = _dda(occ, org, dirs, dims, tmin, tmax, steps,
                                     entry_axis=entry)

    sd = np.array(sun, np.float64)
    sd /= np.linalg.norm(sd)
    col = np.tile(np.array(bg, np.float64), (npix, 1))

    # The ground plane exists so the SHADOW has somewhere to land. A voxel animal in a white void
    # has no cue for how its legs meet the floor, and "the legs read as posts at the corners" was
    # the panel's first complaint about the jaguar. The contact shadow is that cue.
    lo, _ = content_box(m)
    gy = float(lo[1])
    gdist = np.full(npix, np.inf)
    if ground:
        dy = dirs[:, 1]
        with np.errstate(divide="ignore", invalid="ignore"):
            tg = (gy - org[1]) / np.where(np.abs(dy) < 1e-12, 1e-12, dy)
        on = (dy < -1e-9) & (tg > 0) & (tg < np.where(hit, tin, np.inf))
        gdist = np.where(on, tg, np.inf)

    if silhouette:
        img = np.tile(np.array([250, 250, 250], np.float64), (npix, 1))
        img[hit] = (30, 30, 34)
        return img.reshape(height, width, 3).astype(np.uint8)

    hi = np.where(hit)[0]
    if len(hi):
        v = vox[hi]
        pid = ids[v[:, 1], v[:, 2], v[:, 0]]
        ax, sg = axis[hi], sign[hi]
        base = np.where((ax == 1)[:, None], ctop[pid], cside[pid])
        shade = np.array([FACE_SHADE[(int(a), int(s))] for a, s in zip(ax, sg)])
        hitp = org[None, :] + dirs[hi] * tin[hi][:, None]
        k = shade.copy()
        if ao:
            k = k * (1 - ao_strength + ao_strength * _corner_ao(occ, v, ax, sg, hitp, dims))
        if shadows:
            nrm = np.zeros((len(hi), 3))
            nrm[np.arange(len(hi)), ax.astype(np.int64)] = sg
            facing = (nrm @ sd) > 0.01
            oo = hitp + nrm * 1e-3
            sdirs = np.tile(sd, (len(hi), 1))
            s0, s1, _e = _box_range(oo, sdirs, dims)
            blocked = np.zeros(len(hi), bool)
            if facing.any():
                sh, *_ = _dda(occ, oo[facing], sdirs[facing], dims,
                              np.maximum(s0[facing], 1e-4), s1[facing], steps, first_only=True)
                blocked[facing] = sh
            k = k * np.where(facing & ~blocked, 1.0, 1.0 - shadow_strength)
        col[hi] = np.clip(base * k[:, None], 0, 255)

    gi = np.where(np.isfinite(gdist))[0]
    if len(gi):
        gp = org[None, :] + dirs[gi] * gdist[gi][:, None]
        gcol = np.tile(np.array(GROUND_RGB, np.float64), (len(gi), 1))
        chk = ((np.floor(gp[:, 0] / 8).astype(int) + np.floor(gp[:, 2] / 8).astype(int)) % 2) == 0
        gcol[chk] *= 0.94
        sdirs = np.tile(sd, (len(gi), 1))
        oo = gp + np.array([0.0, 1e-3, 0.0])
        s0, s1, _e = _box_range(oo, sdirs, dims)
        sh, *_ = _dda(occ, oo, sdirs, dims, np.maximum(s0, 1e-4), s1, steps, first_only=True)
        gcol *= np.where(sh, 0.58, 1.0)[:, None]
        fade = np.clip(gdist[gi] / (float(np.linalg.norm(dims)) * 2.6), 0, 1)[:, None]
        col[gi] = gcol * (1 - fade) + np.array(bg, np.float64) * fade

    img = col.reshape(height, width, 3)
    if value:
        g = img @ np.array([0.299, 0.587, 0.114])
        img = np.repeat(g[:, :, None], 3, axis=2)
    return np.clip(img, 0, 255).astype(np.uint8)
