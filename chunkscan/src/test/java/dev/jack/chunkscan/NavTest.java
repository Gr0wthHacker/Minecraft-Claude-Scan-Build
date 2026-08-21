package dev.jack.chunkscan;

import net.minecraft.core.BlockPos;
import org.junit.jupiter.api.Test;

import java.util.HashSet;
import java.util.List;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Routing through the world the client can already see.
 *
 * <p>The case that matters is the doorway: a wall with one hole in it. Flying at a bearing presses
 * you against the outside of it forever, and a router that cuts corners catches on the jamb.
 */
class NavTest {
	/** Everything is open except the walls you add. */
	private static final class W {
		final Set<Long> solid = new HashSet<>();

		void wall(int x, int y0, int y1, int z0, int z1) {
			for (int y = y0; y <= y1; y++) {
				for (int z = z0; z <= z1; z++) solid.add(BlockPos.asLong(x, y, z));
			}
		}

		void open(int x, int y, int z) {
			solid.remove(BlockPos.asLong(x, y, z));
		}

		/**
		 * A sealed shell around a volume. A finite WALL in open sky is not sealed - the router
		 * simply flies over the top of it, which is correct behaviour and made the first version of
		 * these tests assert nonsense.
		 */
		void room(int x0, int y0, int z0, int x1, int y1, int z1) {
			for (int x = x0; x <= x1; x++) {
				for (int y = y0; y <= y1; y++) {
					for (int z = z0; z <= z1; z++) {
						boolean shell = x == x0 || x == x1 || y == y0 || y == y1 || z == z0 || z == z1;
						if (shell) solid.add(BlockPos.asLong(x, y, z));
					}
				}
			}
		}

		/** Two clear cells, as the real one does — a player is two blocks tall. */
		Nav.Passable free() {
			return (x, y, z) -> !solid.contains(BlockPos.asLong(x, y, z))
				&& !solid.contains(BlockPos.asLong(x, y + 1, z));
		}
	}

	@Test
	void openAirIsAStraightLine() {
		W w = new W();
		List<BlockPos> p = Nav.route(w.free(), new BlockPos(0, 100, 0), new BlockPos(10, 100, 0));
		assertFalse(p.isEmpty());
		assertEquals(new BlockPos(10, 100, 0), p.get(p.size() - 1));
	}

	@Test
	void itFindsTheDoorway() {
		// A wall from z -8 to 8, one two-high gap at z=4. OFF the straight line on purpose: with the
		// door dead ahead the straight line goes through it, the line-of-sight shortcut answers
		// correctly in zero nodes, and the test proves nothing about the search. Offset, the only
		// way through is to find it.
		W w = new W();
		w.wall(5, 98, 105, -8, 8);
		w.open(5, 100, 4);
		w.open(5, 101, 4);

		List<BlockPos> p = Nav.route(w.free(), new BlockPos(0, 100, 0), new BlockPos(10, 100, 0));
		assertFalse(p.isEmpty(), "no route found through the door");
		assertTrue(p.contains(new BlockPos(5, 100, 4)), "the route did not use the doorway: " + p);
		assertEquals(new BlockPos(10, 100, 0), p.get(p.size() - 1));
	}

	@Test
	void aClearHopCostsNoSearchAtAll() {
		// THE CHEAPEST ROUTE IS THE ONE YOU DO NOT SEARCH FOR, and across this island's open sky it
		// is most of them. One waypoint - the destination - and nothing in between.
		W w = new W();
		List<BlockPos> p = Nav.route(w.free(), new BlockPos(0, 100, 0), new BlockPos(200, 140, 60));
		assertEquals(1, p.size(), "a clear line was searched rather than flown: " + p.size());
		assertEquals(new BlockPos(200, 140, 60), p.get(0));
	}

