"""Small, state-guarded landscape repairs applied before park assembly.

The source owner and original state are mandatory: changed neighbouring builds
must be reviewed instead of silently receiving an old coordinate-based edit.
"""
import json
from pathlib import Path
from mcbuild import nbt

REPAIRS = Path(__file__).resolve().parents[1] / 'configs/park_dressing_repairs.json'


def apply(items, path=REPAIRS):
    if not path.exists():
        return items
    owners = {item[0]: item for item in items}
    for repair in json.loads(path.read_text(encoding='utf-8')):
        name, v, u, model, plane = owners[repair['owner']]
        wx, wy, wz = repair['world']
        x, y, z = wx - 97500 - v, wy - (203 - plane), wz - 80300 - u
        if not (0 <= x < model.ids.shape[2] and 0 <= y < model.ids.shape[0]
                and 0 <= z < model.ids.shape[1]):
            raise ValueError(f'dressing repair outside {name}: {repair}')
        actual = nbt.state_key(model.palette[int(model.ids[y, z, x])])
        if json.loads(json.dumps(actual)) != repair['expected']:
            raise ValueError(f'dressing repair needs review at {repair["world"]}: {actual}')
        replacement = nbt.block_state('minecraft:' + repair['replace'])
        key = nbt.state_key(replacement)
        slot = next((i for i, p in enumerate(model.palette) if nbt.state_key(p) == key), None)
        if slot is None:
            slot = len(model.palette)
            model.palette.append(replacement)
        model.ids[y, z, x] = slot
    return items
