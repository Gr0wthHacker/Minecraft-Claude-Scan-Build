# Redstone evidence and test boundary

`mcbuild.circuit` models deterministic, block-level Java redstone behaviour. A green contract
means the stated inputs produce the stated block outputs in that model; it is not a claim to have
simulated entities, game-tick ordering, or a whole Minecraft server.

## Sources used for rule changes

- [Minecraft: Block of the Week — Observer](https://www.minecraft.net/sv-se/article/block-week-observer)
  is the primary source for the observer’s facing/detection convention and its two-game-tick
  strong pulse. In this project one simulation tick is two game ticks, so it is one simulated tick.
- [Minecraft Wiki: Tutorial: Minecarts](https://minecraft.wiki/w/Tutorial:Minecarts) is the
  reference for rail behaviour used here: an inactive powered rail brakes; a directly powered rail
  propagates power through eight further connected powered rails; and a detector rail outputs only
  while a cart occupies it.
- [Minecraft Wiki: Tutorial: Train station](https://minecraft.wiki/w/Tutorial:Train_station) is a
  design reference for detector-rail station patterns and platform safety. It is a candidate source,
  not a replacement for a local contract test.

## Contract inputs

The simulator cannot fabricate an entity or a world event. Tests must state the event explicitly:

- `sim.observe(position)` supplies a block update to observers whose front face watches `position`.
- `sim.set_signal(position, level)` supplies an external 0–15 signal from a target, sculk sensor,
  detector rail, weighted plate, daylight detector, or trapped chest.
- `sim.fill(position, level)` supplies a comparator-readable inventory fullness; it does not assert
  that an entity actually inserted an item.

These boundaries are intentional. A generator may not call them as a substitute for a contract:
the associated test has to state the real player/cart/projectile/vibration event and assert the
visible output it promises.
