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
		// A wall from z -8 to 8, one two-high gap at z=0. The only way through.
		W w = new W();
		w.wall(5, 98, 105, -8, 8);
		w.open(5, 100, 0);
		w.open(5, 101, 0);

		List<BlockPos> p = Nav.route(w.free(), new BlockPos(0, 100, 0), new BlockPos(10, 100, 0));
		assertFalse(p.isEmpty(), "no route found through the door");
		assertTrue(p.contains(new BlockPos(5, 100, 0)), "the route did not use the doorway: " + p);
		assertEquals(new BlockPos(10, 100, 0), p.get(p.size() - 1));
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
		W w = new W();
		w.wall(5, 98, 105, -8, 8);
		w.open(5, 100, 0);
		w.open(5, 101, 0);
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
		w.open(5, 100, 0);
		w.open(5, 101, 0);
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
		// path that visibly zig-zags between them.
		W w = new W();
		Nav.Passable free = w.free();
		BlockPos from = new BlockPos(0, 100, 0);
		List<BlockPos> raw = Nav.route(free, from, new BlockPos(20, 100, 0));
		List<BlockPos> few = Nav.simplify(free, from, raw);
		assertTrue(few.size() < raw.size(), "nothing was simplified");
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
}
