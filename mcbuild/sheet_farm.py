"""Presentation sheet for the Apothecary Farm: two isometric views, an
annotated top plan, legend, BOM and paste notes. One PNG.

    python -m mcbuild.sheet_farm out/"Apothecary Farm.litematic" out/farm-sheet.png
"""
from __future__ import annotations

import sys
from collections import Counter

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from . import palette, render, schem

FONT = "C:/Windows/Fonts/arial.ttf"
FONTB = "C:/Windows/Fonts/arialbd.ttf"
BG = (236, 232, 222)
INK = (40, 38, 34)
MUTED = (110, 104, 96)

ZONES = [  # (x0, z0, x1, z1, label)  canvas block coords (pad_north=3), inclusive
    (7, 2, 16, 6, "FORECOURT + GATE (bridge side, built 3 out)"),
    (14, 7, 16, 11, "corridor"),
    (17, 7, 27, 11, "stepped crop terrace · 2 beds x 2 rows · festoon lights"),
    (17, 12, 27, 13, "path · arbor at x18"),
    (5, 8, 14, 17, "APIARY PAVILION · 6 hives · cupola · doors east · stair down · bee overhead"),
    (15, 14, 22, 17, "meadow · bench · azalea tree · berries"),
    (23, 14, 26, 17, "cistern"),
]
CELLAR_ZONES = [
    (7, 7, 26, 10, "automated hive bank · 12 hives · observer > dust > dispenser · hoppers > chest"),
    (8, 11, 25, 11, "forage aisle (bees need it)"),
    (8, 12, 13, 12, "stair from pavilion"),
    (8, 13, 25, 15, "hall · pillars · flower beds · barrels"),
]
LEGEND = [
    ("stripped_spruce_log", "stripped spruce (frames, posts)"),
    ("spruce_planks", "spruce planks / stairs (tower, roofs)"),
    ("farmland", "farmland (moist)"),
    ("water", "water"),
    ("wheat", "wheat / carrots / potatoes / beetroot"),
    ("beehive", "beehive (6 in the pavilion, 12 automated below)"),
    ("campfire", "campfire hearth under each pavilion hive"),
    ("dispenser", "dispenser / observer / hopper (hive bank)"),
    ("oak_planks", "oak band under the eave (pavilion)"),
    ("mossy_stone_bricks", "stone brick family (cistern, channel floor)"),
    ("cobblestone_slab", "cobble / mossy / brick slabs (path)"),
    ("lantern", "lantern (20, all hanging)"),
    ("flowering_azalea", "azalea / flowering azalea"),
    ("flowering_azalea_leaves", "azalea + flowering azalea leaves (tree)"),
    ("sweet_berry_bush", "sweet berry bush"),
    ("dandelion", "flowers (bee forage)"),
    ("moss_block", "moss surface (unchanged)"),
]


def _font(size, bold=False):
    return ImageFont.truetype(FONTB if bold else FONT, size)


def top_plan(m: schem.Model, cell: int = 26, zones=None) -> Image.Image:
    zones = ZONES if zones is None else zones
    top = render.elevation(m, "top", shade=False)
    sz, sx = top.shape[:2]
    img = Image.fromarray(top).resize((sx * cell, sz * cell), Image.NEAREST).convert("RGB")
    dr = ImageDraw.Draw(img)
    for x in range(sx + 1):
        dr.line([(x * cell, 0), (x * cell, sz * cell)], fill=(0, 0, 0, 40), width=1)
    for z in range(sz + 1):
        dr.line([(0, z * cell), (sx * cell, z * cell)], fill=(0, 0, 0, 40), width=1)
    # zone boxes + labels
    f = _font(15, bold=True)
    for (x0, z0, x1, z1, label) in zones:
        box = (x0 * cell, z0 * cell, (x1 + 1) * cell, (z1 + 1) * cell)
        dr.rectangle(box, outline=(255, 255, 255), width=3)
        dr.rectangle(box, outline=(20, 20, 20), width=1)
        tw = dr.textlength(label, font=f)
        tx = box[0] + 6; ty = box[1] + 4
        dr.rectangle((tx - 3, ty - 2, tx + tw + 3, ty + 18), fill=(255, 255, 255, 230))
        dr.text((tx, ty), label, fill=INK, font=f)
    # frame with axis ticks
    pad = 28
    out = Image.new("RGB", (img.width + pad * 2, img.height + pad * 2), BG)
    out.paste(img, (pad, pad))
    d2 = ImageDraw.Draw(out)
    ft = _font(11)
    for x in range(0, sx, 2):
        d2.text((pad + x * cell + 6, 8), str(x), fill=MUTED, font=ft)
    for z in range(0, sz, 2):
        d2.text((6, pad + z * cell + 6), str(z), fill=MUTED, font=ft)
    d2.text((pad, out.height - 20), "N is up (z=0)  ·  x east  ·  each square = 1 block", fill=MUTED, font=ft)
    return out


def legend_panel(m: schem.Model, width: int) -> Image.Image:
    f = _font(15); fb = _font(17, bold=True)
    rows = len(LEGEND)
    img = Image.new("RGB", (width, 40 + rows * 26 + 20), BG)
    dr = ImageDraw.Draw(img)
    dr.text((0, 0), "Palette", fill=INK, font=fb)
    for i, (blk, label) in enumerate(LEGEND):
        y = 36 + i * 26
        dr.rectangle((0, y, 20, y + 20), fill=palette.color_of(blk), outline=INK)
        dr.text((30, y + 1), label, fill=INK, font=f)
    return img


