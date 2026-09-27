package dev.jack.chunkscan;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * The reset of last resort, without a client.
 *
 * <p>Everything here is a decision {@link Rally} makes before it types anything, which is the half
 * that can be got wrong quietly: a backoff that does not grow is an infinite loop with a teleport
 * in it, and a "lost" test that fires on ordinary distance teleports the loop away from work it
 * could have flown to.
 */
class RallyTest {

	@Test
	void aFruitlessResetWaitsLongerEachTime() {
		long first = Rally.cooldownFor(0);
		long second = Rally.cooldownFor(1);
		long third = Rally.cooldownFor(2);
		assertEquals(Rally.BASE_COOL_MS, first);
		assertTrue(second > first, "the second reset in a row waited " + second + ", not longer than " + first);
		assertTrue(third > second);
	}

	@Test
	void theBackoffIsCapped() {
		// PAST THE CAP IT IS NOT A BUILD SESSION, it is a thing typing a command at the sky. The
		// cap is what stops the interval growing to hours and the loop looking dead.
		assertEquals(Rally.MAX_COOL_MS, Rally.cooldownFor(50));
		assertEquals(Rally.MAX_COOL_MS, Rally.cooldownFor(1000));
	}

	@Test
	void aBlockPlacedSinceTheLastResetMeansItWorked() {
		// The only honest evidence, exactly as it is for every clock in Loop.
		assertTrue(Rally.worked(41, 40));
		assertFalse(Rally.worked(40, 40));
		assertTrue(Rally.worked(0, -1), "no reset yet must not count as a failed one");
	}

	@Test
	void theCooldownIsHonoured() {
		assertFalse(Rally.ready(1_000, 5_000));
		assertTrue(Rally.ready(5_000, 5_000));
		assertTrue(Rally.ready(9_000, 5_000));
	}

	@Test
	void ordinaryDistanceIsNotBeingLost() {
		// The loop flies to work hundreds of blocks away all session. What LOST means is "no route
		// can even be searched for", which is why the threshold is twice Nav.MAX_RANGE.
		long now = 1_000_000;
		assertFalse(Rally.lost(300, now, now - 600_000, Rally.LOST_MS));
		assertFalse(Rally.lost(Nav.MAX_RANGE, now, now - 600_000, Rally.LOST_MS));
		assertTrue(Rally.LOST_AT > Nav.MAX_RANGE,
			"a leg the router could plan reads as lost: " + Rally.LOST_AT + " vs " + Nav.MAX_RANGE);
	}

	@Test
	void beingOnTheWrongIslandIsBeingLost() {
		long now = 1_000_000;
		assertTrue(Rally.lost(121_000, now, now - Rally.LOST_MS, Rally.LOST_MS));
	}

	@Test
	void oneFarReadingIsNotEvidence() {
		// A recount taken mid-teleport, or while a chunk loads, measures far and means nothing.
		long now = 1_000_000;
		assertFalse(Rally.lost(121_000, now, now, Rally.LOST_MS), "fired on the first reading");
		assertFalse(Rally.lost(121_000, now, 0, Rally.LOST_MS), "fired with no clock running");
	}

	@Test
	void comingBackWithinRangeStopsTheClock() {
		long now = 1_000_000;
		assertFalse(Rally.noteDistance(2_000, now), "fired on the first far reading");
		assertFalse(Rally.noteDistance(10, now + 1_000), "still far after coming back");
		// ...and the clock started again from here, so the old far reading cannot fire it late.
		assertFalse(Rally.noteDistance(2_000, now + 2_000));
		assertTrue(Rally.noteDistance(2_000, now + 2_000 + Rally.LOST_MS));
		Rally.clearSession();
	}

	@Test
	void theHomeCommandIsTypedWithoutItsSlash() {
		// `sendCommand` prepends nothing, so a leading slash is sent as part of the command NAME
		// and the server sees `//visit`.
		assertEquals("visit enroz", Rally.normalise("/visit enroz"));
		assertEquals("visit enroz", Rally.normalise("  visit   enroz  "));
		assertEquals("visit enroz", Rally.normalise("//visit enroz"));
		assertEquals("is", Rally.normalise("/is"));
	}

	@Test
	void theDefaultHomeIsWhereTheWorkIsAndNotYourOwnIsland() {
		// `/is` on a fleet of alts lands on the ALT's island - a bare starter pad 121,000 blocks
		// from the park - which is the way the loop most reliably loses its location. If this ever
		// reads "is" again, the rescue has become the fault it was written to fix.
		assertFalse(Rally.DEFAULT_HOME.equals("is"));
		assertEquals("visit enroz", Rally.DEFAULT_HOME);
	}

