package dev.jack.chunkscan;

import net.minecraft.core.BlockPos;

import java.lang.reflect.Method;
import java.nio.file.Path;

/**
 * Reflection bridge to Litematica (soft dependency: chunkscan works fine without it).
 * Only three things are needed — load a schematic, make a placement at a world origin, register it —
 * plus reading the current area selection.
 */
final class Litematica {
	private Litematica() {}

	static boolean present() {
		return net.fabricmc.loader.api.FabricLoader.getInstance().isModLoaded("litematica");
	}

	/** Load `file` and add an enabled placement whose origin corner sits at `origin`. */
	static void place(Path file, BlockPos origin, String name) throws Exception {
		Class<?> holderC = Class.forName("fi.dy.masa.litematica.data.SchematicHolder");
		Object holder = holderC.getMethod("getInstance").invoke(null);
		Object schematic = holderC.getMethod("getOrLoad", Path.class).invoke(holder, file);
		if (schematic == null) throw new IllegalStateException("Litematica could not load " + file.getFileName());

		Class<?> schemC = Class.forName("fi.dy.masa.litematica.schematic.LitematicaSchematic");
		Class<?> placementC = Class.forName("fi.dy.masa.litematica.schematic.placement.SchematicPlacement");
		Method createFor = placementC.getMethod("createFor", schemC, BlockPos.class, String.class, boolean.class, boolean.class);
		Object placement = createFor.invoke(null, schematic, origin, name, true, true);

		Class<?> dataC = Class.forName("fi.dy.masa.litematica.data.DataManager");
		Object manager = dataC.getMethod("getSchematicPlacementManager").invoke(null);
		Class<?> managerC = manager.getClass();
		managerC.getMethod("addSchematicPlacement", placementC, boolean.class).invoke(manager, placement, false);
	}

	/** Current area selection as {minX, minY, minZ, maxX, maxY, maxZ}, or null if there is none. */
	static int[] currentSelection() throws Exception {
		Class<?> dataC = Class.forName("fi.dy.masa.litematica.data.DataManager");
		Object sel = dataC.getMethod("getSelectionManager").invoke(null);
		Object area = sel.getClass().getMethod("getCurrentSelection").invoke(sel);
		if (area == null) return null;
		Object boxes = area.getClass().getMethod("getAllSubRegionBoxes").invoke(area);
		java.util.List<?> list = (java.util.List<?>) boxes;
		if (list.isEmpty()) return null;
		int[] out = null;
		for (Object box : list) {
			BlockPos p1 = (BlockPos) box.getClass().getMethod("getPos1").invoke(box);
			BlockPos p2 = (BlockPos) box.getClass().getMethod("getPos2").invoke(box);
			if (p1 == null || p2 == null) continue;
			int[] b = {Math.min(p1.getX(), p2.getX()), Math.min(p1.getY(), p2.getY()), Math.min(p1.getZ(), p2.getZ()),
			           Math.max(p1.getX(), p2.getX()), Math.max(p1.getY(), p2.getY()), Math.max(p1.getZ(), p2.getZ())};
			out = out == null ? b : new int[]{Math.min(out[0], b[0]), Math.min(out[1], b[1]), Math.min(out[2], b[2]),
			                                  Math.max(out[3], b[3]), Math.max(out[4], b[4]), Math.max(out[5], b[5])};
		}
		return out;
	}
}
