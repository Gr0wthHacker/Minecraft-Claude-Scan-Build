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
import static org.junit.jupiter.api.Assertions.assertSame;
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
		// It used to need a LOOSER radius than an open-air waypoint, because that one was tight at
		// 1.5. With the open-air radius raised to 3 on the "get within 3 blocks" rule they are the
		// same number, and what still has to hold is that neither of them is outside the distance
		// the loop acts at.
		assertTrue(Autopilot.ARRIVED_SOLID >= Autopilot.ARRIVED,
			"a block cannot be flown into: its radius may never be the tighter of the two");
		assertTrue(Autopilot.ARRIVED < loopFires,
			"the flight stops further out than the loop is willing to act from");
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
	void theJumpKeyIsNeverUsedToCLIMB() throws IOException {
		// THE MOD REVOKED ITS OWN FLIGHT. Vanilla toggles flying on a DOUBLE TAP of jump - a
		// seven-tick window opened by the first press - and driving the key to climb presses and
		// releases it as the desired vertical crosses a deadzone. Inside seven ticks that is a
		// double tap, so it turned off its own flight, fell, and reported the fall as though
		// something had been done to it.
		String src = source();
		assertFalse(src.contains("vertical(mc"), "the climb is driving the flight toggle again");
		// the key work that remains is the rescue, where toggling flight is the POINT
		int rescue = src.indexOf("private static boolean rescue(");
		assertTrue(rescue > 0);
		assertTrue(src.indexOf("keyJump.setDown") < rescue || src.contains("hold(mc, true, false)"),
			"jump is pressed somewhere other than the rescue");
		assertTrue(src.contains("release(mc)"), "nothing releases the keys");
	}

	@Test
	void theVerticalSurvivesFlightFriction() {
		// travelFlying damps a set y velocity every tick, so the naive version arrives as a drift
		// and the flight sinks toward the thing it is trying to clear. Scaled, not pressed.
		assertTrue(Autopilot.VERTICAL_GAIN > 1.0, "a commanded climb will be damped away");
		Vec3 lifted = Autopilot.liftFor(new Vec3(0.1, 0.2, 0.1), 1.0);
		assertTrue(lifted.y > 0.2, "the vertical was not scaled at all");
		assertEquals(0.1, lifted.x, 1e-9, "the horizontal must not be touched");
		assertEquals(0.5, Autopilot.liftFor(new Vec3(0, 9.0, 0), 0.5).y, 1e-9, "not clamped");
	}

	@Test
	void itNeverClimbsIntoACeiling() throws IOException {
		// Every upward push in that file - the ground clearance, the bump handler, the unstick -
		// pushes y up, and with something directly overhead that is a body grinding along the
		// underside of a floor for as long as it is there.
		String src = source();
		assertTrue(src.contains("if (!headroom) step = new Vec3(step.x, Math.min(step.y, 0), step.z);"),
			"the climb is no longer clamped by what is overhead");
	}

	@Test
	void aPlaceToWorkFromHasAirUnderIt() {
		// Jack: "it cant be within 1 block beneath when flying to place because it will auto stop
		// flying". Whatever the plugin measures, it looks further down than the block you touch.
		assertTrue(Nav.AIR_BELOW >= 2, "a standing spot one block off the floor ends the flight");
		assertTrue(Autopilot.GROUND_CLEAR > Nav.AIR_BELOW - 1,
			"the flight would descend below the altitude the standoff was chosen for");
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

	@Test
	void aFallBelowTheDeckGoesStraightHome() {
		// Jack's rule, and the geometry backs it: the plate is Y201 and the deck Y190-199, so above
		// the line you are falling with island under you and a double-tap has time to work and
		// something to land on. Below it, what is beneath you is the void — the taps cost a third of
		// a second and buy nothing, because if flight were available you would not be falling.
		assertTrue(Autopilot.goHomeAtOnce(60), "took the slow route with the void underneath");
		assertTrue(Autopilot.goHomeAtOnce(-20), "below the world and still trying to tap");
		assertFalse(Autopilot.goHomeAtOnce(195), "teleported home from a trip on the deck");
		assertTrue(Autopilot.PANIC_BELOW_Y < 190,
			"the line is above the deck, so working there would teleport you home");
	}

	// ---------------------------------------------------------------- getting round it

	private static final Vec3 EAST = new Vec3(1, 0, 0);

	@Test
	void aBlockedWayOutSlidesSIDEWAYSFirst() {
		// Sliding along a face is how you get round the end of it, and it keeps whatever progress
		// the bump did not eat. Climbing was the old answer to everything.
		Vec3 out = Autopilot.sidestep(EAST, true, true, true, true, true);
		assertEquals(0.0, out.y, 1e-9, "climbed when it could have gone round");
		assertTrue(Math.abs(out.z) > 0.9, "did not step to the side of an eastward heading");
	}

	@Test
	void withTheSidesBlockedItClimbs() {
		Vec3 out = Autopilot.sidestep(EAST, true, true, false, false, true);
		assertEquals(1.0, out.y, 1e-9);
	}

	@Test
	void aCEILINGSendsItDown() {
		// The case the old handler could not express at all: it climbed into the thing that was
		// already on its head, and kept climbing. Down is the correct answer to an overhang, and to
		// a climb that is what wedged you in the first place.
		Vec3 out = Autopilot.sidestep(EAST, false, true, false, false, true);
		assertEquals(-1.0, out.y, 1e-9, "still trying to climb through a ceiling");
	}

	@Test
	void backwardsIsTheLastResortAndBoxedInIsNotACrash() {
		Vec3 back = Autopilot.sidestep(EAST, false, false, false, false, true);
		assertTrue(back.x < -0.9, "did not back out when that was the only way");
		Vec3 nothing = Autopilot.sidestep(EAST, false, false, false, false, false);
		assertEquals(1.0, nothing.y, 1e-9, "boxed in: up is the least-bad guess, not an exception");
	}

	@Test
	void aStraightUpHeadingStillHasASideToStepTo() {
		// dir can be almost vertical when the target is directly above; the sideways vector must not
		// come out as a zero-length nothing.
		Vec3 out = Autopilot.sidestep(new Vec3(0, 1, 0), true, true, true, true, true);
		assertTrue(out.length() > 0.9, "produced no direction at all");
	}

	@Test
	void aBumpLooksForARouteRoundBeforeReachingForAnInstinct() throws IOException {
		String src = source();
		assertTrue(src.contains("Nav.escape(free, here, target, BUMP_LOOK)"),
			"a bump no longer asks the geometry for a way round");
		assertTrue(Autopilot.BUMP_LOOK_EVERY > 1,
			"a flood on every tick of contact is the cost this file has already paid twice");
	}

	// ---------------------------------------------------------------- getting flight back

	@Test
	void itTriesToGetFlightBackRatherThanStandingThereBeingSafe() {
		// Losing flight is not the end of the job. The walk gate stops the loop doing anything
		// DANGEROUS without it, and stopping there is only right if nothing can be done — and
		// usually something can: the same double tap that rescues a fall turns it back on.
		assertTrue(Autopilot.canRegainFlight(false, true, true), "did not try");
		assertFalse(Autopilot.canRegainFlight(true, true, true), "already flying");
		assertFalse(Autopilot.canRegainFlight(false, false, true),
			"the server says no; tapping will not change its mind");
		assertFalse(Autopilot.canRegainFlight(false, true, false),
			"nowhere to be — hopping on the spot is not a feature");
	}

	@Test
	void itGivesUpTryingAfterAFewGoes() {
		// A tap that does not work will not work the fortieth time either, and a player watching
		// their character hop twice a second is watching a bug.
		assertTrue(Autopilot.REGAIN_GIVE_UP >= 2 && Autopilot.REGAIN_GIVE_UP <= 10,
			"either gives up before it has tried or never gives up");
		assertTrue(Autopilot.REGAIN_EVERY >= 20, "would hop on the spot");
	}

	@Test
	void aTargetBELOWYouEscapesDOWNWARDS() {
		// The whole point of scoring instead of laddering. `down` used to sit under `up`, so it was
		// only ever taken when climbing was blocked - and on this island most of the work is BELOW
		// you: the lowland, the belly, half the deck. Every bump on the way there went the wrong way
		// over the obstacle.
		Vec3 downhill = new Vec3(0.3, -0.95, 0).normalize();
		Vec3 out = Autopilot.sidestep(downhill, true, true, true, true, true);
		assertEquals(-1.0, out.y, 1e-9, "climbed over an obstacle while heading down: " + out);
	}

	@Test
	void aTargetABOVEYouEscapesUPWARDS() {
		Vec3 uphill = new Vec3(0.3, 0.95, 0).normalize();
		assertEquals(1.0, Autopilot.sidestep(uphill, true, true, true, true, true).y, 1e-9);
	}

	@Test
	void aLevelHeadingStillPrefersToSlide() {
		// A perpendicular scores zero against a level aim whichever way it points, so without the
		// thumb on the scale a level heading would pick whichever direction happened to be first.
		Vec3 out = Autopilot.sidestep(new Vec3(1, 0, 0), true, true, true, true, true);
		assertEquals(0.0, out.y, 1e-9);
		assertTrue(Autopilot.SIDE_BIAS > 0 && Autopilot.SIDE_BIAS < 0.5,
			"either no preference for sliding, or so much that it never leaves the wall");
	}

	@Test
	void theDescentMayUseSHIFTBecauseSneakTogglesNothing() throws IOException {
		// Only JUMP toggles flight. Sneak is safe, stronger than a damped y velocity, and is what a
		// player does - so the movement path is handed `sink`, which cannot press jump at all.
		String src = source();
		assertTrue(src.contains("sink(mc, step.y < -CLIMB_DEADZONE)"),
			"the descent no longer uses the key it safely can");
		int sink = src.indexOf("private static void sink(");
		assertTrue(sink > 0 && !src.substring(sink, sink + 400).contains("keyJump"),
			"sink can press jump, which is the key that turned off flight in mid-air");
	}

	// ---------------------------------------------------------------- threading a one-wide gap

	private static final boolean[] SHAFT = {true, false, true};    // x and z walled, y open

	@Test
	void offToOneSideOfAShaftItStraightensBeforeGoingDown() {
		// The route through a one-wide shaft is found - Nav models a 0.8-wide body and the island is
		// full of them. What failed is the FLYING: steering at the waypoint centre from off to one
		// side arrives at the mouth still carrying that drift, catches the lip, and bumps.
		Vec3 me = new Vec3(10.0, 100.0, 10.0);            // 0.5 off in x and z
		Vec3 centre = new Vec3(10.5, 95.5, 10.5);
		Vec3 wanted = new Vec3(0, -0.35, 0);              // "go down the shaft"
		Vec3 out = Autopilot.align(me, centre, SHAFT, wanted, Autopilot.ALIGN_TOL, 0.1);
		assertEquals(0.0, out.y, 1e-9, "went down the hole while still beside it");
		assertTrue(out.x > 0 && out.z > 0, "did not move toward the middle of the shaft");
	}

	@Test
	void linedUpItCarriesOn() {
		Vec3 me = new Vec3(10.45, 100.0, 10.52);          // within tolerance
		Vec3 centre = new Vec3(10.5, 95.5, 10.5);
		Vec3 wanted = new Vec3(0, -0.35, 0);
		assertSame(wanted, Autopilot.align(me, centre, SHAFT, wanted, Autopilot.ALIGN_TOL, 0.1),
			"kept fiddling with the alignment instead of flying");
	}

	@Test
	void anOpenAxisIsNeverCorrectedFor() {
		// Only the walled lanes matter. Correcting the open one would drag the flight to the middle
		// of every corridor it passes down, which is not alignment, it is a detour.
		Vec3 me = new Vec3(10.0, 130.0, 10.0);
		Vec3 centre = new Vec3(10.5, 95.5, 10.5);
		Vec3 out = Autopilot.align(me, centre, SHAFT, new Vec3(0, -0.35, 0), Autopilot.ALIGN_TOL, 0.1);
		assertEquals(0.0, out.y, 1e-9, "corrected along the axis it was free to travel");
	}

	@Test
	void nothingWalledMeansNothingToLineUpWith() {
		Vec3 wanted = new Vec3(0.3, 0, 0.1);
		assertSame(wanted, Autopilot.align(new Vec3(0, 0, 0), new Vec3(9, 9, 9),
			new boolean[] {false, false, false}, wanted, Autopilot.ALIGN_TOL, 0.1));
	}

	@Test
	void theCorrectionIsNeverBiggerThanTheErrorOrTheSpeed() {
		// Overshooting the centre of a one-wide shaft puts you against the other wall, which is the
		// same bump from the other side.
		Vec3 out = Autopilot.align(new Vec3(10.48, 100, 10.0), new Vec3(10.5, 100, 10.5), SHAFT,
			new Vec3(0, -0.35, 0), 0.05, 0.9);
		assertTrue(out.length() <= 0.51, "corrected further than it was out: " + out.length());
	}

	@Test
	void aTightGapIsFlownSlowly() {
		assertTrue(Autopilot.TIGHT_SPEED < Autopilot.SPEED,
			"threads a one-wide gap at cruise, which is how you catch the lip");
		assertTrue(Autopilot.ALIGN_TOL < 0.5,
			"tolerance is half a block: it would call any position in the cell lined up");
	}

	// ---------------------------------------------------------------- flying the segment

	@Test
	void offTheLineItSteersBackOntoIt() {
		// `clear` validated waypoint-to-WAYPOINT. What gets flown is wherever-I-am to waypoint, so
		// the moment drift or a bump puts the body off that line, the leg being flown is a chord
		// across whatever the route was going round. This is the structural cause of the bumping,
		// underneath every heuristic bolted on after the contact.
		Vec3 from = new Vec3(0, 100, 0), to = new Vec3(20, 100, 0);
		Vec3 drifted = new Vec3(10, 100, 3);              // three blocks off the corridor
		Vec3 aim = Autopilot.pursue(drifted, from, to, Autopilot.LOOKAHEAD);
		assertTrue(Math.abs(aim.z) < 1e-6, "aimed off the validated line");
		assertTrue(aim.x > 10 && aim.x <= 20, "did not look ahead along the leg: " + aim);
	}

	@Test
	void onTheLineItJustCarriesOn() {
		Vec3 from = new Vec3(0, 100, 0), to = new Vec3(20, 100, 0);
		Vec3 aim = Autopilot.pursue(new Vec3(5, 100, 0), from, to, Autopilot.LOOKAHEAD);
		assertEquals(5 + Autopilot.LOOKAHEAD, aim.x, 1e-6);
	}

	@Test
	void theLookaheadNeverOvershootsTheWaypoint() {
		// Looking past the end of a leg is looking through whatever the corner was avoiding.
		Vec3 from = new Vec3(0, 100, 0), to = new Vec3(4, 100, 0);
		Vec3 aim = Autopilot.pursue(new Vec3(3.8, 100, 0), from, to, 5.0);
		assertEquals(4.0, aim.x, 1e-6, "looked past the corner");
	}

	@Test
	void behindTheStartItComesBackToTheLegRatherThanCuttingAcross() {
		Vec3 from = new Vec3(0, 100, 0), to = new Vec3(20, 100, 0);
		Vec3 aim = Autopilot.pursue(new Vec3(-5, 100, 4), from, to, Autopilot.LOOKAHEAD);
		assertTrue(aim.x >= 0 && Math.abs(aim.z) < 1e-6, "cut the corner from behind the leg");
	}

	@Test
	void aZeroLengthLegIsNotADivisionByZero() {
		Vec3 at = new Vec3(3, 100, 3);
		assertEquals(at, Autopilot.pursue(new Vec3(0, 0, 0), at, at, 1.5));
	}

	@Test
	void theRoutePrefersTheWorldThatKeepsItsDistance() throws IOException {
		String src = source();
		assertTrue(src.contains("Nav.roomyBetween(mc.level, here, target)"),
			"no longer tries for a route that keeps off the surfaces");
		int roomy = src.indexOf("Nav.roomyBetween(mc.level");
		int tight = src.indexOf("if (raw.isEmpty()) raw = Nav.route(free, here, target);");
		assertTrue(tight > roomy, "the tight route is no longer the FALLBACK");
	}

	// ---------------------------------------------------------------- how fast, and why not faster

	@Test
	void aLongOpenFlightRunsAtCRUISE() {
		// THE HALF-SPEED BUG. The approach taper was fed the pure-pursuit point, which sits
		// LOOKAHEAD blocks ahead by construction — so a two-hundred-block flight was told it had 1.5
		// blocks to go on every tick and ran the whole way at 0.125 against a cruise of 0.75.
		double near = Autopilot.waypointRadius(Autopilot.SPEED);
		double v = Autopilot.cruiseSpeed(Autopilot.SPEED, 200, 40, near, false);
		assertEquals(Autopilot.SPEED, v, 1e-9, "crawled across open air");
	}

	@Test
	void aPursuitPointAheadOfYouIsNotAnArrival() {
		// The same thing said the other way round: the number that must NOT be passed in is the
		// distance to the aim.
		double near = Autopilot.waypointRadius(Autopilot.SPEED);
		double wrong = Autopilot.cruiseSpeed(Autopilot.SPEED, 200, Autopilot.LOOKAHEAD, near, false);
		assertTrue(wrong < Autopilot.SPEED / 2, "control: feeding it the aim really does crawl");
		assertTrue(Autopilot.cruiseSpeed(Autopilot.SPEED, 200, 40, near, false) > wrong * 3,
			"the waypoint distance is not what is being measured");
	}

	@Test
	void itStillSlowsForTheDestinationAndForABend() {
		double near = Autopilot.waypointRadius(Autopilot.SPEED);
		assertTrue(Autopilot.cruiseSpeed(Autopilot.SPEED, 2, 40, near, false) < Autopilot.SPEED,
			"arrived at the destination at full speed");
		assertEquals(Autopilot.CORNER_SPEED,
			Autopilot.cruiseSpeed(Autopilot.SPEED, 200, 40, near, true), 1e-9,
			"took a corner at cruise");
	}

	@Test
	void itNeverStopsShortOfWhereItIsGoing() {
		// A taper that reaches zero is a flight hovering a block short for ever. It bottoms out at
		// 0.05 rather than the 0.06 corner floor — the destination taper is the tighter of the two
		// at nil distance — and that is only reachable in a test: ARRIVED fires three blocks out.
		double near = Autopilot.waypointRadius(Autopilot.SPEED);
		assertTrue(Autopilot.cruiseSpeed(Autopilot.SPEED, 0, 0, near, true) > 0,
			"the flight can come to a dead stop before arriving");
		assertTrue(Autopilot.cruiseSpeed(Autopilot.SPEED, Autopilot.ARRIVED, 40, near, false) > 0.3,
			"already crawling at the distance it is allowed to stop at");
	}

	// ---------------------------------------------------------------- how close to get

	@Test
	void inOpenAirItFloatsRightUpToTheWork() {
		// Three blocks is a CEILING, not a target: three blocks of standoff is three blocks off the
		// far corner of the bin, and the printer's reach has to cover both. Jack: "if we always are
		// 3 blocks its hard to reach all blocks since we lose 3 blocks to air".
		assertFalse(Autopilot.hasArrived(2.6, 0, Autopilot.ARRIVE_MIN, Autopilot.ARRIVED,
			Autopilot.CLOSING_PATIENCE, false), "settled for three blocks with room to close");
		assertTrue(Autopilot.hasArrived(1.1, 0, Autopilot.ARRIVE_MIN, Autopilot.ARRIVED,
			Autopilot.CLOSING_PATIENCE, false), "kept closing past the point of any use");
	}

	@Test
	void aWallInFrontMeansThisIsAsCloseAsItGets() {
		// The balance Jack asked for: reach is worth having and it is not worth CONTACT. On this
		// server touching a block ends flight, and a flight is worth more than the block it was
		// reaching for.
		assertTrue(Autopilot.hasArrived(2.6, 0, Autopilot.ARRIVE_MIN, Autopilot.ARRIVED,
			Autopilot.CLOSING_PATIENCE, true), "pressed on into a surface to gain a block of reach");
		// ...but only when already close enough to be useful. A wall five blocks out is an obstacle,
		// not an arrival.
		assertFalse(Autopilot.hasArrived(9.0, 99, Autopilot.ARRIVE_MIN, Autopilot.ARRIVED,
			Autopilot.CLOSING_PATIENCE, true), "gave up nine blocks out and called it arrived");
	}

	@Test
	void stoppingGettingNearerCountsAsArriving() {
		// "The actual space after stopping fly." A flight wedged against a shelf 2.4 blocks from the
		// work has arrived; waiting for 1.2 there is waiting for ever.
		assertFalse(Autopilot.hasArrived(2.4, 2, Autopilot.ARRIVE_MIN, Autopilot.ARRIVED,
			Autopilot.CLOSING_PATIENCE, false), "gave up after two ticks of no progress");
		assertTrue(Autopilot.hasArrived(2.4, Autopilot.CLOSING_PATIENCE, Autopilot.ARRIVE_MIN,
			Autopilot.ARRIVED, Autopilot.CLOSING_PATIENCE, false), "waited for ever");
	}

	@Test
	void theCeilingAndTheFloorAreTheRightWayRound() {
		assertTrue(Autopilot.ARRIVE_MIN < Autopilot.ARRIVED, "the floor is above the ceiling");
		assertTrue(Autopilot.ARRIVE_MIN > 0.5, "would try to occupy the same cell as the work");
		assertTrue(Autopilot.SAFE_GAP >= 1.0, "leaves less than a block of air before a surface");
	}
}
