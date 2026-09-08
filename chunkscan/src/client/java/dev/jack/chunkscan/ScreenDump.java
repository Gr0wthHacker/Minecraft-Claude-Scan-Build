package dev.jack.chunkscan;

import net.fabricmc.fabric.api.client.screen.v1.ScreenEvents;

import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.screens.inventory.AbstractContainerScreen;
import net.minecraft.core.component.DataComponents;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.network.chat.Component;
import net.minecraft.world.inventory.Slot;
import net.minecraft.world.item.ItemStack;

import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;

/**
 * Everything in the last container screen you opened, written down.
 *
 * <p><b>WHY THIS EXISTS RATHER THAN A ROUND OF QUESTIONS.</b> Driving a server's GUI means knowing
 * its slot layout, its item ids and exactly what its lore says, and none of that can be guessed from
 * a description or read off a screenshot. Every menu this mod already drives was written against
 * real slots: {@link Withdraw} against a chest, {@link Crafter} against a grid, {@link Prices}
 * against shop lore. This is the same look, taken once, for a menu nobody has written a driver for.
 *
 * <p><b>IT SNAPSHOTS ON CLOSE, NOT ON COMMAND, AND THAT IS NOT A CONVENIENCE.</b> A container screen
 * captures the keyboard, so there is no way to type a command while one is open - and the contents
 * arrive some ticks after the screen does, so a snapshot taken at open time is an empty menu. Both
 * are the same reason {@link Prices} hooks {@code ScreenEvents.remove}: by the time it closes, the
 * server has filled it. Open the menu, close it, then run the command.
 *
 * <p><b>IT NEVER CLICKS.</b> Not a nicety - a shop menu is somebody's money, and an inspector that
 * could buy something by accident is not an inspector.
 *
 * <p>Item ids come from the registry rather than from the display name, because a shop's display
 * name is decoration and the id is what a driver must match on - the same distinction
 * {@code items.item_for} draws between what a block is called and what you place it from.
 */
final class ScreenDump {

	private ScreenDump() {
	}

	/** Where the dumps go, beside the container index and the price book. */
	static final String FOLDER = "screens";

	/** The last container screen seen, as finished lines. Null until one has been closed. */
	private static List<String> last;
	private static String lastTitle = "";
	private static int lastSlots, lastFilled, lastTheirs;

	static void register() {
		ScreenEvents.AFTER_INIT.register((mc, screen, w, h) -> {
			if (!(screen instanceof AbstractContainerScreen<?> cs)) return;
			ScreenEvents.remove(screen).register(s -> {
				try {
					snapshot(mc, cs);
				} catch (Exception e) {
					// A DIAGNOSTIC NEVER THROWS OUT OF A SCREEN EVENT. A throw here is the same
					// class of fault as a throw out of a tick: it takes the client with it.
					ChunkScanClient.LOG.warn("screen snapshot failed", e);
				}
			});
		});
	}

	/** Read the menu into lines. Called as it closes, when the server has actually filled it. */
	private static void snapshot(Minecraft mc, AbstractContainerScreen<?> cs) {
		if (mc.player == null) return;
		var inv = mc.player.getInventory();
		List<String> body = new ArrayList<>();
		String title = cs.getTitle().getString();
		body.add("title:       " + title);
		body.add("menu class:  " + cs.getMenu().getClass().getName());
		body.add("screen:      " + cs.getClass().getName());
		body.add("containerId: " + cs.getMenu().containerId);
		body.add("slots:       " + cs.getMenu().slots.size());
		body.add("");
		body.add("# index  where     count  item id");
		body.add("#          name/lore lines follow, indented");
		body.add("");

		int i = -1, filled = 0, theirs = 0;
		for (Slot slot : cs.getMenu().slots) {
			i++;
			// The player's own pockets are in every container menu and are never its content.
			// MARKED rather than skipped: which indices are yours is part of the layout, and a
			// driver that guesses that boundary clicks the wrong slot.
			boolean mine = slot.container == inv;
			ItemStack st = slot.getItem();
			if (st.isEmpty()) continue;
			filled++;
			if (!mine) theirs++;
			body.add(String.format("%5d  %-8s  %5d  %s", i, mine ? "POCKETS" : "menu",
				st.getCount(), BuiltInRegistries.ITEM.getKey(st.getItem())));
			String name = st.getHoverName().getString();
			if (!name.isBlank()) body.add("         name: " + name);
			var lore = st.get(DataComponents.LORE);
			if (lore != null) {
				for (Component c : lore.lines()) body.add("         lore: " + c.getString());
			}
		}
		last = body;
		lastTitle = title;
		lastSlots = cs.getMenu().slots.size();
		lastFilled = filled;
		lastTheirs = theirs;
	}

	/**
	 * Write the last menu down.
	 *
	 * @return the lines to print in chat - a summary and a path, never the menu itself, which is
	 *         the point of writing it to a file. Never null and never empty.
	 */
	static List<String> dump(Minecraft mc) {
		List<String> out = new ArrayList<>();
		if (last == null) {
			out.add("no menu seen yet — open the one you want inspected, CLOSE it, then run this."
				+ " A container screen takes the keyboard, so it cannot be read while it is up.");
			return out;
		}
		try {
			Path dir = ScanRunner.schematicsDir(mc).resolve(FOLDER);
			Files.createDirectories(dir);
			String stamp = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMdd-HHmmss"));
			Path file = dir.resolve(safe(lastTitle) + "_" + stamp + ".txt");
			Files.write(file, last);
			out.add("\"" + lastTitle + "\" — " + lastSlots + " slots, " + lastFilled + " filled ("
				+ lastTheirs + " in the menu, " + (lastFilled - lastTheirs) + " in your pockets)");
			out.add("written to " + file);
			out.add("nothing was clicked.");
		} catch (Exception e) {
			out.add("could not write it: " + e);
		}
		return out;
	}

	/**
	 * A menu title is decoration and may hold anything at all - colour codes, slashes, quotes.
	 *
	 * <p>It becomes a FILENAME here, which is the hole {@code /cscan fill ../../x} once opened: a
	 * name that resolves out of the folder it is meant to be written in. Everything but letters,
	 * digits, dash and underscore goes, and an empty result gets a name rather than none.
	 */
	static String safe(String title) {
		String s = title.replaceAll("[^A-Za-z0-9_-]+", "_").replaceAll("^_+|_+$", "");
		if (s.length() > 60) s = s.substring(0, 60);
		return s.isBlank() ? "screen" : s;
	}
}
