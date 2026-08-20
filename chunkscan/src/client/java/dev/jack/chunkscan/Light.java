package dev.jack.chunkscan;

import net.minecraft.core.BlockPos;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.LightLayer;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

/**
 * Where mobs can spawn: standable cells the light does not reach.
 *
 * <p><b>This is the one question only the client can answer.</b> The desktop tooling has always
 * approximated it by DISTANCE — "95% of the deck is within 7 of a light" — and that figure is a
 * lower bound on darkness, because light does not pass through walls and this island is nothing but
 * walls: a belly, an undercroft, a deck, a vault, a store hall. Off the capture, 462 light sources
 * over 14,457 standable cells leaves ~10% more than 7 blocks from ANY source before geometry is
 * considered at all. The real figure has never been measured.
 *
 * <p>The client has the actual light engine, so it can just be read.
 */
final class Light {
	/**
	 * Block light strictly below this and a hostile mob can spawn.
	 *
	 * <p>1.19's rule is blockLight == 0 for most of the overworld, but the server is 1.19 and the
	 * client is 26.2 and neither of us should be betting a dark corner on which rule is live.
	 * Reporting at 8 shows the margin as well as the breach, and {@link #SPAWNABLE} is the number
	 * that actually gets called dangerous.
	 */
	static final int DIM = 8;
	/** Below this it is not dim, it is a spawner. */
	static final int SPAWNABLE = 1;

	record Spot(BlockPos pos, int block, int sky) {
		boolean spawnable() {
			return block < SPAWNABLE;
		}
	}

	record Report(List<Spot> spots, int checked, int dim, int spawnable) {}

	private Light() {}

	static int blockLight(Level level, BlockPos p) {
		return level.getLightEngine().getLayerListener(LightLayer.BLOCK).getLightValue(p);
	}

	static int skyLight(Level level, BlockPos p) {
		return level.getLightEngine().getLayerListener(LightLayer.SKY).getLightValue(p);
	}

	/**
	 * A cell you could stand in: solid floor, two clear courses above.
	 *
	 * <p>The same test the desktop uses for "walkable", so the two are comparable. A mob needs the
	 * same room a player does.
	 */
	static boolean standable(Level level, BlockPos p) {
		if (!level.getBlockState(p.below()).isSolidRender()) return false;
		return level.getBlockState(p).isAir() && level.getBlockState(p.above()).isAir();
	}

	/**
	 * Every dark standable cell within `radius` of `from`, worst first.
	 *
	 * <p>SKY LIGHT IS REPORTED BUT NOT JUDGED. A cell open to the sky is bright by day and dark at
	 * night, so counting it as lit would hide every outdoor spawn and counting it as dark would
	 * flag the entire plate. Block light is what a torch changes and what you can do something
	 * about; the sky value is carried so you can tell an unlit room from an unlit lawn.
	 */
	static Report scan(Level level, BlockPos from, int radius, int limit) {
		List<Spot> spots = new ArrayList<>();
		int checked = 0, dim = 0, spawnable = 0;
		BlockPos.MutableBlockPos p = new BlockPos.MutableBlockPos();
		int r2 = radius * radius;
		for (int dx = -radius; dx <= radius; dx++) {
			for (int dz = -radius; dz <= radius; dz++) {
				if (dx * dx + dz * dz > r2) continue;
				for (int dy = -radius; dy <= radius; dy++) {
					p.set(from.getX() + dx, from.getY() + dy, from.getZ() + dz);
					if (!level.isLoaded(p)) continue;
					if (!standable(level, p)) continue;
					checked++;
					int b = blockLight(level, p);
					if (b >= DIM) continue;
					dim++;
					if (b < SPAWNABLE) spawnable++;
					spots.add(new Spot(p.immutable(), b, skyLight(level, p)));
				}
			}
		}
		// darkest first, then nearest: the cell most likely to put a creeper behind you
		spots.sort(Comparator.<Spot>comparingInt(Spot::block)
			.thenComparingDouble(s -> s.pos().distSqr(from)));
		if (spots.size() > limit) spots = new ArrayList<>(spots.subList(0, limit));
		return new Report(spots, checked, dim, spawnable);
	}

	/**
	 * Group the spots into clusters so the report says "a dark room" rather than listing 300 cells.
	 * Simple grid binning - a cluster is a 8x8x8 cell of space, which is about a room.
	 */
	static List<BlockPos> clusters(List<Spot> spots, int limit) {
		java.util.LinkedHashMap<Long, int[]> bins = new java.util.LinkedHashMap<>();
		for (Spot s : spots) {
			long key = BlockPos.asLong(s.pos().getX() >> 3, s.pos().getY() >> 3, s.pos().getZ() >> 3);
			int[] acc = bins.computeIfAbsent(key, k -> new int[4]);
			acc[0] += s.pos().getX();
			acc[1] += s.pos().getY();
			acc[2] += s.pos().getZ();
			acc[3]++;
		}
		List<int[]> all = new ArrayList<>(bins.values());
		all.sort((a, b) -> Integer.compare(b[3], a[3]));
		List<BlockPos> out = new ArrayList<>();
		for (int[] a : all) {
			if (out.size() >= limit) break;
			out.add(new BlockPos(a[0] / a[3], a[1] / a[3], a[2] / a[3]));
		}
		return out;
	}
}
