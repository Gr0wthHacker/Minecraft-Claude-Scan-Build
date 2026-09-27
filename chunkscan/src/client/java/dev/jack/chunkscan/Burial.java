package dev.jack.chunkscan;

import net.minecraft.client.Minecraft;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;

/**
 * BUILT INTO A BOX, OR DIGGING A HOLE AND STANDING IN IT.
 *
 * <p>Jack: <i>"we also need to make sure the bot doesnt dig itself into a hole - its multiple times
 * now sat still and dug completely around itself"</i>, and then, of the guard written for it:
 * <i>"consistently it will box itself in"</i>.
 *
 * <p><b>NO WATCHDOG IN THIS MOD COULD SEE IT, AND THE REASON IS THE INTERESTING PART.</b> Every
 * stall clock here asks whether the loop is TRAVELLING and failing to arrive - {@code NOWHERE_MS},
 * the station stall, the recovery ladder - and a bot that is standing exactly where it means to
 * stand, placing exactly the cells its design names, is not travelling and is not failing. It is
 * succeeding, one block at a time, into a box of its own making. The fault only exists in the
 * GEOMETRY around the body, so that is what this measures.
 *
 * <p><b>AND IT MEASURED THE WRONG THING FIRST: IT COUNTED WALLS, NOT EXITS.</b> A side was called
 * walled only when BOTH body cells were solid, on the reasoning that a block at the feet is a step
 * to walk up and a block at the head is an overhang to duck under. The first half is true; the
 * second is not, and a head-height RING is precisely what a printer builds round a body hovering a
 * course above the floor. Counted as walls that ring is FOUR SIDES OF NOTHING while the body cannot
 * move an inch, so the guard reported a completely free player and the build boxed itself in every
 * time. What decides whether a body is shut in is whether it can GET OUT - {@link #canLeave}.
 *
 * <p>Two halves, and both are needed. {@link Digger} refuses to break what it is standing on, so
 * the pit never deepens under the feet; this notices the walls and rises out. Neither alone is
 * enough - a bot can be walled in by a trench it did not dig, and it can sink through a floor with
 * no walls at all.
 */
final class Burial {

	/**
	 * Sides the body cannot leave through that count as boxed in.
	 *
	 * <p>Jack's own number. Two of four is a trench or a doorway as much as it is a grave, which is
	 * why it is not acted on the instant it is true - see {@link #HOLD_TICKS}.
	 */
	static final int SIDES = 2;

	/**
	 * ...and how many while the printer is BUILDING.
	 *
	 * <p>Two shut sides while building is standing beside the wall you are putting up, which is
	 * where the loop is supposed to be - fired there it rose, the sides opened, the autopilot flew
	 * it back down and it did it again. All four is not a doorway, a corridor or a wall going up.
	 * It is a box.
	 */
	static final int SIDES_BUILDING = 4;

	/**
	 * How long the walls have to stay up before rising.
	 *
	 * <p><b>A DOORWAY IS TWO SHUT SIDES.</b> So is a corridor, a trench between two spoil heaps and
	 * the gap between two market stalls - all places the loop has legitimate work in, and lifting
	 * out of them the moment it stepped in would be a bot that cannot build anywhere narrow. A
	 * second of it is not a doorway; a bot boxing itself in holds it for minutes.
	 */
	static final int HOLD_TICKS = 20;

	/** Upward velocity for the lift. Enough to clear a course a tick or two, not a launch. */
	static final double RISE = 0.35;

	/**
	 * Lifts out of a box before the PLACE is given up on instead.
	 *
	 * <p>Rising re-opens the sides, the autopilot flies the body back down to the same station, and
	 * the same walls close round it again: a one-second cycle that places nothing and that no clock
	 * in this mod can see, because the body is moving the whole time. Three is enough to tell a spot
	 * that shut once from a spot that shuts every time.
	 */
	static final int LIFT_LIMIT = 3;

	/** ...counted over this long, because a design does eventually box the body in twice honestly. */
	static final long LIFT_WINDOW_MS = 60_000;

	/** What the caller should do about it. */
	enum Move {
		/** Nothing: there is a way out. */
		NONE,
		/** Shut in on the sides, with open sky over the head. Climb. */
		RISE,
		/** Sealed, or lifted out of this same trap once too often. The place is not workable. */
		LEAVE
	}

	private static int held = 0;
	private static long saidAt = 0;
	private static int lifts = 0;
	private static long liftsFrom = 0;
	/** Said at most this often: a message on a tick timer is a reason to turn the loop off. */
	static final long SAY_MS = 30_000;

	private Burial() {}

	/** Whatever stops a body: the world, or a test's fixture. */
	interface Solid {
		boolean at(int x, int y, int z);
	}

	static void reset() {
		held = 0;
	}

	static int heldTicks() {
		return held;
	}

	/**
	 * Can the body leave this way?
	 *
	 * <p><b>THIS IS THE WHOLE MEASUREMENT, AND THE OLD ONE WAS NEARLY ITS OPPOSITE.</b> A player is
	 * 1.8 tall and there is no crouch in this game that fits under a one-block gap, so a head-height
	 * block is as much a wall as a full-height one. Two ways out, and no more: walk straight
	 * through, or step up onto one block - which needs somewhere to put your head over there AND
	 * headroom in your own column to make the jump. Without that step case every kerb in the park
	 * is a wall and the loop rises off all of them.
	 */
	static boolean canLeave(Solid s, BlockPos feet, Direction d) {
		int x = feet.getX() + d.getStepX(), y = feet.getY(), z = feet.getZ() + d.getStepZ();
		boolean low = s.at(x, y, z), mid = s.at(x, y + 1, z);
		if (!low && !mid) return true;
		return low && !mid && !s.at(x, y + 2, z) && !s.at(feet.getX(), y + 2, feet.getZ());
	}

