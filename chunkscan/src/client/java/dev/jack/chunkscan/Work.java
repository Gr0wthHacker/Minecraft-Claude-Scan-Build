package dev.jack.chunkscan;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.Property;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Reads &lt;name&gt;.work.json — a design flattened to world-coordinate cells by mcbuild — and diffs it
 * against the live world.
 *
 * The mod has a Litematica writer but no reader, so the desktop (which already has one) exports the
 * cell list once per generation. Diffing happens here against the world as it is right now, so the
 * answer never goes stale between captures.
 */
final class Work {
	/**
	 * One cell of a design. {@code block} is what mcbuild wrote: either a bare name, or
	 * {@code name[facing=east,half=bottom]} carrying the properties the design MEANT.
	 */
	record Cell(BlockPos pos, String block) {
		/** The block name without its state — what you put in a shulker, and what a tally counts. */
		String item() {
			int b = block.indexOf('[');
			return b < 0 ? block : block.substring(0, b);
		}

		boolean hasState() {
			return block.indexOf('[') >= 0;
		}
	}

	/** A design's cells, split by what the world holds today. */
	/**
	 * A design, diffed against the world.
	 *
	 * <p><b>`unseen` is the load-bearing one for an unattended loop.</b> {@link #split} can only diff
	 * cells in chunks the client has, so everything else is silently absent from all three lists —
	 * and an empty `todo` therefore means "nothing left HERE", not "the design is done". Start
	 * `follow all` at the far end of the island and every design reads complete, one after another,
	 * and the loop congratulates itself and stops. The count of what it could not see is the
	 * difference between finished and out of view.
	 *
	 * @param nearestUnseen a cell in an unloaded chunk to go and look at, or null
	 */
	record Split(String name, List<Cell> todo, List<Cell> wrong, int built, int unseen,
	             BlockPos nearestUnseen, List<BlockPos> dig) {
		int total() { return todo.size() + wrong.size() + built + unseen; }

		/**
		 * Nothing left to place, nothing hiding in a chunk we do not have, AND nothing left to break.
		 *
		 * <p><b>The dig list is work.</b> It was not counted here until it was measured: `Falls` is
		 * 30 blocks to place and 41 cells to break — 58% of the job — and `Island Night` is 22% dig.
		 * A litematic cannot express removal, so "break this" lives in the sidecar and nothing in
		 * the loop ever read it. The loop would place thirty blocks, report the design COMPLETE, and
		 * leave the channel it exists to cut standing in solid rock.
		 *
		 * <p>`/cscan dig` has always been able to SHOW the list. Showing is not the same as knowing:
		 * the number that ends a session has to include it.
		 */
		boolean complete() { return todo.isEmpty() && unseen == 0 && dig.isEmpty(); }

		/**
		 * Everything the LOOP can finish: placements only.
		 *
		 * <p>Kept separate from {@link #complete()} on purpose, and the distinction is load-bearing.
		 * A client mod cannot break a block — the printer places, and digging is Jack with a
		 * pickaxe. So if the loop's own advance condition demanded an empty dig list it would sit on
		 * `Falls` for ever, never able to satisfy the thing it was waiting for, and `follow all`
		 * would never reach the next design. That is the "a thing that does nothing, quietly"
		 * failure this project keeps writing rules about.
		 *
		 * <p>So: the loop advances on THIS, and reports {@link #digLeft()} as it goes. The design is
		 * not finished; the loop's part of it is.
		 */
		boolean placementComplete() { return todo.isEmpty() && unseen == 0; }

		/** Cells still to break, for the report and the highlight. */
		int digLeft() { return dig.size(); }
	}

	private Work() {}

	/**
	 * Where a design's work list lives.
	 *
	 * <p>THE NAME BECOMES A PATH, so it is validated HERE rather than at the fourteen commands that
	 * pass one in. `resolve("../../x")` walks straight out of the schematics folder; the two write
	 * paths were checked when the wand was audited and the read paths never were. One gate at the
	 * point of conversion cannot be forgotten by the next command that wants a design name.
	 */
	static Path file(Path schematicsDir, String name) {
		String bad = ChunkScanClient.badName(name);
		if (bad != null) throw new IllegalArgumentException(bad);
		return schematicsDir.resolve(name + ".work.json");
	}

