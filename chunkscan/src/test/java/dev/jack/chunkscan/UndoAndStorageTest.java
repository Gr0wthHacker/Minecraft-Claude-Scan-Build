package dev.jack.chunkscan;

import net.minecraft.SharedConstants;
import net.minecraft.core.BlockPos;
import net.minecraft.server.Bootstrap;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.assertSame;

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

	// ---------------------------------------------------------------- the index goes stale

	@Test
	void theCacheReloadsWhenTheFileChanges() throws Exception {
		// `load` is a file read and a JSON parse, and the build loop asks every two seconds for as
		// long as it runs. Keyed on the mtime rather than on a timer, because you open a chest
		// PRECISELY so the loop is told about it - a timed cache would walk you to a chest the loop
		// still believes is empty.
		java.nio.file.Path d = java.nio.file.Files.createTempDirectory("cscan-cache");
		Storage.forget();
		Storage.Container c = new Storage.Container();
		c.x = 1; c.y = 2; c.z = 3; c.block = "chest"; c.id = 1;
		c.items.put("minecraft:stone_bricks", 64);
		java.util.Map<String, Storage.Container> m = new java.util.LinkedHashMap<>();
		m.put(c.key(), c);
		Storage.save(d, m);

		assertEquals(1, Storage.loadCached(d).size());
		assertSame(Storage.loadCached(d), Storage.loadCached(d), "re-read an unchanged file");

		Storage.Container two = new Storage.Container();
		two.x = 9; two.y = 2; two.z = 3; two.block = "barrel"; two.id = 2;
		m.put(two.key(), two);
		// the mtime has a resolution, and a test can easily write twice inside it
		Thread.sleep(1100);
		Storage.save(d, m);
		assertEquals(2, Storage.loadCached(d).size(), "did not notice the file had changed");
	}

	@Test
	void anExactFetchDoesNotMatchARelatedBlock() {
		// `stone_bricks` is a substring of `mossy_stone_bricks`, and a trip is a navigation
		// instruction rather than a search box.
		java.util.Map<String, Storage.Container> m = new java.util.LinkedHashMap<>();
		Storage.Container mossy = new Storage.Container();
		mossy.x = 1; mossy.block = "chest"; mossy.id = 1;
		mossy.items.put("minecraft:mossy_stone_bricks", 500);
		m.put(mossy.key(), mossy);
		assertTrue(Storage.findExact(m, "stone_bricks", BlockPos.ZERO).isEmpty(),
			"a fetch for stone bricks matched the mossy chest");
		assertFalse(Storage.find(m, "stone_bricks", BlockPos.ZERO).isEmpty(),
			"...and the fuzzy search that /cscan find wants still matches it");
	}

	@Test
	void aRecordWithNoItemsLeftIsNotAnAddress() {
		java.util.Map<String, Storage.Container> m = new java.util.LinkedHashMap<>();
		Storage.Container empty = new Storage.Container();
		empty.x = 1; empty.block = "chest"; empty.id = 1;
		empty.items.put("minecraft:stone_bricks", 0);
		m.put(empty.key(), empty);
		assertTrue(Storage.findExact(m, "stone_bricks", BlockPos.ZERO).isEmpty(),
			"offered a chest the index says is empty");
	}

	@Test
	void liveWithNoWorldChangesNothing() {
		// UNLOADED IS NOT ABSENT, and neither is "no world to ask". Getting this backwards empties
		// the index the first time it is consulted from the wrong place.
		java.util.Map<String, Storage.Container> m = new java.util.LinkedHashMap<>();
		Storage.Container c = new Storage.Container();
		c.x = 1; c.block = "chest"; c.id = 1;
		m.put(c.key(), c);
		assertSame(m, Storage.live(m, null));
	}

	// ---------------------------------------------------------------- boxes inside chests

	private static Storage.Container boxChest(int x, String boxedItem, int n) {
		Storage.Container c = new Storage.Container();
		c.x = x;
		c.y = 195;
		c.z = 0;
		c.block = "chest";
		c.id = 9;
		c.items.put("minecraft:white_shulker_box", 6);
		c.inBoxes.put("minecraft:" + boxedItem, n);
		return c;
	}

	@Test
	void aChestOfSHULKERSIsNotAChestOfShulkers() {
		// The index recorded "6x white_shulker_box", which is true and useless: the ten thousand
		// bricks inside were invisible to find, to the bill of materials and to the build loop,
		// which would fly past them to a chest holding sixty-four loose ones. Bulk storage on this
		// island IS boxes in chests.
		java.util.Map<String, Storage.Container> m = new java.util.LinkedHashMap<>();
		Storage.Container c = boxChest(1, "stone_bricks", 10368);
		m.put(c.key(), c);

		assertTrue(Storage.findExact(m, "stone_bricks", BlockPos.ZERO).isEmpty(),
			"a plan must not promise boxed blocks as if they were loose");
		assertFalse(Storage.findExact(m, "stone_bricks", BlockPos.ZERO, true).isEmpty(),
			"could not see ten thousand bricks in the boxes");
		assertEquals(10368, Storage.findExact(m, "stone_bricks", BlockPos.ZERO, true).get(0).count());
		assertEquals(10368, Storage.boxedCount(c, "stone_bricks"));
	}

	@Test
	void looseAndBoxedAreAddedUpForTheSameChest() {
		java.util.Map<String, Storage.Container> m = new java.util.LinkedHashMap<>();
		Storage.Container c = boxChest(1, "stone_bricks", 1728);
		c.items.put("minecraft:stone_bricks", 64);
		m.put(c.key(), c);
		assertEquals(64, Storage.findExact(m, "stone_bricks", BlockPos.ZERO).get(0).count());
		assertEquals(1792, Storage.findExact(m, "stone_bricks", BlockPos.ZERO, true).get(0).count());
	}

	@Test
	void aBoxOfSomethingElseIsNotAHit() {
		java.util.Map<String, Storage.Container> m = new java.util.LinkedHashMap<>();
		Storage.Container c = boxChest(1, "cobblestone", 1728);
		m.put(c.key(), c);
		assertTrue(Storage.findExact(m, "stone_bricks", BlockPos.ZERO, true).isEmpty());
	}

	@Test
	void anIndexWrittenBeforeThisStillReads() throws Exception {
		// `inBoxes` is absent from every record written before today, which must read as "no boxes
		// known here" rather than failing the load - the index is re-written from the screen the
		// next time the container is opened.
		java.nio.file.Path d = java.nio.file.Files.createTempDirectory("cscan-boxes");
        java.nio.file.Files.writeString(d.resolve("storage.json"),
			"{\"containers\":[{\"id\":1,\"x\":1,\"y\":2,\"z\":3,\"block\":\"chest\","
				+ "\"items\":{\"minecraft:stone\":5}}]}");
		Storage.forget();
		var all = Storage.load(d);
		assertEquals(1, all.size());
		assertTrue(all.values().iterator().next().inBoxes.isEmpty());
	}

	@Test
	void whatCountsAsABox() {
		assertTrue(Storage.isBox("white_shulker_box"));
		assertTrue(Storage.isBox("shulker_box"));
		assertFalse(Storage.isBox("chest"));
		assertFalse(Storage.isBox("barrel"));
	}
}
