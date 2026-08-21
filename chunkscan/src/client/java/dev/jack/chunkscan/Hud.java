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
	// ---- WHERE TO STAND INSIDE A SPOT. A spot is sized to an inventory load and can be 96 blocks
	// across; the printer reaches four and a half. Standing at the centroid places what happens to
	// be near the middle and then nothing at all, for ninety seconds, until the stall watch fires.
	/** The last todo count the scaffold/seal probe was run for. See advance(). */
	private static int scaffoldFor = -1;
	private static java.util.Set<Long> blocked = new java.util.HashSet<>();
	private static java.util.Set<Long> sealed = new java.util.HashSet<>();

	/** The region being worked. Kept by proximity — a centroid drifts as its cells get placed. */
	private static BlockPos spotCentre = null;
	private static long stationBin = Long.MIN_VALUE;
	private static long stationSince;
	private static int stationTodo = -1;
	private static final java.util.Set<Long> stationsTried = new java.util.HashSet<>();
	/** How many times this station has been re-aimed after placing nothing. See stand(). */
	private static int stationRetry = 0;
	/** Consecutive failures inside advance(). Reported a few times, then given up on. See tick(). */
	private static int hiccups = 0;
	/** Said once per design: there is nothing placed for the printer to print. */
	private static boolean placementWarned = false;
	/**
	 * Nothing placed at ONE station for this long and it moves to the next.
	 *
	 * <p>Much shorter than {@link #STALL_MS}, and they answer different questions: this one asks
	 * "is there anything left here that the printer will take", the other asks "is this loop doing
	 * anything at all". A station that will not build must not cost a minute and a half.
	 */
	static final long STATION_MS = 20_000;
	/**
	 * How far out of the work a standing spot may be.
	 *
	 * <p>Tight on purpose. A bin is a cube of {@link Plan#PRINTER_REACH}, so its far corner is about
	 * 3.5 from the middle and the printer reaches 4.5 — the slack between those two is the whole
	 * budget, and every block of standoff spends it. Wide enough to get out of the wall, no wider.
	 */
	static final int STANDOFF = 3;
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

		// ---- OUT OF VIEW IS NOT FINISHED. `split` can only diff chunks the client has, so an empty
		// todo list means "nothing left within sight". On a 240-block island that is routinely most
		// of a design: start at the far end and every tracked design reads complete in turn, and
		// `follow all` walks the whole list announcing victory in about a second.
		//
		// Go and look instead. Flying there loads the chunks, and the next recount has real work.
		if (sp.todo().isEmpty() && sp.unseen() > 0 && sp.nearestUnseen() != null) {
			if (target == null || !target.equals(sp.nearestUnseen())) {
				fetching = false;
				// Flying to the far side of the island is not a stall. Without this the 90s watch
				// counts through the trip and reports a stall for doing exactly the right thing.
				lastProgressMs = System.currentTimeMillis();
				Highlight.clear("goto");
				guide(sp.nearestUnseen(), sp.unseen() + " cells out of view");
				mc.player.sendSystemMessage(Component.literal("[cscan] nothing left in sight, but "
					+ sp.unseen() + " cells are in chunks I do not have — going to look at "
					+ Wand.fmt(sp.nearestUnseen())));
			}
			return;
		}
		if (sp.complete()) {
			if (target != null) {
				mc.player.sendSystemMessage(Component.literal(
					"[cscan] " + sp.name() + " is complete in every loaded chunk. " + sessionReport()));
			}
			// ON TO THE NEXT ONE. A loop that finishes the deck floor at 2am and then idles until
			// morning is half a loop, and `plan` with no argument already ranks work across all the
			// tracked designs — only `follow` insisted on being told which.
			if (followAll) {
				String next = nextDesign(mc, sp.name());
				if (next != null) {
					mc.player.sendSystemMessage(Component.literal("[cscan] moving on to " + next));
					follow(next);
					followAll = true;
					remember(mc);
					return;
				}
				mc.player.sendSystemMessage(Component.literal(
					"[cscan] every tracked design is complete in the chunks I can see."));
			}
			following = false;
			stopGuiding();
			Highlight.clear("goto");
			remember(mc);
			return;
		}
		// ---- IS THERE ANYTHING FOR THE PRINTER TO PRINT? It places from a Litematica placement, so
		// a design with no placement - or one toggled off - is a session of flying to the right
		// spots and putting nothing down. One line, said once, at the start rather than after the
		// first ninety-second stall.
		if (!placementWarned) {
			placementWarned = true;
			if (Boolean.FALSE.equals(Litematica.enabled(sp.name()))) {
				mc.player.sendSystemMessage(Component.literal("[cscan] heads up: no ENABLED"
					+ " Litematica placement called \"" + sp.name() + "\", so the printer has"
					+ " nothing to print. /cscan place " + sp.name()));
			}
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
			// NEVER placed anything, twice over: that is not a bad spot, that is nothing printing.
			// Worth saying plainly and once - it is the difference between a wasted ten minutes and
			// a wasted night, and it is the one thing this loop cannot check for itself.
			if (placedTotal == 0 && stalls == 2) {
				Boolean live = Litematica.enabled(sp.name());
				mc.player.sendSystemMessage(Component.literal("[cscan] nothing has been placed at"
					+ " all this session. " + (Boolean.FALSE.equals(live)
						? "There is no ENABLED Litematica placement called \"" + sp.name()
							+ "\" — /cscan place " + sp.name()
						: "The placement is loaded, so check that litematica-printer is switched"
							+ " on and that you are in survival with the blocks in hand.")));
			}
			// Give up on this SPOT rather than sitting against it: the next recount picks another.
			// Dropping only the arrow left `spotCentre` set, so the hysteresis above chose the same
			// region straight back again and the stall repeated for as long as you left it.
			spotCentre = null;
			stationBin = Long.MIN_VALUE;
			stationsTried.clear();
			stopGuiding();
			Highlight.clear("goto");
			return;
		}

		// ---- the two ways the world says no: nothing to place against, and no way in. Both are a
		// six-neighbour probe of every remaining cell, which on a design of a few thousand is tens
		// of thousands of world lookups — every two seconds, for the whole session.
		//
		// Memoised on the todo COUNT, which is the only honest evidence anything moved: the printer
		// never reports, so a design whose count has not changed has had nothing placed and the
		// answer cannot have changed either. That makes the idle case — flying to a chest, waiting
		// at a station — free, and it is most of the session.
		if (sp.todo().size() != scaffoldFor) {
			scaffoldFor = sp.todo().size();
			blocked = new java.util.HashSet<>();
			for (Work.Cell c : Work.floating(mc.level, sp.todo())) blocked.add(c.pos().asLong());
			sealed = new java.util.HashSet<>();
			for (Work.Cell c : Work.unreachable(mc.level, sp.todo())) sealed.add(c.pos().asLong());
		}
		Map<String, Integer> carrying = Work.carrying(mc.player);
		java.util.List<Plan.Cluster> cl = Plan.clusters(sp.todo(), carrying, blocked, sealed, me);
		spotsLeft = cl.size();

		Map<String, Storage.Container> index;
		try {
			// CACHED, because this runs every two seconds for as long as the loop does and `load` is
			// a file read and a JSON parse; and LIVE, because the index only ever grows — it is
			// written when you OPEN a container and cannot be told about one you broke. 179 of 339
			// records were dead when it was last measured, and `fetch` navigates to these.
			index = Storage.live(Storage.loadCached(ScanRunner.schematicsDir(mc)), mc.level);
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

		// ---- SPOT HYSTERESIS. Two levels of it now, and they are different questions: this one is
		// "am I still working the same region", and `stand` below is "where in it do I float".
		//
		// Matched by PROXIMITY, not by equality: a cluster's centre is a centroid of the cells still
		// to do, so it drifts a block or two every time you place some. Comparing it exactly would
		// call every recount a new spot, reset the stations and re-announce, twice a second.
		Plan.Cluster next = null;
		if (spotCentre != null) {
			double bestD = Double.MAX_VALUE;
			for (Plan.Cluster c : cl) {
				double d = c.centre().distSqr(spotCentre);
				if (c.doable() > 0 && d < bestD && d <= (double) Plan.MAX_RADIUS * Plan.MAX_RADIUS) {
					bestD = d;
					next = c;
				}
			}
		}
		if (next == null) {
			next = cl.get(0);
			if (spotCentre != null && !wasFetching) spotsDone++;
			spotCentre = next.centre();
			stationBin = Long.MIN_VALUE;
			stationTodo = -1;
			stationsTried.clear();
			mc.player.sendSystemMessage(Component.literal("[cscan] next spot: " + next.doable()
				+ " cells around " + Wand.fmt(next.centre()) + ", " + (cl.size() - 1)
				+ " more after it"));
		}
		stand(mc, next, me, cl.size());
	}

	/**
	 * Go and stand where the printer can actually reach something.
	 *
	 * <p>The station is the fullest reach-sized bin of the spot's cells, and it is re-chosen every
	 * recount: as those cells get placed the bin empties and the next call moves you on, with no
	 * state to go stale. What IS kept is the stall — twenty seconds at one station with nothing
	 * placed and that bin is abandoned, because a bin the printer will not take (out of the
	 * placement's chunk, blocked by an entity, obstructed by something the design does not know
	 * about) is otherwise a bin you sit at.
	 */
	private static void stand(Minecraft mc, Plan.Cluster spot, BlockPos me, int spotsInPlan) {
		long now = System.currentTimeMillis();
		Plan.Station st = Plan.station(spot.cells(), Plan.PRINTER_REACH, me, stationsTried);
		if (st == null) {
			// Every bin here has been tried. Start again rather than stranding the spot: the world
			// has moved since, and the alternative is a spot that can never be worked.
			stationsTried.clear();
			st = Plan.station(spot.cells(), Plan.PRINTER_REACH, me, stationsTried);
			if (st == null) return;
			// ...and give the re-offered bin a FRESH clock. Without this it kept the timestamp from
			// the round that abandoned it, so it stalled again on the very next recount and the spot
			// span through its bins as fast as the loop could count them.
			if (st.bin() == stationBin) stationSince = now;
			stationRetry = 0;
		}

		// ---- the per-station stall, measured on this station's OWN cell count
		java.util.List<Work.Cell> here = Plan.atStation(spot.cells(), st, Plan.PRINTER_REACH);
		if (st.bin() == stationBin) {
			if (stationTodo >= 0 && here.size() < stationTodo) {
				stationSince = now;
				stationTodo = here.size();
				stationRetry = 0;                            // it is placing: the aim is fine
				// ---- MOVE AROUND THE WORK AS IT GETS BUILT. The bin is a 4-cube, so its far corner
				// is 3.5 from the centre and a standoff a few blocks out puts part of it beyond the
				// printer's reach. Re-aiming at the centroid of what is LEFT walks you round the
				// group from a new angle every time some of it goes in — which is the difference
				// between finishing a station and placing the near face of it and stopping.
				BlockPos re = Nav.standoff(Nav.of(mc.level), Plan.centroid(here),
					mc.player.blockPosition(), STANDOFF);
				if (re != null && !re.equals(target)) {
					Highlight.show("goto", Work.positions(here, 200), 0x40FF60, 900);
					guide(re, here.size() + " here");
				}
				return;
			}
			stationTodo = here.size();
			if (now - stationSince > STATION_MS) {
				// CLOSER BEFORE ELSEWHERE. Nothing placed can mean the printer cannot REACH this
				// bin from where the standoff put us: a bin is a 4-cube, so its far corner is 3.46
				// from the middle, and a standoff a few blocks out spends the rest of the 4.5 the
				// printer has. Re-aim as tight as the geometry allows and give it another go before
				// writing the bin off — abandoning a bin you could have reached leaves those cells
				// for a later pass that will make exactly the same mistake.
				if (stationRetry == 0) {
					stationRetry = 1;
					stationSince = now;
					BlockPos close = Nav.standoff(Nav.of(mc.level), Plan.centroid(here),
						mc.player.blockPosition(), 1);
					if (close != null && !close.equals(target)) {
						guide(close, here.size() + " here, closer");
						mc.player.sendSystemMessage(Component.literal(
							"[cscan] nothing placed here in " + (STATION_MS / 1000)
								+ "s — moving in closer"));
						return;
					}
				}
				stationsTried.add(st.bin());
				stationBin = Long.MIN_VALUE;
				stationRetry = 0;
				mc.player.sendSystemMessage(Component.literal("[cscan] nothing placed here in "
					+ (STATION_MS / 1000) + "s — moving to the next angle on this spot"));
				return;                                     // next recount picks another bin
			}
			return;                                          // still working: leave the arrow alone
		}

		// ---- a new station. Stand OFF it: the bin centroid is usually inside the wall you are
		// building, and a spot wedged between two blocks is one the printer never finishes.
		stationBin = st.bin();
		stationSince = now;
		stationTodo = here.size();
		stationRetry = 0;
		BlockPos at = Nav.standoff(Nav.of(mc.level), st.where(), me, STANDOFF);
		if (at == null) at = st.where();
		Highlight.show("goto", Work.positions(here, 200), 0x40FF60, 900);
		guide(at, st.cells() + " here, " + spot.doable() + " in this spot");
		mc.player.sendSystemMessage(Component.literal("[cscan] " + st.cells() + " cells at "
			+ Wand.fmt(st.where()) + " — " + spot.doable() + " left in this spot, "
			+ (spotsInPlan - 1) + " more spots after it"));
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
	 * The next tracked design with anything left to place, or null.
	 *
	 * <p>Tracked, not every design in the folder: the folder holds 61 including a shelf of scratch
	 * animals parked at the origin lock, and `sync.yaml` is the only record of which are real work.
	 * A design whose work list will not load is SKIPPED rather than fatal — one un-regenerated
	 * sidecar must not end an overnight run.
	 */
	static String nextDesign(Minecraft mc, String after) {
		try {
			java.nio.file.Path dir = ScanRunner.schematicsDir(mc);
			java.util.List<String> all = Designs.tracked(dir);
			if (all == null) return null;
			for (String name : all) {
				if (name.equals(after)) continue;
				try {
					Work.Split sp = Work.split(mc.level, dir, name, mc.player.blockPosition(), 0);
					// ...including what it cannot see. Otherwise standing at one end of the island
					// makes every design look finished and the run ends before it starts.
					if (!sp.complete()) return name;
				} catch (Exception skip) {
					// no work.json yet, or it will not parse: not this run's problem
				}
			}
		} catch (Exception e) {
			return null;
		}
		return null;
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
	/** Carry on to the next tracked design when this one is done. */
	private static boolean followAll = false;
	/** Ticks left before the loop is allowed to act after joining a world. */
	private static int grace = 0;

	static boolean followingAll() {
		return followAll;
	}

	static void followAll(Minecraft mc, boolean v) {
		followAll = v;
		remember(mc);
	}

	/**
	 * Write down what the loop is doing, so a disconnect does not end it.
	 *
	 * <p>Called wherever the INTENT changes, never on the tick: this is four fields, and the loop is
	 * meant to run for hours.
	 */
	static void remember(Minecraft mc) {
		try {
			Session.save(ScanRunner.schematicsDir(mc),
				new Session.State(following ? design : null, Autopilot.on(), followAll,
					Autopilot.speed()));
		} catch (Exception ignored) {
		}
	}

	/**
	 * Pick up where it left off.
	 *
	 * <p>Held off for {@link Session#GRACE_TICKS}: on the tick you join, most of the world is
	 * unloaded, and `Nav` treats unloaded as passable — which is right for a route you are already
	 * flying and quite wrong as the first thing you do. Routing then flies you straight into terrain
	 * that was simply not there yet.
	 */
	static void resume(Minecraft mc) {
		try {
			restore(mc);
		} catch (Exception e) {
			// This runs on the JOIN event. Throwing here takes the mod down at the one moment you
			// cannot see why, for the sake of a convenience.
		}
	}

	private static void restore(Minecraft mc) {
		Session.State st = Session.load(ScanRunner.schematicsDir(mc));
		if (st == null) return;
		Autopilot.setSpeed(st.speed());
		followAll = st.all();
		if (st.design() == null) return;
		follow(st.design());
		followAll = st.all();
		grace = Session.GRACE_TICKS;
		if (st.autofly()) Autopilot.set(true);
		if (mc.player != null) {
			mc.player.sendSystemMessage(Component.literal("[cscan] resuming " + st.design()
				+ (st.autofly() ? " with autofly" : "") + " in " + (Session.GRACE_TICKS / 20)
				+ "s — /cscan stop to not."));
		}
	}

	static void follow(String name) {
		watch(name);
		following = true;
		placementWarned = false;
		stopGuiding();
		Withdraw.clearFailures();
		lastTodo = -1;
		lastProgressMs = System.currentTimeMillis();
		startedMs = lastProgressMs;
		placedTotal = 0;
		spotsDone = 0;
		hiccups = 0;
		fetches = 0;
		stalls = 0;
		said = false;
		stationBin = Long.MIN_VALUE;
		stationTodo = -1;
		stationsTried.clear();
		spotCentre = null;
		scaffoldFor = -1;
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
		if (grace > 0 && --grace > 0) return;             // let the world arrive before routing it
		if (tick++ % EVERY_TICKS != 0) return;
		try {
			Work.Split sp = Work.split(mc.level, ScanRunner.schematicsDir(mc), design,
				mc.player.blockPosition(), 0);
			// A THROW INSIDE THE DECISION IS NOT A REASON TO END THE SESSION. Reading the work list
			// can fail permanently - no work.json, bad JSON - and the catch below is right to stop
			// for that. Everything after it is a judgement about a world that is being changed
			// underneath us by another mod, and a transient failure there should cost one tick.
			if (following) {
				try {
					advance(mc, sp);
					hiccups = 0;
				} catch (Exception e) {
					if (++hiccups <= 3) {
						mc.player.sendSystemMessage(Component.literal("[cscan] recovered from "
							+ e + " — carrying on"));
					}
					if (hiccups >= 20) {
						mc.player.sendSystemMessage(Component.literal(
							"[cscan] giving up after 20 failures in a row: " + e));
						following = false;
						stopGuiding();
					}
				}
			}
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
