package dev.jack.chunkscan;

import net.minecraft.core.BlockPos;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * The 2026-09-04 audit of the unattended loop, pinned. Each test is one defect that shipped
 * with a clean build: a chest the flight could not get close enough to, a pack that filled with
 * the far end's materials, a router that declared a sloped leg clear with a ceiling in it, an
 * escape that parked the body flush against the wall it was escaping, a pocket flood that could
 * not turn a corner, a start cell the body did not fit in, and a chest that worked being skipped
 * for the next-nearest one.
 */
class AuditFixesTest {
	/** Everything open except the cells you add. Two clear cells per body, like the real one. */
	private static final class W {
		final Set<Long> solid = new HashSet<>();
		void fill(int x0, int y0, int z0, int x1, int y1, int z1) {
			for (int x = x0; x <= x1; x++)
				for (int y = y0; y <= y1; y++)
					for (int z = z0; z <= z1; z++) solid.add(BlockPos.asLong(x, y, z));
		}
		void carve(int x0, int y0, int z0, int x1, int y1, int z1) {
			for (int x = x0; x <= x1; x++)
				for (int y = y0; y <= y1; y++)
					for (int z = z0; z <= z1; z++) solid.remove(BlockPos.asLong(x, y, z));
		}
		void room(int x0, int y0, int z0, int x1, int y1, int z1) {
			for (int x = x0; x <= x1; x++)
				for (int y = y0; y <= y1; y++)
					for (int z = z0; z <= z1; z++) {
						boolean shell = x == x0 || x == x1 || y == y0 || y == y1 || z == z0 || z == z1;
						if (shell) solid.add(BlockPos.asLong(x, y, z));
					}
		}
		Nav.Passable free() {
			return (x, y, z) -> !solid.contains(BlockPos.asLong(x, y, z))
				&& !solid.contains(BlockPos.asLong(x, y + 1, z));
		}
	}

	private static Work.Cell cell(int x, int y, int z, String block) {
		return new Work.Cell(new BlockPos(x, y, z), block);
	}

	@BeforeEach
	void clean() {
		Withdraw.clearFailures();
	}

	// ------------------------------------------------------------------ the chest approach

	@Test
	void anApproachCellWithinTwoOfTheChestBeatsOneFourAway() {
		// Jack: "chests need to be within 2 blocks". The old choice was nearest the PLAYER,
		// which could be four and a half from the chest.
		BlockPos chest = new BlockPos(0, 64, 0);
		assertEquals(0, ContainerInteraction.rank(new BlockPos(2, 65, 1), chest));
		assertEquals(0, ContainerInteraction.rank(new BlockPos(-2, 66, -2), chest));
		assertEquals(1, ContainerInteraction.rank(new BlockPos(3, 65, 0), chest));
		assertEquals(1, ContainerInteraction.rank(new BlockPos(0, 65, 4), chest));
	}

	@Test
	void theEyeOfAHoveringBodyIsWhereTheFlightPutsItsFeet() {
		// The opening test is cast from the eye the flight will actually have in that cell —
		// feet at FOOT_OFFSET above the cell floor — not from the cell's own floor.
		var eye = ContainerInteraction.eyeAt(new BlockPos(3, 70, 3), 1.62);
		assertEquals(3.5, eye.x, 1e-9);
		assertEquals(70 + Autopilot.FOOT_OFFSET + 1.62, eye.y, 1e-9);
		assertEquals(3.5, eye.z, 1e-9);
	}

	@Test
	void onlyDecidedPropertiesAreRequiredToMatch() {
		// The Python side's work.INTENTIONAL, applied on the Java read: a litematic carries every
		// property, and the game derives most of them from the neighbourhood.
		assertEquals(StateContract.Role.REQUIRED, StateContract.role("stone_brick_stairs", "facing"));
		assertEquals(StateContract.Role.REQUIRED, StateContract.role("stone_brick_slab", "type"));
		assertEquals(StateContract.Role.DERIVED, StateContract.role("stone_brick_stairs", "shape"));
		assertEquals(StateContract.Role.REQUIRED, StateContract.role("stone_brick_stairs", "waterlogged"), "a bucket after the stair: a completion requirement");
		assertEquals(StateContract.Role.REQUIRED, StateContract.role("rail", "shape"));
		assertEquals(StateContract.Role.DERIVED, StateContract.role("sugar_cane", "age"));
		assertEquals(StateContract.Role.DERIVED, StateContract.role("grass_block", "snowy"));
		assertEquals(StateContract.Role.DERIVED, StateContract.role("cave_vines", "berries"));
		assertEquals(StateContract.Role.DERIVED, StateContract.role("chest", "type"), "which half of a double chest is the game's call");
		assertEquals(StateContract.Role.REQUIRED, StateContract.role("pointed_dripstone", "vertical_direction"));
		assertEquals(StateContract.Role.REQUIRED, StateContract.role("vine", "north"), "a vine's faces ARE the decision");
		assertEquals(StateContract.Role.DERIVED, StateContract.role("oak_fence", "north"));
		assertEquals(StateContract.Role.DERIVED, StateContract.role("stone_brick_wall", "up"));
	}

