"""Resolve a species into generator parameters, by DERIVING them from its family's proportions.

    params = resolve("jaguar")          # a full quadruped param dict
    SPECIES["lion"]                     # what a species actually has to say for itself

The point: block dimensions are computed as `family proportion x target height`, not typed in. That
makes a species correct by construction - `tools/proportions.py` measures the same ratios the build
was derived from, so it has nothing to complain about - and it collapses a species from forty numbers
to about six.

It also fixes something tuning could not. Every species tuned in isolation drifted toward whatever
shape the smoothing and the block grid preferred, and the silhouette test kept catching the result:
a bear that measured as a jaguar. Nothing in a per-species dict says "a bear must sit where bears sit
relative to cats". A shared family proportion table says exactly that, once, for every member.

A species supplies:
    family    which table it inherits
    height    total height in blocks (see `tools/scale.py` for the floor below which it cannot work)
    build     the few generator settings that genuinely differ
    coat      palette and pattern - which is most of what separates species inside a family
    features  anything the family list does not already cover
"""
from __future__ import annotations

import functools
import pathlib

import yaml

DATA = pathlib.Path(__file__).resolve().parent.parent / "data/families.yaml"
SPECIES_DATA = pathlib.Path(__file__).resolve().parent.parent / "data/species.yaml"


@functools.lru_cache(maxsize=1)
def families() -> dict:
    return yaml.safe_load(DATA.read_text(encoding="utf-8")) or {}


@functools.lru_cache(maxsize=1)
def species() -> dict:
    if not SPECIES_DATA.exists():
        return {}
    return yaml.safe_load(SPECIES_DATA.read_text(encoding="utf-8")) or {}


def is_retired(name: str) -> bool:
    """A species kept as a record rather than as live work.

    Retirement is a JUDGEMENT the rubric cannot make: the cats and bears score 0.79-0.86 and were
    retired anyway, because a panel could not name them from their silhouettes. The flag exists so
    that verdict survives the next good-looking score - it is not a quality threshold and nothing
    computes it.
    """
    return bool((species().get(name) or {}).get("retired"))


def live() -> dict:
    """Species that are still live work."""
    return {k: v for k, v in species().items() if isinstance(v, dict) and not v.get("retired")}


def resolve(name: str) -> dict:
    """Full generator params for a species, derived from its family's proportions."""
    sp = species().get(name)
    if sp is None:
        raise KeyError(f"unknown species {name!r}; have {sorted(species())}")
    fam = families().get(sp["family"])
    if fam is None:
        raise KeyError(f"unknown family {sp['family']!r} for {name}")
    return derive(fam, float(sp["height"]), {**(fam.get("build") or {}), **(sp.get("build") or {})},
                  sp.get("coat") or {})


def derive(fam: dict, height: float, build: dict, coat: dict) -> dict:
    """Family proportions x height -> block dimensions.

    Everything the proportion table names is derived. The handful it does not name - head width, neck
    girth, hip drop - are family RATIOS rather than absolutes, for the same reason: they have to scale
    with the animal or a big member of the family comes out with a small member's head.
    """
    pr = fam["proportions"]
    # A family whose crown sticks up - big ears, ossicones - has a BOUNDING BOX taller than the
    # animal, and every proportion is measured against that box. The elephant came out uniformly 8%
    # under target for exactly this reason. `crown_bias` scales the parts back up to compensate.
    H = float(height) * float(build.get("crown_bias", 1.0))

    def blocks(key, lo=1):
        return max(lo, int(round(pr[key] * H)))

    withers = blocks("body depth", 2)
    head_len = blocks("head length", 3)
    head_r = max(1.0, float(build.get("head_r_ratio", 0.45)) * head_len)
    out = {
        "leg": blocks("leg (ground->belly)", 2),
        "body_len": blocks("body length", 4),
        "withers": withers,
        "hips": max(1, int(round(withers * float(build.get("hip_drop", 1.0))))),
        "body_r": max(1.0, pr["body width"] * H / 2.0),
        "leg_r": max(0.8, pr["leg width"] * H / 2.0),
        # the generator starts the neck three courses INSIDE the shoulder so there is no seam, and
        # those courses are part of the measured neck. Ask for that much less.
        "neck": max(2, blocks("neck length", 1) - 1),
        "head_len": head_len,
        "head_r": head_r,
        "neck_r0": max(1.0, head_r * float(build.get("neck_r0_ratio", 1.0))),
        "neck_r1": max(0.8, head_r * float(build.get("neck_r1_ratio", 0.9))),
    }
    # everything else the family or species set directly, minus the ratio keys that were only
    # instructions for this function
    for k, v in build.items():
        if k not in ("head_r_ratio", "neck_r0_ratio", "neck_r1_ratio", "hip_drop", "crown_bias"):
            out[k] = v
    out.update(coat)
    return out


def family_of(name: str) -> str:
    return (species().get(name) or {}).get("family", "")


def proportions(name: str) -> dict:
    """The family's proportion table - what this species SHOULD measure, as fractions of height."""
    fam = families().get(family_of(name))
    return dict(fam["proportions"]) if fam else {}


def pose_weights(name: str) -> dict:
    fam = families().get(family_of(name))
    return dict((fam or {}).get("poses") or {})


def required_features(name: str) -> list:
    fam = families().get(family_of(name)) or {}
    return list(fam.get("features") or []) + list((species().get(name) or {}).get("features") or [])
