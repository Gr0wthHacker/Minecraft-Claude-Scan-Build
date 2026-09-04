package dev.jack.chunkscan;

import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.SharedConstants;
import net.minecraft.server.Bootstrap;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.VineBlock;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class ActionRecipeTest {
	@org.junit.jupiter.api.BeforeAll static void boot() { SharedConstants.tryDetectVersion(); Bootstrap.bootStrap(); }
    @Test void ordinaryBlockItemsRemainEligible() {
        assertNull(ActionRecipe.missingFor("stone"));
        assertNull(ActionRecipe.missingFor("oak_planks"));
        assertNull(ActionRecipe.missingFor("stone_slab[type=bottom]"));
    }

    @Test void specialActionsAreClassifiedBeforeMovement() {
		assertNull(ActionRecipe.missingFor("water"));
		assertNull(ActionRecipe.missingFor("water[level=0]"));
		assertEquals("fluid flow shaping", ActionRecipe.missingFor("water[level=3]"));
		assertEquals("fluid bucket placement", ActionRecipe.missingFor("lava"));
		assertNull(ActionRecipe.missingFor("redstone_wall_torch[facing=north]"));
        assertEquals("wall sign placement/configuration", ActionRecipe.missingFor("oak_wall_sign[facing=north]"));
		assertNull(ActionRecipe.missingFor("redstone_wire[north=side,power=0]"));
		assertEquals("redstone/rail commissioning", ActionRecipe.missingFor("redstone_wire[power=4]"));
		assertNull(ActionRecipe.missingFor("stone_slab[type=double]"));
		assertNull(ActionRecipe.missingFor("oak_door[half=lower]"));
    }

	@Test void waterUsesBucketsForPlanningAndStorage() {
		assertEquals("water_bucket", ActionRecipe.itemFor("water[level=0]"));
		assertEquals("stone", ActionRecipe.itemFor("stone"));
		assertEquals("water_bucket", new Work.Cell(BlockPos.ZERO, "water").item());
	}

    @Test void reportCountsRecipeFamiliesAndPreflightFailsClosed() {
        var cells = List.of(new Work.Cell(BlockPos.ZERO, "lava"),
            new Work.Cell(new BlockPos(1,0,0), "lava"),
            new Work.Cell(new BlockPos(2,0,0), "redstone_wire[power=4]"));
        assertEquals(2, ActionRecipe.missing(cells).get("fluid bucket placement"));
        var error = assertThrows(java.io.IOException.class, () -> ActionRecipe.require(cells));
        assertTrue(error.getMessage().contains("2 fluid bucket placement"));
        assertTrue(error.getMessage().contains("1 redstone/rail commissioning"));
    }

	@Test void halfSlabIsARepairableIntermediateButOtherBlocksAreNot() {
		assertTrue(ActionRecipe.slabIntermediate(Blocks.STONE_SLAB.defaultBlockState(), "stone_slab[type=double]"));
		assertFalse(ActionRecipe.slabIntermediate(Blocks.STONE_SLAB.defaultBlockState(), "stone_slab[type=bottom]"));
		assertFalse(ActionRecipe.slabIntermediate(Blocks.STONE.defaultBlockState(), "stone_slab[type=double]"));
	}

	@Test void multiFaceVineAccumulatesOnlyRequiredAttachments() {
		var north = Blocks.VINE.defaultBlockState().setValue(VineBlock.NORTH, true);
		var northEast = north.setValue(VineBlock.EAST, true);
		String wanted = "vine[north=true,east=true,south=false,west=false,up=false]";
		assertTrue(ActionRecipe.vineIntermediate(north, wanted));
		assertTrue(ActionRecipe.vineProgress(Blocks.AIR.defaultBlockState(), north, wanted));
		assertTrue(ActionRecipe.vineProgress(north, northEast, wanted));
		assertFalse(ActionRecipe.vineIntermediate(northEast, wanted));
		assertFalse(ActionRecipe.vineIntermediate(north, "vine[north=false,east=true]"));
	}

	@Test void glowLichenAccumulatesOnlyRequiredAttachments() {
		var down = Blocks.GLOW_LICHEN.defaultBlockState().setValue(
			net.minecraft.world.level.block.MultifaceBlock.getFaceProperty(Direction.DOWN), true);
		var downNorth = down.setValue(
			net.minecraft.world.level.block.MultifaceBlock.getFaceProperty(Direction.NORTH), true);
		String wanted = "glow_lichen[down=true,north=true,south=false,up=false,east=false,west=false,waterlogged=false]";
		assertTrue(ActionRecipe.glowLichenIntermediate(down, wanted));
		assertTrue(ActionRecipe.glowLichenProgress(Blocks.AIR.defaultBlockState(), down, wanted));
		assertTrue(ActionRecipe.glowLichenProgress(down, downNorth, wanted));
		assertFalse(ActionRecipe.glowLichenIntermediate(downNorth, wanted));
	}

	@Test void multiBlockInitiatorsSortBeforeGeneratedHalves() {
		assertTrue(ActionRecipe.order("oak_door[half=lower]") < ActionRecipe.order("oak_door[half=upper]"));
		assertTrue(ActionRecipe.order("red_bed[part=foot]") < ActionRecipe.order("red_bed[part=head]"));
		assertEquals(1, ActionRecipe.order("stone"));
	}
}
