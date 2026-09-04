package dev.jack.chunkscan;

import net.minecraft.core.BlockPos;
import net.minecraft.world.phys.Vec3;
import org.junit.jupiter.api.Test;

import java.util.HashSet;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.*;

/**
 * The geometry the router and the flight have to AGREE on.
 *
 * <p>Every one of these is a place where two correct-looking rules described different shapes, and
 * the only symptom was a loop that bumped, stalled, or lost flight. None of them is visible in a
 * render and none of them failed a build audit.
 */
class NavGeometryTest {

	private static Nav.Passable air(Set<Long> solid) {
		return (x, y, z) -> !solid.contains(BlockPos.asLong(x, y, z))
			&& !solid.contains(BlockPos.asLong(x, y + 1, z));
	}

	// ------------------------------------------------------------------ the body fits the hole

	@Test
	void aWaypointPutsTheBodyInTheTWOCellsTheSearchChecked() {
		// The router's Passable checks the cell and the one above it. The flight has to put a 1.8
		// tall body inside exactly those two, or a two-course corridor is routable and unflyable.
		Vec3 feet = Autopilot.flyTo(new BlockPos(4, 70, -9));
		assertEquals(4.5, feet.x, 1.0e-9);
		assertEquals(-8.5, feet.z, 1.0e-9);
		int low = (int) Math.floor(feet.y);
		int high = (int) Math.floor(feet.y + 1.8 - 1.0e-9);
		assertEquals(70, low, "feet are not in the waypoint's own cell");
		assertEquals(71, high, "the head reaches past the cell the search checked");
	}

	@Test
	void theOldCentreAimedWaypointDidNotFit() {
		// The bug this replaced, stated so nobody reinstates atCenterOf as "tidier".
		double feetY = 70 + 0.5;
		assertEquals(72, (int) Math.floor(feetY + 1.8 - 1.0e-9),
			"a centre-aimed waypoint really did put the head two cells up");
	}

	@Test
	void aTwoCourseCorridorIsFlyable() {
		// Floor at y=69, ceiling at y=72: cells 70 and 71 are the corridor. The search says yes;
		// with the feet on the cell floor the body agrees.
		Set<Long> solid = new HashSet<>();
		for (int x = -2; x <= 8; x++) {
			solid.add(BlockPos.asLong(x, 69, 0));
			solid.add(BlockPos.asLong(x, 72, 0));
		}
		Nav.Passable free = air(solid);
		assertTrue(free.at(3, 70, 0), "the search cannot even enter its own corridor");
		Vec3 feet = Autopilot.flyTo(new BlockPos(3, 70, 0));
		assertTrue(feet.y > 69 + 1.0 - 1.0e-9, "feet inside the floor");
		assertTrue(feet.y + 1.8 < 72, "head inside the ceiling");
	}

	// ------------------------------------------------------------------ never send a touching step

	@Test
	void aStepIntoAWallSlidesRatherThanStopping() {
		// Per axis, so a heading that is half into a wall keeps the half that is not.
		Vec3 out = Autopilot.avoid(new Vec3(0.5, 0, 0.5), d -> d.x == 0);
		assertEquals(0.0, out.x, 1.0e-9, "kept the component that touches");
		assertEquals(0.5, out.z, 1.0e-9, "threw away a component that was free");
	}

	@Test
	void aStepThatTouchesNothingIsUntouched() {
		Vec3 step = new Vec3(0.3, -0.1, 0.2);
		assertEquals(step, Autopilot.avoid(step, d -> true));
	}

	@Test
	void aBodyAlreadyAgainstSomethingCanStillMoveAway() {
		// The failure that would be WORSE than the one being fixed, because it is silent: every axis
		// refused and the flight frozen. Only the axes that actually meet something are dropped.
		Vec3 out = Autopilot.avoid(new Vec3(-0.4, 0, 0), d -> d.x < 0);
		assertEquals(-0.4, out.x, 1.0e-9, "could not back off what it was against");
	}

	@Test
	void everyAxisBlockedIsAStandstillRatherThanAGuess() {
		assertEquals(Vec3.ZERO, Autopilot.avoid(new Vec3(0.4, 0.2, -0.3), d -> false));
	}

	// ------------------------------------------------------------------ clearance under the BODY

	private static Autopilot.View floorAt(int y, int xFrom, int xTo) {
		return new Autopilot.View() {
			public boolean loaded(int x, int yy, int zz) { return true; }
			public boolean solid(int x, int yy, int zz) {
				return yy == y && x >= xFrom && x <= xTo;
			}
		};
	}

