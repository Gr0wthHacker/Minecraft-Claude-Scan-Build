package dev.jack.chunkscan;

import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import org.junit.jupiter.api.Test;

import java.util.HashSet;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * The bot building or digging itself into a box.
 *
 * <p>Jack: <i>"its multiple times now sat still and dug completely around itself"</i>, and then, of
 * the guard written for that: <i>"consistently it will box itself in."</i> Every watchdog in this
 * mod asks whether the loop is TRAVELLING and failing, and a bot standing where it means to stand,
 * placing the cells its design names, passes all of them. The fault is in the geometry, so these
 * are about geometry - no client anywhere in them.
 */
class BurialTest {

	/** A world made of the cells you name. */
	private static Burial.Solid world(Set<String> solid) {
		return (x, y, z) -> solid.contains(x + "," + y + "," + z);
	}

	private static Set<String> cells(String... at) {
		return new HashSet<>(java.util.List.of(at));
	}

	/** Four walls round the body at (0,0,0), two courses tall. */
	private static Set<String> pit() {
		Set<String> s = cells();
		for (int[] d : new int[][]{{1, 0}, {-1, 0}, {0, 1}, {0, -1}}) {
			s.add(d[0] + ",0," + d[1]);
			s.add(d[0] + ",1," + d[1]);
		}
		return s;
	}

	/** ...and the same, closed over the head. */
	private static Set<String> tomb() {
		Set<String> s = pit();
		s.add("0,2,0");
		return s;
	}

	@Test
	void openGroundIsNotWalledAtAll() {
		assertEquals(4, Burial.exits(world(cells()), BlockPos.ZERO));
		assertEquals(0, Burial.walled(world(cells()), BlockPos.ZERO));
		assertFalse(Burial.boxedIn(world(cells()), BlockPos.ZERO));
	}

	@Test
	void aPitIsWalledOnEverySide() {
		assertEquals(0, Burial.exits(world(pit()), BlockPos.ZERO));
		assertEquals(4, Burial.walled(world(pit()), BlockPos.ZERO));
		assertTrue(Burial.boxedIn(world(pit()), BlockPos.ZERO));
	}

	@Test
	void aBlockAtTheFEETALONEisAStepAndNotAWall() {
		// The rule that stops the loop rising off every kerb in the park: one block with somewhere
		// to put your head over it, and headroom in your own column to make the jump, is a way out.
		assertTrue(Burial.canLeave(world(cells("1,0,0")), BlockPos.ZERO, Direction.EAST));
		assertEquals(0, Burial.walled(world(cells("1,0,0")), BlockPos.ZERO));
	}

	@Test
	void aStepYouCannotJUMPontoIsAWall() {
		// ...and the step is only a step while there is room to land and room to leave from. A
		// second course over it, or a ceiling over your own head, and it is a wall like any other.
		assertFalse(Burial.canLeave(world(cells("1,0,0", "1,2,0")), BlockPos.ZERO, Direction.EAST));
		assertFalse(Burial.canLeave(world(cells("1,0,0", "0,2,0")), BlockPos.ZERO, Direction.EAST));
	}

	@Test
	void aRingAtHEADHEIGHTisABOXandTheOldCountCalledItOpenGround() {
		// THE BUG JACK KEPT HITTING. A printer working from a body hovering a course over the floor
		// builds the next course at HEAD height - and the old measure called a side walled only when
		// BOTH cells were solid, so this counted as four sides of nothing while the body could not
		// move an inch. A player is 1.8 tall; there is no crouch that fits under a one-block gap.
		Set<String> ring = cells("1,1,0", "-1,1,0", "0,1,1", "0,1,-1");
		assertEquals(0, Burial.exits(world(ring), BlockPos.ZERO));
		assertEquals(4, Burial.walled(world(ring), BlockPos.ZERO));
		assertTrue(Burial.boxedIn(world(ring), BlockPos.ZERO, Burial.SIDES_BUILDING),
			"a head-height ring is a box, whatever the feet can see");
	}

