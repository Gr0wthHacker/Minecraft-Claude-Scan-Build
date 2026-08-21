package dev.jack.chunkscan;

import net.minecraft.core.BlockPos;
import net.minecraft.world.phys.Vec3;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * The steering maths. Everything else in Autopilot needs a live client, but the turn is pure and it
 * is the part that would send you spinning the long way round a heading for no reason.
 */
class AutopilotTest {
	@Test
	void theTurnTakesTheShortWayRound() {
		// 350 -> 10 is twenty degrees clockwise, not three hundred and forty back the other way.
		float next = Autopilot.approach(350f, 10f);
		assertTrue(next > 350f, "went the long way: " + next);
		float other = Autopilot.approach(10f, 350f);
		assertTrue(other < 10f, "went the long way: " + other);
	}

	@Test
	void itEasesRatherThanSnapping() {
		// A camera that jumps to a bearing is not a player, and it is what a reviewer notices first.
		float next = Autopilot.approach(0f, 90f);
		assertTrue(next > 0f && next < 90f, "snapped straight to the target: " + next);
		assertEquals(90f * Autopilot.TURN_RATE, next, 0.001f);
	}

	@Test
	void itConvergesAndDoesNotOvershoot() {
		float a = 0f;
		for (int i = 0; i < 200; i++) a = Autopilot.approach(a, 90f);
		assertEquals(90f, a, 0.5f, "never arrived at the heading");
	}

	@Test
	void anExactHeadingDoesNotDrift() {
		assertEquals(42f, Autopilot.approach(42f, 42f), 0.0001f);
	}

	@Test
	void theSpeedIsUnderSprintFlight() {
		// Still bounded, just not timid. Vanilla sprint-flight is about 1.0 blocks a tick, and the
		// ceiling that matters is "no faster than a player can go", not "as slow as possible" — an
		// island 240 blocks tall at 0.35 was a long time watching yourself travel.
		assertTrue(Autopilot.SPEED <= 1.0, "faster than a player sprint-flying");
		assertTrue(Autopilot.ARRIVED >= 1.0, "it must stop before it is inside the target");
	}

	@Test
	void theWaypointRadiusGrowsWithTheSpeed() {
		// A fixed radius and a raised speed is how a router that works becomes one that clips every
		// corner: you must not cross the radius in fewer ticks than it takes to notice it.
		double near = Autopilot.waypointRadius(Autopilot.SPEED);
		assertTrue(near >= Autopilot.SPEED * 2,
			"a leg at cruise passes the waypoint before the next one is picked");
		assertEquals(Autopilot.WAYPOINT, Autopilot.waypointRadius(0.05), 0.0001,
			"crawling should keep the tight old radius");
	}

	// ---------------------------------------------------------------- the stale check
	//
	// THE ONE-FRAME-A-SECOND BUG. The route was invalidated by `walkRoute != flying` where
	// `walkRoute = !flying`, which is true whenever flying is true - so an A* ran EVERY TICK instead
	// of twice a second. Nothing about the routing or the steering was wrong and no state showed it:
	// the only symptom was the frame rate. Hence a pure predicate with tests on it.

	@Test
	void aFreshRouteIsNotImmediatelyStale() {
		BlockPos t = new BlockPos(10, 100, 0);
		assertFalse(Autopilot.needsRepath(t, t, Autopilot.REPATH_TICKS, true, true, 0),
			"re-routed on the tick after routing — this is the 1 FPS bug");
		assertFalse(Autopilot.needsRepath(t, t, Autopilot.REPATH_TICKS, false, false, 0),
			"...and the same while walking");
	}

	@Test
	void everyReasonToRepathIsHeldOffByTheFloor() {
		// The floor beats every other reason, so no future invalidation rule can bring back a
		// per-tick search. The destination moving is included: it moves when you finish a spot,
		// which is nowhere near five ticks.
		BlockPos a = new BlockPos(10, 100, 0), b = new BlockPos(90, 100, 0);
		int young = Autopilot.MIN_REPATH_TICKS - 1;
		assertFalse(Autopilot.needsRepath(a, b, -5, true, false, young), "ignored the floor");
	}

	@Test
	void itRepathsWhenTheDestinationMovesOrYouLand() {
		BlockPos a = new BlockPos(10, 100, 0), b = new BlockPos(90, 100, 0);
		int old = Autopilot.MIN_REPATH_TICKS + 1;
		assertTrue(Autopilot.needsRepath(a, b, 99, true, true, old), "the target moved");
		assertTrue(Autopilot.needsRepath(a, a, 99, true, false, old), "you landed");
		assertTrue(Autopilot.needsRepath(a, a, 0, true, true, old), "the timer expired");
		assertTrue(Autopilot.needsRepath(null, a, 99, true, true, old), "there was no route at all");
	}

