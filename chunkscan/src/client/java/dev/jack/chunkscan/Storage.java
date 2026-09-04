package dev.jack.chunkscan;

import com.google.gson.GsonBuilder;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.world.level.Level;

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

	static boolean buildStorage(String block) {
        String n = Rules.shortName(block);
        return n.equals("chest") || n.equals("trapped_chest") || n.equals("barrel")
            || n.equals("shulker_box") || n.endsWith("_shulker_box");
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
		return prune(schematicsDir, null);
	}

	/**
	 * Drop entries that were never containers, and — when a world is given — entries the LOADED
	 * world disproves. Returns how many went.
	 *
	 * <p>Two different wrongs with two different causes. The first is the watcher having filed your
	 * own inventory against whatever block you last clicked; those were never real. The second is a
	 * chest you broke, which was real and is not any more, and which nothing could ever have told
	 * the index about because you cannot open a chest that is gone.
	 *
	 * <p>Removed rather than repaired in both cases: the POSITION is the thing that is wrong, and
	 * there is nothing to repair it to. Reopening the real container re-indexes it in one click.
	 */
	static int prune(Path schematicsDir, Level level) throws IOException {
		Map<String, Container> all = load(schematicsDir);
		int before = all.size();
		all.values().removeIf(c -> !stores(c.block) || !stillThere(level, c));
		if (all.size() != before) save(schematicsDir, all);
		return before - all.size();
	}

	/**
	 * Does this item hold other items? A shulker box does, and it is how this island stores in bulk.
	 */
	static boolean isBox(String item) {
		return item != null && item.contains("shulker_box");
	}

	static final class Container {
		int id;
		int x, y, z;
		String dimension = "";
		String block = "";
		String label = "";          // set with /cscan label
		/**
		 * What is inside the SHULKER BOXES in this container.
		 *
		 * <p>Kept apart from `items` on purpose. The index used to record a chest of six shulker
		 * boxes as "6x white_shulker_box", which is true and useless: the ten thousand stone bricks
		 * inside were invisible to `find`, to the bill of materials and to the build loop, which
		 * would fly past them to a chest with sixty-four loose ones. Bulk storage on this island IS
		 * boxes in chests.
		 *
		 * <p>Not merged, because getting them is a DIFFERENT job — you take the box, set it down and
		 * open it — and a plan that says "64 bricks, 22m NE" when it means "a box you must unpack"
		 * is a plan that lies about the only number that mattered.
		 */
		final java.util.Map<String, Integer> inBoxes = new java.util.LinkedHashMap<>();
		String zone = "";           // nearest marker at capture time
		String updated = "";
		int slots;                  // container size, so "how full is it" is answerable
		int used;                   // slots holding something
		final Map<String, Integer> items = new LinkedHashMap<>();

		String key() {
			String xyz = x + "," + y + "," + z;
            return dimension.isBlank() || dimension.equals("minecraft:overworld") ? xyz : dimension + "|" + xyz;
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
            c.slots = o.has("slots") ? o.get("slots").getAsInt() : 0;
            c.used = o.has("used") ? o.get("used").getAsInt() : 0;
			JsonObject items = o.getAsJsonObject("items");
			if (items != null) {
				for (String k : items.keySet()) c.items.put(k, items.get(k).getAsInt());
			}
			// Absent in every record written before this, which reads correctly as "no boxes known
			// here" — the index is re-written from the screen the next time you open the container.
			JsonObject boxed = o.getAsJsonObject("inBoxes");
			if (boxed != null) {
				for (String k : boxed.keySet()) c.inBoxes.put(k, boxed.get(k).getAsInt());
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
            o.addProperty("slots", c.slots);
            o.addProperty("used", c.used);
			JsonObject items = new JsonObject();
			c.items.entrySet().stream()
				.sorted((a, b) -> Integer.compare(b.getValue(), a.getValue()))
				.forEach(e -> items.addProperty(e.getKey(), e.getValue()));
			o.add("items", items);
			if (!c.inBoxes.isEmpty()) {
				JsonObject boxed = new JsonObject();
				c.inBoxes.entrySet().stream()
					.sorted((a, b) -> Integer.compare(b.getValue(), a.getValue()))
					.forEach(e -> boxed.addProperty(e.getKey(), e.getValue()));
				o.add("inBoxes", boxed);
			}
			arr.add(o);
		}
		JsonObject root = new JsonObject();
		root.add("containers", arr);
		Files.createDirectories(schematicsDir);
		Files.writeString(file(schematicsDir), new GsonBuilder().setPrettyPrinting().create().toJson(root), StandardCharsets.UTF_8);
        forget();
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

	/**
	 * Is this record still true of the world?
	 *
	 * <p><b>THE INDEX HAS NO WAY TO FORGET.</b> It is written when you OPEN a container, and you
	 * cannot open one that has been broken — so every other part of this project regenerates
	 * against the newest capture and this is the one thing that only ever accumulates. Measured
	 * against the 16:33 capture: 179 of 339 indexed containers no longer exist, 63 of those
	 * positions are now air, and the index still claimed 36,088 items inside them.
	 *
	 * <p>That was harmless while `/cscan find` was only ever advice. It stopped being harmless when
	 * `fetch` and `follow` started NAVIGATING to these coordinates.
	 *
	 * <p>UNLOADED IS NOT ABSENT. A chunk you cannot see is not evidence that the chest is gone, and
	 * treating it as such would delete your whole index the first time you ran this from the far
	 * side of the island. Same rule `Work.split` follows.
	 */
	static boolean stillThere(Level level, Container c) {
		BlockPos p = c.pos();
		if (level != null && !c.dimension.isBlank() && !c.dimension.equals(level.dimension().identifier().toString())) return true;
		if (level == null || !level.isLoaded(p)) return stillThere((String) null);
		return stillThere(BuiltInRegistries.BLOCK.getKey(level.getBlockState(p).getBlock()).getPath());
	}

	/**
	 * The decision itself, given what is at the position - or NULL when the chunk is not loaded and
	 * there is nothing to look at.
	 *
	 * <p>Split out so it can be tested: a Level cannot be constructed off a client, and the rule
	 * that unloaded means "leave it alone" is the one worth pinning, because getting it backwards
	 * deletes the whole index the first time you prune from across the island.
	 */
	static boolean stillThere(String blockAtPosition) {
		if (blockAtPosition == null) return true;
		return stores(blockAtPosition);
	}

	/** Containers holding an item whose id or label matches `query` (substring, case-insensitive). */
	static List<Hit> find(Map<String, Container> all, String query, BlockPos from) {
		return find(all, query, from, null);
	}

	/**
	 * As {@link #find}, skipping records the world has since disproved.
	 *
	 * <p>Skipped rather than deleted: this runs on the way to answering a question, and a lookup is
	 * not the place to throw away someone's data. `/cscan prune` is where that decision is made
	 * deliberately.
	 */
	static List<Hit> find(Map<String, Container> all, String query, BlockPos from, Level level) {
		String q = query.toLowerCase();
		List<Hit> hits = new ArrayList<>();
		for (Container c : all.values()) {
			if (level != null && !stillThere(level, c)) continue;
			for (var e : c.items.entrySet()) {
				if (e.getKey().toLowerCase().contains(q)) {
					hits.add(new Hit(c, e.getKey(), e.getValue(), Math.sqrt(c.pos().distSqr(from))));
				}
			}
		}
		hits.sort((a, b) -> Double.compare(a.distance(), b.distance()));
		return hits;
	}

	/**
	 * Containers holding EXACTLY this item.
	 *
	 * <p>{@link #find} is a substring search and should be: `/cscan find wool` is a question about
	 * wool in general. It is the wrong tool for a fetch, because a trip is a navigation instruction
	 * and `stone_bricks` matches `mossy_stone_bricks`, `cracked_stone_bricks` and
	 * `chiseled_stone_bricks`. The loop would fly to the nearest of those, find nothing of what it
	 * asked for, take zero, blacklist a perfectly good chest and try the next one — a whole trip
	 * spent to learn nothing, and it looked exactly like the chest being empty.
	 *
	 * <p>The namespace is optional on both sides, because the index holds `minecraft:stone_bricks`
	 * and every caller here holds a bare block name.
	 */
	static List<Hit> findExact(Map<String, Container> all, String item, BlockPos from) {
		return findExact(all, item, from, false);
	}

	/**
	 * @param inBoxes also count what is inside shulker boxes in the container
	 *
	 * <p>Off by default, and that is the honest setting for a plan: getting at a boxed block is a
	 * different job — take the box, set it down, open it — so a route that promises "500 bricks,
	 * 22m NE" when it means "a box you must unpack" has lied about the thing that mattered. Turned
	 * ON it is how the loop finds this island's actual bulk storage, which is boxes in chests.
	 */
	static List<Hit> findExact(Map<String, Container> all, String item, BlockPos from,
	                           boolean inBoxes) {
		String want = bare(item);
		List<Hit> hits = new ArrayList<>();
		for (Container c : all.values()) {
			int loose = 0, boxed = 0;
			String id = null;
			for (var e : c.items.entrySet()) {
				if (bare(e.getKey()).equals(want) && e.getValue() > 0) {
					loose += e.getValue();
					id = e.getKey();
				}
			}
			if (inBoxes) {
				for (var e : c.inBoxes.entrySet()) {
					if (bare(e.getKey()).equals(want) && e.getValue() > 0) {
						boxed += e.getValue();
						if (id == null) id = e.getKey();
					}
				}
			}
			int total = loose + boxed;
			if (total > 0) hits.add(new Hit(c, id, total, Math.sqrt(c.pos().distSqr(from))));
		}
		hits.sort((a, b) -> Double.compare(a.distance(), b.distance()));
		return hits;
	}

	/** How many of this item are inside boxes in this container. */
	static int boxedCount(Container c, String item) {
		String want = bare(item);
		int n = 0;
		for (var e : c.inBoxes.entrySet()) {
			if (bare(e.getKey()).equals(want)) n += e.getValue();
		}
		return n;
	}

	// ---- the read cache. `load` is a file read and a JSON parse, and the build loop asks for the
	// index every two seconds for as long as it runs. The file only changes when you OPEN a
	// container, and the filesystem already records when that was.
	private static Map<String, Container> cached;
	private static long cachedAt = Long.MIN_VALUE;
	private static Path cachedFrom;

	/**
	 * {@link #load}, but only actually loading when the file has changed.
	 *
	 * <p>Keyed on the modification time rather than on a timer, because a stale index here is not a
	 * cosmetic problem: you open a chest precisely so that the loop can be told about it, and a
	 * thirty-second cache would mean walking to a chest the loop still thinks is empty. An mtime
	 * check is one syscall against a read and a parse.
	 */
	static Map<String, Container> loadCached(Path schematicsDir) throws IOException {
		Path f = file(schematicsDir);
		long stamp = Files.exists(f) ? Files.getLastModifiedTime(f).toMillis() : -1;
		if (cached != null && stamp == cachedAt && schematicsDir.equals(cachedFrom)) return cached;
		// UNMODIFIABLE, and the wrapper is what is cached. Every other caller of `load` owns its
		// copy and two of them edit it — `prune` and the storage report both `removeIf` — so a
		// shared mutable map here is a cache that silently loses containers. Made impossible rather
		// than written down.
		cached = java.util.Collections.unmodifiableMap(load(schematicsDir));
		cachedAt = stamp;
		cachedFrom = schematicsDir;
		return cached;
	}

	/** Drop the cache, for a test or after a write. */
	static void forget() {
		cached = null;
		cachedAt = Long.MIN_VALUE;
		cachedFrom = null;
	}

	/**
	 * The index with the records this world DISPROVES taken out.
	 *
	 * <p>The index only ever grew: it is written when you OPEN a container, and you cannot open one
	 * that has been broken. Measured against a capture it was **179 dead records out of 339**, and
	 * that was harmless while `/cscan find` was advice and stopped being harmless the moment `fetch`
	 * and `follow` started NAVIGATING to those coordinates.
	 *
	 * <p><b>Unloaded is not absent.</b> A chunk you cannot see is not evidence the chest went, so it
	 * stays. This is a filter on the way to answering a question, not a deletion — `/cscan prune` is
	 * where throwing the record away is decided deliberately.
	 */
	static Map<String, Container> live(Map<String, Container> all, Level level) {
		if (level == null) return all;
		Map<String, Container> out = new LinkedHashMap<>();
		for (var e : all.entrySet()) {
			if (stillThere(level, e.getValue())) out.put(e.getKey(), e.getValue());
		}
		return out;
	}

    /** Restocking belongs to the schematic's island, even while travelling from another one. */
    static Map<String, Container> forDesign(Path dir, String name, BlockPos player, Level level) throws IOException {
        BlockPos origin;
        if (Files.exists(ActiveBuild.inputs(dir, name).resolve(name + ".scan.json"))) origin = Designs.load(dir, name).origin();
        else {
            List<Work.Cell> cells = Work.load(dir, name);
            if (cells.isEmpty()) return Map.of();
            origin = cells.getFirst().pos();
        }
        return live(scoped(loadCached(dir), dir, origin, level.dimension().identifier().toString()), level);
    }

    static Map<String, Container> scoped(Map<String, Container> all, Path dir, BlockPos origin, String dimension) {
        Map<String, Container> out = new LinkedHashMap<>();
        Islands.Island island = Islands.at(dir, origin.getX(), origin.getZ());
        for (var e : all.entrySet()) {
            Container c = e.getValue();
            // Legacy records have no dimension: they cannot safely drive automatic withdrawal.
            if (!dimension.equals(c.dimension) || !buildStorage(c.block)) continue;
            if (island != null) {
                if (!island.contains(origin.getX(), origin.getZ()) || !Islands.storageOnSite(dir, island, c.x, c.z)) continue;
            } else if (!Files.exists(ActiveBuild.siteInputs(dir).resolve(Islands.FILE)) && Islands.all(dir).isEmpty() && Plot.known() && !Plot.outside(origin.getX(), origin.getZ())) {
                if (Plot.outside(c.x, c.z)) continue;
            } else continue; // register the island rather than guess which storage is yours
            out.put(e.getKey(), c);
        }
        return out;
    }

	/** An item id without its namespace, lowercased. */
	static String bare(String id) {
		String s = id.toLowerCase();
		int i = s.indexOf(':');
		return i < 0 ? s : s.substring(i + 1);
	}

	/** How many records the loaded world disproves, without changing anything. */
	static int stale(Map<String, Container> all, Level level) {
		int n = 0;
		for (Container c : all.values()) if (!stillThere(level, c)) n++;
		return n;
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
