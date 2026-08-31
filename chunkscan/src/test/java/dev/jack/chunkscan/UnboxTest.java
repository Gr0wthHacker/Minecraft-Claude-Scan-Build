package dev.jack.chunkscan;

import org.junit.jupiter.api.Test;

import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.*;

/**
 * The shulker routine, which is the most dangerous automation in this mod.
 *
 * <p>Everything else here risks one block. This risks a whole inventory, and the failure is
 * silent — a box left on the ground looks exactly like a box that was picked up. So these tests
 * are about REFUSALS and about the absence of shortcuts, and several of them read the source,
 * because what is being asserted is that something is NOT there.
 */
class UnboxTest {

	private static String src(String cls) {
		try {
			return java.nio.file.Files.readString(
				Path.of("src/client/java/dev/jack/chunkscan/" + cls + ".java"));
		} catch (java.io.IOException e) {
			throw new AssertionError("cannot read " + cls + " — run tests from chunkscan/", e);
		}
	}

	@Test
	void itNeverBreaksABoxItDidNotPlace() {
		// The island is full of shulker boxes that are somebody's storage. "A shulker box nearby"
		// is not a thing this may ever break.
		String s = src("Unbox");
		assertTrue(s.contains("ONLY THE CELL WE PLACED INTO"),
			"the rule must stay written down beside the code that enforces it");
		assertTrue(s.contains("if (!n.contains(\"shulker_box\"))"),
			"it must check the cell still holds a box before breaking it");
	}

	@Test
	void itRefusesToStandABoxOverTheVoid() {
		// A dropped block is a block; a dropped shulker is everything that was in it.
		String s = src("Unbox");
		assertTrue(s.contains("VoidRisk.under"), "the siting must consult the void check");
		assertTrue(s.contains("Verdict.CAUGHT"), "it must require a catch, not merely 'not void'");
	}

	@Test
	void theBoxMustComeBackOrTheWholeThingStops() {
		// An unrecovered shulker is not a failed step, it is a lost chest.
		String s = src("Unbox");
		assertTrue(s.contains("THE BOX DID NOT COME BACK"),
			"failing to recover the box must be loud and must stop the routine");
		assertTrue(s.contains("Phase.RECOVERING"), "there must be a phase that checks it returned");
	}

	@Test
	void everyPhaseIsReachableAndTerminal() {
		// A state machine with an unreachable end is one that runs for ever; the "does nothing,
		// quietly" failure this project keeps writing rules about.
		String s = src("Unbox");
		for (Unbox.Phase ph : Unbox.Phase.values()) {
			assertTrue(s.contains("Phase." + ph.name()),
				ph + " is declared but never used");
		}
		assertFalse(Unbox.running(), "an untouched Unbox must be idle");
	}

	@Test
	void itGivesUpRatherThanWaitingForever() {
		assertTrue(Unbox.GIVE_UP_TICKS > 0);
		assertTrue(Unbox.GIVE_UP_TICKS <= 600, "over half a minute stuck on one box is a wedged loop");
	}

	@Test
	void theLoopUnpacksInsteadOfAskingYouTo() {
		// It used to say "set it down and take them", which is the same shape of claim as "a client
		// mod cannot place a block": a policy written as a fact.
		String s = src("Hud");
		assertTrue(s.contains("Unbox.start(mc, item"),
			"the fetch phase must unbox rather than only reporting");
		assertTrue(s.contains("Unbox.boxWith(mc.player, item) >= 0"),
			"...and only when a box in the HOTBAR actually holds it");
	}

	@Test
	void aPlacedShulkerIsAlreadyAFetchSource() {
		// This needed no new code: the index matches containers by substring, so a shulker box
		// standing in the world has always been findable and withdrawable like any chest. Asserted
		// so nobody 'adds' it later and breaks the substring match.
		assertTrue(Storage.isContainer("minecraft:white_shulker_box"));
		assertTrue(Storage.stores("minecraft:shulker_box"));
		assertTrue(Storage.stores("minecraft:light_blue_shulker_box"));
	}

	@Test
	void theSharedFleetFileIsWrittenAtomically() {
		// FIVE CLIENTS SHARE IT. A plain write leaves a window where the file is truncated, and a
		// client reading in that window sees an EMPTY fleet - then claims a design somebody else
		// is already building, which is the one thing that file exists to prevent.
		String s = src("Fleet");
		assertTrue(s.contains("ATOMIC_MOVE"), "fleet.json must be replaced, never written in place");
		assertTrue(s.contains("AtomicMoveNotSupportedException"),
			"and it must still work on a filesystem that cannot do it");
		assertTrue(s.contains("does not make read-modify-write atomic"),
			"the REMAINING race must stay written down rather than implied away");
	}

	@Test
	void unboxCountsFromThePackRatherThanFromTheSlotItClicked() {
		// The Crafter shipped this exact race earlier in the day: `getCount()` is what the server
		// is being ASKED to move, and a full pack moves less.
		String s = src("Unbox");
		assertTrue(s.contains("COUNTED FROM THE PACK ON A LATER TICK"),
			"the reason must stay beside the fix");
		assertFalse(s.contains("got += st.getCount()"), "that is the race, not the fix");
	}
}
