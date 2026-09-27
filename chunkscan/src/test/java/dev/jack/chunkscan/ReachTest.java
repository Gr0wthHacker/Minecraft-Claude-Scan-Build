package dev.jack.chunkscan;

import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * WHAT "IN REACH" MEANS, in the one place it is decided.
 *
 * <p>Jack: <i>"constantly the bot when trying to place is 1 or 2 blocks out of reach and cant place
 * and just sits there"</i>. Three separate parts of the loop had invented a reach of their own and
 * every one measured to the cell's CENTRE - the vicinity hold from the FEET, the stand chooser and
 * the orbit from the eyes. The printer clicks the SUPPORT's face, which is somewhere else, so all
 * three said IN REACH about cells {@link Printer#placement} then refused: five seconds of holding,
 * a move "closer" to another such spot, a tour of every angle, and a stall.
 *
 * <p>These pin the arithmetic rather than the behaviour, because the arithmetic is the whole of it -
 * and because the numbers below are the ones that decided the fix.
 */
class ReachTest {

	/** A full cube at the support's position. */
	private static final AABB CUBE = new AABB(0, 0, 0, 1, 1, 1);

	/** Where a click aimed at {@code cell} through {@code face} lands, given a full-cube support. */
	private static Vec3 clickOn(BlockPos cell, Direction face) {
		BlockPos nb = cell.relative(face.getOpposite());
		return Printer.clickPoint(nb, CUBE, face, Printer.hit(cell, face, false));
	}

	@Test
	void theEyeIsOverTheFeetAndThatIsMostOfTheGap() {
		Vec3 eye = Printer.eyeOver(new BlockPos(0, 0, 0));
		assertEquals(0.5, eye.x, 1e-9);
		assertEquals(0.5, eye.z, 1e-9);
		assertEquals(Plan.EYE, eye.y, 1e-9);
	}

	/**
	 * THE MEASUREMENT THAT PRODUCED THE FIX.
	 *
	 * <p>{@link Loop#VICINITY} is a sphere of 4 on the FEET and the printer's arm is
	 * {@link Printer#REACH} from the EYES, so a cell straight down is a block and a half further off
	 * than the hold believed. Four courses down is inside the sphere, has a perfectly good support,
	 * and cannot be touched - and the hold announced it as "placeable from right here", held five
	 * seconds, and placed nothing.
	 */
	@Test
	void aCellFourCoursesBELOWtheFeetIsInsideVICINITYandOutOfREACH() {
		BlockPos feet = new BlockPos(0, 100, 0);
		BlockPos cell = new BlockPos(0, 96, 0);                 // dy = -4: inside the sphere
		assertTrue(cell.distSqr(feet) <= (double) Loop.VICINITY * Loop.VICINITY,
			"the hold's own focus() includes this cell");

		Vec3 eye = Printer.eyeOver(feet);
		double best = Double.MAX_VALUE;
		for (Direction f : Direction.values()) best = Math.min(best, eye.distanceTo(clickOn(cell, f)));
		assertTrue(best > Printer.REACH,
			"no face of this cell is inside the arm; the nearest click is " + best);
		assertFalse(Printer.withinReach(eye, cell, List.of(clickOn(cell, Direction.UP))));
	}

	/**
	 * ...AND A FLOOR LEAVES THE ARM SOONER THAN THAT, which is the commonest case of all.
	 *
	 * <p>A floor course is supported from BELOW, so the click lands on the cell's own BOTTOM face -
	 * a whole block further from the eye than its top. Three courses down is already out of reach
	 * and {@link Loop#VICINITY} includes it out to four, so a body hovering over paving it has come
	 * to lay is exactly the shape of "sitting there": the cells are real, carried, supported, and a
	 * metre past the fingertips.
	 */
	@Test
	void aFLOORleavesTheArmAtThreeCoursesDownAndVICINITYreachesFour() {
		Vec3 eye = Printer.eyeOver(new BlockPos(0, 100, 0));
		BlockPos two = new BlockPos(0, 98, 0), three = new BlockPos(0, 97, 0);
		assertTrue(Printer.withinReach(eye, two, List.of(clickOn(two, Direction.UP))),
			"two courses down is still inside the arm");
		assertFalse(Printer.withinReach(eye, three, List.of(clickOn(three, Direction.UP))),
			"three is not - and VICINITY reaches four");
		assertTrue(three.distSqr(new BlockPos(0, 100, 0)) <= (double) Loop.VICINITY * Loop.VICINITY);
	}

	/**
	 * A CLICK LANDS ON THE SUPPORT, NOT ON THE CELL. With the support on the far side the click is
	 * half a block further out than the centre every other measure was using - which is the "1 or 2
	 * blocks" in the report, arriving one half-block at a time.
	 */
	@Test
	void theClickIsFURTHERthanTheCentreWhenTheSupportIsOnTheFarSide() {
		Vec3 eye = Printer.eyeOver(new BlockPos(0, 100, 0));
		BlockPos cell = new BlockPos(4, 100, 0);
		double centre = eye.distanceTo(Vec3.atCenterOf(cell));
		double far = eye.distanceTo(clickOn(cell, Direction.WEST));   // support beyond it, at x=5
		double near = eye.distanceTo(clickOn(cell, Direction.EAST));  // support at x=3
		// Not exactly half a block either way: the aim sits in the lower quarter of the face, which
		// is what decides a slab's `type` and a stair's `half`. What matters is the ORDER.
		assertTrue(near < centre && centre < far,
			"near " + near + " < centre " + centre + " < far " + far);
		assertTrue(near < Printer.REACH && far > Printer.REACH,
			"and this cell straddles the arm: reachable from one side and not from the other - so"
				+ " the centre alone cannot answer the question");
	}

	/**
	 * THE CLAMP IS THE SUPPORT'S REAL SHAPE. A bottom slab's top face is at y+0.5, not y+1, so a
	 * cell resting on one is clicked half a block lower than a full cube would be clicked.
	 */
	@Test
	void theClickFollowsTheSupportsOwnSHAPEnotItsCell() {
		BlockPos cell = new BlockPos(0, 100, 0), nb = cell.below();
		Vec3 aim = Printer.hit(cell, Direction.UP, false);
		assertEquals(nb.getY() + 0.5,
			Printer.clickPoint(nb, new AABB(0, 0, 0, 1, 0.5, 1), Direction.UP, aim).y, 1e-9);
		assertEquals(nb.getY() + 1.0, Printer.clickPoint(nb, CUBE, Direction.UP, aim).y, 1e-9);
	}

	/**
	 * THE CHEAP BOUND IS SOUND. The printer's scan rejects a cell whose CENTRE is beyond
	 * {@code REACH + 1} before asking the real question, and that is only safe because no point on a
	 * cell's surface is more than a half-diagonal (0.867) from its centre. Swept rather than argued.
	 */
	@Test
	void theCentreBoundNeverThrowsAwayAReachableClick() {
		Vec3 eye = Printer.eyeOver(new BlockPos(0, 100, 0));
		double bound = Printer.REACH + 1.0;
		for (int dx = -9; dx <= 9; dx++) {
			for (int dy = -9; dy <= 9; dy++) {
				for (int dz = -9; dz <= 9; dz++) {
					BlockPos cell = new BlockPos(dx, 100 + dy, dz);
					if (eye.distanceTo(Vec3.atCenterOf(cell)) <= bound) continue;   // the bound keeps it
					for (Direction f : Direction.values()) {
						assertTrue(eye.distanceTo(clickOn(cell, f)) > Printer.REACH,
							"the cheap bound discarded a click that was in reach at " + cell);
					}
				}
			}
		}
	}

	/**
	 * A STAND THAT CANNOT TOUCH A CELL DOES NOT COVER IT.
	 *
	 * <p>{@link Plan#coveredFrom} is what picks where to stand, where to land and which angle to
	 * orbit to, and it counted a cell as covered on eye-to-centre distance alone. That is the
	 * difference between "moving in closer" arriving somewhere that works and touring vantages that
	 * all place nothing.
	 */
	@Test
	void coveredFromAsksWhetherThePrinterCanTOUCHtheCell() {
		BlockPos stand = new BlockPos(0, 100, 0);
		List<Work.Cell> cells = List.of(new Work.Cell(new BlockPos(3, 100, 0), "stone_bricks"));

		assertEquals(1, Plan.coveredFrom(cells, stand, Printer.REACH, null),
			"near enough by the old measure");
		assertEquals(0, Plan.coveredFrom(cells, stand, Printer.REACH, null, (at, cell) -> false),
			"...and refused when the printer says it cannot touch it");
		assertEquals(1, Plan.coveredFrom(cells, stand, Printer.REACH, null, (at, cell) -> true),
			"...and kept when it says it can");
	}

	/** A null predicate is the old measure exactly, so no other caller moved. */
	@Test
	void noPredicateMeansTheOldMeasure() {
		BlockPos stand = new BlockPos(0, 100, 0);
		List<Work.Cell> cells = List.of(new Work.Cell(new BlockPos(3, 100, 0), "stone_bricks"),
			new Work.Cell(new BlockPos(30, 100, 0), "stone_bricks"));
		assertEquals(Plan.coveredFrom(cells, stand, Printer.REACH, null),
			Plan.coveredFrom(cells, stand, Printer.REACH, null, null));
	}

	/**
	 * THE PREDICATE IS CONSULTED PER (STAND, CELL), which is why the CALLER memoises the click
	 * points: they do not depend on where you stand, and a stand search looks at several hundred
	 * positions. Asked afresh each time this would be the per-node cost this repo has paid for
	 * twice already.
	 */
	@Test
	void theCoverageQuestionIsAskedPerPairSoTheCallerMustMemoise() {
		List<Work.Cell> cells = new ArrayList<>();
		for (int i = 0; i < 8; i++) cells.add(new Work.Cell(new BlockPos(i % 3, 100, i % 2), "stone"));
		int[] asked = {0};
		Plan.Reach counting = (at, cell) -> { asked[0]++; return true; };
		Plan.coveredFrom(cells, new BlockPos(0, 100, 0), Printer.REACH, null, counting);
		assertTrue(asked[0] > 0, "the predicate is consulted at all");
		int once = asked[0];
		Plan.coveredFrom(cells, new BlockPos(1, 100, 0), Printer.REACH, null, counting);
		assertTrue(asked[0] > once, "...and again for the next candidate position");
	}
}
