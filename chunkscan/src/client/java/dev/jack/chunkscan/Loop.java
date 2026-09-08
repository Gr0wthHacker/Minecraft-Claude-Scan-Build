package dev.jack.chunkscan;

import net.minecraft.core.BlockPos;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

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
		return phase(todo, unseen, canWork, fetching, haveTarget, anyShortfall, false);
	}

	/**
	 * @param topUp the loop has just STARTED and the pack has not been filled yet.
	 *
	 * <p>The standing policy is build-before-shop: anything placeable with what you are holding, and
	 * the trip does not start. That is right in the middle of a session and wrong at the beginning
	 * of one, where it means setting off with whatever happened to be in the pack, placing it, and
	 * then making the trip anyway - having already flown to the work and back.
	 *
	 * <p>So a start is a FETCH, on the same terms as any other: it runs until the pack is full or
	 * the design is covered, never until one spot's shortfall is met. Nothing to fetch and it falls
	 * straight through to building, which is what a full pack or a fully-stocked design looks like.
	 */
	static Phase phase(int todo, int unseen, boolean canWork, boolean fetching, boolean haveTarget,
	                   boolean anyShortfall, boolean topUp) {
		if (todo == 0) {
			// A TRIP IN PROGRESS IS NOT INTERRUPTED BY THE WORK BEING OUT OF VIEW. The work is out
			// of view BECAUSE of the trip: the chunks under the anchor unloaded on the way to the
			// chest. Turning round to look at them and then turning round again to finish the
			// trip is the ping-pong Jack watched. Nothing hidden at all means nothing to carry the
			// materials to, and complete still beats everything.
			if (unseen > 0 && fetching && haveTarget) return Phase.FETCH;
			return unseen > 0 ? Phase.LOOK : Phase.COMPLETE;
		}
		if (fetching || !canWork || topUp) {
			if (haveTarget) return Phase.FETCH;
			if (!canWork) return anyShortfall ? Phase.PACK_FULL : Phase.DEAD_END;
		}
		return Phase.BUILD;
	}

	/**
	 * Is the start-of-session top-up finished?
	 *
	 * <p><b>Only once the question has actually been ASKED.</b> The first version ended it on any
	 * phase that was not a fetch, and the frontier is empty at the start of most sessions - the
	 * design is across the island and its chunks are not loaded, so nothing is placeable and the
	 * fetch question was skipped. The phase came back BUILD, the top-up was cleared having done
	 * nothing at all, and the pack was never filled. Reported as: it is not filling inventory.
	 *
	 * <p>Which is this file's own recurring shape - a thing that does nothing, quietly - arriving
	 * in the one place whose whole job is to happen before anything else.
	 *
	 * @param asked whether the shortfall was actually worked out this recount
	 */
	static boolean topUpOver(Phase phase, boolean asked) {
		return asked && phase != Phase.FETCH;
	}

	// ---------------------------------------------------------------- the working area

	/**
	 * How far from the anchor a cell counts as this session's work.
	 *
	 * <p><b>A design is not a work area.</b> The clusters were ranked over every remaining cell the
	 * client could see, so on a 240-block island the "best spot" was routinely at the other end of
	 * it - and having flown there, the next recount could just as well send you back. Jack:
	 * <i>"it shouldnt go across any range to reach blocks, we should be doing focused radius"</i>.
	 *
	 * <p>Two hundred blocks is a working AREA rather than a trip: it comfortably holds the deck, or
	 * the lowland, or the plate, and it does not hold two of them. The area is worked out before
	 * anything else is considered, which is what makes progress legible instead of a tour.
	 *
	 * <p>It bounds the BUILD only. A container three hundred blocks away is still a legitimate trip:
	 * that is one journey to fill a pack, not a hundred journeys to place a hundred blocks.
	 */
	/**
	 * WHAT IS WITHIN ARM'S REACH OF WHERE I AM STANDING.
	 *
	 * <p>This is the radius the loop actually works at, and it is small on purpose. What it replaced
	 * was a two-hundred block AREA whose clusters were then RANKED - doable discounted by distance -
	 * so the best spot in a region the size of a small town won, and having flown there the next
	 * recount could rank something else top and send it back. Two hundred blocks is not an immediate
	 * radius, it is a region, and calling it an area did not make the flying stop. Jack:
	 * <i>"its still flying all over the damn place to find where to place blocks"</i>.
	 *
	 * <p>The rule he asked for is simpler than any ranking and it is monotonic: look at what is
	 * around you, build that out, and only when there is nothing left near you do you look further.
	 * Nothing can send the loop across the map while there is a block at its feet, because nothing
	 * further away is ever considered.
	 */
	static final int NEAR_RADIUS = 16;

	/**
	 * ...and how far it is willing to look once the near work is genuinely finished.
	 *
	 * <p>Doubling, so a design with a sparse patch does not creep outward one block at a time, and
	 * capped: past this it is not looking around, it is choosing a new place to work.
	 */
	static int grow(int radius) {
		return Math.min(WORK_RADIUS, Math.max(NEAR_RADIUS, radius * 2));
	}

	/**
	 * How far the nearest remaining cell is, in one pass.
	 *
	 * <p>Growing by re-scanning is five passes over the whole design every recount while there is
	 * nothing near - and on 540,862 cells that is millions of distance checks for an answer one
	 * pass already contains. Ask how far the work IS, then open the radius to it in a single step.
	 */
	static double nearestDistance(List<Work.Cell> cells, BlockPos from) {
		double best = Double.MAX_VALUE;
		for (Work.Cell c : cells) best = Math.min(best, c.pos().distSqr(from));
		return best == Double.MAX_VALUE ? best : Math.sqrt(best);
	}

	/** The smallest radius on the doubling ladder that reaches {@code want}, or WORK_RADIUS. */
	static int radiusReaching(double want) {
		int r = NEAR_RADIUS;
		while (r < WORK_RADIUS && r < want) r = grow(r);
		return r;
	}

	/** Back to arm's length. Called the moment there is work in front of you again. */
	static int nearAgain() { return NEAR_RADIUS; }

	static final int WORK_RADIUS = 200;

	/**
	 * ...and how far a FETCH may go for it.
	 *
	 * <p>The build was bounded and the fetch deliberately was not: one journey to fill a pack is
	 * worth more than a hundred journeys to place a hundred blocks. That reasoning is right and the
	 * absence of any bound at all was not - a container index spanning two worlds 120,000 blocks
	 * apart made "the biggest shortfall that has an address" into a trip no route can even be
	 * searched for (Nav.MAX_RANGE is 512), so the flight fell through to going direct and simply
	 * kept going. Reported as: still going infinite far radiuses for no reason.
	 *
	 * <p>Twice the working area. A fetch is allowed to be a real trip and is not allowed to be an
	 * expedition, and anything past this is a sign the materials are not where the build is - which
	 * is worth being TOLD rather than worth flying.
	 */
	static final int FETCH_RADIUS = 400;

	/**
	 * ...and the distance past which a trip is not a trip at all.
	 *
	 * <p>{@link #FETCH_RADIUS} is a PREFERENCE - everything inside it comes first and the rest is
	 * kept at the back, because if the only stock in the world is far away then going is still
	 * better than stopping. That reasoning has a floor under it: past twice {@link Nav#MAX_RANGE}
	 * no route can even be searched for, so the flight falls through to going DIRECT and simply
	 * keeps going - into terrain, across an ocean, or at a container index entry left over from
	 * another world 121,000 blocks away. The body is moving the whole time, so no clock and no
	 * rung of the recovery ladder can see it.
	 *
	 * <p>The same number {@link Rally#LOST_AT} uses, for the same reason and from the same source.
	 */
	static final int TRIP_LIMIT = 2 * Nav.MAX_RANGE;

	/** The targets a route could actually be searched for. See {@link #TRIP_LIMIT}. */
	static <T> List<T> withinTrip(List<T> targets, java.util.function.Function<T, BlockPos> where,
	                              BlockPos from, int limit) {
		double r2 = (double) limit * limit;
		List<T> out = new ArrayList<>();
		for (T t : targets) {
			BlockPos p = where.apply(t);
			if (p == null || p.distSqr(from) <= r2) out.add(t);
		}
		return out;
	}

	/**
	 * ONE COURSE AT A TIME, FROM THE BOTTOM.
	 *
	 * <p>Jack: <i>"what if we took baritone's approach where it does it by Y layer"</i>. It answers
	 * four separate reports at once, and the reason is geometric rather than tidy-minded.
	 *
	 * <p><b>A station was a CUBE and a stand is a DISC.</b> Cells were binned into 4-cubes, whose far
	 * corner is 3.46 from the middle, and a standing spot covers about 3 - so part of every bin was
	 * out of reach BY CONSTRUCTION. The loop highlighted them, flew there, placed the near face,
	 * stalled on the rest, moved in closer, abandoned the bin and picked it again next recount.
	 * Reported as: it is covering just out of reach of placing blocks very often.
	 *
	 * <p>Restricted to one course, a bin is a 4x4 SQUARE - half-diagonal 2.83 - and a body hovering
	 * a course above it has its eyes 2.7 up, which leaves about 3.2 of horizontal reach. The whole
	 * bin fits, with room to spare, and it fits the same way everywhere instead of depending on how
	 * the work happened to be shaped.
	 *
	 * <p>Three more things fall out of it. <b>Support</b>: building upward means the course below is
	 * already there, which is what the work list's own bottom-up order has always assumed and
	 * nothing enforced - so far fewer cells have nothing to place against. <b>Travel</b>: a plane is
	 * swept, where a cloud is toured. <b>Standing</b>: the finished course below is a floor, so
	 * there is somewhere to land rather than hover.
	 */
	static final int LAYER_BAND = 1;

	/**
	 * How many placeable cells a recount needs to find before it stops looking.
	 *
	 * <p><b>Jack: <i>"long gaps where its searching and cant find anything, then suddenly will find
	 * things just below it".</b></i> The frontier was built by asking `Printer.everPlaceable` about
	 * EVERY cell of a course - and a course inside a 200-block working radius is tens of thousands
	 * of them, each costing up to seventy-two `getStateForPlacement` calls. The 400-per-recount
	 * budget was therefore spent in COURSE order on cells that happened to come first, most of them
	 * a hundred blocks away, and the work at the body's own feet was reached by luck. Several
	 * recounts of that is the gap; the recount that happens to reach the near cells is the sudden
	 * find.
	 *
	 * <p>Nearest first, and stop once there is enough to choose a station and fill a trip. Enough
	 * is a few bins - the printer re-scans what is actually in reach on its own tick every tick, so
	 * this only has to be good enough to decide WHERE TO STAND.
	 */
	static final int FRONTIER_ENOUGH = 96;

	/**
	 * The courses to try, CURRENT ONE FIRST, then lowest to highest.
	 *
	 * <p><b>Jack: <i>"it flies back and forth"</i>.</b> The frontier was the lowest course of a
	 * window round the anchor, and the anchor is the spot being built - which comes from the
	 * frontier. A circle with no damping: the body moves, the window moves, the lowest course
	 * flips, a new spot is chosen two seconds later, and it flies there. The log shows Y203 and
	 * Y202 trading places every recount for minutes with nothing finished either time.
	 *
	 * <p>Sticking to the course being worked costs almost nothing in build ORDER, because every
	 * cell in a frontier has already been proved to have a real face to click TODAY - bottom-up is
	 * a preference here, not a correctness rule - and it is the difference between working a course
	 * and touring one.
	 */
	static List<Integer> courseOrder(List<Integer> courses, int current) {
		List<Integer> out = new ArrayList<>(courses.size());
		if (courses.contains(current)) out.add(current);
		for (int y : courses) if (y != current) out.add(y);
		return out;
	}

	/** The distinct courses that still hold work, lowest first. */
	static List<Integer> layers(List<Work.Cell> cells) {
		java.util.TreeSet<Integer> ys = new java.util.TreeSet<>();
		for (Work.Cell c : cells) ys.add(c.pos().getY());
		return new ArrayList<>(ys);
	}

	/**
	 * The cells of one course.
	 *
	 * @param band how many courses above it to take as well. A slab and the block it sits on are one
	 *             course of BUILDING even when they are two of geometry, and splitting them costs a
	 *             whole extra pass over the same ground.
	 */
	static List<Work.Cell> layer(List<Work.Cell> cells, int y, int band) {
		List<Work.Cell> out = new ArrayList<>();
		for (Work.Cell c : cells) {
			int d = c.pos().getY() - y;
			if (d >= 0 && d <= band) out.add(c);
		}
		return out;
	}

	/**
	 * The trips worth making, nearest-first among those in range.
	 *
	 * <p>Ranking was by shortfall SIZE alone, so the biggest pile won however far away it was. Size
	 * still decides between two trips you would both make; being out of range decides whether it is
	 * a trip at all. Everything in range comes first, and out-of-range targets are kept at the back
	 * rather than dropped - if the only stock in the world is far away, going is still better than
	 * stopping, and the caller says so.
	 */
	static <T> List<T> byTrip(List<T> targets, java.util.function.Function<T, BlockPos> where,
	                          BlockPos from, int radius) {
		double r2 = (double) radius * radius;
		List<T> near = new ArrayList<>(), far = new ArrayList<>();
		for (T t : targets) {
			BlockPos p = where.apply(t);
			(p != null && p.distSqr(from) <= r2 ? near : far).add(t);
		}
		near.addAll(far);
		return near;
	}

	/** Is every trip on offer out of reasonable range? Worth saying once. */
	static <T> boolean allFar(List<T> targets, java.util.function.Function<T, BlockPos> where,
	                          BlockPos from, int radius) {
		if (targets.isEmpty()) return false;
		double r2 = (double) radius * radius;
		for (T t : targets) {
			BlockPos p = where.apply(t);
			if (p != null && p.distSqr(from) <= r2) return false;
		}
		return true;
	}

	/** The cells of `all` inside `radius` of `anchor`. */
	static List<Work.Cell> focus(List<Work.Cell> all, BlockPos anchor, int radius) {
		if (anchor == null) return all;
		double r2 = (double) radius * radius;
		List<Work.Cell> out = new ArrayList<>();
		for (Work.Cell c : all) if (c.pos().distSqr(anchor) <= r2) out.add(c);
		return out;
	}

	/**
	 * Where to move the working area to, once the old one is finished.
	 *
	 * <p>The NEAREST remaining cell, so the area walks across the design rather than jumping about
	 * it. Null when there is nothing left, which is the caller's cue that the focus is not what is
	 * wrong.
	 */
	/**
	 * A WORKING LOAD of one material: four stacks. Carrying this much of something the design still
	 * wants, the loop goes and places it before it opens a chest for anything else.
	 *
	 * <p>Jack: <i>"it shouldn't be pulling things out of chests if it has for example a 90% inventory
	 * of a single item, just find where to place that item and do it, it doesn't need to go fill up
	 * with 1 stack of a random item."</i> The fetch decision asked only about the lowest course near
	 * the anchor; a pack full of stone brick beside a course of slabs read as "nothing I can place"
	 * and became a trip for one stack of slabs, and the top-up at every session start asked no
	 * question about the pack at all.
	 */
	static final int WORK_LOAD = 256;

	/** The cells whose material the pack holds at least `minLoad` of. */
	static List<Work.Cell> carriedWork(Map<String, Integer> carrying, List<Work.Cell> cells, int minLoad) {
		List<Work.Cell> out = new ArrayList<>();
		for (Work.Cell c : cells) {
			if (carrying.getOrDefault(c.item(), 0) >= minLoad) out.add(c);
		}
		return out;
	}

	/** What is carried for these cells, for a message: "1984x stone_bricks, 320x stone_brick_slab". */
	static String describeCarried(Map<String, Integer> carrying, List<Work.Cell> cells, int minLoad) {
		java.util.LinkedHashMap<String, Integer> seen = new java.util.LinkedHashMap<>();
		for (Work.Cell c : cells) {
			int n = carrying.getOrDefault(c.item(), 0);
			if (n >= minLoad) seen.putIfAbsent(c.item(), n);
		}
		StringBuilder sb = new StringBuilder();
		for (var e : seen.entrySet()) sb.append(sb.length() == 0 ? "" : ", ").append(e.getValue()).append("x ").append(e.getKey());
		return sb.toString();
	}

	/**
	 * Should the loop turn toward cells it already carries the material for instead of fetching?
	 * Only when it is not already on a trip, cannot work where it stands, and there is such a cell.
	 */
	static boolean buildWhatYouCarry(boolean canWork, boolean fetching, boolean carriedAnywhere) {
		return !fetching && !canWork && carriedAnywhere;
	}

	/**
	 * Is there nothing in this list the session wants? With no filter that is simply "empty"; with
	 * `/cscan only moss_block` set, a list of two thousand slabs and no moss is nothing to do.
	 */
	static boolean noneWanted(List<Work.Cell> todo, java.util.Set<String> only) {
		if (only == null) return todo.isEmpty();
		for (Work.Cell c : todo) {
			if (only.contains(c.item())) return false;
		}
		return true;
	}

	/** `minecraft:moss_block`, `moss_block[snowy=false]`, `MOSS_BLOCK` -> `moss_block`. */
	static String itemName(String typed) {
		String s = typed.trim().toLowerCase(java.util.Locale.ROOT);
		int b = s.indexOf('[');
		if (b >= 0) s = s.substring(0, b);
		int c = s.indexOf(':');
		if (c >= 0) s = s.substring(c + 1);
		return s;
	}

	/** Cells this far from the body's own cell are within the printer's reach, give or take the eye. */
	static final int VICINITY = 5;

	/**
	 * Stay put and keep placing? Jack: <i>"it should look in its immediate vicinity and just keep
	 * placing as much as possible always"</i> - and, of the old behaviour, <i>"sometimes it has a
	 * massive patch, will place 5, then go fly away from it."</i> The station was re-chosen every
	 * recount as the FULLEST bin, so placing five blocks made another bin the fullest and the
	 * flight left with work still in reach. While anything placeable is within reach of where the
	 * body is, the answer is to stay: the printer places on its own tick, and moving is a chance
	 * to touch something. The hold ends only when nothing in reach is left, or when it has held
	 * for `stallMs` with nothing placed - then the station machinery gets its turn, and the hold
	 * is not re-armed until `coolUntil`.
	 */
	static boolean holdHere(int inReach, int placedNow, long now, long heldSince, long coolUntil, long stallMs) {
		return holdHere(inReach, placedNow, 0, now, heldSince, coolUntil, stallMs);
	}

	/**
	 * @param dropped attempts the server never applied since the last recount
	 *
	 * <p>A DROPPED PACKET IS THE PRINTER WORKING, NOT THE SPOT FAILING - the same distinction
	 * {@link #stationFromReport} draws, and this clock needed it for the same reason. One attempt
	 * in five is dropped, in runs; without this the hold ends five seconds into a burst, the body
	 * flies off perfectly good work, and the next station meets the same burst.
	 */
	static boolean holdHere(int inReach, int placedNow, int dropped, long now, long heldSince,
	                        long coolUntil, long stallMs) {
		if (inReach <= 0 || now < coolUntil) return false;
		return placedNow > 0 || dropped > 0 || heldSince == 0 || now - heldSince <= stallMs;
	}

	static BlockPos reanchor(List<Work.Cell> all, BlockPos from) {
		BlockPos best = null;
		double bestD = Double.MAX_VALUE;
		for (Work.Cell c : all) {
			double d = c.pos().distSqr(from);
			if (d < bestD) { bestD = d; best = c.pos(); }
		}
		return best;
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

	/**
	 * The same decision, but with the PRINTER'S OWN REPORT instead of a stopwatch.
	 *
	 * <p>Every clock in this file exists because of one sentence in the project's notes: <i>"the
	 * printer never reports back, so `todo` shrinking is the only honest evidence a block was
	 * placed"</i>. When {@link Printer} is the thing placing, that is no longer true, and the
	 * difference is not merely faster - it is a different KIND of answer:
	 *
	 * <ul>
	 *   <li><b>a placement is progress, immediately.</b> No waiting to see whether the count
	 *       moves;</li>
	 *   <li><b>a REFUSAL is proof, immediately.</b> The clock could only ever say "nothing has
	 *       happened for five seconds" and guess why; a refused cell is the world saying no. There
	 *       is nothing to wait for, so the bin is abandoned on the spot;</li>
	 *   <li><b>and silence still means silence.</b> Nothing attempted yet is not evidence of
	 *       anything, so it falls through to the clock exactly as before. That fallback is what
	 *       keeps this honest: the report answers only what it actually observed.</li>
	 * </ul>
	 *
	 * @param placed   cells the printer saw land since the last recount
	 * @param refused  cells it saw refused - still air after its retries, or the wrong state
	 */
	static Station stationFromReport(boolean sameBin, boolean arrived, int todoHere, int todoBefore,
	                                 long sinceMs, long stallMs, int retries,
	                                 int placed, int refused) {
		return stationFromReport(sameBin, arrived, todoHere, todoBefore, sinceMs, stallMs, retries,
			placed, refused, 0);
	}

	/**
	 * @param dropped attempts the SERVER never applied - see Printer.interval
	 *
	 * <p><b>A DROPPED PACKET IS NOT EVIDENCE ABOUT THE SPOT.</b> Measured over 1,215 placements,
	 * one attempt in five is silently dropped, in runs of up to twenty - and every clock in this
	 * file then read those five seconds of nothing as <i>this spot cannot be built</i> and moved.
	 * An actuator failure was being diagnosed as a geometry failure, at every station, which is
	 * most of the thrashing this file has spent four sessions adding watchdogs for.
	 *
	 * <p>So the three answers are now three: something landed is progress, something was REFUSED
	 * is the world saying no and there is nothing to wait for, and something was DROPPED is the
	 * link saying wait - the pace backs off on its own and the next attempt is the evidence. The
	 * ninety-second session stall is still the backstop, so a link that never recovers cannot
	 * park the loop here for ever.
	 */
	static Station stationFromReport(boolean sameBin, boolean arrived, int todoHere, int todoBefore,
	                                 long sinceMs, long stallMs, int retries,
	                                 int placed, int refused, int dropped) {
		if (!sameBin) return Station.NEW;
		if (placed > 0) return Station.RECENTRE;
		// A refusal is knowledge, not a timeout. One more try from closer in, because the commonest
		// refusal is reach; then it is not this trip's work.
		if (refused > 0) return retries == 0 ? Station.CLOSER : Station.ABANDON;
		if (dropped > 0) return Station.RECENTRE;      // the channel, not the spot: hold and retry
		return station(sameBin, arrived, todoHere, todoBefore, sinceMs, stallMs, retries);
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

	// ---------------------------------------------------------------- thrashing

	/**
	 * Giving up on spot after spot and building nothing.
	 *
	 * <p>The SLOW version of the infinite loop, and the one no single watchdog catches: abandon spot
	 * A, take B, abandon B, take A again once its minute is up, for ever. Each individual decision is
	 * correct and the sequence is a machine going nowhere.
	 *
	 * <p>The evidence is the pair: several spots given up on, and NOTHING placed while that happened.
	 * Either alone is normal — a design has awkward corners, and a slow printer is still a printer.
	 */	static boolean thrashing(int spotsAbandoned, int placedSince, int limit) {
		return thrashing(spotsAbandoned, placedSince, limit, 1);
	}

	/** ...where fewer than `trickle` blocks between abandonments counts as nothing placed. */
	static boolean thrashing(int spotsAbandoned, int placedSince, int limit, int trickle) {
		return spotsAbandoned >= limit && placedSince < trickle;
	}

	/** Is this centre inside a spot still being passed over? Expired entries are dropped on the way. */
	static boolean avoided(Map<BlockPos, Long> avoided, BlockPos centre, long now, int radius) {
		avoided.values().removeIf(until -> now >= until);
		double r2 = (double) radius * radius;
		for (BlockPos a : avoided.keySet()) {
			if (a.distSqr(centre) <= r2) return true;
		}
		return false;
	}

	// ---------------------------------------------------------------- the session stall

	/**
	 * Nothing placed for a long time while building.
	 *
	 * <p>`todo` shrinking is the only honest evidence a block was placed — the printer does the
	 * placing and never tells us, so the world is the report. A fetch trip is not a stall, and
	 * neither is flying across the island to look at chunks we do not have: both reset the clock at
	 * the point they start.
	 *//**
	 * A flight back to the work anchor that has not got there. Ignored means the autopilot struck
	 * it twice already; otherwise it is a clock, because the anchor is a destination like any other
	 * and was the only one without a give-up.
	 */
	static boolean returnGivenUp(long now, long sinceMs, long limitMs, boolean ignored) {
		return ignored || (sinceMs > 0 && now - sinceMs > limitMs);
	}

	static boolean stalled(long now, long lastProgressMs, boolean fetching, long stallMs) {
		return !fetching && now - lastProgressMs > stallMs;
	}
}
