package dev.jack.chunkscan;

import net.minecraft.core.BlockPos;
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
		String src = source();
		for (String key : new String[]{"keyUp", "keyDown", "keyLeft", "keyRight", "keyJump",
			"keyShift", "playerIsDriving"}) {
			assertFalse(src.contains(key), "a key rule is back in Autopilot: " + key);
		}
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
}