	@Test
	void aSolidDestinationIsReachedBesideRatherThanNotAtAll() {
		// A CHEST BLOCKS MOTION, and every fetch target is a chest's own cell. Nothing checked for
		// it: the goal was never expanded, the search spent its whole budget and returned empty, and
		// the caller flew straight at the wall the chest was in.
		W w = new W();
		BlockPos chest = new BlockPos(10, 100, 0);
		w.solid.add(chest.asLong());

		List<BlockPos> p = Nav.route(w.free(), new BlockPos(0, 100, 0), chest);
		assertFalse(p.isEmpty(), "gave up on a destination that blocks motion");
		BlockPos end = p.get(p.size() - 1);
		assertTrue(end.distSqr(chest) <= (double) Nav.GOAL_SLACK * Nav.GOAL_SLACK,
			"finished " + Math.sqrt(end.distSqr(chest)) + " from the chest");
		assertTrue(w.free().at(end.getX(), end.getY(), end.getZ()), "finished inside a block");
	}

	@Test
	void aBuriedDestinationStillHasNoRoute() {
		// The slack is for a chest in a wall, not for pretending a sealed cell is reachable.
		W w = new W();
		for (int x = 8; x <= 12; x++) {
			for (int y = 98; y <= 102; y++) {
				for (int z = -2; z <= 2; z++) w.solid.add(BlockPos.asLong(x, y, z));
			}
		}
		assertTrue(Nav.route(w.free(), new BlockPos(0, 100, 0), new BlockPos(10, 100, 0)).isEmpty(),
			"claimed a route into solid rock");
	}

	@Test
	void aWalkingRouteNeedsFooting() {
		// Clearance alone routes through open air above a floor: a perfect flight plan and a walk
		// into a hole. `standable` is the same world seen by something with legs.
		// The real predicate is built from a Level, so what is asserted here is the SHAPE the router
		// relies on: over a floor there is a route, thirty blocks above the same floor there is not.
		W w = new W();
		for (int x = -2; x <= 22; x++) {
			for (int z = -6; z <= 6; z++) w.solid.add(BlockPos.asLong(x, 99, z));
		}
		Nav.Passable stand = (x, y, z) -> {
			if (w.solid.contains(BlockPos.asLong(x, y, z))) return false;
			if (w.solid.contains(BlockPos.asLong(x, y + 1, z))) return false;
			return w.solid.contains(BlockPos.asLong(x, y - 1, z))
				|| w.solid.contains(BlockPos.asLong(x, y - 2, z));
		};
		assertFalse(Nav.route(stand, new BlockPos(0, 100, 0), new BlockPos(20, 100, 0)).isEmpty(),
			"no walking route along a flat floor");
		assertTrue(Nav.route(stand, new BlockPos(0, 130, 0), new BlockPos(20, 130, 0)).isEmpty(),
			"walked through the sky");
	}

	@Test
	void aSealedRoomHasNoRoute() {
		// It must SAY there is none rather than inventing one: the caller then falls back to a
		// bearing and lifting, which is at least honest about being a guess. Handing back a partial
		// route to the outside of the wall is worse, because it also switches the lift OFF.
		W w = new W();
		w.room(6, 96, -4, 14, 104, 4);
		assertTrue(Nav.route(w.free(), new BlockPos(0, 100, 0), new BlockPos(10, 100, 0)).isEmpty(),
			"routed into a sealed room");
	}

	@Test
	void aRoomWithADoorIsReachable() {
		// The control for the test above: same room, one two-high opening.
		W w = new W();
		w.room(6, 96, -4, 14, 104, 4);
		w.open(6, 100, 0);
		w.open(6, 101, 0);
		assertFalse(Nav.route(w.free(), new BlockPos(0, 100, 0), new BlockPos(10, 100, 0)).isEmpty(),
			"could not find the door into the room");
	}

	@Test
	void everyStepOfTheRouteIsPassable() {
		// Door offset from the straight line, so the SEARCH produces the path rather than the
		// line-of-sight shortcut handing back a single waypoint there is nothing to check.
		W w = new W();
		w.wall(5, 98, 105, -8, 8);
		w.open(5, 100, 4);
		w.open(5, 101, 4);
		Nav.Passable free = w.free();
		for (BlockPos b : Nav.route(free, new BlockPos(0, 100, 0), new BlockPos(10, 100, 0))) {
			assertTrue(free.at(b.getX(), b.getY(), b.getZ()), b + " is inside a wall");
		}
	}

