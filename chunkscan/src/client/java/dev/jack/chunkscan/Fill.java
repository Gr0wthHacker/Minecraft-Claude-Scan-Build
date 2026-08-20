package dev.jack.chunkscan;

import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Turn the wand's box into a one-material {@link Capture}, so the existing writer, sidecar and
 * Litematica bridge can carry it the rest of the way. Nothing here places a block in the world —
 * a client mod cannot, and should not: the schematic goes to Litematica and the PRINTER builds it,
 * which is also what makes the whole thing undoable.
 *
 * <p>Two gates, and they exist because the box is drawn in a world people are using:
 *
 * <ul>
 *   <li><b>Protected cells are skipped, never covered.</b> A fill that swallows a hopper is not a
 *       fill, it is a loss. The safe set is {@link Rules}, which is generated from the same
 *       {@code protect.MECHANISM} every Python generator consults — a block that looks like fabric
 *       may be a sculk sensor's silencer.</li>
 *   <li><b>Cells that already hold the material are skipped.</b> Designs in this project are
 *       REMAINING WORK, so a box half-built already should cost half as much, and the block count
 *       you are told should be the count you actually have to place.</li>
 * </ul>
 *
 * <p>Skipped cells come out as air in the schematic, which is exactly right: a litematic cannot
 * express removal, so air means "nothing to do here" and the printer passes over it.
 */
final class Fill {
	/**
	 * What the box looks like, one cell at a time. The world is behind this in game and a fixture
	 * is behind it in the tests — {@code Level} itself cannot be constructed off a client.
	 */
	@FunctionalInterface
	interface Probe {
		BlockState at(int x, int y, int z);
	}

	/**
	 * Which cells of the box are wanted.
	 *
	 * <p>SOLID is the whole box. HOLLOW is its shell — a room, rather than a block of stone you
	 * then have to hollow out by hand, which on a survival server is the expensive half. WALLS is
	 * the four sides without floor or ceiling, which is what you want when the floor is already
	 * there. OUTLINE is the twelve edges: a frame, and the cheapest way to see a volume before
	 * committing 20,000 blocks to it.
	 */
	enum Mode {
		SOLID, HOLLOW, WALLS, OUTLINE,
		BALL, SPHERE, CYLINDER, TUBE, DOME, DISC, RING;

		static Mode of(String s) {
			if (s == null || s.isBlank()) return SOLID;
			return switch (s.trim().toLowerCase(java.util.Locale.ROOT)) {
				case "hollow", "shell" -> HOLLOW;
				case "walls", "wall" -> WALLS;
				case "outline", "frame", "edges" -> OUTLINE;
				case "ball", "solidsphere" -> BALL;
				case "sphere", "orb" -> SPHERE;
				case "cylinder", "column", "pillar" -> CYLINDER;
				case "tube", "pipe", "hollowcylinder" -> TUBE;
				case "dome", "mound" -> DOME;
				case "disc", "disk", "circle" -> DISC;
				case "ring", "hoop" -> RING;
				default -> SOLID;
			};
		}

		/** Does the shape ignore the box's height and lie in one course? */
		boolean isFlat() {
			return this == DISC || this == RING;
		}

		/**
		 * Is this cell part of the shape? Coordinates are offsets from the box's minimum corner.
		 *
		 * <p><b>THE BOX IS THE BOUNDING BOX, not a radius.</b> A sphere in a 21x21x21 selection has
		 * radius 10; in a 21x11x21 it is an ellipsoid, squashed, which is more often what a build
		 * actually wants than a true sphere. Mark the box you want the shape to fill.
		 */
		boolean wants(int x, int y, int z, int sx, int sy, int sz) {
			boolean ex = x == 0 || x == sx - 1;
			boolean ey = y == 0 || y == sy - 1;
			boolean ez = z == 0 || z == sz - 1;
			return switch (this) {
				case SOLID -> true;
				case HOLLOW -> ex || ey || ez;
				case WALLS -> ex || ez;
				// two of the three extremes: that is what an edge of a box IS
				case OUTLINE -> (ex ? 1 : 0) + (ey ? 1 : 0) + (ez ? 1 : 0) >= 2;

				case BALL -> inEllipsoid(x, y, z, sx, sy, sz);
				case SPHERE -> shellOf(this, x, y, z, sx, sy, sz);
				case DOME -> inDome(x, y, z, sx, sy, sz);
				case CYLINDER -> inDisc(x, z, sx, sz);
				case TUBE -> shellOf(this, x, y, z, sx, sy, sz);
				// FLAT shapes ignore the box height and lie on its bottom course - a disc marked in
				// a tall box is a disc, not a cylinder. Use `cylinder` when you want the height.
				case DISC -> y == 0 && inDisc(x, z, sx, sz);
				case RING -> y == 0 && shellOf(this, x, y, z, sx, sy, sz);
			};
		}

