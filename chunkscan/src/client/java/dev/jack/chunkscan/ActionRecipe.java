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
		String block = Rules.shortName(state);
		if (block.equals("water")) return "water_bucket";
		// A wall sign has no item of its own: you carry `oak_sign` and the FACE you click decides
		// whether it lands standing or on a wall. Tallying `oak_wall_sign` asks a chest for an item
		// that does not exist, so the slot is never found and the cell silently never places.
		if (block.endsWith("_wall_hanging_sign")) return block.substring(0, block.length() - 18) + "_hanging_sign";
		if (block.endsWith("_wall_sign")) return block.substring(0, block.length() - 10) + "_sign";
		return block;
	}

	/**
	 * Work this builder DECLINES and hands back, rather than work it cannot do.
	 *
	 * <p>The distinction is the same one {@code Split.digLeft} already draws and is load-bearing
	 * for the same reason: a litematic cannot express removal, so breaking is Jack's, and if the
	 * loop's advance condition waited on it the loop would sit for ever on something it can never
	 * satisfy. A declined cell is REPORTED, excluded from the todo, and never blocks preflight.
	 *
	 * <p>A filled cauldron is here by decision, not by difficulty. It is the only cell that needs
	 * two different items - a {@code cauldron}, then a {@code water_bucket} - so it would make
	 * {@code itemFor} world-aware and touch the slot search and the bill of materials, to automate
	 * two blocks in a park of three hundred and fifty thousand.
	 */
	static String manual(String state) {
		String block = Rules.shortName(state);
		if (block.equals("water_cauldron") || block.equals("lava_cauldron")) return "cauldron fill";
		// COMMISSIONING IS A DELIBERATE PASS, NOT A SIDE EFFECT OF A BUILD LOOP. A repeater's and a
		// comparator's `facing` convention is an OPEN known-wrong in this project - the wiki and the
		// reference builds both say `facing` names the INPUT, and our own simulator treats it as the
		// output - and our renderer draws both directions identically. Placing 1868 of them
		// unattended would stamp a possibly-inverted convention across the whole park, invisibly,
		// and a circuit that looks right and does nothing is this repo's most expensive failure.
		// `equals("rail")` as well as the suffix: plain `rail` does not end in "_rail", so the
		// original gate missed the commonest track block in the game entirely.
		if (block.equals("rail") || block.endsWith("_rail") || block.equals("repeater")
			|| block.equals("comparator") || block.equals("redstone_wire"))
			return "redstone/rail commissioning";
		return null;
	}

	/** Signs, standing or on a wall - the blocks whose TEXT is a second, separate action. */
	static boolean sign(String state) {
		String block = Rules.shortName(state);
		return block.endsWith("_sign") || block.endsWith("_hanging_sign");
	}

	/**
	 * A standing sign has SIXTEEN rotations and a wall sign takes its facing from the clicked face.
	 *
	 * <p>The placement search sweeps yaw and asks vanilla which state it would get, so the geometry
	 * needs no arithmetic here - it only needs the sweep to be able to REACH every rotation. Four
	 * cardinal yaws can only ever produce rotations 0, 4, 8 and 12, so the other twelve are
	 * unplaceable and the cell fails forever with nothing to say why.
	 */
	static float[] yawSweep(String state) {
		if (!sign(state) || Rules.shortName(state).contains("_wall_")) return null;
		float[] out = new float[16];
		for (int i = 0; i < 16; i++) out[i] = -180f + i * 22.5f;
		return out;
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
		// A filled cauldron is DECLINED, not unimplemented - see `manual`. It is the only recipe
		// needing two different items for one cell, and it is two blocks in a park of 350,000.
		// Signs are implemented - placed by the ordinary search, then written by Printer.signText.
		// Their remaining gate is EVIDENCE rather than mechanism, and it needs the design's tile
		// entities, so it lives in `missing(cells, signs)` where the text is actually in hand.
		// Redstone and rails are DECLINED rather than unimplemented - see `manual`. Dust goes with
		// them, though it is an ordinary block: a circuit half-laid by the loop and half by hand is
		// worse than one pass owning the whole thing.
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
        return missing(cells, Map.of());
    }

    /**
     * What this design asks for that the builder cannot do, counted by reason.
     *
     * <p>{@code signs} is the design's own recorded text, keyed by {@link
     * net.minecraft.core.BlockPos#asLong()}. A sign whose text is not recorded stays gated: placing
     * the block alone leaves a BLANK BOARD, which passes every check this project has - legal
     * state, supported, affordable, right block - and is the exact silent failure a park full of
     * unreadable signs already cost once.
     */
    static Map<String, Integer> missing(List<Work.Cell> cells, Map<Long, SignText> signs) {
        Map<String, Integer> out = new LinkedHashMap<>();
        for (Work.Cell cell : cells) {
            String missing = missingFor(cell.block());
            if (missing == null && sign(cell.block())) {
                SignText text = signs.get(cell.pos().asLong());
                if (text == null || text.blank()) missing = "sign text not recorded in the litematic";
            }
            if (missing != null) out.merge(missing, 1, Integer::sum);
        }
        return out;
    }

    static void require(List<Work.Cell> cells) throws IOException {
        require(cells, Map.of());
    }

    static void require(List<Work.Cell> cells, Map<Long, SignText> signs) throws IOException {
        Map<String, Integer> missing = missing(cells, signs);
        if (missing.isEmpty()) return;
        StringBuilder summary = new StringBuilder();
        for (var entry : missing.entrySet()) {
            if (!summary.isEmpty()) summary.append(", ");
            summary.append(entry.getValue()).append(" ").append(entry.getKey());
        }
        throw new IOException("unimplemented action recipes: " + summary);
    }
}
