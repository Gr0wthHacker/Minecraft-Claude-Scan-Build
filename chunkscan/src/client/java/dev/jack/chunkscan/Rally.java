package dev.jack.chunkscan;

import net.minecraft.client.Minecraft;
import net.minecraft.client.player.LocalPlayer;
import net.minecraft.network.chat.Component;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

/**
 * THE RESET OF LAST RESORT: go home, forget every opinion, look again, and start over.
 *
 * <p>Every terminal path in this loop used to end the same way - {@code following = false} and a
 * sentence explaining why. That is honest and it is the wrong answer for a bot meant to run all
 * night. Jack: <i>"if it gets stuck permanently it needs to do /visit enroz and reset itself, if it
 * loses location or cant find, do the same and restart with new materials after a cscan analyze ...
 * make it highly crash resistant so its always doing things."</i>
 *
 * <p><b>{@code /is} IS THE WRONG TELEPORT ON THIS PARK.</b> The recovery ladder's top rung has
 * always typed it, and on a fleet of alts building on somebody else's plot it lands you on YOUR
 * island - a bare starter pad 121,000 blocks from the work, where every route is out of
 * {@link Nav#MAX_RANGE} and nothing can ever load. The rescue was itself the way the loop most
 * reliably lost its location. The home command goes where the WORK is, and it is a setting rather
 * than a literal because it is a fact about a server rather than about this mod.
 *
 * <h2>What a reset actually is</h2>
 *
 * <p>The teleport is the cheap half. What makes it a reset is throwing away every JUDGEMENT the
 * session has accumulated - struck spots, cooled-off chests, refused cells, written-off chunks, the
 * shopping list, the anchor - because every one of them is an opinion about a world we are no
 * longer standing in. What is KEPT is the measurement: how much has been placed, how long we have
 * been at it, which designs are genuinely finished. Opinions go stale; counts do not.
 *
 * <p>Then it LOOKS AGAIN ({@link Analyze}) before deciding anything, and the next phase is a FETCH,
 * so the loop comes back with materials chosen for what the build can take today rather than for
 * whatever the old list said.
 *
 * <h2>Three rules, and two of them are about not making it worse</h2>
 *
 * <ul>
 *   <li><b>A reset that fixes nothing must not be repeated at speed.</b> Resetting every thirty
 *       seconds for ever is the same infinite loop with a teleport in it, and a louder one. The
 *       interval DOUBLES while nothing is placed between attempts, and a single block placed since
 *       the last one puts it back to the beginning - that is the evidence it worked.</li>
 *   <li><b>A teleport cannot be fenced.</b> {@link Bounds} exists because somebody drew a box and
 *       asked the loop to stay in it; leaving to recover strands it outside its own fence with no
 *       legal way back. Fenced, the reset does the FORGETTING half and skips the flight - which is
 *       most of the value anyway, and is said rather than silently degraded.</li>
 *   <li><b>Landing is not instant.</b> The teleport moves the body some ticks later and the chunks
 *       arrive later still, so nothing is decided until the world is there - the same reasoning
 *       {@link Session#GRACE_TICKS} already carries for a join.</li>
 * </ul>
 */
final class Rally {
	/**
	 * Where the work is. NOT {@code /is} - see the class note.
	 *
	 * <p>Typed as the server takes it, without the slash: {@code sendCommand} prepends nothing, and
	 * a leading slash is sent as part of the command NAME.
	 */
	static final String DEFAULT_HOME = "visit enroz";
	static final String FILE = "home.txt";

	/** First interval between resets. */
	static final long BASE_COOL_MS = 30_000;
	/** ...and the longest, however many have been fruitless. */
	static final long MAX_COOL_MS = 300_000;
	/** Ticks to let the world arrive after the teleport before anything is decided. */
	static final int LANDING_TICKS = 120;