	@Test
	void clearanceIsMeasuredUnderTheWholeBodyNotItsCentreLine() {
		// A ledge ending at x=10. Standing at x=10.9 the CENTRE column is over the void and the
		// body's -x corner is over the deck: the centre-only reading said "nothing below, descend",
		// and the flight touched down on the corner it never looked at. On this server that is the
		// flight gone.
		Autopilot.View w = floorAt(64, 0, 10);
		assertEquals(8.0, Autopilot.clearanceBelow(w, 10.9, 73.0, 0.5, 8), 1.0e-9,
			"the fixture is wrong: the centre column should read as open");
		assertTrue(Autopilot.clearanceBelow(w, 10.9, 66.0, 0.5, 8) < 2.0,
			"a corner is over the ledge and the reading did not see it");
	}

	@Test
	void clearanceStillReadsOpenAirAsOpen() {
		Autopilot.View w = floorAt(64, 0, 10);
		assertEquals(8.0, Autopilot.clearanceBelow(w, 40.0, 100.0, 0.5, 8), 1.0e-9);
	}

	// ------------------------------------------------------------------ two rules, one shape

	@Test
	void aChosenStandingSpotSatisfiesTheAltitudeTheFlightDEMANDS() {
		// AIR_BELOW is what standoff and bestStand guarantee; GROUND_CLEAR is what keepAirborne
		// refuses to descend inside. At two against 2.5 the flight could not settle at a spot this
		// project had chosen for it, and the only symptom was a printer that placed nothing.
		//
		// AIR_BELOW counts CELLS below the waypoint; the feet sit FOOT_OFFSET into it.
		double guaranteed = Nav.AIR_BELOW + Autopilot.FOOT_OFFSET;
		assertTrue(guaranteed > Autopilot.GROUND_CLEAR,
			"a spot with " + guaranteed + " of air cannot satisfy a flight wanting "
				+ Autopilot.GROUND_CLEAR);
	}

	// ------------------------------------------------------------------ circling, not hovering

	private static Work.Cell cell(int x, int y, int z) {
		return new Work.Cell(new BlockPos(x, y, z), "stone_bricks");
	}

	@Test
	void theRingGoesAllTheWayROUNDTheWork() {
		// A parked body is the one that drifts into something. A lap has to present more than one
		// face of the wall or it is a hover with extra steps.
		java.util.List<Work.Cell> pillar = new java.util.ArrayList<>();
		for (int y = 100; y <= 103; y++) pillar.add(cell(0, y, 0));
		java.util.List<BlockPos> lap = Plan.ring(air(Set.of()), pillar, 4.2, 4);
		assertTrue(lap.size() >= 4, "only " + lap.size() + " bearings: that is not a lap");
		Set<Integer> arcs = new HashSet<>();
		for (BlockPos p : lap) arcs.add(Plan.arcOf(p.getX(), p.getZ()));
		assertEquals(lap.size(), arcs.size(), "two stops on the same bearing");
		assertTrue(arcs.size() >= 4, "the lap does not get round the work");
	}

	@Test
	void everyStopOnTheLapCanActuallyWORK() {
		// A bearing the printer cannot reach from is a detour, not a vantage.
		java.util.List<Work.Cell> pillar = new java.util.ArrayList<>();
		for (int y = 100; y <= 103; y++) pillar.add(cell(0, y, 0));
		double reach = 4.2;
		for (BlockPos stop : Plan.ring(air(Set.of()), pillar, reach, 4)) {
			boolean any = false;
			for (Work.Cell c : pillar) {
				if (Math.sqrt(c.pos().distSqr(stop)) <= reach) any = true;
			}
			assertTrue(any, "a stop at " + stop + " reaches nothing");
		}
	}

	@Test
	void everyStopOnTheLapKeepsTheAltitudeTheFlightDEMANDS() {
		// The same contradiction as the static stand: a lap of spots the flight refuses to descend
		// to is a lap of hovering above the work.
		Set<Long> solid = new HashSet<>();
		for (int x = -8; x <= 8; x++) {
			for (int z = -8; z <= 8; z++) solid.add(BlockPos.asLong(x, 99, z));
		}
		Nav.Passable free = air(solid);
		java.util.List<BlockPos> lap = Plan.ring(free, java.util.List.of(cell(0, 104, 0)), 4.2, 4);
		for (BlockPos stop : lap) {
			assertTrue(Nav.airBelow(free, stop, Nav.AIR_BELOW), "stop on the floor: " + stop);
		}
	}

	@Test
	void aCellInASlotGivesNoLapRatherThanANonsenseOne() {
		// Boxed in on every side: there is no bearing to fly to, and the caller must be told that
		// rather than handed a stop it cannot reach.
		Set<Long> solid = new HashSet<>();
		for (int x = -6; x <= 6; x++) {
			for (int y = 95; y <= 110; y++) {
				for (int z = -6; z <= 6; z++) {
					if (!(x == 0 && z == 0)) solid.add(BlockPos.asLong(x, y, z));
				}
			}
		}
		assertTrue(Plan.ring(air(solid), java.util.List.of(cell(0, 100, 0)), 4.2, 4).isEmpty());
	}
}
