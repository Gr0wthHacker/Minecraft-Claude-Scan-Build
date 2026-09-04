package dev.jack.chunkscan;

import net.minecraft.core.BlockPos;
import org.junit.jupiter.api.Test;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Consolidation. Measured off the real index: 206 of 244 distinct items live in more than one
 * container, white wool is 12,729 spread over 27 chests, and 37 items have eight or fewer in total
 * and are still split.
 */
class TidyTest {
	private static Storage.Container box(int id, int x, int z, Object... itemsAndCounts) {
		Storage.Container c = new Storage.Container();
		c.id = id;
		c.x = x;
		c.y = 100;
		c.z = z;
		c.block = "chest";
		for (int i = 0; i < itemsAndCounts.length; i += 2) {
			c.items.put("minecraft:" + itemsAndCounts[i], (Integer) itemsAndCounts[i + 1]);
		}
		return c;
	}

	private static Map<String, Storage.Container> index(Storage.Container... cs) {
		Map<String, Storage.Container> m = new LinkedHashMap<>();
		for (Storage.Container c : cs) m.put(c.key(), c);
		return m;
	}

	@Test
	void theHomeIsWhereMostOfItAlreadyIs() {
		// Moving 200 into a chest holding 12,000 beats moving 12,000 into a chest holding 200, and
		// picking the nearest container instead would routinely choose the second.
		var idx = index(box(1, 0, 0, "white_wool", 64), box(2, 40, 40, "white_wool", 4000));
		List<Tidy.Job> jobs = Tidy.plan(idx, BlockPos.ZERO);
		assertEquals(1, jobs.size());
		assertEquals(2, jobs.get(0).home().id, "picked the smaller pile as home");
		assertEquals(64, jobs.get(0).toMove());
	}

	@Test
	void oneContainerIsAlreadyTidy() {
		assertTrue(Tidy.plan(index(box(1, 0, 0, "white_wool", 4000)), BlockPos.ZERO).isEmpty());
	}

	@Test
	void aTinyPileIsNotWorthATrip() {
		// Two chests holding four sticks between them is not a problem to solve.
		var idx = index(box(1, 0, 0, "stick", 2), box(2, 9, 9, "stick", 2));
		assertTrue(Tidy.plan(idx, BlockPos.ZERO).isEmpty());
	}

	@Test
	void rankedBySlotsFreedNotByItemCount() {
		// 12,000 wool in two chests and 12,000 in twenty-seven are the same pile; only the second
		// is a mess. Slots freed is what measures the difference.
		var idx = index(
			box(1, 0, 0, "white_wool", 6000), box(2, 5, 0, "white_wool", 6000),
			box(3, 0, 5, "redstone", 40), box(4, 1, 5, "redstone", 40),
			box(5, 2, 5, "redstone", 40), box(6, 3, 5, "redstone", 40));
		List<Tidy.Job> jobs = Tidy.plan(idx, BlockPos.ZERO);
		assertEquals("redstone", jobs.get(0).item(),
			"four fragments of redstone free more slots than one clean split of wool");
	}

	@Test
	void slotsFreedIsTheRealSaving() {
		// Four chests with 40 redstone each: 4 slots now, 160 total needs 3 -> 1 freed.
		var idx = index(box(1, 0, 0, "redstone", 40), box(2, 1, 0, "redstone", 40),
			box(3, 2, 0, "redstone", 40), box(4, 3, 0, "redstone", 40));
		Tidy.Job j = Tidy.plan(idx, BlockPos.ZERO).get(0);
		assertEquals(160, j.total());
		assertEquals(1, j.slotsFreed());
		assertEquals(3, j.sources().size());
	}

	@Test
	void sourcesAreNearestFirst() {
		var idx = index(box(1, 0, 0, "cobblestone", 5000),
			box(2, 80, 80, "cobblestone", 100), box(3, 6, 6, "cobblestone", 100));
		Tidy.Job j = Tidy.plan(idx, BlockPos.ZERO).get(0);
		assertEquals(3, j.sources().get(0).id, "did not start with the nearest source");
	}

	@Test
	void aContainerEmptiedCompletelyIsCounted() {
		// The real prize: chests you get back, not just slots.
		var idx = index(box(1, 0, 0, "white_wool", 4000), box(2, 5, 0, "white_wool", 200));
		List<Tidy.Job> jobs = Tidy.plan(idx, BlockPos.ZERO);
		assertEquals(1, Tidy.containersFreed(jobs, idx), "chest 2 holds nothing else and empties");
	}

	@Test
	void aContainerHoldingSomethingElseIsNotFreed() {
		var idx = index(box(1, 0, 0, "white_wool", 4000),
			box(2, 5, 0, "white_wool", 200, "diamond", 3));
		List<Tidy.Job> jobs = Tidy.plan(idx, BlockPos.ZERO);
		assertEquals(0, Tidy.containersFreed(jobs, idx));
	}

	@Test
	void nonContainersAreIgnored() {
		Storage.Container sign = box(9, 0, 0, "white_wool", 500);
		sign.block = "oak_wall_sign";
		var idx = index(sign, box(1, 5, 0, "white_wool", 500));
		assertTrue(Tidy.plan(idx, BlockPos.ZERO).isEmpty(), "a sign is not a container");
	}
}