	static List<Cell> load(Path schematicsDir, String name) throws IOException {
		Path p = file(schematicsDir, name);
		if (!Files.exists(p)) {
			throw new IOException(name + ".work.json missing — regenerate it with: python -m mcbuild work \"" + name + "\"");
		}
		JsonObject root = JsonParser.parseString(Files.readString(p, StandardCharsets.UTF_8)).getAsJsonObject();
		JsonArray arr = root.getAsJsonArray("cells");
		List<Cell> out = new ArrayList<>(arr.size());
		for (var e : arr) {
			JsonArray c = e.getAsJsonArray();
			out.add(new Cell(new BlockPos(c.get(0).getAsInt(), c.get(1).getAsInt(), c.get(2).getAsInt()),
				c.get(3).getAsString()));
		}
		return out;
	}

	/**
	 * Split a design against the world. Cells in chunks that are not loaded are skipped entirely —
	 * reporting "not built" for terrain you cannot see would send you to build something that is
	 * already there.
	 */
	/**
	 * The design's dig cells that are STILL SOLID — what is genuinely left to break.
	 *
	 * <p>Like `todo`, this is remaining work rather than the original list: a cell already broken is
	 * done, and re-reporting it would make a finished dig look permanently outstanding. Cells in
	 * unloaded chunks are skipped for the same reason `split` skips them — claiming a cell needs
	 * breaking when you cannot see it sends you across the island to look at air.
	 */
	static List<BlockPos> digLeft(Level level, Path schematicsDir, String name) {
		List<BlockPos> out = new ArrayList<>();
		try {
			for (BlockPos p : Designs.load(schematicsDir, name).dig()) {
				if (!level.isLoaded(p)) continue;
				if (!level.getBlockState(p).isAir()) out.add(p);
			}
		} catch (Exception ignored) {
			// No sidecar, or not a design: no dig list. `split` still answers about placement.
		}
		return out;
	}

	static Split split(Level level, Path schematicsDir, String name, BlockPos near, int radius) throws IOException {
		List<Cell> todo = new ArrayList<>(), wrong = new ArrayList<>();
		int built = 0;
		long r2 = (long) radius * radius;
		int unseen = 0;
		BlockPos nearestUnseen = null;
		double unseenD = Double.MAX_VALUE;
		for (Cell c : load(schematicsDir, name)) {
			if (radius > 0 && c.pos().distSqr(near) > r2) continue;
			if (!level.isLoaded(c.pos())) {
				// COUNTED, not skipped. See the note on Split: absent and finished look identical
				// from here, and only one of them should end a session.
				unseen++;
				double d = c.pos().distSqr(near);
				if (d < unseenD) {
					unseenD = d;
					nearestUnseen = c.pos();
				}
				continue;
			}
			BlockState st = level.getBlockState(c.pos());
			if (matches(st, c.block())) built++;
			else if (isReplaceable(st)) todo.add(c);
			else wrong.add(c);
		}
		todo.sort((a, b) -> {
			int dy = Integer.compare(a.pos().getY(), b.pos().getY());       // bottom-up: always reachable
			if (dy != 0) return dy;
			return Double.compare(a.pos().distSqr(near), b.pos().distSqr(near));
		});
		// Scoped by the same radius as the placements, so `need`/`next` stay about what is in reach
		// while `bom`/`follow` (radius 0) see the whole design.
		List<BlockPos> dig = new ArrayList<>();
		for (BlockPos d : digLeft(level, schematicsDir, name)) {
			if (radius > 0 && d.distSqr(near) > r2) continue;
			dig.add(d);
		}
		return new Split(name, todo, wrong, built, unseen, nearestUnseen, dig);
	}

	private static boolean isReplaceable(BlockState st) {
		return st.isAir() || st.canBeReplaced();
	}

	/**
	 * A block a design ships ONLY so that breaking it leaves the thing actually wanted. The
	 * lowland's pond is ice because a printer places blocks out of your inventory and water is not
	 * a block; mine the sheet and every cell is a water source, which IS the finished pond.
	 *
	 * <p>DIRECTIONAL on purpose. Ice found where water was wanted is a pond that FROZE, and stays a
	 * deviation. Mirrors {@code coop.BECOMES} on the Python side.
	 */
	static final Map<String, Set<String>> BECOMES = Map.of("ice", Set.of("water"));

