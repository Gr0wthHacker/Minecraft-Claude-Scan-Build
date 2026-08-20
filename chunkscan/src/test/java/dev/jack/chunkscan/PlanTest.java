package dev.jack.chunkscan;

import net.minecraft.core.BlockPos;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * "Where can I stand right now and place a lot" — the question `next` and `need` both fail to answer.
 *
 * <p>The number that matters is {@code doable()}, and it is the easiest one to get flatteringly
 * wrong: count every nearby cell and a cluster promises 120 placements to a player carrying 64
 * bricks. Stock is therefore allocated in rank order, so the second cluster is told what the first
 * one leaves it.
 */
class PlanTest {
	private static Work.Cell cell(int x, int y, int z, String block) {
		return new Work.Cell(new BlockPos(x, y, z), block);
	}

	private static Map<String, Integer> carrying(Object... kv) {
		Map<String, Integer> m = new LinkedHashMap<>();
		for (int i = 0; i < kv.length; i += 2) m.put((String) kv[i], (Integer) kv[i + 1]);
		return m;
	}

	/** A tight blob of `n` cells around a point, well inside one working radius. */
	private static List<Work.Cell> blob(int cx, int cy, int cz, int n, String block) {
		List<Work.Cell> out = new ArrayList<>();
		int i = 0;
		for (int dx = -2; dx <= 2 && out.size() < n; dx++) {
			for (int dy = -1; dy <= 1 && out.size() < n; dy++) {
				for (int dz = -2; dz <= 2 && out.size() < n; dz++) {
					out.add(cell(cx + dx, cy + dy, cz + dz, block));
					i++;
				}
			}
		}
		return out;
	}

	@Test
	void cellsYouAreNotCarryingAreNotWork() {
		// That is `need`'s question. Offering them here sends you to stand in front of a wall you
		// cannot build.
		List<Work.Cell> todo = blob(0, 100, 0, 20, "stone_bricks");
		assertTrue(Plan.clusters(todo, carrying("deepslate_bricks", 640), Set.of(), BlockPos.ZERO).isEmpty());
		assertFalse(Plan.clusters(todo, carrying("stone_bricks", 640), Set.of(), BlockPos.ZERO).isEmpty());
	}

	@Test
	void stockIsAllocatedInRankOrderSoTheSecondClusterKnowsWhatIsLeft() {
		// THE NUMBER THAT MATTERS. Two piles of 20, carrying 25: the first gets 20, the second is
		// told it is 15 short - not that it has 20 waiting.
		List<Work.Cell> todo = new ArrayList<>(blob(0, 100, 0, 20, "stone_bricks"));
		todo.addAll(blob(60, 100, 60, 20, "stone_bricks"));
		List<Plan.Cluster> cl = Plan.clusters(todo, carrying("stone_bricks", 25), Set.of(), BlockPos.ZERO);
		assertEquals(2, cl.size());
		assertEquals(25, cl.stream().mapToInt(Plan.Cluster::doable).sum(),
			"the plan cannot promise more placements than you have blocks");
		assertTrue(cl.get(1).shortBy() > 0, "the second cluster must know it is short");
	}

	@Test
	void aClusterNeverPromisesMoreThanYouCarry() {
		List<Work.Cell> todo = blob(0, 100, 0, 40, "stone_bricks");
		List<Plan.Cluster> cl = Plan.clusters(todo, carrying("stone_bricks", 7), Set.of(), BlockPos.ZERO);
		assertEquals(7, cl.get(0).doable());
		assertEquals(33, cl.get(0).shortBy());
	}

	@Test
	void scaffoldBlockedCellsDoNotCountAsDoable() {
		List<Work.Cell> todo = blob(0, 100, 0, 20, "stone_bricks");
		Set<Long> blocked = new HashSet<>();
		for (int i = 0; i < 5; i++) blocked.add(todo.get(i).pos().asLong());
		List<Plan.Cluster> cl = Plan.clusters(todo, carrying("stone_bricks", 640), blocked, BlockPos.ZERO);
		assertEquals(5, cl.get(0).blocked());
		assertEquals(15, cl.get(0).doable());
	}

