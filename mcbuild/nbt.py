"""Minimal big-endian NBT reader/writer (gzip-aware). No third-party deps.

Round-trips Litematica files byte-faithfully: every tag keeps its type id,
lists keep their subtype, so re-serialising a loaded file preserves schema.
"""
from __future__ import annotations

import gzip
import struct

TAG_END, TAG_BYTE, TAG_SHORT, TAG_INT, TAG_LONG = 0, 1, 2, 3, 4
TAG_FLOAT, TAG_DOUBLE, TAG_BYTE_ARRAY, TAG_STRING = 5, 6, 7, 8
TAG_LIST, TAG_COMPOUND, TAG_INT_ARRAY, TAG_LONG_ARRAY = 9, 10, 11, 12


class Tag:
    """Value plus its NBT type id (and list subtype)."""

    __slots__ = ("id", "value", "subtype")

    def __init__(self, tag_id: int, value, subtype: int | None = None):
        self.id = tag_id
        self.value = value
        self.subtype = subtype

    def __repr__(self) -> str:
        return f"Tag({self.id}, {self.value!r})"


# ------------------------------------------------------------------ helpers

def compound(**kw) -> Tag:
    return Tag(TAG_COMPOUND, dict(kw))


def string(s: str) -> Tag:
    return Tag(TAG_STRING, s)


def integer(v: int) -> Tag:
    return Tag(TAG_INT, int(v))


def long(v: int) -> Tag:
    return Tag(TAG_LONG, int(v))


def ivec(x: int, y: int, z: int) -> Tag:
    return Tag(TAG_COMPOUND, {"x": integer(x), "y": integer(y), "z": integer(z)})


def block_state(name: str, **props) -> Tag:
    """A BlockStatePalette entry. Props are stringified, sorted."""
    name = name if ":" in name else "minecraft:" + name
    val = {"Name": string(name)}
    if props:
        val["Properties"] = Tag(TAG_COMPOUND, {k: string(str(v)) for k, v in sorted(props.items())})
    return Tag(TAG_COMPOUND, val)


def state_name(entry: Tag) -> str:
    return entry.value["Name"].value


def state_props(entry: Tag) -> dict:
    p = entry.value.get("Properties")
    return {k: v.value for k, v in p.value.items()} if p else {}


def state_key(entry: Tag) -> tuple:
    return (state_name(entry), tuple(sorted(state_props(entry).items())))


# ------------------------------------------------------------------ reader

class _Reader:
    def __init__(self, data: bytes):
        self.d = data
        self.i = 0

    def _num(self, fmt: str, size: int):
        v = struct.unpack_from(fmt, self.d, self.i)[0]
        self.i += size
        return v

    def string(self) -> str:
        n = self._num(">H", 2)
        s = self.d[self.i:self.i + n].decode("utf-8", errors="replace")
        self.i += n
        return s

    def payload(self, tag_id: int) -> Tag:
        if tag_id == TAG_BYTE:
            return Tag(tag_id, self._num(">b", 1))
        if tag_id == TAG_SHORT:
            return Tag(tag_id, self._num(">h", 2))
        if tag_id == TAG_INT:
            return Tag(tag_id, self._num(">i", 4))
        if tag_id == TAG_LONG:
            return Tag(tag_id, self._num(">q", 8))
        if tag_id == TAG_FLOAT:
            return Tag(tag_id, self._num(">f", 4))
        if tag_id == TAG_DOUBLE:
            return Tag(tag_id, self._num(">d", 8))
        if tag_id == TAG_BYTE_ARRAY:
            n = self._num(">i", 4)
            vals = list(struct.unpack_from(f">{n}b", self.d, self.i)) if n else []
            self.i += n
            return Tag(tag_id, vals)
        if tag_id == TAG_STRING:
            return Tag(tag_id, self.string())
        if tag_id == TAG_LIST:
            sub = self._num(">b", 1)
            n = self._num(">i", 4)
            return Tag(tag_id, [self.payload(sub) for _ in range(n)], subtype=sub)
        if tag_id == TAG_COMPOUND:
            out = {}
            while True:
                t = self._num(">b", 1)
                if t == TAG_END:
                    break
                name = self.string()
                out[name] = self.payload(t)
            return Tag(tag_id, out)
        if tag_id == TAG_INT_ARRAY:
            n = self._num(">i", 4)
            vals = list(struct.unpack_from(f">{n}i", self.d, self.i)) if n else []
            self.i += 4 * n
            return Tag(tag_id, vals)
        if tag_id == TAG_LONG_ARRAY:
            n = self._num(">i", 4)
            vals = list(struct.unpack_from(f">{n}q", self.d, self.i)) if n else []
            self.i += 8 * n
            return Tag(tag_id, vals)
        raise ValueError(f"unknown tag id {tag_id} at offset {self.i}")


def read(path: str) -> tuple[str, Tag]:
    with open(path, "rb") as fh:
        raw = fh.read()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    r = _Reader(raw)
    tag_id = r._num(">b", 1)
    root_name = r.string()
    return root_name, r.payload(tag_id)


# ------------------------------------------------------------------ writer

class _Writer:
    def __init__(self):
        self.parts: list[bytes] = []

    def w(self, b: bytes) -> None:
        self.parts.append(b)

    def string(self, s: str) -> None:
        enc = s.encode("utf-8")
        self.w(struct.pack(">H", len(enc)))
        self.w(enc)

    def payload(self, tag: Tag) -> None:
        t, v = tag.id, tag.value
        if t == TAG_BYTE:
            self.w(struct.pack(">b", v))
        elif t == TAG_SHORT:
            self.w(struct.pack(">h", v))
        elif t == TAG_INT:
            self.w(struct.pack(">i", v))
        elif t == TAG_LONG:
            self.w(struct.pack(">q", v))
        elif t == TAG_FLOAT:
            self.w(struct.pack(">f", v))
        elif t == TAG_DOUBLE:
            self.w(struct.pack(">d", v))
        elif t == TAG_BYTE_ARRAY:
            self.w(struct.pack(">i", len(v)))
            if v:
                self.w(struct.pack(f">{len(v)}b", *v))
        elif t == TAG_STRING:
            self.string(v)
        elif t == TAG_LIST:
            sub = tag.subtype if tag.subtype is not None else (v[0].id if v else TAG_END)
            self.w(struct.pack(">b", sub))
            self.w(struct.pack(">i", len(v)))
            for item in v:
                self.payload(item)
        elif t == TAG_COMPOUND:
            for name, child in v.items():
                self.w(struct.pack(">b", child.id))
                self.string(name)
                self.payload(child)
            self.w(b"\x00")
        elif t == TAG_INT_ARRAY:
            self.w(struct.pack(">i", len(v)))
            if v:
                self.w(struct.pack(f">{len(v)}i", *v))
        elif t == TAG_LONG_ARRAY:
            self.w(struct.pack(">i", len(v)))
            if v:
                self.w(struct.pack(f">{len(v)}q", *v))
        else:
            raise ValueError(f"cannot write tag id {t}")


def write(path: str, root_name: str, root: Tag) -> None:
    w = _Writer()
    w.w(struct.pack(">b", root.id))
    w.string(root_name)
    w.payload(root)
    with open(path, "wb") as fh:
        fh.write(gzip.compress(b"".join(w.parts)))
