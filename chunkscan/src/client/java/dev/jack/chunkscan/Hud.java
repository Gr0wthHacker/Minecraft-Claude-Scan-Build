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
	/**
	 * THE MIDDLE OF THE WORK, and it does not move because the player does.
	 *
	 * <p>Everything about where the loop builds and what it fetches was measured from {@code me},
	 * the player's position this recount. In the middle of a fetch that position is the CHEST: the
	 * shopping list was re-sized to the cells nearest the store hall, the working area re-centred
	 * on it, and when the trip ended the loop built whatever happened to be closest to the chest
	 * rather than going back to where it had been. Jack: <i>"infinitely wanders fetching small
	 * amounts of shit, finding somewhere to put it, often failing to put it, coming back,
	 * repeating"</i>. A trip leaves from the work and comes back to it; the anchor is what it
	 * comes back to.
	 *
	 * <p>Set to the nearest work on the first recount, moved to the spot being built as it drifts,
	 * moved deliberately when the area is finished or when the loop goes to look at unseen cells -
	 * and never while fetching.
	 */
	private static BlockPos workAnchor = null;
	/**
	 * The shopping list of the trip in progress. See {@link Plan#loadPlan}: made at the work when
	 * the trip starts, held until it ends, so a chest across the island cannot rewrite it.
	 */
	private static Map<String, Integer> loadPlan = null;
	/** Where the work was when {@link #loadPlan} was made, and for which design. */
	private static BlockPos loadPlanAt = null;
	private static String loadPlanFor = null;
	/** When it was made: the backstop that stops a list outliving the world it was made for. */
	private static long loadPlanMadeAt = 0;
	/** When the shopping list was last said out loud. See {@link #saidLoadPlan}. */
	private static long saidLoadPlanAt = 0;

	/**
	 * The shopping list as it was last ANNOUNCED - the item NAMES, never the counts.
	 *
	 * <p>Jack: <i>"shopping list keeps getting spammed."</i> The list is cleared at the end of
	 * every recount that is not a fetch - <i>the list belongs to the trip</i> - so whenever the loop
	 * WANTED to fetch and could not (nothing indexed holds the material, no room in the pack, every
	 * chest still cooling off) it rebuilt an identical list and announced it again, every two
	 * seconds, for as long as that stayed true. It shouted loudest exactly while achieving nothing,
	 * which is the failure mode this file already has a rule about: a message on a two-second timer
	 * is a reason to turn the loop off.
	 *
	 * <p>Keyed on the item SET and not the whole line, because the counts drift by a few every
	 * recount as the pack changes, and a signature carrying them is a signature that always differs.
	 * What a trip IS, is what it is going to fetch.
	 */
	private static String saidLoadPlan = null;

	/** How often the shopping list may be read out, however often it is remade. */
	private static final long SAY_LOAD_PLAN_MS = 60_000;
	/** How far the work may move before the trip it was planned for is a different trip. */
	private static final int LOAD_PLAN_MOVE = 24;
	/** A list older than this is about a world that has moved on. */
	private static final long LOAD_PLAN_MAX_MS = 5 * 60_000;

	/**
	 * Is the trip this shopping list was made for finished?
	 *
	 * <p>Four ways, and NOT "the phase this recount was not a fetch", which is what it used to be:
	 * the pack holds the list, the work moved somewhere else, the design changed, or the list is
	 * old enough that the world it was planned against has moved. Anything else - a chest cooling
	 * off, a full pack, a dead end - is the same trip, still unfinished, and remaking the list
	 * there is what changed the target chest mid-flight.
	 */
	private static boolean tripOver(Map<String, Integer> carrying, String design, BlockPos anchor,
	                                long now) {
		if (loadPlan == null) return false;
		if (!design.equals(loadPlanFor)) return true;
		if (Plan.covered(loadPlan, carrying)) return true;
		if (now - loadPlanMadeAt > LOAD_PLAN_MAX_MS) return true;
		return anchor != null && loadPlanAt != null
			&& anchor.distSqr(loadPlanAt) > (double) LOAD_PLAN_MOVE * LOAD_PLAN_MOVE;
	}

	/** Drop the list, and with it the chest it was flying to. */
	private static void forgetLoadPlan() {
		loadPlan = null;
		loadPlanAt = null;
		loadPlanFor = null;
		loadPlanMadeAt = 0;
	}
	/** Every item the followed design wants anywhere, cached per design. Null: could not be read. */
	private static java.util.Set<String> designItems = null;
	private static String designItemsFor = null;

	/**
	 * What the WHOLE design still wants, so a fetch can tell a leftover from a material for the
	 * far end. Read once per design - the work list is half a million cells on the park.
	 */
	private static java.util.Set<String> designItems(Minecraft mc, String name) {
		if (name.equals(designItemsFor)) return designItems;
		designItemsFor = name;
		try {
			java.util.Set<String> items = new java.util.HashSet<>();
			for (Work.Cell c : Work.load(ScanRunner.schematicsDir(mc), name)) items.add(c.item());
			designItems = items;
		} catch (Exception e) {
			designItems = null;                        // unknown needs: nothing is dumpable
		}
		return designItems;
	}
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
	/** When a foreign container screen was first seen holding the loop up; 0 when none is. */
	private static long screenWaitSince = 0;
	private static boolean screenSaid = false;
	static final long SCREEN_WAIT_SAY_MS = 60_000;
	/**
	 * ...and how long before the loop closes it itself.
	 *
	 * <p>A container screen nobody here opened parks everything - correctly, because clicking
	 * slots underneath somebody is worse than waiting. But a screen that never closes is a loop
	 * that is alive, announcing itself once a minute, and doing nothing at all until morning:
	 * a shop GUI the server opened, our own screen left behind by a failure, a menu that ate its
	 * own close. Three minutes is long past a person doing something with it.
	 */
	static final long SCREEN_STUCK_MS = 180_000;
	/** When the loop parked at a dead end with nothing else to do; 0 while it has work. */
	/**
	 * ONE MATERIAL, UNTIL THE SCHEMATIC HAS IT EVERYWHERE. `/cscan only moss_block`: every cell of
	 * any other material is not this session's work - not for the frontier, not for the shopping
	 * list, not for the printer - and the design is complete for this session when no loaded cell
	 * of the material is left and every chunk has been seen. Jack: <i>"if i type moss_block it only
	 * does that material and does it until its filled every potential place of that material on
	 * the schematic."</i> Item names, so `stone_brick_slab` covers both halves and every facing.
	 * Null means everything, which is what `follow` has always meant.
	 */
	private static java.util.Set<String> only = null;
	private static boolean onlySaid = false;

	static java.util.Set<String> only() { return only; }

	static void setOnly(java.util.Set<String> items) {
		only = items == null || items.isEmpty() ? null : java.util.Set.copyOf(items);
		onlySaid = false;
	}

	/** Is this cell this session's work under the material filter? */
	static boolean wanted(Work.Cell c) {
		return only == null || only.contains(c.item());
	}

	/** When the vicinity hold began (0: not holding), and until when it is disarmed after a stall. */
	private static long holdSince = 0, holdCoolUntil = 0;
	private static boolean holdSaid = false;
	static final long HOLD_COOL_MS = 10_000;
	private static long deadEndSince = 0;
	/**
	 * Consecutive 90-second stalls with nothing placed anywhere between them, and the count at
	 * the last one.
	 *
	 * <p>ONE STALL IS A SPOT PROBLEM and the next spot fixes it - that is what {@link
	 * #abandonSpot} is for. Several in a row with the session's total unchanged is not about any
	 * spot: the loop is in the wrong place, out of materials, or carrying a set of write-offs
	 * that has gone stale. That is a {@link Rally}.
	 */
	private static int stallsWithoutProgress = 0;
	private static int placedWhenStalled = 0;
	static final int STALLS_BEFORE_RESET = 2;
	/** Said once per redirect: the frontier course is being skipped for one I carry material for. */
	private static boolean carryFirstSaid = false;
	/** When the loop started flying back to an unloaded work anchor; 0 when it is not. */
	private static long returnSince = 0;
	/** How long a return to the work may take before the anchor is dropped and re-chosen. */
	static final long RETURN_MS = 45_000;
	/** Parked that long with nothing to do, the loop stops and says so rather than idling all night. */
	static final long DEAD_END_STOP_MS = 120_000;
	static final long LOOK_STUCK_MS = 8_000;
	static final int LOOK_STRIKES = 2;
	/** Consecutive recounts whose work list could not be read. */
	private static int splitFailures = 0;
	static final int SPLIT_FAILURE_LIMIT = 3;
	private static int lastUnseen = -1;
	/** The printer's report for this recount, drained ONCE at the top so it is never attributed twice. */
	private static int[] lastReport = {0, 0, 0};
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
	/**
	 * Out of view is not finished: go and look at the nearest unseen cell, under a watchdog.
	 *
	 * <p>ONE method for both places that look - the empty-todo case and the dead end - because the
	 * second was written without the fence check or the watchdog, and a cell in a chunk that never
	 * loads (or one the fence excludes) was flown at for ever, re-guided every recount, with every
	 * clock reset by the re-guiding. Returns true when this recount is spoken for.
	 */
	private static boolean lookForUnseen(Minecraft mc, Work.Split sp, String why) {
		if (sp.unseen() <= 0 || sp.nearestUnseen() == null || unseenGivenUp.contains(sp.name())) return false;
		long t = System.currentTimeMillis();
		BlockPos look = sp.nearestUnseen();
		if (!Bounds.contains(look)) {
			// Out of view AND outside the fence: the flight would refuse it, the watchdog would
			// strike it twice and write the design off - so write it off now and say why.
			unseenGivenUp.add(sp.name());
			mc.player.sendSystemMessage(Component.literal("[cscan] " + sp.unseen() + " cell(s) of "
				+ sp.name() + " are out of view and outside the autofly bounds - not going to look"));
			return false;
		}
		if (target != null && target.equals(lookTarget)) {
			// ---- THE LOOK WATCHDOG. Neither the stall clock nor the going-nowhere clock can see
			// this phase, so: arrived, or parked, and the count has not moved - one strike; two
			// and the design's unseen cells are written off for this session, which is what lets
			// `follow all` move on. Only while the autopilot is the one meant to be moving.
			boolean parked = Autopilot.on()
				&& (Autopilot.arrivedAt(target) || t - Math.max(movedAt, lookSince) > LOOK_STUCK_MS);
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
			return true;
		}
		fetching = false;
		forgetLoadPlan();
		lastProgressMs = t;
		lookTarget = look;
		lookSince = t;
		Highlight.clear("goto");
		goLook(mc, look, why);
		mc.player.sendSystemMessage(Component.literal("[cscan] " + why + " — going to look at "
			+ Wand.fmt(look)));
		return true;
	}

	private static void goLook(Minecraft mc, BlockPos at, String why) {
		// Going to look is a move, so the radius starts again at arm's length when we get there -
		// and the work is wherever we are going to look, or the next recount there sends us back.
		workRadius = Loop.nearAgain();
		workAnchor = at;
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
	/** A spot that went nowhere, and until when to pass over it. *//**
	 * Spots that went nowhere, each with until when to pass over it. A MAP: held as one spot, B's
	 * abandonment un-avoided A the moment it happened, and A-B-A ran until the thrash limit.
	 */
	private static final Map<BlockPos, Long> avoided = new java.util.HashMap<>();

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
		// This must stop the old leg as well as hiding its arrow. A later `guide` re-arms the
		// destination without turning autofly off, but an abandoned chest or spot owns no velocity.
		Autopilot.pauseGuidance(Minecraft.getInstance());
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
		Nav.Passable free = Bounds.within(Nav.of(mc.level));      // a stand outside the fence is refused later
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
			Bounds.within(Nav.of(Minecraft.getInstance().level))) > 0;
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
		if (Screens.container() != null && !Withdraw.busy() && !Unbox.running()) {
			// A CONTAINER SCREEN NOBODY HERE OPENED parks the loop, correctly - and used to do it
			// in silence for as long as it stayed open, for ever. Said once, then closed.
			long t = System.currentTimeMillis();
			if (screenWaitSince == 0) screenWaitSince = t;
			else if (t - screenWaitSince > SCREEN_STUCK_MS) {
				// NOBODY IS COMING. Closing it is what a person would do, it is one packet, and it
				// is the only move that gets the loop working again - see SCREEN_STUCK_MS.
				screenWaitSince = t;
				mc.player.sendSystemMessage(Component.literal("[cscan] a container screen has been"
					+ " open for " + (SCREEN_STUCK_MS / 60_000) + " minutes with the loop parked behind"
					+ " it - closing it and carrying on"));
				mc.player.closeContainer();
			}
			else if (t - screenWaitSince > SCREEN_WAIT_SAY_MS && !screenSaid) {
				screenSaid = true;
				mc.player.sendSystemMessage(Component.literal("[cscan] a container screen has been"
					+ " open for a minute - the loop is waiting for it to close (Escape). It will close"
					+ " it itself in " + ((SCREEN_STUCK_MS - SCREEN_WAIT_SAY_MS) / 60_000) + " minutes."));
			}
		} else {
			screenWaitSince = 0;
			screenSaid = false;
		}
        if (Withdraw.busy() || Unbox.running() || Screens.container() != null || AutomationControl.ownsGuidance()) return;
		BlockPos me = mc.player.blockPosition();
		// ---- HAVE WE LOST THE PLOT ENTIRELY? Not "is the work far away" - the loop flies to far
		// work all the time - but "is it somewhere no route can even be searched for". The fall
		// rescue types /is, which always works and which on an alt lands on that alt's own empty
		// island; a server restart, a hub teleport or a failed warp do the same. From there
		// nothing is wrong with the loop except that it is in the wrong world, and every clock
		// below would happily spend the night measuring it. Held over 30s so a chunk loading, or
		// a recount taken mid-teleport, is not evidence of anything.
		BlockPos anyWork = sp.nearestTodo() != null ? sp.nearestTodo() : sp.nearestUnseen();
		if (anyWork != null) {
			double away = Math.sqrt(anyWork.distSqr(me));
			if (Rally.noteDistance(away, System.currentTimeMillis())) {
				String why = "the work is " + (int) away + " blocks away - this is not where the"
					+ " build is";
				// SAY IT WHEN THE FIX IS THE SETTING. A home command that lands somewhere the work
				// is not would otherwise reset, measure the same distance, reset again - correct
				// every time and never the thing that needs changing.
				if (Rally.fruitless() >= 1) why += " (and /" + Rally.home() + " did not fix that"
					+ " last time - /cscan home <command>?)";
				if (rally(mc, why)) return;
			}
		}
		// WHAT THIS SESSION WANTS OF THE TODO. With a material filter the list can be long and hold
		// nothing to do; every "is there work" question below asks this count, not the list's size.
		int wantedTodo = only == null ? sp.todoTotal() : (int) sp.todo().stream().filter(Hud::wanted).count();
		if (only != null && !onlySaid) {
			onlySaid = true;
			mc.player.sendSystemMessage(Component.literal("[cscan] only " + String.join(", ", only)
				+ ": " + wantedTodo + " cell(s) of it to place in loaded chunks, " + sp.unseen()
				+ " cells of the design out of view. /cscan only off to place everything."));
		}
		if (lookTarget != null && wantedTodo > 0) {
			// THE LOOK WORKED: the chunks loaded and there is work in them. Forget the look now, or
			// its strikes accumulate for the whole session and its start time reads as a 90s stall
			// the moment the first recount with work in it arrives.
			lookTarget = null;
			lookFailures = 0;
			lastProgressMs = System.currentTimeMillis();
		}

		// ---- OUT OF VIEW IS NOT FINISHED. `split` can only diff chunks the client has, so an empty
		// todo list means "nothing left within sight". On a 240-block island that is routinely most
		// of a design: start at the far end and every tracked design reads complete in turn, and
		// `follow all` walks the whole list announcing victory in about a second.
		//
		// Go and look instead. Flying there loads the chunks, and the next recount has real work.
		// ...but NOT in the middle of a trip. The work is out of view because the trip went to the
		// chest and its chunks unloaded on the way; looking at it now, then coming back to finish
		// the trip, is the ping-pong. See Loop.phase, which continues a trip with a target.
		// ...and NOT while the work is merely out of view because a trip took us away from it.
		// goLook moves the anchor to the unseen cell nearest the PLAYER - which, standing at the
		// store hall, is the store hall's neighbourhood - and the shopping list sized at the work
		// then came back somewhere else. The back-to-the-work block below owns this case.
		if (wantedTodo == 0 && !(fetching && loadPlan != null)
			&& !(workAnchor != null && !mc.level.isLoaded(workAnchor))
			&& lookForUnseen(mc, sp, sp.unseen() + " cells out of view")) return;
		if (only != null && wantedTodo == 0 && (sp.unseen() == 0 || unseenGivenUp.contains(sp.name()))) {
			// ---- THE FILTER IS DONE. Every loaded cell of the material is placed and every chunk
			// has been seen; what is left of the design is other materials, which this session
			// was told not to touch. Said, and stopped - not "complete", because it is not.
			mc.player.sendSystemMessage(Component.literal("[cscan] only " + String.join(", ", only)
				+ ": nothing of it left to place in " + sp.name() + ". " + sp.todoTotal()
				+ " cell(s) of other materials remain. " + sessionReport()
				+ "  /cscan only off, then /cscan follow " + sp.name() + " for the rest."));
			following = false;
			ActiveBuild.clear();
			ChunkScanClient.printDesign = null;
			stopGuiding();
			Highlight.clear("goto");
			remember(mc);
			return;
		}
		if (sp.placementComplete() || (sp.todoTotal() == 0 && unseenGivenUp.contains(sp.name()))) {
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
						+ sessionReport() + dig + sp.manualSummary()));
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
					"[cscan] no further automatic placements; check deferred actions, mismatches and dig lists."));
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
		if (!deviationsSaid && !sp.wrong().isEmpty() && sp.todoTotal() < sp.wrong().size()) {
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
		lastReport = Printer.driving() ? Printer.drainReport() : new int[] {0, 0, 0};
		int placedNow;
		if (Printer.driving()) {
			// OUR OWN PRINTER REPORTS, and that is the only count a chunk cannot fake: a chunk that
			// loads with its cells already BUILT moves them from unseen to built with todo
			// untouched, and the inference below read exactly that as placing - inflating the
			// report, resetting the stall clock and blinding the thrash detector on the way in.
			placedNow = lastReport[0];
		} else if (lastTodo >= 0 && lastUnseen >= 0 && sp.unseen() == lastUnseen) {
			// Inferred, for litematica-printer, and only while no chunk moved: a recount in which
			// unseen changed at all is not evidence about placement either way.
			placedNow = Math.max(0, lastTodo - sp.todoTotal());
		} else {
			placedNow = 0;
		}
		if (placedNow > 0) {
			placedTotal += placedNow;
			lastProgressMs = now;
			// ---- AND BACK TO ARM'S LENGTH. The radius grew because there was nothing near;
			// something just went in, so there is. Left wide it would keep ranking the whole
			// two hundred blocks and the flying starts again.
			workRadius = Loop.nearAgain();
		}
		lastTodo = sp.todoTotal();
		lastUnseen = sp.unseen();
		if (++recounts % RELAX_EVERY == 0) Printer.relax();
		if (Loop.stalled(now, lastProgressMs, fetching, STALL_MS)) {
			stalls++;
			lastProgressMs = now;
			mc.player.sendSystemMessage(Component.literal("[cscan] STALLED — nothing placed in "
				+ (STALL_MS / 1000) + "s at " + (target == null ? "?" : Wand.fmt(target))
				// ...AND NAME THE GATE RATHER THAN LISTING THE POSSIBILITIES. "Printer off, out of
				// reach, or the spot cannot be built" is three guesses; the tick knows which.
				+ ". " + (ChunkScanClient.printerIdle != null
					? "The printer is not placing: " + ChunkScanClient.printerIdle + ". "
					: "Out of reach, or the spot cannot be built. ")
				+ sessionReport()));
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
			// ---- A STALL THAT REPEATS IS NOT A SPOT PROBLEM. One is an awkward corner and the
			// next spot fixes it; three minutes of them with nothing placed anywhere is the loop
			// being in the wrong place, out of materials, or holding a set of opinions that have
			// gone stale. Reset rather than abandoning a fourth spot.
			stallsWithoutProgress = placedTotal == placedWhenStalled ? stallsWithoutProgress + 1 : 1;
			placedWhenStalled = placedTotal;
			if (stallsWithoutProgress >= STALLS_BEFORE_RESET
				&& rally(mc, stallsWithoutProgress + " stalls in a row with nothing placed")) {
				stallsWithoutProgress = 0;
			}
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
        // ---- WHAT THIS SESSION MAY WORK ON, decided ONCE. Off the plot, outside the fence, out
        // of the locked profile or given up on: none of it is this session's work, and every
        // question below - how far is the nearest cell, which course is lowest, where to move to -
        // has to be asked of the same list. Asked of the whole todo, the eight-course lookahead
        // was spent on courses the fence excludes and the loop moved to cells it may not reach.
        //
        // HOISTED, AND CHEAPEST FIRST. This runs over EVERY cell of the design - `Park Complete`
        // is 541,764 of them - and it used to resolve the schematics directory, normalise an
        // absolute path, take two class monitors and allocate a stream PER CELL, on the same tick
        // that prints the chat line. That is why the lag and the message arrive together. The
        // directory and the plot gate are one answer for the whole pass; the predicates are
        // ordered by what they cost, so the free ones (a fence that is not set, a material filter
        // that is not set) decide most cells before anything expensive is asked.
        java.nio.file.Path schemDir = ScanRunner.schematicsDir(mc);
        Islands.Gate plot = Islands.gate(schemDir);
        java.util.List<Work.Cell> eligible = Perf.time("loop filter", () -> sp.todo().stream()
            .filter(c -> Bounds.contains(c.pos()))        // the autofly fence: free when none is set
            .filter(Hud::wanted)                          // /cscan only <material>
            .filter(c -> !plot.outside(c.pos().getX(), c.pos().getZ()))
            .filter(c -> Rules.inLockedProfile(c.block()) && !Printer.givenUpOn(c.pos()))
            .toList());
        // ---- STAY WHERE THE WORK IS. See Loop.holdHere. Before any question about anchors, courses,
        // spots or stations: is there anything placeable, that I am carrying, within reach of where
        // I am? Then this is the place, and the only thing to do is let the printer place it.
        java.util.List<Work.Cell> inReach = Work.placeableNow(mc.level, Loop.focus(eligible, me, Loop.VICINITY)).stream()
            .filter(c -> carrying.getOrDefault(c.item(), 0) > 0)
            .filter(c -> Printer.everPlaceableCached(mc, c.pos(), c.block()))
            .toList();
        if (inReach.isEmpty()) {
            holdSince = 0;
            holdSaid = false;
        } else if (!fetching && Loop.holdHere(inReach.size(), placedNow, lastReport[2], now,
                holdSince, holdCoolUntil, STATION_MS)) {
            if (placedNow > 0 || lastReport[2] > 0 || holdSince == 0) holdSince = now;
            if (target == null || target.distSqr(me) > 4) {
                // HOLD HERE, as a target: the body's own cell. The flight arrives at once and
                // keeps its clearance - or stays landed if it landed - and the autopilot does not
                // read "no target" as idle and say so every time a hold begins.
                Highlight.clear("goto");
                guide(me, "placing here", mc.player.onGround() ? Mode.LAND : Mode.NEAR);
            }
            Highlight.show("goto", Work.positions(inReach, 200), 0x40FF60, 900);
            if (!holdSaid) {
                holdSaid = true;
                mc.player.sendSystemMessage(Component.literal("[cscan] " + inReach.size()
                    + " cell(s) placeable from right here — staying until they are in"));
            }
            workAnchor = me;                         // the work is where I am
            // ...AND SAY SO TO THE JOB, or the hold forbids its own printer. BuildJob.decide lives
            // past the end of this method, so returning here left the phase as whatever the LAST
            // recount set - PARKED after a dead end or a look - and AutomationControl.enter(PRINT)
            // refuses unless the phase is BUILD. The loop announced it was staying until the
            // cells were in, placed nothing because it had forbidden itself, and blamed the
            // world five seconds later.
            BuildJob.decide(Loop.Phase.BUILD);
            return;
        } else if (!fetching && holdSince != 0 && now - holdSince > STATION_MS) {
            // Held, in reach, and nothing went in: the printer is refusing what I can see. Let the
            // station logic move in closer or find another angle, and do not re-arm the hold for a
            // while or it wins the next recount straight back.
            holdCoolUntil = now + HOLD_COOL_MS;
            holdSince = 0;
            holdSaid = false;
            mc.player.sendSystemMessage(Component.literal("[cscan] " + inReach.size()
                + " cell(s) in reach but nothing placed for " + (STATION_MS / 1000) + "s — moving"));
        }
        // ---- AROUND THE WORK, NOT AROUND ME. See workAnchor: the first recount anchors on the
        // nearest work to wherever the loop started; after that the anchor is the spot being
        // built, and a fetch does not move it.
        if (workAnchor == null && !eligible.isEmpty()) workAnchor = Loop.reanchor(eligible, me);
        BlockPos anchor = workAnchor != null ? workAnchor : me;
        double nearest = Loop.nearestDistance(eligible, anchor);
        // ...but never while the anchor's own chunks are unloaded: the only cells "near" then are
        // whatever happens to be loaded round the CHEST, and a radius grown to reach them forms a
        // spot there and moves the anchor to it. The trip goes back first.
        if (nearest > workRadius && (workAnchor == null || mc.level.isLoaded(workAnchor))) {
            workRadius = Loop.radiusReaching(nearest);
        }
        java.util.List<Work.Cell> here = Loop.focus(eligible, anchor, workRadius);
        if (here.isEmpty() && !fetching) {
            if (workAnchor != null && !mc.level.isLoaded(workAnchor) && sp.unseen() > 0) {
                // ---- BACK TO THE WORK. The area has nothing loaded in it because we are not
                // there - a trip just ended, or a look did. Going back loads it; deciding
                // anything from here decides it about the wrong place.
                if (target == null || !target.equals(workAnchor)) {
                    workRadius = Loop.nearAgain();
                    returnSince = now;
                    mc.player.sendSystemMessage(Component.literal("[cscan] back to the work at "
                        + Wand.fmt(workAnchor)));
                    guide(workAnchor, "back to the work");
                    lastProgressMs = now;
                } else if (Loop.returnGivenUp(now, returnSince, RETURN_MS, Ignored.has(workAnchor))) {
                    // ---- AND A RETURN THAT NEVER ARRIVES IS GIVEN UP. The anchor was the one
                    // destination with no watchdog, no strike and no avoid: an anchor whose chunk
                    // never loads (no route, out of range, autofly off) was guided to every two
                    // seconds for ever, and the 90s stall then struck nothing because there is no
                    // spot. Re-anchor on whatever is loaded near me instead.
                    mc.player.sendSystemMessage(Component.literal("[cscan] the work at "
                        + Wand.fmt(workAnchor) + " will not load from here - re-anchoring on the"
                        + " nearest work to me"));
                    workAnchor = null;
                    returnSince = 0;
                    stopGuiding();
                    Highlight.clear("goto");
                    lastProgressMs = now;
                }
                return;
            }
            if (!eligible.isEmpty() || sp.nearestTodo() != null) {
                // Nothing within the widest look of an area we can see. That is not a bigger
                // radius, it is a different place to work: the nearest remaining cell to the
                // area just finished, so the work walks across the design rather than jumping
                // about it, and the anchor moves with it.
                //
                // ...AND PAST THE DETAIL RADIUS THE SPLIT ITSELF ANSWERS IT. The listed cells stop
                // at the working radius now, so an area genuinely finished leaves `eligible` empty
                // rather than merely distant - and without this fallback that reads as a dead end
                // on a design with plenty left.
                BlockPos moved = eligible.isEmpty() ? sp.nearestTodo() : Loop.reanchor(eligible, anchor);
                if (moved != null) {
                    workAnchor = moved;
                    workRadius = Loop.nearAgain();
                    if (target == null || !target.equals(moved)) {
                        mc.player.sendSystemMessage(Component.literal(
                            "[cscan] nothing left within " + Loop.WORK_RADIUS + " — moving to "
                                + Wand.fmt(moved)));
                        guide(moved, "next work");
                        lastProgressMs = now;
                    }
                    return;
                }
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
        // ---- THE COURSE IS STICKY. See Loop.courseOrder.
        //
        // Off Jack's log, one recount apart, for minutes: "course Y203 done - up to Y202 (56)",
        // "course Y202 done - up to Y203 (85)", "course Y203 done - up to Y202 (50)". Nothing was
        // finished either time. The frontier is the lowest course of `here`, `here` is a window
        // round the ANCHOR, and the anchor is the spot being built - which is derived from the
        // frontier. That circle has no damping in it: the body moves, the window moves, the lowest
        // course changes, a new spot is chosen, and it flies there. Reported as: it flies back and
        // forth.
        //
        // Spots and stations have both had hysteresis for months. The course never did.
        java.util.List<Integer> courses = Loop.courseOrder(Loop.layers(here), workLayer);
        // EVERY COURSE, not the first eight. Capped, eight consecutive courses whose cells the
        // printer refuses (lanterns waiting on posts, vines, state-refused stairs) emptied the
        // frontier and read as a DEAD_END with real work one course higher - and on a design with
        // unseen cells a dead end goes to LOOK somewhere else, which is the wandering. The cost is
        // bounded by the placeability budget, not by the design.
        for (int i = 0; i < courses.size(); i++) {
            java.util.List<Work.Cell> course = Loop.layer(here, courses.get(i), Loop.LAYER_BAND);
            java.util.List<Work.Cell> ok = Work.placeableNow(mc.level, course).stream()
                .filter(c -> Bounds.contains(c.pos()))   // the autofly fence: not this session's work
                .filter(Hud::wanted)
                .filter(c -> !plot.outside(c.pos().getX(), c.pos().getZ()))
                .filter(c -> Rules.inLockedProfile(c.block()) && !Printer.givenUpOn(c.pos()))
                .toList();
            // ---- AND THEN ASK THE PRINTER, NOT AN APPROXIMATION OF IT. A solid neighbour is
            // necessary and not sufficient: the item has to yield the state the design wants, it
            // has to survive there, and the cell has to be unobstructed. See Printer.everPlaceable.
            // ---- NEAREST FIRST, AND ONLY AS MANY AS IT TAKES. See Loop.FRONTIER_ENOUGH: this
            // question is the most expensive one the loop asks, and it was asked of every cell of
            // the course in whatever order they came - so inside a wide working radius the budget
            // was spent a hundred blocks away and the work underfoot was found by accident.
            java.util.List<Work.Cell> real = ok.stream()
                .sorted(java.util.Comparator.comparingDouble(c -> c.pos().distSqr(me)))
                .filter(c -> Printer.everPlaceableCached(mc, c.pos(), c.block()))
                .limit(Loop.FRONTIER_ENOUGH)
                .toList();
            if (!real.isEmpty()) { supported = ok; frontier = real; layerY = courses.get(i); break; }
            supported = ok;                              // the best answer so far, if none yields
        }
        if (layerY != Integer.MIN_VALUE && layerY != workLayer) {
            // ...and it is only "done" when it really is: with the course sticky, leaving one means
            // it yielded nothing this recount, which is the only honest use of the word.
            if (workLayer != Integer.MIN_VALUE) mc.player.sendSystemMessage(Component.literal(
                "[cscan] course Y" + workLayer + " has nothing placeable left — moving to Y" + layerY
                    + " (" + frontier.size() + " cells)"));
            workLayer = layerY;
        }
        // ONLY MEANINGFUL WHEN THE FRONTIER IS EMPTY, now that the frontier is capped: with cells
        // found, the difference is mostly cells nobody looked at rather than cells refused.
        int refusedByState = frontier.isEmpty() ? supported.size() : 0;
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

		// ---- BUILD WHAT YOU ARE CARRYING FIRST. See Loop.WORK_LOAD. Three cases, in order:
		//   the frontier course has cells for a load I carry  -> no top-up; build
		//   a higher course near the anchor has them          -> that course is the frontier
		//   they are somewhere else in the loaded design      -> go there, not to a chest
		// Only when none of that holds is a chest worth opening.
		if (!fetching) {
			java.util.List<Work.Cell> onFrontier = Loop.carriedWork(carrying, frontier, Loop.WORK_LOAD);
			if (!onFrontier.isEmpty() && topUp) {
				topUp = false;
				mc.player.sendSystemMessage(Component.literal("[cscan] carrying "
					+ Loop.describeCarried(carrying, onFrontier, Loop.WORK_LOAD)
					+ " — building with it first, no top-up trip"));
			}
			if (Loop.buildWhatYouCarry(canWork, fetching, true)) {
				// A WORKING LOAD FIRST, AND THEN ANY LOAD AT ALL. WORK_LOAD is four stacks and it
				// is the right threshold for "do not go shopping, you already have plenty"; it is
				// the wrong one for "am I stuck". A trip that came back with ONE stack of cobbled
				// deepslate, for a design with 545 placeable cells of it, found no cell on the
				// frontier course holding four stacks, declared the pack full of what it cannot
				// place, and parked there until the two-minute reset. Anything I carry that has a
				// face to click somewhere in the loaded area is a reason to go there rather than
				// to stop - build-before-shop, at whatever quantity the trip actually brought.
				int load = Loop.WORK_LOAD;
				java.util.List<Work.Cell> mine = carriedPlaceable(mc, carrying, eligible, load, anchor);
				if (mine.isEmpty()) {
					load = 1;
					mine = carriedPlaceable(mc, carrying, eligible, load, anchor);
				}
				final int carried = load;
				java.util.List<Work.Cell> near = Loop.focus(mine, anchor, workRadius);
				if (!near.isEmpty()) {
					// A HIGHER COURSE WITH WHAT I HOLD BEATS A TRIP FOR THE LOWER ONE. Every cell
					// here has a face to click now, so it is buildable; the course rule yields.
					frontier = near;
					cl = Plan.clusters(frontier, carrying, java.util.Set.of(), java.util.Set.of(), me, spotCentre);
					spotsLeft = cl.size();
					canWork = Plan.anyDoable(cl);
					topUp = false;
					if (!carryFirstSaid) {
						carryFirstSaid = true;
						mc.player.sendSystemMessage(Component.literal("[cscan] course Y" + workLayer
							+ " has nothing I carry — placing " + Loop.describeCarried(carrying, near, carried)
							+ " on the courses above it first (" + near.size() + " cells)"));
					}
				} else if (!mine.isEmpty()) {
					BlockPos moved = Loop.reanchor(mine, anchor);
					if (moved != null) {
						topUp = false;
						workAnchor = moved;
						workRadius = Loop.nearAgain();
						if (target == null || !target.equals(moved)) {
							mc.player.sendSystemMessage(Component.literal("[cscan] carrying "
								+ Loop.describeCarried(carrying, mine, carried) + " — placing that"
								+ " before any trip: " + mine.size() + " cells, nearest at " + Wand.fmt(moved)));
							guide(moved, "placing what I carry");
							lastProgressMs = now;
						}
						return;
					}
				}
			} else if (canWork) {
				carryFirstSaid = false;
			}
		}

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
		// ---- THE PACK IS CHECKED, AND WHAT IT HOLDS FOR NO REASON COUNTS AS ROOM. See
		// Work.dumpable: a fetch puts those stacks into the chest before it takes anything, so
		// the room a trip can bring back is the empty slots PLUS the ones it will empty there.
		java.util.Set<String> needed = designItems(mc, sp.name());
		final int dumpFree = Work.dumpableSlots(mc.player, needed) * 64;
		Plan.Room room = it -> Work.room(mc.player, it) + dumpFree;
		// A trip that has a shopping list keeps asking until the list is covered - wherever the
		// player is and whether or not anything is placeable there.
		// ---- ARRIVE BEFORE DECIDING. Jack: "it doesnt make it to destination and goes back to get
		// more materials". A spot is chosen because it had work we carry; two seconds later the body
		// is still in the air, the window has moved with it, `canWork` reads false about a place we
		// have not reached - and the loop turns round for a chest. It is the same rule the trip
		// already has in the other direction ("the trip is over and the work is out of view: go
		// back, and decide there"), which was never applied on the way OUT.
		//
		// The three-second going-nowhere clock and the ninety-second stall both still run while
		// travelling, so a spot that cannot be reached is still given up on; what cannot happen any
		// more is abandoning one that simply has not been reached yet.
		boolean headingToWork = travelling && !fetching && !topUp && loadPlan == null;
		boolean askedToFetch = (fetching || !canWork || topUp) && !headingToWork
			&& (!frontier.isEmpty() || topUp || loadPlan != null);
		if (askedToFetch) {
			if (loadPlan == null) {
				// ---- THE SHOPPING LIST IS MADE HERE, AT THE WORK, ONCE. See Plan.loadPlan: the
				// frontier first, then the area's next courses, up to what the pack can hold -
				// and held until the trip ends, so a chest across the island cannot re-size it
				// to the cells nearest the chest. ...and never for a cell nothing can ever place:
				// outside the profile, off the plot, or given up on.
				java.util.List<Work.Cell> area = here.isEmpty() ? eligible : here;
				// ...LED BY WHAT CAN GO IN TODAY, on every course near the anchor, not only the
				// frontier course. See Plan.usable: ranked by placeable cells the list fills the
				// pack with the materials the build can take, so the trip that comes back places
				// the most and opens the most - the walls before anyone fetches the roof.
				java.util.List<Work.Cell> usableNow = Work.placeableNow(mc.level, area).stream()
					.filter(c -> Printer.everPlaceableCached(mc, c.pos(), c.block())).toList();
				// ...AND LED BY WHAT THERE IS SOMEWHERE TO GET. See Plan.loadPlan: a list of six
				// materials the index has none of is a trip that cannot be made, and the loop
				// reads that as a dead end rather than as a bad list - three resets in a row,
				// nothing placed in five minutes, with tens of thousands of stone brick, basalt
				// and moss sitting in chests for cells that were placeable the whole time.
				java.util.Set<String> stocked = Storage.stocked(index);
				loadPlan = Plan.loadPlan(area, usableNow.isEmpty() ? frontier : usableNow, anchor,
					Work.loadCapacity(mc.player) + dumpFree, stocked::contains);
				Map<String, Integer> away = Work.dumpable(mc.player, needed);
				// SAID WHEN THE TRIP CHANGES, NOT WHEN THE LIST IS REBUILT. See saidLoadPlan.
				loadPlanAt = anchor;
				loadPlanFor = sp.name();
				loadPlanMadeAt = now;
				String signature = new java.util.TreeSet<>(loadPlan.keySet()).toString();
				// SAID AT MOST ONCE A LIST, AND NEVER MORE THAN ONCE A MINUTE. The signature alone
				// was not enough: a list that legitimately changes as one material is covered and
				// the next comes into range still has nothing to gain from being read out every
				// recount. A cap in seconds cannot be defeated by anything a future list does.
				if (!signature.equals(saidLoadPlan) && now - saidLoadPlanAt >= SAY_LOAD_PLAN_MS) {
					saidLoadPlan = signature;
					saidLoadPlanAt = now;
					mc.player.sendSystemMessage(Component.literal("[cscan] shopping list for "
						+ Plan.cells(loadPlan) + " cells around " + Wand.fmt(anchor) + ": "
						+ Plan.describe(loadPlan)
						+ (away.isEmpty() ? "" : "  (putting away " + Plan.describe(away) + ")")));
				}
			}
			// Skip chests in their cooling-off period, or the loop is guided at one it will not open.
			targets = Plan.shortfalls(loadPlan, carrying, index, me,
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
			// ...AND PAST TWICE THE ROUTER'S RANGE IT IS NOT A TRIP. See Loop.TRIP_LIMIT: no route
			// can be searched for it, so the flight goes DIRECT and keeps going - and because the
			// body is moving the whole time, no clock and no rung of the ladder can see it. Dropped
			// and counted rather than sorted to the back.
			int before = targets.size();
			targets = Loop.withinTrip(targets, r -> r.where().pos(), me, Loop.TRIP_LIMIT);
			if (targets.size() < before && !saidFarFetch) {
				saidFarFetch = true;
				mc.player.sendSystemMessage(Component.literal("[cscan] " + (before - targets.size())
					+ " indexed source(s) are over " + Loop.TRIP_LIMIT + " blocks away - too far for any"
					+ " route to be found, so not going. /cscan prune if they are gone."));
			}
			targets = Loop.byTrip(targets, r -> r.where().pos(), me, Loop.FETCH_RADIUS);
			want = Plan.nextLoadFetch(targets, carrying, room);
			// STAY ON THE CHEST YOU ARE GOING TO. The nearest source is re-picked every recount,
			// so two chests at nearly the same distance took turns being the target mid-flight.
			if (want != null && fetchChest != null && !want.where().pos().equals(fetchChest)) {
				for (Plan.Restock r : targets) {
					if (r.where().pos().equals(fetchChest) && room.of(r.item()) > 0) {
						want = r;
						break;
					}
				}
			}
		}

		Loop.Phase phase = Loop.phase(wantedTodo, sp.unseen(), canWork, fetching,
			want != null, !targets.isEmpty(), topUp);
		BuildJob.decide(phase);
		fetching = phase == Loop.Phase.FETCH;
		if (fetching != wasFetching) lastProgressMs = now;   // a trip's clock and a build's are two clocks
		// ---- THE LIST BELONGS TO THE TRIP, AND A TRIP IS NOT ONE RECOUNT.
		//
		// Cleared on any phase that was not a FETCH, it was thrown away and remade every two
		// seconds in exactly the states where the loop is oscillating - PACK_FULL, DEAD_END, a
		// chest still cooling off - and a remade list is a different list: a different target
		// chest, a flight redirected before it arrives, and the announcement again. Jack:
		// "shopping list is getting constantly spammed and stopping all progress". Both halves
		// of that are this one line.
		//
		// It is kept until the trip is genuinely over: the pack holds it, the work has moved on,
		// the design changed, or it is old enough to be about a world that has moved. See
		// tripOver.
		// ...and a trip you have decided not to make is over too: the phase came back BUILD,
		// which means there is something in front of you to place.
		if (!fetching && canWork) forgetLoadPlan();
		else if (tripOver(carrying, sp.name(), anchor, now)) forgetLoadPlan();
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
		if (wasFetching && !fetching && workAnchor != null && !mc.level.isLoaded(workAnchor)) {
			// ---- THE TRIP IS OVER AND THE WORK IS OUT OF VIEW. Whatever the phase says from here
			// it says about the chest's surroundings, not the work's: "nothing placeable" at a
			// store hall is not a dead end. Go back, and decide there.
			workRadius = Loop.nearAgain();
			returnSince = now;
			mc.player.sendSystemMessage(Component.literal("[cscan] pack loaded — back to the work at "
				+ Wand.fmt(workAnchor)));
			guide(workAnchor, "back to the work");
			lastProgressMs = now;
			return;
		}
		switch (phase) {
			case FETCH -> {
				java.util.Set<String> dump = Work.dumpable(mc.player, needed).keySet();
				fetchTo(mc, me, want, Plan.takeHowMany(want, room.of(want.item())), carrying, dump);
				return;
			}
			case DEAD_END, PACK_FULL -> {
				lastProgressMs = now;                      // parked is not stalled: say it once, not every 90s
                if (phase == Loop.Phase.DEAD_END && !frontier.isEmpty() && ChestScan.advance(mc, sp.name(), index)) {
                    return;
                }
                if (lookForUnseen(mc, sp, "look for remaining schematic support")) return;
				// Nothing placeable and nothing to fetch are DIFFERENT dead ends and want different
				// answers: one sends you to the store hall, the other says your pack is full of
				// something this design has no room left for.
				if (target != null || !said) {
					said = true;
					// ---- SAY WHERE IT LOOKED. Jack: "it doesnt say it has placeable stuff but when
					// loaded it does say stuff is placeable". Both numbers are true and they answer
					// different questions - the start report is the WHOLE design at radius 0, this is one
					// course of a window round the anchor - and worded as a fact about the design it reads
					// as the loop contradicting itself two lines apart.
					mc.player.sendSystemMessage(Component.literal(phase == Loop.Phase.DEAD_END
						? "[cscan] nothing I can place within " + workRadius + " of " + Wand.fmt(anchor)
							+ " on course Y" + workLayer + " — the design has more elsewhere"
							+ (refusedByState > 0 ? "; " + refusedByState + " cell(s) here the printer"
								+ " cannot place at all (state will not survive there, or the cell is"
								+ " obstructed): /cscan check " + sp.name() : "")
							+ ". /cscan why for the reason, /cscan bom " + sp.name() + " for materials"
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
						return;
					}
				}
				// NOTHING ELSE TO DO, AND NOWHERE TO GO. Two minutes of that is a parked loop, and a
				// parked loop that stays "following" all night is the failure this file keeps
				// writing rules about. Long enough for a hand to break the one block in the way.
				if (deadEndSince == 0) deadEndSince = now;
				// ---- PARKED LONG ENOUGH IS A RESET, NOT A STOP. This used to end the session: two
				// minutes with nothing placeable and nowhere to go, and the loop switched itself off
				// until somebody typed. Every reason a dead end can have - the wrong island, an empty
				// pack, a chest list full of cooling-off entries, cells written off from somewhere we
				// have since left - is a reason `Rally` addresses directly, and the ones it cannot
				// cost a teleport and a look. The backoff is what stops this becoming a hot loop:
				// fruitless resets double their interval to five minutes and stay there.
				if (now - deadEndSince > DEAD_END_STOP_MS
						&& rally(mc, "parked at a dead end for " + (DEAD_END_STOP_MS / 60_000)
							+ " minutes with nothing else to do")) {
					deadEndSince = 0;
				}
				return;
			}
			default -> { }
		}
		said = false;
		deadEndSince = 0;

		// ---- SPOT HYSTERESIS. Two levels of it now, and they are different questions: this one is
		// "am I still working the same region", and `stand` below is "where in it do I float".
		//
		// Matched by PROXIMITY, not by equality: a cluster's centre is a centroid of the cells still
		// to do, so it drifts a block or two every time you place some. Comparing it exactly would
		// call every recount a new spot, reset the stations and re-announce, twice a second.
		// ---- THRASHING. Abandon spot A, take B, abandon B, take A again when its minute expires,
		// for ever: every decision correct, the sequence a machine going nowhere. The evidence is
		// the pair — several spots given up on, and nothing placed while it happened.
		if (Loop.thrashing(spotsAbandoned, placedTotal - placedWhenAbandoned, THRASH_LIMIT, THRASH_TRICKLE)) {
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
			// ...AND THE ANSWER IS A RESET, NOT A STOP. Nothing about a design that thrashed from
			// here says it cannot be built from somewhere else, with a full pack, without this
			// session's accumulated write-offs. If the reset is still cooling off, carry on and
			// let the next four abandonments ask again.
			if (!rally(mc, THRASH_LIMIT + " spots given up on with nothing placed")) {
				mc.player.sendSystemMessage(Component.literal("[cscan] /cscan why for what it was"
					+ " trying, /cscan check " + sp.name() + " for cells the world disagrees about."));
			}
			return;
		}

		Plan.Cluster next = Loop.sameSpot(spotCentre, cl, Plan.MAX_RADIUS);
		if (next == null) {
			// PASS OVER THE SPOT THAT JUST WENT NOWHERE. Without this the next recount picks the
			// same region — it is still the best one — flies at the same wall, and sticks again.
			next = null;
			for (Plan.Cluster c : cl) {
				// written off: never again this session
				if (Ignored.has(c.centre())) continue;
				// ...and still cooling off after being given up on. THIS LINE WAS SWALLOWED BY THE
				// COMMENT ABOVE IT - both statements were on one line, so everything after the first
				// `//` was a comment and the whole AVOID_MS cooling-off never ran. `abandonSpot`
				// nulls spotCentre, so the next recount re-picked the SAME best cluster, flew at the
				// same wall and stuck again - abandon, re-pick, abandon, every two seconds, until
				// THRASH_LIMIT killed a design that had one awkward spot in it.
				if (Loop.avoided(avoided, c.centre(), now, Plan.MAX_RADIUS)) continue;
				next = c;
				break;
			}
			// ...but a hard spot is better than no spot: if everything left is merely COOLING OFF,
			// take it anyway rather than idling until the minute expires. An IGNORED spot is
			// different — it has failed twice and is not on the table at all.
			if (next == null) {
				avoided.clear();
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
						return;
					}
				}
				// EVERY SPOT STRUCK TWICE AND NOWHERE ELSE TO GO. This returned quietly and did it
				// again every two seconds for the rest of the night - the loop was alive, silent and
				// doing nothing at all. The strike list is the most obviously stale thing a reset
				// throws away, so this is the case it is best at. Another DESIGN is tried first,
				// because moving on is cheaper than crossing the world and does not move the player.
				rally(mc, "every spot left has failed twice");
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
		workAnchor = next.centre();                     // the anchor is the spot being built
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
				now - stationSince, STATION_MS, stationRetry, rep[0], rep[1], rep[2])
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
				List<BlockPos> lap = Plan.ring(Bounds.within(Nav.of(mc.level)), here, Plan.reachExact(), STANDOFF + 2);
				if (lap.size() >= 2) {
					if (now - orbitSince >= ORBIT_MS || target == null) {
						orbitSince = now;
						orbitLeg = (orbitLeg + 1) % lap.size();
					}
					orbitLeg %= lap.size();                        // the ring shrinks as cells go in
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
				BlockPos re = Plan.bestStand(Bounds.within(Nav.of(mc.level)), here, Plan.reachExact(),
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
						: Nav.standoff(Bounds.within(Nav.of(mc.level)), Plan.centroid(here), mc.player.blockPosition(), 1);
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
	/** How many spots may be given up on with nothing placed before the design is the problem. */	static final int THRASH_LIMIT = 4;
	/** Fewer blocks than this between two abandonments is a trickle, not building. */
	static final int THRASH_TRICKLE = 5;

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
		} else if (strike && spotCentre == null && target != null && Ignored.strike(target)) {
			// NO SPOT, BUT A DESTINATION: a return to the anchor or a look. Struck as a place, or
			// the stall fires every ninety seconds against a target it never marks.
			Highlight.show("ignore", Ignored.marks(), 0xFF3030, 600);
		}
		// Count the giving-up, and remember what had been placed at the time: several abandonments
		// with NOTHING built between them is thrashing, which no single watchdog can see.		// A TRICKLE IS NOT PROGRESS. One block placed per leg of an A-B-A ping-pong reset this
		// count every time, so the thrash detector never fired and the pair ran all night.
		if (placedTotal - placedWhenAbandoned < THRASH_TRICKLE) {
			spotsAbandoned++;
		} else {
			spotsAbandoned = 1;
			placedWhenAbandoned = placedTotal;
		}
		if (spotCentre != null) avoided.put(spotCentre, System.currentTimeMillis() + AVOID_MS);
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

	/**
	 * How long a chest whose chunk has not arrived is flown at before it is given up on.
	 *
	 * <p>Long enough to cross the island at cruise with the chunks coming in behind you, short
	 * enough that a source no flight can reach costs one trip rather than a night. See the note
	 * in {@link #fetchTo}: this is the only phase of the loop with no other clock over it.
	 */
	static final long FETCH_REACH_MS = 45_000;

	/**
	 * How many cells a commitment is CONFIRMED over. See Printer.confirmPlaceable: the scan's
	 * optimistic answer is fine to search with and must never be flown at, and confirming the
	 * whole area would be the sweep this budget exists to bound.
	 */
	static final int CONFIRM = 24;

	/**
	 * Cells of `all` this pack holds at least `load` of and the world really has a face to click for.
	 *
	 * <p>Scanned cheaply, then the nearest {@link #CONFIRM} are ASKED FOR CERTAIN - because this
	 * list is what the loop re-anchors and flies to, and a destination chosen on cells nobody
	 * looked at is a destination the next recount retracts. That retraction is the "flies
	 * somewhere then turns around"; the dead-end branch it lands in then cancels the flight.
	 */
	private static java.util.List<Work.Cell> carriedPlaceable(Minecraft mc,
			Map<String, Integer> carrying, java.util.List<Work.Cell> all, int load, BlockPos near) {
		java.util.List<Work.Cell> maybe = Work.placeableNow(mc.level, Loop.carriedWork(carrying, all, load))
			.stream()
			.filter(c -> Printer.everPlaceableCached(mc, c.pos(), c.block()))
			.sorted(java.util.Comparator.comparingDouble(c -> c.pos().distSqr(near)))
			.toList();
		int checked = Math.min(CONFIRM, maybe.size());
		java.util.List<Work.Cell> sure = new java.util.ArrayList<>();
		int confirmed = 0;
		for (int i = 0; i < maybe.size(); i++) {
			Work.Cell c = maybe.get(i);
			if (i >= checked) { sure.add(c); continue; }          // past the budget: still a guess
			if (Printer.confirmPlaceable(mc, c.pos(), c.block())) { sure.add(c); confirmed++; }
		}
		// NOT ONE OF THE NEAREST SURVIVED, so the tail is guesses of exactly the same kind and
		// flying at them is the retraction this method exists to stop. The nearest IS the one the
		// re-anchor picks, so a confirmed head is what makes the commitment honest.
		return confirmed > 0 ? sure : java.util.List.of();
	}

	private static void fetchTo(Minecraft mc, BlockPos me, Plan.Restock want, int take,
	                            Map<String, Integer> carrying, java.util.Set<String> dump) {
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
				Withdraw.begin(at, want.item(), take + have, dump);
			}
			return;
		}
		if (!mc.level.isLoaded(at)) {
			// ---- OUT OF VIEW IS NOT NOWHERE TO STAND. `approach` answers null for an unloaded
			// chunk, and that null was read as "no cell to open it from" and cooled the chest for
			// a minute - so every chest beyond render distance was blacklisted before the flight
			// started, and the loop could only ever fetch from chests already loaded near the
			// work. Fly toward the chest; the approach cell is chosen once its chunk is here.
			if (target == null || !target.equals(at)) {
				fetchTargetSince = now;
				Highlight.show("goto", java.util.List.of(at), 0xFFC000, 900);
				mc.player.sendSystemMessage(Component.literal("[cscan] fetch: " + take + "x "
					+ want.item() + " from " + want.where().describe() + " — flying there first"));
				guide(at, "to " + want.where().describe());
				return;
			}
			// ---- AND A FLIGHT TO A CHEST THAT NEVER ARRIVES IS THE ONE PHASE WITH NO CLOCK OVER
			// IT AT ALL. Both the going-nowhere watchdog and the ninety-second stall skip while
			// fetching (Loop.goingNowhere, Loop.stalled), and FETCH_STUCK_MS below only runs once
			// an approach cell has been chosen - which needs the chunk. So a chest the flight
			// cannot reach parked the loop here silently: past Nav.MAX_RANGE no route can even be
			// searched, so the flight goes direct and keeps going, and because the body is moving
			// the whole time nothing upstream can see it either.
			if (now - fetchTargetSince > FETCH_REACH_MS) {
				Withdraw.noteFailure(at);
				mc.player.sendSystemMessage(Component.literal("[cscan] " + want.where().describe()
					+ " has not come into view in " + (FETCH_REACH_MS / 1000) + "s — skipping it"
					+ " for a minute and trying another source"));
				stopGuiding();
				Highlight.clear("goto");
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
		// ---- LAND IN IT WHEN IT CANNOT BE HOVERED IN. See ContainerInteraction.mustLand: an
		// approach beside a chest standing on a floor is a cell to STAND in, and a flight guided
		// at one holds its ground clearance two blocks above it and never arrives.
		if (ContainerInteraction.mustLand(mc, approach)) {
			guideLand(approach, "land at chest for " + take + "x " + want.item());
		} else {
			guideExact(approach, "go to chest for " + take + "x " + want.item());
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
	/**
	 * What the ACTUATOR has done, which nothing ever said out loud.
	 *
	 * <p>The journal has held this all along and it took a script to read it: 1,215 attempts, 951
	 * placed, 258 dropped, 6 wrong state - a fifth of every placement silently lost, and every
	 * conversation about it was a conversation rather than a number. A dropped share that climbs
	 * is the server throttling; wrong states are a slot or a state bug; given-up cells are the
	 * design. Three different problems that all look like "it is not placing".
	 */
	static String printerTally() {
		int[] t = Printer.tally();                     // placed, wrong, given up, dropped, attempts
		if (t[4] == 0) return "printer: nothing attempted yet this session";
		return "printer: " + t[0] + " placed, " + t[3] + " dropped by the server ("
			+ (100 * t[3] / t[4]) + "% of " + t[4] + " attempts), " + t[1] + " wrong state, "
			+ t[2] + " given up — pacing at " + Printer.pace() + " ticks/block";
	}

	static java.util.List<String> why(Minecraft mc) {
		java.util.List<String> out = new java.util.ArrayList<>();
		if (design == null) {
			out.add("not watching a design — /cscan follow <design>, or /cscan follow all");
			out.addAll(Autopilot.why(mc));
			return out;
		}
		out.add(design + (following ? (followAll ? "  (following all)" : "  (following)")
			: "  (watching only — /cscan follow " + design + " to work it)"));
		if (only != null) out.add("  ONLY " + String.join(", ", only) + " — every other material is not this session's work");
		out.add("  " + printerTally());
		if (ChunkScanClient.printerIdle != null) {
			out.add("  THE PRINTER IS NOT PLACING: " + ChunkScanClient.printerIdle);
		}
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
		if (workAnchor != null) out.add("  work anchor " + Wand.fmt(workAnchor)
			+ (mc.level != null && mc.level.isLoaded(workAnchor) ? "" : " (not loaded)"));
		if (loadPlan != null) out.add("  shopping list: " + Plan.describe(loadPlan));
		if (following && mc.player != null) {
			Map<String, Integer> away = Work.dumpable(mc.player, designItems(mc, design));
			if (!away.isEmpty()) out.add("  in the pack for no reason: " + Plan.describe(away)
				+ " — put away at the next chest");
		}
		if (target != null) out.add("  arrow at " + Wand.fmt(target) + " — " + targetNote);
		if (Ignored.count() > 0) {
			out.add("  " + Ignored.count() + " place(s) IGNORED after failing twice — /cscan ignore");
		}
		out.add("  reset: /" + Rally.home() + "  (" + Rally.resets() + " this session"
			+ (Rally.fruitless() > 0 ? ", " + Rally.fruitless() + " in a row with nothing placed" : "")
			+ (Rally.pending() ? ", one landing now" : "")
			+ ", next allowed in " + (Rally.readyIn(System.currentTimeMillis()) / 1000) + "s)");
		if (!Rally.lastReason().isEmpty()) out.add("  last reset: " + Rally.lastReason());
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

	/** The design being followed or watched, for {@link Rally} to analyse after a reset. */
	static String designName() {
		return design;
	}

	/**
	 * ASK FOR A RESET. See {@link Rally}: teleport to where the work is, forget every judgement
	 * this session has made, look again, and come back with materials chosen for what the build
	 * can actually take.
	 *
	 * <p>Only while a design is being FOLLOWED. A person who typed `/cscan goto` and wandered
	 * into a corner has not asked to be teleported across the island, and the flight's own
	 * ladder handles them perfectly well by giving the spot up.
	 *
	 * @return false when it did not fire - not following, or too soon since the last one - in
	 *         which case the caller must do whatever it would have done instead.
	 */
	static boolean rally(Minecraft mc, String why) {
		return rally(mc, why, false);
	}

	/** @param force asked for by hand: reset even with no design followed. */
	static boolean rally(Minecraft mc, String why, boolean force) {
		if (!following && !force) return false;
		return Rally.request(mc, why, placedTotal);
	}

	/**
	 * Every OPINION this session has formed about where to work, thrown away. Called by
	 * {@link Rally} on the way out; the counters that measure whether the loop is achieving
	 * anything are deliberately left alone, because they are what judges the reset itself.
	 */
	static void forgetForRally() {
		stopGuiding();
		Highlight.clear("goto");
		fetching = false;
		forgetLoadPlan();
		saidLoadPlan = null;
		saidLoadPlanAt = 0;
		workAnchor = null;
		workRadius = Loop.nearAgain();
		workLayer = Integer.MIN_VALUE;
		spotCentre = null;
		stationBin = Long.MIN_VALUE;
		stationTodo = -1;
		stationRetry = 0;
		stationArrivedAt = 0;
		stationsTried.clear();
		avoided.clear();
		scaffoldFor = -1;
		fetchChest = null;
		approachTried.clear();
		lookTarget = null;
		lookFailures = 0;
		// WRITTEN OFF FROM SOMEWHERE ELSE. `unseenGivenUp` says a design's hidden cells would not
		// load from anywhere we could reach - which was true of the place we are leaving, and is
		// exactly what a teleport to the work is meant to change. Same for `parked`: a design
		// handed back unfinished deserves one more look from the right island. `doneThisSession`
		// stays, because a design that is FINISHED is a measurement, not an opinion.
		unseenGivenUp.clear();
		parked.clear();
		said = false;
		deadEndSince = 0;
		returnSince = 0;
		hiccups = 0;
		splitFailures = 0;
		spotsAbandoned = 0;
		placedWhenAbandoned = placedTotal;
		stallsWithoutProgress = 0;
		holdSince = 0;
		holdCoolUntil = 0;
		orbitLeg = 0;
		orbitSince = 0;
		lastProgressMs = System.currentTimeMillis();
	}

	/**
	 * ...and start again, once the world has arrived.
	 *
	 * <p>The one thing set here that the ordinary machinery would not do for itself is
	 * {@link #topUp}: FILL THE PACK FIRST. Jack asked for the reset to <i>"restart with new
	 * materials after a cscan analyze"</i>, and that is exactly what a top-up is - the phase is
	 * a FETCH sized to what the analysis says the build can take, rather than a build with
	 * whatever happened to survive the trip.
	 */
	static void restartAfterRally(Minecraft mc) {
		if (!following) return;
		topUp = true;
		lastProgressMs = System.currentTimeMillis();
		movedAt = lastProgressMs;
		lastAt = null;
		grace = 0;
		if (mc.player != null) mc.player.sendSystemMessage(Component.literal("[cscan] reset done -"
			+ " filling the pack for what the build can take, then back to work"));
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
		BuildJob.stop();
        ChestScan.reset();
        ChunkScanClient.printDesign = null;
        Printer.reset();
        Withdraw.cancel();
		design = null;
		lines = new ArrayList<>();
		following = false;
		followAll = false;
		fetching = false;
		forgetLoadPlan();
		saidLoadPlan = null;
		saidLoadPlanAt = 0;
		workAnchor = null;
		designItemsFor = null;
		designItems = null;
		said = false;
		placementWarned = false;
		deviationsSaid = false;
		saidBoxed.clear();
		spotCentre = null;
		stationBin = Long.MIN_VALUE;
		stationTodo = -1;
		stationRetry = 0;
		stationArrivedAt = 0;
		stationsTried.clear();		avoided.clear();
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
		stallsWithoutProgress = 0;
		placedWhenStalled = 0;
		Rally.clearSession();          // the backoff belongs to a session, the home command does not
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
					Bounds.corners(), Bounds.dimension(), BuildJob.phase().name(),
					only == null ? null : String.join(",", only)));
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
		// THE FILTER COMES BACK WITH THE SESSION. Resumed without it, a `follow` that was told to
		// place one material would place everything - the dangerous direction.
		if (st.only() != null && !st.only().isBlank()) {
			setOnly(new java.util.HashSet<>(java.util.Arrays.asList(st.only().split(","))));
			if (mc.player != null) mc.player.sendSystemMessage(Component.literal("[cscan] only " + st.only()));
		}
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
        try { Printer.setDesignWater(Work.load(ScanRunner.schematicsDir(Minecraft.getInstance()), name)); }
        catch (Exception ignored) { Printer.setDesignWater(java.util.List.of()); }
        ChunkScanClient.printDesign = name;
        // ---- AND TAKE THE CLAIM, OR SAY WHY NOT, HERE.
        //
        // `/cscan print` has always refused a design held by another account, loudly, at the moment
        // you typed it. `follow` - which is what actually arms the printer for the loop - never
        // asked: it set printDesign and the printer's own tick then refused it silently, every
        // tick, for the whole session. Measured: two placements in three minutes with `fleet.json`
        // holding `park complete` for another name.
        //
        // Following a design IS asserting you are the one building it, so it claims. The common
        // case - your own claim, or one whose lease has lapsed - self-heals in silence; a genuine
        // conflict is said once, at the right moment, with the way out.
        try {
            Minecraft here = Minecraft.getInstance();
            String said = Fleet.claim(ScanRunner.schematicsDir(here), name, Fleet.me(here));
            if (said != null && said.contains("held by") && here.player != null) {
                here.player.sendSystemMessage(Component.literal("[cscan] " + said
                    + ". The printer will place NOTHING until that is resolved - /cscan fleet take "
                    + name + " to override, or /cscan fleet to see it."));
            }
        } catch (Exception e) {
            // A claim that cannot be written is not a reason to refuse the follow; the printer's
            // own gate reports it now rather than returning in silence.
        }
        Withdraw.cancel();
        fetching = false;
        forgetLoadPlan();
        saidLoadPlan = null;
        saidLoadPlanAt = 0;
        workAnchor = null;
        // ---- FILL THE PACK FIRST. See topUp.
        topUp = true;
        saidFarFetch = false;
        workLayer = Integer.MIN_VALUE;
        workRadius = Loop.nearAgain();
        watch(name);
		following = true;
		BuildJob.start();
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
		splitFailures = 0;		avoided.clear();
		holdSince = 0;
		holdCoolUntil = 0;
		holdSaid = false;
		carryFirstSaid = false;
		deadEndSince = 0;
		returnSince = 0;
		unboxRetryAt.clear();
		orbitLeg = 0;
		orbitSince = 0;
		Ignored.clear();                              // written-off places were THIS design's spots
		analyseAtStart = true;
	}

	/**
	 * Read out what the whole design can TAKE, once, at the start of a session.
	 *
	 * <p>Jack: <i>"we need, when it starts, for it to analyze entire schematic and provide a list
	 * of top 5 materials that are immediately placeable."</i> The loop's own first act is a top-up
	 * trip, and until now the only thing it said about that was the shopping list - which is
	 * scoped to the working area round the anchor and says nothing about the design. The reset
	 * already prints this; a session that never resets never saw it.
	 *
	 * <p>DEFERRED TO THE FIRST RECOUNT rather than run inside `follow`, and that is not tidiness:
	 * `follow` is also how a session RESUMES after a join, where most of the world has not arrived
	 * and every cell would be counted out of view. The grace period is exactly the wait this needs,
	 * so it is the one both share.
	 *
	 * <p>It is a whole-design split - the 260ms one - so it happens ONCE, on a tick where the loop
	 * has just started and nothing is in flight.
	 */
	private static boolean analyseAtStart;

	private static void analyseAtStart(Minecraft mc) {
		analyseAtStart = false;
		mc.player.sendSystemMessage(Component.literal("[cscan] what " + design + " can take right"
			+ " now — fill the pack from the top of this list:"));
		for (String line : Analyze.report(mc.level, ScanRunner.schematicsDir(mc), design,
				mc.player, Analyze.START_ROWS)) {
			mc.player.sendSystemMessage(Component.literal("[cscan] " + line));
		}
	}

	/** What the loop has done since `follow` started — the report for a session you were not watching. */
	static String sessionReport() {
		long mins = Math.max(1, (System.currentTimeMillis() - startedMs) / 60_000);
		int[] t = Printer.tally();
		// ...AND WHAT THE SERVER DID WITH THEM. A session that reports "0 placed" and nothing else
		// is a session nobody can diagnose; the same session reporting "0 placed, 40 dropped" is
		// one line from an answer.
		String lost = t[3] > 0 ? ", " + t[3] + " dropped by the server" : "";
		return placedTotal + " placed in " + mins + " min (" + (placedTotal / mins) + "/min)" + lost
			+ ", " + spotsDone + " spot(s) finished, " + fetches + " restock(s), " + stalls + " stall(s)";
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
		// A RESET LANDS ON ITS OWN CLOCK, and it must be able to finish even when there is no
		// design and no world yet - the teleport it is waiting on is exactly what brings those
		// back. It guards its own nulls.
		Rally.tick(mc);
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
			// THE WHOLE DESIGN - on `Park Complete` that is 540,862 cells, every two seconds. Timed,
			// because it is the most expensive thing this mod does and it reads as one line: see
			// Perf, and the memoisation in ActionRecipe/Printer/StateContract behind it.
			long t0 = System.nanoTime();
			// COUNT GLOBALLY, LIST LOCALLY. Measured in game with `/cscan perf`, this call was
			// 262 ms on average and 427 at worst - a quarter-second freeze twice a second, and by
			// far the largest thing this mod does. It built and SORTED every remaining cell of the
			// design - some two hundred thousand of them - so that `advance` could narrow it to
			// the sixteen blocks round the body and throw the rest away. The counts still cover
			// the whole design, because completion is a global question; only the LIST is bounded,
			// and `nearestTodo` answers the one thing the loop asks beyond it.
			// ...AND CENTRED ON THE WORK, NOT ON THE BODY. `advance` focuses on the ANCHOR, so a
			// detail sphere round the player empties the moment the two are apart - which is every
			// fetch. The loop would then read its own area as finished and re-anchor on whatever
			// is nearest the CHEST, and go on building wherever it last shopped.
			BlockPos detailAt = workAnchor != null ? workAnchor : mc.player.blockPosition();
			Work.Split sp = Work.split(mc.level, ScanRunner.schematicsDir(mc), design,
				detailAt, 0, workRadius + Loop.NEAR_RADIUS);
			Perf.record("recount", System.nanoTime() - t0);
			// A THROW INSIDE THE DECISION IS NOT A REASON TO END THE SESSION. Reading the work list
			// can fail permanently - no work.json, bad JSON - and the catch below is right to stop
			// for that. Everything after it is a judgement about a world that is being changed
			// underneath us by another mod, and a transient failure there should cost one tick.
			if (following && !Rally.pending()) {
				// ...AND NOT WHILE A RESET IS LANDING. On the tick a teleport lands most of the
				// world is unloaded, so every judgement below would be made about a world that is
				// not there yet - and the first of them is "is the work unreachable".
				if (analyseAtStart) {
					try { analyseAtStart(mc); }
					catch (Exception e) { analyseAtStart = false; }   // a report never ends a session
				}
				try {
					// TIMED SEPARATELY FROM THE DIFF, because they are separate costs and the
					// profiler measured only the first: `recount` is the world diff, `loop decide`
					// is the half-dozen passes over the todo list that follow it. A report that
					// names one of them blames whichever it happens to name.
					Perf.run("loop decide", () -> advance(mc, sp));
					hiccups = 0;
				} catch (Exception e) {
					if (++hiccups <= 3) {
						mc.player.sendSystemMessage(Component.literal("[cscan] recovered from "
							+ e + " — carrying on"));
					}
					if (hiccups >= 20) {
						// TWENTY THROWS IN A ROW IS A STATE PROBLEM, and a reset is the one move that
						// replaces the state. Stopping was right while there was nothing else to try;
						// it is not right when forgetting everything and looking again is available.
						mc.player.sendSystemMessage(Component.literal(
							"[cscan] 20 failures in a row: " + e));
						hiccups = 0;
						if (!rally(mc, "20 errors in a row inside the loop")) {
							following = false;
							ActiveBuild.clear();
							ChunkScanClient.printDesign = null;
							stopGuiding();
							Highlight.clear("goto");
							remember(mc);              // or session.json still says following, and the next join resumes into it
						}
					}
				}
			}
			int pct = sp.total() == 0 ? 0 : Math.round(100f * sp.built() / sp.total());
			List<String> out = new ArrayList<>();
			out.add(sp.name() + "  " + sp.built() + "/" + sp.total() + "  " + pct + "%");
			String second = sp.todoTotal() + " to place";
			if (!sp.wrong().isEmpty()) second += "   " + sp.wrong().size() + " deviating";
			// The nearest thing left, because "247 to place" does not tell you where to stand.
			BlockPos next = sp.todo().isEmpty() ? sp.nearestTodo() : sp.todo().get(0).pos();
			if (next != null) {
				second += "   next " + (int) Math.sqrt(next.distSqr(mc.player.blockPosition()))
					+ "m " + Storage.direction(mc.player.blockPosition(), next);
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
					+ design + ": cannot read its work list (" + e.getMessage() + ")."));
				// A BROKEN FILE IS NOT FIXED BY A TELEPORT, so this one does not rally - but it is
				// no reason to end an overnight run either. Park the design and take the next one;
				// stopping is only right when it is the last one there is.
				if (followAll && mc.player != null) {
					parked.add(design);
					String other = nextDesign(mc, design);
					splitFailures = 0;
					if (other != null && switchTo(mc, other)) return;
				}
				if (mc.player != null) mc.player.sendSystemMessage(Component.literal("[cscan]"
					+ " stopping. Regenerate it and /cscan follow again."));
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
