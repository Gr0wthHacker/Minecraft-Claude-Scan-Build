# Under-Squid Expansion Plan

## Status and decision

**Implementation status: complete in generated artifacts; live in-game parkour proof remains a
promotion gate.** The plan now drives a mouth-only market, two parkour strands with recovery,
a detailed sperm whale, a glazed tail overlook, and three static sounding frames. The generated
delivery is recorded in `UNDER_SQUID_EXPANSION_DELIVERY.md` and the frozen spatial contract is
`under_squid_expansion.contract.json`.

Build the lower world as **one connected encounter: The Sounder in the Dark**.
The existing Abyss Squid remains the first and largest reveal. A sperm whale
follows it through the darkness from behind, visible only after a player reaches
the squid's tail. The biological relationship is real, the silhouettes are
immediately different, and the existing Sounding Hall bell gains a reason to
exist: sound reveals the hunter.

Access is now locked to the user's direction:

> Prism Tower parkour → squid mouth → squid interior → tail overlook → return
> to the mouth → Prism descent/recovery.

There is no separate surface entrance. The vertical market shaft at
X97600/Z80665 in the current Abyss Market source is obsolete and must not be
built or treated as an anchor in the next generation pass. The current market
artifact remains useful only as measured evidence of the squid's interior.

## What was measured

Coordinates below are world XYZ. Park-local coordinates are V=X-97500 and
U=Z-80300. The current public build plane is Y203.

| Item | Measured bounds | Size / mass | Consequence |
| --- | --- | ---: | --- |
| Park Complete | X97500-97699, Y94-311, Z80300-80899 | 441,087 blocks | The lower composition stays inside the existing 200×600 shadow. |
| Park Complete below Y196 | X97538-97642, Y94-195, Z80399-80867 | 31,725 blocks | Almost all deep occupation is the Prism Well; the Frontier underside near the whale is only at Y190-195. |
| Abyss Squid | X97543-97657, Y101-185, Z80488-80762 | 115×85×275; 46,882 blocks | The whale must remain secondary and cannot merge with the mantle silhouette. |
| Existing market fit-out | X97575-97625, Y105-210, Z80502-80713 | 3,934 blocks | Its 211-block internal walk proves the tail can be reached; its surface shaft is retired. |
| Prism Well keep-out | axis X97590/Z80815, radius 56 | fixed | Only typed parkour landings and their catches may occupy the approach side of this cylinder. |
| Initial whale reservation | X97525-97660, Y108-172, Z80318-80462 | 136×65×145 | Zero occupied cells across Park Complete, Squid, and Market. |
| Adopted leviathan reservation | X97500-97614, Y95-179, Z80255-80469 | 115×85×215 | Zero occupied cells; carries a 200-course predator into the northern void. |

The whale reservation has **25 wholly empty Z rows** before the squid begins at
Z80488. Its top at Y172 has **17 wholly empty courses** below the nearest park
cell at Y190. Its nearest horizontal point is 353 blocks from the Prism Well
axis, far outside the r56 fall keep-out. The reservation leaves 25 blocks to the
west park edge, 39 to the east edge, and 18 to the north edge.

The measured plan and complete machine-readable output are:

- `out/under_squid_plan/measured_plan.png`
- `out/under_squid_plan/measurements.json`
- `tools/measure_under_squid_plan.py`

## Why the second sculpture should be a sperm whale

| Candidate | Story | Voxel silhouette | Relationship to squid | Decision |
| --- | --- | --- | --- | --- |
| Sperm whale | Real deep-ocean hunter of large squid | Square head, tapered body, narrow peduncle and broad flukes read at distance | Creates one understandable pursuit | **Build** |
| Whale skeleton | Strong pale contrast and easy ribs | Reads clearly, but becomes another bone monument | Implies aftermath rather than an active abyss | Fallback only |
| Giant anglerfish | Strong mouth and lure | Competes with the squid's photophores | Predator relationship is weaker and starts an animal collection | Reject |
| Submersible or wreck | Gives scale and human story | Reads as another building/vehicle | Creates expectations of another interior and route | Reject |

The whale should be alive, unarmoured, and inaccessible. It is a secondary
setpiece, not a new attraction or another interior. The guest-facing attraction
is the reveal from the squid and the sound response around it.

## Composition and sculpture contract

### Pose

- Use a target solid envelope of approximately X97507-97603, Y105-164,
  Z80257-80466 inside the larger reservation.
- Point the whale generally south toward the squid, with 6-10 degrees of yaw
  toward the west and 6-8 degrees of roll. A perfectly axial whale would merge
  into the squid in long views.
- Put the head centre near X97558/Y137/Z80454. Its west offset turns the
  tail-window view into a legible three-quarter open-mouth reveal.
- Keep the flukes near Z80324 and the nose no farther south than Z80458.
- Keep the whale's top at or below Y160 in detailed generation. The reservation
  extends to Y172 for fins and review slack, not for a taller body.

