"""A full, verified, rotated backup of everything this project cannot regenerate.

Three stores hold the island and only one of them is in git:

    the repo          code, configs, tests - and out/*.litematic, which git DOES track
    the schematics    what the game reads: designs, sidecars, work.json, storage.json,
                      designs.json, and the scans archive. NOT in git, 18 MB, and the only
                      copy of every capture ever taken
    the game dir      session.json and the mod's own config

Losing the middle one loses the world's history. `sync` regenerates designs from configs; it
cannot regenerate a CAPTURE, because a capture is a photograph of a world that has moved on.

Four rules, each of which is the difference between a backup and a folder of hope:

* **A BACKUP THAT IS NOT VERIFIED IS NOT A BACKUP.** Every archive is re-opened and read back
  after it is written, and the git bundle is handed to `git bundle verify`. A write that failed
  halfway still produces a valid zip file - with fewer entries in it.
* **NOTHING IS PRUNED BEFORE THE NEW ONE VERIFIES**, and the rotation never goes below one.
  Prune-then-write is how a full disk turns one bad night into no backups at all.
* **THE DESTINATION MUST BE OUTSIDE EVERYTHING IT COPIES.** Point it inside the repo and each
  run archives the last one - the size doubles every day and nothing says why.
* **HISTORY IS A BUNDLE, NOT A COPY OF `.git`.** `git bundle` is one file that `verify` can
  check and `clone` can restore from; copying `.git` byte by byte while a gc is running copies
  a torn object store.
"""
from __future__ import annotations

import datetime as _dt
import fnmatch
import json
import os
import pathlib
import shutil
import subprocess
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Regenerable, enormous, or both. Excluded from the working-tree archive by path prefix or glob.
SKIP = (
    ".git/", "__pycache__/", ".pytest_cache/", ".mypy_cache/", ".ruff_cache/",
    "chunkscan/build/", "chunkscan/.gradle/", "chunkscan/run/", "node_modules/",
    ".venv/", "venv/", "out/_test/",
)
SKIP_GLOB = ("*.pyc", "*.pyo", "*.class", "*.log")

KEEP = 7


def default_dest() -> pathlib.Path:
    """Outside the repo and outside the game dir, both of which this backs UP.

    `$MCTEST_BACKUP_DIR` overrides it - point that at OneDrive, a second drive or a NAS mount
    and the same command becomes an offsite backup with no other change.
    """
    env = os.environ.get("MCTEST_BACKUP_DIR")
    if env:
        return pathlib.Path(env)
    return pathlib.Path(os.path.expanduser("~")) / "mctest-backups"


def _skip(rel: str) -> bool:
    r = rel.replace("\\", "/")
    if any(r == s.rstrip("/") or r.startswith(s) for s in SKIP):
        return True
    return any(fnmatch.fnmatch(os.path.basename(r), g) for g in SKIP_GLOB)


def _zip_tree(src: pathlib.Path, dest_zip: pathlib.Path, skip: bool = True) -> tuple[int, int]:
    """Zip a directory tree. Returns (files, source bytes) actually written."""
    n = total = 0
    dest_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(dest_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for dirpath, dirnames, filenames in os.walk(src):
            rel_dir = os.path.relpath(dirpath, src)
            if rel_dir == ".":
                rel_dir = ""
            if skip and rel_dir and _skip(rel_dir + "/"):
                dirnames[:] = []
                continue
            for fn in filenames:
                rel = os.path.join(rel_dir, fn) if rel_dir else fn
                if skip and _skip(rel):
                    continue
                full = pathlib.Path(dirpath) / fn
                try:
                    z.write(full, rel)
                    total += full.stat().st_size
                    n += 1
                except (OSError, ValueError):
                    continue          # a file the game holds open is skipped, never fatal
    return n, total


def _verify_zip(path: pathlib.Path) -> int:
    """Re-open and read the archive back. Returns the entry count; raises if it is corrupt.

    `testzip` walks every entry's CRC, which is the point: a truncated write produces a file
    that opens fine and simply lists fewer entries.
    """
    with zipfile.ZipFile(path) as z:
        bad = z.testzip()
        if bad is not None:
            raise RuntimeError(f"{path.name}: corrupt entry {bad}")
        return len(z.namelist())


def _git(*args: str, cwd: pathlib.Path = ROOT) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True)


def _bundle(dest: pathlib.Path) -> dict:
    """Full history as one verifiable file. Reports rather than raises if this is not a git repo."""
    out = dest / "repo.bundle"
    r = _git("bundle", "create", str(out), "--all")
    if r.returncode != 0 or not out.exists():
        why = (r.stderr or "git bundle failed").strip().splitlines()
        return {"ok": False, "why": why[-1] if why else "failed"}
    v = _git("bundle", "verify", str(out))
    head = _git("rev-parse", "HEAD")
    return {
        "ok": v.returncode == 0,
        "bytes": out.stat().st_size,
        "head": head.stdout.strip(),
        "why": None if v.returncode == 0 else v.stderr.strip(),
    }


