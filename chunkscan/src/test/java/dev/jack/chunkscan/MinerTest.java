package dev.jack.chunkscan;

import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * The miner's decisions, out of the loop.
 *
 * <p>Every bug the unattended build loop ever had lived in four decisions that could not be tested
 * because they were written inline in a method that also opened chests and flew a player. This is
 * the same shape of job, so the same split: the geometry, the fullness rule, the deposit rule, the
 * turn and the escape proof are all plain values here, and the tick that moves a body is the thin
 * part on top.
 */
class MinerTest {

	private static final BlockPos O = new BlockPos(0, 64, 0);

	// ---------------------------------------------------------------- corridor geometry

	@Test
	void aCorridorFaceIsTheTwoCellsABodyOCCUPIES() {
		// Not one, and not three. A one-cell tunnel is not walkable and the miner would cut a
		// corridor it then could not follow; a three-cell one is a third more swinging for nothing.
		List<BlockPos> f = Miner.face(O, Direction.EAST, 1);
		assertEquals(2, f.size());
		assertEquals(f.get(0).above(), f.get(1));
	}

	@Test
	void theStandIsALWAYSWithinReachOfTheFaceItCuts() {
		// The whole advance rests on this: stand one behind, cut the face in front. If it ever came
		// out further than Digger.REACH the miner would guide itself somewhere it cannot work from
		// and the station would stall with nothing to say.
		for (Direction d : Direction.Plane.HORIZONTAL) {
			for (int depth = 1; depth <= 12; depth++) {
				BlockPos stand = Miner.standFor(O, d, depth);
				for (BlockPos c : Miner.face(O, d, depth)) {
					// Eyes are ~1.6 above the feet; the far corner of an adjacent cell is the worst case.
					double dist = Math.sqrt(stand.distSqr(c));
					assertTrue(dist < Digger.REACH, d + " depth " + depth + " is " + dist + " away");
				}
			}
		}
	}

	@Test
	void theBodyStandsInTheCorridorItHasAlreadyCut() {
		// Depth 1's stand is the origin - where the miner was when it started. Every later stand is
		// a cell a previous face made into air, so the miner never has to walk through rock.
		assertEquals(O, Miner.standFor(O, Direction.NORTH, 1));
		for (int depth = 2; depth <= 8; depth++) {
			assertEquals(Miner.face(O, Direction.NORTH, depth - 1).get(0),
				Miner.standFor(O, Direction.NORTH, depth));
		}
	}

	@Test
	void theLookaheadSegmentCoversEveryCellItWillCut() {
		List<BlockPos> seg = Miner.segment(O, Direction.SOUTH, 3, Miner.LOOKAHEAD);
		assertEquals(2 * Miner.LOOKAHEAD, seg.size());
		for (int d = 3; d < 3 + Miner.LOOKAHEAD; d++) {
			assertTrue(seg.containsAll(Miner.face(O, Direction.SOUTH, d)), "depth " + d + " missing");
		}
	}

	@Test
	void theLookaheadReachesFurtherThanTheGuardSOwnRadius() {
		// Otherwise the scan is only ever telling us about rock we have already committed to, and
		// the corridor turns the moment before it breaks into the lava rather than blocks earlier.
		assertTrue(Miner.LOOKAHEAD > LavaGuard.SEGMENT_CLEAR - 1,
			"a lookahead shorter than the clearance is a guard that fires too late to turn");
	}

	// ---------------------------------------------------------------- when the pack is full

	@Test
	void theStashTripStartsBEFOREThePackIsLiterallyFull() {
		// The swing that fills the last slot still drops an ore, and an ore broken with nowhere to
		// put it is one left on the floor of a corridor nobody walks back down.
		assertTrue(Miner.RESERVE_SLOTS >= 1);
		assertTrue(Miner.full(Miner.RESERVE_SLOTS, Miner.RESERVE_SLOTS));
		assertFalse(Miner.full(Miner.RESERVE_SLOTS + 1, Miner.RESERVE_SLOTS));
		assertTrue(Miner.full(0, Miner.RESERVE_SLOTS));
	}

