package dev.jack.chunkscan;

import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.minecraft.client.Minecraft;
import net.minecraft.client.player.LocalPlayer;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import net.minecraft.world.phys.Vec3;

/**
 * Fly the player to whatever the HUD is pointing at.
 *
 * <p><b>This is movement automation on a live server.</b> Most servers' rules treat it as a bot
 * whatever it is for, and smooth constant-velocity flight is the exact signature anticheat looks
 * for. That is a decision about Jack's account rather than about this code, so the code's job is to
 * be conservative — capped well under sprint-fly, steering rather than teleporting, and stoppable
 * in one word.
 *
 * <p><b>No key interrupts it.</b> The first version handed control back on any movement key, which
 * reads as a safety property and behaved as a fault: an unattended loop is unattended precisely
 * because you are typing in chat or looking at another window, and a key left down through a focus
 * change disarmed an hour of work silently. `/cscan stop` and `/cscan autofly off` are the off
 * switch. The one screen that pauses it is a CONTAINER, because flying away mid-withdrawal
 * half-empties a chest and then blacklists it.
 *
 * <p><b>It walks when it cannot fly.</b> Indoors is where the routing matters most and where flight
 * is least likely to be on, so falling back to "warn and do nothing" left the loop parked in exactly
 * the case it was built for.
 *
 * <p>It moves by setting delta movement, never by setting position. A position write is a teleport
 * and is both the thing anticheat catches and the thing that rubber-bands you into a wall.
 *
 * <p><b>It routes rather than aiming.</b> {@link Nav} finds a way through the world the client can
 * already see, and this steers at the next waypoint — which is the entire difference between going
 * through a doorway and pressing on the wall beside it. Flying at a bearing only ever worked in
 * open air, and on this island most destinations are inside something.
 */
final class Autopilot {
	/**
	 * Blocks per tick. Vanilla creative flight is about 0.4 and sprint-flight roughly 1.0.
	 *
	 * <p>Was 0.35 — under a plain creative fly, which on a 240-block island is a long time watching
	 * yourself travel. 0.75 is a brisk sprint-fly and still under what a player holding sprint does.
	 * Everything that makes speed safe is a function of it rather than a constant beside it: the
	 * waypoint radius, the approach taper and the corner crawl all scale, or going faster just means
	 * missing every turn.
	 */
	static final double SPEED = 0.75;
	/** Slowest worth having: below this you are watching a progress bar. */
	static final double MIN_SPEED = 0.10;
	/**
	 * Fastest allowed. Vanilla sprint-flight is about 1.0 and the cap is deliberately AT it rather
	 * than above: this is movement automation on a live server, and "no faster than a player can
	 * actually go" is the one bound that is defensible without knowing the server's rules.
	 */
	static final double MAX_SPEED = 1.0;

	private static double speed = SPEED;

	/** Cruise speed in blocks per tick. */
	static double speed() {
		return speed;
	}

	/** @return the speed actually set, after clamping. */
	static double setSpeed(double v) {
		speed = Math.max(MIN_SPEED, Math.min(MAX_SPEED, v));
		return speed;
	}
	/**
	 * Close enough to be standing at it.
	 *
	 * <p>Was 3.0, which is fine for a chest (reach 4.5) and too loose for a build station: the
	 * printer's slack over a bin's far corner is about a block, and stopping three blocks short of
	 * where you were sent spends it before you start. The approach taper is what stops this
	 * jittering, not the radius.
	 */
	static final double ARRIVED = 1.5;
	/**
	 * ...and how close is close enough when the destination is a BLOCK.
	 *
	 * <p>A chest cannot be flown into, so the tight radius above can never be satisfied and the
	 * flight would nose at its face for ever. This must stay comfortably INSIDE the distance at
	 * which {@link Hud} decides you have arrived and starts the withdrawal — they measure slightly
	 * different things (an entity's position against a block's), so equal thresholds are a race
	 * whose losing outcome is a loop that hovers at a chest and never opens it. Hud fires at
	 * {@code Withdraw.REACH - 0.5} = 4.0; this stops at 3.0.
	 */
	static final double ARRIVED_SOLID = 3.0;
	/** Ease the turn instead of snapping: a camera that jumps to a bearing is not a player. */
	static final float TURN_RATE = 0.18f;

