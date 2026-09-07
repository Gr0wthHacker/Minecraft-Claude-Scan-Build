package dev.jack.chunkscan;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/** Loads schematics at recorded origins (or legacy work lists) and compares them with the live world. */
final class Work {
	/**
	 * One cell of a design. {@code block} is what mcbuild wrote: either a bare name, or
	 * {@code name[facing=east,half=bottom]} carrying the properties the design MEANT.
	 */
	record Cell(BlockPos pos, String block) {
		/** The block name without its state — what you put in a shulker, and what a tally counts. */
		String item() {
			return ActionRecipe.itemFor(block);
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
	/**
	 * @param todoTotal  every cell left to place, WHEREVER it is - see the note on `detail`.
	 * @param nearestTodo the nearest of those to `near`, so "nothing near, move" is still a global
	 *                   question when the list itself is local.
	 */
	record Split(String name, List<Cell> todo, List<Cell> wrong, int built, int unseen,
	             BlockPos nearestUnseen, List<BlockPos> dig, List<Cell> manual,
	             int todoTotal, BlockPos nearestTodo) {
		/** The arity before declined work existed; a design with none reads exactly as it did. */
		Split(String name, List<Cell> todo, List<Cell> wrong, int built, int unseen,
		      BlockPos nearestUnseen, List<BlockPos> dig) {
			this(name, todo, wrong, built, unseen, nearestUnseen, dig, List.of());
		}

		/** The arity before the list could be capped: the list IS everything, as it used to be. */
		Split(String name, List<Cell> todo, List<Cell> wrong, int built, int unseen,
		      BlockPos nearestUnseen, List<BlockPos> dig, List<Cell> manual) {
			this(name, todo, wrong, built, unseen, nearestUnseen, dig, manual,
				todo.size(), todo.isEmpty() ? null : todo.get(0).pos());
		}

		int total() { return todoTotal + wrong.size() + built + unseen + manual.size(); }

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
		boolean complete() {
			return todoTotal == 0 && wrong.isEmpty() && unseen == 0 && dig.isEmpty() && manual.isEmpty();
		}

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

		/** Cells handed back to a human, by reason, for the report. Never a reason to wait. */
		Map<String, Integer> manualLeft() {
			Map<String, Integer> out = new java.util.LinkedHashMap<>();
			for (Cell c : manual) {
				String why = ActionRecipe.manual(c.block());
				if (why == null && ActionRecipe.sign(c.block())) why = "sign text not recorded";
				out.merge(why == null ? "manual" : why, 1, Integer::sum);
			}
			return out;
		}

		/** One compact, deterministic handoff for an automatic pass that has reached deferred work. */
		String manualSummary() {
			Map<String, Integer> byReason = manualLeft();
			if (byReason.isEmpty()) return "";
			StringBuilder out = new StringBuilder("; deferred: ");
			boolean first = true;
			for (var entry : byReason.entrySet()) {
				if (!first) out.append(", ");
				first = false;
				out.append(entry.getValue()).append(" ").append(entry.getKey());
			}
			return out.toString();
		}
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

	/**
	 * A loaded design, BINNED BY CHUNK. Jack: <i>"it scans too frequently, i think it uses a full
	 * radius based on current position"</i> - and it did: the printer's tick asked `split` for the
	 * cells within reach of the body and `split` walked all 540,862 cells of the park to answer,
	 * twenty times a second, re-parsing the design's sidecar for the dig list on every call. A
	 * radius question touches only the chunks the radius covers now, and an unloaded chunk costs
	 * one `hasChunk` rather than a world lookup per cell.
	 */
	private record Cached(java.nio.file.attribute.FileTime dataTime, long dataSize,
        java.nio.file.attribute.FileTime originTime, List<Cell> cells,
        Map<Long, List<Cell>> bins, List<BlockPos> dig) {}
    private static final Map<Path, Cached> cache = new LinkedHashMap<>();

    static long binKey(int cx, int cz) {
        return ((long) cx & 0xFFFFFFFFL) | ((long) cz << 32);
    }

    static Map<Long, List<Cell>> bin(List<Cell> cells) {
        Map<Long, List<Cell>> bins = new java.util.HashMap<>();
        for (Cell c : cells) {
            bins.computeIfAbsent(binKey(c.pos().getX() >> 4, c.pos().getZ() >> 4), k -> new ArrayList<>()).add(c);
        }
        for (Map.Entry<Long, List<Cell>> e : bins.entrySet()) e.setValue(List.copyOf(e.getValue()));
        return Map.copyOf(bins);
    }

    /** Is any cell of the chunk (cx, cz) within `radius` of `near`? A box test, so a bin is skipped whole. */
    static boolean binNear(int cx, int cz, BlockPos near, int radius) {
        int x0 = cx << 4, z0 = cz << 4;
        int dx = Math.max(0, Math.max(x0 - near.getX(), near.getX() - (x0 + 15)));
        int dz = Math.max(0, Math.max(z0 - near.getZ(), near.getZ() - (z0 + 15)));
        return (long) dx * dx + (long) dz * dz <= (long) radius * radius;
    }

    static synchronized List<Cell> load(Path schematicsDir, String name) throws IOException {
        return cached(schematicsDir, name).cells();
    }

    private static synchronized Cached cached(Path schematicsDir, String name) throws IOException {
        schematicsDir = ActiveBuild.inputs(schematicsDir, name);
        Path work = file(schematicsDir, name);
        Path lit = schematicsDir.resolve(name + ".litematic");
        Path side = schematicsDir.resolve(name + ".scan.json");
        boolean schematic = Files.exists(lit);
        Path source = (schematic ? lit : work).toAbsolutePath().normalize();
        if (!Files.exists(source)) throw new IOException("Missing schematic/work list: " + name);
        var time = Files.getLastModifiedTime(source);
        var originTime = schematic ? Files.getLastModifiedTime(side) : null;
        long size = Files.size(source);
        Cached old = cache.get(source);
        if (old != null && old.dataTime().equals(time) && old.dataSize() == size
            && java.util.Objects.equals(old.originTime(), originTime)) return old;
        List<BlockPos> dig = List.of();
        List<Cell> cells;
        if (schematic) {
            Designs.Design d = Designs.load(schematicsDir, name);
            cells = LitematicReader.read(lit, d.origin());
            dig = List.copyOf(d.dig());
        } else {
            cells = loadWork(schematicsDir, name);
            try { dig = List.copyOf(Designs.load(schematicsDir, name).dig()); }
            catch (Exception ignored) { /* no sidecar, or not a design: no dig list */ }
        }
        cells = List.copyOf(cells);
        Cached fresh = new Cached(time, size, originTime, cells, bin(cells), dig);
        if (cache.size() >= 8) cache.remove(cache.keySet().iterator().next());
        cache.put(source, fresh);
        return fresh;
    }

    private static List<Cell> loadWork(Path schematicsDir, String name) throws IOException {
		Path p = file(schematicsDir, name);
		if (!Files.exists(p)) {
			throw new IOException(name + ".work.json missing — regenerate it with: python -m mcbuild work \"" + name + "\"");
		}
		JsonObject root = JsonParser.parseString(Files.readString(p, StandardCharsets.UTF_8)).getAsJsonObject();
		JsonArray arr = root.getAsJsonArray("cells");
		// A MANIFEST IS NOT AN EMPTY DESIGN. `work.json` carries the origin, the dig list and the
		// count; the CELLS live in the schematic beside it, and this fallback exists only for a
		// work list with no schematic. Read as zero cells it would report the design complete -
		// which is the one failure worse than not reading it at all.
		if (arr == null || arr.isEmpty()) {
			String lit = root.has("schematic") ? root.get("schematic").getAsString() : name + ".litematic";
			throw new IOException(name + ".work.json is a manifest — its cells live in " + lit
				+ ", which is missing. Restore the schematic, or regenerate both with:"
				+ " python -m mcbuild gen <config> --ship");
		}
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
		return digLeft(level, schematicsDir, name, null, 0);
	}

	/**
	 * The dig cells still standing, <b>bounded before the world is asked</b>.
	 *
	 * <p>The radius used to be applied by the CALLER, after this had already run `isLoaded` and
	 * `getBlockState` on every entry: `Park Complete` carries 9,846 dig cells and `split` runs on
	 * every printer tick, so a bound that exists to keep the work local was costing two hundred
	 * thousand world lookups a second to produce a list of nothing. A distance test is free and a
	 * chunk lookup is not, so the cheap one goes first.
	 */
	static List<BlockPos> digLeft(Level level, Path schematicsDir, String name, BlockPos near, int radius) {
		List<BlockPos> out = new ArrayList<>();
		long r2 = (long) radius * radius;
		try {
			for (BlockPos p : cached(schematicsDir, name).dig()) {         // cached with the list, not re-parsed
				if (radius > 0 && near != null && p.distSqr(near) > r2) continue;
				if (!level.isLoaded(p)) continue;
				if (!level.getBlockState(p).isAir()) out.add(p);
			}
		} catch (Exception ignored) {
			// No sidecar, or not a design: no dig list. `split` still answers about placement.
		}
		return out;
	}

	static Split split(Level level, Path schematicsDir, String name, BlockPos near, int radius) throws IOException {
		return split(level, schematicsDir, name, near, radius, 0);
	}

	/** How many cells the packed sort key can address: 23 bits of index. */
	static final int SORT_INDEX_MAX = 1 << 23;

	/** The order the packed key encodes, spelled out - the fallback, and what the test compares against. */
	static List<Cell> sortSlowly(List<Cell> todo, BlockPos near) {
		List<Cell> out = new ArrayList<>(todo);
		out.sort((a, b) -> {
			int recipe = Integer.compare(ActionRecipe.order(a.block()), ActionRecipe.order(b.block()));
			if (recipe != 0) return recipe;
			int dy = Integer.compare(a.pos().getY(), b.pos().getY());     // bottom-up: always reachable
			if (dy != 0) return dy;
			return Double.compare(a.pos().distSqr(near), b.pos().distSqr(near));
		});
		return out;
	}

	private static Split finish(String name, List<Cell> todo, List<Cell> wrong, int built, int unseen,
	                            BlockPos nearestUnseen, List<BlockPos> dig, List<Cell> manual,
	                            int todoTotal, BlockPos nearestTodo, long sortT0) {
		Perf.record("split sort", System.nanoTime() - sortT0);
		return new Split(name, todo, wrong, built, unseen, nearestUnseen, dig, manual,
			todoTotal, nearestTodo);
	}

	/**
	 * @param detail how far from `near` a cell has to be to appear in the todo LIST. 0 means all of
	 *               them, which is what every command wants; the loop's own recount passes its
	 *               working radius.
	 *
	 * <p><b>COUNT GLOBALLY, LIST LOCALLY.</b> Measured in game with `/cscan perf`, this call was
	 * <b>262 ms on average and 427 at worst</b> - a quarter-second freeze twice a second, and by
	 * far the largest thing this mod does. It built and SORTED a list of every remaining cell of
	 * `Park Complete` - some two hundred thousand of them - so that {@code Hud.advance} could
	 * immediately narrow it to the sixteen blocks around the body and throw the rest away.
	 *
	 * <p>The counts still cover the whole design, because completion and progress are global
	 * questions and getting those wrong ends a session early. What is bounded is the LIST, and the
	 * one global question the loop asks of it - where is the nearest work when there is none here -
	 * is answered by {@code nearestTodo}, computed in the same pass for nothing.
	 */
	static Split split(Level level, Path schematicsDir, String name, BlockPos near, int radius,
	                   int detail) throws IOException {
		List<Cell> todo = new ArrayList<>(), wrong = new ArrayList<>(), manual = new ArrayList<>();
		// ---- BREAK IT FIRST, THEN PLACE IT. 2,970 cells of `Park Complete` are in the design AND
		// on its dig list - 2,933 of them the ground plane a lake and a well are cut through - and
		// nothing expressed which comes first: `split` put the cell in `todo` while `digLeft`
		// returned it as still standing, on the same tick, under the same radius, so an unattended
		// session could place a block and break it again for ever.
		//
		// It needs no ordering token, only the two rules that follow from what the lists MEAN. A
		// dig cell that is still solid is an obstruction, so it is not placeable yet; once broken
		// it leaves the dig list by itself and becomes ordinary work. The other half of the rule
		// is in `Digger.judge`: a cell already holding what the design wants is the finished
		// build, not the obstruction, and is never broken - without that the pair would loop.
		List<BlockPos> digNow = digLeft(level, schematicsDir, name, near, radius);
		Set<BlockPos> owedToTheDigger = digNow.isEmpty() ? Set.of() : new java.util.HashSet<>(digNow);
		int built = 0;
		long r2 = (long) radius * radius;
		long d2 = (long) detail * detail;
		int unseen = 0;
		int todoTotal = 0;
		BlockPos nearestTodo = null;
		double todoD = Double.MAX_VALUE;
		BlockPos nearestUnseen = null;
		double unseenD = Double.MAX_VALUE;
		// BY CHUNK, and only the chunks the radius reaches. An unloaded chunk is one `hasChunk`
		// and its cells are unseen without a world lookup each; a loaded one is diffed cell by cell.
		long diffT0 = System.nanoTime();
		for (Map.Entry<Long, List<Cell>> bin : cached(schematicsDir, name).bins().entrySet()) {
			int cx = (int) (bin.getKey() & 0xFFFFFFFFL), cz = (int) (bin.getKey() >> 32);
			if (radius > 0 && !binNear(cx, cz, near, radius)) continue;
			boolean loaded = level.hasChunk(cx, cz);
		for (Cell c : bin.getValue()) {
			if (radius > 0 && c.pos().distSqr(near) > r2) continue;
			if (!loaded) {
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
			// A BLANK BOARD IS NOT A BUILT SIGN. The block lands, `matches` says yes, and the text
			// update is a second action that can time out - so a sign whose words never arrived
			// counted as finished and `SignWriter.verification` had no caller at all. Only while a
			// roster is ARMED: outside one we know nothing about any sign's words, and declining
			// them all would quietly forget every board in the park.
			if (matches(st, c.block()) && !awaitingText(c)) built++;
			// ...and a board still waiting for its words is a second ACTION outstanding, not a
			// deviation: it goes to `manual` with the rest of the work handed back, never to
			// `wrong`, which would report a correct sign as the world holding something else.
			else if (matches(st, c.block())) manual.add(c);
			// Still owed to the digger: an obstruction, not work the printer may take.
			else if (owedToTheDigger.contains(c.pos())) manual.add(c);
			// Declined BEFORE the replaceable test, or it lands in `todo` and the printer spends
			// its tries on a cell it can never satisfy - which reads exactly like a stall.
			else if (ActionRecipe.manual(c.block()) != null || textlessSign(c)) manual.add(c);
			else if (isReplaceable(st) || ActionRecipe.slabIntermediate(st, c.block()) || ActionRecipe.cauldronIntermediate(st, c.block())
				|| ActionRecipe.vineIntermediate(st, c.block()) || ActionRecipe.glowLichenIntermediate(st, c.block())) {
				todoTotal++;
				double d = c.pos().distSqr(near);
				if (d < todoD) { todoD = d; nearestTodo = c.pos(); }
				if (detail <= 0 || d <= d2) todo.add(c);
			}
			else wrong.add(c);
		}
		}
		// DECORATE, SORT, UNDECORATE. The comparator asked `ActionRecipe.order` and `distSqr` on
		// BOTH sides of every comparison, so a hundred thousand cells cost about three and a half
		// million of each - and `order` used to parse a string and allocate a map every time. The
		// keys are a property of the cell, not of the comparison, so they are computed once.
		// ...AND SORTED WITHOUT BOXING. A comparator over an `Integer[]` allocates one box per cell
		// and compares through a lambda: two hundred thousand objects and three and a half million
		// virtual calls, twice a second. The order is (recipe, then course, then distance), and all
		// three fit in one primitive key, so `Arrays.sort(long[])` does it with no allocation at
		// all. Distance is quantised to a quarter of a block, which only ever reorders cells that
		// are the same material on the same course within a quarter block of each other.
		Perf.record("split diff", System.nanoTime() - diffT0);
		long sortT0 = System.nanoTime();
		int n = todo.size();
		// ...and 23 bits of index is 8.4 million cells, against 526,385 in the largest design here.
		// Past that the index would wrap into the distance field and the order would be quietly
		// wrong, so it falls back rather than being trusted.
		if (n >= SORT_INDEX_MAX) return finish(name, sortSlowly(todo, near), wrong, built, unseen,
			nearestUnseen, digNow, manual, todoTotal, nearestTodo, sortT0);
		long[] key = new long[n];
		Cell[] flat = todo.toArray(new Cell[0]);
		// THE KEY MUST STAY POSITIVE. Laid out as 8+12+20+24 bits it needs 64, and the top one is
		// the SIGN: a recipe of 128 or more would sort before everything else, silently, and
		// `ActionRecipe.order` returning anything but 0-2 would be the day a build came out in the
		// wrong order with nothing to say why. 63 bits, and every field clamped to its own width.
		for (int i = 0; i < n; i++) {
			Cell c = flat[i];
			long recipe = Math.min(255, Math.max(0, ActionRecipe.order(c.block())));   //  8 bits
			long y = Math.min(4095, Math.max(0, c.pos().getY() + 2048L));              // 12 bits
			long dist = Math.min(1_048_575L, (long) (Math.sqrt(c.pos().distSqr(near)) * 4));  // 20
			key[i] = (recipe << 55) | (y << 43) | (dist << 23) | i;                   // 23 bits
		}
		java.util.Arrays.sort(key);
		List<Cell> sorted = new ArrayList<>(n);
		for (long k : key) sorted.add(flat[(int) (k & 0xFFFFFF)]);
		todo = sorted;
		Perf.record("split sort", System.nanoTime() - sortT0);
		// Scoped by the same radius as the placements, so `need`/`next` stay about what is in reach
		// while `bom`/`follow` (radius 0) see the whole design. Computed ONCE, at the top, because
		// the classification above depends on it.
		return new Split(name, todo, wrong, built, unseen, nearestUnseen, digNow, manual,
			todoTotal, nearestTodo);
	}

	/**
	 * A sign this build would place blank.
	 *
	 * <p>Only while a build is ARMED with a roster: outside one we know nothing about any sign's
	 * text, and declining them all would make `/cscan check` and `need` quietly forget every board
	 * in the park. Placing it anyway is the one thing that is never right - a blank sign passes
	 * every check we have and is exactly the failure this park already shipped 177 of.
	 */
	/**
	 * A sign whose board is standing and whose words have not arrived.
	 *
	 * <p>A BLANK BOARD IS NOT A BUILT SIGN. The block lands, `matches` says yes, and the text is a
	 * second action that can time out - so a sign that never got its words counted as finished,
	 * and `SignWriter.verification`, `written` and `report` had no callers at all. Only while a
	 * roster is ARMED: outside one we know nothing about any board's words, and treating them all
	 * as unfinished would quietly reopen every sign in the park.
	 */
	static boolean awaitingText(Cell c) {
		return SignWriter.armed() && ActionRecipe.sign(c.block())
			&& SignWriter.textFor(c.pos()) != null
			&& SignWriter.verification(c.pos()) != SignWriter.Verification.CONFIRMED;
	}

	private static boolean textlessSign(Cell c) {
		return ActionRecipe.sign(c.block()) && SignWriter.armed() && SignWriter.textFor(c.pos()) == null;
	}

	private static boolean isReplaceable(BlockState st) {
		// What a right-click places INTO: air, and anything the game itself replaces - grass, a
		// fern, a snow layer. Never a fluid, or a source gets built over. Read as air-only, a lawn
		// design over short grass reported every cell as a deviation to break by hand.
		return st.isAir() || (st.canBeReplaced() && st.getFluidState().isEmpty());
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
     * Compare imported requirements while allowing automatic neighbor-derived state to converge.
     * Raw properties remain in StateContract; orientation, fluids and mechanism state stay required.
     * A legacy bare block specification compares identity only.
     */
	/**
	 * The registry path of a block, memoised on the BLOCK.
	 *
	 * <p>{@code BuiltInRegistries.BLOCK.getKey(b).getPath()} is a registry lookup and a substring,
	 * and {@link #matches} runs it once per CELL - a quarter of a million times per recount on the
	 * park. There are about twelve hundred blocks in the game, so this is asked once per block for
	 * the life of the session and never again.
	 */
	private static final Map<net.minecraft.world.level.block.Block, String> PATHS =
		new java.util.concurrent.ConcurrentHashMap<>();

	static String path(BlockState st) {
		return PATHS.computeIfAbsent(st.getBlock(), b -> BuiltInRegistries.BLOCK.getKey(b).getPath());
	}

	static boolean matches(BlockState st, String spec) {
        StateContract contract = StateContract.parse(spec);
        if (!contract.valid) return false;
        String have = path(st);
        if (!have.equals(contract.block)) return BECOMES.getOrDefault(contract.block, Set.of()).contains(have);
        return contract.propertiesMatch(st);
    }

	/**
	 * How many of each BLOCK the given cells need. Keyed on the item, not the state: a shopping
	 * list that says "12x stone_brick_stairs[facing=east,half=bottom]" is not a shopping list, and
	 * four facings of one stair are one stack of one item.
	 */
	/**
	 * A cell that is the SECOND half of a two-cell block: the same item placed once.
	 *
	 * <p>A door, a bed and a tall plant are one item and two cells, so counting a cell each asked
	 * for twice what the build needs. It is small on this park - 6 door cells, 97 two-cell plants
	 * - and it is wrong in the direction that sends you shopping for things you already have.
	 */
	static boolean secondHalf(String state) {
		return state.contains("half=upper") || state.contains("part=head");
	}

	/** A DOUBLE slab is two slabs, not one. Wrong in the other direction: a trip that comes up short. */
	static boolean doubleSlab(String state) {
		return state.contains("type=double");
	}

	static Map<String, Integer> tally(List<Cell> cells) {
		Map<String, Integer> out = new LinkedHashMap<>();
		for (Cell c : cells) {
			if (secondHalf(c.block())) continue;               // its other half already paid for it
			out.merge(c.item(), doubleSlab(c.block()) ? 2 : 1, Integer::sum);
			// A filled cauldron is one scheduled cell but two inventory actions. Buckets are consumed
			// into empty buckets by the fill, and this builder has no source-refill action, so budget
			// one filled bucket per cauldron rather than stranding an otherwise complete run at stage two.
			if (ActionRecipe.cauldronFill(c.block())) out.merge(ActionRecipe.cauldronBucket(c.block()), 1, Integer::sum);
		}
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
		// THE 36 REAL SLOTS. Iterating the Inventory walks 41 - armour and the offhand too - and a
		// stack of the needed block in the offhand read as carried, was never placeable, and the
		// station stalled, moved in, gave up and thrashed on a material it "had".
		for (net.minecraft.world.item.ItemStack st : player.getInventory().getNonEquipmentItems()) {
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
		// THE 36 REAL SLOTS. Iterating the Inventory walks 41 - armour and the offhand too - and a
		// stack of the needed block in the offhand read as carried, was never placeable, and the
		// station stalled, moved in, gave up and thrashed on a material it "had".
		for (net.minecraft.world.item.ItemStack st : player.getInventory().getNonEquipmentItems()) {
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
	/**
	 * How many of this item fit in one slot, asked of the GAME rather than assumed.
	 *
	 * <p>{@link #room} defaulted to 64 for any item the pack was not already carrying, so a trip
	 * for buckets, shulker boxes, signs or eggs was sized at up to sixty-four times the truth: the
	 * withdrawal over-asked, took what was there, and then blacklisted the chest that actually had
	 * the material for a minute. Rule 11 - ask the game, not your memory - applied to a number
	 * nobody thought of as a block property.
	 */
	static int maxStack(String item) {
		var it = BuiltInRegistries.ITEM.getOptional(net.minecraft.resources.Identifier.withDefaultNamespace(item));
		return it.map(i -> new net.minecraft.world.item.ItemStack(i).getMaxStackSize()).orElse(64);
	}

	static int room(net.minecraft.client.player.LocalPlayer player, String item) {
		if (player == null) return 0;
		var inv = player.getInventory();
		int empty = 0;
		int[] partial = new int[36];
		int n = 0;
		int max = maxStack(item);
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
	/**
	 * How many blocks a fetch trip can bring back at all: the empty slots of the pack, at a stack
	 * each. Partial stacks are not counted — they only take one material, and which one is a
	 * question {@link #room} answers per item. Never under a stack, so a full pack still sizes a
	 * fetch to SOMETHING rather than to nothing.
	 */
	static int loadCapacity(net.minecraft.client.player.LocalPlayer player) {
		if (player == null) return 64;
		var inv = player.getInventory();
		int empty = 0;
		int slots = Math.min(36, inv.getContainerSize());
		for (int i = 0; i < slots; i++) {
			net.minecraft.world.item.ItemStack st = inv.getItem(i);
			if (st == null || st.isEmpty()) empty++;
		}
		return Math.max(64, empty * 64);
	}

	/**
	 * THE STACKS IN THE PACK THAT ARE NOT THIS DESIGN'S BUSINESS, by item and count.
	 *
	 * <p>Jack: <i>"doesnt check inventory ... or fill inventory based on needs at all"</i>. The
	 * pack was never emptied of anything: leftovers from the last design, whatever was picked up
	 * on the way, a stack of dirt to pillar with - all of it sat in slots the fetch could not use,
	 * so {@link #loadCapacity} shrank, the trip brought back a stack or two, and the loop went
	 * shopping again an hour later for the same thing. A pack full of the wrong material read as
	 * PACK_FULL, and the loop parked.
	 *
	 * <p>A stack is dumpable when it places a block (so no tool, food, armour or bucket ever
	 * leaves the pack), holds nothing itself (a shulker box is somebody's storage, whatever it
	 * says on the outside), and is wanted by NO cell of the design - the whole design, not only
	 * the part in view, so a material for the far end is not put away and fetched back later.
	 * It goes into the chest the trip is at, which is indexed, so nothing is lost: it is put
	 * away, and the message says what.
	 *
	 * @param needed every item the design still wants anywhere; null means "not known", and
	 *               nothing is dumpable when the design's needs are not known
	 */
	static Map<String, Integer> dumpable(net.minecraft.client.player.LocalPlayer player,
	                                     java.util.Set<String> needed) {
		Map<String, Integer> out = new LinkedHashMap<>();
		if (player == null || needed == null) return out;
		for (net.minecraft.world.item.ItemStack st : player.getInventory().getNonEquipmentItems()) {
			if (st == null || st.isEmpty()) continue;
			String item = BuiltInRegistries.ITEM.getKey(st.getItem()).getPath();
			boolean holdsItems = Storage.isBox(item)
				|| st.has(net.minecraft.core.component.DataComponents.CONTAINER)
				|| st.has(net.minecraft.core.component.DataComponents.BUNDLE_CONTENTS);
			if (dumpableItem(item, st.getItem() instanceof net.minecraft.world.item.BlockItem,
				holdsItems, needed)) {
				out.merge(item, st.getCount(), Integer::sum);
			}
		}
		return out;
	}

	/** The rule of {@link #dumpable}, without a client to hold the pack. */
	static boolean dumpableItem(String item, boolean placesABlock, boolean holdsItems,
	                            java.util.Set<String> needed) {
		return needed != null && placesABlock && !holdsItems && !needed.contains(item);
	}

	/** How many slots {@link #dumpable} would free: what a fetch may count as room once it has put them away. */
	static int dumpableSlots(net.minecraft.client.player.LocalPlayer player, java.util.Set<String> needed) {
		if (player == null || needed == null) return 0;
		int n = 0;
		for (net.minecraft.world.item.ItemStack st : player.getInventory().getNonEquipmentItems()) {
			if (st == null || st.isEmpty()) continue;
			String item = BuiltInRegistries.ITEM.getKey(st.getItem()).getPath();
			boolean holdsItems = Storage.isBox(item)
				|| st.has(net.minecraft.core.component.DataComponents.CONTAINER)
				|| st.has(net.minecraft.core.component.DataComponents.BUNDLE_CONTENTS);
			if (dumpableItem(item, st.getItem() instanceof net.minecraft.world.item.BlockItem,
				holdsItems, needed)) n++;
		}
		return n;
	}

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
		// Unloaded and non-clickable neighbors are not proven placement support.
		return p -> level.isLoaded(p) && Printer.support(level.getBlockState(p));
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
		if (todo.isEmpty()) return out;
		// The exact exterior flood is intentionally a small-design proof. Re-running a volume flood
		// for every cell in Park Complete would turn `plan` into a client freeze; the large-design
		// scheduler needs an incremental exterior-air cache before it can make this stronger claim.
		if (todo.size() > 2048) {
			for (Cell c : todo) {
				if (enclosed(solid, c, earlier)) out.add(c);
				earlier.add(c.pos().asLong());
			}
			return out;
		}
		int minX = Integer.MAX_VALUE, minY = Integer.MAX_VALUE, minZ = Integer.MAX_VALUE;
		int maxX = Integer.MIN_VALUE, maxY = Integer.MIN_VALUE, maxZ = Integer.MIN_VALUE;
		for (Cell c : todo) {
			BlockPos p = c.pos();
			minX = Math.min(minX, p.getX() - 1); minY = Math.min(minY, p.getY() - 1); minZ = Math.min(minZ, p.getZ() - 1);
			maxX = Math.max(maxX, p.getX() + 1); maxY = Math.max(maxY, p.getY() + 1); maxZ = Math.max(maxZ, p.getZ() + 1);
		}
		for (Cell c : todo) {
			if (!hasExteriorApproach(solid, c.pos(), earlier, minX, minY, minZ, maxX, maxY, maxZ)) out.add(c);
			earlier.add(c.pos().asLong());
		}
		return out;
	}

	/** An approach face must connect through air to the outside of the ordered design volume. */
	private static boolean hasExteriorApproach(Solid solid, BlockPos cell, Set<Long> earlier,
	                                          int minX, int minY, int minZ, int maxX, int maxY, int maxZ) {
		java.util.ArrayDeque<BlockPos> queue = new java.util.ArrayDeque<>();
		Set<Long> seen = new java.util.HashSet<>();
		for (net.minecraft.core.Direction d : net.minecraft.core.Direction.values()) {
			BlockPos n = cell.relative(d);
			if (!solid.at(n) && !earlier.contains(n.asLong()) && seen.add(n.asLong())) queue.add(n);
		}
		while (!queue.isEmpty()) {
			BlockPos p = queue.removeFirst();
			if (p.getX() == minX || p.getX() == maxX || p.getY() == minY || p.getY() == maxY || p.getZ() == minZ || p.getZ() == maxZ) return true;
			for (net.minecraft.core.Direction d : net.minecraft.core.Direction.values()) {
				BlockPos n = p.relative(d);
				if (n.getX() < minX || n.getX() > maxX || n.getY() < minY || n.getY() > maxY || n.getZ() < minZ || n.getZ() > maxZ) continue;
				if (!solid.at(n) && !earlier.contains(n.asLong()) && seen.add(n.asLong())) queue.add(n);
			}
		}
		return false;
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
			if (!needsScaffold(solid, c, Set.of()) && !enclosed(solid, c, Set.of())) out.add(c);
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