	// ---------------------------------------------------------------- what goes in the chest

	@Test
	void theRuleIsAKEEPListSoSomethingNobodyThoughtOfIsSTILLDeposited() {
		// THE LOAD-BEARING CHOICE. A deposit list silently leaves behind everything nobody listed,
		// which over a night is a pack of gold nuggets and a miner that believes it is full and
		// cannot empty itself. Anything not needed by the job goes in.
		assertFalse(Miner.keep("ancient_debris", false, false, 4, 0));
		assertFalse(Miner.keep("gold_nugget", false, false, 12, 0));
		assertFalse(Miner.keep("quartz", false, false, 64, 0), "quartz is what we came for");
	}

	@Test
	void theToolTheFoodTheBucketAndTheBoxAllStay() {
		assertTrue(Miner.keep("diamond_pickaxe", true, false, 1, 0), "a tool");
		assertTrue(Miner.keep("cooked_beef", false, true, 8, 0), "eating is how the health gate is survived");
		assertTrue(Miner.keep("water_bucket", false, false, 1, 0));
		assertTrue(Miner.keep("bucket", false, false, 1, 0));
		assertTrue(Miner.keep("red_shulker_box", false, false, 1, 0), "a box is storage, not cargo");
	}

	@Test
	void oneStackOfPlugStaysAndTheRestGoesIn() {
		// The plug is what walls you in and what stops a lava face. Keeping all of it would fill the
		// pack with the corridor's own spoil; keeping none leaves the escape with nothing to build.
		assertTrue(Miner.keep(Miner.PLUG, false, false, 64, 0), "the first stack stays");
		assertFalse(Miner.keep(Miner.PLUG, false, false, 64, Miner.PLUG_KEEP), "the second goes in");
	}

	// ---------------------------------------------------------------- turning away from lava

	@Test
	void itTurnsSIDEWAYSBeforeItTurnsBACK() {
		Direction h = Direction.EAST;
		assertEquals(h.getClockWise(), Miner.turn(h, 0));
		assertEquals(h.getCounterClockWise(), Miner.turn(h, 1));
		assertEquals(h.getOpposite(), Miner.turn(h, 2));
	}

	@Test
	void noTurnIsEverTheWayItIsAlreadyGoing() {
		// A "turn" that carries straight on walks back into the lava that caused it, reports a turn,
		// and does it again - a loop with a reassuring message on it.
		for (Direction h : Direction.Plane.HORIZONTAL) {
			for (int i = 0; i < 6; i++) assertNotEquals(h, Miner.turn(h, i), h + " attempt " + i);
		}
	}

	@Test
	void aBoxedInMinerGivesUpRatherThanSpinning() {
		// Three headings exist and TURN_LIMIT is more than three, so every way out is genuinely
		// tried before it stops - and it does stop, rather than turning forever in a dead end.
		assertTrue(Miner.TURN_LIMIT >= 3, "fewer than three and a way out goes untried");
		assertTrue(Miner.TURN_LIMIT < 50, "a limit this high is not a limit");
	}

	// ---------------------------------------------------------------- the escape proof

	@Test
	void anEscapeThatDidNotMoveUsIsNotAnEscape() {
		BlockPos from = new BlockPos(0, 64, 0);
		assertFalse(Miner.moved(from, from.offset(1, 0, 0)), "one block is not a teleport");
		assertFalse(Miner.moved(from, from), "it did not move at all");
		assertTrue(Miner.moved(from, from.offset(500, 0, 500)));
	}

	@Test
	void nothingSentMeansNothingToJudge() {
		// beginEscape nulls the origin when it did NOT send a command, so the landing tick cannot
		// read "we did not move" as "the command is dead" and count a strike against it.
		assertTrue(Miner.moved(null, new BlockPos(0, 64, 0)));
	}

	@Test
	void theEscapeIsProvedTwiceBeforeItIsAbandoned() {
		// A lag spike is one failure. Rally's own number, and for the same reason.
		assertTrue(Miner.DEAD_ESCAPE_LIMIT >= 2, "one bad landing must not retire the escape");
	}

