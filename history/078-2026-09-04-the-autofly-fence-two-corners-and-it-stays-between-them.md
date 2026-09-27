## The autofly fence: two corners, and it stays between them (2026-09-04)

Jack: *"lets edit auto fly so i can set two points and it only stays within those points."*
`Bounds.java`, `tests/BoundsTest.java` (11), and a bounds round-trip in `SessionTest`.

```
/cscan autofly bounds set                 the wand's two corners become the fence
/cscan autofly bounds <x1 y1 z1 x2 y2 z2> ...or six numbers
/cscan autofly bounds                     where it is, and whether you are inside it
/cscan autofly bounds off                 flight goes anywhere again
```

**THREE LAYERS, BECAUSE ANY ONE ALONE HAS A HOLE IN IT.** The PLAN filters cells and chests
outside the box out of the loop's own choices (`Hud`), so it never aims past the fence and works
the fenced area instead of stalling at its edge; the ROUTE wraps every passability predicate in
`Bounds.within`, so A* cannot find a way that leaves even to go round something; and the STEP is
clamped last, after `avoid`, on the flying step, the walk, and both recovery rungs, so the direct
guess, the unstick slide and the escape flood cannot carry the body past a face either. A body
already outside is pulled back in at 0.3 blocks a tick rather than flung. A destination outside
it - a `goto`, a photo bearing, a tidy source - holds and says so once, and `/cscan why` names it.

- **A FENCE IS NOT AN ACTIVITY**, so `/cscan stop` leaves it standing. It IS coordinates, so it
  clears on DISCONNECT and comes back from `session.json` only in the dimension it was drawn in -
  restored FIRST on resume, because a fenced loop that resumes unfenced is the dangerous direction.
- **A TELEPORT CANNOT BE FENCED.** The fall rescue keeps its `/is` - a fall is the inventory. The
  recovery ladder's GO_HOME rung is convenience and is withheld while a fence is set; it gives the
  spot up instead. Out-of-view cells outside the box are written off at once rather than after two
  look-watchdog strikes.
- **The one-course box has one legal height and it converges over two ticks**, not one - the
  return is speed-capped - which is what the first version of its test got wrong. And `holds` needs
  rounding slack: `(feet + step) clamped - feet`, re-added, is not exact.

Not flown in game yet. `bounds` and `set` went into `RESERVED`, which `SidecarSafetyTest` caught.

