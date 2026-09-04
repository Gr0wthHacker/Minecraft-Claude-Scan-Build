package dev.jack.chunkscan;

import net.minecraft.core.BlockPos;
import net.minecraft.nbt.NbtIo;
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.io.TempDir;
import java.nio.file.*;
import static org.junit.jupiter.api.Assertions.*;

class ActiveBuildTest {
    @TempDir Path dir;
    @BeforeAll static void boot() { BuildAuditTest.boot(); }
    @AfterEach void clear() { ActiveBuild.clear(); }

    ResumeBinding identity() throws Exception {
        return ResumeBinding.capture(dir, "wall", "server:test", "minecraft:overworld");
    }

    void schematic(int origin) throws Exception {
        NbtIo.writeCompressed(BuildAuditTest.schematic(BuildAuditTest.region(1,1,1,
            new int[]{0}, "stone")), dir.resolve("wall.litematic"));
        Files.writeString(dir.resolve("wall.scan.json"), "{\"origin\":{\"x\":" + origin
            + ",\"y\":64,\"z\":0},\"facing\":\"" + (origin == 10 ? "east" : "west")
			+ "\",\"anchor_status\":\"approved live registration\",\"automation_approved\":true,\"dig\":[[" + origin + ",63,0]]}");
    }

    @Test void sourceReplacementCannotMoveActiveCellsOrDigOrOrigin() throws Exception {
        schematic(10);
        var snapshot = ActiveBuild.prepare(dir, "wall", identity());
        ActiveBuild.activate(snapshot);
        schematic(100);
        assertEquals(90, Designs.facingDegrees(dir,"wall"));
        assertEquals(new BlockPos(10,64,0), Work.load(dir,"wall").getFirst().pos());
        assertEquals(new BlockPos(10,64,0), Designs.load(dir,"wall").origin());
        assertEquals(new BlockPos(10,63,0), Designs.load(dir,"wall").dig().getFirst());
        assertEquals(snapshot.binding(), ActiveBuild.binding(dir,"wall"));
        var next = ActiveBuild.prepare(dir, "wall", identity());
        ActiveBuild.activate(next);
        assertEquals(new BlockPos(100,64,0), Work.load(dir,"wall").getFirst().pos());
    }

    @Test void unregisteredWorkListCannotBecomeAnAutonomousBuild() throws Exception {
        Files.writeString(dir.resolve("wall.work.json"), "{\"cells\":[[5,64,0,\"glass\"]]}");
        assertThrows(java.io.IOException.class, () -> ActiveBuild.prepare(dir,"wall",identity()));
		schematic(100);
		var registered = ActiveBuild.prepare(dir,"wall",identity());
		assertTrue(Files.exists(registered.inputDirectory().resolve("wall.litematic")));
		ActiveBuild.activate(registered);
		assertEquals(new BlockPos(100,64,0), Work.load(dir,"wall").getFirst().pos());
    }

    @Test void siteMembershipStaysPinnedButOtherDirectoriesAreIndependent() throws Exception {
        schematic(10);
        Files.writeString(dir.resolve("islands.json"),
            "{\"islands\":{\"home\":{\"cx\":0,\"cz\":0,\"radius\":49}}}");
        ActiveBuild.activate(ActiveBuild.prepare(dir,"wall",identity()));
        Files.writeString(dir.resolve("islands.json"),
            "{\"islands\":{\"home\":{\"cx\":1000,\"cz\":0,\"radius\":49}}}");
        assertFalse(Islands.outside(dir,10,0));
        assertTrue(Islands.outside(dir,1000,0));
        Path other = Files.createDirectory(dir.resolve("other"));
        assertEquals(other, ActiveBuild.siteInputs(other));
        assertEquals(dir, ActiveBuild.inputs(dir,"different"));
    }

    @Test void staleExpectedBindingOrCorruptNewInputCannotReplaceActiveRevision() throws Exception {
        schematic(10);
        var expected = identity();
        var snapshot = ActiveBuild.prepare(dir,"wall",expected);
        ActiveBuild.activate(snapshot);
        schematic(100);
        assertThrows(java.io.IOException.class, () -> ActiveBuild.prepare(dir,"wall",expected));
        Files.writeString(dir.resolve("wall.litematic"),"corrupt");
        var corrupt = identity();
        assertThrows(Exception.class, () -> ActiveBuild.prepare(dir,"wall",corrupt));
        assertEquals(snapshot.binding(), ActiveBuild.binding(dir,"wall"));
        assertEquals(new BlockPos(10,64,0),Work.load(dir,"wall").getFirst().pos());
        try (var revisions = Files.list(dir.resolve(".cscan-build-inputs"))) {
            assertEquals(1, revisions.count(), "failed preparation left a partial revision");
        }
    }

	@Test void previewAndUnapprovedSidecarsNeverPassAutonomousPreflight() throws Exception {
		schematic(10);
		Files.writeString(dir.resolve("wall.scan.json"), "{\"origin\":{\"x\":10,\"y\":64,\"z\":0},"
			+ "\"anchor_status\":\"PREVIEW placement; rebase before building\",\"automation_approved\":true}");
		var preview = assertThrows(java.io.IOException.class, () -> ActiveBuild.prepare(dir,"wall",identity()));
		assertTrue(preview.getMessage().contains("PREVIEW"));
		Files.writeString(dir.resolve("wall.scan.json"), "{\"origin\":{\"x\":10,\"y\":64,\"z\":0},"
			+ "\"anchor_status\":\"approved live registration\"}");
		assertTrue(assertThrows(java.io.IOException.class, () -> ActiveBuild.prepare(dir,"wall",identity()))
			.getMessage().contains("automation_approved"));
	}
}
