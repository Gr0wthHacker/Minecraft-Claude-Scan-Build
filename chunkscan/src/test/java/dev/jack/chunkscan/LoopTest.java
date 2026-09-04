package dev.jack.chunkscan;

import net.minecraft.core.BlockPos;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * The build loop's judgements, asked the awkward questions directly.
 *
 * <p>Every bug in the unattended loop has lived in these four decisions, and none of them could be
 * tested while they were written inline in a method that also opens chests, draws particles and
 * flies a player. Each test below is a bug that shipped.
 */
class LoopTest {
	// ---------------------------------------------------------------- phase

	@Test
	void itDoesNotGoShoppingWhileItHasWorkInFrontOfIt() {
		// THE COMMUTING BUG. The decision was made per SPOT: if the best cluster was short of
		// anything, fetch. So it flew to a chest with a full pack and hundreds of placeable cells,
		// took one spot's worth, and flew back.
		assertEquals(Loop.Phase.BUILD, Loop.phase(500, 0, true, false, true, true),
			"went shopping with work in front of it");
	}

	@Test
	void aTripKeepsGoingUntilThePackIsFull() {
		// ...and the other half: once started, the trip does not stop at the first stack. `fetching`
		// carries between calls, or the loop flip-flops at the boundary - one stack, fly back, find
		// it is short again, fly out again.
		assertEquals(Loop.Phase.FETCH, Loop.phase(500, 0, true, true, true, true),
			"abandoned a fetch trip the moment one spot became workable");
		// and it ends when there is nothing left worth fetching
		assertEquals(Loop.Phase.BUILD, Loop.phase(500, 0, true, true, false, false));
	}

	@Test
	void outOfWorkWithSomewhereToFetchFromIsATrip() {
		assertEquals(Loop.Phase.FETCH, Loop.phase(500, 0, false, false, true, true));
	}

	@Test
	void theTwoDeadEndsAreToldApart() {
		// They want different answers: one sends you to the store hall, the other says your pack is
		// full of something this design cannot use. Saying the wrong one sends you to look at a
		// chest that has nothing you need.
		assertEquals(Loop.Phase.DEAD_END, Loop.phase(500, 0, false, false, false, false),
			"nothing to place and nothing indexed to fetch");
		assertEquals(Loop.Phase.PACK_FULL, Loop.phase(500, 0, false, false, false, true),
			"something to fetch and nowhere to put it");
	}

	@Test
	void outOfViewIsNotFinished() {
		// THE ONE THAT ENDED A `follow all` RUN IN A SECOND. `split` can only diff chunks the client
		// has, so an empty todo means "nothing left HERE". Start at the far end of the island and
		// every design in turn reports complete.
		assertEquals(Loop.Phase.LOOK, Loop.phase(0, 4000, false, false, false, false),
			"called a design finished with 4,000 cells out of view");
		assertEquals(Loop.Phase.COMPLETE, Loop.phase(0, 0, false, false, false, false));
	}

	@Test
	void aFinishedDesignIsNeverAFetchTrip() {
		// Complete beats everything, including a fetch in progress: there is nothing to carry the
		// materials TO.
		assertEquals(Loop.Phase.COMPLETE, Loop.phase(0, 0, false, true, true, true));
	}

	// ---------------------------------------------------------------- the spot

	private static Plan.Cluster cluster(BlockPos centre, int ready) {
		List<Work.Cell> cells = new ArrayList<>();
		for (int i = 0; i < ready; i++) {
			cells.add(new Work.Cell(centre.offset(i % 3, 0, i / 3), "stone_bricks"));
		}
		Map<String, Integer> want = new LinkedHashMap<>();
		want.put("stone_bricks", ready);
		return new Plan.Cluster(centre, cells, cells, want, 0, 0, 0);
	}

	@Test
	void aSpotIsKeptWhileItStillHasWork() {
		BlockPos at = new BlockPos(0, 100, 0);
		Plan.Cluster here = cluster(at, 20);
		Plan.Cluster far = cluster(new BlockPos(400, 100, 400), 900);
		// the far one is bigger; the point of hysteresis is that we do not chase it mid-spot
		assertSame(here, Loop.sameSpot(at, List.of(far, here), Plan.MAX_RADIUS));
	}

