package dev.jack.chunkscan;

import net.minecraft.client.Minecraft;
import net.minecraft.client.player.LocalPlayer;
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
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

/**
 * Places the design's blocks itself, and — the whole point — <b>watches whether they landed</b>.
 *
 * <p>Until now this mod stated as fact that <i>"a client mod cannot place a block, and should
 * not"</i>. Only the second half was ever true, and it was a policy about the server's rules
 * rather than about the client: litematica-printer places blocks from a client exactly as this
 * does. Jack has since confirmed automation is allowed and encouraged on skyblock.net, so the
 * first half is simply wrong and the second half no longer applies.
 *
 * <p><b>THE REASON THIS MATTERS IS NOT SPEED, IT IS FEEDBACK.</b> Delegating to the printer left
 * the loop with no signal at all — this project's own note says <i>"the printer never reports
 * back, so `todo` shrinking is the only honest evidence a block was placed"</i> — and four stall
 * clocks, an abandoned-station set and a whole recovery ladder exist to paper over that silence.
 * A placement made here is verified against the world on a later tick, so the loop finally knows
 * the difference between <i>it did not work</i> and <i>I have not looked yet</i>.
 *
 * <p>Four rules, and three of them are about not making a mess that is expensive to undo:
 *
 * <ul>
 *   <li><b>THE STATE IS VERIFIED, NOT ASSUMED.</b> A stair placed the wrong way round cannot be
 *       walked up, and this repo went to real trouble to settle that convention — then found the
 *       in-game check could not see facing either. A cell whose block is right and whose state is
 *       wrong is reported as a MISMATCH, never counted as placed.</li>
 *   <li><b>It never breaks anything.</b> Placement goes into air only. Replacing is a separate,
 *       explicit job with its own dig list, because breaking the wrong block on a lived-in island
 *       is the one mistake with no undo.</li>
 *   <li><b>{@link Rules} and {@link Plot} still apply.</b> The safe set and the 99x99 boundary are
 *       the same ones every generator and the wand consult.</li>
 *   <li><b>A cell that fails twice is left alone</b> and reported. Retrying for ever is how an
 *       unattended loop spends a night achieving nothing — the lesson {@code Ignored} already
 *       encodes for places, applied to cells.</li>
 * </ul>
 *
 * <p>Aiming is not decoration. The server derives {@code facing} from where the player is LOOKING
 * at the moment of placement and {@code half}/{@code type} from where in the clicked face the hit
 * landed, so both are computed here and the look angle is set before the click. That is the only
 * way to place a stair or a top slab correctly, and it is why this can do what a naive
 * click-the-block loop cannot.
 */
final class Printer {
	/** Vanilla reach is ~4.5; stay inside it so a placement is never refused for distance alone. */
	static final double REACH = 4.2;
	/** Ticks between placements. Vanilla holding right-click is one per tick; this is gentler. */
	static int interval = 2;
	/** A cell that has failed this many times is somebody else's problem. */
	static final int MAX_TRIES = 2;

	private Printer() {}

	/** What one attempt turned into, once the world has been looked at again. */
	enum Verdict { PLACED, MISMATCH, STILL_AIR, BLOCKED, NO_ITEM, NO_FACE, OUT_OF_REACH, REFUSED }

	record Attempt(BlockPos pos, String want, Verdict verdict, String got) {}

	// ---------------------------------------------------------------- geometry

	/**
	 * A face to click, given the cell we want to fill.
	 *
	 * <p>You place a block by clicking an existing one and the new block appears against the face
	 * you clicked, so what is needed is a solid NEIGHBOUR and the direction from it back to us.
	 * Returns null when the cell is floating — which is the scaffolding question the loop already
	 * asks, answered here from the same evidence.
	 */
	static Direction[] faces() {
		// Down first: a block placed on top of another is the commonest and the least ambiguous,
		// and it is what a player does. Sides before up, because clicking a ceiling is awkward and
		// more likely to be out of reach from a standing spot.
		return new Direction[] {Direction.DOWN, Direction.NORTH, Direction.SOUTH,
			Direction.EAST, Direction.WEST, Direction.UP};
	}

