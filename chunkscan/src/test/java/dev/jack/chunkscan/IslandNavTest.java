package dev.jack.chunkscan;

import net.minecraft.core.BlockPos;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

import java.io.DataInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Random;
import java.util.Set;
import java.util.zip.GZIPInputStream;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Routing over THE ISLAND, rather than over worlds I invented.
 *
 * <p>{@link NavTest}'s fixtures are a wall with a hole in it, a tunnel, an L-bend — and they only
 * ever test the cases someone thought of. This is where the loop actually runs, and it has the
 * variance a hand-built world does not: chests recessed into walls, three-wide necks, a deck of
 * slabs and stairs and hoppers, vines hanging in open air, a plate with twenty-five interior holes,
 * a machine room, rails, and 240 blocks of vertical.
 *
 * <p>The fixture is the capture's own geometry, exported by {@code tools/export_navfixture.py} —
 * 103x121x103 at the origin lock, 41,455 cells of it solid. Regenerate it after a rescan; the tests
 * below derive everything they assert from the fixture itself, so a new capture changes the numbers
 * and not the expectations.
 *
 * <p><b>Outside the box is passable</b>, exactly as an unloaded chunk is to the real predicate. That
 * is not a convenience: it is the same rule, and it means these tests exercise the open-sky cases
 * (which the island is mostly surrounded by) as well as the interior.
 */
class IslandNavTest {
	private static byte[] bits;
	private static int ox, oy, oz, sx, sy, sz;

	@BeforeAll
	static void load() throws IOException {
		try (InputStream in = IslandNavTest.class.getResourceAsStream("/island_nav.bin.gz")) {
			assertNotNull(in, "no island fixture — run: python tools/export_navfixture.py");
			DataInputStream d = new DataInputStream(new GZIPInputStream(in));
			byte[] magic = new byte[8];
			d.readFully(magic);
			ox = d.readInt();
			oy = d.readInt();
			oz = d.readInt();
			sx = d.readInt();
			sy = d.readInt();
			sz = d.readInt();
			bits = d.readAllBytes();
		}
	}

	/** Does this world cell stop a player? Outside the capture reads as open, like an unloaded chunk. */
	private static boolean solid(int x, int y, int z) {
		int lx = x - ox, ly = y - oy, lz = z - oz;
		if (lx < 0 || ly < 0 || lz < 0 || lx >= sx || ly >= sy || lz >= sz) return false;
		int i = (ly * sz + lz) * sx + lx;
		return (bits[i >> 3] & (1 << (7 - (i & 7)))) != 0;
	}

	/** The flying predicate, built exactly as {@link Nav#of} builds it from a Level. */
	private static final Nav.Passable FREE =
		(x, y, z) -> !solid(x, y, z) && !solid(x, y + 1, z);

	/** The walking one, as {@link Nav#standable} builds it. */
	private static final Nav.Passable STAND = (x, y, z) ->
		!solid(x, y, z) && !solid(x, y + 1, z) && (solid(x, y - 1, z) || solid(x, y - 2, z));

	private static BlockPos world(int lx, int ly, int lz) {
		return new BlockPos(ox + lx, oy + ly, oz + lz);
	}

	// ---------------------------------------------------------------- the fixture itself

	@Test
	void theFixtureLooksLikeTheIsland() {
		// A broken export would make every test below pass over an empty box. This is the guard that
		// says the ground is really there — derived, so a rescan moves it without breaking anything.
		int solidCells = 0;
		for (byte b : bits) solidCells += Integer.bitCount(b & 0xFF);
		double fraction = (double) solidCells / ((long) sx * sy * sz);
		assertTrue(fraction > 0.005 && fraction < 0.5,
			"the island is " + Math.round(fraction * 1000) / 10.0 + "% solid, which is not an island");
		assertTrue(sy > 100, "the capture is too short to hold the deck and the plate");
	}

