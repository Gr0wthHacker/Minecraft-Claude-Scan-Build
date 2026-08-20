package dev.jack.chunkscan;

import net.minecraft.core.BlockPos;
import org.junit.jupiter.api.Test;

import java.util.HashSet;
import java.util.List;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * The selection outline. A selection you cannot see is a selection you get wrong, so this is the
 * half of the wand that stops a mis-marked corner becoming a mis-built box.
 */
class WandTest {
	@Test
	void anOutlineIsEdgesOnlyAndNeverTheInterior() {
		// Filling the box would bury whatever is inside it behind a wall of gizmos, which is the
		// opposite of seeing your selection.
		List<BlockPos> o = Wand.outline(new BlockPos(0, 0, 0), new BlockPos(4, 4, 4));
		Set<BlockPos> s = new HashSet<>(o);
		assertTrue(s.contains(new BlockPos(0, 0, 0)));
		assertTrue(s.contains(new BlockPos(4, 4, 4)));
		assertTrue(s.contains(new BlockPos(2, 0, 0)), "mid-edge cells are part of the outline");
		assertFalse(s.contains(new BlockPos(2, 2, 2)), "the centre must not be drawn");
		assertFalse(s.contains(new BlockPos(2, 2, 0)), "a face centre is not an edge");
	}

	@Test
	void everyOutlineCellIsOnAtLeastTwoOfTheThreeExtremes() {
		// That is what "edge" means for a box, and it is the cheapest way to state it.
		for (BlockPos p : Wand.outline(new BlockPos(-3, 7, 11), new BlockPos(5, 9, 20))) {
			int extremes = 0;
			if (p.getX() == -3 || p.getX() == 5) extremes++;
			if (p.getY() == 7 || p.getY() == 9) extremes++;
			if (p.getZ() == 11 || p.getZ() == 20) extremes++;
			assertTrue(extremes >= 2, p + " is not on an edge");
		}
	}

	@Test
	void cornersMayBeGivenInAnyOrder() {
		assertEquals(new HashSet<>(Wand.outline(new BlockPos(5, 9, 20), new BlockPos(-3, 7, 11))),
			new HashSet<>(Wand.outline(new BlockPos(-3, 7, 11), new BlockPos(5, 9, 20))));
	}

	@Test
	void aSingleBlockBoxIsOneCell() {
		assertEquals(List.of(new BlockPos(2, 3, 4)).size(),
			new HashSet<>(Wand.outline(new BlockPos(2, 3, 4), new BlockPos(2, 3, 4))).size());
	}

	@Test
	void aHugeBoxFallsBackToItsEightCorners() {
		// Highlight caps a batch at 512 gizmos and drops the far ones; an outline that blew past
		// that would show as an arbitrary PARTIAL box, which reads as a wrong selection.
		Set<BlockPos> s = new HashSet<>(Wand.outline(new BlockPos(0, 0, 0), new BlockPos(300, 200, 300)));
		assertEquals(8, s.size());
		assertTrue(s.contains(new BlockPos(0, 0, 0)));
		assertTrue(s.contains(new BlockPos(300, 200, 300)));
	}

	@Test
	void theOutlineOfANormalRoomStaysUnderTheGizmoCap() {
		int n = Wand.outline(new BlockPos(0, 0, 0), new BlockPos(30, 8, 30)).size();
		assertTrue(n <= 512, "outline of a 31x9x31 room is " + n + " gizmos");
	}
}