### Anatomy that must read

1. A blunt rectangular sperm-whale forehead occupying about one quarter of the
   animal's length.
2. A narrow underslung lower jaw, visible in profile and three-quarter view.
3. One offset blowhole on the crown.
4. Small eyes placed behind the mouth line, not on the forehead.
5. Short pectoral fins with a deliberate bank.
6. A long taper into a thin peduncle.
7. Two broad, shallow flukes with a central notch and trailing-edge curve.
8. Three to five pale circular sucker scars on the head and shoulder. These are
   the visual clue linking the whale to the squid; they cannot become random
   spots over the whole body.

Target length is 200-210 blocks, roughly three quarters of the squid's length.
Target finished mass is 55,000-75,000 blocks after a two-block shell pass. The
open mouth supplies the negative-space cue, while the larger body carries impact
comparable to the squid without exceeding its length.

### Palette and light

Use a cheap 1.19 palette already verified by the repository:

- black wool and gray wool for crown and deep body;
- light gray wool and limited white wool for the belly and jaw;
- bone block only for teeth and selected scar rims;
- polished blackstone/deepslate for any attached survey hardware;
- cyan/light-blue wool and ochre or pearlescent froglight for the sound response;
- waxed copper only where Prismworks has physically tagged or mounted something.

Do not use calcite or sea lanterns; both are currently expensive tier. The whale
is not bioluminescent. Conceal illumination in the overlook and in three sparse
Prism survey frames aimed at the head, so the light has an authored source.

## Guest sequence

### 1. Parkour-to-mouth threshold

The current geometry offers two useful route anchors:

- inbound candidate: Crown Descent rest at X97606/Y162/Z80801;
- outbound candidate: Prism Descent rest at X97613/Y124/Z80791.

The squid mouth is open on its axis around Z80706-80713. Reserve a 5×5 threshold
centred at X97600/Y148/Z80713. At that coordinate the mouth is open void; a small
split stair can descend six courses to the two existing prow galleries around
Y142 without cutting the squid.

Greybox two separate one-way parkour strands:

- **Hunt Line:** Crown rest → 18-24 descending moves → upper mouth threshold.
- **Wake Line:** lower mouth threshold → 18-22 descending moves → Prism Descent
  rest, after which the existing course continues to its recovery pool.

Reserve X97565-97628, Y118-166, Z80713-80805 for these strands and their catches.
This is a study envelope, not permission to fill it. Inside the Well's r56 zone,
only course landings may be added. Outside the Well, every gap needs a slime or
water catch with a route back to its own prior rest; falling into void is not an
acceptable failure state.

This interface must be solved against both descent artifacts, the squid, the
Well, and the Rig. It cannot be inferred from bounding boxes.

### 2. Mouth and prow

The mouth is the only guest entrance. Give it three readable states without a
surface sign tower:

- a bright five-block landing target visible from the final Hunt Line rest;
- two short side stairs from the mouth axis into the west and east prow galleries;
- a clear outbound colour on the Wake Line so returning guests do not reverse
  into incoming parkour.

The entrance should feel like landing inside the animal, not crossing a doorway
installed on its face. Keep the open mouth silhouette and use the squid's own
red/black/pink language at the threshold.

### 3. Interior journey

Retain the useful measured order of the existing fit-out, while rebuilding its
access assumptions:

1. Prow galleries around the open mouth.
2. Bazaar as a compact inhabited chamber.
3. Gullet and collar as the transition into the mantle.
4. Arcade/gallery as the long descent through the body.
5. Sounding Hall and its bell.
6. Tail overlook as the final reveal.

The 211-block interior walk is long enough. Do not add more rooms merely to fill
the 54,994-cell cavity. Add passing bays and a clear return colour instead. The
market, tail overlook, and bell are the three destinations; the connective walk
is atmosphere.

### 4. Tail overlook and whale reveal

Use the existing tail band at Z80500-80518 and floor near Y105. Place the main
standing view around X97600/Y106/Z80503, then aim it toward the whale head near
X97558/Y137/Z80454. The diagonal sightline exposes the forehead, nineteen-course
gape, projecting jaw, body taper, and banked flukes while the dark gap preserves depth.

Make one controlled 9-13-wide opening or glazed blister in the mantle tip only
after ray tests prove it sees the head, eye, jaw, and one fluke. Cap all new squid
skin excavation for this overlook at 60 cells, state-check every removed block,
and keep it in a separate dig manifest. A large hole would damage the sculpture
and flatten the reveal.

The visitor rings the existing Sounding Hall bell before reaching the overlook.
The static version uses three incomplete cyan/copper sound frames between the
overlook and the whale. A later redstone version may light those frames in order
for 8-12 seconds and finish on the whale's eye/scar plane. If the live server
cannot prove the sequence and reset, ship the frames with restrained constant
light and make no reactive claim.

### 5. Return