def run(dest: pathlib.Path | str | None = None, keep: int = KEEP,
        game_dir: str | None = None, schem_dir: str | None = None) -> dict:
    """Take one full backup. Returns the manifest; raises if it wrote something unusable."""
    from .profile import load as load_profile
    prof = load_profile()
    schem = pathlib.Path(schem_dir or prof["schem_dir"])
    game = pathlib.Path(game_dir or prof["game_dir"])

    root = (pathlib.Path(dest) if dest else default_dest()).resolve()
    for guarded, what in ((ROOT, "the repo"), (schem, "the schematics folder"), (game, "the game dir")):
        try:
            g = guarded.resolve()
        except OSError:
            continue
        if root == g or g in root.parents:
            raise ValueError(f"backup destination {root} is inside {what} ({g}) - it would archive "
                             f"its own archives. Set MCTEST_BACKUP_DIR somewhere else.")

    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    here = root / stamp
    here.mkdir(parents=True, exist_ok=True)

    man: dict = {"stamp": stamp, "when": _dt.datetime.now().isoformat(timespec="seconds"),
                 "root": str(ROOT), "parts": {}}

    # 1. the working tree: code, configs, tests, out/*.litematic - everything but .git and build junk
    n, b = _zip_tree(ROOT, here / "repo-tree.zip")
    man["parts"]["repo-tree.zip"] = {"files": n, "source_bytes": b,
                                     "bytes": (here / "repo-tree.zip").stat().st_size}

    # 2. full git history, as one file git itself can check
    man["parts"]["repo.bundle"] = _bundle(here)

    # 3. the schematics folder - designs, sidecars, work lists, storage.json, designs.json, scans
    if schem.exists():
        n, b = _zip_tree(schem, here / "schematics.zip", skip=False)
        man["parts"]["schematics.zip"] = {"files": n, "source_bytes": b,
                                          "bytes": (here / "schematics.zip").stat().st_size,
                                          "source": str(schem)}
    else:
        man["parts"]["schematics.zip"] = {"ok": False, "why": f"not found: {schem}"}

    # 4. the game dir. session.json, designs.json, storage.json and prices.json all live in the
    #    SCHEMATICS folder and are already in (3); what is only here is the jar that was actually
    #    running, which is what tells you later which build wrote a file.
    loose = here / "gamedir"
    loose.mkdir(exist_ok=True)
    got = []
    for pat in ("mods/chunkscan-*.jar", "config/chunkscan*.json"):
        for src in sorted(game.glob(pat)):
            try:
                shutil.copy2(src, loose / src.name)
                got.append(str(src.relative_to(game)).replace("\\", "/"))
            except OSError:
                continue
    man["parts"]["gamedir"] = {"files": got}

    # 5. VERIFY, before anything at all is pruned
    problems = []
    for name in ("repo-tree.zip", "schematics.zip"):
        p = here / name
        if not p.exists():
            continue
        try:
            man["parts"][name]["verified_entries"] = _verify_zip(p)
        except Exception as e:                                  # noqa: BLE001
            problems.append(str(e))
    if not man["parts"]["repo.bundle"].get("ok"):
        problems.append("git bundle did not verify: %s" % man["parts"]["repo.bundle"].get("why"))
    man["ok"] = not problems
    man["problems"] = problems

    (here / "manifest.json").write_text(json.dumps(man, indent=1), encoding="utf-8")

    if problems:
        raise RuntimeError("backup wrote but did NOT verify:\n  " + "\n  ".join(problems)
                           + f"\n(kept at {here} for inspection; nothing was pruned)")

    man["pruned"] = prune(root, keep)
    man["dir"] = str(here)
    return man


def prune(root: pathlib.Path, keep: int = KEEP) -> list[str]:
    """Drop the oldest VERIFIED backups past `keep`.

    Never below one, never a backup that FAILED verification (that one is evidence of what went
    wrong), and never anything it cannot read - an unfamiliar folder is somebody else's.
    """
    keep = max(1, int(keep))
    good = []
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        man = d / "manifest.json"
        if not man.exists():
            continue
        try:
            if json.loads(man.read_text(encoding="utf-8")).get("ok"):
                good.append(d)
        except Exception:                  # noqa: BLE001
            continue
    dropped = []
    for d in (good[:-keep] if len(good) > keep else []):
        shutil.rmtree(d, ignore_errors=True)
        dropped.append(d.name)
    return dropped


def status(root: pathlib.Path | str | None = None) -> str:
    """What backups exist, how big, how old - the line you read before trusting one."""
    r = pathlib.Path(root) if root else default_dest()
    if not r.exists():
        return f"no backups at {r} - run: python -m mcbuild backup"
    rows = []
    for d in sorted((p for p in r.iterdir() if p.is_dir()), reverse=True):
        man = d / "manifest.json"
        if not man.exists():
            rows.append((d.name, "?", "no manifest (half-written?)"))
            continue
        try:
            m = json.loads(man.read_text(encoding="utf-8"))
        except Exception:                  # noqa: BLE001
            rows.append((d.name, "?", "unreadable manifest"))
            continue
        size = sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
        parts = m.get("parts", {})
        files = sum(p.get("files", 0) for p in parts.values()
                    if isinstance(p, dict) and isinstance(p.get("files"), int))
        head = parts.get("repo.bundle", {}).get("head", "") or ""
        rows.append((d.name, f"{size/1e6:.0f} MB",
                     ("OK   " if m.get("ok") else "FAIL ") + f"{files} files, head {head[:8]}"))
    if not rows:
        return f"no backups at {r} - run: python -m mcbuild backup"
    w = max(len(a) for a, _, _ in rows)
    out = [f"{len(rows)} backup(s) in {r}"]
    out += [f"  {a:<{w}}  {b:>7}  {c}" for a, b, c in rows]
    try:
        age = _dt.datetime.now() - _dt.datetime.strptime(rows[0][0], "%Y%m%d-%H%M%S")
        out.append(f"  newest is {age.days}d {age.seconds // 3600}h old")
    except ValueError:
        pass
    return "\n".join(out)
