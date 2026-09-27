"""One authoritative compatibility profile for the target Skyblock server.

**THE GATE IS ONLY AS HARD AS ITS EVIDENCE.** `mcbuild/data/server_blocks.json` says of itself:

    "authoritative": false,
    "source": "captures(...)+curated",
    "enforce": false,
    "note": "OFF by Jack's call: assume every block is usable and flag problems in game."

It holds 191 names mined out of captures, and it does not contain `deepslate_bricks`,
`blackstone` or `polished_blackstone_bricks` - three blocks four shipped designs on this island
are built from, and all three genuinely 1.19. `blocks.available()` already honours that flag;
this module used to bypass it with a hardcoded `enforce_server_blocks: True` and refuse the
build outright, so the plan compiled and then could not produce a single Prism-side artifact.

Two sources for one fact, and the wrong one winning. So the split here is explicit:

    validate_model   what is PROVEN unplaceable - empty while the registry is provisional
    advise_model     what the provisional list does not name - reported, never fatal

That is CLAUDE.md rule 12's own posture ("the audit only *reports* unavailable blocks; it does
not fail on them until a real 1.19 registry dump is supplied"). Supply a real dump with
`tools/server_blocks.py --reports <dir>` and the gate becomes hard on its own, with no code
change here.
"""
from __future__ import annotations

from . import blocks

SKYBLOCK_1_19 = {"name": "skyblock-1.19", "minecraft": "1.19", "data_version": 3120,
                 "allow_entities": False}


def enforced() -> bool:
    """True only when the block registry came from the server version's OWN dump."""
    return blocks.server_authoritative() and bool(blocks.server_block_names())


def current() -> dict:
    """The only server target used for generated artifacts unless a future profile is explicit."""
    return {**SKYBLOCK_1_19, "enforce_server_blocks": enforced()}


def _unnamed(model) -> list[str]:
    names = {name.split(":")[-1].split("[")[0] for name in model.names}
    server = blocks.server_block_names()
    if not server:
        return []
    return sorted(names - {"air", "cave_air", "void_air"} - server)


def validate_model(model) -> list[str]:
    """Return concrete target-profile violations, never silently downgrade them to advice.

    While the registry is provisional this is empty by construction: a name a curated capture
    list happens not to contain is not evidence the server cannot place it.
    """
    if not blocks.server_block_names():
        return ["target server block registry is unavailable"]
    if not enforced():
        return []
    return [f"unsupported on {SKYBLOCK_1_19['name']}: {name}" for name in _unnamed(model)]


def advise_model(model) -> list[str]:
    """Blocks the provisional registry does not name. Reported so a real problem is visible in
    game with a list to check against, and so the gate has something to become hard about."""
    if enforced():
        return []
    return [f"not in the provisional {SKYBLOCK_1_19['name']} list: {name}" for name in _unnamed(model)]
