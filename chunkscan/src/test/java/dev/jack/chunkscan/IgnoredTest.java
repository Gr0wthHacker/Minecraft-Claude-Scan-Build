package dev.jack.chunkscan;

import net.minecraft.core.BlockPos;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Places that have failed twice.
 *
 * <p>Every other watchdog in this loop is a TIMER, and a timer forgets — which is right for a world
 * that changes, and wrong for a place that has beaten the router twice. The loop returning to it for
 * ever is both the infinite loop and the message spam; they are one fault seen from two angles.
 */
class IgnoredTest {
	@BeforeEach
	void clean() {
		Ignored.clear();
	}

	@Test
	void oneFailureIsABadMoment() {
		// A chunk that had not arrived, a block the printer had just placed, a route computed from
		// the wrong side of a wall. Writing a place off for one of those would shrink the island for
		// no reason.
		BlockPos at = new BlockPos(100, 64, 100);
		assertFalse(Ignored.strike(at), "wrote a place off on its first failure");
		assertFalse(Ignored.has(at));
		assertEquals(0, Ignored.count());
	}

	@Test
	void twoIsAProperty() {
		BlockPos at = new BlockPos(100, 64, 100);
		Ignored.strike(at);
		assertTrue(Ignored.strike(at), "the second strike did not report writing it off");
		assertTrue(Ignored.has(at));
		assertEquals(1, Ignored.count());
	}

	@Test
	void itIsReportedOnceRatherThanForEver() {
		// The strike that writes a place off returns true exactly once, so the caller can say so and
		// then stop talking about it. Repeating the message is the spam Jack asked to remove.
		BlockPos at = new BlockPos(100, 64, 100);
		Ignored.strike(at);
		assertTrue(Ignored.strike(at));
		assertFalse(Ignored.strike(at), "announced the same place a third time");
		assertFalse(Ignored.strike(at));
	}

	@Test
	void aPLACEIsNotACOORDINATE() {
		// The loop aims at a centroid that drifts as cells are placed, so a per-cell list would
		// never see the same failure twice - it would collect near-misses for ever and ignore
		// nothing. An area is about the size of a spot the flight can fail to reach for one reason.
		BlockPos first = new BlockPos(100, 64, 100);
		BlockPos drifted = new BlockPos(102, 65, 101);       // the same place, two blocks over
		Ignored.strike(first);
		assertTrue(Ignored.strike(drifted), "a centroid that moved two blocks read as somewhere new");
		assertTrue(Ignored.has(first));
		assertTrue(Ignored.has(drifted));
	}

	@Test
	void somewhereElseIsSomewhereElse() {
		Ignored.strike(new BlockPos(100, 64, 100));
		Ignored.strike(new BlockPos(100, 64, 100));
		assertFalse(Ignored.has(new BlockPos(140, 64, 100)), "wrote off the whole island");
		assertFalse(Ignored.has(new BlockPos(100, 140, 100)), "ignored by column rather than by area");
	}

	@Test
	void theAreaIsBigEnoughToHoldASpotAndSmallEnoughToBeOne() {
		assertTrue(Ignored.AREA >= 4, "smaller than the drift of the centroid it is tracking");
		assertTrue(Ignored.AREA <= 16, "a whole chunk written off because one corner of it failed");
	}

	@Test
	void everyIgnoredPlaceCanBeDrawn() {
		// Seeing the red is the point: a loop that silently stops trying somewhere is a loop you
		// cannot argue with.
		Ignored.strike(new BlockPos(100, 64, 100));
		Ignored.strike(new BlockPos(100, 64, 100));
		Ignored.strike(new BlockPos(300, 64, 300));          // one strike: not yet
		assertEquals(1, Ignored.marks().size());
		BlockPos mark = Ignored.marks().get(0);
		assertTrue(Ignored.has(mark), "the mark is not inside the area it marks");
	}

	@Test
	void clearingPutsEverythingBackOnTheTable() {
		Ignored.strike(new BlockPos(100, 64, 100));
		Ignored.strike(new BlockPos(100, 64, 100));
		Ignored.clear();
		assertEquals(0, Ignored.count());
		assertFalse(Ignored.has(new BlockPos(100, 64, 100)));
	}
}
