package dev.jack.chunkscan;

import net.minecraft.core.BlockPos;

import java.util.List;

/**
 * The build loop's decisions, with the world taken out of them.
 *
 * <p><b>Every bug in the unattended loop has lived in these four judgements</b>, and none of them
 * could be tested, because they were written inline in a method that needs a live client, a level, a
 * player and a schematics folder. The list, in the order they were shipped:
 *
 * <ul>
 *   <li>fetching whenever a spot was short of anything, so the loop went shopping with a full pack
 *       and hundreds of placeable cells — a session of commuting;</li>
 *   <li>a spot stall that cleared the arrow but not the spot, so the hysteresis chose the same
 *       region straight back and stalled again for as long as you left it;</li>
 *   <li>a station re-offered after every bin had been tried, keeping the clock that had just
 *       abandoned it, so it stalled again on the very next recount;</li>
 *   <li>an empty todo list reported as "complete" when most of the design was in chunks the client
 *       did not have, which ended a `follow all` run in about a second.</li>
 * </ul>
 *
 * <p>None of those is a hard problem. All of them are invisible in a method that also opens chests,
 * draws particles and flies a player. So the judgements live here as pure functions over plain
 * values, {@link Hud} does what they say, and {@code LoopTest} can ask them the awkward questions
 * directly.
 */
final class Loop {
	private Loop() {}

	// ---------------------------------------------------------------- phase

	/** What the loop should be doing at all. */
	enum Phase {
		/** Nothing left to place and nothing hidden: this design is done. */
		COMPLETE,
		/** Nothing left IN SIGHT, but cells in chunks we do not have. Go and look at them. */
		LOOK,
		/** Go and get materials. */
		FETCH,
		/** Go and place blocks. */
		BUILD,
		/** Nothing placeable and nothing indexed to fetch. */
		DEAD_END,
		/** Nothing placeable, something to fetch, and nowhere in the pack to put it. */
		PACK_FULL,
	}

	/**
	 * FILL THE PACK, THEN BUILD UNTIL IT IS DRY.
	 *
	 * <p>The order of the two questions is the whole policy: <i>can I place anything with what I am
	 * holding?</i> comes first, and only when the answer is no does a trip start. Once started it
	 * runs until the pack is full or the design is covered, which is what `fetching` carries between
	 * calls — without it the loop flip-flops at the boundary, fetching one stack and flying back.
	 *
	 * @param unseen      cells in chunks the client does not have. Absent is not finished.
	 * @param canWork     is there a spot with something placeable right now
	 * @param fetching    were we already on a fetch trip
	 * @param haveTarget  a shortfall with a container behind it AND room in the pack for it
	 * @param anyShortfall a shortfall exists at all, addressable or not
	 */
	static Phase phase(int todo, int unseen, boolean canWork, boolean fetching, boolean haveTarget,
	                   boolean anyShortfall) {
		if (todo == 0) return unseen > 0 ? Phase.LOOK : Phase.COMPLETE;
		if (fetching || !canWork) {
			if (haveTarget) return Phase.FETCH;
			if (!canWork) return anyShortfall ? Phase.PACK_FULL : Phase.DEAD_END;
		}
		return Phase.BUILD;
	}

	// ---------------------------------------------------------------- the spot

	/**
	 * Keep working the same region while it still has anything doable.
	 *
	 * <p>Matched by PROXIMITY rather than by equality: a cluster's centre is the centroid of the
	 * cells still to do, so it drifts a block or two every time some go in. Comparing exactly called
	 * every recount a new spot — resetting the stations and re-announcing, twice a second.
	 *
	 * @return the cluster to keep working, or null to pick the best one afresh
	 */
	static Plan.Cluster sameSpot(BlockPos current, List<Plan.Cluster> clusters, int maxRadius) {
		if (current == null) return null;
		Plan.Cluster best = null;
		double bestD = Double.MAX_VALUE;
		for (Plan.Cluster c : clusters) {
			double d = c.centre().distSqr(current);
			if (c.doable() > 0 && d < bestD && d <= (double) maxRadius * maxRadius) {
				bestD = d;
				best = c;
			}
		}
		return best;
	}

	// ---------------------------------------------------------------- the station clock

	/** What to do about the place you are standing. */
	enum Station {
		/** Blocks are going in. Leave the arrow alone. */
		WORKING,
		/** Some went in: re-aim at what is LEFT, which walks you round the group. */
		RECENTRE,
		/** Nothing went in. Move in as close as the geometry allows and give it another go. */
		CLOSER,
		/** Nothing went in, twice. This bin is not being built from here. */
		ABANDON,
		/** A different bin from the one we were at. */
		NEW,
	}

	/**
	 * @param sameBin     is this the bin we were already standing at
	 * @param arrived     are we actually within reach of it, or still flying there
	 * @param todoHere    cells left in it now
	 * @param todoBefore  cells left in it at the last recount, or -1 if unknown
	 * @param sinceMs     how long since anything was placed here
	 * @param retries     how many times we have already moved in closer
	 */
	static Station station(boolean sameBin, boolean arrived, int todoHere, int todoBefore,
	                       long sinceMs, long stallMs, int retries) {
		if (!sameBin) return Station.NEW;
		if (todoBefore >= 0 && todoHere < todoBefore) return Station.RECENTRE;
		// THE CLOCK IS ABOUT THE PRINTER, NOT THE JOURNEY. It starts when you get there, or a
		// station across the region is abandoned before you arrive — and with a five-second window
		// that is most of them, which reads as a loop cycling bins and placing nothing.
		if (!arrived) return Station.WORKING;
		if (sinceMs <= stallMs) return Station.WORKING;
		return retries == 0 ? Station.CLOSER : Station.ABANDON;
	}

	// ---------------------------------------------------------------- going nowhere

	/**
	 * Told to go somewhere, and not going.
	 *
	 * <p>A THIRD clock, and the three are about different things — which is why one number cannot
	 * serve all of them:
	 *
	 * <ul>
	 *   <li>the STATION clock asks "is the printer taking anything from where I am standing", and
	 *       only runs once you have arrived;</li>
	 *   <li>the SESSION stall asks "is this loop doing anything at all", over minutes;</li>
	 *   <li>this one asks "am I actually travelling", and it is the fast one, because a flight that
	 *       is not moving is not going to start. Bumped into a corner, routing into a wall, wedged
	 *       under a slab: whatever the cause, three seconds of no movement and no placement while
	 *       there is somewhere to be is enough to say this spot is not working out.</li>
	 * </ul>
	 *
	 * <p>Standing still is only wrong while TRAVELLING. At the work you hover, and at a chest you
	 * stand while the withdrawal runs — both of those are the loop doing its job.
	 */
	static boolean goingNowhere(long now, long movedAtMs, long placedAtMs, boolean travelling,
	                            boolean fetching, long ms) {
		if (!travelling || fetching) return false;
		return now - movedAtMs > ms && now - placedAtMs > ms;
	}

	// ---------------------------------------------------------------- the session stall

	/**
	 * Nothing placed for a long time while building.
	 *
	 * <p>`todo` shrinking is the only honest evidence a block was placed — the printer does the
	 * placing and never tells us, so the world is the report. A fetch trip is not a stall, and
	 * neither is flying across the island to look at chunks we do not have: both reset the clock at
	 * the point they start.
	 */
	static boolean stalled(long now, long lastProgressMs, boolean fetching, long stallMs) {
		return !fetching && now - lastProgressMs > stallMs;
	}
}