	@Test
	void aDriftingCentroidIsStillTheSameSpot() {
		// A cluster's centre is the centroid of what is LEFT, so it moves a block or two every time
		// some of it goes in. Comparing exactly called every recount a new spot: stations reset and
		// the arrival re-announced, twice a second, for the whole session.
		BlockPos was = new BlockPos(0, 100, 0);
		Plan.Cluster drifted = cluster(new BlockPos(3, 101, 2), 15);
		assertNotNull(Loop.sameSpot(was, List.of(drifted), Plan.MAX_RADIUS),
			"a centroid that moved three blocks became a different spot");
	}

	@Test
	void anExhaustedSpotIsLetGo() {
		BlockPos at = new BlockPos(0, 100, 0);
		Plan.Cluster empty = cluster(at, 0);
		assertNull(Loop.sameSpot(at, List.of(empty), Plan.MAX_RADIUS),
			"held on to a spot with nothing doable in it");
	}

	@Test
	void aSpotOnTheOtherSideOfTheIslandIsNotTheSameSpot() {
		assertNull(Loop.sameSpot(new BlockPos(0, 100, 0),
			List.of(cluster(new BlockPos(900, 40, 900), 50)), Plan.MAX_RADIUS));
	}

	@Test
	void noSpotYetMeansPickOne() {
		assertNull(Loop.sameSpot(null, List.of(cluster(new BlockPos(0, 100, 0), 9)),
			Plan.MAX_RADIUS));
	}

	// ---------------------------------------------------------------- the station clock

	@Test
	void aStationThatIsPlacingIsLeftAlone() {
		assertEquals(Loop.Station.WORKING, Loop.station(true, true, 10, 10, 2_000, 5_000, 0));
	}

	@Test
	void placingSomeOfItWalksYouRoundWhatIsLeft() {
		// A bin is a 4-cube: its far corner is 3.46 from the middle and the printer has 4.5, so
		// standing where you first arrived builds the near face and stops. Re-aiming at the centroid
		// of what remains is the "different angles" - it falls out of this rather than being an orbit.
		assertEquals(Loop.Station.RECENTRE, Loop.station(true, true, 6, 10, 1_000, 5_000, 0));
	}

	@Test
	void aStationThatPlacesNothingMovesInCloserBeforeGivingUp() {
		// Abandoning a bin you could have reached leaves those cells for a later pass that will make
		// exactly the same mistake.
		assertEquals(Loop.Station.CLOSER, Loop.station(true, true, 10, 10, 6_000, 5_000, 0));
		assertEquals(Loop.Station.ABANDON, Loop.station(true, true, 10, 10, 6_000, 5_000, 1));
	}

	@Test
	void progressResetsThePatience() {
		// The clock is about "is anything happening here", so a placement anywhere in the bin has to
		// clear it - otherwise a slow but working station is abandoned mid-wall.
		assertEquals(Loop.Station.RECENTRE, Loop.station(true, true, 9, 10, 999_999, 5_000, 1));
	}

	@Test
	void aNewBinIsNewWhateverTheClockSays() {
		assertEquals(Loop.Station.NEW, Loop.station(false, true, 10, 10, 999_999, 5_000, 1));
	}

	@Test
	void aFirstVisitHasNoPreviousCount() {
		// -1 means "not known yet", and it must not read as "the count went down".
		assertEquals(Loop.Station.WORKING, Loop.station(true, true, 10, -1, 0, 5_000, 0));
	}

	// ---------------------------------------------------------------- the session stall

	@Test
	void aFetchTripIsNotAStall() {
		// Nothing is placed while you fly to a chest, and reporting that as a stall abandons the
		// spot you were about to come back and build.
		assertFalse(Loop.stalled(200_000, 0, true, 90_000));
		assertTrue(Loop.stalled(200_000, 0, false, 90_000));
	}

	@Test
	void theStallIsMeasuredFromTheLastPLACEMENT() {
		// `todo` shrinking is the only honest evidence a block went in: the printer never reports,
		// so the world is the report.
		assertFalse(Loop.stalled(100_000, 99_000, false, 90_000), "one second is not a stall");
		assertTrue(Loop.stalled(100_000, 5_000, false, 90_000));
	}

	// ---------------------------------------------------------------- boxed materials

