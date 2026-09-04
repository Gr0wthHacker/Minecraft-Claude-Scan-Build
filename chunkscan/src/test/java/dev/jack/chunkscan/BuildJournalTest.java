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
    @Test void aTransferIsRecordedAcrossRevisionsAndCLOSEDLikeOne() throws Exception {
        String transfer = BuildJournal.beginTransfer(dir, first, new BlockPos(12, 64, 3), "stone", 64);
        assertEquals("12,64,3", BuildJournal.unresolved(dir, first).get(transfer));
        assertEquals("12,64,3", BuildJournal.unresolvedTransfers(dir, second).get(transfer),
            "a withdrawal stopped being visible across a revision change");
        BuildJournal.finishTransfer(dir, first, transfer, "NO_CHANGE", 0);
        assertTrue(BuildJournal.unresolvedTransfers(dir, second).isEmpty());
    }

    @Test void aLooseWITHDRAWALNeverBlocksAResume() throws Exception {
        // The one that bricked a design. A withdrawal moves items between two containers the player
        // already owns, so it cannot corrupt a build - and its outcome cannot be read off the world
        // afterwards, so nothing in this mod could ever settle it. Blocking on one was not caution,
        // it was a build that never started again: the chest turned out to be empty, the withdrawal
        // failed, and every later follow threw "unreconciled action" for good.
        BuildJournal.beginTransfer(dir, first, new BlockPos(12, 64, 3), "stone", 64);
        assertTrue(BuildJournal.unresolvedInContext(dir, second).isEmpty(),
            "an unaccounted withdrawal is refusing to let the design start");
        assertFalse(BuildJournal.unresolvedTransfers(dir, second).isEmpty(),
            "...and it has been forgotten rather than reported");
    }

    @Test void aLoosePLACEMENTStillBlocksAResume() throws Exception {
        // The distinction the whole split rests on: this one leaves a cell of the world in a state
        // the plan does not know about, and it IS settleable - reconcile reads it off the world as
        // soon as that chunk loads.
        BuildJournal.begin(dir, first, new BlockPos(4, 70, 9), "stone_bricks");
        assertFalse(BuildJournal.unresolvedInContext(dir, second).isEmpty(),
            "an unfinished placement is no longer stopping a resume");
    }
}
