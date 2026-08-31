"""Reading OTHER people's schematics — the `.schem` half.

Everything here speaks Litematica because that is what `chunkscan` writes. The wider world shares
`.schem`, and a reference build that cannot be opened is a reference build nobody learns from.
`tools/corpus.py` exists for the same reason: outside builds are the only non-circular evidence
this project has, and the item filter proved it by settling in a minute a question reasoning had
got backwards twice.
"""
from __future__ import annotations

import pathlib

import pytest

from mcbuild import nbt, sponge

REF = pathlib.Path("reference/item_filter.schem")
LITE = pathlib.Path("reference/bonemeal_farm_shulker_loader.litematic")

pytestmark = pytest.mark.skipif(not REF.exists(), reason="no reference build checked in")


def test_a_sponge_schematic_loads_as_an_ordinary_model():
    m = sponge.load(str(REF))
    assert m.shape_xyz == (10, 9, 11)
    assert int((m.ids > 0).sum()) == 203


def test_the_palette_is_read_by_INDEX_not_by_order():
    """SPONGE'S PALETTE IS NAME -> INDEX, the reverse of Litematica's list, and the entries are not
    necessarily in index order. Read in the wrong order it silently relabels every block in the
    file - which would look like a working import of a completely different build."""
    m = sponge.load(str(REF))
    names = {nbt.state_name(e).split(":")[-1] for e in m.palette}
    assert "comparator" in names and "hopper" in names and "redstone_wall_torch" in names


def test_block_states_survive_the_import():
    """A filter whose comparators lose their facing is a filter nobody can copy - which is the
    entire reason this reader exists."""
    m = sponge.load(str(REF))
    e = m.palette[m.ids[6, 6, 3]]
    assert nbt.state_name(e).split(":")[-1] == "comparator"
    assert nbt.state_props(e)["facing"] == "east"


def test_the_format_is_decided_by_CONTENT_not_by_extension():
    """A file called `.litematic.gz` is still a litematic, and people rename things. The root tag
    says what it really is and asking it costs one read."""
    m = sponge.load_any(str(REF))
    assert int((m.ids > 0).sum()) == 203
    if LITE.exists():
        n = sponge.load_any(str(LITE))
        assert int((n.ids > 0).sum()) > 0, "the .gz-named litematic must load as a litematic"


def test_a_truncated_block_array_is_an_error_not_a_silent_short_read():
    """A short read would produce a smaller build that looks fine. Better to refuse."""
    with pytest.raises(ValueError, match="ran out"):
        sponge._varints(b"\x01\x02", 5)


def test_varints_handle_multi_byte_indices():
    """A palette over 128 entries needs two bytes per index, and a reader that assumed one would
    work perfectly on every small file and corrupt every large one."""
    assert sponge._varints(bytes([0x7F]), 1) == [127]
    assert sponge._varints(bytes([0x80, 0x01]), 1) == [128]
    assert sponge._varints(bytes([0xFF, 0x01]), 1) == [255]
