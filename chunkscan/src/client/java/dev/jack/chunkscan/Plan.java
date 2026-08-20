package dev.jack.chunkscan;

import net.minecraft.core.BlockPos;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Where to go and work, given what is actually in your pockets.
 *
 * <p>`/cscan next` answers "what is nearest" and `/cscan need` answers "what should I fetch". Neither
 * answers the question a big design actually poses, which is <b>where can I stand right now and
 * place a hundred blocks without moving or running out</b>. On a design of several thousand cells
 * that is the difference between a build session and an afternoon of walking.
 *
 * <p>Three things have to be true of a cluster before it is worth walking to, and all three are
 * measured rather than assumed:
 *
 * <ul>
 *   <li><b>You are carrying the material.</b> Not "it exists in a chest somewhere" - that is
 *       {@code need}'s question. Cells whose block is not in your inventory are not work you can do.</li>
 *   <li><b>You have ENOUGH of it.</b> Stock is allocated to clusters in rank order, so the second
 *       cluster is told what the first one leaves it. A cluster that says 120 cells when you have
 *       64 bricks has lied about the only number that mattered.</li>
 *   <li><b>It is within reach of one standing spot.</b> Clusters are built around a centre at a
 *       working radius, not by connectivity: a wall is one connected component and forty trips.</li>
 * </ul>
 */
final class Plan {
	/** About what you can place from one spot without walking. */
	static final int WORK_RADIUS = 6;
	/** More than this and the report is a list to read rather than a plan to follow. */
	static final int MAX_CLUSTERS = 6;

	record Cluster(BlockPos centre, List<Work.Cell> cells, Map<String, Integer> materials,
	               int blocked, int shortBy) {
		int size() {
			return cells.size();
		}

		/** Cells you can actually place: not scaffold-blocked, and covered by stock. */
		int doable() {
			return Math.max(0, cells.size() - blocked - shortBy);
		}
	}

	private Plan() {}

	/**
	 * Rank the places worth walking to.
	 *
	 * @param carrying what is in the player's inventory, by block name
	 * @param blockedCells cells with nothing to place against, so they cannot be counted as work
	 */
	static List<Cluster> clusters(List<Work.Cell> todo, Map<String, Integer> carrying,
	                              java.util.Set<Long> blockedCells, BlockPos from) {
		// Only cells whose material is on you. Everything else is `need`'s problem, not this one.
		List<Work.Cell> mine = new ArrayList<>();
		for (Work.Cell c : todo) {
			if (carrying.getOrDefault(c.item(), 0) > 0) mine.add(c);
		}
		if (mine.isEmpty()) return List.of();

		// Bin at the working radius to find dense spots cheaply - an all-pairs density scan over a
		// few thousand cells is not worth the wait for a number this coarse.
		Map<Long, List<Work.Cell>> bins = new LinkedHashMap<>();
		for (Work.Cell c : mine) {
			long key = BlockPos.asLong(Math.floorDiv(c.pos().getX(), WORK_RADIUS),
				Math.floorDiv(c.pos().getY(), WORK_RADIUS),
				Math.floorDiv(c.pos().getZ(), WORK_RADIUS));
			bins.computeIfAbsent(key, k -> new ArrayList<>()).add(c);
		}
		List<List<Work.Cell>> seeds = new ArrayList<>(bins.values());
		// densest first, then nearest: a big pile beats a near one, but a tie goes to your feet
		seeds.sort(Comparator.<List<Work.Cell>>comparingInt(List::size).reversed()
			.thenComparingDouble(l -> l.get(0).pos().distSqr(from)));

		Map<String, Integer> stock = new LinkedHashMap<>(carrying);
		java.util.Set<Long> taken = new java.util.HashSet<>();
		List<Cluster> out = new ArrayList<>();
		long r2 = (long) WORK_RADIUS * WORK_RADIUS;

		for (List<Work.Cell> seed : seeds) {
			if (out.size() >= MAX_CLUSTERS) break;
            if (seed.stream().allMatch(c -> taken.contains(c.pos().asLong()))) continue;
			BlockPos centre = centroid(seed);
			// gather every unclaimed cell within reach of that one standing spot
			List<Work.Cell> group = new ArrayList<>();
			for (Work.Cell c : mine) {
				if (taken.contains(c.pos().asLong())) continue;
				if (c.pos().distSqr(centre) <= r2) group.add(c);
			}
			if (group.size() < 3) continue;               // not worth walking to
			for (Work.Cell c : group) taken.add(c.pos().asLong());

			// Allocate stock IN RANK ORDER. The second cluster is told what the first one leaves.
			Map<String, Integer> want = new LinkedHashMap<>();
			for (Work.Cell c : group) want.merge(c.item(), 1, Integer::sum);
			int shortBy = 0;
			for (var e : want.entrySet()) {
				int have = stock.getOrDefault(e.getKey(), 0);
				int use = Math.min(have, e.getValue());
				stock.put(e.getKey(), have - use);
				shortBy += e.getValue() - use;
			}
			int blocked = 0;
			for (Work.Cell c : group) if (blockedCells.contains(c.pos().asLong())) blocked++;
			out.add(new Cluster(centre, group, want, blocked, shortBy));
		}
		// Report by what you can actually DO there, not by how many cells happen to be nearby.
		out.sort(Comparator.<Cluster>comparingInt(Cluster::doable).reversed()
			.thenComparingDouble(c -> c.centre().distSqr(from)));
		return out;
	}

