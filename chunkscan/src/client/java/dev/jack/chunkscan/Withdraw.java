package dev.jack.chunkscan;

import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.screens.inventory.AbstractContainerScreen;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.network.chat.Component;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.inventory.ContainerInput;
import net.minecraft.world.inventory.Slot;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.Vec3;

/**
 * Open a container and shift-click stacks out of it.
 *
 * <p>Built for the chest move and the consolidation `tidy` computes — 37 containers to relocate and
 * 135 piles split across chests — and it is also what the build loop's fetch phase uses to restock
 * itself. Both are stated plainly because they are both true.
 *
 * <p>A state machine rather than a loop, because opening a chest is not synchronous: you send a
 * use-item, the server decides, the screen arrives a few ticks later, and its contents arrive later
 * still. Clicking slots before the server has filled them takes nothing and looks like a desync.
 *
 * <p><b>26.2 renamed this whole area</b>, and every name below was checked against the jar rather
 * than remembered:
 *
 * <pre>
 *   handleInventoryMouseClick(...)  ->  MultiPlayerGameMode.handleContainerInput(
 *                                           containerId, slotIndex, button, ContainerInput, player)
 *   ClickType.QUICK_MOVE            ->  ContainerInput.QUICK_MOVE     (this is the shift-click)
 *   Player.closeContainer()         ->  protected; LocalPlayer overrides it public
 * </pre>
 */
final class Withdraw {
	/** Ticks to give up after. Covers flying in, the server's reply, and the contents arriving. */
	static final int TIMEOUT = 100;
	/** Ticks between clicks. Emptying a double chest in one tick is not a person. */
	static final int CLICK_EVERY = 2;
	/** Vanilla reach is about 4.5 and the server checks it. */
	static final double REACH = 4.5;

	enum Phase { IDLE, OPENING, TAKING, DONE, FAILED }

	/**
	 * How long a chest that failed is left alone before it is tried again.
	 *
	 * <p>The first version had a single global FAILED phase and the caller gated on it, so ONE bad
	 * chest disabled restocking for the whole session — the loop flew there and sat forever. On an
	 * unattended alt that is an hour of nothing, and nothing in the log to say why.
	 *
	 * <p>Failure is a property of a CHEST, not of the withdrawer.
	 */
	static final long RETRY_AFTER_MS = 60_000;
	/**
	 * ...and a much shorter one for a chest that WORKED.
	 *
	 * <p>These are different facts and collapsing them into one number was a regression. The long
	 * window exists because a chest that had nothing has nothing now either. A chest that handed over
	 * exactly what was asked for has, on this island, thousands more in it — the store hall is piles
	 * of one item — so blacklisting it for a minute sends the next pack-load to a worse chest or
	 * reports nothing fetchable at all.
	 *
	 * <p>It cannot be zero: the only reason a successful chest is marked at all is to stop the
	 * recount two seconds later opening it again, finding what it wanted already in the pack, and
	 * reporting `took 0x`. Anything over one recount does that, and five seconds is two.
	 */
	static final long RETRY_AFTER_OK_MS = 5_000;

	private static Phase phase = Phase.IDLE;
	/** Position -> the time it becomes worth trying again. An EXPIRY, because the wait now varies. */
	private static final java.util.Map<Long, Long> coolUntil = new java.util.HashMap<>();
	private static BlockPos chest;
	private static String want;          // null = take everything
	private static int target;
	private static int timer;
	private static int cool;
	private static int took;
	private static String note = "";

	private Withdraw() {}

	static Phase phase() {
		return phase;
	}

	static boolean busy() {
		return phase == Phase.OPENING || phase == Phase.TAKING;
	}

	static String note() {
		return note;
	}

	static int took() {
		return took;
	}

	/**
	 * Take from the container at `at`.
	 *
	 * @param item  block name to take, or null for everything in there
	 * @param count stop once carrying this many; ignored when `item` is null
	 */
	static void begin(BlockPos at, String item, int count) {
		chest = at;
		want = item == null ? null : Rules.shortName(item);
		target = count;
		timer = TIMEOUT;
		cool = 0;
		took = 0;
		note = "";
		phase = Phase.OPENING;
	}

