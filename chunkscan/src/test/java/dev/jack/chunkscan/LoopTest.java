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
}
