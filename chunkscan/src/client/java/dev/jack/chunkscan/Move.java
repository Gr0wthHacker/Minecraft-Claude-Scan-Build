package dev.jack.chunkscan;

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
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * The chest move: 37 general-storage containers scattered over the deck, into the store hall's
 * banked slots, one trip at a time.
 *
 * <p><b>Nothing here moves an item.</b> A client mod cannot, and should not — this plans and points.
 * It answers the two questions that make the job tedious: which chest next, and which slot does its
 * contents belong in. {@link Highlight} draws the source amber and the destination green, so the
 * trip is a walk between two boxes you can see.
 *
 * <p><b>Three sets, all measured rather than declared:</b>
 * <ul>
 *   <li><b>Sources</b> — indexed containers holding something, outside the hall, that do NOT belong
 *       to a machine. A chest within three blocks of a hopper is that hopper's output and moving it
 *       breaks a farm; of 55 containers outside the hall, 18 are like this (16 hoppers, 2
 *       stonecutters) and they stay exactly where they are. Rule 10, from the other side.</li>
 *   <li><b>Slots</b> — containers standing in the world inside the hall's box. NOT the design's
 *       chest cells: the hall is built, so the design emits nothing and knows nothing.</li>
 *   <li><b>Banks</b> — which wall carries which label, read from the hall's sidecar, which records
 *       it whether or not anything was placed this run.</li>
 * </ul>
 *
 * <p><b>A slot the index has never seen is treated as free.</b> The index only knows containers you
 * have opened, so "empty" and "never opened" are the same evidence. Saying "free" is the useful
 * error: you walk there, find it full, and press on to the next one.
 */
final class Move {
	/**
	 * What a chest can BELONG to. A container within reach of one of these is part of a machine and
	 * is never a candidate to move, however general its contents look.
	 *
	 * <p>Deliberately not {@code protect.MECHANISM}: that list contains `chest` itself, so every
	 * source would disqualify its own neighbours.
	 */
	private static final String[] MACHINES = {
		"hopper", "dropper", "dispenser", "piston", "observer", "comparator", "repeater",
		"furnace", "blast_furnace", "smoker", "brewing_stand", "spawner", "rail", "composter",
		"cauldron", "beehive", "bee_nest", "crafter", "stonecutter", "loom", "smithing_table",
		"grindstone", "anvil", "cartography_table", "fletching_table", "enchanting_table",
	};
	/** How close a machine has to be for the chest to be its. The working-room rule, rule 10. */
	static final int MACHINE_REACH = 3;
	static final String HALL = "Store Hall";
	private static final String HL_SOURCE = "move-from";
	private static final String HL_DEST = "move-to";

	/**
	 * The world, as much of it as this needs: what block is at a cell, and whether that cell is
	 * loaded enough to trust. {@code Level} cannot be constructed off a client, and a planner whose
	 * assignment rules are untestable is a planner that quietly sends you to the wrong chest.
	 */
	interface View {
		String name(int x, int y, int z);

		boolean loaded(int x, int y, int z);
	}

	static View of(Level level) {
		BlockPos.MutableBlockPos c = new BlockPos.MutableBlockPos();
		return new View() {
			public String name(int x, int y, int z) {
				return BuiltInRegistries.BLOCK.getKey(level.getBlockState(c.set(x, y, z)).getBlock()).getPath();
			}

			public boolean loaded(int x, int y, int z) {
				return level.isLoaded(c.set(x, y, z));
			}
		};
	}

	record Slot(BlockPos pos, String bank, String label) {}

	record Source(Storage.Container container, String category, int items) {
		BlockPos pos() {
			return container.pos();
		}
	}

	/** One leg of the job: empty `from`, put it in `to`. */
	record Leg(Source from, Slot to, boolean overflow) {}

	record Plan(List<Leg> legs, int stayed, int slotsFree, List<String> unmatchedCategories) {}

	private Move() {}

	// ---------------------------------------------------------------- the hall

	/** The hall's box, tiers and bank labels, from its sidecar. */
	static JsonObject hall(Path schematicsDir) throws IOException {
		Path side = schematicsDir.resolve(HALL + ".scan.json");
		if (!Files.exists(side)) {
			throw new IOException(HALL + ".scan.json missing — generate the store hall first");
		}
		return JsonParser.parseString(Files.readString(side, StandardCharsets.UTF_8)).getAsJsonObject();
	}

