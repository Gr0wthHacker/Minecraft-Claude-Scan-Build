package dev.jack.chunkscan;

import net.minecraft.client.Minecraft;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.item.BlockItem;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.Vec3;

import java.util.ArrayList;
import java.util.List;

/**
 * A place-wait-harvest loop over a box: the generic shape of every conversion farm.
 *
 * <p>The worked example is the one this project reasoned out and then did by hand: <b>mud on a
 * pointed dripstone becomes clay</b>, 17.6% per random tick, about 6.5 minutes an average. A
 * hundred converter columns is a hundred blocks to place, ten minutes to wait, a hundred to break
 * and repeat — which is a job nobody does twice. Every primitive for it already existed here after
 * {@link Printer} and {@link Digger}; what was missing was the cycle.
 *
 * <p>It is deliberately GENERIC — a `seed` block, a `crop` block and a box — because the same
 * three-step shape is a clay farm, a mud farm, an ice farm and anything else that turns one block
 * into another in place. Nothing about clay is written into it.
 *
 * <p>Three rules, and the first is what stops it being a griefing tool pointed at your own island:
 *
 * <ul>
 *   <li><b>IT ONLY EVER BREAKS THE CROP, AND ONLY INSIDE ITS BOX.</b> Not "whatever is there" —
 *       a cell holding anything other than the crop is left alone and counted. Point it at a wall
 *       by mistake and it does nothing at all.</li>
 *   <li><b>It waits rather than deciding.</b> A conversion that has not happened yet is
 *       indistinguishable from one that never will, so there is no stall clock: it keeps sweeping,
 *       and reports its rate so YOU can decide the farm is not working.</li>
 *   <li><b>It stops when the seed runs out.</b> Silently re-sweeping an empty box for an hour is
 *       the "does nothing, quietly" failure this project keeps writing rules about.</li>
 * </ul>
 */
final class Farm {
	static final int STEP_TICKS = 4;

	private static BlockPos min, max;
	private static String seed = "", crop = "";
	private static boolean on;
	private static int placed, harvested, cycles;
	private static long startedAt, nextAt;

	private Farm() {}

	static boolean running() {
		return on;
	}

	static void stop() {
		on = false;
	}

	static String status() {
		if (!on) return "no farm running";
		long mins = Math.max(1, (System.currentTimeMillis() - startedAt) / 60000);
		return String.format("%s -> %s: %d placed, %d harvested over %d min (%.1f/min), %d sweep(s)",
			seed, crop, placed, harvested, mins, harvested / (double) mins, cycles);
	}

	/**
	 * @param seedBlock what you PLACE (mud)
	 * @param cropBlock what it BECOMES and what gets broken (clay)
	 */
	static String start(BlockPos a, BlockPos b, String seedBlock, String cropBlock) {
		min = new BlockPos(Math.min(a.getX(), b.getX()), Math.min(a.getY(), b.getY()),
			Math.min(a.getZ(), b.getZ()));
		max = new BlockPos(Math.max(a.getX(), b.getX()), Math.max(a.getY(), b.getY()),
			Math.max(a.getZ(), b.getZ()));
		seed = Rules.shortName(seedBlock);
		crop = Rules.shortName(cropBlock);
		placed = harvested = cycles = 0;
		startedAt = System.currentTimeMillis();
		on = true;
		nextAt = 0;
		long vol = (long) (max.getX() - min.getX() + 1) * (max.getY() - min.getY() + 1)
			* (max.getZ() - min.getZ() + 1);
		return "farm on: " + seed + " -> " + crop + " over " + vol + " cell(s). "
			+ "It breaks ONLY " + crop + ", and only inside the box. /cscan farm off to stop";
	}

	/** Every cell of the box holding `name`. */
	static List<BlockPos> cellsOf(Minecraft mc, String name) {
		List<BlockPos> out = new ArrayList<>();
		if (mc.level == null || min == null) return out;
		for (int x = min.getX(); x <= max.getX(); x++) {
			for (int y = min.getY(); y <= max.getY(); y++) {
				for (int z = min.getZ(); z <= max.getZ(); z++) {
					BlockPos p = new BlockPos(x, y, z);
					if (!mc.level.isLoaded(p)) continue;
					BlockState st = mc.level.getBlockState(p);
					String n = BuiltInRegistries.BLOCK.getKey(st.getBlock()).getPath();
					if (n.equals(name)) out.add(p);
				}
			}
		}
		return out;
	}

	/** One step. Harvest first — a full box cannot take a seed. */
	static String tick(Minecraft mc) {
		if (!on || mc.player == null || mc.level == null) return null;
		if (mc.level.getGameTime() < nextAt) return null;
		nextAt = mc.level.getGameTime() + STEP_TICKS;

		List<BlockPos> ripe = cellsOf(mc, crop);
		if (!ripe.isEmpty()) {
			int before = Digger.broke();
			String msg = Digger.tick(mc, ripe);
			harvested += Math.max(0, Digger.broke() - before);
			return msg;
		}

		// Nothing ripe in reach: sow. An empty cell inside the box is one that has been harvested.
		int slot = Printer.hotbarSlot(mc.player, seed);
		if (slot < 0) {
			on = false;
			return "farm stopped: no " + seed + " in your hotbar (" + harvested + " harvested)";
		}
		for (int x = min.getX(); x <= max.getX(); x++) {
			for (int y = min.getY(); y <= max.getY(); y++) {
				for (int z = min.getZ(); z <= max.getZ(); z++) {
					BlockPos p = new BlockPos(x, y, z);
					if (!mc.level.isLoaded(p) || !mc.level.getBlockState(p).isAir()) continue;
					if (mc.player.getEyePosition().distanceToSqr(Vec3.atCenterOf(p))
						> Printer.REACH * Printer.REACH) continue;
					Printer.Verdict v = Printer.place(mc, p, seed);
					if (v == Printer.Verdict.PLACED) {
						placed++;
						return null;
					}
				}
			}
		}
		cycles++;
		return null;                       // nothing to do this pass: the conversion is a WAIT
	}
}
