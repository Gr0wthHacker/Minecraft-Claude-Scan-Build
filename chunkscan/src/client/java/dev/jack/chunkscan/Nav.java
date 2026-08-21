package dev.jack.chunkscan;

import net.minecraft.core.BlockPos;
import net.minecraft.world.level.Level;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.PriorityQueue;

/**
 * A route through the world the client can already see.
 *
 * <p>Flying at a bearing and lifting over whatever you hit gets you across open air and no further:
 * it cannot find a doorway, it presses you into the outside of a wall the room is behind, and on
 * this island — a deck under a plate under a sky bird — most destinations are inside something. The
 * client knows every block. It should route.
 *
 * <p>Plain A* in three dimensions, with three things that matter more than the algorithm:
 *
 * <ul>
 *   <li><b>Clearance, not emptiness.</b> A player is two blocks tall, so a cell is only passable if
 *       the cell above it is too. Checking one cell finds "doorways" a head high and walks you into
 *       the lintel.</li>
 *   <li><b>No corner cutting.</b> A diagonal step is only allowed when the orthogonal cells it
 *       passes between are clear as well. Without that, A* squeezes through the corner of a door
 *       frame — geometrically shorter, and you snag on the jamb every time.</li>
 *   <li><b>Unloaded is passable.</b> A chunk that has not loaded is not a wall; refusing to route
 *       through it would fail every long flight. The route is recomputed as you go, so it sharpens
 *       as the world arrives.</li>
 * </ul>
 *
 * <p>Bounded hard, because this runs on the client thread: past {@link #MAX_NODES} it gives up and
 * says so rather than freezing the game to be clever.
 */
final class Nav {
	/**
	 * Node budget. Generous because the FAILURE is what hurts, not the success: when a route exists
	 * a weighted search finds it in hundreds of nodes, and when none exists the caller backs off
	 * for three seconds rather than retrying twice a second.
	 *
	 * <p>It was 12,000 and that was too small in practice. A* over open 3D air expands a SPHERE, so
	 * the frontier grows as the cube of the distance — a hundred-block hop exhausted the budget
	 * even with a clear line, the route came back empty, and the caller fell through to flying
	 * straight at the terrain. "It tries to fly through walls" was this, not the steering.
	 *
	 * <p>40,000 then, 120,000 now, and the raise is worth much less than it looks: the two changes
	 * that actually stopped the failures are the line-of-sight shortcut (a clear hop costs ZERO
	 * nodes, and across open sky that is most of them) and {@link #GOAL_SLACK} (a goal that blocks
	 * motion can never be reached, so every one of those searches spent the whole budget before
	 * failing). The budget is what is left for the genuinely hard indoor case.
	 */
	static final int MAX_NODES = 120000;
	/**
	 * ...and a wall-clock budget, because the node count is not the thing that hurts the player.
	 *
	 * <p>This runs on the client thread, so the honest limit is "how long may I freeze the game
	 * for", and that is a number of milliseconds rather than a number of nodes: an expansion in open
	 * air costs a handful of map lookups, one against dense geometry costs 26 neighbours x 4 corner
	 * checks x 3 world lookups. 25ms is under two frames, and a search that hits it has failed for
	 * practical purposes anyway.
	 */
	static final long MAX_MILLIS = 25;
	/**
	 * Greediness. Multiplying the heuristic makes the search push at the goal instead of expanding
	 * evenly in every direction; the route can come out a few blocks longer than optimal, which for
	 * flying somewhere is worth nothing at all against finding it in a tenth of the nodes.
	 */
	static final double GREED = 1.4;
	/**
	 * Beyond this the search is refused OUTRIGHT — no nodes expanded, empty list returned.
	 *
	 * <p>Was 160, then 256, now 512. Anything past it fails INSTANTLY and silently and the caller
	 * falls through to flying straight at the terrain, which is indistinguishable from the router
	 * being broken — so the gate wants to be well clear of any route the island actually asks for
	 * (deck to lowland floor is 152; deck to sky bird and back down the far side is more). The gate
	 * itself is free. What costs is the search, and that is bounded by {@link #MAX_NODES} and
	 * {@link #MAX_MILLIS} instead, which is where a cost belongs.
	 */
	static final int MAX_RANGE = 512;
	/**
	 * Past this a failed full search is retried toward a SUB-GOAL on the straight line rather than
	 * being given up on.
	 *
	 * <p>A* expands a sphere, so the cost of a long route is cubic in its length while the cost of
	 * the same route walked in stages is linear. The route is recomputed twice a second and re-staged
	 * as you go, so staging costs nothing and turns "no route, flying direct" — the thing that flies
	 * you into terrain — into real progress plus a fresh search from closer in.
	 */
	static final int STAGE = 128;
	/**
	 * How far off a solid destination we are willing to finish.
	 *
	 * <p><b>A CHEST BLOCKS MOTION.</b> Every fetch target is a container's own cell and every build
	 * spot is a cluster centroid, which lands inside rock about as often as not — so the goal is
	 * routinely a cell no route can ever enter. Nothing checked for it: the goal was simply never
	 * expanded, the search ran to the end of its budget, came back empty, and the caller fell through
	 * to flying straight at the wall the chest is in. That is most of "it still gets stuck".
	 *
	 * <p>So a solid goal is satisfied by any passable cell within this radius of it, nearest first.
	 * 2 covers a chest against a wall, a centroid one course inside a floor, and the far side of a
	 * double slab.
	 */
	static final int GOAL_SLACK = 2;
	/**
	 * How many cells {@link #escape} will look at before settling for the best it has found.
	 *
	 * <p>A flood is cheap per cell — no queue ordering, one visit each — and it only runs when a real
	 * search has already failed, which is rare and already behind a backoff.
	 */
	static final int ESCAPE_CELLS = 6000;
	/** How far from the player {@link #escape} may wander. Round a building, not across the island. */
	static final int ESCAPE_RADIUS = 24;

