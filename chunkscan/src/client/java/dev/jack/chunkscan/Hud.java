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
	// ---- the unattended watch. A loop you leave alone must be able to say what it did, and must
	// not sit silently against a wall it cannot build.
	private static int lastTodo = -1;
	private static long lastProgressMs;
	private static long startedMs;
	private static int placedTotal;
	private static int spotsDone;
	private static int fetches;
	private static int stalls;
	/** No cell placed for this long while following and not fetching: something is wrong. */
	static final long STALL_MS = 90_000;
	/** Guiding to a container rather than to work. */
	private static boolean fetching = false;
	/** A dead end is worth saying once. Every two seconds it is a reason to turn the loop off. */
	private static boolean said = false;
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
				// Say whether it is FOLLOWING A ROUTE or flying at a bearing: those behave very
				// differently around a wall and you want to know which one you are watching.
				String why = Autopilot.stalledBecause(mc);
				String nav = Autopilot.on()
					? (why != null ? "  [autofly idle: " + why + "]" : "  [" + Autopilot.mode(mc) + "]")
					: "";
				extractor.text(mc.font, arrow + "  " + d + "m" + climb(me, target) + nav + "  " + tail,
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
					"[cscan] " + sp.name() + " is complete in every loaded chunk. " + sessionReport()));
			}
			following = false;
			stopGuiding();
			Highlight.clear("goto");
			return;
		}
		// ---- PROGRESS. `todo` shrinking is the only honest evidence a block was placed: the
		// printer does the placing and never tells us, so the world is the report.
		long now = System.currentTimeMillis();
		if (lastTodo >= 0 && sp.todo().size() < lastTodo) {
			placedTotal += lastTodo - sp.todo().size();
			lastProgressMs = now;
		}
		lastTodo = sp.todo().size();
		if (!fetching && now - lastProgressMs > STALL_MS) {
			stalls++;
			lastProgressMs = now;
			mc.player.sendSystemMessage(Component.literal("[cscan] STALLED — nothing placed in "
				+ (STALL_MS / 1000) + "s at " + (target == null ? "?" : Wand.fmt(target))
				+ ". Printer off, out of reach, or the spot cannot be built. " + sessionReport()));
			// Give up on this spot rather than sitting against it: the next recount picks another.
			stopGuiding();
			Highlight.clear("goto");
			return;
		}

		java.util.Set<Long> blocked = new java.util.HashSet<>();
		for (Work.Cell c : Work.floating(mc.level, sp.todo())) blocked.add(c.pos().asLong());
		// ...and the opposite failure: cells sealed inside solid world, which have plenty to place
		// against and no way to reach them. `follow` must not walk you to either.
		java.util.Set<Long> sealed = new java.util.HashSet<>();
		for (Work.Cell c : Work.unreachable(mc.level, sp.todo())) sealed.add(c.pos().asLong());
		Map<String, Integer> carrying = Work.carrying(mc.player);
		java.util.List<Plan.Cluster> cl = Plan.clusters(sp.todo(), carrying, blocked, sealed, me);
		spotsLeft = cl.size();

		Map<String, Storage.Container> index;
		try {
			index = Storage.load(ScanRunner.schematicsDir(mc));
		} catch (Exception e) {
			index = java.util.Map.of();
		}

		// ---- FILL THE PACK, THEN BUILD UNTIL IT IS DRY.
		//
		// This used to be decided per SPOT — if the best cluster was short of anything, go and fetch
		// it — so the loop went shopping while carrying a full inventory and plenty it could place,
		// took one spot's worth, and flew back. On a design of any size that is a session of
		// commuting rather than of building.
		//
		// Now there are two questions and the order between them is the whole policy: anything I can
		// place with what I am holding? Then build. Only when the answer is no does a trip start, and
		// once started it runs until the pack is FULL or the design is covered — not until one
		// spot's shortfall is met.
		boolean canWork = Plan.anyDoable(cl);
		boolean wasFetching = fetching;
		if (fetching || !canWork) {
			// Skip chests in their cooling-off period, or the loop is guided at one it will not open.
			java.util.List<Plan.Restock> targets = Plan.fetchTargets(sp.todo(), carrying, index, me,
				Withdraw.coolingOff(System.currentTimeMillis()));
			Plan.Restock want = Plan.nextFetch(targets, it -> Work.room(mc.player, it));
			fetching = want != null;
			if (want != null) {
				fetchTo(mc, me, want, Work.room(mc.player, want.item()), carrying);
				return;
			}
			if (!canWork) {
				// Nothing placeable and nothing to fetch are DIFFERENT dead ends and want different
				// answers: one sends you to the store hall, the other says your pack is full of
				// something this design has no room left for.
				if (target != null || !said) {
					said = true;
					mc.player.sendSystemMessage(Component.literal(targets.isEmpty()
						? "[cscan] nothing left you are carrying the blocks for, and nothing indexed"
							+ " to fetch — /cscan bom " + sp.name()
						: "[cscan] pack is full of what you cannot place here — store something, or"
							+ " /cscan bom " + sp.name()));
				}
				stopGuiding();
				Highlight.clear("goto");
				return;
			}
		}
		said = false;

		// HYSTERESIS: keep the current spot while it still has anything doable.
		if (target != null) {
			for (Plan.Cluster c : cl) {
				if (c.centre().distSqr(target) <= (double) Plan.WORK_RADIUS * Plan.WORK_RADIUS
					&& c.doable() > 0) {
					targetNote = c.doable() + " here";
					return;
				}
			}
		}
		Plan.Cluster next = cl.get(0);
		// A spot counts as finished when we leave one BUILD target for another — a chest we have just
		// finished at is not a spot. The earlier version never incremented at all, so the session
		// report said 0 spots however long it ran.
		if (target != null && !wasFetching && !target.equals(next.centre())) spotsDone++;
		if (target != null && target.equals(next.centre())) return;   // already pointing there
		Highlight.show("goto", Work.positions(next.cells(), 400), 0x40FF60, 900);
		guide(next.centre(), next.doable() + " here");
		mc.player.sendSystemMessage(Component.literal("[cscan] next spot: " + next.doable()
			+ " cells at " + Wand.fmt(next.centre()) + ", " + (cl.size() - 1) + " more after it"));
	}

	/**
	 * Go and get one material, and take as much of it as the pack will hold.
	 *
	 * <p>The amount is the point. Taking one spot's shortfall is what made a fetch a round trip per
	 * wall; taking {@link Plan#takeHowMany} of it — the design's whole remaining need, capped by the
	 * room in the pack and by what the chest is believed to hold — makes it one trip per pack.
	 */
	private static void fetchTo(Minecraft mc, BlockPos me, Plan.Restock want, int room,
	                            Map<String, Integer> carrying) {
		BlockPos at = want.where().pos();
		int take = Plan.takeHowMany(want, room);
		// INSIDE reach, not at the edge of it. This was 25 (5.0 blocks) against Withdraw.REACH of
		// 4.5, so between 4.5 and 5.0 the withdrawal began, could never fire the use-item, timed
		// out, and blacklisted a perfectly good chest for a minute.
		boolean here = at.distSqr(me) <= (Withdraw.REACH - 0.5) * (Withdraw.REACH - 0.5);
		if (target == null || !target.equals(at)) {
			fetches++;
			Highlight.show("goto", java.util.List.of(at), 0xFFC000, 900);
			mc.player.sendSystemMessage(Component.literal("[cscan] fetch: " + take + "x "
				+ want.item() + " from " + want.where().describe() + " (" + want.available()
				+ " there, " + want.missing() + " still wanted, room for " + room + ")"));
		}
		// Arrived and still short: you are standing at the chest, so say what to take rather than
		// repeating where it is.
		guide(at, (here ? "take " : "") + take + "x " + want.item());
		// ARRIVED: take it. This is the step that closes the loop — without it `follow` flies you to
		// the chest and waits for a human to shift-click. It fires once per trip, because
		// Withdraw.busy() gates it and the next recount sees the fuller pack.
		if (here && !Withdraw.busy() && !Withdraw.recentlyFailed(at, System.currentTimeMillis())) {
			Withdraw.begin(at, want.item(), take + carrying.getOrDefault(want.item(), 0));
		}
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

	/**
	 * Abandon the fetch in progress and clear the instruction.
	 *
	 * <p>The chest stays in the cooling-off set so the loop moves to a DIFFERENT one rather than
	 * turning straight back to the one you just cancelled.
	 */
	static void stopFetching(Minecraft mc) {
		Withdraw.cancel();
		if (fetching && target != null) Withdraw.noteFailureForTest(target);
		fetching = false;
		stopGuiding();
		Highlight.clear("goto");
	}

	static boolean fetching() {
		return fetching;
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
		Withdraw.clearFailures();
		lastTodo = -1;
		lastProgressMs = System.currentTimeMillis();
		startedMs = lastProgressMs;
		placedTotal = 0;
		spotsDone = 0;
		fetches = 0;
		stalls = 0;
		said = false;
	}

	/** What the loop has done since `follow` started — the report for a session you were not watching. */
	static String sessionReport() {
		long mins = Math.max(1, (System.currentTimeMillis() - startedMs) / 60_000);
		return placedTotal + " placed in " + mins + " min (" + (placedTotal / mins) + "/min), "
			+ spotsDone + " spot(s) finished, " + fetches + " restock(s), " + stalls + " stall(s)";
	}

	static boolean following() {
		return following;
	}

	static String watching() {
		return design;
	}

	private static void tick(Minecraft mc) {
		// Withdraw drives itself every tick, independent of whether a design is being followed:
		// `/cscan take` is a chest command first and a build-loop step second.
		Withdraw.tick(mc);
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