	private static boolean on = false;
	private static boolean warnedNoRoute = false;
	private static boolean idleSaid = false;
	private static boolean announcedArrival = false;
	/** Ticks to wait before re-attempting a route that failed. See noRouteBackoff. */
	static final int NO_ROUTE_BACKOFF = 60;

	/** The current route, as waypoints. Empty means "fly straight and hope", which is the fallback. */
	private static java.util.List<BlockPos> path = new java.util.ArrayList<>();
	private static BlockPos pathTo = null;
	private static int repathIn = 0;
	/**
	 * Was the current route computed while FLYING? A change of stance invalidates it, because a
	 * walking route and a flying route are different routes.
	 *
	 * <p>Stored as the stance itself rather than as its negation. It was `walkRoute = !flying`
	 * compared against `walkRoute != flying`, which is true whenever flying is true — so the route
	 * was recomputed EVERY TICK instead of twice a second, and the client ran at one frame a second.
	 * A stale-check that is accidentally always-true is invisible: the routing is correct, the
	 * steering is correct, and the only symptom is the frame rate.
	 */
	private static boolean routedFlying = false;
	/** Is the current path a way AROUND something rather than a way to the goal? For the HUD. */
	private static boolean escaping = false;
	/**
	 * A hard floor on how often a search may run, whatever else asks for one.
	 *
	 * <p>Belt and braces after the above: no invalidation condition, present or future, can produce
	 * a per-tick A* again. The destination moving is the one thing worth an immediate re-route, and
	 * it moves when you finish a spot — twice a second is already far faster than that.
	 */
	static final int MIN_REPATH_TICKS = 5;
	private static int sinceRepath = 0;
	/** Recompute about twice a second: chunks load, doors open, and you drift. */
	static final int REPATH_TICKS = 10;
	/**
	 * Waypoint reached. TIGHT, because the opposite is what clips walls: at full speed the flight
	 * covers 1.75 blocks in five ticks, so a loose radius let it cut the corner it was steering to.
	 */
	static final double WAYPOINT = 1.0;

	/**
	 * Waypoint radius at the speed actually being flown.
	 *
	 * <p>A fixed radius and a raised speed is how a router that works becomes a router that clips
	 * every corner: at 0.75 blocks a tick you cross a 1.0 radius in under two ticks, so you are past
	 * the turn before the next waypoint is even selected. Two ticks of travel, floored at the old
	 * value.
	 */
	static double waypointRadius(double speed) {
		return Math.max(WAYPOINT, speed * 2.5);
	}
	/** Speed through a bend. A corridor turn taken at cruise is a corner clipped. */
	static final double CORNER_SPEED = 0.10;
	/** cos of the bend angle below which we treat it as a corner rather than a drift. */
	static final double CORNER_COS = 0.75;
	/**
	 * On foot. Vanilla walking is about 0.13 blocks/tick and sprinting about 0.17, so this is a
	 * brisk walk and nothing an observer would call impossible.
	 */
	static final double WALK_SPEED = 0.17;
	/** Vanilla jump impulse. Enough for one course, which is every step this island has. */
	static final double JUMP = 0.42;

	private Autopilot() {}

	static void register() {
		// Guarded, because a throw out of a tick event is a client CRASH, and this one runs every
		// tick for hours against a world other mods are changing. Losing a tick of steering is
		// nothing; losing the session is the thing being avoided.
		ClientTickEvents.END_CLIENT_TICK.register(mc -> {
			try {
				tick(mc);
			} catch (Exception e) {
				if (mc.player != null && !crashed) {
					crashed = true;
					mc.player.sendSystemMessage(Component.literal("[cscan] autofly hit " + e
						+ " — it will keep trying"));
				}
			}
		});
	}

	/** Said once per session, so a repeating fault does not become the chat. */
	private static boolean crashed = false;

