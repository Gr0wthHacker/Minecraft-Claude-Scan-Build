package dev.jack.chunkscan;

import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.minecraft.client.Minecraft;
import net.minecraft.core.BlockPos;
import net.minecraft.gizmos.GizmoStyle;
import net.minecraft.gizmos.Gizmos;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

/**
 * Marks blocks in the world with outlined, filled boxes - a design's dig list, the next cells to
 * place, the containers a search matched.
 *
 * This used to be coloured dust particles, and they were the wrong tool for "these blocks must go":
 * faint, washed out against a mossy floor, easy to switch off in video settings, and a thin trail of
 * smoke never tells you WHICH block. MC 26.2 ships a gizmo system, so a highlight is a real box now -
 * a bright stroke, a translucent fill, and always-on-top so the ones behind walls still read.
 *
 * Gizmos are collected per tick and drawn for that frame, so batches are re-submitted every tick
 * rather than registered once. That is what Minecraft.collectPerTickGizmos() is for.
 */
final class Highlight {
	private static final List<Batch> BATCHES = new ArrayList<>();
	/** Past this the boxes are noise, and thousands of them cost frames. */
	static final int RADIUS = 128;
	/** Hard cap per batch: a belly dig list runs to thousands and you only act on the near ones. */
	private static final int MAX_PER_BATCH = 512;

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

	/** How many of a batch are actually being drawn, so a command can say when you are out of range. */
	static int visible(Minecraft mc, String id) {
		if (mc.player == null) return 0;
		BlockPos me = mc.player.blockPosition();
		long r2 = (long) RADIUS * RADIUS;
		for (Batch b : BATCHES) {
			if (!b.id().equals(id)) continue;
			int n = 0;
			for (BlockPos p : b.blocks()) {
				if (p.distSqr(me) <= r2) n++;
			}
			return Math.min(n, MAX_PER_BATCH);
		}
		return 0;
	}

	private static void tick(Minecraft mc) {
		// A THROW OUT OF A TICK EVENT IS A CLIENT CRASH. The pre-upload audit guarded the two ticks
		// that drive movement and looting on exactly this ground and missed this one, which is the
		// busiest of the lot - every highlight layer redraws here on every tick, over block lists
		// the caller supplied. Drawing is never worth taking the client down for.
		try {
			draw(mc);
		} catch (Exception e) {
			BATCHES.clear();                       // whatever was malformed, stop redrawing it
		}
	}

	private static void draw(Minecraft mc) {
		if (mc.level == null || mc.player == null || BATCHES.isEmpty()) return;
		long now = System.currentTimeMillis();
		BATCHES.removeIf(b -> b.until() < now);
		if (BATCHES.isEmpty()) return;
		BlockPos me = mc.player.blockPosition();
		long r2 = (long) RADIUS * RADIUS;
		try (var ignored = mc.collectPerTickGizmos()) {
			for (Batch b : BATCHES) {
				GizmoStyle style = GizmoStyle.strokeAndFill(0xFF000000 | b.color(), 2.5f,
					0x40000000 | (b.color() & 0xFFFFFF));
				List<BlockPos> near = new ArrayList<>();
				for (BlockPos p : b.blocks()) {
					if (p.distSqr(me) <= r2) near.add(p);
				}
				if (near.size() > MAX_PER_BATCH) {
					near.sort(Comparator.comparingDouble(p -> p.distSqr(me)));
					near = near.subList(0, MAX_PER_BATCH);
				}
				for (BlockPos p : near) {
					Gizmos.cuboid(p, style).setAlwaysOnTop();
				}
			}
		}
	}
}
