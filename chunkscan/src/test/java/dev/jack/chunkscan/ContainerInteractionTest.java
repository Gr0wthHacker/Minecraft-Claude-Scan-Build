package dev.jack.chunkscan;

import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.Vec3;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class ContainerInteractionTest {
    private final BlockPos chest = new BlockPos(4, 64, 0);
    private final Vec3 eye = new Vec3(0.5, 65.62, 0.5);

    @Test void visibleSurfaceInsideReachIsAccepted() {
        var hit = new BlockHitResult(new Vec3(4, 64.8, 0.5), Direction.WEST, chest, false);
        assertTrue(ContainerInteraction.accepts(eye, chest, hit, 4.5));
    }

    @Test void nearbyChestBehindAnotherBlockDoesNotCountAsArrival() {
        var wall = new BlockHitResult(new Vec3(2, 65, 0.5), Direction.WEST, new BlockPos(2,65,0), false);
        assertFalse(ContainerInteraction.accepts(eye, chest, wall, 4.5));
    }

    @Test void ActualEyeDistanceControlsArrival() {
        var hit = new BlockHitResult(new Vec3(4,64,0.5), Direction.WEST, chest, false);
        assertFalse(ContainerInteraction.accepts(new Vec3(-0.3,66,0.5), chest, hit, 4.5));
    }

    @Test void MissAndInsideBlockCannotStartWithdrawal() {
        assertFalse(ContainerInteraction.accepts(eye, chest,
            BlockHitResult.miss(Vec3.atCenterOf(chest),Direction.WEST,chest),4.5));
        assertFalse(ContainerInteraction.accepts(eye, chest,
            new BlockHitResult(eye,Direction.WEST,chest,true),4.5));
    }
    @Test void approachSearchCoversReachableHeightsBeforeWorldClearanceFiltersIt() {
        var cells = ContainerInteraction.approachCells(chest).toList();
        assertEquals(405, cells.size());
        assertTrue(cells.contains(new BlockPos(0, 64, 0)));
        assertTrue(cells.contains(new BlockPos(8, 66, 4)));
        assertTrue(cells.contains(chest), "the world-clearance predicate, not enumeration, rejects the solid chest");
    }
}
