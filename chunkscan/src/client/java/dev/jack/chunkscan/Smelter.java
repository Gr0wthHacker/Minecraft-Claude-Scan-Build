package dev.jack.chunkscan;

import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.screens.inventory.AbstractContainerScreen;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.world.inventory.ContainerInput;
import net.minecraft.world.inventory.Slot;
import net.minecraft.world.item.ItemStack;

import java.util.List;
import java.util.Locale;

/**
 * The other two thirds of a craft plan: the FURNACE and the STONECUTTER.
 *
 * <p>{@link Crafter} drives a crafting grid and says so — a plan that also needs smelting was
 * reported as out of scope rather than skipped, which was honest and still left you doing it. The
 * clay farm is the plain case: clay to terracotta is 1,968 smelts, and the only thing standing
 * between "craftable" and "made" is putting things in a box and waiting.
 *
 * <p>They are one class because they are the same shape — an open menu with a small number of
 * fixed slots — and nothing like the crafting grid, which has a layout to satisfy.
 *
 * <p><b>THE STONECUTTER IS A BUTTON, NOT A GRID.</b> {@code handleInventoryButtonClick(containerId,
 * recipeIndex)} selects the recipe and the output appears; there is no arrangement to get right.
 * That also means the index is the ONLY thing identifying which recipe you get, and the order is
 * the server's, so this reads the output slot back and checks it is what was asked for rather than
 * trusting the index. Getting that wrong turns stone bricks into the wrong stair.
 *
 * <p><b>A FURNACE IS A WAIT, AND A WAIT IS NOT A FAILURE.</b> Everything else in this mod treats
 * "nothing happened for N seconds" as a stall; a furnace doing its job looks exactly like that for
 * ten seconds an item. So this never abandons on a clock — it fills the input, checks there is
 * FUEL, and then only reports when the input is gone or the fuel is.
 */
final class Smelter {
	static final int STEP_TICKS = 4;
	/** Slot indices are fixed by the vanilla furnace menu: input, fuel, output. */
	static final int IN = 0, FUEL = 1, OUT = 2;

	/** What a furnace burns, cheapest-first — the order this will spend them in. */
	static final List<String> FUELS = List.of(
		"coal", "charcoal", "coal_block", "dried_kelp_block", "blaze_rod",
		"oak_planks", "spruce_planks", "birch_planks", "jungle_planks", "acacia_planks",
		"dark_oak_planks", "stick", "bamboo");

	enum Kind { FURNACE, STONECUTTER, NEITHER }

	private static String target = "";
	private static int wanted, made;
	private static long nextAt;
	private static String note = "";

	private Smelter() {}

	static String status() {
		if (target.isBlank()) return "idle";
		return made + "/" + wanted + "x " + target + (note.isBlank() ? "" : " — " + note);
	}

	static void stop() {
		target = "";
		note = "";
	}

	static boolean running() {
		return !target.isBlank() && made < wanted;
	}

	/** What kind of menu is open. Named by SLOT SHAPE, because the title is server-skinnable. */
	static Kind kindOf(AbstractContainerScreen<?> cs) {
		var menu = cs.getMenu();
		if (menu instanceof net.minecraft.world.inventory.AbstractFurnaceMenu) return Kind.FURNACE;
		if (menu instanceof net.minecraft.world.inventory.StonecutterMenu) return Kind.STONECUTTER;
		return Kind.NEITHER;
	}

	static String start(Minecraft mc, String item, int count) {
		if (!(Screens.container() instanceof AbstractContainerScreen<?> cs)) {
			return "open a furnace or a stonecutter first";
		}
		Kind k = kindOf(cs);
		if (k == Kind.NEITHER) return "that is not a furnace or a stonecutter";
		target = Rules.shortName(item);
		wanted = Math.max(1, count);
		made = 0;
		note = "";
		nextAt = 0;
		return (k == Kind.FURNACE ? "smelting " : "cutting ") + wanted + "x " + target
			+ " — leave the screen open. /cscan smelt off to stop";
	}

	/** One step. Returns a line worth saying, or null. */
	static String tick(Minecraft mc) {
		if (!running() || mc.player == null || mc.level == null) return null;
		if (mc.level.getGameTime() < nextAt) return null;
		nextAt = mc.level.getGameTime() + STEP_TICKS;
		if (!(Screens.container() instanceof AbstractContainerScreen<?> cs)) {
			String was = target;
			stop();
			return "stopped: the " + was + " screen was closed";
		}
		return switch (kindOf(cs)) {
			case FURNACE -> furnace(mc, cs);
			case STONECUTTER -> stonecutter(mc, cs);
			case NEITHER -> {
				stop();
				yield "stopped: that screen is neither a furnace nor a stonecutter";
			}
		};
	}

