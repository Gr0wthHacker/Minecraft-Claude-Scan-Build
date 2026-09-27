package dev.jack.chunkscan;

import com.google.gson.JsonObject;

/**
 * The buildable square — how far out anything is allowed to go.
 *
 * <p>Every skyblock island has one bedrock block at its origin, and measured against ours the
 * whole of the island's placed content is exactly bedrock ± 49 on both axes: 99 by 99. That
 * boundary was DERIVED in {@code mcbuild/plot.py} and exported into {@code chunkscan_rules.json}
 * with everything else, so the wand answers the same square the generators do.
 *
 * <p><b>The mod could not see it at all until now</b>, and it cost something: the Island Run
 * shipped 120 cells past the edge and a human noticed, not the tooling. A fill drawn over the
 * line is worse than a wasted trip — off the plot the server may refuse the placement outright,
 * so you carry the blocks there and come back with them.
 *
 * <p><b>It is a SQUARE, not a circle.</b> A route at radius 52 is legal on the diagonals
 * (49·√2 = 69) and three blocks over the line at the cardinals. A radius check would either
 * waste the corners or overrun the sides.
 *
 * <p><b>NOT FOUND is not the same as INSIDE.</b> If the export could not locate the bedrock the
 * boundary is unknown, and every check answers "I cannot say" rather than "fine" — a boundary
 * guard that silently passes everything is the failure this file exists to prevent, wearing the
 * opposite hat.
 */
final class Plot {
	private static boolean loaded;
	private static boolean found;
	private static int x0, z0, x1, z1;
	private static String source = "";

	private Plot() {}

	static synchronized void load(JsonObject root) {
		loaded = true;
		found = false;
		if (root == null || !root.has("plot")) return;
		JsonObject p = root.getAsJsonObject("plot");
		if (!p.has("found") || !p.get("found").getAsBoolean()) return;
		x0 = p.get("x0").getAsInt();
		z0 = p.get("z0").getAsInt();
		x1 = p.get("x1").getAsInt();
		z1 = p.get("z1").getAsInt();
		source = p.has("source") ? p.get("source").getAsString() : "";
		found = true;
	}

	/** True once the boundary is known. While false every {@link #outside} answer is false. */
	static boolean known() {
		Rules.load();
		return loaded && found;
	}

	static String describe() {
		if (!known()) return "plot boundary unknown (no bedrock in any capture — re-run tools/export_rules.py)";
		return "plot X " + x0 + ".." + x1 + " / Z " + z0 + ".." + z1 + "  (99x99, from " + source + ")";
	}

	/** Is this column off the island's own square. False whenever the boundary is unknown. */
	static boolean outside(int x, int z) {
		if (!known()) return false;
		return x < x0 || x > x1 || z < z0 || z > z1;
	}

	/** How far off the line, in blocks, on the worse axis. 0 when inside or unknown. */
	static int over(int x, int z) {
		if (!known()) return 0;
		int dx = Math.max(0, Math.max(x0 - x, x - x1));
		int dz = Math.max(0, Math.max(z0 - z, z - z1));
		return Math.max(dx, dz);
	}
}
