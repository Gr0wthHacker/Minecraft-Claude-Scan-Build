"""Measure the occupied and available void around the Abyss Squid.

This produces planning evidence only.  It does not modify a schematic.
"""
from __future__ import annotations

import json
import sys
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from mcbuild import scan


OUT = ROOT / "out" / "under_squid_plan"
PARK_SHADOW = (97500, 80300, 97699, 80899)
WELL = (97590, 80815, 56)
WHALE_RESERVATION = (97525, 108, 80318, 97660, 172, 80462)


def solid_world(item, ymax=None):
    ys, zs, xs = np.nonzero(item.model.ids)
    x = xs.astype(np.int32) + item.origin[0]
    y = ys.astype(np.int32) + item.origin[1]
    z = zs.astype(np.int32) + item.origin[2]
    if ymax is not None:
        keep = y <= ymax
        x, y, z = x[keep], y[keep], z[keep]
    return set(zip(x.tolist(), y.tolist(), z.tolist()))


def bounds(cells):
    if not cells:
        return None
    return {
        "x": [min(p[0] for p in cells), max(p[0] for p in cells)],
        "y": [min(p[1] for p in cells), max(p[1] for p in cells)],
        "z": [min(p[2] for p in cells), max(p[2] for p in cells)],
        "blocks": len(cells),
    }


def components(cells):
    unseen = set(cells)
    found = []
    while unseen:
        seed = unseen.pop()
        q = deque([seed])
        comp = {seed}
        while q:
            x, y, z = q.popleft()
            for n in ((x + 1, y, z), (x - 1, y, z), (x, y + 1, z),
                      (x, y - 1, z), (x, y, z + 1), (x, y, z - 1)):
                if n in unseen:
                    unseen.remove(n)
                    comp.add(n)
                    q.append(n)
        found.append(comp)
    return sorted(found, key=len, reverse=True)


def box_cells(box):
    x0, y0, z0, x1, y1, z1 = box
    return ((x, y, z) for x in range(x0, x1 + 1)
            for y in range(y0, y1 + 1) for z in range(z0, z1 + 1))


def analyse_box(box, occupied):
    x0, y0, z0, x1, y1, z1 = box
    clashes = [p for p in box_cells(box) if p in occupied]
    wx, wz, wr = WELL
    dx = 0 if x0 <= wx <= x1 else min(abs(wx - x0), abs(wx - x1))
    dz = 0 if z0 <= wz <= z1 else min(abs(wz - z0), abs(wz - z1))
    nearest_well = (dx * dx + dz * dz) ** 0.5
    return {
        "box": list(box),
        "size": [x1 - x0 + 1, y1 - y0 + 1, z1 - z0 + 1],
        "volume": (x1 - x0 + 1) * (y1 - y0 + 1) * (z1 - z0 + 1),
        "occupied_cells": len(clashes),
        "occupied_bounds": bounds(clashes),
        "nearest_horizontal_distance_to_well_axis": round(nearest_well, 1),
        "clears_well_keepout": nearest_well > wr,
    }


