"""Up to five accounts building at once, out of ONE shared schematics folder.

    python -m mcbuild fleet --assign casino          # split an approved plan across the alts
    python -m mcbuild fleet                          # who has what, and what is still unclaimed
    python -m mcbuild fleet --release Enroniti3      # hand a stalled account's work back

Jack runs up to five alts, which he has confirmed is what the server allows, and they all read the
same schematics directory on one machine. **That simplification removes the whole problem this file
would otherwise be about.** There is no per-account profile, no separate design set, no syncing:
every client already sees every design. What is left is the only genuinely hard part, which is
deciding WHO BUILDS WHAT.

**FIVE IS A CAP, NOT A DEFAULT.** It is a server rule, so it is enforced here rather than written
in a comment, and `MAX_ACCOUNTS` is checked on every assignment. A tool that quietly allowed a
sixth would be a tool that got the account banned.

**AND TWO ACCOUNTS MUST NEVER SHARE A DESIGN.** Not because the schematics collide - they cannot,
they are the same file - but because two printers placing into the same cells fight: each sees the
other's block as "already built" or as a deviation, and the loop's whole feedback signal becomes
noise. The unit of assignment is therefore a DESIGN, claimed exclusively, with a lease.

**A LEASE, BECAUSE AN ALT CAN DIE.** A client crashes, a session drops, someone logs out mid-build.
A claim that never expires strands a design for ever; a claim with no expiry at all lets two
accounts pick it up the moment one of them is slow. `LEASE_MINUTES` is how long a claim survives
without a heartbeat, and `sweep()` is what hands the work back - the same reasoning as the chest
cooling-off in the build loop, which had to expire for exactly the same reason.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import pathlib

MAX_ACCOUNTS = 5                 # skyblock.net's rule, enforced rather than remembered
LEASE_MINUTES = 15
FILE = "fleet.json"


def path(schem_dir: str | None = None) -> str:
    from .profile import load as load_profile
    return os.path.join(schem_dir or load_profile()["schem_dir"], FILE)


def _now() -> _dt.datetime:
    return _dt.datetime.now()


def _key(island: str | None, design: str) -> str:
    """A claim is keyed by ISLAND AND DESIGN.

    Two alts can be building designs of the same name on two different islands, and the moment
    that is true a bare design name is ambiguous - the claim would be handed to whichever asked
    first and the other account would be told its own work was taken. The island comes from the
    design's own sidecar, so nothing has to be told where it is.
    """
    return f"{island}/{design}" if island else design


def load(schem_dir: str | None = None) -> dict:
    p = path(schem_dir)
    if not os.path.exists(p):
        return {"plan": "", "claims": {}, "done": []}
    try:
        with open(p, encoding="utf-8") as f:
            d = json.load(f) or {}
    except (OSError, ValueError):
        return {"plan": "", "claims": {}, "done": []}
    d.setdefault("claims", {})
    d.setdefault("done", [])
    return d


def save(state: dict, schem_dir: str | None = None) -> str:
    """Write atomically: temp file, then replace.

    FIVE CLIENTS SHARE THIS FILE. A plain open-write leaves a window where the file on disk is
    truncated, and a client that reads in that window sees an empty fleet and cheerfully claims
    a design somebody else is already building. `os.replace` is atomic on Windows and POSIX, so a
    reader sees either the old file or the new one and never a half-written one.

    THIS DOES NOT MAKE READ-MODIFY-WRITE ATOMIC, and pretending otherwise would be worse than the
    bug: two clients that both read, then both write, still lose one of the two changes. What
    saves it in practice is that claims are near-idempotent and heartbeats repeat - a lost
    heartbeat is retried a minute later, and a lost claim is noticed by the next `report`. A real
    lock is the fix if this ever assigns anything that cannot be repeated.
    """
    p = path(schem_dir)
    pathlib.Path(p).parent.mkdir(parents=True, exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=1)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, p)
    return p


def sweep(state: dict) -> list:
    """Drop claims whose lease has run out. Returns the designs handed back.

    UNLOADED IS NOT ABSENT, and neither is quiet: an account that has not checked in may be
    mid-flight across the island. The lease is generous for that reason - it exists to recover from
    a dead client, not to punish a slow one.
    """
    freed = []
    for design, claim in list(state["claims"].items()):
        try:
            seen = _dt.datetime.fromisoformat(claim.get("seen", claim.get("at", "")))
        except ValueError:
            continue
        if (_now() - seen).total_seconds() > LEASE_MINUTES * 60:
            freed.append(design)
            state["claims"].pop(design)
    return freed


def assign(designs: list, accounts: list, schem_dir: str | None = None,
           island: str | None = None, islands_of: dict | None = None) -> dict:
    """Hand each account a share of the work. Existing live claims are respected.

    `islands_of` maps design -> island when the designs are spread over more than one; `island`
    forces them all onto one. Neither is required, and with neither the behaviour is exactly what
    it was before there were two islands.
    """
    islands_of = islands_of or {}
    accounts = [a for a in accounts if a]
    if len(accounts) > MAX_ACCOUNTS:
        raise ValueError(f"{len(accounts)} accounts, and the cap is {MAX_ACCOUNTS} - "
                         f"that is a server rule, not a setting")
    if not accounts:
        raise ValueError("no accounts given")
    state = load(schem_dir)
    sweep(state)
    held = {c["account"] for c in state["claims"].values()}
    free = [d for d in designs
            if _key(island or islands_of.get(d, ""), d) not in state["claims"]
            and d not in state["done"]]
    # Round-robin over the accounts that are actually in this fleet, so an account that already
    # holds something is not handed a second design before the idle ones have one.
    order = sorted(accounts, key=lambda a: (a in held, a))
    for i, design in enumerate(free):
        acct = order[i % len(order)]
        isl = island or islands_of.get(design, "")
        state["claims"][_key(isl, design)] = {
            "account": acct, "design": design, "island": isl,
            "at": _now().isoformat(timespec="seconds"),
            "seen": _now().isoformat(timespec="seconds")}
    save(state, schem_dir)
    return state


def claim(design: str, account: str, schem_dir: str | None = None,
          island: str | None = None) -> tuple:
    """One account taking one design ON ONE ISLAND. (ok, why); refuses what somebody else holds."""
    state = load(schem_dir)
    sweep(state)
    k = _key(island, design)
    cur = state["claims"].get(k)
    if cur and cur["account"] != account:
        return False, f"{k} is held by {cur['account']}"
    state["claims"][k] = {"account": account, "design": design, "island": island or "",
                          "at": _now().isoformat(timespec="seconds"),
                          "seen": _now().isoformat(timespec="seconds")}
    save(state, schem_dir)
    return True, f"{account} holds {k}"


def heartbeat(account: str, schem_dir: str | None = None) -> int:
    """Refresh every claim this account holds. Returns how many."""
    state = load(schem_dir)
    n = 0
    for claim_ in state["claims"].values():
        if claim_["account"] == account:
            claim_["seen"] = _now().isoformat(timespec="seconds")
            n += 1
    save(state, schem_dir)
    return n


def finish(design: str, account: str, schem_dir: str | None = None) -> str:
    state = load(schem_dir)
    state["claims"].pop(design, None)
    if design not in state["done"]:
        state["done"].append(design)
    save(state, schem_dir)
    return f"{account} finished {design}"


def release(account: str, schem_dir: str | None = None) -> list:
    state = load(schem_dir)
    freed = [d for d, c in state["claims"].items() if c["account"] == account]
    for d in freed:
        state["claims"].pop(d)
    save(state, schem_dir)
    return freed


def mine(account: str, schem_dir: str | None = None, island: str | None = None) -> list:
    """What this account holds — everywhere, or on one island."""
    state = load(schem_dir)
    sweep(state)
    out = []
    for k, c in state["claims"].items():
        if c["account"] != account:
            continue
        if island is not None and c.get("island", "") != island:
            continue
        out.append(c.get("design", k))
    return out


def report(schem_dir: str | None = None) -> str:
    state = load(schem_dir)
    freed = sweep(state)
    if freed:
        save(state, schem_dir)
    lines = [f"fleet: {len(state['claims'])} design(s) claimed, {len(state['done'])} done"
             f"  (cap {MAX_ACCOUNTS} accounts, lease {LEASE_MINUTES} min)"]
    if state.get("plan"):
        lines.append(f"  plan: {state['plan']}")
    by: dict = {}
    for d, c in state["claims"].items():
        by.setdefault(c["account"], []).append((d, c.get("seen", "")))
    for acct in sorted(by):
        lines.append(f"  {acct}:")
        for d, seen in sorted(by[acct]):
            age = ""
            try:
                mins = int((_now() - _dt.datetime.fromisoformat(seen)).total_seconds() // 60)
                age = f"  (last seen {mins} min ago)" if mins else "  (just now)"
            except ValueError:
                pass
            lines.append(f"    {d}{age}")
    if freed:
        lines.append(f"  lease expired, handed back: {', '.join(freed)}")
    if state["done"]:
        lines.append("  done: " + ", ".join(state["done"][:8])
                     + (f" ...and {len(state['done']) - 8} more" if len(state["done"]) > 8 else ""))
    if not state["claims"] and not state["done"]:
        lines.append("  nothing assigned - python -m mcbuild fleet --assign <plan>")
    return "\n".join(lines)
