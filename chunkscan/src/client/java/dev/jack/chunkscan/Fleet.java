package dev.jack.chunkscan;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import net.minecraft.client.Minecraft;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.time.LocalDateTime;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Which of this island's designs THIS account is building.
 *
 * <p>Jack runs up to five alts and they all read the same schematics folder on one machine, which
 * removes almost everything a fleet would otherwise have to solve: no per-account profile, no
 * separate design set, nothing to sync. Every client already sees every design. What is left is
 * the only hard part — deciding who builds what — and it is one shared file, {@code fleet.json},
 * written by {@code python -m mcbuild fleet} and claimed from in game.
 *
 * <p><b>TWO ACCOUNTS MUST NEVER SHARE A DESIGN.</b> Not because the files collide — they are the
 * same file — but because two printers placing into the same cells fight: each one sees the
 * other's block as either already built or as a deviation, and {@link Printer}'s report, the one
 * honest signal this loop has, becomes noise. So a design is claimed exclusively.
 *
 * <p><b>A CLAIM IS A LEASE, BECAUSE AN ALT CAN DIE.</b> A client crashes, a session drops, someone
 * logs out mid-build. A claim that never expires strands a design for ever; one with no expiry at
 * all lets a second account grab it the moment the first is slow. So it is refreshed by a
 * heartbeat while the loop runs, and swept when it goes quiet — the same reasoning the chest
 * cooling-off already carries, and it has to expire for exactly the same reason.
 *
 * <p><b>FIVE IS A SERVER RULE.</b> It is enforced on the Python side where the assignment is made;
 * this side reports it so a sixth client cannot quietly appear without anyone seeing.
 */
final class Fleet {
	static final String FILE = "fleet.json";
	/** Matches {@code fleet.LEASE_MINUTES}. A claim unrefreshed for this long is handed back. */
	static final int LEASE_MINUTES = 15;
	/** How often the loop refreshes its claims. Well under the lease, so a busy client never loses one. */
	static final long BEAT_MS = 60_000;

	static final class Claim {
		String account = "";
		String at = "";
		String seen = "";
	}

	static final class State {
		String plan = "";
		Map<String, Claim> claims = new LinkedHashMap<>();
		List<String> done = new ArrayList<>();
	}

	private static long lastBeat;

	private Fleet() {}

	/** This client's account name — whoever is logged in. There is nothing else to configure. */
	static String me(Minecraft mc) {
		return mc.getUser() == null ? "" : mc.getUser().getName();
	}

	static State load(Path dir) {
		Path f = dir.resolve(FILE);
		if (!Files.exists(f)) return new State();
		try {
			JsonObject root = JsonParser.parseString(Files.readString(f, StandardCharsets.UTF_8))
				.getAsJsonObject();
			State s = new Gson().fromJson(root, State.class);
			if (s == null) return new State();
			if (s.claims == null) s.claims = new LinkedHashMap<>();
			if (s.done == null) s.done = new ArrayList<>();
			return s;
		} catch (Exception e) {
			ChunkScanClient.LOG.warn("fleet.json unreadable: {}", e.toString());
			return new State();
		}
	}

	/**
	 * Write atomically: temp file, then move.
	 *
	 * <p><b>FIVE CLIENTS SHARE THIS FILE.</b> A plain write leaves a window in which the file on
	 * disk is truncated, and a client reading in that window sees an EMPTY fleet — and cheerfully
	 * claims a design another account is already building, which is the one thing this file exists
	 * to prevent. An atomic move means a reader sees the old file or the new one, never half of one.
	 *
	 * <p>It does not make read-modify-write atomic, and pretending otherwise would be worse than
	 * the bug. Two clients that both read and then both write still lose one change. What carries
	 * it is that claims are near-idempotent and heartbeats repeat: a lost heartbeat is retried a
	 * minute later and a lost claim shows up in the next report. A real lock is the fix the day
	 * this assigns something that cannot be repeated.
	 */
	static void save(Path dir, State s) throws Exception {
		Files.createDirectories(dir);
		Path tmp = dir.resolve(FILE + ".tmp");
		Files.writeString(tmp, new GsonBuilder().setPrettyPrinting().create().toJson(s),
			StandardCharsets.UTF_8);
		try {
			Files.move(tmp, dir.resolve(FILE), java.nio.file.StandardCopyOption.REPLACE_EXISTING,
				java.nio.file.StandardCopyOption.ATOMIC_MOVE);
		} catch (java.nio.file.AtomicMoveNotSupportedException e) {
			Files.move(tmp, dir.resolve(FILE), java.nio.file.StandardCopyOption.REPLACE_EXISTING);
		}
	}

