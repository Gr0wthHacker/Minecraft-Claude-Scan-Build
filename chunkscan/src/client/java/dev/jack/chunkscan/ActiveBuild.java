package dev.jack.chunkscan;

import net.minecraft.client.Minecraft;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;

/** One immutable input revision for the currently followed design. Storage observations stay live. */
final class ActiveBuild {
    record Snapshot(Path sourceDirectory, Path inputDirectory, String design, ResumeBinding binding) {}
    private static Snapshot current;
    private ActiveBuild() {}

    static Snapshot prepare(Path dir, String design, ResumeBinding expected) throws IOException {
        Path sourceDir = dir.toAbsolutePath().normalize();
		Designs.requireAutonomousApproval(sourceDir, design);
        ResumeBinding before = ResumeBinding.capture(sourceDir, design, expected.world(), expected.dimension());
        String mismatch = expected.mismatch(before);
        if (mismatch != null) throw new IOException(mismatch);
		var unresolved = BuildJournal.unresolvedInContext(sourceDir, expected);
		if (!unresolved.isEmpty()) throw new IOException("unreconciled action at "
			+ unresolved.values().iterator().next() + "; inspect the world before resuming");
        Path snapshots = sourceDir.resolve(".cscan-build-inputs");
        Files.createDirectories(snapshots);
        Path copy = Files.createTempDirectory(snapshots, "revision-");
        Path source = Files.exists(sourceDir.resolve(design + ".litematic"))
            ? sourceDir.resolve(design + ".litematic") : Work.file(sourceDir, design);
        Path[] inputs = { source, sourceDir.resolve(design + ".scan.json"), sourceDir.resolve(Islands.FILE) };
        boolean accepted = false;
        try {
            for (Path input : inputs) if (Files.exists(input))
                Files.copy(input, copy.resolve(input.getFileName()));
            ResumeBinding copied = ResumeBinding.capture(copy, design, expected.world(), expected.dimension());
            ResumeBinding after = ResumeBinding.capture(sourceDir, design, expected.world(), expected.dimension());
            if (before.mismatch(copied) != null || before.mismatch(after) != null)
                throw new IOException("build inputs changed while preparing the revision; start again after generation finishes");
            // Decode the private copy before publishing it; no actuator may discover corrupt input later.
			var cells = Work.load(copy, design);
            if (Files.exists(copy.resolve(design + ".litematic"))) Designs.load(copy, design);
			ActionRecipe.require(cells);
            var manifest = new com.google.gson.JsonObject();
            manifest.addProperty("design", design);
            manifest.addProperty("source_directory", sourceDir.toString());
            manifest.addProperty("world", copied.world());
            manifest.addProperty("dimension", copied.dimension());
            manifest.addProperty("inputs", copied.inputs());
            Files.writeString(copy.resolve("revision.json"), manifest.toString());
            accepted = true;
            return new Snapshot(sourceDir, copy, design, copied);
        } finally {
            if (!accepted) {
                Files.deleteIfExists(copy.resolve("revision.json"));
                for (Path input : inputs) Files.deleteIfExists(copy.resolve(input.getFileName()));
                Files.deleteIfExists(copy);
            }
        }
    }

    static void start(Minecraft mc, String design, ResumeBinding expected) throws IOException {
        Path dir = ScanRunner.schematicsDir(mc);
        if (expected == null) expected = ResumeBinding.capture(mc, dir, design);
		if (mc.level != null) BuildJournal.reconcile(dir, expected, mc.level);
        Snapshot prepared = prepare(dir, design, expected);
        current = prepared;
    }

    static Path inputs(Path dir, String design) {
        return matches(dir, design) ? current.inputDirectory() : dir;
    }

    static Path siteInputs(Path dir) {
        return current != null && current.sourceDirectory().equals(dir.toAbsolutePath().normalize())
            ? current.inputDirectory() : dir;
    }

    static ResumeBinding binding(Path dir, String design) throws IOException {
        if (!matches(dir, design)) throw new IOException("active build revision is missing");
        return current.binding();
    }

    static Snapshot current(Path dir, String design) {
        return matches(dir, design) ? current : null;
    }

    private static boolean matches(Path dir, String design) {
        return current != null && current.design().equals(design)
            && current.sourceDirectory().equals(dir.toAbsolutePath().normalize());
    }

    static void activate(Snapshot snapshot) { current = snapshot; }
    static void clear() { current = null; }
}