	// ---------------------------------------------------------------- routing

	/** Cells you could actually be in, sampled from the capture rather than from a guess. */
	private static List<BlockPos> openCells(long seed, int want) {
		Random r = new Random(seed);
		List<BlockPos> out = new ArrayList<>();
		for (int guard = 0; guard < 200_000 && out.size() < want; guard++) {
			int lx = r.nextInt(sx), ly = r.nextInt(sy), lz = r.nextInt(sz);
			BlockPos p = world(lx, ly, lz);
			if (FREE.at(p.getX(), p.getY(), p.getZ())) out.add(p);
		}
		return out;
	}

	/**
	 * Open cells that are actually NEAR something.
	 *
	 * <p>Uniform sampling over this capture is mostly a test of empty sky: it spans Y-64..270 and is
	 * 2% solid, so two random open cells usually have nothing at all between them and every router
	 * passes. The hard cases are all within a few blocks of a surface — under the deck, inside the
	 * lowland, against the plate — so sample there.
	 */
	private static List<BlockPos> nearTerrain(long seed, int want) {
		Random r = new Random(seed);
		List<BlockPos> out = new ArrayList<>();
		for (int guard = 0; guard < 400_000 && out.size() < want; guard++) {
			int lx = r.nextInt(sx), ly = r.nextInt(sy), lz = r.nextInt(sz);
			BlockPos p = world(lx, ly, lz);
			if (!FREE.at(p.getX(), p.getY(), p.getZ())) continue;
			if (openNear(p, 3) == null) continue;                // control: something is around
			boolean close = false;
			for (int d = 1; d <= 3 && !close; d++) {
				for (int[] o : new int[][]{{d, 0, 0}, {-d, 0, 0}, {0, d, 0}, {0, -d, 0}, {0, 0, d},
					{0, 0, -d}}) {
					if (solid(p.getX() + o[0], p.getY() + o[1], p.getZ() + o[2])) close = true;
				}
			}
			if (close) out.add(p);
		}
		return out;
	}

	@Test
	void routesThroughTheBUILTPartsOfTheIslandAreLegal() {
		// The same property as below, sampled where the island actually is. Uniform sampling over a
		// capture that is 98% air mostly proves that open sky is open.
		List<BlockPos> spots = nearTerrain(4242L, 90);
		assertTrue(spots.size() > 40, "found only " + spots.size() + " cells near terrain");
		int routed = 0;
		for (int i = 0; i + 1 < spots.size(); i += 2) {
			BlockPos a = spots.get(i), b = spots.get(i + 1);
			if (a.distSqr(b) > (double) Nav.MAX_RANGE * Nav.MAX_RANGE) continue;
			List<BlockPos> raw = Nav.route(FREE, a, b);
			if (raw.isEmpty()) continue;
			routed++;
			BlockPos prev = a;
			for (BlockPos c : Nav.loosen(FREE, a, Nav.simplify(FREE, a, raw))) {
				assertTrue(Nav.clear(FREE, prev, c),
					"the leg " + prev + " -> " + c + " passes through the island");
				prev = c;
			}
		}
		assertTrue(routed > 10, "only " + routed + " routes near terrain were found at all");
	}

	@Test
	void theDeckCanBeRoutedDownToTheLowland() {
		// The flight that crashed. 150-odd blocks straight down through the island's own body, which
		// is the longest route the loop actually asks for and the one MAX_RANGE was raised for.
		BlockPos deck = lowestOpenAbove(194);
		BlockPos low = lowestOpenAbove(42);
		// ASSERTED, not skipped. A test that returns early when it cannot find its own endpoints
		// proves nothing and reports success, which is how a suite stops meaning anything.
		assertNotNull(deck, "no open cell found at deck height in the capture");
		assertNotNull(low, "no open cell found at lowland height — is the capture the plate-only one?");
		assertTrue(Math.sqrt(deck.distSqr(low)) < Nav.MAX_RANGE,
			"deck to lowland is outside the range cap: " + Math.sqrt(deck.distSqr(low)));
		List<BlockPos> path = Nav.route(FREE, deck, low);
		assertFalse(path.isEmpty(), "no route from the deck down to the lowland");
		BlockPos prev = deck;
		for (BlockPos c : path) {
			assertTrue(FREE.at(c.getX(), c.getY(), c.getZ()), c + " is inside the island");
			prev = c;
		}
		assertTrue(within(prev, low, Nav.GOAL_SLACK), "ended somewhere other than the lowland");
	}

