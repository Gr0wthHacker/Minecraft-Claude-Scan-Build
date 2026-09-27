package dev.jack.chunkscan;

import net.minecraft.SharedConstants;
import net.minecraft.server.Bootstrap;
import net.minecraft.world.level.block.Blocks;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class StateContractTest {
    @BeforeAll static void boot() { SharedConstants.tryDetectVersion(); Bootstrap.bootStrap(); }

    @Test void leafDistanceCanConvergeWithoutLosingRawRequirement() {
        String spec = "oak_leaves[distance=1]";
        assertTrue(Work.matches(Blocks.OAK_LEAVES.defaultBlockState(), spec));
        assertEquals("1", StateContract.parse(spec).properties.get("distance"));
        assertFalse(Work.matches(Blocks.OAK_LEAVES.defaultBlockState(), "oak_leaves[persistent=true]"));
    }

    @Test void automaticStairShapeDoesNotEraseOrientation() {
        var stairs = Blocks.STONE_BRICK_STAIRS.defaultBlockState();
        assertTrue(Work.matches(stairs, "stone_brick_stairs[shape=outer_left]"));
        assertFalse(Work.matches(stairs, "stone_brick_stairs[half=top]"));
        assertFalse(Work.matches(stairs, "stone_brick_stairs[facing=south]"));
    }

    @Test void fenceConnectionsAreDerivedButVineAttachmentsAreRequired() {
        assertTrue(Work.matches(Blocks.OAK_FENCE.defaultBlockState(), "oak_fence[north=true]"));
        assertFalse(Work.matches(Blocks.VINE.defaultBlockState(), "vine[north=true]"));
    }

    @Test void fluidsPowerAndRailGeometryRemainCompletionRequirements() {
        assertFalse(Work.matches(Blocks.STONE_BRICK_STAIRS.defaultBlockState(), "stone_brick_stairs[waterlogged=true]"));
        assertFalse(Work.matches(Blocks.POWERED_RAIL.defaultBlockState(), "powered_rail[powered=true]"));
        assertFalse(Work.matches(Blocks.RAIL.defaultBlockState(), "rail[shape=east_west]"));
    }

    @Test void malformedOrUnknownPropertiesNeverTurnIntoSuccess() {
        for (String spec : new String[]{"stone[", "stone[]", "stone[foo]", "stone[foo=bar]",
                "oak_leaves[distance=99]", "oak_leaves[distance=1,distance=2]"})
            assertFalse(Work.matches(Blocks.OAK_LEAVES.defaultBlockState(), spec), spec);
        assertFalse(Work.matches(Blocks.STONE.defaultBlockState(), "stone["));
        assertFalse(Work.matches(Blocks.STONE.defaultBlockState(), "stone[foo=bar]"));
    }
}
