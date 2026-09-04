package dev.jack.chunkscan;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.ArrayList;

/**
 * The placement rules, read from chunkscan_rules.json — which is GENERATED from the Python by
 * tools/export_rules.py, not written here. Retyping protect.MECHANISM or blocks.ECONOMY in Java
 * would give two lists that disagree the first time either is edited.
 *
 * <p>Three separate questions, and they are not the same question:
 * <ul>
 *   <li>{@link #isProtected} — a mechanism, container or fixture. A generator must never write
 *       over one; the wand refuses to. Substring match, as {@code protect.is_protected} does it.</li>
 *   <li>{@link #isCurrency} — dirt and its forms are MONEY on skyblock.net. The blocks are real,
 *       legal, in 1.19 and placeable, so every other check passes them.</li>
 *   <li>{@link #isOnServer} — the client is 26.2 and the server is 1.19. A block added after 1.19
 *       is in the client registry, has legal states and renders fine — and cannot be placed.</li>
 * </ul>
 */
final class Rules {
	private static final String RESOURCE = "/chunkscan_rules.json";

	private static Set<String> protectedKeys = Set.of();
	private static Set<String> economy = Set.of();
	private static Set<String> serverBlocks = Set.of();
	/** category name -> substring patterns, longest first so a specific match beats a generic one */
	private static java.util.LinkedHashMap<String, List<String>> categories = new java.util.LinkedHashMap<>();
	private static boolean serverAuthoritative = false;
	private static boolean loaded = false;

	private Rules() {}

	static synchronized void load() {
		if (loaded) return;
		loaded = true;
		try (InputStream in = Rules.class.getResourceAsStream(RESOURCE)) {
			if (in == null) return;                      // ship without it and every check is a no-op
			JsonObject root = JsonParser.parseReader(new InputStreamReader(in, StandardCharsets.UTF_8)).getAsJsonObject();
			protectedKeys = strings(root, "protected");
			economy = strings(root, "economy");
			serverBlocks = strings(root, "server_blocks");
			serverAuthoritative = root.has("server_authoritative") && root.get("server_authoritative").getAsBoolean();
			Plot.load(root);          // the buildable square, derived from the island's own bedrock
			if (root.has("categories")) {
				categories = new java.util.LinkedHashMap<>();
				for (var e : root.getAsJsonObject("categories").entrySet()) {
					List<String> pats = new ArrayList<>();
					for (var v : e.getValue().getAsJsonArray()) pats.add(v.getAsString());
					categories.put(e.getKey(), pats);
				}
			}
		} catch (Exception e) {
			ChunkScanClient.LOG.warn("chunkscan_rules.json unreadable, placement rules are off: {}", e.toString());
		}
	}

	private static Set<String> strings(JsonObject root, String key) {
		Set<String> out = new HashSet<>();
		if (!root.has(key)) return out;
		for (var e : root.getAsJsonArray(key)) out.add(e.getAsString());
		return Collections.unmodifiableSet(out);
	}

	/** Strip namespace and block state, as the Python does before matching. */
	static String shortName(String name) {
		String n = name;
		int c = n.indexOf(':');
		if (c >= 0) n = n.substring(c + 1);
		int b = n.indexOf('[');
		if (b >= 0) n = n.substring(0, b);
		return n;
	}

	/** Substring match — `gray_wool` is protected because `wool` is in the list. */
	static boolean isProtected(String name) {
		load();
		String n = shortName(name);
		for (String k : protectedKeys) if (n.contains(k)) return true;
		return false;
	}

	/** Exact match: DIRT IS CURRENCY here, and so is every one of its forms. */
	static boolean isCurrency(String name) {
		load();
		return economy.contains(shortName(name));
	}

	/**
	 * The allowlist is PROVISIONAL — built from what the captures happen to contain plus a curated
	 * seed, so it holds ~191 of 1.19's blocks and would reject `allium`. Callers must only WARN on
	 * a false here until {@link #serverListIsAuthoritative()} says otherwise. Same posture as
	 * {@code audit.report}.
	 */
	static boolean isOnServer(String name) {
		load();
		return serverBlocks.isEmpty() || serverBlocks.contains(shortName(name));
	}

	static boolean serverListIsAuthoritative() {
		load();
		return serverAuthoritative;
	}

    private static Set<String> vanilla119;
    /** Version availability, independent of the provisional island's observed inventory list. */
    static synchronized boolean inLockedProfile(String block) {
        if (vanilla119 == null) {
            vanilla119 = Set.of();
            try (InputStream in = Rules.class.getResourceAsStream("/chunkscan_1_19.json")) {
                if (in != null) vanilla119 = strings(JsonParser.parseReader(new InputStreamReader(in, StandardCharsets.UTF_8)).getAsJsonObject(), "blocks");
            } catch (Exception e) { ChunkScanClient.LOG.warn("1.19 block registry missing; automatic placement disabled", e); }
        }
        // The running client uses newer names for these existing 1.19 blocks.
        // Translate only for availability; inventory and live states retain client IDs.
        String serverName = switch (shortName(block)) {
            case "iron_chain" -> "chain";
            case "short_grass" -> "grass";
            default -> shortName(block);
        };
        return vanilla119.contains(serverName);
    }

	/**
	 * Which storage category an item belongs to, or null if none claims it.
	 *
	 * <p>Patterns are matched longest-first inside each category, so `cooked_beef` finds `cooked_`
	 * rather than tripping over a shorter pattern somewhere else. Categories are tried in the order
	 * the file lists them, which is the order they are written in `tools/export_rules.py`.
	 */
	static String categoryOf(String item) {
		load();
		String n = shortName(item);
		for (var e : categories.entrySet()) {
			for (String pat : e.getValue()) if (n.contains(pat)) return e.getKey();
		}
		return null;
	}

	/** The category names, in the order they are declared. */
	static List<String> categoryNames() {
		load();
		return new ArrayList<>(categories.keySet());
	}

	/** Every reason this material is a bad idea, in words, for the chat line. Empty = no objection. */
	static List<String> objections(String name) {
		List<String> out = new ArrayList<>();
		if (isCurrency(name)) out.add("CURRENCY on this server (dirt and its forms are money) — use moss or stone");
		if (!isOnServer(name)) out.add("not in the 1.19 server allowlist (the list is provisional, so this may be a false alarm)");
		return out;
	}
}