	static boolean on() {
		return on;
	}

	/** Hard stop: drop the target, the route, and the motion. */
	static void halt(Minecraft mc) {
		on = false;
		path = new java.util.ArrayList<>();
		pathTo = null;
		routedFlying = false;
		sinceRepath = 0;
		announcedArrival = false;
		if (mc != null && mc.player != null) mc.player.setDeltaMovement(Vec3.ZERO);
	}

	/** Why autofly is not moving right now, or null if it is (or is off). */
	static String stalledBecause(Minecraft mc) {
		if (!on) return null;
		if (mc.player == null) return null;
		// A CONTAINER screen, not any screen. Chat, the map and the pause menu do not stop it — see
		// the note on tick(). Only a chest does, and only because flying away from one mid-withdrawal
		// is the one case where carrying on is actively wrong.
		if (Screens.container() != null) return "a container is open";
		if (Hud.target() == null) return "no destination — use goto or follow";
		return null;
	}

	/** What is carrying you right now, for the HUD: a route, a walk, or a guess. */
	static String mode(Minecraft mc) {
		// speed is part of the mode: it is a dial you can move, so it must be visible where you are
		// watching the thing it moves.
		boolean flying = mc.player != null && mc.player.getAbilities().flying;
		String how = flying ? "route" : "walk";
		String tail = String.format(" @%.2f", speed);
		if (path.isEmpty()) return (flying ? "direct" : "walk direct") + tail;
		return (escaping ? "round " : how + " ") + path.size() + tail;
	}

	static void set(boolean v) {
		// Every warning below is a once-per-arming shot. Without this reset, turning autofly off and
		// on again after it has already complained gets you silence instead of the reason.
		warnedNoRoute = false;
		idleSaid = false;
		announcedArrival = false;
		on = v;
		path = new java.util.ArrayList<>();
		pathTo = null;
		repathIn = 0;
	}

	/** How many waypoints are left, for the HUD. */
	static int waypoints() {
		return path.size();
	}

	/** Armed, but nothing has given us a destination. Explain, once. */
	private static void idle(Minecraft mc) {
		if (idleSaid || mc.player == null) return;
		idleSaid = true;
		mc.player.sendSystemMessage(Component.literal(
			"[cscan] autofly is ON but has nowhere to go — it flies to whatever `follow` or `goto` "
			+ "is pointing at. Try /cscan goto <x> <y> <z>, or /cscan follow <design>."));
	}

