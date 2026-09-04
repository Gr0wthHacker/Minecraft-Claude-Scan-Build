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
	/**
	 * Fill the pack before the first block, not after it.
	 *
	 * <p>Set by {@link #follow} and cleared the moment there is nothing left to fetch. See
	 * {@link Loop#phase}: build-before-shop is the right policy in the middle of a session and the
	 * wrong one at the start of it, where it sets off with whatever was in the pack and makes the
	 * trip anyway once that runs out - having already flown to the work and back.
	 */
	private static boolean topUp = false;
	/**
	 * The middle of the area being worked. See {@link Loop#WORK_RADIUS}.
	 *
	 * <p>Null until the first recount, which anchors it wherever the loop actually started. It moves
	 * only when the area is FINISHED - never because somewhere else looks better, which is the
	 * behaviour it exists to stop.
	 */
	private static boolean saidFarFetch = false;
	/** The course being built. See Loop.LAYER_BAND - a design is worked upward, one at a time. */
	private static int workLayer = Integer.MIN_VALUE;
	/** How far the loop is currently willing to look. See Loop.NEAR_RADIUS. */
	private static int workRadius = Loop.NEAR_RADIUS;
	private static boolean saidIndexBroken = false;
	/** Items whose unboxing failed here, and when to try them again. A site is a place, not a fact. */
	private static final Map<String, Long> unboxRetryAt = new java.util.HashMap<>();
	static final long UNBOX_RETRY_MS = 60_000;

	private static boolean unboxWorthTrying(String item) {
		Long at = unboxRetryAt.get(item);
		return at == null || System.currentTimeMillis() >= at;
	}

	private static void noteUnboxOutcome(String item) {
		if (!Unbox.running() && Unbox.phase() == Unbox.Phase.FAILED) {
			unboxRetryAt.put(item, System.currentTimeMillis() + UNBOX_RETRY_MS);
		}
	}
	/** Designs this session has SEEN complete, with their cells in view. Never returned to. */
	private static final java.util.Set<String> doneThisSession = new java.util.HashSet<>();
	/** Designs handed back unfinished — dead end, full pack, every spot ignored — under follow all. */
	private static final java.util.Set<String> parked = new java.util.HashSet<>();
	/** Designs whose out-of-view cells could not be loaded twice: treated as out of reach. */
	private static final java.util.Set<String> unseenGivenUp = new java.util.HashSet<>();
	private static BlockPos lookTarget = null;
	private static long lookSince = 0;
	private static int lookFailures = 0;
	static final long LOOK_STUCK_MS = 8_000;
	static final int LOOK_STRIKES = 2;
	/** Consecutive recounts whose work list could not be read. */
	private static int splitFailures = 0;
	static final int SPLIT_FAILURE_LIMIT = 3;
	private static int lastUnseen = -1;
	/** The printer's report for this recount, drained ONCE at the top so it is never attributed twice. */
	private static int[] lastReport = {0, 0};
	private static int recounts = 0;
	/** Every this many recounts the printer forgets its "never" verdicts and re-asks the world. */
	static final int RELAX_EVERY = 15;

	/**
	 * Stop everything AND forget the intent, so the next join does not resume movement automation
	 * the code has just decided was unsafe to continue. {@link #off} alone leaves session.json
	 * saying "following, with autofly", which is right for a disconnect and wrong for a box that
	 * did not come back.
	 */
	static void stopForSafety(Minecraft mc) {
		off();
		try { Session.clear(ScanRunner.schematicsDir(mc)); } catch (Exception ignored) { }
		Autopilot.set(false);
		if (mc != null && mc.player != null) mc.player.sendSystemMessage(Component.literal(
			"[cscan] automation STOPPED and will not resume on its own — /cscan follow to start again"));
	}

	/**
	 * The key a routing failure is struck against. The loop filters spots by their CENTRE, so a
	 * strike must land on that centre or it lands on nothing anybody ever looks up. During a
	 * fetch there is no spot, and the failing place is the approach cell itself.
	 */
	static BlockPos strikeKeyFor(BlockPos target) {
		return following && !fetching && spotCentre != null ? spotCentre : target;
	}

	/**
	 * Go and look at a cell in a chunk we do not have - and MOVE THE AREA to it rather than making
	 * a round trip out of it.
	 *
	 * <p>This is the flight that was crossing the map. `Park Complete` is 540,862 cells over six
	 * hundred blocks and a render distance is under two hundred, so there are ALWAYS cells out of
	 * view: `unseen > 0` is permanently true, and every dead end sent the loop to the nearest one,
	 * wherever in the park that was. The working area bounded the FRONTIER and this went round it.
	 *
	 * <p>Looking is legitimate - out of view is not finished, and a loop that stops at the edge of
	 * its own render distance would report half a design complete. What is not legitimate is doing
	 * it as an excursion. If the place to look is outside the area, the area is finished, so the
	 * area moves; the next recount then works out from there.
	 */
	private static void goLook(Minecraft mc, BlockPos at, String why) {
		// Going to look is a move, so the radius starts again at arm's length when we get there.
		workRadius = Loop.nearAgain();
		guide(at, why);
	}
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
	 * How long to work one bearing before moving round to the next. See {@link Plan#ring}.
	 *
	 * <p>Long enough that the printer empties what it can see from there - Jack measures it at
	 * roughly seven placements a second - and short enough that the body is never asked to hold a
	 * position, which is when it drifts into something and the flight ends.
	 */
	static final long ORBIT_MS = 3_000;
	private static int orbitLeg = 0;
	private static long orbitSince = 0;
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
		guide(where, note, Mode.NEAR);
	}

	/** What the flight is meant to do at the target. */
	enum Mode { NEAR, EXACT, LAND }
	private static Mode mode = Mode.NEAR;

	/**
	 * Guide to a cell to LAND in: descend onto its floor, let flight end, and work standing. See
	 * Plan.groundStand for why — work on a floor cannot be reached from a hovering stand at all.
	 * The loop takes off again by itself (Autopilot.regain) when the next target needs the air.
	 */
	static void guideLand(BlockPos where, String note) {
		guide(where, note, Mode.LAND);
	}

	/** Whether the current target is a cell to land in. */
	static boolean targetLand() {
		return target != null && mode == Mode.LAND;
	}

	/**
	 * Guide to a cell the body must actually occupy. See {@link Autopilot#EXACT_MIN}: a station is
	 * a place to hover NEAR, a chest's approach cell is a place to BE.
	 */
	static void guideExact(BlockPos where, String note) {
		guide(where, note, Mode.EXACT);
	}

	private static void guide(BlockPos where, String note, Mode how) {
		target = where;
		mode = how;
		targetNote = note == null ? "" : note;
	}

	/** Whether the current target is one the flight must actually reach, not merely approach. */
	static boolean targetExact() {
		return target != null && mode == Mode.EXACT;
	}

	static void stopGuiding() {
		target = null;
		mode = Mode.NEAR;
		targetNote = "";
	}

	/** Slack off the printer's reach for a stand whose position is exact — a landing. */
	static final double LAND_SLACK = 0.4;

	/**
	 * Pick where to work THESE cells from, and guide there: on the ground when the ground covers
	 * as much as the air does, in the air otherwise. Landing is preferred on a tie because a body
	 * on a floor does not drift, does not have to hold altitude, and cannot lose flight by
	 * touching something — it has already touched the one thing it is allowed to.
	 */
	private static void standAt(Minecraft mc, java.util.List<Work.Cell> here, BlockPos me, String note) {
		Nav.Passable free = Nav.of(mc.level);
		java.util.function.Predicate<BlockPos> solid = b -> mc.level.isLoaded(b)
			&& mc.level.getBlockState(b).blocksMotion();
		BlockPos ground = Plan.groundStand(free, solid, here, Plan.reachExact() - LAND_SLACK, me, STANDOFF + 3);
		BlockPos hover = Plan.bestStand(free, here, Plan.reachExact(), me, STANDOFF + 2, Autopilot.ARRIVE_MIN);
		int onGround = ground == null ? 0 : Plan.coveredFrom(here, ground, Plan.reachExact() - LAND_SLACK, free);
		int inAir = hover == null ? 0 : Plan.coveredFrom(here, hover, Plan.reachExact() - Autopilot.ARRIVE_MIN, free);
		Highlight.show("goto", Work.positions(here, 200), 0x40FF60, 900);
		if (ground != null && onGround >= inAir) {
			guideLand(ground, "land: " + note);
			return;
		}
		if (hover == null) hover = Nav.standoff(free, Plan.centroid(here), me, STANDOFF);
		if (hover == null) hover = Plan.centroid(here);
		guide(hover, note);
	}

	/** Standing at a landing that still reaches something of what is left: stay put. */
	private static boolean landedAndReaching(java.util.List<Work.Cell> here) {
		return targetLand() && Plan.coveredFrom(here, target, Plan.reachExact() - LAND_SLACK,
			Nav.of(Minecraft.getInstance().level)) > 0;
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
        if (Withdraw.busy() || Unbox.running() || Screens.container() != null || AutomationControl.ownsGuidance()) return;
		BlockPos me = mc.player.blockPosition();

		// ---- OUT OF VIEW IS NOT FINISHED. `split` can only diff chunks the client has, so an empty
		// todo list means "nothing left within sight". On a 240-block island that is routinely most
		// of a design: start at the far end and every tracked design reads complete in turn, and
		// `follow all` walks the whole list announcing victory in about a second.
		//
		// Go and look instead. Flying there loads the chunks, and the next recount has real work.
		if (sp.todo().isEmpty() && sp.unseen() > 0 && sp.nearestUnseen() != null
			&& !unseenGivenUp.contains(sp.name())) {
			long t = System.currentTimeMillis();
			BlockPos look = sp.nearestUnseen();
			if (!Bounds.contains(look)) {
				// Out of view AND outside the fence: the flight would refuse it, the look watchdog
				// would strike it twice and write the design off - so write it off now and say why.
				unseenGivenUp.add(sp.name());
				mc.player.sendSystemMessage(Component.literal("[cscan] " + sp.unseen() + " cell(s) of "
					+ sp.name() + " are out of view and outside the autofly bounds - not going to look"));
				return;
			}
			if (target != null && target.equals(lookTarget)) {
				// ---- THE LOOK WATCHDOG. Neither the stall clock nor the going-nowhere clock
				// could see this phase (the target is reset every time it is re-guided), so a
				// cell in a chunk that never loads — beyond render distance from anywhere the
				// flight can get, or somewhere it cannot reach at all — was flown at for ever,
				// re-announced every few seconds. Arrived, or parked, and the count has not
				// moved: that is one strike; two and the design's unseen cells are written off
				// for this session, which is what lets `follow all` move on.
				boolean parked = Autopilot.arrivedAt(target)
					|| t - Math.max(movedAt, lookSince) > LOOK_STUCK_MS;
				if (parked) {
					lookFailures++;
					if (lookFailures >= LOOK_STRIKES) {
						unseenGivenUp.add(sp.name());
						mc.player.sendSystemMessage(Component.literal("[cscan] " + sp.unseen()
							+ " cell(s) of " + sp.name() + " sit in chunks that will not load from"
							+ " anywhere I can get to — treating them as out of reach this session"));
					} else {
						mc.player.sendSystemMessage(Component.literal("[cscan] could not get the"
							+ " chunks at " + Wand.fmt(target) + " to load — one more try"));
					}
					lookTarget = null;
					stopGuiding();
					Highlight.clear("goto");
				}
				return;
			}
			fetching = false;
			lastProgressMs = t;
			lookTarget = look;
			lookSince = t;
			Highlight.clear("goto");
			goLook(mc, look, sp.unseen() + " cells out of view");
			mc.player.sendSystemMessage(Component.literal("[cscan] nothing left in sight, but "
				+ sp.unseen() + " cells are in chunks I do not have — going to look at "
				+ Wand.fmt(look)));
			return;
		}
		if (sp.placementComplete() || (sp.todo().isEmpty() && unseenGivenUp.contains(sp.name()))) {
			doneThisSession.add(sp.name());
            if (!sp.wrong().isEmpty()) mc.player.sendSystemMessage(Component.literal("[cscan] " + sp.wrong().size() + " mismatches remain; this design is NOT complete."));
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
					if (!switchTo(mc, next)) return;
					return;
				}
				mc.player.sendSystemMessage(Component.literal(
					"[cscan] no further automatic placements; check remaining mismatches and dig lists."));
			}
			following = false;
        ActiveBuild.clear();
            ChunkScanClient.printDesign = null;
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
		if (!Printer.driving() && !placementWarned) {
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
		// A CHUNK UNLOADING IS NOT A PLACEMENT. Flying off to fetch moves hundreds of cells from
		// todo to unseen; counted as placed they inflated the session report, reset the stall
		// clock, and blinded the thrash detector at exactly the moment spots were being abandoned.
		// Only the part of a shrink that unseen does not account for is progress.
		if (lastTodo >= 0 && lastUnseen >= 0) {
			int gone = (lastTodo - sp.todo().size()) - (sp.unseen() - lastUnseen);
			if (gone > 0) {
				placedTotal += gone;
				lastProgressMs = now;
				// ---- AND BACK TO ARM'S LENGTH. The radius grew because there was nothing near;
				// something just went in, so there is. Left wide it would keep ranking the whole
				// two hundred blocks and the flying starts again.
				workRadius = Loop.nearAgain();
			}
		}
		lastTodo = sp.todo().size();
		lastUnseen = sp.unseen();
		lastReport = Printer.driving() ? Printer.drainReport() : new int[] {0, 0};
		if (lastReport[0] > 0) lastProgressMs = now;      // a placement is progress, whatever the count says
		if (++recounts % RELAX_EVERY == 0) Printer.relax();
		if (Loop.stalled(now, lastProgressMs, fetching, STALL_MS)) {
			stalls++;
			lastProgressMs = now;
			mc.player.sendSystemMessage(Component.literal("[cscan] STALLED — nothing placed in "
				+ (STALL_MS / 1000) + "s at " + (target == null ? "?" : Wand.fmt(target))
				+ ". Printer off, out of reach, or the spot cannot be built. " + sessionReport()));
			if (placedTotal == 0 && stalls == 2) {
				Boolean live = Litematica.enabled(sp.name());
				mc.player.sendSystemMessage(Component.literal("[cscan] nothing has been placed at"
					+ " all this session. " + (Boolean.FALSE.equals(live)
						? "There is no ENABLED Litematica placement called \"" + sp.name()
							+ "\" — /cscan place " + sp.name()
						: "The placement is loaded, so check that litematica-printer is switched"
							+ " on and that you are in survival with the blocks in hand.")));
			}
			abandonSpot(true);                             // it counts, and it is passed over
			return;
		}

		// ---- TOLD TO GO SOMEWHERE, AND NOT GOING. See Loop.goingNowhere: the fast clock, and the
		// only one that fires while there is still somewhere to be.
		boolean travelling = target != null
			&& me.distSqr(target) > (double) (Plan.reach() + STANDOFF) * (Plan.reach() + STANDOFF);
		// ONLY WHEN THE AUTOPILOT IS DRIVING. A player following the arrow by hand who stops to
		// read chat for three seconds is not a stuck flight, and this used to give up their spot
		// every three seconds for as long as they stood there.
		if (Autopilot.on() && Loop.goingNowhere(now, movedAt, lastProgressMs, travelling, fetching, NOWHERE_MS)) {
			mc.player.sendSystemMessage(Component.literal("[cscan] not moving and not placing at "
				+ Wand.fmt(target) + " — giving up on this spot and taking the next one"));
			abandonSpot(false);                            // counted, not struck: three seconds is a moment
			Autopilot.forget();
			return;
		}

        // Re-evaluate actual support each recount: other players/chunk loads can change it
        // without changing this design's remaining count.
        Printer.refreshPlaceability();       // one budget per look at the world
        Map<String, Integer> carrying = Work.carrying(mc.player);
        // ---- WHAT IS AROUND ME, AND ONLY THAT.
        //
        // The radius starts at arm's length and grows only when there is genuinely nothing left
        // near enough to build. See Loop.NEAR_RADIUS: what this replaced was a two-hundred block
        // area whose clusters were RANKED, so the best spot in a region the size of a small town
        // won - and having flown there, the next recount could rank something else top and send it
        // straight back. Nothing further away is considered now while there is a block at my feet,
        // so nothing CAN send the loop across the map.
        //
        // Centred on the player rather than on a remembered anchor, because "immediate" means
        // immediate: as it builds, the circle comes with it.
        // Opened in ONE step rather than by re-scanning at each rung: how far the work is is an
        // answer a single pass already contains, and re-scanning is five passes over half a million
        // cells every recount for as long as there is nothing near.
        double nearest = Loop.nearestDistance(sp.todo(), me);
        if (nearest > workRadius) workRadius = Loop.radiusReaching(nearest);
        java.util.List<Work.Cell> here = Loop.focus(sp.todo(), me, workRadius);
        if (here.isEmpty() && !sp.todo().isEmpty()) {
            // Nothing within the widest look. That is not a bigger radius, it is a different place
            // to work: go to the nearest remaining cell and start again at arm's length there.
            BlockPos moved = Loop.reanchor(sp.todo(), me);
            if (moved != null && (target == null || !target.equals(moved))) {
                workRadius = Loop.nearAgain();
                mc.player.sendSystemMessage(Component.literal(
                    "[cscan] nothing left within " + Loop.WORK_RADIUS + " — moving to "
                        + Wand.fmt(moved)));
                guide(moved, "next work");
                lastProgressMs = now;
                return;
            }
        }
        // ---- ONE COURSE AT A TIME, FROM THE BOTTOM. See Loop.LAYER_BAND.
        //
        // Walk up from the lowest course that still holds work and take the first one that yields
        // anything the printer would actually accept. Bounded, because a design with a hundred
        // empty courses under it must not cost a hundred passes in one recount - what we have after
        // the budget is a truthful answer about the courses we looked at.
        java.util.List<Work.Cell> supported = java.util.List.of();
        java.util.List<Work.Cell> frontier = java.util.List.of();
        int layerY = Integer.MIN_VALUE;
        java.util.List<Integer> courses = Loop.layers(here);
        for (int i = 0; i < courses.size() && i < Loop.LAYER_LOOKAHEAD; i++) {
            java.util.List<Work.Cell> course = Loop.layer(here, courses.get(i), Loop.LAYER_BAND);
            java.util.List<Work.Cell> ok = Work.placeableNow(mc.level, course).stream()
                .filter(c -> Rules.inLockedProfile(c.block()) && !Printer.givenUpOn(c.pos()))
                .filter(c -> !Islands.outside(ScanRunner.schematicsDir(mc), c.pos().getX(), c.pos().getZ()))
                .filter(c -> Bounds.contains(c.pos()))   // the autofly fence: not this session's work
                .toList();
            // ---- AND THEN ASK THE PRINTER, NOT AN APPROXIMATION OF IT. A solid neighbour is
            // necessary and not sufficient: the item has to yield the state the design wants, it
            // has to survive there, and the cell has to be unobstructed. See Printer.everPlaceable.
            java.util.List<Work.Cell> real = ok.stream()
                .filter(c -> Printer.everPlaceableCached(mc, c.pos(), c.block()))
                .toList();
            if (!real.isEmpty()) { supported = ok; frontier = real; layerY = courses.get(i); break; }
            supported = ok;                              // the best answer so far, if none yields
        }
        if (layerY != Integer.MIN_VALUE && layerY != workLayer) {
            if (workLayer != Integer.MIN_VALUE) mc.player.sendSystemMessage(Component.literal(
                "[cscan] course Y" + workLayer + " done — up to Y" + layerY
                    + " (" + frontier.size() + " cells)"));
            workLayer = layerY;
        }
        int refusedByState = supported.size() - frontier.size();
        java.util.List<Plan.Cluster> cl = Plan.clusters(frontier, carrying, java.util.Set.of(), java.util.Set.of(), me, spotCentre);
		spotsLeft = cl.size();

		Map<String, Storage.Container> index;
		try {
			// CACHED, because this runs every two seconds for as long as the loop does and `load` is
			// a file read and a JSON parse; and LIVE, because the index only ever grows — it is
			// written when you OPEN a container and cannot be told about one you broke. 179 of 339
			// records were dead when it was last measured, and `fetch` navigates to these.
			index = fenced(Storage.forDesign(ScanRunner.schematicsDir(mc), sp.name(), me, mc.level));
			saidIndexBroken = false;
		} catch (Exception e) {
			// SAID ONCE. A corrupt index or a missing sidecar used to make every recount report
			// "nothing indexed to fetch" with no hint that the index could not be read at all.
			index = java.util.Map.of();
			if (!saidIndexBroken) {
				saidIndexBroken = true;
				mc.player.sendSystemMessage(Component.literal("[cscan] the storage index cannot be"
					+ " read (" + e.getMessage() + ") — every fetch will report nothing to fetch"
					+ " until it can"));
			}
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
		// ---- A TOP-UP ASKS EVEN WITH NOTHING PLACEABLE IN FRONT OF IT.
		//
		// The frontier is empty at the start of most sessions - the design is across the island and
		// its chunks are not loaded, so Work.split can see none of it. Gated on a non-empty frontier
		// the fetch question was never asked, the phase came back BUILD, and the top-up was cleared
		// having done nothing. The shortfall is computed from the whole TODO, not from the frontier,
		// so there was never a reason to need one.
		boolean askedToFetch = (fetching || !canWork || topUp) && (!frontier.isEmpty() || topUp);
		if (askedToFetch) {
			// Skip chests in their cooling-off period, or the loop is guided at one it will not open.
			// WHAT GOES IN THE PACK IS DECIDED FROM WHERE THE WORK IS. See Plan.nearDemand: the
			// frontier first, then the nearest remaining cells out to about a pack's worth — not
			// the whole design's shortfall, which filled the pack with the far end's materials.
			// ...and never for a cell nothing can ever place: outside the profile, off the plot, or
			// given up on. Shopping for those is a trip to a dead end.
			java.util.List<Work.Cell> everWork = sp.todo().stream()
				.filter(c -> Rules.inLockedProfile(c.block()) && !Printer.givenUpOn(c.pos()))
				.filter(c -> !Islands.outside(ScanRunner.schematicsDir(mc), c.pos().getX(), c.pos().getZ()))
                .filter(c -> Bounds.contains(c.pos()))   // the autofly fence: not this session's work
				.toList();
			java.util.List<Work.Cell> demand = Plan.nearDemand(everWork, frontier,
				me, Work.loadCapacity(mc.player));
			targets = Plan.fetchTargets(demand, carrying, index, me,
				Withdraw.coolingOff(System.currentTimeMillis()));
			// ---- WHAT YOU ALREADY HAVE IN A BOX IS NOT WORTH A TRIP. It is not placeable either —
			// see Work.boxed — so it cannot simply be added to `carrying`; the loop would fly to a
			// spot and find it can place nothing. Told, not fetched.
			Map<String, Integer> boxes = Work.boxed(mc.player);
            for (Work.Cell c : frontier) {
                if (carrying.getOrDefault(c.item(), 0) == 0 && boxes.getOrDefault(c.item(), 0) > 0
                    && Work.room(mc.player, c.item()) > 0 && !Unbox.running()
                    && unboxWorthTrying(c.item())) {
                    String result = Unbox.start(mc, c.item(), boxes.get(c.item()));
                    noteUnboxOutcome(c.item());
                    if (saidBoxed.add(c.item())) mc.player.sendSystemMessage(Component.literal("[cscan] " + result));
                    if (Unbox.running()) return;
                }
            }
			targets = Plan.notInAPack(targets, boxes, item -> {
				// ...AND IT UNPACKS ITSELF NOW. This used to tell you to "set it down and take
				// them", which is the same shape of claim as "a client mod cannot place a block":
				// a policy written as a fact. Unboxing is placing, opening, emptying and breaking,
				// and this mod already does all four. If it cannot be done safely — nowhere to
				// stand the box that is not over the void — Unbox refuses and the message stands.
				if (!Unbox.running() && Unbox.boxWith(mc.player, item) >= 0 && unboxWorthTrying(item)) {
					String said = Unbox.start(mc, item, boxes.get(item));
					noteUnboxOutcome(item);
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
			// Fetch support material before bulk cells that cannot be placed yet.
            java.util.Set<String> frontierItems = new java.util.HashSet<>();
            for (Work.Cell c : frontier) frontierItems.add(c.item());
            targets = new java.util.ArrayList<>(targets);
            targets.sort(java.util.Comparator.comparingInt(r -> frontierItems.contains(r.item()) ? 0 : 1));
			// ---- A FETCH IS A TRIP, NOT AN EXPEDITION. See Loop.FETCH_RADIUS: ranked by shortfall
			// size alone, the biggest pile won however far away it was, and an index spanning two
			// worlds made that a flight no route can be searched for at all.
			if (Loop.allFar(targets, r -> r.where().pos(), me, Loop.FETCH_RADIUS)) {
				if (!saidFarFetch) {
					saidFarFetch = true;
					mc.player.sendSystemMessage(Component.literal("[cscan] the nearest indexed stock"
						+ " is over " + Loop.FETCH_RADIUS + " blocks away — going, but the materials"
						+ " are not where the build is."));
				}
			} else {
				saidFarFetch = false;
			}
			targets = Loop.byTrip(targets, r -> r.where().pos(), me, Loop.FETCH_RADIUS);
			want = Plan.nextLoadFetch(targets, carrying, it -> Work.room(mc.player, it));
			// STAY ON THE CHEST YOU ARE GOING TO. The nearest source is re-picked every recount,
			// so two chests at nearly the same distance took turns being the target mid-flight.
			if (want != null && fetchChest != null && !want.where().pos().equals(fetchChest)) {
				for (Plan.Restock r : targets) {
					if (r.where().pos().equals(fetchChest) && Work.room(mc.player, r.item()) > 0) {
						want = r;
						break;
					}
				}
			}
		}

		Loop.Phase phase = Loop.phase(sp.todo().size(), sp.unseen(), canWork, fetching,
			want != null, !targets.isEmpty(), topUp);
		fetching = phase == Loop.Phase.FETCH;
		if (fetching != wasFetching) lastProgressMs = now;   // a trip's clock and a build's are two clocks
		// THE TOP-UP IS OVER WHEN THERE IS NOTHING LEFT TO FETCH, which is what a full pack and a
		// fully-stocked design both look like. Ending it on a timer or on the first container would
		// be ending it on something other than the thing it is for.
		if (topUp && Loop.topUpOver(phase, askedToFetch)) {
			// ...and ONLY once it has been asked. Cleared on any non-fetch phase, a top-up ended on
			// the first recount of a session that begins away from the work - which is most of them.
			topUp = false;
			if (mc.player != null) {
				// WHICH answer it got. "Nothing to fetch" and "nowhere to fetch it from" are
				// different facts and only one of them is good news.
				mc.player.sendSystemMessage(Component.literal(targets.isEmpty()
					? "[cscan] nothing indexed to fetch — building with what you have."
						+ " /cscan bom " + sp.name() + " for what it will need"
					: "[cscan] pack loaded — building."));
			}
		}
		switch (phase) {
			case FETCH -> {
				fetchTo(mc, me, want, Plan.takeLoadAmount(want, targets.size(), Work.room(mc.player, want.item())), carrying);
				return;
			}
			case DEAD_END, PACK_FULL -> {
				lastProgressMs = now;                      // parked is not stalled: say it once, not every 90s
                if (phase == Loop.Phase.DEAD_END && !frontier.isEmpty() && ChestScan.advance(mc, sp.name(), index)) {
                    return;
                }
                if (sp.unseen() > 0 && sp.nearestUnseen() != null) {
                    goLook(mc, sp.nearestUnseen(), "look for remaining schematic support");
                    lastProgressMs = now;
                    return;
                }
				// Nothing placeable and nothing to fetch are DIFFERENT dead ends and want different
				// answers: one sends you to the store hall, the other says your pack is full of
				// something this design has no room left for.
				if (target != null || !said) {
					said = true;
					mc.player.sendSystemMessage(Component.literal(phase == Loop.Phase.DEAD_END
						? "[cscan] no usable support/material combination"
							+ (refusedByState > 0 ? " — " + refusedByState + " cell(s) the printer"
								+ " cannot place at all (state will not survive there, or the cell is"
								+ " obstructed): /cscan check " + sp.name() : "")
							+ "; check floating cells, state mismatches, island registry and indexed stock"
							+ " to fetch — /cscan bom " + sp.name()
						: "[cscan] pack is full of what you cannot place here — store something, or"
							+ " /cscan bom " + sp.name()));
				}
				stopGuiding();
				Highlight.clear("goto");
				// A DEAD END IS A REASON TO MOVE ON, not a place to spend the night. Under
				// `follow all` the design is handed back unfinished, with the reason said, and
				// the next one is taken. It is not returned to this session.
				if (followAll) {
					parked.add(sp.name());
					String other = nextDesign(mc, sp.name());
					if (other != null) {
						mc.player.sendSystemMessage(Component.literal("[cscan] " + sp.name()
							+ " handed back unfinished; moving on to " + other));
						switchTo(mc, other);
					}
				}
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
					if (!switchTo(mc, other)) return;
					return;
				}
			}
			mc.player.sendSystemMessage(Component.literal("[cscan] stopping. /cscan why for what it"
				+ " was trying, /cscan check " + sp.name() + " for cells the world disagrees about."));
			following = false;
        ActiveBuild.clear();
            ChunkScanClient.printDesign = null;
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
				lastProgressMs = now;
				if (followAll) {
					parked.add(sp.name());
					String other = nextDesign(mc, sp.name());
					if (other != null) {
						mc.player.sendSystemMessage(Component.literal("[cscan] moving on to " + other));
						switchTo(mc, other);
					}
				}
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
		if (live.isEmpty()) { stopGuiding(); spotCentre = null; return; }
		Plan.Station st = Plan.station(live, Plan.binSize(), me, stationsTried);
		if (st == null) {
			// EVERY BIN HERE HAS BEEN TRIED AND NONE TOOK A BLOCK. Retrying them from the top was
			// a loop with a message every five seconds. The spot is given up on, counted, and
			// passed over for a minute — the world may have changed by then, and if not the
			// second strike writes it off.
			mc.player.sendSystemMessage(Component.literal("[cscan] every angle on this spot has"
				+ " been tried and nothing was placed — giving up on it"));
			abandonSpot(true);
			return;
		}

		// ---- the per-station stall, measured on this station's OWN cell count
		java.util.List<Work.Cell> here = Plan.atStation(live, st, Plan.binSize());
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
			Plan.Station staying = Plan.stationOf(live, stationBin, Plan.binSize());
			if (staying != null) {
				st = staying;
				here = Plan.atStation(live, st, Plan.binSize());
			}
		}
		// WHEN WE ARE THE PRINTER, ASK THE PRINTER. The clocks below exist only because placement
		// used to be silent; with a real report a placement is progress immediately and a refusal
		// is proof immediately, where five seconds of nothing could only ever be a guess. Silence
		// still falls through to the clock, because nothing attempted is not evidence of anything.
		int[] rep = lastReport;
		// WHILE OUR OWN PRINTER DRIVES, THE REPORT IS THE EVIDENCE AND THE COUNT IS NOT. `here`
		// shrinks when a neighbour's chunk unloads or somebody else breaks a support, and each
		// such shrink read as "it is placing" and restarted the stall ladder from the top.
		Loop.Station what = Printer.driving()
			? Loop.stationFromReport(st.bin() == stationBin, arrived, here.size(), -1,
				now - stationSince, STATION_MS, stationRetry, rep[0], rep[1])
			: Loop.station(st.bin() == stationBin, arrived, here.size(), stationTodo,
				now - stationSince, STATION_MS, stationRetry);
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
				// ---- KEEP CIRCLING RATHER THAN HOLDING STATION.
				//
				// Holding still was the right answer to a different question - "do not re-approach
				// every two seconds", which was costing flights. It is the wrong answer to this one:
				// a parked body still drifts, still has to correct, and only ever reaches the faces
				// one vantage can see. The ring gives a bearing to move ON to rather than a point to
				// hold, so the correction becomes travel and the far side of the bin gets built.
				if (landedAndReaching(here)) return;      // standing, and it still reaches: stay
				if (targetLand()) {                         // landed, but what is left is out of reach
					standAt(mc, here, me, here.size() + " here");
					return;
				}
				if (landedAndReaching(here)) return;      // standing, and it still reaches: stay
				if (targetLand()) {                         // landed, but what is left is out of reach
					standAt(mc, here, me, here.size() + " here");
					return;
				}
				List<BlockPos> lap = Plan.ring(Nav.of(mc.level), here, Plan.reachExact(), STANDOFF + 2);
				if (lap.size() >= 2) {
					if (now - orbitSince >= ORBIT_MS || target == null) {
						orbitSince = now;
						orbitLeg = (orbitLeg + 1) % lap.size();
					}
					BlockPos stop = lap.get(orbitLeg);
					if (!stop.equals(target)) {
						Highlight.show("goto", Work.positions(here, 200), 0x40FF60, 900);
						guide(stop, here.size() + " here");
					}
					return;
				}
				// No ring - a cell in a slot, a bin against a ceiling. Then holding still is the
				// only thing left, and it is still better than not building.
				if (allWithinReach(me, here, Plan.reachExact() - Autopilot.ARRIVE_MIN)) return;

				// ---- MOVE AROUND THE WORK AS IT GETS BUILT. The bin is a 4-cube, so its far corner
				// is 3.5 from the centre and a standoff a few blocks out puts part of it beyond the
				// printer's reach. Re-aiming at the centroid of what is LEFT walks you round the
				// group from a new angle every time some of it goes in — which is the difference
				// between finishing a station and placing the near face of it and stopping.
				BlockPos re = Plan.bestStand(Nav.of(mc.level), here, Plan.reachExact(),
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
					BlockPos was = target;
					standAt(mc, here, me, here.size() + " here, closer");
					BlockPos close = target != null && !target.equals(was) ? target
						: Nav.standoff(Nav.of(mc.level), Plan.centroid(here), mc.player.blockPosition(), 1);
					if (close != null && !close.equals(was)) {
						if (!close.equals(target)) guide(close, here.size() + " here, closer");
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
		orbitLeg = 0;
		orbitSince = now;                            // a new bin is a new lap
		// COVERAGE, not proximity. See Plan.bestStand and Plan.groundStand: the spot is chosen by
		// how many of these cells the printer can touch from it — from the ground when the work is
		// on a floor, from the air when it is not.
		standAt(mc, here, me, st.cells() + " here, " + spot.doable() + " in this spot");
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

	/** The container index with everything outside the autofly fence removed. */
	private static Map<String, Storage.Container> fenced(Map<String, Storage.Container> index) {
		if (!Bounds.active()) return index;
		Map<String, Storage.Container> out = new java.util.LinkedHashMap<>();
		for (Map.Entry<String, Storage.Container> e : index.entrySet()) {
			if (Bounds.contains(e.getValue().pos())) out.put(e.getKey(), e.getValue());
		}
		return java.util.Collections.unmodifiableMap(out);
	}

	static void abandonSpot() {
		abandonSpot(true);
	}

	static void abandonSpot(boolean strike) {
		if (fetching) {
			// THERE IS NO SPOT DURING A FETCH. What failed is the chest: cool it, so the next
			// recount picks another source, and do not count it toward "this design is not
			// buildable" — four unreachable chests were switching designs under follow all.
			if (fetchChest != null) Withdraw.noteFailure(fetchChest);
			fetchChest = null;
			approachTried.clear();
			stopGuiding();
			Highlight.clear("goto");
			return;
		}
		// A strike against the PLACE, not just a minute of avoiding it. Two and the loop stops
		// coming back at all — a timer forgets, and a place that has beaten it twice will not be
		// different in a minute. Not for a three-second pause, though: see the NOWHERE clock.
		if (strike && spotCentre != null && Ignored.strike(spotCentre)) {
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
	/**
	 * Can the printer touch every one of these from here?
	 *
	 * <p><b>Asked the way the printer asks it.</b> This measured BLOCK to BLOCK against a FLOORED
	 * reach, while Printer.placement measures eye to face against the real one, and Plan.coveredFrom
	 * measures eye to centre - three answers to one question, and the loop was steered by the
	 * loosest of them. One entry point, so they cannot drift.
	 */
	private static boolean allWithinReach(BlockPos me, java.util.List<Work.Cell> cells, double reach) {
		return Plan.coveredFrom(cells, me, reach) >= cells.size();
	}

	/**
	 * Go and get one material, and take as much of it as the pack will hold.
	 *
	 * <p>The amount is the point. Taking one spot's shortfall is what made a fetch a round trip per
	 * wall; taking {@link Plan#takeHowMany} of it — the design's whole remaining need, capped by the
	 * room in the pack and by what the chest is believed to hold — makes it one trip per pack.
	 */
	/** The chest the current fetch is about, and the approach cells already tried for it. */
	private static BlockPos fetchChest = null;
	private static final java.util.Set<Long> approachTried = new java.util.HashSet<>();
	private static long fetchTargetSince = 0;

	/**
	 * A fetch that is neither moving nor opening for this long has stopped, whatever the flight
	 * says. Longer than the flight needs to close the last few blocks, shorter than a player would
	 * wait watching it hover.
	 */
	static final long FETCH_STUCK_MS = 6_000;

	private static void fetchTo(Minecraft mc, BlockPos me, Plan.Restock want, int take,
	                            Map<String, Integer> carrying) {
		long now = System.currentTimeMillis();
		BlockPos at = want.where().pos();
		if (!at.equals(fetchChest)) {
			fetchChest = at;
			approachTried.clear();
			fetches++;
		}
		boolean here = ContainerInteraction.openingHit(mc, at) != null;
		if (here) {
			// Wherever we are, the chest can be opened from it: do that, and do not move.
			guideExact(target != null && target.distSqr(me) <= 4 ? target : me,
				"take " + take + "x " + want.item());
			if (!Withdraw.busy() && !Withdraw.recentlyFailed(at, now)) {
				// The withdrawal stops when the PACK holds the target and it counts boxed stock
				// in the pack; a target computed from loose stock alone was already met the
				// moment a shulker held some, so it took nothing and blacklisted a full chest.
				int have = carrying.getOrDefault(want.item(), 0)
					+ Work.boxed(mc.player).getOrDefault(want.item(), 0);
				Withdraw.begin(at, want.item(), take + have);
			}
			return;
		}
		BlockPos approach = ContainerInteraction.approach(mc, at, approachTried);
		if (approach == null) {
			// ---- NO CELL TO OPEN IT FROM. Every candidate is solid, unloaded, or has been tried
			// and failed. This is the chest's problem, not the trip's: cool it off exactly as an
			// empty one is, so the next recount picks another source instead of hovering here.
			Withdraw.noteFailure(at);
			mc.player.sendSystemMessage(Component.literal("[cscan] cannot find anywhere to open "
				+ want.where().describe() + " from — skipping it for a minute"));
			stopGuiding();
			Highlight.clear("goto");
			return;
		}
		if (target == null || !target.equals(approach)) {
			fetchTargetSince = now;
			Highlight.show("goto", java.util.List.of(at), 0xFFC000, 900);
			int inBoxes = Storage.boxedCount(want.where(), want.item());
			int room = Work.room(mc.player, want.item());
			mc.player.sendSystemMessage(Component.literal("[cscan] fetch: " + take + "x "
				+ want.item() + " from " + want.where().describe() + " (" + want.available()
				+ " there, " + want.missing() + " still wanted, room for " + room + ")"
				+ (inBoxes > 0 ? "  — " + inBoxes + " of them are inside shulker boxes; it will"
					+ " take the box and you set it down" : "")));
		} else {
			// ---- THE FETCH WATCHDOG. Neither the stall clock nor the going-nowhere clock runs
			// while fetching, so a flight parked at an approach cell it cannot open the chest
			// from used to sit there for ever, silently. Arrived and still not opening, or not
			// moved for FETCH_STUCK_MS: that cell is no good, try the next angle.
			boolean parked = Autopilot.arrivedAt(approach)
				|| (now - Math.max(movedAt, fetchTargetSince) > FETCH_STUCK_MS);
			if (parked) {
				approachTried.add(approach.asLong());
				mc.player.sendSystemMessage(Component.literal("[cscan] cannot open "
					+ want.where().describe() + " from " + Wand.fmt(approach)
					+ " — trying another angle"));
				stopGuiding();                           // next recount picks the next cell
				return;
			}
		}
		guideExact(approach, "go to chest for " + take + "x " + want.item());
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
		// NEVER BACK TO A DESIGN SEEN COMPLETE OR HANDED BACK. A finished design on the far side
		// of the island has cells out of view, which reads as "has work", and two such designs
		// shuttled the loop between them all night. Real work — cells in view — beats a design
		// that merely has cells nobody has looked at. IN BUILD ORDER, as before: mcbuild settles
		// which design owes ground to which, and the order carries that.
		try {
			java.nio.file.Path dir = ScanRunner.schematicsDir(mc);
			java.util.List<String> all = Designs.tracked(dir);
			if (all == null) return null;
			all = Designs.inBuildOrder(dir, all);
			String unseenOnly = null;
			for (String name : all) {
				if (name.equals(after) || doneThisSession.contains(name) || parked.contains(name)
					|| unseenGivenUp.contains(name)) continue;
				try {
					Work.Split sp = Work.split(mc.level, dir, name, mc.player.blockPosition(), 0);
					if (!sp.todo().isEmpty()) return name;
					if (sp.unseen() > 0 && unseenOnly == null) unseenOnly = name;
					if (sp.placementComplete()) doneThisSession.add(name);
				} catch (Exception skip) {
				}
			}
			return unseenOnly;
		} catch (Exception e) {
			return null;
		}
	}

	/**
	 * Move the loop to another design, or say why it could not and park that one. Thrown from
	 * inside {@link #advance} the old way, a design whose journal could not be opened was three
	 * "recovered from" messages, seventeen silent recounts and then a dead loop.
	 */
	private static boolean switchTo(Minecraft mc, String name) {
		mc.player.sendSystemMessage(Component.literal("[cscan] moving on to " + name));
		try {
			follow(name);
		} catch (Exception e) {
			parked.add(name);
			mc.player.sendSystemMessage(Component.literal("[cscan] cannot start " + name + ": "
				+ e.getMessage() + " — skipping it"));
			return false;
		}
		followAll = true;
		remember(mc);
		return true;
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
			out.add("  built-in printer: " + (Printer.driving() ? "enabled" : "off") + "; " + Printer.report());
            out.add("  eligible storage containers on schematic island: " + Storage.forDesign(ScanRunner.schematicsDir(mc), design, mc.player.blockPosition(), mc.level).size());
            out.add("  locked skyblock-1.19; no temporary scaffolding or forced air placement");
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
        ActiveBuild.clear();
        ChestScan.reset();
        ChunkScanClient.printDesign = null;
        Printer.reset();
        Withdraw.cancel();
		design = null;
		lines = new ArrayList<>();
		following = false;
        ActiveBuild.clear();
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
		fetchChest = null;
		approachTried.clear();
		lookTarget = null;
		lookFailures = 0;
		doneThisSession.clear();
		parked.clear();
		unseenGivenUp.clear();
		splitFailures = 0;
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
					Autopilot.speed(), following ? ActiveBuild.binding(ScanRunner.schematicsDir(mc), design) : null,
					Bounds.corners(), Bounds.dimension()));
        } catch (Exception failure) {
            Session.clear(ScanRunner.schematicsDir(mc));
            if (mc.player != null) mc.player.sendSystemMessage(Component.literal(
                "[cscan] auto-resume unavailable: " + failure.getMessage()));
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
			// Swallowed, this was a loop that silently did not come back after a disconnect.
			if (mc.player != null) mc.player.sendSystemMessage(Component.literal(
				"[cscan] could not resume the saved session: " + e.getMessage()));
		}
	}

	private static void restore(Minecraft mc) {
		Session.State st = Session.load(ScanRunner.schematicsDir(mc));
		if (st == null) return;
		Autopilot.setSpeed(st.speed());
		// THE FENCE COMES BACK FIRST, and only in the dimension it was drawn in. Losing it on a
		// resume is the dangerous direction: an unattended loop that was fenced flies unfenced.
		if (st.bounds() != null && mc.level != null) {
			String dim = mc.level.dimension().identifier().toString();
			if (dim.equals(st.boundsDim())) {
				int[] b = st.bounds();
				Bounds.set(new BlockPos(b[0], b[1], b[2]), new BlockPos(b[3], b[4], b[5]), dim);
				if (mc.player != null) mc.player.sendSystemMessage(Component.literal("[cscan] " + Bounds.describe()));
			} else if (mc.player != null) {
				mc.player.sendSystemMessage(Component.literal("[cscan] the saved autofly bounds were in "
					+ st.boundsDim() + ", not here - dropped"));
			}
		}
		followAll = st.all();
        if (st.design() == null) return;
        String mismatch;
        try {
            mismatch = st.binding() == null ? "saved session has no world/input binding"
                : st.binding().mismatch(ResumeBinding.capture(mc, ScanRunner.schematicsDir(mc), st.design()));
        } catch (Exception e) { mismatch = "cannot verify saved inputs: " + e.getMessage(); }
        if (mismatch != null) {
            if (mc.player != null) mc.player.sendSystemMessage(Component.literal(
                "[cscan] resume paused: " + mismatch + ". Start the intended design explicitly to bind it."));
            return;
        }
        follow(st.design(), st.binding());
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
        follow(name, null);
    }

    private static void follow(String name, ResumeBinding expected) {
        try { ActiveBuild.start(Minecraft.getInstance(), name, expected); }
        catch (Exception failure) {
            throw new IllegalStateException("Cannot prepare build revision: " + failure.getMessage(), failure);
        }
        ChestScan.reset();
        Printer.reset();
        ChunkScanClient.printDesign = name;
        Withdraw.cancel();
        fetching = false;
        // ---- FILL THE PACK FIRST. See topUp.
        topUp = true;
        saidFarFetch = false;
        workLayer = Integer.MIN_VALUE;
        workRadius = Loop.nearAgain();
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
		fetchChest = null;
		approachTried.clear();
		lookTarget = null;
		lookFailures = 0;
		lastUnseen = -1;
		splitFailures = 0;
		avoidSpot = null;
		Ignored.clear();                              // written-off places were THIS design's spots
	}

	/** What the loop has done since `follow` started — the report for a session you were not watching. */
	static String sessionReport() {
		long mins = Math.max(1, (System.currentTimeMillis() - startedMs) / 60_000);
		return placedTotal + " placed in " + mins + " min (" + (placedTotal / mins) + "/min), "
			+ spotsDone + " spot(s) finished, " + fetches + " restock(s), " + stalls + " stall(s)";
	}

	static boolean warmingUp() { return grace > 0; }

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
        ActiveBuild.clear();
            ChunkScanClient.printDesign = null;
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
			// ONE UNREADABLE RECOUNT IS A FILE BEING WRITTEN — `mcbuild sync` mid-rewrite, a
			// half-written sidecar. It used to null the design on the first, which left
			// `following` true, the HUD blank, and nothing in chat: the loop was dead and looked
			// idle. Three in a row is a broken design; say so and stop properly.
			lines = List.of(design + ": " + e.getMessage());
			if (++splitFailures >= SPLIT_FAILURE_LIMIT) {
				if (mc.player != null) mc.player.sendSystemMessage(Component.literal("[cscan] "
					+ design + ": cannot read its work list (" + e.getMessage() + ") — stopping."
					+ " Regenerate it and /cscan follow again."));
				following = false;
				ActiveBuild.clear();
				ChunkScanClient.printDesign = null;
				stopGuiding();
				remember(mc);
				design = null;
				splitFailures = 0;
			}
			return;
		}
		splitFailures = 0;
	}
}
