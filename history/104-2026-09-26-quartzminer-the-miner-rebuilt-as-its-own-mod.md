## quartzminer: the Nether miner rebuilt as its own mod (2026-09-26, quartzminer 0.1.0)

Jack: *"build the quartz miner as a whole new JAR and separate plugin, its very glitchy and needs to
probably be re-done from scratch so it can properly locate the quartz, mine to it, not die, move
cleanly."* He chose a from-scratch build over wrapping a Baritone fork. The code is on branch
`feature/quartzminer`, dir `quartzminer/`, and doesn't depend on chunkscan.

### Why the old one could not be fixed in place

It had no parts of its own. It fed a scan-derived list to the island `Digger`, walked with the flight
`Autopilot`, and got past three island-only gates (plot, void, walk) through special cases. Every fix
added another special case. It also never searched: a branch tunnel with a heading, plus only the ore
that was already exposed.

### What replaced it

- **Search, not tunnel.** Dijkstra from the feet to *any* stand with minable ore in reach, with dig
  time in the cost. The nearest ore by distance is often the expensive one, sitting behind lava or
  under gravel. Dijkstra finds the cheapest *safe* one. The search is incremental, 400 nodes a tick, and
  uses a per-search `CachedGrid`.
- **All the safety rules sit in the move generator.** A path that was never safe is never offered.
  The executor re-checks each step against the live world before running it.
- **Cardinal moves only, and it turns before it walks.** This fixes the "moves badly" symptoms:
  diagonals clip corners in one-wide tunnels.
- **Reach is the body's own tunnel walls plus the cell overhead,** never the floor.
- **Anti-xray is measured, not assumed.** The old design's premise, that the client sees behind the
  wall, is false on a server that paints over or fakes ore. `XrayLedger` compares each hidden
  neighbour of a dug cell before and after exposure. Three fakes means it drops hidden targets;
  three painted-over cells means it explores by tunnelling.
- **Diggable is an allowlist** of natural Nether blocks, so it never digs a portal, a chest or a base.

### Not done yet

No stash chest: a full pack sends the escape command and stops. No mob handling beyond escaping at
10 health. No pillaring up. The first live run on skyblock.net went cleanly (Jack, same day): it found and
collected quartz, and dug down to reach more. The old `/cscan mine` is still in chunkscan,
along with its uncommitted rewrite (`QuartzSearch`, `MiningWalkInput`). Remove both once `/qm` has
proven itself.
