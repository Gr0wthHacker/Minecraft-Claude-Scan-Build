package dev.jack.chunkscan;

import net.minecraft.SharedConstants;
import net.minecraft.core.BlockPos;
import net.minecraft.server.Bootstrap;
import net.minecraft.world.item.DyeColor;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

import java.util.HashMap;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * The wand fills a box in a world people are USING, so everything worth testing here is about what
 * it must not do: cover a mechanism, charge you for cells that are already right, or quietly place
 * a block where it skipped one.
 */
class FillTest {
	@BeforeAll
	static void boot() {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
	}

	/** A world you can write into, so a test can put a hopper somewhere awkward. */
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
	void aPlainBoxIsAllWork() {
		World w = new World();
		Fill.Plan p = Fill.plan(w.probe(), new BlockPos(0, 0, 0), new BlockPos(2, 1, 3),
			Blocks.STONE_BRICKS.defaultBlockState());
		assertEquals(3 * 2 * 4, p.volume());
		assertEquals(3 * 2 * 4, p.place());
		assertEquals(0, p.skipProtected());
		assertEquals(0, p.already());
	}

	@Test
	void cornersMayBeGivenInAnyOrder() {
		World w = new World();
		BlockState mat = Blocks.STONE_BRICKS.defaultBlockState();
		Fill.Plan a = Fill.plan(w.probe(), new BlockPos(5, 9, 7), new BlockPos(1, 2, 3), mat);
		Fill.Plan b = Fill.plan(w.probe(), new BlockPos(1, 2, 3), new BlockPos(5, 9, 7), mat);
		assertEquals(a.min(), b.min());
		assertEquals(a.max(), b.max());
		assertEquals(new BlockPos(1, 2, 3), a.min());
	}

	@Test
	void aMechanismIsSkippedAndReported() {
		// THE RULE THAT PRODUCED protect.py: a hopper under a floor and a wool block that is really
		// a sculk sensor's silencer. A fill that swallows either is a loss, not a fill.
		World w = new World();
		w.set(1, 0, 1, Blocks.HOPPER.defaultBlockState());
		// 26.x: wool is a ColorCollection, not sixteen Blocks fields - Blocks.GRAY_WOOL is gone.
		w.set(2, 0, 1, Blocks.WOOL.pick(DyeColor.GRAY).defaultBlockState());
		Fill.Plan p = Fill.plan(w.probe(), new BlockPos(0, 0, 0), new BlockPos(3, 0, 3),
			Blocks.STONE_BRICKS.defaultBlockState());
		assertEquals(2, p.skipProtected());
		assertEquals(16 - 2, p.place());
		assertTrue(p.protectedKinds().containsKey("hopper"));
		assertTrue(p.protectedKinds().containsKey("gray_wool"), "wool matches by substring, and must");
		assertTrue(Fill.skipSummary(p).contains("hopper"));
	}

	@Test
	void aCellThatIsAlreadyTheMaterialIsNotWork() {
		// Designs in this project are REMAINING WORK. A box half built already must cost half.
		World w = new World();
		BlockState mat = Blocks.STONE_BRICKS.defaultBlockState();
		for (int x = 0; x < 2; x++) w.set(x, 0, 0, mat);
		Fill.Plan p = Fill.plan(w.probe(), new BlockPos(0, 0, 0), new BlockPos(3, 0, 0), mat);
		assertEquals(2, p.already());
		assertEquals(2, p.place());
	}

	@Test
	void everySkippedCellComesOutAsAirInTheSchematic() {
		// A litematic cannot express removal, so air is how "nothing to do here" is spelt. If a
		// skipped cell carried the material instead, the printer would cover the hopper after all.
		World w = new World();
		w.set(1, 0, 1, Blocks.HOPPER.defaultBlockState());
		BlockState mat = Blocks.STONE_BRICKS.defaultBlockState();
		Fill.Plan p = Fill.plan(w.probe(), new BlockPos(0, 0, 0), new BlockPos(3, 0, 3), mat);
		Capture cap = Fill.capture(w.probe(), p);

		assertEquals(2, cap.palette().size(), "palette is exactly {air, material}");
		assertEquals(Blocks.AIR.defaultBlockState(), cap.palette().get(0), "index 0 must be air");
		assertEquals(p.place(), cap.nonAirCount());

		int sx = p.sizeX(), sz = p.sizeZ();
		int idx = ((0) * sz + (1 - p.min().getZ())) * sx + (1 - p.min().getX());
		assertEquals(0, cap.ids()[idx], "the hopper's cell must be air");
	}