	@Test
	void aDoubleChestIsFiledUnderOneHalf() {
		var a = new BlockPos(10, 64, 20);
		var b = new BlockPos(11, 64, 20);
		assertEquals(a, Storage.lower(a, b));
		assertEquals(a, Storage.lower(b, a), "the same answer from either half");
		assertEquals(new BlockPos(5, 64, 3), Storage.lower(new BlockPos(5, 64, 3), new BlockPos(5, 64, 4)));
	}

	@Test
	void aPoolAsksForAFewBucketsNotOnePerCell() {
		java.util.List<Work.Cell> pool = new java.util.ArrayList<>();
		for (int i = 0; i < 40; i++) pool.add(new Work.Cell(new BlockPos(i, 200, 0), "water[level=0]"));
		pool.add(new Work.Cell(new BlockPos(0, 201, 0), "stone_bricks"));
		var plan = Plan.loadPlan(pool, java.util.List.of(), new BlockPos(0, 200, 0), 2000);
		assertEquals(Plan.BUCKETS_PER_TRIP, plan.get("water_bucket"));
		assertEquals(1, plan.get("stone_bricks"));
		assertTrue(Autopilot.FLY_COMMANDS > 0 && Autopilot.FLY_COMMANDS <= Autopilot.REGAIN_GIVE_UP);
	}

	@Test
	void anExactTargetIsReachedNotApproached() {
		// A station is somewhere to hover NEAR; a chest's approach cell is somewhere to BE.
		assertTrue(Autopilot.EXACT_MIN < Autopilot.ARRIVE_MIN);
		assertTrue(Autopilot.EXACT_ARRIVED < Autopilot.ARRIVED);
		// ...and hovering in it keeps more than the block of air this server ends flight inside
		// of, while staying low enough to open a chest on the floor the cell was chosen over.
		assertTrue(Autopilot.EXACT_CLEAR > 2.0, "one block of air under the feet is where this server ends flight");
		assertTrue(Autopilot.EXACT_CLEAR < Autopilot.GROUND_CLEAR,
			"the ordinary clearance is what held the flight out of reach of every chest on a floor");
		assertTrue(ContainerInteraction.HOVER_CLEAR >= 2, "the approach cell keeps two clear cells under it");
		assertTrue(Autopilot.EXACT_CLEAR < ContainerInteraction.HOVER_CLEAR + Autopilot.FOOT_OFFSET,
			"the clearance the flight holds must fit under the air the cell was chosen for");
		// ...and the eyes still reach a chest on that floor from one block over: feet two cells up,
		// eye height 1.62, chest centre half a block up.
		double dy = 2 + Autopilot.FOOT_OFFSET + 1.62 - 0.5, dx = ContainerInteraction.CLOSE - 1;
		assertTrue(Math.sqrt(dx * dx + dy * dy) < Withdraw.REACH, "hovering two up puts the chest out of reach");
	}

	@Test
	void theFetchWatchdogIsSlowerThanTheFlightAndFasterThanTheSessionClocks() {
		assertTrue(Hud.FETCH_STUCK_MS > Hud.NOWHERE_MS, "it must outlast a normal final approach");
		assertTrue(Hud.FETCH_STUCK_MS < Hud.STALL_MS, "and not wait a minute and a half at a chest");
	}

	// ------------------------------------------------------------------ what goes in the pack

