package dev.jack.chunkscan;

import net.fabricmc.fabric.api.client.networking.v1.ClientPlayConnectionEvents;
import net.fabricmc.fabric.api.event.player.UseBlockCallback;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.network.chat.Component;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.item.BlockItem;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;

import java.util.ArrayList;
import java.util.List;

/**
 * The steak wand: right-click a block to set corner 1, right-click again to set corner 2, a third
 * time to start over. {@code /cscan fill} then turns that box into a schematic the printer builds.
 *
 * <p><b>Why right-click for both corners rather than the WorldEdit left/right split.</b> This is a
 * CLIENT mod on a real server. A left-click on a block is an attack, and suppressing it means
 * suppressing the swing the server is about to be told about; a right-click that we consume never
 * leaves the client at all. One gesture also means one thing to cancel, and the thing being
 * cancelled is the wand item's own use — which matters here because the wand is FOOD.
 *
 * <p><b>The wand must be armed.</b> Steak is for eating, and a wand that is always live turns every
 * meal into a corner. {@code /cscan wand on} arms it and {@code off} gives you your dinner back.
 * While armed, a right-click with the wand on a block is consumed: you do not eat, and you do not
 * open the chest you clicked.
 *
 * <p><b>The box is drawn while you build it.</b> A selection you cannot see is a selection you get
 * wrong, and {@link Highlight} already draws gizmo boxes for the dig list — so the corners show as
 * soon as they are set and the full edge outline appears when the box closes.
 */
final class Wand {
	/** Cooked beef. Anything else in hand behaves normally, armed or not. */
	static final String ITEM = "minecraft:cooked_beef";
	private static final String HL = "wand";
	private static final int CORNER_COLOR = 0x40C0FF;
	private static final int BOX_COLOR = 0x40C0FF;
	/** Refreshed on every change; long enough that a selection does not quietly expire mid-build. */
	private static final int HL_SECONDS = 3600;
	/** An outline of a very large box is thousands of gizmos; past this only the corners are drawn. */
	private static final int MAX_OUTLINE = 400;

	private static boolean armed = false;
	private static BlockPos p1 = null;
	private static BlockPos p2 = null;
	private static String dimension = "";
	private static BlockState material = null;
	private static boolean nextIsFirst = true;

	private Wand() {}

	static void register() {
		UseBlockCallback.EVENT.register((player, level, hand, hit) -> {
			if (!armed || player == null || level == null || !level.isClientSide()) return InteractionResult.PASS;
			ItemStack held = player.getItemInHand(hand);
			if (held == null || held.isEmpty()) return InteractionResult.PASS;
			if (!BuiltInRegistries.ITEM.getKey(held.getItem()).toString().equals(ITEM)) return InteractionResult.PASS;

			mark(player, level, hit.getBlockPos());
			// SUCCESS, so the click is spent here: no bite taken, no chest opened, nothing sent.
			return InteractionResult.SUCCESS;
		});
		// A selection is a pair of coordinates and coordinates mean nothing without a world. Carrying
		// them across a disconnect means the next `/cscan fill` writes a box from the LAST server at
		// positions in THIS one — which audits clean and is entirely wrong.
		ClientPlayConnectionEvents.DISCONNECT.register((handler, client) -> {
			clear();
			material = null;
		});
	}

	private static void mark(net.minecraft.world.entity.player.Player player, Level level, BlockPos pos) {
		String dim = level.dimension().identifier().toString();
		if (nextIsFirst) {
			p1 = pos.immutable();
			p2 = null;
			dimension = dim;
			nextIsFirst = false;
			redraw();
			say(player, "corner 1 at " + fmt(p1) + " — right-click the opposite corner");
			return;
		}
		if (!dim.equals(dimension)) {
			// Two corners in two dimensions is not a box. Start over rather than build nonsense.
			p1 = pos.immutable();
			p2 = null;
			dimension = dim;
			redraw();
			say(player, "corner 1 was in " + dimension + " — different dimension, so that is corner 1 now: " + fmt(p1));
			return;
		}
		p2 = pos.immutable();
		nextIsFirst = true;
		redraw();
		say(player, "corner 2 at " + fmt(p2) + " — " + describe() + ". /cscan fill <name>");
	}

	private static void say(net.minecraft.world.entity.player.Player player, String msg) {
		player.sendSystemMessage(Component.literal("[cscan] " + msg));
	}

