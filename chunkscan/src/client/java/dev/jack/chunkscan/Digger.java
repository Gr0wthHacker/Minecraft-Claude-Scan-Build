package dev.jack.chunkscan;

import net.minecraft.client.Minecraft;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.Vec3;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * Breaks the cells a design's DIG LIST names — and nothing else, ever.
 *
 * <p>A litematic cannot express removal, so "break this" has always lived in the sidecar and has
 * always been a human with a pickaxe. {@code Falls} is 58% dig; {@code Island Night} is 22%. The
 * loop could place thirty blocks, report the design complete and leave the channel it exists to
 * cut standing in solid rock.
 *
 * <p><b>THIS IS THE ONE OPERATION WITH NO UNDO,</b> so every gate here is a refusal rather than a
 * warning — the opposite posture to the rest of the mod, where a provisional list only ever warns:
 *
 * <ul>
 *   <li><b>Only cells on the design's own dig list.</b> Not "anything in the way", not "whatever
 *       the printer wants to replace". If a cell is not in the sidecar, it is not dug.</li>
 *   <li><b>Never a protected block.</b> {@link Rules} holds {@code wool} because wool may be a
 *       sculk sensor's silencer, and this is precisely the pass that would find out the hard way.
 *       A dig list that names one is reported and skipped, not obeyed — the LIST is not the
 *       authority on safety.</li>
 *   <li><b>Never over open void.</b> {@link VoidRisk} already knows what falls forever; breaking
 *       a block whose drop is gone is the skyblock-specific loss no undo can reach.</li>
 *   <li><b>Never outside the plot.</b></li>
 *   <li><b>One block at a time, watched.</b> Breaking is not instant in survival: you hold the
 *       swing and the server decides. This continues on the same cell until the world says it is
 *       gone, and gives up rather than swinging at bedrock forever.</li>
 * </ul>
 *
 * <p>It does NOT pick up what it breaks. Items drop where they were, and on this island that is
 * usually fine and occasionally a hundred-block fall — which is why the void gate is a refusal.
 */
final class Digger {
	static final double REACH = 4.2;
	/** Ticks of swinging at one block before deciding it is not going to break. */
	static final int GIVE_UP_TICKS = 120;

	enum Verdict { BROKE, PROTECTED, OVER_VOID, OFF_PLOT, OUT_OF_REACH, ALREADY_AIR, STUCK, WORKING }

	record Refusal(BlockPos pos, Verdict why, String block) {}

	private static BlockPos target;
	private static int swings;
	private static int broke;
	private static final Set<String> givenUp = new HashSet<>();
	private static final List<Refusal> refusals = new ArrayList<>();

	private Digger() {}

	static void reset() {
		target = null;
		swings = 0;
		broke = 0;
		givenUp.clear();
		refusals.clear();
	}

	static int broke() {
		return broke;
	}

	static List<Refusal> refusals() {
		return refusals;
	}

	private static String key(BlockPos p) {
		return p.getX() + "," + p.getY() + "," + p.getZ();
	}

	/**
	 * May this cell be broken? Pure enough to test: everything it consults is a rule or a lookup.
	 *
	 * <p>Order matters only for the message — a cell can fail several of these at once and the
	 * first one named should be the one that is most obviously not negotiable.
	 */
	static Verdict judge(Minecraft mc, BlockPos p) {
		if (mc.level == null || mc.player == null) return Verdict.STUCK;
		BlockState st = mc.level.getBlockState(p);
		if (st.isAir()) return Verdict.ALREADY_AIR;
		String name = BuiltInRegistries.BLOCK.getKey(st.getBlock()).toString();
		if (Rules.isProtected(name)) return Verdict.PROTECTED;
		if (Islands.outside(ScanRunner.schematicsDir(mc), p.getX(), p.getZ())) {
			return Verdict.OFF_PLOT;
		}
		VoidRisk.Cell under = VoidRisk.under(mc.level, p, mc.level.getMinY());
		if (under.verdict() == VoidRisk.Verdict.VOID) return Verdict.OVER_VOID;
		if (mc.player.getEyePosition().distanceToSqr(Vec3.atCenterOf(p)) > REACH * REACH) {
			return Verdict.OUT_OF_REACH;
		}
		return Verdict.WORKING;
	}

	/**
	 * One tick of digging. Returns a line worth saying, or null.
	 *
	 * @param list the design's dig list — the ONLY cells this will ever touch
	 */
	static String tick(Minecraft mc, List<BlockPos> list) {
		if (mc.level == null || mc.player == null || list.isEmpty()) return null;

		if (target != null) {
			if (mc.level.getBlockState(target).isAir()) {
				broke++;
				target = null;
				swings = 0;
				return null;
			}
			if (++swings > GIVE_UP_TICKS) {
				givenUp.add(key(target));
				refusals.add(new Refusal(target, Verdict.STUCK,
					BuiltInRegistries.BLOCK.getKey(mc.level.getBlockState(target).getBlock()).getPath()));
				String msg = "cannot break " + Wand.fmt(target) + " — wrong tool, or the server said no";
				target = null;
				swings = 0;
				return msg;
			}
			mc.gameMode.continueDestroyBlock(target, Direction.UP);
			mc.player.swing(net.minecraft.world.InteractionHand.MAIN_HAND);
			return null;
		}

		BlockPos best = null;
		double bd = Double.MAX_VALUE;
		for (BlockPos p : list) {
			if (givenUp.contains(key(p))) continue;
			double d = mc.player.getEyePosition().distanceToSqr(Vec3.atCenterOf(p));
			if (d >= bd || d > REACH * REACH) continue;
			Verdict v = judge(mc, p);
			if (v == Verdict.ALREADY_AIR) continue;
			if (v != Verdict.WORKING) {
				if (givenUp.add(key(p))) {
					refusals.add(new Refusal(p, v,
						BuiltInRegistries.BLOCK.getKey(mc.level.getBlockState(p).getBlock()).getPath()));
				}
				continue;
			}
			best = p;
			bd = d;
		}
		if (best == null) return null;
		target = best;
		swings = 0;
		mc.gameMode.startDestroyBlock(best, Direction.UP);
		return null;
	}

	/** The refusals, grouped, for one honest line rather than a hundred. */
	static String summary() {
		if (refusals.isEmpty()) return broke + " broken";
		java.util.Map<Verdict, Integer> by = new java.util.EnumMap<>(Verdict.class);
		for (Refusal r : refusals) by.merge(r.why(), 1, Integer::sum);
		StringBuilder b = new StringBuilder(broke + " broken; refused: ");
		boolean first = true;
		for (var e : by.entrySet()) {
			if (!first) b.append(", ");
			first = false;
			b.append(e.getValue()).append(" ").append(switch (e.getKey()) {
				case PROTECTED -> "PROTECTED (a mechanism, or wool that may be a sensor's silencer)";
				case OVER_VOID -> "over OPEN VOID (the drop would be lost)";
				case OFF_PLOT -> "outside the plot";
				case OUT_OF_REACH -> "out of reach from where you stood";
				case STUCK -> "would not break (wrong tool?)";
				default -> e.getKey().name().toLowerCase(java.util.Locale.ROOT);
			});
		}
		return b.toString();
	}
}
