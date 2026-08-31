"""More than one island — so alt 1 builds on its own, and alt 2 can come over and build here too.

    python -m mcbuild islands                       # what is known
    python -m mcbuild islands --add main --from out/island_now.litematic --owner Enroniti
    python -m mcbuild islands --where -24200 30000  # which island is this coordinate on

Everything in this project has assumed ONE island, because there was one: `plot.find` reads the
bedrock out of a capture, `profile.yaml` names one `origin_lock`, and `fleet.json` claimed designs
with no idea where they were. That holds right up until a second account has its own island and the
two are visited by the same tooling.

**AN ISLAND IS IDENTIFIED BY ITS BEDROCK, NOT BY WHOSE IT IS.** Every skyblock island has exactly
one bedrock block at its origin, which is already how `plot.py` finds the buildable square. So the
bedrock coordinate IS the island's identity: it is stable, it is discoverable from any capture, and
it does not care who is standing on it. Keying off the account instead would break the moment an
alt walks next door — which is the whole thing being built here.

**OWNERSHIP IS A LABEL, NOT A PERMISSION.** `owner` records whose island it is so a report can read
sensibly; it never decides who may build. Alt 2 building on alt 1's island is the case this exists
to support, and a tool that refused it would be enforcing a rule the server does not have.

The one thing that IS enforced: **a design belongs to the island its cells sit on**, so a claim,
a plot check and a build order are all scoped to that island rather than to the whole world.
"""
from __future__ import annotations

import json
import os
import pathlib

FILE = "islands.json"
# Skyblock islands sit far apart; anything within this of a bedrock is on that island. Generous,
# because the plot is 99 wide and the void between islands is much larger than the error here.
NEAR = 256


def path(schem_dir: str | None = None) -> str:
    from .profile import load as load_profile
    return os.path.join(schem_dir or load_profile()["schem_dir"], FILE)


def load(schem_dir: str | None = None) -> dict:
    p = path(schem_dir)
    if not os.path.exists(p):
        return {"islands": {}}
    try:
        with open(p, encoding="utf-8") as f:
            d = json.load(f) or {}
    except (OSError, ValueError):
        return {"islands": {}}
    d.setdefault("islands", {})
    return d


def save(state: dict, schem_dir: str | None = None) -> str:
    p = path(schem_dir)
    pathlib.Path(p).parent.mkdir(parents=True, exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=1)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, p)                     # five clients share this, as with fleet.json
    return p


def add(name: str, capture: str, owner: str = "", radius: int | None = None,
        schem_dir: str | None = None) -> dict:
    """Record an island, with its centre DISCOVERED from the capture's bedrock.

    Raises rather than guessing a centre. A registry entry with a made-up origin would send every
    plot check, every siting decision and every claim to the wrong square, and it would look right.
    """
    from . import plot as plot_mod
    pl = plot_mod.find(capture) if radius is None else plot_mod.find(capture, radius)
    state = load(schem_dir)
    state["islands"][name] = {
        "cx": pl.cx, "cz": pl.cz, "radius": pl.radius,
        "owner": owner, "capture": capture,
    }
    save(state, schem_dir)
    return state["islands"][name]


def at(x: int, z: int, schem_dir: str | None = None) -> str | None:
    """Which island this coordinate is on, or None.

    NEAREST BEDROCK WITHIN RANGE, not "inside the plot". A build on the rim, a route between two
    islands and a player in the void between them all need an answer, and "outside every plot" is
    not the same as "nowhere".
    """
    best, bestd = None, None
    for name, isl in load(schem_dir).get("islands", {}).items():
        d = max(abs(x - isl["cx"]), abs(z - isl["cz"]))
        if d <= NEAR and (bestd is None or d < bestd):
            best, bestd = name, d
    return best


def plot_of(name: str, schem_dir: str | None = None):
    """The buildable square of a named island."""
    from .plot import Plot
    isl = load(schem_dir).get("islands", {}).get(name)
    if not isl:
        return None
    return Plot(isl["cx"], isl["cz"], isl.get("radius", 49))


def owner(name: str, schem_dir: str | None = None) -> str:
    return load(schem_dir).get("islands", {}).get(name, {}).get("owner", "")


def island_of_design(design: str, schem_dir: str | None = None) -> str | None:
    """Which island a design's cells sit on, read from its own sidecar origin.

    The design says where it is; nothing has to be told. That is the same contract the sidecars
    have carried since the beginning - no sidecar, no world position.
    """
    from . import scan as scan_mod
    try:
        sc = scan_mod.load(design)
    except Exception:                                            # noqa: BLE001
        return None
    ox, _, oz = sc.origin
    sy, sz, sx = sc.model.ids.shape
    return at(ox + sx // 2, oz + sz // 2, schem_dir)


def report(schem_dir: str | None = None) -> str:
    state = load(schem_dir)
    isls = state.get("islands", {})
    if not isls:
        return ("no islands recorded yet.\n"
                "  python -m mcbuild islands --add main --from out/island_now.litematic "
                "--owner <account>\n"
                "  (the centre is DISCOVERED from the capture's bedrock, never typed)")
    lines = [f"{len(isls)} island(s):"]
    for name, i in sorted(isls.items()):
        r = i.get("radius", 49)
        lines.append(f"  {name:12s} bedrock {i['cx']} {i['cz']}  "
                     f"X {i['cx'] - r}..{i['cx'] + r} Z {i['cz'] - r}..{i['cz'] + r}"
                     + (f"  owner {i['owner']}" if i.get("owner") else ""))
    lines.append("  ownership is a LABEL, not a permission - any alt may build on any of them")
    return "\n".join(lines)
