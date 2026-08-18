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
			try {
				capture(mc, cs);
			} catch (Exception e) {
				ChunkScanClient.LOG.warn("container capture failed", e);
			}
		});
	}

	private static void capture(Minecraft mc, AbstractContainerScreen<?> cs) throws Exception {
		if (mc.player == null || mc.level == null) return;
		Map<String, Integer> items = new LinkedHashMap<>();
		Inventory inv = mc.player.getInventory();
		int slots = 0;
		for (Slot s : cs.getMenu().slots) {
			if (s.container == inv) continue;                    // skip the player's own inventory
			slots++;
			ItemStack st = s.getItem();
			if (st.isEmpty()) continue;
			items.merge(BuiltInRegistries.ITEM.getKey(st.getItem()).toString(), st.getCount(), Integer::sum);
		}
		if (slots == 0) return;                                  // crafting table / anvil / other non-storage menu

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
