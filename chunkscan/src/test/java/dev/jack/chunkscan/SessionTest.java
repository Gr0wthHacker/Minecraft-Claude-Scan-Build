package dev.jack.chunkscan;

import org.junit.jupiter.api.Test;

import java.nio.file.Files;
import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * The loop's intent, written down so a dropped connection does not end it.
 *
 * <p>Everything the build loop knows lives in static fields, which is fine until the connection
 * drops at three in the morning — and then a loop whose entire purpose is running unattended has
 * stopped, silently, and will not start again until someone types.
 */
class SessionTest {
	@Test
	void itSurvivesTheRoundTrip() throws Exception {
		Path d = Files.createTempDirectory("cscan-session");
		Session.save(d, new Session.State("Deck Floor", true, true, 0.42));
		Session.State got = Session.load(d);
		assertEquals("Deck Floor", got.design());
		assertTrue(got.autofly());
		assertTrue(got.all());
		assertEquals(0.42, got.speed(), 0.0001);
	}

	@Test
	void noNoteMeansNothingToResume() throws Exception {
		Path d = Files.createTempDirectory("cscan-session");
		assertNull(Session.load(d), "invented a session out of an empty folder");
	}

	@Test
	void aCorruptNoteIsNotAResume() throws Exception {
		// It is written by a loop that may have been killed mid-write. Half a file must read as
		// "nothing to resume" rather than throwing on the join event and taking the mod with it.
		Path d = Files.createTempDirectory("cscan-session");
		Files.writeString(Session.file(d), "{\"design\": ");
		assertNull(Session.load(d));
	}

	@Test
	void stoppingClearsIt() throws Exception {
		// STOP MEANS STOP, INCLUDING AFTER A RELOG. Leaving the note behind would have the loop
		// start itself again next time you joined, which is the one thing a panic button must not do.
		Path d = Files.createTempDirectory("cscan-session");
		Session.save(d, new Session.State("Deck Floor", true, false, 0.7));
		Session.clear(d);
		assertNull(Session.load(d));
		assertFalse(Files.exists(Session.file(d)));
	}

	@Test
	void aStoppedLoopRestoresTheSpeedButNotTheFollowing() throws Exception {
		// `follow off` records no design, so the next join picks up the dial and nothing else. The
		// speed is a preference; the following is an action, and only one of those should resume.
		Path d = Files.createTempDirectory("cscan-session");
		Session.save(d, new Session.State(null, false, false, 0.9));
		Session.State got = Session.load(d);
		assertNull(got.design());
		assertEquals(0.9, got.speed(), 0.0001);
	}

	@Test
	void theGraceIsLongEnoughForTheWorldToArrive() {
		// On the tick you join, most of the world is unloaded - and Nav counts unloaded as passable,
		// which is right for a route already in progress and quite wrong as the first thing you do.
		assertTrue(Session.GRACE_TICKS >= 40, "starts routing before the chunks are there");
	}
}