		/**
		 * Inside the ellipsoid inscribed in the box.
		 *
		 * <p>The half-axes are sx/2 rather than (sx-1)/2, which is the difference between a round
		 * ball and one with its poles shaved flat: the extreme cell sits at (sx-1)/2 from centre, so
		 * dividing by the larger radius keeps it inside. This is the voxel-sphere rounding everyone
		 * gets wrong once.
		 */
		private static boolean inEllipsoid(int x, int y, int z, int sx, int sy, int sz) {
			double dx = x - (sx - 1) / 2.0, dy = y - (sy - 1) / 2.0, dz = z - (sz - 1) / 2.0;
			double rx = sx / 2.0, ry = sy / 2.0, rz = sz / 2.0;
			return (dx * dx) / (rx * rx) + (dy * dy) / (ry * ry) + (dz * dz) / (rz * rz) <= 1.0;
		}

		/**
		 * The upper half of an ellipsoid whose EQUATOR IS THE BOX FLOOR.
		 *
		 * <p>Not the top half of an ellipsoid inscribed in the box - that gives a dome standing on a
		 * circle the size of its own waist, floating clear of the rim. The half-height is the FULL
		 * box height, and y is measured from 0, so the base course is the whole circle and the
		 * crown closes in. A dome that does not meet the ground it sits on is a dome you then have
		 * to hand-fill a ring under.
		 */
		private static boolean inDome(int x, int y, int z, int sx, int sy, int sz) {
			double dx = x - (sx - 1) / 2.0, dz = z - (sz - 1) / 2.0;
			double rx = sx / 2.0, ry = sy, rz = sz / 2.0;
			return (dx * dx) / (rx * rx) + (y * y) / (ry * ry) + (dz * dz) / (rz * rz) <= 1.0;
		}

		/** Inside the ellipse inscribed in the box's PLAN - the cylinder and disc cross-section. */
		private static boolean inDisc(int x, int z, int sx, int sz) {
			double dx = x - (sx - 1) / 2.0, dz = z - (sz - 1) / 2.0;
			double rx = sx / 2.0, rz = sz / 2.0;
			return (dx * dx) / (rx * rx) + (dz * dz) / (rz * rz) <= 1.0;
		}

		/**
		 * The one-cell skin of a solid shape: inside it, with at least one neighbour outside.
		 *
		 * <p>Not a radius band. A band of constant thickness in the EQUATION gives a shell that is
		 * fat at the poles and thin at the equator - or the reverse - because the gradient of an
		 * ellipsoid is not constant. Asking which cells have an exposed face gives an even skin by
		 * construction, and it is the same rule the box HOLLOW uses one line up.
		 */
		private static boolean shellOf(Mode m, int x, int y, int z, int sx, int sy, int sz) {
			if (!solidPart(m, x, y, z, sx, sy, sz)) return false;
			// TUBE and RING are open-ended on purpose: a tube with caps is a hollow cylinder, and
			// what you reach for `tube` to build is a chimney or a well, which has neither.
			int[][] around = (m == TUBE || m == RING)
				? new int[][]{{1, 0, 0}, {-1, 0, 0}, {0, 0, 1}, {0, 0, -1}}
				: new int[][]{{1, 0, 0}, {-1, 0, 0}, {0, 1, 0}, {0, -1, 0}, {0, 0, 1}, {0, 0, -1}};
			for (int[] d : around) {
				if (!solidPart(m, x + d[0], y + d[1], z + d[2], sx, sy, sz)) return true;
			}
			return false;
		}

