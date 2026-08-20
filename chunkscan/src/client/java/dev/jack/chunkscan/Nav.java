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
	/** Enough for a route through a building; small enough not to stutter. */
	static final int MAX_NODES = 12000;
	/** Beyond this the answer is "fly closer first". */
	static final int MAX_RANGE = 160;

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
	 * <p>The returned path EXCLUDES the start and ends at `to`.
	 */
	static List<BlockPos> route(Passable free, BlockPos from, BlockPos to) {
		Node start = new Node(from.getX(), from.getY(), from.getZ());
		Node goal = new Node(to.getX(), to.getY(), to.getZ());
		if (start.dist(goal) > MAX_RANGE) return List.of();

		Map<Long, Node> came = new HashMap<>();
		Map<Long, Double> g = new HashMap<>();
		PriorityQueue<Object[]> open = new PriorityQueue<>((a, b) ->
			Double.compare((Double) a[0], (Double) b[0]));
		g.put(start.key(), 0.0);
		open.add(new Object[]{start.dist(goal), start});

		int expanded = 0;

		while (!open.isEmpty() && expanded < MAX_NODES) {
			Node cur = (Node) open.poll()[1];
			if (cur.equals(goal)) return rebuild(came, cur);
			expanded++;

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
						open.add(new Object[]{ng + nb.dist(goal), nb});
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

	/** Is the straight line between two cells flyable? Sampled at half-block steps. */
	static boolean clear(Passable free, BlockPos a, BlockPos b) {
		double dx = b.getX() - a.getX(), dy = b.getY() - a.getY(), dz = b.getZ() - a.getZ();
		double len = Math.sqrt(dx * dx + dy * dy + dz * dz);
		if (len == 0) return true;
		int steps = (int) Math.ceil(len * 2);
		for (int i = 1; i <= steps; i++) {
			double t = (double) i / steps;
			int x = (int) Math.floor(a.getX() + dx * t + 0.5);
			int y = (int) Math.floor(a.getY() + dy * t + 0.5);
			int z = (int) Math.floor(a.getZ() + dz * t + 0.5);
			if (!free.at(x, y, z)) return false;
		}
		return true;
	}
}