	private static void tick(Minecraft mc) {
		if (!on) return;
		LocalPlayer p = mc.player;
		if (p == null || mc.level == null) return;
		// A CONTAINER screen only. This used to be `Screens.anyOpen()`, which meant opening chat or
		// alt-tabbing away stopped the loop dead — and the whole point of an unattended loop is that
		// you are doing something else while it runs. A chest is the one screen worth pausing for,
		// because flying off mid-withdrawal is how you half-empty a chest and blacklist it.
		if (Screens.container() != null) return;

		BlockPos target = Hud.target();
		if (target == null) {
			// ARMED WITH NOWHERE TO GO. autofly is a MODIFIER, not an action: the destination comes
			// from `follow` or `goto`. Turned on by itself it used to report ON and then sit there
			// in silence, which is indistinguishable from broken. Say it once.
			idle(mc);
			return;
		}
		idleSaid = false;

		// ---- NO KEY STOPS THIS, and that is deliberate. The earlier rule was "any movement key
		// hands control back", which read as a safety property and behaved as a fault: a key left
		// down when the window loses focus, or a nudge while reading chat, silently disarmed an
		// hour-long unattended loop and left it parked. `/cscan stop` and `/cscan autofly off` are
		// the off switch, they are one word each, and they cannot be pressed by accident.
		Vec3 me = p.position();
		Vec3 to = Vec3.atCenterOf(target);
		double dist = me.distanceTo(to);
		// A SOLID DESTINATION IS ARRIVED AT FROM OUTSIDE IT. A chest is a block, so the tight radius
		// can never be satisfied and the flight would hover against its face trying — inside reach
		// the whole time, which is all the fetch needs, but visibly nosing at it.
		if (dist <= ARRIVED
			|| (dist <= ARRIVED_SOLID && mc.level.getBlockState(target).blocksMotion())) {
			// ARRIVING IS NOT DISARMING. The first version called stop(), which sets on=false — so
			// autofly switched itself off at the first chest and the unattended loop never flew
			// again. Hold still and stay armed; the next `guide()` moves the target and this
			// resumes on its own. Only the player taking over turns it off.
			arrive(mc);
			return;
		}

		// ON FOOT IS NOT A STALL. It used to warn and return here, so any destination reached by
		// walking — which on this island means anything indoors, where the loop routes you through a
		// doorway and then has no flight to finish with — simply stopped. It walks instead; see
		// walk() for the difference that makes to the ROUTE as well as to the steering.
		boolean flying = p.getAbilities().flying;

		// ---- ROUTE. Recomputed on a timer and whenever the destination moves, because the world
		// loads in around you and the plan's target changes as you build.
		if (pathTo != null && !pathTo.equals(target)) announcedArrival = false;
		sinceRepath++;
		repathIn--;
		if (needsRepath(pathTo, target, repathIn, routedFlying, flying, sinceRepath)) {
			// A WALKING ROUTE IS A DIFFERENT ROUTE. Clearance alone sends you along a line of air
			// above a floor, which flies beautifully and walks into a hole.
			Nav.Passable free = flying ? Nav.of(mc.level) : Nav.standable(mc.level);
			BlockPos here = p.blockPosition();
			java.util.List<BlockPos> raw = Nav.route(free, here, target);
			if (raw.isEmpty() && !flying) {
				// No footing all the way there. The flying route at least has the right doorways in
				// it, and walking it gets as far as the ground allows rather than nowhere at all.
				free = Nav.of(mc.level);
				raw = Nav.route(free, here, target);
			}
			// NO ROUTE IS NOT A REASON TO FLY AT THE WALL. Getting round an obstacle is a search,
			// not a nudge: flood outward and take the reachable cell that gets closest to the goal —
			// up, down, left, right, behind, whichever actually helps. Re-run every repath it is a
			// wall-follower that keeps making progress, and this island is nothing but walls.
			escaping = false;
			if (raw.isEmpty()) {
				raw = Nav.escape(free, here, target, Nav.ESCAPE_RADIUS);
				escaping = !raw.isEmpty();
			}
			path = raw.isEmpty() ? new java.util.ArrayList<>()
				: new java.util.ArrayList<>(Nav.loosen(free, here, Nav.simplify(free, here, raw)));
			pathTo = target;
			routedFlying = flying;
			sinceRepath = 0;
			// A FAILED SEARCH IS THE EXPENSIVE ONE. When a route exists A* finds it in a few
			// hundred nodes; when there is none it burns the whole 12,000-node budget, and at
			// REPATH_TICKS that is millions of block lookups a second on the client thread for as
			// long as the target stays unreachable. Back off hard on failure, stay responsive on
			// success.
			// An ESCAPE is stale as soon as you have flown it: the whole point is to look again from
			// somewhere new. Only a total failure earns the long backoff.
			repathIn = raw.isEmpty() ? NO_ROUTE_BACKOFF : REPATH_TICKS;
		}

		// Steer at the next waypoint rather than at the destination: that is the whole difference
		// between going through the door and pressing on the wall beside it.
		Vec3 aim = to;
		double near = waypointRadius(flying ? speed : WALK_SPEED);
		while (!path.isEmpty() && me.distanceTo(Vec3.atCenterOf(path.get(0))) <= near) {
			path.remove(0);
		}
		if (!path.isEmpty()) aim = Vec3.atCenterOf(path.get(0));

		// ---- aim
		Vec3 dir = aim.subtract(me).normalize();
		float wantYaw = (float) Math.toDegrees(Math.atan2(-dir.x, dir.z));
		// Level on foot. A walking player does not stare at the floor to walk toward it, and the
		// look angle is sent to the server.
		float wantPitch = flying ? (float) Math.toDegrees(-Math.asin(dir.y)) : 0f;
		p.setYRot(approach(p.getYRot(), wantYaw));
		p.setXRot(approach(p.getXRot(), wantPitch));

		// ---- go. Slow into the target so the last few blocks are not an overshoot and a wobble.
		// The walk scales with the same dial, because a speed setting that only changes flight is a
		// setting that stops working the moment you go indoors — which is where you would most want
		// to slow it down. Capped at a sprint either way: legs are legs.
		double cruise = flying ? speed : Math.min(WALK_SPEED, WALK_SPEED * speed / SPEED);
		double speed = Math.min(cruise, dist / 8.0 + 0.05);

		// SLOW INTO A BEND. Movement is set directly along `dir`, so the eased turn is cosmetic and
		// nothing was actually limiting the speed at which it entered a corner. A doorway taken at
		// cruise is a doorway missed: check the angle between this leg and the next, and crawl
		// through anything that is not roughly straight ahead.
		if (path.size() >= 2) {
			Vec3 nextLeg = Vec3.atCenterOf(path.get(1)).subtract(aim).normalize();
			if (dir.dot(nextLeg) < CORNER_COS) speed = Math.min(speed, CORNER_SPEED);
		}
		// ...and never arrive at a waypoint faster than we can notice it.
		double toWaypoint = me.distanceTo(aim);
		if (toWaypoint < near * 3) speed = Math.min(speed, Math.max(0.06, toWaypoint / 12.0));

		if (path.isEmpty()) {
			// Neither a route nor a way round: shut in, or the goal is sealed. Say so once, because
			// "it is routing" and "it is guessing" behave very differently around a building and you
			// should know which one is carrying you.
			if (!warnedNoRoute) {
				warnedNoRoute = true;
				p.sendSystemMessage(Component.literal("[cscan] no route and no way round — going"
					+ " direct. If it is sealed or far, get closer and it will re-route."));
			}
		} else {
			warnedNoRoute = false;
		}

		if (flying) {
			Vec3 step = dir.scale(speed);
			// Only ever applied to the DIRECT guess. A real route is already clear, and second-
			// guessing it here is how you fight your own pathfinder at a doorway.
			if (path.isEmpty()) step = unstick(mc, p, step);
			p.setDeltaMovement(step);
		} else {
			walk(p, dir, aim, speed);
		}
	}

