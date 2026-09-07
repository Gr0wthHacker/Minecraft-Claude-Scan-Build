package dev.jack.chunkscan;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * What this mod costs the client thread, per subsystem.
 *
 * <p><b>WRITTEN BECAUSE A FRAME-RATE COMPLAINT WAS ANSWERED BY READING THE CODE THREE TIMES.</b>
 * Jack: <i>"its scanning too fast, you start autofly and its supremely laggy, basically no frames
 * per second."</i> Every subsystem here looked affordable in isolation and the arithmetic between
 * them was what hurt - the design recount sorted a hundred thousand cells with a comparator that
 * parsed a string and allocated a map on both sides of every comparison. Nothing about the call
 * site said so, and no amount of re-reading was going to.
 *
 * <p>This is the same argument `mcbuild.printable` makes offline: a fault nobody can measure is a
 * fault somebody argues about. `/cscan perf` answers it in one command.
 *
 * <p><b>IT MUST BE CHEAPER THAN WHAT IT MEASURES.</b> One `nanoTime` pair and one array write per
 * section per tick - no allocation, no map lookup on the hot path, and a fixed ring per section, so
 * a profiler left on for an overnight run cannot grow. `nanoTime` is not free, which is why the
 * sections are whole subsystems rather than inner loops: about a dozen calls a tick, against the
 * hundreds of thousands of world lookups they are measuring.
 */
final class Perf {

	/** Ticks kept per section: about ten seconds at twenty ticks a second. */
	static final int WINDOW = 200;

	private static final Map<String, long[]> RING = new LinkedHashMap<>();
	private static final Map<String, Integer> AT = new LinkedHashMap<>();
	private static final Map<String, long[]> WORST = new LinkedHashMap<>();
	/** Total nanos and calls since the last reset, per section: the LOAD, as against the spike. */
	private static final Map<String, long[]> TOTAL = new LinkedHashMap<>();
	private static long ticks = 0;
	private static boolean on = true;

	/**
	 * One client tick has passed.
	 *
	 * <p><b>A MEAN PER CALL AND A SHARE OF A TICK ARE DIFFERENT NUMBERS, and the report used to
	 * print one and label it the other.</b> The ring holds the last {@link #WINDOW} CALLS, so for
	 * `autofly` - called every tick - the mean is per tick and the label was right; for `recount` -
	 * called every fortieth - it is per call, and summing those into "692% of a 50ms tick" said the
	 * mod was using seven client threads. It was not: it was one 262 ms freeze twice a second,
	 * which is a much more specific complaint and the one Jack could feel.
	 */
	static void tick() {
		if (on) ticks++;
	}

	private Perf() {}

	static void enabled(boolean v) {
		on = v;
		if (!v) reset();
	}

	static boolean enabled() {
		return on;
	}

	static void reset() {
		RING.clear();
		AT.clear();
		WORST.clear();
		TOTAL.clear();
		ticks = 0;
	}

	/**
	 * Time a section. Returns whatever the body returns.
	 *
	 * <p>The body's own exception is NEVER swallowed here - a profiler that changed which errors
	 * reach a caller would be a profiler that changes behaviour, and every tick in this mod already
	 * has its own guard for exactly that reason.
	 */
	static <T> T time(String section, java.util.function.Supplier<T> body) {
		if (!on) return body.get();
		long t0 = System.nanoTime();
		try {
			return body.get();
		} finally {
			record(section, System.nanoTime() - t0);
		}
	}

	static void run(String section, Runnable body) {
		time(section, () -> {
			body.run();
			return null;
		});
	}

	static void record(String section, long nanos) {
		if (!on) return;
		long[] ring = RING.computeIfAbsent(section, k -> new long[WINDOW]);
		int at = AT.getOrDefault(section, 0);
		ring[at] = nanos;
		AT.put(section, (at + 1) % WINDOW);
		long[] worst = WORST.computeIfAbsent(section, k -> new long[]{0});
		if (nanos > worst[0]) worst[0] = nanos;
		long[] tot = TOTAL.computeIfAbsent(section, k -> new long[2]);
		tot[0] += nanos;
		tot[1]++;
	}

	/**
	 * The report, worst mean first.
	 *
	 * <p>MEAN AND WORST, never one of them. A recount that costs two seconds every fortieth tick has
	 * a mean of fifty milliseconds and is the thing you can feel; a mean alone hides it in the
	 * ticks that did nothing, and a worst alone cannot tell a one-off chunk load from a permanent
	 * cost. The share of a 50ms tick budget is printed because that is the number that decides
	 * whether the client keeps up.
	 */
	static List<String> report() {
		if (!on) return List.of("perf is OFF — /cscan perf on");
		if (RING.isEmpty()) return List.of("perf: nothing measured yet");
		List<String> out = new ArrayList<>();
		List<String> names = new ArrayList<>(RING.keySet());
		names.sort((a, b) -> Double.compare(load(b), load(a)));
		double load = 0;
		for (String n : names) load += load(n);
		out.add(String.format("perf over %d ticks — %.1f%% of the client thread (%.2f ms per tick)",
			ticks, load, load * 0.5));
		for (String n : names) {
			if (load(n) < 0.05 && WORST.get(n)[0] < 2_000_000L) continue;   // idle and never spiked
			long[] t = TOTAL.getOrDefault(n, new long[2]);
			// PER CALL, and then what it costs OVERALL - because a quarter-second freeze twice a
			// second and a millisecond every tick are the same load and completely different to
			// play with. The freeze is the one you feel; the share is the one that runs you out of
			// frame budget.
			out.add(String.format("  %-14s %7.1f ms/call  worst %7.1f  %5.1f%% of thread  (%d calls)",
				n, t[1] == 0 ? 0 : t[0] / 1_000_000.0 / t[1], WORST.get(n)[0] / 1_000_000.0,
				load(n), t[1]));
		}
		return out;
	}

	/** What this section costs the client thread, as a percentage: total time over time elapsed. */
	private static double load(String section) {
		long[] t = TOTAL.get(section);
		if (t == null || ticks == 0) return 0;
		return 100.0 * (t[0] / 1_000_000.0) / (ticks * 50.0);
	}

	private static double mean(String section) {
		long[] ring = RING.get(section);
		if (ring == null) return 0;
		long sum = 0;
		for (long v : ring) sum += v;
		return sum / (double) WINDOW / 1_000_000.0;
	}
}
