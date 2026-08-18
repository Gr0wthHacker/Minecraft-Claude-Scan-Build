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

/**
 * Reads &lt;name&gt;.work.json — a design flattened to world-coordinate cells by mcbuild — and diffs it
 * against the live world.
 *
 * The mod has a Litematica writer but no reader, so the desktop (which already has one) exports the
 * cell list once per generation. Diffing happens here against the world as it is right now, so the
 * answer never goes stale between captures.
 */
final class Work {
	record Cell(BlockPos pos, String block) {}

	/** A design's cells, split by what the world holds today. */
	record Split(String name, List<Cell> todo, List<Cell> wrong, int built) {
		int total() { return todo.size() + wrong.size() + built; }
	}

	private Work() {}

	static Path file(Path schematicsDir, String name) {
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
	static Split split(Level level, Path schematicsDir, String name, BlockPos near, int radius) throws IOException {
		List<Cell> todo = new ArrayList<>(), wrong = new ArrayList<>();
		int built = 0;
		long r2 = (long) radius * radius;
		for (Cell c : load(schematicsDir, name)) {
			if (radius > 0 && c.pos().distSqr(near) > r2) continue;
			if (!level.isLoaded(c.pos())) continue;
			String have = BuiltInRegistries.BLOCK.getKey(level.getBlockState(c.pos()).getBlock()).getPath();
			if (have.equals(c.block())) built++;
			else if (isReplaceable(level.getBlockState(c.pos()))) todo.add(c);
			else wrong.add(c);
		}
		todo.sort((a, b) -> {
			int dy = Integer.compare(a.pos().getY(), b.pos().getY());       // bottom-up: always reachable
			if (dy != 0) return dy;
			return Double.compare(a.pos().distSqr(near), b.pos().distSqr(near));
		});
		return new Split(name, todo, wrong, built);
	}

	private static boolean isReplaceable(BlockState st) {
		return st.isAir() || st.canBeReplaced();
	}

	/** How many of each block the given cells need. */
	static Map<String, Integer> tally(List<Cell> cells) {
		Map<String, Integer> out = new LinkedHashMap<>();
		for (Cell c : cells) out.merge(c.block(), 1, Integer::sum);
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
