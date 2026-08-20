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
		place(file, origin, name, "NONE");
	}

	/**
	 * As {@link #place}, rotated. `rotation` is a {@code net.minecraft.world.level.block.Rotation}
	 * constant name — NONE, CLOCKWISE_90, CLOCKWISE_180, COUNTERCLOCKWISE_90.
	 *
	 * <p>Litematica's setters take an {@code IMessageConsumer} for feedback and there is no public
	 * no-op to hand them, so one is synthesised with a {@link java.lang.reflect.Proxy}. Passing null
	 * is the obvious alternative and risks an NPE deep inside a soft dependency, which would surface
	 * as "paste silently did nothing".
	 */
	static void place(Path file, BlockPos origin, String name, String rotation) throws Exception {
		Object placement = placementFor(file, origin, name);
		if (rotation != null && !rotation.equals("NONE")) {
			Class<?> rotC = Class.forName("net.minecraft.world.level.block.Rotation");
			Object rot = Enum.valueOf((Class<Enum>) rotC.asSubclass(Enum.class), rotation);
			Class<?> consumerC = Class.forName("fi.dy.masa.malilib.gui.interfaces.IMessageConsumer");
			Object noop = java.lang.reflect.Proxy.newProxyInstance(
				Litematica.class.getClassLoader(), new Class<?>[]{consumerC},
				(p, m, a) -> m.getReturnType() == boolean.class ? Boolean.FALSE : null);
			placement.getClass().getMethod("setRotation", rotC, consumerC).invoke(placement, rot, noop);
		}
		register(placement);
	}

	private static Object placementFor(Path file, BlockPos origin, String name) throws Exception {
		Class<?> holderC = Class.forName("fi.dy.masa.litematica.data.SchematicHolder");
		Object holder = holderC.getMethod("getInstance").invoke(null);
		Object schematic = holderC.getMethod("getOrLoad", Path.class).invoke(holder, file);
		if (schematic == null) throw new IllegalStateException("Litematica could not load " + file.getFileName());

		Class<?> schemC = Class.forName("fi.dy.masa.litematica.schematic.LitematicaSchematic");
		Class<?> placementC = Class.forName("fi.dy.masa.litematica.schematic.placement.SchematicPlacement");
		Method createFor = placementC.getMethod("createFor", schemC, BlockPos.class, String.class, boolean.class, boolean.class);
		Object placement = createFor.invoke(null, schematic, origin, name, true, true);

		return placement;
	}

	private static void register(Object placement) throws Exception {
		Class<?> placementC = Class.forName("fi.dy.masa.litematica.schematic.placement.SchematicPlacement");
		Class<?> dataC = Class.forName("fi.dy.masa.litematica.data.DataManager");
		Object manager = dataC.getMethod("getSchematicPlacementManager").invoke(null);
		manager.getClass().getMethod("addSchematicPlacement", placementC, boolean.class)
			.invoke(manager, placement, false);
	}

	/** The rotation names `/cscan paste` accepts, in the order they are offered. */
	static String rotationOf(String word) {
		if (word == null) return "NONE";
		return switch (word.trim().toLowerCase(java.util.Locale.ROOT)) {
			case "90", "cw", "rot90", "clockwise_90" -> "CLOCKWISE_90";
			case "180", "rot180", "clockwise_180" -> "CLOCKWISE_180";
			case "270", "ccw", "rot270", "counterclockwise_90" -> "COUNTERCLOCKWISE_90";
			default -> "NONE";
		};
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