	static void cancel() {
		phase = Phase.IDLE;
		chest = null;
	}

	static void tick(Minecraft mc) {
		try {
			step(mc);
		} catch (Exception e) {
			// Clicking slots in a screen the server is still filling is the one place here that can
			// throw, and it must cost the chest rather than the session.
			if (chest != null) cool(chest, RETRY_AFTER_MS);
			phase = Phase.FAILED;
			note = String.valueOf(e);
		}
	}

	private static void step(Minecraft mc) {
		if (!busy() || mc.player == null || mc.level == null) return;
		if (--timer <= 0) {
			fail(mc, "gave up at " + Wand.fmt(chest));
			return;
		}
		if (phase == Phase.OPENING) open(mc);
		else take(mc);
	}

	private static void open(Minecraft mc) {
		if (Screens.container() != null) {          // it opened
			phase = Phase.TAKING;
			cool = CLICK_EVERY * 2;                 // let the server fill it before clicking
			return;
		}
		if (Math.sqrt(mc.player.blockPosition().distSqr(chest)) > REACH) return;   // still flying in
		String n = BuiltInRegistries.BLOCK.getKey(mc.level.getBlockState(chest).getBlock()).getPath();
		if (!Storage.stores(n)) {
			fail(mc, "no container at " + Wand.fmt(chest) + " any more (" + n + ")");
			return;
		}
		mc.gameMode.useItemOn(mc.player, InteractionHand.MAIN_HAND,
			new BlockHitResult(Vec3.atCenterOf(chest), Direction.UP, chest, false));
	}

	private static void take(Minecraft mc) {
		AbstractContainerScreen<?> cs = Screens.container();
		if (cs == null) {                            // closed under us; count what we got
			finish(mc);
			return;
		}
		if (want != null && carrying(mc) >= target) {
			close(mc);                               // got what we came for
			return;
		}
		if (cool-- > 0) return;
		cool = CLICK_EVERY;

		Inventory inv = mc.player.getInventory();
		for (Slot s : cs.getMenu().slots) {
			if (s.container == inv) continue;        // that half is already ours
			ItemStack st = s.getItem();
			if (st.isEmpty()) continue;
			String item = BuiltInRegistries.ITEM.getKey(st.getItem()).getPath();
			// A SHULKER BOX THAT HOLDS WHAT WE CAME FOR IS WHAT WE CAME FOR. Bulk storage on this
			// island is boxes in chests, and a fetch that walks past six shulkers of stone brick to
			// find sixty-four loose ones is not a fetch. Taking the box is the first half; `Work.
			// boxed` then tells you to set it down, because a client mod cannot unpack it for you.
			if (want != null && !item.equals(want) && !holdsWanted(st)) continue;
			// QUICK_MOVE is the shift-click: the whole stack, straight into the pack.
			mc.gameMode.handleContainerInput(cs.getMenu().containerId, s.index, 0,
				ContainerInput.QUICK_MOVE, mc.player);
			took += st.getCount();
			return;                                  // one stack a pass, then re-read the screen
		}
		close(mc);                                   // nothing of ours left in there
	}

	private static void close(Minecraft mc) {
		mc.player.closeContainer();                  // public on LocalPlayer; protected on Player
		finish(mc);
	}