	static BlockPos centroid(List<Work.Cell> cells) {
		long x = 0, y = 0, z = 0;
		for (Work.Cell c : cells) {
			x += c.pos().getX();
			y += c.pos().getY();
			z += c.pos().getZ();
		}
		int n = cells.size();
		return new BlockPos((int) (x / n), (int) (y / n), (int) (z / n));
	}

	/**
	 * One thing you are short of, and where it lives. `where` is null when nothing indexed holds it.
	 */
	record Restock(String item, int missing, Storage.Container where, int available) {}

	/**
	 * What this cluster is short of, and the nearest indexed container holding each.
	 *
	 * <p>The plan used to say "64 short of stock" and stop, leaving you to run `need` and join the
	 * two in your head. The container index already knows where the bricks are; a shortfall with no
	 * address is half an answer, and one you cannot be NAVIGATED to is most of the way to no answer
	 * at all — which is why this returns a container rather than a sentence.
	 */
	static List<Restock> restockTargets(Cluster c, Map<String, Integer> carrying,
	                                    Map<String, Storage.Container> index, BlockPos from) {
		List<Restock> out = new ArrayList<>();
		Map<String, Integer> left = new LinkedHashMap<>(carrying);
		for (var e : c.materials().entrySet()) {
			int have = left.getOrDefault(e.getKey(), 0);
			int miss = e.getValue() - have;
			left.put(e.getKey(), Math.max(0, have - e.getValue()));
			if (miss <= 0) continue;
			List<Storage.Hit> hits = Storage.find(index, e.getKey(), from);
			if (hits.isEmpty()) {
				out.add(new Restock(e.getKey(), miss, null, 0));
			} else {
				Storage.Hit h = hits.get(0);
				out.add(new Restock(e.getKey(), miss, h.container(), h.count()));
			}
		}
		// The biggest shortfall first: that is the trip most worth making, and with `/fly` the
		// walk between two chests costs about the same either way.
		out.sort(Comparator.comparingInt(Restock::missing).reversed());
		return out;
	}

	/** The same thing in words, for the chat report. */
	static List<String> restock(Cluster c, Map<String, Integer> carrying,
	                            Map<String, Storage.Container> index, BlockPos from) {
		List<String> out = new ArrayList<>();
		for (Restock r : restockTargets(c, carrying, index, from)) {
			if (r.where() == null) {
				out.add(r.missing() + " more " + r.item() + " — not in any indexed chest");
			} else {
				out.add(r.missing() + " more " + r.item() + " — " + r.available() + " in "
					+ r.where().describe() + " " + (int) Math.sqrt(r.where().pos().distSqr(from))
					+ "m " + Storage.direction(from, r.where().pos()));
			}
		}
		return out;
	}

	/** The first shortfall that has somewhere to be fetched from, or null. */
	static Restock firstFetchable(Cluster c, Map<String, Integer> carrying,
	                              Map<String, Storage.Container> index, BlockPos from) {
		for (Restock r : restockTargets(c, carrying, index, from)) {
			if (r.where() != null) return r;
		}
		return null;
	}

	/** The two or three materials a cluster needs, commonest first, for one line of chat. */
	static String materialLine(Cluster c, Map<String, Integer> carrying) {
		return c.materials().entrySet().stream()
			.sorted((l, r) -> Integer.compare(r.getValue(), l.getValue()))
			.limit(3)
			.map(e -> e.getValue() + "x " + e.getKey()
				+ " (have " + carrying.getOrDefault(e.getKey(), 0) + ")")
			.reduce((l, r) -> l + ", " + r).orElse("");
	}
}
