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
 */
final class ContainerWatcher {
	private static BlockPos lastUsed;
	private static String lastBlock = "";
	private static long lastUsedAt;
	static boolean enabled = true;

	private ContainerWatcher() {}

	static void register() {
		UseBlockCallback.EVENT.register((player, level, hand, hit) -> {
			if (level.isClientSide()) {
				lastUsed = hit.getBlockPos();
				BlockState st = level.getBlockState(lastUsed);
				lastBlock = BuiltInRegistries.BLOCK.getKey(st.getBlock()).getPath();
				lastUsedAt = System.currentTimeMillis();
			}
			return InteractionResult.PASS;
		});
		ScreenEvents.AFTER_INIT.register((mc, screen, w, h) -> {
			if (!enabled || !(screen instanceof AbstractContainerScreen<?> cs)) return;
			if (lastUsed == null || System.currentTimeMillis() - lastUsedAt > 4000) return;   // not opened from a block
			// The server sends the contents AFTER the screen is built, so reading the slots here always
			// yields an empty container. Snapshot every tick instead and write the last one out on close.
			final BlockPos pos = lastUsed;
			final String block = lastBlock;
			final Map<String, Integer> latest = new LinkedHashMap<>();
			final int[] slots = {0, 0};                      // {container size, slots in use}
			ScreenEvents.afterTick(screen).register(s -> {
				Map<String, Integer> items = new LinkedHashMap<>();
				int[] n = read(mc, cs, items);
				if (n[0] > 0) {
					slots[0] = n[0];
					slots[1] = n[1];
					latest.clear();
					latest.putAll(items);
				}
			});
			ScreenEvents.remove(screen).register(s -> {
				if (slots[0] == 0) return;                       // crafting table / anvil / other non-storage menu
				try {
					write(mc, cs, pos, block, latest, slots[0], slots[1]);
				} catch (Exception e) {
					ChunkScanClient.LOG.warn("container capture failed", e);
				}
			});
		});
	}

	/** Container slots only (never the player's own inventory); returns {size, slots in use}. */
	private static int[] read(Minecraft mc, AbstractContainerScreen<?> cs, Map<String, Integer> items) {
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
		}
		return new int[] {slots, used};
	}

	private static void write(Minecraft mc, AbstractContainerScreen<?> cs, BlockPos lastUsed, String lastBlock,
							  Map<String, Integer> items, int slots, int used) throws Exception {
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
