package dev.jack.chunkscan;

import net.minecraft.SharedConstants;
import net.minecraft.core.Direction;
import net.minecraft.server.Bootstrap;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.StairBlock;
import net.minecraft.world.level.block.SlabBlock;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.BlockStateProperties;
import net.minecraft.world.level.block.state.properties.Half;
import net.minecraft.world.level.block.state.properties.SlabType;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.assertEquals;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * State-aware verification. `/cscan check` used to compare block NAMES, so it could not tell a
 * stair facing east from one facing west, or a top slab from a bottom one — and the taproot
 * entrance places `smooth_stone_slab` as BOTH, four courses apart. Every one of them read "built".
 *
 * <p>The other half matters as much: the design names only the properties it DECIDED, so a property
 * it did not name must not be compared. A stair's `shape` and a wall's connections come from the
 * neighbourhood, and a check that flags those is a check nobody runs.
 */
class WorkStateTest {
	@BeforeAll
	static void boot() {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
	}

	@Test
	void aBareNameStillMatchesByNameAlone() {
		// Every work.json written before this carries bare names. An un-regenerated design has to
		// keep reading correctly or the upgrade breaks every design at once.
		assertTrue(Work.matches(Blocks.STONE_BRICKS.defaultBlockState(), "stone_bricks"));
		assertFalse(Work.matches(Blocks.STONE_BRICKS.defaultBlockState(), "deepslate_bricks"));
	}

	@Test
	void aStairFacingTheWrongWayIsNotBuilt() {
		// THE STAIR CONVENTION: a flight that ascends toward D has every tread facing=D. Built the
		// other way the risers face into the descent and you cannot walk up it.
		BlockState east = Blocks.STONE_BRICK_STAIRS.defaultBlockState()
			.setValue(StairBlock.FACING, Direction.EAST).setValue(StairBlock.HALF, Half.BOTTOM);
		BlockState west = east.setValue(StairBlock.FACING, Direction.WEST);
		String spec = "stone_brick_stairs[facing=east,half=bottom]";
		assertTrue(Work.matches(east, spec));
		assertFalse(Work.matches(west, spec), "a west-facing tread must not read as built");
	}

	@Test
	void aStairsShapeIsNotComparedBecauseTheGameChoseIt() {
		// `shape` is inner_left/outer_right/... derived from the neighbours. Flagging it would
		// report a deviation for a stair that is exactly right.
		BlockState s = Blocks.STONE_BRICK_STAIRS.defaultBlockState()
			.setValue(StairBlock.FACING, Direction.EAST).setValue(StairBlock.HALF, Half.BOTTOM)
			.setValue(StairBlock.SHAPE, net.minecraft.world.level.block.state.properties.StairsShape.INNER_LEFT);
		assertTrue(Work.matches(s, "stone_brick_stairs[facing=east,half=bottom]"));
	}

	@Test
	void aTopSlabIsNotABottomSlab() {
		// The taproot entrance places both, deliberately: `sill_cap` is type=top.
		BlockState top = Blocks.SMOOTH_STONE_SLAB.defaultBlockState().setValue(SlabBlock.TYPE, SlabType.TOP);
		BlockState bottom = top.setValue(SlabBlock.TYPE, SlabType.BOTTOM);
		BlockState dbl = top.setValue(SlabBlock.TYPE, SlabType.DOUBLE);
		assertTrue(Work.matches(top, "smooth_stone_slab[type=top]"));
		assertFalse(Work.matches(bottom, "smooth_stone_slab[type=top]"));
		// A double slab is a FULL BLOCK. Island Belly Full places these next to top slabs.
		assertFalse(Work.matches(dbl, "smooth_stone_slab[type=top]"));
		assertTrue(Work.matches(dbl, "smooth_stone_slab[type=double]"));
	}

	@Test
	void waterloggingIsNotADeviation() {
		// Someone poured water in, or the slab went into a flooded cell. The design did not decide
		// it and must not fail on it.
		BlockState wet = Blocks.SMOOTH_STONE_SLAB.defaultBlockState()
			.setValue(SlabBlock.TYPE, SlabType.TOP).setValue(BlockStateProperties.WATERLOGGED, true);
		assertTrue(Work.matches(wet, "smooth_stone_slab[type=top]"));
	}

	@Test
	void aLanternHangingIsDifferentFromOneStanding() {
		BlockState hung = Blocks.LANTERN.defaultBlockState().setValue(BlockStateProperties.HANGING, true);
		BlockState stood = hung.setValue(BlockStateProperties.HANGING, false);
		assertTrue(Work.matches(hung, "lantern[hanging=true]"));
		assertFalse(Work.matches(stood, "lantern[hanging=true]"));
	}

	@Test
	void aPropertyTheBlockDoesNotHaveReadsAsWrong() {
		// That is a design bug rather than a world deviation, and it should surface loudly instead
		// of silently passing.
		assertFalse(Work.matches(Blocks.STONE_BRICKS.defaultBlockState(), "stone_bricks[facing=east]"));
	}

	@Test
	void aTallyCountsItemsNotStates() {
		// A shopping list that says "12x stone_brick_stairs[facing=east,half=bottom]" is not a
		// shopping list, and four facings of one stair are one stack of one item.
		var cells = java.util.List.of(
			new Work.Cell(new net.minecraft.core.BlockPos(0, 0, 0), "stone_brick_stairs[facing=east,half=bottom]"),
			new Work.Cell(new net.minecraft.core.BlockPos(1, 0, 0), "stone_brick_stairs[facing=west,half=bottom]"),
			new Work.Cell(new net.minecraft.core.BlockPos(2, 0, 0), "stone_bricks"));
		var t = Work.tally(cells);
		org.junit.jupiter.api.Assertions.assertEquals(2, t.get("stone_brick_stairs"));
		org.junit.jupiter.api.Assertions.assertEquals(1, t.get("stone_bricks"));
		org.junit.jupiter.api.Assertions.assertEquals(2, t.size());
	}

	// ---------------------------------------------------------------- out of view is not finished

	@Test
	void aSplitCountsWhatItCouldNotSee() {
		// `split` can only diff chunks the client has, so everything else is absent from all three
		// lists — and an empty todo therefore means "nothing left HERE". On a 240-block island that
		// is routinely most of a design: start `follow all` at the far end and every design reads
		// complete in turn, in about a second, and the loop congratulates itself and stops.
		Work.Split seen = new Work.Split("x", java.util.List.of(), java.util.List.of(), 10, 0, null);
		assertTrue(seen.complete(), "nothing left and nothing hidden is finished");

		Work.Split hidden = new Work.Split("x", java.util.List.of(), java.util.List.of(), 10, 40,
			new net.minecraft.core.BlockPos(1, 2, 3));
		assertFalse(hidden.complete(), "called a design finished with 40 cells out of view");
		assertEquals(50, hidden.total(), "the unseen cells are part of the design");
	}

	@Test
	void whatCannotBeSeenIsNotCountedAsBuilt() {
		// The tempting shortcut - treat unloaded as built - reports a design finished and quietly
		// leaves it half-standing. It is remaining WORK either way; we just cannot see it yet.
		Work.Split hidden = new Work.Split("x", java.util.List.of(), java.util.List.of(), 0, 7,
			new net.minecraft.core.BlockPos(0, 0, 0));
		assertEquals(0, hidden.built());
		assertEquals(7, hidden.total());
	}
}
