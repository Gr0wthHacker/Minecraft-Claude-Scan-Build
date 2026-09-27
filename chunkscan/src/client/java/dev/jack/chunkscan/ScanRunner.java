package dev.jack.chunkscan;

import net.minecraft.client.Minecraft;
import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.client.multiplayer.ServerData;
import net.minecraft.client.player.LocalPlayer;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.Comparator;
import java.util.List;
import java.util.regex.Pattern;

/** Glue: validate → capture → write .litematic + .scan.json into the Litematica schematics folder. */
final class ScanRunner {
	private static final Pattern SAFE_NAME = Pattern.compile("[A-Za-z0-9_\\-.]{1,64}");

	private ScanRunner() {}

	static Path schematicsDir(Minecraft mc) {
		return mc.gameDirectory.toPath().resolve("schematics");
	}

	/** Capture exactly the box Litematica currently has selected. */
	static ScanResult scanSelection(Minecraft mc, String name) throws ScanException, IOException {
		int[] box;
		try {
			box = Litematica.present() ? Litematica.currentSelection() : null;
		} catch (Exception e) {
			throw new ScanException("could not read the Litematica selection: " + e);
		}
		if (box == null) throw new ScanException("no Litematica area selection (make one, or use /cscan <name>)");
		return scan(mc, name, 0, false, box);
	}

	static ScanResult scan(Minecraft mc, String name, int radius, boolean chunkAligned) throws ScanException, IOException {
		return scan(mc, name, radius, chunkAligned, null);
	}

	static ScanResult scan(Minecraft mc, String name, int radius, boolean chunkAligned, int[] box) throws ScanException, IOException {
		ClientLevel level = mc.level;
		LocalPlayer player = mc.player;
		if (level == null || player == null) throw new ScanException("not in a world");
		if (!SAFE_NAME.matcher(name).matches()) throw new ScanException("name: letters, digits, _ - . only");

		// A SCAN MUST NOT WRITE OVER A DESIGN. They share one folder and one namespace, and until
		// this check existed a scan simply overwrote whatever was there. It happened: `/cscan Falls`
		// replaced the 30-block Falls design with a 111,631-block island capture and took its 41
		// dig cells with it — including the notch that has to be cut LAST, because pulling it early
		// floods the trench you are standing in. The design survived only because a copy lives in
		// the repo; the shipped one was gone, `/cscan dig Falls` reported nothing to clear, and the
		// design was still in the tracked list, so `/cscan place` would have pasted an island onto
		// the island.
		//
		// The scan's own output is never at risk here: a capture sidecar is not a design sidecar,
		// so re-scanning `island` over yesterday's `island` still works, which is the whole daily
		// loop. Only a DESIGN is protected, and the message says how to mean it.
		if (Designs.designExists(schematicsDir(mc), name)) {
			throw new ScanException("\"" + name + "\" is a DESIGN, not a scan name — scanning would "
				+ "destroy it and its dig list. Pick another name, or move the design first.");
		}

		long t0 = System.nanoTime();
		Capture cap = box != null ? WorldCapture.captureBox(level, box)
			: WorldCapture.capture(level, player.chunkPosition(), radius, chunkAligned);

		Path dir = schematicsDir(mc);
		Files.createDirectories(dir);
		Path lit = dir.resolve(name + ".litematic");
		Path json = dir.resolve(name + ".scan.json");

		String where = describeWorld(mc, level);
		String author = player.getName().getString();
		String description = "chunkscan | " + where + " | origin "
			+ cap.originX() + " " + cap.originY() + " " + cap.originZ()
			+ (box != null ? " | selection" : chunkAligned ? " | chunk-aligned" : "") + " | r=" + radius;
		LitematicWriter.write(lit, cap, name, author, description);
		SidecarWriter.write(json, cap, name, lit.getFileName().toString(), mc, level, player, radius, chunkAligned);
		archive(dir, name, lit, json);

		long ms = (System.nanoTime() - t0) / 1_000_000;
		ChunkScanClient.LOG.info("saved {} ({} blocks, {} ms)", lit, cap.nonAirCount(), ms);
		return new ScanResult(cap, lit, json, ms);
	}

	/**
	 * How many timestamped copies of one scan name to keep. `/cscan auto` writes one per tick
	 * forever, so without a cap this only ever grows — it was 24 files and 1.6 MB when first noted
	 * and 56 files and 4.4 MB by the time anyone measured it again. Twelve is enough to diff a
	 * fortnight of daily scans and small enough that an auto-scan session cannot fill a disk.
	 */
	static final int KEEP_ARCHIVED = 12;

	/** Every scan is also kept as schematics/scans/<name>_<yyyyMMdd-HHmm>.* so history can be diffed. */
	private static void archive(Path dir, String name, Path lit, Path json) throws IOException {
		Path scans = dir.resolve("scans");
		Files.createDirectories(scans);
		String stamp = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMdd-HHmm"));
		Files.copy(lit, scans.resolve(name + "_" + stamp + ".litematic"), StandardCopyOption.REPLACE_EXISTING);
		Files.copy(json, scans.resolve(name + "_" + stamp + ".scan.json"), StandardCopyOption.REPLACE_EXISTING);
		prune(scans, name);
	}

	/**
	 * Drop the oldest archived copies of ONE scan name, keeping {@link #KEEP_ARCHIVED}.
	 *
	 * <p>Scoped to the name on purpose: pruning the whole folder to a global count would let a
	 * chatty auto-scan evict the one hand-made capture a design was verified against. Sorted by
	 * FILENAME, which carries the timestamp — file mtime moves when a folder is copied or synced,
	 * and the name does not.
	 *
	 * <p>Failures here are swallowed. Losing an archive copy is a housekeeping problem; failing the
	 * scan that has already been written to disk because the tidy-up threw is a worse one.
	 */
	private static void prune(Path scans, String name) {
		try (var s = Files.list(scans)) {
			List<Path> mine = s.filter(p -> {
					String n = p.getFileName().toString();
					return n.startsWith(name + "_") && n.endsWith(".litematic");
				})
				.sorted(Comparator.comparing(p -> p.getFileName().toString()))
				.collect(java.util.stream.Collectors.toList());
			for (int i = 0; i < mine.size() - KEEP_ARCHIVED; i++) {
				String base = mine.get(i).getFileName().toString();
				base = base.substring(0, base.length() - ".litematic".length());
				Files.deleteIfExists(scans.resolve(base + ".litematic"));
				Files.deleteIfExists(scans.resolve(base + ".scan.json"));
			}
		} catch (IOException ignored) {
		}
	}

	static String describeWorld(Minecraft mc, ClientLevel level) {
		ServerData server = mc.getCurrentServer();
		String world = server != null ? server.ip : "singleplayer";
		return world + " " + level.dimension().identifier();
	}
}
