package dev.jack.chunkscan;

import net.minecraft.core.BlockPos;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Landing to work, and taking off again. Jack: <i>"it is hovering above a group thats not
 * placeable; i think we need to also analyze area and identify when it can land and it should
 * take off by itself"</i>. A flying stand needs three clear cells under it, so work ON a floor
 * had no stand at all and the flight parked three blocks over the centroid, out of reach.
 */
class LandingTest {
	private static final class W {
		final Set<Long> solid = new HashSet<>();
		void floor(int x0, int z0, int x1, int z1, int y) {
			for (int x = x0; x <= x1; x++) for (int z = z0; z <= z1; z++) solid.add(BlockPos.asLong(x, y, z));
		}
		Nav.Passable free() {
			return (x, y, z) -> !solid.contains(BlockPos.asLong(x, y, z))
				&& !solid.contains(BlockPos.asLong(x, y + 1, z));
		}
		java.util.function.Predicate<BlockPos> isSolid() {
			return b -> solid.contains(b.asLong());
		}
	}

	private static Work.Cell cell(int x, int y, int z) {
		return new Work.Cell(new BlockPos(x, y, z), "stone_bricks");
	}

	@Test
	void pavingOnAPlateHasNoFlyingStandAndAGroundOne() {
		// A 30x30 plate at y=99, and a row of paving to lay on top of it at y=100.
		W w = new W();
		w.floor(-15, -15, 15, 15, 99);
		List<Work.Cell> row = new ArrayList<>();
		for (int x = 0; x < 6; x++) row.add(cell(x, 100, 0));
		BlockPos me = new BlockPos(-8, 100, -8);
		BlockPos hover = Plan.bestStand(w.free(), row, 4.2, me, 4, Autopilot.ARRIVE_MIN);
		assertTrue(hover == null || Plan.coveredFrom(row, hover, 4.2 - Autopilot.ARRIVE_MIN) == 0,
			"control: a hovering stand over a plate reaches none of the paving from its eyes");
		BlockPos land = Plan.groundStand(w.free(), w.isSolid(), row, 4.2 - 0.4, me, 5);
		assertNotNull(land, "nowhere to land beside a row of paving on a plate");
		assertEquals(100, land.getY(), "a landing stands ON the plate");
		assertFalse(row.stream().anyMatch(c -> c.pos().equals(land)), "landed in the work itself");
		assertTrue(Plan.coveredFrom(row, land, 4.2 - 0.4) >= 4, "a landing that reaches almost nothing");
	}

	@Test
	void aLedgeOverTheVoidIsNotAFloor() {
		// One block wide: standing on it is one drift from the void, and landing is how flight ends.
		W w = new W();
		w.floor(0, 0, 8, 0, 99);
		List<Work.Cell> row = List.of(cell(4, 100, 1), cell(5, 100, 1));
		assertNull(Plan.groundStand(w.free(), w.isSolid(), row, 3.8, new BlockPos(0, 100, 0), 5));
	}

	@Test
	void theStandIsTheEyesReachNotTheFeet() {
		// From the feet cell a block two courses down and four along is out of reach; from the eyes
		// it is not — and it is the eyes the printer's ray leaves from.
		assertEquals(1, Plan.coveredFrom(List.of(cell(3, 99, 0)), new BlockPos(0, 100, 0), 4.2));
		assertEquals(0, Plan.coveredFrom(List.of(cell(4, 98, 0)), new BlockPos(0, 100, 0), 4.2),
			"two courses down and four along is 5.1 from the eyes, whatever it is from the feet");
	}

	@Test
	void aLandingIsWalkedToWhenItIsNearAndFlownToWhenItIsNot() {
		assertFalse(Autopilot.needsFlight(true, false, 6.0), "took off for the next patch of paving");
		assertTrue(Autopilot.needsFlight(true, true, 6.0), "no walking route: the air is the only way");
		assertTrue(Autopilot.needsFlight(true, false, Autopilot.WALK_AT_MOST + 1), "a long walk is a flight");
		assertTrue(Autopilot.needsFlight(false, false, 1.0), "a hovering station always needs the air");
	}

	@Test
	void aLandingKeepsTheCeilingUnderTheReach() {
		// The slack a landing gives up is smaller than the slack a hover gives up, so on a tie the
		// ground wins the comparison in Hud.standAt — by design, not by accident.
		assertTrue(Hud.LAND_SLACK < Autopilot.ARRIVE_MIN);
		assertTrue(Plan.PAD_MIN >= 5, "a landing needs most of a 3x3 under it");
	}
}
