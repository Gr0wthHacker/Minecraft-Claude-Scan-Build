package dev.jack.chunkscan;

import java.util.*;
import net.minecraft.world.item.ItemStack;

/** Server-sent menu state, separate from the mutable, locally predicted menu. Client thread only. */
public final class MenuObservations {
    public static final MenuObservations LIVE = new MenuObservations();
    private Object connection;
    private long revision;
    private final Map<Integer, Snapshot> menus = new LinkedHashMap<>();

    static final class Snapshot {
        final long revision;
        private final List<ItemStack> items;
        Snapshot(long revision, List<ItemStack> items) {
            this.revision = revision;
            this.items = items.stream().map(ItemStack::copy).toList();
        }
        int size() { return items.size(); }
        ItemStack stack(int slot) { return items.get(slot).copy(); }
        boolean matches(net.minecraft.world.inventory.AbstractContainerMenu menu) {
            if (items.size() != menu.slots.size() || !menu.getCarried().isEmpty()) return false;
            for (var slot : menu.slots) if (!ItemStack.matches(slot.getItem(), items.get(slot.index))) return false;
            return true;
        }
    }

    private void bind(Object source) {
        if (source != connection) { connection = source; menus.clear(); revision++; }
    }

    public void opened(Object source, int menu) {
        bind(source); menus.remove(menu); revision++;
    }

    public void content(Object source, int menu, List<ItemStack> items) {
        bind(source);
        menus.put(menu, new Snapshot(++revision, items));
        while (menus.size() > 16) menus.remove(menus.keySet().iterator().next());
    }

    public void slot(Object source, int menu, int slot, ItemStack item) {
        bind(source);
        Snapshot old = menus.get(menu);
        if (old == null || slot < 0 || slot >= old.size()) return;
        var items = new ArrayList<>(old.items);
        items.set(slot, item);
        menus.put(menu, new Snapshot(++revision, items));
    }

    long revision() { return revision; }
    Snapshot snapshot(Object source, int menu) { return source == connection ? menus.get(menu) : null; }
    public void clear() { connection = null; menus.clear(); revision++; }
}