	private static Plan.Restock want(String item, int missing) {
		Storage.Container c = new Storage.Container();
		c.x = 50;
		c.y = 195;
		c.z = 50;
		c.block = "chest";
		c.id = 7;
		c.items.put("minecraft:" + item, 500);
		return new Plan.Restock(item, missing, c, 500);
	}

	@Test
	void aTripIsNotMadeForSomethingOnYourOwnHip() {
		// A block in a shulker box is NOT placeable - you would have to set the box down, open it,
		// take the stack and break the box, none of which this mod does - so it cannot be counted as
		// carried. But it is absolutely a reason not to fly across the island for more.
		Map<String, Integer> boxes = new LinkedHashMap<>();
		boxes.put("stone_bricks", 1728);
		List<String> told = new ArrayList<>();
		List<Plan.Restock> left = Plan.notInAPack(List.of(want("stone_bricks", 600)), boxes,
			told::add);
		assertTrue(left.isEmpty(), "flew for bricks that were in a box on the player");
		assertEquals(List.of("stone_bricks"), told, "and said nothing about why it did not go");
	}

	@Test
	void aBoxThatDoesNotCoverTheShortfallIsStillATrip() {
		// Half a box is not a solution: you would set it down, take 64, and still be short.
		Map<String, Integer> boxes = new LinkedHashMap<>();
		boxes.put("stone_bricks", 64);
		assertEquals(1, Plan.notInAPack(List.of(want("stone_bricks", 600)), boxes, x -> {}).size());
	}

	@Test
	void anEmptyPackChangesNothing() {
		List<Plan.Restock> targets = List.of(want("stone_bricks", 600));
		assertSame(targets, Plan.notInAPack(targets, Map.of(), x -> {}));
	}

	@Test
	void onlyTheMaterialInTheBoxIsSkipped() {
		Map<String, Integer> boxes = new LinkedHashMap<>();
		boxes.put("stone_bricks", 1728);
		List<Plan.Restock> left = Plan.notInAPack(
			List.of(want("stone_bricks", 600), want("deepslate_bricks", 200)), boxes, x -> {});
		assertEquals(1, left.size());
		assertEquals("deepslate_bricks", left.get(0).item());
	}

	// ---------------------------------------------------------------- the phases compose

	@Test
	void aWholeSessionOfPhasesTerminates() {
		// The property that matters for leaving it running: from any starting point, the loop either
		// does something or says why - it never sits in a phase with nothing to do and no message.
		for (int todo : new int[]{0, 500}) {
			for (int unseen : new int[]{0, 40}) {
				for (boolean canWork : new boolean[]{false, true}) {
					for (boolean fetching : new boolean[]{false, true}) {
						for (boolean target : new boolean[]{false, true}) {
							for (boolean any : new boolean[]{false, true}) {
								Loop.Phase p = Loop.phase(todo, unseen, canWork, fetching, target,
									any);
								assertNotNull(p);
								if (p == Loop.Phase.FETCH) {
									assertTrue(target, "a fetch phase with nowhere to fetch from");
								}
								if (p == Loop.Phase.BUILD) {
									assertTrue(todo > 0, "a build phase with nothing to build");
								}
							}
						}
					}
				}
			}
		}
	}

	@Test
	void theStationClockStartsWhenYouGetThere() {
		// A five-second window is only safe if it is about the PRINTER and not the journey. Timed
		// from the moment the station is chosen, anything more than a few seconds' flight away is
		// abandoned before the printer has ever had a chance at it — a loop touring bins and placing
		// nothing, which looks exactly like the failure the clock exists to catch.
		assertEquals(Loop.Station.WORKING, Loop.station(true, false, 10, 10, 999_999, 5_000, 0),
			"gave up on a station it had not reached yet");
		assertEquals(Loop.Station.CLOSER, Loop.station(true, true, 10, 10, 999_999, 5_000, 0),
			"...and once there, five seconds of nothing is enough");
	}

	@Test
	void fiveSecondsIsTheWindow() {
		assertEquals(5_000L, Hud.STATION_MS, "the per-station patience moved");
		assertTrue(Hud.STATION_MS < Hud.STALL_MS,
			"a station must give up long before the whole loop does");
	}

	// ---------------------------------------------------------------- going nowhere

