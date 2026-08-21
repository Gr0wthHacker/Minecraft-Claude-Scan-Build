package dev.jack.chunkscan;

import net.fabricmc.fabric.api.client.screen.v1.ScreenEvents;
import net.fabricmc.fabric.api.event.player.UseBlockCallback;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.screens.inventory.AbstractContainerScreen;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.inventory.Slot;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.block.state.BlockState;

import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Watches container screens and records their contents against the block you opened.
 *
 * The position comes from the last block you right-clicked (client side), so every entry is anchored to a
 * real coordinate and keeps a stable number in storage.json. The screen title becomes the default label,
 * which is how named shulkers and barrels identify themselves.
 *
 * <p><b>The last block you clicked is not necessarily a container.</b> That assumption put 141 of 269
 * entries in storage.json on signs, stone bricks, slabs and moss, holding 1,028 items between them —
 * because right-clicking a sign and then pressing E within four seconds files YOUR OWN INVENTORY as a
 * chest at the sign's coordinates. `/cscan find` then sends you to a sign. Two guards, both narrow:
 * the block must be one that actually opens a container, and the player's own inventory screen is
 * never a container screen no matter what was clicked.
 */
final class ContainerWatcher {
	private static BlockPos lastUsed;
	private static String lastBlock = "";
	private static long lastUsedAt;
	static boolean enabled = true;

	private ContainerWatcher() {}

	/**
	 * Blocks that open a container when you click them. A BlockEntity test would be neater and is
	 * wrong here: a sign, a bed and a beehive all have one. Matching the names keeps this the same
	 * question `Storage.isContainer` asks when it cleans the index.
	 */
	static boolean opensAContainer(String block) {
		return Storage.isContainer(block);
	}

	static void register() {
		UseBlockCallback.EVENT.register((player, level, hand, hit) -> {
			if (level.isClientSide()) {
				BlockPos p = hit.getBlockPos();
				BlockState st = level.getBlockState(p);
				String name = BuiltInRegistries.BLOCK.getKey(st.getBlock()).getPath();
				// Only remember a click that could actually have opened something. Remembering
				// every click is what let a sign become a chest.
				if (opensAContainer(name)) {
					lastUsed = p;
					lastBlock = name;
					lastUsedAt = System.currentTimeMillis();
				}
			}
			return InteractionResult.PASS;
		});
		ScreenEvents.AFTER_INIT.register((mc, screen, w, h) -> {
			if (!enabled || !(screen instanceof AbstractContainerScreen<?> cs)) return;
			// Your own inventory is an AbstractContainerScreen and it is not a container. Neither is
			// the creative menu. Without this, opening your pack near a barrel re-files your pockets
			// as that barrel's contents.
			if (screen instanceof net.minecraft.client.gui.screens.inventory.InventoryScreen
				|| screen instanceof net.minecraft.client.gui.screens.inventory.CreativeModeInventoryScreen) return;
			if (lastUsed == null || System.currentTimeMillis() - lastUsedAt > 4000) return;   // not opened from a block
			// The server sends the contents AFTER the screen is built, so reading the slots here always
			// yields an empty container. Snapshot every tick instead and write the last one out on close.
			final BlockPos pos = lastUsed;
			final String block = lastBlock;
			final Map<String, Integer> latest = new LinkedHashMap<>();
			final Map<String, Integer> latestBoxed = new LinkedHashMap<>();
			final int[] slots = {0, 0};                      // {container size, slots in use}
			ScreenEvents.afterTick(screen).register(s -> {
				Map<String, Integer> items = new LinkedHashMap<>();
				Map<String, Integer> inBoxes = new LinkedHashMap<>();
				int[] n = read(mc, cs, items, inBoxes);
				if (n[0] > 0) {
					slots[0] = n[0];
					slots[1] = n[1];
					latest.clear();
					latest.putAll(items);
					latestBoxed.clear();
					latestBoxed.putAll(inBoxes);
				}
			});
			ScreenEvents.remove(screen).register(s -> {
				if (slots[0] == 0) return;                       // crafting table / anvil / other non-storage menu
				try {
					write(mc, cs, pos, block, latest, latestBoxed, slots[0], slots[1]);
				} catch (Exception e) {
					ChunkScanClient.LOG.warn("container capture failed", e);
				}
			});
		});
	}

	/** Container slots only (never the player's own inventory); returns {size, slots in use}. */
	private static int[] read(Minecraft mc, AbstractContainerScreen<?> cs, Map<String, Integer> items,
	                          Map<String, Integer> inBoxes) {
		if (mc.player == null) return new int[] {0, 0};
		Inventory inv = mc.player.getInventory();
		int slots = 0, used = 0;
		for (Slot s : cs.getMenu().slots) {
			if (s.container == inv) continue;
			slots++;
			ItemStack st = s.getItem();
			if (st.isEmpty()) continue;
			used++;
			items.merge(BuiltInRegistries.ITEM.getKey(st.getItem()).toString(), st.getCount(), Integer::sum);
			// ...and what is INSIDE it, if it is a box. See Storage.Container.inBoxes: a chest of
			// six shulkers indexed as "6x white_shulker_box" hides ten thousand blocks from every
			// question this mod can answer.
			st.getOrDefault(net.minecraft.core.component.DataComponents.CONTAINER,
				net.minecraft.world.item.component.ItemContainerContents.EMPTY)
				.nonEmptyItemCopyStream().forEach(inner -> inBoxes.merge(
					BuiltInRegistries.ITEM.getKey(inner.getItem()).toString(), inner.getCount(),
					Integer::sum));
		}
		return new int[] {slots, used};
	}

	private static void write(Minecraft mc, AbstractContainerScreen<?> cs, BlockPos lastUsed, String lastBlock,
							  Map<String, Integer> items, Map<String, Integer> inBoxes, int slots,
							  int used) throws Exception {
		if (mc.player == null || mc.level == null) return;
		Path dir = ScanRunner.schematicsDir(mc);
		Map<String, Storage.Container> all = Storage.load(dir);
		Storage.Container c = new Storage.Container();
		c.x = lastUsed.getX();
		c.y = lastUsed.getY();
		c.z = lastUsed.getZ();
		c.dimension = mc.level.dimension().identifier().toString();
		c.block = lastBlock;
		String zone = Markers.nearestLabel(Markers.load(dir), lastUsed, 24.0);
		c.zone = zone == null ? "" : zone;
		String title = cs.getTitle().getString();
		if (!title.isBlank() && !title.equalsIgnoreCase("Chest") && !title.equalsIgnoreCase("Large Chest")
			&& !title.equalsIgnoreCase("Barrel") && !title.equalsIgnoreCase("Shulker Box")) {
			c.label = title;                                     // a renamed container names itself
		}
		c.slots = slots;
		c.used = used;
		c.items.putAll(items);
		c.inBoxes.putAll(inBoxes);
		Storage.upsert(all, c);
		Storage.save(dir, all);
		ChunkScanClient.LOG.info("indexed container #{} at {} ({} stacks)", c.id, c.key(), items.size());
	}

	/** Set a label on the container at `pos`; null if it has not been indexed yet. */
	static String label(Minecraft mc, BlockPos pos, String text) throws Exception {
		Path dir = ScanRunner.schematicsDir(mc);
		Map<String, Storage.Container> all = Storage.load(dir);
		Storage.Container c = all.get(pos.getX() + "," + pos.getY() + "," + pos.getZ());
		if (c == null) return null;
		c.label = text;
		Storage.save(dir, all);
		return c.describe();
	}
}