		/** The SOLID shape a hollow one is the skin of. */
		private static boolean solidPart(Mode m, int x, int y, int z, int sx, int sy, int sz) {
			if (x < 0 || y < 0 || z < 0 || x >= sx || y >= sy || z >= sz) return false;
			return switch (m) {
				case SPHERE -> inEllipsoid(x, y, z, sx, sy, sz);
				case TUBE -> inDisc(x, z, sx, sz);
				case RING -> inDisc(x, z, sx, sz);
				default -> true;
			};
		}
	}

	/** Report of a planned fill; nothing is written until {@link #capture} is asked for. */
	record Plan(BlockPos min, BlockPos max, BlockState material, Mode mode, String replaceOnly,
	            int place, int skipProtected, int already, long volume, int outsideShape,
	            Map<String, Integer> protectedKinds) {

		int sizeX() { return max.getX() - min.getX() + 1; }

		int sizeY() { return max.getY() - min.getY() + 1; }

		int sizeZ() { return max.getZ() - min.getZ() + 1; }

		String materialName() {
			return BuiltInRegistries.BLOCK.getKey(material.getBlock()).toString();
		}
	}

	private Fill() {}

	static Probe of(Level level) {
		BlockPos.MutableBlockPos c = new BlockPos.MutableBlockPos();
		return (x, y, z) -> level.getBlockState(c.set(x, y, z));
	}

	/**
	 * Walk the box once and decide, per cell, whether it is work. Cheap enough to run on every
	 * {@code /cscan fill}, so the numbers reported are the numbers that get written.
	 */
	static Plan plan(Probe probe, BlockPos a, BlockPos b, BlockState material) {
		return plan(probe, a, b, material, Mode.SOLID, null);
	}

	/**
	 * Walk the box once and decide, per cell, whether it is work. Cheap enough to run on every
	 * {@code /cscan fill}, so the numbers reported are the numbers that get written.
	 *
	 * @param replaceOnly when set, only cells currently holding THIS block are touched — the
	 *                    in-game form of the deckfloor's wood reclaim.
	 */
	static Plan plan(Probe probe, BlockPos a, BlockPos b, BlockState material, Mode mode, String replaceOnly) {
		BlockPos min = new BlockPos(Math.min(a.getX(), b.getX()), Math.min(a.getY(), b.getY()), Math.min(a.getZ(), b.getZ()));
		BlockPos max = new BlockPos(Math.max(a.getX(), b.getX()), Math.max(a.getY(), b.getY()), Math.max(a.getZ(), b.getZ()));
		int sx = max.getX() - min.getX() + 1, sy = max.getY() - min.getY() + 1, sz = max.getZ() - min.getZ() + 1;
		int place = 0, prot = 0, already = 0, outside = 0;
		Map<String, Integer> kinds = new LinkedHashMap<>();
		for (int y = 0; y < sy; y++) {
			for (int z = 0; z < sz; z++) {
				for (int x = 0; x < sx; x++) {
					if (!mode.wants(x, y, z, sx, sy, sz)) {
						outside++;
						continue;
					}
					BlockState cur = probe.at(min.getX() + x, min.getY() + y, min.getZ() + z);
					String name = BuiltInRegistries.BLOCK.getKey(cur.getBlock()).toString();
					if (Rules.isProtected(name)) {
						prot++;
						kinds.merge(Rules.shortName(name), 1, Integer::sum);
					} else if (cur == material) {
						already++;
					} else if (replaceOnly != null && !Rules.shortName(name).equals(Rules.shortName(replaceOnly))) {
						outside++;                    // not the block we came to replace
					} else {
						place++;
					}
				}
			}
		}
		return new Plan(min, max, material, mode, replaceOnly, place, prot, already,
			(long) sx * sy * sz, outside, kinds);
	}