	/**
	 * Take the components out of a direct guess that press into a block.
	 *
	 * <p>The old version added a little upward velocity while keeping full forward speed, which does
	 * not lift you over anything — it grinds you along the wall at an angle. Zeroing the axis that is
	 * blocked lets the others carry you, so a ceiling slides you sideways and a wall slides you up,
	 * which is what "go round it" looks like when you have no route to follow.
	 */
	private static Vec3 unstick(Minecraft mc, LocalPlayer p, Vec3 step) {
		Vec3 at = p.position();
		double x = step.x, y = step.y, z = step.z;
		if (y > 0 && solid(mc, at.x, at.y + 2.3, at.z)) y = 0;          // ceiling
		if (y < 0 && solid(mc, at.x, at.y - 0.4, at.z)) y = 0;          // floor
		// Horizontal, tested at the feet AND the head: a step over a fence and a duck under a lintel
		// are different failures and only checking one of them finds neither.
		if (x != 0 && (solid(mc, at.x + Math.signum(x) * 0.9, at.y + 0.2, at.z)
			|| solid(mc, at.x + Math.signum(x) * 0.9, at.y + 1.6, at.z))) x = 0;
		if (z != 0 && (solid(mc, at.x, at.y + 0.2, at.z + Math.signum(z) * 0.9)
			|| solid(mc, at.x, at.y + 1.6, at.z + Math.signum(z) * 0.9))) z = 0;
		// Everything blocked: rise. Better than vibrating against a corner, and the next repath sees
		// a different vantage.
		if (x == 0 && y == 0 && z == 0) y = speed * 0.5;
		return new Vec3(x, y, z);
	}