	/**
	 * Further than this from the nearest remaining cell and we are not merely far away, we are
	 * somewhere else. Twice {@link Nav#MAX_RANGE}, so a leg the router could plan never reads as
	 * lost - what this catches is the wrong island, which on this park is 121,000 blocks.
	 */
	static final int LOST_AT = 2 * Nav.MAX_RANGE;
	/** ...and for this long, so one recount taken mid-teleport is not evidence of anything. */
	static final long LOST_MS = 30_000;

	private Rally() {}

	private static String home = DEFAULT_HOME;
	private static boolean homeLoaded = false;
	/** Consecutive resets with nothing placed between them. Zeroed by a single block. */
	private static int fruitless = 0;
	/** Consecutive resets whose teleport provably did not move the body. */
	private static int deadHome = 0;
	/** ...after which it is not sent again this session. Two proofs, not one: a lag spike is one. */
	static final int DEAD_HOME_LIMIT = 2;
	/** Total this session, for the report. */
	private static int resets = 0;
	private static long coolUntil = 0;
	private static String lastWhy = "";
	private static int placedAtLast = -1;
	/** Ticks left before the landing is finished. 0 when nothing is pending. */
	private static int landing = 0;
	/** Where the body was when the teleport was sent, and null when none was. */
	private static net.minecraft.core.BlockPos leftFrom = null;
	/** How far the home command has to move us before we believe it ran. */
	static final double MOVED_ENOUGH = 8.0;
	/** When the work first measured further away than {@link #LOST_AT}, or 0. */
	private static long lostSince = 0;

	// ---------------------------------------------------------------- the decisions (pure)

	/**
	 * How long to wait before the next reset, given how many in a row have achieved nothing.
	 *
	 * <p>Doubling, capped. The cap is not a formality: past five minutes the loop has stopped being
	 * a build session and become a thing that types a command at the sky, and there is no interval
	 * at which that is better than saying so.
	 */
	static long cooldownFor(int fruitless) {
		long ms = BASE_COOL_MS;
		for (int i = 0; i < fruitless && ms < MAX_COOL_MS; i++) ms *= 2;
		return Math.min(ms, MAX_COOL_MS);
	}

	/** Is a reset allowed right now? */
	static boolean ready(long now, long until) {
		return now >= until;
	}

	/**
	 * Did the LAST reset achieve anything?
	 *
	 * <p>Placement is the only honest evidence, exactly as it is for every clock in {@link Loop}: a
	 * loop that is placing blocks is working whatever else is true of it. {@code -1} is "no reset
	 * yet", which counts as working rather than as failing.
	 */
	static boolean worked(int placedTotal, int placedAtLastRally) {
		return placedAtLastRally < 0 || placedTotal > placedAtLastRally;
	}

	/**
	 * Has the loop lost its location - is the work somewhere it cannot get to from here at all?
	 *
	 * <p>Measured rather than guessed: the distance to the nearest cell the design still wants. The
	 * fall rescue types {@code /is} (which always works, which is why it is the fall's answer) and
	 * that lands an alt on its own empty island; a server restart, a hub teleport or a failed warp
	 * do the same. From there nothing is wrong with the loop except that it is in the wrong world,
	 * and no amount of routing fixes it.
	 */
	static boolean lost(double distance, long now, long farSinceMs, long forMs) {
		return distance >= LOST_AT && farSinceMs > 0 && now - farSinceMs >= forMs;
	}

	// ---------------------------------------------------------------- the home command

	static String home() {
		return home;
	}

	/** Strip a leading slash and collapse whitespace: {@code /visit  enroz } is {@code visit enroz}. */
	static String normalise(String typed) {
		String s = typed == null ? "" : typed.trim();
		while (s.startsWith("/")) s = s.substring(1).trim();
		return s.replaceAll("\\s+", " ");
	}

	static void setHome(Minecraft mc, String typed) {
		home = normalise(typed);
		homeLoaded = true;
		try {
			Files.writeString(ScanRunner.schematicsDir(mc).resolve(FILE), home, StandardCharsets.UTF_8);
		} catch (Exception ignored) {
			// A loop that cannot write its notes is still a working loop.
		}
	}