	@Test
	void aCellIsOnlyEverInOneCluster() {
		List<Work.Cell> todo = new ArrayList<>(blob(0, 100, 0, 25, "stone_bricks"));
		todo.addAll(blob(40, 100, 40, 25, "stone_bricks"));
		List<Plan.Cluster> cl = Plan.clusters(todo, carrying("stone_bricks", 640), Set.of(), BlockPos.ZERO);
		Set<Long> seen = new HashSet<>();
		for (Plan.Cluster c : cl) {
			for (Work.Cell x : c.cells()) {
				assertTrue(seen.add(x.pos().asLong()), "cell counted twice: " + x.pos());
			}
		}
	}

	@Test
	void everyClusterFitsWithinOneWorkingRadius() {
		// The whole promise is "stand here and place these without moving".
		List<Work.Cell> todo = new ArrayList<>(blob(0, 100, 0, 25, "stone_bricks"));
		todo.addAll(blob(50, 100, 50, 25, "stone_bricks"));
		for (Plan.Cluster c : Plan.clusters(todo, carrying("stone_bricks", 640), Set.of(), BlockPos.ZERO)) {
			for (Work.Cell x : c.cells()) {
				assertTrue(x.pos().distSqr(c.centre()) <= (double) Plan.WORK_RADIUS * Plan.WORK_RADIUS,
					x.pos() + " is outside reach of " + c.centre());
			}
		}
	}

	@Test
	void theBiggestDoablePileComesFirst() {
		List<Work.Cell> todo = new ArrayList<>(blob(0, 100, 0, 6, "stone_bricks"));
		todo.addAll(blob(80, 100, 80, 30, "stone_bricks"));
		List<Plan.Cluster> cl = Plan.clusters(todo, carrying("stone_bricks", 640), Set.of(), BlockPos.ZERO);
		assertTrue(cl.get(0).doable() >= cl.get(cl.size() - 1).doable());
		assertEquals(30, cl.get(0).doable(), "the far pile of 30 beats the near pile of 6");
	}

	@Test
	void mixedMaterialsAreReportedPerCluster() {
		List<Work.Cell> todo = new ArrayList<>(blob(0, 100, 0, 10, "stone_bricks"));
		todo.addAll(blob(1, 100, 1, 10, "deepslate_bricks"));
		var carry = carrying("stone_bricks", 640, "deepslate_bricks", 640);
		List<Plan.Cluster> cl = Plan.clusters(todo, carry, Set.of(), BlockPos.ZERO);
		assertTrue(cl.get(0).materials().size() >= 2, "both materials should be listed");
		assertTrue(Plan.materialLine(cl.get(0), carry).contains("have 640"));
	}

	@Test
	void aScatterTooThinToBeWorthWalkingToIsDropped() {
		List<Work.Cell> todo = List.of(cell(0, 100, 0, "stone_bricks"),
			cell(500, 100, 500, "stone_bricks"));
		assertTrue(Plan.clusters(todo, carrying("stone_bricks", 64), Set.of(), BlockPos.ZERO).isEmpty(),
			"two cells 500 apart are not a place to go and work");
	}

	// ---------------------------------------------------------------- the arrow

	@Test
	void theArrowIsRelativeToWhereYouAreFacing() {
		// "NE" is something you translate while walking; an arrow that swings as you turn is one
		// you follow. yRot 0 faces +Z in Minecraft.
		BlockPos me = new BlockPos(0, 0, 0);
		BlockPos ahead = new BlockPos(0, 0, 10);
		assertTrue(Hud.bearing(0f, me, ahead).contains("ahead"));
		assertTrue(Hud.bearing(180f, me, ahead).contains("behind"));
	}

