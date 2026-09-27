"""Measure frontage approaches against the assembled park and current captures.

Run from the repository root. Output is a review packet, never a world edit.
"""
from pathlib import Path
import json
import sys

import numpy as np
import yaml
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from mcbuild import scan, render
from mcbuild.gen import park_frontage as pf


def block(s, v, y, u):
    x, h, z = 97500 + v - s.origin[0], y - s.origin[1], 80300 + u - s.origin[2]
    if not (0 <= h < s.model.ids.shape[0] and 0 <= z < s.model.ids.shape[1] and 0 <= x < s.model.ids.shape[2]):
        return "unknown"
    return s.model.palette[int(s.model.ids[h, z, x])].value['Name'].value.split(':')[-1]


def approach(s, piece, distance=16):
    """Record the ground and two player courses along the opening's inward axis."""
    f = pf._Frame(piece['at'], piece.get('facing', 'west'), (97500, 203, 80300))
    cells = []
    for d in range(distance):
        v, u, _ = f.at(0, d)
        cells.append({'v': v, 'u': u, 'floor': block(s, v, 202, u),
                      'feet': block(s, v, 203, u), 'head': block(s, v, 204, u)})
    return cells


def main():
    out = ROOT / 'out/arch_audit'
    out.mkdir(exist_ok=True)
    sources = {'schematic': scan.load(str(ROOT / 'out/Park Complete.litematic')),
               'capture': scan.load(str(ROOT / 'out/park_stitch_audit.litematic'))}
    pieces = []
    for path in sorted((ROOT / 'configs').glob('pf_front_*.yaml')):
        cfg = yaml.safe_load(path.read_text(encoding='utf-8'))
        for p in cfg['params']['pieces']:
            if p['kind'] not in ('marquee', 'portal', 'porch', 'queue'):
                continue
            pieces.append({'config': path.name, **p,
                           'approaches': {k: approach(s, p) for k, s in sources.items()}})
    (out / 'approaches.json').write_text(json.dumps(pieces, indent=2), encoding='utf-8')
    for key, s in sources.items():
        model, _ = scan.cut(s, 97500, 202, 80300, 97699, 215, 80899)
        im = Image.fromarray(render.elevation(model, 'top')).resize((800, 2400))
        draw = ImageDraw.Draw(im)
        for i, p in enumerate(pieces, 1):
            v, u = p['at']
            draw.ellipse((v*4-5, u*4-5, v*4+5, u*4+5), outline='yellow', width=2)
            draw.text((v*4+7, u*4-6), str(i), fill='yellow', stroke_width=1, stroke_fill='black')
        im.save(out / f'{key}_annotated.png')
    for i, p in enumerate(pieces, 1):
        findings = []
        for k, cells in p['approaches'].items():
            blocked = [c for c in cells if c['head'] not in ('air', 'cave_air', 'void_air')]
            findings.append(f"{k}: {len(blocked)}/16 head obstructions")
        print(i, p['name'], p['at'], '; '.join(findings))


if __name__ == '__main__':
    main()
