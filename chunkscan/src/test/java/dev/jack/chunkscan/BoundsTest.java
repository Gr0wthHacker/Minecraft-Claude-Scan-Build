package dev.jack.chunkscan;

import net.minecraft.core.BlockPos;
import net.minecraft.world.phys.Vec3;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * The autofly fence: two corners, and the flight stays between them.
 *
 * <p>What is pinned is the property that matters for leaving the loop running - that no step it is
 * handed can carry the body past a face - rather than any particular number. A fence that leaks
 * by one step per tick is a fence that leaks.
 */
class BoundsTest {
	@AfterEach
	void lift() {
		Bounds.clear();
	}

	@Test
	void noFenceMeansEverythingIsInside() {
		assertFalse(Bounds.active());
		assertTrue(Bounds.contains(new BlockPos(1_000_000, -64, -1_000_000)));
		assertTrue(Bounds.holds(new Vec3(5.5, 300, -2)));
		Vec3 step = new Vec3(3, -2, 1);
		assertEquals(step, Bounds.clamp(new Vec3(0, 100, 0), step), "a step with no fence is untouched");
		assertNull(Bounds.corners());
	}

	@Test
	void theCornersMayBeGivenInAnyOrderAndAreInclusive() {
		Bounds.set(new BlockPos(10, 70, -5), new BlockPos(-3, 60, 4), "overworld");
		assertTrue(Bounds.contains(-3, 60, -5), "the low corner is inside");
		assertTrue(Bounds.contains(10, 70, 4), "the high corner is inside");
		assertFalse(Bounds.contains(11, 65, 0));
		assertFalse(Bounds.contains(0, 59, 0));
		assertFalse(Bounds.contains(0, 65, 5));
		assertEquals("overworld", Bounds.dimension());
	}

	@Test
	void aStepThatStaysInsideIsHandedBackUnchanged() {
		Bounds.set(new BlockPos(0, 60, 0), new BlockPos(20, 80, 20), "d");
		Vec3 me = new Vec3(10.5, 70, 10.5);
		Vec3 step = new Vec3(0.5, 0.2, -0.4);
		Vec3 got = Bounds.clamp(me, step);
		assertEquals(0, got.distanceTo(step), 1.0e-9, "changed a legal step: " + got);
	}

	@Test
	void noStepEverCarriesTheBodyPastAFace() {
		// Random walks from the middle, each step aimed anywhere at up to twice cruise speed. If
		// the fence holds, the body is still inside after every one of them.
		Bounds.set(new BlockPos(0, 60, 0), new BlockPos(9, 69, 9), "d");
		java.util.Random r = new java.util.Random(7);
		for (int walk = 0; walk < 50; walk++) {
			Vec3 me = new Vec3(5, 65, 5);
			for (int i = 0; i < 400; i++) {
				Vec3 want = new Vec3(r.nextDouble() * 3 - 1.5, r.nextDouble() * 3 - 1.5, r.nextDouble() * 3 - 1.5);
				me = me.add(Bounds.clamp(me, want));
				assertTrue(Bounds.holds(me), "left the fence at " + me + " on step " + i);
			}
		}
	}

	@Test
	void aStepAcrossOneFaceStillSlidesAlongIt() {
		// Cut at the face, not stopped dead: the other components carry, which is what lets the
		// flight work along the edge of its box rather than pressing on it.
		Bounds.set(new BlockPos(0, 60, 0), new BlockPos(9, 69, 9), "d");
		Vec3 me = new Vec3(9.5, 65, 5);          // right on the +X face's margin
		Vec3 got = Bounds.clamp(me, new Vec3(0.7, 0, 0.7));
		assertTrue(got.x <= 0.2, "did not cross the face: " + got);
		assertEquals(0.7, got.z, 1.0e-9, "the along-face component still carries");
	}

	@Test
	void theTopFaceAllowsForTheBodysHeight() {
		Bounds.set(new BlockPos(0, 60, 0), new BlockPos(9, 69, 9), "d");
		Vec3 me = new Vec3(5, 68.0, 5);
		Vec3 up = Bounds.clamp(me, new Vec3(0, 1.0, 0));
		assertTrue(me.y + up.y + Bounds.HEIGHT <= 70.0 + 1.0e-9, "the head went through the top face");
	}

