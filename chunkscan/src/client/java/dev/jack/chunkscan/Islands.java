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

    record Bounds(int minX, int minZ, int maxXExclusive, int maxZExclusive) {
        Bounds {
            if (minX >= maxXExclusive || minZ >= maxZExclusive) throw new IllegalArgumentException("Empty/inverted island bounds");
        }
        boolean contains(int x, int z) {
            return x >= minX && x < maxXExclusive && z >= minZ && z < maxZExclusive;
        }
        int over(int x, int z) {
            long dx = Math.max(0L, Math.max((long) minX - x, (long) x - maxXExclusive + 1));
            long dz = Math.max(0L, Math.max((long) minZ - z, (long) z - maxZExclusive + 1));
            return (int) Math.min(Integer.MAX_VALUE, Math.max(dx, dz));
        }
    }

    record Island(String name, int cx, int cz, int radius, String owner, Bounds bounds, String site) {
        boolean contains(int x, int z) { return bounds.contains(x, z); }
        int over(int x, int z) { return bounds.over(x, z); }
    }

    private static Island parse(String name, JsonObject o) {
        int cx = o.get("cx").getAsInt(), cz = o.get("cz").getAsInt();
        int radius = o.has("radius") ? o.get("radius").getAsInt() : 49;
        if (radius < 0) throw new IllegalArgumentException("Negative island radius");
        Bounds bounds;
        if (o.has("bounds")) {
            JsonObject b = o.getAsJsonObject("bounds");
            bounds = new Bounds(b.get("min_x").getAsInt(), b.get("min_z").getAsInt(),
                b.get("max_x_exclusive").getAsInt(), b.get("max_z_exclusive").getAsInt());
        } else bounds = new Bounds(Math.subtractExact(cx, radius), Math.subtractExact(cz, radius),
            Math.addExact(Math.addExact(cx, radius), 1), Math.addExact(Math.addExact(cz, radius), 1));
        if (!bounds.contains(cx, cz)) throw new IllegalArgumentException("Bedrock outside island bounds");
        String site = o.has("site") ? o.get("site").getAsString() : name;
        if (site.isBlank()) throw new IllegalArgumentException("Empty island site");
        return new Island(name, cx, cz, radius, o.has("owner") ? o.get("owner").getAsString() : "", bounds, site);
    }

	// KEYED BY DIRECTORY, not just by time. Cached on the clock alone, a second schematics folder
	// silently gets the first one's islands — which is benign today (there is one folder) and is
	// exactly the latent bug that bites the day there are two. Its own test found this.
	private static final Map<String, Map<String, Island>> cache = new LinkedHashMap<>();
	private static final Map<String, Long> cachedAt = new LinkedHashMap<>();

	private Islands() {}

	static synchronized Map<String, Island> all(Path dir) {
        dir = ActiveBuild.siteInputs(dir);
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
                        out.put(e.getKey(), parse(e.getKey(), o));
					}
				}
			} catch (Exception e) {
				ChunkScanClient.LOG.warn("islands.json unreadable: {}", e.toString());
                out.clear(); // Never retain a partially parsed authorization registry.
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
            if (i.contains(x, z)) return i;
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

    /** Known registries authorize only their exact plot union. Missing registries retain legacy Plot behavior. */
    static boolean outside(Path dir, int x, int z) {
        Map<String, Island> islands = all(dir);
        if (islands.isEmpty()) return Files.exists(ActiveBuild.siteInputs(dir).resolve(FILE)) || Plot.outside(x, z);
        return islands.values().stream().noneMatch(i -> i.contains(x, z));
    }

    static boolean storageOnSite(Path dir, Island source, int x, int z) {
        return all(dir).values().stream().anyMatch(i -> i.site().equals(source.site()) && i.contains(x, z));
    }

	static int over(Path dir, int x, int z) {
		Island i = at(dir, x, z);
		if (i == null) return all(dir).isEmpty() ? Plot.over(x, z) : 0;
		return i.over(x, z);
	}

	static String describe(Minecraft mc, Path dir) {
		Map<String, Island> all = all(dir);
		if (all.isEmpty()) {
			return Files.exists(ActiveBuild.siteInputs(dir).resolve(FILE)) ? "island registry empty or invalid — automatic placement disabled" : "no island registry — falling back to the single plot: " + Plot.describe()
				+ "\n  python -m mcbuild islands --add <name> --from <capture> to record more";
		}
		Island h = here(mc, dir);
		StringBuilder b = new StringBuilder(all.size() + " island(s) known");
		if (h != null) {
			b.append("\n  you are on ").append(h.name())
				.append(h.owner().isBlank() ? "" : " (" + h.owner() + "'s)")
				.append("  X ").append(h.bounds().minX()).append("..").append(h.bounds().maxXExclusive() - 1)
				.append(" Z ").append(h.bounds().minZ()).append("..").append(h.bounds().maxZExclusive() - 1);
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
