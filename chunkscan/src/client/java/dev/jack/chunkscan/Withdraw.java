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

	private static Phase phase = Phase.IDLE;
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
			close(mc);
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
			if (want != null && !item.equals(want)) continue;
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

	private static void finish(Minecraft mc) {
		phase = took > 0 ? Phase.DONE : Phase.FAILED;
		if (took == 0) note = "there was none of it in there";
		mc.player.sendSystemMessage(Component.literal("[cscan] took " + took
			+ (want == null ? " item(s)" : "x " + want)
			+ (want != null && took < target ? " (wanted " + target + ")" : "")));
	}

	private static int carrying(Minecraft mc) {
		return Work.carrying(mc.player).getOrDefault(want, 0);
	}

	private static void fail(Minecraft mc, String why) {
		phase = Phase.FAILED;
		note = why;
		if (mc.player != null) mc.player.sendSystemMessage(Component.literal("[cscan] " + why));
	}
}