	private Nav() {}

	/** What the world looks like to a route. Split out so the search is testable. */
	@FunctionalInterface
	interface Passable {
		boolean at(int x, int y, int z);
	}

	/**
	 * Two clear cells, because a player is two tall. `blocksMotion` rather than `isAir`, so a slab
	 * or a fence is judged by what it actually stops rather than by whether it is nothing.
	 */
	static Passable of(Level level) {
		BlockPos.MutableBlockPos c = new BlockPos.MutableBlockPos();
		return (x, y, z) -> {
			if (!level.isLoaded(c.set(x, y, z))) return true;       // not a wall: just unseen
			if (level.getBlockState(c.set(x, y, z)).blocksMotion()) return false;
			return !level.getBlockState(c.set(x, y + 1, z)).blocksMotion();
		};
	}

	/**
	 * The same world, to something that cannot fly.
	 *
	 * <p>Clearance is not enough on foot: {@link #of} happily routes through open air thirty blocks
	 * above a floor, which is a perfect flight plan and a walk into a hole. A walkable cell needs
	 * FOOTING as well as headroom.
	 *
	 * <p>One course of slack under the floor, deliberately — that is a step DOWN, and without it
	 * every route breaks at the lip of a stair, a doorway sill or a ledge. Anything deeper is a fall,
	 * and a fall is not a step.
	 */
	static Passable standable(Level level) {
		BlockPos.MutableBlockPos c = new BlockPos.MutableBlockPos();
		return (x, y, z) -> {
			if (!level.isLoaded(c.set(x, y, z))) return true;
			if (level.getBlockState(c.set(x, y, z)).blocksMotion()) return false;
			if (level.getBlockState(c.set(x, y + 1, z)).blocksMotion()) return false;
			return level.getBlockState(c.set(x, y - 1, z)).blocksMotion()
				|| level.getBlockState(c.set(x, y - 2, z)).blocksMotion();
		};
	}

	private record Node(int x, int y, int z) {
		long key() {
			return BlockPos.asLong(x, y, z);
		}

		double dist(Node o) {
			double dx = x - o.x, dy = y - o.y, dz = z - o.z;
			return Math.sqrt(dx * dx + dy * dy + dz * dz);
		}
	}

