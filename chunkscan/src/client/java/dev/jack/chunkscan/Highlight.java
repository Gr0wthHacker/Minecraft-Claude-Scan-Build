package dev.jack.chunkscan;

import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.minecraft.client.Minecraft;
import net.minecraft.core.BlockPos;
import net.minecraft.core.particles.DustParticleOptions;

import java.util.ArrayList;
import java.util.List;

/**
 * Marks blocks in the world with coloured dust particles for a while — used to show a design's dig list
 * and to point at the containers a search matched. Particles instead of a custom renderer: same job,
 * no render-pipeline coupling, works through walls at close range.
 */
final class Highlight {
	private static final List<Batch> BATCHES = new ArrayList<>();
	/** Particles stop rendering well past this; the belly dig list is far bigger than one screenful. */
	private static final int RADIUS = 128;

	private record Batch(String id, List<BlockPos> blocks, int color, long until) {}

	private Highlight() {}

	static void register() {
		ClientTickEvents.END_CLIENT_TICK.register(Highlight::tick);
	}

	/** Replace the batch with this id. Keyed by id, not colour: two designs sharing a colour used to
	 *  silently wipe each other out. */
	static void show(String id, List<BlockPos> blocks, int color, int seconds) {
		BATCHES.removeIf(b -> b.id().equals(id));
		BATCHES.add(new Batch(id, new ArrayList<>(blocks), color, System.currentTimeMillis() + seconds * 1000L));
	}

	static void clear(String id) {
		BATCHES.removeIf(b -> b.id().equals(id));
	}

	static void clear() {
		BATCHES.clear();
	}

	static int count() {
		return BATCHES.stream().mapToInt(b -> b.blocks().size()).sum();
	}

	private static void tick(Minecraft mc) {
		if (mc.level == null || mc.player == null || BATCHES.isEmpty()) return;
		long now = System.currentTimeMillis();
		BATCHES.removeIf(b -> b.until() < now);
		if ((mc.level.getGameTime() % 4) != 0) return;                 // 5 times a second is plenty
		BlockPos me = mc.player.blockPosition();
		for (Batch b : BATCHES) {
			DustParticleOptions dust = new DustParticleOptions(b.color(), 1.4f);
			for (BlockPos p : b.blocks()) {
				if (p.distSqr(me) > RADIUS * RADIUS) continue;
				mc.level.addParticle(dust, true, true, p.getX() + 0.5, p.getY() + 0.55, p.getZ() + 0.5, 0, 0, 0);
			}
		}
	}
}