	/** An open cell at about this height, near the middle of the capture. */
	private static BlockPos lowestOpenAbove(int y) {
		int ly = y - oy;
		if (ly < 0 || ly >= sy) return null;
		for (int spread = 0; spread < Math.max(sx, sz); spread++) {
			for (int lx = Math.max(0, sx / 2 - spread); lx < Math.min(sx, sx / 2 + spread + 1); lx++) {
				for (int lz = Math.max(0, sz / 2 - spread);
					lz < Math.min(sz, sz / 2 + spread + 1); lz++) {
					BlockPos p = world(lx, ly, lz);
					if (FREE.at(p.getX(), p.getY(), p.getZ()) && openNear(p, 6) != null
						&& solidWithin(p, 8)) return p;
				}
			}
		}
		return null;
	}

	/** Is there anything solid within `d`? Keeps the endpoints on the island rather than in sky. */
	private static boolean solidWithin(BlockPos p, int d) {
		for (int i = 1; i <= d; i++) {
			if (solid(p.getX(), p.getY() - i, p.getZ())) return true;
		}
		return false;
	}

	@Test
	void everyRouteItReturnsOverTheIslandIsLegal() {
		// The property that matters most and cannot be eyeballed: whatever it hands back, the
		// autopilot will fly. Every waypoint has to be somewhere you can be, and every LEG between
		// them somewhere you can pass — which is a stronger claim than the waypoints alone, and the
		// one that "it tries to fly through walls" was about.
		List<BlockPos> spots = openCells(20260820L, 120);
		int routed = 0;
		for (int i = 0; i + 1 < spots.size(); i += 2) {
			BlockPos a = spots.get(i), b = spots.get(i + 1);
			if (a.distSqr(b) > (double) Nav.MAX_RANGE * Nav.MAX_RANGE) continue;
			List<BlockPos> path = Nav.route(FREE, a, b);
			if (path.isEmpty()) continue;
			routed++;
			BlockPos prev = a;
			for (BlockPos c : path) {
				assertTrue(FREE.at(c.getX(), c.getY(), c.getZ()),
					"waypoint " + c + " is inside the island (" + a + " -> " + b + ")");
				assertTrue(Nav.clear(FREE, prev, c),
					"the leg " + prev + " -> " + c + " passes through the island");
				prev = c;
			}
			assertTrue(within(prev, b, Nav.GOAL_SLACK), "ended at " + prev + " rather than at " + b);
		}
		assertTrue(routed > 20, "only " + routed + " of the sampled pairs routed at all");
	}

	@Test
	void theSimplifiedAndLoosenedRouteIsStillLegal() {
		// What the autopilot flies is route -> simplify -> loosen, and each stage can undo the last
		// one's care. Over real terrain, where every corner is a different shape.
		List<BlockPos> spots = openCells(99L, 80);
		for (int i = 0; i + 1 < spots.size(); i += 2) {
			BlockPos a = spots.get(i), b = spots.get(i + 1);
			if (a.distSqr(b) > (double) Nav.MAX_RANGE * Nav.MAX_RANGE) continue;
			List<BlockPos> raw = Nav.route(FREE, a, b);
			if (raw.isEmpty()) continue;
			BlockPos prev = a;
			for (BlockPos c : Nav.loosen(FREE, a, Nav.simplify(FREE, a, raw))) {
				assertTrue(Nav.clear(FREE, prev, c),
					"simplify/loosen straightened " + prev + " -> " + c + " through the island");
				prev = c;
			}
		}
	}