	@Test
	void turningInPlaceTurnsTheArrow() {
		BlockPos me = new BlockPos(0, 0, 0);
		BlockPos north = new BlockPos(0, 0, -10);
		String facingNorth = Hud.bearing(180f, me, north);
		String facingSouth = Hud.bearing(0f, me, north);
		assertFalse(facingNorth.equals(facingSouth), "the arrow must move when you do");
		assertTrue(facingNorth.contains("ahead"));
		assertTrue(facingSouth.contains("behind"));
	}

    @Test
    void leftAndRightAreNotMirrored() {
        // The sign error that sends you consistently the wrong way and that nothing but walking
        // would reveal. Worked out rather than guessed: yaw 0 faces +Z (south). Facing south, east
        // is on your LEFT, and east is +X. So +X must read left and -X must read right.
        BlockPos me = new BlockPos(0, 0, 0);
        assertTrue(Hud.bearing(0f, me, new BlockPos(10, 0, 0)).contains("left"),
            "+X is east; facing south, east is your left");
        assertTrue(Hud.bearing(0f, me, new BlockPos(-10, 0, 0)).contains("right"));
        // ...and turning to face east puts it ahead
        assertTrue(Hud.bearing(-90f, me, new BlockPos(10, 0, 0)).contains("ahead"));
    }

	// ---------------------------------------------------------------- restock

	private static Storage.Container chest(int x, int y, int z, String item, int n) {
		Storage.Container c = new Storage.Container();
		c.x = x;
		c.y = y;
		c.z = z;
		c.block = "chest";
		c.id = 37;
		c.items.put("minecraft:" + item, n);
		return c;
	}

	@Test
	void aShortfallComesWithAnAddress() {
		// The plan used to say "64 short" and stop, leaving you to run `need` and join the two in
		// your head. The index already knows where the bricks are.
		List<Work.Cell> todo = blob(0, 100, 0, 40, "stone_bricks");
		var carry = carrying("stone_bricks", 10);
		List<Plan.Cluster> cl = Plan.clusters(todo, carry, Set.of(), BlockPos.ZERO);
		Map<String, Storage.Container> index = new LinkedHashMap<>();
		Storage.Container c = chest(20, 100, 0, "stone_bricks", 500);
		index.put(c.key(), c);

		List<String> lines = Plan.restock(cl.get(0), carry, index, BlockPos.ZERO);
		assertEquals(1, lines.size());
		assertTrue(lines.get(0).contains("30 more stone_bricks"), lines.get(0));
		assertTrue(lines.get(0).contains("500"), "it should say how many are there");
		assertTrue(lines.get(0).contains("#37"), "and which container");
	}

	@Test
	void nothingShortMeansNothingToFetch() {
		List<Work.Cell> todo = blob(0, 100, 0, 20, "stone_bricks");
		var carry = carrying("stone_bricks", 640);
		List<Plan.Cluster> cl = Plan.clusters(todo, carry, Set.of(), BlockPos.ZERO);
		assertTrue(Plan.restock(cl.get(0), carry, new LinkedHashMap<>(), BlockPos.ZERO).isEmpty());
	}

	@Test
	void aShortfallWithNowhereToFetchItSaysSo() {
		// Silence here would read as "you have enough", which is the opposite of the truth.
		List<Work.Cell> todo = blob(0, 100, 0, 40, "stone_bricks");
		var carry = carrying("stone_bricks", 10);
		List<Plan.Cluster> cl = Plan.clusters(todo, carry, Set.of(), BlockPos.ZERO);
		List<String> lines = Plan.restock(cl.get(0), carry, new LinkedHashMap<>(), BlockPos.ZERO);
		assertEquals(1, lines.size());
		assertTrue(lines.get(0).contains("not in any indexed chest"));
	}

	// ---------------------------------------------------------------- fetch targeting

