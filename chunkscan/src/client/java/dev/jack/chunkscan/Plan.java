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
	static final int MAX_RADIUS = 48;
	/** Kept for callers that just want the old reach figure. */
	static final int WORK_RADIUS = MIN_RADIUS;
	/** More than this and the report is a list to read rather than a plan to follow. */
	static final int MAX_CLUSTERS = 6;

	/**
	 * How far you should be willing to fly to double the work waiting for you.
	 *
	 * <p>Ranking was {@code doable} first with distance as a TIE-BREAK, which across a park spanning
	 * six hundred blocks means distance is never consulted at all: exact ties in count are rare, so
	 * a spot with 400 cells at the far end of the map beats 399 at your feet, every recount. The
	 * loop then spends the session travelling.
	 *
	 * <p>So a spot is worth {@code doable} discounted by how far it is: at this many blocks it must
	 * carry twice the work to win, at twice this, four times. 48 is about one comfortable flight
	 * here - short enough that the loop finishes what is under it first, long enough that it will
	 * still cross a land for a genuinely bigger job rather than picking at scraps.
	 */
	static final double TRAVEL_SCALE = 48.0;

	/**
	 * A place worth going to.
	 *
	 * @param cells every cell of the design in reach of one standing spot — including the ones that
	 *              cannot be built yet, because they are still part of what is left here
	 * @param ready the subset you could actually place: not floating, not sealed in. <b>This is what
	 *              anything pointing a player at the work must use.</b> The two were the same list
	 *              once and the loop marked out whole bins of cells with nothing to place against,
	 *              sent you to stand at them, and waited twenty seconds for a printer that was never
	 *              going to place a block in mid-air.
	 */
	record Cluster(BlockPos centre, List<Work.Cell> cells, List<Work.Cell> ready,
	               Map<String, Integer> materials, int blocked, int sealed, int shortBy) {
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
			return Math.max(0, ready.size() - shortBy);
		}

		/**
		 * What this spot is worth from where you are standing: work, discounted by travel.
		 *
		 * <p>Nearness is not a tie-break, it is part of the price. See {@link #TRAVEL_SCALE}.
		 */
		double worth(BlockPos from) {
			return doable() / (1.0 + Math.sqrt(centre.distSqr(from)) / TRAVEL_SCALE);
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
	/**
	 * How much bigger a sphere has to get before growing it is worth it.
	 *
	 * <p>Doubling a radius is EIGHT TIMES the volume. If that only finds half again as many cells,
	 * the work is not out there and the extra reach is just distance.
	 */
	static final double DENSITY_GAIN = 1.5;

	/**
	 * The radius this PARTICULAR pile of work needs, which is not the same as the one the pack
	 * could pay for.
	 *
	 * <p><b>{@link #radiusFor} is a function of the INVENTORY and nothing else.</b> That is right
	 * about the ceiling - there is no sense gathering more cells than you can place - and it was
	 * being used as the answer. Carrying six shulkers it returned 48 whether the work was a wall
	 * twelve blocks across or a scatter over the whole deck, so a dense pile at your feet was
	 * treated as a region half the size of the island and the loop flew about inside its own spot.
	 * Jack: <i>"its flying crazy far for no reason"</i> - and the reason really was nothing to do
	 * with the work, it was how much he happened to be carrying.
	 *
	 * <p>So the pack sets the CAP and the geometry sets the number: grow from {@link #MIN_RADIUS}
	 * only while a bigger sphere actually finds meaningfully more to do. A wall stays tight; a
	 * scatter opens out as far as it has to and no further.
	 */
	static int fitRadius(List<Work.Cell> cells, BlockPos centre, int budget) {
		int cap = radiusFor(budget);
		int r = MIN_RADIUS;
		int have = within(cells, centre, r);
		while (r * 2 <= cap) {
			if (have >= budget) break;                     // the pack is the ceiling
			int bigger = within(cells, centre, r * 2);
			if (bigger < have * DENSITY_GAIN) break;       // eight times the volume, no more work
			r *= 2;
			have = bigger;
		}
		return Math.min(r, cap);
	}

	static int within(List<Work.Cell> cells, BlockPos centre, int r) {
		long r2 = (long) r * r;
		int n = 0;
		for (Work.Cell c : cells) if (c.pos().distSqr(centre) <= r2) n++;
		return n;
	}

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
		return clusters(todo, carrying, blockedCells, sealedCells, from, null);
	}

	/**
	 * @param keep the spot being worked, if any: its seed is clustered FIRST so the cap on
	 *             clusters can never eject the region the loop is standing in. As cells there are
	 *             placed its bin shrinks, and sorted by size alone it dropped out of the top six
	 *             while still holding work — the loop then announced a "next spot" and reset its
	 *             stations for a region it had never left.
	 */
	static List<Cluster> clusters(List<Work.Cell> todo, Map<String, Integer> carrying,
	                              java.util.Set<Long> blockedCells, java.util.Set<Long> sealedCells,
	                              BlockPos from, BlockPos keep) {
		List<Work.Cell> mine = new ArrayList<>();
		for (Work.Cell c : todo) {
			if (carrying.getOrDefault(c.item(), 0) > 0) mine.add(c);
		}
		if (mine.isEmpty()) return List.of();

		// Bin at the working radius to find dense spots cheaply - an all-pairs density scan over a
		// few thousand cells is not worth the wait for a number this coarse.
		// A SEEDING GRAIN IS NOT A TRIP SIZE. This used to be the trip radius, so a big pack binned
		// the whole design into a handful of boxes and every spot came out the size of a box. The
		// grain only has to be fine enough to find where the work IS; how far a spot then reaches is
		// fitRadius's question, asked per seed.
		int bin = Math.max(MIN_RADIUS, Math.min(24, radiusFor(budget(mine, carrying))));
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
		if (keep != null) {
			long k2 = (long) MAX_RADIUS * MAX_RADIUS;
			seeds.sort(Comparator.comparingInt(l -> centroid(l).distSqr(keep) <= k2 ? 0 : 1)); // stable
		}

		Map<String, Integer> stock = new LinkedHashMap<>(carrying);
		java.util.Set<Long> taken = new java.util.HashSet<>();
		List<Cluster> out = new ArrayList<>();
		int budget = budget(mine, carrying);


		for (List<Work.Cell> seed : seeds) {
			if (out.size() >= MAX_CLUSTERS) break;
            if (seed.stream().allMatch(c -> taken.contains(c.pos().asLong()))) continue;
			BlockPos centre = centroid(seed);
			// ---- AND THIS SPOT GETS THE RADIUS THIS SPOT NEEDS. See fitRadius: the pack is the
			// ceiling, the work decides the number, and two spots in one plan may differ.
			int radius = fitRadius(mine, centre, budget);
			long r2 = (long) radius * radius;
			// gather every unclaimed cell within reach of that one standing spot
			List<Work.Cell> group = new ArrayList<>();
			for (Work.Cell c : mine) {
				if (taken.contains(c.pos().asLong())) continue;
				if (c.pos().distSqr(centre) <= r2) group.add(c);
			}
			if (group.isEmpty()) continue; // the final one or two cells are still work
			for (Work.Cell c : group) taken.add(c.pos().asLong());

			int blocked = 0, sealed = 0;
			List<Work.Cell> ready = new ArrayList<>();
			for (Work.Cell c : group) {
				long k = c.pos().asLong();
				if (blockedCells.contains(k)) blocked++;
				else if (sealedCells.contains(k)) sealed++;   // one reason each, never counted twice
				else ready.add(c);
			}
			// Allocate stock IN RANK ORDER. The second cluster is told what the first one leaves.
			Map<String, Integer> want = new LinkedHashMap<>();
			for (Work.Cell c : ready) want.merge(c.item(), 1, Integer::sum);
			int shortBy = 0;
			for (var e : want.entrySet()) {
				int have = stock.getOrDefault(e.getKey(), 0);
				int use = Math.min(have, e.getValue());
				stock.put(e.getKey(), have - use);
				shortBy += e.getValue() - use;
			}
			out.add(new Cluster(centre, group, ready, want, blocked, sealed, shortBy));
		}
		// Report by what you can actually DO there, not by how many cells happen to be nearby -
		// and DISCOUNTED BY THE TRIP, so the work under your feet is finished before the loop
		// crosses an island for a slightly larger pile.
		out.sort(Comparator.<Cluster>comparingDouble(c -> c.worth(from)).reversed()
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
		// floorDiv, not truncation: the island is at X -24200, and truncating toward zero biased
		// every centroid a block toward the origin — bins, "same spot" distances and ignore keys.
		return new BlockPos((int) Math.floorDiv(x, n), (int) Math.floorDiv(y, n), (int) Math.floorDiv(z, n));
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
	 * Choose the least-covered material during one refill trip.
	 *
	 * <p>A first-fit list fills every empty slot with its first entry. That is fine for a stone-only
	 * wall and disastrous for a build that needs stone, wood and glass before any of them can make a
	 * useful frontier. Coverage is measured against the remaining demand represented by the target,
	 * so each material gets a turn before the largest demand takes a second stack.
	 */
	static Restock nextLoadFetch(List<Restock> addressable, Map<String, Integer> carrying, Room room) {
		Restock best = null;
		for (Restock r : addressable) {
			if (room.of(r.item()) <= 0) continue;
			if (best == null || coverage(r, carrying) < coverage(best, carrying)
				|| (coverage(r, carrying) == coverage(best, carrying) && r.missing() > best.missing())) best = r;
		}
		return best;
	}

	private static double coverage(Restock r, Map<String, Integer> carrying) {
		int have = Math.max(0, carrying.getOrDefault(r.item(), 0));
		return (double) have / Math.max(1, have + r.missing());
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
		return shortfalls(want, carrying, index, from, skip);
	}

	/**
	 * What a SHOPPING LIST is still short of, biggest shortfall first, with an address.
	 *
	 * <p>The list is {@link #loadPlan}: what the pack should hold when the trip is over. Subtracting
	 * what is carried gives what is still to be fetched, and a material with nowhere to fetch it
	 * from is dropped here for the same reason {@link #fetchTargets} drops it - this is a list of
	 * places to fly to.
	 */
	static List<Restock> shortfalls(Map<String, Integer> want, Map<String, Integer> carrying,
	                                Map<String, Storage.Container> index, BlockPos from,
	                                Set<Long> skip) {
		List<Restock> out = new ArrayList<>();
		for (var e : want.entrySet()) {
			int miss = e.getValue() - carrying.getOrDefault(e.getKey(), 0);
			if (miss <= 0) continue;
			// `true`: count what is inside shulker boxes as well. This island's bulk storage IS
			// boxes in chests, and a fetch that walks past six shulkers of stone brick to reach
			// sixty-four loose ones is not a fetch. `Withdraw` takes the box; `Work.boxed` then
			// tells you to set it down, because a client mod cannot unpack it for you.
			for (Storage.Hit h : Storage.findExact(index, e.getKey(), from, true)) {
				if (skip.contains(h.container().pos().asLong())) continue;
				out.add(new Restock(e.getKey(), miss, h.container(), h.count()));
				break;                                   // nearest one that is not cooling off
			}
		}
		out.sort(Comparator.comparingInt(Restock::missing).reversed());
		return out;
	}

	/**
	 * THE SHOPPING LIST OF ONE TRIP: what the pack should hold when it comes back.
	 *
	 * <p>Jack: <i>"it stacks up with random resources vs things it logically might need based on
	 * the radius around it"</i>, and then: <i>"doesnt check inventory, area, or fill inventory
	 * based on needs at all"</i>. Two things were wrong with the load and both are answered here.
	 *
	 * <p><b>It is sized to the area, in BUILD ORDER.</b> The loop lays a design one course at a
	 * time from the bottom, so the next cells to be placed are the next courses of the area being
	 * worked - not the cells nearest in three dimensions, which are mostly courses that cannot be
	 * placed until the ones under them exist. Sorted by nearest, a pack filled with roof for a
	 * wall whose ground course still wanted stone. The frontier (placeable now) comes first
	 * whatever its distance, because it is the reason for the trip; then the area's cells lowest
	 * course first, nearest the anchor within a course; up to {@code cap} cells, which is what
	 * the pack can hold.
	 *
	 * <p><b>And it is made ONCE, at the work, and kept for the trip.</b> Recomputed every recount
	 * from wherever the player happened to be, the demand was re-sized at the CHEST to the cells
	 * nearest the chest - a different part of the design entirely - and the loop then flew back to
	 * those. The caller holds the returned map until the trip ends.
	 *
	 * @param area     the cells of the area being worked (the anchor's radius), loaded
	 * @param frontier the cells placeable right now
	 * @param anchor   the middle of the work
	 * @param cap      how many cells the pack can bring back, at a stack a slot
	 * @return item -> how many the pack should hold, in the order they will be needed
	 */
	static Map<String, Integer> loadPlan(List<Work.Cell> area, List<Work.Cell> frontier,
	                                     BlockPos anchor, int cap) {
		return loadPlan(area, frontier, anchor, cap, item -> true);
	}

	/**
	 * ...preferring materials there is somewhere to GET.
	 *
	 * <p><b>Measured off Jack's own session log, three resets in a row.</b> The area round the
	 * anchor offered six materials - froglight, chiseled stone brick, oak fence, smooth stone
	 * slab, cracked stone brick, oak plank - and the index held not one of them, so `shortfalls`
	 * came back empty, the phase was DEAD_END, and two minutes later the loop reset, re-anchored
	 * in the same place, chose the same six and did it again. Nothing was placed in five minutes.
	 * Sitting in that same index at that moment: 40,545 stone brick, 15,040 smooth basalt and
	 * 4,057 moss block, against 23,106 placeable cells - and 1,403 of those were moss. Reported
	 * as: it is not detecting things it can 100% place, e.g. moss blocks, right next to tons of
	 * placeable ones.
	 *
	 * <p>The cap on MATERIALS is what makes a trip a trip and it stays; what was missing is that
	 * six is a CHOICE, and choosing six things nobody has is choosing not to go. Obtainable
	 * materials are offered the slots first, in exactly the order they were before; the rest fill
	 * whatever is left, so a design whose index is empty produces the same list it always did and
	 * the "nothing indexed to fetch" message still gets to be true.
	 *
	 * @param obtainable is there stock somewhere for this item - carried, or in the index
	 */
	static Map<String, Integer> loadPlan(List<Work.Cell> area, List<Work.Cell> frontier,
	                                     BlockPos anchor, int cap,
	                                     java.util.function.Predicate<String> obtainable) {
		List<Work.Cell> sorted = new ArrayList<>(area);
		Comparator<Work.Cell> byCourse = Comparator.comparingInt(c -> c.pos().getY());
		if (anchor != null) byCourse = byCourse.thenComparingDouble(c -> c.pos().distSqr(anchor));
		sorted.sort(byCourse);
		Set<Long> seen = new java.util.HashSet<>();
		Map<String, Integer> out = new LinkedHashMap<>();
		int n = 0;
		int limit = Math.max(1, cap);
		// A TRIP IS A HANDFUL OF MATERIALS, NOT WHATEVER FALLS INSIDE A CELL BUDGET. Two things
		// come out of capping the MATERIALS, and the second is why the list used to change every
		// two seconds:
		//   - Jack, on the pack: "it stacks up with random resources vs things it logically might
		//     need". A cell budget of `empty slots x 64` reaches deep into an area holding forty
		//     materials, so a trip fetched forty things and finished none of them.
		//   - and the cut point of a CELL budget is UNSTABLE. The tail is ordered by distance to
		//     an anchor that drifts as cells go in, and the budget itself shrinks as the pack
		//     fills, so which materials fell either side of the line moved on every recount - a
		//     different shopping list, announced, every two seconds. See Hud.saidLoadPlan.
		// Capped at materials, the list is a decision rather than an accident, and it changes only
		// when the WORK does.
		// TWO PASSES: what there is somewhere to get, and then the rest. A material past the cap
		// is SKIPPED rather than ending the list, in both - the cells under it are still the next
		// courses of this area, and their materials are still this trip's.
		for (boolean canGet : new boolean[]{true, false}) {
			for (Work.Cell c : frontier) {
				if (obtainable.test(c.item()) != canGet) continue;
				if (!out.containsKey(c.item()) && out.size() >= MAX_MATERIALS) continue;
				if (seen.add(c.pos().asLong())) {
					out.merge(c.item(), 1, Integer::sum);
					n++;
				}
			}
			for (Work.Cell c : sorted) {
				if (n >= limit) break;
				if (obtainable.test(c.item()) != canGet) continue;
				if (!out.containsKey(c.item()) && out.size() >= MAX_MATERIALS) continue;
				if (seen.add(c.pos().asLong())) {
					out.merge(c.item(), 1, Integer::sum);
					n++;
				}
			}
		}
		// A BUCKET DOES NOT STACK. A 200-cell pool asked for 200 water buckets, which is 200 slots
		// - the whole pack, slot by slot, of a thing the loop places one cell at a time and never
		// refills. A few per trip; the rest of the pool is the next trip's.
		for (Map.Entry<String, Integer> e : out.entrySet()) {
			if (e.getKey().endsWith("_bucket") && e.getValue() > BUCKETS_PER_TRIP) e.setValue(BUCKETS_PER_TRIP);
		}
		return out;
	}

	/**
	 * Materials ranked by how many of their remaining cells can be placed against what stands
	 * TODAY - a face to click, in the world, now - not by how many the design is made of. Jack:
	 * <i>"identify most used materials, and most placeable based on no air blocks around it based
	 * on currently placed, so we can efficiently spread resources in large builds."</i> A pack of
	 * the commonest block is a pack with nothing to place against if the commonest block is the
	 * roof; a trip for the top of this list places the most.
	 */
	record Usable(String item, int placeable, int remaining) {}

	static List<Usable> usable(List<Work.Cell> todo, List<Work.Cell> placeable) {
		Map<String, Integer> left = Work.tally(todo), now = Work.tally(placeable);
		List<Usable> out = new ArrayList<>();
		for (Map.Entry<String, Integer> e : left.entrySet()) {
			out.add(new Usable(e.getKey(), now.getOrDefault(e.getKey(), 0), e.getValue()));
		}
		out.sort(Comparator.comparingInt((Usable u) -> -u.placeable()).thenComparingInt(u -> -u.remaining())
			.thenComparing(Usable::item));
		return out;
	}

	/** Buckets a shopping list may ask for at once: they take a slot each. */
	static final int BUCKETS_PER_TRIP = 4;

	/**
	 * How many DIFFERENT materials one trip may be for. See {@link #loadPlan}.
	 *
	 * <p>Six is about a working load: enough that a course of masonry with its trim and its
	 * lighting is one journey, and few enough that the list is legible, stable between recounts,
	 * and can be finished before the next one is planned.
	 */
	static final int MAX_MATERIALS = 6;

	/**
	 * A REMAINDER IS NOT A TRIP. Off Jack's log: {@code fetch: 2x white_wool from #430 Found shops
	 * (1984 there, 2 still wanted)} - a flight across the park, an approach, a chest opened and a
	 * withdrawal, for two blocks, because the list wanted sixty-six and the pack held sixty-four.
	 *
	 * <p>A trip is a load, and a load is covered when the last of it is not worth going for. What
	 * is left stays on the design and the next trip picks it up on the way past.
	 */
	static final int REMAINDER = 16;

	/**
	 * ...AND SMALL IN ABSOLUTE TERMS IS NOT ENOUGH ON ITS OWN. A list of four lanterns is four
	 * blocks missing out of four, and that IS the trip - it is the whole reason the loop is going.
	 * A remainder is a remainder relative to the load it is left over from.
	 */
	static final int REMAINDER_SHARE = 4;

	/** Is this list already in the pack, near enough? Then the trip is over, wherever you are. */
	static boolean covered(Map<String, Integer> plan, Map<String, Integer> carrying) {
		int missing = 0, total = 0;
		for (Map.Entry<String, Integer> e : plan.entrySet()) {
			total += e.getValue();
			missing += Math.max(0, e.getValue() - carrying.getOrDefault(e.getKey(), 0));
		}
		return missing == 0 || (missing <= REMAINDER && missing * REMAINDER_SHARE <= total);
	}

	/** How many cells a shopping list covers. */
	static int cells(Map<String, Integer> plan) {
		int n = 0;
		for (int v : plan.values()) n += v;
		return n;
	}

	/** The list as a sentence: "320x stone_bricks, 12x lantern". */
	static String describe(Map<String, Integer> plan) {
		StringBuilder sb = new StringBuilder();
		for (var e : plan.entrySet()) {
			if (sb.length() > 0) sb.append(", ");
			sb.append(e.getValue()).append("x ").append(e.getKey());
		}
		return sb.toString();
	}

	/**
	 * Drop the shortfalls you are already carrying, in a box.
	 *
	 * <p>A trip is a navigation instruction, and flying across the island for something on your own
	 * hip is the most annoying kind of wrong. NOT merged into `carrying` — see {@link Work#boxed}
	 * for why a boxed block is not a carried one — so it is subtracted here instead, at the point
	 * where the question is "is this trip worth making".
	 *
	 * @param say called once per material, so the loop explains rather than silently doing nothing
	 */
	static List<Restock> notInAPack(List<Restock> targets, Map<String, Integer> boxed,
	                                java.util.function.Consumer<String> say) {
		if (boxed.isEmpty()) return targets;
		List<Restock> out = new ArrayList<>();
		for (Restock r : targets) {
			if (boxed.getOrDefault(r.item(), 0) >= r.missing()) {
				say.accept(r.item());
				continue;
			}
			out.add(r);
		}
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

	// ---------------------------------------------------------------- inside a spot: STATIONS
	//
	// A SPOT IS A TRIP, NOT A PLACE TO STAND. `radiusFor` sizes a spot to one inventory load, which
	// with a shulker or two is a region 48 or 96 blocks across — and the loop then guided you to its
	// CENTROID and stopped, because arriving is not disarming. The printer reaches about four and a
	// half blocks. So it placed whatever happened to be near the middle of the region, ran out, and
	// sat there until the ninety-second stall watch gave up on a spot that was almost entirely
	// unbuilt. "It stays in a small place the entire time and never moves on" is exactly this.
	//
	// A station is where you actually stand: the cells binned at the printer's reach, and you are
	// sent to the fullest bin. There is no state to keep — as the cells get placed that bin empties
	// and the next call picks the next one, which is the same hysteresis the spot itself uses, one
	// level down.

	/**
	 * About what litematica-printer will place from where you float — the FALLBACK, when it cannot
	 * be asked.
	 *
	 * <p>Everything about where the loop stands is budgeted against this number and it was a guess.
	 * {@link #reach} asks the printer's own config instead; this is what is used when the printer is
	 * not installed, which is also when none of it matters.
	 */
	static final int PRINTER_REACH = 4;

	/**
	 * The printer's real reach, rounded down to a bin size.
	 *
	 * <p>One less than the range it claims: the range is measured from the player's EYES to the
	 * block, and a bin of that size has corners further away than its own width. Rounding down is
	 * the same conservatism the rest of this file uses about reach.
	 */
	/**
	 * The printer's real range, unfloored.
	 *
	 * <p>{@link #reach} floors it to an int because bins and keys are integers. Anything that then
	 * SUBTRACTS from it - a standoff, an arrival allowance - must not pay the flooring as well, or a
	 * 4.2-block reach is spent down to 2.8 and the only way to cover a cluster is to stand in it.
	 */
	/**
	 * How wide a station may be, so that ONE stand covers all of it.
	 *
	 * <p>The bin size was {@link #reach} - the printer's range, floored - and a bin that wide cannot
	 * be covered from a spot inside it: a square bin of side b has its far corner b*sqrt(2)/2 from
	 * the middle, and the stand only has {@code reach - ARRIVE_MIN}. At the real 4.2 a 4-wide bin is
	 * 2.83 against 3.0 and just fits; at the fallback 4 it is 2.83 against 2.8 and does not, and
	 * nothing said so - the leftover corner was simply highlighted, flown to, and stalled on.
	 *
	 * <p>So it is DERIVED. Whatever the reach turns out to be, the station is the largest square a
	 * stand can finish, and "just out of reach" stops being expressible.
	 */
	static int binSize() {
		double usable = reachExact() - Autopilot.ARRIVE_MIN;
		int b = (int) Math.floor(usable * 2 / Math.sqrt(2));
		return Math.max(2, b);
	}

	static double reachExact() {
		if (Printer.driving()) return Printer.REACH;
		double real = Litematica.printerRange();
		return real > 0 ? real : PRINTER_REACH;
	}

	static int reach() {
        if (Printer.driving()) return (int)Math.floor(Printer.REACH);
		double real = Litematica.printerRange();
		if (real <= 0) return PRINTER_REACH;
		return Math.max(2, (int) Math.floor(real) - 1);
	}

	/**
	 * Where to stand INSIDE a spot, and how many cells that covers.
	 *
	 * @param skip bin keys already tried and abandoned — see {@link #binKey}
	 */
	record Station(BlockPos where, int cells, long bin) {}

	/** Which reach-sized bin a cell belongs to. Stations are named by this, so they can be skipped. */
	static long binKey(BlockPos p, int reach) {
		return BlockPos.asLong(Math.floorDiv(p.getX(), reach), Math.floorDiv(p.getY(), reach),
			Math.floorDiv(p.getZ(), reach));
	}

	/**
	 * The fullest bin of cells you are not already carrying past, nearest on a tie.
	 *
	 * <p>Fullest rather than nearest, because the walk between two bins inside one spot is nothing
	 * and the number of blocks you place when you get there is everything. Nearest only breaks ties,
	 * which is what stops it crossing the region for a bin one cell bigger.
	 */
	static Station station(List<Work.Cell> cells, int reach, BlockPos from, Set<Long> skip) {
		Map<Long, List<Work.Cell>> bins = new LinkedHashMap<>();
		for (Work.Cell c : cells) {
			long k = binKey(c.pos(), reach);
			if (skip.contains(k)) continue;
			bins.computeIfAbsent(k, x -> new ArrayList<>()).add(c);
		}
		Station best = null;
		for (var e : bins.entrySet()) {
			BlockPos centre = centroid(e.getValue());
			if (best == null || e.getValue().size() > best.cells()
				|| (e.getValue().size() == best.cells()
					&& centre.distSqr(from) < best.where().distSqr(from))) {
				best = new Station(centre, e.getValue().size(), e.getKey());
			}
		}
		return best;
	}

	/**
	 * Where to float so the printer can reach the MOST of these cells.
	 *
	 * <p>The standing spot used to be chosen by proximity to a centroid, and then the flight stopped
	 * somewhere short of it — so the number that decided everything was a distance to a point nobody
	 * cared about. What matters is COVERAGE: how many of the cells left here can actually be touched
	 * from where the body ends up.
	 *
	 * <p>So every open cell near the work is scored by the count it covers, at a radius discounted
	 * for the fact that the flight parks a little short of the spot it was sent to. Ties go to the
	 * one nearest the player, because two spots that build the same wall are the same spot.
	 *
	 * <p>Clearance is a FILTER rather than part of the score: a spot that touches something is not a
	 * worse spot, it is not a spot — on this server it ends the flight. Only if nothing at all
	 * clears does it fall back to the roomiest thing available.
	 *
	 * @param slack how far short of the chosen spot the flight is expected to stop
	 */
	/**
	 * A RING of standing spots around the work, ordered so that walking it circles the cells.
	 *
	 * <p><b>A hovering body is the one that loses flight.</b> {@link #bestStand} answers "where is
	 * the single best place to float", and the loop then held that place while the printer worked -
	 * so the flight spent every build parked a block or two off a wall, holding station against
	 * drift, for as long as the bin took. Jack: <i>"it also flies and hovers when realistically it
	 * can just keep circling areas and going"</i>. He is right twice over: standing still is where
	 * the contact happens, and one vantage only ever reaches the faces that vantage can see.
	 *
	 * <p>So the spot is not a POINT, it is an ORBIT. Every cell that passes the same clearance rules
	 * {@link #bestStand} applies is a candidate; they are bucketed into eight bearings around the
	 * cluster and the best-covering one from each is kept. Flying that ring keeps the printer inside
	 * its own reach the whole way round, presents a different face of the work every leg, and never
	 * asks the body to hold a position.
	 *
	 * <p>Only stops that carry real work are kept: a bearing from which the printer can reach barely
	 * anything is a detour, not a vantage. Returns an empty list when the geometry gives no ring at
	 * all - a cell in a slot, a bin against a ceiling - and the caller falls back to standing still,
	 * which is worse and is still better than not building.
	 */
	static final int ARCS = 8;

	static List<BlockPos> ring(Nav.Passable free, List<Work.Cell> cells, double reach, int maxOut) {
		return ring(free, cells, reach, maxOut, null);
	}

	static List<BlockPos> ring(Nav.Passable free, List<Work.Cell> cells, double reach, int maxOut,
	                           Reach canTouch) {
		List<BlockPos> out = new ArrayList<>();
		if (cells.isEmpty()) return out;
		BlockPos mid = centroid(cells);
		double r = Math.max(1.0, reach - 1.2);
		BlockPos[] bestAt = new BlockPos[ARCS];
		int[] bestCover = new int[ARCS];
		int mostAnywhere = 0;
		for (int dx = -maxOut; dx <= maxOut; dx++) {
			for (int dy = -maxOut; dy <= maxOut; dy++) {
				for (int dz = -maxOut; dz <= maxOut; dz++) {
					if (dx == 0 && dz == 0) continue;      // no bearing: that is the centre, not a stop
					BlockPos c = mid.offset(dx, dy, dz);
					if (!free.at(c.getX(), c.getY(), c.getZ())) continue;
					if (!Nav.airBelow(free, c, Nav.AIR_BELOW)) continue;
					if (!Nav.headroom(free, c, Nav.AIR_ABOVE)) continue;
					// THE SAME MEASURE AS bestStand. This was a third one - feet to the cell's centre,
					// no sight line and no reach - so an orbit stop could score well on cells the
					// printer could not touch from it, and "the next angle on this spot" was a tour of
					// vantages that all placed nothing.
					int covered = coveredFrom(cells, c, r, free, canTouch);
					if (covered == 0) continue;
					mostAnywhere = Math.max(mostAnywhere, covered);
					int arc = arcOf(dx, dz);
					if (covered > bestCover[arc]) {
						bestCover[arc] = covered;
						bestAt[arc] = c;
					}
				}
			}
		}
		// A vantage worth flying to has to be able to work from. Half of the best is generous - the
		// point is to keep moving, not to insist every leg is the best leg.
		int floor = Math.max(1, mostAnywhere / 2);
		for (int a = 0; a < ARCS; a++) {
			if (bestAt[a] != null && bestCover[a] >= floor) out.add(bestAt[a]);
		}
		return out;
	}

	/** Which of the eight bearings round the cluster a horizontal offset falls in. */
	static int arcOf(int dx, int dz) {
		double a = Math.atan2(dz, dx);                     // -PI..PI
		int k = (int) Math.floor((a + Math.PI) / (2 * Math.PI) * ARCS);
		return Math.max(0, Math.min(ARCS - 1, k));
	}

	static BlockPos bestStand(Nav.Passable free, List<Work.Cell> cells, double reach, BlockPos from,
	                          int maxOut, double slack) {
		return bestStand(free, cells, reach, from, maxOut, slack, null);
	}

	static BlockPos bestStand(Nav.Passable free, List<Work.Cell> cells, double reach, BlockPos from,
	                          int maxOut, double slack, Reach canTouch) {
		if (cells.isEmpty()) return null;
		BlockPos mid = centroid(cells);
		// ---- SCORE AT THE REACH WE ACTUALLY HAVE.
		//
		// `reach` used to arrive here already FLOORED to an int, and the slack was then taken off
		// that - so a 4.2-block reach was being scored as 2.8. A radius of 2.8 round a cluster is
		// maximised by standing IN it, which is what the flight then did: it threaded its way into
		// the middle of the work, spent the whole approach at low speed between the very blocks it
		// had come to place, and touched one. Jack: "we have a 4-5 block reach so we dont need to be
		// on top".
		double r = Math.max(1.0, reach - slack);
		double r2 = r * r;
		BlockPos best = null;
		int bestCovered = -1;
		double bestStandBack = -1.0;
		double bestNear = Double.MAX_VALUE;
		for (int dx = -maxOut; dx <= maxOut; dx++) {
			for (int dy = -maxOut; dy <= maxOut; dy++) {
				for (int dz = -maxOut; dz <= maxOut; dz++) {
					BlockPos c = mid.offset(dx, dy, dz);
					if (!free.at(c.getX(), c.getY(), c.getZ())) continue;
					if (!Nav.airBelow(free, c, Nav.AIR_BELOW)) continue;
					if (!Nav.headroom(free, c, Nav.AIR_ABOVE)) continue;
					// FROM THE EYES, not the feet cell: the printer's ray leaves from the eyes, and
					// a cell four courses below the feet is a block and a half further from them.
					int covered = coveredFrom(cells, c, r, free, canTouch);
					double nearestCell = Double.MAX_VALUE;
					for (Work.Cell w : cells) nearestCell = Math.min(nearestCell, eyeDistSqr(c, w.pos()));
					if (covered == 0) continue;
					double near = c.distSqr(from);
					// ---- COVERAGE FIRST, THEN STAND BACK.
					//
					// Two spots that place the same blocks are the same spot to the printer and are
					// not the same spot to the FLIGHT: one of them is a block off a wall it is about
					// to build, and on this server touching that wall ends the session. So among
					// equal coverage, take the one furthest from the nearest cell - the reach is
					// already paid for, and the air is free.
					boolean better = covered > bestCovered
						|| (covered == bestCovered && nearestCell > bestStandBack + 1.0e-9)
						|| (covered == bestCovered && Math.abs(nearestCell - bestStandBack) <= 1.0e-9
							&& near < bestNear);
					if (better) {
						bestCovered = covered;
						bestStandBack = nearestCell;
						bestNear = near;
						best = c;
					}
				}
			}
		}
		return best;
	}

	/**
	 * The station for one particular bin, or null if nothing is left in it.
	 *
	 * <p>{@link #station} answers "where is the best work"; this answers "what about the bin I am
	 * already standing at", which is what a dwell needs — otherwise staying put means re-deciding
	 * every two seconds that staying put is still best, and the moment another bin looks fuller the
	 * loop leaves mid-wall.
	 */
	/** Where the eyes are above the feet cell's floor. */
	static final double EYE = 1.62;
	/** Solid cells wanted in the 3x3 under a landing: a one-block ledge over the void is not a floor. */
	static final int PAD_MIN = 6;

	/**
	 * A place to LAND and work from, or null if the work has no floor beside it.
	 *
	 * <p>Jack: <i>"it is hovering above a group thats not placeable; i think we need to also analyze
	 * area and identify when it can land"</i>. A flying stand needs three clear cells under it
	 * ({@link Nav#AIR_BELOW}) and the flight holds two and a half off any floor — both right for
	 * work on a wall, and both impossible for work ON A FLOOR: paving, a lawn, the bottom course of
	 * anything. Over a plate no cell qualifies, the fallback is the centroid, the flight parks three
	 * blocks over it, and the printer reaches nothing. That is the hover.
	 *
	 * <p>So: a cell the body fits in, with a real floor under it (a 3x3 pad, not a ledge), that is not
	 * itself work still to be placed, from which the eyes are within reach of the most cells. The
	 * loop lands there, builds standing, and takes off again when the next station needs it.
	 */
	static BlockPos groundStand(Nav.Passable free, java.util.function.Predicate<BlockPos> solid,
	                            List<Work.Cell> cells, double reach, BlockPos from, int maxOut) {
		return groundStand(free, solid, cells, reach, from, maxOut, null);
	}

	static BlockPos groundStand(Nav.Passable free, java.util.function.Predicate<BlockPos> solid,
	                            List<Work.Cell> cells, double reach, BlockPos from, int maxOut,
	                            Reach canTouch) {
		if (cells.isEmpty()) return null;
		Set<Long> work = new java.util.HashSet<>();
		for (Work.Cell c : cells) work.add(c.pos().asLong());
		BlockPos mid = centroid(cells);
		BlockPos best = null;
		int bestCovered = 0;
		double bestNear = Double.MAX_VALUE;
		for (int dx = -maxOut; dx <= maxOut; dx++) {
			for (int dz = -maxOut; dz <= maxOut; dz++) {
				for (int dy = -4; dy <= 4; dy++) {
					BlockPos c = mid.offset(dx, dy, dz);
					if (!free.at(c.getX(), c.getY(), c.getZ())) continue;
					if (work.contains(c.asLong()) || work.contains(c.above().asLong())) continue;
					BlockPos floor = c.below();
					if (!solid.test(floor)) continue;
					int pad = 0;
					for (int ex = -1; ex <= 1; ex++)
						for (int ez = -1; ez <= 1; ez++)
							if (solid.test(floor.offset(ex, 0, ez))) pad++;
					if (pad < PAD_MIN) continue;
					int covered = coveredFrom(cells, c, reach, free, canTouch);
					if (covered == 0) continue;
					double near = c.distSqr(from);
					if (covered > bestCovered || (covered == bestCovered && near < bestNear)) {
						bestCovered = covered;
						bestNear = near;
						best = c;
					}
				}
			}
		}
		return best;
	}

	/** How many of these cells the printer can touch from a body standing (feet) in {@code stand}. */
	static int coveredFrom(List<Work.Cell> cells, BlockPos stand, double reach) {
		return coveredFrom(cells, stand, reach, null);
	}

	/**
	 * ...and, given the world, only the ones the eyes can SEE. Reach alone let a stand UNDER a
	 * plate count the paving on top of it — a block and a half from the eyes, through a floor.
	 */
	static int coveredFrom(List<Work.Cell> cells, BlockPos stand, double reach, Nav.Passable free) {
		return coveredFrom(cells, stand, reach, free, null);
	}

	/**
	 * Can the printer TOUCH this cell from a body whose feet are in {@code stand}?
	 *
	 * <p>Supplied by the caller because only it has a world. Everything here measured to the cell's
	 * CENTRE, and the printer clicks the SUPPORT's face - so a stand could score full marks on a
	 * group it then could not place, and "moving in closer" moved to another such stand. See
	 * {@link Printer#clickPoint}.
	 */
	interface Reach { boolean touches(BlockPos stand, Work.Cell cell); }

	static int coveredFrom(List<Work.Cell> cells, BlockPos stand, double reach, Nav.Passable free,
	                       Reach canTouch) {
		double r2 = reach * reach;
		int n = 0;
		for (Work.Cell w : cells) {
			if (eyeDistSqr(stand, w.pos()) > r2) continue;
			if (free != null && !Nav.sees(free, stand, w.pos())) continue;
			if (canTouch != null && !canTouch.touches(stand, w)) continue;
			n++;
		}
		return n;
	}

	/** Squared distance from the eyes of a body standing in {@code stand} to the centre of {@code cell}. */
	static double eyeDistSqr(BlockPos stand, BlockPos cell) {
		double dx = cell.getX() + 0.5 - (stand.getX() + 0.5), dy = cell.getY() + 0.5 - (stand.getY() + EYE),
			dz = cell.getZ() + 0.5 - (stand.getZ() + 0.5);
		return dx * dx + dy * dy + dz * dz;
	}

	static Station stationOf(List<Work.Cell> cells, long bin, int reach) {
		List<Work.Cell> mine = new ArrayList<>();
		for (Work.Cell c : cells) {
			if (binKey(c.pos(), reach) == bin) mine.add(c);
		}
		return mine.isEmpty() ? null : new Station(centroid(mine), mine.size(), bin);
	}

	/** The cells one station covers, for the highlight and for knowing when it is finished. */
	static List<Work.Cell> atStation(List<Work.Cell> cells, Station st, int reach) {
		List<Work.Cell> out = new ArrayList<>();
		for (Work.Cell c : cells) if (binKey(c.pos(), reach) == st.bin()) out.add(c);
		return out;
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
