# chunkscan

Client-side Fabric mod (Minecraft 26.2). Dumps the chunks the server has sent you into a
Litematica schematic **with air included**, plus a JSON sidecar with the world coordinates —
so `mcbuild` (and anyone you share the file with) has exact ground truth of the island.
Sends nothing to the server; works on any multiplayer server.

## In game

```
/cscan <name> [radius]          # loaded chunks within radius (default 8), cropped to non-air bounds + 2 air margin
/cscan chunks <name> [radius]   # same, but XZ stays on the exact chunk grid
/cscan sel <name>               # capture exactly the current Litematica area selection
/cscan auto <name> <minutes>    # rescan on a timer while building   (/cscan auto off, /cscan auto)

/cscan place [design]           # add Litematica placements at each design's recorded origin (all designs if omitted)
/cscan dig <design>             # highlight the design's dig list in red for 2 min   (/cscan dig = clear)

/cscan mark <label>             # name the block you are looking at -> markers.json   (/cscan marks, /cscan unmark)

/cscan find <item>              # which container holds it: number, zone, coords, distance, direction + blue highlight
/cscan chests                   # how much is indexed
/cscan label <text>             # name the container you are looking at
```

**Placements** (`/cscan place`) read each design's `.scan.json` origin and add an enabled placement with
rotation and mirror NONE — no typing coordinates, no stale placement settings. Needs Litematica loaded;
everything else works without it.

**Containers** index themselves whenever you open one: position, block, contents, the screen title as a
label, the nearest marker as a zone, and a stable number that never changes. `/cscan find diamond` then
answers *which* container, so you never open a hundred by hand.

## From Python

```bash
python -m mcbuild scan island                 # summary + coverage warnings
python -m mcbuild scan island --info          # + audit / BOM
python -m mcbuild scan island --cut 120 64 -40 160 90 -10 --out out/tower.litematic --name-out tower
```

`--cut` takes **world coordinates** (any corner order), keeps tile entities, writes a new pair
whose `.scan.json` origin is the cut's world position.

## Build & deploy

Needs no system JDK: Gradle runs on the launcher's Java 25 runtime and provisions a JDK 25
toolchain into `~/.gradle/jdks` on first build.

```bash
cd chunkscan
export JAVA_HOME=/path/to/a/jdk-21-or-newer     # no system JDK needed; Gradle provisions its own
./gradlew build test
# then upload build/libs/chunkscan-<version>.jar through your launcher's mod manager
```

`test` writes `build/test-out/synthetic.litematic` through the real writer; then from `mctest`:
`python chunkscan/verify_synthetic.py` decodes it with `mcbuild` and compares block-for-block.

Bumping Minecraft: change `minecraft_version` / `fabric_api_version` in `gradle.properties`
(check https://fabricmc.net/develop) and the folder name in the `cp` above.

## Layout

```
src/client/java/dev/jack/chunkscan/
  ChunkScanClient   command registration (/cscan)
  ScanRunner        validate → capture → write both files
  WorldCapture      reads client chunks → Capture (bounds, palette, packed ids, tile entities)
  LitematicWriter   Litematica v7 NBT, straddling bit-pack (matches mcbuild.schem)
  SidecarWriter     <name>.scan.json
src/test/java/...   pack/bits/format tests
```
