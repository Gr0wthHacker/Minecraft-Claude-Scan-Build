import sys; sys.path.insert(0, r"C:\Users\Jack\mctest")
import json, math, collections
AX, AZ = -24200, 30018
night = json.load(open("out/Island Night.work.json"))["cells"]
falls = json.load(open("out/Falls.work.json"))["cells"]
print("Island Night fixtures in the descent band Y51-99:")
for x,y,z,b in sorted(night, key=lambda c:-c[1]):
    if 51 <= y <= 99:
        r = math.hypot(x-AX, z-AZ)
        print(f"   Y{y:>3}  r={r:5.1f}  {b.split('[')[0]:<18} at ({x},{z})")
print("\nFalls water sources (the head of the lower fall):")
for x,y,z,b in falls:
    if b.split('[')[0]=='water': print(f"   Y{y} ({x},{z}) r={math.hypot(x-AX,z-AZ):.1f}")
# how far does the lower fall travel and at what radius
print("\nlower fall column r from axis:", round(math.hypot(-24212-AX, 30002-AZ),1), " spans Y98..Y38")
