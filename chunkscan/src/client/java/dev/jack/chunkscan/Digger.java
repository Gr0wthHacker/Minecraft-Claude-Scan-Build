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
	/** Ticks past the block's own expected break time before it is written off. */
	static final int GIVE_UP_SLACK = 60;
	static final int GIVE_UP_MAX = 1200;
	private static int giveUpAt = GIVE_UP_MAX;

	enum Verdict { BROKE, PROTECTED, OVER_VOID, OVER_LAVA, LAVA, OFF_PLOT, FENCED, OUT_OF_REACH, ALREADY_AIR,
		ALREADY_BUILT, STUCK, UNDERFOOT, WORKING }

	record Refusal(BlockPos pos, Verdict why, String block) {}

	private static BlockPos target;
	private static int swings;
	private static int broke;

	/**
	 * What the design being dug WANTS at each cell.
	 *
	 * <p>2,970 cells of `Park Complete` are on its dig list and in its block list - the ground
	 * plane a lake and a well are cut through - and without this the pair loops: the printer
	 * places the cell, the digger sees a solid block on its list and breaks it, for as long as
	 * the session runs. Once the design's own block stands there the dig has done its job.
	 * Rebuilt only when the design changes, because it is a map over the whole design.
	 */
	private static java.util.Map<BlockPos, String> wanted = java.util.Map.of();
	private static String wantedFor;

	/**
	 * A box this digger is authorized to work in, REPLACING the island plot gate while it is set.
	 *
	 * <p>{@link Islands.Gate} authorizes only the recorded plots, and an island is recorded as an
	 * X/Z rectangle with no dimension on it. In the Nether every cell is therefore outside every
	 * plot and {@code judge} refuses all of them — no swing, no error, nothing to read. That is the
	 * "does nothing, quietly" failure this project keeps writing rules about, and it would have been
	 * the entire behaviour of a Nether miner.
	 *
	 * <p>The answer is not to weaken the plot gate: on the island it is the only thing standing
	 * between a dig list and somebody's build. It is to make the authorization EXPLICIT where the
	 * registry has nothing to say — a job that wants to dig outside a recorded plot has to name the
	 * box it will stay inside, and is then held to it exactly as a design is held to its plot.
	 *
	 * <p><b>The dimension has to match.</b> A box is coordinates, and coordinates mean nothing
	 * without a world — the rule {@link Wand} already lives under. Without this, an area declared in
	 * the Nether would go on authorizing digs at the same X/Z after a walk through the portal, which
	 * on this island is somebody's plate.
	 */
	private static BlockPos areaMin, areaMax;
	private static String areaDimension = "";

	/** Authorize a box. Idempotent and meant to be re-stated every tick by the job that owns it. */
	static void authorize(BlockPos min, BlockPos max, String dimension) {
		areaMin = min;
		areaMax = max;
		areaDimension = dimension == null ? "" : dimension;
	}

	static void clearAuthorization() {
		areaMin = null;
		areaMax = null;
		areaDimension = "";
	}

	/** Is this cell inside a declared working area that speaks for the dimension we are in? */
	static boolean authorizedHere(String dimension, BlockPos p) {
		if (areaMin == null || areaMax == null) return false;
		if (!areaDimension.equals(dimension)) return false;
		return p.getX() >= Math.min(areaMin.getX(), areaMax.getX())
			&& p.getX() <= Math.max(areaMin.getX(), areaMax.getX())
			&& p.getY() >= Math.min(areaMin.getY(), areaMax.getY())
			&& p.getY() <= Math.max(areaMin.getY(), areaMax.getY())
			&& p.getZ() >= Math.min(areaMin.getZ(), areaMax.getZ())
			&& p.getZ() <= Math.max(areaMin.getZ(), areaMax.getZ());
	}

	/** Whether a working area has been declared at all — for the report, and for tests. */
	static boolean hasAuthorization() {
		return areaMin != null && areaMax != null;
	}

	/** Tell the digger which design it is working, so it can tell finished from obstructing. */
	static void design(java.nio.file.Path schematicsDir, String name) {
		String key = schematicsDir + "::" + name;
		if (key.equals(wantedFor)) return;
		wantedFor = key;
		java.util.Map<BlockPos, String> m = new java.util.HashMap<>();
		try {
			for (Work.Cell c : Work.load(schematicsDir, name)) m.put(c.pos(), c.block());
		} catch (Exception ignored) {
			// No design behind this dig list - `/cscan dig` on a bare sidecar. Then every cell on
			// the list is an obstruction, which is the old behaviour and the safe one.
		}
		wanted = m;
	}

	/** What the design wants at this cell, or null. */
	private static String wantedHere(BlockPos p) {
		return wanted.get(p);
	}
	private static final Set<String> givenUp = new HashSet<>();
	private static final List<Refusal> refusals = new ArrayList<>();

	private Digger() {}

	static void reset() {
		target = null;
		swings = 0;
		broke = 0;
		givenUp.clear();
		refusals.clear();
		// A design dig must never inherit a miner's working area: the box is the AUTHORIZATION,
		// and one left standing would let the next list dig wherever the last job was allowed to.
		clearAuthorization();
	}

    static boolean busy() { return target != null; }

    static void pause(Minecraft mc) {
        if (target != null && mc.gameMode != null) mc.gameMode.stopDestroyBlock();
        target = null;
        swings = 0;
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
	 * Is this cell holding the player up?
	 *
	 * <p>The cell under the feet, and the two the body's own 0.6-wide box can overhang when it is
	 * standing on an edge - taking either of those drops you just the same. Tested on the BODY's
	 * footprint rather than on `blockPosition()` alone, which is a rounded centre and says nothing
	 * about which blocks are actually carrying it.
	 */
	static boolean underfoot(net.minecraft.world.entity.player.Player player, BlockPos p) {
		int fy = net.minecraft.util.Mth.floor(player.getY() - 0.05);
		if (p.getY() != fy) return false;
		double half = player.getBbWidth() / 2.0 + 0.02;
		return p.getX() >= net.minecraft.util.Mth.floor(player.getX() - half)
			&& p.getX() <= net.minecraft.util.Mth.floor(player.getX() + half)
			&& p.getZ() >= net.minecraft.util.Mth.floor(player.getZ() - half)
			&& p.getZ() <= net.minecraft.util.Mth.floor(player.getZ() + half);
	}

	/**
	 * May this cell be broken? Pure enough to test: everything it consults is a rule or a lookup.
	 *
	 * <p>Order matters only for the message — a cell can fail several of these at once and the
	 * first one named should be the one that is most obviously not negotiable.
	 */
	static Verdict judge(Minecraft mc, BlockPos p) {
		if (mc.level == null || mc.player == null || !mc.level.isLoaded(p)) return Verdict.STUCK;
		BlockState st = mc.level.getBlockState(p);
		if (st.isAir()) return Verdict.ALREADY_AIR;
		// A CELL ALREADY HOLDING WHAT THE DESIGN WANTS IS THE FINISHED BUILD, NOT THE OBSTRUCTION.
		// The other half of the rule in `Work.split`: a cell that is both dug and placed would
		// otherwise be broken, placed, broken and placed for as long as the session ran. Once the
		// design's own block stands there the dig has done its job.
		String want = wantedHere(p);
		if (want != null && Work.matches(st, want)) return Verdict.ALREADY_BUILT;
		String name = BuiltInRegistries.BLOCK.getKey(st.getBlock()).toString();
		if (Rules.isProtected(name)) return Verdict.PROTECTED;
		// LAVA ON ANY FACE, INCLUDING THE ONE OVERHEAD YOU CANNOT SEE FROM INSIDE A CORRIDOR.
		// Checked before the plot and the fence because it is the least negotiable thing here:
		// off-plot costs an apology and this costs the inventory. See LavaGuard for why the client
		// can answer this at all - it holds the blocks behind the rock, which is the whole edge a
		// bot has over a person swinging blind.
		if (LavaGuard.touching(LavaGuard.of(mc.level), p)) return Verdict.LAVA;
		// The declared working area REPLACES the plot gate where it speaks, and only in its own
		// dimension. Without it the Nether is entirely off-plot and nothing is ever dug.
		String dimension = mc.level.dimension().identifier().toString();
		if (!authorizedHere(dimension, p)
			&& Islands.outside(ScanRunner.schematicsDir(mc), p.getX(), p.getZ())) {
			return Verdict.OFF_PLOT;
		}
		if (!Bounds.contains(p)) return Verdict.FENCED;    // the autofly fence, at the actuator
		// THE FLOOR YOU ARE STANDING ON IS NOT A CELL TO BREAK. Jack: "its multiple times now sat
		// still and dug completely around itself." Breaking the block under your own feet drops you
		// a course into the hole you are making, and the next cell of the list is then at head
		// height with walls on every side. POSITIONAL, not a fault in the cell: it is skipped from
		// HERE and dug from anywhere else, so it never joins the given-up set.
		if (!mc.player.getAbilities().flying && underfoot(mc.player, p)) return Verdict.UNDERFOOT;
		VoidRisk.Cell under = VoidRisk.under(mc.level, p, mc.level.getMinY());
		if (under.verdict() == VoidRisk.Verdict.VOID) return Verdict.OVER_VOID;
		// A drop into lava is the same loss as a drop into the void, and until VoidRisk learned
		// about lava it reported one as CAUGHT - lava is not solid, so the search walked past it to
		// the bedrock underneath and called that a floor.
		if (under.verdict() == VoidRisk.Verdict.BURNED) return Verdict.OVER_LAVA;
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
        if (mc.level == null || mc.player == null || mc.gameMode == null) return null;
        if (Screens.container() != null) { pause(mc); return null; }
        if (!AutomationControl.enter(ActionGate.Owner.DIG)) return null;
        if (list.isEmpty()) {
            if (target != null) {
                if (mc.level.isLoaded(target) && mc.level.getBlockState(target).isAir()) broke++;
                mc.gameMode.stopDestroyBlock();
            }
            target = null;
            swings = 0;
            return null;
        }

		if (target != null) {
            if (!list.contains(target) || judge(mc, target) != Verdict.WORKING) {
                if (mc.level.isLoaded(target) && mc.level.getBlockState(target).isAir()) broke++;
                mc.gameMode.stopDestroyBlock();
                target = null; swings = 0;
                return null;
            }
			if (++swings > giveUpAt) {
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

		// IN THE LIST'S ORDER, not nearest-first. A dig list is a sequence: the Falls' own contract
		// is "the notch is the plug — cut it LAST", and nearest-first cuts whatever you happen to be
		// standing beside. Within reach the first undug cell in order is taken; and THE LAST CELL
		// OF THE LIST IS NEVER DUG WHILE ANY OTHER REMAINS, whatever is in reach.
		BlockPos best = null;
		int remaining = 0;
		for (BlockPos p : list) {
			if (givenUp.contains(key(p))) continue;
			if (mc.level.isLoaded(p) && mc.level.getBlockState(p).isAir()) continue;
			remaining++;
		}
		BlockPos last = list.isEmpty() ? null : list.get(list.size() - 1);
		for (BlockPos p : list) {
			if (givenUp.contains(key(p))) continue;
			if (remaining > 1 && p.equals(last)) continue;
			double d = mc.player.getEyePosition().distanceToSqr(Vec3.atCenterOf(p));
			if (d > REACH * REACH) continue;
			Verdict v = judge(mc, p);
			if (v == Verdict.ALREADY_AIR || v == Verdict.ALREADY_BUILT) continue;
			// SKIPPED, NOT WRITTEN OFF. Standing on it is a fact about where the BODY is, not
			// about the cell: given up here, the loop could never come back and dig it from the
			// side, and the design would carry a cell nobody may ever break.
			if (v == Verdict.UNDERFOOT) continue;
			// SKIPPED, NOT WRITTEN OFF, for the same reason and a second one: lava is exactly what
			// the miner's plug routine removes, so a cell refused for it now is routinely fine a
			// moment later. OVER_LAVA is deliberately NOT in this list - a lake under a cell is a
			// stable fact about the world and nothing this job does changes it.
			if (v == Verdict.LAVA) continue;
			if (v != Verdict.WORKING) {
				if (givenUp.add(key(p))) {
					refusals.add(new Refusal(p, v,
						BuiltInRegistries.BLOCK.getKey(mc.level.getBlockState(p).getBlock()).getPath()));
				}
				continue;
			}
			best = p;
			break;
		}
		if (best == null) return null;
		target = best;
		swings = 0;
		holdBestTool(mc, best);
		giveUpAt = giveUpFor(mc, best);
		mc.gameMode.startDestroyBlock(best, Direction.UP);
		return null;
	}

	/**
	 * Select the hotbar slot that breaks this block fastest. Swinging whatever happened to be held
	 * — the printer's stone, or the steak — took deepslate past the old fixed give-up and wrote the
	 * cell off as "wrong tool", which it was, and which nothing had tried to fix.
	 */
	static void holdBestTool(Minecraft mc, BlockPos at) {
		if (mc.player == null || mc.level == null) return;
		BlockState st = mc.level.getBlockState(at);
		var inv = mc.player.getInventory();
		int bestSlot = inv.getSelectedSlot();
		float bestSpeed = inv.getItem(bestSlot).getDestroySpeed(st);
		for (int i = 0; i < 9; i++) {
			float s = inv.getItem(i).getDestroySpeed(st);
			if (s > bestSpeed + 1.0e-3f) { bestSpeed = s; bestSlot = i; }
		}
		if (bestSlot != inv.getSelectedSlot()) inv.setSelectedSlot(bestSlot);
	}

	/** How long this block should take with what is now held, plus slack — never a flat number. */
	static int giveUpFor(Minecraft mc, BlockPos at) {
		if (mc.player == null || mc.level == null) return GIVE_UP_MAX;
		float perTick = mc.level.getBlockState(at).getDestroyProgress(mc.player, mc.level, at);
		if (perTick <= 0) return GIVE_UP_SLACK;                 // unbreakable: give up fast
		int expected = (int) Math.ceil(1.0 / perTick);
		return Math.min(GIVE_UP_MAX, expected * 2 + GIVE_UP_SLACK);
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
				case OVER_LAVA -> "over LAVA (the drop would burn)";
				case LAVA -> "lava on a face of it";
				case OFF_PLOT -> "outside the plot";
				case FENCED -> "outside the autofly bounds";
				case OUT_OF_REACH -> "out of reach from where you stood";
				case STUCK -> "would not break (wrong tool?)";
				default -> e.getKey().name().toLowerCase(java.util.Locale.ROOT);
			});
		}
		return b.toString();
	}
}
