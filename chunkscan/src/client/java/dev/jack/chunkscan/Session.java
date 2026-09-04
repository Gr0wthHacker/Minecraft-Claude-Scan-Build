package dev.jack.chunkscan;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

/**
 * What the loop was doing, so a disconnect does not throw it away.
 *
 * <p>Everything the build loop knows lives in static fields — which design is being followed, how
 * fast to fly, whether to carry on to the next design. That is fine until the connection drops at
 * three in the morning, and then a loop whose entire purpose is running unattended has quietly
 * stopped and will not start again until someone types.
 *
 * <p>Intent plus a world/input binding in JSON beside the schematics. This is not the whole state: the
 * abandoned-station set, the cooling-off chests and the session counters are all judgements about a
 * world that has moved on while you were away, and restoring them would carry a stale opinion into
 * a fresh look. What is restored is the INTENT, only after matching the saved binding.
 *
 * <p><b>It resumes movement automation by itself</b>, which is a real thing to do to somebody's
 * account and is therefore announced loudly, held off until the world has loaded, and switched off
 * with one word. The alternative — restore the design but not the flying — restores the half that
 * does nothing on its own.
 */
final class Session {
	/** Ticks after joining before anything moves. Routing a half-loaded world flies you into it. */
	static final int GRACE_TICKS = 100;

	private Session() {}

	static Path file(Path schematicsDir) {
		return schematicsDir.resolve("session.json");
	}

	record State(String design, boolean autofly, boolean all, double speed, ResumeBinding binding) {
        State(String design, boolean autofly, boolean all, double speed) {
            this(design, autofly, all, speed, null);
        }
    }

	static void save(Path schematicsDir, State s) {
		try {
			JsonObject o = new JsonObject();
			if (s.design() != null) o.addProperty("design", s.design());
			o.addProperty("autofly", s.autofly());
			o.addProperty("all", s.all());
			o.addProperty("speed", s.speed());
			if (s.binding() != null) {
                JsonObject binding = new JsonObject();
                binding.addProperty("world", s.binding().world());
                binding.addProperty("dimension", s.binding().dimension());
                binding.addProperty("inputs", s.binding().inputs());
                o.add("binding", binding);
            }
            Path temporary = Files.createTempFile(schematicsDir, ".session-", ".tmp");
            try {
                Files.writeString(temporary, o.toString(), StandardCharsets.UTF_8);
                try {
                    Files.move(temporary, file(schematicsDir), java.nio.file.StandardCopyOption.ATOMIC_MOVE,
                        java.nio.file.StandardCopyOption.REPLACE_EXISTING);
                } catch (java.nio.file.AtomicMoveNotSupportedException unsupported) {
                    Files.move(temporary, file(schematicsDir), java.nio.file.StandardCopyOption.REPLACE_EXISTING);
                }
            } finally { Files.deleteIfExists(temporary); }
		} catch (IOException e) {
			// A loop that cannot write its notes is still a working loop. Never fail the build for
			// the bookkeeping about the build.
		}
	}

	static State load(Path schematicsDir) {
		try {
			Path f = file(schematicsDir);
			if (!Files.exists(f)) return null;
			JsonObject o = JsonParser.parseString(
				Files.readString(f, StandardCharsets.UTF_8)).getAsJsonObject();
			ResumeBinding binding = null;
            if (o.has("binding")) {
                JsonObject b = o.getAsJsonObject("binding");
                binding = new ResumeBinding(b.get("world").getAsString(),
                    b.get("dimension").getAsString(), b.get("inputs").getAsString());
            }
            return new State(o.has("design") ? o.get("design").getAsString() : null,
				o.has("autofly") && o.get("autofly").getAsBoolean(),
				o.has("all") && o.get("all").getAsBoolean(),
				o.has("speed") ? o.get("speed").getAsDouble() : Autopilot.SPEED, binding);
		} catch (Exception e) {
			return null;
		}
	}

	static void clear(Path schematicsDir) {
		try {
			Files.deleteIfExists(file(schematicsDir));
		} catch (IOException ignored) {
		}
	}
}