	/** Read the setting once per session. A missing or unreadable file is the default, not an error. */
	static void loadHome(Minecraft mc) {
		if (homeLoaded) return;
		homeLoaded = true;
		try {
			Path f = ScanRunner.schematicsDir(mc).resolve(FILE);
			if (Files.exists(f)) {
				String s = normalise(Files.readString(f, StandardCharsets.UTF_8));
				if (!s.isBlank()) home = s;
			}
		} catch (Exception ignored) {
		}
	}

	// ---------------------------------------------------------------- state, for the report

	static int resets() { return resets; }

	static int fruitless() { return fruitless; }

	/** True while a reset is landing: nothing else may decide anything until the world is here. */
	static boolean pending() { return landing > 0; }

	static long readyIn(long now) { return Math.max(0, coolUntil - now); }

	static String lastReason() { return lastWhy; }

	/** A fresh session forgets all of it - but never the home command, which is a setting. */
	static void clearSession() {
		fruitless = 0;
		resets = 0;
		coolUntil = 0;
		lastWhy = "";
		placedAtLast = -1;
		landing = 0;
		leftFrom = null;
		lostSince = 0;
		deadHome = 0;
	}

	/**
	 * The work is far away: start (or keep) the clock, and say whether it has run out.
	 *
	 * <p>Held over time rather than judged on one reading, because a single recount taken while a
	 * chunk is loading, or on the tick a teleport lands, is not evidence about anything.
	 */
	static boolean noteDistance(double distance, long now) {
		if (distance < LOST_AT) {
			lostSince = 0;
			return false;
		}
		if (lostSince == 0) lostSince = now;
		return lost(distance, now, lostSince, LOST_MS);
	}

	// ---------------------------------------------------------------- doing it

	/**
	 * Reset, if it is time to.
	 *
	 * @param placedTotal blocks placed this session, which is how the last reset is judged
	 * @return true when this recount is spoken for - the reset fired, or one is already landing.
	 *         False means the cooldown has not expired and the caller should do what it would
	 *         otherwise have done, which at a dead end is usually nothing.
	 */
	static boolean request(Minecraft mc, String why, int placedTotal) {
		if (landing > 0) return true;
		long now = System.currentTimeMillis();
		if (!ready(now, coolUntil)) return false;
		LocalPlayer p = mc == null ? null : mc.player;
		if (p == null) return false;

		// A RESET THAT PLACED SOMETHING WORKED. The interval only grows for the ones that did not,
		// so a design with one awkward hour does not inherit the backoff from it.
		fruitless = worked(placedTotal, placedAtLast) ? 0 : fruitless + 1;
		placedAtLast = placedTotal;
		resets++;
		lastWhy = why;
		coolUntil = now + cooldownFor(fruitless);

		p.sendSystemMessage(Component.literal("[cscan] RESET #" + resets + " - " + why
			+ ". Forgetting this session's dead ends and starting again"
			+ (fruitless > 1 ? " (" + fruitless + " in a row with nothing placed)" : "") + "."));

		forgetOpinions(mc);

		if (Bounds.active()) {
			// A TELEPORT CANNOT BE FENCED. Somebody drew a box and asked the loop to stay in it;
			// leaving to recover strands it outside its own fence with no legal way back. The
			// forgetting is done and the flight is not, and that is said rather than degraded
			// silently.
			p.sendSystemMessage(Component.literal("[cscan] autofly bounds are set, so no teleport"
				+ " - reset in place. /cscan autofly bounds off to allow /" + home));
			leftFrom = null;
			landing = 20;                                  // a second, then look again
			return true;
		}
		loadHome(mc);
		if (deadHome >= DEAD_HOME_LIMIT) {
			// ---- A DETECTION THAT CHANGES NO BEHAVIOUR IS NOT A FIX. `land` has always NOTICED that
			// the teleport did not move us and said so - and then printed the analysis and restarted
			// the loop exactly as if it had worked, so the backoff repeated it every two, four and
			// eight minutes all night against byte-identical output. That is verbatim the failure its
			// own docstring says it exists to end. Two proofs is enough: the forgetting still happens,
			// the flight does not, and the one thing that would fix it is named.
			p.sendSystemMessage(Component.literal("[cscan] /" + home + " has not moved us "
				+ deadHome + " times, so this reset is in place only. Set the right one with"
				+ " /cscan home <command> - until then the loop cannot recover by teleporting."));
			leftFrom = null;
			landing = 20;
			return true;
		}
		if (p.connection != null) {
			p.connection.sendCommand(home);
			p.sendSystemMessage(Component.literal("[cscan] /" + home + " - back in a moment"));
		}
		leftFrom = p.blockPosition();
		landing = LANDING_TICKS;
		lostSince = 0;                                     // wherever we end up, judge it afresh
		return true;
	}

