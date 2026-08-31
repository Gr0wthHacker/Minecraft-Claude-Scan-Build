package dev.jack.chunkscan;

import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.screens.inventory.AbstractContainerScreen;
import net.minecraft.client.player.LocalPlayer;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.component.DataComponents;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.inventory.ContainerInput;
import net.minecraft.world.inventory.Slot;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.component.ItemContainerContents;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.Vec3;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Takes what is inside a shulker box you are carrying: set it down, empty it, pick it up.
 *
 * <p>This mod has said for a long time that a boxed block *"is not placeable until you set the box
 * down"* and that *"a client mod cannot unpack one for you"*. The first half is true and the second
 * is not — it is the same mistake as *"a client mod cannot place a block"*, which turned out to be
 * a policy rather than a fact. Placing, opening, emptying and breaking a box are four things this
 * mod already knows how to do separately.
 *
 * <p>It matters because <b>bulk storage on this island IS boxes in chests</b>. The index already
 * reads their contents into {@code inBoxes}, {@link Plan} already subtracts them from a shortfall
 * so you are not sent shopping for something you own — and then the loop stopped, because the last
 * step needed hands.
 *
 * <p><b>A SHULKER BOX IS THE MOST DANGEROUS BLOCK IN THE GAME TO AUTOMATE.</b> Everything else here
 * risks one block; this risks a whole inventory, and the failure is silent. So the rules are hard
 * refusals, not warnings:
 *
 * <ul>
 *   <li><b>NEVER over the void.</b> {@link VoidRisk} already knows what falls for ever. A dropped
 *       block is a block; a dropped shulker is everything that was in it.</li>
 *   <li><b>Only ever break a box THIS ROUTINE PLACED, at the exact cell it placed it.</b> Not "a
 *       shulker box nearby" — the island is full of placed boxes that are somebody's storage.</li>
 *   <li><b>The box must come back.</b> After breaking, the pack is checked for it, and if it is not
 *       there the whole thing STOPS and says so loudly rather than moving on. An unrecovered box is
 *       not a failed step, it is a lost chest.</li>
 *   <li><b>It places into AIR only</b>, on a solid support, in reach, inside the plot.</li>
 * </ul>
 */
final class Unbox {
	static final int STEP_TICKS = 4;
	/** Long enough for a slow server to answer, short enough that a wedged run is noticed. */
	static final int GIVE_UP_TICKS = 200;

	enum Phase { IDLE, PLACING, OPENING, TAKING, BREAKING, RECOVERING, DONE, FAILED }

	private static Phase phase = Phase.IDLE;
	private static String want = "";
	private static int wanted, got;
	private static BlockPos where;
	private static String boxItem = "";
	private static int boxesBefore;
	private static long nextAt;
	private static int waited;
	private static String why = "";
	private static boolean counting;
	private static int beforeTake;

	private Unbox() {}

	static Phase phase() {
		return phase;
	}

	static boolean running() {
		return phase != Phase.IDLE && phase != Phase.DONE && phase != Phase.FAILED;
	}

	static String status() {
		if (phase == Phase.IDLE) return "idle";
		return phase.name().toLowerCase(java.util.Locale.ROOT) + " " + got + "/" + wanted + "x "
			+ want + (why.isBlank() ? "" : " — " + why);
	}

	static void stop() {
		phase = Phase.IDLE;
		where = null;
		why = "";
	}

	/** Which hotbar slot holds a shulker box containing `item`, or -1. */
	static int boxWith(LocalPlayer p, String item) {
		String w = Rules.shortName(item);
		for (int i = 0; i < 9; i++) {
			ItemStack st = p.getInventory().getItem(i);
			if (st.isEmpty()) continue;
			String n = BuiltInRegistries.ITEM.getKey(st.getItem()).getPath();
			if (!n.contains("shulker_box")) continue;
			ItemContainerContents c = st.getOrDefault(DataComponents.CONTAINER,
				ItemContainerContents.EMPTY);
			boolean has = c.nonEmptyItemCopyStream().anyMatch(
				inner -> BuiltInRegistries.ITEM.getKey(inner.getItem()).getPath().equals(w));
			if (has) return i;
		}
		return -1;
	}

	/** How many of `item` sit inside boxes in the pack — the number this can actually recover. */
	static int boxedCount(LocalPlayer p, String item) {
		return Work.boxed(p).getOrDefault(Rules.shortName(item), 0);
	}

