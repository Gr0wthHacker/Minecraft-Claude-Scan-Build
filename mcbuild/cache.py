"""Content-addressed artifact records for incremental Skyblock regeneration."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def key(config: dict, *, source_digest: str = "", dependencies=()) -> str:
    payload = {"config": config, "source": source_digest, "dependencies": sorted(dependencies)}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def impacted(previous: dict, current: dict) -> dict:
    """Return changed artifacts and their reverse dependency closure."""
    old, new = previous.get("artifacts", {}), current.get("artifacts", {})
    changed = {name for name in set(old) | set(new) if old.get(name, {}).get("key") != new.get(name, {}).get("key")}
    dirty = set(changed)
    while True:
        downstream = {name for name, value in new.items() if set(value.get("depends_on", [])) & dirty}
        if downstream <= dirty: break
        dirty |= downstream
    return {"changed": sorted(changed), "dirty": sorted(dirty),
            "reusable": sorted(set(new) - dirty)}


def load(path: str | Path) -> dict:
    path = Path(path)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"format": 1, "artifacts": {}}


def save(path: str | Path, manifest: dict) -> None:
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def artifact_paths(root: str | Path, digest: str) -> tuple[Path, Path]:
    root = Path(root)
    return root / f"{digest}.litematic", root / f"{digest}.scan.json"
