package dev.jack.chunkscan;

import org.junit.jupiter.api.Test;

import net.minecraft.core.BlockPos;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * The five ways the loop could stand still all night, each read off a real session log.
 *
 * <p>Every one of them has the same shape, and it is the shape worth naming: <b>a decision is
 * re-made, or a watchdog fires, on the two-second recount cadence, before the action it commands
 * has had time to finish - and the recovery it triggers puts the loop back into the state that
 * triggered it.</b> That is a latch, not a hiccup: once entered it cannot be left, because leaving
 * requires the very thing the recovery has just prevented.
 *
 * <p>The measured cost, from {@code 2026-09-08-4.log}: the cycle
 * {@code next spot -> not moving -> giving up -> next spot} ran <b>2,041 times</b> with
 * <b>zero blocks placed</b>, against a design the same session's own analysis reported as having
 * 23,672 placeable cells.
 *
 * <p>Several of these are asserted by reading the source, which is the honest form for a rule whose
 * whole content is "this term is present": there is no state to inspect, and a snapshot of the
 * behaviour would pass a build in which the term had been quietly dropped again.
 */
class StuckLoopTest {

	private static String src(String cls) throws Exception {
		return Files.readString(Path.of("src/client/java/dev/jack/chunkscan/" + cls + ".java"));
	}

	/**
	 * ...with the comments taken out, for the assertions that forbid a call rather than require one.
	 *
	 * <p>A CHECK THAT FORBIDS NAMING A THING FORBIDS EXPLAINING IT. The first version of
	 * {@link #theCoolingOffFallbackDoesNotWipeTheRecord()} failed on the comment left behind to say
	 * why the call had been removed - which is the third time this repo has written that down, and
	 * the second time it has been paid for.
	 */
	private static String code(String cls) throws Exception {
		return src(cls).replaceAll("//[^\\n]*", " ");
	}

	// ---------------------------------------------------------------- the avoid radius

	/**
	 * ONE CONSTANT WAS SERVING TWO OPPOSITE QUESTIONS.
	 *
	 * <p>{@code sameSpot} asks "am I still working the same region", where a wide radius IS the
	 * feature. {@code avoided} asks "is this the spot I just gave up on", where a wide radius is
	 * fatal - and both were passed {@link Plan#MAX_RADIUS}.
	 */
	@Test
	void avoidingOneSpotMustNotAvoidEverySpot() {
		Map<BlockPos, Long> avoided = new HashMap<>();
		long now = 1_000_000L;
		BlockPos gaveUpOn = new BlockPos(0, 204, 0);
		avoided.put(gaveUpOn, now + 60_000);

		// A neighbouring cluster. Clusters form within Loop.NEAR_RADIUS of the body, so this is
		// about as far apart as two spots in one working area can be.
		BlockPos neighbour = new BlockPos(Loop.NEAR_RADIUS * 2, 204, 0);

		assertTrue(Loop.avoided(avoided, gaveUpOn, now, Hud.AVOID_RADIUS),
			"the spot just given up on must still be passed over");
		assertFalse(Loop.avoided(avoided, neighbour, now, Hud.AVOID_RADIUS),
			"a DIFFERENT spot " + (Loop.NEAR_RADIUS * 2) + " blocks away read as the one just"
				+ " abandoned, so the selector found nothing and the fallback handed back the spot"
				+ " that had just failed - 2,041 times in one session");

		// ...and the proof that the radius was the bug, rather than the fallback below it.
		assertTrue(Loop.avoided(avoided, neighbour, now, Plan.MAX_RADIUS),
			"if MAX_RADIUS no longer swallows a neighbouring cluster this test has stopped"
				+ " measuring anything - re-derive it rather than deleting it");
	}

	/** The two radii answer opposite questions and must not drift back together. */
	@Test
	void theAvoidRadiusIsSpotScaleAndTheHysteresisIsRegionScale() {
		assertTrue(Hud.AVOID_RADIUS < Loop.NEAR_RADIUS,
			"an avoid radius at or above the radius clusters form in cannot tell one spot from"
				+ " another: " + Hud.AVOID_RADIUS + " against " + Loop.NEAR_RADIUS);
		assertTrue(Plan.MAX_RADIUS > Loop.NEAR_RADIUS,
			"sameSpot's hysteresis is meant to be wide - it is what stops a drifting centroid"
				+ " reading as a new region on every recount");
	}

	/** Throwing the record away is how the next recount forgets which spot just failed. */
	@Test
	void theCoolingOffFallbackDoesNotWipeTheRecord() throws Exception {
		int from = src("Hud").indexOf("// ...but a hard spot is better than no spot");
		assertTrue(from > 0, "the fallback's own comment has moved - re-anchor this test");
		// ...and then judged on the CODE, or the note explaining the removal reads as the removal
		// not having happened. Offsets differ once comments are stripped, so re-find the anchor.
		String code = code("Hud");
		// The SECOND pass over the clusters is the fallback; the clear stood immediately before it.
		int at = code.indexOf("for (Plan.Cluster c : cl) {", code.indexOf("next = c;"));
		assertTrue(at > 0, "the fallback loop has moved - re-anchor this test");
		String fallback = code.substring(Math.max(0, at - 200), Math.min(code.length(), at + 200));
		assertFalse(fallback.contains("avoided.clear()"),
			"the fallback cleared the whole avoid map, so the NEXT recount had forgotten which"
				+ " spot had just failed and picked it again");
	}

	// ---------------------------------------------------------------- commitment clocks

