package dev.jack.chunkscan;

import net.minecraft.core.BlockPos;
import org.junit.jupiter.api.Test;

import java.util.HashSet;
import java.util.List;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
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

		/** Fill a box solid. The island is mostly rock with holes in it, not walls in the sky. */
		void fill(int x0, int y0, int z0, int x1, int y1, int z1) {
			for (int x = x0; x <= x1; x++) {
				for (int y = y0; y <= y1; y++) {
					for (int z = z0; z <= z1; z++) solid.add(BlockPos.asLong(x, y, z));
				}
			}
		}

		/** Hollow a box out of the rock. */
		void carve(int x0, int y0, int z0, int x1, int y1, int z1) {
			for (int x = x0; x <= x1; x++) {
				for (int y = y0; y <= y1; y++) {
					for (int z = z0; z <= z1; z++) solid.remove(BlockPos.asLong(x, y, z));
				}
			}
		}

		/**
		 * A tunnel through solid rock: `h` cells of headroom, one wide, running along X.
		 *
		 * <p>This is the shape the island is full of - the taproot, the undercroft, the workshop
		 * necks - and it is the one a router gets wrong, because every cell of it is against a wall.
		 * Every rule that is "usually fine" meets its worst case here at once.
		 */
		void highway(int x0, int x1, int y, int z, int h) {
			// EIGHT blocks of rock around it, not three. With three, open sky was inside the first
			// few shells of a standoff search, so the corridor case never actually got tested — the
			// spot it picked was outside the tunnel altogether. A fixture that is thinner than the
			// thing under test measures the thing beside it.
			fill(x0 - 8, y - 8, z - 8, x1 + 8, y + h + 8, z + 8);
			carve(x0, y, z, x1, y + h - 1, z);
		}

		/** Two clear cells, as the real one does - a player is two blocks tall. */
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
		// Chebyshev: GOAL_SLACK is a box radius, so (2,2,2) is legal at 3.46 as the crow flies.
		assertTrue(Math.abs(end.getX() - chest.getX()) <= Nav.GOAL_SLACK
				&& Math.abs(end.getY() - chest.getY()) <= Nav.GOAL_SLACK
				&& Math.abs(end.getZ() - chest.getZ()) <= Nav.GOAL_SLACK,
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
		// The goal is SEALED, so there is genuinely no route and the only question is whether it
		// makes progress - which means ending up closer than it started.
		//
		// Written first with a tall finite wall between the two, and that stopped being a control:
		// with staging and the raised budget the router now finds its way round the end of it, which
		// is the router getting better rather than the test getting stale. A wall in the open is not
		// sealed - the same lesson two of these tests learned once already.
		W w = new W();
		w.room(8, 97, -3, 14, 103, 3);
		BlockPos from = new BlockPos(0, 100, 0);
		BlockPos to = new BlockPos(11, 100, 0);

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

	// ---------------------------------------------------------------- somewhere to work from

	@Test
	void aStandoffIsOpenEnoughToWorkFrom() {
		// `reachable` answers "may a route END here" and takes the first free cell it finds, which
		// beside a wall is the crevice between two blocks. A place to FLOAT and print from wants
		// more: this island is a deck under a plate, full of hoppers, chests and roots, and a spot
		// wedged between two of them is one the printer never finishes.
		//
		// Written first as a pocket sealed inside a solid mass, which stopped being a fair question
		// once a standoff had to SEE the work: nothing outside a sealed mass can, and null is then
		// the right answer. A wall with a hole beside the work is the real shape of it.
		W w = new W();
		w.fill(-6, 90, -6, -1, 110, 6);                  // a wall to the west
		BlockPos work = new BlockPos(-1, 100, 0);        // the block being placed, in its face
		w.carve(-1, 100, 1, -1, 101, 1);                 // a two-cell pocket beside it

		BlockPos pocket = new BlockPos(-1, 100, 1);
		assertTrue(w.free().at(pocket.getX(), pocket.getY(), pocket.getZ()),
			"control: the pocket is a free cell");
		assertTrue(Nav.openness(w.free(), pocket) < 3, "control: and a wedged one");

		BlockPos stand = Nav.standoff(w.free(), work, null, 4);
		assertNotNull(stand, "found nowhere at all to work from");
		assertNotEquals(pocket, stand, "climbed into the pocket");
		assertTrue(Nav.openness(w.free(), stand) >= 3, "wedged in beside the work");
		assertTrue(Nav.sees(w.free(), stand, work), "cannot see the block it is meant to place");
	}

	@Test
	void aStandoffPrefersYourSideOfTheWork() {
		// The different angles: pass where you are coming from and it stands on that side rather
		// than burrowing round to the far face of the wall you are building.
		W w = new W();
		BlockPos work = new BlockPos(0, 100, 0);
		w.solid.add(work.asLong());
		BlockPos east = Nav.standoff(w.free(), work, new BlockPos(40, 100, 0), 4);
		BlockPos west = Nav.standoff(w.free(), work, new BlockPos(-40, 100, 0), 4);
		assertNotNull(east);
		assertNotNull(west);
		assertTrue(east.getX() > west.getX(),
			"ignored the side it was asked for: " + east + " vs " + west);
	}

	// ---------------------------------------------------------------- clearance

	@Test
	void loosenPushesAWaypointOffTheWallItWasShavedAgainst() {
		// The search's only cost is distance, so the cheapest route grazes every corner. Legal, and
		// it flies like something nervous. Doing it to the CORNERS after simplify is nearly free;
		// doing it inside the search would be six more lookups on every one of 120,000 nodes.
		W w = new W();
		for (int y = 90; y <= 110; y++) {
			for (int z = -10; z <= 10; z++) w.solid.add(BlockPos.asLong(0, y, z));
		}
		Nav.Passable free = w.free();
		BlockPos hugging = new BlockPos(1, 100, 0);          // free, but flat against the wall
		assertTrue(free.at(1, 100, 0));

		List<BlockPos> loose = Nav.loosen(free, new BlockPos(4, 100, -6),
			List.of(hugging, new BlockPos(4, 100, 6)));
		assertTrue(Nav.openness(free, loose.get(0)) > Nav.openness(free, hugging),
			"stayed flat against the wall");
	}

	@Test
	void loosenNeverWidensADoorwayOutOfItsDoor() {
		// The one place a waypoint MUST hug: a nudge is only kept when both legs through the moved
		// point are still flyable.
		W w = new W();
		w.wall(5, 98, 105, -8, 8);
		w.open(5, 100, 4);
		w.open(5, 101, 4);
		Nav.Passable free = w.free();
		BlockPos from = new BlockPos(0, 100, 0);
		List<BlockPos> raw = Nav.route(free, from, new BlockPos(10, 100, 0));
		List<BlockPos> few = Nav.simplify(free, from, raw);
		List<BlockPos> loose = Nav.loosen(free, from, few);

		BlockPos prev = from;
		for (BlockPos b : loose) {
			assertTrue(Nav.clear(free, prev, b), "loosened the route through the wall at " + b);
			prev = b;
		}
	}

	@Test
	void loosenLeavesTheDestinationAlone() {
		// It is the goal, not a waypoint: moving it means arriving somewhere else.
		W w = new W();
		BlockPos goal = new BlockPos(9, 100, 0);
		List<BlockPos> loose = Nav.loosen(w.free(), BlockPos.ZERO, List.of(new BlockPos(4, 100, 0), goal));
		assertEquals(goal, loose.get(loose.size() - 1));
	}

	// ================================================================ the shapes this island has
	//
	// Everything above tests a wall with a hole in it, which is the textbook case and not what this
	// island is made of. What it is made of is TUNNELS: the taproot, the undercroft, the workshop
	// necks, the store hall door. Every cell of a one-wide tunnel is against a wall, so every rule
	// that is "usually fine" meets its worst case there, all at once.

	@Test
	void aOneWideHighwayIsFlyable() {
		W w = new W();
		w.highway(0, 30, 100, 0, 2);
		List<BlockPos> p = Nav.route(w.free(), new BlockPos(0, 100, 0), new BlockPos(30, 100, 0));
		assertFalse(p.isEmpty(), "would not fly a straight one-wide tunnel");
		assertEquals(new BlockPos(30, 100, 0), p.get(p.size() - 1));
	}

	@Test
	void aOneWideHighwaySurvivesTheWholePipeline() {
		// route -> simplify -> loosen is what the autopilot actually flies, and each stage can undo
		// the last one's care. A tunnel is where that shows: `loosen` exists to push waypoints away
		// from walls, and in here there is nowhere to push them to.
		W w = new W();
		w.highway(0, 30, 100, 0, 2);
		Nav.Passable free = w.free();
		BlockPos from = new BlockPos(0, 100, 0);
		List<BlockPos> flown = Nav.loosen(free, from,
			Nav.simplify(free, from, Nav.route(free, from, new BlockPos(30, 100, 0))));

		BlockPos prev = from;
		for (BlockPos b : flown) {
			assertTrue(free.at(b.getX(), b.getY(), b.getZ()), b + " is inside the rock");
			assertTrue(Nav.clear(free, prev, b), "the leg " + prev + " -> " + b + " goes through rock");
			prev = b;
		}
		assertEquals(new BlockPos(30, 100, 0), flown.get(flown.size() - 1));
	}

	@Test
	void aDoglegHighwayIsFlyable() {
		// An L. The corner is where the no-corner-cutting rule earns its keep: the diagonal step has
		// a blocked orthogonal, so it must go straight and then turn.
		W w = new W();
		w.fill(-4, 96, -4, 24, 106, 24);
		w.carve(0, 100, 0, 20, 101, 0);
		w.carve(20, 100, 0, 20, 101, 20);
		Nav.Passable free = w.free();
		BlockPos from = new BlockPos(0, 100, 0), to = new BlockPos(20, 100, 20);
		List<BlockPos> p = Nav.route(free, from, to);
		assertFalse(p.isEmpty(), "would not turn a corner in a tunnel");
		for (BlockPos b : p) assertTrue(free.at(b.getX(), b.getY(), b.getZ()), b + " is in the rock");
		assertEquals(to, p.get(p.size() - 1));
	}

	@Test
	void aVerticalShaftIsFlyable() {
		// The taproot: a one-wide well straight down through the deck.
		W w = new W();
		w.fill(-4, 160, -4, 4, 202, 4);
		w.carve(0, 162, 0, 0, 200, 0);
		List<BlockPos> p = Nav.route(w.free(), new BlockPos(0, 198, 0), new BlockPos(0, 163, 0));
		assertFalse(p.isEmpty(), "would not fly down a shaft");
		for (BlockPos b : p) {
			assertEquals(0, b.getX(), "left the shaft at " + b);
			assertEquals(0, b.getZ(), "left the shaft at " + b);
		}
	}

	@Test
	void aCrawlSpaceIsNotAHighway() {
		// One cell of headroom is a hole you brain yourself on. A player is two blocks tall, and
		// `of()` checking the cell above is the whole reason this is refused.
		W w = new W();
		w.highway(0, 30, 100, 0, 1);
		assertTrue(Nav.route(w.free(), new BlockPos(0, 100, 0), new BlockPos(30, 100, 0)).isEmpty(),
			"routed down a one-high crawl space");
	}

	@Test
	void aSlabCeilingIsSolidAndTheCellsUnderItAreNot() {
		// A slab is a whole cell to a router: `blocksMotion` is true for it, so the cell it sits in
		// is rock and the two beneath it are the tunnel. Modelling it as half a block instead is how
		// you fly into every slab ceiling on the deck.
		W w = new W();
		w.highway(0, 20, 100, 0, 2);
		assertFalse(w.free().at(0, 102, 0), "treated a slab ceiling as air");
		assertTrue(w.free().at(0, 100, 0), "lost the tunnel under it");
		assertFalse(Nav.route(w.free(), new BlockPos(0, 100, 0), new BlockPos(20, 100, 0)).isEmpty());
	}

	@Test
	void aStandingSpotExistsInsideAHighway() {
		// `standoff` wants somewhere OPEN to work from - three ways out - and a one-wide tunnel has
		// exactly two, along its length. Insisting finds nowhere at all, and the caller then falls
		// back to the bin centroid, which is inside the wall being built.
		W w = new W();
		w.highway(0, 20, 100, 0, 2);
		BlockPos stand = Nav.standoff(w.free(), new BlockPos(10, 100, 0), null, 4);
		assertNotNull(stand, "found nowhere to stand in a corridor");
		assertTrue(w.free().at(stand.getX(), stand.getY(), stand.getZ()), "stood inside the rock");
	}

	@Test
	void aStandingSpotStillPrefersOpenAirWhenThereIsSome() {
		// ...and the fallback must not become the rule: offered both a dead-end pocket in the wall
		// and the open air in front of it, it takes the open air.
		W w = new W();
		w.fill(-6, 90, -6, -1, 110, 6);                  // a wall to the west
		w.carve(-1, 100, 0, -1, 101, 0);                 // with a two-cell pocket in its face
		BlockPos work = new BlockPos(0, 100, 0);
		w.solid.add(work.asLong());                      // the block being placed

		BlockPos stand = Nav.standoff(w.free(), work, null, 4);
		assertNotNull(stand);
		assertNotEquals(new BlockPos(-1, 100, 0), stand, "climbed into the pocket");
		assertTrue(Nav.openness(w.free(), stand) >= 3, "settled for a crevice with open air beside it");
	}

	@Test
	void aStandingSpotCanSeeTheWork() {
		// "Near" measured through rock is not near. A wall with the work on one side and open air on
		// the other: the far side is closer in blocks and useless in every other way.
		W w = new W();
		w.fill(-1, 90, -20, 1, 110, 20);                 // a thick wall at x = -1..1
		BlockPos work = new BlockPos(1, 100, 0);         // its east face
		BlockPos stand = Nav.standoff(w.free(), work, null, 4);
		assertNotNull(stand);
		assertTrue(stand.getX() > 1, "stood on the far side of the wall from the work: " + stand);
		assertTrue(Nav.sees(w.free(), stand, work), "cannot see the block it is meant to place");
	}

	@Test
	void seesIgnoresTheTargetBlockItself() {
		// The block you are placing is solid by definition; if it counted against the line of sight
		// nothing could ever be placed.
		W w = new W();
		BlockPos work = new BlockPos(5, 100, 0);
		w.solid.add(work.asLong());
		assertTrue(Nav.sees(w.free(), new BlockPos(0, 100, 0), work));
		w.solid.add(BlockPos.asLong(3, 100, 0));         // ...but something in between does
		assertFalse(Nav.sees(w.free(), new BlockPos(0, 100, 0), work));
	}

	@Test
	void loosenCannotPushAWaypointOutOfAHighway() {
		// There is nowhere to push to, and a nudge is only kept if both legs stay flyable.
		W w = new W();
		w.highway(0, 20, 100, 0, 2);
		Nav.Passable free = w.free();
		List<BlockPos> loose = Nav.loosen(free, new BlockPos(0, 100, 0),
			List.of(new BlockPos(10, 100, 0), new BlockPos(20, 100, 0)));
		for (BlockPos b : loose) {
			assertTrue(free.at(b.getX(), b.getY(), b.getZ()), "loosened " + b + " into the rock");
		}
	}

	@Test
	void escapeInsideAHighwayRunsAlongIt() {
		// Shut in a tunnel with the goal beyond its far end: the only progress available is forward,
		// and it must find that rather than deciding it is stuck.
		W w = new W();
		w.highway(0, 20, 100, 0, 2);
		List<BlockPos> out = Nav.escape(w.free(), new BlockPos(2, 100, 0),
			new BlockPos(60, 100, 0), Nav.ESCAPE_RADIUS);
		assertFalse(out.isEmpty(), "sat still in a tunnel with an open end");
		assertTrue(out.get(out.size() - 1).getX() > 2, "went the wrong way down the tunnel");
	}

	@Test
	void aChestInTheWallOfAHighwayIsStillReachable() {
		// Every fetch target is a container's own cell, and in a tunnel that cell IS the wall. The
		// route has to finish in the tunnel, beside it.
		W w = new W();
		w.highway(0, 20, 100, 0, 2);
		BlockPos chest = new BlockPos(10, 100, 1);
		assertFalse(w.free().at(10, 100, 1), "control: the chest cell is solid");

		List<BlockPos> p = Nav.route(w.free(), new BlockPos(0, 100, 0), chest);
		assertFalse(p.isEmpty(), "gave up on a chest in a wall");
		BlockPos end = p.get(p.size() - 1);
		assertTrue(Math.abs(end.getX() - chest.getX()) <= Nav.GOAL_SLACK
				&& Math.abs(end.getY() - chest.getY()) <= Nav.GOAL_SLACK
				&& Math.abs(end.getZ() - chest.getZ()) <= Nav.GOAL_SLACK,
			"finished " + Math.sqrt(end.distSqr(chest)) + " away");
		assertTrue(w.free().at(end.getX(), end.getY(), end.getZ()), "finished inside the wall");
	}

	@Test
	void aDoorwayOffTheAxisIsFoundInsideAHighway() {
		// A side passage: the branch you have to notice rather than fly past. This is the store hall
		// door and the undercroft neck.
		W w = new W();
		w.highway(0, 20, 100, 0, 2);
		w.carve(10, 100, 1, 10, 101, 8);
		Nav.Passable free = w.free();
		List<BlockPos> p = Nav.route(free, new BlockPos(0, 100, 0), new BlockPos(10, 100, 8));
		assertFalse(p.isEmpty(), "missed the side passage");
		for (BlockPos b : p) assertTrue(free.at(b.getX(), b.getY(), b.getZ()), b + " is in the rock");
	}

	// ---------------------------------------------------------------- on foot

	@Test
	void aStaircaseIsWalkable() {
		// One course per step, which is what `gen/stairhead.py` builds and what the deck is full of.
		W w = new W();
		w.fill(-2, 90, -3, 22, 99, 3);
		for (int i = 0; i <= 10; i++) w.fill(i, 100, -3, i, 99 + i, 3);
		Nav.Passable stand = standable(w);
		assertFalse(Nav.route(stand, new BlockPos(-1, 100, 0), new BlockPos(10, 110, 0)).isEmpty(),
			"would not walk up a staircase");
	}

	@Test
	void aWalkStepsDownOneCourseButNotOffACliff() {
		// One course of slack under the floor is a STEP; anything deeper is a fall, and a fall is
		// not reversible - you walk somewhere you cannot walk back from.
		W w = new W();
		w.fill(-2, 90, -3, 10, 99, 3);
		w.fill(11, 70, -3, 20, 79, 3);
		Nav.Passable stand = standable(w);
		assertTrue(Nav.route(stand, new BlockPos(0, 100, 0), new BlockPos(15, 80, 0)).isEmpty(),
			"walked off a twenty-block drop");
	}

	@Test
	void aWalkingRouteNeverFloats() {
		// Every cell of a walking route needs something under it, or it is a flight plan.
		W w = new W();
		w.fill(-2, 90, -2, 30, 99, 8);
		Nav.Passable stand = standable(w);
		List<BlockPos> p = Nav.route(stand, new BlockPos(0, 100, 0), new BlockPos(25, 100, 5));
		assertFalse(p.isEmpty(), "would not walk across a flat floor");
		for (BlockPos b : p) {
			assertTrue(w.solid.contains(BlockPos.asLong(b.getX(), b.getY() - 1, b.getZ()))
					|| w.solid.contains(BlockPos.asLong(b.getX(), b.getY() - 2, b.getZ())),
				b + " has no floor under it");
		}
	}

	@Test
	void aWalkerUsesTheDoorRatherThanTheWall() {
		// Indoors is where walking happens and where the routing matters most.
		W w = new W();
		w.fill(-2, 90, -12, 22, 99, 12);
		w.fill(10, 100, -12, 10, 104, 12);
		w.carve(10, 100, 4, 10, 101, 4);
		Nav.Passable stand = standable(w);
		List<BlockPos> p = Nav.route(stand, new BlockPos(0, 100, 0), new BlockPos(20, 100, 0));
		assertFalse(p.isEmpty(), "would not walk through a doorway");
		assertTrue(p.contains(new BlockPos(10, 100, 4)), "walked through the wall: " + p);
	}

	/** The walking predicate, built as {@link Nav#standable} builds it from a Level. */
	private static Nav.Passable standable(W w) {
		return (x, y, z) -> {
			if (w.solid.contains(BlockPos.asLong(x, y, z))) return false;
			if (w.solid.contains(BlockPos.asLong(x, y + 1, z))) return false;
			return w.solid.contains(BlockPos.asLong(x, y - 1, z))
				|| w.solid.contains(BlockPos.asLong(x, y - 2, z));
		};
	}

	@Test
	void aPlaceToWorkFromHasAirOverItsHeadToo() {
		// `Passable` guarantees the two cells a player OCCUPIES, which is enough to be somewhere and
		// not enough to work there: the flight holds altitude by climbing, so a spot with the
		// ceiling on its head grinds upward into it for as long as it stands there.
		W w = new W();
		w.fill(-6, 90, -6, 6, 110, 6);
		// a two-cell slot with the ceiling right on top of it, and a roomier one beside it
		w.carve(0, 100, 0, 0, 101, 0);
		w.carve(2, 100, 0, 2, 103, 0);
		BlockPos tight = new BlockPos(0, 100, 0);
		assertTrue(w.free().at(tight.getX(), tight.getY(), tight.getZ()),
			"control: a body fits in the tight one");
		assertFalse(Nav.headroom(w.free(), tight, Nav.AIR_ABOVE), "control: and has nothing over it");
		assertTrue(Nav.headroom(w.free(), new BlockPos(2, 100, 0), Nav.AIR_ABOVE));
	}

	@Test
	void aStandoffTakesTheSpotWithHeadroom() {
		W w = new W();
		w.fill(-8, 90, -8, 8, 112, 8);
		w.carve(-1, 100, 0, -1, 101, 0);                 // tight pocket beside the work
		w.carve(1, 96, -1, 1, 104, 1);                   // roomy shaft, open above AND below
		BlockPos work = new BlockPos(0, 100, 0);
		w.solid.add(work.asLong());

		BlockPos stand = Nav.standoff(w.free(), work, null, 3);
		assertNotNull(stand);
		assertTrue(Nav.headroom(w.free(), stand, Nav.AIR_ABOVE),
			"picked a spot with the ceiling on its head: " + stand);
	}

	// ---------------------------------------------------------------- routes that keep their distance

	@Test
	void aRoomyRouteDoesNotSkimTheFloor() {
		// A* minimises DISTANCE, so the cheapest route runs along the surface it is passing. That is
		// fine for a pathfinder and wrong for a server where flight ends on contact.
		W w = new W();
		w.fill(-20, 90, -20, 20, 99, 20);                // a floor at y=99
		Nav.Passable roomy = roomy(w);
		assertFalse(roomy.at(0, 100, 0), "a cell resting on the floor counts as roomy");
		assertTrue(roomy.at(0, 102, 0), "nothing counts as roomy at all");

		List<BlockPos> p = Nav.route(roomy, new BlockPos(-10, 102, 0), new BlockPos(10, 102, 0));
		assertFalse(p.isEmpty(), "no roomy route across open air over a floor");
		for (BlockPos b : p) {
			assertTrue(b.getY() > 100, "the roomy route still skimmed the floor at " + b);
		}
	}

	@Test
	void aOneWideShaftHasNoRoomyRouteAtAll() {
		// Which is exactly why it cannot be the only rule: the island is full of them, and the
		// caller falls back to the tight world when the roomy one has no answer.
		W w = new W();
		w.fill(-4, 90, -4, 4, 120, 4);
		w.carve(0, 92, 0, 0, 118, 0);
		assertTrue(Nav.route(roomy(w), new BlockPos(0, 117, 0), new BlockPos(0, 93, 0)).isEmpty(),
			"claimed elbow room inside a one-wide shaft");
		assertFalse(Nav.route(w.free(), new BlockPos(0, 117, 0), new BlockPos(0, 93, 0)).isEmpty(),
			"...and the tight world must still get down it");
	}

	/** {@link Nav#roomy} built over the fixture rather than over a Level. */
	private static Nav.Passable roomy(W w) {
		Nav.Passable tight = w.free();
		return (x, y, z) -> tight.at(x, y, z)
			&& tight.at(x + 1, y, z) && tight.at(x - 1, y, z)
			&& tight.at(x, y, z + 1) && tight.at(x, y, z - 1)
			&& tight.at(x, y + 1, z) && tight.at(x, y - 1, z);
	}
}
