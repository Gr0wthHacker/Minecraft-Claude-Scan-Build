package dev.jack.chunkscan;

import com.google.gson.GsonBuilder;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import net.minecraft.core.BlockPos;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;

/**
 * schematics/markers.json — named world positions you point at in game, so design configs stop being
 * guesswork: `/cscan mark apiary-centre` then read the coordinate on the tooling side.
 */
final class Markers {
	record Marker(String label, int x, int y, int z, String dimension, String created) {
		double distance(BlockPos p) {
			return Math.sqrt(p.distSqr(new BlockPos(x, y, z)));
		}
	}

	private Markers() {}

	static Path file(Path schematicsDir) {
		return schematicsDir.resolve("markers.json");
	}

	static List<Marker> load(Path schematicsDir) throws IOException {
		List<Marker> out = new ArrayList<>();
		Path f = file(schematicsDir);
		if (!Files.exists(f)) return out;
		JsonObject root = JsonParser.parseString(Files.readString(f, StandardCharsets.UTF_8)).getAsJsonObject();
		for (var e : root.getAsJsonArray("markers")) {
			JsonObject o = e.getAsJsonObject();
			out.add(new Marker(o.get("label").getAsString(), o.get("x").getAsInt(), o.get("y").getAsInt(), o.get("z").getAsInt(),
				o.has("dimension") ? o.get("dimension").getAsString() : "", o.has("created") ? o.get("created").getAsString() : ""));
		}
		return out;
	}

	/** Add or replace by label; returns the whole list. */
	static List<Marker> put(Path schematicsDir, String label, BlockPos pos, String dimension) throws IOException {
		List<Marker> all = load(schematicsDir);
		all.removeIf(m -> m.label().equalsIgnoreCase(label));
		all.add(new Marker(label, pos.getX(), pos.getY(), pos.getZ(), dimension, Instant.now().toString()));
		write(schematicsDir, all);
		return all;
	}

	static boolean remove(Path schematicsDir, String label) throws IOException {
		List<Marker> all = load(schematicsDir);
		boolean hit = all.removeIf(m -> m.label().equalsIgnoreCase(label));
		if (hit) write(schematicsDir, all);
		return hit;
	}

	static void write(Path schematicsDir, List<Marker> all) throws IOException {
		JsonArray arr = new JsonArray();
		for (Marker m : all) {
			JsonObject o = new JsonObject();
			o.addProperty("label", m.label());
			o.addProperty("x", m.x());
			o.addProperty("y", m.y());
			o.addProperty("z", m.z());
			o.addProperty("dimension", m.dimension());
			o.addProperty("created", m.created());
			arr.add(o);
		}
		JsonObject root = new JsonObject();
		root.add("markers", arr);
		Files.writeString(file(schematicsDir), new GsonBuilder().setPrettyPrinting().create().toJson(root), StandardCharsets.UTF_8);
	}

	/** Label of the nearest marker within `maxDist`, or null — used to give containers a human zone name. */
	static String nearestLabel(List<Marker> all, BlockPos pos, double maxDist) {
		String best = null;
		double bestD = maxDist;
		for (Marker m : all) {
			double d = m.distance(pos);
			if (d <= bestD) {
				bestD = d;
				best = m.label();
			}
		}
		return best;
	}
}
