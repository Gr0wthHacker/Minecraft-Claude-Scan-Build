package dev.jack.chunkscan;

import net.minecraft.core.BlockPos;
import org.junit.jupiter.api.Test;

import java.util.HashSet;
import java.util.List;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * The lava model, as geometry — no client anywhere in it.
 *
 * <p>This is the one part of the miner that must be right before anything else is worth running:
 * every other failure costs a trip, and this one costs the inventory. So the cases here are the
 * ways it could be wrong that would still LOOK like a working guard.
 */
class LavaGuardTest {

	/**
	 * A world made of the cells you name: anything unnamed is plain rock, anything in {@code dark}
	 * is an unloaded chunk, anything in {@code falling} is gravel.
	 */
	private static LavaGuard.Cells world(Set<String> lava, Set<String> dark, Set<String> falling) {
		return new LavaGuard.Cells() {
			@Override public boolean loaded(int x, int y, int z) {
				return !dark.contains(x + "," + y + "," + z);
			}

			@Override public boolean lava(int x, int y, int z) {
				return loaded(x, y, z) && lava.contains(x + "," + y + "," + z);
			}

			@Override public boolean falls(int x, int y, int z) {
				return falling.contains(x + "," + y + "," + z);
			}
		};
	}

	private static LavaGuard.Cells plain() {
		return world(Set.of(), Set.of(), Set.of());
	}

	private static LavaGuard.Cells withLava(String... at) {
		return world(set(at), Set.of(), Set.of());
	}

	/** A two-course corridor face at the origin. */
	private static List<BlockPos> face() {
		return List.of(new BlockPos(0, 0, 0), new BlockPos(0, 1, 0));
	}

	// ------------------------------------------------------------------ the substring trap

	@Test
	void aLavaCauldronIsADecorationAndNotAHazard() {
		// Rules.isProtected matches substrings ON PURPOSE - gray_wool is protected because wool is
		// in the list. The same trick here refuses every corridor near somebody's brewing room.
		assertTrue(LavaGuard.isLava("lava"));
		assertFalse(LavaGuard.isLava("lava_cauldron"));
		assertFalse(LavaGuard.isLava("lava_bucket"));
	}

	// ------------------------------------------------------------------ the per-swing check

	@Test
	void lavaOnAnyOfTheSixFacesStopsTheSwing() {
		for (String side : new String[]{"1,0,0", "-1,0,0", "0,0,1", "0,0,-1", "0,1,0", "0,-1,0"}) {
			assertTrue(LavaGuard.touching(withLava(side), BlockPos.ZERO),
				"lava at " + side + " has to stop the break - it is in the hole before the drop lands");
		}
	}

	@Test
	void lavaAboveCountsBecauseThatIsTheOneYouCannotSeeFromInsideACorridor() {
		assertTrue(LavaGuard.touching(withLava("0,1,0"), BlockPos.ZERO));
	}

	@Test
	void aBlockOfRockBetweenYouAndTheLavaIsStillARockBetweenYouAndTheLava() {
		// Two away is not touching. The SEGMENT scan is what keeps a margin; this one is the last
		// gate before a swing and must not refuse every cell in the Nether.
		assertFalse(LavaGuard.touching(withLava("2,0,0"), BlockPos.ZERO));
	}

	// ------------------------------------------------------------------ the segment pre-clear

	@Test
	void aClearSegmentIsClear() {
		assertNull(LavaGuard.scan(plain(), face(), LavaGuard.SEGMENT_CLEAR));
	}

	@Test
	void lavaInsideTheRadiusRefusesTheSegmentAndOutsideItDoesNot() {
		int r = LavaGuard.SEGMENT_CLEAR;
		// Chebyshev: exactly r away is inside, r+1 is out. Getting this boundary wrong by one is
		// invisible in play - the corridor merely turns a little early, or a little late and once.
		LavaGuard.Threat inside = LavaGuard.scan(withLava(r + ",0,0"), face(), r);
		assertNotNull(inside, "lava exactly at the clearance radius must refuse");
		assertEquals(LavaGuard.Kind.LAVA_SEEN, inside.kind());
		assertNull(LavaGuard.scan(withLava((r + 1) + ",0,0"), face(), r),
			"lava past the radius must not refuse, or nothing in the Nether is ever diggable");
	}

