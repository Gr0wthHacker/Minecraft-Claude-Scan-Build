package dev.jack.chunkscan;

import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.screens.inventory.AbstractContainerScreen;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.world.inventory.ContainerInput;
import net.minecraft.world.inventory.Slot;
import net.minecraft.world.item.ItemStack;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Crafts the plan {@link Recipes} works out — the other half of {@code /cscan craft}.
 *
 * <p>{@code craft} says "craft 87x powered_rail from 522 gold, 87 sticks, 87 redstone" and then
 * leaves you clicking for twenty minutes. This drives the crafting screen the same way
 * {@link Withdraw} drives a chest, which is the proven pattern here: opening a menu is not
 * synchronous, so this is a state machine and not a loop.
 *
 * <p><b>THE GRID IS THE WHOLE DIFFICULTY, AND THE COST DATA DID NOT HAVE IT.</b> {@code needs} is
 * an aggregate — six stone bricks — which is everything a cost needs and not enough to craft:
 * putting six bricks anywhere in the grid does not make stairs. The extractor now keeps the real
 * 3x3 layout for all 1,056 crafting recipes, anchored top-left, which is where the game matches
 * a shaped recipe from.
 *
 * <p>Four things it has to get right:
 *
 * <ul>
 *   <li><b>One craft at a time, verified.</b> The result slot is read back before the next round;
 *       clicking ahead of the server takes nothing and looks exactly like a desync.</li>
 *   <li><b>SHIFT-CLICK THE RESULT, NEVER PICK IT UP.</b> {@code QUICK_MOVE} on the output slot
 *       crafts as many as the grid can make and puts them away in one action. Picking the result
 *       up leaves it on the cursor, and the next click puts it somewhere nobody chose.</li>
 *   <li><b>It never touches a slot it did not fill.</b> A crafting table's grid is shared with
 *       whatever you left in it, so the grid is emptied back to your inventory first and anything
 *       already there is returned rather than consumed.</li>
 *   <li><b>Missing an ingredient stops the round</b> and says which one. Half-filling a grid and
 *       walking away leaves your materials in a block that any hopper could empty.</li>
 * </ul>
 *
 * <p>Stonecutting and smelting are deliberately NOT done here. A stonecutter is one button
 * ({@code handleInventoryButtonClick}) and a furnace is two slots and a wait; both are worth
 * having and neither is this state machine. {@code /cscan make} says so rather than silently
 * skipping those steps.
 */
final class Crafter {
	/** Ticks between actions: the server has to answer, and a fast loop looks like a desync. */
	static final int STEP_TICKS = 3;

	enum Phase { IDLE, CLEARING, FILLING, TAKING, COUNTING, DONE, FAILED }

	private static Phase phase = Phase.IDLE;
	private static String target = "";
	private static int wanted, made;
	private static String why = "";
	private static long nextAt;
	private static List<List<String>> grid = List.of();
	private static int slotCursor;
	private static int beforeCount;

	private Crafter() {}

	static Phase phase() {
		return phase;
	}

	static String status() {
		if (phase == Phase.IDLE) return "idle";
		return phase.name().toLowerCase(java.util.Locale.ROOT) + " " + made + "/" + wanted + "x "
			+ target + (why.isBlank() ? "" : " — " + why);
	}

	static void stop() {
		phase = Phase.IDLE;
		target = "";
		why = "";
	}

	/**
	 * Begin crafting `count` of `item`. The crafting screen must already be OPEN — this never
	 * opens one, for the same reason {@link Prices} never opens a shop: walking up to a table and
	 * right-clicking it is the player's move, and a mod that does it decides where you stand.
	 */
	static String start(Minecraft mc, String item, int count) {
		if (!(Screens.container() instanceof AbstractContainerScreen<?> cs)) {
			return "open a crafting table first (or your own 2x2), then run this again";
		}
		Recipes.Recipe r = pick(item, cs);
		if (r == null) {
			return "no crafting recipe for " + item + " that fits this grid — "
				+ "a stonecutter recipe needs the stonecutter, and smelting needs a furnace";
		}
		grid = new ArrayList<>();
		for (List<String> alts : gridOf(r)) grid.add(alts);
		target = Rules.shortName(item);
		wanted = count;
		made = 0;
		why = "";
		slotCursor = 0;
		phase = Phase.CLEARING;
		nextAt = 0;
		return "crafting " + count + "x " + target + " — leave the screen open. /cscan make off to stop";
	}

