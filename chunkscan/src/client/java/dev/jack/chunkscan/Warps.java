package dev.jack.chunkscan;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import net.minecraft.client.Minecraft;
import net.minecraft.client.player.LocalPlayer;
import net.minecraft.core.BlockPos;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

/**
 * Teleports as a ROUTING PRIMITIVE, not just as a rescue.
 *
 * <p>{@link Nav} searches 3D at up to 512 blocks and this island is 240 tall, so a deck-to-lowland
 * leg is a real flight. {@code /is} and {@code /is warp <name>} make some of those legs free, and
 * {@link Autopilot} already types {@code /is} — but only when falling. Using the same command
 * because it is SHORTER is the same call in a different place, and it was never made.
 *
 * <p>Four rules, and three of them are about not making things worse:
 *
 * <ul>
 *   <li><b>A warp must actually save something.</b> {@link #MIN_SAVING} blocks, or the trip is a
 *       teleport plus most of the flight you were already making. Warping 30 blocks is theatre.</li>
 *   <li><b>The destination is where the warp LANDS, which is not where you typed it.</b> Every
 *       warp is recorded by standing at its arrival point, so the saving is measured against a
 *       position that was observed rather than assumed.</li>
 *   <li><b>Rate-limited and announced.</b> A teleport moves you across the island: doing one
 *       silently, or twice in ten seconds because the plan flickered, is how an unattended loop
 *       becomes unusable.</li>
 *   <li><b>Coordinates mean nothing without a world.</b> Warps are keyed to the server they were
 *       recorded on, and a warp from another server is not offered — the same rule the wand's box
 *       and the strike list both live under.</li>
 * </ul>
 */
final class Warps {
	static final String FILE = "warps.json";
	/** Below this a warp costs a command and a load screen to save a few seconds of flying. */
	static final int MIN_SAVING = 80;
	static final long COOLDOWN_MS = 15_000;

	static final class Warp {
		String name = "";                 // "" is bare `/is`
		String server = "";
		int x, y, z;
		String note = "";

		String command() {
			return name.isBlank() ? "is" : "is warp " + name;
		}

		BlockPos pos() {
			return new BlockPos(x, y, z);
		}
	}

	static final class Book {
		List<Warp> warps = new ArrayList<>();
	}

	private static long lastWarpAt;
	private static boolean enabled = true;

	private Warps() {}

	static boolean enabled() {
		return enabled;
	}

	static void enabled(boolean v) {
		enabled = v;
	}

	static Book load(Path dir) {
		Path f = dir.resolve(FILE);
		if (!Files.exists(f)) return new Book();
		try {
			JsonObject root = JsonParser.parseString(Files.readString(f, StandardCharsets.UTF_8)).getAsJsonObject();
			Book b = new Gson().fromJson(root, Book.class);
			return b == null ? new Book() : b;
		} catch (Exception e) {
			ChunkScanClient.LOG.warn("warps.json unreadable: {}", e.toString());
			return new Book();
		}
	}

	static void save(Path dir, Book b) throws Exception {
		Files.createDirectories(dir);
		Files.writeString(dir.resolve(FILE),
			new GsonBuilder().setPrettyPrinting().create().toJson(b), StandardCharsets.UTF_8);
	}

	static String server(Minecraft mc) {
		return mc.getCurrentServer() == null ? "singleplayer" : mc.getCurrentServer().ip;
	}

	/** Record where you are standing as the ARRIVAL POINT of `name` (empty name = bare /is). */
	static String add(Minecraft mc, String name) throws Exception {
		LocalPlayer p = mc.player;
		if (p == null) return "no player";
		Path dir = ScanRunner.schematicsDir(mc);
		Book b = load(dir);
		String key = name == null ? "" : name.trim().toLowerCase(Locale.ROOT);
		b.warps.removeIf(w -> w.name.equalsIgnoreCase(key) && w.server.equals(server(mc)));
		Warp w = new Warp();
		w.name = key;
		w.server = server(mc);
		w.x = p.getBlockX();
		w.y = p.getBlockY();
		w.z = p.getBlockZ();
		b.warps.add(w);
		save(dir, b);
		return "recorded " + (key.isBlank() ? "/is" : "/is warp " + key) + " landing at "
			+ w.x + " " + w.y + " " + w.z + " — STAND WHERE IT DROPS YOU, not where you type it";
	}

	static String remove(Minecraft mc, String name) throws Exception {
		Path dir = ScanRunner.schematicsDir(mc);
		Book b = load(dir);
		String key = name == null ? "" : name.trim().toLowerCase(Locale.ROOT);
		boolean gone = b.warps.removeIf(w -> w.name.equalsIgnoreCase(key));
		save(dir, b);
		return gone ? "forgot warp \"" + key + "\"" : "no warp called \"" + key + "\"";
	}

	static List<Warp> forServer(Minecraft mc) {
		List<Warp> out = new ArrayList<>();
		try {
			for (Warp w : load(ScanRunner.schematicsDir(mc)).warps) {
				if (w.server.equals(server(mc))) out.add(w);
			}
		} catch (Exception ignored) {
			// no schematics dir yet: no warps, which is the honest answer
		}
		return out;
	}

	/**
	 * The warp worth taking to get from {@code from} to {@code to}, or null.
	 *
	 * <p>Pure, so the arithmetic is testable without a client: the saving is
	 * {@code dist(from,to) - dist(warp,to)}, and a warp that lands further away than you already
	 * are is not a shortcut however close its name sounds.
	 */
	static Warp best(List<Warp> warps, BlockPos from, BlockPos to) {
		double direct = Math.sqrt(from.distSqr(to));
		Warp best = null;
		double bestLeft = direct - MIN_SAVING;
		for (Warp w : warps) {
			double left = Math.sqrt(w.pos().distSqr(to));
			if (left < bestLeft) {
				best = w;
				bestLeft = left;
			}
		}
		return best;
	}

	/** How many blocks this warp saves on that trip. */
	static int saving(Warp w, BlockPos from, BlockPos to) {
		return (int) Math.round(Math.sqrt(from.distSqr(to)) - Math.sqrt(w.pos().distSqr(to)));
	}

	static boolean cooling(long now) {
		return now - lastWarpAt < COOLDOWN_MS;
	}

	/** Take it. Returns the message to show, or null when nothing was done. */
	static String take(Minecraft mc, Warp w, BlockPos to) {
		if (mc.player == null || !enabled || cooling(System.currentTimeMillis())) return null;
		lastWarpAt = System.currentTimeMillis();
		mc.player.connection.sendCommand(w.command());
		return "warping (/" + w.command() + ") — saves about "
			+ saving(w, mc.player.blockPosition(), to) + "m of flying";
	}
}