	static boolean expired(Claim c) {
		try {
			String seen = (c.seen == null || c.seen.isBlank()) ? c.at : c.seen;
			return Duration.between(LocalDateTime.parse(seen), LocalDateTime.now()).toMinutes()
				>= LEASE_MINUTES;
		} catch (DateTimeParseException | NullPointerException e) {
			return false;      // an unparseable stamp is not evidence the account is gone
		}
	}

	/** Designs this account holds, expired claims excluded. */
	static List<String> mine(Path dir, String account) {
		List<String> out = new ArrayList<>();
		State s = load(dir);
		for (var e : s.claims.entrySet()) {
			if (e.getValue().account.equals(account) && !expired(e.getValue())) out.add(e.getKey());
		}
		return out;
	}

	/** True when somebody ELSE holds this design and their lease is still good. */
	static boolean heldByOther(Path dir, String design, String account) {
		Claim c = load(dir).claims.get(design);
		return c != null && !c.account.equals(account) && !expired(c);
	}

	static String claim(Path dir, String design, String account) throws Exception {
		State s = load(dir);
		Claim cur = s.claims.get(design);
		if (cur != null && !cur.account.equals(account) && !expired(cur)) {
			return design + " is held by " + cur.account + " - two printers on one design fight";
		}
		Claim c = new Claim();
		c.account = account;
		c.at = LocalDateTime.now().toString();
		c.seen = c.at;
		s.claims.put(design, c);
		save(dir, s);
		return account + " holds " + design;
	}

	/** Refresh every claim this account holds. Rate-limited: the loop calls it every tick. */
	static void heartbeat(Minecraft mc) {
		if (System.currentTimeMillis() - lastBeat < BEAT_MS) return;
		lastBeat = System.currentTimeMillis();
		try {
			Path dir = ScanRunner.schematicsDir(mc);
			String me = me(mc);
			State s = load(dir);
			boolean any = false;
			for (Claim c : s.claims.values()) {
				if (c.account.equals(me)) {
					c.seen = LocalDateTime.now().toString();
					any = true;
				}
			}
			if (any) save(dir, s);
		} catch (Exception e) {
			ChunkScanClient.LOG.warn("fleet heartbeat failed: {}", e.toString());
		}
	}

	static String finish(Path dir, String design, String account) throws Exception {
		State s = load(dir);
		s.claims.remove(design);
		if (!s.done.contains(design)) s.done.add(design);
		save(dir, s);
		return account + " finished " + design;
	}

	static String report(Path dir, String me) {
		State s = load(dir);
		StringBuilder b = new StringBuilder();
		b.append("fleet: ").append(s.claims.size()).append(" claimed, ")
			.append(s.done.size()).append(" done");
		if (s.plan != null && !s.plan.isBlank()) b.append("  plan ").append(s.plan);
		b.append("\n  you are ").append(me);
		List<String> mine = mine(dir, me);
		b.append(mine.isEmpty() ? " and hold nothing" : " and hold: " + String.join(", ", mine));
		for (var e : s.claims.entrySet()) {
			if (e.getValue().account.equals(me)) continue;
			b.append("\n  ").append(e.getValue().account).append(": ").append(e.getKey())
				.append(expired(e.getValue()) ? "  (LEASE EXPIRED - free to take)" : "");
		}
		return b.toString();
	}
}