	static String fmt(BlockPos p) {
		return p.getX() + " " + p.getY() + " " + p.getZ();
	}

	// ---- the drawing

	/** Corners while you are picking, the whole edge outline once the box closes. */
	private static void redraw() {
		if (p1 == null) {
			Highlight.clear(HL);
			return;
		}
		if (p2 == null) {
			Highlight.show(HL, List.of(p1), CORNER_COLOR, HL_SECONDS);
			return;
		}
		List<BlockPos> outline = outline(p1, p2);
		Highlight.show(HL, outline, BOX_COLOR, HL_SECONDS);
	}

	/**
	 * The twelve edges of the box, as cells. Only the edges: filling the box would bury whatever is
	 * inside it behind a wall of gizmos, which is the opposite of seeing your selection.
	 */
	static List<BlockPos> outline(BlockPos a, BlockPos b) {
		int x1 = Math.min(a.getX(), b.getX()), x2 = Math.max(a.getX(), b.getX());
		int y1 = Math.min(a.getY(), b.getY()), y2 = Math.max(a.getY(), b.getY());
		int z1 = Math.min(a.getZ(), b.getZ()), z2 = Math.max(a.getZ(), b.getZ());
		List<BlockPos> out = new ArrayList<>();
		long edges = 4L * ((x2 - x1 + 1) + (y2 - y1 + 1) + (z2 - z1 + 1));
		if (edges > MAX_OUTLINE) {                       // too big to outline: show the corners only
			for (int x : new int[]{x1, x2}) {
				for (int y : new int[]{y1, y2}) {
					for (int z : new int[]{z1, z2}) out.add(new BlockPos(x, y, z));
				}
			}
			return out;
		}
		for (int x = x1; x <= x2; x++) {
			for (int y : new int[]{y1, y2}) {
				for (int z : new int[]{z1, z2}) out.add(new BlockPos(x, y, z));
			}
		}
		for (int y = y1; y <= y2; y++) {
			for (int x : new int[]{x1, x2}) {
				for (int z : new int[]{z1, z2}) out.add(new BlockPos(x, y, z));
			}
		}
		for (int z = z1; z <= z2; z++) {
			for (int x : new int[]{x1, x2}) {
				for (int y : new int[]{y1, y2}) out.add(new BlockPos(x, y, z));
			}
		}
		return out;
	}

	// ---- state, read by the commands

	static boolean armed() {
		return armed;
	}

	static void arm(boolean on) {
		armed = on;
		if (!on) {
			Highlight.clear(HL);
			return;
		}
		clear();                          // arming always starts a fresh box
	}

	/** Set the box directly, as `/cscan around` does. Draws it, exactly as clicking would. */
	static void setBox(BlockPos a, BlockPos b, String dim) {
		p1 = a.immutable();
		p2 = b.immutable();
		dimension = dim;
		nextIsFirst = true;
		redraw();
	}

	static void clear() {
		p1 = null;
		p2 = null;
		dimension = "";
		nextIsFirst = true;
		Highlight.clear(HL);
	}

	static BlockPos pos1() {
		return p1;
	}

	static BlockPos pos2() {
		return p2;
	}

	static String dimension() {
		return dimension;
	}

	static boolean complete() {
		return p1 != null && p2 != null;
	}

	static BlockState material() {
		return material;
	}

	static void material(BlockState state) {
		material = state;
	}

	/** The block an item stack would place, or null if it does not place one. */
	static BlockState blockOf(ItemStack stack) {
		if (stack == null || stack.isEmpty()) return null;
		if (!(stack.getItem() instanceof BlockItem bi)) return null;
		return bi.getBlock().defaultBlockState();
	}

	/** {sizeX, sizeY, sizeZ} of the current box, or null. */
	static int[] size() {
		if (!complete()) return null;
		return new int[]{Math.abs(p1.getX() - p2.getX()) + 1,
		                 Math.abs(p1.getY() - p2.getY()) + 1,
		                 Math.abs(p1.getZ() - p2.getZ()) + 1};
	}

	static long volume() {
		int[] s = size();
		return s == null ? 0 : (long) s[0] * s[1] * s[2];
	}

	static String describe() {
		int[] s = size();
		if (s == null) return "no box";
		return s[0] + "x" + s[1] + "x" + s[2] + " = " + volume() + " cells";
	}
}
