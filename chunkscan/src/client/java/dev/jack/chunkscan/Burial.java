package dev.jack.chunkscan;

import net.minecraft.client.Minecraft;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;

/**
 * DIGGING A HOLE AND STANDING IN IT.
 *
 * <p>Jack: <i>"we also need to make sure the bot doesnt dig itself into a hole - its multiple times
 * now sat still and dug completely around itself. If it starts to have sides of itself covered,
 * e.g. 2/3 sides of body, it should move up etc to start avoiding being stuck."</i>
 *
 * <p><b>NO WATCHDOG IN THIS MOD COULD SEE IT, AND THE REASON IS THE INTERESTING PART.</b> Every
 * stall clock here asks whether the loop is TRAVELLING and failing to arrive - {@code NOWHERE_MS},
 * the station stall, the recovery ladder - and a bot that is standing exactly where it means to
 * stand, breaking exactly the cells its dig list names, is not travelling and is not failing. It is
 * succeeding, one block at a time, into a pit of its own making. The fault only exists in the
 * GEOMETRY around the body, so that is what this measures.
 *
 * <p>Two halves, and both are needed. {@link Digger} refuses to break what it is standing on, so
 * the pit never deepens under the feet; this notices the walls and rises out. Neither alone is
 * enough - a bot can be walled in by a trench it did not dig, and it can sink through a floor with
 * no walls at all.
 */
final class Burial {

	/**
	 * Walled sides that count as boxed in.
	 *
	 * <p>Jack's own number. Two of four is a trench or a doorway as much as it is a grave, which is
	 * why it is not acted on the instant it is true - see {@link #HOLD_TICKS}.
	 */
	static final int SIDES = 2;

	/**
	 * How long the walls have to stay up before rising.
	 *
	 * <p><b>A DOORWAY IS TWO WALLED SIDES.</b> So is a corridor, a trench between two spoil heaps
	 * and the gap between two market stalls - all places the loop has legitimate work in, and
	 * lifting out of them the moment it stepped in would be a bot that cannot build anywhere narrow.
	 * A second of it is not a doorway; a bot digging itself in holds it for minutes.
	 */
	static final int HOLD_TICKS = 20;

	/** Upward velocity for the lift. Enough to clear a course a tick or two, not a launch. */
	static final double RISE = 0.35;

	private static int held = 0;
	private static long saidAt = 0;
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
	 * How many of the four horizontal sides of the BODY are walled.
	 *
	 * <p>The body is two cells tall, so a side counts only when BOTH are blocked: a block at the
	 * feet alone is a step to walk up and a block at the head alone is an overhang to duck under,
	 * and calling either of them a wall would have the loop rising off every kerb in the park.
	 */
	static int walled(Solid solid, BlockPos feet) {
		int n = 0;
		for (Direction d : Direction.Plane.HORIZONTAL) {
			BlockPos q = feet.relative(d);
			if (solid.at(q.getX(), q.getY(), q.getZ())
				&& solid.at(q.getX(), q.getY() + 1, q.getZ())) n++;
		}
		return n;
	}

	/** Is there anywhere to go? Rising into a ceiling is grinding, which this mod has done before. */
	static boolean canRise(Solid solid, BlockPos feet) {
		return !solid.at(feet.getX(), feet.getY() + 2, feet.getZ());
	}

	/**
	 * Boxed in, with a way out upward.
	 *
	 * <p>THE HEADROOM TEST IS NOT A DETAIL. Underground - a mine gallery, the undercroft, a tunnel
	 * the loop is meant to be inside - the sides are walled by design and there is a roof, so this
	 * is false and nothing happens. That is the same rule {@code keepAirborne} learned the hard way:
	 * landing on a floor inside a building is not the failure being guarded against.
	 */
	static boolean boxedIn(Solid solid, BlockPos feet) {
		return walled(solid, feet) >= SIDES && canRise(solid, feet);
	}

	/** The world's own answer, for the caller that has one. */
	static Solid of(Level level) {
		return (x, y, z) -> {
			BlockPos p = new BlockPos(x, y, z);
			return level.isLoaded(p) && level.getBlockState(p).blocksMotion();
		};
	}

	/**
	 * Notice, and climb out. Returns true when it acted, so the caller stops steering this tick.
	 *
	 * <p>It only ever RISES. Working out which way is out is a search, and a search is what the
	 * recovery ladder is for; the one direction that is always right in a pit is up, and one course
	 * of it re-opens the sides, which ends this by itself.
	 */
	static boolean lift(Minecraft mc) {
		Player p = mc.player;
		if (p == null || mc.level == null) return false;
		BlockPos feet = p.blockPosition();
		if (!boxedIn(of(mc.level), feet)) {
			held = 0;
			return false;
		}
		if (++held < HOLD_TICKS) return false;
		long now = System.currentTimeMillis();
		if (now - saidAt > SAY_MS) {
			saidAt = now;
			p.sendSystemMessage(net.minecraft.network.chat.Component.literal(
				"[cscan] walled in on " + walled(of(mc.level), feet) + " sides at " + Wand.fmt(feet)
				+ " — climbing out before it becomes a hole"));
		}
		if (p.getAbilities().flying) {
			Vec3 v = p.getDeltaMovement();
			p.setDeltaMovement(v.x * 0.5, Math.max(v.y, RISE), v.z * 0.5);
		} else {
			// NOT THE JUMP KEY. Driving it is a double tap inside seven ticks, which toggles flight
			// off - the mistake that once revoked Jack's flight in mid-air. `jumpFromGround` is the
			// jump itself, with no key and no toggle anywhere near it.
			if (p.onGround()) p.jumpFromGround();
		}
		return true;
	}
}
