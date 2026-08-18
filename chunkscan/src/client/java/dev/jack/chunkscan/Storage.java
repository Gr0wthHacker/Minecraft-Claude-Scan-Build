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
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * schematics/storage.json — an index of every container you have opened.
 *
 * Each container keeps a short stable NUMBER (#37) keyed to its position, plus an optional label you set
 * and the zone it falls in (nearest marker). `/cscan find <item>` then answers "which container", with
 * number, zone, coordinates, distance and direction — instead of opening a hundred chests.
 */
final class Storage {
	static final class Container {
		int id;
		int x, y, z;
		String dimension = "";
		String block = "";
		String label = "";          // set with /cscan label
		String zone = "";           // nearest marker at capture time
		String updated = "";
		final Map<String, Integer> items = new LinkedHashMap<>();

		String key() {
			return x + "," + y + "," + z;
		}

		BlockPos pos() {
			return new BlockPos(x, y, z);
		}

		int total() {
			return items.values().stream().mapToInt(Integer::intValue).sum();
		}

		String describe() {
			String name = !label.isEmpty() ? label : (!zone.isEmpty() ? zone : block);
			return "#" + id + " " + name;
		}
	}

	private Storage() {}

	static Path file(Path schematicsDir) {
		return schematicsDir.resolve("storage.json");
	}

	static Map<String, Container> load(Path schematicsDir) throws IOException {
		Map<String, Container> out = new LinkedHashMap<>();
		Path f = file(schematicsDir);
		if (!Files.exists(f)) return out;
		JsonObject root = JsonParser.parseString(Files.readString(f, StandardCharsets.UTF_8)).getAsJsonObject();
		for (var e : root.getAsJsonArray("containers")) {
			JsonObject o = e.getAsJsonObject();
			Container c = new Container();
			c.id = o.get("id").getAsInt();
			c.x = o.get("x").getAsInt();
			c.y = o.get("y").getAsInt();
			c.z = o.get("z").getAsInt();
			c.dimension = str(o, "dimension");
			c.block = str(o, "block");
			c.label = str(o, "label");
			c.zone = str(o, "zone");
			c.updated = str(o, "updated");
			JsonObject items = o.getAsJsonObject("items");
			if (items != null) {
				for (String k : items.keySet()) c.items.put(k, items.get(k).getAsInt());
			}
			out.put(c.key(), c);
		}
		return out;
	}

	private static String str(JsonObject o, String k) {
		return o.has(k) && !o.get(k).isJsonNull() ? o.get(k).getAsString() : "";
	}

	static void save(Path schematicsDir, Map<String, Container> all) throws IOException {
		JsonArray arr = new JsonArray();
		for (Container c : all.values()) {
			JsonObject o = new JsonObject();
			o.addProperty("id", c.id);
			o.addProperty("x", c.x);
			o.addProperty("y", c.y);
			o.addProperty("z", c.z);
			o.addProperty("dimension", c.dimension);
			o.addProperty("block", c.block);
			o.addProperty("label", c.label);
			o.addProperty("zone", c.zone);
			o.addProperty("updated", c.updated);
			JsonObject items = new JsonObject();
			c.items.entrySet().stream()
				.sorted((a, b) -> Integer.compare(b.getValue(), a.getValue()))
				.forEach(e -> items.addProperty(e.getKey(), e.getValue()));
			o.add("items", items);
			arr.add(o);
		}
		JsonObject root = new JsonObject();
		root.add("containers", arr);
		Files.createDirectories(schematicsDir);
		Files.writeString(file(schematicsDir), new GsonBuilder().setPrettyPrinting().create().toJson(root), StandardCharsets.UTF_8);
	}

	/** Insert or update the container at `c.pos()`, keeping its existing number and label. */
	static Container upsert(Map<String, Container> all, Container c) {
		Container old = all.get(c.key());
		if (old != null) {
			c.id = old.id;
			if (c.label.isEmpty()) c.label = old.label;
		} else {
			c.id = all.values().stream().mapToInt(v -> v.id).max().orElse(0) + 1;
		}
		c.updated = Instant.now().toString();
		all.put(c.key(), c);
		return c;
	}

	record Hit(Container container, String item, int count, double distance) {}

	/** Containers holding an item whose id or label matches `query` (substring, case-insensitive). */
	static List<Hit> find(Map<String, Container> all, String query, BlockPos from) {
		String q = query.toLowerCase();
		List<Hit> hits = new ArrayList<>();
		for (Container c : all.values()) {
			for (var e : c.items.entrySet()) {
				if (e.getKey().toLowerCase().contains(q)) {
					hits.add(new Hit(c, e.getKey(), e.getValue(), Math.sqrt(c.pos().distSqr(from))));
				}
			}
		}
		hits.sort((a, b) -> Double.compare(a.distance(), b.distance()));
		return hits;
	}

	/** Compass-ish direction from `from` to `to`, for "walk that way". */
	static String direction(BlockPos from, BlockPos to) {
		int dx = to.getX() - from.getX(), dz = to.getZ() - from.getZ();
		StringBuilder sb = new StringBuilder();
		if (Math.abs(dz) > Math.abs(dx) / 3) sb.append(dz < 0 ? "N" : "S");
		if (Math.abs(dx) > Math.abs(dz) / 3) sb.append(dx > 0 ? "E" : "W");
		int dy = to.getY() - from.getY();
		if (Math.abs(dy) >= 4) sb.append(dy > 0 ? " up" : " down");
		return sb.isEmpty() ? "here" : sb.toString();
	}
}
