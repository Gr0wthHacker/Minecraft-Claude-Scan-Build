package dev.jack.chunkscan;

import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.FallingBlock;

import java.util.Collection;

/**
 * Where the lava is, and whether it is near enough to kill you.
 *
 * <p><b>THE CLIENT CAN SEE BEHIND THE WALL, AND THAT IS THE ENTIRE EDGE OVER A HUMAN.</b> A person
 * branch-mining in the Nether digs blind and dies to a pocket they had no way to know about; this
 * mod already holds every block of every loaded chunk, the ones behind the rock included. So the
 * guard here is not "react to lava when it appears" — by then you have ten ticks. It is <i>never
 * open a corridor that has lava anywhere near it, because we could already see it.</i>
 *
 * <p>Reaction is still the third layer, and it has to be fast: <b>lava in the Nether spreads one
 * block every 10 ticks against the Overworld's 30.</b> Half a second of deciding is two blocks of
 * flow.
 *
 * <p>Three rules, and the middle one is the opposite of what the router does:
 *
 * <ul>
 *   <li><b>{@code lava} is matched EXACTLY, never as a substring.</b> {@link Rules#isProtected}
 *       matches substrings on purpose — {@code gray_wool} is protected because {@code wool} is in
 *       the list — and the same trick here makes {@code lava_cauldron}, a decoration, read as a
 *       lethal hazard and refuses every corridor near somebody's brewing room.</li>
 *   <li><b>UNLOADED IS UNSAFE.</b> {@link Nav} counts an unloaded chunk as PASSABLE, deliberately,
 *       because refusing to route through one fails every long flight. For DIGGING the same fact
 *       means the opposite: a cell we cannot see is a cell whose lava we cannot see, and digging
 *       toward it is the blind case this class exists to remove. The asymmetry is the point —
 *       routing is optimistic because a wasted flight is cheap, and mining is pessimistic because
 *       a wrong answer is the inventory.</li>
 *   <li><b>A falling block overhead is the same class of death.</b> Gravel is common in the Nether
 *       and a column of it dropped on your head in a one-wide corridor is suffocation. Asked of
 *       the GAME ({@link FallingBlock}) rather than of a name list, because a name list is a
 *       memory and this project has been bitten by that rule a dozen times.</li>
 * </ul>
 *
 * <p>Distance is CHEBYSHEV — a cube, not a sphere. It over-refuses slightly at the corners, and
 * that is the correct direction to be wrong in: the cost is a corridor that turns earlier than it
 * strictly had to, against a cost of dying.
 */
final class LavaGuard {

	/** Exactly the fluid. See the class note on why this is not a substring test. */
	static final String LAVA = "lava";

	/** How far from a planned corridor lava has to be before the corridor is worth digging. */
	static final int SEGMENT_CLEAR = 3;

	/** ...and how far from the BODY, which is a tighter question than how far from the work. */
	static final int BODY_CLEAR = 2;

	private LavaGuard() {}

	enum Kind {
		/** Lava, seen. */
		LAVA_SEEN,
		/** A cell we cannot see, which for digging is not the same as a cell that is empty. */
		UNSEEN,
		/** Gravel or sand overhead: it comes down when you take what is under it. */
		FALLING
	}

	record Threat(BlockPos at, Kind kind) {
		String describe() {
			return switch (kind) {
				case LAVA_SEEN -> "lava at " + at.getX() + " " + at.getY() + " " + at.getZ();
				case UNSEEN -> "an unloaded cell at " + at.getX() + " " + at.getY() + " " + at.getZ()
					+ " — we cannot see what is behind it";
				case FALLING -> "a falling block over " + at.getX() + " " + at.getY() + " " + at.getZ();
			};
		}
	}

	/**
	 * A world you can ask about by name, so the geometry is testable with no client anywhere near
	 * it — the shape {@link Nav.Passable} and {@link Burial.Solid} already use here.
	 */
	interface Cells {
		/** The block at this cell, or NULL when the chunk is not loaded. */
		String at(int x, int y, int z);

		/**
		 * Does this block fall when what is under it goes? Asked of the game in play and stated
		 * outright in a test — one source each, so the two cannot drift.
		 */
		boolean falls(int x, int y, int z);
	}

	/** The live world. */
	static Cells of(Level level) {
		return new Cells() {
			@Override public String at(int x, int y, int z) {
				BlockPos p = new BlockPos(x, y, z);
				if (!level.isLoaded(p)) return null;
				return BuiltInRegistries.BLOCK.getKey(level.getBlockState(p).getBlock()).getPath();
			}

			@Override public boolean falls(int x, int y, int z) {
				BlockPos p = new BlockPos(x, y, z);
				if (!level.isLoaded(p)) return false;
				return level.getBlockState(p).getBlock() instanceof FallingBlock;
			}
		};
	}

