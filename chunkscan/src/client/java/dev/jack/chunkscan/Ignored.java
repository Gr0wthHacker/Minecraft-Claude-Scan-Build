package dev.jack.chunkscan;

import net.minecraft.core.BlockPos;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Places that have failed twice, and are not to be tried again.
 *
 * <p>Jack: <i>"it shouldnt spam no route and no way around, if it does it twice, just find a new
 * location, it should notice if an area gets flagged twice it gets flagged as an ignore (red)."</i>
 *
 * <p>Every watchdog in this loop is a TIMER, and a timer forgets. The spot avoid expires after a
 * minute, the station retry clears when every bin has been tried, the cooling-off on a chest lapses —
 * all correct, because a world that changes deserves a second look. But a place that has beaten the
 * router twice is not going to be different in a minute, and the loop returning to it for ever is
 * both the infinite loop and the message spam: they are the same fault seen from two angles.
 *
 * <p><b>Two strikes, then never.</b> One failure is a bad moment — a chunk that had not arrived, a
 * block the printer had just placed, a route computed from the wrong side of a wall. Two is a
 * property of the place.
 *
 * <p>Held by AREA rather than by cell, because "the same place" is not the same coordinate: the loop
 * picks a centroid that drifts as cells are placed, so a per-cell list would never see the same
 * failure twice. {@link #AREA} is eight blocks, which is about the size of a spot the flight can
 * fail to reach for one reason.
 *
 * <p>Session-scoped on purpose, and NOT written to disk. Breaking one block can change the answer,
 * and a permanent file would quietly shrink the buildable island over weeks with nothing to say why.
 * `/cscan ignore clear` is the deliberate version, and a relog is the accidental one.
 *
 * <p><b>A relog really does clear it now.</b> That sentence sat in this docstring before it was
 * true: nothing was registered on DISCONNECT, so the list survived a reconnect and carried its
 * coordinates into whatever world came next. `Wand` already states the rule these keys live under —
 * <i>coordinates mean nothing without a world</i> — and a strike list is nothing but coordinates.
 */
final class Ignored {
	/** How big a "place" is. See the note above about drifting centroids. */
	static final int AREA = 8;
	/** Failures before a place is written off. */
	static final int STRIKES = 2;
	/**
	 * How long a write-off lasts.
	 *
	 * <p><b>IT HAD NO EXPIRY AT ALL, and the two strikes that spend it are not always about the
	 * place.</b> A search that runs out of its millisecond budget returns the same empty list as a
	 * search that proved there is no way through, and three unrelated give-up paths all strike the
	 * same key - so two slow ticks could delete an eight-block cube of the park for the rest of
	 * the session, with the only symptom being work that never gets done.
	 *
	 * <p>Ten minutes is long enough that a genuinely unreachable place is not retried every two
	 * seconds, and short enough that a place written off by accident comes back inside one
	 * session. It is the same reasoning as the chest cooling-off: a timer forgets, which is wrong
	 * for a property of a place and right for a judgement made from one bad moment.
	 */
	static final long FORGET_MS = 10 * 60_000L;

	private static final Map<Long, Integer> strikes = new LinkedHashMap<>();
	/** When each place was last struck, so a write-off can expire. */
	private static final Map<Long, Long> struckAt = new LinkedHashMap<>();

	private Ignored() {}

	static long key(BlockPos at) {
		return BlockPos.asLong(Math.floorDiv(at.getX(), AREA), Math.floorDiv(at.getY(), AREA),
			Math.floorDiv(at.getZ(), AREA));
	}

	/**
	 * Record a failure here.
	 *
	 * @return true if this was the strike that wrote the place off
	 */
	static boolean strike(BlockPos at) {
		long k = key(at);
		expire(k);
		struckAt.put(k, System.currentTimeMillis());
		int n = strikes.merge(k, 1, Integer::sum);
		return n == STRIKES;
	}

	/** Is this place written off? */
	static boolean has(BlockPos at) {
		long k = key(at);
		expire(k);
		return strikes.getOrDefault(k, 0) >= STRIKES;
	}

	/** How many failures this place has, for the report. */
	static int strikesAt(BlockPos at) {
		long k = key(at);
		expire(k);
		return strikes.getOrDefault(k, 0);
	}

	/** Drop a write-off older than {@link #FORGET_MS}. Lazy, so it costs nothing while nothing asks. */
	private static void expire(long k) {
		Long when = struckAt.get(k);
		if (when != null && System.currentTimeMillis() - when > FORGET_MS) {
			strikes.remove(k);
			struckAt.remove(k);
		}
	}

    /** One block in each ignored area, to draw. */
	static List<BlockPos> marks() {
		List<BlockPos> out = new ArrayList<>();
		for (var e : strikes.entrySet()) {
			if (e.getValue() < STRIKES) continue;
			BlockPos k = BlockPos.of(e.getKey());
			out.add(new BlockPos(k.getX() * AREA + AREA / 2, k.getY() * AREA + AREA / 2,
				k.getZ() * AREA + AREA / 2));
		}
		return out;
	}

	static int count() {
		int n = 0;
		for (int v : strikes.values()) if (v >= STRIKES) n++;
		return n;
	}

	/** Clear on DISCONNECT: these are coordinates, and coordinates mean nothing without a world. */
	static void register() {
		net.fabricmc.fabric.api.client.networking.v1.ClientPlayConnectionEvents.DISCONNECT.register(
			(handler, client) -> clear());
	}

	static void clear() {
		strikes.clear();
		struckAt.clear();
	}
}