	/**
	 * A WATCHDOG THAT ASKS ONLY "HAVE I MOVED" FIRES ON A TARGET IT NEVER GAVE A CHANCE.
	 *
	 * <p>Giving up on a spot leaves the body standing still, so every target after the first
	 * inherited an expired clock and was abandoned before the flight could start. The two sibling
	 * watchdogs - the look watchdog and the fetch watchdog - both take
	 * {@code Math.max(movedAt, whenThisTargetWasSet)}. This one did not.
	 */
	@Test
	void aFreshTargetGetsTheWholeClockBeforeItIsGivenUpOn() {
		long now = 1_000_000L;
		long stillSince = now - 60_000;                 // standing still for a minute
		long committedJustNow = now - 200;              // ...but this target is 200ms old

		assertTrue(Loop.goingNowhere(now, stillSince, stillSince, true, false, Hud.NOWHERE_MS),
			"a body still for a minute, with a target a minute old, IS stuck");
		assertFalse(
			Loop.goingNowhere(now, Math.max(stillSince, committedJustNow), stillSince, true, false,
				Hud.NOWHERE_MS),
			"a target committed to 200ms ago was given up on because the BODY had been still"
				+ " longer - which it always has been, because giving up is what left it still");
	}

	/** ...and the call site actually passes the commitment term. */
	@Test
	void theGoingNowhereCallSiteTakesTheCommitmentTerm() throws Exception {
		String s = src("Hud");
		assertTrue(s.contains("Loop.goingNowhere(now, Math.max(movedAt, targetSince)"),
			"the going-nowhere clock is measured on movedAt alone again - it is a latch in that"
				+ " form, because releasing it requires moving and moving requires a target that"
				+ " survives more than zero seconds");
		assertTrue(s.contains("if (where != null && !where.equals(target)) targetSince ="),
			"targetSince must be stamped only when the destination CHANGES: re-stamping it on"
				+ " every re-guide to the same cell means the watchdog can never fire at all");
	}

	// ---------------------------------------------------------------- the chest

	/**
	 * A CELL IS ONLY PROVED BAD FROM INSIDE IT.
	 *
	 * <p>{@code Autopilot.EXACT_ARRIVED} is 1.6 blocks and approach candidates are ONE block apart,
	 * so a body parked near a chest "arrives at" every candidate the instant it is offered. The log
	 * shows 41 "cannot open" against 43 "fetch", alternating about 1.5s apart - one candidate burnt
	 * per recount, and the chest never opened.
	 */
	@Test
	void anApproachCellIsOnlyBlacklistedFromInsideIt() throws Exception {
		String s = src("Hud");
		assertTrue(
			s.contains("boolean parked = (Autopilot.arrivedAt(approach) && me.equals(approach))"),
			"the arrival flag alone blacklists cells the body never entered, and burns through the"
				+ " whole approach grid at recount speed");
		assertTrue(Autopilot.EXACT_ARRIVED > 1.0,
			"this test only matters while the arrival slop is wider than the one-block spacing of"
				+ " the approach candidates; at " + Autopilot.EXACT_ARRIVED + " it is");
	}

	// ---------------------------------------------------------------- the dead end

	/** A dead end is a fact about an ANCHOR. It was being treated as a fact about a DESIGN. */
	@Test
	void aDeadEndLooksForWorkElsewhereBeforeItParks() throws Exception {
		String hud = src("Hud"), analyze = src("Analyze");
		assertTrue(analyze.contains("static Where bestWork("),
			"nothing could answer 'where IS the work' - the reset printed the placeable count and"
				+ " threw the positions away");
		int at = hud.indexOf("case DEAD_END, PACK_FULL ->");
		assertTrue(at > 0, "the dead-end branch has moved - re-anchor this test");
		String branch = hud.substring(at, Math.min(hud.length(), at + 4000));
		assertTrue(branch.contains("Analyze.bestWork("),
			"the dead-end branch parked for two minutes beside 23,672 placeable cells that the"
				+ " same session's analysis had just finished counting");
	}

	// ---------------------------------------------------------------- the reset

	/** A detection that changes no behaviour is not a fix. */
	@Test
	void aTeleportProvenNotToMoveStopsBeingSent() throws Exception {
		String s = src("Rally");
		assertTrue(Rally.DEAD_HOME_LIMIT >= 2,
			"one no-move is a lag spike; the limit must take more than one proof");
		assertTrue(s.contains("if (deadHome >= DEAD_HOME_LIMIT)"),
			"the reset NOTICED that the teleport did not move us, said so, and then ran the"
				+ " analysis and restarted the loop exactly as if it had worked - three times in"
				+ " one session, against byte-identical output, on a doubling backoff");
		assertTrue(s.contains("deadHome = 0;"),
			"the count must clear the moment the teleport works, or one bad minute disables the"
				+ " recovery for the rest of the session");
	}

	// ---------------------------------------------------------------- the printer's report

	/** {@code drainReport} is destructive, and the verdict that consumes it is 600 lines below. */
	@Test
	void thePrintersReportSurvivesAnEarlyReturn() throws Exception {
		String s = src("Hud");
		assertTrue(s.contains("pendingReport[0] += lastReport[0];"),
			"the report was replaced rather than accumulated, so every early return threw away"
				+ " real placements and refusals and the station verdict fell back to the"
				+ " stopwatch - which is the guess the report exists to replace");
		assertTrue(s.contains("int[] rep = pendingReport;")
				&& s.contains("pendingReport = new int[] {0, 0, 0};"),
			"it must be cleared where it is CONSUMED, or it accumulates for ever");
	}
}