	static boolean isLava(String name) {
		return LAVA.equals(name);
	}

	/**
	 * Is this cell, or any of the six it touches, lava?
	 *
	 * <p>The per-swing check. Break a block with lava on any face and the lava is in the hole
	 * before the item has finished dropping — including from ABOVE, which is why this is six
	 * neighbours and not the four you can see standing in a corridor.
	 */
	static boolean touching(Cells w, BlockPos p) {
		if (isLava(w.at(p.getX(), p.getY(), p.getZ()))) return true;
		for (net.minecraft.core.Direction d : net.minecraft.core.Direction.values()) {
			BlockPos q = p.relative(d);
			if (isLava(w.at(q.getX(), q.getY(), q.getZ()))) return true;
		}
		return false;
	}

	/**
	 * Is something that falls sitting directly on top of this cell?
	 *
	 * <p>Only the cell immediately above. A stack of gravel comes down as a column, so catching the
	 * bottom of it catches the whole stack; walking the column upward would refuse a corridor under
	 * any gravel anywhere above it, which in the Nether is most of them.
	 */
	static boolean unstableAbove(Cells w, BlockPos p) {
		return w.falls(p.getX(), p.getY() + 1, p.getZ());
	}

	/**
	 * The first thing near this segment that makes it not worth digging, or null when it is clear.
	 *
	 * <p>Scans the segment's own bounding box grown by {@code radius} and measures CHEBYSHEV
	 * distance back to the nearest segment cell, so the answer is exact for a cube and the scan is
	 * one pass rather than one per cell.
	 *
	 * <p>Reports the FIRST threat rather than all of them on purpose: the caller's only decision is
	 * whether to dig here, and one reason not to is as good as twenty for that. What the caller
	 * does want is to be able to say WHY in one line, which {@link Threat#describe} is for.
	 */
	static Threat scan(Cells w, Collection<BlockPos> segment, int radius) {
		if (segment.isEmpty()) return null;
		int x0 = Integer.MAX_VALUE, y0 = Integer.MAX_VALUE, z0 = Integer.MAX_VALUE;
		int x1 = Integer.MIN_VALUE, y1 = Integer.MIN_VALUE, z1 = Integer.MIN_VALUE;
		for (BlockPos p : segment) {
			x0 = Math.min(x0, p.getX()); x1 = Math.max(x1, p.getX());
			y0 = Math.min(y0, p.getY()); y1 = Math.max(y1, p.getY());
			z0 = Math.min(z0, p.getZ()); z1 = Math.max(z1, p.getZ());
		}
		for (int x = x0 - radius; x <= x1 + radius; x++) {
			for (int y = y0 - radius; y <= y1 + radius; y++) {
				for (int z = z0 - radius; z <= z1 + radius; z++) {
					String name = w.at(x, y, z);
					boolean unseen = name == null;
					if (!unseen && !isLava(name)) continue;
					if (!within(segment, x, y, z, radius)) continue;
					return new Threat(new BlockPos(x, y, z), unseen ? Kind.UNSEEN : Kind.LAVA_SEEN);
				}
			}
		}
		// Checked last and separately: a falling block is only a hazard over a cell we are actually
		// going to take, never merely near one.
		for (BlockPos p : segment) {
			if (unstableAbove(w, p)) return new Threat(p, Kind.FALLING);
		}
		return null;
	}

	/** Chebyshev distance from (x,y,z) to the nearest cell of the segment, against a radius. */
	private static boolean within(Collection<BlockPos> segment, int x, int y, int z, int radius) {
		for (BlockPos p : segment) {
			if (Math.abs(p.getX() - x) <= radius
				&& Math.abs(p.getY() - y) <= radius
				&& Math.abs(p.getZ() - z) <= radius) return true;
		}
		return false;
	}

	/**
	 * Is the body itself in trouble — lava within {@link #BODY_CLEAR} of where it is standing?
	 *
	 * <p>Both cells a player occupies, not just the feet: lava at head height burns you exactly as
	 * well, and a corridor dug at eye level is where it will be.
	 */
	static Threat aroundBody(Cells w, BlockPos feet) {
		java.util.List<BlockPos> body = java.util.List.of(feet, feet.above());
		Threat t = scan(w, body, BODY_CLEAR);
		// An unloaded chunk around the BODY is not a danger — it is the world still arriving, and
		// the body is standing in it. Only actual lava counts here.
		return t != null && t.kind() == Kind.LAVA_SEEN ? t : null;
	}
}