	@Test
	void theFetchTargetIsTheBiggestShortfallThatHasAnAddress() {
		// Ordering matters because `follow` takes the FIRST one and walks you there. A material
		// with nowhere to fetch it from must never be the trip.
		List<Work.Cell> todo = new ArrayList<>(blob(0, 100, 0, 30, "stone_bricks"));
		todo.addAll(blob(1, 100, 1, 12, "deepslate_bricks"));
		var carry = carrying("stone_bricks", 2, "deepslate_bricks", 2);
		List<Plan.Cluster> cl = Plan.clusters(todo, carry, Set.of(), BlockPos.ZERO);

		Map<String, Storage.Container> index = new LinkedHashMap<>();
		// only the SMALLER shortfall has a chest
		Storage.Container c = chest(20, 100, 0, "deepslate_bricks", 500);
		index.put(c.key(), c);

		Plan.Restock r = Plan.firstFetchable(cl.get(0), carry, index, BlockPos.ZERO);
		assertEquals("deepslate_bricks", r.item(), "the fetchable one must win over the bigger one");
		assertEquals(500, r.available());
		assertTrue(r.missing() > 0);
	}

	@Test
	void nothingFetchableWhenTheIndexIsEmpty() {
		List<Work.Cell> todo = blob(0, 100, 0, 30, "stone_bricks");
		var carry = carrying("stone_bricks", 2);
		List<Plan.Cluster> cl = Plan.clusters(todo, carry, Set.of(), BlockPos.ZERO);
		assertEquals(null, Plan.firstFetchable(cl.get(0), carry, new LinkedHashMap<>(), BlockPos.ZERO),
			"a shortfall with no chest is not a trip");
	}

	@Test
	void carryingEnoughMeansNoFetchAtAll() {
		List<Work.Cell> todo = blob(0, 100, 0, 20, "stone_bricks");
		var carry = carrying("stone_bricks", 640);
		List<Plan.Cluster> cl = Plan.clusters(todo, carry, Set.of(), BlockPos.ZERO);
		Map<String, Storage.Container> index = new LinkedHashMap<>();
		Storage.Container c = chest(20, 100, 0, "stone_bricks", 500);
		index.put(c.key(), c);
		assertEquals(null, Plan.firstFetchable(cl.get(0), carry, index, BlockPos.ZERO));
	}

	@Test
	void restockTargetsAreOrderedByHowMuchIsMissing() {
		List<Work.Cell> todo = new ArrayList<>(blob(0, 100, 0, 30, "stone_bricks"));
		todo.addAll(blob(1, 100, 1, 12, "deepslate_bricks"));
		var carry = carrying("stone_bricks", 1, "deepslate_bricks", 1);
		List<Plan.Cluster> cl = Plan.clusters(todo, carry, Set.of(), BlockPos.ZERO);
		List<Plan.Restock> rs = Plan.restockTargets(cl.get(0), carry, new LinkedHashMap<>(), BlockPos.ZERO);
		assertTrue(rs.get(0).missing() >= rs.get(rs.size() - 1).missing());
	}

	// ---------------------------------------------------------------- the vertical leg

	@Test
	void theClimbIsStatedBecauseACompassCannotCarryIt() {
		// This island is 240 blocks tall - lowland Y24, deck Y194, sky bird Y268 - so the up-down
		// component is routinely the LARGER one, and a horizontal-only arrow calls a chest 150
		// blocks below you "18m NE".
		assertTrue(Hud.climb(new BlockPos(0, 40, 0), new BlockPos(0, 194, 0)).contains("up 154"));
		assertTrue(Hud.climb(new BlockPos(0, 194, 0), new BlockPos(0, 40, 0)).contains("down 154"));
	}

	@Test
	void aSmallStepIsNotWorthSaying() {
		// Two blocks up is a jump, not a leg of a journey, and saying so on every frame is noise.
		assertEquals("", Hud.climb(new BlockPos(0, 100, 0), new BlockPos(0, 102, 0)));
		assertEquals("", Hud.climb(new BlockPos(0, 100, 0), new BlockPos(0, 100, 0)));
	}
}
