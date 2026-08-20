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
 * be conservative and to be trivially interruptible — it is capped well under sprint-fly, it steers
 * rather than teleports, and ANY key you press hands control straight back.
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
	/** Blocks per tick. Vanilla creative flight is about 0.4 and sprint-flight roughly double. */
	static final double SPEED = 0.35;
	/** Close enough to be standing at it. */
	static final double ARRIVED = 3.0;
	/** Ease the turn instead of snapping: a camera that jumps to a bearing is not a player. */
	static final float TURN_RATE = 0.18f;

	private static boolean on = false;
	private static boolean warnedNoFly = false;
	private static boolean warnedNoRoute = false;

	/** The current route, as waypoints. Empty means "fly straight and hope", which is the fallback. */
	private static java.util.List<BlockPos> path = new java.util.ArrayList<>();
	private static BlockPos pathTo = null;
	private static int repathIn = 0;
	/** Recompute about twice a second: chunks load, doors open, and you drift. */
	static final int REPATH_TICKS = 10;
	/** Waypoint reached. Loose, because overshooting a corridor corner is how you clip a wall. */
	static final double WAYPOINT = 1.8;

	private Autopilot() {}

	static void register() {
		ClientTickEvents.END_CLIENT_TICK.register(Autopilot::tick);
	}

	static boolean on() {
		return on;
	}

	static void set(boolean v) {
		on = v;
		warnedNoFly = false;
		warnedNoRoute = false;
		path = new java.util.ArrayList<>();
		pathTo = null;
		repathIn = 0;
	}

	/** How many waypoints are left, for the HUD. */
	static int waypoints() {
		return path.size();
	}

	/**
	 * Any manual input cancels.
	 *
	 * <p>The one property that makes this safe to leave switched on: you never have to fight it, or
	 * find the command to turn it off while it flies you into a wall. Touch a key and it is yours.
	 */
	private static boolean playerIsDriving(Minecraft mc) {
		var o = mc.options;
		return o.keyUp.isDown() || o.keyDown.isDown() || o.keyLeft.isDown() || o.keyRight.isDown()
			|| o.keyJump.isDown() || o.keyShift.isDown();
	}

	private static void tick(Minecraft mc) {
		if (!on) return;
		LocalPlayer p = mc.player;
		if (p == null || mc.level == null) return;
		if (Screens.anyOpen()) return;               // a menu is open; do not fly under it

		BlockPos target = Hud.target();
		if (target == null) return;

		if (playerIsDriving(mc)) {
			stop(mc, "you took over — autofly off");
			return;
		}

		Vec3 me = p.position();
		Vec3 to = Vec3.atCenterOf(target);
		double dist = me.distanceTo(to);
		if (dist <= ARRIVED) {
			stop(mc, "arrived at " + Wand.fmt(target));
			return;
		}

		if (!p.getAbilities().flying) {
			if (!warnedNoFly) {
				warnedNoFly = true;
				p.sendSystemMessage(Component.literal(
					"[cscan] autofly needs you flying — turn on /fly, then double-tap jump"));
			}
			return;                                   // steering a walk is a different problem
		}

		// ---- ROUTE. Recomputed on a timer and whenever the destination moves, because the world
		// loads in around you and the plan's target changes as you build.
		if (pathTo == null || !pathTo.equals(target) || --repathIn <= 0) {
			Nav.Passable free = Nav.of(mc.level);
			BlockPos here = p.blockPosition();
			java.util.List<BlockPos> raw = Nav.route(free, here, target);
			path = raw.isEmpty() ? new java.util.ArrayList<>()
				: new java.util.ArrayList<>(Nav.simplify(free, here, raw));
			pathTo = target;
			repathIn = REPATH_TICKS;
		}

		// Steer at the next waypoint rather than at the destination: that is the whole difference
		// between going through the door and pressing on the wall beside it.
		Vec3 aim = to;
		while (!path.isEmpty() && me.distanceTo(Vec3.atCenterOf(path.get(0))) <= WAYPOINT) {
			path.remove(0);
		}
		if (!path.isEmpty()) aim = Vec3.atCenterOf(path.get(0));

		// ---- aim
		Vec3 dir = aim.subtract(me).normalize();
		float wantYaw = (float) Math.toDegrees(Math.atan2(-dir.x, dir.z));
		float wantPitch = (float) Math.toDegrees(-Math.asin(dir.y));
		p.setYRot(approach(p.getYRot(), wantYaw));
		p.setXRot(approach(p.getXRot(), wantPitch));

		// ---- go. Slow into the target so the last few blocks are not an overshoot and a wobble.
		double speed = Math.min(SPEED, dist / 8.0 + 0.05);
		Vec3 step = dir.scale(speed);

		// No route: fly direct and lift over what you meet. Say so once, because "it is routing"
		// and "it is guessing" behave very differently around a building and you should know which
		// one is carrying you.
		if (path.isEmpty()) {
			if (!warnedNoRoute) {
				warnedNoRoute = true;
				p.sendSystemMessage(Component.literal("[cscan] no route found — flying direct."
					+ " If it is sealed or far, get closer and it will re-route."));
			}
			if (blockedAhead(mc, p, dir)) step = new Vec3(step.x, Math.max(step.y, SPEED * 0.8), step.z);
		} else {
			warnedNoRoute = false;
		}

		p.setDeltaMovement(step);
	}

	/** True if the two cells directly ahead at body height are not passable. */
	private static boolean blockedAhead(Minecraft mc, LocalPlayer p, Vec3 dir) {
		Vec3 ahead = p.position().add(dir.scale(1.6));
		for (double dy : new double[]{0.2, 1.2}) {
			BlockPos b = BlockPos.containing(ahead.x, ahead.y + dy, ahead.z);
			if (!mc.level.getBlockState(b).isAir()) return true;
		}
		return false;
	}

	/** Shortest-way-round easing between two angles. */
	static float approach(float from, float to) {
		float d = to - from;
		while (d <= -180) d += 360;
		while (d > 180) d -= 360;
		return from + d * TURN_RATE;
	}

	private static void stop(Minecraft mc, String why) {
		on = false;
		if (mc.player != null) {
			mc.player.setDeltaMovement(Vec3.ZERO);
			mc.player.sendSystemMessage(Component.literal("[cscan] " + why));
		}
	}
}
