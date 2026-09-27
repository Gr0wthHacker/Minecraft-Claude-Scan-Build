package dev.jack.chunkscan;

import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import java.util.*;

/** Bounded search through supported, two-block-high corridors to actual quartz. */
final class QuartzSearch {
    interface World {
        boolean corridor(BlockPos feet);
        boolean ore(BlockPos cell);
    }
    record Deposit(BlockPos ore, List<BlockPos> path) {}

    static Deposit find(World world, BlockPos start, Set<BlockPos> rejected, int budget) {
        return new Search(start).advance(world,rejected,budget);
    }
    static final class Search {
        private final ArrayDeque<BlockPos> queue = new ArrayDeque<>();
        private final HashMap<BlockPos,BlockPos> parents = new HashMap<>();
        private final Set<BlockPos> examined = new HashSet<>();
        private int visited;
        Search(BlockPos start) { queue.add(start); parents.put(start,null); examined.add(start); }
        boolean done() { return queue.isEmpty() || visited >= 4096; }
        Deposit advance(World world, Set<BlockPos> rejected, int budget) {
        int slice = 0;
        while (!done() && slice++ < budget) {
            visited++;
            BlockPos feet = queue.remove();
            for (BlockPos cell : List.of(feet, feet.above())) {
                if (world.ore(cell) && !rejected.contains(cell)) {
                    var path = new ArrayList<BlockPos>();
                    for (BlockPos at = feet; at != null; at = parents.get(at)) path.add(at);
                    Collections.reverse(path);
                    return new Deposit(cell, List.copyOf(path));
                }
            }
            for (Direction d : Direction.Plane.HORIZONTAL) {
                BlockPos next = feet.relative(d);
                if (examined.add(next) && world.corridor(next)) {
                    parents.put(next, feet);
                    queue.add(next);
                }
            }
        }
        return null;
    }
}
}
