package dev.jack.chunkscan;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import net.fabricmc.fabric.api.client.screen.v1.ScreenEvents;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.screens.inventory.AbstractContainerScreen;
import net.minecraft.core.component.DataComponents;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.network.chat.Component;
import net.minecraft.world.inventory.Slot;
import net.minecraft.world.item.ItemStack;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * What a block actually COSTS, read off the server's own shop menu.
 *
 * <p>{@code mcbuild/palette.py} sorts the whole registry into three hand-written buckets —
 * cheap, ok, expensive — with prices noted in a comment ("terracotta, 10 grass each"). Every
 * palette this project has ever picked rests on that table, and CLAUDE.md already admits it is
 * invented. The server has real numbers and nothing had ever asked for them.
 *
 * <p><b>A shop menu IS a container screen</b>, which is the whole reason this was cheap:
 * {@link ContainerWatcher} already hooks {@code ScreenEvents} and walks {@code menu.slots}. The
 * price is not in the item — it is in the item's LORE, as text a human reads. So this is a text
 * scraper, and it is honest about that:
 *
 * <ul>
 *   <li><b>Nothing is guessed.</b> A slot whose lore has no recognisable price is skipped and
 *       counted, never defaulted to zero — a missing price must never read as "free".</li>
 *   <li><b>Buy and sell are different numbers</b> and are kept apart. Costing a build with a
 *       sell price understates it by whatever the spread is, which on most servers is most of
 *       the price.</li>
 *   <li><b>A price is per ITEM, not per stack.</b> A menu that offers 64 for 320 coins is 5
 *       each, and the quantity is in the lore too. Recording 320 makes stone look like quartz.</li>
 *   <li><b>It never opens a menu by itself.</b> You walk the shop; this reads what you look at.
 *       Automating a shop walk is a trading bot, which is a different thing entirely and not
 *       one this mod is going to become.</li>
 * </ul>
 *
 * <p>Written to {@code schematics/prices.json} — beside the storage index rather than baked into
 * the jar, because these change when the SERVER changes, which is the test that decides.
 */
final class Prices {
	static final String FILE = "prices.json";

	/** Kept apart on purpose: costing a build with a sell price understates it by the spread. */
	static final class Price {
		double buy = -1;                 // coins to buy ONE
		double sell = -1;                // coins you get for ONE
		String seen = "";
		String source = "";
	}

	static final class Book {
		String server = "";
		String updated = "";
		int skipped;                     // slots whose lore held no price we could read
		Map<String, Price> prices = new LinkedHashMap<>();
	}

	private static boolean capturing;
	private static int found, skipped;

	private Prices() {}

	// "$1,234.5", "1234 coins", "Buy: 25", "Price: 12.5 each". Deliberately permissive on the
	// number and strict on the KEYWORD, because a menu is full of numbers that are not prices —
	// stack sizes, enchantment levels, cooldowns.
	private static final Pattern BUY = Pattern.compile(
		"(?:buy|price|cost)\\D{0,12}?([0-9][0-9,.]*)\\s*([kmb])?", Pattern.CASE_INSENSITIVE);
	private static final Pattern SELL = Pattern.compile(
		"(?:sell|sale|worth)\\D{0,12}?([0-9][0-9,.]*)\\s*([kmb])?", Pattern.CASE_INSENSITIVE);
	// "x64", "64x", "Amount: 64", "Stack of 64" — the quantity a listed price is FOR.
	private static final Pattern QTY = Pattern.compile(
		"(?:x\\s*([0-9]{1,4})\\b|\\b([0-9]{1,4})\\s*x\\b|(?:amount|qty|quantity|stack of)\\D{0,4}([0-9]{1,4}))",
		Pattern.CASE_INSENSITIVE);

	static double number(String raw, String suffix) {
		double v = Double.parseDouble(raw.replace(",", ""));
		if (suffix == null) return v;
		return switch (suffix.toLowerCase(Locale.ROOT)) {
			case "k" -> v * 1_000;
			case "m" -> v * 1_000_000;
			case "b" -> v * 1_000_000_000;
			default -> v;
		};
	}

