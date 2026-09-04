package dev.jack.chunkscan;

import net.minecraft.SharedConstants;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.server.Bootstrap;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.SlabBlock;
import net.minecraft.world.level.block.StairBlock;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.Half;
import net.minecraft.world.level.block.state.properties.SlabType;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * The spiral staircase shapes. A spiral is the first fill shape whose cells are NOT
 * interchangeable - a stair tread faces the ascent and a slab tread is a half-step - so what is
 * worth testing is not the count of cells but whether a player can actually climb the thing:
 * every course has a tread, consecutive treads touch, stairs lean the right way, and a slab flight
 * rises half a block at a time from the bottom to the top. Our renderer draws a backwards stair
 * and a forwards one identically, so none of this can be eyeballed.
 */
class SpiralTest {
	@BeforeAll
	static void boot() {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
	}

	// NOT static fields: a block state read at class-load time initialises the registries before
	// @BeforeAll has bootstrapped them, and that poisons every test class that runs after this one
	// in the same JVM with "Not bootstrapped". Forty-one failures across ten files, from three lines.
	private static BlockState brick() { return Blocks.STONE_BRICKS.defaultBlockState(); }
	private static BlockState stair() { return Blocks.STONE_BRICK_STAIRS.defaultBlockState(); }
	private static BlockState slab() { return Blocks.STONE_BRICK_SLAB.defaultBlockState(); }

	private static Fill.Probe empty() {
		return (x, y, z) -> Blocks.AIR.defaultBlockState();
	}

	/** Every tread cell of a course, as (x, z). */
	private static List<int[]> tread(Fill.Mode m, BlockState mat, int y, int sx, int sy, int sz) {
		Fill.Mode.Helix h = Fill.Mode.Helix.of(m, sx, sz, mat.getBlock() instanceof SlabBlock);
		List<int[]> out = new ArrayList<>();
		for (int z = 0; z < sz; z++) {
			for (int x = 0; x < sx; x++) {
				if (h.inPost(x, z)) continue;
				if (m.state(mat, x, y, z, sx, sy, sz) != null) out.add(new int[]{x, z});
			}
		}
		return out;
	}

	@Test
	void everyCourseHasATreadAndTheyTouch() {
		for (int s : new int[]{3, 4, 5, 6, 7, 9, 12, 15}) {
			int sy = 20;
			for (Fill.Mode m : new Fill.Mode[]{Fill.Mode.SPIRAL, Fill.Mode.HELIX_CCW}) {
				List<int[]> prev = null;
				for (int y = 0; y < sy; y++) {
					List<int[]> now = tread(m, brick(), y, s, sy, s);
					assertFalse(now.isEmpty(), m + " " + s + "-box has no tread at course " + y);
					if (prev != null) {
						boolean touch = false;
						for (int[] a : prev) for (int[] b : now)
							if (Math.abs(a[0] - b[0]) <= 1 && Math.abs(a[1] - b[1]) <= 1) touch = true;
						assertTrue(touch, m + " " + s + "-box: courses " + (y - 1) + " and " + y + " do not touch");
					}
					prev = now;
				}
			}
		}
	}

	@Test
	void theRingIsCoveredExactlyOnceATurnAndThePostEveryCourse() {
		// A 5x5 round a 1x1 post is the classic eight-step spiral. Over eight courses every cell of
		// the ring appears exactly once - no gap where a sector was thinner than a cell, no cell
		// claimed by two treads - and the post is there on every course.
		int s = 5, sy = 8;
		Fill.Mode.Helix h = Fill.Mode.Helix.of(Fill.Mode.SPIRAL, s, s, false);
		assertEquals(8, h.perTurn);
		for (int z = 0; z < s; z++) {
			for (int x = 0; x < s; x++) {
				int n = 0;
				for (int y = 0; y < sy; y++) if (Fill.Mode.SPIRAL.wants(x, y, z, s, sy, s)) n++;
				if (h.inPost(x, z)) assertEquals(sy, n, "post at " + x + "," + z);
				else if (h.inRing(x, z)) assertEquals(1, n, "ring cell " + x + "," + z + " appears " + n + " times a turn");
				else assertEquals(0, n, "corner " + x + "," + z + " is outside the disc");
			}
		}
		assertTrue(h.inPost(2, 2), "the centre is the post");
		assertFalse(h.inPost(1, 2), "a 5-box post is one cell");
	}

	@Test
	void aHelixLeavesTheCoreOpen() {
		int s = 7, sy = 6;
		for (int y = 0; y < sy; y++) {
			assertTrue(Fill.Mode.SPIRAL.wants(3, y, 3, s, sy, s), "spiral post at course " + y);
			assertFalse(Fill.Mode.HELIX.wants(3, y, 3, s, sy, s), "helix core must be air at course " + y);
		}
	}

	@Test
	void anEvenBoxStillGetsAPost() {
		// The box's centre falls between cells, so no cell is at distance zero - a naive post test
		// would give an even box no post at all.
		Fill.Mode.Helix h = Fill.Mode.Helix.of(Fill.Mode.SPIRAL, 6, 6, false);
		int post = 0;
		for (int z = 0; z < 6; z++) for (int x = 0; x < 6; x++) if (h.inPost(x, z)) post++;
		assertEquals(4, post, "a 6-box has a 2x2 post");
	}

