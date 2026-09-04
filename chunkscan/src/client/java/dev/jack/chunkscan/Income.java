package dev.jack.chunkscan;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import net.minecraft.client.Minecraft;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * How fast the island PRODUCES things — the axis "can I afford this" was missing.
 *
 * <p>{@code /cscan bom} says 289 gold ingots short. That is a different sentence depending on
 * whether the gold farm makes 40 an hour or you have no source at all, and on skyblock income is
 * the constraint, not inventory. The container index is already a snapshot of everything you own;
 * a series of them is a rate.
 *
 * <p>Three things this has to get right, and two of them are ways to report a farm that does not
 * exist:
 *
 * <ul>
 *   <li><b>A snapshot is only evidence for containers you actually OPENED.</b> The index grows
 *       when you look in a chest, so a total that rises because you finally opened the gold chest
 *       is not production. Every sample records how many containers it saw, and a comparison
 *       across a different container set is reported as such rather than divided into a rate.</li>
 *   <li><b>Spending is not negative income.</b> Taking 500 bricks out to build with looks exactly
 *       like a farm running backwards. Rates are reported for RISES only, and falls are shown
 *       separately as consumption — which is its own useful number.</li>
 *   <li><b>Two samples an hour apart is a rate; two a minute apart is noise.</b> Below
 *       {@link #MIN_GAP_MS} the pair is not divided at all.</li>
 * </ul>
 *
 * <p>Samples live in {@code schematics/income.json}, capped at {@link #KEEP} — this is a rate
 * meter, not an archive, and the scans folder has already been an unbounded-growth bug once.
 */
final class Income {
	static final String FILE = "income.json";
	static final int KEEP = 240;
	static final long MIN_GAP_MS = 10 * 60 * 1000L;         // ten minutes

	static final class Sample {
		long at;
		int containers;
		Map<String, Integer> items = new LinkedHashMap<>();
	}

	static final class Log {
		List<Sample> samples = new ArrayList<>();
	}

	/** One material's movement between two samples. */
	record Rate(String item, int delta, double perHour) {}

	private Income() {}

	static Log load(Path dir) {
		Path f = dir.resolve(FILE);
		if (!Files.exists(f)) return new Log();
		try {
			JsonObject root = JsonParser.parseString(Files.readString(f, StandardCharsets.UTF_8)).getAsJsonObject();
			Log l = new Gson().fromJson(root, Log.class);
			return l == null ? new Log() : l;
		} catch (Exception e) {
			ChunkScanClient.LOG.warn("income.json unreadable: {}", e.toString());
			return new Log();
		}
	}

	static void save(Path dir, Log l) throws Exception {
		Files.createDirectories(dir);
		while (l.samples.size() > KEEP) l.samples.remove(0);
		Files.writeString(dir.resolve(FILE),
			new GsonBuilder().create().toJson(l), StandardCharsets.UTF_8);
	}

	/** Total everything the index currently holds, boxed contents included — it is all owned. */
	static Sample snapshot(Map<String, Storage.Container> all, long now) {
		Sample s = new Sample();
		s.at = now;
		s.containers = all.size();
		for (Storage.Container c : all.values()) {
			c.items.forEach((k, v) -> s.items.merge(Rules.shortName(k), v, Integer::sum));
			c.inBoxes.forEach((k, v) -> s.items.merge(Rules.shortName(k), v, Integer::sum));
		}
		return s;
	}

	/**
	 * Sample if enough time has passed AND the index has moved. Called after every container the
	 * watcher indexes, so a rate exists without anyone remembering to ask for one.
	 *
	 * <p>Both conditions, not either. Sampling on a pure timer fills the log with identical rows
	 * while you sleep and makes the "index grew" caveat meaningless; sampling on every change
	 * writes a row per chest opened, which is a rate measured over thirty seconds of walking.
	 */
	static void auto(Minecraft mc) {
		try {
			Path dir = ScanRunner.schematicsDir(mc);
			Log l = load(dir);
			Sample now = snapshot(Storage.load(dir), System.currentTimeMillis());
			if (!l.samples.isEmpty()) {
				Sample last = l.samples.get(l.samples.size() - 1);
				if (now.at - last.at < MIN_GAP_MS) return;
				if (now.items.equals(last.items)) return;      // nothing moved: nothing to record
			}
			l.samples.add(now);
			save(dir, l);
		} catch (Exception e) {                                // never cost anyone a container index
			ChunkScanClient.LOG.warn("income auto-sample failed: {}", e.toString());
		}
	}

	static String record(Minecraft mc) throws Exception {
		Path dir = ScanRunner.schematicsDir(mc);
		Log l = load(dir);
		Sample s = snapshot(Storage.load(dir), System.currentTimeMillis());
		l.samples.add(s);
		save(dir, l);
		return "sampled " + s.items.size() + " materials across " + s.containers + " containers ("
			+ l.samples.size() + " samples on file)";
	}

	/**
	 * Production between the oldest sample at least {@link #MIN_GAP_MS} back and the newest.
	 *
	 * <p>Returns an empty list rather than a wrong one when there is not enough evidence; the
	 * caller says why.
	 */
	static List<Rate> rates(Log l, boolean rising) {
		List<Rate> out = new ArrayList<>();
		if (l.samples.size() < 2) return out;
		Sample now = l.samples.get(l.samples.size() - 1);
		Sample then = null;
		for (int i = l.samples.size() - 2; i >= 0; i--) {
			if (now.at - l.samples.get(i).at >= MIN_GAP_MS) {
				then = l.samples.get(i);
				break;
			}
		}
		if (then == null) return out;
		double hours = (now.at - then.at) / 3_600_000.0;
		if (hours <= 0) return out;
		for (var e : now.items.entrySet()) {
			int d = e.getValue() - then.items.getOrDefault(e.getKey(), 0);
			if (rising ? d > 0 : d < 0) out.add(new Rate(e.getKey(), d, d / hours));
		}
		out.sort(Comparator.comparingDouble(r -> -Math.abs(r.perHour())));
		return out;
	}

	/** Hours of production to cover a shortfall, or -1 when nothing is making it. */
	static double hoursFor(List<Rate> rising, String item, int n) {
		for (Rate r : rising) {
			if (r.item().equals(Rules.shortName(item)) && r.perHour() > 0) return n / r.perHour();
		}
		return -1;
	}

	/** Whether the newest pair is comparable at all, and why not when it is not. */
	static String caveat(Log l) {
		if (l.samples.size() < 2) return "only " + l.samples.size() + " sample so far — run /cscan income again later";
		Sample now = l.samples.get(l.samples.size() - 1);
		Sample prev = l.samples.get(l.samples.size() - 2);
		if (now.at - prev.at < MIN_GAP_MS) {
			return "samples are " + ((now.at - prev.at) / 60000) + " min apart; under 10 min is noise, not a rate";
		}
		if (now.containers != prev.containers) {
			return "the index grew from " + prev.containers + " to " + now.containers + " containers between "
				+ "samples — some of this 'production' is just chests you had not opened before";
		}
		return "";
	}
}