	private static String furnace(Minecraft mc, AbstractContainerScreen<?> cs) {
		int id = cs.getMenu().containerId;
		ItemStack out = cs.getMenu().slots.get(OUT).getItem();
		if (!out.isEmpty()) {
			made += out.getCount();
			mc.gameMode.handleContainerInput(id, OUT, 0, ContainerInput.QUICK_MOVE, mc.player);
			if (made >= wanted) {
				String t = target;
				int n = made;
				stop();
				return "smelted " + n + "x " + t;
			}
			return null;
		}
		// FUEL FIRST. An input with no fuel is not a stall, it is a furnace that will never start,
		// and it looks identical to one that is working.
		if (cs.getMenu().slots.get(FUEL).getItem().isEmpty()) {
			Integer f = findAny(cs, FUELS);
			if (f == null) {
				note = "no fuel";
				return "out of fuel — coal, charcoal or planks in your pack, then it resumes";
			}
			mc.gameMode.handleContainerInput(id, f, 0, ContainerInput.QUICK_MOVE, mc.player);
			return null;
		}
		if (cs.getMenu().slots.get(IN).getItem().isEmpty()) {
			Integer src = findSource(cs);
			if (src == null) {
				note = "no input";
				String t = target;
				int n = made;
				stop();
				return "stopped: nothing left to smelt into " + t + " (" + n + " done)";
			}
			mc.gameMode.handleContainerInput(id, src, 0, ContainerInput.QUICK_MOVE, mc.player);
		}
		return null;                          // it is cooking. A wait is not a failure.
	}

	private static String stonecutter(Minecraft mc, AbstractContainerScreen<?> cs) {
		int id = cs.getMenu().containerId;
		ItemStack out = cs.getMenu().slots.get(1).getItem();
		if (!out.isEmpty()) {
			String got = BuiltInRegistries.ITEM.getKey(out.getItem()).getPath();
			// THE INDEX IS THE ONLY THING NAMING THE RECIPE, and the order is the server's. Read
			// the output back rather than trusting it, or stone bricks quietly become the wrong stair.
			if (!got.equals(target)) {
				note = "wrong recipe selected (" + got + ")";
				return null;
			}
			made += out.getCount();
			mc.gameMode.handleContainerInput(id, 1, 0, ContainerInput.QUICK_MOVE, mc.player);
			if (made >= wanted) {
				String t = target;
				int n = made;
				stop();
				return "cut " + n + "x " + t;
			}
			return null;
		}
		if (cs.getMenu().slots.get(0).getItem().isEmpty()) {
			Integer src = findSource(cs);
			if (src == null) {
				String t = target;
				int n = made;
				stop();
				return "stopped: nothing left to cut into " + t + " (" + n + " done)";
			}
			mc.gameMode.handleContainerInput(id, src, 0, ContainerInput.QUICK_MOVE, mc.player);
			return null;
		}
		// Input is in and no output: walk the recipe buttons until one produces what we asked for.
		for (int i = 0; i < 32; i++) {
			mc.gameMode.handleInventoryButtonClick(id, i);
			ItemStack now = cs.getMenu().slots.get(1).getItem();
			if (!now.isEmpty()
				&& BuiltInRegistries.ITEM.getKey(now.getItem()).getPath().equals(target)) {
				return null;
			}
		}
		String t = target;
		stop();
		return "stopped: this stonecutter has no recipe making " + t + " from what you gave it";
	}

	/** A player slot holding an ingredient that smelts or cuts into the target. */
	private static Integer findSource(AbstractContainerScreen<?> cs) {
		for (Recipes.Recipe r : Recipes.ways(target)) {
			if (r.kind().equals("craft")) continue;
			for (Recipes.Slot s : r.needs()) {
				Integer i = findAny(cs, s.alts());
				if (i != null) return i;
			}
		}
		return null;
	}

	private static Integer findAny(AbstractContainerScreen<?> cs, List<String> names) {
		var inv = Minecraft.getInstance().player == null ? null
			: Minecraft.getInstance().player.getInventory();
		for (int i = 0; i < cs.getMenu().slots.size(); i++) {
			Slot s = cs.getMenu().slots.get(i);
			if (inv != null && s.container != inv) continue;     // only YOUR pockets are a source
			ItemStack st = s.getItem();
			if (st.isEmpty()) continue;
			if (names.contains(BuiltInRegistries.ITEM.getKey(st.getItem()).getPath())) return i;
		}
		return null;
	}

	static String describeFuels() {
		return String.join(", ", FUELS.subList(0, Math.min(5, FUELS.size()))).toLowerCase(Locale.ROOT);
	}
}
