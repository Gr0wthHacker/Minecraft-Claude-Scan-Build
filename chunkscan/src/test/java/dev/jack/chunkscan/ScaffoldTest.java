package dev.jack.chunkscan;

import net.minecraft.core.BlockPos;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Cells with nothing to place against. You cannot put a block in mid-air — it needs a face to click
 * — and the alternative to knowing is finding out with a shulker in your hand.
 *
 * <p>The rule that makes this useful rather than noisy: the worklist is sorted BOTTOM-UP, so a wall
 * builds against itself course by course and only its first block needs something under it. Ignoring
 * that would flag most of every design.
 */
class ScaffoldTest {
	private static Work.Cell cell(int x, int y, int z) {
		return new Work.Cell(new BlockPos(x, y, z), "stone_bricks");
	}

	/** A world where only the listed positions are solid. */
	private static Work.Solid world(BlockPos... solid) {
		Set<Long> s = new HashSet<>();
		for (BlockPos p : solid) s.add(p.asLong());
		return p -> s.contains(p.asLong());
	}

	@Test
	void aCellInOpenAirNeedsScaffolding() {
		assertTrue(Work.needsScaffold(world(), cell(0, 100, 0), Set.of()));
	}

	@Test
	void aCellOnTheGroundDoesNot() {
		assertFalse(Work.needsScaffold(world(new BlockPos(0, 99, 0)), cell(0, 100, 0), Set.of()));
	}

	@Test
	void anyOfTheSixFacesWillDo() {
		// You can click the side of a block as readily as its top.
		for (BlockPos n : new BlockPos[]{new BlockPos(1, 100, 0), new BlockPos(-1, 100, 0),
		                                 new BlockPos(0, 101, 0), new BlockPos(0, 99, 0),
		                                 new BlockPos(0, 100, 1), new BlockPos(0, 100, -1)}) {
			assertFalse(Work.needsScaffold(world(n), cell(0, 100, 0), Set.of()), "neighbour " + n);
		}
	}

	@Test
	void aTowerBuildsAgainstItselfAndOnlyItsFootIsFlagged() {
		// THE RULE THAT MAKES THIS USABLE. Without it, every cell above the first would be reported
		// as floating and the check would be worthless.
		List<Work.Cell> todo = new ArrayList<>();
		for (int y = 100; y < 110; y++) todo.add(cell(0, y, 0));
		List<Work.Cell> air = Work.floating(world(), todo);
		assertEquals(1, air.size());
		assertEquals(100, air.get(0).pos().getY(), "only the foot of the tower is the problem");
	}

	@Test
	void aTowerStandingOnGroundIsEntirelyFine() {
		List<Work.Cell> todo = new ArrayList<>();
		for (int y = 100; y < 110; y++) todo.add(cell(0, y, 0));
		assertTrue(Work.floating(world(new BlockPos(0, 99, 0)), todo).isEmpty());
	}

	@Test
	void buildOrderDecidesWhetherAGroundedColumnIsFlaggedAtAll() {
		// Any EARLIER neighbour gives you a face, including the one above - you can place a block
		// under an existing one by clicking its underside. So a top-down column is self-supporting
		// too, and only its FIRST cell is ever the question.
		//
		// Which is exactly why `Work.split` sorts bottom-up: start at the ground and the first cell
		// has the ground to stand on, so nothing is flagged. Start at the top and that same column,
		// over that same ground, reports one cell floating - because at the moment you place it,
		// it is.
		List<Work.Cell> down = new ArrayList<>();
		for (int y = 109; y >= 100; y--) down.add(cell(0, y, 0));
		List<Work.Cell> up = new ArrayList<>();
		for (int y = 100; y < 110; y++) up.add(cell(0, y, 0));
		Work.Solid ground = world(new BlockPos(0, 99, 0));

		assertEquals(1, Work.floating(ground, down).size(), "top-down starts in mid-air");
		assertEquals(109, Work.floating(ground, down).get(0).pos().getY());
		assertTrue(Work.floating(ground, up).isEmpty(), "bottom-up starts on the ground");
	}

	@Test
	void twoSeparatePiecesAreEachFlaggedOnce() {
		List<Work.Cell> todo = new ArrayList<>();
		for (int y = 100; y < 103; y++) todo.add(cell(0, y, 0));
		for (int y = 100; y < 103; y++) todo.add(cell(20, y, 20));
		assertEquals(2, Work.floating(world(), todo).size());
	}

	@Test
	void anUnloadedNeighbourCountsAsSolid() {
		// Claiming a cell needs scaffolding because the chunk behind it is not loaded would send
		// you to build a tower against terrain that is already there. `solidIn` treats unloaded as
		// solid; this pins the intent at the interface level.
		Work.Solid allUnloaded = p -> true;
		assertFalse(Work.needsScaffold(allUnloaded, cell(0, 100, 0), Set.of()));
	}
}
