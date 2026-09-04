"""Circulation first: a street grid per land, then lots into the cells it leaves.

**THIS EXISTS BECAUSE THE PARK WAS PLANNED THE OTHER WAY ROUND AND FAILED.** Lots were sized to
hit block budgets and packed until they filled their land; the routes were drawn afterwards and
had nowhere to go, so every one of the twenty-four modules had a public route running through its
own footprint. Measured on the failed plan: not one V-line in any land was clear of lots outside
the threshold band, and a boustrophedon "programme loop" swept the full 200 depth through every
building. That is what "a random building blocking the walkway" is, from the plan's own numbers.

A theme park is mostly circulation with buildings in the gaps. So the grid is laid FIRST and is
not negotiable, and a lot is a rectangle of whatever cells are left.

The depth programme is PARK_FINAL_ARCHITECTED_PLAN.md's, unchanged:

    V   0- 23  threshold / orientation      (spine at V12, frontage walk behind it)
    V  24-127  playable public floor        (the grid below lives here)
    V 128-151  exit, reward, observation
    V 152-169  concealed service
    V 170-199  protected rim and void reserve
"""
from __future__ import annotations

#: The public floor, cut into three lot bands by four streets. 3*28 + 4*5 = 104 = V24-127 exactly.
BAND_DEPTH, STREET_V = 28, 5
#: ...and into lot columns by cross-streets along the land's own length.
COL_LEN, STREET_U = 34, 6


def bands(v0: int = 24, v1: int = 127) -> list[tuple[int, int]]:
    """Lot bands across the public floor, street-first and street-last."""
    out, v = [], v0 + STREET_V
    while v + BAND_DEPTH - 1 <= v1 - STREET_V:
        out.append((v, v + BAND_DEPTH - 1))
        v += BAND_DEPTH + STREET_V
    return out


def columns(u0: int, u1: int) -> list[tuple[int, int]]:
    """Lot columns along a land, street-first and street-last."""
    out, u = [], u0 + STREET_U
    while u + COL_LEN - 1 <= u1 - STREET_U:
        out.append((u, u + COL_LEN - 1))
        u += COL_LEN + STREET_U
    return out


def cells(region: dict) -> list[dict]:
    """Every free lot cell of a land, as {v0,u0,v1,u1,row,col}."""
    _x0, z0, _x1, z1 = region["bounds"]
    out = []
    for row, (v0, v1) in enumerate(bands()):
        for col, (u0, u1) in enumerate(columns(z0, z1)):
            out.append({"v0": v0, "u0": u0, "v1": v1, "u1": u1, "row": row, "col": col})
    return out


def streets(region: dict) -> list[dict]:
    """The routes the grid guarantees: every gap between bands and between columns, plus the
    frontage walk behind the spine. These are laid before any lot and no lot may enter them."""
    _x0, z0, _x1, z1 = region["bounds"]
    band = bands()
    col = columns(z0, z1)
    out = [{"name": f"walk_{region['name']}", "kind": "path", "width": 7,
            "points": [[19, z0], [19, z1]]}]
    # cross-land avenues in every band gap
    edges = [24 + STREET_V // 2] + [b[1] + 1 + STREET_V // 2 for b in band]
    for i, v in enumerate(edges):
        out.append({"name": f"ave_{region['name']}_{i}", "kind": "path", "width": STREET_V,
                    "points": [[v, z0], [v, z1]]})
    # cross-streets in every column gap, from the spine to the last band
    deep = band[-1][1] + STREET_V
    gaps = [z0 + STREET_U // 2] + [c[1] + 1 + STREET_U // 2 for c in col]
    for i, u in enumerate(gaps):
        out.append({"name": f"st_{region['name']}_{i}", "kind": "path", "width": STREET_U - 1,
                    "points": [[12, u], [deep, u]]})
    return out


def place(region: dict, wants: list[tuple[str, int, int]]) -> dict[str, dict]:
    """Assign each module a rectangle of grid cells big enough for it.

    ``wants`` is ``[(name, depth_v, length_u), ...]``, BIGGEST FIRST - a large module that is
    sited late finds only fragments, which is how the Colour Wheel got three NO SITEs and the
    Mine Coaster ended up straddling four streets.
    """
    grid = cells(region)
    rows = max(c["row"] for c in grid) + 1
    cols = max(c["col"] for c in grid) + 1
    taken: set[tuple[int, int]] = set()
    out: dict[str, dict] = {}
    for name, want_v, want_u in sorted(wants, key=lambda w: -(w[1] * w[2])):
        placed = False
        for nr in range(1, rows + 1):
            for nc in range(1, cols + 1):
                span_v = nr * BAND_DEPTH + (nr - 1) * STREET_V
                span_u = nc * COL_LEN + (nc - 1) * STREET_U
                if span_v < want_v or span_u < want_u:
                    continue
                for r in range(rows - nr + 1):
                    for c in range(cols - nc + 1):
                        block = {(r + i, c + j) for i in range(nr) for j in range(nc)}
                        if block & taken:
                            continue
                        first = next(g for g in grid if g["row"] == r and g["col"] == c)
                        last = next(g for g in grid if g["row"] == r + nr - 1 and g["col"] == c + nc - 1)
                        taken |= block
                        out[name] = {"bounds": [first["v0"], first["u0"], last["v1"], last["u1"]],
                                     "cells": sorted(block)}
                        placed = True
                        break
                    if placed: break
                if placed: break
            if placed: break
        if not placed:
            out[name] = None
    return out
