package dev.jack.chunkscan;

import net.minecraft.core.BlockPos;
import net.minecraft.world.level.Level;

import java.util.ArrayList;
import java.util.List;

/**
 * Which cells you must not break without something underneath them.
 *
 * <p>This is a skyblock-only failure and it has no analogue in a normal world: break a block over
 * open void and the drop is gone — not scattered, not despawned in five minutes, GONE the moment
 * it passes the bottom of the world. On this island most designs hang over it. {@code Falls} lists
 * 41 dig cells and some are a hundred blocks up; {@code /cscan dig} has always been happy to walk
 * you to them and say nothing.
 *
 * <p>Three things decide the answer and each one was a way to be wrong:
 *
 * <ul>
 *   <li><b>A catch has to be SOLID, not merely present.</b> Vine, grass and water do not stop a
 *       falling item, and this file has already been bitten twice by "not air" being read as
 *       "solid" — the rim stair built twelve floating treads off a vine. {@code blocksMotion} is
 *       the question, the same one {@link Nav} asks.</li>
 *   <li><b>UNLOADED IS NOT EMPTY.</b> A chunk you cannot see is not evidence of void, and treating
 *       it as such would mark the whole lowland as a hazard from the deck. An unloaded column
 *       answers UNKNOWN, which is reported separately and never as safe.</li>
 *   <li><b>Depth, not the next block down.</b> An item falls until something stops it, so the
 *       search runs to the bottom of the world. A gap of three blocks under a dig cell is a step
 *       down; a gap of two hundred is a loss.</li>
 *   <li><b>LAVA DOES NOT CATCH A DROP, IT DESTROYS ONE — and it does not {@code blocksMotion}
 *       either.</b> {@link Nav} says so in as many words, and this search walked straight past a
 *       lava lake and kept going to the bedrock underneath it, returning CAUGHT. On the island
 *       that was almost unreachable; in the Nether it is the normal case, and it made the digger's
 *       one loss-preventing gate cheerfully approve every block whose drop burns.</li>
 * </ul>
 */
final class VoidRisk {
	/** Below this a drop is a nuisance, above it the item is gone for good. */
	static final int SAFE_FALL = 8;

	enum Verdict { CAUGHT, VOID, BURNED, UNKNOWN }

	record Cell(BlockPos pos, Verdict verdict, int drop) {}

	private VoidRisk() {}

	/**
	 * What is under this cell.
	 *
	 * @param bottom the world's floor (Y -64 here); the search never runs past it
	 */
	static Cell under(Level level, BlockPos p, int bottom) {
		for (int y = p.getY() - 1; y >= bottom; y--) {
			BlockPos q = new BlockPos(p.getX(), y, p.getZ());
			if (!level.isLoaded(q)) return new Cell(p, Verdict.UNKNOWN, p.getY() - y);
			// LAVA FIRST, because it is not solid and the solid test would walk past it. Source and
			// flowing are the same BLOCK (Blocks.LAVA, differing only in `level`), so one name test
			// catches both - and it is LavaGuard's name test, so the two cannot come to disagree
			// about what lava is.
			if (LavaGuard.isLava(net.minecraft.core.registries.BuiltInRegistries.BLOCK
					.getKey(level.getBlockState(q).getBlock()).getPath())) {
				return new Cell(p, Verdict.BURNED, p.getY() - y);
			}
			if (level.getBlockState(q).blocksMotion()) {
				return new Cell(p, Verdict.CAUGHT, p.getY() - y);
			}
		}
		return new Cell(p, Verdict.VOID, p.getY() - bottom);
	}

	/** Every cell in `cells` whose drop is long enough to lose what you break. */
	static List<Cell> hazards(Level level, List<BlockPos> cells) {
		List<Cell> out = new ArrayList<>();
		int bottom = level.getMinY();
		for (BlockPos p : cells) {
			Cell c = under(level, p, bottom);
			if (c.verdict() == Verdict.VOID || c.verdict() == Verdict.BURNED
				|| (c.verdict() == Verdict.CAUGHT && c.drop() > SAFE_FALL)) {
				out.add(c);
			}
		}
		return out;
	}

	/** One line for chat, or "" when there is nothing to say. */
	static String warn(List<Cell> hazards, int total) {
		if (hazards.isEmpty()) return "";
		long lost = hazards.stream().filter(c -> c.verdict() == Verdict.VOID).count();
		long burned = hazards.stream().filter(c -> c.verdict() == Verdict.BURNED).count();
		StringBuilder b = new StringBuilder();
		b.append("WARNING: ").append(hazards.size()).append(" of ").append(total)
			.append(" hang over a long drop");
		if (lost > 0) b.append(" — ").append(lost).append(" over OPEN VOID: what you break is gone");
		if (burned > 0) b.append(" — ").append(burned).append(" over LAVA: what you break burns");
		Cell worst = hazards.get(0);
		for (Cell c : hazards) if (c.drop() > worst.drop()) worst = c;
		b.append(". Worst at ").append(worst.pos().getX()).append(" ").append(worst.pos().getY())
			.append(" ").append(worst.pos().getZ()).append(", ").append(worst.drop())
			.append(" blocks of nothing. Put a catch floor under it first");
		return b.toString();
	}
}