	@Test
	void clockwiseAndCounterAreMirrorImages() {
		// Mirroring across the z axis negates the angle, which is exactly what reversing the spin
		// does - so the two must agree cell for cell, or one of them is not the other's twin.
		int s = 9, sy = 14;
		for (int y = 0; y < sy; y++) for (int z = 0; z < s; z++) for (int x = 0; x < s; x++) {
			assertEquals(Fill.Mode.SPIRAL.wants(x, y, s - 1 - z, s, sy, s),
				Fill.Mode.SPIRAL_CCW.wants(x, y, z, s, sy, s), "at " + x + "," + y + "," + z);
		}
	}

	@Test
	void stairsFaceTheWayTheFlightAscends() {
		// THE STAIR CONVENTION: a flight that ascends toward D has every tread facing=D. Clockwise
		// seen from above with north up, the tread due EAST of the post is climbed heading SOUTH,
		// and the tread due NORTH of it heading EAST. Counter-clockwise is the reverse.
		int s = 9, sy = 30;
		assertFacing(Fill.Mode.SPIRAL, 8, 4, s, sy, Direction.SOUTH);
		assertFacing(Fill.Mode.SPIRAL, 4, 0, s, sy, Direction.EAST);
		assertFacing(Fill.Mode.SPIRAL, 0, 4, s, sy, Direction.NORTH);
		assertFacing(Fill.Mode.SPIRAL, 4, 8, s, sy, Direction.WEST);
		assertFacing(Fill.Mode.SPIRAL_CCW, 8, 4, s, sy, Direction.NORTH);
		assertFacing(Fill.Mode.SPIRAL_CCW, 4, 0, s, sy, Direction.WEST);
	}

	private static void assertFacing(Fill.Mode m, int x, int z, int s, int sy, Direction want) {
		BlockState got = null;
		for (int y = 0; y < sy && got == null; y++) got = m.state(stair(), x, y, z, s, sy, s);
		assertNotNull(got, "no tread ever lands on " + x + "," + z);
		assertEquals(want, got.getValue(StairBlock.FACING), m + " tread at " + x + "," + z);
		assertEquals(Half.BOTTOM, got.getValue(StairBlock.HALF));
	}

	@Test
	void thePostIsNeverTurnedIntoAStair() {
		int s = 5, sy = 4;
		for (int y = 0; y < sy; y++) {
			assertEquals(stair(), Fill.Mode.SPIRAL.state(stair(), 2, y, 2, s, sy, s),
				"the post takes the material exactly as held");
		}
		assertNull(Fill.Mode.SPIRAL.state(stair(), 0, 0, 0, s, sy, s), "the corner is outside the disc");
	}

	/**
	 * Walk the flight from its lowest tread: an 8-neighbour step is allowed when it rises by no
	 * more than {@code rise}. Returns the highest course reached.
	 */
	private static int climb(Fill.Mode m, BlockState mat, int s, int sy, double rise) {
		Map<Long, Double> top = new HashMap<>();          // walkable surface height per cell
		Fill.Mode.Helix h = Fill.Mode.Helix.of(m, s, s, mat.getBlock() instanceof SlabBlock);
		for (int y = 0; y < sy; y++) for (int z = 0; z < s; z++) for (int x = 0; x < s; x++) {
			if (h.inPost(x, z)) continue;
			BlockState st = m.state(mat, x, y, z, s, sy, s);
			if (st == null) continue;
			double height = y + 1.0;
			if (st.getBlock() instanceof SlabBlock && st.getValue(SlabBlock.TYPE) == SlabType.BOTTOM) height = y + 0.5;
			top.put(BlockPos.asLong(x, y, z), height);
		}
		// start on every tread of the bottom course
		ArrayDeque<long[]> q = new ArrayDeque<>();
		Set<Long> seen = new HashSet<>();
		for (int z = 0; z < s; z++) for (int x = 0; x < s; x++) {
			long k = BlockPos.asLong(x, 0, z);
			if (top.containsKey(k)) { q.add(new long[]{x, 0, z}); seen.add(k); }
		}
		int best = 0;
		while (!q.isEmpty()) {
			long[] c = q.poll();
			double here = top.get(BlockPos.asLong((int) c[0], (int) c[1], (int) c[2]));
			best = Math.max(best, (int) c[1]);
			for (int dz = -1; dz <= 1; dz++) for (int dx = -1; dx <= 1; dx++) {
				if (dx == 0 && dz == 0) continue;
				int nx = (int) c[0] + dx, nz = (int) c[2] + dz;
				for (int ny = (int) c[1] - 1; ny <= (int) c[1] + 1; ny++) {
					long k = BlockPos.asLong(nx, ny, nz);
					Double there = top.get(k);
					if (there == null || seen.contains(k)) continue;
					if (there - here > rise + 1e-9) continue;
					seen.add(k);
					q.add(new long[]{nx, ny, nz});
				}
			}
		}
		return best;
	}