	/** Containers standing in the world inside the hall, tagged with the bank they sit on. */
	static List<Slot> slots(View view, JsonObject hall) {
		JsonArray box = hall.getAsJsonArray("box");
		int x1 = Math.min(box.get(0).getAsInt(), box.get(2).getAsInt());
		int x2 = Math.max(box.get(0).getAsInt(), box.get(2).getAsInt());
		int z1 = Math.min(box.get(1).getAsInt(), box.get(3).getAsInt());
		int z2 = Math.max(box.get(1).getAsInt(), box.get(3).getAsInt());
		int fy = hall.get("floor_y").getAsInt();
		int tiers = hall.has("tiers") ? hall.get("tiers").getAsInt() : 4;

		Map<String, String> cellBank = new LinkedHashMap<>();      // "x,z" -> wall
		Map<String, String> bankLabel = new LinkedHashMap<>();
		if (hall.has("banks")) {
			for (var e : hall.getAsJsonObject("banks").entrySet()) {
				JsonObject b = e.getValue().getAsJsonObject();
				bankLabel.put(e.getKey(), b.has("label") ? b.get("label").getAsString() : "");
				for (var c : b.getAsJsonArray("cells")) {
					JsonArray xz = c.getAsJsonArray();
					cellBank.put(xz.get(0).getAsInt() + "," + xz.get(1).getAsInt(), e.getKey());
				}
			}
		}

		List<Slot> out = new ArrayList<>();
		for (int x = x1; x <= x2; x++) {
			for (int z = z1; z <= z2; z++) {
				for (int y = fy + 1; y <= fy + tiers; y++) {
					String n = view.name(x, y, z);
					if (!Storage.stores(n)) continue;
					String bank = cellBank.getOrDefault(x + "," + z, "");
					out.add(new Slot(new BlockPos(x, y, z), bank, bankLabel.getOrDefault(bank, "")));
				}
			}
		}
		return out;
	}

	// ---------------------------------------------------------------- the sources

	static boolean servesAMachine(View view, BlockPos at) {
		for (int dx = -MACHINE_REACH; dx <= MACHINE_REACH; dx++) {
			for (int dy = -MACHINE_REACH; dy <= MACHINE_REACH; dy++) {
				for (int dz = -MACHINE_REACH; dz <= MACHINE_REACH; dz++) {
					String n = view.name(at.getX() + dx, at.getY() + dy, at.getZ() + dz);
					for (String k : MACHINES) if (n.contains(k)) return true;
				}
			}
		}
		return false;
	}

	/** The category whose patterns match the most ITEMS in this container. */
	static String categoryOf(Map<String, Integer> items) {
		Map<String, Integer> score = new LinkedHashMap<>();
		for (var e : items.entrySet()) {
			String c = Rules.categoryOf(e.getKey());
			if (c == null) continue;
			score.merge(c, e.getValue(), Integer::sum);
		}
		return score.entrySet().stream().max(Map.Entry.comparingByValue()).map(Map.Entry::getKey).orElse("");
	}

	// ---------------------------------------------------------------- the plan

	static Plan plan(View view, Path schematicsDir, BlockPos from) throws IOException {
		JsonObject hall = hall(schematicsDir);
		Set<String> done = doneSet(schematicsDir);
		return plan(view, hall, Storage.load(schematicsDir), done, from);
	}

