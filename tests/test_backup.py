"""The backup: the four rules that separate it from a folder of hope."""
from __future__ import annotations

import json
import pathlib
import zipfile

import pytest

from mcbuild import backup


def _fake_project(tmp_path: pathlib.Path) -> pathlib.Path:
    src = tmp_path / "proj"
    (src / "sub").mkdir(parents=True)
    (src / "a.txt").write_text("a" * 4096, encoding="utf-8")
    (src / "sub" / "b.txt").write_text("b" * 4096, encoding="utf-8")
    (src / "__pycache__").mkdir()
    (src / "__pycache__" / "x.pyc").write_bytes(b"junk")
    return src


def test_it_skips_what_can_be_regenerated(tmp_path):
    src = _fake_project(tmp_path)
    z = tmp_path / "out.zip"
    n, _ = backup._zip_tree(src, z)
    names = set(zipfile.ZipFile(z).namelist())
    assert "a.txt" in names and "sub/b.txt" in names.union({s.replace("\\", "/") for s in names})
    assert not any("__pycache__" in s for s in names), "build junk went into the archive"
    assert n == 2


def test_a_backup_that_is_not_verified_is_not_a_backup(tmp_path):
    """`testzip` walks every entry's CRC. A truncated write still OPENS fine and simply lists
    fewer entries, which is why the count alone proves nothing."""
    src = _fake_project(tmp_path)
    z = tmp_path / "out.zip"
    backup._zip_tree(src, z)
    assert backup._verify_zip(z) == 2
    raw = bytearray(z.read_bytes())
    # Flip a span inside the first entry's DATA, past its local header (30 bytes + the name).
    # One byte in the middle of a tiny archive lands in a header or the central directory, where
    # it produces a different error or none at all - the CRC is what is being tested here.
    for i in range(40, 60):
        raw[i] ^= 0xFF
    z.write_bytes(bytes(raw))
    with pytest.raises(Exception):
        backup._verify_zip(z)


def test_the_destination_may_not_be_inside_what_it_copies(tmp_path, monkeypatch):
    """Point it inside the repo and every run archives the last one: the size doubles daily and
    nothing says why."""
    with pytest.raises(ValueError, match="inside"):
        backup.run(backup.ROOT / "out" / "backups")
    with pytest.raises(ValueError, match="inside"):
        backup.run(backup.ROOT)


def _stamp(root: pathlib.Path, name: str, ok: bool = True) -> pathlib.Path:
    d = root / name
    d.mkdir(parents=True)
    (d / "manifest.json").write_text(json.dumps({"ok": ok, "parts": {}}), encoding="utf-8")
    return d


def test_rotation_never_goes_below_one_and_never_drops_the_evidence(tmp_path):
    """Prune-then-write is how a full disk turns one bad night into no backups. And a FAILED
    backup is kept: it is the evidence of what went wrong."""
    for n in ("20260101-000000", "20260102-000000", "20260103-000000"):
        _stamp(tmp_path, n)
    bad = _stamp(tmp_path, "20260104-000000", ok=False)
    other = tmp_path / "somebody-elses-folder"
    other.mkdir()

    dropped = backup.prune(tmp_path, keep=1)
    assert dropped == ["20260101-000000", "20260102-000000"]
    assert (tmp_path / "20260103-000000").exists(), "the newest good one was pruned"
    assert bad.exists(), "a failed backup is evidence and must survive"
    assert other.exists(), "an unfamiliar folder is somebody else's"

    assert backup.prune(tmp_path, keep=0) == [], "keep=0 must still leave one"


def test_status_says_how_old_the_newest_one_is(tmp_path):
    assert "no backups" in backup.status(tmp_path / "nothing-here")
    _stamp(tmp_path, "20260101-000000")
    out = backup.status(tmp_path)
    assert "1 backup" in out and "OK" in out and "old" in out


def test_the_default_destination_is_outside_the_repo():
    dest = backup.default_dest().resolve()
    assert backup.ROOT.resolve() not in dest.parents and dest != backup.ROOT.resolve()