	/** Quantity the price refers to; 1 when the lore does not say. Never 0 — that would divide. */
	static int quantity(List<String> lines) {
		for (String l : lines) {
			Matcher m = QTY.matcher(l);
			while (m.find()) {
				for (int g = 1; g <= 3; g++) {
					if (m.group(g) != null) {
						int q = Integer.parseInt(m.group(g));
						if (q > 0 && q <= 3456) return q;
					}
				}
			}
		}
		return 1;
	}

	/**
	 * Read one listing's lore into a price, or null if there is no price in it.
	 *
	 * <p>Returned PER ITEM, which is the number every caller wants and the one the lore usually
	 * does not state.
	 */
	static Price read(List<String> lines) {
		Price p = new Price();
		int qty = quantity(lines);
		for (String l : lines) {
			Matcher b = BUY.matcher(l);
			if (b.find() && p.buy < 0) p.buy = number(b.group(1), b.group(2)) / qty;
			Matcher s = SELL.matcher(l);
			if (s.find() && p.sell < 0) p.sell = number(s.group(1), s.group(2)) / qty;
		}
		return (p.buy < 0 && p.sell < 0) ? null : p;
	}

	static void register() {
		ScreenEvents.AFTER_INIT.register((mc, screen, w, h) -> {
			if (!capturing || !(screen instanceof AbstractContainerScreen<?> cs)) return;
			ScreenEvents.remove(screen).register(s -> {
				try {
					scrape(mc, cs);
				} catch (Exception e) {
					ChunkScanClient.LOG.warn("price scrape failed", e);
				}
			});
		});
	}

	static boolean capturing() {
		return capturing;
	}

	static String start() {
		capturing = true;
		found = skipped = 0;
		return "price capture ON — now walk the shop and open every category. "
			+ "Nothing is opened for you; this only reads menus you look at. /cscan prices off when done";
	}

	static String stop(Minecraft mc) {
		capturing = false;
		return "price capture OFF — " + found + " priced, " + skipped + " slots had no readable price";
	}

	private static void scrape(Minecraft mc, AbstractContainerScreen<?> cs) throws Exception {
		if (mc.player == null || mc.level == null) return;
		var inv = mc.player.getInventory();
		Path dir = ScanRunner.schematicsDir(mc);
		Book book = load(dir);
		String title = cs.getTitle().getString();
		int gotHere = 0;
		for (Slot slot : cs.getMenu().slots) {
			if (slot.container == inv) continue;              // your own pockets are not a shop
			ItemStack st = slot.getItem();
			if (st.isEmpty()) continue;
			List<String> lines = new ArrayList<>();
			var lore = st.get(DataComponents.LORE);
			if (lore != null) for (Component c : lore.lines()) lines.add(c.getString());
			lines.add(st.getHoverName().getString());
			Price p = read(lines);
			if (p == null) {
				skipped++;
				continue;
			}
			p.seen = java.time.Instant.now().toString();
			p.source = title;
			book.prices.put(BuiltInRegistries.ITEM.getKey(st.getItem()).getPath(), p);
			found++;
			gotHere++;
		}
		if (gotHere == 0) return;                              // not a shop menu; leave the file alone
		book.server = mc.getCurrentServer() == null ? "" : mc.getCurrentServer().ip;
		book.updated = java.time.Instant.now().toString();
		book.skipped = skipped;
		save(dir, book);
		ChunkScanClient.LOG.info("prices: +{} from \"{}\" ({} known)", gotHere, title, book.prices.size());
	}

	static Book load(Path dir) {
		Path f = dir.resolve(FILE);
		if (!Files.exists(f)) return new Book();
		try {
			JsonObject root = JsonParser.parseString(Files.readString(f, StandardCharsets.UTF_8)).getAsJsonObject();
			return new Gson().fromJson(root, Book.class);
		} catch (Exception e) {
			ChunkScanClient.LOG.warn("prices.json unreadable: {}", e.toString());
			return new Book();
		}
	}

	static void save(Path dir, Book b) throws Exception {
		Files.createDirectories(dir);
		Files.writeString(dir.resolve(FILE),
			new GsonBuilder().setPrettyPrinting().create().toJson(b), StandardCharsets.UTF_8);
	}

	/** Coins to buy this many, or -1 when the price is unknown. NEVER 0 — unknown is not free. */
	static double buyCost(Book b, String item, int n) {
		Price p = b.prices.get(Rules.shortName(item));
		return (p == null || p.buy < 0) ? -1 : p.buy * n;
	}
}
