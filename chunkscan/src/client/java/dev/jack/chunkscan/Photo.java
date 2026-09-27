package dev.jack.chunkscan;

import net.minecraft.client.Minecraft;
import net.minecraft.client.Screenshot;
import net.minecraft.core.BlockPos;
import net.minecraft.world.phys.Vec3;

/**
 * Flies the eight bearings {@code tools/look.py} renders, and takes a real screenshot at each.
 *
 * <p>This closes the largest thing CLAUDE.md lists as known-wrong. The file says it plainly:
 * <i>"Validation is circular FOR COLOUR... `views.py` and `look.py` both draw with the same DB the
 * palette picker optimises against"</i>, and — after a hundred thousand blocks — <i>"nothing built
 * in this system has been placed in Minecraft and looked at"</i>. Every palette decision this
 * project has made rests on a colour table judging its own work.
 *
 * <p>A screenshot is the one image in the whole pipeline that owes nothing to our colour database.
 * It is the game's own textures, the game's own light, the biome tint the extractor had to
 * ASSUME (plains, because nothing offline can say what biome this island sits in). Put beside
 * {@code look.py}'s render of the same bearing, it is the first non-circular evidence available.
 *
 * <p>Three things make it usable rather than a pile of screenshots:
 *
 * <ul>
 *   <li><b>The bearing is relative to the design's RECORDED FACING</b>, exactly as {@code look.py}
 *       and {@code panel.py} choose theirs — 0 head-on, 90 profile, 180 tail-on. Picked by hand
 *       this was got wrong twice in one session, which is why nothing here picks by hand.</li>
 *   <li><b>The camera distance comes from the design's own size</b>, so a frog and the island are
 *       both framed rather than one being a speck.</li>
 *   <li><b>It flies, it does not teleport.</b> {@link Autopilot} already knows how to get
 *       somewhere without hitting anything, and a position write is the thing this mod has always
 *       refused to do.</li>
 * </ul>
 */
final class Photo {
	/** The eight bearings, as `look.py --sheet orbit` uses them. */
	static final int[] BEARINGS = {0, 45, 90, 135, 180, 225, 270, 315};
	/** Ticks to hold still at a station before the shutter, so chunks and entities settle. */
	static final int SETTLE = 30;

	private static boolean on;
	private static int index;
	private static long settleAt;
	private static String design = "";
	private static BlockPos centre;
	private static double radius;
	private static int facing;
	private static int taken;

	private Photo() {}

	static boolean running() {
		return on;
	}

	static void stop() {
		on = false;
	}

	static String status() {
		if (!on) return "not touring";
		return "photo " + design + ": bearing " + BEARINGS[Math.min(index, BEARINGS.length - 1)]
			+ " (" + taken + "/" + BEARINGS.length + " taken)";
	}

	/**
	 * @param facingDeg the design's recorded facing, so bearing 0 really is head-on
	 */
	static String start(String name, BlockPos c, double r, int facingDeg) {
		design = name;
		centre = c;
		radius = Math.max(6.0, r);
		facing = facingDeg;
		index = 0;
		taken = 0;
		settleAt = 0;
		on = true;
		return "photo tour of " + name + ": " + BEARINGS.length + " bearings, flying between them. "
			+ "Screenshots land in .minecraft/screenshots. /cscan photo off to stop";
	}

	/** Where the camera should stand for bearing `i`, in world coordinates. */
	static Vec3 stationFor(int i) {
		double deg = Math.toRadians(facing + BEARINGS[i % BEARINGS.length]);
		// Back off far enough that the whole thing is in frame at the game's ~70 degree FOV, and
		// lift by a third of the radius: a level shot of anything large is mostly its own base.
		double back = radius * 2.2;
		return new Vec3(centre.getX() + Math.sin(deg) * back,
			centre.getY() + radius * 0.35,
			centre.getZ() + Math.cos(deg) * back);
	}

	/** One step. Returns a line worth saying, or null. */
	static String tick(Minecraft mc) {
		if (!on || mc.player == null || mc.level == null) return null;
		if (index >= BEARINGS.length) {
			on = false;
			Hud.stopGuiding();
			return "photo tour done: " + taken + " shot(s) in .minecraft/screenshots — "
				+ "put them beside tools/look.py's renders of the same bearings";
		}
		Vec3 want = stationFor(index);
		BlockPos station = BlockPos.containing(want);
		double d = mc.player.position().distanceTo(want);
		if (d > 3.0) {
			settleAt = 0;
			Hud.guide(station, "photo bearing " + BEARINGS[index]);   // fly, never teleport
			return null;
		}
		// Look AT the subject, so the bearing means what it says.
		aimAt(mc, Vec3.atCenterOf(centre));
		if (settleAt == 0) {
			settleAt = mc.level.getGameTime() + SETTLE;
			return null;
		}
		if (mc.level.getGameTime() < settleAt) return null;

		// ANOTHER 26.x API CHANGE, found by javap rather than by memory: there is no
		// `Minecraft.getMainRenderTarget()` any more, so the naming overload of `Screenshot.grab`
		// cannot be reached — its RenderTarget argument has nowhere to come from. `grab(mc, true)`
		// is the F2 path: the game names the file itself and PRINTS that name in chat, which is
		// why the bearing is announced immediately before. The two lines together are the caption.
		int bearing = BEARINGS[index];
		mc.player.sendSystemMessage(net.minecraft.network.chat.Component.literal(
			"[cscan] " + design + " bearing " + bearing + " ->"));
		Screenshot.grab(mc, true);
		taken++;
		index++;
		settleAt = 0;
		return null;
	}

	/** Point the player at a world position. Yaw first, then pitch; both in degrees. */
	static void aimAt(Minecraft mc, Vec3 at) {
		if (mc.player == null) return;
		Vec3 eye = mc.player.getEyePosition();
		double dx = at.x - eye.x, dy = at.y - eye.y, dz = at.z - eye.z;
		double flat = Math.sqrt(dx * dx + dz * dz);
		mc.player.setYRot((float) (Math.toDegrees(Math.atan2(-dx, dz))));
		mc.player.setXRot((float) (-Math.toDegrees(Math.atan2(dy, flat))));
	}
}