	@Test
	void placesThatAreConnectedAlwaysGetARoute() {
		// The hard direction. "It returned nothing" is the failure that flies you into terrain, and
		// on real geometry it is the one that actually happens — a budget runs out, a goal is solid,
		// a corridor is too tight. So: flood a region to find out what is GENUINELY connected under
		// the same predicate the router uses, then demand a route between pairs of it.
		BlockPos seed = interiorSeed();
		List<BlockPos> reach = flood(seed, 20000);
		assertTrue(reach.size() > 500, "the interior flood found only " + reach.size() + " cells");

		Random r = new Random(4242);
		int checked = 0;
		for (int i = 0; i < 60; i++) {
			BlockPos a = reach.get(r.nextInt(reach.size()));
			BlockPos b = reach.get(r.nextInt(reach.size()));
			if (a.equals(b) || a.distSqr(b) > (double) Nav.MAX_RANGE * Nav.MAX_RANGE) continue;
			checked++;
			assertFalse(Nav.route(FREE, a, b).isEmpty(),
				"no route between two connected places: " + a + " -> " + b
					+ " (" + Math.round(Math.sqrt(a.distSqr(b))) + " blocks apart)");
		}
		assertTrue(checked > 30, "only " + checked + " pairs were actually tested");
	}

	@Test
	void aChestSizedTargetInTheGeometryIsStillReachable() {
		// Every fetch target is a container's own cell, and on this island containers are recessed
		// into walls, tucked under the deck and stood against rock. Sample real SOLID cells that
		// have somewhere open beside them and demand the router still finish next to them.
		Random r = new Random(7);
		int tried = 0;
		for (int guard = 0; guard < 60_000 && tried < 40; guard++) {
			int lx = r.nextInt(sx), ly = r.nextInt(sy), lz = r.nextInt(sz);
			BlockPos target = world(lx, ly, lz);
			if (!solid(target.getX(), target.getY(), target.getZ())) continue;
			if (Nav.reachable(FREE, target) == null) continue;      // genuinely buried: fair enough
			BlockPos from = openNear(target, 30);
			if (from == null) continue;
			tried++;
			List<BlockPos> path = Nav.route(FREE, from, target);
			if (path.isEmpty()) continue;                            // may be sealed from that side
			BlockPos end = path.get(path.size() - 1);
			assertTrue(FREE.at(end.getX(), end.getY(), end.getZ()), "finished inside a block");
			assertTrue(within(end, target, Nav.GOAL_SLACK),
				"finished " + Math.round(Math.sqrt(end.distSqr(target))) + " from the target");
		}
		assertTrue(tried > 15, "only " + tried + " solid targets were tested");
	}

	@Test
	void aStandoffOnRealGeometryCanSeeItsWork() {
		// The build loop stands off a cell it is about to place. On this island that cell is as
		// likely to be in a wall, under the deck or against the plate's underside as in open air.
		Random r = new Random(11);
		int tried = 0, roomy = 0;
		for (int guard = 0; guard < 60_000 && tried < 60; guard++) {
			int lx = r.nextInt(sx), ly = r.nextInt(sy), lz = r.nextInt(sz);
			BlockPos work = world(lx, ly, lz);
			if (!solid(work.getX(), work.getY(), work.getZ())) continue;
			if (openNear(work, 3) == null) continue;                 // buried: nothing to stand in
			BlockPos stand = Nav.standoff(FREE, work, null, Hud.STANDOFF);
			if (stand == null) continue;
			tried++;
			assertTrue(FREE.at(stand.getX(), stand.getY(), stand.getZ()), "stood inside the island");
			assertTrue(Nav.sees(FREE, stand, work),
				"cannot see the block it is meant to place: " + stand + " -> " + work);
			// CHEBYSHEV: `standoff` searches in shells, so `maxOut` is a box radius. Asserting a
			// euclidean distance is the same box-for-a-sphere slip GOAL_SLACK had, and it passed
			// here only until the air-below rule started picking corner cells.
			assertTrue(within(stand, work, Hud.STANDOFF), "stood further off than it was allowed");
			if (Nav.openness(FREE, stand) >= 3) roomy++;
		}
		assertTrue(tried > 20, "only " + tried + " standoffs were tested");
		// Most of them should be roomy; the tight ones are the tunnels, and those are real.
		assertTrue(roomy * 2 > tried, "only " + roomy + " of " + tried + " standoffs had room to work");
	}

