package dev.jack.chunkscan;

import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.minecraft.client.Minecraft;
import net.minecraft.client.player.LocalPlayer;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import net.minecraft.world.level.levelgen.Heightmap;
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
	static final double SPEED = 1.5;
	/** Slowest worth having: below this you are watching a progress bar. */
	static final double MIN_SPEED = 0.10;
	/**
	 * Fastest that can be asked for.
	 *
	 * <p><b>The old cap was 1.0 for a reason that no longer holds, and the reason was also wrong.</b>
	 * It read "vanilla sprint-flight is about 1.0, and this is movement automation on a live server:
	 * no faster than a player can actually go is the one bound defensible without knowing the
	 * server's rules." Vanilla creative sprint-flight is about 10.9 blocks a second, which is 0.545
	 * a tick - so 1.0 was already twice it and the sentence justifying it was measuring nothing. And
	 * the rules ARE known now: automation is allowed and encouraged on skyblock.net, which retires
	 * the argument the number rested on.
	 *
	 * <p>What actually bounds it is arithmetic, and all of it is now a function of the speed rather
	 * than a constant beside it: the swept-volume test in {@link #avoid} (which is what makes a fast
	 * step honest rather than a tunnel), {@link #sightFor}, {@link #repathFor}, the waypoint radius,
	 * the approach taper and the corner crawl. 2.5 is fifty blocks a second and crosses this island
	 * in five.
	 */
	static final double MAX_SPEED = 2.5;
	/**
	 * Past this the dial says that this is a server nobody has measured.
	 *
	 * <p>Not a safety limit - the safety is the swept test - but the point past which rubber-banding
	 * becomes the server's opinion rather than ours, and a rubber-band into terrain is contact.
	 */
	static final double RISKY_SPEED = 2.0;

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
	 * <p>It went 3.0 -> 1.5 to protect the printer's reach budget, and back to 3.0 on Jack's
	 * instruction: <i>"the focus should be getting within a 3 block radius of the point since we
	 * know we reach+place further"</i>. He is right, and the tight radius was buying precision with
	 * the currency that actually costs — CONTACT. The last two blocks of an approach are threaded
	 * between whatever the standing spot is beside, at low speed, with the alignment fighting the
	 * drift, and every one of those is a chance to touch a block and lose flight. The printer does
	 * not care whether you are at the spot or three blocks off it.
	 *
	 * <p>What pays for it is {@link Plan#reach}, which now asks the printer how far it really places
	 * instead of assuming four blocks.
	 */
	static final double ARRIVED = 3.0;
	/**
	 * As close as it ever needs to get.
	 *
	 * <p>{@link #ARRIVED} is a CEILING, not a target. Jack: <i>"if we always are 3 blocks its hard to
	 * reach all blocks since we lose 3 blocks to air, we need to decrease it based on whats around us
	 * and actual space after stopping fly."</i> Three blocks of standoff is three blocks off the far
	 * corner of the bin, and the printer's reach has to cover both.
	 *
	 * <p>So it keeps closing until it physically cannot — the clearance rules, the alignment, a wall
	 * — and accepts wherever that turned out to be, provided it is inside the ceiling. In open air it
	 * ends up here; against a surface it ends up wherever the surface allows; and neither number is
	 * guessed in advance, which is the point.
	 */
	static final double ARRIVE_MIN = 1.2;

	/**
	 * An EXACT target is a place the body has to actually be — a chest's approach cell, chosen so
	 * the eyes have a line to the chest from THAT cell and no other. Jack: <i>"it doesnt get close
	 * enough to chests, chests need to be within 2 blocks"</i>. The ordinary ceiling lets a flight
	 * call itself arrived three blocks short of a spot, which is right for a station (the printer
	 * reaches) and wrong here: three blocks short of the approach cell is out of reach of the chest,
	 * and the loop then waited for an opening test that could never pass.
	 *
	 * <p>{@link #EXACT_MIN} is inside the cell; {@link #EXACT_ARRIVED} is the most it may stop
	 * short, and only when something is physically in the way or it has stopped closing.
	 */
	static final double EXACT_MIN = 0.6;
	static final double EXACT_ARRIVED = 1.6;
	/**
	 * How much air an exact target keeps under the feet. The approach cell is chosen with
	 * {@link ContainerInteraction#HOVER_CLEAR} clear cells beneath it, so the feet sit just over TWO
	 * blocks of air above whatever floor the chest stands on. It was one, on the reasoning that two
	 * and a half is "exactly where it could not" open a chest on that floor — and one block of air
	 * is the distance this server has been measured to end flight at, so every fetch approach was
	 * a chance to lose it. From two blocks up the eyes still reach a chest one block over
	 * (Withdraw.REACH is 4.5), and the opening ray is tested from the cell before it is chosen.
	 */
	static final double EXACT_CLEAR = 2.05;
	/** Ticks of getting no nearer before "this is as close as it gets" is the honest reading. */
	static final int CLOSING_PATIENCE = 12;
	/**
	 * Air to keep between the body and whatever it is approaching.
	 *
	 * <p>The other half of Jack's rule: <i>"this needs to balance against safe landing and stopping
	 * fly... we need to be smart about this when its possible, and when we should just be floating a
	 * bit closer."</i> Closing in is worth reach and it is not worth CONTACT — on this server contact
	 * ends flight, and a flight that ends is worth far more than the block it was reaching for.
	 *
	 * <p>So the approach stops a block short of a surface rather than pressing up to it. In open air
	 * nothing is in the way and it closes to {@link #ARRIVE_MIN}; against a wall it stops here; and
	 * the difference between those two is measured, not assumed.
	 */
	static final double SAFE_GAP = 1.0;

	/** The closest this target has been, and how long since that improved. Reset when it moves. */
	private static double bestDist = Double.MAX_VALUE;
	private static int sinceCloser = 0;
	/** Which target `bestDist` is about. See tick(): it is not always the route's target. */
	private static BlockPos approaching = null;

	/**
	 * Are we there?
	 *
	 * <p>Two ways to be, and the second is the one that matters on a real island: either close
	 * enough that nothing is gained by more, or NO LONGER GETTING CLOSER while already inside the
	 * ceiling — which is what "the space after stopping" actually means. A flight wedged against a
	 * shelf 2.4 blocks from the work has arrived; waiting for 1.2 there is waiting for ever.
	 */
	static boolean hasArrived(double dist, int ticksSinceCloser, double min, double max,
	                          int patience) {
		return hasArrived(dist, ticksSinceCloser, min, max, patience, false);
	}

	/**
	 * @param wallAhead there is a surface within {@link #SAFE_GAP} of the body, in the direction of
	 *                  travel. Getting nearer would mean touching it, and touching it ends the
	 *                  flight — so if we are inside the ceiling, this is as close as it gets.
	 */
	static boolean hasArrived(double dist, int ticksSinceCloser, double min, double max,
	                          int patience, boolean wallAhead) {
		if (dist <= min) return true;
		if (dist > max) return false;                      // too far to call it arrived, whatever
		return wallAhead || ticksSinceCloser >= patience;
	}
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
	/**
	 * The fall safety outlives the autopilot.
	 *
	 * <p>Jack, twice now: <i>"if we turn off auto fly because of w/e, we still need to for the next
	 * 30 seconds have active /is auto usage or auto fly to save falling in case its a momentum
	 * mistake."</i>
	 *
	 * <p>Switching off is the MOST dangerous moment, not the safest. Whatever the reason — the
	 * emergency disarm, a stop, flight revoked in mid-air — the body keeps whatever velocity it had
	 * and there is now nothing watching it. The rescue is the one part that has no business being
	 * tied to whether the loop is driving: it does not steer, it does not build, it only notices a
	 * fall and does something about it.
	 *
	 * <p>Thirty seconds is long enough to cover the arc of any fall this island can produce and
	 * short enough that it is not quietly on for ever.
	 */
	static final long GUARD_MS = 30_000;

	private static long guardUntil = 0;

	/** Is the fall safety still watching, though the autopilot is off? */
	static boolean guarding(long now, long until) {
		return now < until;
	}

	/** For `/cscan why`: seconds of fall cover left, or 0. */
	static long guardLeft() {
		return Math.max(0, (guardUntil - System.currentTimeMillis()) / 1000);
	}
	private static boolean warnedNoRoute = false;
	private static boolean warnedOutside = false;
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
	/** The route in hand stops short of the target (a stage, or a way round): exhausting it is not arriving. */
	private static boolean partialRoute = false;
	/** The last search found NOTHING — not a stage, not a way round. Only this earns a strike. */
	private static boolean noRoute = false;
	/** Was the current route found in the world that keeps its distance? For the HUD and `why`. */
	private static boolean roomyRoute = false;
	/**
	 * Were we flying last tick?
	 *
	 * <p>A true -> false while off the ground is the server taking flight away mid-air, which on
	 * this island is mid-VOID. It is an emergency rather than a mode change — see tick().
	 */
	private static boolean wasFlying = false;
	/** Said once: we are hands-off because you are falling. */
	private static boolean warnedFalling = false;
	/** Consecutive ticks spent pressed against something. See tick(). */
	private static int bumps = 0;
	/** Ticks of solid contact before the route itself is declared wrong rather than stale. */
	static final int STUCK_TICKS = 40;
	/** How far to flood for a way round when pressed against something. */
	static final int BUMP_LOOK = 10;
	/** ...and how often. A flood on every tick of contact is a cost this file has paid twice. */
	static final int BUMP_LOOK_EVERY = 10;
	/**
	 * Ticks of bumping inside a tight passage before the passage is the problem.
	 *
	 * <p>Generous, because the answer while threading is to line up and creep, and that takes longer
	 * than barging would. Past it, the gap is genuinely not being flown and the way round is worth
	 * looking for after all.
	 */
	static final int WEDGED_TICKS = 60;
	/** Ticks of being wedged before the SPOT is abandoned rather than the route. */
	static final int WEDGED_GIVE_UP = 160;

	private static int wedged = 0;

	// ---- THE RECOVERY LADDER. See Recovery: when every specific handler has had its turn and the
	// flight is still going nowhere, the reason stops mattering and only the escalation does.
	/** How far a destination may move and still be the same destination. See the drift note below. */
	static final double SAME_TARGET = 4.0;
	private static int trouble = 0;private static Recovery.Stage stage = Recovery.Stage.NONE;
	/** A climb-out has already been spent on this destination. The next one is a give-up. */
	private static boolean climbedOut = false;
	/** Somewhere we were definitely fine, to back off to. */
	private static BlockPos breadcrumb = null;
	private static int breadcrumbAge = 0;
	/** How high the climb-out is aiming, once it starts. */
	private static BlockPos climbTo = null;
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
	 * ...and the same argument as {@link #sightFor}: a route recomputed every ten ticks is a route
	 * that goes seven and a half blocks stale at 0.75 and fifteen at 1.5. What matters is the
	 * DISTANCE it is allowed to go stale over, not the time - so the timer is that distance divided
	 * by the speed, floored by {@link #MIN_REPATH_TICKS} because a per-tick A* is the one cost this
	 * file has already paid for twice.
	 */
	static final double REPATH_BLOCKS = 7.0;

	static int repathFor(double speed) {
		if (speed <= 0) return REPATH_TICKS;
		return Math.max(MIN_REPATH_TICKS, Math.min(REPATH_TICKS,
			(int) Math.round(REPATH_BLOCKS / speed)));
	}
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
	 */static double waypointRadius(double speed) {
		return Math.max(WAYPOINT, speed * 2.5);
	}

	/**
	 * Has this waypoint been passed? Inside {@link #WAYPOINT} of it, yes. Inside the speed-scaled
	 * radius, only once the body is PAST the corner - on the far side of the plane through the
	 * waypoint perpendicular to the next leg. Popped before that, `legFrom` jumps ahead of the body
	 * and the pursuit aims LOOKAHEAD along a leg the body has not reached: a chord across the very
	 * corner the waypoint was there to round, on a line `clear` never validated. At cruise that
	 * chord began nearly two blocks before the corner, which is a shop's own width.
	 */
	static boolean popped(Vec3 me, Vec3 legFrom, Vec3 wp, Vec3 nextWp, double near) {
		double d = me.distanceTo(wp);
		if (d <= WAYPOINT) return true;
		if (d > near) return false;
		if (nextWp == null || legFrom == null) return true;    // the last one: nothing to round
		Vec3 in = wp.subtract(legFrom), out = nextWp.subtract(wp);
		if (in.lengthSqr() < 1e-9 || out.lengthSqr() < 1e-9) return true;
		// A DRIFT MAY BE POPPED EARLY, A CORNER MAY NOT: the same bend test the speed uses. Through a
		// right angle the plane through the corner contains the whole leg being flown, so "past the
		// plane" is no test at all there - the chord is what has to be avoided, and it only exists
		// where the route actually turns.
		return in.normalize().dot(out.normalize()) >= CORNER_COS;
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
				Perf.run("autofly", () -> tick(mc));
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

	/** Hard stop: drop the target, the route, the motion and any key we were holding. */
	static void halt(Minecraft mc) {
		if (on) guardUntil = System.currentTimeMillis() + GUARD_MS;
		on = false;
		Burial.reset();
		release(mc);
		rescueStage = 0;
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
		if (!mc.player.getAbilities().flying && !Hud.fetching() && !Hud.targetLand()) {
			return "flight is off and building needs it";
		}
		// A CONTAINER screen, not any screen. Chat, the map and the pause menu do not stop it — see
		// the note on tick(). Only a chest does, and only because flying away from one mid-withdrawal
		// is the one case where carrying on is actively wrong.
		if (Screens.container() != null) return "a container is open";
		if (Hud.target() == null) return "no destination — use goto or follow";
		if (!Bounds.contains(Hud.target())) return "destination " + Wand.fmt(Hud.target()) + " is outside the autofly bounds";
		return null;
	}

	// ---- THE JUMP KEY IS NOT A CLIMB CONTROL, IT IS A FLIGHT TOGGLE.
	//
	// This was written the other way round for about twenty minutes and it revoked Jack's flight in
	// mid-air. **Vanilla toggles flying on a DOUBLE TAP of jump** — `LocalPlayer.aiStep` starts a
	// seven-tick window on the first press and flips `abilities.flying` on the second. Driving the
	// key to climb presses and releases it as the desired vertical crosses a deadzone, which inside
	// seven ticks is a double tap. So the mod turned off its own flight, fell, and then reported the
	// fall as though something else had happened to it.
	//
	// The vertical is a VELOCITY again. `travelFlying` damps it every tick, which is why the naive
	// version was weak, so it is scaled up rather than pressed: see VERTICAL_GAIN.
	//
	// The keys are still here, and `hold` still exists, for exactly one job — the rescue taps, where
	// toggling flight is the POINT rather than the accident.

	private static boolean holdUp = false;
	private static boolean holdDown = false;
	/**
	 * How much to over-command the vertical.
	 *
	 * <p>`travelFlying` applies friction every tick, so a y velocity set to the speed you want
	 * arrives as roughly half of it and the flight sinks toward the thing it is trying to clear.
	 * Doubling it and clamping is a great deal safer than touching the key that toggles flight.
	 */
	static final double VERTICAL_GAIN = 2.0;
	/** Downward speed worth holding shift for. Below it, the velocity alone is the whole descent. */
	static final double CLIMB_DEADZONE = 0.05;

	/** The step, with the vertical scaled to survive flight friction. */
	/**
	 * Where in a waypoint cell to put the BODY.
	 *
	 * <p><b>A player is 1.8 tall and stands on its feet.</b> Every waypoint here was flown to
	 * {@code atCenterOf}, which is the cell's MIDDLE - so the feet sat at y+0.5 and the head at
	 * y+2.3, and the body occupied THREE cells: y, y+1 and y+2. {@link Nav.Passable} checks TWO.
	 *
	 * <p>So the router and the flight disagreed about the shape of the thing being routed, on every
	 * cell of every path, permanently. A corridor exactly two courses high - which is most of the
	 * deck, the store hall, the undercroft and every doorway on this island - is routable and
	 * unflyable: the search says yes and the head is in the ceiling. That is the structural cause of
	 * <i>"we bump our head a lot"</i>, and no amount of climbing, sliding or unsticking can fix a
	 * body that does not fit the hole it was sent through.
	 *
	 * <p>Aimed at the feet instead, a hair off the floor of the cell, the box spans y+0.1 to y+1.9
	 * and occupies exactly the two cells the search checked. The two agree BY CONSTRUCTION rather
	 * than by a margin somebody chose.
	 */
	static final double FOOT_OFFSET = 0.1;

	static Vec3 flyTo(BlockPos cell) {
		return new Vec3(cell.getX() + 0.5, cell.getY() + FOOT_OFFSET, cell.getZ() + 0.5);
	}

	static Vec3 liftFor(Vec3 step, double cap) {
		double y = step.y * VERTICAL_GAIN;
		return new Vec3(step.x, Math.max(-cap, Math.min(cap, y)), step.z);
	}

	private static void hold(Minecraft mc, boolean up, boolean down) {
		if (mc == null || mc.options == null) return;
		if (up != holdUp) {
			holdUp = up;
			mc.options.keyJump.setDown(up);
		}
		if (down != holdDown) {
			holdDown = down;
			mc.options.keyShift.setDown(down);
		}
	}

	/**
	 * Sneak, and only sneak.
	 *
	 * <p>Safe in a way that {@link #hold} is not: **only JUMP toggles flight**, so holding shift
	 * while flying simply descends, which is what a player does and is stronger than a y velocity
	 * `travelFlying` is busy damping. The movement path is given this rather than `hold` so that it
	 * CANNOT press the key that turned off Jack's flight in mid-air.
	 */
	private static void sink(Minecraft mc, boolean down) {
		if (mc.options == null || down == holdDown) return;
		holdDown = down;
		mc.options.keyShift.setDown(down);
	}

	/** Let go of both, for every path that stops steering. A stuck key is worse than a stuck loop. */
	static void release(Minecraft mc) {
		hold(mc, false, false);
	}

	// ---- FALLING. Jack: "if it detects falling suddenly it needs to automatically start flying
	// (tap space twice) or just instant type in chat /is".
	//
	// Two rescues, tried in that order, because they cost different things. A double-tap of jump
	// re-enters flight and costs nothing — but only works if the server still says you MAY fly.
	// `/is` teleports you home, which always works and moves you across the island. So: tap first,
	// and only fall back to the command when the tap has plainly not worked.

	/** Downward speed that means falling rather than descending. */
	static final double FALLING = 0.6;
	/** Ticks between the two taps, and how long to wait before deciding the tap failed. */
	static final int TAP_GAP = 3;
	static final int TAP_WAIT = 20;
	/** Never send the command more often than this, whatever happens. */
	static final int RESCUE_COOLDOWN = 200;
	/**
	 * Below this, a fall goes straight to `/is` without trying the taps first.
	 *
	 * <p>Jack's rule, and the geometry backs it: the plate is Y201 and the deck Y190-199, so ABOVE
	 * this you are falling somewhere with island under you and a double-tap has both time to work
	 * and something to land on. Below it you are under the belly, and what is beneath you is the
	 * void — the taps cost about a third of a second and buy nothing there, because if flight were
	 * available you would not be falling in the first place.
	 *
	 * <p>The lowland floor is Y24-47, which is under this line too. Landing on it is survivable and
	 * being teleported home from above it is merely inconvenient; the fall that is not survivable is
	 * the one that misses it.
	 */
	static final int PANIC_BELOW_Y = 100;

	// ---- GETTING FLIGHT BACK, when it is merely absent rather than an emergency.
	//
	// Jack: "it needs to also activate fly again if its purely not moving because its not in fly
	// anymore because it bumped into something etc". Losing flight is not the end of the job — the
	// walk gate stops the loop from doing anything DANGEROUS without it, and stopping there is only
	// right if nothing can be done about it. Usually something can: the same double tap that rescues
	// a fall turns flight back on while standing on a floor.
	//
	// Tried whenever the loop has somewhere to be, is not flying, and the server still says it MAY.
	// Rate-limited, because a tap that does not work will not work the second time either, and a
	// player watching their character hop twice a second is watching a bug.

	/** Ticks between attempts to get flight back. */
	static final int REGAIN_EVERY = 60;
	/** After this many failed attempts, stop trying and say so once. */
	static final int REGAIN_GIVE_UP = 4;
	/** How many times /fly is sent for one destination before it is left to a human. */
	static final int FLY_COMMANDS = 3;
	private static int flyCommands = 0;

	private static int regainCool = 0;
	private static int regainTries = 0;
	// ITS OWN STAGE, NOT THE RESCUE'S. Sharing `rescueStage` meant rescue() - which runs first on
	// every tick and resets its stage whenever the body is NOT falling - wiped the take-off
	// sequence one tick after it began: the key was held for four consecutive ticks (one jump,
	// never a double tap), four "tries" were spent, and the session was permanently on foot.
	private static int regainStage = 0;
	private static int regainTimer = 0;
	private static boolean regainSaid = false;

	/** Should we be flying and are not, with the server's permission to fix that? */
	static boolean canRegainFlight(boolean flying, boolean mayfly, boolean hasTarget) {
		return hasTarget && !flying && mayfly;
	}

	/**
	 * Turn flight back on.
	 *
	 * @return true while an attempt is in progress and nothing else should touch the controls
	 */
	private static boolean regain(Minecraft mc, LocalPlayer p) {
		if (regainCool > 0) regainCool--;
		if (p.getAbilities().flying) {
			regainTries = 0;
			regainSaid = false;
			if (regainStage != 0) {
				regainStage = 0;
				release(mc);
			}
			return false;
		}
		BlockPos goal = Hud.target();
		boolean wanted = goal != null && needsFlight(Hud.targetLand(), groundNoRoute,
			Math.sqrt(p.blockPosition().distSqr(goal)));
		if (!canRegainFlight(false, p.getAbilities().mayfly, wanted)) {
			if (!p.getAbilities().mayfly && wanted && p.connection != null && regainCool == 0
				&& flyCommands < FLY_COMMANDS) {
				// ---- THE SERVER TOOK IT: ASK FOR IT BACK. On this server flight is a plugin grant
				// and touching a block ends it, so a landing was one-way - the taps cannot toggle
				// what the server has revoked, and the loop was on foot for the rest of the night.
				// `/fly` is a TOGGLE, which is exactly why it is only ever sent while mayfly is
				// FALSE: then the one direction it can go is on. Bounded, like the taps.
				flyCommands++;
				regainCool = REGAIN_EVERY;
				p.connection.sendCommand("fly");
				p.sendSystemMessage(Component.literal("[cscan] flight was revoked — sent /fly ("
					+ flyCommands + "/" + FLY_COMMANDS + "), then the double tap."));
				return true;
			}
			if (!p.getAbilities().mayfly && !regainSaid && flyCommands >= FLY_COMMANDS) {
				regainSaid = true;
				p.sendSystemMessage(Component.literal("[cscan] flight is off and /fly did not bring"
					+ " it back " + FLY_COMMANDS + " times — do it by hand: /fly, then double-tap jump."));
			}
			return false;
		}
		if (regainTries >= REGAIN_GIVE_UP) {
			if (!regainSaid) {
				regainSaid = true;
				p.sendSystemMessage(Component.literal("[cscan] tried " + REGAIN_GIVE_UP
					+ " times to get flight back and it is not taking. /fly, then double-tap jump."));
			}
			return false;
		}
		if (regainCool > 0) return regainStage != 0;       // mid-sequence, or waiting to try again

		// The same two taps as the fall rescue. From the ground the first is a jump and the second
		// lands while airborne, which is exactly the gesture a player makes.
		regainTimer++;
		switch (regainStage) {
			case 0 -> {
				regainStage = 1;
				regainTimer = 0;
				regainTries++;
				hold(mc, true, false);
			}
			case 1 -> {
				if (regainTimer >= TAP_GAP) {
					regainStage = 2;
					regainTimer = 0;
					hold(mc, false, false);
				}
			}
			case 2 -> {
				if (regainTimer >= TAP_GAP) {
					regainStage = 3;
					regainTimer = 0;
					hold(mc, true, false);
				}
			}
			default -> {
				if (regainTimer >= TAP_GAP) {
					regainStage = 0;
					regainTimer = 0;
					regainCool = REGAIN_EVERY;
					hold(mc, false, false);
				}
			}
		}
		return true;
	}

	/** Straight home, no taps: see {@link #PANIC_BELOW_Y}. */
	static boolean goHomeAtOnce(double y) {
		return y < PANIC_BELOW_Y;
	}

	private static int rescueStage = 0;
	private static int rescueTimer = 0;
	private static int rescueCool = 0;

	/** Is this a fall rather than a flight? */
	static boolean isFalling(double dy, boolean flying, boolean onGround, boolean groundBelow) {
		return !flying && !onGround && dy < -FALLING && !groundBelow;
	}

	/**
	 * Get out of a fall.
	 *
	 * @return true while a rescue is in progress and nothing else should touch the controls
	 */
	private static boolean rescue(Minecraft mc, LocalPlayer p) {
		if (rescueCool > 0) rescueCool--;
		boolean falling = isFalling(p.getDeltaMovement().y, p.getAbilities().flying, p.onGround(),
			groundBelow(mc, p, VOID_LOOK));
		if (!falling) {
			if (rescueStage != 0) {
				rescueStage = 0;
				release(mc);
			}
			return false;
		}
		rescueTimer++;
		switch (rescueStage) {
			case 0 -> {
				rescueTimer = 0;
				if (goHomeAtOnce(p.getY())) {
					// No time and nothing to land on. Skip the taps entirely.
					if (rescueCool == 0 && p.connection != null) {
						rescueCool = RESCUE_COOLDOWN;
						p.sendSystemMessage(Component.literal("[cscan] FALLING below Y"
							+ PANIC_BELOW_Y + " — /is, now"));
						p.connection.sendCommand("is");
					}
					return true;
				}
				rescueStage = 1;
				p.sendSystemMessage(Component.literal("[cscan] FALLING — trying to get flight back"));
				if (p.getAbilities().mayfly) hold(mc, true, false);        // tap one, down
			}
			case 1 -> {
				if (rescueTimer >= TAP_GAP) {
					rescueStage = 2;
					rescueTimer = 0;
					hold(mc, false, false);                                 // tap one, up
				}
			}
			case 2 -> {
				if (rescueTimer >= TAP_GAP) {
					rescueStage = 3;
					rescueTimer = 0;
					if (p.getAbilities().mayfly) hold(mc, true, false);      // tap two, down
				}
			}
			case 3 -> {
				if (rescueTimer >= TAP_GAP) {
					rescueStage = 4;
					rescueTimer = 0;
					hold(mc, false, false);                                 // tap two, up
				}
			}
			default -> {
				// Still falling a second after both taps: either flight was revoked outright, or
				// something is holding it off. Go home — it always works, and the island is the one
				// place on this server with a floor.
				if (rescueTimer >= TAP_WAIT && rescueCool == 0 && p.connection != null) {
					rescueCool = RESCUE_COOLDOWN;
					rescueStage = 0;
					p.sendSystemMessage(Component.literal(
						"[cscan] still falling — sending /is to get you home"));
					p.connection.sendCommand("is");
				}
			}
		}
		return true;
	}

	/** Everything this thing knows about why it is or is not moving. For `/cscan why`. */
	static java.util.List<String> why(Minecraft mc) {
		java.util.List<String> out = new java.util.ArrayList<>();
		if (!on) {
			long left = guardLeft();
			out.add("autofly: OFF  (/cscan autofly on)"
				+ (left > 0 ? "   fall safety still watching for " + left + "s" : ""));
			return out;
		}
		String stalled = stalledBecause(mc);
		out.add("autofly: ON  " + (stalled == null ? "moving" : "IDLE — " + stalled));
		if (mc.player != null) {
			out.add("  flying " + mc.player.getAbilities().flying
				+ "   on ground " + mc.player.onGround()
				+ "   speed " + String.format("%.2f", speed)
				+ (bumps > 0 ? "   BUMPING (" + bumps + " ticks)" : ""));
		}
		if (Bounds.active()) out.add("  " + Bounds.describe());
		out.add("  route: " + (path.isEmpty() ? "none — flying direct"
			: (escaping ? "a way ROUND, " : "") + path.size() + " waypoint(s), next "
				+ Wand.fmt(path.get(0))));
		if (Hud.target() != null && mc.player != null) {
			out.add("  target " + Wand.fmt(Hud.target()) + "  "
				+ (int) Math.sqrt(mc.player.blockPosition().distSqr(Hud.target())) + "m");
		}
		return out;
	}

	/** What is carrying you right now, for the HUD: a route, a walk, or a guess. */
	static String mode(Minecraft mc) {
		// speed is part of the mode: it is a dial you can move, so it must be visible where you are
		// watching the thing it moves.
		boolean flying = mc.player != null && mc.player.getAbilities().flying;
		String how = flying ? "route" : "walk";
		// The APPLIED speed, and the dial behind it. Showing only the dial is showing the one number
		// that is guaranteed not to be the problem.
		String tail = appliedSpeed > 0 && appliedSpeed < speed - 1.0e-6
			? String.format(" @%.2f/%.2f %s", appliedSpeed, speed, slowBecause)
			: String.format(" @%.2f", speed);
		if (Bounds.active()) tail += " fenced";
		if (path.isEmpty()) return (flying ? "direct" : "walk direct") + tail;
		// `tight` is worth seeing: it is the difference between a route that keeps a block of air
		// off everything and one that has to thread something.
		return (escaping ? "round " : how + " ") + path.size() + (roomyRoute ? "" : " tight") + tail;
	}

	static void set(boolean v) {
		// Every warning below is a once-per-arming shot. Without this reset, turning autofly off and
		// on again after it has already complained gets you silence instead of the reason.
		warnedNoRoute = false;
		warnedOutside = false;
		idleSaid = false;
		announcedArrival = false;
		warnedFalling = false;
		wasFlying = false;
		bumps = 0;
		rescueStage = 0;
		rescueCool = 0;
		Burial.reset();
		regainCool = 0;
		regainTries = 0;
		regainSaid = false;
		// Turning it OFF starts the watch; turning it on does not need one, because it is watching.
		if (on && !v) guardUntil = System.currentTimeMillis() + GUARD_MS;
		on = v;
		path = new java.util.ArrayList<>();
		pathTo = null;
		repathIn = 0;
	}

	/**
	 * Throw away the current route.
	 *
	 * <p>Called when the LOOP gives up on where it was sending you. The route is computed from a
	 * destination, so keeping it after the destination has been abandoned is keeping a plan to fly
	 * at the thing that just stuck.
	 */
	static void forget() {
		path = new java.util.ArrayList<>();
		pathTo = null;
		legFrom = null;
		bumps = 0;
		partialRoute = false;
		noRoute = false;
		bestDist = Double.MAX_VALUE;
		sinceCloser = 0;
	}

	/**
	 * Stop the current leg without disarming autofly.
	 *
	 * <p>A build can abandon a chest approach or an unbuildable spot while leaving autofly armed for
	 * its replacement. Clearing only the HUD target made the next movement tick return early, with
	 * the previous route and delta velocity still alive. That is not a pause: it is a player drifting
	 * in the direction of work the scheduler has already rejected.
	 */
	static void pauseGuidance(Minecraft mc) {
		forget();
		approaching = null;
		arrivedAt = null;
		announcedArrival = false;
		if (mc != null && mc.player != null) mc.player.setDeltaMovement(Vec3.ZERO);
		release(mc);
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
		LocalPlayer p = mc.player;
		if (!on) {
			// ---- THE SAFETY OUTLIVES THE AUTOPILOT. See GUARD_MS. Switching off is the most
			// dangerous moment rather than the safest: the body keeps its velocity and nothing is
			// watching it any more. This steers nothing — it only notices a fall.
			if (p != null && mc.level != null && guarding(System.currentTimeMillis(), guardUntil)) {
				if (rescue(mc, p)) return;
			}
			release(mc);
			return;
		}
		if (p == null || mc.level == null) return;
		// A CONTAINER screen only. This used to be `Screens.anyOpen()`, which meant opening chat or
		// alt-tabbing away stopped the loop dead — and the whole point of an unattended loop is that
		// you are doing something else while it runs. A chest is the one screen worth pausing for,
		// because flying off mid-withdrawal is how you half-empty a chest and blacklist it.
		if (Screens.container() != null || AutomationControl.blocksMovement()) {
            if (rescue(mc, p)) return;
            if (p.getAbilities().flying) p.setDeltaMovement(Vec3.ZERO);
			release(mc);
			return;
		}

		// ---- FALLING BEATS EVERY OTHER CONSIDERATION, including having no destination: the whole
		// point is that it fires when the loop is not in control of what is happening.
		if (rescue(mc, p)) return;

		// ---- ...AND SO DOES BEING WALLED IN, for the same reason: it happens while the loop is
		// standing exactly where it means to stand, so every clock in this mod reads it as success.
		// Above the destination check on purpose — a bot digging itself into a pit usually has
		// nowhere it is trying to go, which is precisely why nothing noticed.
		//
		// THE STEP GOES THROUGH THE FENCE AND THEN THE WORLD, like every other one in this file. A
		// rise that set its own velocity would be the single movement path never tested against a
		// block, and contact ends flight — see Burial.wants, which owns the decision and no more.
		if (Burial.wants(mc)) {
			if (p.getAbilities().flying) {
				p.setDeltaMovement(avoid(p, Bounds.clamp(p.position(), Burial.step(p))));
			} else {
				Burial.hop(p);
			}
			return;
		}

		// ...and the quieter version of the same thing: on the ground, not flying, with somewhere to
		// be. See regain — the loop should get flight back rather than stand there being safe.
		if (regain(mc, p)) return;

		BlockPos target = Hud.target();
		if (target == null) {
			// ARMED WITH NOWHERE TO GO. autofly is a MODIFIER, not an action: the destination comes
			// from `follow` or `goto`. Turned on by itself it used to report ON and then sit there
			// in silence, which is indistinguishable from broken. Say it once.
			idle(mc);
			return;
		}
		idleSaid = false;
		if (!Bounds.contains(target)) {
			// ---- OUTSIDE THE FENCE. The loop filters its own work and its chests by the bounds, so
			// a destination past them is a goto, a photo bearing or a tidy source somebody pointed
			// there by hand. Hold - pulled back in if we are already past the fence - and say once.
			if (!warnedOutside) {
				warnedOutside = true;
				p.sendSystemMessage(Component.literal("[cscan] " + Wand.fmt(target)
					+ " is outside the autofly bounds - not going. /cscan autofly bounds off to lift them."));
			}
			if (p.getAbilities().flying) p.setDeltaMovement(avoid(p, keepAirborne(mc, p, Bounds.clamp(p.position(), Vec3.ZERO), GROUND_CLEAR)));
			release(mc);
			return;
		}
		warnedOutside = false;

		// ---- NO KEY STOPS THIS, and that is deliberate. The earlier rule was "any movement key
		// hands control back", which read as a safety property and behaved as a fault: a key left
		// down when the window loses focus, or a nudge while reading chat, silently disarmed an
		// hour-long unattended loop and left it parked. `/cscan stop` and `/cscan autofly off` are
		// the off switch, they are one word each, and they cannot be pressed by accident.
		Vec3 me = p.position();
		// A SOLID target is a thing to LOOK AT, so its middle is the right point. An empty one is a
		// place to PUT THE BODY, and a body stands on its feet - see flyTo.
		boolean solidTarget = mc.level.getBlockState(target).blocksMotion();
		boolean exact = !solidTarget && Hud.targetExact();
		// A LANDING. The target is a cell with a floor under it, and the point is to touch that
		// floor: flight ends on contact on this server, and here that is what is wanted.
		boolean landing = !solidTarget && Hud.targetLand();
		Vec3 to = solidTarget ? Vec3.atCenterOf(target) : flyTo(target);
		double dist = me.distanceTo(to);
		// A SOLID DESTINATION IS ARRIVED AT FROM OUTSIDE IT. A chest is a block, so the tight radius
		// can never be satisfied and the flight would hover against its face trying — inside reach
		// the whole time, which is all the fetch needs, but visibly nosing at it.
		// ---- HOW CLOSE DID WE ACTUALLY GET? Tracked per target, so "it stopped getting nearer" is
		// a measurement rather than a guess about what is around it.
		// A NEW DESTINATION HAS NEVER BEEN APPROACHED. This was only reset when the ROUTE's target
		// changed, and the route is often null at exactly that moment — a fetch that ends, a station
		// that moves — so `bestDist` carried over from the last place. The next target then looked
		// like something that had stopped getting nearer, `sinceCloser` ran up, and it "arrived" at
		// the ceiling instead of closing in. That is the "not getting close enough" half, again,
		// from a third direction.
		// A TARGET THAT HAS DRIFTED IS THE SAME DESTINATION. A station re-centres on the cells
		// still to place, so in follow mode the target moves a block or two on EVERY recount -
		// and compared with `equals`, that zeroed `trouble` twice a second, before it could ever
		// reach the first rung. The whole escalation was dead code in exactly the mode it was
		// written for. Same hysteresis, and the same reason, as `Loop.sameSpot`.
		boolean elsewhere = approaching == null || target.distSqr(approaching) > SAME_TARGET * SAME_TARGET;
		if (!target.equals(approaching)) {
			approaching = target;
		}
		if (elsewhere) {
			arrivedAt = null;
			groundNoRoute = false;
			bestDist = Double.MAX_VALUE;
			sinceCloser = 0;
			// ...AND THE LADDER STARTS AGAIN. Carried over, one spot's wedge fired "not getting
			// anywhere (5s) - backing off" within a second of arriving at a brand-new station.
			trouble = 0;
			stage = Recovery.Stage.NONE;
			climbTo = null;
			climbedOut = false;
			// ...AND SO DOES THE TAKE-OFF. Four failed taps at one station wrote flight off for the
			// whole session; a new destination gets its own tries.
			regainTries = 0;
			flyCommands = 0;
			regainSaid = false;
		}
		if (dist < bestDist - 0.05) {
			bestDist = dist;
			sinceCloser = 0;
		} else {
			sinceCloser++;
		}
		double ceiling = solidTarget ? ARRIVED_SOLID : exact ? EXACT_ARRIVED : ARRIVED;
		double floor = exact ? EXACT_MIN : ARRIVE_MIN;
		// ...and whether closing any further would mean touching something. See SAFE_GAP: reach is
		// worth having and it is not worth the flight.
		boolean wall = surfaceAhead(mc, p, to.subtract(me), SAFE_GAP);
		boolean landed = landing && (dist <= 0.5 || (p.onGround() && dist < 2.0));
		if (landing ? landed : hasArrived(dist, sinceCloser, floor, ceiling, CLOSING_PATIENCE, wall)) {
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
		if (landing && dist < 2.5) {
			// Touching down: flight ending here is the plan, not an emergency.
			wasFlying = flying;
		} else if (wasFlying && !flying && !p.onGround()) {
			wasFlying = false;
			// Worded carefully: this is not "you took over". The player is often not touching
			// anything, and being told they are in control when they are falling and did nothing is
			// both confusing and, on the one occasion it was this mod's own doing, wrong.
			p.sendSystemMessage(Component.literal("[cscan] flight ended in mid-air — not by you."
				+ " autofly is OFF and the controls are yours; the fall safety is still watching"
				+ " for " + (GUARD_MS / 1000) + "s."));
			halt(mc);
			return;
		}
		wasFlying = flying;

		// ON FOOT IS NOT A STALL — for a FETCH. It used to warn and do nothing here, so any
		// destination reached by walking simply stopped; it walks instead. But only to a container:
		// see walk(), where the rule and the reason for it are written down.

		// ---- YOU HIT SOMETHING. The route said this leg was clear and the world disagreed: a chunk
		// arrived, the printer placed a block, or the straight-line test was optimistic about a
		// corner. Worth a fresh route and worth slowing down — but the first version of this handler
		// did three things wrong at once and produced a flight that turned a few degrees and then
		// sat there:
		//
		//   - it set `pathTo = null`, which is checked BEFORE the MIN_REPATH_TICKS floor, so it ran
		//     a full A* every tick for as long as you were touching the wall;
		//   - it RETURNED before the aim, so the yaw never updated while colliding: it turned once
		//     and then froze, which is exactly what "moves like 5 degrees and gets stuck" looks like;
		//   - and it backed off along that frozen yaw, into whatever was behind, and collided again.
		//
		// Keep steering. Ask for a route through the normal gate, which respects the floor. Climb,
		// because on this island going up clears almost everything. Only after two seconds of solid
		// contact is the route itself declared wrong.
		// ---- ARE WE THREADING SOMETHING? Asked BEFORE the bump is interpreted, because the answer
		// changes what a bump means entirely. Looked up at the next WAYPOINT as well as at the aim,
		// so the alignment starts before the mouth rather than after the first contact with it.
		boolean threading = flying && (isTight(mc, Hud.target() == null ? null : aimCell())
			|| (!path.isEmpty() && isTight(mc, path.get(0))));

		// A ceiling or a floor met in flight is a bump as much as a wall is - and on this server
		// the vertical one is the contact that ends flight. Not while landing, where the floor is
		// the plan.
		boolean bumped = flying && (p.horizontalCollision || (p.verticalCollision && !landing));
		if (bumped) {
			bumps++;
			repathIn = 0;
			if (bumps == 1) {
				p.sendSystemMessage(Component.literal("[cscan] bumped into something — finding a"
					+ " way round"));
			}
			// ---- ASK THE GEOMETRY, DO NOT GUESS. The first version answered every obstacle by
			// climbing, which is one instinct applied to five different situations — and when the
			// thing in the way is a CEILING, or when climbing is what wedged you in the first place,
			// it is the worst available answer.
			//
			// `Nav.escape` already knows how to do this properly: flood outward from where you are
			// and take the reachable cell that gets closest to the goal, whichever direction that
			// turns out to be. It is used here at a short radius, on a timer, because a flood on
			// every tick of contact is the cost that has bitten this file twice.
			// ---- A BUMP IN A ONE-WIDE GAP IS NOT AN OBSTACLE, IT IS A NUDGE.
			//
			// The loop Jack watched: enter the shaft, clip the lip, "find a way round" — which finds
			// the way back OUT, because going round a shaft means not using it — then re-route,
			// which correctly picks the shaft again, and repeat for ever. Two mechanisms fighting,
			// each doing its own job correctly.
			//
			// While threading, a bump means line up better and creep. Only when that has plainly not
			// worked, after WEDGED_TICKS of it, is the passage itself the problem.
			// Counted whenever we are threading and touching, independently of `bumps` — which is
			// reset every STUCK_TICKS. The first version incremented this inside the
			// `bumps < WEDGED_TICKS` branch, so it only ever accumulated because STUCK_TICKS
			// happened to be the smaller number. Raise that constant and the give-up below would
			// silently never fire again.
			if (threading) wedged++;
			if (threading && wedged < WEDGED_TICKS) {
				// line up and creep: see the note above
			} else if (bumps % BUMP_LOOK_EVERY == 1) {
				Nav.Passable free = Bounds.within(Nav.of(mc.level));
				BlockPos here = p.blockPosition();
				java.util.List<BlockPos> round = Nav.escape(free, here, target, BUMP_LOOK,
					System.nanoTime() + Nav.MAX_MILLIS * 1_000_000L / 2);
				if (!round.isEmpty()) {
					path = new java.util.ArrayList<>(Nav.simplify(free, here, round));
					pathTo = target;
					routedFlying = true;
					sinceRepath = 0;
					repathIn = REPATH_TICKS;
					escaping = true;
					partialRoute = true;
					bumps = 1;                          // it has a plan: let it fly the plan
				}
			}
			if (bumps > STUCK_TICKS) {
				// Two seconds pressed against the same thing: the route is not merely stale, it is
				// wrong. Drop it so the next search starts from scratch — once, not every tick.
				bumps = 0;
				pathTo = null;
				path = new java.util.ArrayList<>();
			}
		} else {
			bumps = 0;
			wedged = 0;
		}
		if (wedged > WEDGED_GIVE_UP) {
			// Threaded, aligned, crept, and still going nowhere. The shaft is not the problem to
			// solve any more — the SPOT on the other side of it is not worth this.
			wedged = 0;
			p.sendSystemMessage(Component.literal("[cscan] cannot thread the gap to " + Wand.fmt(
				Hud.target()) + " — giving up on this spot"));
			Hud.abandonSpot();
			forget();
			return;
		}

		// ---- THE LADDER. Everything above this point is a specific answer to a specific problem;
		// this is what happens when all of them have had their turn. It only knows one thing: how
		// long the flight has been getting nowhere.
		boolean moving = legFrom == null || p.position().distanceTo(lastSeenAt) > MOVED_ENOUGH;
		lastSeenAt = p.position();
		if (Recovery.inTrouble(moving, true, false)) {
			trouble++;
		} else if (stage != Recovery.Stage.NONE) {
			// A RUNG IS NOT CANCELLED BY THE MOVEMENT IT CAUSES. Written as "moving means fine",
			// every rung lasted exactly one tick: the back-off's own first step read as progress,
			// the stage reset, and the flight steered straight back into the wedge it was leaving.
			// While a rung is driving, only the rung ends itself - see recover().
		} else {
			trouble = 0;
			// ...and while things are fine, drop a crumb every so often. The way out of a wedge is
			// almost always the way in, and that is the only place we KNOW was open.
			if (++breadcrumbAge > CRUMB_EVERY && !p.horizontalCollision) {
				breadcrumbAge = 0;
				breadcrumb = p.blockPosition();
			}
		}
		if (trouble >= Recovery.BACK_OFF_AT) {
			boolean sealed = Nav.pocket(Nav.of(mc.level), p.blockPosition(),
				Recovery.SEALED_CELLS) < Recovery.SEALED_CELLS;Recovery.Stage want = Recovery.stageFor(trouble, sealed);
			if (want == Recovery.Stage.CLIMB_OUT && climbedOut) {
				// A SECOND CLIMB IS NOT A RUNG. The first ended by handing the flight back at
				// BACK_OFF_AT, so the ladder re-entered at back-off, climbed again, backed off again
				// - 25 blocks up each time and never GO_HOME, because trouble never reached it.
				// Climbed out once and still going nowhere: the spot beyond is not worth this.
				p.sendSystemMessage(Component.literal("[cscan] climbed out and still not getting"
					+ " anywhere toward " + Wand.fmt(target) + " — giving up on this spot"));
				trouble = 0;
				stage = Recovery.Stage.NONE;
				climbedOut = false;
				forget();
				Hud.abandonSpot();
				return;
			}
			if (want != stage) {
				stage = want;
				climbTo = null;
				p.sendSystemMessage(Component.literal("[cscan] not getting anywhere ("
					+ (trouble / 20) + "s) — " + switch (want) {
						case BACK_OFF -> "backing off to open air";
						case CLIMB_OUT -> "climbing out of it";
						case GO_HOME -> sealed ? "shut in — going home" : "giving up, going home";
						default -> "carrying on";
					}));
			}
			if (recover(mc, p, target)) return;
		}

		// ---- ROUTE. Recomputed on a timer and whenever the destination moves, because the world
		// loads in around you and the plan's target changes as you build.
		if (pathTo != null && !pathTo.equals(target)) {
			announcedArrival = false;
			bestDist = Double.MAX_VALUE;                   // a new destination has never been near
			sinceCloser = 0;
		}
		sinceRepath++;
		repathIn--;
		if (needsRepath(pathTo, target, repathIn, routedFlying, flying, sinceRepath)) {
			// A WALKING ROUTE IS A DIFFERENT ROUTE. Clearance alone sends you along a line of air
			// above a floor, which flies beautifully and walks into a hole.
			// ...AND NEVER A ROUTE THAT LEAVES THE FENCE, even to go round something: see Bounds.
			Nav.Passable free = Bounds.within(flying ? Nav.of(mc.level) : Nav.standable(mc.level));
			BlockPos here = p.blockPosition();
			// ONE CLOCK FOR THE WHOLE DECISION. The roomy search, the tight search and the escape
			// flood each had their own budget, so an indoor repath — where the roomy search FAILS
			// as a matter of course — cost three budgets on the client thread every half second.// ...BUT EACH TIER GETS ITS OWN SLICE OF IT. One deadline handed to every tier in turn
			// let the first search that FAILS BY BUDGET spend the whole 25ms: beside a row of shops
			// the cruise and roomy searches fail that way as a matter of course, the tight search
			// that would have found the indoor route got about thirty nodes, and "no route and no
			// way round" was the clock, not the geometry. A tier that finishes early hands its
			// remainder on; a tier that runs out leaves the next one its own share.
			long start = System.nanoTime();
			long total = Nav.MAX_MILLIS * 1_000_000L;
			long deadline = start + total;
			java.util.List<BlockPos> raw = java.util.List.of();
			Nav.Passable used = free;
			boolean partial = false;
			boolean overTopRoute = false;
			if (flying) {
				// ---- OVER THE TOP, BEFORE ANY SEARCH. See OVERTOP_CLEAR: up, across, down. Three
				// waypoints, no search, and nothing in the crossing by construction. Only when this
				// is not the right tool - a short hop, a roof over the ascent - does a search run.
				java.util.List<BlockPos> ot = overTop(mc, free, here, target,
					start + (long) (total * OVERTOP_SHARE));
				if (!ot.isEmpty()) {
					raw = ot;
					overTopRoute = true;
					roomyRoute = true;
				}
			}
			if (raw.isEmpty() && flying) {
				// ---- CRUISE FIRST. A roomy route keeps ONE block of air off every surface, and
				// this server has ended flight at a block's distance from a floor - which is why
				// GROUND_CLEAR is two and a half and not one. A route was the one thing that
				// bypassed that clearance (see the routed step: the clamp has nothing to add while
				// there is a route), so a routed flight over the plate skimmed its paving at the
				// height the clamp forbids everywhere else. Cruise asks for the same clearance the
				// hover keeps, relaxed within ENDS of either end where the work and the chests are.
				Nav.Passable cruise = Bounds.within(Nav.cruiseBetween(mc.level, here, target, CRUISE_BELOW));
				Nav.Route r = Nav.routeEx(cruise, here, target, start + (long) (total * CRUISE_SHARE));
				if (!r.path().isEmpty()) {
					raw = r.path();
					used = cruise;
					partial = !r.complete();
					roomyRoute = true;
				}
			}
			if (raw.isEmpty() && flying) {
				// ---- ROOMY SECOND. A route that keeps a block of air off every surface is a route
				// that never tests whether this server ends flight on contact. Only when there is no
				// such route — a one-wide shaft, a doorway, the taproot — do we accept one that has
				// to touch, and then the alignment and the tight speed take over.
				Nav.Passable roomy = Bounds.within(Nav.roomyBetween(mc.level, here, target));
				Nav.Route r = Nav.routeEx(roomy, here, target, start + (long) (total * ROOMY_SHARE));
				raw = r.path();
				roomyRoute = !raw.isEmpty();
				if (roomyRoute) {
					used = roomy;                  // simplified with the predicate that FOUND it, or
					partial = !r.complete();       // the chords throw the elbow room straight away
				}
			}
			if (raw.isEmpty() && flying) {
				// ---- LIFTED SECOND. A tight route keeps only the two cells the body occupies
				// clear, so its cheapest leg skims a floor at a tenth of a block - and on this
				// server contact ends flight, and Jack has watched it end at a block's distance.
				// Before accepting a route that may hug a floor, look for one with a clear cell
				// under the feet the whole way. Indoors this fails at once (a two-course room has
				// no such cell) and costs almost nothing; in open air it keeps the ride off the deck.
				Nav.Passable base = free;
				Nav.Passable lifted = (x, y, z) -> base.at(x, y, z) && base.at(x, y - 1, z);Nav.Route r = Nav.routeEx(lifted, here, target, start + (long) (total * LIFTED_SHARE));
				if (!r.path().isEmpty()) { raw = r.path(); used = lifted; partial = !r.complete(); }
			}if (raw.isEmpty()) {
				Nav.Route r = Nav.routeEx(free, here, target, start + (long) (total * TIGHT_SHARE));
				raw = r.path();
				partial = !r.complete();
			}
			escaping = false;
			if (raw.isEmpty()) {
				raw = Nav.escape(free, here, target, Nav.ESCAPE_RADIUS, deadline);
				escaping = !raw.isEmpty();
			}
			noRoute = raw.isEmpty();
			// A new bounded route search is a new observation. Keep one strike per SEARCH, never one
			// per tick, so two independent failures abandon the spot without flying at the wall.
			if (noRoute) warnedNoRoute = false;
			if (!flying && noRoute && Hud.targetLand()) groundNoRoute = true;   // cannot walk it: fly
			partialRoute = !noRoute && (partial || escaping);
			path = raw.isEmpty() ? new java.util.ArrayList<>()
				// ...AND AN OVER-THE-TOP ROUTE IS NEVER SIMPLIFIED: its three legs are the point, and
				// a chord from the ascent's foot to the descent's head is the diagonal through the
				// buildings this route exists to fly over.
				: new java.util.ArrayList<>(flying && !overTopRoute ? Nav.loosen(used, here, Nav.simplify(used, here, raw)) : raw);
			legFrom = p.position();                        // the first leg starts where we are
			pathTo = target;
			routedFlying = flying;
			sinceRepath = 0;
			// A FAILED SEARCH IS THE EXPENSIVE ONE: back off hard on failure, stay responsive on
			// success. An ESCAPE or a STAGE is stale as soon as it has been flown — the whole
			// point is to look again from somewhere new — so only a total failure earns the wait.
			repathIn = raw.isEmpty() ? NO_ROUTE_BACKOFF : repathFor(flying ? speed : WALK_SPEED);
		}

		// Steer at the next waypoint rather than at the destination: that is the whole difference
		// between going through the door and pressing on the wall beside it.
		Vec3 aim = to;
		// From the speed actually being flown (last tick's), not the dial: at dial 1.5 crawling
		// through a bend at 0.45, the dial's radius popped a waypoint 3.75 blocks early and the
		// pursuit chord cut the corner that waypoint was there to round.
		double near = waypointRadius(flying ? Math.min(speed, Math.max(appliedSpeed, CORNER_SPEED)) : WALK_SPEED);while (!path.isEmpty() && (flying
			? popped(me, legFrom, flyTo(path.get(0)), path.size() > 1 ? flyTo(path.get(1)) : null, near)
			: WalkingSpace.arrived(me, path.get(0)))) {
			legFrom = flyTo(path.get(0));                 // the leg we are on starts where we passed
			path.remove(0);
		}
		if (path.isEmpty() && partialRoute) {
			// THE END OF A STAGE IS NOT THE END OF THE ROUTE. Search again from here, now, rather
			// than flying direct at whatever the stage was going round.
			partialRoute = false;
			repathIn = 0;
			sinceRepath = MIN_REPATH_TICKS;
		}
		if (!flying) {
			// Ground travel must never fall through to direct steering after a failed search.
			boolean valid = !path.isEmpty();
			if (valid && p.onGround()) {
				BlockPos start = p.blockPosition(), next = path.get(0);
				Nav.Passable ground = Bounds.within(Nav.standable(mc.level));
				valid = start.equals(next) ? ground.at(next.getX(), next.getY(), next.getZ())
					: Nav.stepFits(ground, start.getX(), start.getY(), start.getZ(),
						next.getX()-start.getX(), next.getY()-start.getY(), next.getZ()-start.getZ());
			}
			if (!valid) {
				release(mc);
				p.setDeltaMovement(0, p.getDeltaMovement().y, 0);
				appliedSpeed = 0;
				slowBecause = "waiting for supported walking route";
				if (!path.isEmpty()) { path.clear(); repathIn = 0; }
				return;
			}
			aim = Vec3.atBottomCenterOf(path.get(0));
		}
		if (flying && !path.isEmpty()) {
			// ---- FLY THE SEGMENT, NOT THE POINT.
			//
			// `clear` validated waypoint-to-WAYPOINT. What actually gets flown is
			// wherever-I-am to waypoint, and the moment drift, a bump or a corner puts the body off
			// that line, the leg being flown is NOT the leg that was checked — it is a chord across
			// whatever the route was going round. That is the structural reason for "still lots of
			// bumping", underneath every heuristic bolted on after the contact.
			//
			// So: steer at the nearest point on the validated segment, a little way ahead. Off the
			// line it pulls back onto it; on the line it is the same as before.
			aim = pursue(me, legFrom == null ? me : legFrom, flyTo(path.get(0)),
				LOOKAHEAD);
		}

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

		// ---- MEASURE AGAINST THE WAYPOINT, NOT THE AIM.
		//
		// `aim` is the pure-pursuit point and it sits LOOKAHEAD blocks ahead BY CONSTRUCTION, so
		// measuring the approach against it says "1.5 blocks to go" on every tick of a two-hundred
		// block flight — and the taper below then held the whole journey at 0.125 against a cruise
		// of 0.75. The bend check read off the same point and saw a permanent corner on top of it.
		//
		// The waypoint is the thing being approached. The aim is only where to point.
		Vec3 wp = path.isEmpty() ? to : flyTo(path.get(0));
		boolean bend = false;
		if (path.size() >= 2) {
			Vec3 thisLeg = wp.subtract(me);
			Vec3 nextLeg = flyTo(path.get(1)).subtract(wp);
			if (thisLeg.lengthSqr() > 1.0e-6 && nextLeg.lengthSqr() > 1.0e-6) {
				bend = thisLeg.normalize().dot(nextLeg.normalize()) < CORNER_COS;
			}
		}
		double speed = cruiseSpeed(cruise, dist, me.distanceTo(wp), near, bend, path.size() <= 1);
		slowBecause = speed >= cruise - 1.0e-6 ? ""
			: bend ? "corner" : path.size() <= 1 ? "arriving" : "?";

		if (path.isEmpty() && noRoute) {
			// ---- NO ROUTE AND NO WAY ROUND. Said ONCE PER PLACE, and counted: the second time a
			// place beats the router it is written off rather than reported again. Repeating the
			// message is the same fault as returning to the spot — see Ignored. `noRoute`, not an
			// empty path: a stage or a way round that has just been flown to its end is an empty
			// path too, and used to earn the strike for a route that was working.
			if (!warnedNoRoute) {
				warnedNoRoute = true;
				// STRIKE THE THING THE LOOP CHOOSES BY. It filters spots by their centre; a strike
				// on the stand position — up to fifty blocks from that centre — landed on a key
				// nothing ever looked up, and no spot was ever actually ignored.
				if (Ignored.strike(Hud.strikeKeyFor(target))) {
					p.sendSystemMessage(Component.literal("[cscan] no route to " + Wand.fmt(target)
						+ " again — marking it IGNORED (red) and taking another spot."));
					Highlight.show("ignore", Ignored.marks(), 0xFF3030, 600);
					Hud.abandonSpot();
					forget();
					return;
				}
				p.sendSystemMessage(Component.literal("[cscan] no route and no way round to "
					+ Wand.fmt(target) + " — holding position; one more failed search marks it ignored."));
			}
			// Direct flight after a failed search is not a fallback: it is an instruction to collide
			// with the obstacle the search just proved it cannot pass. Hold for the bounded re-search.
			release(mc);
			p.setDeltaMovement(Vec3.ZERO);
			appliedSpeed = 0;
			slowBecause = "no route";
			return;
		} else {
			warnedNoRoute = false;
		}

		// ---- DO NOT FLY INTO WHAT YOU CANNOT SEE. See BLIND_SPEED.
		boolean blind = flying && !loadedAhead(view(mc), p.position(), dir, sightFor(speed));
		if (blind) {
			if (speed > BLIND_SPEED) slowBecause = "chunks not loaded";
			speed = Math.min(speed, BLIND_SPEED);
		}
		appliedSpeed = speed;

		if (flying) {
			Vec3 step = dir.scale(speed);
			// ...and never descend into it: an absent chunk answers "air" to every question, so the
			// floor of the lowland is indistinguishable from open void until you are standing on it.
			if (blind && step.y < 0) step = new Vec3(step.x, 0, step.z);
			// Only ever applied to the DIRECT guess. A real route is already clear, and second-
			// guessing it here is how you fight your own pathfinder at a doorway.
			if (path.isEmpty()) step = unstick(mc, p, step);
			// ---- LINE UP FOR A TIGHT GAP BEFORE ENTERING IT. See align().
			boolean[] lock = boxedAxes(mc, aim);
			// ---- AND SLOW FOR A GAP ONLY WHILE ACTUALLY CORRECTING IN IT.
			//
			// Being in a one-wide lane is not a reason to crawl; being OFF CENTRE in one is, because
			// creeping forward off to one side is how you catch the lip you were threading. Once
			// lined up, align() already hands the step straight back unchanged - and the flight was
			// still being held at a fifteenth of cruise for the whole passage anyway.
			if ((lock[0] || lock[1] || lock[2]) && offCentre(me, aim, lock) > ALIGN_TOL) {
				if (speed > TIGHT_SPEED) slowBecause = "threading";
				speed = Math.min(speed, TIGHT_SPEED);
				step = align(me, aim, lock, dir.scale(speed), ALIGN_TOL, speed);
			}
			if (bumped) {
				if (path.isEmpty()) {
					// Nothing to route along and something in the way: slide, and pick the direction
					// by what is actually OPEN. See sidestep — "up" is one of five answers, and the
					// version that always climbed made a ceiling worse and a wedge permanent.
					Vec3 out = sidestep(dir,
						openAt(mc, p, 0, 3, 0), openAt(mc, p, 0, -2, 0),
						openAt(mc, p, -dir.z, 0, dir.x), openAt(mc, p, dir.z, 0, -dir.x),
						openAt(mc, p, -dir.x, 0, -dir.z));
					step = out.scale(Math.max(speed * 0.5, RISE));
				} else {
					step = new Vec3(step.x * 0.4, step.y, step.z * 0.4);   // easing round a corner
				}
			}
			// ---- AND THE GROUND CLEARANCE DOES NOT ARGUE WITH A ROUTE.
			//
			// It refuses to descend inside 2.5 blocks of a floor, and a two-course corridor has about
			// one - so on a route through anything indoors the vertical was clamped to zero and the
			// flight rode the ceiling of wherever it happened to be while the pursuit point pulled it
			// forward. That is the head grinding. The route was checked by Nav and avoid below now
			// guarantees no step touches anything, so the clamp has nothing to add while there is a
			// route; it is for the direct guess and for holding still at a spot.
			// ...EXCEPT THAT A ROUTE WHICH STAYS HIGH IS HELD HIGH TOO. The bypass exists for routes
			// that genuinely go low - a doorway, a two-course room - where the clamp would refuse the
			// descent the route needs. When the next waypoint has the clearance under it anyway, the
			// clamp changes nothing about the route and everything about the drift toward the floor
			// between waypoints, which is where a flight over the plate has been ending.
			boolean routeLow = !path.isEmpty() && !routeStaysHigh(mc, path.get(0), exact ? EXACT_CLEAR : GROUND_CLEAR);
			if (!routeLow && !landing) step = keepAirborne(mc, p, step, exact ? EXACT_CLEAR : GROUND_CLEAR);
			// Scaled, not pressed — for the CLIMB. See the note on VERTICAL_GAIN and, more
			// importantly, the one above it about what the jump key actually does.
			step = liftFor(step, Math.max(speed, RISE) * 1.5);
			// Going down is the half that can safely use a key: sneak toggles nothing.
			sink(mc, step.y < -CLIMB_DEADZONE);
			// ---- AND DO NOT SEND A STEP THAT TOUCHES ANYTHING. Last, after every other rule has
			// had its say, because it is the only one that is about the world rather than the plan.
			// ---- NEVER PAST THE FENCE, and then never into a block. The fence runs FIRST: when the
			// body is already outside it, clamp ADDS a pull back toward the box, and a component
			// nothing has tested against the world is exactly what avoid exists to catch. Inside
			// the box clamp only ever shortens an axis, which avoid then cannot make unsafe.
			step = Bounds.clamp(me, step);
			step = avoid(p, step);
			p.setDeltaMovement(step);
		} else {
			release(mc);                               // on foot the vertical is the ground's job
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
		// ...and a LANDING, which is a floor by construction: the whole point of Hud.Mode.LAND is
		// that the body stands beside the work and walks to the next patch of it. Written without
		// this, needsFlight said "walk" and this gate said "not a fetch", and a landed body never
		// moved again.
		if (!Hud.fetching() && !Hud.targetLand()) {
			if (!warnedFalling) {
				warnedFalling = true;
				p.sendSystemMessage(Component.literal("[cscan] flight is off and building needs it"
					+ " — trying to get it back; /fly if that does not take."));
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
		walkOn(mc, p, dir, aim, speed);
	}

	private static void walkOn(Minecraft mc, LocalPlayer p, Vec3 dir, Vec3 aim, double speed) {
		Vec3 flat = new Vec3(dir.x, 0, dir.z);
		if (flat.lengthSqr() < 1.0e-6) {
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
		Vec3 fenced = Bounds.clamp(p.position(), new Vec3(flat.x * speed, 0, flat.z * speed));
		p.setDeltaMovement(fenced.x, y, fenced.z);
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
	 * <p>Was a block and a half, which is enough that a slab or a lip cannot catch a foot and NOT
	 * enough for the server: Jack, watching it work, <i>"it cant be within 1 block beneath when
	 * flying to place because it will auto stop flying"</i>. Whatever the plugin measures, it is
	 * looking further down than the block you are touching. Two and a half, and the standoff refuses
	 * to pick a cell with less air under it than that.
	 *
	 * <p>It is bought out of the printer's reach budget, which is why the station moves in CLOSER on
	 * its first stall rather than giving up: altitude first, reach second.
	 */static final double GROUND_CLEAR = 2.5;

	/**
	 * OVER THE TOP. Jack, after a day of router fixes: <i>"its path finding and flying is still
	 * really bad, constant collisions, running right into objects."</i> Every one of those was a
	 * flight THROUGH built space - a route threaded between shops, under awnings, past corners - and
	 * every fix made the threading a little better without making it safe. A player with /fly does
	 * not thread anything: they go UP, cross in open sky, and come DOWN on the spot. Three legs, two
	 * of them vertical, the third with nothing in it by construction.
	 *
	 * <p>{@link #OVERTOP_CLEAR} is how far over the corridor's highest surface the crossing runs
	 * (more than GROUND_CLEAR, so the clamp never argues with it); {@link #OVERTOP_MARGIN} widens
	 * the corridor for drift; {@link #OVERTOP_MIN} is the horizontal distance under which a hop is
	 * left to the router - a station's orbit stops, a chest two blocks away. Where the descent
	 * column is roofed - a target indoors - the descent stops on the roof and the router does the
	 * last few blocks, which is the one place it has ever been good.
	 */
	static final int OVERTOP_CLEAR = 3, OVERTOP_MARGIN = 2, OVERTOP_MIN = 4;

	/** The crossing height: over the corridor's top, never below where we already are, inside the world. */
	static int cruiseHeight(int corridorTop, int hereY, int worldMaxY) {
		return Math.min(Math.max(corridorTop + OVERTOP_CLEAR, hereY), worldMaxY);
	}

	/** Up to the crossing height, across to the target's column, down to the target. Degenerate legs dropped. */
	static java.util.List<BlockPos> overTopLegs(BlockPos here, BlockPos target, int cruise) {
		java.util.List<BlockPos> legs = new java.util.ArrayList<>();
		BlockPos up = new BlockPos(here.getX(), cruise, here.getZ());
		BlockPos over = new BlockPos(target.getX(), cruise, target.getZ());
		if (!up.equals(here)) legs.add(up);
		if (!over.equals(up)) legs.add(over);
		if (!target.equals(over)) legs.add(target);
		return legs;
	}

	/** Highest MOTION_BLOCKING surface over the corridor from a to b, or MIN_VALUE if none of it is loaded. */
	private static int corridorTop(Minecraft mc, BlockPos a, BlockPos b, long deadline) {
		int dx = b.getX() - a.getX(), dz = b.getZ() - a.getZ();
		int n = Math.max(Math.abs(dx), Math.abs(dz));
		double len = Math.max(1e-9, Math.hypot(dx, dz));
		double px = -dz / len, pz = dx / len;                // the perpendicular, for the margin
		int top = Integer.MIN_VALUE;
		// SAMPLED, not walked cell by cell. A 600-block corridor was 600 steps of five heightmap
		// lookups before anything else happened. Under-sampling cannot produce a collision, only a
		// crossing height that is too low - and `Nav.clear` then rejects those legs and the search
		// tiers get their turn, which is the outcome an honest failure should have.
		int step = Math.max(1, n / CORRIDOR_SAMPLES);
		for (int i = 0; i <= n; i += step) {
			if ((i & 15) == 0 && System.nanoTime() > deadline) return Integer.MIN_VALUE;
			double t = n == 0 ? 0 : (double) i / n;
			double x = a.getX() + 0.5 + dx * t, z = a.getZ() + 0.5 + dz * t;
			for (int m = -OVERTOP_MARGIN; m <= OVERTOP_MARGIN; m++) {
				int cx = (int) Math.floor(x + px * m), cz = (int) Math.floor(z + pz * m);
				if (!mc.level.hasChunk(cx >> 4, cz >> 4)) continue;
				top = Math.max(top, mc.level.getHeight(Heightmap.Types.MOTION_BLOCKING, cx, cz));
			}
		}
		return top;
	}

	/** The lowest cell on the way down from `from` toward `to` that the body can still reach in a straight line. */
	private static BlockPos lowestClear(Nav.Passable free, BlockPos from, BlockPos to) {
		BlockPos best = null;
		for (int y = from.getY() - 1; y >= to.getY(); y--) {
			BlockPos c = new BlockPos(to.getX(), y, to.getZ());
			if (!Nav.clear(free, from, c)) break;
			best = c;
		}
		return best;
	}

	/**
	 * The over-the-top route, or empty when it is not the right tool: too short a hop, nothing of
	 * the corridor loaded, a ceiling over the ascent, or a fence that forbids the height.
	 */
	private static java.util.List<BlockPos> overTop(Minecraft mc, Nav.Passable free, BlockPos here,
	                                               BlockPos target, long deadline) {
		double flat = Math.hypot(target.getX() - here.getX(), target.getZ() - here.getZ());
		if (flat < OVERTOP_MIN) return java.util.List.of();
		// ---- BUDGETED AND RANGED. This ran before any tier deadline was consulted and was gated
		// only on being further than four blocks, so a cross-park hop walked thousands of heightmap
		// lookups and tens of thousands of `Nav.clear` samples FIRST - and every tier then "failed"
		// on a deadline that had already passed, reporting no route where the geometry was never
		// examined. It gets its own slice, and past `Nav.MAX_RANGE` there is no route to find
		// anyway, so there is nothing to fly over.
		if (flat > Nav.MAX_RANGE) return java.util.List.of();
		int top = corridorTop(mc, here, target, deadline);
		if (top == Integer.MIN_VALUE) return java.util.List.of();
		int cruise = cruiseHeight(top, here.getY(), mc.level.getMaxY() - 2);
		java.util.List<BlockPos> legs = overTopLegs(here, target, cruise);
		java.util.List<BlockPos> out = new java.util.ArrayList<>();
		BlockPos prev = here;
		for (int i = 0; i < legs.size(); i++) {
			if (System.nanoTime() > deadline) return java.util.List.of();
			BlockPos wp = legs.get(i);
			if (!Bounds.contains(wp)) return java.util.List.of();
			if (!Nav.clear(free, prev, wp)) {
				if (i == legs.size() - 1 && !out.isEmpty()) {
					// A ROOFED DESCENT stops on the roof; the router takes it from there.
					BlockPos low = lowestClear(free, prev, wp);
					if (low != null) out.add(low);
					return out;
				}
				return java.util.List.of();               // a ceiling over the ascent, or a wall at the crossing height
			}
			out.add(wp);
			prev = wp;
		}
		return out;
	}
	/** How many points along a corridor the heightmap is sampled at, however long it is. */
	static final int CORRIDOR_SAMPLES = 128;
	/** The share of one route call's budget the over-the-top check may spend before any search. */
	static final double OVERTOP_SHARE = 0.15;

	/** Clear cells a CRUISE route keeps under the body in its middle: the hover's own clearance. */
	static final int CRUISE_BELOW = (int) Math.ceil(GROUND_CLEAR);
	/**
	 * Where each route tier's deadline falls as a fraction of {@link Nav#MAX_MILLIS}. Cruise, roomy,
	 * lifted, tight, and the escape flood takes what is left. The order is the safety order; the
	 * shares are what stops a safe tier that cannot succeed from starving the one that can.
	 */
	static final double CRUISE_SHARE = 0.25, ROOMY_SHARE = 0.45, LIFTED_SHARE = 0.60, TIGHT_SHARE = 0.90;
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
	 * ...and it has to grow with the speed, or the guard stops guarding.
	 *
	 * <p>Eight blocks is five ticks of travel at 1.5 and a whole second at 0.4. A lookahead measured
	 * in BLOCKS is a lookahead that shrinks as you go faster, which is backwards: the whole point is
	 * to see the unloaded world before arriving in it. Six tenths of a second of travel, floored at
	 * the old eight so nothing got shorter.
	 */
	static int sightFor(double speed) {
		return Math.max(SIGHT, (int) Math.ceil(speed * 12.0));
	}

	/**
	 * Never touch down.
	 *
	 * <p>Applied to the flying step only, and it does two things: it refuses to DESCEND inside the
	 * clearance, and it climbs when already at or under it. Both are needed — the first stops you
	 * arriving at a floor, the second gets you off one you have already met, including the case
	 * where the ground came up to you because the terrain rose.
	 */
	/**
	 * Air to leave between the body and a block when clipping a step. Under a tick of travel, so it
	 * can never stop a flight short of somewhere it has to get to, and enough that the server's own
	 * rounding cannot land the box flush against a face.
	 */
	static final double SKIN = 0.12;

	/**
	 * THE STEP THAT IS SENT MUST NOT TOUCH ANYTHING.
	 *
	 * <p>Everything else in this file reacts to contact - climb over it, slide round it, ease off
	 * the corner, get flight back, tap it on again, rescue the fall. All of it is downstream of one
	 * decision made here: a heading is normalised, scaled by the speed and WRITTEN, and whatever
	 * that vector runs into is Minecraft's problem. Minecraft solves it by clipping the movement
	 * against the block - which is to say BY TOUCHING IT - and on this server touching a block ends
	 * flight. Every heuristic above is standing in for a velocity that should never have been sent.
	 *
	 * <p>Baritone never has this problem, and not because its search is better: it does not write
	 * velocities at all. It presses movement keys along a path of cells it has already proved a body
	 * fits through, and re-proves each one as it goes. We cannot press keys to fly - the jump key is
	 * a flight TOGGLE, which this mod has already revoked its own flight with once - so the
	 * equivalent is to do the collision test OURSELVES, before sending, and drop whatever would land
	 * us against a face.
	 *
	 * <p>Per axis, so a step into a wall SLIDES along it rather than stopping dead: that is the same
	 * resolution the game does, arrived at a tick earlier, while there is still something to be done
	 * about it. The box is inflated by {@link #SKIN} so it stops SHORT of the block rather than
	 * flush against it.
	 *
	 * <p><b>An already-touching body must still be able to move.</b> Inflated, a flight legitimately
	 * parked a block off a wall fails every axis and freezes - which is a worse failure than the one
	 * being fixed, because it is silent. So when the cushion is already occupied the axis is judged
	 * on the real box, which lets it move away from what it is against.
	 */
	static Vec3 avoid(LocalPlayer p, Vec3 step) {
		net.minecraft.world.phys.AABB body = p.getBoundingBox();
		// ---- THE VOLUME SWEPT, NOT THE BOX AT THE FAR END.
		//
		// A body 0.6 wide displaced by 0.75 leaves 0.15 of its path untested; displaced by 1.5 it
		// leaves 0.9, which is room for a whole block to sit in unseen. Tested at the destination
		// only, a fast step TUNNELS: the check says clear, the game says otherwise, and the faster
		// it goes the wider the hole. expandTowards is the swept volume, so the test is about the
		// journey rather than about the arrival and holds at any speed.
		//
		// ---- AND THE CUSHION IS PER AXIS, WITH ALMOST NONE OF IT VERTICAL.
		//
		// Inflated on all three, a body 1.8 tall in a two-course corridor is 2.04 and collides with
		// the corridor itself - so the "already touching, use the real box" fallback fired EVERYWHERE
		// indoors and the horizontal cushion was silently switched off in exactly the places it was
		// for. A two-course gap cannot afford a vertical cushion by construction; it can afford a
		// horizontal one, and that is the one that keeps a flight off walls.
		return avoid(step, d -> {
			double px = d.x != 0 ? SKIN : 0, pz = d.z != 0 ? SKIN : 0;
			double py = d.y != 0 ? Math.min(SKIN, 0.02) : 0;
			net.minecraft.world.phys.AABB box = body.inflate(px, py, pz);
			// Already inside the cushion on this axis: judge on the real box, so a flight parked
			// against something can still move away from it.
			if (!p.level().noCollision(p, box)) box = body;
			return p.level().noCollision(p, box.expandTowards(d.x, d.y, d.z));
		});
	}

	/**
	 * The axis rule on its own, so it can be argued with without a client.
	 *
	 * @param fits whether the body may be displaced by that offset without meeting anything
	 */
	static Vec3 avoid(Vec3 step, java.util.function.Predicate<Vec3> fits) {
		if (step.lengthSqr() < 1.0e-9) return step;
		double x = step.x, y = step.y, z = step.z;
		if (x != 0 && !fits.test(new Vec3(x, 0, 0))) x = 0;
		if (y != 0 && !fits.test(new Vec3(0, y, 0))) y = 0;
		if (z != 0 && !fits.test(new Vec3(0, 0, z))) z = 0;
		// ...AND THE STEP THAT IS ACTUALLY SENT. Each axis can be clear on its own while the
		// diagonal clips a block's corner - the game resolves the axes in sequence from the moved
		// position. Test the combination, and give up the smaller horizontal component first.
		if (!fits.test(new Vec3(x, y, z))) {
			if (Math.abs(x) < Math.abs(z)) x = 0; else z = 0;
			if (!fits.test(new Vec3(x, y, z))) { x = 0; z = 0; }
			if (!fits.test(new Vec3(x, y, z))) y = 0;
		}
		return new Vec3(x, y, z);
	}

	/** Does the next waypoint itself keep `clear` air under the body? Then the route is not going low. */
	private static boolean routeStaysHigh(Minecraft mc, BlockPos wp, double clear) {
		Vec3 at = flyTo(wp);
		return clearanceBelow(view(mc), at.x, at.y, at.z, (int) Math.ceil(clear) + 1) > clear;
	}

	private static Vec3 keepAirborne(Minecraft mc, LocalPlayer p, Vec3 step, double clear) {
		// ...unless there is a ceiling. Indoors — the store hall, the entrance, the undercroft — a
		// room can be two courses high, and forcing a climb there just grinds you along the ceiling.
		// Landing on a floor inside a building is not the failure this guards against: that failure
		// is landing on the deck with the void one step away.
		boolean headroom = !mc.level.getBlockState(
			BlockPos.containing(p.getX(), p.getY() + 2.6, p.getZ())).blocksMotion();
		// NO CLIMBING INTO A CEILING. Every upward push in this file — the ground clearance, the bump
		// handler, the direct-flight unstick — raises y, and with something directly overhead that is
		// a body grinding along the underside of a floor for as long as it is there. Jack, watching
		// it work: "we bump our head a lot".
		if (!headroom) step = new Vec3(step.x, Math.min(step.y, 0), step.z);
		if (p.onGround()) return headroom ? new Vec3(step.x, RISE, step.z) : step;
		double air = clearanceBelow(view(mc), p.getX(), p.getY(), p.getZ(),
			(int) Math.ceil(clear) + 1);
		if (air > clear) return step;
		double lift = headroom && air < clear * 0.6 ? RISE : 0.0;
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
		// ---- ALL FOUR CORNERS OF THE BODY, AND THE WORST OF THEM.
		//
		// The centre column alone is not what a flight lands on. The player is 0.6 wide, so half a
		// block either side of the point this used to sample is the box that actually meets the
		// floor - and over a LEDGE those disagree completely: the centre reads open void while a
		// corner is over the deck. The flight then descends happily onto the corner it never
		// looked at, touches down, and the plugin takes the flight away. That is what dropping
		// flight at an edge is, and it is the same 'sampled the centre line' fault that once let
		// simplify() straighten a route between two blocks.
		double best = depth;
		for (double ox : new double[]{-0.31, 0.31}) {
			for (double oz : new double[]{-0.31, 0.31}) {
				best = Math.min(best, column(w, px + ox, py, pz + oz, depth));
			}
		}
		return best;
	}

	private static double column(View w, double px, double py, double pz, int depth) {
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

	/**
	 * Which way to slide when the way ahead is blocked and there is no route to follow.
	 *
	 * <p>Pure, so the priorities can be argued with in a test rather than in the air. The caller
	 * probes the world and passes what is open.
	 *
	 * <p>The ORDER is the point. Sideways first, because sliding along a face is how you get round
	 * the end of it, and it keeps whatever progress the bump did not eat. Then UP — the old
	 * unconditional answer, right perhaps a third of the time. Then DOWN, which nothing used to
	 * consider at all and is the correct answer to a ceiling, an overhang, or a climb that is what
	 * wedged you in the first place. Back last: it undoes progress, but it beats vibrating.
	 */
	static Vec3 sidestep(Vec3 dir, boolean up, boolean down, boolean left, boolean right,
	                     boolean back) {
		Vec3 flat = new Vec3(dir.x, 0, dir.z);
		flat = flat.lengthSqr() > 1.0e-6 ? flat.normalize() : new Vec3(1, 0, 0);
		Vec3 side = new Vec3(-flat.z, 0, flat.x);
		Vec3 aim = dir.lengthSqr() > 1.0e-6 ? dir.normalize() : flat;

		// EVERY direction, scored by whether it actually helps, rather than a fixed ladder with
		// `down` at the bottom of it. The ladder version only ever descended when climbing was
		// blocked — so flying to anything BELOW you, which on this island is the lowland, the belly
		// and half the deck, met an obstacle and went the wrong way over it.
		Vec3[] ways = {side, side.scale(-1), new Vec3(0, 1, 0), new Vec3(0, -1, 0), flat.scale(-1)};
		boolean[] open = {left, right, up, down, back};
		Vec3 best = null;
		double bestScore = -Double.MAX_VALUE;
		for (int k = 0; k < ways.length; k++) {
			if (!open[k]) continue;
			// ...with a thumb on the scale for sideways. A purely horizontal target scores every
			// perpendicular the same, and sliding along the face is the one that gets round the end
			// of it; up and down from a level heading are detours.
			double score = aim.dot(ways[k]) + (k < 2 ? SIDE_BIAS : 0);
			if (score > bestScore) {
				bestScore = score;
				best = ways[k];
			}
		}
		return best == null ? new Vec3(0, 1, 0) : best;    // boxed in: up is the least-bad guess
	}

	// ---- THREADING A ONE-WIDE GAP.
	//
	// Jack: "we also need to do better at being able to locate areas we can fly through e.g. 1x open
	// spaces we can fly up through if we align correctly, it gets stuck quite a lot still."
	//
	// The ROUTE through those is already found — `Nav` models a body 0.8 wide and a one-wide shaft
	// passes it, and the island is full of them: the taproot, the workshop necks, the well. What
	// fails is the FLYING. Steering at a waypoint centre from off to one side arrives at the mouth
	// still carrying that lateral drift, catches the lip, and bumps — and then the bump handler goes
	// round something it was already lined up with.
	//
	// So: when the way ahead is walled on both sides of an axis, CENTRE THAT AXIS FIRST and make no
	// progress along the passage until it is lined up. It is what a player does without thinking.

	/** Off-centre by more than this and it is worth straightening before going on. */
	static final double ALIGN_TOL = 0.18;
	/** Speed through a gap you have to be lined up for. */
	static final double TIGHT_SPEED = 0.10;

	/**
	 * Centre yourself in whichever lanes are walled, before moving along the one that is not.
	 *
	 * @param lock which axes are boxed in — {x, y, z}
	 * @return the step to take: a pure correction while off-centre, otherwise the step asked for
	 */
	/** How far off the middle of the LOCKED lanes we are. The question align() asks first. */
	static double offCentre(Vec3 me, Vec3 centre, boolean[] lock) {
		double dx = lock[0] ? centre.x - me.x : 0;
		double dy = lock[1] ? centre.y - me.y : 0;
		double dz = lock[2] ? centre.z - me.z : 0;
		return Math.sqrt(dx * dx + dy * dy + dz * dz);
	}

	static Vec3 align(Vec3 me, Vec3 centre, boolean[] lock, Vec3 step, double tol, double speed) {
		double dx = lock[0] ? centre.x - me.x : 0;
		double dy = lock[1] ? centre.y - me.y : 0;
		double dz = lock[2] ? centre.z - me.z : 0;
		double off = offCentre(me, centre, lock);        // one source: the gate above asks the same
		if (off <= tol) return step;
		// Nothing along the passage until the lanes line up. Creeping forward while still off to one
		// side is exactly how you catch the lip you were trying to thread.
		Vec3 fix = new Vec3(dx, dy, dz).normalize().scale(Math.min(speed, off));
		return fix;
	}

	/**
	 * How fast to travel: cruise, tapered near the destination and near a bend.
	 *
	 * <p>Pure, because it was inline and wrong for an hour — fed the pursuit point instead of the
	 * waypoint, which is always {@link #LOOKAHEAD} away, so a two-hundred-block flight ran the whole
	 * way at the speed meant for the last block of it.
	 *
	 * @param toTarget   distance to the DESTINATION, which is what the final slow-down is about
	 * @param toWaypoint distance to the next waypoint, which is what the corner slow-down is about
	 */
	static double cruiseSpeed(double cruise, double toTarget, double toWaypoint, double near,
	                          boolean bend) {
		return cruiseSpeed(cruise, toTarget, toWaypoint, near, bend, true);
	}

	/**
	 * @param lastLeg is the next waypoint the DESTINATION, or just a corner on the way?
	 *
	 * <p>This is the second half of the same bug. The taper exists so the flight does not overshoot
	 * where it is GOING — and it was applied to every waypoint, including the dozens of corners a
	 * route through cluttered terrain is made of. On the deck, waypoints land about four blocks
	 * apart, so `toWaypoint` was never more than four, the taper fired on every tick, and the whole
	 * flight ran at `4/12` = 0.33 against a cruise of 0.75. Exactly half speed, which is what it
	 * looked like.
	 *
	 * <p>A corner does not need slowing down FOR ITSELF — {@code bend} already covers turning — and
	 * flying past an intermediate waypoint at speed is not overshooting anything. Only the last one
	 * is a place to stop.
	 */
	static double cruiseSpeed(double cruise, double toTarget, double toWaypoint, double near,
	                          boolean bend, boolean lastLeg) {
		double v = Math.min(cruise, toTarget / 8.0 + 0.05);
		// ---- A CORNER SLOWS YOU DOWN NEAR THE CORNER, NOT FOR THE WHOLE LEG UP TO IT.
		//
		// `bend` is the angle between the leg being flown and the one after it, and that angle
		// barely changes as you travel the leg - so it was true from the moment the leg started.
		// A sixty-block run toward a corner ran all sixty at CORNER_SPEED: at cruise 1.5 that is
		// thirty seconds to cross a room, which is what "it goes hyper slow" looks like. This is the
		// THIRD time a taper in this function has been applied to the whole journey instead of the
		// end of it, and it is the same mistake each time: the thing being approached is not the
		// thing being measured against.
		//
		// It is also floored at a fraction of cruise rather than pinned to a constant. 0.10 was a
		// seventh of the old cruise and is a fifteenth of this one; a corner does not get sharper
		// because the dial went up.
		if (bend && toWaypoint < near * 2) v = Math.min(v, Math.max(CORNER_SPEED, cruise * 0.30));
		if (lastLeg && toWaypoint < near * 3) v = Math.min(v, Math.max(0.06, toWaypoint / 12.0));
		return v;
	}

	/** How far along the validated segment to look. Short: this is a correction, not a shortcut. */
	static final double LOOKAHEAD = 1.5;
	/** Where the leg being flown started, so the flight can stay ON it rather than near it. */
	private static Vec3 legFrom = null;
	/**
	 * The speed actually applied last tick, and why it is not the dial.
	 *
	 * <p>The HUD showed the DIAL, which is the one number guaranteed not to be the problem. Two
	 * separate taper bugs held the flight at a third of it for hours of testing, and either would
	 * have been a glance to spot if the readout had said what was really being flown.
	 */
	private static double appliedSpeed = 0;
	private static String slowBecause = "";

	/**
	 * The point to steer at: the nearest point on the segment, a little way along it.
	 *
	 * <p>Pure pursuit, and the reason for it is that a route is a set of CORRIDORS rather than a set
	 * of points. Steering straight at the next point from wherever you have drifted to cuts the
	 * corner off the corridor that was checked; steering at the segment holds you inside it.
	 */
	static Vec3 pursue(Vec3 me, Vec3 from, Vec3 to, double lookahead) {
		Vec3 leg = to.subtract(from);
		double len2 = leg.lengthSqr();
		if (len2 < 1.0e-6) return to;
		double t = me.subtract(from).dot(leg) / len2;      // how far along we are
		t = Math.max(0, Math.min(1, t));
		Vec3 onLine = from.add(leg.scale(t));
		double step = Math.min(lookahead, Math.sqrt(len2) * (1 - t));
		return onLine.add(leg.normalize().scale(step));
	}

	/** How much to prefer sliding along a face over leaving it. See sidestep. */
	static final double SIDE_BIAS = 0.15;

	/**
	 * Which axes are walled on BOTH sides at this point: the lanes you have to be centred in.
	 *
	 * <p>Measured at the target rather than at the player, because the point is to be lined up
	 * BEFORE arriving. A one-wide vertical shaft locks x and z and leaves y open, which is exactly
	 * the instruction: get over the hole, then go down it.
	 */
	private static boolean[] boxedAxes(Minecraft mc, Vec3 at) {
		BlockPos c = BlockPos.containing(at.x, at.y, at.z);
		return new boolean[] {
			solidAt(mc, c.east()) && solidAt(mc, c.west()),
			// ---- THE VERTICAL IS NOT A LANE YOU THREAD.
			//
			// It used to be: floor below, ceiling two above, which is a two-course corridor - and a
			// two-course corridor is what Nav.Passable guarantees EVERYWHERE. So the check fired on
			// every route through anything with a roof, which on this island is the whole deck, the
			// undercroft, the store hall and every doorway; the flight then crawled at TIGHT_SPEED
			// through all of it. A gap you have to line up for is a gap that is TIGHT, and the
			// vertical never is: flyTo already puts the feet a tenth of a block off the floor of the
			// cell, which is as lined up as it is possible to be.
			false,
			solidAt(mc, c.south()) && solidAt(mc, c.north()),
		};
	}

	private static boolean solidAt(Minecraft mc, BlockPos b) {
		return mc.level.isLoaded(b) && mc.level.getBlockState(b).blocksMotion();
	}

	/**
	 * Is there a surface within `gap` of the body, the way it is going?
	 *
	 * <p>Both the feet and the head, because an approach that clears one and not the other is the
	 * head-bumping by another name.
	 */
	private static boolean surfaceAhead(Minecraft mc, LocalPlayer p, Vec3 towards, double gap) {
		if (towards.lengthSqr() < 1.0e-6) return false;
		Vec3 step = towards.normalize().scale(gap);
		Vec3 at = p.position().add(step);
		for (double dy : new double[] {0.2, 1.7}) {
			BlockPos b = BlockPos.containing(at.x, at.y + dy, at.z);
			if (mc.level.isLoaded(b) && mc.level.getBlockState(b).blocksMotion()) return true;
		}
		return false;
	}

	/** The cell the current aim points at, for the tightness test. */
	private static BlockPos aimCell() {
		return path.isEmpty() ? Hud.target() : path.get(0);
	}

	/** Is this cell in a passage narrow enough that it has to be threaded? */
	private static boolean isTight(Minecraft mc, BlockPos at) {
		if (at == null) return false;
		boolean[] lock = boxedAxes(mc, Vec3.atCenterOf(at));
		return lock[0] || lock[1] || lock[2];
	}

	/** Is a body able to be at this offset from the player? */
	private static boolean openAt(Minecraft mc, LocalPlayer p, double dx, double dy, double dz) {
		BlockPos b = BlockPos.containing(p.getX() + dx, p.getY() + dy, p.getZ() + dz);
		if (!mc.level.isLoaded(b)) return false;           // unseen is not a way out
		return !mc.level.getBlockState(b).blocksMotion()
			&& !mc.level.getBlockState(b.above()).blocksMotion();
	}

	/** Movement below this in a tick is not travel, it is drift. */
	static final double MOVED_ENOUGH = 0.05;
	/** Ticks between breadcrumbs. */
	static final int CRUMB_EVERY = 40;
	/** A crumb further than this is not the way in, it is somewhere we were a while ago. */
	static final double CRUMB_MAX = 16.0;
	/** How far up the climb-out goes before trying again. */
	static final int CLIMB_HEIGHT = 25;

	private static Vec3 lastSeenAt = Vec3.ZERO;

	/**
	 * Work the ladder.
	 *
	 * @return true when the recovery is driving and nothing else should
	 */
	private static boolean recover(Minecraft mc, LocalPlayer p, BlockPos target) {
		switch (stage) {
			case BACK_OFF -> {
				// The way out is the way in. Fly the crumb, not the destination.
				if (breadcrumb == null) return false;
				Vec3 back = Vec3.atCenterOf(breadcrumb);
				if (p.position().distanceTo(back) > CRUMB_MAX) {
					breadcrumb = null;                  // too old to be the way in: let the ladder climb
					return false;
				}
				if (p.position().distanceTo(back) < 2.0) {
					breadcrumb = null;                  // used it: the normal flight gets another go
					stage = Recovery.Stage.NONE;
					trouble = 0;
					return false;
				}
				p.setDeltaMovement(avoid(p, Bounds.clamp(p.position(), keepAirborne(mc, p,
					back.subtract(p.position()).normalize().scale(BLIND_SPEED * 2), GROUND_CLEAR))));
				return true;
			}
			case CLIMB_OUT -> {
				// Straight up until there is nothing overhead. Above this island there is nothing to
				// be stuck on, and from open sky every route is findable again.
				if (climbTo == null) climbTo = p.blockPosition().above(CLIMB_HEIGHT);if (p.getY() >= climbTo.getY() || !p.getAbilities().flying) {
					climbTo = null;
					stage = Recovery.Stage.NONE;
					climbedOut = true;                  // once; the next time it is a give-up
					trouble = Recovery.BACK_OFF_AT;     // give the normal flight another go
					return false;
				}
				// Through the ceiling clamp and the collision test: a climb into the underside of
				// the plate is contact, and contact is what this rung exists to get away from.
				// Blocked overhead it does not move, `trouble` keeps counting, and GO_HOME follows.
				p.setDeltaMovement(avoid(p, Bounds.clamp(p.position(),
					keepAirborne(mc, p, new Vec3(0, Math.min(SPEED, 0.4), 0), GROUND_CLEAR))));
				return true;
			}
			case GO_HOME -> {
				if (Bounds.active()) {
					// A TELEPORT CANNOT BE FENCED, and this rung is convenience rather than safety
					// (the fall rescue keeps its /is). Give the spot up instead and stay inside.
					p.sendSystemMessage(Component.literal("[cscan] stuck, and /is would leave the"
						+ " autofly bounds - giving this spot up instead."));
					trouble = 0;
					stage = Recovery.Stage.NONE;
					forget();
					Hud.abandonSpot();
					return true;
				}
				if (p.connection != null && rescueCool == 0) {
					rescueCool = RESCUE_COOLDOWN;
					p.connection.sendCommand("is");
					p.sendSystemMessage(Component.literal("[cscan] sent /is — the loop picks up again"
						+ " from wherever that puts us."));
				}
				trouble = 0;
				stage = Recovery.Stage.NONE;
				forget();
				Hud.abandonSpot();                      // whatever it was, it is not worth this
				return true;
			}
			default -> {
				return false;
			}
		}
	}

	/** Shortest-way-round easing between two angles. */
	static float approach(float from, float to) {
		float d = to - from;
		while (d <= -180) d += 360;
		while (d > 180) d -= 360;
		return from + d * TURN_RATE;
	}

	/** At the target: kill the drift but stay armed for the next leg. */
	/** The target the flight last called itself arrived at, or null while it is still going. */
	private static BlockPos arrivedAt = null;
	/** A landing target that could not be walked to from here — so take off for it. */
	private static boolean groundNoRoute = false;
	/** Further than this on foot and it is quicker to take off, even to another landing. */
	static final double WALK_AT_MOST = 24.0;

	/**
	 * Does getting to the current target need the air? A hovering station or a chest approach
	 * does. A LANDING does not, if it can be walked to from here — a body already standing on
	 * the floor beside the next patch of paving walks over rather than taking off, landing, and
	 * losing flight twice for nothing. It takes off when the walk is long, or when there is no
	 * walking route at all.
	 */
	static boolean needsFlight(boolean landTarget, boolean walkRouteFailed, double distance) {
		if (!landTarget) return true;
		return walkRouteFailed || distance > WALK_AT_MOST;
	}

	/** Has the flight arrived at THIS target? False for any other, and false while still closing. */
	static boolean arrivedAt(BlockPos t) {
		return t != null && t.equals(arrivedAt);
	}

	private static void arrive(Minecraft mc) {
		arrivedAt = approaching;
		release(mc);                                   // holding jump at the destination is a climb
		bumps = 0;                                     // whatever we brushed on the way is history
		wedged = 0;
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