	@Test
	void threeSecondsOfNotMovingIsEnough() {
		// The fast clock. A flight that has not moved in three seconds is not about to start: it is
		// pressed into a corner, routing at a wall, or wedged under something.
		assertTrue(Loop.goingNowhere(10_000, 6_000, 6_000, true, false, 3_000));
		assertFalse(Loop.goingNowhere(10_000, 8_500, 6_000, true, false, 3_000),
			"it moved a second and a half ago");
	}

	@Test
	void placingCountsAsGettingSomewhere() {
		// "doesn't move OR doesn't perform action" — hovering at the work while the printer takes
		// blocks off you is the loop doing exactly its job, and the arrow is on the work, so the
		// travelling test alone would not save it.
		assertFalse(Loop.goingNowhere(10_000, 1_000, 9_000, true, false, 3_000),
			"gave up on a spot that is actively placing");
	}

	@Test
	void standingStillIsOnlyWrongWhileTravelling() {
		// At the work you hover; at a chest you stand while the withdrawal runs. Neither is stuck.
		assertFalse(Loop.goingNowhere(10_000, 0, 0, false, false, 3_000), "not going anywhere");
		assertFalse(Loop.goingNowhere(10_000, 0, 0, true, true, 3_000), "mid-withdrawal");
	}

	@Test
	void theThreeClocksAreOrderedByWhatTheyAskAbout() {
		// going nowhere < a station that will not print < the whole loop doing nothing. Getting this
		// order wrong means the slow one fires first and the fast one never does.
		assertTrue(Hud.NOWHERE_MS < Hud.STATION_MS, "a travel stall must beat a station stall");
		assertTrue(Hud.STATION_MS < Hud.STALL_MS, "a station stall must beat the session stall");
	}

	// ---------------------------------------------------------------- filling the pack first

	@Test
	void aStartFETCHESBeforeItBuilds() {
		// Build-before-shop is right in the middle of a session and wrong at the start of one: it
		// sets off with whatever was in the pack and makes the trip anyway once that runs out,
		// having already flown to the work and back.
		assertEquals(Loop.Phase.FETCH,
			Loop.phase(500, 0, true, false, true, true, true));
	}

	@Test
	void aStartWithNothingToFetchGetsStraightOnWithIt() {
		// A full pack and a fully-stocked design look identical from here, and both mean build.
		assertEquals(Loop.Phase.BUILD,
			Loop.phase(500, 0, true, false, false, false, true));
	}

	@Test
	void theTopUpDoesNotChangeWhatHappensLaterInASession() {
		// Off, every answer is exactly what it was before the flag existed.
		for (int t : new int[]{0, 500}) {
			for (boolean w : new boolean[]{true, false}) {
				for (boolean f : new boolean[]{true, false}) {
					for (boolean h : new boolean[]{true, false}) {
						for (boolean a : new boolean[]{true, false}) {
							assertEquals(Loop.phase(t, 0, w, f, h, a),
								Loop.phase(t, 0, w, f, h, a, false),
									"the flag changed a decision it was off for");
						}
					}
				}
			}
		}
	}

	// ---------------------------------------------------------------- one area at a time

	private static Work.Cell at(int x, int y, int z) {
		return new Work.Cell(new BlockPos(x, y, z), "stone_bricks");
	}

	@Test
	void workAcrossTheIslandIsNotThisAreasWork() {
		java.util.List<Work.Cell> all = java.util.List.of(
			at(0, 200, 0), at(30, 200, 10), at(900, 200, 0));
		java.util.List<Work.Cell> here = Loop.focus(all, new BlockPos(0, 200, 0), Loop.WORK_RADIUS);
		assertEquals(2, here.size(), "the far end of the island came along");
	}

	@Test
	void theAreaMovesToTheNEARESTRemainingWorkNotTheBiggestPile() {
		// So it walks across a design rather than touring it: the biggest pile is exactly the
		// criterion that sent it back and forth in the first place.
		java.util.List<Work.Cell> all = new java.util.ArrayList<>();
		all.add(at(400, 200, 0));
		for (int i = 0; i < 50; i++) all.add(at(900 + i, 200, 0));
		assertEquals(new BlockPos(400, 200, 0), Loop.reanchor(all, new BlockPos(0, 200, 0)));
	}

