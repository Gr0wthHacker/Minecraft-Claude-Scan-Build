package dev.jack.chunkscan;

import net.minecraft.client.player.LocalPlayer;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.Level;

import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * What the build can actually TAKE today, ranked - as lines, so the command and the loop read the
 * same answer.
 *
 * <p>This is {@code /cscan analyze}, lifted out of the command so {@link Rally} can run it too.
 * Jack asked for the reset to <i>"restart with new materials after a cscan analyze"</i>, and a
 * report that exists twice is a report two callers can disagree about - the same reason
 * {@code proportions.measure} and {@code rubric.score} share one entry point on the Python side.
 *
 * <p>A bill of materials answers the wrong question for a trip: the commonest block in a design is
 * usually its roof, and a pack of roof is a pack with nothing to place against. What decides a trip
 * is how many cells of each material have a clickable face standing TODAY, which is what
 * {@link Plan#usable} ranks.
 */
final class Analyze {
	/** How many materials are worth reading out. Past this it is a bill of materials, not a trip. */
	static final int ROWS = 15;
	/**
	 * How many at the START of a session. Jack: <i>"when it starts, for it to analyze entire
	 * schematic and provide a list of top 5 materials that are immediately placeable"</i> - five,
	 * because this is the answer to <b>what should be in the pack</b>, and a pack holds a handful
	 * (see Plan.MAX_MATERIALS). Fifteen is the diagnostic, read after a reset when the question is
	 * why nothing worked.
	 */
	static final int START_ROWS = 5;

	/**
	 * How big a "place to work" is, in blocks.
	 *
	 * <p>The loop's own working window is {@link Loop#NEAR_RADIUS}, so a region of twice that is
	 * about what one anchor covers before the radius has to grow. Bigger, and two unrelated pieces
	 * of the park score as one destination; smaller, and a single mass is cut into fragments that
	 * each look like a poor trip.
	 */
	static final int REGION = Loop.NEAR_RADIUS * 2;

	/**
	 * How much better a FURTHER region has to be before it is worth crossing the park for.
	 *
	 * <p>Half. Among regions this close to the best, the NEAREST wins - so a marginal gain never
	 * buys a long flight, and a large one always does.
	 */
	static final double ENOUGH = 0.5;

	private Analyze() {}

	/** Somewhere worth flying to, and how many cells the pack could place once it got there. */
	record Where(BlockPos at, int cells) {}

	static List<String> report(Level level, Path dir, String name, LocalPlayer who) {
		return report(level, dir, name, who, ROWS);
	}

	/**
	 * The best place in the WHOLE design to go and use what is in the pack.
	 *
	 * <p><b>A DEAD END IS A FACT ABOUT AN ANCHOR, NOT ABOUT A DESIGN.</b> The loop's frontier is one
	 * course of a window round the anchor, so "nothing I can place here" says nothing at all about
	 * the other half a million cells - and the dead-end branch used to park for two minutes, teleport,
	 * re-anchor in the same place and do it again, all night. The log is unambiguous: it printed
	 * <i>23,672 placeable</i> from this very class and then reported a dead end on the next line.
	 *
	 * <p><b>...AND A TRIP IS WORTH WHAT YOU CAN PLACE AT THE FAR END, NOT HOW SHORT IT IS.</b> This
	 * ranked candidates by DISTANCE ALONE, and Jack watched what that does to a loaded pack: a full
	 * inventory of copper and deepslate, and the loop flew sixty-three blocks to place ONE submerged
	 * froglight in a lake, because it was nearer than the twenty thousand cells of copper and
	 * deepslate brick the pack was actually full of. It got shut in there, climbed out, stalled
	 * twice and reset, with nothing placed all session. Ranking one cell against a region is the
	 * whole bug: they are not comparable quantities.
	 *
	 * <p>So a candidate is a REGION ({@link #REGION}), scored by {@link #worth} - how many cells the
	 * pack could actually put in there, which caps a mountain of copper at the copper you carry. The
	 * nearest region within {@link #ENOUGH} of the best score wins.
	 *
	 * <p>Answered from the same pass {@link #report} already makes, so the reset stops throwing away
	 * the one number it computes that would have told it where to go. Restricted to what is CARRIED:
	 * flying to work we have no material for is the trip that started the dead end.
	 *
	 * @return null when there is nothing placeable anywhere, or nothing we hold the material for -
	 *         which is a real dead end, and is the only kind worth parking on.
	 */
	static Where bestWork(Level level, Path dir, String name, LocalPlayer who) {
		try {
			Work.Split sp = Work.split(level, dir, name, who.blockPosition(), 0);
			if (sp.todo().isEmpty()) return null;
			Map<String, Integer> have = Work.carrying(who);
			return bestOf(carriedNow(level, sp.todo(), have), have, who.blockPosition());
		} catch (Exception e) {
			// NEVER THROWS AT ITS CALLER, for the reason report() does not: this runs on the tick a
			// dead end is decided, and an exception there ends the session.
			return null;
		}
	}

	/** The cells of {@code todo} that can be placed right now with what is in the pack. */
	private static List<Work.Cell> carriedNow(Level level, List<Work.Cell> todo,
			Map<String, Integer> have) {
		List<Work.Cell> out = new ArrayList<>();
		for (Work.Cell c : Work.placeableNow(level, todo)) {
			if (have.getOrDefault(c.item(), 0) > 0) out.add(c);
		}
		return out;
	}

	/** A region of the world, {@link #REGION} blocks on a side. */
	private record Region(int x, int y, int z) {}

	private static Region regionOf(BlockPos p) {
		return new Region(Math.floorDiv(p.getX(), REGION), Math.floorDiv(p.getY(), REGION),
			Math.floorDiv(p.getZ(), REGION));
	}

	/**
	 * What one trip to this region could achieve: cells, capped per material by what is carried.
	 *
	 * <p>The cap is what makes two regions comparable. Nine thousand cells of copper is not nine
	 * thousand blocks of work when the pack holds seventeen hundred of it - and without the cap a
	 * region of one abundant material would outrank one holding everything the pack is full of.
	 */
	static int worth(List<Work.Cell> cells, Map<String, Integer> have) {
		Map<String, Integer> want = new HashMap<>();
		for (Work.Cell c : cells) want.merge(c.item(), 1, Integer::sum);
		int total = 0;
		for (Map.Entry<String, Integer> e : want.entrySet()) {
			total += Math.min(e.getValue(), have.getOrDefault(e.getKey(), 0));
		}
		return total;
	}

	/**
	 * Pick a place out of the cells the pack can place: the most work, and the nearest of the
	 * places that come close to it. Pure, so the rule can be argued with rather than watched.
	 *
	 * <p><b>A CANDIDATE IS A NEIGHBOURHOOD, NOT A BIN.</b> Scored on the bin alone, a grid cuts a
	 * long wall into a dozen fragments that each look like a poor trip - four hundred cells of it
	 * scored 32, and lost to a compact heap of forty. The score is the bin and its twenty-six
	 * neighbours, so a mass is measured whole wherever the grid happens to fall across it. The
	 * bins only exist to make that cheap; they are not what is being ranked.
	 */
	static Where bestOf(List<Work.Cell> mine, Map<String, Integer> have, BlockPos me) {
		if (mine.isEmpty()) return null;
		Map<Region, List<Work.Cell>> bins = new HashMap<>();
		for (Work.Cell c : mine) bins.computeIfAbsent(regionOf(c.pos()), k -> new ArrayList<>()).add(c);
		Map<Region, List<Work.Cell>> around = new HashMap<>();
		int best = 0;
		for (Region r : bins.keySet()) {
			List<Work.Cell> near = new ArrayList<>();
			for (int dx = -1; dx <= 1; dx++) {
				for (int dy = -1; dy <= 1; dy++) {
					for (int dz = -1; dz <= 1; dz++) {
						List<Work.Cell> n = bins.get(new Region(r.x() + dx, r.y() + dy, r.z() + dz));
						if (n != null) near.addAll(n);
					}
				}
			}
			around.put(r, near);
			best = Math.max(best, worth(near, have));
		}
		int enough = Math.max(1, (int) Math.ceil(best * ENOUGH));
		List<Work.Cell> pick = null;
		int picked = 0;
		double pickD = Double.MAX_VALUE;
		for (Map.Entry<Region, List<Work.Cell>> e : around.entrySet()) {
			int s = worth(e.getValue(), have);
			if (s < enough) continue;
			double d = centroid(e.getValue()).distSqr(me);
			if (d < pickD) { pickD = d; pick = e.getValue(); picked = s; }
		}
		if (pick == null) return null;
		// AIM AT THE MIDDLE OF THE MASS, not at whichever of its cells happens to be nearest: the
		// loop's own window is NEAR_RADIUS, and an anchor on the edge of a region covers half of it.
		BlockPos centre = centroid(pick);
		BlockPos at = pick.get(0).pos();
		double bestD = Double.MAX_VALUE;
		for (Work.Cell c : pick) {
			double d = c.pos().distSqr(centre);
			if (d < bestD) { bestD = d; at = c.pos(); }
		}
		return new Where(at, picked);
	}

	private static BlockPos centroid(List<Work.Cell> cells) {
		long x = 0, y = 0, z = 0;
		for (Work.Cell c : cells) {
			x += c.pos().getX();
			y += c.pos().getY();
			z += c.pos().getZ();
		}
		int n = cells.size();
		return new BlockPos((int) (x / n), (int) (y / n), (int) (z / n));
	}

	/** The carried materials this design still wants, biggest first. */
	private static String describeCarried(List<Work.Cell> mine, Map<String, Integer> have) {
		Map<String, Integer> cells = new HashMap<>();
		for (Work.Cell c : mine) cells.merge(c.item(), 1, Integer::sum);
		List<Map.Entry<String, Integer>> rows = new ArrayList<>(cells.entrySet());
		rows.sort((a, b) -> Integer.compare(b.getValue(), a.getValue()));
		StringBuilder sb = new StringBuilder();
		int shown = Math.min(rows.size(), 4);
		for (int i = 0; i < shown; i++) {
			if (i > 0) sb.append(", ");
			sb.append(have.getOrDefault(rows.get(i).getKey(), 0)).append("x ").append(rows.get(i).getKey());
		}
		if (rows.size() > shown) sb.append(" and ").append(rows.size() - shown).append(" more");
		return sb.toString();
	}

	/**
	 * @param rows how many materials to read out
	 * @return one line per row, without the {@code [cscan]} prefix, never null and never empty
	 */
	static List<String> report(Level level, Path dir, String name, LocalPlayer who, int rows) {
		List<String> out = new ArrayList<>();
		try {
			// Radius 0: the WHOLE design. `need` is the question about what is in reach.
			Work.Split sp = Work.split(level, dir, name, who.blockPosition(), 0);
			if (sp.todo().isEmpty()) {
				out.add(sp.name() + " has nothing left to place in a loaded chunk"
					+ (sp.digLeft() > 0 ? ", and " + sp.digLeft() + " to break by hand" : ""));
				return out;
			}
			List<Work.Cell> now = Work.placeableNow(level, sp.todo());
			Map<String, Integer> have = Work.carrying(who);
			Map<String, Storage.Container> index = Storage.load(dir);
			out.add(sp.name() + ": " + sp.todo().size() + " left in loaded chunks, " + now.size()
				+ " placeable against what stands, " + sp.unseen() + " out of view");
			// ---- WHAT THE PACK CAN ALREADY DO, BEFORE ANY LIST OF WHAT TO FETCH.
			//
			// Every row of this report used to read `carrying 0`, because the ranking is by
			// placeable cells and says nothing at all about the inventory - so a session that
			// began with a full pack of copper and deepslate was told to go and shop for oak
			// stairs. The one question a loaded pack asks is "where do I put this", and nothing
			// in the report answered it.
			List<Work.Cell> mine = new ArrayList<>();
			for (Work.Cell c : now) {
				if (have.getOrDefault(c.item(), 0) > 0) mine.add(c);
			}
			Where w = bestOf(mine, have, who.blockPosition());
			if (w != null) {
				out.add("  CARRYING WORK: " + describeCarried(mine, have) + " - " + mine.size()
					+ " cell(s) of it placeable now; best group is " + w.cells() + " at "
					+ Wand.fmt(w.at()));
			} else if (!have.isEmpty()) {
				out.add("  nothing in the pack can be placed anywhere loaded - the list below is"
					+ " what to fetch");
			}
			out.add("  placeable / left / carrying / indexed  - fill the pack top-down");
			int shown = 0;
			for (Plan.Usable u : Plan.usable(sp.todo(), now)) {
				if (shown++ >= rows) break;
				int indexed = 0;
				for (Storage.Hit h : Storage.findExact(index, u.item(), who.blockPosition(), true)) {
					indexed += h.count();
				}
				out.add("  " + u.placeable() + " / " + u.remaining() + " / "
					+ have.getOrDefault(u.item(), 0) + " / " + indexed + "  " + u.item()
					+ (u.placeable() == 0 ? "  (nothing to place against yet)" : ""));
			}
		} catch (Exception e) {
			// A REPORT NEVER THROWS AT ITS CALLER. The command can print an error; the loop cannot
			// afford one, because this runs on the tick that finishes a reset.
			out.add(name + ": could not analyse - " + e.getMessage());
		}
		return out;
	}
}