	/**
	 * Where in the clicked face to aim, so that {@code half}/{@code type} come out right.
	 *
	 * <p>A slab is {@code type=bottom} when the hit is in the lower half of the clicked face and
	 * {@code top} when it is in the upper half; a stair's {@code half} is the same question. Aim
	 * at the middle and you get whichever the geometry happens to give, which is how you end up
	 * with a flight you cannot walk up.
	 */
	static Vec3 hit(BlockPos target, Direction faceFromNeighbour, boolean upperHalf) {
		BlockPos nb = target.relative(faceFromNeighbour.getOpposite());
		double y = upperHalf ? 0.75 : 0.25;
		double cx = nb.getX() + 0.5, cy = nb.getY() + 0.5, cz = nb.getZ() + 0.5;
		return switch (faceFromNeighbour) {
			case UP -> new Vec3(cx, nb.getY() + 1.0, cz);
			case DOWN -> new Vec3(cx, nb.getY(), cz);
			case NORTH -> new Vec3(cx, nb.getY() + y, nb.getZ());
			case SOUTH -> new Vec3(cx, nb.getY() + y, nb.getZ() + 1.0);
			case WEST -> new Vec3(nb.getX(), nb.getY() + y, cz);
			case EAST -> new Vec3(nb.getX() + 1.0, nb.getY() + y, cz);
		};
	}

	/** The yaw that makes the server give a block this horizontal {@code facing}. */
	static float yawFor(Direction facing) {
		// A stair's `facing` is the direction its TALL side points, which is the direction the
		// player is looking AWAY from: place while facing north and the stair faces south. The
		// game derives it as `player.getDirection().getOpposite()` for stairs, so the yaw wanted
		// is the one that looks at the OPPOSITE of the target facing.
		return switch (facing) {
			case NORTH -> 0f;      // looking south (+Z) => facing north
			case SOUTH -> 180f;
			case WEST -> 270f;
			case EAST -> 90f;
			default -> 0f;
		};
	}

	/** Parse `stone_brick_stairs[facing=east,half=top]` into what the aiming needs to know. */
	static Map<String, String> props(String state) {
		Map<String, String> out = new HashMap<>();
		int b = state.indexOf('[');
		if (b < 0 || !state.endsWith("]")) return out;
		for (String part : state.substring(b + 1, state.length() - 1).split(",")) {
			int eq = part.indexOf('=');
			if (eq > 0) out.put(part.substring(0, eq).trim(), part.substring(eq + 1).trim());
		}
		return out;
	}

	// ---------------------------------------------------------------- the pass

	private static final Map<String, Integer> tries = new HashMap<>();
	private static final Set<String> givenUp = new HashSet<>();
	private static final List<Attempt> pending = new ArrayList<>();
	private static long lastPlaceTick;
	private static int placed, mismatched, failed;
	// Since the loop last asked. THIS IS THE SIGNAL THE LOOP HAS NEVER HAD: a refusal is instant
	// knowledge, where the five-second station clock had to wait and then guess.
	private static int placedSince, refusedSince;

	static void reset() {
		tries.clear();
		givenUp.clear();
		pending.clear();
		placed = mismatched = failed = 0;
		placedSince = refusedSince = 0;
	}

	/** True while this printer is the thing placing blocks, so the loop knows to trust its report. */
	static boolean driving() {
		return ChunkScanClient.printDesign != null;
	}

	/**
	 * What has happened since the last call, and RESETS. Two numbers, because they mean opposite
	 * things: cells that went in are progress, cells that were refused are proof this spot is not
	 * buildable from here and there is nothing to wait for.
	 */
	static int[] drainReport() {
		int[] r = {placedSince, refusedSince};
		placedSince = refusedSince = 0;
		return r;
	}

	static int placed() { return placed; }

	static int mismatched() { return mismatched; }

	static int failed() { return failed; }

	static boolean givenUpOn(BlockPos p) {
		return givenUp.contains(key(p));
	}

	private static String key(BlockPos p) {
		return p.getX() + "," + p.getY() + "," + p.getZ();
	}

	/** Which hotbar slot holds this block, or -1. Only the hotbar: a click uses what is held. */
	static int hotbarSlot(LocalPlayer p, String block) {
		String want = Rules.shortName(block);
		for (int i = 0; i < 9; i++) {
			ItemStack st = p.getInventory().getItem(i);
			if (st.isEmpty() || !(st.getItem() instanceof BlockItem)) continue;
			if (BuiltInRegistries.ITEM.getKey(st.getItem()).getPath().equals(want)) return i;
		}
		return -1;
	}

