## The autonomy audit: three readers, 55 findings, 28 fixed (2026-09-04)

Jack: *"audit this and all autonomous functions deeply, we need this to be a seamless smooth system
that carefully guides the prints of entire schematics without getting caught or falling."* Three
parallel read-only audits - flight and routing, the loop's decisions, placement and materials -
then every finding verified against the code before it was touched. 632 Java tests, 0 failures.

**THE WORST FINDINGS WERE ALL "CORRECT ON THEIR OWN, WRONG TOGETHER"**, which is this file's own
recurring lesson at a larger scale:

- **THE TAKE-OFF COULD NEVER COMPLETE.** `regain()` (double-tap jump to get flight back) shared
  `rescueStage` with the fall rescue, which runs first every tick and resets that stage whenever
  the body is NOT falling. Stage 1 was wiped one tick after it began, so the key was held for four
  consecutive ticks - one jump, never a double tap - four tries were spent, and the session was
  permanently on foot. The landing mode shipped a day earlier depended on it. Own stage now.
- **A LANDED BODY NEVER MOVED AGAIN.** `needsFlight` said a landing within 24 blocks is WALKED,
  and `walk()`'s gate said only a FETCH may walk. Both rules are right; together no landing ever
  chained. The gate admits a landing, which is a floor by construction.
- **EVERY RECOVERY RUNG LASTED ONE TICK.** "Moving means fine" reset the ladder the moment the
  back-off's own first step moved the body, so the flight steered straight back into the wedge.
  While a rung drives, only the rung ends itself.
- **A ROUTED FLIGHT HAD NO FLOOR CLEARANCE AT ALL.** `Nav.of` keeps the two cells the body
  occupies clear and nothing below, so a tight route's cheapest leg skims a floor at 0.1 - and this
  server ends flight on contact. A LIFTED tier now sits between roomy and tight: a clear cell under
  the feet the whole way, tried before any route that may hug a floor. Indoors it fails at once.
- **`avoid()` TESTED AXES AND SENT THE DIAGONAL.** Each axis clear, the corner clipped. The
  combined step is tested and the smaller horizontal component is dropped first.

**The fence's own holes**, found the day after it shipped: stands, orbit stops and chest approach
cells were chosen with UNFENCED predicates, so the loop aimed at cells the autopilot then refused
and abandoned the spot (`Bounds.within` at all nine sites); `Bounds.within` wrapped a
`WalkingSpace` in a lambda and Nav lost the on-foot rules by type (`WalkingSpace.confined`);
`clamp` ran AFTER `avoid`, so a pull back into the box was never collision-tested (clamp first);
the Printer and Digger acted on cells outside the fence from inside it (the gate is at the
actuator now); the course lookahead and the re-anchor read the UNFILTERED todo, so eight courses
of fenced-out cells left fenced work one course up unreached (`eligible` is decided once).

**The loop's silent phases**: the dead end's second look path had no watchdog and no fence check
(one `lookForUnseen` for both sites); a completed look kept its strikes and its start time, so a
long look read as a 90s stall on arrival; a chunk loading with cells already BUILT counted as
placements (the printer's own report is the count now, the inference only while no chunk moved);
`Work.carrying` walked 41 slots so a block in the OFFHAND read as placeable stock; a dead end under
single `follow` idled all night (two minutes, then it stops and says so); the orbit index outlived
its ring; the hiccup stop did not write the session note; a foreign container screen parked the
loop in silence.

**The placement side**: `support()` let the printer right-click repeaters, comparators,
composters and bells - the server USES those before placing, so a repeater's delay cycled and
nothing went in (`Printer.toggles`); a water bucket used on a waterloggable kerb waterlogs the
KERB, which is a source flowing out of the pool; a half-placed double slab or multi-face vine was
judged a MISMATCH, given up and reported as a refusal (`Verdict.PARTIAL`); the hotbar swap evicted
whatever was selected - the digger's pickaxe - into the pack; a grass or fern cell was a
"deviation to break by hand" rather than something a right-click replaces; three journal I/O
failures called `Hud.off()` in silence and kept the note that resumes into the same failure.

**Deliberately NOT changed, stated:** chest approaches hover at 1.05 over the floor (the audit's
one worry, and the number Jack asked for); `hasArrived`'s wall-ahead rule; `Nav.standable` cannot
stand on carpet; `Printer.relax()` re-admits a twice-refused cell every 30s without back-off;
nothing here has been flown in game.

**And a working-practice note that cost an hour:** these Java files mix CRLF and LF WITHIN ONE
METHOD, and tabs with spaces on adjacent lines. A patch anchor with one newline style never
matches; the patcher that worked matches tokens with `\s+` between them.

