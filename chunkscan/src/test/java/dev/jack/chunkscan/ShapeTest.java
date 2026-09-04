package dev.jack.chunkscan;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * The fill shapes. Every one is a predicate over the selection box, which is what lets them reuse
 * the whole pipeline — protection, economy, undo, the printer — without any of it knowing a sphere
 * from a cuboid.
 *
 * <p>Voxel spheres are the classic place to be quietly wrong: off-by-half in the radius gives a ball
 * with its poles shaved flat, and a "hollow" done as a radius band gives a shell that is fat at the
 * poles and thin at the equator.
 */
class ShapeTest {
	private static int count(Fill.Mode m, int sx, int sy, int sz) {
		int n = 0;
		for (int y = 0; y < sy; y++) {
			for (int z = 0; z < sz; z++) {
				for (int x = 0; x < sx; x++) if (m.wants(x, y, z, sx, sy, sz)) n++;
			}
		}
		return n;
	}

	@Test
	void aBallIsRoundNotACubeWithCornersOff() {
		// A 21-cube ball is ~4/3 pi r^3 with r=10.5-ish. If the radius is off by half the poles get
		// shaved and the count drops well below this.
		int n = count(Fill.Mode.BALL, 21, 21, 21);
		double ideal = 4.0 / 3.0 * Math.PI * Math.pow(10.5, 3);
		assertTrue(n > ideal * 0.85 && n < ideal * 1.15, "21-ball is " + n + ", ideal ~" + (int) ideal);
	}

	@Test
	void aBallReachesEveryFaceOfItsBox() {
		// The poles must exist. This is the off-by-half, stated directly.
		int s = 15, c = 7;
		assertTrue(Fill.Mode.BALL.wants(c, 0, c, s, s, s), "no bottom pole");
		assertTrue(Fill.Mode.BALL.wants(c, s - 1, c, s, s, s), "no top pole");
		assertTrue(Fill.Mode.BALL.wants(0, c, c, s, s, s), "no -x pole");
		assertTrue(Fill.Mode.BALL.wants(c, c, s - 1, s, s, s), "no +z pole");
	}

	@Test
	void aBallDoesNotReachItsCorners() {
		int s = 15;
		assertFalse(Fill.Mode.BALL.wants(0, 0, 0, s, s, s), "a ball with corners is a cube");
		assertFalse(Fill.Mode.BALL.wants(s - 1, s - 1, s - 1, s, s, s));
	}

	@Test
	void aSphereIsTheSkinOfABall() {
		int s = 21;
		int ball = count(Fill.Mode.BALL, s, s, s);
		int shell = count(Fill.Mode.SPHERE, s, s, s);
		assertTrue(shell < ball, "the shell cannot be the whole ball");
		assertTrue(shell > ball * 0.15, "shell is " + shell + " of " + ball + " — that is not a skin");
		// and its centre must be hollow
		assertFalse(Fill.Mode.SPHERE.wants(10, 10, 10, s, s, s));
		assertTrue(Fill.Mode.BALL.wants(10, 10, 10, s, s, s));
	}

	@Test
	void theShellIsEvenlyThickNotFatAtThePoles() {
		// The reason the skin is defined as "inside, with a neighbour outside" rather than as a band
		// in the radius equation: the gradient of an ellipsoid is not constant, so a band is uneven.
		int s = 25, c = 12;
		int atPole = 0, atEquator = 0;
		for (int y = 0; y < s; y++) if (Fill.Mode.SPHERE.wants(c, y, c, s, s, s)) atPole++;
		for (int x = 0; x < s; x++) if (Fill.Mode.SPHERE.wants(x, c, c, s, s, s)) atEquator++;
		// two crossings either way, one cell thick each
		assertEquals(2, atPole, "pole crossings");
		assertEquals(2, atEquator, "equator crossings");
	}

	@Test
	void aSquashedBoxGivesAnEllipsoidNotASphere() {
		// The box is the BOUNDING BOX. That is the feature: a dome 30 wide and 8 tall is what a
		// build usually wants, and a fixed radius cannot express it.
		int sx = 31, sy = 9, sz = 31;
		assertTrue(Fill.Mode.BALL.wants(15, 8, 15, sx, sy, sz), "must reach the flattened top");
		assertFalse(Fill.Mode.BALL.wants(0, 8, 0, sx, sy, sz), "and still not the corner");
	}