	/**
	 * Everything the session has DECIDED, thrown away. Everything it has MEASURED, kept.
	 *
	 * <p>The list is long on purpose and every entry earns its place: each is a set of write-offs
	 * that is correct about the world it was made in and worthless about a world we have just been
	 * teleported into. Left standing, a reset would land somewhere new and immediately refuse the
	 * same spots, skip the same chests and give up on the same cells.
	 */
	private static void forgetOpinions(Minecraft mc) {
		Ignored.clear();                 // struck spots: a strike is about a place we have left
		Withdraw.cancel();               // a half-open withdrawal belongs to a chest we are leaving
		Withdraw.clearFailures();        // ...and so does its cooling-off list
		ChestScan.reset();
		Digger.reset();
		Printer.relax();                 // not forgetPlaceability: a stale verdict stands until re-asked
		Autopilot.forget();
		Autopilot.resetRecovery();       // the trouble that got us here is about a place we have left
		Hud.forgetForRally();
	}

	/**
	 * Finish the landing. Called every tick; does nothing until the world has arrived.
	 *
	 * <p><b>Nothing is decided while this counts down.</b> On the tick a teleport lands, most of the
	 * world is unloaded and {@link Nav} treats unloaded as passable - which is right for a route
	 * already being flown and quite wrong as the first thing you do after arriving somewhere.
	 */
	static void tick(Minecraft mc) {
		if (landing <= 0) return;
		if (--landing > 0) return;
		if (mc == null || mc.player == null || mc.level == null) return;
		try {
			land(mc);
		} catch (Exception e) {
			// A reset that cannot read the design is still a reset: the loop carries on and the
			// ordinary machinery re-anchors on the next recount. NEVER throw out of a tick.
			mc.player.sendSystemMessage(Component.literal("[cscan] reset landed but could not"
				+ " analyse: " + e.getMessage() + " - carrying on anyway"));
			Hud.restartAfterRally(mc);
		}
	}

	/** LOOK BEFORE DECIDING. The report, then the anchor, then a trip sized to what it says. */
	private static void land(Minecraft mc) {
		// A TELEPORT THAT DID NOT TELEPORT IS A SILENT NO-OP, and this is the only place that can
		// see it: a wrong command name, a closed island, a permission that has lapsed. Without this
		// the loop announces a reset, does not move, backs off and repeats all night - which is the
		// exact shape of failure the reset exists to end.
		if (leftFrom != null) {
			if (mc.player.blockPosition().distSqr(leftFrom) < MOVED_ENOUGH * MOVED_ENOUGH) {
				deadHome++;
				mc.player.sendSystemMessage(Component.literal("[cscan] /" + home + " did not move us -"
					+ " is that the right command on this server? /cscan home <command> to change it."));
			} else {
				deadHome = 0;                                  // it works: judge every future one afresh
			}
		}
		leftFrom = null;
		String design = Hud.designName();
		if (design != null) {
			for (String line : Analyze.report(mc.level, ScanRunner.schematicsDir(mc), design,
					mc.player)) {
				mc.player.sendSystemMessage(Component.literal("[cscan] " + line));
			}
		}
		Hud.restartAfterRally(mc);
	}
}