	@Test
	void itDoesNotCutTheCornerOfADoorFrame() {
		// THE JAMB. A diagonal step is only legal when the orthogonal cells it passes between are
		// clear too; without that the route squeezes the corner - shorter on paper, snagged in game.
		W w = new W();
		w.wall(5, 98, 105, -8, 8);
		w.open(5, 100, 4);                       // off the straight line: see everyStepOfTheRoute...
		w.open(5, 101, 4);
		Nav.Passable free = w.free();
		List<BlockPos> p = Nav.route(free, new BlockPos(0, 100, 0), new BlockPos(10, 100, 0));

		BlockPos prev = new BlockPos(0, 100, 0);
		for (BlockPos b : p) {
			int dx = b.getX() - prev.getX(), dy = b.getY() - prev.getY(), dz = b.getZ() - prev.getZ();
			if (dx != 0 && (dy != 0 || dz != 0)) {
				assertTrue(free.at(prev.getX() + dx, prev.getY(), prev.getZ()),
					"cut the corner at " + prev + " -> " + b);
			}
			prev = b;
		}
	}

	@Test
	void aOneBlockHighGapIsNotADoorway() {
		// Clearance, not emptiness. One clear cell with a solid one above it is a hole you brain
		// yourself on, and a player is two blocks tall.
		W w = new W();
		w.room(6, 96, -4, 14, 104, 4);
		w.open(6, 100, 0);                       // ONE cell; 101 stays solid
		assertTrue(Nav.route(w.free(), new BlockPos(0, 100, 0), new BlockPos(10, 100, 0)).isEmpty(),
			"routed through a one-block-high gap");
	}

	@Test
	void unloadedIsPassableNotAWall() {
		// A chunk that has not arrived is not a wall, and refusing to route through it would fail
		// every long flight. The route is recomputed as you go and sharpens as the world loads.
		Nav.Passable nothingKnown = (x, y, z) -> true;
		assertFalse(Nav.route(nothingKnown, new BlockPos(0, 100, 0), new BlockPos(40, 100, 40)).isEmpty());
	}

	@Test
	void aRouteBeyondTheRangeCapIsRefused() {
		Nav.Passable open = (x, y, z) -> true;
		assertTrue(Nav.route(open, new BlockPos(0, 100, 0),
			new BlockPos(Nav.MAX_RANGE + 50, 100, 0)).isEmpty());
	}

	@Test
	void simplifyKeepsTheCornersAndDropsTheBeadChain() {
		// A* returns every cell it stepped on; through open air that is forty points and a flight
		// path that visibly zig-zags between them. Fed by hand rather than by route(), which now
		// answers a clear line with one waypoint and so has nothing left to simplify — the thing
		// under test is simplify, not the shortcut in front of it.
		W w = new W();
		Nav.Passable free = w.free();
		BlockPos from = new BlockPos(0, 100, 0);
		List<BlockPos> raw = new java.util.ArrayList<>();
		for (int x = 1; x <= 20; x++) raw.add(new BlockPos(x, 100, 0));
		List<BlockPos> few = Nav.simplify(free, from, raw);
		assertEquals(1, few.size(), "a straight bead chain should collapse to its endpoint: " + few);
		assertEquals(raw.get(raw.size() - 1), few.get(few.size() - 1), "the destination was dropped");
	}

	@Test
	void simplifyNeverStraightensThroughAWall() {
		W w = new W();
		w.wall(5, 98, 105, -8, 8);
		w.open(5, 100, 0);
		w.open(5, 101, 0);
		Nav.Passable free = w.free();
		BlockPos from = new BlockPos(0, 100, 4);
		List<BlockPos> few = Nav.simplify(free, from, Nav.route(free, from, new BlockPos(10, 100, -4)));
		BlockPos prev = from;
		for (BlockPos b : few) {
			assertTrue(Nav.clear(free, prev, b), "simplified straight through a wall: " + prev + " -> " + b);
			prev = b;
		}
	}