def diagram(park_deep, squid_cells, market_cells):
    """Draw measured top and long-section diagrams in the shared world frame."""
    image = Image.new("RGB", (1240, 980), (13, 17, 25))
    d = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    left, top, width, height = 70, 70, 420, 780
    sx = width / 200
    sz = height / 600

    def tx(x): return left + int((x - 97500) * sx)
    def tz(z): return top + int((z - 80300) * sz)

    d.text((left, 28), "TOP — X/V across, Z/U down", fill=(235, 240, 246), font=font)
    d.rectangle((left, top, left + width, top + height), outline=(95, 108, 126), width=2)
    for cells, colour in ((park_deep, (78, 84, 96)), (squid_cells, (145, 42, 52)),
                          (market_cells, (198, 124, 63))):
        for x, _, z in {(x, 0, z) for x, _, z in cells}:
            d.point((tx(x), tz(z)), fill=colour)
    x0, y0, z0, x1, y1, z1 = WHALE_RESERVATION
    d.rectangle((tx(x0), tz(z0), tx(x1), tz(z1)), outline=(132, 214, 225), width=3)
    wx, wz, wr = WELL
    d.ellipse((tx(wx - wr), tz(wz - wr), tx(wx + wr), tz(wz + wr)),
              outline=(231, 196, 86), width=2)
    # Measured route-to-mouth connection is an interface to solve, not approved geometry.
    d.line((tx(97594), tz(80782), tx(97600), tz(80713)), fill=(218, 111, 218), width=3)
    d.ellipse((tx(97600) - 4, tz(80713) - 4, tx(97600) + 4, tz(80713) + 4),
              fill=(255, 255, 255))

    sl, st, sw, sh = 585, 70, 580, 780
    sy = sh / 220
    szz = sw / 600
    def lz(z): return sl + int((z - 80300) * szz)
    def ly(y): return st + sh - int((y - 90) * sy)
    d.text((sl, 28), "LONG SECTION — Z/U across, Y up", fill=(235, 240, 246), font=font)
    d.rectangle((sl, st, sl + sw, st + sh), outline=(95, 108, 126), width=2)
    for cells, colour in ((park_deep, (78, 84, 96)), (squid_cells, (145, 42, 52)),
                          (market_cells, (198, 124, 63))):
        for _, y, z in {(0, y, z) for _, y, z in cells}:
            d.point((lz(z), ly(y)), fill=colour)
    d.rectangle((lz(z0), ly(y1), lz(z1), ly(y0)), outline=(132, 214, 225), width=3)
    d.line((lz(80782), ly(132), lz(80713), ly(146)), fill=(218, 111, 218), width=3)

    labels = [
        ((520, 880), (145, 42, 52), "Abyss Squid — existing solid"),
        ((520, 902), (198, 124, 63), "Market fit-out — spatial reference; surface shaft retired"),
        ((520, 924), (132, 214, 225), "Reserved whale volume — entirely clear in measured artifacts"),
        ((520, 946), (218, 111, 218), "Parkour-to-mouth interface — requires greybox and jump proof"),
    ]
    for (x, y), colour, label in labels:
        d.rectangle((x, y, x + 14, y + 14), fill=colour)
        d.text((x + 22, y + 2), label, fill=(225, 231, 238), font=font)
    image.save(OUT / "measured_plan.png")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    park = scan.load(str(ROOT / "out" / "Park Complete.litematic"))
    squid = scan.load(str(ROOT / "out" / "Abyss Squid.litematic"))
    market = scan.load(str(ROOT / "out" / "Abyss Market.litematic"))
    park_deep = solid_world(park, 195)
    squid_cells = solid_world(squid)
    market_cells = solid_world(market)
    occupied = park_deep | squid_cells | market_cells
    whale_x0, whale_y0, whale_z0, whale_x1, whale_y1, whale_z1 = WHALE_RESERVATION
    overhead = [p for p in park_deep if whale_x0 <= p[0] <= whale_x1
                and whale_z0 <= p[2] <= whale_z1 and p[1] > whale_y1]

    comps = components(park_deep)
    large_components = [bounds(c) for c in comps if len(c) >= 8]
    bands = []
    for z0 in range(PARK_SHADOW[1], PARK_SHADOW[3] + 1, 25):
        z1 = min(z0 + 24, PARK_SHADOW[3])
        cells = [p for p in occupied if z0 <= p[2] <= z1]
        bands.append({"z": [z0, z1], "occupied": len(cells), "bounds": bounds(cells)})

    # These are reservation volumes, not proposed solid shapes.  A future animal
    # must fit inside one and is still generated against the exact occupied mask.
    candidates = {
        "A_whale_centered": (97535, 104, 80318, 97664, 177, 80462),
        "B_whale_west": (97505, 104, 80318, 97629, 177, 80462),
        "C_whale_east": (97570, 104, 80318, 97694, 177, 80462),
        "D_skeleton_backdrop": (97520, 112, 80322, 97679, 175, 80455),
    }
    report = {
        "coordinate_system": "world XYZ; park local V=X-97500, U=Z-80300",
        "park_shadow": [PARK_SHADOW[0], PARK_SHADOW[1], PARK_SHADOW[2], PARK_SHADOW[3]],
        "park_complete": bounds(solid_world(park)),
        "park_below_y196": bounds(park_deep),
        "park_below_y196_components_ge8": large_components,
        "squid": bounds(squid_cells),
        "market": bounds(market_cells),
        "well_keepout": {"axis_xz": [WELL[0], WELL[1]], "radius": WELL[2]},
        "distance": {
            "squid_rear_to_park_north_edge": min(p[2] for p in squid_cells) - PARK_SHADOW[1],
            "whale_reservation_to_squid_edge": min(p[2] for p in squid_cells) - whale_z1,
            "clear_z_cells_between_whale_and_squid": min(p[2] for p in squid_cells) - whale_z1 - 1,
            "whale_reservation_to_nearest_overhead_park_cell":
                min(p[1] for p in overhead) - whale_y1 if overhead else None,
            "clear_y_cells_below_overhead_park":
                min(p[1] for p in overhead) - whale_y1 - 1 if overhead else None,
        },
        "z_bands": bands,
        "recommended_whale_reservation": analyse_box(WHALE_RESERVATION, occupied),
        "candidate_reservations": {k: analyse_box(v, occupied) for k, v in candidates.items()},
    }
    (OUT / "measurements.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    diagram(park_deep, squid_cells, market_cells)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