	/**
	 * A cell to stand the box in: air, supported, in reach, inside the plot, NOT over the void.
	 *
	 * <p>Returns null rather than guessing. Standing a shulker somewhere it can fall is how an
	 * inventory is lost, and there is always the option of doing nothing.
	 */
	static BlockPos site(Minecraft mc) {
		LocalPlayer p = mc.player;
		if (p == null || mc.level == null) return null;
		BlockPos me = p.blockPosition();
		for (int r = 1; r <= 3; r++) {
			for (Direction d : Direction.Plane.HORIZONTAL) {
				for (int dy = 0; dy >= -1; dy--) {
					BlockPos c = me.relative(d, r).offset(0, dy, 0);
					if (!mc.level.getBlockState(c).isAir()) continue;
					BlockPos below = c.below();
					if (!mc.level.getBlockState(below).blocksMotion()) continue;
					if (Rules.isProtected(BuiltInRegistries.BLOCK
						.getKey(mc.level.getBlockState(below).getBlock()).toString())) continue;
					if (Islands.outside(ScanRunner.schematicsDir(mc), c.getX(), c.getZ())) continue;
					// A DROPPED BLOCK IS A BLOCK; A DROPPED SHULKER IS EVERYTHING IN IT.
					VoidRisk.Cell under = VoidRisk.under(mc.level, c, mc.level.getMinY());
					if (under.verdict() != VoidRisk.Verdict.CAUGHT || under.drop() > 3) continue;
					if (p.getEyePosition().distanceToSqr(Vec3.atCenterOf(c)) > 16.0) continue;
					return c;
				}
			}
		}
		return null;
	}

	static String start(Minecraft mc, String item, int count) {
		LocalPlayer p = mc.player;
		if (p == null) return "no player";
		want = Rules.shortName(item);
		wanted = Math.max(1, count);
		got = 0;
		why = "";
		counting = false;
		waited = 0;
		int slot = boxWith(p, want);
		if (slot < 0) {
			phase = Phase.FAILED;
			return "no shulker box in your HOTBAR holds " + want
				+ " (it places what you hold, so put the box on the bar)";
		}
		where = site(mc);
		if (where == null) {
			phase = Phase.FAILED;
			return "nowhere safe to set the box down — needs air on solid ground, in reach, "
				+ "inside the plot, and NOT over the void";
		}
		boxItem = BuiltInRegistries.ITEM.getKey(p.getInventory().getItem(slot).getItem()).getPath();
		boxesBefore = count(p, boxItem);
		phase = Phase.PLACING;
		nextAt = 0;
		return "unboxing " + wanted + "x " + want + " at " + Wand.fmt(where)
			+ " — it will be broken and picked back up";
	}

	private static int count(LocalPlayer p, String item) {
		int n = 0;
		for (ItemStack st : p.getInventory()) {
			if (!st.isEmpty()
				&& BuiltInRegistries.ITEM.getKey(st.getItem()).getPath().equals(item)) {
				n += st.getCount();
			}
		}
		return n;
	}

	/** One step. Returns a line worth saying, or null. */
	static String tick(Minecraft mc) {
		if (!running() || mc.player == null || mc.level == null) return null;
		if (mc.level.getGameTime() < nextAt) return null;
		nextAt = mc.level.getGameTime() + STEP_TICKS;
		if (++waited > GIVE_UP_TICKS) {
			phase = Phase.FAILED;
			why = "took too long";
			return "unbox gave up at " + Wand.fmt(where) + " — check the box is not still on the ground";
		}
		LocalPlayer p = mc.player;
		return switch (phase) {
			case PLACING -> place(mc, p);
			case OPENING -> open(mc, p);
			case TAKING -> take(mc, p);
			case BREAKING -> breakIt(mc, p);
			case RECOVERING -> recover(mc, p);
			default -> null;
		};
	}

	private static String place(Minecraft mc, LocalPlayer p) {
		if (!mc.level.getBlockState(where).isAir()) {
			phase = Phase.OPENING;                      // it is already down
			return null;
		}
		int slot = boxWith(p, want);
		if (slot < 0) {
			phase = Phase.FAILED;
			why = "the box left your hotbar";
			return "unbox stopped: " + why;
		}
		Direction face = null;
		for (Direction d : Direction.values()) {
			if (mc.level.getBlockState(where.relative(d)).blocksMotion()) {
				face = d.getOpposite();
				break;
			}
		}
		if (face == null) {
			phase = Phase.FAILED;
			why = "nothing to place the box against";
			return "unbox stopped: " + why;
		}
		int was = p.getInventory().getSelectedSlot();
		p.getInventory().setSelectedSlot(slot);
		BlockPos nb = where.relative(face.getOpposite());
		mc.gameMode.useItemOn(p, InteractionHand.MAIN_HAND,
			new BlockHitResult(Vec3.atCenterOf(nb), face, nb, false));
		p.swing(InteractionHand.MAIN_HAND);
		p.getInventory().setSelectedSlot(was);
		return null;
	}

