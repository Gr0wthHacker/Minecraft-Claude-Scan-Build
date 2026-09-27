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
    /**
     * <b>A PLAIN CONCURRENT MAP, AND NEITHER LOCKED NOR ACCESS-ORDERED.</b> This was an LRU
     * {@code LinkedHashMap(128, .75f, true)} behind a {@code synchronized} method, and both halves
     * were costing more than the parse they were saving: an access-ordered map REWRITES ITS LINKED
     * LIST ON EVERY GET, so every lookup was a structural mutation under a monitor - and
     * {@code Work.matches} calls this once per cell, which on `Park Complete` is a quarter of a
     * million times per recount. A design has a few hundred distinct block states; the cache never
     * needed evicting at all, so it is bounded and stops filling rather than churning.
     */
    private static final Map<String, StateContract> CACHE = new java.util.concurrent.ConcurrentHashMap<>();
    private static final int CACHE_MAX = 16384;
    final String block;
    final Map<String, String> properties;
    final boolean valid;

    private StateContract(String block, Map<String, String> properties, boolean valid) {
        this.block = block;
        this.properties = Collections.unmodifiableMap(properties);
        this.valid = valid;
    }

    static StateContract parse(String spec) {
        StateContract hit = CACHE.get(spec);
        if (hit != null) return hit;
        StateContract made = decode(spec);
        if (CACHE.size() < CACHE_MAX) CACHE.put(spec, made);
        return made;
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

    /**
     * The properties a design DECIDES - the Python side's `work.INTENTIONAL`, applied here on the
     * Java read. A litematic's state string carries every property, and treating the rest as
     * required meant `sugar_cane[age=7]`, `cave_vines[berries=true]`, `chest[type=left]`,
     * `grass_block[snowy=false]`, `campfire[lit=true]` all had to match exactly: the placement
     * predicted a state the world would never yield and the cell silently left the frontier, or it
     * placed, the server derived the other value, and a correct block was reported WRONG STATE and
     * given up on. Most of a block state is the game reacting to the neighbourhood.
     */
    static final Set<String> INTENTIONAL = Set.of("facing", "half", "type", "axis", "rotation",
        "hanging", "face", "orientation", "hinge", "part", "attachment", "vertical_direction", "tilt",
        // ...and four this side keeps as COMPLETION requirements that the Python side does not
        // record: a waterlogged stair needs a bucket after the stair, a powered rail needs its
        // signal, a leaf a player placed is persistent, and an open trapdoor is a click the
        // printer cannot make - all of them amber in /cscan check for a hand, never "built".
        "waterlogged", "powered", "persistent", "open");
    /** ...except that for these the direction flags ARE the decision: which face the thing clings to. */
    static final Set<String> MULTIFACE = Set.of("vine", "glow_lichen", "sculk_vein", "resin_clump");
    private static final Set<String> FACES = Set.of("north", "south", "east", "west", "up", "down");

    /** The shipped sets when there are any, else the constants above. See Rules.intentional(). */
    private static Set<String> intentional() {
        Set<String> s = Rules.intentional();
        return s.isEmpty() ? INTENTIONAL : s;
    }

    private static Set<String> multiface() {
        Set<String> s = Rules.multiface();
        return s.isEmpty() ? MULTIFACE : s;
    }

    static Role role(String block, String property) {
        if (multiface().contains(block)) return FACES.contains(property) ? Role.REQUIRED : Role.DERIVED;
        // A chest's `type` is which half of a double chest it is - the game's decision, made when
        // the neighbour was placed. Every other `type` (slabs) is the design's.
        if (block.endsWith("chest") && property.equals("type")) return Role.DERIVED;
        // A rail's shape is the line's geometry - straight, ascending, a curve - and a curve is
        // laid on purpose; a stair's shape is the game's corner rule.
        if (block.endsWith("rail") && property.equals("shape")) return Role.REQUIRED;
        return intentional().contains(property) ? Role.REQUIRED : Role.DERIVED;
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