	/** The same walk again, this time emitting. Palette is always {air, material}. */
	static Capture capture(Probe probe, Plan p) {
		int sx = p.sizeX(), sy = p.sizeY(), sz = p.sizeZ();
		int[] ids = new int[sx * sy * sz];
		List<BlockState> palette = new ArrayList<>();
		palette.add(Blocks.AIR.defaultBlockState());          // index 0 is always air
		palette.add(p.material());
		long placed = 0;
		for (int y = 0; y < sy; y++) {
			for (int z = 0; z < sz; z++) {
				for (int x = 0; x < sx; x++) {
					if (!p.mode().wants(x, y, z, sx, sy, sz)) continue;
					BlockState cur = probe.at(p.min().getX() + x, p.min().getY() + y, p.min().getZ() + z);
					String name = BuiltInRegistries.BLOCK.getKey(cur.getBlock()).toString();
					if (Rules.isProtected(name) || cur == p.material()) continue;   // stays air: no work here
					if (p.replaceOnly() != null
						&& !Rules.shortName(name).equals(Rules.shortName(p.replaceOnly()))) continue;
					ids[(y * sz + z) * sx + x] = 1;
					placed++;
				}
			}
		}
		return new Capture(p.min().getX(), p.min().getY(), p.min().getZ(), sx, sy, sz,
			ids, palette, List.of(), List.of(), placed, List.of(), List.of());
	}

	/**
	 * The box as it stands TODAY, restricted to the cells the fill is about to change — an undo.
	 *
	 * <p>It cannot be a straight inverse, because a litematic cannot express removal. Where the fill
	 * covers an existing block, that block goes into the schematic and re-placing it restores the
	 * cell. Where the fill puts something into AIR, there is nothing to record: those cells go into
	 * the sidecar's `dig` list instead, which is what `/cscan dig` already reads. Undo is therefore
	 * "place these back, break those" — and both halves are needed or the undo half-works.
	 */
	static Capture undoCapture(Probe probe, Plan p, List<int[]> dig) {
		int sx = p.sizeX(), sy = p.sizeY(), sz = p.sizeZ();
		int[] ids = new int[sx * sy * sz];
		List<BlockState> palette = new ArrayList<>();
		palette.add(Blocks.AIR.defaultBlockState());
		Map<BlockState, Integer> index = new LinkedHashMap<>();
		long kept = 0;
		for (int y = 0; y < sy; y++) {
			for (int z = 0; z < sz; z++) {
				for (int x = 0; x < sx; x++) {
					if (!p.mode().wants(x, y, z, sx, sy, sz)) continue;
					int wx = p.min().getX() + x, wy = p.min().getY() + y, wz = p.min().getZ() + z;
					BlockState cur = probe.at(wx, wy, wz);
					String name = BuiltInRegistries.BLOCK.getKey(cur.getBlock()).toString();
					if (Rules.isProtected(name) || cur == p.material()) continue;   // the fill skips it
					if (p.replaceOnly() != null
						&& !Rules.shortName(name).equals(Rules.shortName(p.replaceOnly()))) continue;
					if (cur.isAir()) {
						dig.add(new int[]{wx, wy, wz});          // the fill CREATES this one
						continue;
					}
					int id = index.computeIfAbsent(cur, k -> {
						palette.add(k);
						return palette.size() - 1;
					});
					ids[(y * sz + z) * sx + x] = id;
					kept++;
				}
			}
		}
		return new Capture(p.min().getX(), p.min().getY(), p.min().getZ(), sx, sy, sz,
			ids, palette, List.of(), List.of(), kept, List.of(), List.of());
	}

	/** The protected kinds that were skipped, commonest first, for one line of chat. */
	static String skipSummary(Plan p) {
		if (p.protectedKinds().isEmpty()) return "";
		return p.protectedKinds().entrySet().stream()
			.sorted((l, r) -> Integer.compare(r.getValue(), l.getValue()))
			.limit(5)
			.map(e -> e.getValue() + "x " + e.getKey())
			.reduce((l, r) -> l + ", " + r).orElse("");
	}
}