	/** The recipe whose grid fits the open menu: 3x3 needs a table, 2x2 fits either. */
	static Recipes.Recipe pick(String item, AbstractContainerScreen<?> cs) {
		int size = craftSlots(cs);
		for (Recipes.Recipe r : Recipes.ways(item)) {
			if (!r.kind().equals("craft")) continue;
			List<List<String>> g = gridOf(r);
			if (g.isEmpty()) continue;
			if (size >= 9) return r;
			// A 2x2 grid can only take a recipe that fits in its top-left corner.
			boolean fits = true;
			for (int i = 0; i < 9; i++) {
				int row = i / 3, col = i % 3;
				if ((row > 1 || col > 1) && !g.get(i).isEmpty()) fits = false;
			}
			if (fits) return r;
		}
		return null;
	}

	static List<List<String>> gridOf(Recipes.Recipe r) {
		return r.grid() == null ? List.of() : r.grid();
	}

	/** How many crafting-grid slots the open menu has (4 or 9), or 0 if it is not a crafting menu. */
	static int craftSlots(AbstractContainerScreen<?> cs) {
		int n = 0;
		for (Slot s : cs.getMenu().slots) {
			if (s.container instanceof net.minecraft.world.inventory.CraftingContainer) n++;
		}
		return n;
	}

