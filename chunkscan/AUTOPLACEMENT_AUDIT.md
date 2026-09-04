# ChunkScan 0.8 automatic-build audit

**Follow-up:** the [full autonomy audit](AUTONOMOUS_BUILD_SYSTEM_AUDIT.md) identifies additional release blockers and regressions in the 0.8.1 candidate. Its verdict supersedes any interpretation of this report as release readiness.

Audit date: 2026-09-03. User-confirmed running version: **0.8**.

**Verdict: 0.8 did not implement a reliable unattended schematic → stock → build → restock loop.**
The fixes in 0.8.1 are a locally tested candidate, not an in-game certification. Do not interpret unit-test success as proof that server interaction, flight or shulker recovery works on the live island.

## Artifacts and compatibility

- Audited input: `build/libs/chunkscan-0.8.0.jar`, SHA-256 `d2a38e2f2deff4d32aa0eef2bab34893fec7fc0d737d67279287979c7fbdcc52`.
- That JAR contains 112 class files, including the built-in printer.
- `../out/chunkscan-0.2.0.jar` contains only 9 class files and no built-in printer. It is not the user's running version.
- Candidate: `build/libs/chunkscan-0.8.1.jar`, copied to `../out/chunkscan-0.8.1.jar` after the build.
- Client runtime remains **Minecraft 26.2, Fabric, Java 25**. This is not a native Minecraft 1.19 client mod. Automatic placement is restricted to the **skyblock-1.19 block inventory**; server translation and mechanics still require live verification.
- Original JARs and unrelated park-generation edits are preserved. No game profile was modified and no live-server action was performed.

## Findings and changes

| Severity | 0.8 finding | 0.8.1 change |
|---|---|---|
| High | Work loading required `.work.json`; changing the `.litematic` did not change what the printer built. | Read `.litematic` directly at the `.scan.json` origin. Legacy work-only input remains supported. Cache invalidation covers schematic and origin changes. |
| High | `follow` guided and fetched but did not enable the printer; advancing designs could leave the printer on the previous design. | Following starts/reset the built-in printer for that design. Stopping following stops it; transitions switch it. Flight remains explicitly controlled by `autofly`. |
| High | The nearest target was selected before checking its face or inventory. An unsupported nearest cell could starve all valid neighboring cells. | Candidate selection requires carried stock and a valid placement before ranking by distance. |
| High | Planning treated unloaded neighbors, fluids and vegetation as support; it also fell back to unsupported stations. | Recompute the live supported, accessible frontier each recount. Unseen cells are not proven support. Remove the unsupported fallback. |
| High | The printer searched only the hotbar while the loop counted the whole inventory. | Search all 36 normal inventory slots; move stock into the hotbar with a normal inventory swap before placing. |
| High | Chest lookup used the shared index without filtering by schematic island or dimension. | Resolve storage against the schematic origin and registered island bounds; exclude other dimensions, unknown-dimension records, and non-storage utility blocks. |
| High | Unknown chests could never become stock sources without manual opening. | When supported work lacks indexed stock, discover loaded chest/barrel/shulker block entities on the design island, navigate to them, and open them for a read-only contents scan. Bound attempts and refresh stale records. |
| High | Placement verification read client-predicted state on the next tick. | A per-client-level Mixin tracks server block acknowledgements. Verify after the attempt's sequence is acknowledged; stop following after a missing-ack timeout. |
| High | Face ordering preferred the ceiling despite comments claiming support below; a single yaw convention was incorrectly applied to every block, including stairs. | Prefer clicking UP on support below. Probe actual shape surfaces, check the eye ray and reach, ask vanilla for the placement state, and send rotation before interaction. |
| High | The documented 1.19 placement guard was absent from the printer. The existing observed-block list is explicitly provisional. | Add a separate version-specific block-name registry and enforce it in automatic placement. Missing registry fails closed. |
| High | Withdrawal accepted any container screen, including a pre-existing screen. | Bind block-open tracking to the expected position/current level and then bind withdrawal to the resulting menu ID. Unexpected screens cancel withdrawal. |
| High | Withdrawal added the clicked stack size to `took`, even if no transfer happened; timeout could expire during a productive large refill. | Wait for the server menu-state response and measure inventory gain. Refresh timeout after confirmed progress. Full packs stop taking. Compare final inventory with the requested total. |
| High | Shulker routines only searched the hotbar and assumed any occupied destination meant their box had been placed. | Search normal inventory, swap into hotbar, use validated placement, wait for acknowledgement and inventory decrement, and require the expected box type before opening/breaking. Reuse the withdrawal state machine. |
| High | Unboxing could fill the last slot and leave nowhere for its box; failure allowed following to continue. | Reserve a slot, pause competing placement/movement, and stop following if box placement/recovery fails. |
| Medium | Clusters with one or two cells were deliberately discarded. | Keep isolated final cells. Allocate material budgets to ready cells rather than spending them on blocked cells. |
| Medium | A stale scaffold result was cached solely by remaining-cell count. Other players could add support without changing that count. | Replace that navigation cache with fresh live-frontier evaluation. |
| Medium | Correct block names with wrong properties could be classified as complete. | Strict completion includes mismatches. The loop may advance after exhausting automatic placements but reports unresolved mismatches instead of calling them complete. |
| Medium | Storage slot counts were written into memory but not persisted; equal coordinates in different dimensions collided. | Persist slot/used counts and separate non-overworld dimension keys. Invalidate the storage cache after writes. |
| Medium | Null Litematica availability caused `/cscan print` to throw after partially starting. | Use a null-safe Boolean check. Built-in printing does not require Litematica. |
| Medium | Planning could use an external printer's configured reach while the built-in printer had a shorter reach. | Use the built-in reach while it is active. |
| Medium | Disconnect left active printer/withdrawal coordinate state behind; the reconnect grace period only covered HUD movement. | Clear transient machinery on disconnect and apply reconnect grace to printing as well. |

