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
		// Only cells whose material is on you. Everything else is `need`'s problem, not this one.
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

	/** Four stacks per material before the load planner rotates to another needed material. */
	static int takeLoadAmount(Restock r, int materialKinds, int room) {
		int ordinary = takeHowMany(r, room);
		if (materialKinds <= 1) return ordinary;
		return Math.min(ordinary, 4 * 64);
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
		List<BlockPos> out = new ArrayList<>();
		if (cells.isEmpty()) return out;
		BlockPos mid = centroid(cells);
		double r = Math.max(1.0, reach - 1.2);
		double r2 = r * r;
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
					int covered = 0;
					for (Work.Cell w : cells) if (w.pos().distSqr(c) <= r2) covered++;
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
					int covered = 0;
					double nearestCell = Double.MAX_VALUE;
					for (Work.Cell w : cells) {
						double d2 = w.pos().distSqr(c);
						if (d2 <= r2) covered++;
						nearestCell = Math.min(nearestCell, d2);
					}
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
