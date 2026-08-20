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
	/**
	 * The smallest a spot ever gets: about what you can place without moving your feet.
	 *
	 * <p>Only reached when you are nearly out of blocks. See {@link #radiusFor}.
	 */
	static final int MIN_RADIUS = 6;
	/**
	 * The largest. Past this it is not a trip, it is the island — and a "spot" you cannot see the
	 * far side of is not guidance, it is a compass bearing to a region.
	 */
	static final int MAX_RADIUS = 96;
	/** Kept for callers that just want the old reach figure. */
	static final int WORK_RADIUS = MIN_RADIUS;
	/** More than this and the report is a list to read rather than a plan to follow. */
	static final int MAX_CLUSTERS = 6;

	record Cluster(BlockPos centre, List<Work.Cell> cells, Map<String, Integer> materials,
	               int blocked, int sealed, int shortBy) {
		int size() {
			return cells.size();
		}

		/**
		 * Cells you can actually place standing there: covered by stock, with something to place
		 * against, and reachable.
		 *
		 * <p>`blocked` and `sealed` are the two ways the surrounding blocks can say no, and they are
		 * opposite failures — nothing to click, and no way in. Counting either as work sends you to
		 * stand in front of something you cannot build.
		 */
		int doable() {
			return Math.max(0, cells.size() - blocked - sealed - shortBy);
		}
	}

	private Plan() {}

	/**
	 * How many cells your inventory can actually cover.
	 *
	 * <p>Summed per material and capped by what is NEEDED, because 3,000 cobblestone does not help
	 * a design that wants forty of it.
	 */
	static int budget(List<Work.Cell> mine, Map<String, Integer> carrying) {
		Map<String, Integer> want = new LinkedHashMap<>();
		for (Work.Cell c : mine) want.merge(c.item(), 1, Integer::sum);
		int n = 0;
		for (var e : want.entrySet()) n += Math.min(carrying.getOrDefault(e.getKey(), 0), e.getValue());
		return n;
	}

	/**
	 * A TRIP IS BOUNDED BY WHAT YOU CARRY, NOT BY YOUR REACH.
	 *
	 * <p>The first version of this sized every spot at one standing radius, and on a thirty-thousand
	 * cell design that is a plan made of five hundred trips. It was reasoning about WALKING. With
	 * flight, moving forty blocks inside a region costs nothing and flying back to a chest costs the
	 * session, so the unit that matters is one inventory load: the radius grows until the spot holds
	 * about as many cells as you are carrying blocks for.
	 *
	 * <p>Carrying 64 bricks it stays at {@link #MIN_RADIUS} and behaves as before. Carrying six
	 * shulkers it opens out until the trip is worth making.
	 */
	static int radiusFor(int budget) {
		int r = MIN_RADIUS;
		// cells scale with the cube of the radius, so double it rather than creeping
		while (r < MAX_RADIUS && (long) r * r * r < (long) budget * 4) r *= 2;
		return Math.min(r, MAX_RADIUS);
	}

	/**
	 * Rank the places worth walking to.
	 *
	 * @param carrying what is in the player's inventory, by block name
	 * @param blockedCells cells with nothing to place against, so they cannot be counted as work
	 */
	static List<Cluster> clusters(List<Work.Cell> todo, Map<String, Integer> carrying,
	                              java.util.Set<Long> blockedCells, BlockPos from) {
		return clusters(todo, carrying, blockedCells, java.util.Set.of(), from);
	}

	/**
	 * @param blockedCells cells with nothing to place against
	 * @param sealedCells  cells with no way to reach them
	 */
	static List<Cluster> clusters(List<Work.Cell> todo, Map<String, Integer> carrying,
	                              java.util.Set<Long> blockedCells, java.util.Set<Long> sealedCells,
	                              BlockPos from) {
		// Only cells whose material is on you. Everything else is `need`'s problem, not this one.
		List<Work.Cell> mine = new ArrayList<>();
		for (Work.Cell c : todo) {
			if (carrying.getOrDefault(c.item(), 0) > 0) mine.add(c);
		}
		if (mine.isEmpty()) return List.of();

		// Bin at the working radius to find dense spots cheaply - an all-pairs density scan over a
		// few thousand cells is not worth the wait for a number this coarse.
		int bin = Math.max(MIN_RADIUS, radiusFor(budget(mine, carrying)));
		Map<Long, List<Work.Cell>> bins = new LinkedHashMap<>();
		for (Work.Cell c : mine) {
			long key = BlockPos.asLong(Math.floorDiv(c.pos().getX(), bin),
				Math.floorDiv(c.pos().getY(), bin),
				Math.floorDiv(c.pos().getZ(), bin));
			bins.computeIfAbsent(key, k -> new ArrayList<>()).add(c);
		}
		List<List<Work.Cell>> seeds = new ArrayList<>(bins.values());
		// densest first, then nearest: a big pile beats a near one, but a tie goes to your feet
		seeds.sort(Comparator.<List<Work.Cell>>comparingInt(List::size).reversed()
			.thenComparingDouble(l -> l.get(0).pos().distSqr(from)));

		Map<String, Integer> stock = new LinkedHashMap<>(carrying);
		java.util.Set<Long> taken = new java.util.HashSet<>();
		List<Cluster> out = new ArrayList<>();
		// Sized to the inventory, not to arm's length. One trip, not one standing spot.
		int radius = radiusFor(budget(mine, carrying));
		long r2 = (long) radius * radius;

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
			int blocked = 0, sealed = 0;
			for (Work.Cell c : group) {
				long k = c.pos().asLong();
				if (blockedCells.contains(k)) blocked++;
				else if (sealedCells.contains(k)) sealed++;   // one reason each, never counted twice
			}
			out.add(new Cluster(centre, group, want, blocked, sealed, shortBy));
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
		return restockTargets(c, carrying, index, from, java.util.Set.of());
	}

	/**
	 * @param skip container positions to pass over — chests that have just failed.
	 *
	 * <p><b>This parameter is the fix for a freeze.</b> Without it the nearest container was chosen
	 * every time, so once a chest failed and went into its cooling-off period the loop was pointed
	 * at it, refused to withdraw from it, and sat there: guided forever at a chest it would not
	 * open. A shortfall usually has several containers holding it — take the next one.
	 */
	static List<Restock> restockTargets(Cluster c, Map<String, Integer> carrying,
	                                    Map<String, Storage.Container> index, BlockPos from,
	                                    java.util.Set<Long> skip) {
		List<Restock> out = new ArrayList<>();
		Map<String, Integer> left = new LinkedHashMap<>(carrying);
		for (var e : c.materials().entrySet()) {
			int have = left.getOrDefault(e.getKey(), 0);
			int miss = e.getValue() - have;
			left.put(e.getKey(), Math.max(0, have - e.getValue()));
			if (miss <= 0) continue;
			List<Storage.Hit> all = Storage.findExact(index, e.getKey(), from);
			List<Storage.Hit> hits = new ArrayList<>();
			for (Storage.Hit h : all) {
				if (!skip.contains(h.container().pos().asLong())) hits.add(h);
			}
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
		return firstFetchable(c, carrying, index, from, java.util.Set.of());
	}

	static Restock firstFetchable(Cluster c, Map<String, Integer> carrying,
	                              Map<String, Storage.Container> index, BlockPos from,
	                              java.util.Set<Long> skip) {
		for (Restock r : restockTargets(c, carrying, index, from, skip)) {
			if (r.where() != null) return r;
		}
		return null;
	}

	// ---------------------------------------------------------------- the fetch policy
	//
	// FILL THE PACK, THEN BUILD UNTIL IT IS DRY. The loop used to decide this per SPOT: if the best
	// cluster was short of anything, fetch. So it fetched with a full inventory and plenty to do,
	// took one spot's worth, flew back, and on a design of any size that is a session of commuting.
	//
	// Two questions instead, and they are asked in this order:
	//
	//   1. is there anything at all I can place with what I am carrying?   -> build, and do not fetch
	//   2. otherwise: is there something to fetch, and room to put it?     -> fetch until full
	//
	// Which means a fetch trip ends when the PACK is full or the DESIGN is covered, not when one
	// spot's shortfall happens to be met.

	/** Is any spot worth standing at right now? One placeable cell is enough to say yes. */
	static boolean anyDoable(List<Cluster> clusters) {
		for (Cluster c : clusters) if (c.doable() > 0) return true;
		return false;
	}

	/** How much of one item the pack could still take. Supplied by {@link Work#room}. */
	@FunctionalInterface
	interface Room {
		int of(String item);
	}

	/**
	 * The next thing to go and get, or null when the trip is over.
	 *
	 * <p>Two ways to be done, and they are different: nothing left worth fetching, or nowhere left to
	 * put it. Both mean go and build.
	 *
	 * <p>It walks the whole list rather than judging the first entry, because a pack with no space
	 * for the biggest shortfall may have plenty for the next one — stopping at the first is a trip
	 * not taken and a spot not finished.
	 *
	 * @param addressable shortfalls that have a container behind them — see {@link #fetchTargets}
	 */
	static Restock nextFetch(List<Restock> addressable, Room room) {
		for (Restock r : addressable) {
			if (room.of(r.item()) > 0) return r;
		}
		return null;
	}

	/**
	 * What the WHOLE remaining design is short of, biggest shortfall first, with an address.
	 *
	 * <p>Not per-cluster: a cluster's shortfall is the wrong unit for a trip. {@link #restockTargets}
	 * answers "what is this spot missing" and is still what the per-spot report wants; this answers
	 * "what should I be carrying", which is the question a trip to the store hall is asking.
	 *
	 * <p>A shortfall with nowhere to fetch it from is DROPPED here rather than reported as a null
	 * address, because this list is used for navigation: an entry with no container is a place to fly
	 * to that does not exist. It comes back in words through {@link #restock}.
	 */
	static List<Restock> fetchTargets(List<Work.Cell> todo, Map<String, Integer> carrying,
	                                  Map<String, Storage.Container> index, BlockPos from,
	                                  Set<Long> skip) {
		Map<String, Integer> want = new LinkedHashMap<>();
		for (Work.Cell c : todo) want.merge(c.item(), 1, Integer::sum);
		List<Restock> out = new ArrayList<>();
		for (var e : want.entrySet()) {
			int miss = e.getValue() - carrying.getOrDefault(e.getKey(), 0);
			if (miss <= 0) continue;
			for (Storage.Hit h : Storage.findExact(index, e.getKey(), from)) {
				if (skip.contains(h.container().pos().asLong())) continue;
				out.add(new Restock(e.getKey(), miss, h.container(), h.count()));
				break;                                   // nearest one that is not cooling off
			}
		}
		out.sort(Comparator.comparingInt(Restock::missing).reversed());
		return out;
	}

	/**
	 * How much to actually take: the shortfall, capped by what will fit.
	 *
	 * <p>Capped by the CHEST's count too — asking for more than is in there is what left the loop
	 * standing at a chest waiting for a stack that was never coming.
	 */
	static int takeHowMany(Restock r, int room) {
		return Math.max(0, Math.min(room, Math.min(r.missing(), Math.max(0, r.available()))));
	}

	/** How far the cluster reaches from its centre, so "1,850 cells" has a size attached. */
	static int extent(Cluster c) {
		double worst = 0;
		for (Work.Cell x : c.cells()) worst = Math.max(worst, x.pos().distSqr(c.centre()));
		return (int) Math.ceil(Math.sqrt(worst));
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