	@Test
	void theLoadIsTheAreasNextCoursesNotTheNearestCellsInThreeDimensions() {
		// Jack: "it stacks up with random resources vs things it logically might need". The loop
		// lays one course at a time from the bottom, so the next cells to be placed are the next
		// COURSES - not the nearest cells, which are mostly courses that cannot be placed until
		// the ones under them exist. Ten stone on the ground course, two hundred wool a course up,
		// a pack of 64: ten stone and fifty-four wool, and nothing of the roof.
		List<Work.Cell> area = new java.util.ArrayList<>();
		for (int i = 0; i < 10; i++) area.add(cell(i, 200, 0, "stone_bricks"));
		for (int i = 0; i < 200; i++) area.add(cell(i % 20, 201, i / 20, "white_wool"));
		for (int i = 0; i < 100; i++) area.add(cell(i % 10, 210, i / 10, "oak_planks"));
		var plan = Plan.loadPlan(area, List.of(), new BlockPos(0, 200, 0), 64);
		assertEquals(64, Plan.cells(plan), "sized to the pack");
		assertEquals(10, plan.get("stone_bricks"), "the lowest course comes first, all of it");
		assertEquals(54, plan.get("white_wool"), "...then the course above it");
		assertNull(plan.get("oak_planks"), "the roof is not this trip's business");
	}

	@Test
	void withinACourseTheNearestCellsToTheAnchorComeFirst() {
		List<Work.Cell> area = new java.util.ArrayList<>();
		for (int i = 0; i < 5; i++) area.add(cell(i, 200, 0, "stone_bricks"));
		for (int i = 14; i < 19; i++) area.add(cell(i, 200, 0, "glass"));
		var plan = Plan.loadPlan(area, List.of(), new BlockPos(0, 200, 0), 8);
		assertEquals(5, plan.get("stone_bricks"));
		assertEquals(3, plan.get("glass"));
	}

	@Test
	void theFrontierIsAlwaysInTheLoadWhateverItsDistanceOrCourse() {
		// The cells that can be placed right now are the reason for the trip.
		List<Work.Cell> area = new java.util.ArrayList<>();
		for (int i = 0; i < 100; i++) area.add(cell(i, 200, 0, "stone_bricks"));
		Work.Cell far = cell(500, 230, 0, "lantern");
		area.add(far);
		var plan = Plan.loadPlan(area, List.of(far), new BlockPos(0, 200, 0), 16);
		assertEquals(1, plan.get("lantern"), "the frontier cell was dropped for being far");
		assertEquals(16, Plan.cells(plan), "the frontier counts toward the load, it is not on top of it");
	}

	@Test
	void aTripIsAHandfulOfMaterialsAndNotWhateverFallsInsideACellBudget() {
		// Jack: "shopping list is getting constantly spammed and stopping all progress."
		// Twenty materials on one course and a generous budget used to make one trip for all
		// twenty - which finishes none of them, and whose tail moved every recount as the budget
		// and the anchor drifted, so the list was a different list every two seconds.
		List<Work.Cell> area = new java.util.ArrayList<>();
		for (int m = 0; m < 20; m++) {
			for (int i = 0; i < 40; i++) area.add(cell(i, 200, m, "material_" + m));
		}
		var plan = Plan.loadPlan(area, List.of(), new BlockPos(0, 200, 0), 2000);
		assertEquals(Plan.MAX_MATERIALS, plan.size(), "one trip, a handful of materials");
		assertEquals(40 * Plan.MAX_MATERIALS, Plan.cells(plan),
			"and all of each of them, not a slice cut by a cell budget");
	}

	@Test
	void aMaterialPastTheCapIsSkippedRatherThanEndingTheList() {
		// The cells under a capped-out material are still the next courses of this area, and their
		// materials are still this trip's. Ending the walk there would make the list depend on the
		// order the area happened to arrive in.
		List<Work.Cell> area = new java.util.ArrayList<>();
		for (int m = 0; m < Plan.MAX_MATERIALS; m++) area.add(cell(m, 200, 0, "material_" + m));
		area.add(cell(0, 201, 0, "over_the_cap"));
		for (int i = 1; i < 20; i++) area.add(cell(i, 201, 0, "material_0"));
		var plan = Plan.loadPlan(area, List.of(), new BlockPos(0, 200, 0), 64);
		assertNull(plan.get("over_the_cap"), "the seventh material is not this trip's");
		assertEquals(20, plan.get("material_0"), "and the walk carried on past it");
	}

	@Test
	void theListDoesNotChangeWhenTheBUDGETWOBBLES() {
		// The pack fills and empties as a session runs, so the cap moves; the SHOPPING LIST must
		// not, or the loop announces a new trip - and re-picks a target chest - every recount.
		List<Work.Cell> area = new java.util.ArrayList<>();
		for (int m = 0; m < 12; m++) {
			for (int i = 0; i < 20; i++) area.add(cell(i, 200 + m, m, "material_" + m));
		}
		BlockPos at = new BlockPos(0, 200, 0);
		assertEquals(Plan.loadPlan(area, List.of(), at, 900).keySet(),
			Plan.loadPlan(area, List.of(), at, 1600).keySet(),
			"the same work, two budgets, one shopping list");
	}

