package dev.jack.chunkscan;

import net.minecraft.core.BlockPos;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Where a loaded pack should go, and why the nearest cell is the wrong answer.
 *
 * <p>{@link Analyze#bestOf} is pure over a cell list, an inventory and a position, so the rule that
 * decides every dead-end flight can be argued with here rather than watched in game.
 */
class AnalyzeTest {
	private static final BlockPos ME = new BlockPos(0, 200, 0);

	/** A compact mass of {@code n} cells, centred near (x, y, z). */
	private static List<Work.Cell> blob(String block, int x, int y, int z, int n) {
		List<Work.Cell> out = new ArrayList<>();
		int side = (int) Math.ceil(Math.cbrt(n));
		for (int i = 0; i < side && out.size() < n; i++) {
			for (int j = 0; j < side && out.size() < n; j++) {
				for (int k = 0; k < side && out.size() < n; k++) {
					out.add(new Work.Cell(new BlockPos(x + i, y + j, z + k), block));
				}
			}
		}
		return out;
	}

	/** A wall: long in one axis, so it straddles the binning grid. */
	private static List<Work.Cell> wall(String block, int x, int y, int z, int n) {
		List<Work.Cell> out = new ArrayList<>();
		for (int i = 0; i < n; i++) out.add(new Work.Cell(new BlockPos(x + i, y, z), block));
		return out;
	}

	private static Map<String, Integer> pack(Object... pairs) {
		Map<String, Integer> m = new LinkedHashMap<>();
		for (int i = 0; i < pairs.length; i += 2) m.put((String) pairs[i], (Integer) pairs[i + 1]);
		return m;
	}

	// ---------------------------------------------------------------- the bug Jack flew

	/**
	 * THE FLIGHT THAT STARTED THIS. A full pack of copper and deepslate, and the loop flew sixty-
	 * three blocks to place ONE submerged froglight because it was nearer than the twenty thousand
	 * cells the pack was full of.
	 */
	@Test
	void oneCellNearbyDoesNotBeatARegionOfWorkFurtherOff() {
		List<Work.Cell> cells = new ArrayList<>();
		cells.addAll(blob("ochre_froglight", 60, 201, 0, 1));           // 60 away, one block of work
		cells.addAll(blob("waxed_copper_block", 300, 210, 0, 216));     // 300 away, a building
		Map<String, Integer> have = pack("ochre_froglight", 64, "waxed_copper_block", 1728);

		Analyze.Where w = Analyze.bestOf(cells, have, ME);
		assertNotNull(w);
		assertTrue(w.at().getX() >= 300,
			"it flew to the nearest CELL rather than to the most WORK - one submerged froglight"
				+ " beat a region the pack was full of, then it stalled there and reset");
		assertEquals(216, w.cells(), "the message has to be able to say how much work is there");
	}

	/** ...and the converse, or the fix is just "always cross the park". */
	@Test
	void aMarginalGainDoesNotBuyALongFlight() {
		List<Work.Cell> cells = new ArrayList<>();
		cells.addAll(blob("stone_bricks", 10, 200, 0, 125));            // 10 away
		cells.addAll(blob("stone_bricks", 400, 200, 0, 216));           // 400 away, a little better
		Analyze.Where w = Analyze.bestOf(cells, pack("stone_bricks", 999), ME);
		assertNotNull(w);
		assertTrue(w.at().getX() < 200,
			"a modest gain is not worth four hundred blocks; ENOUGH is the band that says so, and"
				+ " without it the loop would tour the park");
	}

	/**
	 * A CANDIDATE IS A NEIGHBOURHOOD, NOT A BIN. Scored on the bin alone a grid cuts a long wall
	 * into fragments that each look like a poor trip, and a small compact heap wins.
	 */
	@Test
	void aLongWallIsOnePlaceAndNotADozenPoorOnes() {
		List<Work.Cell> cells = new ArrayList<>();
		cells.addAll(blob("stone_bricks", 20, 200, 0, 40));             // near, and small
		cells.addAll(wall("stone_bricks", 400, 200, 0, 400));           // far, and ten times the work
		Analyze.Where w = Analyze.bestOf(cells, pack("stone_bricks", 999), ME);
		assertNotNull(w);
		assertTrue(w.at().getX() >= 400,
			"the wall was binned into " + (400 / Analyze.REGION) + " fragments of about "
				+ Analyze.REGION + " cells each and lost to a heap of 40");
		assertTrue(w.cells() > 40, "scored " + w.cells() + " for four hundred cells of wall");
	}

	// ---------------------------------------------------------------- the cap

	/**
	 * A region is worth what the PACK can put in it. Without the cap a mountain of one material
	 * outranks the place holding everything you are actually carrying.
	 */
	@Test
	void aRegionIsWorthWhatYouCanActuallyPlaceThere() {
		List<Work.Cell> copper = blob("waxed_copper_block", 0, 200, 0, 5000);
		assertEquals(64, Analyze.worth(copper, pack("waxed_copper_block", 64)),
			"five thousand cells is not five thousand blocks of work with one stack in the pack");
		assertEquals(0, Analyze.worth(copper, pack("stone", 640)),
			"a region we hold none of the material for is worth nothing, whatever is in it");
	}

	@Test
	void aRegionYouHoldNothingForIsNeverChosen() {
		// The carried filter is upstream in bestWork; bestOf must not resurrect it by scoring
		// cells at zero and then picking one anyway.
		assertNull(Analyze.bestOf(blob("stone", 5, 200, 0, 50), pack("oak_planks", 64), ME),
			"nothing here is placeable with what is carried - that is a real dead end, and the"
				+ " only kind worth parking on");
		assertNull(Analyze.bestOf(List.of(), pack("stone", 64), ME));
	}

	// ---------------------------------------------------------------- where it aims

	/**
	 * AIM INTO THE MASS, NOT AT ITS NEAR EDGE. The loop's own window is NEAR_RADIUS; an anchor on
	 * the edge of a region covers half of it and re-anchors again on the next recount.
	 */
	@Test
	void itAimsIntoTheMassRatherThanAtItsNearEdge() {
		List<Work.Cell> cells = wall("stone", 200, 200, 0, 40);
		Analyze.Where w = Analyze.bestOf(cells, pack("stone", 999), ME);
		assertNotNull(w);
		assertTrue(w.at().getX() > 205,
			"aimed at " + w.at().getX() + ", which is the cell nearest ME rather than the middle"
				+ " of the work");
		assertTrue(w.at().getX() <= 239, "aimed past the end of the mass at " + w.at().getX());
	}

	/** Two masses a long way apart must not score as one destination. */
	@Test
	void distantMassesAreDifferentPlaces() {
		List<Work.Cell> cells = new ArrayList<>();
		cells.addAll(blob("stone", 40, 200, 0, 27));
		cells.addAll(blob("stone", 4000, 200, 0, 27));
		Analyze.Where w = Analyze.bestOf(cells, pack("stone", 999), ME);
		assertNotNull(w);
		assertEquals(27, w.cells(), "the two ends of the park were counted as one region");
		assertTrue(w.at().getX() < 1000, "and the near one wins on a tie");
	}

	@Test
	void aRegionIsAboutTheSizeOfTheLoopsOwnWindow() {
		// REGION and NEAR_RADIUS are one decision: a destination the loop cannot see the far side
		// of is a destination it re-anchors inside the moment it arrives.
		assertEquals(Loop.NEAR_RADIUS * 2, Analyze.REGION);
		assertTrue(Analyze.ENOUGH > 0 && Analyze.ENOUGH < 1,
			"at 1 nothing but the single best region qualifies and every tie becomes a long"
				+ " flight; at 0 the nearest cell wins again, which is the bug");
	}
}
