package dev.jack.chunkscan;

import net.fabricmc.fabric.api.client.screen.v1.ScreenEvents;
import net.minecraft.client.gui.screens.inventory.AbstractContainerScreen;

/**
 * Which screen is open, because 26.2 has no {@code Minecraft.screen} accessor.
 *
 * <p>This file's own notes said so and I reached for it twice in one session anyway. Tracked from
 * the screen events instead — the same thing {@link ContainerWatcher} has always done, now in one
 * place so the next caller does not invent a third copy.
 */
final class Screens {
	private static AbstractContainerScreen<?> container;
	private static boolean any;

	private Screens() {}

	static void register() {
		ScreenEvents.AFTER_INIT.register((mc, screen, w, h) -> {
			any = true;
			if (screen instanceof AbstractContainerScreen<?> cs) container = cs;
			ScreenEvents.remove(screen).register(s -> {
				any = false;
				if (s == container) container = null;
			});
		});
	}

	/** The open container screen, or null. The player's own inventory counts — see the caller. */
	static AbstractContainerScreen<?> container() {
		return container;
	}

	/**
	 * Any screen at all, including chat and the pause menu.
	 *
	 * <p>No callers today, deliberately: {@link Autopilot} used this and stopping for chat is what
	 * made "I opened chat and the loop parked" a bug. Kept because the distinction is the useful
	 * part — if you reach for this, check that you do not mean {@link #container()}.
	 */
	static boolean anyOpen() {
		return any;
	}
}
