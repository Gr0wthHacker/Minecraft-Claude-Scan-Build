package dev.jack.chunkscan;

import net.minecraft.client.player.LocalPlayer;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.Level;

import java.nio.file.Path;
import java.util.ArrayList;
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

	private Analyze() {}

	static List<String> report(Level level, Path dir, String name, LocalPlayer who) {
		return report(level, dir, name, who, ROWS);
	}

	/**
	 * The nearest cell in the WHOLE design that can be placed right now with what is carried.
	 *
	 * <p><b>A DEAD END IS A FACT ABOUT AN ANCHOR, NOT ABOUT A DESIGN.</b> The loop's frontier is one
	 * course of a window round the anchor, so "nothing I can place here" says nothing at all about
	 * the other half a million cells - and the dead-end branch used to park for two minutes, teleport,
	 * re-anchor in the same place and do it again, all night. The log is unambiguous: it printed
	 * <i>23,672 placeable</i> from this very class and then reported a dead end on the next line.
	 *
	 * <p>Answered from the same pass {@link #report} already makes, so the reset stops throwing away
	 * the one number it computes that would have told it where to go. Restricted to what is CARRIED:
	 * flying to work we have no material for is the trip that started the dead end.
	 *
	 * @return null when there is nothing placeable anywhere, or nothing we hold the material for -
	 *         which is a real dead end, and is the only kind worth parking on.
	 */
	static BlockPos nearestPlaceable(Level level, Path dir, String name, LocalPlayer who) {
		try {
			Work.Split sp = Work.split(level, dir, name, who.blockPosition(), 0);
			if (sp.todo().isEmpty()) return null;
			Map<String, Integer> have = Work.carrying(who);
			BlockPos me = who.blockPosition();
			BlockPos best = null;
			double bestD = Double.MAX_VALUE;
			for (Work.Cell c : Work.placeableNow(level, sp.todo())) {
				if (have.getOrDefault(c.item(), 0) <= 0) continue;
				double d = c.pos().distSqr(me);
				if (d < bestD) {
					bestD = d;
					best = c.pos();
				}
			}
			return best;
		} catch (Exception e) {
			// NEVER THROWS AT ITS CALLER, for the reason report() does not: this runs on the tick a
			// dead end is decided, and an exception there ends the session.
			return null;
		}
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