	@Test
	void aBlockFlightClimbsOneCourseAtATimeToTheTop() {
		for (int s : new int[]{3, 5, 7, 9, 13}) {
			int sy = 24;
			assertEquals(sy - 1, climb(Fill.Mode.SPIRAL, brick(), s, sy, 1.0), s + "-box block spiral");
			assertEquals(sy - 1, climb(Fill.Mode.HELIX, stair(), s, sy, 1.0), s + "-box stair helix");
		}
	}

	@Test
	void aSlabFlightIsWalkedWithoutAJump() {
		// The whole point of a slab spiral: every step is half a block, so it walks. A single
		// course whose sector landed no top slab at the rim is a full-block rise, which is a jump,
		// which is the thing this material was chosen to avoid.
		for (int s : new int[]{3, 5, 7, 9, 11, 15}) {
			int sy = 24;
			assertEquals(sy - 1, climb(Fill.Mode.SPIRAL, slab(), s, sy, 0.5), s + "-box slab spiral");
			assertEquals(sy - 1, climb(Fill.Mode.HELIX_CCW, slab(), s, sy, 0.5), s + "-box slab helix ccw");
		}
	}

	@Test
	void aSlabTreadIsTwoHalfStepsInAscentOrder() {
		int s = 7, sy = 12;
		Fill.Mode.Helix h = Fill.Mode.Helix.of(Fill.Mode.SPIRAL, s, s, true);
		for (int y = 0; y < h.perTurn; y++) {
			double lastBottom = -1, firstTop = 99;
			for (int[] c : tread(Fill.Mode.SPIRAL, slab(), y, s, sy, s)) {
				BlockState st = Fill.Mode.SPIRAL.state(slab(), c[0], y, c[1], s, sy, s);
				double along = h.along(c[0], c[1]);
				if (st.getValue(SlabBlock.TYPE) == SlabType.BOTTOM) lastBottom = Math.max(lastBottom, along);
				else firstTop = Math.min(firstTop, along);
			}
			assertTrue(lastBottom < firstTop, "course " + y + ": a top slab before a bottom one");
		}
	}

	@Test
	void theCaptureCarriesEveryOrientationAndCountsTheRightCellsAsBuilt() {
		int s = 7, sy = 12;
		BlockPos a = new BlockPos(10, 60, 10), b = new BlockPos(10 + s - 1, 60 + sy - 1, 10 + s - 1);
		Fill.Plan p = Fill.plan(empty(), a, b, stair(), Fill.Mode.SPIRAL, null);
		Capture cap = Fill.capture(empty(), p);
		assertEquals(p.place(), cap.nonAirCount());
		Set<Direction> facings = new HashSet<>();
		for (BlockState st : cap.palette()) {
			if (st.getBlock() instanceof StairBlock) facings.add(st.getValue(StairBlock.FACING));
		}
		assertEquals(4, facings.size(), "a full turn faces every cardinal: " + facings);

		// A tread already standing with the RIGHT facing is built; the same block facing the wrong
		// way is work - which is the one thing `/cscan check` could not see before states were
		// recorded, and the one that makes a flight unwalkable.
		BlockState right = null;
		int rx = -1, ry = -1, rz = -1;
		for (int y = 0; y < sy && right == null; y++) {
			right = Fill.Mode.SPIRAL.state(stair(), 0, y, 3, s, sy, s);
			rx = 10; ry = 60 + y; rz = 13;
		}
		assertNotNull(right);
		final int fx = rx, fy = ry, fz = rz;
		final BlockState placed = right;
		Fill.Probe built = (x, y, z) -> (x == fx && y == fy && z == fz) ? placed : Blocks.AIR.defaultBlockState();
		assertEquals(1, Fill.plan(built, a, b, stair(), Fill.Mode.SPIRAL, null).already());
		final BlockState wrong = right.setValue(StairBlock.FACING, right.getValue(StairBlock.FACING).getOpposite());
		Fill.Probe backwards = (x, y, z) -> (x == fx && y == fy && z == fz) ? wrong : Blocks.AIR.defaultBlockState();
		assertEquals(0, Fill.plan(backwards, a, b, stair(), Fill.Mode.SPIRAL, null).already());
	}

	@Test
	void modeNamesParse() {
		assertEquals(Fill.Mode.SPIRAL, Fill.Mode.of("spiral"));
		assertEquals(Fill.Mode.SPIRAL, Fill.Mode.of("stairs"));
		assertEquals(Fill.Mode.SPIRAL_CCW, Fill.Mode.of("SpiralCCW"));
		assertEquals(Fill.Mode.HELIX, Fill.Mode.of("helix"));
		assertEquals(Fill.Mode.HELIX_CCW, Fill.Mode.of("helixccw"));
		assertFalse(Fill.Mode.SPIRAL.isFlat());
		assertTrue(Fill.Mode.HELIX_CCW.isSpiral());
		assertFalse(Fill.Mode.BALL.isSpiral());
	}
}