	@Test
	void theCaptureIsAnchoredAtTheBoxCorner() {
		// The sidecar's origin IS the paste origin. Get this wrong and the printer builds the box
		// somewhere else entirely - the one failure that looks like a Litematica bug and is not.
		World w = new World();
		Fill.Plan p = Fill.plan(w.probe(), new BlockPos(-24205, 194, 30012), new BlockPos(-24200, 196, 30016),
			Blocks.DEEPSLATE_BRICKS.defaultBlockState());
		Capture cap = Fill.capture(w.probe(), p);
		assertEquals(-24205, cap.originX());
		assertEquals(194, cap.originY());
		assertEquals(30012, cap.originZ());
		assertEquals(6, cap.sizeX());
		assertEquals(3, cap.sizeY());
		assertEquals(5, cap.sizeZ());
	}

	@Test
	void plainBuildingBlocksAreNotProtected() {
		// The gate has to let the actual palette through, or nothing fills at all.
		for (String n : new String[]{"minecraft:stone_bricks", "minecraft:deepslate_bricks",
		                             "minecraft:smooth_stone", "minecraft:moss_block"}) {
			assertFalse(Rules.isProtected(n), n + " would be unfillable");
		}
	}

	@Test
	void dirtIsCurrencyAndSaysSo() {
		// DIRT IS CURRENCY on skyblock.net. It is real, legal, in 1.19 and placeable, so every
		// other check passes it silently - this is the only one that can object.
		assertTrue(Rules.isCurrency("minecraft:dirt"));
		assertTrue(Rules.isCurrency("minecraft:grass_block[snowy=false]"));
		assertFalse(Rules.isCurrency("minecraft:stone_bricks"));
		assertFalse(Rules.objections("minecraft:dirt").isEmpty());
		assertTrue(Rules.objections("minecraft:stone_bricks").isEmpty(),
			"the deck's own palette must draw no warning");
	}

	@Test
	void aBlockStateCarriesItsPropertiesIntoThePalette() {
		BlockState slab = Blocks.STONE_BRICK_SLAB.defaultBlockState();
		assertNotEquals(Blocks.STONE_BRICKS.defaultBlockState(), slab);
		World w = new World();
		Fill.Plan p = Fill.plan(w.probe(), new BlockPos(0, 0, 0), new BlockPos(1, 0, 1), slab);
		Capture cap = Fill.capture(w.probe(), p);
		assertEquals(slab, cap.palette().get(1));
	}

	@Test
	void hollowIsTheShellAndNotTheInterior() {
		// A room, rather than a block of stone you then hollow out by hand - which on a survival
		// server is the expensive half.
		World w = new World();
		Fill.Plan p = Fill.plan(w.probe(), new BlockPos(0, 0, 0), new BlockPos(4, 4, 4),
			Blocks.STONE_BRICKS.defaultBlockState(), Fill.Mode.HOLLOW, null);
		assertEquals(125, p.volume());
		assertEquals(125 - 27, p.place(), "a 5x5x5 shell is the box less its 3x3x3 core");
		assertEquals(27, p.outsideShape());
	}

	@Test
	void wallsLeaveTheFloorAndCeilingAlone() {
		World w = new World();
		Fill.Plan p = Fill.plan(w.probe(), new BlockPos(0, 0, 0), new BlockPos(4, 4, 4),
			Blocks.STONE_BRICKS.defaultBlockState(), Fill.Mode.WALLS, null);
		// the four sides of a 5x5 plan, every course: 16 per course, 5 courses
		assertEquals(16 * 5, p.place());
	}