	private static String open(Minecraft mc, LocalPlayer p) {
		if (Screens.container() instanceof AbstractContainerScreen<?>) {
			phase = Phase.TAKING;
			return null;
		}
        if (mc.level.getBlockState(where).isAir()) {
			phase = Phase.PLACING;                      // it never went down
			return null;
		}
		mc.gameMode.useItemOn(p, InteractionHand.MAIN_HAND,
			new BlockHitResult(Vec3.atCenterOf(where), Direction.UP, where, false));
		return null;
	}

	private static String take(Minecraft mc, LocalPlayer p) {
		if (counting) {
			counting = false;
			got += Math.max(0, count(p, want) - beforeTake);
		}
		if (!(Screens.container() instanceof AbstractContainerScreen<?> cs)) {
			phase = Phase.BREAKING;                     // closed, by us or by the server
			return null;
		}
		var inv = p.getInventory();
		for (int i = 0; i < cs.getMenu().slots.size(); i++) {
			Slot s = cs.getMenu().slots.get(i);
			if (s.container == inv) continue;
			ItemStack st = s.getItem();
			if (st.isEmpty()) continue;
			if (!BuiltInRegistries.ITEM.getKey(st.getItem()).getPath().equals(want)) continue;
			// COUNTED FROM THE PACK ON A LATER TICK, NOT FROM THE SLOT NOW. `st.getCount()` is what
			// the server is being ASKED to move, and a full pack moves less; the Crafter shipped
			// exactly this race a few hours ago and reported zero for ever. Here it would only
			// overstate a message, which is a smaller lie and still a lie.
			beforeTake = count(p, want);
			mc.gameMode.handleContainerInput(cs.getMenu().containerId, i, 0,
				ContainerInput.QUICK_MOVE, p);
			counting = true;
			return null;
		}
		// nothing left worth taking
		p.closeContainer();
		phase = Phase.BREAKING;
		return null;
	}

	private static String breakIt(Minecraft mc, LocalPlayer p) {
		if (mc.level.getBlockState(where).isAir()) {
			phase = Phase.RECOVERING;
			return null;
		}
		// ONLY THE CELL WE PLACED INTO. The island is full of shulker boxes that are somebody's
		// storage, and "a shulker box nearby" is not a thing this may ever break.
		String n = BuiltInRegistries.BLOCK.getKey(mc.level.getBlockState(where).getBlock()).getPath();
		if (!n.contains("shulker_box")) {
			phase = Phase.FAILED;
			why = "the cell holds " + n + ", not our box";
			return "unbox stopped: " + why;
		}
		mc.gameMode.startDestroyBlock(where, Direction.UP);
		mc.gameMode.continueDestroyBlock(where, Direction.UP);
		p.swing(InteractionHand.MAIN_HAND);
		return null;
	}

	private static String recover(Minecraft mc, LocalPlayer p) {
		// THE BOX MUST COME BACK. An unrecovered shulker is not a failed step, it is a lost chest,
		// so this stops the whole routine rather than reporting a shortfall and carrying on.
		if (count(p, boxItem) >= boxesBefore) {
			phase = Phase.DONE;
			String w = want;
			int g = got;
			return "unboxed " + g + "x " + w + " and got the box back";
		}
		if (waited > GIVE_UP_TICKS - 40) {
			phase = Phase.FAILED;
			why = "THE BOX DID NOT COME BACK";
			return "unbox: " + why + " — it is on the ground at " + Wand.fmt(where)
				+ ". Go and pick it up before anything else.";
		}
		return null;                                    // the drop takes a moment to reach you
	}

	/** What a plan is short of that is sitting in a box you are carrying. */
	static Map<String, Integer> recoverable(LocalPlayer p, Map<String, Integer> shortfall) {
		Map<String, Integer> out = new LinkedHashMap<>();
		Map<String, Integer> boxed = Work.boxed(p);
		for (var e : shortfall.entrySet()) {
			int have = boxed.getOrDefault(Rules.shortName(e.getKey()), 0);
            if (have > 0) out.put(e.getKey(), Math.min(have, e.getValue()));
		}
		return out;
	}
}