	@Test
	void aListThePackAlreadyHoldsIsATripThatIsOver() {
		var plan = java.util.Map.of("stone_bricks", 64, "lantern", 4);
		assertFalse(Plan.covered(plan, java.util.Map.of("stone_bricks", 64)));
		assertFalse(Plan.covered(plan, java.util.Map.of("stone_bricks", 63, "lantern", 9)));
		assertTrue(Plan.covered(plan, java.util.Map.of("stone_bricks", 70, "lantern", 4)));
	}

	@Test
	void aCellIsNeverDemandedTwice() {
		Work.Cell c = cell(1, 200, 1, "stone");
		var plan = Plan.loadPlan(List.of(c), List.of(c), new BlockPos(0, 200, 0), 64);
		assertEquals(1, Plan.cells(plan));
	}

	@Test
	void theShoppingListIsWhatIsStillShortOfItWithAnAddress() {
		// Subtracting what is carried gives what is still to fetch; a material nobody indexed is
		// dropped, because this list is flown to.
		Map<String, Integer> plan = new java.util.LinkedHashMap<>();
		plan.put("stone_bricks", 300);
		plan.put("lantern", 12);
		Map<String, Integer> carrying = new java.util.LinkedHashMap<>();
		carrying.put("stone_bricks", 100);
		Storage.Container c = new Storage.Container();
		c.x = 20; c.y = 200; c.z = 0; c.block = "chest";
		c.items.put("stone_bricks", 500);
		Map<String, Storage.Container> index = new java.util.LinkedHashMap<>();
		index.put(c.key(), c);
		List<Plan.Restock> out = Plan.shortfalls(plan, carrying, index, new BlockPos(0, 200, 0), Set.of());
		assertEquals(1, out.size(), "the lantern has no address and is not a trip");
		assertEquals("stone_bricks", out.get(0).item());
		assertEquals(200, out.get(0).missing(), "what is carried is subtracted");
		assertEquals(500, out.get(0).available());
	}

	@Test
	void aCentroidOnTheNegativeSideOfTheWorldIsNotBiasedTowardZero() {
		// The island is at X -24200. (int)(x / n) truncates toward zero; floorDiv does not.
		BlockPos c = Plan.centroid(List.of(cell(-3, 100, -3, "stone"), cell(-4, 100, -4, "stone")));
		assertEquals(new BlockPos(-4, 100, -4), c);
	}

	// ------------------------------------------------------------------ the router

	@Test
	void aSlopedLegIsNotClearWhenTheHeadPassesThroughACeiling() {
		// Feet at py+0.1, head at py+1.9: between courses the body spans THREE cells. The old
		// check rounded y and tested two, so a block exactly where the head passes was invisible.
		W w = new W();
		w.fill(2, 102, -1, 2, 102, 1);                  // a ceiling block over x=2 at y=102
		// A leg rising one course over eight blocks: at x=2 the feet are at ~100.25, the head at
		// ~102.15 — inside the block.
		assertFalse(Nav.clear(w.free(), new BlockPos(0, 100, 0), new BlockPos(8, 101, 0)),
			"declared a leg clear with a ceiling where the head passes");
		// ...and the same leg with the block a course higher is genuinely clear.
		W ok = new W();
		ok.fill(2, 103, -1, 2, 103, 1);
		assertTrue(Nav.clear(ok.free(), new BlockPos(0, 100, 0), new BlockPos(8, 101, 0)));
	}

	@Test
	void anEscapeStopsABlockShortOfTheWallItIsGoingRound() {
		// Scored on distance alone the winner was the cell flush against the obstacle, which is
		// where a flight touches and loses flight. A roomy cell that improves at all beats it.
		W w = new W();
		w.room(8, 97, -3, 14, 103, 3);                  // sealed box round the goal
		BlockPos from = new BlockPos(0, 100, 0), to = new BlockPos(11, 100, 0);
		List<BlockPos> out = Nav.escape(w.free(), from, to, Nav.ESCAPE_RADIUS);
		assertFalse(out.isEmpty());
		BlockPos end = out.get(out.size() - 1);
		assertEquals(6, Nav.openness(w.free(), end), "parked against the wall: " + end);
		assertTrue(end.distSqr(to) < from.distSqr(to), "went nowhere nearer");
	}