	/** The assignment itself, with every input supplied — the part worth testing. */
	static Plan plan(View view, JsonObject hall, Map<String, Storage.Container> index,
	                 Set<String> done, BlockPos from) {
		JsonArray box2 = hall.getAsJsonArray("box");
		int x1 = Math.min(box2.get(0).getAsInt(), box2.get(2).getAsInt());
		int x2 = Math.max(box2.get(0).getAsInt(), box2.get(2).getAsInt());
		int z1 = Math.min(box2.get(1).getAsInt(), box2.get(3).getAsInt());
		int z2 = Math.max(box2.get(1).getAsInt(), box2.get(3).getAsInt());

		List<Source> sources = new ArrayList<>();
		int stayed = 0;
		for (Storage.Container c : index.values()) {
			if (!Storage.stores(c.block)) continue;
			if (c.items.isEmpty()) continue;                        // already emptied
			if (done.contains(c.key())) continue;
			boolean inHall = c.x >= x1 && c.x <= x2 && c.z >= z1 && c.z <= z2;
			if (inHall) continue;
			if (!view.loaded(c.x, c.y, c.z)) continue;              // cannot judge what is not loaded
			if (servesAMachine(view, c.pos())) {
				stayed++;
				continue;
			}
			int n = c.items.values().stream().mapToInt(Integer::intValue).sum();
			sources.add(new Source(c, categoryOf(c.items), n));
		}

		// Free slots: standing in the world, and not something the index says already holds items.
		Set<String> occupied = new HashSet<>();
		for (Storage.Container c : index.values()) {
			if (!c.items.isEmpty()) occupied.add(c.key());
		}
		List<Slot> free = new ArrayList<>();
		for (Slot s : slots(view, hall)) {
			if (!occupied.contains(s.pos().getX() + "," + s.pos().getY() + "," + s.pos().getZ())) free.add(s);
		}

		// Nearest first: you clear the area you are standing in rather than criss-crossing the deck.
		sources.sort(Comparator.comparingDouble(s -> s.pos().distSqr(from)));

		List<Leg> legs = new ArrayList<>();
		List<String> unmatched = new ArrayList<>();
		Set<BlockPos> taken = new HashSet<>();
		for (Source s : sources) {
			Slot pick = null;
			for (Slot slot : free) {                        // the right bank first
				if (taken.contains(slot.pos())) continue;
				if (!slot.label().isEmpty() && slot.label().equals(s.category())) {
					pick = slot;
					break;
				}
			}
			boolean overflow = false;
			if (pick == null) {                             // ...then anywhere at all, and say so
				for (Slot slot : free) {
					if (taken.contains(slot.pos())) continue;
					pick = slot;
					overflow = true;
					break;
				}
				if (pick != null && !s.category().isEmpty() && !unmatched.contains(s.category())) {
					unmatched.add(s.category());
				}
			}
			if (pick == null) break;                        // hall is full; the rest is reported
			taken.add(pick.pos());
			legs.add(new Leg(s, pick, overflow));
		}
		return new Plan(legs, stayed, free.size(), unmatched);
	}

	// ---------------------------------------------------------------- progress

	static Path progressFile(Path schematicsDir) {
		return schematicsDir.resolve("move.json");
	}

	static Set<String> doneSet(Path schematicsDir) throws IOException {
		Set<String> out = new HashSet<>();
		Path f = progressFile(schematicsDir);
		if (!Files.exists(f)) return out;
		JsonObject root = JsonParser.parseString(Files.readString(f, StandardCharsets.UTF_8)).getAsJsonObject();
		if (!root.has("done")) return out;
		for (var e : root.getAsJsonArray("done")) out.add(e.getAsString());
		return out;
	}

	static void markDone(Path schematicsDir, String key) throws IOException {
		Set<String> all = doneSet(schematicsDir);
		all.add(key);
		JsonObject root = new JsonObject();
		JsonArray arr = new JsonArray();
		all.stream().sorted().forEach(arr::add);
		root.add("done", arr);
		Files.writeString(progressFile(schematicsDir),
			new com.google.gson.GsonBuilder().setPrettyPrinting().create().toJson(root), StandardCharsets.UTF_8);
	}

	static void reset(Path schematicsDir) throws IOException {
		Files.deleteIfExists(progressFile(schematicsDir));
	}

	// ---------------------------------------------------------------- drawing

	static void draw(Leg leg) {
		Highlight.show(HL_SOURCE, List.of(leg.from().pos()), 0xFFC000, 600);
		Highlight.show(HL_DEST, List.of(leg.to().pos()), 0x40FF60, 600);
	}

	static void clearDraw() {
		Highlight.clear(HL_SOURCE);
		Highlight.clear(HL_DEST);
	}

	/** The three or four commonest things in a container, for one line of chat. */
	static String contents(Storage.Container c) {
		return c.items.entrySet().stream()
			.sorted((l, r) -> Integer.compare(r.getValue(), l.getValue()))
			.limit(3)
			.map(e -> e.getValue() + "x " + Rules.shortName(e.getKey()))
			.reduce((l, r) -> l + ", " + r).orElse("empty");
	}
}
