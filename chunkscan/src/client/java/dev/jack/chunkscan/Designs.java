package dev.jack.chunkscan;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import net.minecraft.core.BlockPos;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

/** Reads the .scan.json sidecars mcbuild writes next to each design. */
final class Designs {
	record Design(String name, Path litematic, Path sidecar, BlockPos origin, List<BlockPos> dig) {}

	private Designs() {}

	static Design load(Path schematicsDir, String name) throws IOException {
		// The name becomes a path here. See Work.file for why the gate lives at the conversion.
		String bad = ChunkScanClient.badName(name);
		if (bad != null) throw new IOException(bad);
		Path lit = schematicsDir.resolve(name + ".litematic");
		Path side = schematicsDir.resolve(name + ".scan.json");
		if (!Files.exists(lit)) throw new IOException("no schematic " + lit.getFileName());
		if (!Files.exists(side)) throw new IOException(name + ".scan.json missing (not a chunkscan/mcbuild design)");
		JsonObject root = JsonParser.parseString(Files.readString(side, StandardCharsets.UTF_8)).getAsJsonObject();
		JsonObject o = root.getAsJsonObject("origin");
		BlockPos origin = new BlockPos(o.get("x").getAsInt(), o.get("y").getAsInt(), o.get("z").getAsInt());
		List<BlockPos> dig = new ArrayList<>();
		JsonArray arr = root.getAsJsonArray("dig");
		if (arr != null) {
			for (var e : arr) {
				JsonArray c = e.getAsJsonArray();
				dig.add(new BlockPos(c.get(0).getAsInt(), c.get(1).getAsInt(), c.get(2).getAsInt()));
			}
		}
		String display = root.has("name") ? root.get("name").getAsString() : name;
		return new Design(display, lit, side, origin, dig);
	}

	/**
	 * The designs Jack actually tracks, or null when nothing has told us.
	 *
	 * <p>`sync.yaml`'s `progress:` list is the only place that knows, and the mod cannot read it -
	 * gson and no YAML parser, and the file lives in the repo rather than beside the schematics. So
	 * `python -m mcbuild sync` writes it out as `designs.json` and this reads it.
	 *
	 * <p>NULL, not an empty list, when the file is missing: "we do not know" and "you track nothing"
	 * are different answers, and only one of them should make `/cscan place` fall back to placing
	 * all 61.
	 */
	static List<String> tracked(Path schematicsDir) throws IOException {
		Path f = schematicsDir.resolve("designs.json");
		if (!Files.exists(f)) return null;
		JsonObject root = JsonParser.parseString(Files.readString(f, StandardCharsets.UTF_8)).getAsJsonObject();
		if (!root.has("tracked")) return null;
		List<String> out = new ArrayList<>();
		for (var e : root.getAsJsonArray("tracked")) out.add(e.getAsString());
		return out;
	}

	/**
	 * Is this sidecar a DESIGN's, or a world capture's?
	 *
	 * <p>Both are `<name>.scan.json` in the same folder, and telling them apart is not cosmetic. A
	 * capture sidecar carries `chunk_radius` and `chunks_included` because `SidecarWriter` records
	 * what it swept; a design's carries `kind` and `generated_by` because mcbuild records what it
	 * built. Nothing else distinguishes them, and until this existed `list()` offered captures as
	 * designs — its own docstring claimed it "skips the raw scans" and it never did.
	 *
	 * <p>What that cost, measured on the live folder: ten captures were being offered as designs,
	 * including a 111,631-block full-island scan that had overwritten the 30-block `Falls` design
	 * and was TRACKED. Bare `/cscan place` would have pasted the island onto the island.
	 *
	 * <p><b>THE CAPTURE MARKERS ARE THE DEFINITIVE HALF, so that is what is tested.</b> Requiring a
	 * positive design marker instead — `kind`, `generated_by`, `dig` — looked equivalent and was
	 * not: `Lowland Axolotl` was adopted as-built and its sidecar is a hand-written record carrying
	 * only `file`, `name`, `note` and `origin`. A real design would have been hidden from
	 * `/cscan place` by a check meant to hide captures. Absence of evidence that a file is a
	 * capture is good evidence that it is a design; the reverse does not hold.
	 *
	 * <p>Unreadable counts as NOT a design — nothing can place it anyway.
	 */
	static boolean isDesign(Path sidecar) {
		try {
			JsonObject root = JsonParser.parseString(
				Files.readString(sidecar, StandardCharsets.UTF_8)).getAsJsonObject();
			return !isCapture(root);
		} catch (Exception e) {
			return false;
		}
	}

	/** A world capture records what it SWEPT; only `SidecarWriter` writes these two keys. */
	private static boolean isCapture(JsonObject root) {
		return root.has("chunk_radius") || root.has("chunks_included");
	}

	/**
	 * True if a design of this name already exists here — what a scan must not write over.
	 *
	 * <p>Deliberately MORE cautious than {@link #isDesign}: anything that is not provably a capture
	 * blocks a scan, including a sidecar too broken to parse. Re-scanning `island` over yesterday's
	 * `island` is the daily loop and still works, because a capture is recognisable. Everything
	 * else gets the benefit of the doubt, because the cost of being wrong here is a design and its
	 * dig list, and the cost of being wrong the other way is picking another name.
	 */
	static boolean designExists(Path schematicsDir, String name) {
		Path side = schematicsDir.resolve(name + ".scan.json");
		if (!Files.exists(side)) return false;
		try {
			JsonObject root = JsonParser.parseString(
				Files.readString(side, StandardCharsets.UTF_8)).getAsJsonObject();
			return !isCapture(root);
		} catch (Exception e) {
			return true;                          // unparseable: do not overwrite what you cannot read
		}
	}