The return remains inside the squid to the mouth. Use a visibly different band
or upper-side route where the cavity permits; use passing bays where it does not.
At the mouth, returning guests take the Wake Line to the existing Prism Descent
rest and continue to the established catch and return column. No ladder, shaft,
door, or path reaches the surface independently.

## Environmental additions

Keep the void mostly empty. Its darkness gives both animals scale.

- Three incomplete sound frames, 18-34 blocks in diameter, clustered in the
  final 35 blocks before the whale's head. They share one axis and never form a
  full tunnel.
- Two small Prism survey brackets attached to existing interior structure at the
  overlook. These hold the light source and explain why the whale can be seen.
- A very sparse set of pale particles around the light cone, tested as groups
  rather than random single blocks. Omit them if they read as confetti.
- No third large animal, ruins field, seabed, generic cave, detached shops, or
  broad exterior catwalk.

## Interfaces and ownership

| Module | Purpose | Access | Return | Service | Provisional block budget |
| --- | --- | --- | --- | --- | ---: |
| Abyss parkour threshold | Exclusive connection from Prism run to mouth | Crown Descent rest | Wake Line to Prism Descent | From typed recovery rests only | 350-650 |
| Mouth landing | Separate inbound/outbound and join the prow | Hunt Line | Wake Line | From interior prow | 120-220 |
| Squid interior revision | Market, bell, tail journey | Mouth only | Mouth only | Concealed inside existing cavity | Existing 3,934 plus up to 800 |
| Tail overlook | Frame whale reveal | Interior walk | Interior walk | Sounding Hall side | 250-500 plus ≤60 dig cells |
| Sperm whale leviathan | Secondary abyss landmark | None | None | Build-only inspection | 55,000-75,000 |
| Sound response | Explain/reveal whale | Bell and overlook | Same | Concealed relay access | 300-700 |

No module may claim a public surface access point. The whale has no guest anchor
and no interior. Its only public interface is the named tail-overlook view.

## Generation order

1. **Correct the source contract.** Remove the market's surface-shaft generation
   from the candidate configuration and add mouth entry/exit anchors. Do not
   delete or replace the current artifact until the new route is proven.
2. **Strict spatial solve.** Register the whale reservation, both parkour strands,
   mouth threshold, tail overlook, Well keep-out, existing course cells, and all
   squid skin as protected context.
3. **Access greybox.** Generate only landings, catches, mouth platform, interior
   route bands, and overlook volume. Validate the complete guest loop and every
   failure recovery before sculpting the whale.
4. **Whale anatomy greybox.** Generate head, body taper, jaw, fins, peduncle and
   flukes as named parts inside the reservation. Review head-on, profile,
   three-quarter, tail-on, parkour discovery, and tail-overlook views.
5. **Detailed whale.** Apply value bands, eyes, blowhole, jaw line, sucker scars,
   controlled asymmetry, and shell hollowing. Keep one connected printable body.
6. **Sound and light.** Add the three frames and overlook sources. Run night-light
   propagation and remove any decorative light visible as unexplained glowing
   anatomy.
7. **Assembly and proof.** Compose Park Complete, Well, both descents, Rig, Squid,
   revised Market, threshold, and Whale. Run world validation, collision, route,
   headroom, support, materials, light, animal-quality, and printability gates.
8. **Live proof.** Test every parkour move and miss, arrival at the mouth, passing
   another player inside, bell reach, whale reveal, return to the course, and
   final recovery to the surface.

## Acceptance gates

- The squid remains the first clear silhouette from Prism parkour; the whale
  does not appear as a fused extension of its mantle.
- The whale is recognisable from silhouette alone in profile and three-quarter
  views at 60 and 120 blocks.
- The tail-overlook frame includes forehead, eye/jaw relationship, and at least
  one fluke; otherwise the pose or aperture moves before detail.
- The whale reservation stays at zero collisions. Any later collision is a hard
  generation failure, not a trim operation.
- No new non-course surface enters the Well r56 fall cylinder.
- Every new parkour miss has a proven safe catch and recovery. No route strands a
  player on the squid or in the void.
- The only way into the market is the mouth from parkour. The only way out rejoins
  the Prism descent/recovery system.
- Public route, inbound parkour, outbound parkour, and service access remain
  distinct at the mouth.
- All whale anatomy is connected; no eye, fin, jaw, scar, or fluke floats.
- Materials exist, are available in the locked 1.19 profile, and are spendable.
- The static night scene is readable before any redstone sound sequence is
  promoted.
- Multi-player live proof confirms two players can pass inside and one player's
  failure does not block another's entry or return.

## Immediate next build package

The first implementation package should contain only:

1. a strict route/volume contract with the obsolete shaft disabled;
2. the two parkour-strand and mouth-platform greybox;
3. a low-resolution whale anatomy greybox inside the measured reservation;
4. six review views, including the current parkour approach and tail overlook.

Do not detail the whale, cut the squid, or alter the existing descents until this
packet proves the mouth loop and the whale reveal together.
