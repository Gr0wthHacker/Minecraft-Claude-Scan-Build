package dev.jack.chunkscan;

import net.fabricmc.fabric.api.client.networking.v1.ClientPlayConnectionEvents;
import net.minecraft.core.BlockPos;
import net.minecraft.world.phys.Vec3;

/**
 * A fence for autofly: two corners, and the flight never leaves the box between them.
 *
 * <p>Jack: <i>"lets edit auto fly so i can set two points and it only stays within those
 * points."</i> The wand already sets two points, so {@code /cscan autofly bounds set} takes its
 * box. Once set, the loop will not choose work or a chest outside it, the router will not find a
 * route that leaves it, and the flight will not take a step that crosses it.
 *
 * <p><b>Three layers, because any one of them alone has a hole in it.</b>
 * <ul>
 *   <li><b>The plan.</b> Cells and containers outside the box are not offered to the loop at all
 *       (see Hud), so it never AIMS outside. Filtering here rather than refusing later is the
 *       difference between a loop that works the fenced area and one that stalls at its edge.</li>
 *   <li><b>The route.</b> {@link #within} wraps the passability predicate, so A* cannot find a
 *       route that steps outside even to go round something. A route that leaves and comes back
 *       would pass every other check and still be a flight past the fence.</li>
 *   <li><b>The step.</b> {@link #clamp} is applied to the final delta movement. Direct flight,
 *       the unstick slide, the escape flood and the recovery ladder all move the body without a
 *       route, and the fence has to hold for all of them without each one remembering it.</li>
 * </ul>
 *
 * <p><b>It is a fence, not an activity</b>, so {@code /cscan stop} leaves it standing; but it IS
 * coordinates, and coordinates mean nothing without a world (the wand's rule), so it is cleared on
 * DISCONNECT and restored from the session note only when the dimension matches.
 *
 * <p><b>What it does not stop.</b> The fall rescue's {@code /is} is a teleport and this cannot
 * fence a teleport; nor should it, because a fall is losing the inventory. The recovery ladder's
 * GO_HOME rung, which is convenience rather than safety, is withheld while a fence is set.
 */
final class Bounds {
	/** How far inside a face the body's centre is kept. Half a player's width, and a little. */
	static final double MARGIN = 0.35;
	/** A standing body's height: the feet may not rise closer than this to the top face. */
	static final double HEIGHT = 1.85;
	/** The pull back toward the box when the body is already outside it, in blocks per tick. */
	static final double RETURN_SPEED = 0.3;

	private static boolean active = false;
	private static int x1, y1, z1, x2, y2, z2;      // inclusive cells, ordered
	private static String dimension = "";

	private Bounds() {}

	static void register() {
		ClientPlayConnectionEvents.DISCONNECT.register((handler, client) -> clear());
	}

	static void set(BlockPos a, BlockPos b, String dim) {
		x1 = Math.min(a.getX(), b.getX()); x2 = Math.max(a.getX(), b.getX());
		y1 = Math.min(a.getY(), b.getY()); y2 = Math.max(a.getY(), b.getY());
		z1 = Math.min(a.getZ(), b.getZ()); z2 = Math.max(a.getZ(), b.getZ());
		dimension = dim == null ? "" : dim;
		active = true;
	}

	static void clear() {
		active = false;
		dimension = "";
	}

	static boolean active() {
		return active;
	}

	static String dimension() {
		return dimension;
	}

	/** {x1, y1, z1, x2, y2, z2}, ordered, or null when no fence is set. */
	static int[] corners() {
		return active ? new int[]{x1, y1, z1, x2, y2, z2} : null;
	}

	/** Is this CELL inside the fence? With no fence set, everything is. */
	static boolean contains(int x, int y, int z) {
		if (!active) return true;
		return x >= x1 && x <= x2 && y >= y1 && y <= y2 && z >= z1 && z <= z2;
	}

	static boolean contains(BlockPos p) {
		return p == null || contains(p.getX(), p.getY(), p.getZ());
	}

	/**
	 * The passability a route may use: the cell must be inside the fence AND passable. Both cells
	 * a body occupies, because the head being over the top face is the body being outside.
	 */
	static Nav.Passable within(Nav.Passable free) {
		if (!active) return free;
		// A WALK STAYS A WALK. Nav tests `instanceof WalkingSpace` to apply the step rules a body
		// on foot needs (no diagonal climbs, footing under every cell); wrapped in a plain lambda
		// the fenced walk lost that type and routed like a flight - across gaps.
		if (free instanceof WalkingSpace walk) {
			return walk.confined((x, y, z) -> contains(x, y, z) && contains(x, y + 1, z));
		}
		return (x, y, z) -> contains(x, y, z) && contains(x, y + 1, z) && free.at(x, y, z);
	}

	// The body's allowed range for its FEET position. The box's outer faces are at x1 and x2+1;
	// the body is kept MARGIN inside them, and cannot rise past the top face minus its height.
	private static double loX() { return x1 + MARGIN; }
	private static double hiX() { return x2 + 1 - MARGIN; }
	private static double loZ() { return z1 + MARGIN; }
	private static double hiZ() { return z2 + 1 - MARGIN; }
	private static double loY() { return y1; }
	private static double hiY() { return y2 + 1 - HEIGHT; }

	private static double into(double v, double lo, double hi) {
		// A box thinner than the body has one legal answer: its middle.
		if (lo > hi) return (lo + hi) / 2;
		return Math.max(lo, Math.min(hi, v));
	}

	/** Rounding slack: a clamp is `(feet + step) clamped - feet`, and re-adding it is not exact. */
	private static final double EPS = 1.0e-6;

	/** Is a body standing at this position inside the fence? */
	static boolean holds(Vec3 feet) {
		if (!active) return true;
		return feet.x >= loX() - EPS && feet.x <= hiX() + EPS && feet.z >= loZ() - EPS
			&& feet.z <= hiZ() + EPS && feet.y >= loY() - EPS && feet.y <= hiY() + EPS;
	}

	/**
	 * The step, with anything that would carry the body past the fence taken out.
	 *
	 * <p>Inside the box a step that stays inside is returned unchanged. A step that would cross a
	 * face is cut at the face: the other components still carry, so the body slides along the
	 * fence rather than stopping dead against it. A body ALREADY outside — the fence was set while
	 * standing past it, or something else moved it — is pulled back in, no faster than
	 * {@link #RETURN_SPEED} or the step's own length, whichever is larger.
	 */
	static Vec3 clamp(Vec3 feet, Vec3 step) {
		if (!active) return step;
		Vec3 next = feet.add(step);
		Vec3 legal = new Vec3(into(next.x, loX(), hiX()), into(next.y, loY(), hiY()),
			into(next.z, loZ(), hiZ()));
		Vec3 out = legal.subtract(feet);
		double cap = Math.max(step.length(), RETURN_SPEED);
		if (out.length() > cap) out = out.normalize().scale(cap);
		return out;
	}

	static String describe() {
		if (!active) return "no autofly bounds — flight goes anywhere";
		return "autofly bounds " + x1 + " " + y1 + " " + z1 + " to " + x2 + " " + y2 + " " + z2
			+ " (" + (x2 - x1 + 1) + "x" + (y2 - y1 + 1) + "x" + (z2 - z1 + 1) + ")";
	}
}