	/**
	 * Does the world hold what the design asked for? The design names only the properties it
	 * DECIDED — a stair's facing and half, a slab's type — so anything it did not name is not
	 * compared. Everything else about a block state is the game reacting to the neighbourhood
	 * (a stair's shape, a wall's connections, waterlogged), and flagging those reports a deviation
	 * for a block that is exactly right.
	 *
	 * <p>A spec with no properties compares by name alone, which is also what every work.json
	 * written before this looked like — so an un-regenerated design still reads correctly.
	 */
	static boolean matches(BlockState st, String spec) {
		int b = spec.indexOf('[');
		String want = b < 0 ? spec : spec.substring(0, b);
		String have = BuiltInRegistries.BLOCK.getKey(st.getBlock()).getPath();
		if (!have.equals(want)) return BECOMES.getOrDefault(want, Set.of()).contains(have);
		if (b < 0) return true;
		int end = spec.lastIndexOf(']');
		if (end <= b) return true;
		for (String pair : spec.substring(b + 1, end).split(",")) {
			int eq = pair.indexOf('=');
			if (eq < 0) continue;
			if (!propEquals(st, pair.substring(0, eq).trim(), pair.substring(eq + 1).trim())) return false;
		}
		return true;
	}

	private static boolean propEquals(BlockState st, String key, String value) {
		for (Property<?> p : st.getProperties()) {
			if (!p.getName().equals(key)) continue;
			return valueName(st, p).equals(value);
		}
		// The design named a property this block does not have. That is a design bug, not a
		// deviation in the world - say the cell is wrong so it surfaces rather than hiding.
		return false;
	}

	private static <T extends Comparable<T>> String valueName(BlockState st, Property<T> p) {
		return p.getName(st.getValue(p));
	}

	/**
	 * How many of each BLOCK the given cells need. Keyed on the item, not the state: a shopping
	 * list that says "12x stone_brick_stairs[facing=east,half=bottom]" is not a shopping list, and
	 * four facings of one stair are one stack of one item.
	 */
	static Map<String, Integer> tally(List<Cell> cells) {
		Map<String, Integer> out = new LinkedHashMap<>();
		for (Cell c : cells) out.merge(c.item(), 1, Integer::sum);
		return out;
	}

	/**
	 * Merge a `dig` list into a design's sidecar. A litematic stores no air, so "break this" can
	 * only ever live in the sidecar — which is why every generator carries `dig` too.
	 */
	static void writeDig(Path schematicsDir, String name, List<int[]> dig) throws IOException {
		Path side = schematicsDir.resolve(name + ".scan.json");
		if (!Files.exists(side)) return;
		JsonObject root = JsonParser.parseString(Files.readString(side, StandardCharsets.UTF_8)).getAsJsonObject();
		JsonArray arr = new JsonArray();
		for (int[] d : dig) {
			JsonArray c = new JsonArray();
			c.add(d[0]);
			c.add(d[1]);
			c.add(d[2]);
			arr.add(c);
		}
		root.add("dig", arr);
		Files.writeString(side, new com.google.gson.GsonBuilder().setPrettyPrinting().create().toJson(root),
			StandardCharsets.UTF_8);
	}

	/**
	 * What the player is carrying, by block name.
	 *
	 * <p>Loose stacks only — the contents of a shulker box in your pack are NOT counted, because
	 * reading them means reading the box's item component and they are not placeable until you set
	 * the box down anyway. So this under-reports rather than over-reports, which is the safe
	 * direction: it sends you to a chest you did not strictly need rather than telling you that you
	 * have something you cannot reach.
	 *
	 * <p>`/cscan need` used to send you to a chest for something already in your hotbar. The names
	 * are ITEM names and the tally holds BLOCK names; for everything this project builds with they
	 * are the same string, and where they are not (redstone, doors) the lookup simply misses and
	 * you get the old behaviour rather than a wrong number.
	 */
	static Map<String, Integer> carrying(net.minecraft.client.player.LocalPlayer player) {
		Map<String, Integer> out = new LinkedHashMap<>();
		if (player == null) return out;
		for (net.minecraft.world.item.ItemStack st : player.getInventory()) {
			if (st == null || st.isEmpty()) continue;
			out.merge(BuiltInRegistries.ITEM.getKey(st.getItem()).getPath(), st.getCount(), Integer::sum);
		}
		return out;
	}

