package dev.jack.chunkscan;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import java.nio.file.Files;
import java.nio.file.Path;
import static org.junit.jupiter.api.Assertions.*;

class ResumeBindingTest {
    @TempDir Path dir;

    ResumeBinding capture() throws Exception {
        return ResumeBinding.capture(dir, "Deck", "server:example", "minecraft:overworld");
    }

    @Test void changedBytesAreDetectedEvenWithSameSizeAndTimestamp() throws Exception {
        Path source = dir.resolve("Deck.work.json");
        Files.writeString(source, "first");
        var time = Files.getLastModifiedTime(source);
        var saved = capture();
        assertNull(saved.mismatch(capture()));
        Files.writeString(source, "other");
        Files.setLastModifiedTime(source, time);
        assertNotNull(saved.mismatch(capture()));
    }

    @Test void registrationAndSiteChangesInvalidateResume() throws Exception {
        Files.writeString(dir.resolve("Deck.litematic"), "fixture");
        assertThrows(java.io.IOException.class, this::capture);
        Files.writeString(dir.resolve("Deck.scan.json"), "origin one");
        var saved = capture();
        Files.writeString(dir.resolve("Deck.scan.json"), "origin two");
        assertNotNull(saved.mismatch(capture()));
        saved = capture();
        Files.writeString(dir.resolve("islands.json"), "new site policy");
        assertNotNull(saved.mismatch(capture()));
    }

    @Test void worldAndDimensionAreIndependentOfCoordinates() throws Exception {
        Files.writeString(dir.resolve("Deck.work.json"), "fixture");
        var saved = capture();
        assertEquals("server/world changed", saved.mismatch(ResumeBinding.capture(dir,
            "Deck", "server:elsewhere", "minecraft:overworld")));
        assertEquals("dimension changed", saved.mismatch(ResumeBinding.capture(dir,
            "Deck", "server:example", "minecraft:the_nether")));
    }

    @Test void bindingSurvivesAtomicSessionReplacementAndLegacyRemainsUnbound() throws Exception {
        Files.writeString(dir.resolve("Deck.work.json"), "fixture");
        var binding = capture();
        Session.save(dir, new Session.State("Deck", true, false, 0.4, binding));
        assertEquals(binding, Session.load(dir).binding());
        Session.save(dir, new Session.State("Deck", false, true, 0.5, binding));
        assertFalse(Session.load(dir).autofly());
        try (var files = Files.list(dir)) {
            assertFalse(files.anyMatch(p -> p.getFileName().toString().endsWith(".tmp")));
        }
        Files.writeString(Session.file(dir), "{\"design\":\"Deck\",\"autofly\":true}");
        assertNull(Session.load(dir).binding());
    }
}