	@Test
	void aROOFEDplaceWITHAWAYOUTisNotAPit() {
		// UNDERGROUND IS WHERE THE LOOP IS SUPPOSED TO BE. A mine gallery, the undercroft, a tunnel:
		// roofed by design, and with a way along it. That is what keeps this out of them - not a
		// blanket exemption for anything with a ceiling, which is what used to hide a sealed body.
		Set<String> gallery = cells("1,0,0", "1,1,0", "-1,0,0", "-1,1,0", "0,2,0");
		assertEquals(2, Burial.exits(world(gallery), BlockPos.ZERO));
		assertFalse(Burial.sealed(world(gallery), BlockPos.ZERO));
		assertFalse(Burial.boxedIn(world(gallery), BlockPos.ZERO, Burial.SIDES_BUILDING));
	}

	@Test
	void aSEALEDbodyIsTheEMERGENCYandNotTheEXEMPTION() {
		// The rescue used to be gated out of exactly this case: boxedIn demanded headroom, so a body
		// that had built itself a lid - the actual "fully stuck" - measured as fine and NOTHING
		// fired. Rising is not on offer here, so it is a different answer, not no answer.
		assertTrue(Burial.sealed(world(tomb()), BlockPos.ZERO));
		assertFalse(Burial.boxedIn(world(tomb()), BlockPos.ZERO, Burial.SIDES_BUILDING),
			"there is nowhere to climb to - LEAVE, not RISE");
		assertFalse(Burial.sealed(world(pit()), BlockPos.ZERO),
			"an open-top shaft is not sealed; it is somewhere to climb out of");
	}

	@Test
	void aDoorwayIsTwoSidesAndMustNotFireInstantly() {
		// Two shut sides is a doorway, a corridor and a trench as much as it is a grave. The
		// geometry cannot tell them apart; TIME can, which is what HOLD_TICKS is for.
		assertTrue(Burial.HOLD_TICKS >= 20,
			"a bot that lifts out of every doorway it steps into cannot build anywhere narrow");
	}

	@Test
	void itOnlyEverRises() {
		// Working out which way is OUT is a search, and the recovery ladder owns searches. Up is the
		// one direction that is always right in a pit, and one course of it re-opens the sides.
		assertTrue(Burial.RISE > 0);
	}

	@Test
	void buildingBesideAWallIsNotBeingBoxedIn() {
		// THE GATE THAT REPLACED A BLIND SPOT. At two sides this fired at every station the loop
		// picks - standing beside the wall you are putting up - so it rose, the sides opened, the
		// autopilot flew it back down and it bounced there placing nothing. The first answer was to
		// stop looking whenever there was a destination, which hid the one case it exists for: a
		// printer walls its own STATION in, and a station is a destination.
		Set<String> two = cells("1,0,0", "1,1,0", "-1,0,0", "-1,1,0");
		assertTrue(Burial.boxedIn(world(two), BlockPos.ZERO, Burial.SIDES),
			"two sides is a doorway, a corridor, or a wall going up");
		assertFalse(Burial.boxedIn(world(two), BlockPos.ZERO, Burial.SIDES_BUILDING),
			"...and while building it is exactly where the loop is supposed to be");
	}

	@Test
	void allFourSidesIsABoxWhateverIsBeingDone() {
		assertTrue(Burial.boxedIn(world(pit()), BlockPos.ZERO, Burial.SIDES_BUILDING));
	}

	@Test
	void theBuildingThresholdIsStricterAndBothAreStated() {
		assertTrue(Burial.SIDES_BUILDING > Burial.SIDES);
		assertEquals(4, Burial.SIDES_BUILDING, "four horizontal sides is all of them");
	}

	@Test
	void aLiftThatKeepsBeingNeededIsNotAFix() {
		// Rising re-opens the sides, the autopilot flies the body back down to the same station and
		// the same walls close round it again - a one-second cycle that places nothing and that no
		// clock in this mod can see, because the body is moving the whole time.
		assertTrue(Burial.LIFT_LIMIT >= 2, "one bad spot is not a pattern");
		assertTrue(Burial.LIFT_LIMIT <= 5, "...and neither is an evening of them");
		assertTrue(Burial.LIFT_WINDOW_MS > 0, "counted over a window: a design does box you in twice honestly");
	}
}