	/**
	 * TAKE WHAT IS THERE AND MOVE ON.
	 *
	 * <p>The index is a memory of the last time the chest was opened, so it routinely promises more
	 * than the chest holds — it said 150 and there were 64. Demanding the exact number would leave
	 * the loop asking a chest for something it does not have; instead the shortfall stays in the
	 * plan and the NEXT recount looks for it somewhere else.
	 *
	 * <p>Either way the chest goes into the cooling-off set. Emptied or merely short, there is no
	 * reason to come back to it this trip, and coming back is what produced the freeze.
	 */
	private static void finish(Minecraft mc) {
		boolean short_ = want != null && took < target;
		phase = took > 0 ? Phase.DONE : Phase.FAILED;
		if (took == 0) note = "there was none of it in there";
		else if (short_) note = "took " + took + " of " + target + "; the rest is elsewhere";
		// LEAVE THIS CHEST ALONE FOR A WHILE, whatever happened — emptied, short, or exactly what we
		// came for. There is no version of "come straight back to the chest I have just been through"
		// that is useful, and it produced a real bug: the loop finished a withdrawal, the phase left
		// `busy()`, the next recount two seconds later saw itself still standing at the chest and
		// began a SECOND withdrawal, which found nothing of what it asked for and reported
		//
		//     [cscan] took 0x stone_bricks
		//
		// straight after a successful one. The items were in the pack; the message was about the
		// pointless second trip. Worse, that second pass then blacklisted a chest that had just
		// worked.
		if (chest != null) {
			// Emptied or short: it has no more, leave it alone properly. Gave us what we asked for:
			// just long enough not to open it again on the next recount.
			cool(chest, took == 0 || short_ ? RETRY_AFTER_MS : RETRY_AFTER_OK_MS);
		}
		if (took > 0 || want == null) {
			mc.player.sendSystemMessage(Component.literal("[cscan] took " + took
				+ (want == null ? " item(s)" : "x " + want)
				+ (short_ ? " of " + target + " — looking elsewhere for the rest" : "")));
		} else {
			// Nothing taken is worth saying, but not as "took 0": say WHY, or it reads as a failure
			// of the taking rather than of the index that sent you here.
			mc.player.sendSystemMessage(Component.literal("[cscan] no " + want + " in "
				+ Wand.fmt(chest) + " — the index was out of date. Trying elsewhere."));
		}
	}

	/** Is this a container item with the wanted block inside it? */
	private static boolean holdsWanted(ItemStack st) {
		if (want == null || !Storage.isBox(BuiltInRegistries.ITEM.getKey(st.getItem()).getPath())) {
			return false;
		}
		return st.getOrDefault(net.minecraft.core.component.DataComponents.CONTAINER,
				net.minecraft.world.item.component.ItemContainerContents.EMPTY)
			.nonEmptyItemCopyStream()
			.anyMatch(in -> BuiltInRegistries.ITEM.getKey(in.getItem()).getPath().equals(want));
	}

	private static int carrying(Minecraft mc) {
		// Boxed ones count toward the target: we have fetched them, even though setting the box
		// down is still on the player. Without this the withdrawal keeps taking boxes for ever.
		return Work.carrying(mc.player).getOrDefault(want, 0)
			+ Work.boxed(mc.player).getOrDefault(want, 0);
	}

	/**
	 * Is this particular chest in its cooling-off period?
	 *
	 * <p>"Cooling off" now means "been there this trip", not only "failed there": see {@link #finish}.
	 * The window has to expire either way — a chest can be refilled and a timeout can be lag, so a
	 * permanent mark turns a hiccup into a dead session.
	 */
	static boolean recentlyFailed(BlockPos at, long now) {
		Long until = coolUntil.get(at.asLong());
		return until != null && now < until;
	}

	private static void cool(BlockPos at, long ms) {
		coolUntil.put(at.asLong(), System.currentTimeMillis() + ms);
	}

	/** Positions still cooling off, so the planner can route round them rather than at them. */
	static java.util.Set<Long> coolingOff(long now) {
		java.util.Set<Long> out = new java.util.HashSet<>();
		for (var e : coolUntil.entrySet()) {
			if (now < e.getValue()) out.add(e.getKey());
		}
		return out;
	}

	static void clearFailures() {
		coolUntil.clear();
	}

	/** Record a failure without a live client, so the cooldown itself can be tested. */
	static void noteFailureForTest(BlockPos at) {
		cool(at, RETRY_AFTER_MS);
	}

	private static void fail(Minecraft mc, String why) {
		phase = Phase.FAILED;
		if (chest != null) cool(chest, RETRY_AFTER_MS);
		note = why;
		if (mc.player != null) mc.player.sendSystemMessage(Component.literal("[cscan] " + why));
	}
}
