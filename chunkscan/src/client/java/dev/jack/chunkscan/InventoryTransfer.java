package dev.jack.chunkscan;

import java.util.List;
import net.minecraft.world.item.ItemStack;

/** Reconciles a quick-move with a freshly reopened, server-populated copy of the same container. */
final class InventoryTransfer {
    enum Result { CONFIRMED, NO_CHANGE, CONFLICT }
    private final MenuObservations.Snapshot before;
    private final int source;
    private final List<Integer> destination;
    private final ItemStack item;
    private int moved;

    InventoryTransfer(MenuObservations.Snapshot before, int source, List<Integer> destination) {
        this.before = before;
        this.source = source;
        this.destination = List.copyOf(destination);
        this.item = before.stack(source);
        if (item.isEmpty() || destination.contains(source)) throw new IllegalArgumentException("Invalid transfer slots");
    }

    Result reconcile(MenuObservations.Snapshot after) {
        moved = 0;
        if (after.size() != before.size()) return Result.CONFLICT;
        ItemStack remaining = after.stack(source);
        if (!remaining.isEmpty() && !ItemStack.isSameItemSameComponents(item, remaining)) return Result.CONFLICT;
        int lost = item.getCount() - remaining.getCount();
        int gained = count(after) - count(before);
        if (lost == 0 && gained == 0) return Result.NO_CHANGE;
        if (lost <= 0 || lost != gained) return Result.CONFLICT;
        moved = gained;
        return Result.CONFIRMED;
    }

    private int count(MenuObservations.Snapshot state) {
        int count = 0;
        for (int slot : destination) {
            ItemStack stack = state.stack(slot);
            if (ItemStack.isSameItemSameComponents(item, stack)) count += stack.getCount();
        }
        return count;
    }

    int moved() { return moved; }
    ItemStack item() { return item.copy(); }
}