	/**
	 * What is inside the shulker boxes in your pack.
	 *
	 * <p><b>Deliberately NOT added to {@link #carrying}.</b> A block in a box is not placeable — you
	 * would have to set the box down, open it, take the stack and break the box again, none of which
	 * this mod does — so counting it as carried would have the loop fly to a spot, find it can place
	 * nothing, and stall there. `carrying` means "can go into the world right now" and must keep
	 * meaning that.
	 *
	 * <p>It is the FETCH that needs to know. Flying across the island for stone bricks when you have
	 * 1,728 of them in a box on your hip is a wasted trip, and the loop had no way to tell.
	 *
	 * <p>One level deep: a box inside a box is not something to plan around.
	 */
	static Map<String, Integer> boxed(net.minecraft.client.player.LocalPlayer player) {
		Map<String, Integer> out = new LinkedHashMap<>();
		if (player == null) return out;
		for (net.minecraft.world.item.ItemStack st : player.getInventory()) {
			if (st == null || st.isEmpty()) continue;
			var contents = st.getOrDefault(net.minecraft.core.component.DataComponents.CONTAINER,
				net.minecraft.world.item.component.ItemContainerContents.EMPTY);
			contents.nonEmptyItemCopyStream().forEach(inner ->
				out.merge(BuiltInRegistries.ITEM.getKey(inner.getItem()).getPath(), inner.getCount(),
					Integer::sum));
		}
		return out;
	}

	/**
	 * How many more of one item would fit in the pack.
	 *
	 * <p>This is what makes "fill the inventory" a number rather than a hope. The fetch phase used to
	 * take exactly the shortfall of the ONE spot it was standing in — sixty-four bricks, place them,
	 * fly back — so a thousand-cell wall was a hundred round trips. Asking the pack how much room it
	 * has turns the same trip into one load.
	 *
	 * <p>Main inventory only: the hotbar and the three storage rows, which is what
	 * {@code getContainerSize()} minus armour and offhand comes to. Armour slots are empty on this
	 * account and would otherwise read as 320 blocks of room that does not exist.
	 */
	static int room(net.minecraft.client.player.LocalPlayer player, String item) {
		if (player == null) return 0;
		var inv = player.getInventory();
		int empty = 0;
		int[] partial = new int[36];
		int n = 0;
		int max = 64;
		int slots = Math.min(36, inv.getContainerSize());
		for (int i = 0; i < slots; i++) {
			net.minecraft.world.item.ItemStack st = inv.getItem(i);
			if (st == null || st.isEmpty()) {
				empty++;
				continue;
			}
			if (!BuiltInRegistries.ITEM.getKey(st.getItem()).getPath().equals(item)) continue;
			max = inv.getMaxStackSize(st);
			partial[n++] = st.getCount();
		}
		return roomIn(empty, java.util.Arrays.copyOf(partial, n), max);
	}

	/** The arithmetic of {@link #room}, without a client to hold it. */
	static int roomIn(int emptySlots, int[] partials, int max) {
		int n = emptySlots * max;
		for (int c : partials) if (c < max) n += max - c;
		return n;
	}

	/**
	 * A cell with nothing to place against. You cannot put a block in mid-air: it needs a face to
	 * click, and on a survival server that means a neighbour that already exists.
	 *
	 * <p>A cell counts as reachable if ANY of its six neighbours is solid in the world OR is another
	 * cell of the same design that comes earlier in the build order - the worklist is sorted
	 * bottom-up, so a tower builds against itself course by course and only its FIRST block needs
	 * something under it. Ignoring that would flag most of a wall.
	 */
	/** Is there a solid block here? The world answers in game; a fixture answers in the tests. */
	@FunctionalInterface
	interface Solid {
		boolean at(BlockPos p);
	}

	static Solid solidIn(Level level) {
		// An UNLOADED neighbour is treated as solid: claiming a cell needs scaffolding because the
		// chunk behind it is not loaded would send you to build a tower against terrain that is
		// already there.
		return p -> !level.isLoaded(p) || !level.getBlockState(p).isAir();
	}

