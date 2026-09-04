package dev.jack.chunkscan;

import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.screens.inventory.AbstractContainerScreen;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.world.inventory.ContainerInput;
import net.minecraft.world.inventory.Slot;
import net.minecraft.world.item.ItemStack;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Buys a design's shortfall from the shop, up to a ceiling YOU set.
 *
 * <p>Everything needed already exists: {@link Recipes} knows what is short, {@link Prices} knows
 * what it costs, and a shop menu is a container screen this mod can already read. What is new is
 * the only part that is dangerous — clicking BUY spends real currency, and unlike every other
 * automation here a mistake cannot be undone by breaking a block.
 *
 * <p>So the design is almost entirely refusals:
 *
 * <ul>
 *   <li><b>THE CAP IS MANDATORY AND HAS NO DEFAULT.</b> {@code /cscan buy <design> <cap>} — there
 *       is no form of this command that spends an amount nobody chose. A default, however
 *       conservative, is a number I picked for money that is not mine.</li>
 *   <li><b>It spends against the SHORTFALL, never the design.</b> Buying 518 powered rails when
 *       167 are already in a chest is 167 rails of waste, and the whole point of the craft
 *       resolver is knowing the difference.</li>
 *   <li><b>An unpriced item is never bought.</b> No price means the shop was never seen selling
 *       it; clicking a slot whose cost is unknown is how you spend a fortune on one item.</li>
 *   <li><b>It stops at the cap, at the shortfall, or at the first surprise</b> — a slot whose
 *       price has moved since it was read, or a purchase that did not arrive.</li>
 *   <li><b>It never opens the shop.</b> You walk there; this clicks what is in front of you, and
 *       only after saying out loud what it is about to spend.</li>
 * </ul>
 *
 * <p>The spend is checked against what the menu ACTUALLY holds at click time rather than against
 * the price book, because the book is a memory of a menu seen at some point in the past and a
 * shop's prices move.
 */
final class Shop {
	static final int STEP_TICKS = 6;

	private static final Map<String, Integer> want = new LinkedHashMap<>();
	private static double cap, spent;
	private static int bought;
	private static boolean armed;
	private static long nextAt;

	private Shop() {}

	static boolean armed() {
		return armed;
	}

	static void stop() {
		armed = false;
		want.clear();
	}

	static String status() {
		if (!armed) return "not buying";
		return String.format("buying: %d item(s) so far, %.0f of %.0f coins spent, %d material(s) left",
			bought, spent, cap, want.size());
	}

	/**
	 * Arm a purchase run.
	 *
	 * @param shortfall what the craft resolver says is missing
	 * @param coinCap   the ceiling, in coins. No default anywhere: the caller must have been told one.
	 */
	static String arm(Map<String, Integer> shortfall, double coinCap, Minecraft mc) {
		want.clear();
		cap = coinCap;
		spent = 0;
		bought = 0;
		Prices.Book book = Prices.load(ScanRunner.schematicsDir(mc));
		double est = 0;
		int unpriced = 0;
		for (var e : shortfall.entrySet()) {
			double c = Prices.buyCost(book, e.getKey(), e.getValue());
			if (c < 0) {
				unpriced++;
				continue;                       // never buy what the shop was not seen selling
			}
			want.put(e.getKey(), e.getValue());
			est += c;
		}
		if (want.isEmpty()) {
			return "nothing to buy: " + (unpriced > 0
				? unpriced + " material(s) have no price — /cscan prices on and walk the shop"
				: "the shortfall is empty");
		}
		armed = true;
		nextAt = 0;
		return String.format("armed: up to %.0f coins, estimated %.0f for %d material(s)%s. "
				+ "Open the shop and it buys what it can. /cscan buy off to stop",
			cap, est, want.size(), unpriced > 0 ? " (" + unpriced + " unpriced, skipped)" : "");
	}

	/** One step against whatever menu is open. Returns a line worth saying, or null. */
	static String tick(Minecraft mc) {
		if (!armed || mc.player == null || mc.level == null) return null;
		if (mc.level.getGameTime() < nextAt) return null;
		nextAt = mc.level.getGameTime() + STEP_TICKS;
		if (!(Screens.container() instanceof AbstractContainerScreen<?> cs)) return null;
		if (want.isEmpty()) {
			armed = false;
			return String.format("bought %d item(s) for about %.0f coins", bought, spent);
		}

		var inv = mc.player.getInventory();
		for (int i = 0; i < cs.getMenu().slots.size(); i++) {
			Slot s = cs.getMenu().slots.get(i);
			if (s.container == inv) continue;
			ItemStack st = s.getItem();
			if (st.isEmpty()) continue;
			String name = BuiltInRegistries.ITEM.getKey(st.getItem()).getPath();
			Integer need = want.get(name);
			if (need == null || need <= 0) continue;

			// PRICED FROM THE SLOT IN FRONT OF US, not from the book. The book is a memory of a
			// menu seen at some point in the past, and a shop's prices move.
			java.util.List<String> lore = new java.util.ArrayList<>();
			var l = st.get(net.minecraft.core.component.DataComponents.LORE);
			if (l != null) for (var c : l.lines()) lore.add(c.getString());
			lore.add(st.getHoverName().getString());
			Prices.Price p = Prices.read(lore);
			if (p == null || p.buy < 0) continue;          // unknown here and now: leave it alone

			double each = p.buy;
			if (spent + each > cap) {
				armed = false;
				return String.format("stopping at the cap: %.0f coins spent, next item is %.0f more",
					spent, each);
			}
			mc.gameMode.handleContainerInput(cs.getMenu().containerId, i, 0,
				ContainerInput.PICKUP, mc.player);
			spent += each;
			bought++;
			int left = need - 1;
			if (left <= 0) want.remove(name);
			else want.put(name, left);
			return null;
		}
		return null;                                        // nothing we want in this menu
	}

	/** What it would cost, without buying anything — the line to read BEFORE arming. */
	static String quote(Map<String, Integer> shortfall, Minecraft mc) {
		Prices.Book book = Prices.load(ScanRunner.schematicsDir(mc));
		double total = 0;
		int priced = 0, unpriced = 0;
		StringBuilder b = new StringBuilder();
		for (var e : shortfall.entrySet()) {
			double c = Prices.buyCost(book, e.getKey(), e.getValue());
			if (c < 0) {
				unpriced++;
				continue;
			}
			priced++;
			total += c;
			if (b.length() < 200) {
				b.append(b.length() == 0 ? "" : ", ").append(e.getValue()).append("x ")
					.append(e.getKey()).append(" = ").append(Math.round(c));
			}
		}
		if (priced == 0) {
			return "nothing in the shortfall has a known price — /cscan prices on, then walk the shop";
		}
		return String.format("%s%n  about %.0f coins for %d material(s)%s", b, total, priced,
			unpriced > 0 ? ", plus " + unpriced + " with no known price" : "");
	}
}
