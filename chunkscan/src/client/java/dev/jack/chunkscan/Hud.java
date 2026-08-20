package dev.jack.chunkscan;

import net.fabricmc.fabric.api.client.rendering.v1.hud.HudElementRegistry;
import net.minecraft.client.Minecraft;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.Identifier;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * A two-line readout of the design you are building, so "how much is left" does not cost a command
 * every time you want it.
 *
 * <p><b>The split is recomputed on a timer, not per frame.</b> {@link Work#split} walks every cell
 * of the design and diffs it against the world - `Island Belly Full` is 8,210 of them - and doing
 * that sixty times a second to draw two lines of text would cost more than the information is
 * worth. Every {@link #EVERY_TICKS} ticks is faster than you can place a block.
 *
 * <p>26.2 draws its HUD by EXTRACTING RENDER STATE rather than by immediate-mode calls:
 * {@code HudRenderCallback} is gone and {@link HudElementRegistry} takes a
 * {@link net.fabricmc.fabric.api.client.rendering.v1.hud.HudElement} whose only job is to hand
 * geometry to the extractor. Worth knowing before porting any older HUD guide.
 */
final class Hud {
	private static final Identifier ID = Identifier.parse("chunkscan:progress");
	/** 2 seconds. A build session moves in blocks, not in frames. */
	static final int EVERY_TICKS = 40;

	private static String design = null;
	private static List<String> lines = new ArrayList<>();
	private static int tick = 0;
	private static BlockPos target = null;
	private static String targetNote = "";
	private static boolean following = false;
	/** Guiding to a container rather than to work. */
	private static boolean fetching = false;
	private static int spotsLeft = 0;

	private Hud() {}

	static void register() {
		HudElementRegistry.addLast(ID, (extractor, delta) -> {
			if (design == null || lines.isEmpty()) return;
			Minecraft mc = Minecraft.getInstance();
			// No F1 or open-screen guard here, and none is needed: an element registered through
			// HudElementRegistry is part of the HUD layer stack, so vanilla hides it with the rest
			// of the GUI. `Options.hideGui` and `Minecraft.screen` do not exist in 26.2 anyway.
			int y = 4;
			for (String s : lines) {
				extractor.text(mc.font, s, 4, y, 0xFFE0E0E0);
				y += 10;
			}
			// The guidance line is computed HERE rather than on the timer: it is a subtraction and
			// a compass bearing, and a direction that updates every two seconds is a direction that
			// is wrong every time you turn around.
			if (target != null && mc.player != null) {
				BlockPos me = mc.player.blockPosition();
				int d = (int) Math.sqrt(me.distSqr(target));
				String arrow = bearing(mc.player.getYRot(), me, target);
				int colour = d <= Plan.WORK_RADIUS ? 0xFF60FF60 : 0xFFFFC000;
				String tail = targetNote + (following && spotsLeft > 1
					? "   (" + (spotsLeft - 1) + " more spot" + (spotsLeft == 2 ? "" : "s") + ")" : "");
				extractor.text(mc.font, arrow + "  " + d + "m" + climb(me, target) + "  " + tail,
					4, y, colour);
			}
		});
		net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents.END_CLIENT_TICK.register(Hud::tick);
	}

	/**
	 * Point at a place until told otherwise.
	 *
	 * <p>The arrow is relative to where you are FACING, not to north. "NE" is a thing you have to
	 * translate while walking; an arrow that swings as you turn is one you follow.
	 */
	static void guide(BlockPos where, String note) {
		target = where;
		targetNote = note == null ? "" : note;
	}

	static void stopGuiding() {
		target = null;
		targetNote = "";
	}

	static BlockPos target() {
		return target;
	}

	/** An arrow in the player's own frame: the angle between where they look and where to go. */
	/**
	 * Keep the arrow on a spot until it is done, then move it to the next.
	 *
	 * <p>Announced in chat only when the target actually CHANGES. Saying "spot 2" every two seconds
	 * for as long as you stand there is not guidance, it is noise.
	 */
	private static void advance(Minecraft mc, Work.Split sp) {
		BlockPos me = mc.player.blockPosition();
		if (sp.todo().isEmpty()) {
			if (target != null) {
				mc.player.sendSystemMessage(Component.literal(
					"[cscan] " + sp.name() + " is complete in every loaded chunk"));
			}
			following = false;
			stopGuiding();
			Highlight.clear("goto");
			return;
		}
		java.util.Set<Long> blocked = new java.util.HashSet<>();
		for (Work.Cell c : Work.floating(mc.level, sp.todo())) blocked.add(c.pos().asLong());
		java.util.List<Plan.Cluster> cl =
			Plan.clusters(sp.todo(), Work.carrying(mc.player), blocked, me);
		spotsLeft = cl.size();
		if (cl.isEmpty()) {
			// Not "no work left" - no work you can do with what you are holding. Different problem,
			// different answer, and saying the wrong one sends you to look at a finished wall.
			if (target != null) {
				mc.player.sendSystemMessage(Component.literal("[cscan] nothing left you are carrying"
					+ " the blocks for — /cscan bom " + sp.name()));
			}
			stopGuiding();
			Highlight.clear("goto");
			return;
		}
		// HYSTERESIS: keep the current spot while it still has anything doable.
		if (!fetching && target != null) {
			for (Plan.Cluster c : cl) {
				if (c.centre().distSqr(target) <= (double) Plan.WORK_RADIUS * Plan.WORK_RADIUS
					&& c.doable() > 0) {
					targetNote = c.doable() + " here";
					return;
				}
			}
		}
		Plan.Cluster next = cl.get(0);

		// ---- FETCH FIRST. A spot you cannot finish is a spot you will walk to twice, so if the
		// best one is short of stock and the index knows where the material is, that trip comes
		// first. Only when nothing is fetchable do we go and do the part we can.
		Map<String, Integer> carrying = Work.carrying(mc.player);
		Map<String, Storage.Container> index;
		try {
			index = Storage.load(ScanRunner.schematicsDir(mc));
		} catch (Exception e) {
			index = java.util.Map.of();
		}
		Plan.Restock want = Plan.firstFetchable(next, carrying, index, me);
		if (want != null) {
			BlockPos at = want.where().pos();
			// Arrived and still short: you are standing at the chest, so say what to take rather
			// than repeating where it is.
			boolean here = at.distSqr(me) <= 25;
			if (!fetching || target == null || !target.equals(at)) {
				fetching = true;
				Highlight.show("goto", java.util.List.of(at), 0xFFC000, 900);
				mc.player.sendSystemMessage(Component.literal("[cscan] fetch first: "
					+ want.missing() + "x " + want.item() + " from " + want.where().describe()
					+ " (" + want.available() + " there)"));
			}
			guide(at, here ? "take " + want.missing() + "x " + want.item()
				: want.missing() + "x " + want.item());
			return;
		}

		fetching = false;
		if (target != null && target.equals(next.centre())) return;   // already pointing there
		Highlight.show("goto", Work.positions(next.cells(), 400), 0x40FF60, 900);
		guide(next.centre(), next.doable() + " here");
		mc.player.sendSystemMessage(Component.literal("[cscan] next spot: " + next.doable()
			+ " cells at " + Wand.fmt(next.centre()) + ", " + (cl.size() - 1) + " more after it"));
	}

	/**
	 * The vertical leg, stated separately because a compass bearing cannot carry it.
	 *
	 * <p>This island is 240 blocks tall — the lowland floor is Y24, the deck Y194, the sky bird
	 * Y268 — so the up-down component is routinely the LARGER one, and a chest 150 blocks below you
	 * reads as "18m NE" on any horizontal-only arrow. Jack flies, which makes the vertical leg free
	 * to travel and therefore free to ignore, right up until you are hunting a floor.
	 */
	static String climb(BlockPos from, BlockPos to) {
		int dy = to.getY() - from.getY();
		if (Math.abs(dy) < 3) return "";
		return dy > 0 ? "  up " + dy : "  down " + (-dy);
	}

	static String bearing(float yRotDegrees, BlockPos from, BlockPos to) {
		double want = Math.toDegrees(Math.atan2(-(to.getX() - from.getX()), to.getZ() - from.getZ()));
		double rel = want - yRotDegrees;
		while (rel <= -180) rel += 360;
		while (rel > 180) rel -= 360;
		int oct = (int) Math.round(rel / 45.0);
		return switch (((oct % 8) + 8) % 8) {
			case 0 -> "^ ahead";
			case 1 -> "> right-ahead";
			case 2 -> "> right";
			case 3 -> "v right-back";
			case 4 -> "v behind";
			case 5 -> "v left-back";
			case 6 -> "< left";
			default -> "< left-ahead";
		};
	}

	static void watch(String name) {
		design = name;
		lines = new ArrayList<>();
		tick = 0;
	}

	static void off() {
		design = null;
		lines = new ArrayList<>();
		following = false;
		fetching = false;
		stopGuiding();
	}

	/**
	 * Follow the plan: guide to the best spot, and when it is finished move to the next one without
	 * being asked.
	 *
	 * <p><b>With hysteresis.</b> The plan is recomputed on every recount, and the best spot changes
	 * as you place blocks and burn stock — repointing at whatever is best THIS second would swing
	 * the arrow around while you stand still. So the current target is kept while it still has
	 * anything doable, and only when it is exhausted does the next one get picked.
	 */
	static void follow(String name) {
		watch(name);
		following = true;
		stopGuiding();
	}

	static boolean following() {
		return following;
	}

	static String watching() {
		return design;
	}

	private static void tick(Minecraft mc) {
		if (design == null || mc.level == null || mc.player == null) return;
		if (tick++ % EVERY_TICKS != 0) return;
		try {
			Work.Split sp = Work.split(mc.level, ScanRunner.schematicsDir(mc), design,
				mc.player.blockPosition(), 0);
			if (following) advance(mc, sp);
			int pct = sp.total() == 0 ? 0 : Math.round(100f * sp.built() / sp.total());
			List<String> out = new ArrayList<>();
			out.add(sp.name() + "  " + sp.built() + "/" + sp.total() + "  " + pct + "%");
			String second = sp.todo().size() + " to place";
			if (!sp.wrong().isEmpty()) second += "   " + sp.wrong().size() + " deviating";
			// The nearest thing left, because "247 to place" does not tell you where to stand.
			if (!sp.todo().isEmpty()) {
				Work.Cell f = sp.todo().get(0);
				second += "   next " + (int) Math.sqrt(f.pos().distSqr(mc.player.blockPosition()))
					+ "m " + Storage.direction(mc.player.blockPosition(), f.pos());
			}
			out.add(second);
			lines = out;
		} catch (Exception e) {
			// A missing work.json is a normal thing to be told once, not sixty times a second.
			lines = List.of(design + ": " + e.getMessage());
			design = null;
		}
	}
}
