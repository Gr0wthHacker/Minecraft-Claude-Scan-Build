package dev.jack.chunkscan;

import net.minecraft.core.BlockPos;
import net.minecraft.tags.FluidTags;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.FallingBlock;
import net.minecraft.world.level.block.state.BlockState;

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
 *   <li><b>Source and flowing lava are ONE question, asked of the game.</b> {@link FluidTags#LAVA}
 *       holds both; a name test would have to know that flowing lava is still {@code Blocks.LAVA}
 *       with a {@code level} on it. It is also the reason this is not a substring match:
 *       {@link Rules#isProtected} matches substrings on purpose — {@code gray_wool} is protected
 *       because {@code wool} is in the list — and the same trick here makes {@code lava_cauldron},
 *       a decoration, read as lethal and refuse every corridor near somebody's brewing room.</li>
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

	/** The block name, for the callers that only have one. See {@link #isLava(BlockState)}. */
	static final String LAVA = "lava";

	/** How far from a planned corridor lava has to be before the corridor is worth digging. */
	static final int SEGMENT_CLEAR = 3;

	/**
	 * ...and how far from the BODY, which is a tighter question and a much cheaper one.
	 *
	 * <p>One, so {@link #aroundBody} is the six faces of each of the two cells a player occupies —
	 * twelve lookups. It was a radius-2 box, which is 150 cells of {@code getBlockState} EVERY TICK
	 * for a question whose honest answer is "is there lava against me": at range 1 lava sets you
	 * alight, and past it the corridor's own clearance is what keeps the body away from it.
	 */
	static final int BODY_CLEAR = 1;

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
	 * A world you can ask the three questions this guard actually has, so the geometry is testable
	 * with no client anywhere near it — the shape {@link Nav.Passable} and {@link Burial.Solid}
	 * already use here.
	 *
	 * <p>Three booleans rather than a block name, and that is not tidiness: the scan runs over
	 * several hundred cells every replan and the body check runs every tick, so a registry lookup
	 * and a string comparison per cell is the per-cell cost this project has been bitten by three
	 * times. Nothing here ever needed to know WHICH block it was looking at.
	 */
	interface Cells {
		/** Is this cell in a chunk we can see at all? */
		boolean loaded(int x, int y, int z);

		/** Is it lava — source or flowing? */
		boolean lava(int x, int y, int z);

		/** Does it fall when what is under it goes? */
		boolean falls(int x, int y, int z);
	}

	/** The live world. */
	static Cells of(Level level) {
		BlockPos.MutableBlockPos at = new BlockPos.MutableBlockPos();
		return new Cells() {
			@Override public boolean loaded(int x, int y, int z) {
				return level.isLoaded(at.set(x, y, z));
			}

			@Override public boolean lava(int x, int y, int z) {
				at.set(x, y, z);
				return level.isLoaded(at) && isLava(level.getBlockState(at));
			}

			@Override public boolean falls(int x, int y, int z) {
				at.set(x, y, z);
				return level.isLoaded(at) && level.getBlockState(at).getBlock() instanceof FallingBlock;
			}
		};
	}

	/**
	 * ONE SOURCE for what lava is, asked of the state.
	 *
	 * <p>{@link VoidRisk} asks it too, and has to: it walks down looking for something that will
	 * catch a falling item, and lava neither catches one nor {@code blocksMotion}, so before this
	 * existed it walked straight past a lava lake to the bedrock underneath and called that a floor.
	 */
	static boolean isLava(BlockState st) {
		return st.getFluidState().is(FluidTags.LAVA);
	}

	/** The same fact for a caller that only has a name. Exact — see the class note. */
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
		if (w.lava(p.getX(), p.getY(), p.getZ())) return true;
		for (net.minecraft.core.Direction d : net.minecraft.core.Direction.values()) {
			BlockPos q = p.relative(d);
			if (w.lava(q.getX(), q.getY(), q.getZ())) return true;
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
					boolean unseen = !w.loaded(x, y, z);
					if (!unseen && !w.lava(x, y, z)) continue;
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
	 * Is the body itself in trouble — lava against where it is standing?
	 *
	 * <p>Both cells a player occupies, not just the feet: lava at head height burns you exactly as
	 * well, and a corridor dug at eye level is where it will be.
	 *
	 * <p>An unloaded cell is deliberately NOT a threat here. Around the corridor it means "we
	 * cannot see what we are about to open"; around the BODY it means the world is still arriving
	 * and the body is already standing in it, which is not a reason to abandon a trip.
	 */
	static Threat aroundBody(Cells w, BlockPos feet) {
		for (BlockPos cell : new BlockPos[]{feet, feet.above()}) {
			if (w.lava(cell.getX(), cell.getY(), cell.getZ())) return new Threat(cell, Kind.LAVA_SEEN);
			for (net.minecraft.core.Direction d : net.minecraft.core.Direction.values()) {
				BlockPos q = cell.relative(d);
				if (w.lava(q.getX(), q.getY(), q.getZ())) return new Threat(q, Kind.LAVA_SEEN);
			}
		}
		return null;
	}
}