	@Test
	void aCylinderIsRoundInPlanAndFullHeight() {
		int sx = 15, sy = 7, sz = 15;
		for (int y = 0; y < sy; y++) {
			assertTrue(Fill.Mode.CYLINDER.wants(7, y, 7, sx, sy, sz), "hollow at course " + y);
			assertTrue(Fill.Mode.CYLINDER.wants(0, y, 7, sx, sy, sz), "not round at course " + y);
			assertFalse(Fill.Mode.CYLINDER.wants(0, y, 0, sx, sy, sz), "corner at course " + y);
		}
	}

	@Test
	void aTubeIsOpenAtBothEnds() {
		// A tube with caps is a hollow cylinder. What you reach for `tube` to build is a chimney or
		// a well shaft, and both are open.
		int sx = 15, sy = 7, sz = 15;
		assertFalse(Fill.Mode.TUBE.wants(7, 0, 7, sx, sy, sz), "the bottom is capped");
		assertFalse(Fill.Mode.TUBE.wants(7, sy - 1, 7, sx, sy, sz), "the top is capped");
		assertTrue(Fill.Mode.TUBE.wants(0, 3, 7, sx, sy, sz), "the wall is missing");
		// wall present at every course, same thickness
		for (int y = 0; y < sy; y++) {
			int n = 0;
			for (int x = 0; x < sx; x++) if (Fill.Mode.TUBE.wants(x, y, 7, sx, sy, sz)) n++;
			assertEquals(2, n, "course " + y + " wall crossings");
		}
	}

	@Test
	void aDiscIsFlatEvenInATallBox() {
		int sx = 15, sy = 20, sz = 15;
		assertTrue(Fill.Mode.DISC.wants(7, 0, 7, sx, sy, sz));
		assertFalse(Fill.Mode.DISC.wants(7, 1, 7, sx, sy, sz), "a disc must not become a cylinder");
		assertTrue(Fill.Mode.DISC.isFlat());
		assertFalse(Fill.Mode.CYLINDER.isFlat());
	}

	@Test
	void aRingIsTheOutlineOfADisc() {
		int sx = 15, sy = 1, sz = 15;
		assertTrue(Fill.Mode.DISC.wants(7, 0, 7, sx, sy, sz), "disc centre");
		assertFalse(Fill.Mode.RING.wants(7, 0, 7, sx, sy, sz), "ring centre must be open");
		assertTrue(count(Fill.Mode.RING, sx, sy, sz) < count(Fill.Mode.DISC, sx, sy, sz));
	}

	@Test
	void aDomeIsTheUpperHalfAndSitsOnItsBase() {
		int sx = 21, sy = 11, sz = 21;
		assertTrue(Fill.Mode.DOME.wants(10, 0, 10, sx, sy, sz), "no base");
		assertTrue(Fill.Mode.DOME.wants(0, 0, 10, sx, sy, sz), "base does not reach the rim");
		assertTrue(Fill.Mode.DOME.wants(10, sy - 1, 10, sx, sy, sz), "no crown");
		assertFalse(Fill.Mode.DOME.wants(0, sy - 1, 10, sx, sy, sz), "the rim should have closed in");
	}

	@Test
	void everyShapeFitsInsideItsBox() {
		for (Fill.Mode m : Fill.Mode.values()) {
			assertTrue(count(m, 13, 13, 13) <= 13 * 13 * 13, m + " overflows its box");
			assertTrue(count(m, 13, 13, 13) > 0, m + " is empty");
		}
	}

	@Test
	void everyShapeNameParsesAndUnknownFallsBackToSolid() {
		assertEquals(Fill.Mode.BALL, Fill.Mode.of("ball"));
		assertEquals(Fill.Mode.SPHERE, Fill.Mode.of("SPHERE"));
		assertEquals(Fill.Mode.SPHERE, Fill.Mode.of("orb"));
		// `shell` keeps its original meaning - a hollow BOX. It shipped meaning that.
		assertEquals(Fill.Mode.HOLLOW, Fill.Mode.of("shell"));
		assertEquals(Fill.Mode.CYLINDER, Fill.Mode.of("pillar"));
		assertEquals(Fill.Mode.TUBE, Fill.Mode.of("pipe"));
		assertEquals(Fill.Mode.DISC, Fill.Mode.of("circle"));
		assertEquals(Fill.Mode.RING, Fill.Mode.of("hoop"));
		assertEquals(Fill.Mode.DOME, Fill.Mode.of("mound"));
		assertEquals(Fill.Mode.SOLID, Fill.Mode.of("banana"));
	}

	@Test
	void aOneCellBoxIsOneCellInEveryShape() {
		for (Fill.Mode m : Fill.Mode.values()) {
			assertEquals(1, count(m, 1, 1, 1), m + " on a single cell");
		}
	}
}