	@Test
	void aFreshSessionForgetsTheBackoffButNotTheSetting() {
		Rally.clearSession();
		assertEquals(0, Rally.resets());
		assertEquals(0, Rally.fruitless());
		assertFalse(Rally.pending());
		assertEquals(0, Rally.readyIn(System.currentTimeMillis()));
		assertFalse(Rally.home().isBlank(), "a session reset wiped the home command");
	}

	@Test
	void theLandingIsLongEnoughForTheWorldToArrive() {
		// Nothing may be decided on the tick a teleport lands: most of the world is unloaded, Nav
		// treats unloaded as passable, and the first question the loop asks afterwards is "is the
		// work unreachable" - which would answer yes about every chunk still on its way.
		assertTrue(Rally.LANDING_TICKS >= Session.GRACE_TICKS,
			"a reset landing gets less time than a join does");
	}

	@Test
	void aStallIsGivenMoreThanOneChanceBeforeTheLoopIsReset() {
		// A single 90-second stall is an awkward spot and the next spot fixes it. Resetting on the
		// first would teleport the loop away from work it was about to reach.
		assertTrue(Hud.STALLS_BEFORE_RESET >= 2);
	}

	// ------------------------------------------------------------------ the source-level rules
	//
	// These assert the ABSENCE of something, and there is no state to look at, so the source IS
	// the artefact - the same technique the "no key interrupts it" rule already lives under.
	// Comments are stripped first, or a test that forbids naming a thing also forbids explaining
	// why it is absent, which is the more valuable half.

	private static String source(String cls) throws java.io.IOException {
		String src = java.nio.file.Files.readString(
			java.nio.file.Path.of("src/client/java/dev/jack/chunkscan/" + cls + ".java"),
			java.nio.charset.StandardCharsets.UTF_8);
		src = src.replaceAll("(?s)/\\*.*?\\*/", " ");     // block comments and javadoc
		return src.replaceAll("//[^\\n]*", " ");            // line comments
	}

	@Test
	void theCommentStripperWorks() throws java.io.IOException {
		// Or every check below passes by reading an empty string, which is the classic way for a
		// source-level assertion to be quietly vacuous.
		assertTrue(source("Autopilot").contains("static void resetRecovery()"), "stripped the code too");
		assertFalse(source("Autopilot").contains("THE TOP RUNG IS A RESET"), "did not strip comments");
	}

	@Test
	void theRecoveryLaddersTopRungNoLongerTypesTheWrongTeleport() throws java.io.IOException {
		// `/is` on an alt lands on the ALT's island. The rung that exists to rescue a stuck flight
		// was the way it most reliably ended up 121,000 blocks from the work, holding a shopping
		// list made beside a chest that is no longer there. It asks for a reset instead.
		String src = source("Autopilot");
		int from = src.indexOf("private static boolean recover(");
		assertTrue(from > 0, "recover() has been renamed - this rule needs re-pointing");
		String ladder = src.substring(from);
		int end = ladder.indexOf("static float approach(");
		if (end > 0) ladder = ladder.substring(0, end);
		assertFalse(ladder.contains("sendCommand(\"is\")"),
			"the recovery ladder types /is again - see Rally");
		assertTrue(ladder.contains("Hud.rally("), "the top rung no longer asks for a reset");
	}

	@Test
	void theFallRescueKEEPSItsOwnTeleport() throws java.io.IOException {
		// The other half, and it must not be "tidied up" to match: a fall is the whole inventory,
		// `/is` cannot fail, and a `/visit` can (a closed island, a name that has changed). Landing
		// on the wrong island is survivable and the lost-location check brings us back; falling
		// past the bottom of the world is not.
		assertTrue(source("Autopilot").contains("sendCommand(\"is\")"),
			"the fall rescue lost its /is - a rescue that can fail is not a rescue");
	}

	@Test
	void theDeadEndAndTheThrashNoLongerEndTheSession() throws java.io.IOException {
		// Jack: "make it highly crash resistant so its always doing things". Both of these used to
		// set following = false and wait for somebody to type.
		String src = source("Hud");
		int deadEnd = src.indexOf("DEAD_END_STOP_MS");
		int lastUse = src.lastIndexOf("DEAD_END_STOP_MS");
		assertTrue(deadEnd > 0 && lastUse > deadEnd);
		assertTrue(src.substring(deadEnd, Math.min(src.length(), lastUse + 400)).contains("rally("),
			"a two-minute dead end does not ask for a reset");
		int thrash = src.indexOf("Loop.thrashing(");
		assertTrue(thrash > 0);
		assertTrue(src.substring(thrash, Math.min(src.length(), thrash + 900)).contains("rally("),
			"thrashing does not ask for a reset");
	}
}