	static boolean needsScaffold(Solid solid, Cell c, Set<Long> earlier) {
		BlockPos p = c.pos();
		for (net.minecraft.core.Direction d : net.minecraft.core.Direction.values()) {
			BlockPos n = p.relative(d);
			if (earlier.contains(n.asLong())) return false;
			if (solid.at(n)) return false;
		}
		return true;
	}

	/**
	 * A cell you cannot get AT: every one of its six neighbours is solid.
	 *
	 * <p>The scaffold check asks whether there is a face to click. This asks the opposite question
	 * and it is just as fatal: a cell buried inside a solid mass has plenty to place against and no
	 * way to reach it. You cannot put a block inside a sealed volume, and a plan that sends you to
	 * stand in front of one is a plan that wastes the trip.
	 *
	 * <p>Together the two bracket what "buildable right now" means — at least one solid neighbour
	 * to place against, at least one open one to reach through. A cell with six of either is not
	 * work you can do this trip.
	 *
	 * <p>Cells of the same design placed EARLIER do not count as openings: they will be solid by
	 * the time you get there, which is the same reason they DO count for scaffolding.
	 */
	static boolean enclosed(Solid solid, Cell c, Set<Long> earlier) {
		BlockPos p = c.pos();
		for (net.minecraft.core.Direction d : net.minecraft.core.Direction.values()) {
			BlockPos n = p.relative(d);
			if (earlier.contains(n.asLong())) continue;      // will be filled before you arrive
			if (!solid.at(n)) return false;                  // an opening: you can reach in
		}
		return true;
	}

	/** Cells of `todo` that are sealed inside solid world, in build order. */
	static List<Cell> unreachable(Level level, List<Cell> todo) {
		return unreachable(solidIn(level), todo);
	}

	static List<Cell> unreachable(Solid solid, List<Cell> todo) {
		Set<Long> earlier = new java.util.HashSet<>();
		List<Cell> out = new ArrayList<>();
		for (Cell c : todo) {
			if (enclosed(solid, c, earlier)) out.add(c);
			earlier.add(c.pos().asLong());
		}
		return out;
	}

	/**
	 * Every cell of `todo` that has nothing to place against, in build order.
	 *
	 * <p>The Python side has `floating` and answers the same question against a capture. This
	 * answers it against the world as it is right now, standing in front of the problem, which is
	 * when it actually matters - the alternative is discovering it with a shulker in your hand.
	 */
	/**
	 * Cells the printer could place THIS SECOND.
	 *
	 * <p>{@link #floating} answers a different question and answers it correctly: it counts an
	 * EARLIER cell of the same design as support, because the work list is sorted bottom-up and a
	 * wall builds against itself course by course. That is the right rule for "does this design need
	 * scaffolding".
	 *
	 * <p>It is the wrong rule for "where should I go and stand". A cell whose only support is
	 * another cell that has not been built yet is not floating and is not placeable either, and if
	 * that support is in a different bin — or a different spot — nothing you do here will place it.
	 * Reported as: <i>"its still choosing clusters that cant be placed"</i>.
	 *
	 * <p>So this asks the world alone: is there a real face to click, right now.
	 */
	static List<Cell> placeableNow(Level level, List<Cell> cells) {
		return placeableNow(solidIn(level), cells);
	}

	static List<Cell> placeableNow(Solid solid, List<Cell> cells) {
		List<Cell> out = new ArrayList<>();
		for (Cell c : cells) {
			if (!needsScaffold(solid, c, Set.of())) out.add(c);
		}
		return out;
	}

	static List<Cell> floating(Level level, List<Cell> todo) {
		return floating(solidIn(level), todo);
	}

	static List<Cell> floating(Solid solid, List<Cell> todo) {
		Set<Long> earlier = new java.util.HashSet<>();
		List<Cell> out = new ArrayList<>();
		for (Cell c : todo) {
			if (needsScaffold(solid, c, earlier)) out.add(c);
			earlier.add(c.pos().asLong());
		}
		return out;
	}

	static List<BlockPos> positions(List<Cell> cells, int limit) {
		List<BlockPos> out = new ArrayList<>();
		for (Cell c : cells) {
			if (out.size() >= limit) break;
			out.add(c.pos());
		}
		return out;
	}
}
