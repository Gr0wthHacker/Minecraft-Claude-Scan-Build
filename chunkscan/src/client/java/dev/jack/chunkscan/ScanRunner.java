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
import java.util.regex.Pattern;

/** Glue: validate → capture → write .litematic + .scan.json into the Litematica schematics folder. */
final class ScanRunner {
	private static final Pattern SAFE_NAME = Pattern.compile("[A-Za-z0-9_\\-.]{1,64}");

	private ScanRunner() {}

	static ScanResult scan(Minecraft mc, String name, int radius, boolean chunkAligned) throws ScanException, IOException {
		ClientLevel level = mc.level;
		LocalPlayer player = mc.player;
		if (level == null || player == null) throw new ScanException("not in a world");
		if (!SAFE_NAME.matcher(name).matches()) throw new ScanException("name: letters, digits, _ - . only");

		long t0 = System.nanoTime();
		Capture cap = WorldCapture.capture(level, player.chunkPosition(), radius, chunkAligned);

		Path dir = mc.gameDirectory.toPath().resolve("schematics");
		Files.createDirectories(dir);
		Path lit = dir.resolve(name + ".litematic");
		Path json = dir.resolve(name + ".scan.json");

		String where = describeWorld(mc, level);
		String author = player.getName().getString();
		String description = "chunkscan | " + where + " | origin "
			+ cap.originX() + " " + cap.originY() + " " + cap.originZ()
			+ (chunkAligned ? " | chunk-aligned" : "") + " | r=" + radius;
		LitematicWriter.write(lit, cap, name, author, description);
		SidecarWriter.write(json, cap, name, lit.getFileName().toString(), mc, level, player, radius, chunkAligned);
		archive(dir, name, lit, json);

		long ms = (System.nanoTime() - t0) / 1_000_000;
		ChunkScanClient.LOG.info("saved {} ({} blocks, {} ms)", lit, cap.nonAirCount(), ms);
		return new ScanResult(cap, lit, json, ms);
	}

	/** Every scan is also kept as schematics/scans/<name>_<yyyyMMdd-HHmm>.* so history can be diffed. */
	private static void archive(Path dir, String name, Path lit, Path json) throws IOException {
		Path scans = dir.resolve("scans");
		Files.createDirectories(scans);
		String stamp = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMdd-HHmm"));
		Files.copy(lit, scans.resolve(name + "_" + stamp + ".litematic"), StandardCopyOption.REPLACE_EXISTING);
		Files.copy(json, scans.resolve(name + "_" + stamp + ".scan.json"), StandardCopyOption.REPLACE_EXISTING);
	}

	static String describeWorld(Minecraft mc, ClientLevel level) {
		ServerData server = mc.getCurrentServer();
		String world = server != null ? server.ip : "singleplayer";
		return world + " " + level.dimension().identifier();
	}
}
