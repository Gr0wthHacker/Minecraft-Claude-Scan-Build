package dev.jack.chunkscan;

import net.minecraft.core.BlockPos;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Consolidation: one item, one home, and the list of chests to empty into it.
 *
 * <p>Measured off the real index — 96 containers holding 244 distinct items, and <b>206 of those
 * 244 live in more than one container</b>. White wool is 12,729 spread over 27 chests and would fit
 * in eight; cobblestone is 11,830 over 26. Thirty-seven items have eight or fewer in total and are
 * still split across two or more.
 *
 * <p>The tedious part of fixing that is not the shift-clicking, it is knowing WHICH twenty-seven
 * chests and in what order. That is what this computes; {@link Hud} and {@link Autopilot} then walk
 * you round them.
 *
 * <p><b>It plans and points. It does not move items</b> — that would need slot manipulation, which
 * is a separate piece of work.
 */
final class Tidy {
	/** Below this an item is not worth a trip: two chests holding four sticks is not a problem. */
	static final int MIN_TOTAL = 32;
	/** One container is already tidy; two is usually where you left a stack behind. */
	static final int MIN_SOURCES = 2;

	/**
	 * One item's consolidation.
	 *
	 * @param home    where it should all end up: whichever container already holds the most, so the
	 *                plan moves the FEWEST stacks rather than the most convenient ones
	 * @param sources everywhere else it lives, nearest first
	 */
	record Job(String item, Storage.Container home, int inHome,
	           List<Storage.Container> sources, int total, int slotsFreed) {
		int toMove() {
			return total - inHome;
		}
	}

	private Tidy() {}

	/**
	 * What is worth consolidating, biggest win first.
	 *
	 * <p>Ranked by SLOTS FREED rather than by item count. Twelve thousand wool in 27 chests and
	 * twelve thousand in two are the same pile; only the first is a mess, and slots freed is what
	 * measures the difference.
	 */
	static List<Job> plan(Map<String, Storage.Container> index, BlockPos from) {
		Map<String, List<Storage.Container>> holders = new LinkedHashMap<>();
		Map<String, Map<String, Integer>> counts = new LinkedHashMap<>();
		for (Storage.Container c : index.values()) {
			if (!Storage.stores(c.block)) continue;
			for (var e : c.items.entrySet()) {
				String item = Rules.shortName(e.getKey());
				holders.computeIfAbsent(item, k -> new ArrayList<>()).add(c);
				counts.computeIfAbsent(item, k -> new LinkedHashMap<>()).put(c.key(), e.getValue());
			}
		}

		List<Job> out = new ArrayList<>();
		for (var e : holders.entrySet()) {
			List<Storage.Container> all = e.getValue();
			if (all.size() < MIN_SOURCES) continue;
			Map<String, Integer> per = counts.get(e.getKey());
			int total = per.values().stream().mapToInt(Integer::intValue).sum();
			if (total < MIN_TOTAL) continue;

			// The home is wherever most of it already is: moving 200 into a chest holding 12,000
			// beats moving 12,000 into a chest holding 200.
			Storage.Container home = all.stream()
				.max(Comparator.comparingInt(c -> per.getOrDefault(c.key(), 0)))
				.orElse(all.get(0));
			int inHome = per.getOrDefault(home.key(), 0);

			List<Storage.Container> sources = new ArrayList<>();
			for (Storage.Container c : all) if (c != home) sources.add(c);
			sources.sort(Comparator.comparingDouble(c -> c.pos().distSqr(from)));

			// Slots the pile currently occupies, against the slots it needs once it is one pile.
			int now = 0;
			for (int n : per.values()) now += (n + 63) / 64;
			int after = (total + 63) / 64;
			out.add(new Job(e.getKey(), home, inHome, sources, total, Math.max(0, now - after)));
		}
		out.sort(Comparator.<Job>comparingInt(Job::slotsFreed).reversed()
			.thenComparingInt(j -> -j.sources().size()));
		return out;
	}

	/** Containers that would be emptied completely, and so become free to remove or reuse. */
	static int containersFreed(List<Job> jobs, Map<String, Storage.Container> index) {
		Map<String, Integer> kindsLeft = new LinkedHashMap<>();
		for (Storage.Container c : index.values()) {
			if (Storage.stores(c.block)) kindsLeft.put(c.key(), c.items.size());
		}
		for (Job j : jobs) {
			for (Storage.Container c : j.sources()) {
				kindsLeft.computeIfPresent(c.key(), (k, v) -> v - 1);
			}
		}
		int n = 0;
		for (int v : kindsLeft.values()) if (v <= 0) n++;
		return n;
	}

	/** One line for chat. */
	static String describe(Job j, BlockPos from) {
		return j.total() + "x " + j.item() + " in " + (j.sources().size() + 1) + " containers"
			+ " — " + j.toMove() + " to move into " + j.home().describe()
			+ " (" + (int) Math.sqrt(j.home().pos().distSqr(from)) + "m "
			+ Storage.direction(from, j.home().pos()) + Hud.climb(from, j.home().pos()) + ")"
			+ ", frees " + j.slotsFreed() + " slot(s)";
	}
}