	// ---------------------------------------------------------------- the digger's authorization

	@Test
	void aWorkingAreaDOESNOTAuthorizeTheSameCoordinatesInAnotherDimension() throws Exception {
		// The trap this whole mechanism is built around. A box is coordinates; walk through a
		// portal and the same numbers are somebody's plate. Bounds already lives under this rule
		// and the digger's authorization had to as well.
		try {
			Digger.authorize(new BlockPos(-10, 0, -10), new BlockPos(10, 40, 10), "minecraft:the_nether");
			BlockPos inside = new BlockPos(0, 20, 0);
			assertTrue(Digger.authorizedHere("minecraft:the_nether", inside));
			assertFalse(Digger.authorizedHere("minecraft:overworld", inside),
				"the same cell in another world must not be authorized by a Nether box");
		} finally {
			Digger.clearAuthorization();
		}
	}

	@Test
	void aCellOutsideTheBoxIsNotAuthorizedEvenInTheRightDimension() {
		try {
			Digger.authorize(new BlockPos(-10, 0, -10), new BlockPos(10, 40, 10), "d");
			assertFalse(Digger.authorizedHere("d", new BlockPos(11, 20, 0)), "x");
			assertFalse(Digger.authorizedHere("d", new BlockPos(0, 41, 0)), "y");
			assertFalse(Digger.authorizedHere("d", new BlockPos(0, 20, -11)), "z");
			assertTrue(Digger.authorizedHere("d", new BlockPos(10, 40, 10)), "the corner is inside");
		} finally {
			Digger.clearAuthorization();
		}
	}

	@Test
	void resetTakesTheAuthorizationWithIt() {
		// A design dig must never inherit a miner's box, or the next list digs wherever the last
		// job was allowed to - which is the plot gate defeated by a leftover.
		Digger.authorize(new BlockPos(0, 0, 0), new BlockPos(1, 1, 1), "d");
		assertTrue(Digger.hasAuthorization());
		Digger.reset();
		assertFalse(Digger.hasAuthorization());
		assertFalse(Digger.authorizedHere("d", new BlockPos(0, 0, 0)));
	}

	@Test
	void withNoAreaDeclaredNothingIsAuthorizedAndThePlotGateStillSpeaks() {
		// The fallback has to be the OLD behaviour exactly. If "no area" ever started meaning
		// "anywhere", every design dig in the project would quietly lose its plot gate.
		Digger.clearAuthorization();
		assertFalse(Digger.authorizedHere("d", new BlockPos(0, 0, 0)));
		assertFalse(Digger.hasAuthorization());
	}

	// ---------------------------------------------------------------- rules with no state to read

	private static String source(String cls) throws java.io.IOException {
		String src = java.nio.file.Files.readString(
			java.nio.file.Path.of("src/client/java/dev/jack/chunkscan/" + cls + ".java"),
			java.nio.charset.StandardCharsets.UTF_8);
		src = src.replaceAll("(?s)/\\*.*?\\*/", " ");
		return src.replaceAll("//[^\\n]*", " ");
	}

	@Test
	void theCommentStripperWorks() throws java.io.IOException {
		// Or every check below passes by reading an empty string.
		assertTrue(source("Miner").contains("static boolean running()"), "stripped the code too");
		assertFalse(source("Miner").contains("THE LOAD-BEARING CHOICE"), "did not strip comments");
	}

	@Test
	void theWalkGateAdmitsAMiningDestination() throws java.io.IOException {
		// Without this the miner is correct in every other respect and never takes a step: the gate
		// steers on foot only toward a fetch or a landing, and a mining stand is neither.
		String walk = source("Autopilot");
		assertTrue(walk.contains("Hud.targetMine()"),
			"the walk gate does not know about mining - the miner will stand still");
	}

	@Test
	void theGroundConditionSurvivedTheGateChange() throws java.io.IOException {
		// The gate's real content is "only walk where there is ground". Admitting a third
		// destination must not have taken that with it, or the island's void rule is gone.
		String walk = source("Autopilot");
		assertTrue(walk.contains("groundBelow(mc, p, VOID_LOOK)"),
			"the falling check is what makes walking safe at all");
	}