	@Test
	void theWalkIsUnderASprint() {
		// It walks when it cannot fly, which is most of indoors. Vanilla walking is about 0.13
		// blocks per tick and sprinting about 0.17.
		assertTrue(Autopilot.WALK_SPEED <= 0.17, "faster than a sprint");
		assertTrue(Autopilot.WALK_SPEED > 0.0, "a walk that does not move is the bug being fixed");
		assertEquals(0.42, Autopilot.JUMP, 0.0001, "not the vanilla jump impulse");
	}

	// ---------------------------------------------------------------- the interruption doctrine
	//
	// These read the SOURCE, because what is being pinned is the absence of something. There is no
	// state to assert on: the failure mode is that a future session helpfully re-adds "any key hands
	// control back", which reads as a safety property and behaves as a fault - an unattended loop is
	// unattended precisely because you are typing in chat or looking at another window.

	/**
	 * Autopilot's source with the prose taken out.
	 *
	 * <p>Comments must not count. The first version of these tests matched the whole file and failed
	 * on the comments EXPLAINING why the key rule was removed — a check that forbids naming a thing
	 * forbids explaining it, and the explanation is the part worth keeping.
	 */
	private static String source() throws IOException {
		String src = Files.readString(Path.of("src/client/java/dev/jack/chunkscan/Autopilot.java"),
			StandardCharsets.UTF_8);
		src = src.replaceAll("(?s)/\\*.*?\\*/", " ");     // block comments and javadoc
		return src.replaceAll("//[^\\n]*", " ");           // line comments
	}

	@Test
	void theCommentStripperWorks() throws IOException {
		// Or the two checks below pass by reading an empty string, which is the classic way for a
		// source-level assertion to be quietly vacuous.
		assertTrue(source().contains("static void register()"), "stripped the code as well");
		assertFalse(source().contains("ARRIVING IS NOT DISARMING"), "did not strip comments");
	}

	@Test
	void noKeyDisarmsIt() throws IOException {
		// READING a key and DRIVING one are opposite things and the first version of this test
		// forbade both by name — which broke the moment the vertical moved onto space and shift.
		// What must never come back is the rule that a key press hands control away: an unattended
		// loop is unattended precisely because you are typing in chat or looking at another window.
		String src = source();
		assertFalse(src.contains("playerIsDriving"), "the key-disarm rule is back");
		assertFalse(src.contains("isDown()"),
			"Autopilot is reading the keyboard again, which is how it learns to give up");
		for (String key : new String[]{"keyUp", "keyLeft", "keyRight"}) {
			assertFalse(src.contains(key), "a movement-key rule is back in Autopilot: " + key);
		}
		// ...and it does press the two it is supposed to press.
		assertTrue(src.contains("keyJump.setDown") && src.contains("keyShift.setDown"),
			"the vertical is no longer driven by the keys");
	}

	@Test
	void chatDoesNotStopItButAChestDoes() throws IOException {
		// `Screens.anyOpen()` means chat, the map and the pause menu as well, and stopping for those
		// is what made "I opened chat and it parked" a bug. A container is the one screen worth
		// pausing for: flying off mid-withdrawal half-empties a chest and then blacklists it.
		String src = source();
		assertFalse(src.contains("Screens.anyOpen()"), "back to stopping for chat");
		assertTrue(src.contains("Screens.container() != null"), "it no longer pauses for a chest");
	}

	@Test
	void itStopsShortOfAChestBeforeTheLoopDecidesItHasArrived() {
		// TWO FILES, ONE DISTANCE. The autopilot stops flying at ARRIVED_SOLID; the loop starts the
		// withdrawal at Withdraw.REACH - 0.5. They measure slightly different things — an entity's
		// position against a block's — so equal thresholds are a race, and the losing outcome is a
		// loop that hovers at a chest for ever without opening it. That exact bug has been shipped
		// here once already, at 5.0 against 4.5.
		double loopFires = Withdraw.REACH - 0.5;
		assertTrue(Autopilot.ARRIVED_SOLID < loopFires - 0.5,
			"autofly stops at " + Autopilot.ARRIVED_SOLID + " and the loop only acts inside "
				+ loopFires + " — too close to call");
		assertTrue(Autopilot.ARRIVED_SOLID > Autopilot.ARRIVED,
			"a block cannot be flown into: it needs a looser radius than an open-air waypoint");
	}

