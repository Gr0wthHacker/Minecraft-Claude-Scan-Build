# chunkscan

Client-side Fabric mod (Minecraft 26.2). Dumps the chunks the server has sent you into a
Litematica schematic **with air included**, plus a JSON sidecar with the world coordinates —
so `mcbuild` (and anyone you share the file with) has exact ground truth of the island.
Sends nothing to the server; works on any multiplayer server.

## In game

```
/cscan <name> [radius]          # loaded chunks within radius (default 8) → cropped to non-air bounds + 2 air margin
/cscan chunks <name> [radius]   # same, but XZ stays on the exact chunk grid (full 16x16 cells, air and all)
```

Writes to the Litematica folder (`<gameDir>/schematics/`):

- `<name>.litematic` — Litematica v7, one region at (0,0,0), palette[0] = air, tile entities and entities (item frames, armor stands, paintings…) included
- `scans/<name>_<yyyyMMdd-HHmm>.litematic` + `.scan.json` — an archived copy of every scan, for `mcbuild diff`
- `<name>.scan.json` — server, dimension, `origin` (world XYZ of region [0,0,0] = paste origin),
  size, chunks included, chunks inside the box that were **not loaded** (saved as air — walk closer and rescan)

Chat shows origin/size/blocks/palette. Give the same origin to a teammate and their Litematica placement lines up.

Limits: only what the server sends (its view distance, not your render distance); chest/shulker
contents only if you've opened them; entity data is what the client knows (frames' items, stand poses, painting variants — not mob inventories).

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
cd C:/Users/Jack/mctest/chunkscan
export JAVA_HOME="C:/Users/Jack/AppData/Roaming/CCBlueX/LiquidLauncher/data/runtimes/temurin_25/jdk-25.0.3+9-jre"
./gradlew build test
cp build/libs/chunkscan-0.2.0.jar "$APPDATA/CCBlueX/LiquidLauncher/data/custom_mods/nextgen-26.2/"
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
