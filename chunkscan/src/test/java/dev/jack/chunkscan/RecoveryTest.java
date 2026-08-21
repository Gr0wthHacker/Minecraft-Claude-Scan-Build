package dev.jack.chunkscan;

import net.minecraft.core.BlockPos;
import org.junit.jupiter.api.Test;

import java.util.HashSet;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * The last resort, when every specific answer has had its turn.
 *
 * <p>Every stuck loop so far was fixed by understanding one situation — the shaft, the ceiling, the
 * unloaded chunk, the wall the route thought was clear. That has a floor under it: there will always
 * be a situation nobody thought of, and a design cell in the middle of a solid mass cannot be reached
 * by any amount of cleverness about flying.
 */
class RecoveryTest {
	@Test
	void ordinaryTroubleIsNotAnEmergency() {
		// Bumping and re-routing are normal. A ladder that fires on the first contact would take
		// over the flight constantly and never let the specific handlers work.
		assertEquals(Recovery.Stage.NONE, Recovery.stageFor(0, false));
		assertEquals(Recovery.Stage.NONE, Recovery.stageFor(Recovery.BACK_OFF_AT - 1, false));
	}

	@Test
	void itClimbsTheLadderInOrder() {
		assertEquals(Recovery.Stage.BACK_OFF, Recovery.stageFor(Recovery.BACK_OFF_AT, false));
		assertEquals(Recovery.Stage.CLIMB_OUT, Recovery.stageFor(Recovery.CLIMB_OUT_AT, false));
		assertEquals(Recovery.Stage.GO_HOME, Recovery.stageFor(Recovery.GO_HOME_AT, false));
		assertEquals(Recovery.Stage.GO_HOME, Recovery.stageFor(Recovery.GO_HOME_AT * 10, false));
	}

	@Test
	void theRungsAreInTheRightOrderAndFarEnoughApart() {
		assertTrue(Recovery.BACK_OFF_AT < Recovery.CLIMB_OUT_AT);
		assertTrue(Recovery.CLIMB_OUT_AT < Recovery.GO_HOME_AT);
		// Each rung has to be given long enough to work before the next one interrupts it: backing
		// off and climbing out are both several seconds of flying.
		assertTrue(Recovery.CLIMB_OUT_AT - Recovery.BACK_OFF_AT >= 60);
		assertTrue(Recovery.GO_HOME_AT - Recovery.CLIMB_OUT_AT >= 60);
	}

	@Test
	void beingSHUTINSkipsStraightToTheTop() {
		// Jack's case: built into the middle of something. Backing off, climbing and going round are
		// all about getting somewhere else in this world, and there is nowhere else to get to. Every
		// rung below the top is a waste of the next ten minutes.
		assertEquals(Recovery.Stage.GO_HOME, Recovery.stageFor(Recovery.BACK_OFF_AT, true));
		// ...but not before the ladder starts at all: one tick of contact inside a small room is
		// still just a bump.
		assertEquals(Recovery.Stage.NONE, Recovery.stageFor(1, true));
	}

	@Test
	void movingIsAlwaysFine() {
		// The one honest signal, and the one that cannot be argued with: a flight covering ground is
		// fine whatever else is true of it.
		assertFalse(Recovery.inTrouble(true, true, false), "a moving flight is in trouble");
		assertFalse(Recovery.inTrouble(false, false, false), "nowhere to be is not trouble");
		assertFalse(Recovery.inTrouble(false, true, true), "arrived and holding still is the job");
		assertTrue(Recovery.inTrouble(false, true, false));
	}

	// ---------------------------------------------------------------- sealed in

	@Test
	void aClosedPocketIsToldApartFromOpenWorld() {
		// The measurement the shortcut rests on. Without it, "no route" reads the same whether there
		// is a door round the corner or six layers of stone.
		//
		// The fixture matters: written first as a 5x5x5 room, which has a hundred passable cells and
		// is correctly NOT sealed — see the next test. Jack's case is being built INTO something,
		// which is a hole you fit in, not a room you are shut in.
		Set<Long> solid = new HashSet<>();
		for (int x = -4; x <= 4; x++) {
			for (int y = 96; y <= 104; y++) {
				for (int z = -4; z <= 4; z++) solid.add(BlockPos.asLong(x, y, z));
			}
		}
		solid.remove(BlockPos.asLong(0, 100, 0));          // a body-sized hole in the middle
		solid.remove(BlockPos.asLong(0, 101, 0));
		Nav.Passable free = free(solid);

		assertTrue(free.at(0, 100, 0), "control: the hole holds a body");
		assertTrue(Nav.pocket(free, new BlockPos(0, 100, 0), Recovery.SEALED_CELLS)
			< Recovery.SEALED_CELLS, "being walled into a two-cell hole read as open world");
		assertEquals(Recovery.SEALED_CELLS,
			Nav.pocket(free, new BlockPos(40, 100, 40), Recovery.SEALED_CELLS),
			"open sky was called a pocket");
	}

	@Test
	void aROOMIsNotAPocket() {
		// The boundary that matters as much as the detection: the loop WORKS indoors — the store
		// hall is nine by nine — and a recovery that teleports you home every time you fly into a
		// building would be worse than no recovery at all.
		Set<Long> solid = new HashSet<>();
		for (int x = -5; x <= 5; x++) {
			for (int y = 97; y <= 103; y++) {
				for (int z = -5; z <= 5; z++) {
					boolean shell = Math.abs(x) == 5 || y == 97 || y == 103 || Math.abs(z) == 5;
					if (shell) solid.add(BlockPos.asLong(x, y, z));
				}
			}
		}
		assertEquals(Recovery.SEALED_CELLS,
			Nav.pocket(free(solid), new BlockPos(0, 100, 0), Recovery.SEALED_CELLS),
			"a room you can work in was called a pocket you are stuck in");
	}

	private static Nav.Passable free(Set<Long> solid) {
		return (x, y, z) -> !solid.contains(BlockPos.asLong(x, y, z))
			&& !solid.contains(BlockPos.asLong(x, y + 1, z));
	}

	@Test
	void thePocketCountStopsAtTheCap() {
		// Or "am I sealed in" floods the sky every time it is asked.
		Nav.Passable open = (x, y, z) -> true;
		assertEquals(200, Nav.pocket(open, BlockPos.ZERO, 200));
	}

	// ---------------------------------------------------------------- thrashing

	@Test
	void givingUpOnSpotsWhileBuildingNothingIsALoop() {
		// The slow version, which no single watchdog catches: abandon A, take B, abandon B, take A
		// again when its minute expires, for ever. Every decision correct, the sequence a machine
		// going nowhere.
		assertTrue(Loop.thrashing(4, 0, 4));
		assertFalse(Loop.thrashing(4, 12, 4), "it is placing blocks between spots, so it is working");
		assertFalse(Loop.thrashing(1, 0, 4), "one awkward spot is not a pattern");
	}
}
