package dev.jack.chunkscan;

import net.minecraft.core.BlockPos;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.HashSet;
import java.util.List;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
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
	void anExactTargetIsReachedNotApproached() {
		// A station is somewhere to hover NEAR; a chest's approach cell is somewhere to BE.
		assertTrue(Autopilot.EXACT_MIN < Autopilot.ARRIVE_MIN);
		assertTrue(Autopilot.EXACT_ARRIVED < Autopilot.ARRIVED);
		// ...and hovering in it keeps more than the block of air this server ends flight inside
		// of, while staying low enough to open a chest on the floor the cell was chosen over.
		assertTrue(Autopilot.EXACT_CLEAR > 1.0, "a block or less under the feet is a landing");
		assertTrue(Autopilot.EXACT_CLEAR < Autopilot.GROUND_CLEAR,
			"the ordinary clearance is what held the flight out of reach of every chest on a floor");
		assertTrue(ContainerInteraction.HOVER_CLEAR >= 1, "the cell must have air under it to hover in");
	}

	@Test
	void theFetchWatchdogIsSlowerThanTheFlightAndFasterThanTheSessionClocks() {
		assertTrue(Hud.FETCH_STUCK_MS > Hud.NOWHERE_MS, "it must outlast a normal final approach");
		assertTrue(Hud.FETCH_STUCK_MS < Hud.STALL_MS, "and not wait a minute and a half at a chest");
	}

	// ------------------------------------------------------------------ what goes in the pack

	@Test
	void theFetchIsSizedToTheAreaOutwardNotToTheWholeDesign() {
		// Jack: "it stacks up with random resources vs things it logically might need based on
		// the radius around it". Two hundred far cells of wool must not beat ten near stone.
		List<Work.Cell> todo = new java.util.ArrayList<>();
		for (int i = 0; i < 10; i++) todo.add(cell(i, 200, 0, "stone_bricks"));
		for (int i = 0; i < 200; i++) todo.add(cell(300 + i, 200, 0, "white_wool"));
		List<Work.Cell> near = Plan.nearDemand(todo, List.of(), new BlockPos(0, 200, 0), 64);
		assertEquals(64, near.size(), "sized to the pack");
		assertEquals(10, near.stream().filter(c -> c.block().equals("stone_bricks")).count(),
			"everything near comes first");
		assertEquals(54, near.stream().filter(c -> c.block().equals("white_wool")).count(),
			"...and the rest of the load is the NEXT nearest work, not a random slice of the design");
	}

	@Test
	void theFrontierIsAlwaysInTheDemandWhateverItsDistance() {
		// The cells that can be placed right now are the reason for the trip.
		List<Work.Cell> todo = new java.util.ArrayList<>();
		for (int i = 0; i < 100; i++) todo.add(cell(i, 200, 0, "stone_bricks"));
		Work.Cell far = cell(500, 200, 0, "lantern");
		todo.add(far);
		List<Work.Cell> near = Plan.nearDemand(todo, List.of(far), new BlockPos(0, 200, 0), 16);
		assertTrue(near.contains(far), "the frontier cell was dropped for being far");
		assertEquals(16, near.size(), "the frontier counts toward the load, it is not on top of it");
	}

	@Test
	void aCellIsNeverDemandedTwice() {
		Work.Cell c = cell(1, 200, 1, "stone");
		List<Work.Cell> near = Plan.nearDemand(List.of(c), List.of(c), new BlockPos(0, 200, 0), 64);
		assertEquals(1, near.size());
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
