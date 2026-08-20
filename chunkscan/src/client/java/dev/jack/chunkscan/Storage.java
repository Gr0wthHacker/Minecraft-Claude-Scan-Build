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
	/**
	 * Block names that actually hold items. Kept here rather than in the watcher so the guard that
	 * stops a bad entry being written and the sweep that removes one already written cannot drift.
	 */
	private static final String[] CONTAINERS = {
		"chest", "trapped_chest", "barrel", "shulker_box", "hopper", "dispenser", "dropper",
		"furnace", "blast_furnace", "smoker", "brewing_stand", "chiseled_bookshelf", "decorated_pot",
		"crafter", "campfire", "lectern", "beacon", "cartography_table", "loom", "smithing_table",
		"grindstone", "stonecutter", "enchanting_table", "anvil", "crafting_table",
	};
	/** ...of which only these actually STORE things. The rest open a screen and hold nothing. */
	private static final String[] STORES = {
		"chest", "trapped_chest", "barrel", "shulker_box", "hopper", "dispenser", "dropper",
		"furnace", "blast_furnace", "smoker", "brewing_stand", "chiseled_bookshelf", "decorated_pot",
		"crafter",
	};

	static boolean isContainer(String block) {
		String n = block == null ? "" : block.substring(block.indexOf(':') + 1);
		for (String k : CONTAINERS) if (n.contains(k)) return true;
		return false;
	}

	static boolean stores(String block) {
		String n = block == null ? "" : block.substring(block.indexOf(':') + 1);
		for (String k : STORES) if (n.contains(k)) return true;
		return false;
	}

	/**
	 * Drop entries that were filed against something that is not a container. Returns how many went.
	 *
	 * <p>141 of 269 entries were like this — signs, stone bricks, slabs, moss — because the watcher
	 * remembered every right-click and then attributed the next screen to it. They are removed rather
	 * than repaired: the position is the one thing that was wrong, so there is nothing to repair to.
	 * Reopening the real container re-indexes it in one click.
	 */
	static int prune(Path schematicsDir) throws IOException {
		Map<String, Container> all = load(schematicsDir);
		int before = all.size();
		all.values().removeIf(c -> !stores(c.block));
		if (all.size() != before) save(schematicsDir, all);
		return before - all.size();
	}

	static final class Container {
		int id;
		int x, y, z;
		String dimension = "";
		String block = "";
		String label = "";          // set with /cscan label
		String zone = "";           // nearest marker at capture time
		String updated = "";
		int slots;                  // container size, so "how full is it" is answerable
		int used;                   // slots holding something
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

		/** Percent of slots in use, or -1 when the container was indexed before this was recorded. */
		int fullness() {
			return slots <= 0 ? -1 : Math.round(100f * used / slots);
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