	@Test
	void aBodyAlreadyOutsideIsPulledBackInAndNotFlungAtIt() {
		Bounds.set(new BlockPos(0, 60, 0), new BlockPos(9, 69, 9), "d");
		Vec3 me = new Vec3(30, 65, 5);           // twenty blocks past the +X face
		Vec3 got = Bounds.clamp(me, Vec3.ZERO);
		assertTrue(got.x < 0, "pulled toward the box");
		assertEquals(Bounds.RETURN_SPEED, got.length(), 1.0e-9, "at the return speed, not in one jump");
		// ...and once inside, it stays inside.
		Vec3 pos = me;
		for (int i = 0; i < 200; i++) pos = pos.add(Bounds.clamp(pos, Vec3.ZERO));
		assertTrue(Bounds.holds(pos), "never got back in: " + pos);
	}

	@Test
	void theRoutePredicateRefusesCellsOutsideAndDefersInside() {
		Bounds.set(new BlockPos(0, 60, 0), new BlockPos(9, 69, 9), "d");
		Nav.Passable open = (x, y, z) -> true;
		Nav.Passable wall = (x, y, z) -> x != 5;
		Nav.Passable fenced = Bounds.within(open);
		assertTrue(fenced.at(4, 62, 4));
		assertFalse(fenced.at(10, 62, 4), "one past the +X face");
		assertFalse(fenced.at(4, 69, 4), "the head cell would be over the top face");
		assertTrue(fenced.at(4, 68, 4), "feet at 68, head at 69: both inside");
		assertFalse(Bounds.within(wall).at(5, 62, 5), "inside the fence but still a wall");
		Bounds.clear();
		assertTrue(Bounds.within(open) == open, "no fence: the predicate is handed back as it was");
	}

	@Test
	void aOneWideLaneLeavesTheBodyItsOwnPlay() {
		// A one-wide corridor is 0.3 of sideways room after the margins. A step that wants more
		// gets exactly that much and no more, and the along-lane component still carries.
		Bounds.set(new BlockPos(3, 60, 0), new BlockPos(3, 69, 9), "d");
		Vec3 me = new Vec3(3.5, 65, 5);
		Vec3 got = Bounds.clamp(me, new Vec3(0.6, 0, 0.3));
		assertEquals(0.15, got.x, 1.0e-9, "to the margin and no further");
		assertEquals(0.3, got.z, 1.0e-9);
		assertTrue(Bounds.holds(me.add(got)));
	}

	@Test
	void aBoxShorterThanTheBodyHasOneLegalHeightAndDoesNotOscillate() {
		// One course tall: there is no feet height at which the head is under the top face, so
		// the fence settles on the middle rather than pushing the body up and down every tick.
		Bounds.set(new BlockPos(0, 65, 0), new BlockPos(9, 65, 9), "d");
		Vec3 a = new Vec3(5, 65.3, 5);
		for (int i = 0; i < 10; i++) a = a.add(Bounds.clamp(a, new Vec3(0, i % 2 == 0 ? 0.5 : -0.5, 0)));
		Vec3 c = a.add(Bounds.clamp(a, new Vec3(0, 0.5, 0)));
		Vec3 d = c.add(Bounds.clamp(c, new Vec3(0, -0.5, 0)));
		assertEquals(a.y, c.y, 1.0e-9, "settled, a push up still moved it");
		assertEquals(a.y, d.y, 1.0e-9, "settled, a push down still moved it");
		assertEquals(0.4, Bounds.clamp(a, new Vec3(0.4, 0, 0)).x, 1.0e-9, "the horizontal still carries");
	}

	@Test
	void clearingTheFenceForgetsIt() {
		Bounds.set(new BlockPos(0, 60, 0), new BlockPos(9, 69, 9), "d");
		assertTrue(Bounds.active());
		Bounds.clear();
		assertFalse(Bounds.active());
		assertTrue(Bounds.contains(100, 100, 100));
		assertEquals("", Bounds.dimension());
	}
}