	@Test
	void anAreaWithNoAnchorIsTheWholeDesign() {
		// Before the first recount there is nowhere to be focused on, and refusing everything would
		// be a loop that does nothing on its first tick and says why on none of them.
		java.util.List<Work.Cell> all = java.util.List.of(at(0, 200, 0), at(9000, 200, 0));
		assertEquals(2, Loop.focus(all, null, Loop.WORK_RADIUS).size());
	}

	@Test
	void nothingLeftAnywhereIsNotAFocusProblem() {
		assertNull(Loop.reanchor(java.util.List.of(), new BlockPos(0, 200, 0)));
	}

	@Test
	void aTopUpSURVIVESARecountThatCouldNotAsk() {
		// The bug: the frontier is empty at the start of most sessions, because the design is across
		// the island and its chunks have not loaded. Gated on a non-empty frontier the fetch
		// question was never asked, the phase came back BUILD, and the top-up was cleared having
		// done nothing. It is not over until it has been answered.
		assertFalse(Loop.topUpOver(Loop.Phase.BUILD, false), "ended before it was asked");
		assertFalse(Loop.topUpOver(Loop.Phase.LOOK, false));
		assertFalse(Loop.topUpOver(Loop.Phase.DEAD_END, false));
	}

	@Test
	void aTopUpEndsOnceItHasBeenAnswered() {
		assertTrue(Loop.topUpOver(Loop.Phase.BUILD, true));
		assertTrue(Loop.topUpOver(Loop.Phase.DEAD_END, true));
		assertFalse(Loop.topUpOver(Loop.Phase.FETCH, true), "ended mid-trip");
	}

	@Test
	void aCompositeSpanningSeveralPlotsHasAnOriginOnNoneOfThem() {
		// The evidence, kept because it is what made the storage index vanish. `Park Complete`
		// origins at (97500, 80300) - the corner of its bounding box - and the three park plots
		// start at 97551 and 80351, so the origin is on no island at all. Anything that decides
		// 'whose ground is this' from a litematic's origin is deciding it from a padding corner.
		int[][] plots = {{97600, 80400}, {97600, 80600}, {97600, 80800}};
		int ox = 97500, oz = 80300;
		for (int[] c : plots) {
			assertFalse(Math.abs(ox - c[0]) <= 49 && Math.abs(oz - c[1]) <= 49,
				"the fixture is wrong: the origin is inside a plot after all");
		}
		// ...while the design itself plainly stands on all three.
		int[][] cells = {{97600, 80400}, {97600, 80600}, {97600, 80800}};
		for (int[] cell : cells) {
			boolean any = false;
			for (int[] c : plots) {
				if (Math.abs(cell[0] - c[0]) <= 49 && Math.abs(cell[1] - c[1]) <= 49) any = true;
			}
			assertTrue(any, "a cell of the design is on no plot");
		}
	}

	// ---------------------------------------------------------------- a fetch is a trip

	private static BlockPos at(int x, int z) { return new BlockPos(x, 200, z); }

	@Test
	void aFetchTakesWhatIsINRANGEBeforeWhatIsBiggest() {
		// Ranked by shortfall size alone the biggest pile won however far away it was - and an index
		// spanning two worlds 120,000 blocks apart made that a flight no route can even be searched
		// for, so it fell through to going direct and simply kept going.
		java.util.List<BlockPos> targets = java.util.List.of(at(120_000, 0), at(30, 0), at(90_000, 0));
		java.util.List<BlockPos> ranked = Loop.byTrip(targets, p -> p, at(0, 0), Loop.FETCH_RADIUS);
		assertEquals(at(30, 0), ranked.get(0), "crossed two worlds past a chest thirty blocks away");
	}

	@Test
	void anOutOfRangeTripIsKeptRatherThanDropped() {
		// If the only stock in the world is far away, going is still better than stopping. It is
		// the ORDER that changes, not the offer.
		java.util.List<BlockPos> only = java.util.List.of(at(120_000, 0));
		assertEquals(1, Loop.byTrip(only, p -> p, at(0, 0), Loop.FETCH_RADIUS).size());
		assertTrue(Loop.allFar(only, p -> p, at(0, 0), Loop.FETCH_RADIUS),
			"a trip across two worlds is not being reported as one");
	}