	/**
	 * A route from `from` to `to`, or an empty list when there is not one within the bounds.
	 *
	 * <p>The returned path EXCLUDES the start and ends at `to` — or, when `to` itself blocks motion,
	 * at the nearest cell within {@link #GOAL_SLACK} of it that does not.
	 *
	 * <p>Three gates before any node is expanded, in cost order:
	 * <ol>
	 *   <li><b>Out of range</b> — refused outright.</li>
	 *   <li><b>Line of sight</b> — if you can fly straight there, that IS the route. Costs nothing,
	 *       and across this island's open sky it answers most calls.</li>
	 *   <li><b>Staging</b> — a long search that fails is retried toward a sub-goal, because a route
	 *       walked in stages is linear in its length where one search is cubic.</li>
	 * </ol>
	 */
	static List<BlockPos> route(Passable free, BlockPos from, BlockPos to) {
		if (from.distSqr(to) > (double) MAX_RANGE * MAX_RANGE) return List.of();

		// ---- 2. LINE OF SIGHT. The cheapest route is the one you do not search for, and it is also
		// the commonest: fetch trips across this island are mostly open air. `clear` already models
		// the player's width, so if it says yes there is nothing an A* could improve on.
		BlockPos aim = reachable(free, to);
		if (aim != null && clear(free, from, aim)) return List.of(aim);

		// ONE budget for the whole call, shared by every attempt below. Otherwise each staged retry
		// gets its own 25ms and four of them is a visible hitch twice a second.
		long deadline = System.nanoTime() + MAX_MILLIS * 1_000_000L;

		List<BlockPos> direct = search(free, from, to, deadline);
		if (!direct.isEmpty()) return direct;

		// ---- 3. STAGE. Long searches fail by exhausting a budget, not by proving anything, so
		// getting closer and asking again is a better answer than giving up. Shortening on each try,
		// because a sub-goal can land inside the island as easily as in front of it.
		double d = Math.sqrt(from.distSqr(to));
		for (int stage = STAGE; stage >= 16 && stage < d; stage /= 2) {
			if (System.nanoTime() > deadline) break;
			List<BlockPos> staged = search(free, from, along(from, to, stage), deadline);
			if (!staged.isEmpty()) return staged;
		}
		return List.of();
	}

	/**
	 * When there is no route: the best you CAN reach, which is how you get round a wall.
	 *
	 * <p>Flying direct at an unreachable goal presses you into whatever is between, which is the
	 * thing this whole file exists to stop — and the previous fallback did exactly that, with a
	 * little upward nudge that mostly ground you along the wall. Getting round an obstacle is not a
	 * heuristic, it is a search: flood outward from where you stand and take the reachable cell that
	 * gets you CLOSEST to the goal. Up, down, left, right, behind — whichever actually helps.
	 *
	 * <p>Breadth-first, so it is bounded by cells rather than by geometry, and cheap: no priority
	 * queue, no heuristic, one visit per cell. Re-run as you go it is a wall-follower that always
	 * makes progress, and when it cannot improve at all it returns empty — which is the honest
	 * answer that you are shut in.
	 */
	static List<BlockPos> escape(Passable free, BlockPos from, BlockPos to, int radius) {
		Map<Long, Node> came = new HashMap<>();
		java.util.ArrayDeque<Node> queue = new java.util.ArrayDeque<>();
		java.util.Set<Long> seen = new java.util.HashSet<>();
		Node start = new Node(from.getX(), from.getY(), from.getZ());
		queue.add(start);
		seen.add(start.key());

		Node best = null;
		double bestD = Math.sqrt(from.distSqr(to));
		long r2 = (long) radius * radius;
		int visited = 0;

		while (!queue.isEmpty() && visited < ESCAPE_CELLS) {
			Node cur = queue.poll();
			visited++;
			for (int dx = -1; dx <= 1; dx++) {
				for (int dy = -1; dy <= 1; dy++) {
					for (int dz = -1; dz <= 1; dz++) {
						if (dx == 0 && dy == 0 && dz == 0) continue;
						int nx = cur.x + dx, ny = cur.y + dy, nz = cur.z + dz;
						Node nb = new Node(nx, ny, nz);
						if (!seen.add(nb.key())) continue;
						if (from.distSqr(new BlockPos(nx, ny, nz)) > r2) continue;
						if (!free.at(nx, ny, nz)) continue;
						if (dx != 0 && !free.at(cur.x + dx, cur.y, cur.z)) continue;
						if (dy != 0 && !free.at(cur.x, cur.y + dy, cur.z)) continue;
						if (dz != 0 && !free.at(cur.x, cur.y, cur.z + dz)) continue;
						came.put(nb.key(), cur);
						queue.add(nb);
						double d = Math.sqrt(new BlockPos(nx, ny, nz).distSqr(to));
						if (d < bestD - 0.5) {          // must actually IMPROVE, not tie
							bestD = d;
							best = nb;
						}
					}
				}
			}
		}
		return best == null ? List.of() : rebuild(came, best);
	}

