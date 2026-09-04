package dev.jack.chunkscan;

import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.Property;

/** Keeps the imported state intact while separating automatic connections from build requirements. */
final class StateContract {
    enum Role { REQUIRED, DERIVED }
    private static final Set<String> SIDES = Set.of("north", "south", "east", "west");
    private static final Map<String, StateContract> CACHE = new LinkedHashMap<>(128, .75f, true) {
        @Override protected boolean removeEldestEntry(Map.Entry<String, StateContract> entry) {
            return size() > 2048;
        }
    };
    final String block;
    final Map<String, String> properties;
    final boolean valid;

    private StateContract(String block, Map<String, String> properties, boolean valid) {
        this.block = block;
        this.properties = Collections.unmodifiableMap(properties);
        this.valid = valid;
    }

    static synchronized StateContract parse(String spec) {
        return CACHE.computeIfAbsent(spec, StateContract::decode);
    }

    private static StateContract decode(String spec) {
        int bracket = spec.indexOf('[');
        String block = Rules.shortName(spec);
        Map<String, String> properties = new LinkedHashMap<>();
        if (bracket < 0) return new StateContract(block, properties, !block.isBlank() && !spec.contains("]"));
        boolean valid = spec.endsWith("]") && spec.indexOf('[', bracket + 1) < 0;
        if (!valid) return new StateContract(block, properties, false);
        String inner = spec.substring(bracket + 1, spec.length() - 1);
        for (String pair : inner.split(",", -1)) {
            String[] parts = pair.split("=", -1);
            if (parts.length != 2 || parts[0].isBlank() || parts[1].isBlank()) { valid = false; continue; }
            if (properties.putIfAbsent(parts[0].trim(), parts[1].trim()) != null) valid = false;
        }
        return new StateContract(block, properties, valid && !block.isBlank());
    }

    static Role role(String block, String property) {
        if (block.endsWith("_leaves") && property.equals("distance")) return Role.DERIVED;
        if (block.endsWith("_stairs") && property.equals("shape")) return Role.DERIVED;
        boolean connections = block.endsWith("_fence") || block.endsWith("_wall")
            || block.endsWith("_pane") || block.equals("iron_bars") || block.equals("redstone_wire");
        if (connections && SIDES.contains(property)) return Role.DERIVED;
        if (block.endsWith("_wall") && property.equals("up")) return Role.DERIVED;
        return Role.REQUIRED;
    }

    boolean propertiesMatch(BlockState state) {
        if (!valid) return false;
        for (var entry : properties.entrySet()) {
            Property<?> property = state.getBlock().getStateDefinition().getProperty(entry.getKey());
            // Even derived properties must exist and have a legal value: bad imports are not success.
            if (property == null || property.getValue(entry.getValue()).isEmpty()) return false;
            if (role(block, entry.getKey()) == Role.REQUIRED
                    && !value(state, property).equals(entry.getValue())) return false;
        }
        return true;
    }

    private static <T extends Comparable<T>> String value(BlockState state, Property<T> property) {
        return property.getName(state.getValue(property));
    }
}
