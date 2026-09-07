package dev.jack.chunkscan;

import net.minecraft.core.BlockPos;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;
import java.util.Random;

import static org.junit.jupiter.api.Assertions.*;

/**
 * The recount's sort, which went from a boxed comparator to one packed primitive key.
 *
 * <p><b>Measured in game, `Work.split` cost 262 ms on average and 427 at worst - a quarter-second
 * freeze twice a second, and by far the largest thing this mod does.</b> A good part of it was
 * `Arrays.sort(Integer[], comparator)` over every remaining cell of the design: two hundred
 * thousand `Integer` allocations and about three and a half million virtual calls, per call.
 *
 * <p>The order is (recipe, then course, then distance) and all three fit in one long. What has to
 * be pinned is that the fast key still MEANS that - a build coming out in a different order would
 * be silent, and doors and beds are ordered by it on purpose.
 */
class SplitOrderTest {

	private static Work.Cell cell(int x, int y, int z, String state) {
		return new Work.Cell(new BlockPos(x, y, z), state);
	}

	/** The packed key, applied exactly as `split` applies it. */
	private static List<Work.Cell> fast(List<Work.Cell> todo, BlockPos near) {
		int n = todo.size();
		long[] key = new long[n];
		Work.Cell[] flat = todo.toArray(new Work.Cell[0]);
		for (int i = 0; i < n; i++) {
			Work.Cell c = flat[i];
			long recipe = Math.min(255, Math.max(0, ActionRecipe.order(c.block())));
			long y = Math.min(4095, Math.max(0, c.pos().getY() + 2048L));
			long dist = Math.min(1_048_575L, (long) (Math.sqrt(c.pos().distSqr(near)) * 4));
			key[i] = (recipe << 55) | (y << 43) | (dist << 23) | i;
		}
		java.util.Arrays.sort(key);
		List<Work.Cell> out = new ArrayList<>(n);
		for (long k : key) out.add(flat[(int) (k & 0x7FFFFF)]);
		return out;
	}

	@Test
	void theKeyIsNeverNegative() {
		// 8 + 12 + 20 + 24 bits needs 64, and the top one is the SIGN - a recipe of 128 or more
		// would have sorted before everything else, silently. 63 bits, every field clamped.
		long worst = (255L << 55) | (4095L << 43) | (1_048_575L << 23) | 0x7FFFFF;
		assertTrue(worst > 0, "the packed key must stay positive or the order inverts");
	}

	@Test
	void aDoorsLowerHalfComesBeforeItsUpper() {
		// This is what `ActionRecipe.order` is FOR: a door leaf placed top-first does not place.
		List<Work.Cell> in = List.of(
			cell(0, 10, 0, "minecraft:oak_door[half=upper,facing=north]"),
			cell(0, 9, 0, "minecraft:oak_door[half=lower,facing=north]"));
		List<Work.Cell> out = fast(in, BlockPos.ZERO);
		assertEquals("lower", out.get(0).block().contains("half=lower") ? "lower" : "upper");
	}

	@Test
	void bottomUpBeatsNearness() {
		// A cell at your feet on a higher course must not jump the course below it: you would
		// place a ceiling before the wall that was going to hold it.
		List<Work.Cell> in = List.of(
			cell(0, 20, 0, "minecraft:stone"),
			cell(60, 5, 0, "minecraft:stone"));
		assertEquals(5, fast(in, BlockPos.ZERO).get(0).pos().getY());
	}

	@Test
	void itAgreesWithTheOrderItReplaced() {
		// THE ONE THAT MATTERS. Random cells over a real spread of courses and distances; the fast
		// key and the spelled-out comparator must agree on every position but ties, and a tie here
		// is the same material on the same course within a quarter block - which is the whole of
		// what quantising the distance can reorder.
		Random r = new Random(20260907L);
		List<Work.Cell> in = new ArrayList<>();
		String[] states = {"minecraft:stone", "minecraft:oak_door[half=lower,facing=north]",
			"minecraft:oak_door[half=upper,facing=north]", "minecraft:red_bed[part=head,facing=north]"};
		for (int i = 0; i < 4000; i++) {
			in.add(cell(r.nextInt(400) - 200, r.nextInt(120), r.nextInt(400) - 200,
				states[r.nextInt(states.length)]));
		}
		BlockPos near = new BlockPos(7, 64, -13);
		List<Work.Cell> a = fast(in, near), b = Work.sortSlowly(in, near);
		assertEquals(b.size(), a.size());
		for (int i = 0; i < a.size(); i++) {
			Work.Cell x = a.get(i), y = b.get(i);
			assertEquals(ActionRecipe.order(y.block()), ActionRecipe.order(x.block()),
				"recipe order differs at " + i);
			assertEquals(y.pos().getY(), x.pos().getY(), "course differs at " + i);
			assertEquals(Math.sqrt(y.pos().distSqr(near)), Math.sqrt(x.pos().distSqr(near)), 0.25,
				"distance differs by more than the quarter block the key quantises to, at " + i);
		}
	}

	@Test
	void theIndexFieldBoundsTheDesignItCanSort() {
		// 23 bits is 8.4 million cells against 526,385 in the largest design here; past it the
		// index would wrap into the distance field and the order would be quietly wrong.
		assertTrue(Work.SORT_INDEX_MAX > 8_000_000);
	}
}