	// ---------------------------------------------------------------- the void

	@Test
	void itNeverFliesItselfIntoTheGround() throws IOException {
		// THE REAL CAUSE of the flight that was lost mid-session. Speed was the obvious suspect
		// because it had just been raised, and it was innocent: it LANDED. Where flight is a plugin
		// grant rather than creative mode, touching the ground ends it — so the fix is never to
		// touch it, and the clearance is not optional decoration.
		assertTrue(Autopilot.GROUND_CLEAR >= 1.0, "less than a block of air is a landing waiting");
		assertTrue(Autopilot.RISE > 0, "it can sink onto a floor and never climb off");
		String src = source();
		assertTrue(src.contains("keepAirborne(mc, p, step)"),
			"the flying step no longer goes through the no-landing clamp");
		// The BEHAVIOUR cannot be tested without a client, so what is pinned is that the clamp is
		// still in the flying path and still reacts to the ground. Pinning the exact line was worse
		// than useless: it failed the moment the ceiling check was added, which was a fix.
		assertTrue(src.contains("p.onGround()") && src.contains("RISE"),
			"the clamp no longer does anything about touching down");
	}

	@Test
	void theSpeedDialIsBoundedByWhatAPlayerCanDo() {
		assertTrue(Autopilot.MAX_SPEED <= 1.0, "faster than a player sprint-flying");
		assertTrue(Autopilot.RISKY_SPEED < Autopilot.MAX_SPEED, "the warning can never fire");
	}

	@Test
	void buildingRequiresFlightAndOnlyAFetchMayWalk() throws IOException {
		// Jack's rule, and a better one than "walk whenever you cannot fly": where the loop BUILDS
		// is out over the work — the belly, the underside of the plate, a lowland eighty blocks
		// down — and on foot that is the air over the void. Where it FETCHES is a container somebody
		// walked to, which is a floor.
		String src = source();
		assertTrue(src.contains("if (!Hud.fetching())"),
			"walking is no longer gated on the trip being a fetch");
		assertTrue(src.contains("groundBelow"), "walking no longer checks there is a floor");
		assertTrue(src.contains("wasFlying && !flying"),
			"losing flight in mid-air is no longer treated as an emergency");
	}

	// ---------------------------------------------------------------- what it cannot see
	//
	// THE LOWLAND CRASH. `Nav` counts an unloaded chunk as PASSABLE on purpose — refusing to route
	// through one would fail every long flight on a 240-block island. The autopilot then flew that
	// route at cruise into blocks nobody had loaded yet. The lowland is the worst case by
	// construction: 150 blocks below the deck, so the whole descent is into chunks arriving on the
	// way down, and an absent chunk answers "air" to every question you ask it.

	/** A world with a floor at y=40 and nothing loaded below y=100. */
	private static Autopilot.View sky() {
		return new Autopilot.View() {
			public boolean loaded(int x, int y, int z) {
				return y >= 100;
			}

			public boolean solid(int x, int y, int z) {
				return y <= 40;
			}
		};
	}

	@Test
	void anUnloadedCellUnderYouCountsAsGround() {
		// Not as air. This is the opposite of what Nav does with an unloaded cell, and right for the
		// opposite reason: a router that stops at unseen chunks never leaves the island, and a
		// flight that descends into them lands on whatever arrives.
		// The number is the distance to the first thing that stops you, and an unloaded cell IS one.
		// What matters is that it lands inside the clearance, so keepAirborne refuses to descend.
		double air = Autopilot.clearanceBelow(sky(), 0.5, 101.0, 0.5, 4);
		assertTrue(air < Autopilot.GROUND_CLEAR,
			"read " + air + " of clear air below and would have descended into unseen chunks");
		// ...and deep inside the unloaded region it is zero: there is nothing under you but unknown.
		assertEquals(0.0, Autopilot.clearanceBelow(sky(), 0.5, 100.0, 0.5, 4), 0.001);
	}

	@Test
	void aLoadedDropStillReadsAsOpen() {
		// ...and the guard must not fire in mid-air over loaded void, or it can never descend at all
		// and the loop cannot reach anything below it.
		Autopilot.View allLoaded = new Autopilot.View() {
			public boolean loaded(int x, int y, int z) {
				return true;
			}

			public boolean solid(int x, int y, int z) {
				return y <= 40;
			}
		};
		assertEquals(4.0, Autopilot.clearanceBelow(allLoaded, 0.5, 200.0, 0.5, 4), 0.001,
			"refused to descend through open, loaded air");
		// and it finds a real floor
		assertEquals(1.9, Autopilot.clearanceBelow(allLoaded, 0.5, 42.9, 0.5, 4), 0.2,
			"did not measure the floor under it");
	}