	/**
	 * Every DESIGN in the folder, EXCEPT the wand's scratch fills, clips and undos.
	 *
	 * <p>`/cscan place` with no argument places everything this returns, so what it returns has to
	 * be exactly what someone meant to build. Two things are filtered and both were learned the
	 * hard way: the scratch prefixes (a shelf of one-off fills is the pile that already caught this
	 * project once with the scratch animals), and now world CAPTURES — see {@link #isDesign}.
	 * Name one explicitly — `/cscan place _fill porch` — and it still places.
	 */
	static List<String> list(Path schematicsDir) throws IOException {
		List<String> out = new ArrayList<>();
		try (var s = Files.list(schematicsDir)) {
			s.filter(p -> p.getFileName().toString().endsWith(".scan.json")).forEach(p -> {
				String n = p.getFileName().toString();
				if (n.startsWith(ChunkScanClient.FILL_PREFIX)
					|| n.startsWith(ChunkScanClient.CLIP_PREFIX)
					|| n.startsWith(ChunkScanClient.UNDO_PREFIX)) return;
				if (!isDesign(p)) return;
				out.add(n.substring(0, n.length() - ".scan.json".length()));
			});
		}
		out.sort(String::compareToIgnoreCase);
		return out;
	}

	/**
	 * Designs this one must be built AFTER, from the sidecar's `after` list.
	 *
	 * <p>mcbuild already knows the order — `finish.defer_to` settles which design owns a shared
	 * cell, and CLAUDE.md states the sequences in prose ("portal first, ruinway defers to it";
	 * "the notch is the plug: cut it LAST"). None of that reached the mod, so `follow all` walked
	 * the tracked list alphabetically and could build a design whose ground another one still owes.
	 *
	 * <p>Empty when the sidecar says nothing, which is every design written before this existed.
	 */
	static List<String> after(Path schematicsDir, String name) {
		List<String> out = new ArrayList<>();
		Path side = schematicsDir.resolve(name + ".scan.json");
		if (!Files.exists(side)) return out;
		try {
			JsonObject root = JsonParser.parseString(
				Files.readString(side, StandardCharsets.UTF_8)).getAsJsonObject();
			JsonArray arr = root.getAsJsonArray("after");
			if (arr != null) for (var e : arr) out.add(e.getAsString());
		} catch (Exception ignored) {
		}
		return out;
	}

	/**
	 * `names` reordered so nothing is built before what it defers to.
	 *
	 * <p>A stable topological sort: ties and unknowns keep the order they came in, so a folder with
	 * no `after` anywhere is returned untouched. A CYCLE does not throw — it emits the remainder in
	 * input order, because refusing to build anything is a worse answer to a bad sidecar than
	 * building in a debatable order.
	 */
	static List<String> inBuildOrder(Path schematicsDir, List<String> names) {
		List<String> pending = new ArrayList<>(names);
		java.util.Set<String> placed = new java.util.LinkedHashSet<>();
		List<String> out = new ArrayList<>();
		while (!pending.isEmpty()) {
			boolean progressed = false;
			for (var it = pending.iterator(); it.hasNext(); ) {
				String n = it.next();
				boolean ready = true;
				for (String dep : after(schematicsDir, n)) {
					if (names.contains(dep) && !placed.contains(dep)) { ready = false; break; }
				}
				if (ready) {
					out.add(n); placed.add(n); it.remove(); progressed = true;
				}
			}
			if (!progressed) {                       // a cycle, or a dep on itself
				out.addAll(pending);
				break;
			}
		}
		return out;
	}

	/**
	 * The design's recorded FACING, in degrees, or 0 when it has none.
	 *
	 * <p>THE BEARING IS RELATIVE TO THIS, exactly as {@code look.py} and {@code panel.py} choose
	 * their profile axis — 0 head-on, 90 profile, 180 tail-on. Picked by hand it was got wrong
	 * twice in one session, and a design with no recorded facing SAYS SO rather than defaulting
	 * quietly: {@link #hasFacing} is what a caller checks before believing "head-on".
	 */
	static int facingDegrees(java.nio.file.Path schematicsDir, String name) {
		String f = facingName(schematicsDir, name);
		return switch (f) {
			case "south" -> 180;
			case "east" -> 90;
			case "west" -> 270;
			case "north" -> 0;
			default -> {
				try {
					yield Integer.parseInt(f);
				} catch (NumberFormatException e) {
					yield 0;
				}
			}
		};
	}

	static boolean hasFacing(java.nio.file.Path schematicsDir, String name) {
		return !facingName(schematicsDir, name).isBlank();
	}

	private static String facingName(java.nio.file.Path schematicsDir, String name) {
		try {
			java.nio.file.Path side = schematicsDir.resolve(name + ".scan.json");
			if (!java.nio.file.Files.exists(side)) return "";
			com.google.gson.JsonObject o = com.google.gson.JsonParser
				.parseString(java.nio.file.Files.readString(side)).getAsJsonObject();
			for (String key : new String[] {"facing", "faces"}) {
				if (o.has(key)) return o.get(key).getAsString().toLowerCase(java.util.Locale.ROOT);
			}
			if (o.has("designed") && o.getAsJsonObject("designed").has("facing")) {
				return o.getAsJsonObject("designed").get("facing").getAsString()
					.toLowerCase(java.util.Locale.ROOT);
			}
		} catch (Exception ignored) {
			// a sidecar we cannot read has no facing, which is the honest answer
		}
		return "";
	}
}
