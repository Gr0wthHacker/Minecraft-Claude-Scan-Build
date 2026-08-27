import sys; sys.path.insert(0, r"C:\Users\Jack\mctest")
import numpy as np, collections
from mcbuild import schem, scan
cap = schem.load("out/island_full.litematic"); sc = scan.load("out/island_full.scan.json")
o = sc.meta['origin']; ox,oy,oz = o['x'],o['y'],o['z']
pal=[n.split(":")[-1] for n in cap.names]; base=[p.split("[")[0] for p in pal]
ids=cap.ids
cnt = collections.Counter()
ys,zs,xs = np.nonzero(ids!=0)
for y,z,x in zip(ys,zs,xs): cnt[base[ids[y,z,x]]] += 1
print("MOTION AND SOUND already standing on the island:")
for k in ("campfire","soul_campfire","bell","note_block","water","lava","jukebox",
          "beehive","bee_nest","sculk_sensor","chain","iron_chain","lantern","soul_lantern",
          "sea_pickle","amethyst_cluster","budding_amethyst","conduit","end_rod","banner",
          "white_banner","item_frame","glow_item_frame","flower_pot","composter","cauldron",
          "bookshelf","lectern","candle","tinted_glass","glass_pane","big_dripleaf",
          "spore_blossom","glow_berries","cave_vines","pointed_dripstone","target","tripwire"):
    if cnt.get(k): print(f"   {k:<22}{cnt[k]}")
print("\nabsent entirely (candidates):", ", ".join(k for k in
   ("campfire","soul_campfire","bell","note_block","jukebox","conduit","end_rod",
    "banner","item_frame","flower_pot","bookshelf","candle","spore_blossom",
    "big_dripleaf","amethyst_cluster","budding_amethyst","sculk_sensor") if not cnt.get(k)))
print("\ntotal distinct block types standing:", len(cnt))