	/** A point `dist` of the way from `a` toward `b`. */
	static BlockPos along(BlockPos a, BlockPos b, double dist) {
		double dx = b.getX() - a.getX(), dy = b.getY() - a.getY(), dz = b.getZ() - a.getZ();
		double len = Math.sqrt(dx * dx + dy * dy + dz * dz);
		if (len <= dist || len == 0) return b;
		double t = dist / len;
		return new BlockPos((int) Math.round(a.getX() + dx * t), (int) Math.round(a.getY() + dy * t),
			(int) Math.round(a.getZ() + dz * t));
	}

	/**
	 * The cell a route may actually finish in, given a destination that may be solid.
	 *
	 * <p>Nearest passable cell within {@link #GOAL_SLACK}, or null when the destination is buried.
	 * Ties break DOWNWARD-last: standing on top of a chest is a better place to be handed to than
	 * hovering under it, and the sort is by true distance so the six faces come before the corners.
	 */
	static BlockPos reachable(Passable free, BlockPos goal) {
		if (free.at(goal.getX(), goal.getY(), goal.getZ())) return goal;
		BlockPos best = null;
		double bestD = Double.MAX_VALUE;
		for (int dx = -GOAL_SLACK; dx <= GOAL_SLACK; dx++) {
			for (int dy = -GOAL_SLACK; dy <= GOAL_SLACK; dy++) {
				for (int dz = -GOAL_SLACK; dz <= GOAL_SLACK; dz++) {
					if (dx == 0 && dy == 0 && dz == 0) continue;
					int x = goal.getX() + dx, y = goal.getY() + dy, z = goal.getZ() + dz;
					if (!free.at(x, y, z)) continue;
					// a hair of bias for staying level, so a chest in a wall hands you the cell in
					// front of it rather than the one on the ceiling above it
					double d = dx * dx + dy * dy * 1.6 + dz * dz;
					if (d < bestD) {
						bestD = d;
						best = new BlockPos(x, y, z);
					}
				}
			}
		}
		return best;
	}

	/** The A* itself. `to` may block motion; see {@link #reachable}. */
	private static List<BlockPos> search(Passable free, BlockPos from, BlockPos to, long deadline) {
		BlockPos aim = reachable(free, to);
		if (aim == null) return List.of();          // the destination is buried: no route exists
		Node start = new Node(from.getX(), from.getY(), from.getZ());
		Node goal = new Node(aim.getX(), aim.getY(), aim.getZ());
		if (start.equals(goal)) return List.of();

		Map<Long, Node> came = new HashMap<>();
		Map<Long, Double> g = new HashMap<>();
		PriorityQueue<Object[]> open = new PriorityQueue<>((a, b) ->
			Double.compare((Double) a[0], (Double) b[0]));
		g.put(start.key(), 0.0);
		open.add(new Object[]{start.dist(goal) * GREED, start});

		int expanded = 0;

		while (!open.isEmpty() && expanded < MAX_NODES) {
			Node cur = (Node) open.poll()[1];
			if (cur.equals(goal)) return rebuild(came, cur);
			expanded++;
			// Checked in blocks: nanoTime is not free either, and the frontier does not change
			// character between one expansion and the next.
			if ((expanded & 255) == 0 && System.nanoTime() > deadline) break;

			for (int dx = -1; dx <= 1; dx++) {
				for (int dy = -1; dy <= 1; dy++) {
					for (int dz = -1; dz <= 1; dz++) {
						if (dx == 0 && dy == 0 && dz == 0) continue;
						int nx = cur.x + dx, ny = cur.y + dy, nz = cur.z + dz;
						if (!free.at(nx, ny, nz)) continue;
						// NO CORNER CUTTING: every orthogonal component of a diagonal must be clear
						// too, or the route squeezes through the corner of a door frame and you
						// catch on the jamb.
						if (dx != 0 && !free.at(cur.x + dx, cur.y, cur.z)) continue;
						if (dy != 0 && !free.at(cur.x, cur.y + dy, cur.z)) continue;
						if (dz != 0 && !free.at(cur.x, cur.y, cur.z + dz)) continue;

						Node nb = new Node(nx, ny, nz);
						double step = cur.dist(nb);
						double ng = g.get(cur.key()) + step;
						Double old = g.get(nb.key());
						if (old != null && ng >= old) continue;
						g.put(nb.key(), ng);
						came.put(nb.key(), cur);
						open.add(new Object[]{ng + nb.dist(goal) * GREED, nb});
					}
				}
			}
		}
		// NO PARTIAL ROUTES. An earlier version handed back the best progress it had made when the
		// node budget ran out, on the theory that half a route beats none. It does not:
		//
		//   - in open sky the search NEVER exhausts, because there is always more air to expand
		//     into, so the budget always runs out and the partial always fired - including when the
		//     destination was sealed and there was no route at all;
		//   - and a partial route reads to the caller as a real one, which switches off the
		//     straight-line fallback that might actually have got there.
		//
		// Empty means "I could not find a way", and the caller says so and flies direct instead.
		// That is a worse route honestly labelled, rather than a wrong one confidently followed.
		//
		// STAGING is the honest version of the same instinct, and it lives in route(): a shorter
		// search that SUCCEEDS, rather than a long one that half-failed.
		return List.of();
	}

