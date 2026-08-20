package dev.jack.chunkscan;

import net.minecraft.SharedConstants;
import net.minecraft.core.BlockPos;
import net.minecraft.server.Bootstrap;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * The undo snapshot, and the storage guard.
 *
 * <p>Undo cannot be a straight inverse, because a litematic cannot express removal. Where the fill
 * covers a block, that block is recorded and re-placing it restores the cell; where the fill puts
 * something into AIR there is nothing to record, and the cell has to go in the `dig` list instead.
 * Both halves are needed or the undo half-works — which is worse than none, because you would
 * believe it.
 */
class UndoAndStorageTest {
	@BeforeAll
	static void boot() {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
	}

	private static final class World {
		final Map<Long, BlockState> cells = new HashMap<>();

		void set(int x, int y, int z, BlockState s) {
			cells.put(BlockPos.asLong(x, y, z), s);
		}

		Fill.Probe probe() {
			return (x, y, z) -> cells.getOrDefault(BlockPos.asLong(x, y, z), Blocks.AIR.defaultBlockState());
		}
	}

	@Test
	void undoRecordsWhatWasThereAndDigsWhatWasNot() {
		World w = new World();
		w.set(0, 0, 0, Blocks.COBBLESTONE.defaultBlockState());
		w.set(1, 0, 0, Blocks.MOSS_BLOCK.defaultBlockState());
		// (2,0,0) and (3,0,0) are air
		BlockState mat = Blocks.STONE_BRICKS.defaultBlockState();
		Fill.Plan p = Fill.plan(w.probe(), new BlockPos(0, 0, 0), new BlockPos(3, 0, 0), mat);
		List<int[]> dig = new ArrayList<>();
		Capture undo = Fill.undoCapture(w.probe(), p, dig);

		assertEquals(2, undo.nonAirCount(), "the two real blocks are restorable");
		assertEquals(2, dig.size(), "the two air cells can only be undone by breaking");
		assertEquals(p.place(), undo.nonAirCount() + dig.size(),
			"every cell the fill changes must be undoable one way or the other");
	}

	@Test
	void theUndoPaletteCarriesTheOriginalBlocks() {
		World w = new World();
		w.set(0, 0, 0, Blocks.COBBLESTONE.defaultBlockState());
		w.set(1, 0, 0, Blocks.MOSS_BLOCK.defaultBlockState());
		Fill.Plan p = Fill.plan(w.probe(), new BlockPos(0, 0, 0), new BlockPos(1, 0, 0),
			Blocks.STONE_BRICKS.defaultBlockState());
		Capture undo = Fill.undoCapture(w.probe(), p, new ArrayList<>());
		assertTrue(undo.palette().contains(Blocks.COBBLESTONE.defaultBlockState()));
		assertTrue(undo.palette().contains(Blocks.MOSS_BLOCK.defaultBlockState()));
		assertEquals(Blocks.AIR.defaultBlockState(), undo.palette().get(0), "index 0 must be air");
	}

	@Test
	void undoIgnoresCellsTheFillNeverTouched() {
		// A protected cell is skipped by the fill, so undoing it would RE-place a hopper the fill
		// never covered - noise at best, and a second hopper at worst.
		World w = new World();
		w.set(1, 0, 1, Blocks.HOPPER.defaultBlockState());
		Fill.Plan p = Fill.plan(w.probe(), new BlockPos(0, 0, 0), new BlockPos(3, 0, 3),
			Blocks.STONE_BRICKS.defaultBlockState());
		List<int[]> dig = new ArrayList<>();
		Capture undo = Fill.undoCapture(w.probe(), p, dig);
		assertFalse(undo.palette().contains(Blocks.HOPPER.defaultBlockState()));
		assertEquals(p.place(), undo.nonAirCount() + dig.size());
	}

	@Test
	void undoFollowsTheShapeNotTheBox() {
		World w = new World();
		for (int x = 0; x < 5; x++) {
			for (int y = 0; y < 5; y++) {
				for (int z = 0; z < 5; z++) w.set(x, y, z, Blocks.COBBLESTONE.defaultBlockState());
			}
		}
		Fill.Plan p = Fill.plan(w.probe(), new BlockPos(0, 0, 0), new BlockPos(4, 4, 4),
			Blocks.STONE_BRICKS.defaultBlockState(), Fill.Mode.HOLLOW, null);
		Capture undo = Fill.undoCapture(w.probe(), p, new ArrayList<>());
		assertEquals(125 - 27, undo.nonAirCount(), "a hollow fill's undo is the shell, not the box");
	}

	@Test
	void aSignIsNotAContainer() {
		// 141 of 269 storage entries were filed against blocks like these, because the watcher
		// remembered every right-click and then attributed the next screen to it.
		for (String n : new String[]{"warped_wall_sign", "oak_wall_sign", "stone_bricks",
		                             "mossy_stone_brick_slab", "stone_brick_wall", "moss_block",
		                             "cobblestone"}) {
			assertFalse(Storage.stores(n), n + " must never be indexed as storage");
		}
	}

	@Test
	void aChestIsAContainer() {
		for (String n : new String[]{"chest", "trapped_chest", "barrel", "minecraft:barrel",
		                             "white_shulker_box", "hopper", "blast_furnace"}) {
			assertTrue(Storage.stores(n), n + " must be indexable");
			assertTrue(Storage.isContainer(n));
		}
	}

	@Test
	void aCraftingTableOpensAScreenButStoresNothing() {
		// The watcher may fire on it; the index must not keep it, or `/cscan find` starts offering
		// you a workbench as a source of stone.
		assertTrue(Storage.isContainer("crafting_table"));
		assertFalse(Storage.stores("crafting_table"));
		assertTrue(Storage.isContainer("enchanting_table"));
		assertFalse(Storage.stores("enchanting_table"));
	}

	@Test
	void rotationWordsMapToTheGamesNames() {
		assertEquals("CLOCKWISE_90", Litematica.rotationOf("90"));
		assertEquals("CLOCKWISE_90", Litematica.rotationOf("cw"));
		assertEquals("CLOCKWISE_180", Litematica.rotationOf("180"));
		assertEquals("COUNTERCLOCKWISE_90", Litematica.rotationOf("270"));
		assertEquals("COUNTERCLOCKWISE_90", Litematica.rotationOf("ccw"));
		assertEquals("NONE", Litematica.rotationOf(null));
		assertEquals("NONE", Litematica.rotationOf("sideways"));
	}

	@Test
	void everyRotationNameIsARealGameConstant() {
		// The name is handed to Enum.valueOf by reflection, so a typo here is a crash in game and
		// nothing sooner.
		for (String w : new String[]{"90", "180", "270", "cw", "ccw"}) {
			String r = Litematica.rotationOf(w);
			assertTrue(java.util.Arrays.stream(net.minecraft.world.level.block.Rotation.values())
				.anyMatch(v -> v.name().equals(r)), r + " is not a Rotation constant");
		}
	}
}