	/**
	 * Try to place one cell. Does NOT decide whether it worked — {@link #verify} does that on a
	 * later tick, because the server has to answer first and a placement is not synchronous.
	 */
	static Verdict place(Minecraft mc, BlockPos pos, String state) {
		LocalPlayer p = mc.player;
		if (p == null || mc.level == null) return Verdict.REFUSED;
		if (givenUpOn(pos)) return Verdict.REFUSED;
		if (!mc.level.getBlockState(pos).isAir()) {
			// Something is already here. Never break it: that is the one mistake with no undo.
			return Verdict.BLOCKED;
		}
		// The island UNDER THIS CELL, not whichever one was exported: alt 2 building on alt 1's
		// island must be judged against alt 1's square.
		if (Islands.outside(ScanRunner.schematicsDir(mc), pos.getX(), pos.getZ())) {
			return Verdict.REFUSED;
		}
		if (p.getEyePosition().distanceToSqr(Vec3.atCenterOf(pos)) > REACH * REACH) {
			return Verdict.OUT_OF_REACH;
		}
		int slot = hotbarSlot(p, state);
		if (slot < 0) return Verdict.NO_ITEM;

		Map<String, String> want = props(state);
		Direction chosen = null;
		for (Direction d : faces()) {
			BlockPos nb = pos.relative(d.getOpposite());
			BlockState ns = mc.level.getBlockState(nb);
			if (ns.isAir() || Rules.isProtected(BuiltInRegistries.BLOCK.getKey(ns.getBlock()).toString())) {
				continue;                       // nothing to click, or something not to disturb
			}
			if (!ns.blocksMotion()) continue;   // a vine is not a face: the rim stair's own lesson
			chosen = d;
			break;
		}
		if (chosen == null) return Verdict.NO_FACE;

		boolean upper = "top".equals(want.get("half")) || "top".equals(want.get("type"));
		String facing = want.get("facing");
		if (facing != null) {
			Direction f = Direction.byName(facing.toLowerCase(Locale.ROOT));
			if (f != null && f.getAxis().isHorizontal()) {
				p.setYRot(yawFor(f));
				p.setXRot(0f);
			}
		}
		int was = p.getInventory().getSelectedSlot();
		p.getInventory().setSelectedSlot(slot);
		BlockHitResult hr = new BlockHitResult(hit(pos, chosen, upper), chosen,
			pos.relative(chosen.getOpposite()), false);
		mc.gameMode.useItemOn(p, InteractionHand.MAIN_HAND, hr);
		p.swing(InteractionHand.MAIN_HAND);
		p.getInventory().setSelectedSlot(was);
		pending.add(new Attempt(pos, state, Verdict.STILL_AIR, ""));
		lastPlaceTick = mc.level.getGameTime();
		return Verdict.PLACED;
	}

	/**
	 * Look at every pending cell and decide what actually happened.
	 *
	 * <p>THIS IS THE SIGNAL THE LOOP HAS NEVER HAD. Called a few ticks after the attempts, so the
	 * server has had time to answer; a cell still air is a failure, a cell holding the wrong STATE
	 * is a mismatch and is never counted as built.
	 */
	static List<Attempt> verify(Minecraft mc) {
		List<Attempt> out = new ArrayList<>();
		if (mc.level == null) return out;
		for (Attempt a : new ArrayList<>(pending)) {
			BlockState st = mc.level.getBlockState(a.pos());
			if (st.isAir()) {
				int n = tries.merge(key(a.pos()), 1, Integer::sum);
				if (n >= MAX_TRIES) {
					givenUp.add(key(a.pos()));
					failed++;
					refusedSince++;
					out.add(new Attempt(a.pos(), a.want(), Verdict.STILL_AIR, "air"));
				}
				continue;                       // one more go before writing it off
			}
			String got = BuiltInRegistries.BLOCK.getKey(st.getBlock()).getPath();
			// `Work.matches` is the SAME comparison `/cscan check` uses, so a cell the printer
			// calls placed and a cell the check calls built can never disagree.
			if (Work.matches(st, a.want())) {
				placed++;
				placedSince++;
				out.add(new Attempt(a.pos(), a.want(), Verdict.PLACED, got));
			} else {
				mismatched++;
				refusedSince++;
				givenUp.add(key(a.pos()));      // placing over it would mean breaking it
				out.add(new Attempt(a.pos(), a.want(), Verdict.MISMATCH, got));
			}
		}
		pending.clear();
		return out;
	}

	static boolean busy() {
		return !pending.isEmpty();
	}

	static boolean ready(Minecraft mc) {
		return mc.level != null && mc.level.getGameTime() - lastPlaceTick >= interval;
	}

	static String report() {
		return placed + " placed, " + mismatched + " wrong state, " + failed + " refused";
	}
}