	/** How many of the four horizontal sides the body can actually get out through. */
	static int exits(Solid solid, BlockPos feet) {
		int n = 0;
		for (Direction d : Direction.Plane.HORIZONTAL) if (canLeave(solid, feet, d)) n++;
		return n;
	}

	/** ...and how many it cannot. A wall, an overhang and a two-course face all count the same. */
	static int walled(Solid solid, BlockPos feet) {
		return 4 - exits(solid, feet);
	}

	/** Is there anywhere to go? Rising into a ceiling is grinding, which this mod has done before. */
	static boolean canRise(Solid solid, BlockPos feet) {
		return !solid.at(feet.getX(), feet.getY() + 2, feet.getZ());
	}

	/**
	 * Shut in on the sides, with a way out upward.
	 *
	 * <p>The roof is not an exemption from the whole check, it is what decides which answer applies:
	 * roofed AND shut on every side is {@link #sealed}, which is the emergency rather than the safe
	 * case. A gallery, the undercroft or a tunnel the loop is meant to be inside is roofed and has
	 * EXITS, so it is neither - which is what {@link #canLeave} buys and what the old wall count
	 * needed a special case for.
	 */
	static boolean boxedIn(Solid solid, BlockPos feet) {
		return boxedIn(solid, feet, SIDES);
	}

	static boolean boxedIn(Solid solid, BlockPos feet, int sides) {
		return walled(solid, feet) >= sides && canRise(solid, feet);
	}

	/**
	 * No way out at all: every side shut and a block over the head.
	 *
	 * <p><b>THE RESCUE USED TO BE GATED OUT OF EXACTLY THIS CASE.</b> {@code boxedIn} required
	 * headroom, so a body that had built itself a lid - the actual "fully stuck" - measured as fine
	 * and nothing fired at all. Rising is not available here, so the answer is the recovery ladder's
	 * last rung and giving the place up; see {@link Move#LEAVE}.
	 */
	static boolean sealed(Solid solid, BlockPos feet) {
		return exits(solid, feet) == 0 && !canRise(solid, feet);
	}

	/** How many shut sides count as boxed in right now. See SIDES_BUILDING. */
	static int sidesNow() {
		return (Digger.busy() || Hud.target() == null) ? SIDES : SIDES_BUILDING;
	}

	/** The world's own answer, for the caller that has one. */
	static Solid of(Level level) {
		return (x, y, z) -> {
			BlockPos p = new BlockPos(x, y, z);
			return level.isLoaded(p) && level.getBlockState(p).blocksMotion();
		};
	}

	/**
	 * Notice a box. Says what the caller should do about it, and does none of it.
	 *
	 * <p>It only ever asks to rise. Working out which way is out is a search, and a search is what
	 * the recovery ladder is for; the one direction always right in a pit is up, and one course of
	 * it re-opens the sides, which ends this by itself.
	 *
	 * <p><b>It sets no velocity of its own.</b> Every other movement path in this mod ends with
	 * {@code Bounds.clamp} and then {@code avoid} - the fence, then the world - and a step that
	 * skipped both would be the one place the body can be pushed into a block, which on this server
	 * ends flight. The caller owns the step; this owns the decision.
	 */
	static Move wants(Minecraft mc) {
		Player p = mc.player;
		if (p == null || mc.level == null) {
			held = 0;
			return Move.NONE;
		}
		BlockPos feet = p.blockPosition();
		Solid w = of(mc.level);
		boolean shut = sealed(w, feet);
		boolean boxed = boxedIn(w, feet, sidesNow());
		if (!shut && !boxed) {
			held = 0;
			return Move.NONE;
		}
		if (++held < HOLD_TICKS) return Move.NONE;
		long now = System.currentTimeMillis();
		if (now - saidAt > SAY_MS) {
			saidAt = now;
			p.sendSystemMessage(net.minecraft.network.chat.Component.literal(shut
				? "[cscan] sealed in at " + Wand.fmt(feet) + " - nothing can be reached from here"
				: "[cscan] shut in on " + walled(w, feet) + " sides at " + Wand.fmt(feet)
					+ " - climbing out before it becomes a hole"));
		}
		if (shut) return Move.LEAVE;
		// A LIFT THAT KEEPS BEING NEEDED IS NOT A FIX. Counted once per episode, at the tick the
		// hold expires, because `held` goes on climbing while the body does.
		if (held == HOLD_TICKS) {
			if (now - liftsFrom > LIFT_WINDOW_MS) {
				lifts = 0;
				liftsFrom = now;
			}
			if (++lifts > LIFT_LIMIT) {
				lifts = 0;
				return Move.LEAVE;
			}
		}
		return Move.RISE;
	}

	/** The step this wants, before the fence and the world have had their say. */
	static Vec3 step(Player p) {
		Vec3 v = p.getDeltaMovement();
		return new Vec3(v.x * 0.5, Math.max(v.y, RISE), v.z * 0.5);
	}

	/**
	 * On foot, the climb is a JUMP and never the jump KEY. Driving that key is a double tap inside
	 * seven ticks, which toggles flight off - the mistake that once revoked Jack's flight in
	 * mid-air. {@code jumpFromGround} is the jump itself, with no toggle anywhere near it.
	 */
	static void hop(Player p) {
		if (p.onGround()) p.jumpFromGround();
	}
}
