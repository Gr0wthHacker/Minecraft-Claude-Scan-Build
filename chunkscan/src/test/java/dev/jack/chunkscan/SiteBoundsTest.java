package dev.jack.chunkscan;

import java.nio.file.*;
import java.util.Map;
import net.minecraft.core.BlockPos;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import static org.junit.jupiter.api.Assertions.*;

class SiteBoundsTest {
    private void park(Path dir) throws Exception {
        Files.writeString(dir.resolve("islands.json"), """
            {"islands": {
              "left": {"cx":97600,"cz":80400,"site":"park","bounds":{"min_x":97500,"min_z":80300,"max_x_exclusive":97700,"max_z_exclusive":80500}},
              "middle": {"cx":97600,"cz":80600,"site":"park","bounds":{"min_x":97500,"min_z":80500,"max_x_exclusive":97700,"max_z_exclusive":80700}},
              "right": {"cx":97600,"cz":80800,"site":"park","bounds":{"min_x":97500,"min_z":80700,"max_x_exclusive":97700,"max_z_exclusive":80900}},
              "old_main": {"cx":-24200,"cz":30000,"radius":49}
            }}
            """);
    }

    @Test void allExpandedParkColumnsAndOnlyTheirExactRimArePermitted(@TempDir Path dir) throws Exception {
        park(dir);
        for (int x=97500; x<97700; x++) for (int z=80300; z<80900; z++)
            assertFalse(Islands.outside(dir,x,z));
        for (int z=80300; z<80900; z++) {
            assertTrue(Islands.outside(dir,97499,z));
            assertTrue(Islands.outside(dir,97700,z));
        }
        assertTrue(Islands.outside(dir,97600,80299));
        assertTrue(Islands.outside(dir,97600,80900));
        assertEquals("middle",Islands.at(dir,97500,80500).name());
        assertEquals(1,Islands.at(dir,97500,80499).over(97500,80500));
    }

    @Test void originPlotCanUseLinkedDepotButNotOtherSitesOrDimensions(@TempDir Path dir) throws Exception {
        park(dir);
        var depot = BuildAuditTest.chest(97600,"minecraft:overworld",64); depot.z=80600;
        var old = BuildAuditTest.chest(-24200,"minecraft:overworld",999); old.z=30000;
        var nether = BuildAuditTest.chest(97600,"minecraft:the_nether",999); nether.z=80600;
        var result = Storage.scoped(Map.of("depot",depot,"old",old,"nether",nether),dir,
            new BlockPos(97500,94,80300),"minecraft:overworld");
        assertEquals(Map.of("depot",depot),result);
    }

    @Test void invalidRegistryDoesNotFallBackOrKeepPartialPermissions(@TempDir Path dir) throws Exception {
        Files.writeString(dir.resolve("islands.json"),"""
            {"islands":{"valid":{"cx":0,"cz":0},"bad":{"cx":100,"cz":0,
              "bounds":{"min_x":100,"min_z":0,"max_x_exclusive":100,"max_z_exclusive":20}}}}
            """);
        assertTrue(Islands.all(dir).isEmpty());
        assertTrue(Islands.outside(dir,0,0));
        assertTrue(Storage.scoped(Map.of("a",BuildAuditTest.chest(0,"minecraft:overworld",64)),
            dir,BlockPos.ZERO,"minecraft:overworld").isEmpty());
    }
}
