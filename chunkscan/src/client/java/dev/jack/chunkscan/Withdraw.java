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
	/**
	 * TWO WINDOWS, TWO FACTS. A chest that FAILED (empty, short, would not open) is off the table
	 * for targeting for {@link #RETRY_AFTER_MS}. A chest that WORKED is only kept from being
	 * re-OPENED for {@link #RETRY_AFTER_OK_MS} — it stays a perfectly good target, and the trip
	 * waits those few seconds rather than flying to the second-nearest chest of the same thing.
	 * One map for both made the recount two seconds later route past the chest that had just
	 * handed over a stack.
	 */
	private static final java.util.Map<Long, Long> coolUntil = new java.util.HashMap<>();
	private static final java.util.Map<Long, Long> okUntil = new java.util.HashMap<>();
	/** What the pack held of {@code want} when the current transfer was asked for. */
	private static int packBefore;
	/** Consecutive uncertain transfers this session: the reason to stop, if there is one. */
	private static int uncertainRuns;
	static final int UNCERTAIN_LIMIT = 3;
	private static BlockPos chest;
	private static String want;          // null = take everything
	private static int target;
	private static int timer;
	private static int cool;
	private static int took;
    private static boolean requested, scanOnly, awaitingTransfer;
    private static int menuId;
    private static long openRevision;
    private static InventoryTransfer transfer;
	/** Followed-build transfer evidence; an absent completion remains an intentional hard stop. */
	private static String transferJournal;
    static int reserveSlots;
    private static Object levelAtStart;
	private static String note = "";
	/**
	 * Items to put INTO the chest before anything is taken out of it - see {@link Work#dumpable}:
	 * the stacks in the pack that no cell of the design wants. The pack was never emptied of
	 * anything, so a trip could only ever bring back what fitted round the leftovers.
	 */
	private static java.util.Set<String> dump = java.util.Set.of();
	/** The transfer in flight is a deposit rather than a take. */
	private static boolean depositing;
	/** A deposit moved nothing: the chest is full, and the rest stays in the pack. */
	private static boolean dumpBlocked;
	/** Items put away this withdrawal. */
	private static int putAway;

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
		begin(at, item, count, java.util.Set.of());
	}

	/**
	 * @param dump items to put INTO the chest first - the stacks the design has no use for, so the
	 *             pack has room for what it is here to take. Put away, never dropped: the chest is
	 *             indexed and nothing is lost.
	 */
	static void begin(BlockPos at, String item, int count, java.util.Set<String> dump) {
		Withdraw.dump = dump == null ? java.util.Set.of() : java.util.Set.copyOf(dump);
		depositing = dumpBlocked = false;
		putAway = 0;
		chest = at;
		want = item == null ? null : Rules.shortName(item);
		target = count;
		timer = TIMEOUT;
		cool = 0;
		took = 0;
		note = "";
		phase = Phase.OPENING;
        requested = scanOnly = awaitingTransfer = false;
        reserveSlots = 0;
        menuId = -1;
        transfer = null;
		transferJournal = null;
        levelAtStart = null;
	}

	static void inspect(BlockPos at) {
        begin(at, null, 0);
        scanOnly = true;
    }

    static boolean unconfirmed() { return awaitingTransfer; }

    static void cancel() {
		Minecraft mc = Minecraft.getInstance();
		closeJournal(mc, "CANCELLED");
		closeOurScreen(mc);
		phase = Phase.IDLE;
		chest = null;
        awaitingTransfer = false; transfer = null;
		transferJournal = null;
	}

	/**
	 * Close a container screen WE asked for. Left open, a chest GUI halts the autopilot, the loop
	 * and the printer until a human presses Escape — and an OPENING-phase failure used to leave
	 * exactly that, because it only closed a screen whose menu id it had already recorded.
	 */
	private static void closeOurScreen(Minecraft mc) {
		if (mc == null || mc.player == null || !requested) return;
		var cs = Screens.container();
		if (cs != null && cs.getMenu() != mc.player.inventoryMenu) mc.player.closeContainer();
	}

	/**
	 * Close whatever record this withdrawal opened, whichever way it is ending.
	 *
	 * <p><b>A started record with no finish must only ever mean the client died mid-action.</b> It
	 * did not: every failure path dropped the field and wrote nothing, so a chest that no longer
	 * held what the index promised left an open record - and ActiveBuild.prepare then refused to
	 * start that design ever again, with an error nothing in this mod could resolve. Jack, on the
	 * loop going to grab materials that were not there any more: <i>"it broke it; it should move
	 * on"</i>.
	 */
	private static void closeJournal(Minecraft mc, String result) {
		if (transferJournal == null || mc == null) return;
		try {
			ActiveBuild.Snapshot revision = ChunkScanClient.printDesign == null ? null
				: ActiveBuild.current(ScanRunner.schematicsDir(mc), ChunkScanClient.printDesign);
			if (revision != null) BuildJournal.finishTransfer(revision.sourceDirectory(),
				revision.binding(), transferJournal, result, 0);
		} catch (Exception ignored) {
			// The record stays open and reconcile() closes it on the next resume. That path exists
			// precisely so a write that cannot happen now is not a design that never starts again.
		}
		transferJournal = null;
	}

	static void tick(Minecraft mc) {
        if (!busy() || !AutomationControl.enter(ActionGate.Owner.WITHDRAW)) return;
		try {
			step(mc);
		} catch (Exception e) {
			// Clicking slots in a screen the server is still filling is the one place here that can
			// throw, and it must cost the chest rather than the session.
			if (chest != null) cool(chest, RETRY_AFTER_MS);
            fail(mc, "withdrawal error: " + e);
		}
	}

	private static void step(Minecraft mc) {
		if (!busy()) return;
        if (mc.player == null || mc.level == null) { cancel(); return; }
        if (levelAtStart == null) levelAtStart = mc.level;
        if (levelAtStart != mc.level) { cancel(); return; }
		if (--timer <= 0) {
			if (awaitingTransfer) { settleFromPack(mc); close(mc); return; }
			fail(mc, "gave up at " + Wand.fmt(chest));
			return;
		}
		if (phase == Phase.OPENING) open(mc);
		else take(mc);
	}

    private static void open(Minecraft mc) {
        var cs = Screens.container();
        if (cs != null) {
            if (!requested || cs.getMenu() == mc.player.inventoryMenu
                || !ContainerWatcher.openedAt(chest, cs.getMenu().containerId)) {
                fail(mc, "unexpected container screen; withdrawal cancelled"); return;
            }
            var observed = MenuObservations.LIVE.snapshot(mc.getConnection(), cs.getMenu().containerId);
            if (observed == null || observed.revision <= openRevision) return;
            menuId = cs.getMenu().containerId;
            phase = Phase.TAKING;
            cool = CLICK_EVERY * 3;
            return;
        }
        if (requested || !mc.level.isLoaded(chest)) return;
        String n = BuiltInRegistries.BLOCK.getKey(mc.level.getBlockState(chest).getBlock()).getPath();
        if (!Storage.stores(n)) { fail(mc, "no container at " + Wand.fmt(chest)); return; }
        if ((n.equals("chest") || n.equals("trapped_chest"))
            && net.minecraft.world.level.block.ChestBlock.isChestBlockedAt(mc.level, chest)) {
            fail(mc, "the chest at " + Wand.fmt(chest) + " is blocked (something on its lid)");
            return;
        }
        BlockHitResult hit = ContainerInteraction.openingHit(mc, chest);
        if (hit == null) return;
        // SNEAK-CLICKING A CHEST PLACES THE HELD BLOCK ON ITS FACE. The autopilot's descent key is
        // sneak, and this only ever worked because its release ran earlier in the same tick.
        if (mc.player.isShiftKeyDown()) return;
        ContainerWatcher.expect(mc, chest);
        openRevision = MenuObservations.LIVE.revision();
        requested = true;
        mc.gameMode.useItemOn(mc.player, InteractionHand.MAIN_HAND, hit);
    }

	private static void take(Minecraft mc) {
		AbstractContainerScreen<?> cs = Screens.container();
		if (cs == null) {                            // closed under us; count what we got
            if (awaitingTransfer) settleFromPack(mc);
            finish(mc);
			return;
		}
		if (cs.getMenu().containerId != menuId) { fail(mc, "container changed during withdrawal"); return; }
        var observed = MenuObservations.LIVE.snapshot(mc.getConnection(), menuId);
        if (observed == null) return;
        if (awaitingTransfer) {
            var result = transfer.reconcile(observed);
            if (result == InventoryTransfer.Result.CONFLICT) {
                // Something else moved items while we were not looking — litematica-printer
                // taking from the pack, a hopper under the chest. The PACK is still the truth
                // about what we hold, so count from it and cool the chest rather than ending
                // the night over a bookkeeping disagreement.
                settleFromPack(mc);
                close(mc);
                return;
            }
            awaitingTransfer = false;
			if (!journalTransfer(mc, result == InventoryTransfer.Result.CONFIRMED ? "CONFIRMED" : "NO_CHANGE",
				transfer.moved())) return;
            if (depositing) {
                // A DEPOSIT THAT MOVED NOTHING IS A FULL CHEST, not a reason to leave: the rest
                // of the pack stays as it is and the taking goes ahead with the room there is.
                depositing = false;
                if (result == InventoryTransfer.Result.NO_CHANGE) {
                    dumpBlocked = true;
                    if (mc.player != null) mc.player.sendSystemMessage(Component.literal("[cscan] "
                        + Wand.fmt(chest) + " has no room for what I wanted to put away - keeping it"));
                } else {
                    putAway += transfer.moved();
                }
                transfer = null;
                timer = TIMEOUT;
                uncertainRuns = 0;
            } else {
                if (result == InventoryTransfer.Result.NO_CHANGE) { transfer = null; close(mc); return; }
                took += transferredUnits(transfer.item(), transfer.moved());
                transfer = null;
                timer = TIMEOUT;
                uncertainRuns = 0;
            }
        }
        if (want != null && carrying(mc) >= target) {
			close(mc);                               // got what we came for
			return;
		}
		if (cool-- > 0) return;
        if (scanOnly) { close(mc); return; }
        cool = CLICK_EVERY;

        // A slot update or manual click since the full snapshot invalidates the baseline.
        if (observed.size() != cs.getMenu().slots.size()) { fail(mc, "container layout changed"); return; }
        if (!cs.getMenu().getCarried().isEmpty()) { fail(mc, "cursor holds an item; withdrawal paused"); return; }
        for (Slot slot : cs.getMenu().slots) {
            if (!ItemStack.matches(slot.getItem(), observed.stack(slot.index))) { reopen(mc); return; }
        }
		Inventory inv = mc.player.getInventory();
        // ---- PUT AWAY FIRST. What the design has no use for goes into this chest before anything
        // comes out of it, one stack a pass exactly as taking is - and BEFORE the room check below,
        // because a pack full of the wrong thing is precisely when there is no room.
        if (!dump.isEmpty() && !dumpBlocked) {
            for (Slot s : cs.getMenu().slots) {
                if (s.container != inv) continue;
                ItemStack st = s.getItem();
                if (st.isEmpty()) continue;
                String item = BuiltInRegistries.ITEM.getKey(st.getItem()).getPath();
                if (!dump.contains(item)) continue;
                depositing = true;
                startTransfer(mc, cs, inv, s, item, st.getCount(), true);
                return;
            }
        }
        if (want != null && Work.room(mc.player, want) <= 0) { close(mc); return; }
        if (reserveSlots > 0) {
            int empty = 0;
            for (int i = 0; i < 36; i++) if (inv.getItem(i).isEmpty()) empty++;
            if (empty <= reserveSlots) { close(mc); return; }
        }
		// LOOSE STACKS FIRST, and a box only when it is worth the trip through Unbox: a box is a
		// slot, a place-open-take-break cycle, and a risk, so one holding a handful of what we
		// want is not a source. And a box needs an EMPTY slot to land in — a partial stack of the
		// wanted item is room for the item and no room at all for a box.
		Slot boxed = null;
		for (Slot s : cs.getMenu().slots) {
			if (s.container == inv) continue;        // that half is already ours
			ItemStack st = s.getItem();
			if (st.isEmpty()) continue;
			String item = BuiltInRegistries.ITEM.getKey(st.getItem()).getPath();
			if (want != null && !item.equals(want)) {
				if (boxed == null && holdsWanted(st) && boxedCount(st) >= BOX_WORTH
					&& emptySlots(inv) > 0) boxed = s;
				continue;
			}
			startTransfer(mc, cs, inv, s, item, st.getCount(), false);
			return;                                  // one stack a pass, then re-read the screen
		}
		if (boxed != null) {
			ItemStack st = boxed.getItem();
			startTransfer(mc, cs, inv, boxed, BuiltInRegistries.ITEM.getKey(st.getItem()).getPath(),
				st.getCount(), false);
			return;
		}
		close(mc);                                   // nothing of ours left in there
	}

	/**
	 * Ask the server to move one stack, and remember what the pack held when we asked.
	 *
	 * @param toChest a DEPOSIT: the stack is one of ours and the destination is the chest's half of
	 *                the menu. A shift-click is the same gesture either way; only the slots it is
	 *                reconciled against differ.
	 */
	private static void startTransfer(Minecraft mc, AbstractContainerScreen<?> cs, Inventory inv,
	                                  Slot s, String item, int count, boolean toChest) {
		var observed = MenuObservations.LIVE.snapshot(mc.getConnection(), menuId);
		var destination = cs.getMenu().slots.stream()
			.filter(slot -> (slot.container == inv) != toChest)
			.map(slot -> slot.index).toList();
		transfer = new InventoryTransfer(observed, s.index, destination);
		packBefore = carrying(mc);
		if (!journalTransferStart(mc, chest, item, count)) return;
		awaitingTransfer = true;
		mc.gameMode.handleContainerInput(cs.getMenu().containerId, s.index, 0,
			ContainerInput.QUICK_MOVE, mc.player);
		reopen(mc);
	}

	/** A box is only a source of {@code want} if it holds at least this much of it. */
	static final int BOX_WORTH = 64;

	private static int boxedCount(ItemStack st) {
		return st.getOrDefault(net.minecraft.core.component.DataComponents.CONTAINER,
				net.minecraft.world.item.component.ItemContainerContents.EMPTY)
			.nonEmptyItemCopyStream()
			.filter(in -> BuiltInRegistries.ITEM.getKey(in.getItem()).getPath().equals(want))
			.mapToInt(ItemStack::getCount).sum();
	}

	private static int emptySlots(Inventory inv) {
		int empty = 0;
		for (int i = 0; i < 36; i++) if (inv.getItem(i).isEmpty()) empty++;
		return empty;
	}

	/**
	 * The transfer's answer never came, or came back inconsistent. The pack did not lie: whatever
	 * it holds more of than it did when the click went out is what arrived. Counted, journalled as
	 * UNCERTAIN, and the chest cooled — the session goes on. Only a RUN of these is evidence that
	 * something is wrong with the world rather than with one click.
	 */
	private static void settleFromPack(Minecraft mc) {
		int gained = Math.max(0, carrying(mc) - packBefore);
		took += gained;
		awaitingTransfer = false;
		transfer = null;
		journalTransfer(mc, "UNCERTAIN", gained);
		if (chest != null) cool(chest, RETRY_AFTER_MS);
		if (++uncertainRuns >= UNCERTAIN_LIMIT) {
			uncertainRuns = 0;
			if (mc.player != null) mc.player.sendSystemMessage(Component.literal("[cscan] "
				+ UNCERTAIN_LIMIT + " withdrawals in a row could not be confirmed — the server is"
				+ " not answering container clicks; stopping so nothing is lost"));
			Hud.stopForSafety(mc);
		}
	}

    private static void reopen(Minecraft mc) {
        // Successful vanilla prediction may produce no slot echo. Reopen requests a fresh full view.
        mc.player.closeContainer();
        phase = Phase.OPENING;
        requested = false;
        menuId = -1;
    }

	private static boolean journalTransferStart(Minecraft mc, BlockPos at, String item, int expected) {
		ActiveBuild.Snapshot revision = ChunkScanClient.printDesign == null ? null
			: ActiveBuild.current(ScanRunner.schematicsDir(mc), ChunkScanClient.printDesign);
		if (revision == null) return true;
		try {
			transferJournal = BuildJournal.beginTransfer(revision.sourceDirectory(), revision.binding(), at, item, expected);
			return true;
		} catch (java.io.IOException unavailable) {
			fail(mc, "withdrawal journal unavailable; automation stopped");
			Hud.stopForSafety(mc);                  // and the session note, or the next join resumes into it
			return false;
		}
	}

	private static boolean journalTransfer(Minecraft mc, String result, int moved) {
		if (transferJournal == null) return true;
		ActiveBuild.Snapshot revision = ChunkScanClient.printDesign == null ? null
			: ActiveBuild.current(ScanRunner.schematicsDir(mc), ChunkScanClient.printDesign);
		if (revision == null) { Hud.off(); return false; }
		try {
			BuildJournal.finishTransfer(revision.sourceDirectory(), revision.binding(), transferJournal, result, moved);
			transferJournal = null;
			return true;
		} catch (java.io.IOException unavailable) {
			// Start record remains. Do not let an unaccounted transfer feed a placement plan.
			if (mc.player != null) mc.player.sendSystemMessage(net.minecraft.network.chat.Component.literal(
				"[cscan] the withdrawal journal cannot be written (" + unavailable + ") — stopping"));
			Hud.stopForSafety(mc);
			return false;
		}
	}

    private static int transferredUnits(ItemStack stack, int count) {
        if (want == null || BuiltInRegistries.ITEM.getKey(stack.getItem()).getPath().equals(want)) return count;
        return count * stack.getOrDefault(net.minecraft.core.component.DataComponents.CONTAINER,
            net.minecraft.world.item.component.ItemContainerContents.EMPTY).nonEmptyItemCopyStream()
            .filter(inner -> BuiltInRegistries.ITEM.getKey(inner.getItem()).getPath().equals(want))
            .mapToInt(ItemStack::getCount).sum();
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
		if (scanOnly) { phase = Phase.DONE; return; }
        boolean short_ = want != null && carrying(mc) < target;
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
			if (took == 0 || short_) cool(chest, RETRY_AFTER_MS);
			else okUntil.put(chest.asLong(), System.currentTimeMillis() + RETRY_AFTER_OK_MS);
		}
		String stored = putAway > 0 ? " — put away " + putAway + " item(s) the design has no use for" : "";
		if (took > 0 || want == null) {
			mc.player.sendSystemMessage(Component.literal("[cscan] took " + took
				+ (want == null ? " item(s)" : "x " + want)
				+ (short_ ? " of " + target + " — looking elsewhere for the rest" : "") + stored));
		} else {
			// Nothing taken is worth saying, but not as "took 0": say WHY, or it reads as a failure
			// of the taking rather than of the index that sent you here.
			mc.player.sendSystemMessage(Component.literal("[cscan] no " + want + " in "
				+ Wand.fmt(chest) + " — the index was out of date. Trying elsewhere." + stored));
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
	/** Not to be OPENED now: it failed recently, or it was used moments ago and needs a beat. */
	static boolean recentlyFailed(BlockPos at, long now) {
		Long until = coolUntil.get(at.asLong());
		if (until != null && now < until) return true;
		Long ok = okUntil.get(at.asLong());
		return ok != null && now < ok;
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
		okUntil.clear();
		uncertainRuns = 0;
	}

	/** Record a failure without a live client, so the cooldown itself can be tested. */
	static void noteFailureForTest(BlockPos at) {
		noteFailure(at);
	}

	/**
	 * Record that this container could not be used — a chest with no cell to open it from is as
	 * useless to a trip as an empty one, and must be passed over for the same window.
	 */
	static void noteFailure(BlockPos at) {
		cool(at, RETRY_AFTER_MS);
	}

	private static void fail(Minecraft mc, String why) {
		// The record this attempt opened is closed here, whatever went wrong. See closeJournal.
		closeJournal(mc, "FAILED");
		BlockPos failedChest = chest;
		if (awaitingTransfer) settleFromPack(mc);
		closeOurScreen(mc);
		chest = failedChest;
		phase = Phase.FAILED;
		awaitingTransfer = false;
		transfer = null;
		if (chest != null) cool(chest, RETRY_AFTER_MS);
		note = why;
		if (mc.player != null) mc.player.sendSystemMessage(Component.literal("[cscan] " + why));
	}
}
