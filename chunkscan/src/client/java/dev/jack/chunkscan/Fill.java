package dev.jack.chunkscan;

import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.world.level.Level;
import net.minecraft.core.Direction;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.SlabBlock;
import net.minecraft.world.level.block.StairBlock;
import net.minecraft.world.level.block.state.properties.Half;
import net.minecraft.world.level.block.state.properties.SlabType;
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
	 *
	 * <p>SPIRAL is a staircase winding round a central post, HELIX the same flight with the core
	 * left open; both come clockwise-ascending by default and with a CCW twin. They are the one
	 * family whose cells are not all the same block - see {@link #state}.
	 */
	enum Mode {
		SOLID, HOLLOW, WALLS, OUTLINE,
		BALL, SPHERE, CYLINDER, TUBE, DOME, DISC, RING,
		SPIRAL, SPIRAL_CCW, HELIX, HELIX_CCW;

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
				case "spiral", "stair", "stairs", "spiralstair", "spiralcw" -> SPIRAL;
				case "spiralccw" -> SPIRAL_CCW;
				case "helix", "openspiral", "helixcw" -> HELIX;
				case "helixccw" -> HELIX_CCW;
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
				// the full-block pitch; a slab material takes a gentler one, see state()
				case SPIRAL, SPIRAL_CCW, HELIX, HELIX_CCW -> Helix.of(this, sx, sz, false).wants(x, y, z);
			};
		}

		/** Is this one of the spiral-stair shapes, whose cells carry an ORIENTATION? */
		boolean isSpiral() {
			return this == SPIRAL || this == SPIRAL_CCW || this == HELIX || this == HELIX_CCW;
		}

		/**
		 * The block state this cell gets, or {@code null} when the cell is not part of the shape.
		 *
		 * <p>Every shape but the spirals answers with the material exactly as held. A spiral is the
		 * one shape whose cells are not interchangeable: a STAIR tread has to face the way the flight
		 * ascends (the rule pinned in {@code test_stairhead} - a flight that ascends toward D has
		 * every tread facing=D, and our renderer draws both directions identically), and a SLAB
		 * tread is split into a bottom half and a top half so each course carries two half-steps
		 * and the rise is 0.5, which is the only spiral a player can WALK up without jumping. Any
		 * other material - a full block, a fence, a wall - is placed as it is and the flight climbs a
		 * whole block per course, which is a jump staircase.
		 */
		BlockState state(BlockState material, int x, int y, int z, int sx, int sy, int sz) {
			if (!isSpiral()) return wants(x, y, z, sx, sy, sz) ? material : null;
			return Helix.of(this, sx, sz, material.getBlock() instanceof SlabBlock).state(material, x, y, z);
		}

		/**
		 * A spiral staircase inscribed in the box's plan: a post in the middle (SPIRAL) or open air
		 * there (HELIX), and one tread per course winding round it.
		 *
		 * <p><b>The tread is a SECTOR, and every cell of the annulus belongs to exactly one course
		 * per turn.</b> A cell's angle round the post picks its course modulo the courses-per-turn,
		 * so consecutive treads tile the ring with no gap and no overlap: the flight is connected
		 * at the rim by construction (each sector touches the next), and nothing near the post is
		 * dropped for being thinner than a cell - it simply falls to whichever course its angle
		 * says. Courses per turn is chosen so a tread is about two cells wide at the rim, which is
		 * the classic 5x5-round-a-post spiral (eight steps a turn) and scales with the box.
		 *
		 * <p>CW means clockwise ASCENDING, seen from above with north up - which in Minecraft's
		 * frame (x east, z south) is the direction of increasing atan2(z, x). Both spins are
		 * offered because a real staircase has a wall on one side and a rail on the other, and
		 * which side is which is not the tool's decision.
		 */
		static final class Helix {
			/** Target tread width at the rim, in cells; sets the courses per turn. */
			static final double RIM_TREAD = 2.0;
			/**
			 * ...and for a SLAB flight, whose every tread is two half-steps. Each half has to land
			 * at least one cell on a grid that samples the sector unevenly, or the rise between two
			 * courses is a whole block where a half was promised; three cells at the rim is the
			 * narrowest that walks without a jump on every box from 3 wide up.
			 */
			static final double RIM_TREAD_HALF = 3.0;
			static final int MIN_PER_TURN = 4;

			final double cx, cz, rx, rz;
			final int perTurn;
			final double step;          // radians a course advances
			final int spin;             // +1 clockwise from above, -1 counter
			final double coreHalf;      // Chebyshev half-size of the core the treads wind round
			final boolean post;         // is the core filled (a post) or left open (a well)

			static Helix of(Mode m, int sx, int sz, boolean halfSteps) {
				return new Helix(sx, sz, (m == SPIRAL || m == HELIX) ? 1 : -1, m == SPIRAL || m == SPIRAL_CCW,
					halfSteps);
			}

			private Helix(int sx, int sz, int spin, boolean post, boolean halfSteps) {
				cx = (sx - 1) / 2.0;
				cz = (sz - 1) / 2.0;
				rx = sx / 2.0;
				rz = sz / 2.0;
				this.spin = spin;
				double r = Math.sqrt(rx * rz);
				perTurn = Math.max(MIN_PER_TURN,
					(int) Math.round(2 * Math.PI * r / (halfSteps ? RIM_TREAD_HALF : RIM_TREAD)));
				step = 2 * Math.PI / perTurn;
				// A post a quarter of the radius, at least one cell, always centred: 1x1 up to a
				// 7-box, 3x3 from 9, 2x2 on an even 6-box. The +0.5 is what lets an EVEN box have a
				// post at all - its centre falls between cells, so no cell is at distance zero.
				coreHalf = Math.max(0, Math.round(Math.min(rx, rz) / 4.0 - 0.5)) + 0.5;
				this.post = post;
			}

			/** The core: the post's cells, or the open well the same size a HELIX winds round. */
			boolean inCore(int x, int z) {
				return Math.max(Math.abs(x - cx), Math.abs(z - cz)) <= coreHalf + 1e-9;
			}

			boolean inPost(int x, int z) {
				return post && inCore(x, z);
			}

			boolean inRing(int x, int z) {
				if (inCore(x, z)) return false;
				double dx = x - cx, dz = z - cz;
				return (dx * dx) / (rx * rx) + (dz * dz) / (rz * rz) <= 1.0;
			}

			/** Where this cell sits along the ascent, in courses: the integer part is its course mod perTurn. */
			double along(int x, int z) {
				double phi = Math.atan2(z - cz, x - cx);          // increases clockwise from above
				double t = spin * phi / step + 0.5;
				return t - Math.floor(t / perTurn) * perTurn;       // into [0, perTurn)
			}

			int courseOf(int x, int z) {
				return (int) Math.floor(along(x, z));
			}

			boolean wants(int x, int y, int z) {
				if (inCore(x, z)) return post;
				if (!inRing(x, z)) return false;
				return Math.floorMod(y - courseOf(x, z), perTurn) == 0;
			}

			BlockState state(BlockState material, int x, int y, int z) {
				if (!wants(x, y, z)) return null;
				if (inPost(x, z)) return material;
				if (material.getBlock() instanceof StairBlock) {
					return material.setValue(StairBlock.FACING, ascent(x, z)).setValue(StairBlock.HALF, Half.BOTTOM);
				}
				if (material.getBlock() instanceof SlabBlock) {
					// the half of the sector you reach FIRST is the lower step
					double frac = along(x, z) - Math.floor(along(x, z));
					return material.setValue(SlabBlock.TYPE, frac < 0.5 ? SlabType.BOTTOM : SlabType.TOP);
				}
				return material;
			}

			/** The cardinal nearest the tangent of ascent at this cell - a stair's FACING. */
			Direction ascent(int x, int z) {
				double phi = Math.atan2(z - cz, x - cx);
				double tx = -spin * Math.sin(phi), tz = spin * Math.cos(phi);
				if (Math.abs(tx) >= Math.abs(tz)) return tx > 0 ? Direction.EAST : Direction.WEST;
				return tz > 0 ? Direction.SOUTH : Direction.NORTH;
			}
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
					BlockState want = mode.state(material, x, y, z, sx, sy, sz);
					if (want == null) {
						outside++;
						continue;
					}
					BlockState cur = probe.at(min.getX() + x, min.getY() + y, min.getZ() + z);
					String name = BuiltInRegistries.BLOCK.getKey(cur.getBlock()).toString();
					if (Rules.isProtected(name)) {
						prot++;
						kinds.merge(Rules.shortName(name), 1, Integer::sum);
					} else if (cur == want) {
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

	/**
	 * The same walk again, this time emitting. Palette is {air, material} for every shape but the
	 * spirals, whose treads carry an orientation - a stair's facing, a slab's half - so the
	 * palette holds each state in order of first use. Index 1 is still the first state placed.
	 */
	static Capture capture(Probe probe, Plan p) {
		int sx = p.sizeX(), sy = p.sizeY(), sz = p.sizeZ();
		int[] ids = new int[sx * sy * sz];
		List<BlockState> palette = new ArrayList<>();
		palette.add(Blocks.AIR.defaultBlockState());          // index 0 is always air
		Map<BlockState, Integer> index = new LinkedHashMap<>();
		long placed = 0;
		for (int y = 0; y < sy; y++) {
			for (int z = 0; z < sz; z++) {
				for (int x = 0; x < sx; x++) {
					BlockState want = p.mode().state(p.material(), x, y, z, sx, sy, sz);
					if (want == null) continue;
					BlockState cur = probe.at(p.min().getX() + x, p.min().getY() + y, p.min().getZ() + z);
					String name = BuiltInRegistries.BLOCK.getKey(cur.getBlock()).toString();
					if (Rules.isProtected(name) || cur == want) continue;   // stays air: no work here
					if (p.replaceOnly() != null
						&& !Rules.shortName(name).equals(Rules.shortName(p.replaceOnly()))) continue;
					ids[(y * sz + z) * sx + x] = index.computeIfAbsent(want, k -> {
						palette.add(k);
						return palette.size() - 1;
					});
					placed++;
				}
			}
		}
		if (palette.size() == 1) palette.add(p.material());
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
					BlockState want = p.mode().state(p.material(), x, y, z, sx, sy, sz);
					if (want == null) continue;
					int wx = p.min().getX() + x, wy = p.min().getY() + y, wz = p.min().getZ() + z;
					BlockState cur = probe.at(wx, wy, wz);
					String name = BuiltInRegistries.BLOCK.getKey(cur.getBlock()).toString();
					if (Rules.isProtected(name) || cur == want) continue;   // the fill skips it
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
