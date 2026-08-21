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
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
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
	void aClusterIsSizedToTheInventoryNotToArmsLength() {
		// A TRIP IS BOUNDED BY WHAT YOU CARRY. The first version sized every spot at one standing
		// radius, which on a 30,000-cell design is a plan made of five hundred trips - it was
		// reasoning about WALKING, and Jack flies.
		assertEquals(Plan.MIN_RADIUS, Plan.radiusFor(16), "nearly empty: stay at arm's length");
		assertTrue(Plan.radiusFor(1728) > Plan.MIN_RADIUS, "a shulker should open the spot out");
		assertTrue(Plan.radiusFor(13824) > Plan.radiusFor(1728), "six shulkers, wider still");
		assertEquals(Plan.MAX_RADIUS, Plan.radiusFor(1000000), "capped: past this it is the island");
		int last = 0;
		for (int b : new int[]{1, 64, 512, 4096, 32768, 262144}) {
			int r = Plan.radiusFor(b);
			assertTrue(r >= last, "radius went backwards at budget " + b);
			last = r;
		}
	}

	@Test
	void everyCellIsWithinTheRadiusThatTripWasSizedTo() {
		// Whatever the radius turns out to be, the cluster must not exceed it - otherwise "one
		// trip" is a claim rather than a property.
		List<Work.Cell> todo = new ArrayList<>(blob(0, 100, 0, 25, "stone_bricks"));
		todo.addAll(blob(50, 100, 50, 25, "stone_bricks"));
		Map<String, Integer> carry = carrying("stone_bricks", 640);
		int r = Plan.radiusFor(Plan.budget(todo, carry));
		for (Plan.Cluster c : Plan.clusters(todo, carry, Set.of(), BlockPos.ZERO)) {
			for (Work.Cell x : c.cells()) {
				assertTrue(x.pos().distSqr(c.centre()) <= (double) r * r,
					x.pos() + " is outside the " + r + "-block trip around " + c.centre());
			}
		}
	}

	@Test
	void budgetIsCappedByWhatTheDesignActuallyNeeds() {
		// 3,000 cobblestone does not help a design that wants forty of it, and letting it inflate
		// the budget would open the radius to the whole island for no reason.
		List<Work.Cell> todo = blob(0, 100, 0, 40, "stone_bricks");
		assertEquals(40, Plan.budget(todo, carrying("stone_bricks", 3000)));
		assertEquals(7, Plan.budget(todo, carrying("stone_bricks", 7)));
		assertEquals(0, Plan.budget(todo, carrying("deepslate_bricks", 3000)));
	}

	// ---------------------------------------------------------------- sealed in

	@Test
	void aCellSealedInSolidWorldIsNotWork() {
		// The opposite failure to scaffolding and just as fatal: plenty to place against, no way to
		// reach it. You cannot put a block inside a sealed volume.
		Work.Solid allSolid = p -> true;
		assertTrue(Work.enclosed(allSolid, cell(0, 100, 0, "stone_bricks"), Set.of()));
		Work.Solid oneGap = p -> !(p.getX() == 1 && p.getY() == 100 && p.getZ() == 0);
		assertFalse(Work.enclosed(oneGap, cell(0, 100, 0, "stone_bricks"), Set.of()),
			"one opening is enough to reach in");
	}

	@Test
	void anEarlierCellOfTheSameDesignIsNotAnOpening() {
		// It will be solid by the time you get there - the same reason it DOES count as something
		// to place against.
		Work.Solid oneGap = p -> !(p.getX() == 1 && p.getY() == 100 && p.getZ() == 0);
		Set<Long> earlier = Set.of(new BlockPos(1, 100, 0).asLong());
		assertTrue(Work.enclosed(oneGap, cell(0, 100, 0, "stone_bricks"), earlier));
	}

	@Test
	void sealedCellsAreSubtractedFromDoable() {
		List<Work.Cell> todo = blob(0, 100, 0, 20, "stone_bricks");
		Set<Long> sealed = new HashSet<>();
		for (int i = 0; i < 6; i++) sealed.add(todo.get(i).pos().asLong());
		List<Plan.Cluster> cl = Plan.clusters(todo, carrying("stone_bricks", 640),
			Set.of(), sealed, BlockPos.ZERO);
		assertEquals(6, cl.get(0).sealed());
		assertEquals(14, cl.get(0).doable());
	}

	@Test
	void aCellIsNeverCountedAsBothBlockedAndSealed() {
		// They are contradictory - six solid neighbours and six open ones - but a caller could pass
		// overlapping sets, and double-subtracting would make doable() lie low.
		List<Work.Cell> todo = blob(0, 100, 0, 10, "stone_bricks");
		Set<Long> both = new HashSet<>();
		for (int i = 0; i < 4; i++) both.add(todo.get(i).pos().asLong());
		List<Plan.Cluster> cl = Plan.clusters(todo, carrying("stone_bricks", 640), both, both, BlockPos.ZERO);
		assertEquals(4, cl.get(0).blocked() + cl.get(0).sealed());
		assertEquals(6, cl.get(0).doable());
	}

	// ---------------------------------------------------------------- the index forgets

	@Test
	void anUnloadedChunkIsNotEvidenceTheChestIsGone() {
		// Getting this backwards deletes the whole index the first time you prune from across the
		// island. null = nothing to look at = leave it alone.
		assertTrue(Storage.stillThere((String) null));
	}

	@Test
	void aChestThatIsNowStoneIsGone() {
		// 179 of 339 indexed containers no longer existed: 63 positions now air, the rest stone
		// brick, walls, slabs and moss. The index has no way to learn that by itself, because you
		// cannot open a chest that has been broken.
		assertTrue(Storage.stillThere("chest"));
		assertTrue(Storage.stillThere("barrel"));
		assertFalse(Storage.stillThere("air"));
		assertFalse(Storage.stillThere("stone_bricks"));
		assertFalse(Storage.stillThere("moss_block"));
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

	// ---------------------------------------------------------------- the freeze

	@Test
	void aFailedChestIsSkippedForTheNextOneHoldingIt() {
		// THE FREEZE, exactly. The nearest container was chosen every time, so once a chest went
		// into its cooling-off period the loop was pointed at it, refused to open it, and sat
		// there. A shortfall usually has several containers holding it.
		List<Work.Cell> todo = blob(0, 100, 0, 40, "stone_bricks");
		var carry = carrying("stone_bricks", 2);
		List<Plan.Cluster> cl = Plan.clusters(todo, carry, Set.of(), BlockPos.ZERO);

		Map<String, Storage.Container> index = new LinkedHashMap<>();
		Storage.Container near = chest(10, 100, 0, "stone_bricks", 500);
		Storage.Container far = chest(60, 100, 0, "stone_bricks", 500);
		index.put(near.key(), near);
		index.put(far.key(), far);

		assertEquals(near.pos(), Plan.firstFetchable(cl.get(0), carry, index, BlockPos.ZERO).where().pos(),
			"should start with the nearest");
		Plan.Restock second = Plan.firstFetchable(cl.get(0), carry, index, BlockPos.ZERO,
			Set.of(near.pos().asLong()));
		assertEquals(far.pos(), second.where().pos(), "did not fall through to the other chest");
	}

	@Test
	void everyChestFailedMeansNoFetchRatherThanAWrongOne() {
		List<Work.Cell> todo = blob(0, 100, 0, 40, "stone_bricks");
		var carry = carrying("stone_bricks", 2);
		List<Plan.Cluster> cl = Plan.clusters(todo, carry, Set.of(), BlockPos.ZERO);
		Map<String, Storage.Container> index = new LinkedHashMap<>();
		Storage.Container only = chest(10, 100, 0, "stone_bricks", 500);
		index.put(only.key(), only);
		assertEquals(null, Plan.firstFetchable(cl.get(0), carry, index, BlockPos.ZERO,
			Set.of(only.pos().asLong())));
	}

	// ---------------------------------------------------------------- the fetch policy
	//
	// FILL THE PACK, THEN BUILD UNTIL IT IS DRY. The decision used to be made per SPOT — if the best
	// cluster was short of anything, go shopping — so the loop fetched with a full inventory and
	// plenty it could place. These pin the two questions and the order between them.

	@Test
	void aFullPackWithWorkToDoDoesNotGoShopping() {
		// The old rule: this cluster wants 40 and is 30 short, so fetch. The new one: you can place
		// ten right now, so place them. A trip is what you do when you cannot work, not when you
		// could work faster.
		List<Work.Cell> todo = blob(0, 100, 0, 40, "stone_bricks");
		var carry = carrying("stone_bricks", 10);
		List<Plan.Cluster> cl = Plan.clusters(todo, carry, Set.of(), BlockPos.ZERO);
		assertTrue(Plan.anyDoable(cl), "ten placeable bricks is work");
	}

	@Test
	void carryingNothingIsNotWork() {
		List<Work.Cell> todo = blob(0, 100, 0, 40, "stone_bricks");
		assertFalse(Plan.anyDoable(Plan.clusters(todo, carrying(), Set.of(), BlockPos.ZERO)));
	}

	@Test
	void cellsYouCannotBuildAreNotWorkEither() {
		// Carrying the material is not enough: nothing to place against, and no way in, are the two
		// ways the world says no. Either one and the spot is not a spot.
		List<Work.Cell> todo = blob(0, 100, 0, 20, "stone_bricks");
		Set<Long> all = new HashSet<>();
		for (Work.Cell c : todo) all.add(c.pos().asLong());
		assertFalse(Plan.anyDoable(
			Plan.clusters(todo, carrying("stone_bricks", 640), all, Set.of(), BlockPos.ZERO)),
			"every cell was floating and it still offered the spot");
		assertFalse(Plan.anyDoable(
			Plan.clusters(todo, carrying("stone_bricks", 640), Set.of(), all, BlockPos.ZERO)),
			"every cell was sealed and it still offered the spot");
	}

	@Test
	void aTripEndsWhenThePackIsFullOrTheDesignIsCovered() {
		// The two ways to be done are different and both mean go and build.
		Storage.Container c = chest(20, 100, 0, "stone_bricks", 500);
		List<Plan.Restock> some = List.of(new Plan.Restock("stone_bricks", 300, c, 500));
		assertNotNull(Plan.nextFetch(some, it -> 640), "room to carry more and more to carry");
		assertNull(Plan.nextFetch(some, it -> 0), "kept shopping with a full pack");
		assertNull(Plan.nextFetch(List.of(), it -> 640), "kept shopping with nothing to buy");
	}

	@Test
	void noRoomForTheBiggestShortfallStillFetchesTheNextOne() {
		// A pack full of bricks has no space for more bricks and plenty for the deepslate. Judging
		// only the first entry is a trip not taken and a spot not finished.
		Storage.Container a = chest(20, 100, 0, "stone_bricks", 500);
		Storage.Container b = chest(21, 100, 0, "deepslate_bricks", 500);
		List<Plan.Restock> some = List.of(new Plan.Restock("stone_bricks", 300, a, 500),
			new Plan.Restock("deepslate_bricks", 40, b, 500));
		Plan.Restock got = Plan.nextFetch(some, it -> it.equals("stone_bricks") ? 0 : 64);
		assertNotNull(got);
		assertEquals("deepslate_bricks", got.item());
	}

	@Test
	void aFetchMatchesTheItemExactlyAndNotAsASubstring() {
		// `find` is a substring search and should be — `/cscan find wool` is a question about wool.
		// It is the wrong tool for a TRIP: `stone_bricks` matches `mossy_stone_bricks`, so the loop
		// flew to the mossy chest, took nothing, and blacklisted it. That looked exactly like the
		// chest being empty.
		Map<String, Storage.Container> index = new LinkedHashMap<>();
		Storage.Container mossy = chest(5, 100, 0, "mossy_stone_bricks", 500);
		Storage.Container plain = chest(60, 100, 0, "stone_bricks", 500);
		index.put(mossy.key(), mossy);
		index.put(plain.key(), plain);
		List<Work.Cell> todo = blob(0, 100, 0, 40, "stone_bricks");

		List<Plan.Restock> t = Plan.fetchTargets(todo, carrying(), index, BlockPos.ZERO, Set.of());
		assertEquals(1, t.size());
		assertEquals(plain.pos(), t.get(0).where().pos(),
			"routed to the nearest chest of a DIFFERENT block");
	}

	@Test
	void theFetchIsSizedToTheWholeDesignNotToOneSpot() {
		// The number that made a fetch a round trip per wall. The design wants 400; the spot in
		// front of you wants 40. You are carrying nothing, so the trip is for 400.
		List<Work.Cell> todo = blob(0, 100, 0, 40, "stone_bricks");
		for (int i = 0; i < 360; i++) todo.add(cell(400 + i % 5, 100, 400 + i / 5, "stone_bricks"));
		Map<String, Storage.Container> index = new LinkedHashMap<>();
		Storage.Container c = chest(20, 100, 0, "stone_bricks", 500);
		index.put(c.key(), c);

		List<Plan.Restock> t = Plan.fetchTargets(todo, carrying(), index, BlockPos.ZERO, Set.of());
		assertEquals(1, t.size());
		assertEquals(400, t.get(0).missing(), "asked for one spot's worth rather than the design's");
	}

	@Test
	void theAmountTakenIsCappedByTheRoomAndByTheChest() {
		Storage.Container c = chest(20, 100, 0, "stone_bricks", 128);
		Plan.Restock want = new Plan.Restock("stone_bricks", 400, c, 128);
		assertEquals(128, Plan.takeHowMany(want, 640), "took more than the chest holds");
		assertEquals(64, Plan.takeHowMany(want, 64), "took more than would fit");
		assertEquals(0, Plan.takeHowMany(want, 0));
		// A chest the index believes is empty is not a trip.
		assertEquals(0, Plan.takeHowMany(new Plan.Restock("stone_bricks", 400, c, 0), 640));
	}

	@Test
	void aCoolingOffChestIsNotTheFetchTarget() {
		// The freeze: once a chest failed, the nearest-container rule pointed the loop back at it
		// forever. A shortfall usually has more than one address.
		Map<String, Storage.Container> index = new LinkedHashMap<>();
		Storage.Container near = chest(5, 100, 0, "stone_bricks", 500);
		Storage.Container far = chest(60, 100, 0, "stone_bricks", 500);
		index.put(near.key(), near);
		index.put(far.key(), far);
		List<Work.Cell> todo = blob(0, 100, 0, 40, "stone_bricks");

		List<Plan.Restock> t = Plan.fetchTargets(todo, carrying(), index, BlockPos.ZERO,
			Set.of(near.pos().asLong()));
		assertEquals(1, t.size());
		assertEquals(far.pos(), t.get(0).where().pos(), "guided back at the chest it just failed on");
	}

	@Test
	void aShortfallWithNoAddressIsNotSomethingToFlyTo() {
		// It is reported in words by `restock`; this list is used for NAVIGATION, and an entry with
		// no container is a place to fly to that does not exist.
		List<Work.Cell> todo = blob(0, 100, 0, 40, "stone_bricks");
		assertTrue(Plan.fetchTargets(todo, carrying(), new LinkedHashMap<>(), BlockPos.ZERO, Set.of())
			.isEmpty());
	}

	// ---------------------------------------------------------------- room in the pack

	@Test
	void roomIsEmptySlotsPlusThePartOfAStackThatIsFree() {
		assertEquals(64 * 36, Work.roomIn(36, new int[0], 64), "an empty pack");
		assertEquals(0, Work.roomIn(0, new int[]{64, 64}, 64), "two full stacks is no room");
		assertEquals(24, Work.roomIn(0, new int[]{40}, 64));
		assertEquals(64 + 24, Work.roomIn(1, new int[]{40, 64}, 64));
	}

	// ---------------------------------------------------------------- stations inside a spot
	//
	// A SPOT IS A TRIP, NOT A PLACE TO STAND. `radiusFor` sizes a spot to one inventory load, so with
	// a shulker aboard it is a region 48 blocks across - and the loop guided you to its CENTROID and
	// stopped there, because arriving is not disarming. The printer reaches about four and a half.
	// It placed whatever was near the middle, ran out, and sat until the stall watch abandoned a spot
	// that was almost entirely unbuilt.

	@Test
	void aStationIsWithinPrinterReachOfTheCellsItCovers() {
		List<Work.Cell> far = new ArrayList<>();
		for (int i = 0; i < 30; i++) far.add(cell(100 + i % 3, 100, 100 + i / 3, "stone_bricks"));
		Plan.Station st = Plan.station(far, Plan.PRINTER_REACH, BlockPos.ZERO, Set.of());
		assertNotNull(st);
		for (Work.Cell c : Plan.atStation(far, st, Plan.PRINTER_REACH)) {
			assertTrue(Math.sqrt(c.pos().distSqr(st.where())) <= Plan.PRINTER_REACH * 2,
				c.pos() + " is out of reach of the station at " + st.where());
		}
	}

	@Test
	void theCentroidOfAWholeSpotIsNotAStation() {
		// The bug, stated as a test. Two dense knots 40 blocks apart: their joint centroid is 20
		// blocks from either, which is nothing the printer can touch. A station must be AT one knot.
		List<Work.Cell> two = new ArrayList<>(blob(0, 100, 0, 20, "stone_bricks"));
		two.addAll(blob(40, 100, 0, 20, "stone_bricks"));
		BlockPos centroid = Plan.centroid(two);
		Plan.Station st = Plan.station(two, Plan.PRINTER_REACH, BlockPos.ZERO, Set.of());
		assertNotNull(st);
		assertTrue(Math.sqrt(st.where().distSqr(centroid)) > Plan.PRINTER_REACH,
			"the station is the useless middle: " + st.where());
	}

	@Test
	void itGoesToTheFullestBinAndTheNearestOnATie() {
		List<Work.Cell> mixed = new ArrayList<>(blob(0, 100, 0, 6, "stone_bricks"));
		mixed.addAll(blob(60, 100, 0, 25, "stone_bricks"));
		Plan.Station st = Plan.station(mixed, Plan.PRINTER_REACH, BlockPos.ZERO, Set.of());
		assertTrue(st.where().getX() > 30, "took the near handful over the far pile: " + st.where());
		// ...and a genuine tie goes to your feet, or it crosses the region for nothing
		List<Work.Cell> tied = new ArrayList<>(blob(0, 100, 0, 9, "stone_bricks"));
		tied.addAll(blob(60, 100, 0, 9, "stone_bricks"));
		assertTrue(Plan.station(tied, Plan.PRINTER_REACH, BlockPos.ZERO, Set.of())
			.where().getX() < 30, "walked past an identical pile");
	}

	@Test
	void anAbandonedStationIsNotOfferedAgain() {
		// Twenty seconds at one station with nothing placed and the bin is skipped: a bin the
		// printer will not take is otherwise a bin you sit at until the spot times out.
		List<Work.Cell> mixed = new ArrayList<>(blob(0, 100, 0, 25, "stone_bricks"));
		mixed.addAll(blob(60, 100, 0, 6, "stone_bricks"));
		Plan.Station first = Plan.station(mixed, Plan.PRINTER_REACH, BlockPos.ZERO, Set.of());
		Plan.Station second = Plan.station(mixed, Plan.PRINTER_REACH, BlockPos.ZERO,
			Set.of(first.bin()));
		assertNotNull(second, "gave up when the fullest bin was skipped");
		assertNotEquals(first.bin(), second.bin());
	}

	@Test
	void everyCellOfASpotBelongsToSomeStation() {
		// The property that makes the sweep finish: no cell can be left with nowhere to stand for it,
		// or the spot never empties and the stall watch is what ends it.
		List<Work.Cell> spread = new ArrayList<>();
		for (int x = 0; x < 30; x += 2) {
			for (int z = 0; z < 30; z += 3) spread.add(cell(x, 100, z, "stone_bricks"));
		}
		Set<Long> tried = new HashSet<>();
		int covered = 0;
		for (int guard = 0; guard < 500; guard++) {
			Plan.Station st = Plan.station(spread, Plan.PRINTER_REACH, BlockPos.ZERO, tried);
			if (st == null) break;
			covered += Plan.atStation(spread, st, Plan.PRINTER_REACH).size();
			tried.add(st.bin());
		}
		assertEquals(spread.size(), covered, "some cells had no station to place them from");
	}

	@Test
	void aStationCanReachItsOwnFarCorner() {
		// The arithmetic the whole sweep rests on, and it breaks silently if anyone tunes the reach:
		// a bin is a cube of PRINTER_REACH, so its half-diagonal must stay under what the printer
		// can actually touch, plus whatever the standoff and the arrival radius spend getting there.
		double halfDiagonal = Math.sqrt(3) * Plan.PRINTER_REACH / 2.0;
		double budget = 4.5;                                  // litematica-printer's reach
		assertTrue(halfDiagonal < budget,
			"a station cannot build the far corner of its own bin: " + halfDiagonal);
		// Jack: "the focus should be getting within a 3 block radius of the point since we know we
		// reach+place further". So the flight's precision is no longer bought with contact, and what
		// pays for it is asking the printer its real range rather than assuming four blocks.
		assertTrue(Autopilot.ARRIVED <= 3.0, "stops further off than the instruction");
		assertTrue(Plan.reach() >= 2, "a reach that small is not a printer");
	}

	// ---------------------------------------------------------------- only what can be built NOW

	@Test
	void aClusterKeepsTheCellsItCannotBuildOutOfWhatItPointsAt() {
		// Reported from a real session: "it's highlighting chunks to build on that aren't possible
		// to be built on yet". A station picked over EVERY cell left in a spot can be made entirely
		// of cells with nothing to place against — you get flown to a bin of mid-air, the printer
		// places none of it, and twenty seconds later the loop moves to the next bin of mid-air.
		List<Work.Cell> todo = blob(0, 100, 0, 20, "stone_bricks");
		Set<Long> floating = new HashSet<>();
		for (int i = 0; i < 12; i++) floating.add(todo.get(i).pos().asLong());

		List<Plan.Cluster> cl = Plan.clusters(todo, carrying("stone_bricks", 640), floating,
			Set.of(), BlockPos.ZERO);
		assertFalse(cl.isEmpty());
		Plan.Cluster c = cl.get(0);
		assertEquals(20, c.cells().size(), "the unbuildable cells are still work left here");
		assertEquals(8, c.ready().size(), "ready must be what you can place NOW");
		for (Work.Cell x : c.ready()) {
			assertFalse(floating.contains(x.pos().asLong()), "offered a cell with nothing to build on");
		}
	}

	@Test
	void aSpotOfNothingButFloatingCellsIsNotWork() {
		List<Work.Cell> todo = blob(0, 100, 0, 20, "stone_bricks");
		Set<Long> all = new HashSet<>();
		for (Work.Cell c : todo) all.add(c.pos().asLong());
		List<Plan.Cluster> cl = Plan.clusters(todo, carrying("stone_bricks", 640), all, Set.of(),
			BlockPos.ZERO);
		assertFalse(Plan.anyDoable(cl), "offered a spot where nothing can be placed");
		for (Plan.Cluster c : cl) {
			assertTrue(c.ready().isEmpty());
			assertNull(Plan.station(c.ready(), Plan.PRINTER_REACH, BlockPos.ZERO, Set.of()),
				"found somewhere to stand for cells that cannot be built");
		}
	}

	@Test
	void doableCountsTheReadyCellsAndNotTheRest() {
		// It was cells - blocked - sealed - short, which is the same number by a different route and
		// stopped being so the moment `ready` had to be a LIST. One source, so the count the player
		// is told and the cells they are sent to cannot disagree.
		List<Work.Cell> todo = blob(0, 100, 0, 20, "stone_bricks");
		Set<Long> floating = new HashSet<>();
		for (int i = 0; i < 5; i++) floating.add(todo.get(i).pos().asLong());
		Plan.Cluster c = Plan.clusters(todo, carrying("stone_bricks", 8), floating, Set.of(),
			BlockPos.ZERO).get(0);
		assertEquals(Math.max(0, c.ready().size() - c.shortBy()), c.doable());
		assertTrue(c.doable() <= c.ready().size(), "promised more than it has cells for");
	}

	// ---------------------------------------------------------------- where to float

	/** Open air, except where you say otherwise. */
	private static Nav.Passable air(Set<Long> solid) {
		return (x, y, z) -> !solid.contains(BlockPos.asLong(x, y, z))
			&& !solid.contains(BlockPos.asLong(x, y + 1, z));
	}

	@Test
	void theStandingSpotIsChosenByWhatItCanREACH() {
		// It used to be chosen by proximity to a centroid, and then the flight parked short of it -
		// so the number deciding everything was a distance to a point nobody cared about. What
		// matters is how many of the cells left here can actually be touched from where the body
		// ends up.
		List<Work.Cell> wall = new ArrayList<>();
		for (int y = 100; y <= 106; y++) wall.add(cell(0, y, 0, "stone_bricks"));

		BlockPos stand = Plan.bestStand(air(Set.of()), wall, 5, new BlockPos(9, 103, 0), 4, 1.2);
		assertNotNull(stand);
		int covered = 0;
		for (Work.Cell c : wall) {
			if (Math.sqrt(c.pos().distSqr(stand)) <= 5) covered++;
		}
		assertTrue(covered >= 6, "stood where it can only reach " + covered + " of 7 cells");
	}

	@Test
	void aSpotWithNoAirUnderItIsNotASpot() {
		// Clearance is a FILTER rather than part of the score: a spot that touches something is not
		// a worse spot, it is not a spot - on this server it ends the flight.
		Set<Long> solid = new HashSet<>();
		for (int x = -6; x <= 6; x++) {
			for (int z = -6; z <= 6; z++) solid.add(BlockPos.asLong(x, 99, z));   // a floor
		}
		List<Work.Cell> low = List.of(cell(0, 100, 0, "stone_bricks"));
		BlockPos stand = Plan.bestStand(air(solid), low, 5, new BlockPos(6, 104, 0), 4, 1.2);
		assertNotNull(stand);
		assertTrue(Nav.airBelow(air(solid), stand, Nav.AIR_BELOW),
			"chose a spot resting on the floor: " + stand);
	}

	@Test
	void aTieGoesToTheNearestSpot() {
		// Two spots that build the same wall are the same spot, so there is no reason to cross the
		// room for one of them.
		List<Work.Cell> one = List.of(cell(0, 100, 0, "stone_bricks"));
		BlockPos near = new BlockPos(3, 100, 0);
		BlockPos stand = Plan.bestStand(air(Set.of()), one, 5, near, 4, 1.2);
		assertNotNull(stand);
		assertTrue(stand.distSqr(near) <= 9, "walked past an identical spot: " + stand);
	}

	@Test
	void nothingToStandForIsNull() {
		assertNull(Plan.bestStand(air(Set.of()), List.of(), 5, BlockPos.ZERO, 4, 1.2));
	}
}