	@Test
	void outlineIsTheTwelveEdges() {
		World w = new World();
		Fill.Plan p = Fill.plan(w.probe(), new BlockPos(0, 0, 0), new BlockPos(4, 4, 4),
			Blocks.STONE_BRICKS.defaultBlockState(), Fill.Mode.OUTLINE, null);
		// 12 edges of 5, less the 8 corners counted three times each
		assertEquals(12 * 5 - 8 * 2, p.place());
	}

	@Test
	void everyModeIsASubsetOfSolid() {
		World w = new World();
		BlockState mat = Blocks.STONE_BRICKS.defaultBlockState();
		BlockPos a = new BlockPos(0, 0, 0), b = new BlockPos(6, 4, 5);
		int solid = Fill.plan(w.probe(), a, b, mat, Fill.Mode.SOLID, null).place();
		for (Fill.Mode m : Fill.Mode.values()) {
			Fill.Plan p = Fill.plan(w.probe(), a, b, mat, m, null);
			assertTrue(p.place() <= solid, m + " places more than solid");
			assertEquals(p.volume(), p.place() + p.outsideShape() + p.already() + p.skipProtected());
		}
	}

	@Test
	void replaceTouchesOnlyTheNamedBlock() {
		// The deck floor's wood reclaim, by hand: 70 blocks of dark oak healed back into the plane
		// they interrupted, without touching the 1,700 cells around them.
		World w = new World();
		BlockState oak = Blocks.DARK_OAK_WOOD.defaultBlockState();
		w.set(1, 0, 1, oak);
		w.set(2, 0, 2, oak);
		w.set(3, 0, 3, Blocks.COBBLESTONE.defaultBlockState());
		Fill.Plan p = Fill.plan(w.probe(), new BlockPos(0, 0, 0), new BlockPos(3, 0, 3),
			Blocks.SMOOTH_STONE.defaultBlockState(), Fill.Mode.SOLID, "minecraft:dark_oak_wood");
		assertEquals(2, p.place(), "only the two dark oak cells are work");
		assertEquals(14, p.outsideShape(), "everything else is left exactly as it is");
	}

	@Test
	void replaceStillRefusesToCoverAMechanism() {
		// Naming a block explicitly does not buy an exemption: if someone's hopper is dark oak's
		// neighbour, or IS the named block, the safe set still wins.
		World w = new World();
		w.set(1, 0, 1, Blocks.HOPPER.defaultBlockState());
		Fill.Plan p = Fill.plan(w.probe(), new BlockPos(0, 0, 0), new BlockPos(3, 0, 3),
			Blocks.SMOOTH_STONE.defaultBlockState(), Fill.Mode.SOLID, "minecraft:hopper");
		assertEquals(0, p.place());
		assertEquals(1, p.skipProtected());
	}

	@Test
	void aModeOnlyEmitsCellsItAskedFor() {
		World w = new World();
		Fill.Plan p = Fill.plan(w.probe(), new BlockPos(0, 0, 0), new BlockPos(4, 4, 4),
			Blocks.STONE_BRICKS.defaultBlockState(), Fill.Mode.HOLLOW, null);
		Capture cap = Fill.capture(w.probe(), p);
		assertEquals(p.place(), cap.nonAirCount());
		int sx = p.sizeX(), sz = p.sizeZ();
		assertEquals(0, cap.ids()[(2 * sz + 2) * sx + 2], "the core must stay air");
	}

	@Test
	void modeNamesParseAndDefaultToSolid() {
		assertEquals(Fill.Mode.HOLLOW, Fill.Mode.of("hollow"));
		assertEquals(Fill.Mode.HOLLOW, Fill.Mode.of("SHELL"));
		assertEquals(Fill.Mode.WALLS, Fill.Mode.of("walls"));
		assertEquals(Fill.Mode.OUTLINE, Fill.Mode.of("frame"));
		assertEquals(Fill.Mode.SOLID, Fill.Mode.of(null));
		assertEquals(Fill.Mode.SOLID, Fill.Mode.of("nonsense"));
	}
}