	private static boolean solid(Minecraft mc, double x, double y, double z) {
		return mc.level.getBlockState(BlockPos.containing(x, y, z)).blocksMotion();
	}

	/**
	 * Steer on foot.
	 *
	 * <p>Three differences from flying, and all three are the ground:
	 *
	 * <ul>
	 *   <li><b>Only the horizontal is ours.</b> The vertical belongs to gravity, so the existing
	 *       y velocity is carried through untouched — write a y here and you either hover or you
	 *       drive yourself into the floor.</li>
	 *   <li><b>A step up is a JUMP.</b> Collision handles a slab or a stair on its own (that is what
	 *       the 0.6 step height is), but a full block needs the impulse. Fired on horizontal
	 *       collision or when the next waypoint is genuinely above you — the first is the honest
	 *       signal and the second is what gets you onto a stair before you have bumped it.</li>
	 *   <li><b>Never mid-air.</b> Jumping while already falling does nothing except look wrong to a
	 *       server, so it is gated on {@code onGround()}.</li>
	 * </ul>
	 */
	private static void walk(LocalPlayer p, Vec3 dir, Vec3 aim, double speed) {
		Vec3 flat = new Vec3(dir.x, 0, dir.z);
		if (flat.lengthSqr() < 1.0e-6) {
			// Straight up or straight down: no heading to walk in. Jump if the way out is upward,
			// otherwise stand still and let the next repath find a floor route.
			if (aim.y > p.getY() + 0.5 && p.onGround()) {
				p.setDeltaMovement(new Vec3(0, JUMP, 0));
			}
			return;
		}
		flat = flat.normalize();
		Vec3 v = p.getDeltaMovement();
		double y = v.y;
		boolean stepUp = aim.y > p.getY() + 0.6;
		if (p.onGround() && (p.horizontalCollision || stepUp)) y = JUMP;
		p.setDeltaMovement(flat.x * speed, y, flat.z * speed);
	}

	/**
	 * Is the route stale?
	 *
	 * <p>Pure, and separate, because the bug it replaces could not be seen in any state: an
	 * always-true stale check routes correctly and steers correctly, and the only thing it changes
	 * is how many times a second the client runs an A*.
	 */
	static boolean needsRepath(BlockPos pathTo, BlockPos target, int repathIn,
	                           boolean routedFlying, boolean flying, int sinceRepath) {
		if (pathTo == null) return true;                       // nothing to be stale
		if (sinceRepath < MIN_REPATH_TICKS) return false;      // floor beats every reason below
		if (!pathTo.equals(target)) return true;               // it moved
		if (routedFlying != flying) return true;               // you took off, or landed
		return repathIn <= 0;                                  // the timer
	}

	/** Shortest-way-round easing between two angles. */
	static float approach(float from, float to) {
		float d = to - from;
		while (d <= -180) d += 360;
		while (d > 180) d -= 360;
		return from + d * TURN_RATE;
	}

	/** At the target: kill the drift but stay armed for the next leg. */
	private static void arrive(Minecraft mc) {
		if (mc.player != null) mc.player.setDeltaMovement(Vec3.ZERO);
		path = new java.util.ArrayList<>();
		pathTo = null;
		if (!announcedArrival) {
			announcedArrival = true;
			// Not while following. The loop re-aims at the work every time a few blocks go in, so
			// this fired every couple of seconds for a whole session - and the HUD says it anyway.
			// It is worth saying exactly once: when a person sent you somewhere with `goto`.
			if (mc.player != null && !Hud.following()) {
				mc.player.sendSystemMessage(Component.literal("[cscan] arrived — autofly still on"));
			}
		}
	}

	/**
	 * The only way it turns itself off is being told to.
	 *
	 * <p>There was a {@code stop(why)} here that {@code playerIsDriving} called, and removing the
	 * key rule left it with no callers — which is the honest shape of the decision: nothing the
	 * player does WHILE playing disarms this any more. {@link #halt} is the off switch and
	 * `/cscan stop` is the word.
	 */
}
