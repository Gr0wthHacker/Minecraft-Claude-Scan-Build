package dev.jack.chunkscan;

import net.fabricmc.fabric.api.client.screen.v1.ScreenEvents;

import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.screens.Screen;
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
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.List;

/**
 * Everything in the last container menu you had open, written down.
 *
 * <p><b>WHY THIS EXISTS RATHER THAN A ROUND OF QUESTIONS.</b> Driving a server's GUI means knowing
 * its slot layout, its item ids and exactly what its lore says, and none of that can be guessed from
 * a description or read off a screenshot. Every menu this mod already drives was written against
 * real slots: {@link Withdraw} against a chest, {@link Crafter} against a grid, {@link Shop} against
 * shop lore. This is the same look, taken once, for a menu nobody has written a driver for.
 *
 * <p><b>IT SNAPSHOTS FROM THE TICK, NOT FROM A SCREEN EVENT.</b> The first version hooked
 * {@code ScreenEvents.remove} - the same event {@link Prices} uses - and on a live server it never
 * fired once: three attempts, no snapshot, and nothing in the log because nothing had thrown. That
 * is the whole failure shape this repo keeps writing rules about, so the dependency is gone rather
 * than debugged. {@link Screens#container()} is set from {@code AFTER_INIT} and is demonstrably
 * live - it is what pauses the build loop while a chest is open - so the tick reads THAT, and the
 * newest reading wins. By the time you close the menu the last snapshot is a few ticks old, which
 * is exactly what is wanted: the contents arrive some ticks after the screen does, so a snapshot
 * taken at open time is an empty menu.
 *
 * <p>A container screen also takes the keyboard, so the command cannot be typed while one is up.
 * Open the menu, close it, then run it.
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
	/** Ticks between readings. A slot walk is cheap; sixty a second is not, and buys nothing. */
	static final int EVERY_TICKS = 10;
	/** How many screen sightings to remember, for when the answer is "that was not a container". */
	static final int HISTORY = 12;

	private static List<String> last;
	private static String lastTitle = "";
	private static int lastSlots, lastFilled, lastTheirs;
	private static int tick;
	/** Every screen seen, container or not. The diagnostic for "nothing was captured". */
	private static final Deque<String> seen = new ArrayDeque<>();

	static void register() {
		ScreenEvents.AFTER_INIT.register((mc, screen, w, h) -> note(screen));
	}

	/**
	 * Remember that a screen existed at all.
	 *
	 * <p>EVERY screen, not only container ones. When nothing is captured the useful question is
	 * whether the menu was a container at all, and a list of what WAS seen answers it - where a
	 * filter that silently drops non-containers leaves the same empty result for two very different
	 * causes.
	 */
	private static void note(Screen screen) {
		if (screen == null) return;
		String s = LocalDateTime.now().format(DateTimeFormatter.ofPattern("HH:mm:ss")) + "  "
			+ (screen instanceof AbstractContainerScreen<?> ? "CONTAINER  " : "plain      ")
			+ screen.getClass().getName()
			+ "  \"" + screen.getTitle().getString() + "\"";
		seen.addLast(s);
		while (seen.size() > HISTORY) seen.removeFirst();
	}

	/** Called every client tick; reads the open container a few times a second. */
	static void tick(Minecraft mc) {
		if (++tick % EVERY_TICKS != 0) return;
		AbstractContainerScreen<?> cs = Screens.container();
		if (cs == null || mc.player == null) return;
		snapshot(mc, cs);
	}

	private static void snapshot(Minecraft mc, AbstractContainerScreen<?> cs) {
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
		// A MENU STILL FILLING IS NOT A BETTER READING THAN THE ONE BEFORE IT. The server sends
		// contents some ticks after the screen, so the first readings of a menu are empty - and
		// overwriting a good snapshot with an empty one is how this ends up reporting nothing.
		if (theirs == 0 && last != null && lastTitle.equals(title) && lastTheirs > 0) return;
		last = body;
		lastTitle = title;
		lastSlots = cs.getMenu().slots.size();
		lastFilled = filled;
		lastTheirs = theirs;
	}

	/**
	 * Write the last menu down.
	 *
	 * @return the lines to print in chat - a summary and a path, never the menu itself, which is the
	 *         point of writing it to a file. Never null and never empty: "nothing seen" is an answer,
	 *         and it comes with the list of what WAS seen.
	 */
	static List<String> dump(Minecraft mc) {
		List<String> out = new ArrayList<>();
		if (last == null) {
			out.add("no container menu captured. Open the one you want inspected, CLOSE it, then run"
				+ " this — a container screen takes the keyboard and cannot be read while it is up.");
			if (seen.isEmpty()) {
				out.add("...and no screen of any kind has been seen since this client started,"
					+ " which means the screen hook is not firing at all — tell me that.");
			} else {
				out.add("screens seen so far (newest last):");
				for (String s : seen) out.add("  " + s);
			}
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
