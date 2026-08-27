import sys; sys.path.insert(0, r"C:\Users\Jack\mctest")
import numpy as np, collections
from mcbuild import schem, scan
cap = schem.load("out/island_full.litematic"); sc = scan.load("out/island_full.scan.json")
o = sc.meta['origin']; ox,oy,oz = o['x'],o['y'],o['z']
pal=[n.split(":")[-1] for n in cap.names]; base=[p.split("[")[0] for p in pal]
ids=cap.ids
def band(y0,y1):
    c=collections.Counter()
    for y in range(y0,y1+1):
        row=ids[y-oy]
        vals,counts=np.unique(row,return_counts=True)
        for v,n in zip(vals,counts):
            if v: c[base[v]]+=int(n)
    return c
deck = band(188,199)
print(f"THE DECK / INTERIOR (Y188-199): {sum(deck.values())} blocks, {len(deck)} types")
print("  structure:", ", ".join(f"{k}:{v}" for k,v in deck.most_common(10)))
FURN = ("bookshelf","lectern","flower_pot","candle","banner","item_frame","glow_item_frame",
        "painting","barrel","chest","crafting_table","furnace","anvil","cauldron","composter",
        "loom","smithing_table","stonecutter","cartography_table","fletching_table",
        "brewing_stand","enchanting_table","jukebox","note_block","bell","campfire",
        "soul_campfire","lantern","soul_lantern","torch","wall_torch","carpet","bed")
print("\n  furnishing present:")
for k in FURN:
    n=sum(v for kk,v in deck.items() if kk==k or (k=="carpet" and kk.endswith("_carpet")) or (k=="bed" and kk.endswith("_bed")))
    if n: print(f"     {k:<22}{n}")
print("  absent:", ", ".join(k for k in FURN if not any(kk==k for kk in deck)))
