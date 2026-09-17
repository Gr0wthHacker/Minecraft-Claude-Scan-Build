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
	/** A click is settled on the NEXT tick by measuring the inventory delta: a shop may hand over a
	 *  whole stack per click, so charging one per-item price per click both miscounts and blows the
	 *  cap. Null when no purchase is in flight. */
	private static String pendingName;
	private static int pendingBefore;
	private static double pendingEach;

	private Shop() {}

	static boolean armed() {
		return armed;
	}

	static void stop() {
		armed = false;
		want.clear();
		pendingName = null;
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
		pendingName = null;
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

		// SETTLE THE LAST CLICK BY WHAT ACTUALLY ARRIVED. A shop may hand over a whole stack per
		// click, so the amount bought and the amount spent are only known by the inventory DELTA -
		// never by assuming one item at the per-item price, which is how a 64-per-click shop bought
		// 4096 and sailed past the cap while the code believed it had spent for one.
		if (pendingName != null) {
			int gained = held(mc, pendingName) - pendingBefore;
			String name = pendingName;
			pendingName = null;
			if (gained <= 0) {
				// A purchase that did not arrive is a stop condition: out of stock, or it went
				// somewhere we cannot see. Money-safe failure is to stop rather than click again.
				armed = false;
				return String.format("stopping: a purchase of %s did not arrive — %d item(s) for "
					+ "about %.0f coins so far", name, bought, spent);
			}
			spent += pendingEach * gained;
			bought += gained;
			Integer need = want.get(name);
			int left = (need == null ? 0 : need) - gained;
			if (left <= 0) want.remove(name);
			else want.put(name, left);
			if (want.isEmpty()) {
				armed = false;
				return String.format("bought %d item(s) for about %.0f coins", bought, spent);
			}
			if (spent >= cap) {
				armed = false;
				return String.format("reached the cap: about %.0f of %.0f coins, %d item(s)",
					spent, cap, bought);
			}
			return null;
		}

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

			double each = p.buy;                            // per ITEM (Prices divides by listed qty)
			// A shop click usually hands over the listed stack, so pre-check the cap against that
			// predicted quantity, not against one item — otherwise one click can blow the cap.
			int qty = Math.max(1, st.getCount());
			if (spent + each * qty > cap) {
				armed = false;
				return String.format("stopping at the cap: about %.0f coins spent, next purchase is "
					+ "about %.0f more (%dx %.0f)", spent, each * qty, qty, each);
			}
			// Click, then settle on the next tick by the real delta.
			pendingName = name;
			pendingBefore = held(mc, name);
			pendingEach = each;
			mc.gameMode.handleContainerInput(cs.getMenu().containerId, i, 0,
				ContainerInput.PICKUP, mc.player);
			return null;
		}
		return null;                                        // nothing we want in this menu
	}

	/** How many of a block/item are in the player's main inventory now — the delta is the buy. */
	private static int held(Minecraft mc, String name) {
		int n = 0;
		var inv = mc.player.getInventory();
		for (int i = 0; i < 36; i++) {
			ItemStack st = inv.getItem(i);
			if (!st.isEmpty() && BuiltInRegistries.ITEM.getKey(st.getItem()).getPath().equals(name)) {
				n += st.getCount();
			}
		}
		return n;
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