	@Test
	void clearSeesAWallBetweenTwoOpenCells() {
		W w = new W();
		w.wall(5, 98, 105, -8, 8);
		assertFalse(Nav.clear(w.free(), new BlockPos(0, 100, 0), new BlockPos(10, 100, 0)));
		assertTrue(Nav.clear(w.free(), new BlockPos(0, 100, 0), new BlockPos(4, 100, 0)));
	}

	// ---------------------------------------------------------------- getting round it
	//
	// The fallback when no route exists used to be "fly at the goal and add a little upward nudge",
	// which does not lift you over anything - it grinds you along the wall at an angle. Getting round
	// an obstacle is a SEARCH, not a nudge.

	@Test
	void escapeGoesAroundRatherThanInto() {
		// A wall with no door, and a way round the end of it. There is no route to the goal, so the
		// question is only whether it makes progress - and progress means ending up closer.
		W w = new W();
		w.wall(5, 90, 130, -20, 20);        // tall and wide, but finite: you can go round the top
		BlockPos from = new BlockPos(0, 100, 0);
		BlockPos to = new BlockPos(10, 100, 0);

		assertTrue(Nav.route(w.free(), from, to).isEmpty(), "control: there is no route through");
		List<BlockPos> out = Nav.escape(w.free(), from, to, Nav.ESCAPE_RADIUS);
		assertFalse(out.isEmpty(), "gave up instead of going round");
		BlockPos end = out.get(out.size() - 1);
		assertTrue(end.distSqr(to) < from.distSqr(to), "went somewhere no closer than where it was");
		for (BlockPos b : out) {
			assertTrue(w.free().at(b.getX(), b.getY(), b.getZ()), b + " is inside a wall");
		}
	}

	@Test
	void escapeUsesEveryDirectionNotJustUp() {
		// "up, down, left, right" - a ceiling is escaped sideways, not by rising into it.
		W w = new W();
		for (int x = -20; x <= 20; x++) {
			for (int z = -20; z <= 20; z++) {
				if (z > 3) continue;                     // open to the north only
				for (int y = 101; y <= 120; y++) w.solid.add(BlockPos.asLong(x, y, z));
			}
		}
		BlockPos from = new BlockPos(0, 99, 0);
		BlockPos to = new BlockPos(0, 130, 0);           // straight up, through the lid
		List<BlockPos> out = Nav.escape(w.free(), from, to, Nav.ESCAPE_RADIUS);
		assertFalse(out.isEmpty(), "sat under the ceiling");
		assertTrue(out.get(out.size() - 1).getZ() > 3, "did not look sideways for the way out");
	}

	@Test
	void escapeFromASealedBoxStaysInTheBoxAndThenStops() {
		// Written first as "a sealed box has no escape", which was wrong: crossing the room really
		// does get you closer to something outside it, and "the best cell you can reach" is the
		// honest answer even when it is two blocks away. What matters is that it never leaves, and
		// that it CONVERGES - one move to the near wall, and then nothing, rather than an autopilot
		// bouncing off the inside of a room for ever.
		W w = new W();
		w.room(-3, 97, -3, 3, 103, 3);
		BlockPos goal = new BlockPos(60, 100, 0);
		List<BlockPos> first = Nav.escape(w.free(), new BlockPos(0, 100, 0), goal, Nav.ESCAPE_RADIUS);
		for (BlockPos b : first) {
			assertTrue(b.getX() > -3 && b.getX() < 3, "escaped a sealed box at " + b);
			assertTrue(w.free().at(b.getX(), b.getY(), b.getZ()), b + " is inside a wall");
		}
		BlockPos best = first.isEmpty() ? new BlockPos(0, 100, 0) : first.get(first.size() - 1);
		assertTrue(Nav.escape(w.free(), best, goal, Nav.ESCAPE_RADIUS).isEmpty(),
			"kept finding new progress from the best cell in a closed room");
	}
}