	@Test
	void lavaIsFoundInEveryDirectionNotJustAhead() {
		int r = LavaGuard.SEGMENT_CLEAR;
		for (String at : new String[]{r + ",0,0", "-" + r + ",0,0", "0,0," + r, "0,0,-" + r,
			"0," + (r + 1) + ",0", "0,-" + r + ",0"}) {
			assertNotNull(LavaGuard.scan(withLava(at), face(), r), "missed lava at " + at);
		}
	}

	// ------------------------------------------------------------------ unloaded is unsafe HERE

	@Test
	void anUnloadedCellRefusesTheSegment_whichIsTheOppositeOfWhatNavDoes() {
		// Nav counts an unloaded chunk as PASSABLE, deliberately: refusing to route through one
		// fails every long flight. For DIGGING the same fact means the opposite - a cell we cannot
		// see is a cell whose lava we cannot see. If this ever starts returning null the guard has
		// gone blind in exactly the case it exists for.
		LavaGuard.Cells dark = world(Set.of(), Set.of("2,0,0"), Set.of());
		LavaGuard.Threat t = LavaGuard.scan(dark, face(), LavaGuard.SEGMENT_CLEAR);
		assertNotNull(t);
		assertEquals(LavaGuard.Kind.UNSEEN, t.kind());
	}

	@Test
	void anUnloadedCellAroundTheBodyIsTheWorldArrivingAndNotADanger() {
		// The body is STANDING there; a chunk still loading around it is not a reason to panic.
		// Only actual lava is, and it still is.
		LavaGuard.Cells dark = world(Set.of(), Set.of("2,0,0"), Set.of());
		assertNull(LavaGuard.aroundBody(dark, BlockPos.ZERO));
		assertNotNull(LavaGuard.aroundBody(withLava("1,0,0"), BlockPos.ZERO));
	}

	// ------------------------------------------------------------------ falling blocks

	@Test
	void gravelOverACellWeAreAboutToTakeIsAThreat() {
		LavaGuard.Cells w = world(Set.of(), Set.of(), Set.of("0,2,0"));
		LavaGuard.Threat t = LavaGuard.scan(w, face(), LavaGuard.SEGMENT_CLEAR);
		assertNotNull(t);
		assertEquals(LavaGuard.Kind.FALLING, t.kind());
	}

	@Test
	void gravelMerelyNEARTheCorridorIsNotAThreat() {
		// Over a cell we never take, it never moves. Refusing this would refuse most of the Nether.
		LavaGuard.Cells w = world(Set.of(), Set.of(), Set.of("3,2,0"));
		assertNull(LavaGuard.scan(w, face(), LavaGuard.SEGMENT_CLEAR));
	}

	@Test
	void unstableAboveLooksAtOneCellAndNotTheWholeColumn() {
		// A stack of gravel falls as a column, so catching its bottom catches all of it. Walking
		// upward instead would refuse a corridor under any gravel anywhere above it.
		assertTrue(LavaGuard.unstableAbove(world(Set.of(), Set.of(), Set.of("0,1,0")), BlockPos.ZERO));
		assertFalse(LavaGuard.unstableAbove(world(Set.of(), Set.of(), Set.of("0,5,0")), BlockPos.ZERO));
	}

	// ------------------------------------------------------------------ degenerate input

	@Test
	void anEmptySegmentIsClearRatherThanACrash() {
		assertNull(LavaGuard.scan(plain(), List.of(), LavaGuard.SEGMENT_CLEAR));
	}

	@Test
	void everyThreatCanSayWhatItIsInOneLine() {
		// The caller's whole job on a refusal is to print one honest line. A threat that cannot
		// describe itself becomes "the miner stopped", which is the message nobody can act on.
		for (LavaGuard.Kind k : LavaGuard.Kind.values()) {
			String s = new LavaGuard.Threat(new BlockPos(1, 2, 3), k).describe();
			assertTrue(s != null && !s.isBlank(), k + " has no description");
			assertTrue(s.contains("1") && s.contains("2") && s.contains("3"),
				k + " does not say where: " + s);
		}
	}

	/** Sanity: the body clearance must not exceed the segment clearance, or the body refuses first. */
	@Test
	void theBodyClearanceIsTighterThanTheCorridorClearance() {
		assertTrue(LavaGuard.BODY_CLEAR <= LavaGuard.SEGMENT_CLEAR,
			"a body panicking further out than the corridor refuses would escape from every corridor"
				+ " the corridor gate was happy to dig");
	}

	private static Set<String> set(String... s) {
		return new HashSet<>(List.of(s));
	}
}