def bom_panel(m: schem.Model, width: int) -> Image.Image:
    f = _font(14); fb = _font(17, bold=True)
    s = m.solid()
    bom = Counter(m.names[i].split(":")[-1] for i in m.ids[s].tolist())
    bom.pop("moss_block", None)                      # the surface, already there
    items = bom.most_common()
    cols = 2; per = (len(items) + cols - 1) // cols
    img = Image.new("RGB", (width, 40 + per * 22 + 10), BG)
    dr = ImageDraw.Draw(img)
    dr.text((0, 0), f"Bill of materials  ·  {sum(bom.values())} blocks, all cheap tier", fill=INK, font=fb)
    for i, (n, c) in enumerate(items):
        col, row = divmod(i, per)
        x = col * (width // cols); y = 36 + row * 22
        dr.rectangle((x, y + 3, x + 14, y + 17), fill=palette.color_of(n), outline=INK)
        dr.text((x + 22, y), f"{c:>4}  {n.replace('_', ' ')}", fill=INK, font=f)
    return img


def notes_panel(width: int) -> Image.Image:
    f = _font(15); fb = _font(17, bold=True)
    lines = [
        "Paste: build-farm-area's origin shifted DOWN 5 and NORTH 3 (schematic y=6 = moss surface, z=3 = file z=0), replace = 'with non-air'.",
        "Clear the old redstone out of the box first; then break the 2 moss blocks over the stairwell: file coords (11,1,9) and (12,1,9).",
        "Hive bank wiring: observer behind each hive watches honey_level; its pulse runs dust up onto the dispenser above the hive.",
        "Any hive filling fires ALL dispensers — load them with SHEARS only (shears fail silently on a non-full hive; bottles would eject).",
        "Hopper under each hive catches the honeycomb -> chain west -> chest at x10. Bees forage on the aisle flowers; keep the doors shut.",
        "Pavilion hives: 6 on the N/S/W faces over campfire hearths, hand-harvest. Stepped terrace: raised channel hydrates both bed rows.",
        "Grind items: 18 beehives (54 honeycomb), 12 observers + 12 dispensers (1 quartz each), 12 hoppers, 12 shears. Everything else cheap.",
    ]
    img = Image.new("RGB", (width, 40 + len(lines) * 24), BG)
    dr = ImageDraw.Draw(img)
    dr.text((0, 0), "Notes", fill=INK, font=fb)
    for i, t in enumerate(lines):
        dr.text((0, 36 + i * 24), "•  " + t, fill=INK, font=f)
    return img


def cellar_model(m: schem.Model, surface_y: int = 6) -> schem.Model:
    """Underground only, south wall removed so the hall reads from the south-east."""
    c = m.copy()
    c.ids[surface_y:] = 0
    c.ids[:, 16, :] = 0
    return c


def surface_model(m: schem.Model, surface_y: int = 6) -> schem.Model:
    c = m.copy()
    c.ids[:surface_y] = 0
    return c


def compose(m: schem.Model) -> Image.Image:
    sur = surface_model(m)
    iso_se = render.isometric(sur, scale=22)
    iso_sw = render.isometric(sur, scale=22, flip=True)
    cel = cellar_model(m)
    iso_cel = render.isometric(cel, scale=22)
    plan = top_plan(m)
    plan_cel = top_plan(cel, zones=CELLAR_ZONES)
    W = max(iso_se.width + iso_sw.width + 60, plan.width + plan_cel.width + 60, iso_cel.width + 40, 1400)
    legend = legend_panel(m, 420)
    bom = bom_panel(m, W - 420 - 80)
    notes = notes_panel(W - 40)
    ftitle = _font(34, bold=True); fsub = _font(17)
    header_h = 100
    row1_h = max(iso_se.height, iso_sw.height) + 50
    row1b_h = iso_cel.height + 50
    row2_h = max(plan.height, plan_cel.height) + 40
    row3_h = max(legend.height, bom.height) + 30
    row4_h = notes.height + 30
    H = header_h + row1_h + row1b_h + row2_h + row3_h + row4_h
    out = Image.new("RGB", (W, H), BG)
    dr = ImageDraw.Draw(out)
    dr.text((30, 22), "Apothecary Farm  ·  apiary pavilion, stepped terrace, honey hall", fill=INK, font=ftitle)
    dr.text((32, 66), f"{m.shape_xyz[0]} x {m.shape_xyz[2]} footprint · 12 up + 6 down · fits build-farm-area and its box · skyblock cheap tier only",
            fill=MUTED, font=fsub)
    y = header_h
    fl = _font(15, bold=True)
    dr.text((30, y), "View from south-east", fill=MUTED, font=fl)
    out.paste(iso_se, (30, y + 24))
    x2 = 30 + iso_se.width + 30
    dr.text((x2, y), "View from south-west", fill=MUTED, font=fl)
    out.paste(iso_sw, (x2, y + 24))
    y += row1_h
    dr.text((30, y), "Honey hall — cutaway from the south-east (surface and south wall removed)", fill=MUTED, font=fl)
    out.paste(iso_cel, (30, y + 24))
    y += row1b_h
    dr.text((30, y), "Top plan — surface", fill=MUTED, font=fl)
    out.paste(plan, (20, y + 20))
    dr.text((30 + plan.width + 30, y), "Top plan — honey hall", fill=MUTED, font=fl)
    out.paste(plan_cel, (20 + plan.width + 30, y + 20))
    y += row2_h
    out.paste(legend, (30, y))
    out.paste(bom, (30 + 420 + 40, y))
    y += row3_h
    out.paste(notes, (30, y))
    return out


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    compose(schem.load(src)).save(dst)
    print("wrote", dst)