## Input contract

Place `<name>.litematic` and `<name>.scan.json` together in the game profile's `schematics` directory. The sidecar must contain an explicit world origin:

```json
{"origin":{"x":100,"y":64,"z":200}}
```

The reader supports Litematica format versions 5–7, multiple regions, signed region dimensions, palettes/properties, and bit-packed entries crossing long boundaries. It rejects malformed packed data and conflicting overlapping non-air regions. Bounds: 256 MiB NBT allocation accounting, 64 million region-volume cells, and one million non-air cells. Air is ignored, never interpreted as permission to dig. Entities and block-entity contents are not reconstructed by the printer.

Rotation/mirror are NONE. The recorded origin is authoritative; moving a visual Litematica placement does not move the built-in printer's target. A `.litematic` with a missing origin sidecar produces an error rather than falling back to stale coordinates.

For multiple islands, `islands.json` must identify their actual centers and radii. Without a matching registry entry, automatic storage falls back only to the known single baked-in plot containing the origin. Otherwise no chest is selected. Unknown-dimension legacy chest records need reopening/scanning.

## Running the candidate

With 0.8.1 installed in the 26.2 client profile in place of 0.8.0:

```text
/cscan follow <design>
/cscan autofly on
/cscan why
/cscan stop
```

`follow` enables printing and automatic replenishment. `autofly` is still a separate movement switch. It uses carried blocks where possible; once replenishing, it fills available capacity toward remaining demand, prioritizing materials needed by the current supported frontier, then resumes building. New supported cells become eligible as the world changes. `follow all` switches through tracked designs. Only one printer should be active; a separately installed Litematica printer is not automatically disabled.

## Validation and remaining release gates

The original baseline passed **447 tests** despite the defects above. Some tests asserted comments/source strings or encoded the incorrect behavior (discarding isolated cells and the reversed clicked-face preference). Those expectations were corrected; gameplay claims are not inferred from such tests.

The candidate's full Gradle test suite and build pass: **462 tests, 0 failures, 0 errors, 0 skipped**. Added coverage exercises real compressed NBT loading, signed regions, straddling packed entries, stale work/origin cache changes, invalid input, namespaced states, profile filtering, island/dimension storage isolation, support filtering, server-ack gating, strict completion and final singleton work. A deterministic production-planner simulation builds 137 vertically dependent cells using three 64-block-capacity loads. This simulation does **not** simulate network packets, inventory screens, flight or actual block placement. The existing Java-writer/Python-reader cross-check also passes.

Still unproven or limited:

1. **Runtime Mixin and protocol behavior:** no live 26.2 Fabric launch/server session was available. Confirm the acknowledgement hook applies and that the server/protocol translator sends block acknowledgements and inventory state updates. Missing acknowledgement stops the candidate; it does not assume success.
2. **Actual flight/approach and recovery:** the existing movement controller remains heuristic. A route can still fail to find a reachable face or item pickup location. Test multi-level chest approaches, walls, ceilings, tight gaps and shulker recovery in-game.
3. **Inventory/menus under lag:** confirm hotbar swaps, delayed initial contents, shift-click acknowledgements, rejected transfers and repeated refills on the actual server. Standard vanilla menus are assumed; custom plugin menus can require different handling.
4. **Special construction actions:** no temporary scaffolding, removal/replacement, slab doubling, waterlogging action sequence, wrench-like rotation, entity placement, or block-entity NBT reconstruction is implemented by this printer. A target state requiring such actions may remain unresolved. It will not force an air placement to make progress.
5. **Unloaded storage:** discovery scans loaded chunks within 16 chunks of the player, filtered by island. It cannot read unopened contents remotely or discover arbitrary unloaded chests. Previously indexed chest positions remain navigable; otherwise visit the storage area to load it.
6. **Cross-server profiles:** the legacy storage/island/session files share the profile's schematics directory and are not partitioned by server identity. Use this profile for the intended server; cross-server automation is not certified. Dimension/island filtering does not solve identical coordinates on different servers.
7. **Multiple clients:** storage read-modify-write remains vulnerable to simultaneous writers in one shared schematics folder. Fleet checks do not constitute an atomic distributed lock. Single-client loop correctness does not certify multi-alt concurrency.
8. **Completeness:** exhausted automatic placements can still leave wrong blocks, unsupported islands of schematic cells, unloaded dig work or special-state actions. Inspect `/cscan check` and `/cscan why`; do not equate an idle printer with a fully completed schematic.

Before unattended promotion, demonstrate two complete refill/return cycles with server-confirmed placements, finish isolated final cells, reject a deliberately floating target, prove another island's chest is never selected, and recover a partially emptied shulker with a nearly full pack. Also test disconnect/stop during a pending placement and withdrawal. These are live acceptance gates, not completed tests.

Version-name data source: [PrismarineJS minecraft-data, Java 1.19 blocks](https://raw.githubusercontent.com/PrismarineJS/minecraft-data/master/data/pc/1.19/blocks.json). The packaged name-only resource records the source URL and downloaded-data SHA-256; this is a version registry, not a claim that the server grants every listed block or mechanic.

Candidate SHA-256: `081aa7f74dda8114900200532c8b9cfacb8c586680f840260c660c4458584773`. Machine-readable validation and command logs: `build/audit/`.
