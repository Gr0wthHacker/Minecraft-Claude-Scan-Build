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
	/** Where the player was, and when they were last somewhere else. Sampled every TICK. */
	private static BlockPos lastAt = null;
	private static long movedAt;
	/** A spot that went nowhere, and until when to pass over it. */
	private static BlockPos avoidSpot = null;
	private static long avoidUntil;

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
	/** When we actually got to the current station, or 0 if we have not yet. For the dwell. */
	private static long stationArrivedAt = 0;
	/** Consecutive failures inside advance(). Reported a few times, then given up on. See tick(). */
	private static int hiccups = 0;
	/** Said once per design: there is nothing placed for the printer to print. */
	private static boolean placementWarned = false;
	/** Said once per design: most of what is left is a block the printer cannot replace. */
	private static boolean deviationsSaid = false;
	/** Materials we have already pointed out are sitting in a shulker box. */
	private static final java.util.Set<String> saidBoxed = new java.util.HashSet<>();
	/**
	 * Nothing placed at ONE station for this long and it moves to the next.
	 *
	 * <p>Much shorter than {@link #STALL_MS}, and they answer different questions: this one asks
	 * "is there anything left here that the printer will take", the other asks "is this loop doing
	 * anything at all". A station that will not build must not cost a minute and a half.
	 *
	 * <p>Five seconds, on Jack's instruction, and it is only safe because the clock starts when you
	 * ARRIVE. Timed from the moment the station is chosen it would abandon anything more than a few
	 * seconds' flight away before the printer ever had a chance at it — a loop touring bins and
	 * placing nothing, which looks exactly like the failure it is meant to catch.
	 */
	static final long STATION_MS = 5_000;
	/**
	 * Once you get somewhere, STAY there for a moment.
	 *
	 * <p>Jack: <i>"when we reach an area we dont instantly run away if we are placing blocks, we
	 * should reach an area, stay for a few seconds, then move on unless something e.g. blocked."</i>
	 *
	 * <p>The bin is re-chosen on every recount, and the fullest one changes as cells elsewhere become
	 * placeable — so a station could be abandoned two seconds after arriving, before the printer had
	 * taken a single block, in favour of somewhere that merely looked better. All of the flying, none
	 * of the building.
	 *
	 * <p>Just under {@link #STATION_MS} on purpose: the dwell holds the spot, and if nothing has been
	 * placed by the time the stall fires, that is the thing that moves it on. A dwell longer than the
	 * stall would be a loop that cannot leave somewhere it cannot build.
	 */
	static final long DWELL_MS = 4_000;
	/**
	 * How far out of the work a standing spot may be.
	 *
	 * <p>Tight on purpose, and tighter now. A bin's far corner is already about 3.5 from its middle
	 * and the printer reaches around 4.5, so the slack between them is the entire budget. It was 3 —
	 * which is 3 in CHEBYSHEV, so up to 5.2 as the crow flies — and between that and stopping short
	 * on arrival, the far half of a bin was simply unreachable. That is the "not getting close
	 * enough" half of the report.
	 *
	 * <p>What keeps it safe at 2 is no longer the distance. It is {@link Nav#AIR_BELOW},
	 * {@link Nav#AIR_ABOVE} and {@link Autopilot#SAFE_GAP} — clearance rules, rather than standing
	 * further back and hoping.
	 */
	static final int STANDOFF = 2;
	/**
	 * Told to go somewhere and not going. Jack: <i>"if it says it needs to reroute and doesnt move
	 * or doesnt perform action within 3 seconds, move to next cluster"</i>.
	 *
	 * <p>The fast clock of the three. A flight that has not moved in three seconds is not about to
	 * start: it is pressed into a corner, routing at a wall, or wedged under something. Whatever the
	 * cause, the spot is not working out and there is usually another.
	 */
	static final long NOWHERE_MS = 3_000;
	/** How long a spot that went nowhere is passed over for. */
	static final long AVOID_MS = 60_000;
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
		if (sp.placementComplete()) {
			if (target != null) {
				// THE LOOP CANNOT DIG, so it says what it is handing back rather than calling a
				// design finished that still has rock standing in it. `Falls` is 30 blocks placed
				// and 41 cells to break; announcing that as complete is how the channel never
				// gets cut.
				String dig = sp.digLeft() == 0 ? ""
					: "  " + sp.digLeft() + " cell(s) still to BREAK by hand — /cscan dig " + sp.name();
				mc.player.sendSystemMessage(Component.literal(
					"[cscan] " + sp.name() + ": nothing left to place in a loaded chunk. "
						+ sessionReport() + dig));
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
		// ---- CELLS THE WORLD HAS SOMETHING ELSE IN. The printer places into air; it does not
		// replace. So a design whose remaining work is mostly deviations will never finish however
		// long the loop runs, and the loop cannot tell you that by getting quieter. Said once.
		if (!deviationsSaid && !sp.wrong().isEmpty() && sp.todo().size() < sp.wrong().size()) {
			deviationsSaid = true;
			mc.player.sendSystemMessage(Component.literal("[cscan] " + sp.wrong().size()
				+ " cells hold a DIFFERENT block from the design — the printer places into air and"
				+ " cannot replace them. /cscan check " + sp.name() + " marks them amber;"
				+ " they need breaking by hand."));
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
		if (Loop.stalled(now, lastProgressMs, fetching, STALL_MS)) {
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

		// ---- TOLD TO GO SOMEWHERE, AND NOT GOING. See Loop.goingNowhere: the fast clock, and the
		// only one that fires while there is still somewhere to be.
		boolean travelling = target != null
			&& me.distSqr(target) > (double) (Plan.reach() + STANDOFF) * (Plan.reach() + STANDOFF);
		if (Loop.goingNowhere(now, movedAt, lastProgressMs, travelling, fetching, NOWHERE_MS)) {
			mc.player.sendSystemMessage(Component.literal("[cscan] not moving and not placing at "
				+ Wand.fmt(target) + " — giving up on this spot and taking the next one"));
			avoidSpot = spotCentre;
			avoidUntil = now + AVOID_MS;
			spotCentre = null;
			stationBin = Long.MIN_VALUE;
			stationRetry = 0;
			stationsTried.clear();
			movedAt = now;                                 // one report per stick, not one per tick
			stopGuiding();
			Highlight.clear("goto");
			Autopilot.forget();
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

		// Only worked out when the answer can matter — a fetch costs a container index walk and an
		// inventory scan, and while there is work in front of you the question is not asked.
		java.util.List<Plan.Restock> targets = java.util.List.of();
		Plan.Restock want = null;
		if (fetching || !canWork) {
			// Skip chests in their cooling-off period, or the loop is guided at one it will not open.
			targets = Plan.fetchTargets(sp.todo(), carrying, index, me,
				Withdraw.coolingOff(System.currentTimeMillis()));
			// ---- WHAT YOU ALREADY HAVE IN A BOX IS NOT WORTH A TRIP. It is not placeable either —
			// see Work.boxed — so it cannot simply be added to `carrying`; the loop would fly to a
			// spot and find it can place nothing. Told, not fetched.
			Map<String, Integer> boxes = Work.boxed(mc.player);
			targets = Plan.notInAPack(targets, boxes, item -> {
				// ...AND IT UNPACKS ITSELF NOW. This used to tell you to "set it down and take
				// them", which is the same shape of claim as "a client mod cannot place a block":
				// a policy written as a fact. Unboxing is placing, opening, emptying and breaking,
				// and this mod already does all four. If it cannot be done safely — nowhere to
				// stand the box that is not over the void — Unbox refuses and the message stands.
				if (!Unbox.running() && Unbox.boxWith(mc.player, item) >= 0) {
					String said = Unbox.start(mc, item, boxes.get(item));
					if (saidBoxed.add(item)) {
						mc.player.sendSystemMessage(Component.literal("[cscan] " + said));
					}
					return;
				}
				if (saidBoxed.add(item)) {
					mc.player.sendSystemMessage(Component.literal("[cscan] you are carrying "
						+ boxes.get(item) + "x " + item + " in a shulker box — set it down and take"
						+ " them rather than flying across the island for more."));
				}
			});
			want = Plan.nextFetch(targets, it -> Work.room(mc.player, it));
		}

		Loop.Phase phase = Loop.phase(sp.todo().size(), sp.unseen(), canWork, fetching,
			want != null, !targets.isEmpty());
		fetching = phase == Loop.Phase.FETCH;
		switch (phase) {
			case FETCH -> {
				fetchTo(mc, me, want, Work.room(mc.player, want.item()), carrying);
				return;
			}
			case DEAD_END, PACK_FULL -> {
				// Nothing placeable and nothing to fetch are DIFFERENT dead ends and want different
				// answers: one sends you to the store hall, the other says your pack is full of
				// something this design has no room left for.
				if (target != null || !said) {
					said = true;
					mc.player.sendSystemMessage(Component.literal(phase == Loop.Phase.DEAD_END
						? "[cscan] nothing left you are carrying the blocks for, and nothing indexed"
							+ " to fetch — /cscan bom " + sp.name()
						: "[cscan] pack is full of what you cannot place here — store something, or"
							+ " /cscan bom " + sp.name()));
				}
				stopGuiding();
				Highlight.clear("goto");
				return;
			}
			default -> { }
		}
		said = false;

		// ---- SPOT HYSTERESIS. Two levels of it now, and they are different questions: this one is
		// "am I still working the same region", and `stand` below is "where in it do I float".
		//
		// Matched by PROXIMITY, not by equality: a cluster's centre is a centroid of the cells still
		// to do, so it drifts a block or two every time you place some. Comparing it exactly would
		// call every recount a new spot, reset the stations and re-announce, twice a second.
		// ---- THRASHING. Abandon spot A, take B, abandon B, take A again when its minute expires,
		// for ever: every decision correct, the sequence a machine going nowhere. The evidence is
		// the pair — several spots given up on, and nothing placed while it happened.
		if (Loop.thrashing(spotsAbandoned, placedTotal - placedWhenAbandoned, THRASH_LIMIT)) {
			spotsAbandoned = 0;
			mc.player.sendSystemMessage(Component.literal("[cscan] " + THRASH_LIMIT + " spots given"
				+ " up on with nothing placed — this design is not buildable from here right now."));
			if (followAll) {
				String other = nextDesign(mc, sp.name());
				if (other != null) {
					mc.player.sendSystemMessage(Component.literal("[cscan] moving on to " + other));
					follow(other);
					followAll = true;
					remember(mc);
					return;
				}
			}
			mc.player.sendSystemMessage(Component.literal("[cscan] stopping. /cscan why for what it"
				+ " was trying, /cscan check " + sp.name() + " for cells the world disagrees about."));
			following = false;
			stopGuiding();
			Highlight.clear("goto");
			remember(mc);
			return;
		}

		Plan.Cluster next = Loop.sameSpot(spotCentre, cl, Plan.MAX_RADIUS);
		if (next == null) {
			// PASS OVER THE SPOT THAT JUST WENT NOWHERE. Without this the next recount picks the
			// same region — it is still the best one — flies at the same wall, and sticks again.
			next = null;
			for (Plan.Cluster c : cl) {
				if (Ignored.has(c.centre())) continue;         // written off: never again this session
				if (avoidSpot != null && now < avoidUntil
					&& c.centre().distSqr(avoidSpot) <= (double) Plan.MAX_RADIUS * Plan.MAX_RADIUS) {
					continue;                                   // still cooling off
				}
				next = c;
				break;
			}
			// ...but a hard spot is better than no spot: if everything left is merely COOLING OFF,
			// take it anyway rather than idling until the minute expires. An IGNORED spot is
			// different — it has failed twice and is not on the table at all.
			if (next == null) {
				avoidSpot = null;
				for (Plan.Cluster c : cl) {
					if (!Ignored.has(c.centre())) {
						next = c;
						break;
					}
				}
			}
			if (next == null) {
				if (!said) {
					said = true;
					mc.player.sendSystemMessage(Component.literal("[cscan] every spot left is one"
						+ " that has failed twice (" + Ignored.count() + " ignored, marked red)."
						+ " /cscan ignore clear to try them again."));
				}
				stopGuiding();
				return;
			}
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
		// READY, NOT CELLS — and then NOW, not ready. Three different questions, and the loop has
		// been wrong about each of them in turn:
		//
		//   cells   everything left in this region, including what has nothing to place against
		//   ready   minus the floating and the sealed-in — but `floating` counts an earlier DESIGN
		//           cell as support, which is right for "does this need scaffolding" and wrong for
		//           "can I place it now": that support may not be built, and may not even be in
		//           this bin
		//   now     has a real face to click, in the world, this second
		//
		// Standing anywhere else is standing in front of something the printer will not touch.
		java.util.List<Work.Cell> live = Work.placeableNow(mc.level, spot.ready());
		if (live.isEmpty()) live = spot.ready();     // nothing placeable yet; fall back rather than
		                                             // strand the spot
		Plan.Station st = Plan.station(live, Plan.reach(), me, stationsTried);
		if (st == null) {
			// Every bin here has been tried. Start again rather than stranding the spot: the world
			// has moved since, and the alternative is a spot that can never be worked.
			stationsTried.clear();
			st = Plan.station(live, Plan.reach(), me, stationsTried);
			if (st == null) return;
			// ...and give the re-offered bin a FRESH clock. Without this it kept the timestamp from
			// the round that abandoned it, so it stalled again on the very next recount and the spot
			// span through its bins as fast as the loop could count them.
			if (st.bin() == stationBin) stationSince = now;
			stationRetry = 0;
		}

		// ---- the per-station stall, measured on this station's OWN cell count
		java.util.List<Work.Cell> here = Plan.atStation(live, st, Plan.reach());
		// Within reach of the work, rather than still on the way to it.
		boolean arrived = target == null
			|| me.distSqr(target) <= (double) (Plan.reach() + STANDOFF) * (Plan.reach() + STANDOFF);
		if (!arrived) {
			stationSince = now;                          // the clock has not started yet
		} else if (stationArrivedAt == 0) {
			stationArrivedAt = now;                      // ...and the dwell starts here
		}

		// ---- STAY A MOMENT. See DWELL_MS: the fullest bin changes as cells elsewhere become
		// placeable, and without this the loop leaves a spot it has only just reached because
		// somewhere else now looks better — all of the flying, none of the building.
		if (stationBin != Long.MIN_VALUE && stationArrivedAt > 0
			&& now - stationArrivedAt < DWELL_MS) {
			Plan.Station staying = Plan.stationOf(live, stationBin, Plan.reach());
			if (staying != null) {
				st = staying;
				here = Plan.atStation(live, st, Plan.reach());
			}
		}
		// WHEN WE ARE THE PRINTER, ASK THE PRINTER. The clocks below exist only because placement
		// used to be silent; with a real report a placement is progress immediately and a refusal
		// is proof immediately, where five seconds of nothing could only ever be a guess. Silence
		// still falls through to the clock, because nothing attempted is not evidence of anything.
		int[] rep = Printer.driving() ? Printer.drainReport() : new int[] {0, 0};
		Loop.Station what = Printer.driving()
			? Loop.stationFromReport(st.bin() == stationBin, arrived, here.size(), stationTodo,
				now - stationSince, STATION_MS, stationRetry, rep[0], rep[1])
			: Loop.station(st.bin() == stationBin, arrived, here.size(), stationTodo,
				now - stationSince, STATION_MS, stationRetry);
		if (rep[0] > 0) lastProgressMs = now;   // a placement is progress, whatever the count says
		if (what != Loop.Station.NEW) {
			if (what == Loop.Station.RECENTRE) {
				stationSince = now;
				stationTodo = here.size();
				stationRetry = 0;                            // it is placing: the aim is fine

				// ---- DO NOT ADJUST WHAT IS ALREADY WORKING.
				//
				// Re-aiming after every few blocks meant a fresh approach every couple of seconds,
				// and every approach is a chance to nudge a wall and lose flight — the "getting too
				// close when adjusting and then stopping flight" half of the report. The question is
				// not whether the aim is still IDEAL, it is whether the printer can still REACH what
				// is left. While it can, holding still beats improving.
				if (allWithinReach(me, here, Plan.reach())) return;

				// ---- MOVE AROUND THE WORK AS IT GETS BUILT. The bin is a 4-cube, so its far corner
				// is 3.5 from the centre and a standoff a few blocks out puts part of it beyond the
				// printer's reach. Re-aiming at the centroid of what is LEFT walks you round the
				// group from a new angle every time some of it goes in — which is the difference
				// between finishing a station and placing the near face of it and stopping.
				BlockPos re = Plan.bestStand(Nav.of(mc.level), here, Plan.reach(),
					mc.player.blockPosition(), STANDOFF + 2, Autopilot.ARRIVE_MIN);
				if (re != null && !re.equals(target)) {
					Highlight.show("goto", Work.positions(here, 200), 0x40FF60, 900);
					guide(re, here.size() + " here");
				}
				return;
			}
			stationTodo = here.size();
			if (what == Loop.Station.CLOSER || what == Loop.Station.ABANDON) {
				// CLOSER BEFORE ELSEWHERE. Nothing placed can mean the printer cannot REACH this
				// bin from where the standoff put us: a bin is a 4-cube, so its far corner is 3.46
				// from the middle, and a standoff a few blocks out spends the rest of the 4.5 the
				// printer has. Re-aim as tight as the geometry allows and give it another go before
				// writing the bin off — abandoning a bin you could have reached leaves those cells
				// for a later pass that will make exactly the same mistake.
				if (what == Loop.Station.CLOSER) {
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
				stationArrivedAt = 0;
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
		stationArrivedAt = 0;                            // not there yet; the dwell starts on arrival
		// COVERAGE, not proximity. See Plan.bestStand: the spot is chosen by how many of these cells
		// the printer can touch from it, discounted by how far short the flight parks.
		BlockPos at = Plan.bestStand(Nav.of(mc.level), here, Plan.reach(), me, STANDOFF + 2,
			Autopilot.ARRIVE_MIN);
		if (at == null) at = Nav.standoff(Nav.of(mc.level), st.where(), me, STANDOFF);
		if (at == null) at = st.where();
		Highlight.show("goto", Work.positions(here, 200), 0x40FF60, 900);
		guide(at, st.cells() + " here, " + spot.doable() + " in this spot");
		mc.player.sendSystemMessage(Component.literal("[cscan] " + st.cells() + " cells at "
			+ Wand.fmt(st.where()) + " — " + spot.doable() + " left in this spot, "
			+ (spotsInPlan - 1) + " more spots after it"));
	}

	/**
	 * Give up on the region being worked and take the next one.
	 *
	 * <p>Called by the autopilot when it cannot physically get there — wedged in a gap it has spent
	 * long enough trying to thread. The loop owns the decision about WHERE to work, so the flight
	 * asks rather than deciding; but the flight is the only thing that knows the way is not flyable.
	 *
	 * <p>Same treatment as the three-second watchdog: the spot is passed over for a minute, because
	 * without that the next recount picks the same region — it is still the best one — and flies at
	 * the same gap again.
	 */
	/** How many spots may be given up on with nothing placed before the design is the problem. */
	static final int THRASH_LIMIT = 4;

	private static int spotsAbandoned = 0;
	private static int placedWhenAbandoned = 0;

	static void abandonSpot() {
		// A strike against the PLACE, not just a minute of avoiding it. Two and the loop stops
		// coming back at all — a timer forgets, and a place that has beaten it twice will not be
		// different in a minute.
		if (spotCentre != null && Ignored.strike(spotCentre)) {
			Highlight.show("ignore", Ignored.marks(), 0xFF3030, 600);
		}
		// Count the giving-up, and remember what had been placed at the time: several abandonments
		// with NOTHING built between them is thrashing, which no single watchdog can see.
		if (placedTotal == placedWhenAbandoned) {
			spotsAbandoned++;
		} else {
			spotsAbandoned = 1;
			placedWhenAbandoned = placedTotal;
		}
		avoidSpot = spotCentre;
		avoidUntil = System.currentTimeMillis() + AVOID_MS;
		spotCentre = null;
		stationBin = Long.MIN_VALUE;
		stationRetry = 0;
		stationArrivedAt = 0;
		stationsTried.clear();
		movedAt = System.currentTimeMillis();
		stopGuiding();
		Highlight.clear("goto");
	}

	/** Can the printer still touch every one of these from where the player is standing? */
	private static boolean allWithinReach(BlockPos me, java.util.List<Work.Cell> cells, int reach) {
		double r2 = (double) reach * reach;
		for (Work.Cell c : cells) {
			if (c.pos().distSqr(me) > r2) return false;
		}
		return true;
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
			int inBoxes = Storage.boxedCount(want.where(), want.item());
			mc.player.sendSystemMessage(Component.literal("[cscan] fetch: " + take + "x "
				+ want.item() + " from " + want.where().describe() + " (" + want.available()
				+ " there, " + want.missing() + " still wanted, room for " + room + ")"
				+ (inBoxes > 0 ? "  — " + inBoxes + " of them are inside shulker boxes; it will"
					+ " take the box and you set it down" : "")));
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
			// IN BUILD ORDER. `follow all` used to walk the tracked list as written, so it could
			// start a design whose ground another one still owes - mcbuild settles that with
			// `finish.defer_to` and CLAUDE.md states the sequences in prose, and none of it reached
			// the mod. A design with no `after` in its sidecar keeps its place, so a folder written
            // before this existed is ordered exactly as it was.
			all = Designs.inBuildOrder(dir, all);
			for (String name : all) {
				if (name.equals(after)) continue;
				try {
					Work.Split sp = Work.split(mc.level, dir, name, mc.player.blockPosition(), 0);
					// ...including what it cannot see. Otherwise standing at one end of the island
					// makes every design look finished and the run ends before it starts.
					// placementComplete, not complete: a design whose only remainder is a dig list
					// is not work the loop can do, and choosing it means choosing to stall.
					if (!sp.placementComplete()) return name;
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
	 * Everything the loop is thinking, in one place, on demand.
	 *
	 * <p>Written after the fourth "it got stuck" that had to be diagnosed from a sentence. The loop
	 * computes all of this every two seconds and then says almost none of it, because a loop that
	 * narrates itself continuously is a loop nobody reads. Asked, it should answer completely.
	 */
	static java.util.List<String> why(Minecraft mc) {
		java.util.List<String> out = new java.util.ArrayList<>();
		if (design == null) {
			out.add("not watching a design — /cscan follow <design>, or /cscan follow all");
			out.addAll(Autopilot.why(mc));
			return out;
		}
		out.add(design + (following ? (followAll ? "  (following all)" : "  (following)")
			: "  (watching only — /cscan follow " + design + " to work it)"));
		try {
			Work.Split sp = Work.split(mc.level, ScanRunner.schematicsDir(mc), design,
				mc.player.blockPosition(), 0);
			out.add("  " + sp.built() + " built, " + sp.todo().size() + " to place, "
				+ sp.wrong().size() + " deviating, " + sp.unseen() + " in chunks I do not have");
			if (!sp.todo().isEmpty()) {
				Map<String, Integer> carrying = Work.carrying(mc.player);
				java.util.List<Work.Cell> live = Work.placeableNow(mc.level, sp.todo());
				out.add("  " + live.size() + " of those have something to build against right now");
				Map<String, Integer> want = new java.util.LinkedHashMap<>();
				for (Work.Cell c : sp.todo()) want.merge(c.item(), 1, Integer::sum);
				StringBuilder sb = new StringBuilder("  materials:");
				int shown = 0;
				for (var e : want.entrySet()) {
					if (shown++ >= 4) break;
					sb.append(' ').append(e.getValue()).append('x').append(' ').append(e.getKey())
						.append(" (have ").append(carrying.getOrDefault(e.getKey(), 0)).append(')');
				}
				out.add(sb.toString());
			}
			Boolean live = Litematica.enabled(sp.name());
			out.add("  litematica placement: " + (live == null ? "cannot tell"
				: live ? "loaded and enabled" : "MISSING or disabled — /cscan place " + sp.name()));
		} catch (Exception e) {
			out.add("  work list: " + e);
		}
		out.add(fetching ? "  phase: FETCHING" : "  phase: building");
		if (spotCentre != null) out.add("  spot around " + Wand.fmt(spotCentre));
		if (target != null) out.add("  arrow at " + Wand.fmt(target) + " — " + targetNote);
		if (Ignored.count() > 0) {
			out.add("  " + Ignored.count() + " place(s) IGNORED after failing twice — /cscan ignore");
		}
		if (following) out.add("  " + sessionReport());
		out.addAll(Autopilot.why(mc));
		return out;
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

	/**
	 * Everything off, and everything FORGOTTEN.
	 *
	 * <p>It used to clear only the four obvious fields, which left `followAll` set — so a later
	 * `/cscan follow <one design>` silently became "follow all of them" — and left the spot, the
	 * abandoned stations and the avoid list to be inherited by a run that has nothing to do with
	 * them. Half a stop is the kind that is discovered an hour later.
	 */
	static void off() {
		design = null;
		lines = new ArrayList<>();
		following = false;
		followAll = false;
		fetching = false;
		said = false;
		placementWarned = false;
		deviationsSaid = false;
		saidBoxed.clear();
		spotCentre = null;
		stationBin = Long.MIN_VALUE;
		stationTodo = -1;
		stationRetry = 0;
		stationArrivedAt = 0;
		stationsTried.clear();
		avoidSpot = null;
		scaffoldFor = -1;
		hiccups = 0;
		grace = 0;
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
		deviationsSaid = false;
		saidBoxed.clear();
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
		spotsAbandoned = 0;
		placedWhenAbandoned = 0;
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
		// EVERY TICK, not every recount: a three-second watchdog sampled at two-second intervals
		// cannot tell three seconds from five.
		BlockPos at = mc.player.blockPosition();
		if (lastAt == null || at.distSqr(lastAt) > 1) {
			lastAt = at;
			movedAt = System.currentTimeMillis();
		}
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
