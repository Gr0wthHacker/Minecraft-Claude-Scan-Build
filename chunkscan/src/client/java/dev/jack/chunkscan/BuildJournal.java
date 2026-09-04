package dev.jack.chunkscan;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.Level;

import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.nio.channels.FileChannel;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;

/** Append-only evidence for actions whose server outcome can outlive the client. */
final class BuildJournal {
    private static final String FILE = ".cscan-build-journal.jsonl";
    private BuildJournal() {}

    static Path file(Path sourceDirectory) { return sourceDirectory.resolve(FILE); }

    static String begin(Path sourceDirectory, ResumeBinding binding, BlockPos pos, String wanted) throws IOException {
        return begin(sourceDirectory, binding, "placement", pos, wanted, 0);
    }

	static String beginTransfer(Path sourceDirectory, ResumeBinding binding, BlockPos chest, String item, int expected)
		throws IOException {
		return begin(sourceDirectory, binding, "withdrawal", chest, item, expected);
	}

	private static String begin(Path sourceDirectory, ResumeBinding binding, String kind, BlockPos pos, String wanted,
		int expected) throws IOException {
        String id = UUID.randomUUID().toString();
        JsonObject event = base("started", id, binding);
		event.addProperty("kind", kind);
        event.addProperty("x", pos.getX()); event.addProperty("y", pos.getY()); event.addProperty("z", pos.getZ());
        event.addProperty("wanted", wanted);
		if (expected > 0) event.addProperty("expected", expected);
        append(file(sourceDirectory), event);
        return id;
    }

    static void finish(Path sourceDirectory, ResumeBinding binding, String id, Printer.Verdict verdict, String observed)
        throws IOException {
        if (id == null) return;
        JsonObject event = base("finished", id, binding);
        event.addProperty("verdict", verdict.name());
        event.addProperty("observed", observed == null ? "" : observed);
        append(file(sourceDirectory), event);
    }

	static void finishTransfer(Path sourceDirectory, ResumeBinding binding, String id, String result, int moved)
		throws IOException {
		if (id == null) return;
		JsonObject event = base("finished", id, binding);
		event.addProperty("result", result);
		event.addProperty("moved", moved);
		append(file(sourceDirectory), event);
	}

    /** A damaged journal is unknown work, never permission to resume. */
    static Map<String, String> unresolved(Path sourceDirectory, ResumeBinding binding) {
		return unresolved(sourceDirectory, binding, true);
	}

	/** Unknown physical edits block every job in their world/dimension, including a rebase. */
	static Map<String, String> unresolvedInContext(Path sourceDirectory, ResumeBinding binding) {
		return unresolved(sourceDirectory, binding, false);
	}

	private static Map<String, String> unresolved(Path sourceDirectory, ResumeBinding binding, boolean sameInputs) {
        Map<String, String> active = new LinkedHashMap<>();
        Path file = file(sourceDirectory);
        if (!Files.exists(file)) return active;
        try {
            for (String line : Files.readAllLines(file, StandardCharsets.UTF_8)) {
                if (line.isBlank()) continue;
                JsonObject event = JsonParser.parseString(line).getAsJsonObject();
				if (!sameContext(event, binding) || (sameInputs && !binding.inputs().equals(event.get("inputs").getAsString()))) continue;
                String id = event.get("id").getAsString();
                if ("started".equals(event.get("event").getAsString())) {
                    active.put(id, event.get("x").getAsInt()+","+event.get("y").getAsInt()+","+event.get("z").getAsInt());
                } else if ("finished".equals(event.get("event").getAsString())) active.remove(id);
                else throw new IOException("unknown journal event");
            }
        } catch (Exception bad) {
            active.put("journal-corrupt", "journal cannot be trusted: " + bad.getClass().getSimpleName());
        }
        return active;
    }

    /** Resolve only cells visible in the newly joined world; invisible cells stay unknown. */
    static void reconcile(Path sourceDirectory, ResumeBinding binding, Level level) {
        Map<String, Pending> pending = new LinkedHashMap<>();
        try {
            Path file = file(sourceDirectory);
            if (!Files.exists(file)) return;
            for (String line : Files.readAllLines(file, StandardCharsets.UTF_8)) {
                if (line.isBlank()) continue;
                JsonObject event = JsonParser.parseString(line).getAsJsonObject();
				if (!sameContext(event, binding)) continue;
                String id = event.get("id").getAsString();
                if ("started".equals(event.get("event").getAsString())) {
                    pending.put(id, new Pending(event.has("kind") ? event.get("kind").getAsString() : "placement",
						new BlockPos(event.get("x").getAsInt(), event.get("y").getAsInt(),
                        event.get("z").getAsInt()), event.get("wanted").getAsString(),
						new ResumeBinding(event.get("world").getAsString(), event.get("dimension").getAsString(),
							event.get("inputs").getAsString())));
                } else if ("finished".equals(event.get("event").getAsString())) pending.remove(id);
                else throw new IOException("unknown journal event");
            }
            for (var entry : pending.entrySet()) {
                Pending action = entry.getValue();
				if (!"placement".equals(action.kind())) continue;
                if (!level.isLoaded(action.pos())) continue;
                var state = level.getBlockState(action.pos());
                Printer.Verdict verdict = state.isAir() ? Printer.Verdict.STILL_AIR
                    : Work.matches(state, action.wanted()) ? Printer.Verdict.PLACED : Printer.Verdict.MISMATCH;
                String observed = state.isAir() ? "air"
                    : net.minecraft.core.registries.BuiltInRegistries.BLOCK.getKey(state.getBlock()).getPath();
                finish(sourceDirectory, action.binding(), entry.getKey(), verdict, observed);
            }
        } catch (Exception ignored) {
            // Keep the original start event. A bad journal or a transient read is never resolved.
        }
    }

    private record Pending(String kind, BlockPos pos, String wanted, ResumeBinding binding) {}

    private static JsonObject base(String event, String id, ResumeBinding binding) {
        JsonObject out = new JsonObject();
        out.addProperty("event", event); out.addProperty("id", id);
        out.addProperty("inputs", binding.inputs());
        out.addProperty("world", binding.world()); out.addProperty("dimension", binding.dimension());
        return out;
    }

    private static boolean sameBinding(JsonObject event, ResumeBinding binding) {
		return sameContext(event, binding) && event.has("inputs")
			&& binding.inputs().equals(event.get("inputs").getAsString());
    }

	private static boolean sameContext(JsonObject event, ResumeBinding binding) {
		return event.has("world") && event.has("dimension")
			&& binding.world().equals(event.get("world").getAsString())
			&& binding.dimension().equals(event.get("dimension").getAsString());
	}

    private static void append(Path file, JsonObject event) throws IOException {
		byte[] bytes = (event.toString() + System.lineSeparator()).getBytes(StandardCharsets.UTF_8);
		try (FileChannel channel = FileChannel.open(file, StandardOpenOption.CREATE,
			StandardOpenOption.WRITE, StandardOpenOption.APPEND)) {
			channel.write(ByteBuffer.wrap(bytes));
			channel.force(true);
		}
    }
}