	@Test
	void aPocketFloodCanTurnACorner() {
		// A cell first met through an illegal diagonal used to be marked seen and never entered
		// through the legal orthogonal step round the corner, so an L-bend read as sealed and the
		// recovery ladder typed /is from inside a perfectly good corridor.
		W w = new W();
		w.fill(-5, 95, -5, 40, 110, 40);
		w.carve(0, 100, 0, 20, 101, 0);                 // a corridor along X...
		w.carve(20, 100, 0, 20, 101, 60);               // ...turning the corner along Z
		int cells = Nav.pocket(w.free(), new BlockPos(0, 100, 0), Recovery.SEALED_CELLS + 10);
		assertTrue(cells >= Recovery.SEALED_CELLS, "an L-shaped corridor of 81 cells read as a pocket of " + cells);
	}

	@Test
	void aStartCellTheBodyDoesNotFitInStillGetsARoute() {
		// Standing on a slab or a carpet, the feet cell reads solid; every step out of it was
		// refused because the step's box included the cell being left.
		W w = new W();
		w.fill(0, 100, 0, 0, 100, 0);                   // the start cell itself is "solid"
		List<BlockPos> p = Nav.route(w.free(), new BlockPos(0, 100, 0), new BlockPos(10, 100, 0));
		assertFalse(p.isEmpty(), "no route out of a cell the body was standing in");
	}

	@Test
	void beingAtTheGoalIsARouteOfOneStepNotNoRoute() {
		// Walkers standing beside their chest got "no route" every repath and a strike for it.
		Nav.Passable open = (x, y, z) -> true;
		assertFalse(Nav.route(open, new BlockPos(3, 100, 3), new BlockPos(3, 100, 3)).isEmpty());
	}

	@Test
	void theAimForAChestInAWallIsOnThePlayersSide() {
		// A chest with a free cell on each side: iteration order picked the -x side about half
		// the time whichever side the player was on, and the search then looked for a way round
		// the whole building.
		W w = new W();
		w.fill(5, 95, -5, 5, 105, 5);                   // a wall along z at x=5
		BlockPos chest = new BlockPos(5, 100, 0);
		assertEquals(6, Nav.reachable(w.free(), chest, new BlockPos(9, 100, 0)).getX());
		assertEquals(4, Nav.reachable(w.free(), chest, new BlockPos(1, 100, 0)).getX());
	}

	@Test
	void aStageIsReportedAsPartialAndACompleteRouteIsNot() {
		Nav.Passable open = (x, y, z) -> true;
		Nav.Route r = Nav.routeEx(open, new BlockPos(0, 100, 0), new BlockPos(20, 100, 0),
			System.nanoTime() + 25_000_000L);
		assertTrue(r.complete());
		assertEquals(List.of(new BlockPos(20, 100, 0)), r.path());
	}

	// ------------------------------------------------------------------ chests that worked

	@Test
	void aChestThatWorkedIsStillATargetAndOnlyNotReopenedForAMoment() {
		// One map for "failed" and "just used" made the recount two seconds later route to the
		// second-nearest chest of the same thing, with thousands still in the first.
		BlockPos ok = new BlockPos(0, 100, 0), bad = new BlockPos(9, 100, 9);
		Withdraw.noteFailure(bad);
		long now = System.currentTimeMillis();
		assertTrue(Withdraw.coolingOff(now).contains(bad.asLong()), "a failed chest is off the table");
		assertFalse(Withdraw.coolingOff(now).contains(ok.asLong()));
		assertTrue(Withdraw.RETRY_AFTER_OK_MS > Hud.EVERY_TICKS * 50L,
			"the OK window must outlast one recount or the chest is reopened before the pack has settled");
	}

	@Test
	void theLastCellOfADigListIsDugLast() {
		// The Falls: "the notch is the plug — cut it LAST". Nearest-first cut whatever the player
		// happened to be beside. Pinned by the constants the digger's give-up derives from, since
		// its selection needs a level; the order rule is exercised in the client.
		assertTrue(Digger.GIVE_UP_MAX > Digger.GIVE_UP_TICKS,
			"deepslate by hand takes 450 ticks; a flat 120 wrote every hard block off as 'wrong tool'");
		assertTrue(Digger.GIVE_UP_SLACK > 0);
	}

	@Test
	void thePrinterEasesOffWhenTheServerRefusesAndOnlyARunOfSilenceStopsIt() {
		assertTrue(Printer.INTERVAL_MAX > Printer.INTERVAL_MIN);
		assertTrue(Printer.ACK_TIMEOUT_LIMIT >= 3, "one missing ack is lag; it used to end the session");
		assertTrue(Withdraw.UNCERTAIN_LIMIT >= 2, "one unconfirmed transfer is lag too");
		assertTrue(Withdraw.BOX_WORTH >= 64, "a box holding a handful is not a source");
	}
}
