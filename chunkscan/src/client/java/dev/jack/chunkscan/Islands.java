package dev.jack.chunkscan;

import com.google.gson.Gson;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import net.minecraft.client.Minecraft;
import net.minecraft.core.BlockPos;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Which island you are standing on — so alt 2 can walk onto alt 1's island and build there.
 *
 * <p>Everything in this mod has assumed one island, because there was one. {@link Plot} carried a
 * single square baked in at export time; {@link Fleet} claimed designs with no idea where they
 * were. Both hold right up until a second account has its own island and the same tooling visits
 * it.
 *
 * <p><b>AN ISLAND IS IDENTIFIED BY ITS BEDROCK, NOT BY WHOSE IT IS.</b> Every skyblock island has
 * exactly one bedrock at its origin, which is already how the plot is found. So the bedrock
 * coordinate IS the identity: stable, discoverable, and indifferent to who is standing on it.
 * Keying off the account would break the moment an alt walks next door, which is the entire case
 * this exists to support.
 *
 * <p><b>OWNERSHIP IS A LABEL, NOT A PERMISSION.</b> It makes a report read sensibly and it never
 * decides who may build — a tool that refused alt 2 on alt 1's island would be enforcing a rule
 * the server does not have.
 *
 * <p>Read from {@code islands.json}, written by {@code python -m mcbuild islands --add}. When the
 * file is absent everything falls back to the single baked-in plot, so a setup that has never
 * heard of a second island behaves exactly as it did.
 */
final class Islands {
	static final String FILE = "islands.json";
	/** Islands sit far apart; the plot is 99 wide and the void between them is much larger. */
	static final int NEAR = 256;

	record Island(String name, int cx, int cz, int radius, String owner) {
		boolean contains(int x, int z) {
			return Math.abs(x - cx) <= radius && Math.abs(z - cz) <= radius;
		}

		int over(int x, int z) {
			int dx = Math.max(0, Math.abs(x - cx) - radius);
			int dz = Math.max(0, Math.abs(z - cz) - radius);
			return Math.max(dx, dz);
		}
	}

	// KEYED BY DIRECTORY, not just by time. Cached on the clock alone, a second schematics folder
	// silently gets the first one's islands — which is benign today (there is one folder) and is
	// exactly the latent bug that bites the day there are two. Its own test found this.
	private static final Map<String, Map<String, Island>> cache = new LinkedHashMap<>();
	private static final Map<String, Long> cachedAt = new LinkedHashMap<>();

	private Islands() {}

	static synchronized Map<String, Island> all(Path dir) {
		// Re-read now and then rather than once: the registry is written by the Python side while
		// the game is running, and a client that cached it at login would never see a new island.
		String key = dir.toString();
		Long when = cachedAt.get(key);
		if (when != null && System.currentTimeMillis() - when < 30_000) return cache.get(key);
		Map<String, Island> out = new LinkedHashMap<>();
		Path f = dir.resolve(FILE);
		if (Files.exists(f)) {
			try {
				JsonObject root = JsonParser.parseString(Files.readString(f, StandardCharsets.UTF_8))
					.getAsJsonObject();
				JsonObject isls = root.getAsJsonObject("islands");
				if (isls != null) {
					for (var e : isls.entrySet()) {
						JsonObject o = e.getValue().getAsJsonObject();
						out.put(e.getKey(), new Island(e.getKey(),
							o.get("cx").getAsInt(), o.get("cz").getAsInt(),
							o.has("radius") ? o.get("radius").getAsInt() : 49,
							o.has("owner") ? o.get("owner").getAsString() : ""));
					}
				}
			} catch (Exception e) {
				ChunkScanClient.LOG.warn("islands.json unreadable: {}", e.toString());
			}
		}
		cache.put(key, out);
		cachedAt.put(key, System.currentTimeMillis());
		return out;
	}

	/**
	 * The island nearest this coordinate, or null.
	 *
	 * <p>NEAREST BEDROCK WITHIN RANGE, not "inside the plot": a build on the rim, a flight between
	 * two islands and a player hanging in the void between them all need an answer, and "outside
	 * every plot" is not the same as "nowhere".
	 */
	static Island at(Path dir, int x, int z) {
		Island best = null;
		int bestD = Integer.MAX_VALUE;
		for (Island i : all(dir).values()) {
			int d = Math.max(Math.abs(x - i.cx()), Math.abs(z - i.cz()));
			if (d <= NEAR && d < bestD) {
				best = i;
				bestD = d;
			}
		}
		return best;
	}

	/** The island the player is standing on, or null. */
	static Island here(Minecraft mc, Path dir) {
		if (mc.player == null) return null;
		BlockPos p = mc.player.blockPosition();
		return at(dir, p.getX(), p.getZ());
	}

	/**
	 * Is this column off the buildable square of whatever island it belongs to.
	 *
	 * <p>Falls back to the single baked-in {@link Plot} when no registry exists, so a setup that
	 * has never heard of a second island is unchanged. <b>And an unknown island is not an
	 * off-plot one</b>: somewhere the registry has never been told about answers "I cannot say",
	 * the same posture {@code Plot} already takes when the bedrock was never found.
	 */
	static boolean outside(Path dir, int x, int z) {
		Island i = at(dir, x, z);
		if (i == null) return all(dir).isEmpty() && Plot.outside(x, z);
		return !i.contains(x, z);
	}

	static int over(Path dir, int x, int z) {
		Island i = at(dir, x, z);
		if (i == null) return all(dir).isEmpty() ? Plot.over(x, z) : 0;
		return i.over(x, z);
	}

	static String describe(Minecraft mc, Path dir) {
		Map<String, Island> all = all(dir);
		if (all.isEmpty()) {
			return "no island registry — falling back to the single plot: " + Plot.describe()
				+ "\n  python -m mcbuild islands --add <name> --from <capture> to record more";
		}
		Island h = here(mc, dir);
		StringBuilder b = new StringBuilder(all.size() + " island(s) known");
		if (h != null) {
			b.append("\n  you are on ").append(h.name())
				.append(h.owner().isBlank() ? "" : " (" + h.owner() + "'s)")
				.append("  X ").append(h.cx() - h.radius()).append("..").append(h.cx() + h.radius())
				.append(" Z ").append(h.cz() - h.radius()).append("..").append(h.cz() + h.radius());
			if (mc.player != null) {
				int o = h.over(mc.player.getBlockX(), mc.player.getBlockZ());
				b.append(o > 0 ? "  — you are " + o + " OUTSIDE it" : "  — you are inside it");
			}
		} else {
			b.append("\n  you are not on any island the registry knows");
		}
		for (Island i : all.values()) {
			if (h != null && i.name().equals(h.name())) continue;
			b.append("\n  ").append(i.name()).append("  bedrock ").append(i.cx()).append(" ")
				.append(i.cz()).append(i.owner().isBlank() ? "" : "  owner " + i.owner());
		}
		b.append("\n  ownership is a LABEL: any alt may build on any of them");
		return b.toString();
	}
}