	@Test
	void itWillNotFlyAtCruiseIntoChunksItHasNotGot() {
		Vec3 down = new Vec3(0, -1, 0);
		assertFalse(Autopilot.loadedAhead(sky(), new Vec3(0.5, 104, 0.5), down, Autopilot.SIGHT),
			"flew full speed into the unloaded lowland");
		assertTrue(Autopilot.loadedAhead(sky(), new Vec3(0.5, 200, 0.5), new Vec3(1, 0, 0),
			Autopilot.SIGHT), "crawled across open loaded sky for no reason");
	}

	@Test
	void theBlindSpeedIsSlowEnoughToStop() {
		// It has to be recoverable within the clearance: at BLIND_SPEED you cover less than
		// GROUND_CLEAR in the time it takes to notice a chunk has arrived.
		assertTrue(Autopilot.BLIND_SPEED < Autopilot.GROUND_CLEAR / 4,
			"too fast to stop inside the clearance once the world appears");
		assertTrue(Autopilot.BLIND_SPEED < Autopilot.SPEED, "not actually a slowdown");
		assertTrue(Autopilot.SIGHT >= 4, "looks too short a way ahead to react");
	}

	// ---------------------------------------------------------------- falling

	@Test
	void aFallIsToldApartFromADescent() {
		// Flying down on purpose must never trip the rescue, or every trip to the lowland ends with
		// the loop sending you home. What makes it a FALL is that you are not flying, not on the
		// ground, dropping fast, and there is nothing under you.
		assertTrue(Autopilot.isFalling(-1.2, false, false, false), "did not notice a fall");
		assertFalse(Autopilot.isFalling(-1.2, true, false, false), "a flight down is not a fall");
		assertFalse(Autopilot.isFalling(-1.2, false, true, false), "standing still is not a fall");
		assertFalse(Autopilot.isFalling(-1.2, false, false, true),
			"dropping onto a floor two blocks down is not a fall");
		assertFalse(Autopilot.isFalling(-0.1, false, false, false), "a drift is not a fall");
	}

	@Test
	void theRescueTriesTheFreeThingFirst() {
		// A double-tap of jump costs nothing and re-enters flight — when the server still says you
		// MAY fly. `/is` always works and moves you across the island, so it is the fallback rather
		// than the first move, and it is rate-limited because it is a teleport.
		assertTrue(Autopilot.TAP_GAP >= 2, "taps too close together to read as two presses");
		assertTrue(Autopilot.TAP_WAIT > Autopilot.TAP_GAP * 4,
			"gives up on the taps before they have had a chance to work");
		assertTrue(Autopilot.RESCUE_COOLDOWN >= 100, "would spam a teleport command");
	}

	@Test
	void theVerticalIsDrivenByTheKEYS() throws IOException {
		// Setting a y velocity works and works badly: travelFlying damps it every tick, so a
		// commanded climb arrives as a drift and the flight sinks toward whatever it was trying to
		// clear. Holding JUMP is how a player goes up and SHIFT is how they come down.
		String src = source();
		assertTrue(src.contains("keyJump.setDown"), "no longer presses space to climb");
		assertTrue(src.contains("keyShift.setDown"), "no longer presses shift to descend");
		// ...and lets go on every path that stops steering. A stuck key is worse than a stuck loop.
		assertTrue(src.contains("release(mc)"), "nothing releases the keys");
	}

	@Test
	void aBumpDoesNotStopTheSteering() throws IOException {
		// "it moves like 5 degrees and gets stuck": the collision handler returned before the aim,
		// so the yaw froze after one eased step; it nulled the route, which is checked BEFORE the
		// repath floor, so it ran a full A* every tick; and it backed off along the frozen yaw into
		// whatever was behind.
		String src = source();
		int bump = src.indexOf("boolean bumped = flying && p.horizontalCollision");
		assertTrue(bump > 0, "the collision branch is gone");
		int aim = src.indexOf("p.setYRot(approach");
		assertTrue(aim > bump, "the aim no longer happens after a bump is noticed");
		assertFalse(src.contains("dirBack"), "still backing off along a stale heading");
		assertTrue(Autopilot.STUCK_TICKS >= 20,
			"declares the route wrong before the climb has had time to clear the obstacle");
	}
}
