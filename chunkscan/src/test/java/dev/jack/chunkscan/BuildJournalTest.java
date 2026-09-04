package dev.jack.chunkscan;

import net.minecraft.core.BlockPos;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Files;
import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.*;

class BuildJournalTest {
    @TempDir Path dir;
    private final ResumeBinding first = new ResumeBinding("server:a", "minecraft:overworld", "input-a");
    private final ResumeBinding second = new ResumeBinding("server:a", "minecraft:overworld", "input-b");

    @Test void startedActionRemainsUnknownUntilExplicitOutcome() throws Exception {
        String id = BuildJournal.begin(dir, first, new BlockPos(4, 70, -2), "stone");
        assertEquals("4,70,-2", BuildJournal.unresolved(dir, first).get(id));
        BuildJournal.finish(dir, first, id, Printer.Verdict.STILL_AIR, "air");
        assertTrue(BuildJournal.unresolved(dir, first).isEmpty());
    }

    @Test void aRejectedOrWrongPlacementIsAnAccountedOutcomeNotAnOpenAction() throws Exception {
        String rejected = BuildJournal.begin(dir, first, BlockPos.ZERO, "stone");
        BuildJournal.finish(dir, first, rejected, Printer.Verdict.REFUSED, "");
        String wrong = BuildJournal.begin(dir, first, new BlockPos(1, 1, 1), "stone");
        BuildJournal.finish(dir, first, wrong, Printer.Verdict.MISMATCH, "dirt");
        assertTrue(BuildJournal.unresolved(dir, first).isEmpty());
    }

    @Test void otherRevisionCannotClearOrBlockThisRevision() throws Exception {
        String old = BuildJournal.begin(dir, first, BlockPos.ZERO, "stone");
        String current = BuildJournal.begin(dir, second, new BlockPos(9, 9, 9), "glass");
        assertEquals("0,0,0", BuildJournal.unresolved(dir, first).get(old));
        assertEquals("9,9,9", BuildJournal.unresolved(dir, second).get(current));
        assertEquals("0,0,0", BuildJournal.unresolvedInContext(dir, second).get(old),
            "a rebase cannot make an unknown physical edit disappear");
    }

    @Test void corruptedOrTruncatedJournalFailsClosed() throws Exception {
        Files.writeString(BuildJournal.file(dir), "{\"event\":\"started\"");
        assertTrue(BuildJournal.unresolved(dir, first).containsKey("journal-corrupt"));
    }
    @Test void transferIsNotResolvedByPlacementRulesOrByARevisionChange() throws Exception {
        String transfer = BuildJournal.beginTransfer(dir, first, new BlockPos(12, 64, 3), "stone", 64);
        assertEquals("12,64,3", BuildJournal.unresolved(dir, first).get(transfer));
        assertEquals("12,64,3", BuildJournal.unresolvedInContext(dir, second).get(transfer));
        BuildJournal.finishTransfer(dir, first, transfer, "NO_CHANGE", 0);
        assertTrue(BuildJournal.unresolvedInContext(dir, second).isEmpty());
    }
}