	@Test
	void nothingToFetchIsNotAFarFetch() {
		assertFalse(Loop.allFar(java.util.List.<BlockPos>of(), p -> p, at(0, 0), Loop.FETCH_RADIUS));
	}

	@Test
	void aFetchMayTravelFurtherThanTheBuildEverDoes() {
		// One journey to fill a pack is worth more than a hundred journeys to place a hundred
		// blocks - so the two bounds are deliberately different, and the fetch is the looser.
		assertTrue(Loop.FETCH_RADIUS > Loop.WORK_RADIUS);
	}

	// ---------------------------------------------------------------- one course at a time

	private static Nav.Passable air(java.util.Set<Long> solid) {
		return (x, y, z) -> !solid.contains(BlockPos.asLong(x, y, z))
			&& !solid.contains(BlockPos.asLong(x, y + 1, z));
	}

	private static Work.Cell c(int x, int y, int z) {
		return new Work.Cell(new BlockPos(x, y, z), "stone_bricks");
	}

	@Test
	void aStationIsNeverWiderThanONEStandCanFinish() {
		// The bin used to be the printer's range, floored - and a bin that wide cannot be covered
		// from a spot inside it: a square of side b has its far corner b*sqrt(2)/2 from the middle,
		// and the stand only has reach - ARRIVE_MIN. At the real 4.2 a 4-wide bin is 2.83 against
		// 3.0 and just fits; at 4 it is 2.83 against 2.8 and does not, and nothing said so - the
		// leftover corner was highlighted, flown to and stalled on. Derived, it cannot not fit.
		double stand = Plan.reachExact() - Autopilot.ARRIVE_MIN;
		double corner = Math.sqrt(2) * Plan.binSize() / 2.0;
		assertTrue(corner <= stand,
			"the station is wider than one stand can finish: " + corner + " > " + stand);
		assertTrue(Plan.binSize() >= 2, "a station one cell wide is not a station");
	}

	@Test
	void aStandIsFOUNDThatCoversAWholeCourseBin() {
		// Asserted through the search rather than by hand, because hand-picking one is how you get
		// the arithmetic wrong: two courses above a bin already puts the eyes 3.1 from its far cell
		// at reach 4, which is out. What actually works is being CLOSE to the course - level with
		// it, or one above - which is the same thing as landing on the finished course below.
		int b = Plan.binSize();
		java.util.List<Work.Cell> square = new java.util.ArrayList<>();
		for (int x = 0; x < b; x++) for (int z = 0; z < b; z++) square.add(c(x, 100, z));
		BlockPos stand = Plan.bestStand(air(java.util.Set.of()), square, Plan.reachExact(),
			new BlockPos(9, 101, 9), 4, Autopilot.ARRIVE_MIN);
		assertNotNull(stand, "no stand at all for a flat " + b + "x" + b + " course");
		assertEquals(square.size(),
			Plan.coveredFrom(square, stand, Plan.reachExact() - Autopilot.ARRIVE_MIN),
			"the best stand for a whole course bin still cannot finish it");
	}

	@Test
	void itWorksUPWARDSFromTheLowestCourse() {
		// Which is what makes the course below already built, and therefore both the support for
		// this one and a floor to stand on.
		java.util.List<Work.Cell> mixed = java.util.List.of(c(0, 105, 0), c(1, 100, 1), c(2, 103, 2));
		assertEquals(java.util.List.of(100, 103, 105), Loop.layers(mixed));
	}

	@Test
	void aCourseTakesTheBandAboveItAndNothingElse() {
		// A slab and the block it sits on are one course of BUILDING even when they are two of
		// geometry; splitting them costs a whole extra pass over the same ground.
		java.util.List<Work.Cell> stack = java.util.List.of(c(0, 100, 0), c(0, 101, 0), c(0, 102, 0));
		assertEquals(2, Loop.layer(stack, 100, Loop.LAYER_BAND).size());
		assertEquals(1, Loop.layer(stack, 100, 0).size());
	}

	@Test
	void aCourseNeverReachesDOWNWARDS() {
		// It would take work whose support is not built yet, which is the order the whole thing
		// exists to keep.
		java.util.List<Work.Cell> stack = java.util.List.of(c(0, 99, 0), c(0, 100, 0));
		assertEquals(1, Loop.layer(stack, 100, Loop.LAYER_BAND).size());
	}
}