	@Test
	void walkingRoutesOnTheIslandNeverFloat() {
		// Indoors is where walking happens. Every cell of a walking route needs footing, or it is a
		// flight plan being walked.
		Random r = new Random(3);
		List<BlockPos> footed = new ArrayList<>();
		for (int guard = 0; guard < 200_000 && footed.size() < 60; guard++) {
			int lx = r.nextInt(sx), ly = r.nextInt(sy), lz = r.nextInt(sz);
			BlockPos p = world(lx, ly, lz);
			if (STAND.at(p.getX(), p.getY(), p.getZ())) footed.add(p);
		}
		assertTrue(footed.size() > 20, "found almost nowhere to stand on the island");
		int routed = 0;
		for (int i = 0; i + 1 < footed.size(); i += 2) {
			List<BlockPos> path = Nav.route(STAND, footed.get(i), footed.get(i + 1));
			if (path.isEmpty()) continue;
			routed++;
			for (BlockPos c : path) {
				assertTrue(solid(c.getX(), c.getY() - 1, c.getZ())
						|| solid(c.getX(), c.getY() - 2, c.getZ()),
					"walking route floats at " + c);
				assertTrue(!solid(c.getX(), c.getY(), c.getZ())
						&& !solid(c.getX(), c.getY() + 1, c.getZ()),
					"walking route goes through the island at " + c);
			}
		}
		assertTrue(routed > 0, "no walking route was found anywhere on the island");
	}

	@Test
	void escapeAlwaysMakesProgressOrAdmitsItCannot() {
		// The fallback, on real geometry. It must never hand back something that is no closer, or
		// the autopilot flies to it, looks again, and does the same thing for ever.
		List<BlockPos> spots = openCells(555L, 40);
		for (int i = 0; i + 1 < spots.size(); i += 2) {
			BlockPos a = spots.get(i), b = spots.get(i + 1);
			List<BlockPos> out = Nav.escape(FREE, a, b, Nav.ESCAPE_RADIUS);
			if (out.isEmpty()) continue;
			BlockPos end = out.get(out.size() - 1);
			assertTrue(end.distSqr(b) < a.distSqr(b),
				"escape from " + a + " toward " + b + " ended no closer, at " + end);
			for (BlockPos c : out) {
				assertTrue(FREE.at(c.getX(), c.getY(), c.getZ()), "escaped into the island at " + c);
			}
		}
	}

	@Test
	void noSingleSearchIsSlowEnoughToHitchTheClient() {
		// This runs on the client thread, twice a second, for hours. The budget is stated in
		// milliseconds for exactly this reason - so measure it on the real thing, where the frontier
		// meets real geometry rather than an empty box.
		List<BlockPos> spots = openCells(31337L, 60);
		long worst = 0;
		BlockPos wa = null, wb = null;
		for (int i = 0; i + 1 < spots.size(); i += 2) {
			BlockPos a = spots.get(i), b = spots.get(i + 1);
			long t0 = System.nanoTime();
			Nav.route(FREE, a, b);
			long ms = (System.nanoTime() - t0) / 1_000_000;
			if (ms > worst) {
				worst = ms;
				wa = a;
				wb = b;
			}
		}
		// Generous against a cold JIT and a shared machine; the point is to catch a search that has
		// stopped being bounded at all, which is what a raised budget plus a bad gate produces.
		assertTrue(worst < 4 * Nav.MAX_MILLIS + 250,
			"a single search took " + worst + "ms (" + wa + " -> " + wb + ")");
	}