	@Test
	void theMinerIsNotPersistedAcrossARelog() throws java.io.IOException {
		// A deliberate refusal, not an omission. It holds a box, a heading and a stash position -
		// coordinates, all three - and resuming a job that swings a pickaxe into a world that has
		// moved is the dangerous direction. Typing the command again costs nothing.
		String src = source("Miner");
		assertFalse(src.contains("Session.save"), "the miner must not write a resume note");
		assertFalse(src.contains("Session.load"), "...nor read one");
	}

	@Test
	void everyCellIsCheckedForLavaBeforeTheSwingAndNotOnlyBeforeTheSegment() throws java.io.IOException {
		// Two layers, and the per-swing one is what catches a chunk that loaded since the segment
		// was cleared. A guard that ran only at plan time would be exactly as blind as a human
		// between one plan and the next.
		assertTrue(source("Digger").contains("LavaGuard.touching"),
			"the digger does not check lava per cell - the pre-clear alone is not enough");
	}

	@Test
	void theCorridorTurnsAtTheEDGEOfItsOwnBoxAndNotOnlyAtLava() throws java.io.IOException {
		// Past the boundary the digger answers OFF_PLOT for every cell - correctly - so the plan
		// stays full and no swing ever lands. Before this, only a LAVA threat could turn the
		// corridor, so a miner that reached the edge of its own working area stood there refusing
		// its own work for the rest of the session without saying a word.
		String src = source("Miner");
		assertTrue(src.contains("Digger.authorizedHere(dimension, c)"),
			"nothing turns the corridor at the edge of the box - it will stall there in silence");
	}

	@Test
	void aDropAheadIsBridgedOrTurnedAwayFromRatherThanWalkedInto() throws java.io.IOException {
		// A tunnel breaking into a cavern is the normal way a Nether corridor ends, and what is at
		// the bottom of one is routinely the lava the rest of this class exists to avoid.
		String src = source("Miner");
		assertTrue(src.contains("blocksMotion()"), "the advance does not check for a floor to step onto");
		assertTrue(src.contains("bridgeTries"), "there is no bound on trying to bridge the same drop");
		assertTrue(Miner.BRIDGE_TRIES >= 1 && Miner.BRIDGE_TRIES < 20,
			"a bridge budget of zero never bridges and an unbounded one never turns");
	}

	@Test
	void theDiggerLetsGoOfItsBlockBeforeTheBodyWalksAnywhere() throws java.io.IOException {
		// Nothing ticks the digger while the stash runs, so a target left set stays set - and
		// AutomationControl.blocksMovement pins the body while the digger is busy. That is right for
		// a swing and fatal for a trip: the miner stands at the face with a full pack, unable to walk
		// to the chest it is trying to reach, and no clock in this mod can see it, because nothing is
		// travelling and nothing is failing.
		String src = source("Miner");
		int trip = src.indexOf("stashing = Stash.GOING");
		assertTrue(trip > 0, "the stash trip is gone");
		String before = src.substring(Math.max(0, trip - 400), trip);
		assertTrue(before.contains("Digger.pause(mc)"),
			"the stash trip starts without releasing the block - the body cannot move");
	}

	@Test
	void aRetiredEscapeStopsTheJobRatherThanReportingAnEscapeThatDidNotHappen() throws java.io.IOException {
		// Waiting out the landing after sending nothing reports "out, and stopped" about a body that
		// never went anywhere - the exact shape of reassuring message this project keeps deleting.
		String src = source("Miner");
		assertTrue(src.contains("walled in where it stood"),
			"the fallback does not say what actually happened");
	}

	@Test
	void aDropIntoLavaIsRefusedLikeADropIntoTheVoid() throws java.io.IOException {
		assertTrue(source("Digger").contains("Verdict.OVER_LAVA"),
			"the digger will break blocks whose drops burn");
		assertTrue(source("VoidRisk").contains("Verdict.BURNED"),
			"VoidRisk still walks past lava to the bedrock underneath and calls that a floor");
	}
}
