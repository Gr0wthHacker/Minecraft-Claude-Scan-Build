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
	 * <p><b>This was dropped to 0.35 for a reason that turned out to be wrong.</b> Flight was lost
	 * in mid-air on the first real run and speed was the obvious suspect — it had just been raised.
	 * It was not: Jack watched it happen and it LANDED. On a server where flight is granted by a
	 * plugin, touching the ground ends it, and everything after that followed from being on foot
	 * somewhere only a flying player should be.
	 *
	 * <p>So the speed is back, and the fix is {@link #keepAirborne}: never touch down at all. The
	 * lesson is the diagnosis, not the number — the first plausible cause was a change I had just
	 * made, which is exactly the kind of suspect that gets convicted without evidence.
	 *
	 * <p>Everything that makes speed safe is a function of it rather than a constant beside it: the
	 * waypoint radius, the approach taper and the corner crawl all scale, or going faster just means
	 * missing every turn.
	 */
	static final double SPEED = 0.75;
	/** Slowest worth having: below this you are watching a progress bar. */
	static final double MIN_SPEED = 0.10;
	/**
	 * Fastest that can be asked for. Vanilla sprint-flight is about 1.0, and this is movement
	 * automation on a live server: "no faster than a player can actually go" is the one bound that
	 * is defensible without knowing the server's rules.
	 */
	static final double MAX_SPEED = 1.0;
	/** Past this the dial says that this is a server nobody has measured. */
	static final double RISKY_SPEED = 0.80;

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
	 * Were we flying last tick?
	 *
	 * <p>A true -> false while off the ground is the server taking flight away mid-air, which on
	 * this island is mid-VOID. It is an emergency rather than a mode change — see tick().
	 */
	private static boolean wasFlying = false;
	/** Said once: we are hands-off because you are falling. */
	private static boolean warnedFalling = false;
	/** Consecutive ticks spent pressed against something. Reported sparingly. */
	private static int bumps = 0;
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
		if (!mc.player.getAbilities().flying && !Hud.fetching()) {
			return "flight is off and building needs it";
		}
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
		warnedFalling = false;
		wasFlying = false;
		bumps = 0;
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

		boolean flying = p.getAbilities().flying;

		// ---- FLIGHT REVOKED. The server can take flight away mid-air — anticheat, a permission
		// change, a plugin — and on this island mid-air is over the VOID. The first flight at the
		// raised speed had exactly this happen, and the walking code below then kept driving the
		// player sideways while falling, which is the worst thing this mod could possibly do.
		//
		// So: losing flight while off the ground is not a mode change, it is an emergency. Hands
		// off completely, say so where it cannot be missed, and disarm — resuming automatically
		// into whatever revoked it is how you lose the inventory the second time as well.
		if (wasFlying && !flying && !p.onGround()) {
			wasFlying = false;
			p.sendSystemMessage(Component.literal("[cscan] FLIGHT WAS REVOKED IN THE AIR — autofly"
				+ " OFF, you have control. Get to ground before anything else."));
			halt(mc);
			return;
		}
		wasFlying = flying;

		// ON FOOT IS NOT A STALL — for a FETCH. It used to warn and do nothing here, so any
		// destination reached by walking simply stopped; it walks instead. But only to a container:
		// see walk(), where the rule and the reason for it are written down.

		// ---- YOU HIT SOMETHING. The route said this leg was clear and the world disagreed: a chunk
		// arrived, the printer placed a block, or the straight-line test was optimistic about a
		// corner. Grinding along it is how a flight ends up sliding down a wall onto a ledge, and
		// landing is how flight is lost. Re-route THIS TICK and back off a little first.
		if (flying && p.horizontalCollision) {
			bumps++;
			repathIn = 0;
			pathTo = null;
			if (bumps == 1 || bumps % 40 == 0) {
				p.sendSystemMessage(Component.literal("[cscan] bumped into something — re-routing"));
			}
			// A short push back the way we came, so the next route is computed from open air rather
			// than from inside the face we are pressed against.
			p.setDeltaMovement(dirBack(p).scale(BLIND_SPEED));
			return;
		}
		if (!p.horizontalCollision) bumps = 0;

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

		// ---- DO NOT FLY INTO WHAT YOU CANNOT SEE. See BLIND_SPEED.
		boolean blind = flying && !loadedAhead(view(mc), p.position(), dir, SIGHT);
		if (blind) speed = Math.min(speed, BLIND_SPEED);

		if (flying) {
			Vec3 step = dir.scale(speed);
			// ...and never descend into it: an absent chunk answers "air" to every question, so the
			// floor of the lowland is indistinguishable from open void until you are standing on it.
			if (blind && step.y < 0) step = new Vec3(step.x, 0, step.z);
			// Only ever applied to the DIRECT guess. A real route is already clear, and second-
			// guessing it here is how you fight your own pathfinder at a doorway.
			if (path.isEmpty()) step = unstick(mc, p, step);
			p.setDeltaMovement(keepAirborne(mc, p, step));
		} else {
			walk(mc, p, dir, aim, speed);
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
	private static void walk(Minecraft mc, LocalPlayer p, Vec3 dir, Vec3 aim, double speed) {
		// ---- BUILDING REQUIRES FLIGHT; WALKING IS ONLY EVER A FETCH.
		//
		// Jack's rule, and it is a better one than "walk whenever you cannot fly". Where the loop
		// BUILDS is by definition out over the work — the belly of the island, the underside of the
		// plate, a lowland eighty blocks down — and every one of those is a place where being on
		// foot means being in the air over the void. Where it FETCHES is a container somebody
		// walked to and placed, which is a floor.
		//
		// So on foot the only destination it will steer to is a fetch, and only with ground under
		// it. Anything else and it takes its hands off and says why: a stalled loop costs an hour,
		// and the alternative cost an inventory.
		if (!Hud.fetching()) {
			if (!warnedFalling) {
				warnedFalling = true;
				p.sendSystemMessage(Component.literal("[cscan] flight is off, and building needs it"
					+ " — autofly is holding. /fly, then double-tap jump."));
			}
			return;
		}
		if (!p.onGround() && !groundBelow(mc, p, VOID_LOOK)) {
			if (!warnedFalling) {
				warnedFalling = true;
				p.sendSystemMessage(Component.literal("[cscan] you are falling with nothing below —"
					+ " autofly is keeping its hands off. /fly, or find a floor."));
			}
			return;
		}
		warnedFalling = false;
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

	/** How far down we look for a floor before calling it a fall. */
	static final int VOID_LOOK = 6;
	/**
	 * How much air to keep under you while flying.
	 *
	 * <p><b>THE WHOLE REASON FLIGHT WAS LOST.</b> On a server where flight is a plugin grant rather
	 * than creative mode, TOUCHING THE GROUND ENDS IT — and the autopilot happily flew down onto a
	 * block, because the destination it was given was a standing spot beside the work and nothing
	 * said it had to stay off the floor. It landed, flight went, and the loop was on foot in a place
	 * only a flying player has any business being.
	 *
	 * <p>A block and a half is enough that a slab, a stair or a lip cannot catch a foot, and small
	 * enough that a station a course above the floor is still well inside the printer's reach.
	 */
	static final double GROUND_CLEAR = 1.5;
	/** How briskly to climb off a floor it has got too close to. */
	static final double RISE = 0.18;
	/**
	 * Speed when flying into world the client has not got yet.
	 *
	 * <p><b>"Unloaded is passable" is correct for ROUTING and dangerous for FLYING.</b> {@link Nav}
	 * counts an unloaded chunk as open on purpose — refusing to route through one would fail every
	 * long flight, and the route is recomputed twice a second so it sharpens as the world arrives.
	 * The autopilot then flew that route at cruise, into blocks nobody had seen yet.
	 *
	 * <p>It cost a flight at the lowlands, which is the worst case on this island by construction:
	 * 150 blocks below the deck, so the whole descent is into chunks that load somewhere on the way
	 * down. The clearance check read air under it the entire time, because an absent chunk answers
	 * air to every question you ask it.
	 *
	 * <p>So: when what is ahead or below is unloaded, crawl and do not descend. Slow is recoverable;
	 * a landing is not.
	 */
	static final double BLIND_SPEED = 0.12;
	/** How far ahead the world has to be loaded before flying at cruise. */
	static final int SIGHT = 8;

	/**
	 * Never touch down.
	 *
	 * <p>Applied to the flying step only, and it does two things: it refuses to DESCEND inside the
	 * clearance, and it climbs when already at or under it. Both are needed — the first stops you
	 * arriving at a floor, the second gets you off one you have already met, including the case
	 * where the ground came up to you because the terrain rose.
	 */
	private static Vec3 keepAirborne(Minecraft mc, LocalPlayer p, Vec3 step) {
		// ...unless there is a ceiling. Indoors — the store hall, the entrance, the undercroft — a
		// room can be two courses high, and forcing a climb there just grinds you along the ceiling.
		// Landing on a floor inside a building is not the failure this guards against: that failure
		// is landing on the deck with the void one step away.
		boolean headroom = !mc.level.getBlockState(
			BlockPos.containing(p.getX(), p.getY() + 2.6, p.getZ())).blocksMotion();
		if (p.onGround()) return headroom ? new Vec3(step.x, RISE, step.z) : step;
		double air = clearanceBelow(view(mc), p.getX(), p.getY(), p.getZ(),
			(int) Math.ceil(GROUND_CLEAR) + 1);
		if (air > GROUND_CLEAR) return step;
		double lift = headroom && air < GROUND_CLEAR * 0.6 ? RISE : 0.0;
		return new Vec3(step.x, Math.max(step.y, lift), step.z);
	}

	/**
	 * The world as the flight needs to see it: what is solid, and what is merely UNSEEN.
	 *
	 * <p>Split out from the level so the two functions below can be tested. They are entirely about
	 * the difference between "there is nothing there" and "I cannot see", which is the distinction
	 * that cost a flight at the lowlands, and it cannot be exercised against a live client.
	 */
	interface View {
		boolean loaded(int x, int y, int z);

		boolean solid(int x, int y, int z);
	}

	static View view(Minecraft mc) {
		return new View() {
			public boolean loaded(int x, int y, int z) {
				return mc.level.isLoaded(new BlockPos(x, y, z));
			}

			public boolean solid(int x, int y, int z) {
				return mc.level.getBlockState(new BlockPos(x, y, z)).blocksMotion();
			}
		};
	}

	/**
	 * Distance to the first thing under a point, or `depth` if there is nothing that close.
	 *
	 * <p><b>An unloaded cell counts as GROUND</b> — the opposite of what {@link Nav} does with one,
	 * and right for the opposite reason. A router that stops at unseen chunks never leaves the
	 * island; a flight that DESCENDS into them lands on whatever arrives. An absent chunk answers
	 * "air" to every question you ask it, so the floor of the lowland is indistinguishable from open
	 * void until you are standing on it.
	 */
	static double clearanceBelow(View w, double px, double py, double pz, int depth) {
		for (int d = 0; d <= depth; d++) {
			int by = (int) Math.floor(py - 0.1 - d);
			int bx = (int) Math.floor(px), bz = (int) Math.floor(pz);
			if (!w.loaded(bx, by, bz) || w.solid(bx, by, bz)) {
				return Math.max(0, py - (by + 1.0));
			}
		}
		return depth;
	}

	/** Is the world along the next `blocks` of travel actually here to be seen? */
	static boolean loadedAhead(View w, Vec3 from, Vec3 dir, int blocks) {
		for (int d = 1; d <= blocks; d += 2) {
			Vec3 at = from.add(dir.scale(d));
			if (!w.loaded((int) Math.floor(at.x), (int) Math.floor(at.y), (int) Math.floor(at.z))) {
				return false;
			}
			// ...and under it, because the descent is the leg that ends in a floor
			if (!w.loaded((int) Math.floor(at.x), (int) Math.floor(at.y) - 2,
				(int) Math.floor(at.z))) {
				return false;
			}
		}
		return true;
	}

	/** Is there anything to land on within `depth` blocks? */
	private static boolean groundBelow(Minecraft mc, LocalPlayer p, int depth) {
		for (int d = 1; d <= depth; d++) {
			if (mc.level.getBlockState(BlockPos.containing(p.getX(), p.getY() - d, p.getZ()))
				.blocksMotion()) return true;
		}
		return false;
	}

	/** Away from where the player is looking: the way back out of what they just hit. */
	private static Vec3 dirBack(LocalPlayer p) {
		double yaw = Math.toRadians(p.getYRot());
		return new Vec3(Math.sin(yaw), 0.1, -Math.cos(yaw));
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
