package dev.jack.chunkscan;

import java.io.IOException;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.world.level.block.SlabBlock;
import net.minecraft.world.level.block.state.BlockState;

/** Recipes which need more than one ordinary BlockItem placement are explicit preflight gates. */
final class ActionRecipe {
	private ActionRecipe() {}

	/** The inventory item consumed by one cell's action, rather than its final block identity. */
	static String itemFor(String state) {
		return Rules.shortName(state).equals("water") ? "water_bucket" : Rules.shortName(state);
	}

	static boolean waterBucket(String state) {
		return Rules.shortName(state).equals("water");
	}

    static String missingFor(String state) {
        String block = Rules.shortName(state);
		// A bucket creates a source. A litematic can also encode a flowing level, which requires a
		// controlled source/layout action rather than pretending one click can reproduce it.
		if (block.equals("water") && props(state).containsKey("level")
			&& !"0".equals(props(state).get("level"))) return "fluid flow shaping";
		// A water bucket is a direct, acknowledged item use. Lava remains an explicit gate because
		// its destructive placement and collection policy has not been approved for this builder.
		if (block.equals("lava")) return "fluid bucket placement";
        if (block.equals("water_cauldron") || block.equals("lava_cauldron")) return "cauldron fill";
        if (block.endsWith("_wall_sign") || block.endsWith("_wall_hanging_sign")) return "wall sign placement/configuration";
        if (block.endsWith("_sign") || block.endsWith("_hanging_sign")) return "sign text/configuration";
		if (block.equals("redstone_wire") && (props(state).get("power") == null
			|| "0".equals(props(state).get("power")))) return null;
        if (block.equals("redstone_wire") || block.endsWith("_rail") || block.equals("repeater")
            || block.equals("comparator")) return "redstone/rail commissioning";
		return null;
	}

	private static Map<String, String> props(String state) {
		return Printer.props(state);
	}

	/** Vanilla creates the secondary door/bed cell; this puts its initiating cell first. */
	static int order(String state) {
		String block = Rules.shortName(state);
		Map<String, String> props = Printer.props(state);
		if (block.endsWith("_door")) return "upper".equals(props.get("half")) ? 2 : 0;
		if (block.endsWith("_bed")) return "head".equals(props.get("part")) ? 2 : 0;
		return 1;
	}

	static boolean doubleSlab(String state) {
		return Rules.shortName(state).endsWith("_slab") && "double".equals(Printer.props(state).get("type"));
	}

	/** A bottom/top slab is an intentional, retryable intermediate for a desired double slab. */
	static boolean slabIntermediate(BlockState state, String wanted) {
		return doubleSlab(wanted) && BuiltInRegistries.BLOCK.getKey(state.getBlock()).getPath()
			.equals(Rules.shortName(wanted)) && state.hasProperty(SlabBlock.TYPE)
			&& state.getValue(SlabBlock.TYPE) != net.minecraft.world.level.block.state.properties.SlabType.DOUBLE;
	}

	/** A vine may require several uses; each observed subset is a valid intermediate. */
	static boolean vineIntermediate(BlockState state, String wanted) {
		if (!Rules.shortName(wanted).equals("vine")
			|| !BuiltInRegistries.BLOCK.getKey(state.getBlock()).getPath().equals("vine")) return false;
		Map<String, String> want = Printer.props(wanted);
		boolean missing = false;
		for (var property : state.getProperties()) {
			String name = property.getName();
			if (!name.equals("north") && !name.equals("east") && !name.equals("south") && !name.equals("west") && !name.equals("up")) continue;
			boolean actual = "true".equals(String.valueOf(state.getValue(property)));
			boolean required = "true".equals(want.get(name));
			if (actual && !required) return false;
			if (required && !actual) missing = true;
		}
		return missing;
	}

	static boolean vineProgress(BlockState before, BlockState after, String wanted) {
		if (!Work.matches(after, wanted) && !vineIntermediate(after, wanted)) return false;
		if (!BuiltInRegistries.BLOCK.getKey(before.getBlock()).getPath().equals("vine")) return true;
		for (var property : after.getProperties()) {
			String name = property.getName();
			if ((name.equals("north") || name.equals("east") || name.equals("south") || name.equals("west") || name.equals("up"))
				&& "true".equals(String.valueOf(after.getValue(property)))
				&& "false".equals(String.valueOf(before.getValue(property)))) return true;
		}
		return false;
	}

	/** Glow lichen is a six-face analogue of vines, with each use allowed to add one wanted face. */
	static boolean glowLichenIntermediate(BlockState state, String wanted) {
		return multiFaceIntermediate(state, wanted, "glow_lichen", Set.of("down", "north", "south", "up", "east", "west"));
	}

	static boolean glowLichenProgress(BlockState before, BlockState after, String wanted) {
		return multiFaceProgress(before, after, wanted, "glow_lichen", Set.of("down", "north", "south", "up", "east", "west"));
	}

	private static boolean multiFaceIntermediate(BlockState state, String wanted, String block, Set<String> faces) {
		if (!Rules.shortName(wanted).equals(block)
			|| !BuiltInRegistries.BLOCK.getKey(state.getBlock()).getPath().equals(block)) return false;
		Map<String, String> want = Printer.props(wanted);
		boolean missing = false;
		for (var property : state.getProperties()) {
			String name = property.getName();
			if (!faces.contains(name)) continue;
			boolean actual = "true".equals(String.valueOf(state.getValue(property)));
			boolean required = "true".equals(want.get(name));
			if (actual && !required) return false;
			if (required && !actual) missing = true;
		}
		return missing;
	}

	private static boolean multiFaceProgress(BlockState before, BlockState after, String wanted, String block, Set<String> faces) {
		if (!Work.matches(after, wanted) && !multiFaceIntermediate(after, wanted, block, faces)) return false;
		if (!BuiltInRegistries.BLOCK.getKey(before.getBlock()).getPath().equals(block)) return true;
		for (var property : after.getProperties()) {
			String name = property.getName();
			if (faces.contains(name) && "true".equals(String.valueOf(after.getValue(property)))
				&& "false".equals(String.valueOf(before.getValue(property)))) return true;
		}
		return false;
	}

    static Map<String, Integer> missing(List<Work.Cell> cells) {
        Map<String, Integer> out = new LinkedHashMap<>();
        for (Work.Cell cell : cells) {
            String missing = missingFor(cell.block());
            if (missing != null) out.merge(missing, 1, Integer::sum);
        }
        return out;
    }

    static void require(List<Work.Cell> cells) throws IOException {
        Map<String, Integer> missing = missing(cells);
        if (missing.isEmpty()) return;
        StringBuilder summary = new StringBuilder();
        for (var entry : missing.entrySet()) {
            if (!summary.isEmpty()) summary.append(", ");
            summary.append(entry.getValue()).append(" ").append(entry.getKey());
        }
        throw new IOException("unimplemented action recipes: " + summary);
    }
}
