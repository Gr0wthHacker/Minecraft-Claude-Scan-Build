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
 */
final class Ignored {
	/** How big a "place" is. See the note above about drifting centroids. */
	static final int AREA = 8;
	/** Failures before a place is written off. */
	static final int STRIKES = 2;

	private static final Map<Long, Integer> strikes = new LinkedHashMap<>();

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
		int n = strikes.merge(k, 1, Integer::sum);
		return n == STRIKES;
	}

	/** Is this place written off? */
	static boolean has(BlockPos at) {
		return strikes.getOrDefault(key(at), 0) >= STRIKES;
	}

	/** How many failures this place has, for the report. */
	static int strikesAt(BlockPos at) {
		return strikes.getOrDefault(key(at), 0);
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

	static void clear() {
		strikes.clear();
	}
}