	// ---------------------------------------------------------------- helpers

	/** A passable cell with the island overhead: the deck and the undercroft, not the open sky. */
	private static BlockPos interiorSeed() {
		Random r = new Random(1);
		BlockPos best = null;
		for (int guard = 0; guard < 200_000; guard++) {
			int lx = r.nextInt(sx), ly = r.nextInt(sy), lz = r.nextInt(sz);
			BlockPos p = world(lx, ly, lz);
			if (!FREE.at(p.getX(), p.getY(), p.getZ())) continue;
			boolean roofed = false;
			for (int up = 2; up <= 12 && !roofed; up++) {
				if (solid(p.getX(), p.getY() + up, p.getZ())) roofed = true;
			}
			if (!roofed) continue;
			if (flood(p, 800).size() >= 400) return p;    // a real space, not a pocket
			best = p;
		}
		return best;
	}

	/** Everything reachable from here under the flying predicate, up to a cell budget. */
	private static List<BlockPos> flood(BlockPos from, int cap) {
		List<BlockPos> out = new ArrayList<>();
		Set<Long> seen = new HashSet<>();
		ArrayDeque<BlockPos> q = new ArrayDeque<>();
		q.add(from);
		seen.add(from.asLong());
		while (!q.isEmpty() && out.size() < cap) {
			BlockPos c = q.poll();
			out.add(c);
			for (int dx = -1; dx <= 1; dx++) {
				for (int dy = -1; dy <= 1; dy++) {
					for (int dz = -1; dz <= 1; dz++) {
						if (dx == 0 && dy == 0 && dz == 0) continue;
						BlockPos n = c.offset(dx, dy, dz);
						if (!seen.add(n.asLong())) continue;
						if (!FREE.at(n.getX(), n.getY(), n.getZ())) continue;
						// the same no-corner-cutting rule the router uses, or the flood claims a
						// connectivity the route cannot deliver and the test blames the router
						if (dx != 0 && !FREE.at(c.getX() + dx, c.getY(), c.getZ())) continue;
						if (dy != 0 && !FREE.at(c.getX(), c.getY() + dy, c.getZ())) continue;
						if (dz != 0 && !FREE.at(c.getX(), c.getY(), c.getZ() + dz)) continue;
						q.add(n);
					}
				}
			}
		}
		return out;
	}

	/**
	 * Chebyshev distance, because {@link Nav#GOAL_SLACK} is a BOX radius and not a sphere.
	 *
	 * <p>Slack 2 permits (2,2,2), which is 3.46 away as the crow flies — so a euclidean assertion
	 * fails on a corner the code is entitled to pick. Caught by the island tests, where the corner
	 * cases turn up on their own rather than being thought of.
	 */
	private static boolean within(BlockPos a, BlockPos b, int slack) {
		return Math.abs(a.getX() - b.getX()) <= slack && Math.abs(a.getY() - b.getY()) <= slack
			&& Math.abs(a.getZ() - b.getZ()) <= slack;
	}

	/** Somewhere open within `r` of a block, or null. */
	private static BlockPos openNear(BlockPos at, int radius) {
		for (int d = 1; d <= radius; d++) {
			for (int[] o : new int[][]{{d, 0, 0}, {-d, 0, 0}, {0, d, 0}, {0, -d, 0}, {0, 0, d},
				{0, 0, -d}}) {
				BlockPos c = at.offset(o[0], o[1], o[2]);
				if (FREE.at(c.getX(), c.getY(), c.getZ())) return c;
			}
		}
		return null;
	}
}
