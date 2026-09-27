package dev.jack.chunkscan;

import java.util.List;
import net.minecraft.SharedConstants;
import net.minecraft.server.Bootstrap;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class InventoryTransferTest {
    @BeforeAll static void boot() {
        SharedConstants.tryDetectVersion(); Bootstrap.bootStrap();
        // Offline bootstrap has no server data-component synchronization. Bind the fixture item only.
        var holder = Items.STONE.builtInRegistryHolder();
        if (!holder.areComponentsBound()) holder.bindComponents(net.minecraft.core.component.DataComponentMap.builder()
            .set(net.minecraft.core.component.DataComponents.MAX_STACK_SIZE,64).build());
    }
    private ItemStack stone(int count) { return count == 0 ? ItemStack.EMPTY : new ItemStack(Items.STONE,count); }
    private MenuObservations.Snapshot state(int source, int a, int b) {
        return new MenuObservations.Snapshot(1,List.of(stone(source),stone(a),stone(b)));
    }

    @Test void partialStackTransferRequiresMatchingSourceLossAndInventoryGain() {
        var tx = new InventoryTransfer(state(64,60,0),0,List.of(1,2));
        assertEquals(InventoryTransfer.Result.CONFIRMED,tx.reconcile(state(0,64,60)));
        assertEquals(64,tx.moved());
        assertEquals(InventoryTransfer.Result.CONFLICT,tx.reconcile(state(0,64,0)));
    }

    @Test void rejectionAndUnrelatedInventoryChangesAreNotConfirmed() {
        var tx = new InventoryTransfer(state(64,0,0),0,List.of(1,2));
        assertEquals(InventoryTransfer.Result.NO_CHANGE,tx.reconcile(state(64,0,0)));
        assertEquals(InventoryTransfer.Result.CONFLICT,tx.reconcile(state(64,64,0)));
        assertEquals(InventoryTransfer.Result.CONFLICT,tx.reconcile(state(0,0,0)));
    }

    @Test void observationsAreCopiesAndMenuReuseCannotSatisfyNewOpen() {
        var observations = new MenuObservations();
        Object connection = new Object();
        ItemStack packetStack = stone(64);
        observations.content(connection,1,List.of(packetStack));
        packetStack.setCount(0);
        assertEquals(64,observations.snapshot(connection,1).stack(0).getCount());
        assertNull(observations.snapshot(new Object(),1));
        observations.opened(connection,1);
        assertNull(observations.snapshot(connection,1));
        long before = observations.revision();
        observations.content(connection,1,List.of(stone(32)));
        assertTrue(observations.snapshot(connection,1).revision > before);
    }

    @Test void sameItemWithDifferentComponentsCannotConfirmTransfer() {
        ItemStack named = stone(64);
        named.set(net.minecraft.core.component.DataComponents.CUSTOM_NAME,
            net.minecraft.network.chat.Component.literal("Reserved"));
        var tx = new InventoryTransfer(state(64,0,0),0,List.of(1,2));
        var after = new MenuObservations.Snapshot(2,List.of(ItemStack.EMPTY,named,ItemStack.EMPTY));
        assertEquals(InventoryTransfer.Result.CONFLICT,tx.reconcile(after));
    }
}
