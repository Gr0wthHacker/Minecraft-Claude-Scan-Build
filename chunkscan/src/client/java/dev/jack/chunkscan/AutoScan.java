package dev.jack.chunkscan;

import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.minecraft.client.Minecraft;
import net.minecraft.network.chat.Component;

/** `/cscan auto <name> <minutes>` — rescan on a timer while building, so the archive has a real history. */
final class AutoScan {
	private static String name;
	private static int radius = 8;
	private static long everyMs;
	private static long nextAt;

	private AutoScan() {}

	static void register() {
		ClientTickEvents.END_CLIENT_TICK.register(AutoScan::tick);
	}

	static void start(String scanName, int minutes, int scanRadius) {
		name = scanName;
		everyMs = minutes * 60_000L;
		radius = scanRadius;
		nextAt = System.currentTimeMillis() + everyMs;
	}

	static void stop() {
		name = null;
	}

	static boolean running() {
		return name != null;
	}

	static String status() {
		if (name == null) return "auto-scan off";
		long left = Math.max(0, nextAt - System.currentTimeMillis()) / 1000;
		return "auto-scan " + name + " every " + (everyMs / 60_000) + " min (next in " + left + "s)";
	}

	private static void tick(Minecraft mc) {
		if (name == null || mc.level == null || mc.player == null) return;
		if (System.currentTimeMillis() < nextAt) return;
		nextAt = System.currentTimeMillis() + everyMs;
		try {
			ScanResult r = ScanRunner.scan(mc, name, radius, false);
			mc.player.sendSystemMessage(Component.literal("[cscan] auto: " + r.summaryLines().get(0)));
		} catch (Exception e) {
			ChunkScanClient.LOG.warn("auto-scan failed", e);
			mc.player.sendSystemMessage(Component.literal("[cscan] auto-scan failed: " + e.getMessage()));
		}
	}
}