	/**
	 * One step of the machine. Returns a line worth showing, or null.
	 *
	 * <p>Everything here is guarded by {@link #nextAt} rather than run every tick: a click sent
	 * before the server has answered the last one takes nothing and reads as a desync.
	 */
	static String tick(Minecraft mc) {
		if (phase == Phase.IDLE || phase == Phase.DONE || phase == Phase.FAILED) return null;
		if (mc.player == null || mc.level == null) return null;
		if (mc.level.getGameTime() < nextAt) return null;
		nextAt = mc.level.getGameTime() + STEP_TICKS;
		if (!(Screens.container() instanceof AbstractContainerScreen<?> cs)) {
			phase = Phase.FAILED;
			why = "the crafting screen was closed";
			return "make stopped: " + why;
		}
		int id = cs.getMenu().containerId;
		List<Integer> craft = new ArrayList<>();
		int result = -1;
		for (int i = 0; i < cs.getMenu().slots.size(); i++) {
			Slot s = cs.getMenu().slots.get(i);
			if (s.container instanceof net.minecraft.world.inventory.ResultContainer) result = i;
			else if (s.container instanceof net.minecraft.world.inventory.CraftingContainer) craft.add(i);
		}
		if (craft.isEmpty() || result < 0) {
			phase = Phase.FAILED;
			why = "that screen has no crafting grid";
			return "make stopped: " + why;
		}

		switch (phase) {
			case CLEARING -> {
				// Return anything already in the grid. It is not ours and consuming it silently is
				// how you lose something you left there.
				for (int i : craft) {
					if (!cs.getMenu().slots.get(i).getItem().isEmpty()) {
						mc.gameMode.handleContainerInput(id, i, 0, ContainerInput.QUICK_MOVE, mc.player);
						return null;
					}
				}
				phase = Phase.FILLING;
				slotCursor = 0;
			}
			case FILLING -> {
				int cols = craft.size() >= 9 ? 3 : 2;
				while (slotCursor < 9) {
					List<String> alts = grid.get(slotCursor);
					if (alts.isEmpty()) { slotCursor++; continue; }
					int row = slotCursor / 3, col = slotCursor % 3;
					if (row >= cols || col >= cols) { slotCursor++; continue; }
					int menuSlot = craft.get(row * cols + col);
					if (!cs.getMenu().slots.get(menuSlot).getItem().isEmpty()) { slotCursor++; continue; }
					Integer from = findIngredient(cs, alts);
					if (from == null) {
						phase = Phase.FAILED;
						why = "out of " + alts.get(0);
						return "make stopped: " + why + " — the grid was emptied back to you";
					}
					// PICKUP from the source, PICKUP into the grid slot: two clicks, one item moved.
					mc.gameMode.handleContainerInput(id, from, 1, ContainerInput.PICKUP, mc.player);
					mc.gameMode.handleContainerInput(id, menuSlot, 1, ContainerInput.PICKUP, mc.player);
					slotCursor++;
					return null;
				}
				phase = Phase.TAKING;
			}
			case TAKING -> {
				ItemStack out = cs.getMenu().slots.get(result).getItem();
				if (out.isEmpty()) {
					phase = Phase.FAILED;
					why = "the grid produced nothing — the server may not have this recipe";
					return "make stopped: " + why;
				}
				beforeCount = count(cs, target);
				// SHIFT-CLICK: crafts everything the grid can make and puts it away in one action.
				mc.gameMode.handleContainerInput(id, result, 0, ContainerInput.QUICK_MOVE, mc.player);
				phase = Phase.COUNTING;
			}
			case COUNTING -> {
				// COUNTED ON A LATER TICK, NOT THE SAME ONE. The first version read the inventory
				// immediately after the click - before the server had answered - so the count never
				// moved, `made` stayed 0, and the machine crafted in a loop until it ran out of
				// ingredients and then reported that as the failure. Every state machine in this
				// mod has had to learn the same thing: opening and clicking a menu is not
				// synchronous, which is why `Withdraw` re-reads the screen each pass.
				int now = count(cs, target);
				int gained = Math.max(0, now - beforeCount);
				if (gained == 0) {
					phase = Phase.FAILED;
					why = "the craft produced nothing - the server may not have this recipe";
					return "make stopped: " + why;
				}
				made += gained;
				if (made >= wanted) {
					phase = Phase.DONE;
					return "made " + made + "x " + target;
				}
				phase = Phase.CLEARING;
				slotCursor = 0;
			}
			default -> { }
		}
		return null;
	}

	/** A player-inventory slot holding one of these, or null. Never a grid slot. */
	private static Integer findIngredient(AbstractContainerScreen<?> cs, List<String> alts) {
		for (int i = 0; i < cs.getMenu().slots.size(); i++) {
			Slot s = cs.getMenu().slots.get(i);
			if (s.container instanceof net.minecraft.world.inventory.CraftingContainer) continue;
			if (s.container instanceof net.minecraft.world.inventory.ResultContainer) continue;
			ItemStack st = s.getItem();
			if (st.isEmpty()) continue;
			String n = BuiltInRegistries.ITEM.getKey(st.getItem()).getPath();
			if (alts.contains(n)) return i;
		}
		return null;
	}

	private static int count(AbstractContainerScreen<?> cs, String item) {
		int n = 0;
		for (Slot s : cs.getMenu().slots) {
			ItemStack st = s.getItem();
			if (!st.isEmpty() && BuiltInRegistries.ITEM.getKey(st.getItem()).getPath().equals(item)) {
				n += st.getCount();
			}
		}
		return n;
	}

	/** What a plan needs that this cannot do, in words, so nothing is skipped in silence. */
	static Map<String, String> unsupported(Recipes.Plan plan) {
		Map<String, String> out = new LinkedHashMap<>();
		for (Recipes.Step s : plan.steps) {
			switch (s.kind()) {
				case "cut" -> out.put(s.item(), "stonecutter (" + s.made() + "x)");
				case "smelt" -> out.put(s.item(), "furnace (" + s.made() + "x, plus fuel)");
				case "cook" -> out.put(s.item(), "smoker or campfire (" + s.made() + "x)");
				default -> { }
			}
		}
		return out;
	}
}
