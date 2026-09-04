package dev.jack.chunkscan;

import net.minecraft.client.Minecraft;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import java.util.*;

/** Discover loaded storage on the design island, then open it to obtain server-sent contents. */
final class ChestScan {
	private static final Map<Long, Long> attempted = new HashMap<>();
	private static Object level;
	private static BlockPos target;
	private static long started;
	static void reset() { attempted.clear(); target = null; level = null; }

	static boolean advance(Minecraft mc, String design, Map<String, Storage.Container> indexed) {
		if (!ContainerWatcher.enabled) return false;
		if (level != mc.level) { reset(); level = mc.level; }
		long now = System.currentTimeMillis();
		if (target != null && (now - started > 30_000 || Withdraw.recentlyFailed(target, now))) target = null;
		try {
			if (target == null) {
				var dir = ScanRunner.schematicsDir(mc);
				BlockPos origin = Designs.load(dir, design).origin();
				Map<String, Storage.Container> candidates = new LinkedHashMap<>();
				int cx = mc.player.getBlockX() >> 4, cz = mc.player.getBlockZ() >> 4;
				for (int x = cx - 16; x <= cx + 16; x++) for (int z = cz - 16; z <= cz + 16; z++) {
					if (!mc.level.getChunkSource().hasChunk(x, z)) continue;
					for (BlockPos p : mc.level.getChunk(x, z).getBlockEntities().keySet()) {
						String block = BuiltInRegistries.BLOCK.getKey(mc.level.getBlockState(p).getBlock()).getPath();
						if (!Storage.buildStorage(block) || attempted.getOrDefault(p.asLong(), 0L) > now) continue;
						Storage.Container c = new Storage.Container();
						c.x = p.getX(); c.y = p.getY(); c.z = p.getZ(); c.block = block;
						c.dimension = mc.level.dimension().identifier().toString();
						// Existing records are refreshed after five minutes if no stock can be found.
						Storage.Container old = indexed.get(c.key());
						if (old != null && !old.updated.isBlank()) {
							try { if (now - java.time.Instant.parse(old.updated).toEpochMilli() < 300_000) continue; }
							catch (RuntimeException ignored) { }
						}
						candidates.put(c.key(), c);
					}
				}
				target = Storage.scoped(candidates, dir, origin, mc.level.dimension().identifier().toString()).values()
					.stream().map(Storage.Container::pos).min(Comparator.comparingDouble(p -> p.distSqr(mc.player.blockPosition())))
					.orElse(null);
				if (target == null) return false;
				attempted.put(target.asLong(), now + 300_000);
				started = now;
			}
			BlockPos approach = ContainerInteraction.approach(mc, target);
			Hud.guide(approach == null ? target : approach,
				approach == null ? "find approach to scan island storage" : "scan island storage");
			if (ContainerInteraction.openingHit(mc, target) != null) {
				Withdraw.inspect(target);
				target = null;
			}
			return true;
		} catch (Exception e) {
			ChunkScanClient.LOG.warn("storage discovery: {}", e.toString());
			return false;
		}
	}
}
