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
	 * Every design in the folder that has a sidecar (skips the raw scans), EXCEPT the wand's
	 * scratch fills. `/cscan place` with no argument places everything this returns, and a shelf
	 * of one-off fills is exactly the pile that trap already caught once with the scratch animals.
	 * Name one explicitly - `/cscan place _fill porch` - and it still places.
	 */
	static List<String> list(Path schematicsDir) throws IOException {
		List<String> out = new ArrayList<>();
		try (var s = Files.list(schematicsDir)) {
			s.filter(p -> p.getFileName().toString().endsWith(".scan.json")).forEach(p -> {
				String n = p.getFileName().toString();
				if (n.startsWith(ChunkScanClient.FILL_PREFIX)
					|| n.startsWith(ChunkScanClient.CLIP_PREFIX)
					|| n.startsWith(ChunkScanClient.UNDO_PREFIX)) return;
				out.add(n.substring(0, n.length() - ".scan.json".length()));
			});
		}
		out.sort(String::compareToIgnoreCase);
		return out;
	}
}