	private static List<BlockPos> rebuild(Map<Long, Node> came, Node end) {
		List<BlockPos> out = new ArrayList<>();
		Node cur = end;
		while (cur != null) {
			out.add(new BlockPos(cur.x, cur.y, cur.z));
			cur = came.get(cur.key());
		}
		Collections.reverse(out);
		if (!out.isEmpty()) out.remove(0);              // the start is where we already are
		return out;
	}

	/**
	 * Drop waypoints you can fly straight through.
	 *
	 * <p>A* returns every cell it stepped on, which through open air is a bead chain of forty
	 * points and a flight path that visibly zig-zags between them. Keeping only the corners — the
	 * points where the straight line would clip something — leaves the doorways and throws away the
	 * rest.
	 */
	static List<BlockPos> simplify(Passable free, BlockPos from, List<BlockPos> path) {
		List<BlockPos> out = new ArrayList<>();
		BlockPos anchor = from;
		for (int i = 0; i < path.size(); i++) {
			boolean last = i == path.size() - 1;
			if (last || !clear(free, anchor, path.get(i + 1))) {
				out.add(path.get(i));
				anchor = path.get(i);
			}
		}
		return out;
	}

	/**
	 * Is the straight line between two cells flyable, for a body 0.6 wide?
	 *
	 * <p>Sampled every quarter block, and each sample checks the four cells the player's WIDTH
	 * actually covers rather than the single cell its centre line passes through. The centre-only
	 * version was too permissive: a line running diagonally between two blocks touched neither of
	 * their centres, `simplify` straightened the route through the gap, and the flight caught on
	 * the corner. That is the other half of "it tries to fly through walls".
	 */
	static boolean clear(Passable free, BlockPos a, BlockPos b) {
		double dx = b.getX() - a.getX(), dy = b.getY() - a.getY(), dz = b.getZ() - a.getZ();
		double len = Math.sqrt(dx * dx + dy * dy + dz * dz);
		if (len == 0) return true;
		int steps = (int) Math.ceil(len * 4);
		for (int i = 1; i <= steps; i++) {
			double t = (double) i / steps;
			double px = a.getX() + dx * t, py = a.getY() + dy * t, pz = a.getZ() + dz * t;
			int y = (int) Math.floor(py + 0.5);
			for (double ox : new double[]{-0.35, 0.35}) {
				for (double oz : new double[]{-0.35, 0.35}) {
					if (!free.at((int) Math.floor(px + ox + 0.5), y,
						(int) Math.floor(pz + oz + 0.5))) return false;
				}
			}
		}
		return true;
	}
}
