package dev.jack.chunkscan;

import net.minecraft.core.BlockPos;
import org.junit.jupiter.api.Test;

import java.util.HashSet;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * The bot digging itself into a hole.
 *
 * <p>Jack: <i>"its multiple times now sat still and dug completely around itself. If it starts to
 * have sides of itself covered, e.g. 2/3 sides of body, it should move up."</i> Every watchdog in
 * this mod asks whether the loop is TRAVELLING and failing, and a bot standing where it means to
 * stand, breaking the cells its list names, passes all of them. The fault is in the geometry, so
 * these are about geometry — no client anywhere in them.
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

	@Test
	void openGroundIsNotWalledAtAll() {
		assertEquals(0, Burial.walled(world(cells()), BlockPos.ZERO));
		assertFalse(Burial.boxedIn(world(cells()), BlockPos.ZERO));
	}

	@Test
	void aPitIsWalledOnEverySide() {
		assertEquals(4, Burial.walled(world(pit()), BlockPos.ZERO));
		assertTrue(Burial.boxedIn(world(pit()), BlockPos.ZERO));
	}

	@Test
	void aBlockAtTheFEETALONEisAStepAndNotAWall() {
		// The rule that stops the loop rising off every kerb in the park: a side counts only when
		// BOTH body cells are blocked.
		assertEquals(0, Burial.walled(world(cells("1,0,0")), BlockPos.ZERO));
	}

	@Test
	void aBlockAtTheHEADALONEisAnOverhangAndNotAWall() {
		assertEquals(0, Burial.walled(world(cells("1,1,0")), BlockPos.ZERO));
	}

	@Test
	void twoSidesIsJacksThreshold() {
		Set<String> s = cells("1,0,0", "1,1,0", "-1,0,0", "-1,1,0");
		assertEquals(Burial.SIDES, Burial.walled(world(s), BlockPos.ZERO));
		assertTrue(Burial.boxedIn(world(s), BlockPos.ZERO));
	}

	@Test
	void aROOFEDplaceIsNotAPitHoweverWalledItIs() {
		// UNDERGROUND IS WHERE THE LOOP IS SUPPOSED TO BE. A mine gallery, the undercroft, a tunnel:
		// walled by design and roofed, so rising is grinding a ceiling — which this mod has done.
		Set<String> s = pit();
		s.add("0,2,0");
		assertEquals(4, Burial.walled(world(s), BlockPos.ZERO));
		assertFalse(Burial.boxedIn(world(s), BlockPos.ZERO),
			"a roofed room is somewhere to work, not somewhere to climb out of");
	}

	@Test
	void aDoorwayIsTwoSidesAndMustNotFireInstantly() {
		// Two walled sides is a doorway, a corridor and a trench as much as it is a grave. The
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
}
